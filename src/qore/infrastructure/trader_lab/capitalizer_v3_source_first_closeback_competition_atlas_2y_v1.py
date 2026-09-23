"""Outcome-free closeback competition atlas for SOURCE_FIRST No-Rearm.

Current V3 chooses only the chronologically first sweep/closeback candidate in
each H1 window. If that candidate later fails MSS/FVG/fill/No-Rearm/stop geometry,
other already-causal liquidity candidates inside the same H1 are never evaluated.

This atlas changes no trading rule. It enumerates the exact candidate set that
already exists at decision time and asks:
- how often an H1 has multiple closeback candidates;
- whether the current first candidate is ambiguous or structurally non-executable;
- whether a strictly later closeback candidate independently reaches
  SOURCE_FIRST MSS + causal M1 FVG + No-Rearm-valid normal fill + valid stop.

No lifecycle outcome, target/stop result, PnL, ranking by economics, or future
admission information is read.
"""

from __future__ import annotations

import argparse
import bisect
import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_owner_h1_m3_m1_causal_reversal_1y_v3 as v3,
)
from qore.infrastructure.trader_lab.capitalizer_v3_frozen_replay_2y_v1 import (
    LOOKBACK_START,
    WINDOW_END,
    WINDOW_START,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
    iter_cibo_m1,
)
from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerSession
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_full_ict_density_scanner_1y_v1 import (
    _aggregate_h1,
)
from qore.infrastructure.trader_lab.capitalizer_strict_htf_gate_1y_v1 import (
    Pivot,
    TFBar,
    _aggregate_tf,
    _index_day_inputs,
    _pivots,
)
from qore.infrastructure.trader_lab.capitalizer_v3_source_first_cisd_v1 import (
    find_source_first_m3_mss,
)

IDENTITY = "QORE_CAPITALIZER_V3_SOURCE_FIRST_CLOSEBACK_COMPETITION_ATLAS_2Y_V1"
MATRIX_IDENTITY = (
    "QORE_CAPITALIZER_NINE_MARKET_V3_SOURCE_FIRST_"
    "CLOSEBACK_COMPETITION_ATLAS_2Y_V1"
)
WAIT_MINUTES = 5


@dataclass(frozen=True, slots=True)
class ClosebackCompetitionRow:
    symbol: str
    session: str
    operating_date: str
    h1_open: str
    h1_deadline: str
    candidate_count: int
    current_first_ambiguous: bool
    current_first_stage: str
    current_first_closeback_at: str | None
    later_candidate_count: int
    later_executable_count: int
    earliest_later_executable_at: str | None
    earliest_later_executable_source: str | None
    earliest_later_executable_side: str | None
    recoverable_after_first_failure: bool
    outcome_fields_read: bool = False


def _enumerate_closebacks(
    hour_bars: tuple[CapitalizerM1Bar, ...],
    *,
    levels: tuple[v3.LiquidityLevel, ...],
    m5: tuple[TFBar, ...],
    m5_closes: tuple[datetime, ...],
    h1_open: datetime,
    h1_deadline: datetime,
) -> tuple[bool, tuple[v3.SweepCloseback, ...]]:
    sweep_seen = False
    candidates: list[v3.SweepCloseback] = []
    for level in levels:
        sweep_bar: CapitalizerM1Bar | None = None
        for bar in hour_bars:
            swept = (
                bar.high > level.price
                if level.kind == "HIGH"
                else bar.low < level.price
            )
            if swept:
                sweep_seen = True
                sweep_bar = bar
                break
        if sweep_bar is None:
            continue

        start = bisect.bisect_right(m5_closes, sweep_bar.opened_at)
        end = bisect.bisect_right(m5_closes, h1_deadline)
        for m5_bar in m5[start:end]:
            closed_back = (
                m5_bar.source.close < level.price
                if level.kind == "HIGH"
                else m5_bar.source.close > level.price
            )
            if not closed_back:
                continue
            side = (
                CapitalizerSide.SHORT
                if level.kind == "HIGH"
                else CapitalizerSide.LONG
            )
            candidates.append(
                v3.SweepCloseback(
                    side=side,
                    reference=level,
                    sweep_at=sweep_bar.opened_at,
                    sweep_extreme=(
                        sweep_bar.high if level.kind == "HIGH" else sweep_bar.low
                    ),
                    closeback_at=m5_bar.closed_at,
                    h1_open=h1_open,
                    h1_deadline=h1_deadline,
                )
            )
            break

    ordered = tuple(
        sorted(
            candidates,
            key=lambda item: (
                item.closeback_at,
                item.sweep_at,
                item.reference.source,
                item.reference.price,
            ),
        )
    )
    return sweep_seen, ordered


def _current_first(
    candidates: tuple[v3.SweepCloseback, ...],
) -> tuple[v3.SweepCloseback | None, bool]:
    if not candidates:
        return None, False
    first = candidates[0]
    ambiguous = any(
        item.closeback_at == first.closeback_at
        and item.side is not first.side
        for item in candidates[1:]
    )
    return (None if ambiguous else first), ambiguous


def _stage(
    closeback: v3.SweepCloseback,
    *,
    execution: tuple[CapitalizerM1Bar, ...],
    m3: tuple[TFBar, ...],
    m3_closes: tuple[datetime, ...],
    m3_pivots: tuple[Pivot, ...],
    buffer_price: Decimal,
) -> tuple[str, datetime | None]:
    mss = find_source_first_m3_mss(
        m3,
        m3_closes,
        m3_pivots,
        sweep_at=closeback.sweep_at,
        after=closeback.closeback_at,
        before=closeback.h1_deadline,
        side=closeback.side,
    )
    if mss is None:
        return "M3_MSS_MISSING", None

    zone = v3._m1_causal_zone(execution, event=mss)
    if zone is None:
        return "M1_CAUSAL_FVG_MISSING", None

    normal_fill = v3._find_m1_fill(
        execution,
        event=mss,
        zone=zone,
        deadline=closeback.h1_deadline,
    )
    if normal_fill is None:
        return "M1_FILL_MISSING", None

    entry_index, entry_price, _ = normal_fill
    entry_at = execution[entry_index].opened_at
    has_overlap = zone.overlap_low is not None and zone.overlap_high is not None
    eligible_at = mss.confirmed_at + timedelta(minutes=WAIT_MINUTES)
    if not has_overlap and entry_at < eligible_at:
        return "NO_REARM_ABSTAIN", None

    stop_price = (
        mss.broken_swing_price - buffer_price
        if closeback.side.value == "LONG"
        else mss.broken_swing_price + buffer_price
    )
    valid_stop = (
        stop_price < entry_price
        if closeback.side.value == "LONG"
        else stop_price > entry_price
    )
    if not valid_stop:
        return "STOP_INVALID_GEOMETRY", None
    return "EXECUTABLE_NO_REARM", entry_at


def build_market_report(
    m1_root: Path,
    *,
    session: CapitalizerSession,
) -> tuple[dict[str, Any], tuple[ClosebackCompetitionRow, ...]]:
    all_bars = tuple(
        bar
        for bar in iter_cibo_m1(m1_root)
        if LOOKBACK_START
        <= bar.opened_at
        < WINDOW_END + timedelta(days=1)
    )
    if not all_bars:
        raise ValueError("closeback competition atlas found no native M1")
    symbol = all_bars[0].symbol
    if any(bar.symbol != symbol for bar in all_bars):
        raise ValueError("closeback competition atlas requires one market")

    h1 = _aggregate_h1(all_bars)
    h1_swings = v3._build_h1_swings(h1)
    m5 = _aggregate_tf(all_bars, minutes=5)
    m5_closes = tuple(item.closed_at for item in m5)
    m3 = _aggregate_tf(all_bars, minutes=3)
    m3_closes = tuple(item.closed_at for item in m3)
    m3_pivots = _pivots(m3)
    buffer_price = v3._stop_buffer(all_bars)
    execution_by_day, reference_by_day = _index_day_inputs(
        all_bars,
        session=session,
    )

    rows: list[ClosebackCompetitionRow] = []
    selected_stage_counts: Counter[str] = Counter()
    alternative_source_counts: Counter[str] = Counter()
    current_control_mismatches = 0

    dates = sorted(
        key
        for key in execution_by_day
        if WINDOW_START.date().isoformat()
        <= key
        < WINDOW_END.date().isoformat()
    )
    for value in dates:
        operating_day = date.fromisoformat(value)
        execution = execution_by_day.get(value, ())
        if len(execution) < 15:
            continue
        prior_session = reference_by_day.get(value)
        previous_day = v3._previous_day_range(
            all_bars,
            operating_day=operating_day,
        )

        for h1_open, h1_deadline, hour_bars in v3._h1_windows(execution):
            levels = v3._liquidity_levels(
                prior_session=prior_session,
                previous_day=previous_day,
                h1_swings=h1_swings,
                hour_open=h1_open,
            )
            if not levels:
                continue

            sweep_seen, candidates = _enumerate_closebacks(
                hour_bars,
                levels=levels,
                m5=m5,
                m5_closes=m5_closes,
                h1_open=h1_open,
                h1_deadline=h1_deadline,
            )
            frozen_sweep, frozen_first = v3._find_sweep_closeback(
                hour_bars,
                levels=levels,
                m5=m5,
                m5_closes=m5_closes,
                h1_open=h1_open,
                h1_deadline=h1_deadline,
            )
            selected, ambiguous = _current_first(candidates)
            if frozen_sweep != sweep_seen:
                current_control_mismatches += 1
            if (frozen_first is None) != (selected is None):
                current_control_mismatches += 1
            elif frozen_first is not None and selected is not None:
                if (
                    frozen_first.closeback_at != selected.closeback_at
                    or frozen_first.side is not selected.side
                    or frozen_first.reference.price != selected.reference.price
                ):
                    current_control_mismatches += 1

            if not candidates:
                continue

            if selected is None:
                first_stage = "AMBIGUOUS_FIRST_CLOSEBACK"
                first_time = candidates[0].closeback_at
            else:
                first_stage, _ = _stage(
                    selected,
                    execution=execution,
                    m3=m3,
                    m3_closes=m3_closes,
                    m3_pivots=m3_pivots,
                    buffer_price=buffer_price,
                )
                first_time = selected.closeback_at
            selected_stage_counts[first_stage] += 1

            later = tuple(
                item for item in candidates if item.closeback_at > first_time
            )
            executable_later: list[tuple[v3.SweepCloseback, datetime]] = []
            for item in later:
                stage, entry_at = _stage(
                    item,
                    execution=execution,
                    m3=m3,
                    m3_closes=m3_closes,
                    m3_pivots=m3_pivots,
                    buffer_price=buffer_price,
                )
                if stage == "EXECUTABLE_NO_REARM" and entry_at is not None:
                    executable_later.append((item, entry_at))

            earliest: tuple[v3.SweepCloseback, datetime] | None = None
            if executable_later:
                earliest = min(
                    executable_later,
                    key=lambda pair: (pair[1], pair[0].closeback_at),
                )
                alternative_source_counts[earliest[0].reference.source] += 1

            recoverable = (
                first_stage != "EXECUTABLE_NO_REARM"
                and earliest is not None
            )
            rows.append(
                ClosebackCompetitionRow(
                    symbol=symbol,
                    session=session.value,
                    operating_date=value,
                    h1_open=h1_open.isoformat(),
                    h1_deadline=h1_deadline.isoformat(),
                    candidate_count=len(candidates),
                    current_first_ambiguous=ambiguous,
                    current_first_stage=first_stage,
                    current_first_closeback_at=(
                        None if selected is None else selected.closeback_at.isoformat()
                    ),
                    later_candidate_count=len(later),
                    later_executable_count=len(executable_later),
                    earliest_later_executable_at=(
                        None if earliest is None else earliest[1].isoformat()
                    ),
                    earliest_later_executable_source=(
                        None if earliest is None else earliest[0].reference.source
                    ),
                    earliest_later_executable_side=(
                        None if earliest is None else earliest[0].side.value
                    ),
                    recoverable_after_first_failure=recoverable,
                )
            )

    ordered = tuple(
        sorted(
            rows,
            key=lambda item: (item.h1_open, item.symbol),
        )
    )
    return {
        "identity": IDENTITY,
        "symbol": symbol,
        "session": session.value,
        "h1_with_closeback_candidates": len(ordered),
        "h1_with_multiple_candidates": sum(item.candidate_count > 1 for item in ordered),
        "h1_with_later_candidates": sum(item.later_candidate_count > 0 for item in ordered),
        "h1_with_later_executable": sum(item.later_executable_count > 0 for item in ordered),
        "recoverable_after_first_failure": sum(
            item.recoverable_after_first_failure for item in ordered
        ),
        "ambiguous_first_closeback": sum(
            item.current_first_ambiguous for item in ordered
        ),
        "current_first_stage_counts": dict(sorted(selected_stage_counts.items())),
        "earliest_alternative_source_counts": dict(
            sorted(alternative_source_counts.items())
        ),
        "current_selection_control_mismatches": current_control_mismatches,
        "same_liquidity_universe": True,
        "same_h1_deadline": True,
        "same_source_first_mss": True,
        "same_m1_fvg": True,
        "same_no_rearm_architecture": True,
        "same_stop_geometry": True,
        "outcome_fields_read": False,
        "outcome_used_for_admission": False,
        "strategy_mutated": False,
        "diagnostic_only": True,
        "economic_candidate": False,
        "rule_promotion_allowed": False,
        "fresh_holdout_claimed": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }, ordered


def write_market(
    report: dict[str, Any],
    rows: tuple[ClosebackCompetitionRow, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    stem = (
        f"capitalizer-{symbol}-v3-source-first-"
        "closeback-competition-atlas-2y-v1"
    )
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-rows.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def _load_reports(root: Path) -> list[dict[str, Any]]:
    paths = sorted(
        root.rglob(
            "capitalizer-*-v3-source-first-closeback-competition-atlas-2y-v1.json"
        )
    )
    if len(paths) != 9:
        raise ValueError(
            f"closeback competition matrix requires 9 reports, got {len(paths)}"
        )
    return [dict(json.loads(path.read_text(encoding="utf-8"))) for path in paths]


def build_matrix(root: Path) -> dict[str, Any]:
    reports = _load_reports(root)
    stage_counts: Counter[str] = Counter()
    source_counts: Counter[str] = Counter()
    for report in reports:
        for key, value in dict(report["current_first_stage_counts"]).items():
            stage_counts[str(key)] += int(value)
        for key, value in dict(report["earliest_alternative_source_counts"]).items():
            source_counts[str(key)] += int(value)

    return {
        "identity": MATRIX_IDENTITY,
        "market_count": 9,
        "h1_with_closeback_candidates": sum(
            int(item["h1_with_closeback_candidates"]) for item in reports
        ),
        "h1_with_multiple_candidates": sum(
            int(item["h1_with_multiple_candidates"]) for item in reports
        ),
        "h1_with_later_candidates": sum(
            int(item["h1_with_later_candidates"]) for item in reports
        ),
        "h1_with_later_executable": sum(
            int(item["h1_with_later_executable"]) for item in reports
        ),
        "recoverable_after_first_failure": sum(
            int(item["recoverable_after_first_failure"]) for item in reports
        ),
        "ambiguous_first_closeback": sum(
            int(item["ambiguous_first_closeback"]) for item in reports
        ),
        "current_first_stage_counts": dict(sorted(stage_counts.items())),
        "earliest_alternative_source_counts": dict(sorted(source_counts.items())),
        "current_selection_control_mismatches": sum(
            int(item["current_selection_control_mismatches"]) for item in reports
        ),
        "markets": sorted(reports, key=lambda item: str(item["symbol"])),
        "same_liquidity_universe": True,
        "same_h1_deadline": True,
        "same_source_first_mss": True,
        "same_m1_fvg": True,
        "same_no_rearm_architecture": True,
        "same_stop_geometry": True,
        "outcome_fields_read": False,
        "outcome_used_for_admission": False,
        "strategy_mutated": False,
        "diagnostic_only": True,
        "economic_candidate": False,
        "rule_promotion_allowed": False,
        "fresh_holdout_claimed": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }


def write_matrix(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / (
        "capitalizer-nine-market-v3-source-first-"
        "closeback-competition-atlas-2y-v1.json"
    )
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    market = sub.add_parser("market")
    market.add_argument("m1_root", type=Path)
    market.add_argument("output", type=Path)
    market.add_argument(
        "--session",
        required=True,
        choices=[item.value for item in CapitalizerSession],
    )

    matrix = sub.add_parser("matrix")
    matrix.add_argument("input_root", type=Path)
    matrix.add_argument("output", type=Path)

    args = parser.parse_args()
    if args.command == "market":
        report, rows = build_market_report(
            args.m1_root,
            session=CapitalizerSession(args.session),
        )
        write_market(report, rows, args.output)
        print(json.dumps(report, sort_keys=True))
        return

    report = build_matrix(args.input_root)
    write_matrix(report, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
