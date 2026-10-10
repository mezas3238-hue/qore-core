"""Triad/session/side compatibility research for QORE Capitalizer.

Consumed-development evidence only. This lab characterizes complete three-execution session
configurations under the Owner MAX3 ceiling. It measures canonical market/side triads and the
chronological 1->2->3 path, including active-position overlap and causal exposure relation
visible when the second and third candidates arrive.

No triad is ranked, promoted, frozen, or authorized here. No numeric threshold optimization,
outcome-aware routing, profit objective, costs, fresh holdout claim, or QORE Risk authority is
introduced.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_pair_session_compatibility import (
    _selected_by_session,
)
from qore.infrastructure.trader_lab.capitalizer_portfolio_exposure_forensics import (
    CapitalizerExposureCandidate,
    _assessment,
    _load_candidates,
)
from qore.infrastructure.trader_lab.capitalizer_portfolio_session_flow_viability import (
    PortfolioFlowMetrics,
    _metrics,
    _session_key,
)
from qore.infrastructure.trader_lab.capitalizer_session_clock import capitalizer_session_at

IDENTITY = "QORE_CAPITALIZER_TRIAD_SESSION_COMPATIBILITY_V1"


@dataclass(frozen=True, slots=True)
class CapitalizerTriadEpisodeMetrics:
    episodes: int
    total_r: str
    mean_r: str
    profit_factor: str | None
    max_drawdown_r: str
    max_losing_streak: int
    positive_years: int
    years_observed: int


@dataclass(frozen=True, slots=True)
class CapitalizerTriadSideCell:
    tie_policy: str
    session: str
    symbol_a: str
    side_a: str
    symbol_b: str
    side_b: str
    symbol_c: str
    side_c: str
    episodes: int
    all_three_active_at_third_entry: int
    triad_metrics: CapitalizerTriadEpisodeMetrics
    leg_a_metrics: PortfolioFlowMetrics
    leg_b_metrics: PortfolioFlowMetrics
    leg_c_metrics: PortfolioFlowMetrics


@dataclass(frozen=True, slots=True)
class CapitalizerTriadPathCell:
    tie_policy: str
    session: str
    first_symbol: str
    first_side: str
    second_symbol: str
    second_side: str
    third_symbol: str
    third_side: str
    second_relation: str
    third_relation: str
    first_active_at_third_entry: bool
    second_active_at_third_entry: bool
    episodes: int
    triad_metrics: CapitalizerTriadEpisodeMetrics
    third_leg_metrics: PortfolioFlowMetrics


@dataclass(frozen=True, slots=True)
class CapitalizerTriadSessionCompatibilityReport:
    identity: str
    market_count: int
    symbols: tuple[str, ...]
    baseline_opportunities: int
    complete_three_trade_sessions_by_tie_policy: dict[str, int]
    triad_side_cells: tuple[CapitalizerTriadSideCell, ...]
    triad_path_cells: tuple[CapitalizerTriadPathCell, ...]
    max_executions_per_session: int = 3
    complete_triad_only: bool = True
    sides_profiled: bool = True
    chronological_order_profiled: bool = True
    active_position_overlap_profiled: bool = True
    exposure_relation_profiled: bool = True
    categorical_characterization_only: bool = True
    numeric_threshold_optimization_used: bool = False
    outcome_aware_routing_used: bool = False
    triad_routing_selected: bool = False
    positive_pnl_is_not_stop_condition: bool = True
    governed_profit_objective_not_modeled: bool = True
    qore_risk_authority_granted: bool = False
    costs_applied: bool = False
    development_only: bool = True
    candidate_frozen: bool = False
    fresh_holdout_claimed: bool = False
    promotion_allowed: bool = False


@dataclass(frozen=True, slots=True)
class _TriadObservation:
    operating_date: date
    session: str
    first: CapitalizerExposureCandidate
    second: CapitalizerExposureCandidate
    third: CapitalizerExposureCandidate
    second_relation: str
    third_relation: str
    first_active_at_third_entry: bool
    second_active_at_third_entry: bool

    @property
    def triad_r(self) -> Decimal:
        return self.first.realized_r + self.second.realized_r + self.third.realized_r


def _profit_factor(values: tuple[Decimal, ...]) -> str | None:
    gross_profit = sum((value for value in values if value > 0), Decimal("0"))
    gross_loss = -sum((value for value in values if value < 0), Decimal("0"))
    if gross_loss == 0:
        return None if gross_profit == 0 else "Infinity"
    return str(gross_profit / gross_loss)


def _triad_metrics(
    observations: tuple[_TriadObservation, ...],
) -> CapitalizerTriadEpisodeMetrics:
    if not observations:
        raise ValueError("triad metrics require observations")
    ordered = tuple(
        sorted(
            observations,
            key=lambda item: (
                item.third.entry_at,
                item.second.entry_at,
                item.first.entry_at,
            ),
        )
    )
    values = tuple(item.triad_r for item in ordered)
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
    return CapitalizerTriadEpisodeMetrics(
        episodes=len(values),
        total_r=str(total),
        mean_r=str(total / Decimal(len(values))),
        profit_factor=_profit_factor(values),
        max_drawdown_r=str(max_drawdown),
        max_losing_streak=max_losing_streak,
        positive_years=sum(value > 0 for value in by_year.values()),
        years_observed=len(by_year),
    )


def _operating_date(candidate: CapitalizerExposureCandidate) -> date:
    return date.fromisoformat(_session_key(candidate.as_trade()).split(":", maxsplit=1)[1])


def _observations(
    selected: dict[str, tuple[CapitalizerExposureCandidate, ...]],
) -> tuple[_TriadObservation, ...]:
    result: list[_TriadObservation] = []
    for rows in selected.values():
        if len(rows) != 3:
            continue
        first, second, third = rows
        session = capitalizer_session_at(first.entry_at)
        if session is None:
            raise ValueError("triad lost Capitalizer session")
        if any(capitalizer_session_at(item.entry_at) is not session for item in rows):
            raise ValueError("triad crossed Capitalizer session")
        if len({item.symbol for item in rows}) != 3:
            continue

        second_active = (first,) if first.exit_at > second.entry_at else ()
        active_at_third = tuple(
            item for item in (first, second) if item.exit_at > third.entry_at
        )
        result.append(
            _TriadObservation(
                operating_date=_operating_date(first),
                session=session.value,
                first=first,
                second=second,
                third=third,
                second_relation=_assessment(second, second_active).state,
                third_relation=_assessment(third, active_at_third).state,
                first_active_at_third_entry=first.exit_at > third.entry_at,
                second_active_at_third_entry=second.exit_at > third.entry_at,
            )
        )
    return tuple(result)


def _canonical(
    item: _TriadObservation,
) -> tuple[
    tuple[str, CapitalizerSide],
    tuple[str, CapitalizerSide],
    tuple[str, CapitalizerSide],
]:
    rows = sorted(
        (
            (item.first.symbol, item.first.side),
            (item.second.symbol, item.second.side),
            (item.third.symbol, item.third.side),
        ),
        key=lambda row: row[0],
    )
    return rows[0], rows[1], rows[2]


def _candidate_for_symbol(
    item: _TriadObservation,
    symbol: str,
) -> CapitalizerExposureCandidate:
    for candidate in (item.first, item.second, item.third):
        if candidate.symbol == symbol:
            return candidate
    raise ValueError("triad symbol not found")


def _side_cells(
    observations: tuple[_TriadObservation, ...],
    *,
    tie_policy: str,
) -> tuple[CapitalizerTriadSideCell, ...]:
    grouped: dict[
        tuple[
            str,
            str,
            CapitalizerSide,
            str,
            CapitalizerSide,
            str,
            CapitalizerSide,
        ],
        list[_TriadObservation],
    ] = defaultdict(list)

    for item in observations:
        a, b, c = _canonical(item)
        grouped[
            (
                item.session,
                a[0],
                a[1],
                b[0],
                b[1],
                c[0],
                c[1],
            )
        ].append(item)

    cells: list[CapitalizerTriadSideCell] = []
    for (
        session,
        symbol_a,
        side_a,
        symbol_b,
        side_b,
        symbol_c,
        side_c,
    ), rows in sorted(grouped.items(), key=lambda entry: tuple(str(v) for v in entry[0])):
        obs = tuple(rows)
        cells.append(
            CapitalizerTriadSideCell(
                tie_policy=tie_policy,
                session=session,
                symbol_a=symbol_a,
                side_a=side_a.value,
                symbol_b=symbol_b,
                side_b=side_b.value,
                symbol_c=symbol_c,
                side_c=side_c.value,
                episodes=len(obs),
                all_three_active_at_third_entry=sum(
                    item.first_active_at_third_entry
                    and item.second_active_at_third_entry
                    for item in obs
                ),
                triad_metrics=_triad_metrics(obs),
                leg_a_metrics=_metrics(
                    tuple(_candidate_for_symbol(item, symbol_a).as_trade() for item in obs)
                ),
                leg_b_metrics=_metrics(
                    tuple(_candidate_for_symbol(item, symbol_b).as_trade() for item in obs)
                ),
                leg_c_metrics=_metrics(
                    tuple(_candidate_for_symbol(item, symbol_c).as_trade() for item in obs)
                ),
            )
        )
    return tuple(cells)


def _path_cells(
    observations: tuple[_TriadObservation, ...],
    *,
    tie_policy: str,
) -> tuple[CapitalizerTriadPathCell, ...]:
    grouped: dict[
        tuple[
            str,
            str,
            CapitalizerSide,
            str,
            CapitalizerSide,
            str,
            CapitalizerSide,
            str,
            str,
            bool,
            bool,
        ],
        list[_TriadObservation],
    ] = defaultdict(list)

    for item in observations:
        grouped[
            (
                item.session,
                item.first.symbol,
                item.first.side,
                item.second.symbol,
                item.second.side,
                item.third.symbol,
                item.third.side,
                item.second_relation,
                item.third_relation,
                item.first_active_at_third_entry,
                item.second_active_at_third_entry,
            )
        ].append(item)

    cells: list[CapitalizerTriadPathCell] = []
    for (
        session,
        first_symbol,
        first_side,
        second_symbol,
        second_side,
        third_symbol,
        third_side,
        second_relation,
        third_relation,
        first_active,
        second_active,
    ), rows in sorted(grouped.items(), key=lambda entry: tuple(str(v) for v in entry[0])):
        obs = tuple(rows)
        cells.append(
            CapitalizerTriadPathCell(
                tie_policy=tie_policy,
                session=session,
                first_symbol=first_symbol,
                first_side=first_side.value,
                second_symbol=second_symbol,
                second_side=second_side.value,
                third_symbol=third_symbol,
                third_side=third_side.value,
                second_relation=second_relation,
                third_relation=third_relation,
                first_active_at_third_entry=first_active,
                second_active_at_third_entry=second_active,
                episodes=len(obs),
                triad_metrics=_triad_metrics(obs),
                third_leg_metrics=_metrics(tuple(item.third.as_trade() for item in obs)),
            )
        )
    return tuple(cells)


def build_triad_session_compatibility_report(
    root: Path,
) -> CapitalizerTriadSessionCompatibilityReport:
    candidates = _load_candidates(root)
    side_cells: list[CapitalizerTriadSideCell] = []
    path_cells: list[CapitalizerTriadPathCell] = []
    complete_counts: dict[str, int] = {}

    for tie_policy in ("SYMBOL_ASC", "SYMBOL_DESC"):
        selected = _selected_by_session(candidates, tie_policy=tie_policy)
        observations = _observations(selected)
        complete_counts[tie_policy] = len(observations)
        side_cells.extend(_side_cells(observations, tie_policy=tie_policy))
        path_cells.extend(_path_cells(observations, tie_policy=tie_policy))

    symbols = tuple(sorted({item.symbol for item in candidates}))
    return CapitalizerTriadSessionCompatibilityReport(
        identity=IDENTITY,
        market_count=len(symbols),
        symbols=symbols,
        baseline_opportunities=len(candidates),
        complete_three_trade_sessions_by_tie_policy=complete_counts,
        triad_side_cells=tuple(side_cells),
        triad_path_cells=tuple(path_cells),
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Capitalizer three-trade session compatibility characterization"
    )
    parser.add_argument("input_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = build_triad_session_compatibility_report(args.input_root)
    args.output.mkdir(parents=True, exist_ok=True)
    path = args.output / "capitalizer-triad-session-compatibility-v1.json"
    path.write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(asdict(report), sort_keys=True))


if __name__ == "__main__":
    main()
