"""Pair/session/side compatibility research for QORE Capitalizer.

Consumed-development evidence only. This lab characterizes which market pairs coexist inside
the Owner's MAX3 session budget and how their joint economics change by:
- operating session;
- canonical LONG/SHORT side combination;
- same-session co-presence versus true active-position overlap;
- shared-factor relation;
- chronological order and ordinal of the second leg.

It does not rank or promote pairs, invent a profit objective, optimize numeric thresholds,
grant authority over QORE Risk, apply costs, freeze a candidate, or claim a fresh holdout.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import date, datetime
from decimal import Decimal
from itertools import combinations
from pathlib import Path

from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_portfolio_exposure_forensics import (
    CapitalizerExposureCandidate,
    _assessment,
    _load_candidates,
    _ordered,
)
from qore.infrastructure.trader_lab.capitalizer_portfolio_session_flow_viability import (
    PortfolioFlowMetrics,
    _metrics,
    _session_key,
)
from qore.infrastructure.trader_lab.capitalizer_session_clock import capitalizer_session_at
from qore.infrastructure.trader_lab.capitalizer_session_flow_viability import NEW_YORK

IDENTITY = "QORE_CAPITALIZER_PAIR_SESSION_COMPATIBILITY_V1"


@dataclass(frozen=True, slots=True)
class CapitalizerPairEpisodeMetrics:
    episodes: int
    total_r: str
    mean_r: str
    profit_factor: str | None
    max_drawdown_r: str
    max_losing_streak: int
    positive_years: int
    years_observed: int


@dataclass(frozen=True, slots=True)
class CapitalizerPairAggregateCell:
    tie_policy: str
    scope: str
    session: str
    symbol_a: str
    symbol_b: str
    relation: str
    episodes: int
    pair_metrics: CapitalizerPairEpisodeMetrics
    leg_a_metrics: PortfolioFlowMetrics
    leg_b_metrics: PortfolioFlowMetrics


@dataclass(frozen=True, slots=True)
class CapitalizerPairSideCell:
    tie_policy: str
    scope: str
    session: str
    symbol_a: str
    side_a: str
    symbol_b: str
    side_b: str
    relation: str
    episodes: int
    pair_metrics: CapitalizerPairEpisodeMetrics
    leg_a_metrics: PortfolioFlowMetrics
    leg_b_metrics: PortfolioFlowMetrics


@dataclass(frozen=True, slots=True)
class CapitalizerPairTransitionCell:
    tie_policy: str
    session: str
    first_symbol: str
    first_side: str
    second_symbol: str
    second_side: str
    second_ordinal: int
    active_overlap: bool
    relation: str
    episodes: int
    second_leg_metrics: PortfolioFlowMetrics
    pair_metrics: CapitalizerPairEpisodeMetrics


@dataclass(frozen=True, slots=True)
class CapitalizerPairSessionCompatibilityReport:
    identity: str
    market_count: int
    symbols: tuple[str, ...]
    baseline_opportunities: int
    max3_selected_trades_by_tie_policy: dict[str, int]
    pair_aggregate_cells: tuple[CapitalizerPairAggregateCell, ...]
    pair_side_cells: tuple[CapitalizerPairSideCell, ...]
    transition_cells: tuple[CapitalizerPairTransitionCell, ...]
    max_executions_per_session: int = 3
    same_session_copresence_profiled: bool = True
    active_position_overlap_profiled: bool = True
    sides_profiled: bool = True
    chronological_order_profiled: bool = True
    shared_factor_relation_profiled: bool = True
    categorical_characterization_only: bool = True
    numeric_threshold_optimization_used: bool = False
    outcome_aware_ranking_used: bool = False
    pair_ranking_selected: bool = False
    positive_pnl_is_not_stop_condition: bool = True
    governed_profit_objective_not_modeled: bool = True
    qore_risk_authority_granted: bool = False
    costs_applied: bool = False
    development_only: bool = True
    candidate_frozen: bool = False
    fresh_holdout_claimed: bool = False
    promotion_allowed: bool = False


@dataclass(frozen=True, slots=True)
class _PairObservation:
    operating_date: date
    session: str
    symbol_a: str
    side_a: CapitalizerSide
    symbol_b: str
    side_b: CapitalizerSide
    relation: str
    active_overlap: bool
    first: CapitalizerExposureCandidate
    second: CapitalizerExposureCandidate
    first_ordinal: int
    second_ordinal: int

    @property
    def pair_r(self) -> Decimal:
        return self.first.realized_r + self.second.realized_r


def _profit_factor(values: tuple[Decimal, ...]) -> str | None:
    gross_profit = sum((value for value in values if value > 0), Decimal("0"))
    gross_loss = -sum((value for value in values if value < 0), Decimal("0"))
    if gross_loss == 0:
        return None if gross_profit == 0 else "Infinity"
    return str(gross_profit / gross_loss)


def _episode_metrics(
    observations: tuple[_PairObservation, ...],
) -> CapitalizerPairEpisodeMetrics:
    ordered = tuple(
        sorted(
            observations,
            key=lambda item: (
                item.second.entry_at,
                item.first.entry_at,
                item.symbol_a,
                item.symbol_b,
            ),
        )
    )
    values = tuple(item.pair_r for item in ordered)
    equity = Decimal("0")
    peak = Decimal("0")
    max_drawdown = Decimal("0")
    losing_streak = 0
    max_losing_streak = 0
    by_year: dict[int, Decimal] = defaultdict(lambda: Decimal("0"))

    for item, value in zip(ordered, values, strict=True):
        equity += value
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, peak - equity)
        if value < 0:
            losing_streak += 1
            max_losing_streak = max(max_losing_streak, losing_streak)
        else:
            losing_streak = 0
        by_year[item.operating_date.year] += value

    total = sum(values, Decimal("0"))
    return CapitalizerPairEpisodeMetrics(
        episodes=len(values),
        total_r=str(total),
        mean_r=str(total / Decimal(len(values))),
        profit_factor=_profit_factor(values),
        max_drawdown_r=str(max_drawdown),
        max_losing_streak=max_losing_streak,
        positive_years=sum(value > 0 for value in by_year.values()),
        years_observed=len(by_year),
    )


def _selected_by_session(
    candidates: tuple[CapitalizerExposureCandidate, ...],
    *,
    tie_policy: str,
) -> dict[str, tuple[CapitalizerExposureCandidate, ...]]:
    grouped: dict[str, list[CapitalizerExposureCandidate]] = defaultdict(list)
    for candidate in _ordered(candidates, tie_policy=tie_policy):
        key = _session_key(candidate.as_trade())
        if len(grouped[key]) < 3:
            grouped[key].append(candidate)
    return {key: tuple(value) for key, value in grouped.items()}


def _relation(
    first: CapitalizerExposureCandidate,
    second: CapitalizerExposureCandidate,
) -> str:
    return _assessment(second, (first,)).state


def _operating_date(candidate: CapitalizerExposureCandidate) -> date:
    return date.fromisoformat(_session_key(candidate.as_trade()).split(":", maxsplit=1)[1])


def _pair_observations(
    selected: dict[str, tuple[CapitalizerExposureCandidate, ...]],
) -> tuple[_PairObservation, ...]:
    result: list[_PairObservation] = []
    for rows in selected.values():
        for (first_index, first), (second_index, second) in combinations(
            tuple(enumerate(rows, start=1)),
            2,
        ):
            if first.symbol == second.symbol:
                continue
            if first.entry_at > second.entry_at:
                raise ValueError("MAX3 session rows lost chronological ordering")

            session = capitalizer_session_at(first.entry_at)
            second_session = capitalizer_session_at(second.entry_at)
            if session is None or second_session is None or session is not second_session:
                raise ValueError("pair observation crossed Capitalizer session")

            if first.symbol < second.symbol:
                symbol_a, side_a = first.symbol, first.side
                symbol_b, side_b = second.symbol, second.side
            else:
                symbol_a, side_a = second.symbol, second.side
                symbol_b, side_b = first.symbol, first.side

            result.append(
                _PairObservation(
                    operating_date=_operating_date(first),
                    session=session.value,
                    symbol_a=symbol_a,
                    side_a=side_a,
                    symbol_b=symbol_b,
                    side_b=side_b,
                    relation=_relation(first, second),
                    active_overlap=first.exit_at > second.entry_at,
                    first=first,
                    second=second,
                    first_ordinal=first_index,
                    second_ordinal=second_index,
                )
            )
    return tuple(result)


def _aggregate_cells(
    observations: tuple[_PairObservation, ...],
    *,
    tie_policy: str,
) -> tuple[CapitalizerPairAggregateCell, ...]:
    grouped: dict[
        tuple[str, str, str, str, str],
        list[_PairObservation],
    ] = defaultdict(list)

    for item in observations:
        grouped[
            ("SESSION_COPRESENCE", item.session, item.symbol_a, item.symbol_b, item.relation)
        ].append(item)
        if item.active_overlap:
            grouped[
                ("ACTIVE_OVERLAP", item.session, item.symbol_a, item.symbol_b, item.relation)
            ].append(item)

    cells: list[CapitalizerPairAggregateCell] = []
    for (scope, session, symbol_a, symbol_b, relation), rows in sorted(grouped.items()):
        observations_tuple = tuple(rows)
        leg_a = tuple(
            (item.first if item.first.symbol == symbol_a else item.second).as_trade()
            for item in observations_tuple
        )
        leg_b = tuple(
            (item.first if item.first.symbol == symbol_b else item.second).as_trade()
            for item in observations_tuple
        )
        cells.append(
            CapitalizerPairAggregateCell(
                tie_policy=tie_policy,
                scope=scope,
                session=session,
                symbol_a=symbol_a,
                symbol_b=symbol_b,
                relation=relation,
                episodes=len(rows),
                pair_metrics=_episode_metrics(observations_tuple),
                leg_a_metrics=_metrics(leg_a),
                leg_b_metrics=_metrics(leg_b),
            )
        )
    return tuple(cells)


def _side_cells(
    observations: tuple[_PairObservation, ...],
    *,
    tie_policy: str,
) -> tuple[CapitalizerPairSideCell, ...]:
    grouped: dict[
        tuple[str, str, str, CapitalizerSide, str, CapitalizerSide, str],
        list[_PairObservation],
    ] = defaultdict(list)

    for item in observations:
        key = (
            "SESSION_COPRESENCE",
            item.session,
            item.symbol_a,
            item.side_a,
            item.symbol_b,
            item.side_b,
            item.relation,
        )
        grouped[key].append(item)
        if item.active_overlap:
            grouped[
                (
                    "ACTIVE_OVERLAP",
                    item.session,
                    item.symbol_a,
                    item.side_a,
                    item.symbol_b,
                    item.side_b,
                    item.relation,
                )
            ].append(item)

    cells: list[CapitalizerPairSideCell] = []
    for (
        scope,
        session,
        symbol_a,
        side_a,
        symbol_b,
        side_b,
        relation,
    ), rows in sorted(grouped.items(), key=lambda item: tuple(str(value) for value in item[0])):
        observations_tuple = tuple(rows)
        leg_a = tuple(
            (item.first if item.first.symbol == symbol_a else item.second).as_trade()
            for item in observations_tuple
        )
        leg_b = tuple(
            (item.first if item.first.symbol == symbol_b else item.second).as_trade()
            for item in observations_tuple
        )
        cells.append(
            CapitalizerPairSideCell(
                tie_policy=tie_policy,
                scope=scope,
                session=session,
                symbol_a=symbol_a,
                side_a=side_a.value,
                symbol_b=symbol_b,
                side_b=side_b.value,
                relation=relation,
                episodes=len(rows),
                pair_metrics=_episode_metrics(observations_tuple),
                leg_a_metrics=_metrics(leg_a),
                leg_b_metrics=_metrics(leg_b),
            )
        )
    return tuple(cells)


def _transition_cells(
    observations: tuple[_PairObservation, ...],
    *,
    tie_policy: str,
) -> tuple[CapitalizerPairTransitionCell, ...]:
    grouped: dict[
        tuple[str, str, CapitalizerSide, str, CapitalizerSide, int, bool, str],
        list[_PairObservation],
    ] = defaultdict(list)

    for item in observations:
        grouped[
            (
                item.session,
                item.first.symbol,
                item.first.side,
                item.second.symbol,
                item.second.side,
                item.second_ordinal,
                item.active_overlap,
                item.relation,
            )
        ].append(item)

    cells: list[CapitalizerPairTransitionCell] = []
    for (
        session,
        first_symbol,
        first_side,
        second_symbol,
        second_side,
        second_ordinal,
        active_overlap,
        relation,
    ), rows in sorted(grouped.items(), key=lambda item: tuple(str(value) for value in item[0])):
        observations_tuple = tuple(rows)
        cells.append(
            CapitalizerPairTransitionCell(
                tie_policy=tie_policy,
                session=session,
                first_symbol=first_symbol,
                first_side=first_side.value,
                second_symbol=second_symbol,
                second_side=second_side.value,
                second_ordinal=second_ordinal,
                active_overlap=active_overlap,
                relation=relation,
                episodes=len(rows),
                second_leg_metrics=_metrics(
                    tuple(item.second.as_trade() for item in observations_tuple)
                ),
                pair_metrics=_episode_metrics(observations_tuple),
            )
        )
    return tuple(cells)


def build_pair_session_compatibility_report(
    root: Path,
) -> CapitalizerPairSessionCompatibilityReport:
    candidates = _load_candidates(root)
    aggregate_cells: list[CapitalizerPairAggregateCell] = []
    side_cells: list[CapitalizerPairSideCell] = []
    transition_cells: list[CapitalizerPairTransitionCell] = []
    selected_counts: dict[str, int] = {}

    for tie_policy in ("SYMBOL_ASC", "SYMBOL_DESC"):
        selected = _selected_by_session(candidates, tie_policy=tie_policy)
        observations = _pair_observations(selected)
        selected_counts[tie_policy] = sum(len(rows) for rows in selected.values())
        aggregate_cells.extend(_aggregate_cells(observations, tie_policy=tie_policy))
        side_cells.extend(_side_cells(observations, tie_policy=tie_policy))
        transition_cells.extend(_transition_cells(observations, tie_policy=tie_policy))

    symbols = tuple(sorted({item.symbol for item in candidates}))
    return CapitalizerPairSessionCompatibilityReport(
        identity=IDENTITY,
        market_count=len(symbols),
        symbols=symbols,
        baseline_opportunities=len(candidates),
        max3_selected_trades_by_tie_policy=selected_counts,
        pair_aggregate_cells=tuple(aggregate_cells),
        pair_side_cells=tuple(side_cells),
        transition_cells=tuple(transition_cells),
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Capitalizer pair/session/side compatibility characterization"
    )
    parser.add_argument("input_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = build_pair_session_compatibility_report(args.input_root)
    args.output.mkdir(parents=True, exist_ok=True)
    path = args.output / "capitalizer-pair-session-compatibility-v1.json"
    path.write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(asdict(report), sort_keys=True))


if __name__ == "__main__":
    main()
