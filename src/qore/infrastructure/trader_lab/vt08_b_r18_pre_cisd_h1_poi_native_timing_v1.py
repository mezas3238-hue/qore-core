"""VT08 B R18: independent PRE-CISD HTF POI candidate timing census.

On original, frozen source-only VT08 M3/M15 cTrader bars, enumerate the
last three *fully closed* H1 lows and H1 three-bar FVG zones existing
before C2 starts, then independently locate their first C2 M3 touches.
A touch in the CISD M3 bar is not proven BEFORE the CISD close intrabar;
a touched low/FVG is not yet an AUTHOR-SIGNIFICANT POI.
No alpha import, trade, fill, PnL, lookahead, or alternative VT08 track.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.trader_lab.vt08_5m_b_independent_raw_receipts_v1 import (
    _instant,
    _raw_bars,
    _verify_bar,
)
from qore.infrastructure.trader_lab.vt08_b_r10_three_h1_current_asof_v1 import (
    PINNED_M15,
    _window,
)
from qore.infrastructure.trader_lab.vt08_b_r11_cisd_after_htf_close_chronology_v1 import (
    STAGE,
    audit_cisd_htf_sequence,
)
from qore.infrastructure.trader_lab.vt08_b_r16_owner_scope_no_alpha_v1 import (
    audit_frozen_source_program_scope,
)

SCHEMA = "qore.vt08.b.r18.pre_cisd_h1_poi_physical_timing.v1"
M3 = timedelta(minutes=3)
M30 = timedelta(minutes=30)
H1 = timedelta(hours=1)
POI_SOURCE = "https://ttrades.com/ttrades-ideal-formation-high-probability-swing-points/"
SWING_SOURCE = "https://ttrades.com/relevant-swings-which-swing-highs-and-lows-matter-in-trading/"


def h1_causal_context(
    raw15: dict, sha15: str, *, c2_open: datetime,
) -> dict[str, object]:
    """Upstream H1 must be closed by C2.open; no partial/future H1."""
    if c2_open.utcoffset() is None or c2_open.minute not in (0, 30):
        raise ValueError("R18 source C2 alignment impossible")
    hour = c2_open.replace(minute=0, second=0, microsecond=0)
    candles = []
    for i in (3, 2, 1):
        begin = hour - i * H1
        obs = _window(raw15, sha15, begin, begin + H1)
        if obs is None:
            return {"status": "UPSTREAM_H1_SOURCE_GAP", "h1_candles": []}
        prices = obs.get("ohlc")
        if not isinstance(prices, list) or len(prices) != 4:
            raise ValueError("R18 incomplete H1 raw aggregate")
        if len(obs["bar_ids"]) != 4:
            raise ValueError("R18 incomplete original H1 provenance")
        if begin + H1 > c2_open:
            raise ValueError("R18 pre-C2 H1 future leakage")
        candles.append({
            "opened_at_utc": begin.isoformat(),
            "available_at_utc": (begin + H1).isoformat(),
            "raw_m15_bar_ids": obs["bar_ids"],
            "ohlc": prices,
        })
    older, _, newer = candles
    older_high = Decimal(older["ohlc"][1])
    older_low = Decimal(older["ohlc"][2])
    newer_high = Decimal(newer["ohlc"][1])
    newer_low = Decimal(newer["ohlc"][2])
    fvg = None
    if older_high < newer_low:
        fvg = {
            "type": "BULLISH_H1_3BAR_FVG_GEOMETRY",
            "lower": str(older_high),
            "upper": str(newer_low),
            "available_at_utc": newer["available_at_utc"],
            "source_bar_ids": older["raw_m15_bar_ids"] + newer["raw_m15_bar_ids"],
        }
    elif newer_high < older_low:
        fvg = {
            "type": "BEARISH_H1_3BAR_FVG_GEOMETRY",
            "lower": str(newer_high),
            "upper": str(older_low),
            "available_at_utc": newer["available_at_utc"],
            "source_bar_ids": older["raw_m15_bar_ids"] + newer["raw_m15_bar_ids"],
        }
    return {"status": "THREE_PRIOR_H1_CLOSED", "h1_candles": candles, "fvg": fvg}


def first_touch_phase(
    observed: list[tuple[datetime, tuple[Decimal, Decimal, Decimal, Decimal]]],
    *,
    lower: Decimal,
    upper: Decimal,
    cisd_closed_at: datetime,
) -> dict[str, object]:
    """CISD-bar touch has UNKNOWN intrabar sequence, never counted as prior."""
    if lower > upper or not observed or cisd_closed_at.utcoffset() is None:
        raise ValueError("R18 invalid zone or cutoff")
    last: datetime | None = None
    candidates = []
    for opened, (_, high, low, _) in observed:
        if last is not None and opened != last + M3:
            raise ValueError("R18 gaps in native C2 M3 source")
        if opened.utcoffset() is None:
            raise ValueError("R18 M3 clock naive")
        last = opened
        if low <= upper and high >= lower:
            candidates.append(opened)
    if not candidates:
        return {
            "first_touch_phase": "NOT_TOUCHED_DURING_C2",
            "first_touch_bar_opened_at_utc": None,
        }
    first = candidates[0]
    if first + M3 < cisd_closed_at:
        phase = "TOUCHED_BEFORE_CISD_BAR"
    elif first + M3 == cisd_closed_at:
        phase = "TOUCHED_IN_CISD_BAR_SEQUENCE_UNKNOWN"
    else:
        phase = "TOUCHED_AFTER_CISD_CLOSE"
    return {"first_touch_phase": phase, "first_touch_bar_opened_at_utc": first.isoformat()}


def audit_pre_cisd_h1_poi_inventory(
    frozen: dict[str, object], *, market: str,
    original_m3: Path, original_m15: Path,
) -> dict[str, object]:
    """Reconcile 2,657 source-only identities with 3 original H1 M15 bars/TF."""
    owner = audit_frozen_source_program_scope(frozen, expected_market=market)
    timing = audit_cisd_htf_sequence(
        frozen, expected_market=market, native_m3_file=original_m3,
    )
    sha3, raw3 = _raw_bars(original_m3, "M3", market)
    sha15, raw15 = _raw_bars(original_m15, "M15", market)
    if sha15 != PINNED_M15[market] or sha15 != frozen.get("source_m15_sha256"):
        raise ValueError("R18 original cTrader M15 SHA changed")
    if sha3 != frozen.get("source_m3_sha256"):
        raise ValueError("R18 original cTrader M3 SHA changed")
    cases = frozen["examples_by_stage"][STAGE]
    if len(cases) != owner["frozen_vt08_cases_verified"] or len(cases) != timing[
        "r3_unique_m3_proxy_source_cases"
    ]:
        raise ValueError("R18 frozen universe changed")
    counts: Counter[str] = Counter()
    out = []
    seen: set[str] = set()
    for item in cases:
        c2 = _instant(item["c2_opened_at_utc"])
        entry = _instant(item["decision_at_utc"])
        if entry != c2 + M30:
            raise ValueError("R18 C2/C3 clock drift")
        details = item.get("details")
        if not isinstance(details, dict):
            raise ValueError("R18 original CISD receipt absent")
        cisd = _instant(details["cisd_confirmed_at_utc"])
        if not (c2 < cisd <= entry):
            raise ValueError("R18 CISD not inside completed C2")
        cid = hashlib.sha256(
            (market + "|" + c2.isoformat() + "|" + entry.isoformat()).encode()
        ).hexdigest()
        if cid in seen:
            raise ValueError("R18 duplicate VT08 source case")
        seen.add(cid)
        c2_recs = item.get("c2_m3_raw_bar_receipts")
        if not isinstance(c2_recs, list) or len(c2_recs) != 10:
            raise ValueError("R18 missing original source M3 window")
        first_touch_ids = {
            _instant(rec["opened_at_utc"]): rec["source_bar_id"]
            for rec in c2_recs
        }
        bars = [(c2 + M3 * i, _verify_bar(
            rec, expected_open=c2 + M3 * i, minutes=3, profile="M3",
            source_sha=sha3, raw=raw3,
        )) for i, rec in enumerate(c2_recs)]
        h = h1_causal_context(raw15, sha15, c2_open=c2)
        levels = []
        if h["status"] == "THREE_PRIOR_H1_CLOSED":
            for candle in h["h1_candles"]:
                level = Decimal(candle["ohlc"][2])
                touch = first_touch_phase(
                    bars, lower=level, upper=level, cisd_closed_at=cisd,
                )
                touch_open = touch["first_touch_bar_opened_at_utc"]
                touch_id = (
                    first_touch_ids.get(_instant(touch_open))
                    if touch_open is not None else None
                )
                if touch_open is not None and touch_id is None:
                    raise ValueError("R18 low first touch lacks source M3 bar ID")
                levels.append({
                    "first_touch_m3_source_bar_id": touch_id,
                    "type": "H1_PREVIOUS_CLOSED_CANDLE_LOW_GEOMETRY",
                    "level": str(level),
                    "source_h1_opened_at_utc": candle["opened_at_utc"],
                    "available_at_utc": candle["available_at_utc"],
                    "raw_m15_bar_ids": candle["raw_m15_bar_ids"],
                    **touch, "author_relevant_low_adjudicated": False,
                })
            counts["cases_three_upstream_h1_complete"] += 1
        else:
            counts["cases_h1_gap_quarantined"] += 1
        fvg = h.get("fvg")
        fvg_witness = None
        if fvg is not None:
            touch = first_touch_phase(
                bars, lower=Decimal(fvg["lower"]),
                upper=Decimal(fvg["upper"]), cisd_closed_at=cisd,
            )
            fvg_touch_open = touch["first_touch_bar_opened_at_utc"]
            fvg_touch_id = (
                first_touch_ids.get(_instant(fvg_touch_open))
                if fvg_touch_open is not None else None
            )
            if fvg_touch_open is not None and fvg_touch_id is None:
                raise ValueError("R18 FVG first touch lacks source M3 bar ID")
            fvg_witness = {
                **fvg, **touch,
                "first_touch_m3_source_bar_id": fvg_touch_id,
                "author_significant_poi": False,
            }
            counts["cases_pre_c2_h1_fvg_exists"] += 1
            counts["fvg_"+touch["first_touch_phase"]] += 1
            counts["fvg_"+fvg["type"]] += 1
            counts["fvg_"+fvg["type"]+"_"+touch["first_touch_phase"]] += 1
        h1_pre_touch = any(
            x["first_touch_phase"] == "TOUCHED_BEFORE_CISD_BAR" for x in levels
        )
        h1_same = any(
            x["first_touch_phase"] == "TOUCHED_IN_CISD_BAR_SEQUENCE_UNKNOWN"
            for x in levels
        )
        counts["cases_h1_prior_low_touched_before_cisd_bar"] += int(h1_pre_touch)
        counts["cases_h1_prior_low_touch_in_cisd_bar_no_prior"] += int(
            h1_same and not h1_pre_touch
        )
        counts["cases_source_only"] += 1
        out.append({
            "market": market, "case_id_sha256": cid,
            "c2_opened_at_utc": c2.isoformat(),
            "cisd_closed_at_utc": cisd.isoformat(),
            "c3_opened_at_utc": entry.isoformat(),
            "upstream_h1_status": h["status"],
            "pre_existing_h1_low_candidates": levels,
            "pre_existing_h1_fvg_candidate": fvg_witness,
            "author_relevant_swing_selected": False,
            "author_poi_significant_and_selected": False,
            "author_protected_swing_adjudicated": False,
            "author_source_complete": False,
            "cognitive_admission": False, "broker_fill": False,
        })
    if len(out) != len(seen) or len(out) != len(cases):
        raise ValueError("R18 source loss/deduplication")
    return {
        "schema": SCHEMA, "market": market,
        "original_m3_sha256": sha3, "original_m15_sha256": sha15,
        "original_source_cases": len(out), "counts": dict(counts),
        "all_pre_cisd_h1_poi_source_witnesses": out,
        "important_poi_is_not_proven_by_touch": True,
        "h1_fvg_was_causal_preexisting_when_available": True,
        "poi_author_source": POI_SOURCE, "swing_author_source": SWING_SOURCE,
        "owner_scope": "VT08_CURRENT_ONLY_NO_QORE_ALPHA",
        "source_complete_entries": 0, "cognitive_admissions": 0,
        "broker_fills": 0, "profit_factor": None,
        "holdout_7y_accessed": False, "sizing_used": False,
    }


def digest(result: dict[str, object]) -> str:
    return hashlib.sha256(json.dumps(
        result, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode()).hexdigest()
