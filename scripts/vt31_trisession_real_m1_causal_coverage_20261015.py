#!/usr/bin/env python3
"""VT31: independent REAL NAS100 M1 coverage ledger for all 3 Silver Bullet windows.

Read-only M0/M1 investigation. Completeness of bars is NEVER authorial method,
MSS, protected swing, COG certification, an entry or authority to trade.
"""
from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import time
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from typing import Any

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    NEW_YORK,
    M1Bar,
    SessionId,
    window_bounds,
)
from scripts.vt31_m0_predecision_method_router_20261015 import PREDECLARED
from scripts.vt31_m0_temporal_admission_20261015 import admission_court
from scripts.vt31_ttrades_am_method_m1_census_20261014 import (
    M1_TOTAL,
    MARKET_SHA,
    hash_file,
    market_rows,
    parse_time,
    run_census,
)

VERSION = "VT31_TRISESION_M0_M1_REAL_SOURCE_COVERAGE_ONLY_V1"
PREREG_COMMIT = "a4352c9ad787111604d618f3fb10660de015230d"
SLOTS = (
    (SessionId.LONDON, 3),
    (SessionId.NY_AM, 10),
    (SessionId.NY_PM, 14),
)
HOURS = frozenset({3, 9, 10, 14})
CENSUS_BASELINE = {
    "MSS_ATTESTED_CONTEXT_ONLY": 128,
    "FIRST_RETURN_NO_QORE_MSS": 483,
    "SWEEP_NO_RETURN": 92,
    "NO_SWEEP": 65,
    "INCOMPLETE_M1_HOURS": 6,
    "REJECTED_SOURCE": 1,
}
COMPLETE = "CLOSED_M1_WINDOW_COMPLETE_CONTEXT_ONLY"
PARTIAL = "PARTIAL_M1_WINDOW_SOURCE_UNKNOWN"
EMPTY = "NO_M1_WINDOW_SOURCE_UNKNOWN"
H1_WAIT = "TTRADES_H1_09_SOURCE_INCOMPLETE_WAIT"
_LOADED: dict[str, dict[int, tuple[M1Bar, ...]]] | None = None


def collect_tri_hour_groups(
    rows: Any, *, expected_m1: int = M1_TOTAL,
) -> tuple[dict[str, dict[int, tuple[M1Bar, ...]]], int]:
    """One source scan, no M1 interpolation and no outcome conditioning."""
    buckets: dict[str, dict[int, list[M1Bar]]] = defaultdict(
        lambda: {hour: [] for hour in HOURS}
    )
    previous_opened: datetime | None = None
    total = 0
    for row in rows:
        opened, closed = parse_time(row["opened_at"]), parse_time(row["closed_at"])
        if (
            closed - opened != timedelta(minutes=1)
            or previous_opened is not None and opened <= previous_opened
        ):
            raise ValueError("TRISESION_M1_SOURCE_NONCAUSAL_OR_DUPLICATED")
        previous_opened = opened
        total += 1
        ny = opened.astimezone(NEW_YORK)
        if ny.hour in HOURS:
            b = M1Bar(
                opened, closed,
                Decimal(str(row["open"])),
                Decimal(str(row["high"])),
                Decimal(str(row["low"])),
                Decimal(str(row["close"])),
            )
            buckets[ny.date().isoformat()][ny.hour].append(b)
    if total != expected_m1:
        raise ValueError("TRISESION_ORIGINAL_M1_BAR_COUNT_CHANGED")
    return {
        day: {h: tuple(v) for h, v in hs.items()}
        for day, hs in buckets.items()
    }, total


def _complete_hour(
    *, day: str, hour: int, bars: tuple[M1Bar, ...],
) -> bool:
    """NY-civil 60-minute window, including EST/EDT transitions correctly."""
    daystamp = datetime.fromisoformat(day).replace(tzinfo=NEW_YORK)
    starts = daystamp.replace(hour=hour).astimezone(UTC)
    expected = tuple(starts + timedelta(minutes=i) for i in range(60))
    if len(bars) > 60:
        raise ValueError("TRISESION_MORE_THAN_60_M1_IN_LOCAL_HOUR")
    allowed = set(expected)
    for b in bars:
        if (
            not isinstance(b, M1Bar)
            or b.opened_at.astimezone(UTC) not in allowed
            or b.closed_at.astimezone(UTC) != b.opened_at.astimezone(UTC)
            + timedelta(minutes=1)
        ):
            raise ValueError("TRISESION_BAR_OUTSIDE_DECLARED_NY_HOUR")
    if len({b.opened_at for b in bars}) != len(bars):
        raise ValueError("TRISESION_DUPLICATE_M1_TIMESTAMP")
    return len(bars) == 60 and all(
        b.opened_at.astimezone(UTC) == instant
        for b, instant in zip(bars, expected, strict=True)
    )


def audit_session(
    *, day: str, session: SessionId,
    hours: dict[int, tuple[M1Bar, ...]],
) -> dict[str, Any]:
    """Do NOT call COG on historic context from this coverage ledger."""
    if not isinstance(session, SessionId):
        raise ValueError("UNTYPED_METHOD_SESSION")
    session_hours = dict(SLOTS)
    if session not in session_hours:
        raise ValueError("SESSION_NOT_IN_PREREGISTERED_SILVER_BULLET_WINDOWS")
    profile = PREDECLARED.profile_for(session)
    source_hour = session_hours[session]
    bars = hours.get(source_hour, ())
    daystamp = datetime.fromisoformat(day).replace(tzinfo=NEW_YORK)
    start, end = window_bounds(daystamp, session)
    if start != daystamp.replace(hour=source_hour).astimezone(UTC):
        raise AssertionError("SESSION_LOCAL_HOUR_OR_DST_MISMATCH")
    fully_closed = _complete_hour(day=day, hour=source_hour, bars=bars)
    h1_complete = None
    if session is SessionId.NY_AM:
        h1_complete = _complete_hour(day=day, hour=9, bars=hours.get(9, ()))
    count = len(bars)
    status = (
        H1_WAIT if h1_complete is False
        else COMPLETE if fully_closed
        else EMPTY if count == 0
        else PARTIAL
    )
    if session in (SessionId.LONDON, SessionId.NY_PM) and h1_complete is not None:
        raise AssertionError("TTRADES_H1_09_LEAKED_INTO_ICT_SESSION")
    return {
        "ny_day": day,
        "session": session.value,
        "preregistered_profile": profile,
        "utc_window_open": start.isoformat(),
        "utc_window_end": end.isoformat(),
        "observed_window_m1": count,
        "missing_window_m1": 60 - count,
        "h1_09_ttrades_required": session is SessionId.NY_AM,
        "h1_09_ttrades_complete": h1_complete,
        "state": status,
        "window_m1_complete": fully_closed,
        "methodology_certified": False,
        "cognition_certified": False,
        "trader_certified": False,
        "cog_runtime_integrated": False,
        "trading_or_sizing": 0,
    }


def audit_day(day: str) -> list[dict[str, Any]]:
    if _LOADED is None:
        raise ValueError("TRISESION_REAL_M1_NOT_PRELOADED")
    return [
        audit_session(day=day, session=session, hours=_LOADED[day])
        for session, _ in SLOTS
    ]


def _worker(days: list[str]) -> list[dict[str, Any]]:
    return [r for day in days for r in audit_day(day)]


def _digest(records: list[dict[str, Any]]) -> str:
    return sha256(json.dumps(
        records, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")).hexdigest()


def real_tri_session_audit(market: Path, *, parity: bool = True) -> dict[str, Any]:
    global _LOADED  # noqa: PLW0603
    if hash_file(market) != MARKET_SHA:
        raise ValueError("TRISESION_CANONICAL_MARKET_SHA_MISMATCH")
    load_started = time.monotonic()
    groups, n = collect_tri_hour_groups(market_rows(market))
    # Preserve the original 775-day NY AM cohort; never discard a date
    # merely because London/NY PM is missing on that date.
    ny_am_groups = {
        day: {9: hours[9], 10: hours[10]}
        for day, hours in groups.items()
        if hours[9] or hours[10]
    }
    if len(ny_am_groups) != 775:
        raise AssertionError("TRISESION_SOURCE_775_DAY_ANCHOR_CHANGED")
    frozen = run_census(ny_am_groups)
    if frozen["state_counts"] != CENSUS_BASELINE:
        raise AssertionError("TRISESION_PRIOR_NY_AM_CENSUS_CHANGED")
    days = sorted(ny_am_groups)
    _LOADED = groups
    loading_seconds = time.monotonic() - load_started

    started = time.monotonic()
    scalar = (
        sorted(_worker(days), key=lambda x: (x["ny_day"], x["session"]))
        if parity else None
    )
    scalar_seconds = time.monotonic() - started if parity else None

    started = time.monotonic()
    with mp.get_context("fork").Pool(processes=2) as pool:
        result = pool.map(_worker, [days[::2], days[1::2]])
    fast = sorted(
        (x for group in result for x in group),
        key=lambda x: (x["ny_day"], x["session"]),
    )
    fork_seconds = time.monotonic() - started
    if (
        len(fast) != 775 * 3 or
        (parity and (scalar is None or _digest(fast) != _digest(scalar)))
    ):
        raise AssertionError("TRISESION_SCALAR_FORK_FULL_CASEBOOK_DIVERGED")
    if len({(x["ny_day"], x["session"]) for x in fast}) != 775 * 3:
        raise AssertionError("TRISESION_MISSING_OR_DUPLICATED_DAY_SESSION")
    by_session: dict[str, dict[str, int]] = {}
    examples: dict[str, dict[str, str]] = {}
    for session, _ in SLOTS:
        its = [x for x in fast if x["session"] == session.value]
        if len(its) != 775:
            raise AssertionError("TRISESION_SESSION_DENOMINATOR_NOT_775")
        by_session[session.value] = dict(sorted(Counter(
            x["state"] for x in its
        ).items()))
        first: dict[str, str] = {}
        for row in its:
            first.setdefault(row["state"], row["ny_day"])
        examples[session.value] = first

    # Keep original G3 original COG synthetic court unchanged; its
    # source state is NOT inferred from the real M1 coverage census.
    court = admission_court()
    if len(court["cases"]) != 16:
        raise AssertionError("ORIGINAL_G3_PR978_16_RESEARCH_CASES_CHANGED")
    synthetic_states = Counter(x["research_source_state"] for x in court["cases"])
    expected_synthetic_states = {
        "RESEARCH_TTRADES_CONTEXT_CONFORMANT_NOT_CERTIFIED": 4,
        "G3_MIN10_AND_TTRADES_SOURCE_TARGET_CONFLICT_WAIT": 4,
        "ICT_CONTEXT_WITNESS_UNDERDETERMINED": 8,
    }
    if synthetic_states != expected_synthetic_states:
        raise AssertionError("ORIGINAL_G3_PR978_COG_COURT_REGRESSION")
    if any(
        x["methodology_certified"] or x["cognition_certified"]
        or x["trader_certified"] or x["trading_or_sizing"]
        for x in fast
    ):
        raise AssertionError("SOURCE_M1_COMPLETENESS_MUST_NOT_ISSUE_CERTIFICATES")
    return {
        "version": VERSION,
        "preregistered_commit": PREREG_COMMIT,
        "source_sha256": MARKET_SHA,
        "total_canonical_m1": n,
        "anchor_ny_am_days": 775,
        "evaluations": len(fast),
        "NY_AM_original_states_frozen": frozen["state_counts"],
        "three_session_source_coverage_states": by_session,
        "first_days_per_state": examples,
        "original_g3_synthetic_research_cases": len(court["cases"]),
        "original_g3_synthetic_states": dict(sorted(synthetic_states.items())),
        "casebook_json_sha256": _digest(fast),
        "scalar_fork_full_JSON_parity": parity,
        "all_2325_day_session_records": fast,
        "timings_wall_seconds_not_economics": {
            "stream_source_and_NYAM_census": round(loading_seconds, 6),
            "scalar": round(scalar_seconds, 6) if scalar_seconds else None,
            "fork_2process": round(fork_seconds, 6),
        },
        "context_coverage_only_not_ICT_TTRADES_doctrinal_certification": True,
        "qore_g3_producer_unchanged": True,
        "m0_profile_owner_signed": False,
        "m1_source_complete_does_not_mean_broker_open": True,
        "m2_ict_liquidity_doctrine_certified": False,
        "m3_displacement_author_certified": False,
        "m4_four_entry_families_certified": False,
        "m5_causative_swing_certified": False,
        "m6_two_human_signatures_verified": False,
        "m7_integrated_certification": False,
        "london_certified": False,
        "ny_am_certified": False,
        "ny_pm_certified": False,
        "methodology_certified": False,
        "cognition_certified": False,
        "trader_certified": False,
        "Pnl_PF_DD_Sortino": None,
        "live_demo_vps_broker_orders_fills_sizing": 0,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--market", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--parity", action="store_true")
    args = p.parse_args()
    result = real_tri_session_audit(args.market, parity=args.parity)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "evaluations": result["evaluations"],
        "session_states": result["three_session_source_coverage_states"],
        "full_casebook_sha256": result["casebook_json_sha256"],
        "scalar_fork_parity": result["scalar_fork_full_JSON_parity"],
        "certified": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
