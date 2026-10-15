"""VT08 Trader Lab indexed ultra-fast RAW geometry runner (research only).

Performance seam, NOT an alternative strategy: index M30 from original M3 and
M15 once per clock, reuse adjacent C1/C2 windows, and verify exact equality to
the slower B R3 independent reference. No PS judgement, no trades, no PnL.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Mapping
from datetime import datetime, timedelta
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.vt08_5m_b_independent_raw_receipts_v1 import (
    _aggregate,
    _instant,
    _prices,
    _raw_bars,
)

NY = ZoneInfo("America/New_York")
OHLC = tuple[Decimal, Decimal, Decimal, Decimal]
CENSUS_SCHEMA = "qore.vt08.b.r3.indexed_ultrafast_geometry.v1"


def _hash_counts(value: Mapping[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()


def _is_c2_clock(opened: datetime) -> bool:
    local = opened.astimezone(NY)
    return (
        1 <= local.hour < 13
        and local.minute in (0, 30)
        and local.second == 0
        and local.microsecond == 0
    )


def run_indexed_native_geometry(
    *, market: str, m3_file: Path, m15_file: Path
) -> dict[str, object]:
    """Pre-index closed M30 once; reuse C1/C2, fail closed on missing bars."""
    sha3, raw3 = _raw_bars(m3_file, "M3", market)
    sha15, raw15 = _raw_bars(m15_file, "M15", market)
    clocks = sorted(t for t in raw3 if _is_c2_clock(t))
    if not clocks:
        raise ValueError("VT08 indexed runner no C2 windows")

    @lru_cache(maxsize=60000)
    def m30(profile: str, start: datetime) -> OHLC | None:
        if profile == "M3":
            raw, minutes, count = raw3, 3, 10
        elif profile == "M15":
            raw, minutes, count = raw15, 15, 2
        else:
            raise ValueError("VT08 indexed runner invalid source timeframe")
        rows: list[OHLC] = []
        for i in range(count):
            at = start + timedelta(minutes=minutes * i)
            bar = raw.get(at)
            if bar is None or _instant(bar.get("closed_at")) != (
                at + timedelta(minutes=minutes)
            ):
                return None
            rows.append(
                _prices(tuple(str(bar.get(k)) for k in (
                    "open", "high", "low", "close"
                )))
            )
        return _aggregate(rows)

    # The four independent source calls are cached across adjacent windows:
    # C1 of next C2 = previously computed C2, without future lookahead.
    missing = 0
    mismatch = 0
    geometry_negative = 0
    geometry_positive = 0
    for c2 in clocks:
        c1 = c2 - timedelta(minutes=30)
        a3, b3 = m30("M3", c1), m30("M3", c2)
        a15, b15 = m30("M15", c1), m30("M15", c2)
        if a3 is None or b3 is None or a15 is None or b15 is None:
            missing += 1
        elif a3 != a15 or b3 != b15:
            mismatch += 1
        elif (
            b3[2] < a3[2]
            and b3[1] <= a3[1]
            and a3[2] < b3[3] < a3[1]
            and b3[3] > b3[0]
        ):
            geometry_positive += 1
        else:
            geometry_negative += 1

    counts = {
        "c2_windows_total": len(clocks),
        "missing_raw_windows": missing,
        "m3_m15_m30_mismatches": mismatch,
        "rejected_bullish_c2_geometry": geometry_negative,
        "passes_c2_bullish_geometry": geometry_positive,
    }
    if sum((
        missing, mismatch, geometry_negative, geometry_positive
    )) != len(clocks):
        raise ValueError("VT08 indexed runner conservation failure")
    return {
        "schema": CENSUS_SCHEMA,
        "market": market,
        "m3_raw_sha256": sha3,
        "m15_raw_sha256": sha15,
        **counts,
        "geometry_counts_sha256": _hash_counts(counts),
        "reference_B_R3_differential_passed": False,
        "author_semantics_certified": False,
        "cognitive_certified": False,
        "economic_gates_evaluated": False,
        "holdout_accessed": False,
        "orders_authorized": False,
    }


def compare_indexed_against_reference(
    indexed: Mapping[str, object],
    reference: Mapping[str, object],
) -> dict[str, object]:
    """Mandatory differential gate before fast result can be published."""
    keys = (
        "market", "c2_windows_total", "missing_raw_windows",
        "m3_m15_m30_mismatches", "rejected_bullish_c2_geometry",
        "passes_c2_bullish_geometry",
    )
    for field in keys:
        if indexed.get(field) != reference.get(field):
            raise ValueError(f"VT08 indexed vs independent B reference drift: {field}")
    if (
        indexed.get("author_semantics_certified") is not False
        or indexed.get("economic_gates_evaluated") is not False
        or reference.get("source_author_entries_certified") != 0
        or reference.get("economic_gates_evaluated") is not False
    ):
        raise ValueError("VT08 indexed runner prohibited promotion of source/PNL")
    return {
        **indexed,
        "reference_B_R3_differential_passed": True,
    }
