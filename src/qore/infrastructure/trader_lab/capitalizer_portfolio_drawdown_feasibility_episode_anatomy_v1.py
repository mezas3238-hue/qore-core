"""Portfolio drawdown feasibility and episode anatomy for Capitalizer.

This laboratory is deliberately diagnostic.  V27-V34 showed that choosing an
existing protection mode from a local trade/trigger state does not transport
across consumed eras.  Before another controller is trained, this module asks
three simpler questions on the immutable Surface chronology:

1. Does the existing nine-mode toolbox have physical ex-post capacity while
   preserving every entrant and Surface sizing multipliers?
2. What exactly composes the maximum peak-to-trough episode?
3. How much of that episode is outside the reach of the first +0.50R
   protection milestone, and how often do the existing actions matter at all?

The outcome oracle is intentionally non-causal and is never a candidate.  It
selects, per frozen trade, the already-existing protection mode with maximum
realized R under the Surface multiplier.  Its sole purpose is a physical
feasibility bound.  Runtime inference never consumes oracle outcomes here.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass, replace
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_r_milestone_protection_2r_v1 as milestone,
)
from qore.infrastructure.trader_lab import (
    capitalizer_factor_journey_probe_ranker_v11 as v11,
)
from qore.infrastructure.trader_lab import (
    capitalizer_recovery_trajectory_trigger_v18 as recovery_v18,
)
from qore.infrastructure.trader_lab import (
    capitalizer_sequence_failure_memory_abstention_v13 as v13,
)

IDENTITY = "QORE_CAPITALIZER_PORTFOLIO_DRAWDOWN_FEASIBILITY_EPISODE_ANATOMY_V1"
FIRST_PROTECTION_MILESTONE_R = Decimal("0.50")
ACTION_ORDER = tuple(mode.value for mode in milestone.ProtectionMode)


@dataclass(frozen=True, slots=True)
class DrawdownEpisode:
    episode_id: int
    peak_equity_r: str
    trough_equity_r: str
    max_drawdown_r: str
    start_index: int
    trough_index: int
    end_index: int
    trade_count: int
    descent_trade_count: int
    recovered_peak: bool


@dataclass(frozen=True, slots=True)
class EpisodeTradeAudit:
    period: str
    episode_id: int
    sequence_index: int
    symbol: str
    session: str
    operating_date: str
    side: str
    entry_at: str
    exit_at: str
    surface_mode: str
    base_multiplier: str
    surface_scaled_r: str
    surface_exit_reason: str
    original_max_milestone_r: str
    reached_first_protection_milestone: bool
    no_trigger_loss: bool
    trigger_reachable_loss: bool
    counterfactual_unique_outcomes: int
    counterfactual_range_r: str
    best_existing_mode: str
    best_existing_scaled_r: str
    best_existing_delta_r: str
    action_relevant: bool
    loss_rescuable_to_nonnegative: bool
    active_peer_count_at_entry: int
    shared_factor_peer_count_at_entry: int
    outcome_oracle_used_for_diagnostic: bool = True
    current_outcome_visible_to_runtime_decision: bool = False


def _canonical_rows(
    rows: tuple[milestone.SimulatedTrade, ...],
) -> tuple[milestone.SimulatedTrade, ...]:
    return tuple(
        sorted(
            rows,
            key=lambda row: (milestone._aware(row.entry_at), row.symbol),
        )
    )


def _drawdown_episodes(values: tuple[Decimal, ...]) -> tuple[DrawdownEpisode, ...]:
    episodes: list[DrawdownEpisode] = []
    equity = Decimal("0")
    peak = Decimal("0")
    active_start: int | None = None
    active_peak = Decimal("0")
    active_trough = Decimal("0")
    active_trough_index = -1

    for index, value in enumerate(values):
        equity += value
        if active_start is None:
            if equity >= peak:
                peak = equity
                continue
            active_start = index
            active_peak = peak
            active_trough = equity
            active_trough_index = index
            continue

        if equity < active_trough:
            active_trough = equity
            active_trough_index = index

        if equity >= active_peak:
            episodes.append(
                DrawdownEpisode(
                    episode_id=len(episodes) + 1,
                    peak_equity_r=str(active_peak),
                    trough_equity_r=str(active_trough),
                    max_drawdown_r=str(active_peak - active_trough),
                    start_index=active_start,
                    trough_index=active_trough_index,
                    end_index=index,
                    trade_count=index - active_start + 1,
                    descent_trade_count=active_trough_index - active_start + 1,
                    recovered_peak=True,
                )
            )
            peak = equity
            active_start = None

    if active_start is not None:
        episodes.append(
            DrawdownEpisode(
                episode_id=len(episodes) + 1,
                peak_equity_r=str(active_peak),
                trough_equity_r=str(active_trough),
                max_drawdown_r=str(active_peak - active_trough),
                start_index=active_start,
                trough_index=active_trough_index,
                end_index=len(values) - 1,
                trade_count=len(values) - active_start,
                descent_trade_count=active_trough_index - active_start + 1,
                recovered_peak=False,
            )
        )
    return tuple(episodes)


def _surface_ledger(
    *,
    period: str,
    ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
    contexts: dict[tuple[str, str], Any],
    contextual_model: dict[str, Any],
) -> tuple[
    dict[str, Any],
    tuple[milestone.SimulatedTrade, ...],
    dict[tuple[str, str], recovery_v18.TriggerDecision],
]:
    control, decisions = recovery_v18._simulate(
        period=period,
        policy="SURFACE_CONTROL",
        models=None,
        ledgers=ledgers,
        contexts=contexts,
        contextual_model=contextual_model,
    )
    by_mode = {
        mode: {(row.symbol, row.entry_at): row for row in rows}
        for mode, rows in ledgers.items()
    }
    decision_map = {(row.symbol, row.entry_at): row for row in decisions}
    original = _canonical_rows(
        ledgers[milestone.ProtectionMode.ORIGINAL.value]
    )
    if len(decision_map) != len(original):
        raise ValueError("feasibility audit Surface decision identity drift")

    rebuilt: list[milestone.SimulatedTrade] = []
    for trade in original:
        key = (trade.symbol, trade.entry_at)
        decision = decision_map[key]
        selected = by_mode[decision.surface_mode][key]
        rebuilt.append(
            replace(
                selected,
                realized_gross_r=str(
                    Decimal(selected.realized_gross_r)
                    * Decimal(decision.base_multiplier)
                ),
            )
        )

    ledger = tuple(rebuilt)
    if milestone._metrics(ledger) != control["metrics"]:
        raise ValueError("feasibility audit Surface reconstruction mismatch")
    return control, ledger, decision_map


def _best_existing_action(
    *,
    key: tuple[str, str],
    multiplier: Decimal,
    by_mode: dict[str, dict[tuple[str, str], milestone.SimulatedTrade]],
) -> tuple[str, milestone.SimulatedTrade, Decimal, tuple[Decimal, ...]]:
    candidates: list[tuple[Decimal, int, str, milestone.SimulatedTrade]] = []
    outcomes: list[Decimal] = []
    for order, mode in enumerate(ACTION_ORDER):
        row = by_mode[mode][key]
        value = Decimal(row.realized_gross_r) * multiplier
        outcomes.append(value)
        candidates.append((value, -order, mode, row))
    value, _tie, mode, row = max(candidates)
    return mode, row, value, tuple(outcomes)


def _active_peers(
    ledger: tuple[milestone.SimulatedTrade, ...],
    *,
    current: milestone.SimulatedTrade,
) -> tuple[milestone.SimulatedTrade, ...]:
    observed_at = milestone._aware(current.entry_at)
    return tuple(
        row
        for row in ledger
        if (row.symbol, row.entry_at) != (current.symbol, current.entry_at)
        and milestone._aware(row.entry_at) < observed_at
        and observed_at <= milestone._aware(row.exit_at)
    )


def _shared_factor_peers(
    peers: tuple[milestone.SimulatedTrade, ...],
    *,
    current: milestone.SimulatedTrade,
) -> int:
    factors = frozenset(
        v11._factor_map(symbol=current.symbol, side=current.side)
    )
    return sum(
        bool(
            factors
            & frozenset(v11._factor_map(symbol=row.symbol, side=row.side))
        )
        for row in peers
    )


def _period_report(
    *,
    period: str,
    ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
    contexts: dict[tuple[str, str], Any],
    contextual_model: dict[str, Any],
) -> tuple[
    dict[str, Any],
    tuple[DrawdownEpisode, ...],
    tuple[EpisodeTradeAudit, ...],
]:
    control, surface, decisions = _surface_ledger(
        period=period,
        ledgers=ledgers,
        contexts=contexts,
        contextual_model=contextual_model,
    )
    surface = _canonical_rows(surface)
    by_mode = {
        mode: {(row.symbol, row.entry_at): row for row in rows}
        for mode, rows in ledgers.items()
    }
    surface_values = tuple(Decimal(row.realized_gross_r) for row in surface)
    episodes = _drawdown_episodes(surface_values)
    if not episodes:
        raise ValueError("feasibility audit requires at least one DD episode")
    max_episode = max(
        episodes,
        key=lambda row: (Decimal(row.max_drawdown_r), -row.episode_id),
    )

    oracle_rows: list[milestone.SimulatedTrade] = []
    best_by_key: dict[
        tuple[str, str], tuple[str, Decimal, tuple[Decimal, ...]]
    ] = {}
    for surface_row in surface:
        key = (surface_row.symbol, surface_row.entry_at)
        decision = decisions[key]
        mode, raw, value, outcomes = _best_existing_action(
            key=key,
            multiplier=Decimal(decision.base_multiplier),
            by_mode=by_mode,
        )
        oracle_rows.append(replace(raw, realized_gross_r=str(value)))
        best_by_key[key] = (mode, value, outcomes)

    oracle = tuple(oracle_rows)
    oracle_metrics = milestone._metrics(oracle)
    if len(oracle) != len(surface):
        raise ValueError("feasibility outcome oracle lost entrants")

    max_episode_audits: list[EpisodeTradeAudit] = []
    no_trigger_loss_r = Decimal("0")
    trigger_reachable_loss_r = Decimal("0")
    oracle_delta_inside_episode = Decimal("0")
    overlap_rows = 0
    shared_factor_overlap_rows = 0

    for index in range(
        max_episode.start_index,
        max_episode.trough_index + 1,
    ):
        surface_row = surface[index]
        key = (surface_row.symbol, surface_row.entry_at)
        decision = decisions[key]
        original = by_mode[milestone.ProtectionMode.ORIGINAL.value][key]
        milestone_seen = Decimal(original.max_milestone_r_seen_before_exit)
        reached = milestone_seen >= FIRST_PROTECTION_MILESTONE_R
        surface_r = Decimal(surface_row.realized_gross_r)
        best_mode, best_r, outcomes = best_by_key[key]
        unique = tuple(sorted(set(outcomes)))
        delta = best_r - surface_r
        no_trigger = surface_r < 0 and not reached
        reachable_loss = surface_r < 0 and reached
        if no_trigger:
            no_trigger_loss_r += surface_r
        if reachable_loss:
            trigger_reachable_loss_r += surface_r
        oracle_delta_inside_episode += delta

        peers = _active_peers(surface, current=surface_row)
        shared = _shared_factor_peers(peers, current=surface_row)
        overlap_rows += int(bool(peers))
        shared_factor_overlap_rows += int(shared > 0)

        max_episode_audits.append(
            EpisodeTradeAudit(
                period=period,
                episode_id=max_episode.episode_id,
                sequence_index=index,
                symbol=surface_row.symbol,
                session=surface_row.session,
                operating_date=surface_row.operating_date,
                side=surface_row.side,
                entry_at=surface_row.entry_at,
                exit_at=surface_row.exit_at,
                surface_mode=decision.surface_mode,
                base_multiplier=decision.base_multiplier,
                surface_scaled_r=str(surface_r),
                surface_exit_reason=surface_row.exit_reason,
                original_max_milestone_r=str(milestone_seen),
                reached_first_protection_milestone=reached,
                no_trigger_loss=no_trigger,
                trigger_reachable_loss=reachable_loss,
                counterfactual_unique_outcomes=len(unique),
                counterfactual_range_r=str(max(unique) - min(unique)),
                best_existing_mode=best_mode,
                best_existing_scaled_r=str(best_r),
                best_existing_delta_r=str(delta),
                action_relevant=len(unique) > 1,
                loss_rescuable_to_nonnegative=surface_r < 0 and best_r >= 0,
                active_peer_count_at_entry=len(peers),
                shared_factor_peer_count_at_entry=shared,
            )
        )

    actionability_counts: Counter[str] = Counter()
    all_no_trigger_losses = 0
    all_trigger_reachable_losses = 0
    all_rescuable_losses = 0
    oracle_improvements = 0
    for surface_row in surface:
        key = (surface_row.symbol, surface_row.entry_at)
        original = by_mode[milestone.ProtectionMode.ORIGINAL.value][key]
        reached = (
            Decimal(original.max_milestone_r_seen_before_exit)
            >= FIRST_PROTECTION_MILESTONE_R
        )
        surface_r = Decimal(surface_row.realized_gross_r)
        _best_mode, best_r, outcomes = best_by_key[key]
        unique_count = len(set(outcomes))
        actionability_counts[str(unique_count)] += 1
        all_no_trigger_losses += int(surface_r < 0 and not reached)
        all_trigger_reachable_losses += int(surface_r < 0 and reached)
        all_rescuable_losses += int(surface_r < 0 and best_r >= 0)
        oracle_improvements += int(best_r > surface_r)

    surface_total = Decimal(control["metrics"]["total_r"])
    oracle_total = Decimal(oracle_metrics["total_r"])
    oracle_dd = Decimal(oracle_metrics["max_drawdown_r"])
    max_rows = tuple(max_episode_audits)
    max_losses = tuple(
        row for row in max_rows if Decimal(row.surface_scaled_r) < 0
    )

    return (
        {
            "period": period,
            "surface": control["metrics"],
            "outcome_oracle": oracle_metrics,
            "outcome_oracle_total_r_gain_vs_surface": str(
                oracle_total - surface_total
            ),
            "outcome_oracle_total_r_ratio_vs_surface": (
                None
                if surface_total == 0
                else str(oracle_total / surface_total)
            ),
            "outcome_oracle_dd_at_or_below_6r": oracle_dd <= Decimal("6"),
            "outcome_oracle_uses_future_information": True,
            "outcome_oracle_is_candidate": False,
            "episode_count": len(episodes),
            "max_drawdown_episode": asdict(max_episode),
            "max_episode_anatomy": {
                "scope": "PEAK_TO_TROUGH_ONLY",
                "descent_trade_count": max_episode.descent_trade_count,
                "recovery_tail_trade_count": (
                    max_episode.end_index - max_episode.trough_index
                ),
                "negative_trades": len(max_losses),
                "no_trigger_losses": sum(row.no_trigger_loss for row in max_rows),
                "no_trigger_loss_r": str(no_trigger_loss_r),
                "trigger_reachable_losses": sum(
                    row.trigger_reachable_loss for row in max_rows
                ),
                "trigger_reachable_loss_r": str(trigger_reachable_loss_r),
                "action_relevant_trades": sum(row.action_relevant for row in max_rows),
                "losses_rescuable_to_nonnegative": sum(
                    row.loss_rescuable_to_nonnegative for row in max_rows
                ),
                "trades_with_active_peer_at_entry": overlap_rows,
                "trades_with_shared_factor_peer_at_entry": (
                    shared_factor_overlap_rows
                ),
                "sum_best_existing_delta_r": str(oracle_delta_inside_episode),
                "symbols": dict(
                    sorted(Counter(row.symbol for row in max_rows).items())
                ),
                "sessions": dict(
                    sorted(Counter(row.session for row in max_rows).items())
                ),
            },
            "all_trade_actionability": {
                "unique_counterfactual_outcome_count_distribution": dict(
                    sorted(actionability_counts.items())
                ),
                "no_trigger_losses": all_no_trigger_losses,
                "trigger_reachable_losses": all_trigger_reachable_losses,
                "losses_rescuable_to_nonnegative": all_rescuable_losses,
                "trades_where_outcome_oracle_improves_surface": oracle_improvements,
            },
        },
        episodes,
        max_rows,
    )


def build_report(
    development_root: Path,
    validation_root: Path,
    reserved_root: Path,
    development_validation_context_root: Path,
    reserved_context_root: Path,
) -> tuple[
    dict[str, Any],
    tuple[tuple[str, DrawdownEpisode], ...],
    tuple[EpisodeTradeAudit, ...],
]:
    windows, contextual_model = v13._load_windows(
        development_root,
        validation_root,
        reserved_root,
        development_validation_context_root,
        reserved_context_root,
    )
    simultaneous: dict[
        tuple[str, str, str], tuple[milestone.SimulatedTrade, ...]
    ] = {}
    for period, (ledgers, _contexts) in windows.items():
        simultaneous.update(
            v11._simultaneous_map(period=period, ledgers=ledgers)
        )

    previous = dict(v11._SIMULTANEOUS)
    v11._SIMULTANEOUS.clear()
    v11._SIMULTANEOUS.update(simultaneous)
    try:
        results: list[dict[str, Any]] = []
        episode_rows: list[tuple[str, DrawdownEpisode]] = []
        max_episode_rows: list[EpisodeTradeAudit] = []
        for period, (ledgers, contexts) in windows.items():
            result, episodes, audits = _period_report(
                period=period,
                ledgers=ledgers,
                contexts=contexts,
                contextual_model=contextual_model,
            )
            results.append(result)
            episode_rows.extend((period, row) for row in episodes)
            max_episode_rows.extend(audits)
    finally:
        v11._SIMULTANEOUS.clear()
        v11._SIMULTANEOUS.update(previous)

    physical_capacity = all(
        bool(row["outcome_oracle_dd_at_or_below_6r"])
        and Decimal(row["outcome_oracle"]["total_r"])
        >= Decimal(row["surface"]["total_r"])
        for row in results
    )
    return (
        {
            "identity": IDENTITY,
            "evaluation": "PHYSICAL_FEASIBILITY_PLUS_SURFACE_EPISODE_ANATOMY",
            "first_protection_milestone_r": str(
                FIRST_PROTECTION_MILESTONE_R
            ),
            "existing_action_count": len(ACTION_ORDER),
            "existing_actions": list(ACTION_ORDER),
            "surface_chronology_rebuilt_causally": True,
            "surface_multiplier_path_preserved_for_oracle": True,
            "outcome_oracle_definition": (
                "PER_TRADE_MAX_REALIZED_R_AMONG_EXISTING_NINE_MODES_"
                "WITH_FIXED_SURFACE_MULTIPLIER"
            ),
            "outcome_oracle_future_information_used": True,
            "outcome_oracle_policy_candidate": False,
            "physical_position_management_capacity_confirmed": physical_capacity,
            "results": results,
            "all_entries_preserved": True,
            "density_retention": "1",
            "same_entrant_identities": True,
            "fixed_target_r": "2.00",
            "original_stop_geometry_preserved_at_entry": True,
            "new_protection_geometry_created": False,
            "admission_changed": False,
            "sizing_changed": False,
            "max3_preserved": True,
            "automatic_policy_promotion": False,
            "trader_certified": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "next_phase": (
                "MEASURE_CAUSAL_INFORMATION_FRONTIER_ON_ACTION_RELEVANT_EPISODE_STATES"
                if physical_capacity
                else "POSITION_MANAGEMENT_PHYSICAL_CAPACITY_FALSIFIED"
            ),
        },
        tuple(episode_rows),
        tuple(max_episode_rows),
    )


def write_report(
    report: dict[str, Any],
    episodes: tuple[tuple[str, DrawdownEpisode], ...],
    audits: tuple[EpisodeTradeAudit, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    stem = "capitalizer-portfolio-drawdown-feasibility-episode-anatomy-v1"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-episodes.jsonl").open(
        "w", encoding="utf-8"
    ) as handle:
        for period, episode in episodes:
            handle.write(
                json.dumps(
                    {"period": period, **asdict(episode)},
                    sort_keys=True,
                )
                + "\n"
            )
    with (output / f"{stem}-max-episode-trades.jsonl").open(
        "w", encoding="utf-8"
    ) as handle:
        for audit in audits:
            handle.write(json.dumps(asdict(audit), sort_keys=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("development_root", type=Path)
    parser.add_argument("validation_root", type=Path)
    parser.add_argument("reserved_root", type=Path)
    parser.add_argument("development_validation_context_root", type=Path)
    parser.add_argument("reserved_context_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    report, episodes, audits = build_report(
        args.development_root,
        args.validation_root,
        args.reserved_root,
        args.development_validation_context_root,
        args.reserved_context_root,
    )
    write_report(report, episodes, audits, args.output)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
