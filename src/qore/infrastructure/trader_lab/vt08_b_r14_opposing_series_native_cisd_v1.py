"""VT08 B R14: independent original-M3 bearish-series close geometry.

Never infers authentic author CISD / protected swing from physical candles.
A original detector is NOT imported; all C1/C2 native bars are independently
attested against raw SHA and source IDs prior to source-only reconstruction.
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
from qore.infrastructure.trader_lab.vt08_b_r11_cisd_after_htf_close_chronology_v1 import (
    STAGE,
    audit_cisd_htf_sequence,
)

M3 = timedelta(minutes=3)
M30 = timedelta(minutes=30)
SCHEMA = "qore.vt08.b.r14.native_m3_bearish_series_bullish_cross.v1"


def independent_m3_cisd_proxy(
    bars: list[tuple[datetime, tuple[Decimal, Decimal, Decimal, Decimal]]],
    *,
    prior_low: Decimal,
) -> list[dict[str, object]]:
    """Identify bearish run then nonbearish close above run's initial open."""
    out: list[dict[str, object]] = []
    beginning: datetime | None = None
    level: Decimal | None = None
    low: Decimal | None = None
    last: datetime | None = None
    for when, (opened, _, bar_low, closed) in bars:
        if last is not None and when != last + M3:
            raise ValueError("R14 discontinuous original M3 time")
        last = when
        if closed < opened:
            if beginning is None:
                beginning, level, low = when, opened, bar_low
            else:
                assert low is not None
                low = min(low, bar_low)
            continue
        if beginning is not None:
            assert level is not None and low is not None
            if low < prior_low and closed > level:
                out.append({
                    "opposing_series_opened_at_utc": beginning.isoformat(),
                    "cisd_proxy_confirmed_at_utc": (when + M3).isoformat(),
                    "cisd_level_proxy": str(level),
                    "ps_low_proxy": str(low),
                })
        beginning = level = low = None
    return out


def audit_m3_opposing_series(
    frozen: dict[str, object], *, market: str, native_m3: Path,
) -> dict[str, object]:
    verified = audit_cisd_htf_sequence(
        frozen, expected_market=market, native_m3_file=native_m3,
    )
    sha, raw = _raw_bars(native_m3, "M3", market)
    stages = frozen.get("examples_by_stage")
    cases = stages.get(STAGE) if isinstance(stages, dict) else None
    if not isinstance(cases, list) or len(cases) != verified[
        "r3_unique_m3_proxy_source_cases"
    ]:
        raise ValueError("R14 changed original R3 source denominator")
    counts: Counter[str] = Counter()
    witnesses: list[dict[str, object]] = []
    ids: set[str] = set()
    for case in cases:
        if not isinstance(case, dict) or case.get("market") != market:
            raise ValueError("R14 cross-market event")
        c1 = _instant(case.get("c1_opened_at_utc"))
        c2 = _instant(case.get("c2_opened_at_utc"))
        entry = _instant(case.get("decision_at_utc"))
        if c1 + M30 != c2 or c2 + M30 != entry:
            raise ValueError("R14 C1/C2/C3 time changed")
        digest = hashlib.sha256(
            (market+"|"+c2.isoformat()+"|"+entry.isoformat()).encode()
        ).hexdigest()
        if digest in ids:
            raise ValueError("R14 duplicate source case")
        ids.add(digest)
        c1_rec = case.get("c1_m3_raw_bar_receipts")
        c2_rec = case.get("c2_m3_raw_bar_receipts")
        detail = case.get("details")
        if (
            not isinstance(c1_rec, list) or len(c1_rec) != 10
            or not isinstance(c2_rec, list) or len(c2_rec) != 10
            or not isinstance(detail, dict)
        ):
            raise ValueError("R14 missing original ten-bar physical source")
        low_c1: Decimal | None = None
        for i, rec in enumerate(c1_rec):
            _, _, bar_low, _ = _verify_bar(
                rec, expected_open=c1+i*M3, minutes=3,
                profile="M3", source_sha=sha, raw=raw,
            )
            low_c1 = bar_low if low_c1 is None else min(low_c1, bar_low)
        assert low_c1 is not None
        ordered: list[
            tuple[datetime, tuple[Decimal, Decimal, Decimal, Decimal]]
        ] = []
        for i, rec in enumerate(c2_rec):
            when = c2+i*M3
            ordered.append((when, _verify_bar(
                rec, expected_open=when, minutes=3,
                profile="M3", source_sha=sha, raw=raw,
            )))
        geometry = independent_m3_cisd_proxy(ordered, prior_low=low_c1)
        if len(geometry) != 1:
            raise ValueError("R14 native M3 proxy count disagrees with A")
        one = geometry[0]
        if (
            _instant(detail.get("opposing_series_opened_at_utc"))
            != _instant(one["opposing_series_opened_at_utc"])
            or _instant(detail.get("cisd_confirmed_at_utc"))
            != _instant(one["cisd_proxy_confirmed_at_utc"])
            or Decimal(str(detail.get("ps_proxy_price")))
            != Decimal(str(one["ps_low_proxy"]))
            or Decimal(str(detail.get("cisd_level_proxy")))
            != Decimal(str(one["cisd_level_proxy"]))
        ):
            raise ValueError("R14 source-rebuilt opposing M3 differs from A")
        counts["independent_unique_m3_opposing_series_proxy"] += 1
        counts["cisd_proxy_known_asof_c3"] += int(
            _instant(one["cisd_proxy_confirmed_at_utc"]) <= entry
        )
        witnesses.append({
            "market": market, "case_id_sha256": digest,
            "c1_low": str(low_c1), "c2_open": c2.isoformat(),
            "c3_open": entry.isoformat(), **one,
            "original_m3_source_bar_ids": [
                rec["source_bar_id"] for rec in c2_rec
                if _instant(rec["opened_at_utc"]) >= _instant(
                    one["opposing_series_opened_at_utc"]
                ) and _instant(rec["closed_at_utc"]) <= _instant(
                    one["cisd_proxy_confirmed_at_utc"]
                )
            ],
            "author_quality_of_cisd": "D_UNADJUDICATED",
            "author_protected_swing_validated": False,
        })
    if len(ids) != len(witnesses):
        raise ValueError("R14 native source conservation error")
    return {
        "schema": SCHEMA, "market": market,
        "native_m3_sha256": sha,
        "frozen_source_cases": len(witnesses),
        "counts": dict(counts), "all_source_only_witnesses": witnesses,
        "physical_cisd_proxy_reconstructed": True,
        "author_cisd_and_ps_validated": False,
        "cognitive_admissions": 0, "broker_fills": 0,
        "profit_factor": None, "holdout_7y_accessed": False,
        "sizing_used": False,
    }


def result_sha256(result: dict[str, object]) -> str:
    return hashlib.sha256(json.dumps(
        result, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode()).hexdigest()
