"""Session-flow viability for QORE Capitalizer.

Consumed-development falsification of the Owner-amended scalper contract:
- up to three executions per session;
- positive realized session PnL does not itself stop valid new opportunities;
- diagnostic comparison of MAX2, MAX3, and a third execution allowed only when
  prior realized session PnL is positive;
- every position must close inside the same session.

No numeric profit objective is invented here. QORE Risk/CORE remains sovereign.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerSession
from qore.infrastructure.trader_lab.capitalizer_departure_timing_forensics import (
    _load_timing_rows,
    _timing_state,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_h1_boundary_type_forensics import (
    _boundary_type_state,
    _episode_boundary_types,
)
from qore.infrastructure.trader_lab.capitalizer_h1_episode_multiplicity_forensics import (
    _baseline,
    _journey_boundaries,
)
from qore.infrastructure.trader_lab.capitalizer_h1_source_age_forensics import (
    _source_age_state,
)
from qore.infrastructure.trader_lab.capitalizer_position_lifecycle_forensics import (
    _state_family,
)
from qore.infrastructure.trader_lab.capitalizer_r0_gross_characterization import (
    CapitalizerR0Metrics,
    CapitalizerR0Trade,
    summarize_r0,
)
from qore.infrastructure.trader_lab.capitalizer_reclaim_phase_forensics import (
    _episode_reclaim_times,
    _reclaim_phase,
)
from qore.infrastructure.trader_lab.capitalizer_session_clock import capitalizer_session_at

IDENTITY = "QORE_CAPITALIZER_SESSION_FLOW_VIABILITY_V1"
NEW_YORK = ZoneInfo("America/New_York")


@dataclass(frozen=True, slots=True)
class CapitalizerSessionFlowVariant:
    name: str
    mean_monthly_trades: str
    metrics: CapitalizerR0Metrics


@dataclass(frozen=True, slots=True)
class CapitalizerThirdExecutionCell:
    name: str
    prior_realized_positive: int
    prior_realized_nonpositive: int
    metrics: CapitalizerR0Metrics


@dataclass(frozen=True, slots=True)
class CapitalizerSessionFlowViabilityReport:
    identity: str
    symbol: str
    sessions_observed: int
    sessions_with_at_least_three_candidates: int
    baseline_metrics: CapitalizerR0Metrics
    variants: tuple[CapitalizerSessionFlowVariant, ...]
    third_execution_cells: tuple[CapitalizerThirdExecutionCell, ...]
    same_session_exit_verified: bool
    positive_pnl_is_not_stop_condition: bool = True
    governed_profit_objective_not_modeled: bool = True
    max_executions_per_session: int = 3
    development_only: bool = True
    costs_applied: bool = False
    candidate_frozen: bool = False
    fresh_holdout_claimed: bool = False
    rule_selected: bool = False
    promotion_allowed: bool = False


def _session_key(trade: CapitalizerR0Trade) -> str:
    session = capitalizer_session_at(trade.entry_at)
    if session is None:
        raise ValueError("trade entry must belong to a Capitalizer session")
    local = trade.entry_at.astimezone(NEW_YORK)
    operating_date = local.date()
    if session is CapitalizerSession.ASIA and local.time() < time(2, 0):
        operating_date -= timedelta(days=1)
    return f"{session.value}:{operating_date.isoformat()}"


def _session_end(entry_at: datetime) -> datetime:
    session = capitalizer_session_at(entry_at)
    if session is None:
        raise ValueError("entry must belong to a Capitalizer session")
    local = entry_at.astimezone(NEW_YORK)
    day = local.date()
    if session is CapitalizerSession.ASIA:
        if local.time() >= time(20, 0):
            day += timedelta(days=1)
        return datetime.combine(day, time(2, 0), tzinfo=NEW_YORK)
    if session is CapitalizerSession.LONDON:
        return datetime.combine(day, time(8, 30), tzinfo=NEW_YORK)
    return datetime.combine(day, time(16, 0), tzinfo=NEW_YORK)


def _assert_same_session_exit(trades: tuple[CapitalizerR0Trade, ...]) -> None:
    for trade in trades:
        if trade.exit_at > _session_end(trade.entry_at):
            raise ValueError("Capitalizer scalp crossed its session boundary")


def _prior_realized_r(
    selected_in_session: tuple[CapitalizerR0Trade, ...],
    candidate: CapitalizerR0Trade,
) -> Decimal:
    return sum(
        (
            trade.realized_gross_r
            for trade in selected_in_session
            if trade.exit_at <= candidate.entry_at
        ),
        Decimal("0"),
    )


def _select(
    trades: tuple[CapitalizerR0Trade, ...],
    *,
    mode: str,
) -> tuple[CapitalizerR0Trade, ...]:
    if mode not in {"MAX2", "MAX3_ANY_VALID", "MAX3_POSITIVE_REALIZED_CONTINUATION"}:
        raise ValueError("unsupported session-flow mode")
    per_session: dict[str, list[CapitalizerR0Trade]] = defaultdict(list)
    selected: list[CapitalizerR0Trade] = []
    for trade in sorted(trades, key=lambda item: (item.entry_at, item.exit_at)):
        accepted = per_session[_session_key(trade)]
        cap = 2 if mode == "MAX2" else 3
        if len(accepted) >= cap:
            continue
        if (
            mode == "MAX3_POSITIVE_REALIZED_CONTINUATION"
            and len(accepted) >= 2
            and _prior_realized_r(tuple(accepted), trade) <= 0
        ):
            continue
        accepted.append(trade)
        selected.append(trade)
    return tuple(selected)


def _mean_monthly_trades(trades: tuple[CapitalizerR0Trade, ...]) -> str:
    ordered = sorted(trades, key=lambda item: item.entry_at)
    first = ordered[0].entry_at.astimezone(NEW_YORK)
    last = ordered[-1].entry_at.astimezone(NEW_YORK)
    months = (last.year - first.year) * 12 + last.month - first.month + 1
    return str(Decimal(len(trades)) / Decimal(months))


def _third_execution_cell(
    *,
    name: str,
    trades: tuple[CapitalizerR0Trade, ...],
) -> CapitalizerThirdExecutionCell:
    per_session: dict[str, list[CapitalizerR0Trade]] = defaultdict(list)
    third: list[CapitalizerR0Trade] = []
    positive = 0
    nonpositive = 0
    for trade in sorted(trades, key=lambda item: (item.entry_at, item.exit_at)):
        accepted = per_session[_session_key(trade)]
        accepted.append(trade)
        if len(accepted) == 3:
            prior = _prior_realized_r(tuple(accepted[:2]), trade)
            if prior > 0:
                positive += 1
            else:
                nonpositive += 1
            third.append(trade)
    if not third:
        raise ValueError("third-execution cell requires observations")
    return CapitalizerThirdExecutionCell(
        name=name,
        prior_realized_positive=positive,
        prior_realized_nonpositive=nonpositive,
        metrics=summarize_r0(tuple(third)).metrics,
    )


def _build_report_from_baseline(
    baseline: tuple[CapitalizerR0Trade, ...],
) -> CapitalizerSessionFlowViabilityReport:
    _assert_same_session_exit(baseline)
    grouped: dict[str, int] = defaultdict(int)
    for trade in baseline:
        grouped[_session_key(trade)] += 1

    raw = (
        ("MAX2", _select(baseline, mode="MAX2")),
        ("MAX3_ANY_VALID", _select(baseline, mode="MAX3_ANY_VALID")),
        (
            "MAX3_POSITIVE_REALIZED_CONTINUATION",
            _select(baseline, mode="MAX3_POSITIVE_REALIZED_CONTINUATION"),
        ),
    )
    variants = tuple(
        CapitalizerSessionFlowVariant(
            name=name,
            mean_monthly_trades=_mean_monthly_trades(selected),
            metrics=summarize_r0(selected).metrics,
        )
        for name, selected in raw
    )

    return CapitalizerSessionFlowViabilityReport(
        identity=IDENTITY,
        symbol=baseline[0].symbol,
        sessions_observed=len(grouped),
        sessions_with_at_least_three_candidates=sum(
            count >= 3 for count in grouped.values()
        ),
        baseline_metrics=summarize_r0(baseline).metrics,
        variants=variants,
        third_execution_cells=(
            _third_execution_cell(
                name="MAX3_ANY_VALID_THIRD_EXECUTION",
                trades=raw[1][1],
            ),
            _third_execution_cell(
                name="POSITIVE_REALIZED_CONTINUATION_THIRD_EXECUTION",
                trades=raw[2][1],
            ),
        ),
        same_session_exit_verified=True,
    )





def build_session_flow_viability_report(
    *,
    m5_root: Path,
    journey_root: Path,
    target_root: Path,
) -> CapitalizerSessionFlowViabilityReport:
    baseline, _, _ = _baseline(
        m5_root=m5_root,
        journey_root=journey_root,
        target_root=target_root,
    )
    return _build_report_from_baseline(baseline)


def _write_baseline_trade_ledger(
    baseline: tuple[CapitalizerR0Trade, ...],
    output: Path,
    *,
    journey_root: Path,
    state_index: dict[tuple[str, CapitalizerSide], str],
    episode_index: dict[tuple[str, CapitalizerSide], tuple[str, ...]],
) -> None:
    symbol = baseline[0].symbol
    path = output / f"capitalizer-{symbol.lower()}-session-flow-trades-v1.jsonl"
    rows = sorted(baseline, key=lambda item: (item.entry_at, item.exit_at))
    timing = _load_timing_rows(journey_root)
    boundaries = _journey_boundaries(journey_root)
    boundary_types = _episode_boundary_types(journey_root)
    reclaim_times = _episode_reclaim_times(journey_root)

    with path.open("w", encoding="utf-8") as handle:
        for trade in rows:
            row = {
                "symbol": trade.symbol,
                "side": trade.side.value,
                "signal_at": trade.signal_at.isoformat(),
                "entry_at": trade.entry_at.isoformat(),
                "exit_at": trade.exit_at.isoformat(),
                "event_labels": list(trade.event_labels),
                "planned_reward_r": str(trade.planned_reward_r),
                "state_family": _state_family(trade, state_index),
                "cisd_timing_state": _timing_state(
                    trade,
                    dimension="cisd",
                    episode_index=episode_index,
                    timing=timing,
                ),
                "source_age_state": _source_age_state(
                    trade,
                    episode_index=episode_index,
                    boundaries=boundaries,
                ),
                "boundary_type_state": _boundary_type_state(
                    trade,
                    episode_index=episode_index,
                    boundary_types=boundary_types,
                ),
                "reclaim_phase": _reclaim_phase(
                    trade,
                    episode_index=episode_index,
                    reclaim_times=reclaim_times,
                ),
                "realized_gross_r": str(trade.realized_gross_r),
            }
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Capitalizer session-flow viability")
    parser.add_argument("m5_root", type=Path)
    parser.add_argument("journey_root", type=Path)
    parser.add_argument("target_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    baseline, state_index, episode_index = _baseline(
        m5_root=args.m5_root,
        journey_root=args.journey_root,
        target_root=args.target_root,
    )
    report = _build_report_from_baseline(baseline)
    args.output.mkdir(parents=True, exist_ok=True)
    _write_baseline_trade_ledger(
        baseline,
        args.output,
        journey_root=args.journey_root,
        state_index=state_index,
        episode_index=episode_index,
    )
    path = args.output / f"capitalizer-{report.symbol.lower()}-session-flow-viability-v1.json"
    path.write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(asdict(report), sort_keys=True))


if __name__ == "__main__":
    main()
