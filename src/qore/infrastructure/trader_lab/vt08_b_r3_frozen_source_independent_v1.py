"""Independent B verification of A's frozen 93k C2 census and every raw precursor.

A's producer/PS detector is NEVER imported: B independently recounts native
M3/M15 C2 window geometry and rechecks ALL 2657 A-source positive bar receipts.
The PS/CISD *author meaning* remains pending; this is not an entry signal or PnL.
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.vt08_5m_b_independent_raw_receipts_v1 import (
    _aggregate,
    _instant,
    _prices,
    _raw_bars,
    _verify_bar,
)

NY = ZoneInfo("America/New_York")
POSITIVE_STAGE = "UNIQUE_M3_CISD_PS_SHAPE_REQUIRES_AUTHOR_ADJUDICATION"
C2_INVALID = "C2_NOT_BULLISH_SINGLE_LOW_SWEEP"
CROSS = "M30_CROSS_SOURCE_MISMATCH"
MISSING = "MISSING_M30_M3_OR_M15"
FAMILY = "BULLISH_M30_C2_REVERSAL_M3_CISD_C3_POSITIONAL"
SCHEMA = "qore.vt08.a.frozen_bullish_m30m3.source_funnel.v1"


def _window(
    raw: Mapping[datetime, Mapping[str, object]],
    opened: datetime, duration: int, count: int,
) -> list[tuple] | None:
    values: list[tuple] = []
    for n in range(count):
        t = opened + timedelta(minutes=n * duration)
        row = raw.get(t)
        if row is None or _instant(row.get("closed_at")) != (
            t + timedelta(minutes=duration)
        ):
            return None
        values.append(_prices(tuple(str(row.get(k)) for k in (
            "open", "high", "low", "close"
        ))))
    return values


def _source_times(case: Mapping[str, object]) -> tuple[datetime, datetime]:
    c2 = _instant(case.get("c2_opened_at_utc"))
    c1 = _instant(case.get("c1_opened_at_utc"))
    entry = _instant(case.get("decision_at_utc"))
    if c1 + timedelta(minutes=30) != c2 or entry != c2 + timedelta(minutes=30):
        raise ValueError("VT08 B R3 C1-C2-C3 source clock inconsistency")
    local = c2.astimezone(NY)
    if not (1 <= local.hour < 13 and local.minute in (0, 30)):
        raise ValueError("VT08 B R3 C2 outside frozen Owner window")
    if case.get("ny_date") != local.date().isoformat():
        raise ValueError("VT08 B R3 source NY day mismatch")
    return c2, entry


def verify_a_r3_raw_bundle(
    package: Mapping[str, object], m3_file: Path, m15_file: Path
) -> dict[str, object]:
    """Validate physical source/every positive, never re-label PS as TTrades."""
    if package.get("schema") != SCHEMA:
        raise ValueError("VT08 B R3 source schema not frozen")
    market = package.get("market")
    if not isinstance(market, str):
        raise ValueError("VT08 B R3 market invalid")
    sha3, raw3 = _raw_bars(m3_file, "M3", market)
    sha15, raw15 = _raw_bars(m15_file, "M15", market)
    if (
        package.get("source_m3_sha256") != sha3
        or package.get("source_m15_sha256") != sha15
    ):
        raise ValueError("VT08 B R3 source SHA mismatch")
    observed = 0
    missing = 0
    cross = 0
    c2_geometry_rejected = 0
    geometry_pass = 0
    for opening in sorted(raw3):
        local = opening.astimezone(NY)
        if not (1 <= local.hour < 13 and local.minute in (0, 30)):
            continue
        observed += 1
        c1 = opening - timedelta(minutes=30)
        x3 = _window(raw3, c1, 3, 10)
        y3 = _window(raw3, opening, 3, 10)
        x15 = _window(raw15, c1, 15, 2)
        y15 = _window(raw15, opening, 15, 2)
        if any(a is None for a in (x3, y3, x15, y15)):
            missing += 1
            continue
        assert x3 is not None and y3 is not None
        assert x15 is not None and y15 is not None
        c1ohlc = _aggregate(x3)
        c2ohlc = _aggregate(y3)
        if c1ohlc != _aggregate(x15) or c2ohlc != _aggregate(y15):
            cross += 1
        elif not (
            c2ohlc[2] < c1ohlc[2]
            and c2ohlc[1] <= c1ohlc[1]
            and c1ohlc[2] < c2ohlc[3] < c1ohlc[1]
            and c2ohlc[3] > c2ohlc[0]
        ):
            c2_geometry_rejected += 1
        else:
            geometry_pass += 1
    counts = package.get("stage_counts")
    if not isinstance(counts, dict):
        raise ValueError("VT08 B R3 stage counts invalid")
    other = sum(
        int(counts.get(k, -1))
        for k in (
            "NO_M3_CISD_PS_SHAPE",
            "MULTIPLE_M3_CISD_PS_SHAPES_D",
            POSITIVE_STAGE,
        )
    )
    if (
        package.get("c2_windows_total") != observed
        or counts.get(MISSING) != missing
        or counts.get(CROSS) != cross
        or counts.get(C2_INVALID) != c2_geometry_rejected
        or other != geometry_pass
    ):
        raise ValueError("VT08 B R3 independent 93k C2 funnel contradiction")
    examples = package.get("examples_by_stage")
    if not isinstance(examples, dict):
        raise ValueError("VT08 B R3 missing evidence receipts")
    cases = examples.get(POSITIVE_STAGE)
    if not isinstance(cases, list) or len(cases) != counts.get(POSITIVE_STAGE):
        raise ValueError("VT08 B R3 missing any positive source precursor")
    valid_h1 = 0
    days: set[str] = set()
    days_h1: set[str] = set()
    for item in cases:
        if not isinstance(item, dict):
            raise ValueError("VT08 B R3 positive source row invalid")
        if (
            item.get("market") != market or item.get("family") != FAMILY
            or item.get("stage") != POSITIVE_STAGE
            or item.get("source_m3_file_sha256") != sha3
            or item.get("source_m15_file_sha256") != sha15
        ):
            raise ValueError("VT08 B R3 positive case lineage drift")
        for field in (
            "A_rule_complete", "B_signoff", "cognitive_ready",
            "broker_fill", "pnl_read", "reference_swing_author_relevance_validated",
        ):
            if item.get(field) is not False:
                raise ValueError("VT08 B R3 false source/trading authority")
        c2, entry = _source_times(item)
        days.add(str(item["ny_date"]))
        c1rows = item.get("c1_m3_raw_bar_receipts")
        c2rows = item.get("c2_m3_raw_bar_receipts")
        c2m15rows = item.get("c2_m15_raw_bar_receipts")
        h1rows = item.get("pre_c2_h1_m15_raw_bar_receipts")
        if (
            not isinstance(c1rows, list) or len(c1rows) != 10
            or not isinstance(c2rows, list) or len(c2rows) != 10
            or not isinstance(c2m15rows, list) or len(c2m15rows) != 2
            or not isinstance(h1rows, list) or len(h1rows) not in (0, 12)
        ):
            raise ValueError("VT08 B R3 missing positive bars")
        c1 = [
            _verify_bar(
                row, expected_open=c2 - timedelta(minutes=30-3*i),
                minutes=3, profile="M3", source_sha=sha3, raw=raw3,
            )
            for i, row in enumerate(c1rows)
        ]
        c2m3 = [
            _verify_bar(
                row, expected_open=c2 + timedelta(minutes=3*i),
                minutes=3, profile="M3", source_sha=sha3, raw=raw3,
            )
            for i, row in enumerate(c2rows)
        ]
        c2m15 = [
            _verify_bar(
                row, expected_open=c2 + timedelta(minutes=15*i),
                minutes=15, profile="M15", source_sha=sha15, raw=raw15,
            )
            for i, row in enumerate(c2m15rows)
        ]
        if _aggregate(c2m3) != _aggregate(c2m15):
            raise ValueError("VT08 B R3 M30 C2 crossfeed contradiction")
        a, b = _aggregate(c1), _aggregate(c2m3)
        if not (
            b[2] < a[2] and b[1] <= a[1]
            and a[2] < b[3] < a[1] and b[3] > b[0]
        ):
            raise ValueError("VT08 B R3 positive precursor is not bullish sweep")
        if item.get("pre_c2_h1_context_available") is not (len(h1rows) == 12):
            raise ValueError("VT08 B R3 H1 completeness claim inconsistent")
        if len(h1rows) == 12:
            cutoff_hour = c2.replace(minute=0, second=0, microsecond=0)
            begin = cutoff_hour - timedelta(hours=3)
            for i, row in enumerate(h1rows):
                opened = begin + timedelta(minutes=15*i)
                _verify_bar(
                    row, expected_open=opened, minutes=15,
                    profile="M15_PRE_C2_H1", source_sha=sha15, raw=raw15,
                )
                if opened + timedelta(minutes=15) > c2:
                    raise ValueError("VT08 B R3 H1 future bar ahead of C2 open")
            valid_h1 += 1
            days_h1.add(str(item["ny_date"]))
        details = item.get("details")
        if not isinstance(details, dict):
            raise ValueError("VT08 B R3 missing PS geometry metadata")
        if (
            details.get("m3_ps_proxy_count") != 1
            or details.get("proxy_not_author_validated") is not True
            or details.get("methodology_complete") is not False
        ):
            raise ValueError("VT08 B R3 PS proxy falsely promoted")
        if _instant(details.get("cisd_confirmed_at_utc")) > entry:
            raise ValueError("VT08 B R3 M3 CISD confirms after C3 entry")
        if _instant(details.get("opposing_series_opened_at_utc")) > entry:
            raise ValueError("VT08 B R3 opposing source after C3 entry")
    if (
        package.get("all_unique_proxy_cases_with_raw_receipts") != len(cases)
        or package.get("unique_ps_proxy_cases_with_three_closed_pre_c2_h1") != valid_h1
        or package.get("distinct_ny_days_with_h1_and_unique_ps_proxy") != len(days_h1)
        or package.get("earliest_unique_proxy_per_market_ny_day_upper_bound")
        != len(days)
    ):
        raise ValueError("VT08 B R3 counts/NY day cap conflict")
    for field in (
        "A_B_signed_manifest", "pnl_evaluated",
        "sealed_holdout_accessed", "sizing_applied",
    ):
        if package.get(field) is not False:
            raise ValueError("VT08 B R3 source package claims forbidden authority")
    for field in ("source_complete_entries", "real_cognitive_admissions", "fills"):
        if package.get(field) != 0:
            raise ValueError("VT08 B R3 manufactured author trades")
    return {
        "schema": "qore.vt08.b.r3.independent_source_reconciliation.v1",
        "market": market, "c2_windows_total": observed,
        "missing_raw_windows": missing, "m3_m15_m30_mismatches": cross,
        "rejected_bullish_c2_geometry": c2_geometry_rejected,
        "passes_c2_bullish_geometry": geometry_pass,
        "all_positive_proxy_receipts_reverified": len(cases),
        "pre_c2_h1_12bars_verified": valid_h1,
        "geometric_ny_days_upper_bound": len(days),
        "source_author_entries_certified": 0,
        "cognitive_real_admissions": 0,
        "economic_gates_evaluated": False,
        "holdout_accessed": False,
    }
