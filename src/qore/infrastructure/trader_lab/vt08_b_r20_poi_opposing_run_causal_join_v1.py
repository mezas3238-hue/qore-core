"""VT08 B R20: genuine PRE-CISD POI touch vs causal bearish run.

Physical/causal audit only: TTrades links important POI, bearish movement
INTO it, CISD across those opposing candles, protected swing. The source
does not supply a universal POI identity/selection criterion. Thus no
source-complete entries can be emitted by this module.

R18 full native HTF POI inventory + R19 SHA-fixed blind review + R14
independent M3 opposing run + R3 immutable raw cTrader M3.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.trader_lab.vt08_5m_b_independent_raw_receipts_v1 import (
    _instant,
    _raw_bars,
    _verify_bar,
)
from qore.infrastructure.trader_lab.vt08_b_r11_cisd_after_htf_close_chronology_v1 import (
    STAGE,
)
from qore.infrastructure.trader_lab.vt08_b_r14_opposing_series_native_cisd_v1 import (
    audit_m3_opposing_series,
)
from qore.infrastructure.trader_lab.vt08_b_r18_pre_cisd_h1_poi_native_timing_v1 import (
    SCHEMA as R18_SCHEMA,
)
from qore.infrastructure.trader_lab.vt08_b_r18_pre_cisd_h1_poi_native_timing_v1 import (
    digest as r18_digest,
)
from qore.infrastructure.trader_lab.vt08_b_r19_blind_dual_rater_poi_queue_v1 import (
    MARKET_EXPECTED,
)
from qore.infrastructure.trader_lab.vt08_b_r19_blind_dual_rater_poi_queue_v1 import (
    SCHEMA as R19_SCHEMA,
)
from qore.infrastructure.trader_lab.vt08_b_r19_blind_dual_rater_poi_queue_v1 import (
    digest as r19_digest,
)

SCHEMA = "qore.vt08.b.r20.poi_to_opposing_m3_run_native_causal_join.v1"
M3 = timedelta(minutes=3)
PRE = "TOUCHED_BEFORE_CISD_BAR"
SAME = "TOUCHED_IN_CISD_BAR_SEQUENCE_UNKNOWN"
AUTHOR = (
    "https://ttrades.com/let-the-wick-form-trade-the-body-stop-getting-stopped-out/"
)
R19_DIGESTS = {
    "EURJPY": "f553e6f8da86d7af30ce1f811257b0d05b892d03ee4d60d046d1f10bb65c5b7c",
    "USDCHF": "87d43288eecddce84c1fcc99578558cb03f1be69dbf5d438766582fbd8e14bc4",
    "NZDUSD": "cbba1ff00d19608968ed58c48b7eb5fdfd038e5187ab738b4710ae0b91e26e56",
    "CADJPY": "b16f7ffe78892c5eb53d2ecf33c2057e7a70e70140e2b1fd1e2ddd3673486e32",
    "USDCAD": "a5ed7db7cb965db87ffb949ea0644d24199114895fd3b3da3529c870781c01f9",
}


def classify_physical_poi_into_series(
    fvg: dict[str, object] | None,
    *,
    verified_bars: list[tuple[object, tuple[Decimal, Decimal, Decimal, Decimal], str]],
    series_open: object,
    cisd_close: object,
    c1_low: Decimal,
) -> dict[str, object]:
    """Reverify first touch from ORIGINAL M3, not from source assertions."""
    beginning = series_open
    end = cisd_close
    if not hasattr(beginning, "tzinfo") or not hasattr(end, "tzinfo"):
        raise ValueError("R20 needs datetime source clocks")
    if beginning.utcoffset() is None or end.utcoffset() is None or end <= beginning:
        raise ValueError("R20 illegal opposing-series chronology")
    if not verified_bars or c1_low <= 0:
        raise ValueError("R20 missing physical original source")
    expected_next = verified_bars[0][0]
    for when, _, bid in verified_bars:
        if when != expected_next or not isinstance(bid, str) or len(bid) != 64:
            raise ValueError("R20 discontinuous/unsigned source M3 receipts")
        expected_next = when + M3
    if beginning not in {row[0] for row in verified_bars}:
        raise ValueError("R20 opposing run outside native C2 source")
    if end-M3 not in {row[0] for row in verified_bars}:
        raise ValueError("R20 CISD close not native M3 close")
    if not beginning < end:
        raise ValueError("R20 no opposing run before CISD")
    if fvg is None:
        return {
            "original_fvg_physical_exists": False,
            "physical_first_touch_relative_to_run": "NO_H1_THREE_BAR_FVG",
            "bearish_series_touched_fvg": False,
            "bearish_series_swept_c1_low": None,
            "same_bar_fvg_touch_and_liquidity_sweep": None,
            "author_poi_significance_certified": False,
        }
    low = Decimal(str(fvg["lower"]))
    high = Decimal(str(fvg["upper"]))
    if not (Decimal("0") < low < high):
        raise ValueError("R20 invalid source FVG price zone")
    touched = [
        (when, bid) for when, (_, bar_high, bar_low, _) , bid in verified_bars
        if bar_low <= high and bar_high >= low
    ]
    native_first = touched[0] if touched else None
    claimed_at = fvg.get("first_touch_bar_opened_at_utc")
    claimed_id = fvg.get("first_touch_m3_source_bar_id")
    if (
        (native_first is None and (claimed_at is not None or claimed_id is not None))
        or (
            native_first is not None and (
                claimed_at != native_first[0].isoformat()
                or claimed_id != native_first[1]
            )
        )
    ):
        raise ValueError("R20 POI first touch disagrees with raw native M3")
    phase = fvg.get("first_touch_phase")
    if native_first is None:
        expected_phase = "NOT_TOUCHED_DURING_C2"
        relative = "NOT_TOUCHED_DURING_C2"
    elif native_first[0] + M3 < end:
        expected_phase = PRE
        relative = (
            "BEFORE_BEARISH_OPPOSING_SERIES"
            if native_first[0] < beginning
            else "WITHIN_BEARISH_OPPOSING_SERIES"
        )
    elif native_first[0] + M3 == end:
        expected_phase = SAME
        relative = "IN_CISD_CONFIRMATION_BAR_INTRABAR_UNKNOWN"
    else:
        expected_phase = "TOUCHED_AFTER_CISD_CLOSE"
        relative = "AFTER_CISD_CLOSE"
    if phase != expected_phase:
        raise ValueError("R20 R18 time classification disagrees native M3")
    run = [
        (when, ohlc, bid) for when, ohlc, bid in verified_bars
        if beginning <= when < end-M3
    ]
    if not run or any(ohlc[3] >= ohlc[0] for _, ohlc, _ in run):
        raise ValueError("R20 supposed bearish opposing run is not down-closes")
    swept = [(when, bid) for when, (_, _, bar_low, _), bid in run if bar_low < c1_low]
    run_touch = [
        (when, bid) for when, (_, bar_high, bar_low, _), bid in run
        if bar_low <= high and bar_high >= low
    ]
    return {
        "original_fvg_physical_exists": True,
        "fvg_direction_geometry": fvg["type"],
        "fvg_first_touch_m3_bar_id": claimed_id,
        "fvg_first_touch_phase": phase,
        "physical_first_touch_relative_to_run": relative,
        "bearish_series_touched_fvg": bool(run_touch),
        "bearish_series_fvg_touch_bar_ids": [x[1] for x in run_touch],
        "bearish_series_swept_c1_low": bool(swept),
        "bearish_series_sweep_bar_ids": [x[1] for x in swept],
        "same_bar_fvg_touch_and_liquidity_sweep": bool(
            set(x[1] for x in swept) & set(x[1] for x in run_touch)
        ),
        "author_poi_significance_certified": False,
    }


def audit_r20(
    frozen: dict[str, object],
    r18: dict[str, object],
    r19: dict[str, object],
    *,
    market: str,
    native_m3: Path,
) -> dict[str, object]:
    """Strictly join whole original source and preregistered blind sample."""
    if market not in MARKET_EXPECTED:
        raise ValueError("R20 market not in original VT08 scope")
    expected, pinned18 = MARKET_EXPECTED[market]
    if (
        r18.get("schema") != R18_SCHEMA
        or r18_digest(r18) != pinned18
        or r18.get("market") != market
        or r18.get("owner_scope") != "VT08_CURRENT_ONLY_NO_QORE_ALPHA"
        or r18.get("original_source_cases") != expected
        or r19.get("schema") != R19_SCHEMA
        or r19.get("market") != market
        or r19_digest(r19) != R19_DIGESTS[market]
        or r19.get("original_r18_sha256") != pinned18
        or r19.get("original_r18_cases") != expected
        or r19.get("rater_A_signed") != 0
        or r19.get("rater_B_signed") != 0
    ):
        raise ValueError("R20 source-only immutable R18/R19 input mismatch")
    independent = audit_m3_opposing_series(
        frozen, market=market, native_m3=native_m3,
    )
    sha, raw = _raw_bars(native_m3, "M3", market)
    if sha != r18.get("original_m3_sha256") or independent[
        "frozen_source_cases"
    ] != expected:
        raise ValueError("R20 original source native M3 mismatch")
    all18 = r18["all_pre_cisd_h1_poi_source_witnesses"]
    m3_source = frozen["examples_by_stage"][STAGE]
    r14_by_id = {
        i["case_id_sha256"]: i
        for i in independent["all_source_only_witnesses"]
    }
    r18_by_id = {i["case_id_sha256"]: i for i in all18}
    if len(r14_by_id) != expected or len(r18_by_id) != expected:
        raise ValueError("R20 original source IDs duplicate")
    counts: Counter[str] = Counter()
    full = []
    for case in m3_source:
        c2 = _instant(case["c2_opened_at_utc"])
        entry = _instant(case["decision_at_utc"])
        cid = hashlib.sha256(
            (market + "|" + c2.isoformat() + "|" + entry.isoformat()).encode()
        ).hexdigest()
        if cid not in r18_by_id or cid not in r14_by_id:
            raise ValueError("R20 missing cross-attested R14/R18 source case")
        a = r18_by_id[cid]
        b = r14_by_id[cid]
        series_at = _instant(b["opposing_series_opened_at_utc"])
        cisd_at = _instant(b["cisd_proxy_confirmed_at_utc"])
        if (
            a["cisd_closed_at_utc"] != cisd_at.isoformat()
            or a["c2_opened_at_utc"] != c2.isoformat()
            or a["c3_opened_at_utc"] != entry.isoformat()
        ):
            raise ValueError("R20 R14/R18 CISD clocks disagree")
        receipts = case["c2_m3_raw_bar_receipts"]
        observed = [
            (c2+i*M3, _verify_bar(
                rec, expected_open=c2+i*M3, minutes=3,
                profile="M3", source_sha=sha, raw=raw,
            ), rec["source_bar_id"])
            for i, rec in enumerate(receipts)
        ]
        physical = classify_physical_poi_into_series(
            a["pre_existing_h1_fvg_candidate"],
            verified_bars=observed, series_open=series_at,
            cisd_close=cisd_at, c1_low=Decimal(b["c1_low"]),
        )
        counts["all_original_source_cases"] += 1
        zone = a["pre_existing_h1_fvg_candidate"]
        if isinstance(zone, dict):
            counts["fvg_"+zone["type"]] += 1
            key = "fvg_"+zone["type"]+"_"+physical[
                "physical_first_touch_relative_to_run"
            ]
            counts[key] += 1
            counts["fvg_bearish_run_touched"] += int(
                physical["bearish_series_touched_fvg"]
            )
            counts["fvg_same_bar_run_sweep"] += int(
                physical["same_bar_fvg_touch_and_liquidity_sweep"]
            )
        full.append({
            "case_id_sha256": cid, "market": market,
            "original_r18_source_sha256": pinned18,
            "c2_opened_at_utc": c2.isoformat(),
            "opposing_series_opened_at_utc": series_at.isoformat(),
            "cisd_close_at_utc": cisd_at.isoformat(),
            **physical, "author_validated_swing": False,
            "author_protected_swing": False, "source_complete": False,
        })
    if len(full) != expected:
        raise ValueError("R20 incomplete full VT08 denominator")
    by_id = {x["case_id_sha256"]: x for x in full}
    sample = r19["review_packets"]
    if len(sample) != r19.get("selected_source_only_cases"):
        raise ValueError("R20 blind R19 sample count drift")
    enriched = []
    for item in sample:
        cid = item["case_id_sha256"]
        if cid not in by_id:
            raise ValueError("R20 blind packet missing source R20")
        enriched.append({
            **item,
            "independent_bearish_run_causal_witness": by_id[cid],
            "review_status": "AWAITING_TWO_REAL_SOURCE_RATERS",
        })
    return {
        "schema": SCHEMA, "market": market,
        "owner_scope": "VT08_CURRENT_ONLY_NO_QORE_ALPHA",
        "r18_pinned_sha256": pinned18,
        "r19_pinned_sha256": R19_DIGESTS[market],
        "original_native_m3_sha256": sha,
        "original_cases": expected, "counts": dict(counts),
        "all_physical_causal_opposing_run_witnesses": full,
        "blind_review_cases": len(enriched),
        "enriched_blind_review_packets": enriched,
        "source_authorized_entries": 0,
        "genuine_human_A_signoffs": 0,
        "genuine_human_B_signoffs": 0,
        "cognitive_admissions": 0, "broker_fills": 0,
        "profit_factor": None, "holdout_7y_accessed": False,
        "sizing_used": False, "poi_source": AUTHOR,
    }


def digest(data: dict[str, object]) -> str:
    return hashlib.sha256(json.dumps(
        data, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode()).hexdigest()
