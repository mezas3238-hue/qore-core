#!/usr/bin/env python3
"""VT31 M3 source swing STRUCTURAL CLOSE after FIRST OPEN CISD.

TTrades: MSS requires displacement AND close beyond a swing. A close beyond
a pre-confirmed short-term swing is ONLY ONE COMPONENT and NEVER proves
authorial displacement, OB, trade intent, fill, stop or sizing.
"""
from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import time
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from zoneinfo import ZoneInfo

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import M1Bar, Side
from scripts.vt31_m3_cisd_first_series_source_witness_20261015 import (
    EXPECTED,
    audit_real_day,
)
from scripts.vt31_m3_source_first_cisd_cognition_v3_20261015 import (
    TTradesAmSourceFirstCognitionV3,
)
from scripts.vt31_m4_m5_author_semantics_bridge_20261015 import (
    short_term_swings,
)
from scripts.vt31_ttrades_am_method_m1_census_20261014 import (
    M1_TOTAL,
    MARKET_SHA,
    collect_hours,
    hash_file,
    market_rows,
    run_census,
)

PREREG = "24a5226eb52d96f612db2e524a2a6ed4a9baa212"
NY = ZoneInfo("America/New_York")
SCHEMA = "VT31_M3_V4_CISD_THEN_SOURCE_SWING_CLOSE_RESEARCH_NOT_MSS"
ACTIVE_V3 = frozenset({
    "AUTHOR_FIRST_OPEN_CISD_COMPONENT_MSS_UNVERIFIED",
})
_GROUPS: dict | None = None


@dataclass(frozen=True, slots=True)
class SwingCloseComponent:
    state: str
    as_of: datetime
    eligible_swings: int
    crossed_swings: int
    reference_pivot_confirmed_at: datetime | None = None


def structural_close_component(
    closed_ten: tuple[M1Bar, ...],
    *,
    side: Side,
    first_return_at: datetime,
    as_of: datetime,
) -> SwingCloseComponent:
    """Single pre-confirmed swing and fresh CLOSE-through, not displacement.

    Selection of *short-term* level versus a protected intermediate-term
    swing is a QORE research restriction, not a universal TTrades MSS rule.
    """
    if (
        first_return_at.tzinfo is None
        or first_return_at.utcoffset() is None
        or as_of.tzinfo is None
        or as_of.utcoffset() is None
    ):
        raise ValueError("MSS_SOURCE_CLOCK_MUST_BE_AWARE")
    if not closed_ten or closed_ten[-1].closed_at != as_of:
        raise ValueError("NO_CLOSED_M1_AT_MSS_ASOF")
    for bar in closed_ten:
        if (
            bar.opened_at.tzinfo is None
            or bar.closed_at.tzinfo is None
            or bar.opened_at.utcoffset() is None
            or bar.closed_at.utcoffset() is None
            or bar.closed_at-bar.opened_at != timedelta(minutes=1)
        ):
            raise ValueError("MSS_REQUIRES_CLOSED_ONE_MINUTE_BAR")
    if any(
        a.closed_at != b.opened_at
        for a, b in zip(closed_ten, closed_ten[1:], strict=False)
    ):
        raise ValueError("MSS_HISTORICAL_SOURCE_GAPPED_OR_OVERLAPPED")
    if len(closed_ten) < 4 or as_of <= first_return_at:
        return SwingCloseComponent("WAIT_FOR_CONFIRMED_SWING", as_of, 0, 0)
    previous, current = closed_ten[-2:]
    expected_kind = "HIGH" if side is Side.LONG else "LOW"
    source = short_term_swings(closed_ten)
    eligible = tuple(
        s for s in source
        if s.kind == expected_kind
        and s.pivot_closed_at >= first_return_at
        and s.confirmed_at < as_of
    )
    crossed = tuple(
        s for s in eligible
        if (
            previous.close <= s.extremum < current.close
            if side is Side.LONG
            else previous.close >= s.extremum > current.close
        )
    )
    if crossed and len(eligible) > 1:
        return SwingCloseComponent(
            "MULTIPLE_SWINGS_MSS_REFERENCE_UNKNOWN",
            as_of, len(eligible), len(crossed),
        )
    if len(crossed) == 1 and len(eligible) == 1:
        return SwingCloseComponent(
            "SOURCE_SWING_CLOSE_COMPONENT_DISPLACEMENT_UNVERIFIED",
            as_of, len(eligible), 1,
            crossed[0].confirmed_at,
        )
    return SwingCloseComponent(
        "WAIT_FOR_NEW_STRUCTURAL_CLOSE",
        as_of, len(eligible), len(crossed),
    )


@dataclass(frozen=True, slots=True)
class COGV4Snapshot:
    state: str
    as_of: datetime
    v3_state: str
    first_source_cisd_at: datetime | None
    first_structural_close_component_at: datetime | None
    first_ambiguous_multi_swing_at: datetime | None
    candidate_pivot_confirmed_at: datetime | None
    first_return_at: datetime | None
    source_bias: str | None
    profile: str = "TTRADES_NY_AM_2025"
    displacement_author_certified: bool = False
    mss_author_certified: bool = False
    method_certified: bool = False
    cognition_certified: bool = False
    trader_certified: bool = False
    orders_fills_sizing: int = 0


class TTradesSourceSwingCOGV4:
    """Read-only V3 composition; no producer/OPS mutation."""

    def __init__(self) -> None:
        self._v3 = TTradesAmSourceFirstCognitionV3()
        self._ten: list[M1Bar] = []
        self._first_break: datetime | None = None
        self._first_pivot_confirm: datetime | None = None
        self._first_ambiguous: datetime | None = None
        self._snapshot: COGV4Snapshot | None = None

    def observe_closed_m1(self, bar: M1Bar) -> COGV4Snapshot:
        source = self._v3.observe_closed_m1(bar)
        hour = bar.opened_at.astimezone(NY).hour
        if hour == 9:
            state = "WAIT_FOR_09H_CONTEXT"
        else:
            self._ten.append(bar)
            if source.state == "INVALIDATED_OPPOSITE_RAID":
                state = "INVALIDATED_OPPOSITE_RAID"
            elif source.state == "TARGET_CONSUMED_NO_FRESH_INTENT":
                state = "TARGET_CONSUMED_NO_FRESH_INTENT"
            elif source.state == "EXPIRED_11_NY":
                state = "EXPIRED_11_NY"
            elif source.state in ("UNKNOWN_SOURCE_GAP", "UNKNOWN_ORIGINAL_SOURCE_WITNESS"):
                state = "UNKNOWN_MSS_SOURCE"
            elif source.state not in ACTIVE_V3 or source.first_author_cisd_at is None:
                state = "WAIT_FOR_AUTHOR_FIRST_OPEN_CISD"
            elif source.first_return_at is None or source.bias not in ("LONG", "SHORT"):
                state = "UNKNOWN_MSS_SOURCE_IDENTITY"
            else:
                try:
                    witness = structural_close_component(
                        tuple(self._ten),
                        side=Side(source.bias),
                        first_return_at=source.first_return_at,
                        as_of=source.as_of,
                    )
                except ValueError as exc:
                    if str(exc) not in (
                        "MSS_HISTORICAL_SOURCE_GAPPED_OR_OVERLAPPED",
                        "MSS_REQUIRES_CLOSED_ONE_MINUTE_BAR",
                    ):
                        raise
                    state = "UNKNOWN_MSS_SOURCE"
                else:
                    if (
                        witness.state
                        == "SOURCE_SWING_CLOSE_COMPONENT_DISPLACEMENT_UNVERIFIED"
                        and self._first_break is None
                    ):
                        self._first_break = source.as_of
                        self._first_pivot_confirm = witness.reference_pivot_confirmed_at
                    if (
                        witness.state == "MULTIPLE_SWINGS_MSS_REFERENCE_UNKNOWN"
                        and self._first_ambiguous is None
                    ):
                        self._first_ambiguous = source.as_of
                    if self._first_break is not None:
                        state = "SOURCE_SWING_CLOSE_COMPONENT_DISPLACEMENT_UNVERIFIED"
                    elif self._first_ambiguous is not None:
                        state = "MULTIPLE_SWINGS_MSS_REFERENCE_UNKNOWN"
                    else:
                        state = "WAIT_FOR_CONFIRMED_STRUCTURAL_CLOSE"
        self._snapshot = COGV4Snapshot(
            state=state,
            as_of=source.as_of,
            v3_state=source.state,
            first_source_cisd_at=source.first_author_cisd_at,
            first_structural_close_component_at=self._first_break,
            first_ambiguous_multi_swing_at=self._first_ambiguous,
            candidate_pivot_confirmed_at=self._first_pivot_confirm,
            first_return_at=source.first_return_at,
            source_bias=source.bias,
        )
        return self._snapshot

    def snapshot(self) -> COGV4Snapshot:
        if self._snapshot is None:
            raise ValueError("COG_V4_NEEDS_A_CLOSED_M1")
        return self._snapshot


def audit_day(
    *, day: str, nine: tuple[M1Bar, ...], ten: tuple[M1Bar, ...],
    return_at: datetime,
) -> dict[str, object]:
    engine = TTradesSourceSwingCOGV4()
    for bar in nine:
        engine.observe_closed_m1(bar)
    for bar in ten:
        engine.observe_closed_m1(bar)
    final = engine.snapshot()
    # Independent previously source-verified CISD oracle; per-day consistency
    # is necessary for the new MSS-component witness.
    oracle = audit_real_day(
        day=day, nine=nine, ten=ten, first_return_at=return_at,
    )
    author_iso = (
        final.first_source_cisd_at.isoformat()
        if final.first_source_cisd_at is not None else None
    )
    if author_iso != oracle["author_first_series_close_at"]:
        raise AssertionError("COG_V4_FIRST_OPEN_SOURCE_CISD_PARITY_BROKEN")
    if final.first_structural_close_component_at is not None:
        kind = "SINGLE_CONFIRMED_SWING_CLOSE_COMPONENT_ONLY"
    elif final.first_ambiguous_multi_swing_at is not None:
        kind = "MULTIPLE_MSS_SWING_REFERENCE_UNKNOWN"
    else:
        kind = "NO_ATTESTED_STRUCTURAL_CLOSE_COMPONENT"
    return {
        "day": day,
        "first_return_at": return_at.astimezone(UTC).isoformat(),
        "source_CISD_first_open_at": author_iso,
        "first_single_swing_structural_close_at": (
            final.first_structural_close_component_at.isoformat()
            if final.first_structural_close_component_at is not None else None
        ),
        "first_ambiguous_multi_swing_at": (
            final.first_ambiguous_multi_swing_at.isoformat()
            if final.first_ambiguous_multi_swing_at is not None else None
        ),
        "candidate_swing_was_confirmed_at": (
            final.candidate_pivot_confirmed_at.isoformat()
            if final.candidate_pivot_confirmed_at is not None else None
        ),
        "m3_component_classification": kind,
        "v4_final_cognitive_state": final.state,
        "v3_final_cognitive_state": final.v3_state,
        "author_MSS_displacement_certified": False,
        "author_MSS_swing_hierarchy_certified": False,
        "cognition_runtime_certified": False,
        "trader_certified": False,
        "trades_sizing_fills": 0,
    }


def _worker(items: list[tuple[str, datetime]]) -> list[dict[str, object]]:
    if _GROUPS is None:
        raise ValueError("ULTRAFAST_SOURCE_NOT_PRELOADED")
    return [
        audit_day(day=day, nine=_GROUPS[day][9], ten=_GROUPS[day][10],
                  return_at=at)
        for day, at in items
    ]


def _sha(records: list[dict[str, object]]) -> str:
    return sha256(json.dumps(
        records, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")).hexdigest()


def audit_real_source(market: Path, *, parity: bool = True) -> dict[str, object]:
    global _GROUPS  # noqa: PLW0603
    if hash_file(market) != MARKET_SHA:
        raise ValueError("ORIGINAL_NAS100_M1_SHA_MISMATCH")
    start = time.monotonic()
    groups, total = collect_hours(market_rows(market))
    if total != M1_TOTAL:
        raise AssertionError("ORIGINAL_SOURCE_M1_TOTAL_DRIFT")
    census = run_census(groups)
    if census["observed_days_total"] != 775 or census["state_counts"] != EXPECTED:
        raise AssertionError("FROZEN_COG_SOURCE_CENSUS_CHANGED")
    rows = [
        (row["ny_day"], datetime.fromisoformat(row["as_of"]).astimezone(UTC))
        for row in census["source_classifications"]
        if row["classification"] == "FIRST_RETURN_NO_QORE_MSS"
    ]
    if len(rows) != 483 or len({day for day, _at in rows}) != 483:
        raise AssertionError("FROZEN_SOURCE_FIRST_RETURN_483_CHANGED")
    _GROUPS = groups
    load_time = time.monotonic() - start
    scalar_time = None
    scalar = None
    if parity:
        start = time.monotonic()
        scalar = sorted(_worker(rows), key=lambda x: x["day"])
        scalar_time = time.monotonic() - start
    start = time.monotonic()
    with mp.get_context("fork").Pool(processes=2) as pool:
        partitions = pool.map(_worker, [rows[::2], rows[1::2]])
    fast = sorted([x for group in partitions for x in group], key=lambda x: x["day"])
    fast_time = time.monotonic() - start
    if len(fast) != 483 or (parity and (scalar is None or _sha(scalar) != _sha(fast))):
        raise AssertionError("ULTRAFAST_V4_SCALAR_FULL_SOURCE_PARITY_FAILED")
    states = Counter(x["m3_component_classification"] for x in fast)
    endings = Counter(x["v4_final_cognitive_state"] for x in fast)
    if sum(states.values()) != 483:
        raise AssertionError("V4_SOURCE_COMPONENT_PARTITION_DRIFT")
    if endings != {"EXPIRED_11_NY": 435, "INVALIDATED_OPPOSITE_RAID": 48}:
        raise AssertionError("V3_SESSION_END_INVALIDATION_COG_PARITY_FAILED")
    if any(x["trader_certified"] or x["trades_sizing_fills"] for x in fast):
        raise AssertionError("V4_SOURCE_WITNESS_EMITTED_UNAUTHORIZED_TRADE")
    return {
        "schema": SCHEMA,
        "pre_code_prereg_sha": PREREG,
        "original_market_sha256": MARKET_SHA,
        "original_market_M1_total": total,
        "frozen_days": 775,
        "frozen_contexts": len(fast),
        "CISD_source_reference": "FIRST_OPEN_OF_OPPOSING_SERIES_PR968",
        "author_MSS_requires_displacement_plus_close": True,
        "short_term_3bar_swings_source_defined": True,
        "choice_of_MSS_swing_hierarchy_is_QORE_formalization": True,
        "scalar_ultrafast_full_casebook_sha_parity": parity,
        "full_casebook_sha256": _sha(fast),
        "m3_swing_close_source_components_not_trades": dict(sorted(states.items())),
        "end_of_session_cognition": dict(sorted(endings.items())),
        "all_483_per_case_cognitive_evidence": fast,
        "timings_wall_seconds_not_economic": {
            "market_read_and_census": round(load_time, 6),
            "scalar_gates": round(scalar_time, 6) if scalar_time is not None else None,
            "ultrafast_two_fork": round(fast_time, 6),
        },
        "source_market_dev_not_OOS": True,
        "method_M3_author_full_certified": False,
        "cognition_integrated_certified": False,
        "M4_entry_author_certified": False,
        "M5_causative_swing_certified": False,
        "M6_dual_signers_verified": False,
        "trader_certified": False,
        "broker_orders_ack_fills": 0,
        "vt31_sizing": False,
        "live_authorized": False,
    }


def main() -> None:
    args = argparse.ArgumentParser()
    args.add_argument("--market", type=Path, required=True)
    args.add_argument("--out", type=Path, required=True)
    args.add_argument("--parity", action="store_true")
    opt = args.parse_args()
    report = audit_real_source(opt.market, parity=opt.parity)
    opt.out.parent.mkdir(parents=True, exist_ok=True)
    opt.out.write_text(json.dumps(report, indent=2, sort_keys=True)+"\n")
    print(json.dumps({
        "real_cases": report["frozen_contexts"],
        "component_states": report["m3_swing_close_source_components_not_trades"],
        "end_states": report["end_of_session_cognition"],
        "full_casebook_sha256": report["full_casebook_sha256"],
        "scalar_fork_parity": report["scalar_ultrafast_full_casebook_sha_parity"],
        "timings": report["timings_wall_seconds_not_economic"],
        "trader_certified": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
