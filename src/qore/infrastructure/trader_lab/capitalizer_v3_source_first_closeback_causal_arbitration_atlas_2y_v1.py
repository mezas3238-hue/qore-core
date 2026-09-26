"""Outcome-free causal arbitration atlas for competing H1 closebacks.

V1 proved that multiple liquidity closebacks frequently coexist inside one H1,
but "recover after first failure" can be non-causal when the first failure is
only knowable at the H1 deadline.

This V2 freezes a stricter causal policy:
- enumerate all already-causal liquidity closebacks in the H1;
- preserve fail-closed handling for candidates tied at the earliest closeback
  timestamp with opposite sides;
- those tied ambiguous candidates are ineligible;
- all strictly later independent closebacks remain trackable;
- for each eligible candidate, apply the exact frozen SOURCE_FIRST + No-Rearm
  structural rules;
- the first candidate to become executable by entry timestamp wins the H1;
- no lifecycle outcome, PnL, stop/target result, or future failure state is used.

This is diagnostic only. It does not promote or mutate the trader.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_owner_h1_m3_m1_causal_reversal_1y_v3 as v3,
)
from qore.infrastructure.trader_lab import (
    capitalizer_v3_source_first_closeback_competition_atlas_2y_v1 as v1,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import iter_cibo_m1
from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerSession
from qore.infrastructure.trader_lab.capitalizer_full_ict_density_scanner_1y_v1 import (
    _aggregate_h1,
)
from qore.infrastructure.trader_lab.capitalizer_strict_htf_gate_1y_v1 import (
    _aggregate_tf,
    _index_day_inputs,
    _pivots,
)
from qore.infrastructure.trader_lab.capitalizer_v3_frozen_replay_2y_v1 import (
    LOOKBACK_START,
    WINDOW_END,
    WINDOW_START,
)

IDENTITY = (
    "QORE_CAPITALIZER_V3_SOURCE_FIRST_CLOSEBACK_CAUSAL_ARBITRATION_ATLAS_2Y_V1"
)
MATRIX_IDENTITY = (
    "QORE_CAPITALIZER_NINE_MARKET_V3_SOURCE_FIRST_"
    "CLOSEBACK_CAUSAL_ARBITRATION_ATLAS_2Y_V1"
)


@dataclass(frozen=True, slots=True)
class CausalArbitrationRow:
    symbol: str
    session: str
    operating_date: str
    h1_open: str
    h1_deadline: str
    candidate_count: int
    earliest_closeback_ambiguous: bool
    eligible_candidate_count: int
    current_first_stage: str
    current_first_entry_at: str | None
    causal_winner_exists: bool
    causal_winner_entry_at: str | None
    causal_winner_closeback_at: str | None
    causal_winner_source: str | None
    causal_winner_side: str | None
    causal_winner_is_current_first: bool
    relation_vs_current: str
    outcome_fields_read: bool = False


def _eligible_after_ambiguity(
    candidates: tuple[v3.SweepCloseback, ...],
) -> tuple[tuple[v3.SweepCloseback, ...], bool]:
    if not candidates:
        return (), False
    first_at = candidates[0].closeback_at
    tied = tuple(item for item in candidates if item.closeback_at == first_at)
    ambiguous = len({item.side for item in tied}) > 1
    if not ambiguous:
        return candidates, False
    return tuple(item for item in candidates if item.closeback_at > first_at), True


def _relation(
    *,
    current_selected: v3.SweepCloseback | None,
    current_stage: str,
    current_entry: datetime | None,
    winner: tuple[v3.SweepCloseback, datetime] | None,
) -> str:
    if winner is None:
        return "NO_EXECUTABLE_CANDIDATE"
    if current_selected is None or current_stage != "EXECUTABLE_NO_REARM":
        return "RECOVERS_WITH_CAUSAL_ALTERNATIVE"
    if current_entry is None:
        raise ValueError("current executable candidate lost entry timestamp")
    win_candidate, win_entry = winner
    same = (
        win_candidate.closeback_at == current_selected.closeback_at
        and win_candidate.side is current_selected.side
        and win_candidate.reference.price == current_selected.reference.price
        and win_candidate.reference.source == current_selected.reference.source
    )
    if same:
        return "CURRENT_FIRST_REMAINS_WINNER"
    if win_entry < current_entry:
        return "ALTERNATIVE_PREEMPTS_CURRENT_FIRST"
    if win_entry == current_entry:
        return "ALTERNATIVE_TIES_CURRENT_ENTRY"
    return "CURRENT_FIRST_SHOULD_PRECEDE_ALTERNATIVE"


def build_market_report(
    m1_root: Path,
    *,
    session: CapitalizerSession,
) -> tuple[dict[str, Any], tuple[CausalArbitrationRow, ...]]:
    all_bars = tuple(
        bar
        for bar in iter_cibo_m1(m1_root)
        if LOOKBACK_START <= bar.opened_at < WINDOW_END + timedelta(days=1)
    )
    if not all_bars:
        raise ValueError("causal arbitration atlas found no native M1")
    symbol = all_bars[0].symbol
    if any(bar.symbol != symbol for bar in all_bars):
        raise ValueError("causal arbitration atlas requires one market")

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

    rows: list[CausalArbitrationRow] = []
    relation_counts: Counter[str] = Counter()
    winner_sources: Counter[str] = Counter()
    control_mismatches = 0

    dates = sorted(
        key
        for key in execution_by_day
        if WINDOW_START.date().isoformat() <= key < WINDOW_END.date().isoformat()
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

            _, candidates = v1._enumerate_closebacks(
                hour_bars,
                levels=levels,
                m5=m5,
                m5_closes=m5_closes,
                h1_open=h1_open,
                h1_deadline=h1_deadline,
            )
            if not candidates:
                continue

            current_selected, current_ambiguous = v1._current_first(candidates)
            eligible, ambiguous = _eligible_after_ambiguity(candidates)
            if ambiguous != current_ambiguous:
                control_mismatches += 1

            current_stage = "AMBIGUOUS_FIRST_CLOSEBACK"
            current_entry: datetime | None = None
            if current_selected is not None:
                current_stage, current_entry = v1._stage(
                    current_selected,
                    execution=execution,
                    m3=m3,
                    m3_closes=m3_closes,
                    m3_pivots=m3_pivots,
                    buffer_price=buffer_price,
                )

            executable: list[tuple[v3.SweepCloseback, datetime]] = []
            for candidate in eligible:
                stage, entry_at = v1._stage(
                    candidate,
                    execution=execution,
                    m3=m3,
                    m3_closes=m3_closes,
                    m3_pivots=m3_pivots,
                    buffer_price=buffer_price,
                )
                if stage == "EXECUTABLE_NO_REARM" and entry_at is not None:
                    executable.append((candidate, entry_at))

            winner: tuple[v3.SweepCloseback, datetime] | None = None
            if executable:
                winner = min(
                    executable,
                    key=lambda pair: (
                        pair[1],
                        pair[0].closeback_at,
                        pair[0].sweep_at,
                        pair[0].reference.source,
                        pair[0].reference.price,
                    ),
                )

            relation = _relation(
                current_selected=current_selected,
                current_stage=current_stage,
                current_entry=current_entry,
                winner=winner,
            )
            relation_counts[relation] += 1
            if winner is not None:
                winner_sources[winner[0].reference.source] += 1

            winner_is_current = False
            if winner is not None and current_selected is not None:
                winner_is_current = (
                    winner[0].closeback_at == current_selected.closeback_at
                    and winner[0].side is current_selected.side
                    and winner[0].reference.price == current_selected.reference.price
                    and winner[0].reference.source == current_selected.reference.source
                )

            rows.append(
                CausalArbitrationRow(
                    symbol=symbol,
                    session=session.value,
                    operating_date=value,
                    h1_open=h1_open.isoformat(),
                    h1_deadline=h1_deadline.isoformat(),
                    candidate_count=len(candidates),
                    earliest_closeback_ambiguous=ambiguous,
                    eligible_candidate_count=len(eligible),
                    current_first_stage=current_stage,
                    current_first_entry_at=(
                        None if current_entry is None else current_entry.isoformat()
                    ),
                    causal_winner_exists=winner is not None,
                    causal_winner_entry_at=(
                        None if winner is None else winner[1].isoformat()
                    ),
                    causal_winner_closeback_at=(
                        None if winner is None else winner[0].closeback_at.isoformat()
                    ),
                    causal_winner_source=(
                        None if winner is None else winner[0].reference.source
                    ),
                    causal_winner_side=(
                        None if winner is None else winner[0].side.value
                    ),
                    causal_winner_is_current_first=winner_is_current,
                    relation_vs_current=relation,
                )
            )

    ordered = tuple(sorted(rows, key=lambda item: (item.h1_open, item.symbol)))
    return {
        "identity": IDENTITY,
        "symbol": symbol,
        "session": session.value,
        "h1_with_candidates": len(ordered),
        "h1_with_multiple_candidates": sum(item.candidate_count > 1 for item in ordered),
        "earliest_closeback_ambiguous": sum(
            item.earliest_closeback_ambiguous for item in ordered
        ),
        "h1_with_causal_winner": sum(item.causal_winner_exists for item in ordered),
        "relation_vs_current": dict(sorted(relation_counts.items())),
        "causal_winner_source_counts": dict(sorted(winner_sources.items())),
        "control_mismatches": control_mismatches,
        "earliest_executable_wins": True,
        "ambiguous_earliest_tie_fail_closed": True,
        "strictly_later_closebacks_remain_eligible_after_ambiguity": True,
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
    rows: tuple[CausalArbitrationRow, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    stem = (
        f"capitalizer-{symbol}-v3-source-first-"
        "closeback-causal-arbitration-atlas-2y-v1"
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
            "capitalizer-*-v3-source-first-"
            "closeback-causal-arbitration-atlas-2y-v1.json"
        )
    )
    if len(paths) != 9:
        raise ValueError(
            f"causal arbitration matrix requires 9 reports, got {len(paths)}"
        )
    return [dict(json.loads(path.read_text(encoding="utf-8"))) for path in paths]


def build_matrix(root: Path) -> dict[str, Any]:
    reports = _load_reports(root)
    relations: Counter[str] = Counter()
    sources: Counter[str] = Counter()
    for report in reports:
        for key, value in dict(report["relation_vs_current"]).items():
            relations[str(key)] += int(value)
        for key, value in dict(report["causal_winner_source_counts"]).items():
            sources[str(key)] += int(value)

    return {
        "identity": MATRIX_IDENTITY,
        "market_count": 9,
        "h1_with_candidates": sum(int(item["h1_with_candidates"]) for item in reports),
        "h1_with_multiple_candidates": sum(
            int(item["h1_with_multiple_candidates"]) for item in reports
        ),
        "earliest_closeback_ambiguous": sum(
            int(item["earliest_closeback_ambiguous"]) for item in reports
        ),
        "h1_with_causal_winner": sum(
            int(item["h1_with_causal_winner"]) for item in reports
        ),
        "relation_vs_current": dict(sorted(relations.items())),
        "causal_winner_source_counts": dict(sorted(sources.items())),
        "control_mismatches": sum(int(item["control_mismatches"]) for item in reports),
        "markets": sorted(reports, key=lambda item: str(item["symbol"])),
        "earliest_executable_wins": True,
        "ambiguous_earliest_tie_fail_closed": True,
        "strictly_later_closebacks_remain_eligible_after_ambiguity": True,
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
        "closeback-causal-arbitration-atlas-2y-v1.json"
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
