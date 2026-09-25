"""VT08 Index shadow falsification for Shared stop-vs-target discrimination.

Phase-1 only. This lab does NOT change stops, targets, sizing, entries, trade
count, market selection, or economics. It asks whether Shared can causally
separate possible terminal-stop paths from possible target-reaching paths
before the canonical VT08 outcome is known.

Realized outcome is read only after classification to score the shadow
hypothesis. All runtime classifications use bars closed by the assessment time.
"""
# ruff: noqa: E501
from __future__ import annotations

import argparse
import bisect
import json
from collections import Counter
from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from statistics import median

import vt08_index_shared_full_stack_no_sizing_v3 as v3

from qore.infrastructure.core_stack_v2.competing_risk_decision_gate import (
    CompetingRiskDecision,
    assess_competing_risk_decision,
)
from qore.infrastructure.core_stack_v2.competing_risk_path_core import (
    assess_competing_risk_path,
)
from qore.infrastructure.core_stack_v2.path_intelligence import (
    PositionPathObservation,
    assess_position_path,
)
from qore.infrastructure.core_stack_v2.recovery_failure_intelligence import (
    RecoveryChallengeState,
    assess_recovery_failure,
)
from qore.infrastructure.core_stack_v2.stop_target_discrimination import (
    StopTargetHypothesis,
    assess_stop_target_path,
)
from qore.infrastructure.core_stack_v2.terminal_failure_confirmation import (
    TerminalFailureState,
    assess_terminal_failure,
)

SCHEMA = "qore.shared.vt08_index.stop_target_discrimination.v6"
IDENTITY = "QORE_SHARED_VT08_INDEX_STOP_TARGET_DISCRIMINATION_V6"
ZERO = Decimal("0")
TARGET_R = Decimal("2.5")


def _clip(value: int) -> int:
    return max(0, min(10_000, int(value)))


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _signed_r(signal: object, price: Decimal) -> Decimal:
    risk = abs(_d(signal.entry) - _d(signal.stop))
    if risk <= ZERO:
        return ZERO
    if str(signal.side.value).lower() == "long":
        return (price - _d(signal.entry)) / risk
    return (_d(signal.entry) - price) / risk


def _path_observation(
    *,
    signal: object,
    bar: object,
    latest: object,
    environment: object,
    trajectory: object,
    max_mfe: Decimal,
    max_mae: Decimal,
) -> PositionPathObservation:
    risk = abs(_d(signal.entry) - _d(signal.stop))
    side = str(signal.side.value).lower()
    close_r = _signed_r(signal, _d(bar.close))
    body_r = (
        (_d(bar.close) - _d(bar.open)) / risk
        if side == "long"
        else (_d(bar.open) - _d(bar.close)) / risk
    )
    progress_bps = _clip(
        int(max(ZERO, max_mfe) / TARGET_R * Decimal(10_000))
    )
    return PositionPathObservation(
        as_of=bar.closed_at.astimezone(UTC),
        data_integrity_bps=latest.data_integrity_bps,
        journey_progress_bps=progress_bps,
        close_support_bps=_clip(int(Decimal(5_000) + close_r * Decimal(2_500))),
        directional_efficiency_bps=latest.momentum_bps,
        favorable_excursion_bps=progress_bps,
        adverse_excursion_bps=_clip(
            int(max(ZERO, max_mae) * Decimal(10_000))
        ),
        favorable_body_bps=_clip(
            int(max(ZERO, body_r) * Decimal(10_000))
        ),
        adverse_body_bps=_clip(
            int(max(ZERO, -body_r) * Decimal(10_000))
        ),
        market_support_bps=environment.market_support_bps,
        environment_adverse_bps=environment.adverse_environment_bps,
        recovery_evidence_bps=_clip(
            (
                trajectory.recovery_velocity_bps
                + environment.recovery_velocity_bps
            )
            // 2
        ),
    )


def _shadow_trade(
    item: object,
    *,
    bars_by_symbol: dict[str, Sequence[object]],
    closed_by_symbol: dict[str, tuple[datetime, ...]],
) -> dict[str, object]:
    signal = item.opportunity.signal
    symbol = str(signal.symbol)
    side = str(signal.side.value).lower()
    risk = abs(_d(signal.entry) - _d(signal.stop))
    terminal_r = _d(item.outcome.r_multiple)
    actual = "LOSS" if terminal_r < ZERO else "WIN" if terminal_r > ZERO else "FLAT"

    entry = v3._entry_assessment(
        item,
        bars_by_symbol=bars_by_symbol,
        closed_by_symbol=closed_by_symbol,
        closed_memory=(),
    )
    entry_shadow = assess_stop_target_path(
        entry["environment"],
        entry["trajectory"],
        entry["geometry"],
        entry["futures"],
    )
    entry_belief = assess_competing_risk_path(
        entry["environment"],
        entry["trajectory"],
        entry["geometry"],
        entry["futures"],
    )
    belief_history = [entry_belief]
    entry_gate = assess_competing_risk_decision(tuple(belief_history))
    entry_recovery = assess_recovery_failure(tuple(belief_history))

    all_bars = bars_by_symbol[symbol]
    closed = closed_by_symbol[symbol]
    start = bisect.bisect_right(closed, signal.signal_at.astimezone(UTC))
    # The canonical exit bar is excluded. If stop/target was touched
    # intrabar, its close is not causally available before the outcome.
    end = bisect.bisect_left(closed, item.exited_at.astimezone(UTC))
    observed = tuple(all_bars[start:end])

    path_history: list[PositionPathObservation] = []
    rows: list[dict[str, object]] = [
        {
            "stage": "ENTRY",
            "as_of": signal.signal_at.astimezone(UTC).isoformat(),
            "bar_index": 0,
            "bars_before_canonical_exit": len(observed),
            "hypothesis": entry_shadow.hypothesis.value,
            "agreement_bps": entry_shadow.structural_agreement_bps,
            "terminal_relations": entry_shadow.terminal_relation_count,
            "target_relations": entry_shadow.target_relation_count,
            "recovery_relations": entry_shadow.recovery_relation_count,
            "stop_pressure_bps": entry_belief.stop_pressure_bps,
            "stop_formation_bps": entry_belief.stop_formation_bps,
            "target_capacity_bps": entry_belief.target_capacity_bps,
            "recovery_strength_bps": entry_belief.recovery_strength_bps,
            "uncertainty_bps": entry_belief.uncertainty_bps,
            "stop_hazard_proxy_bps": entry_belief.stop_hazard_proxy_bps,
            "target_hazard_proxy_bps": entry_belief.target_hazard_proxy_bps,
            "risk_separation_margin_bps": entry_belief.separation_margin_bps,
            "ccrpc_decision": entry_gate.decision.value,
            "ccrpc_stop_persistence_bps": entry_gate.stop_persistence_bps,
            "ccrpc_stop_formation_persistence_bps": entry_gate.stop_formation_persistence_bps,
            "ccrpc_target_persistence_bps": entry_gate.target_persistence_bps,
            "ccrpc_recovery_persistence_bps": entry_gate.recovery_persistence_bps,
            "recovery_challenge_state": entry_recovery.state.value,
            "terminal_failure_state": TerminalFailureState.INSUFFICIENT.value,
            "recovery_challenge_observations": entry_recovery.observations_since_formation,
            "recovery_challenge_formation_persistence_bps": entry_recovery.formation_persistence_bps,
        }
    ]

    max_mfe = ZERO
    max_mae = ZERO
    if risk > ZERO:
        for idx, bar in enumerate(observed, start=1):
            if side == "long":
                max_mfe = max(max_mfe, (_d(bar.high) - _d(signal.entry)) / risk)
                max_mae = max(max_mae, (_d(signal.entry) - _d(bar.low)) / risk)
            else:
                max_mfe = max(max_mfe, (_d(signal.entry) - _d(bar.low)) / risk)
                max_mae = max(max_mae, (_d(bar.high) - _d(signal.entry)) / risk)

            as_of = bar.closed_at.astimezone(UTC)
            history = v3._history(
                item,
                bars_by_symbol=bars_by_symbol,
                closed_by_symbol=closed_by_symbol,
                as_of=as_of,
            )
            trajectory = v3._trajectory(history)
            environment = v3._environment(history)
            geometry = v3._geometry(history)
            futures = v3._competing_futures(history)
            latest = history[-1]
            path_history.append(
                _path_observation(
                    signal=signal,
                    bar=bar,
                    latest=latest,
                    environment=environment,
                    trajectory=trajectory,
                    max_mfe=max_mfe,
                    max_mae=max_mae,
                )
            )
            path = assess_position_path(
                tuple(path_history[-min(v3.PATH_WINDOW, len(path_history)):])
            )
            shadow = assess_stop_target_path(
                environment,
                trajectory,
                geometry,
                futures,
                path=path,
            )
            belief = assess_competing_risk_path(
                environment,
                trajectory,
                geometry,
                futures,
                path=path,
            )
            belief_history.append(belief)
            gate = assess_competing_risk_decision(tuple(belief_history))
            recovery_challenge = assess_recovery_failure(tuple(belief_history))
            terminal_failure = assess_terminal_failure(
                belief,
                path,
                recovery_challenge,
            )
            rows.append(
                {
                    "stage": "PATH",
                    "as_of": as_of.isoformat(),
                    "bar_index": idx,
                    "bars_before_canonical_exit": len(observed) - idx,
                    "hypothesis": shadow.hypothesis.value,
                    "agreement_bps": shadow.structural_agreement_bps,
                    "terminal_relations": shadow.terminal_relation_count,
                    "target_relations": shadow.target_relation_count,
                    "recovery_relations": shadow.recovery_relation_count,
                    "stop_pressure_bps": belief.stop_pressure_bps,
                    "stop_formation_bps": belief.stop_formation_bps,
                    "target_capacity_bps": belief.target_capacity_bps,
                    "recovery_strength_bps": belief.recovery_strength_bps,
                    "uncertainty_bps": belief.uncertainty_bps,
                    "stop_hazard_proxy_bps": belief.stop_hazard_proxy_bps,
                    "target_hazard_proxy_bps": belief.target_hazard_proxy_bps,
                    "risk_separation_margin_bps": belief.separation_margin_bps,
                    "ccrpc_decision": gate.decision.value,
                    "ccrpc_stop_persistence_bps": gate.stop_persistence_bps,
                    "ccrpc_stop_formation_persistence_bps": gate.stop_formation_persistence_bps,
                    "ccrpc_target_persistence_bps": gate.target_persistence_bps,
                    "ccrpc_recovery_persistence_bps": gate.recovery_persistence_bps,
                    "recovery_challenge_state": recovery_challenge.state.value,
                    "terminal_failure_state": terminal_failure.state.value,
                    "terminal_failure_stop_formation_bps": terminal_failure.stop_formation_bps,
                    "terminal_failure_path_risk_bps": terminal_failure.terminal_failure_bps,
                    "terminal_failure_adverse_dominance_bps": terminal_failure.adverse_dominance_bps,
                    "terminal_failure_target_hazard_bps": terminal_failure.target_hazard_bps,
                    "terminal_failure_uncertainty_bps": terminal_failure.uncertainty_bps,
                    "recovery_challenge_observations": recovery_challenge.observations_since_formation,
                    "recovery_challenge_formation_persistence_bps": recovery_challenge.formation_persistence_bps,
                    "path_state": path.state.value,
                    "path_evidence_count": path.evidence_count,
                    "path_support_bps": path.path_support_bps,
                    "path_adverse_dominance_bps": path.adverse_dominance_bps,
                    "path_adverse_persistence_bps": path.adverse_persistence_bps,
                    "path_recovery_persistence_bps": path.recovery_persistence_bps,
                    "path_winner_protection_bps": path.winner_protection_bps,
                    "path_terminal_failure_risk_bps": path.terminal_failure_risk_bps,
                    "trajectory_state": trajectory.state.value,
                    "trajectory_support_bps": trajectory.support_bps,
                    "trajectory_adversity_bps": trajectory.adversity_bps,
                    "trajectory_deterioration_pressure_bps": trajectory.deterioration_pressure_bps,
                    "trajectory_deterioration_velocity_bps": trajectory.deterioration_velocity_bps,
                    "trajectory_recovery_velocity_bps": trajectory.recovery_velocity_bps,
                    "trajectory_deterioration_persistence_bps": trajectory.deterioration_persistence_bps,
                    "trajectory_recovery_persistence_bps": trajectory.recovery_persistence_bps,
                    "environment_state": environment.state.value,
                    "environment_support_bps": environment.market_support_bps,
                    "environment_adverse_bps": environment.adverse_environment_bps,
                    "environment_adverse_velocity_bps": environment.adverse_velocity_bps,
                    "environment_recovery_velocity_bps": environment.recovery_velocity_bps,
                    "environment_adverse_persistence_bps": environment.adverse_persistence_bps,
                    "environment_recovery_persistence_bps": environment.recovery_persistence_bps,
                    "geometry_state": geometry.state.value,
                    "geometry_structural_agreement_bps": geometry.structural_agreement_bps,
                    "geometry_collapse_horizon_count": geometry.collapse_horizon_count,
                    "geometry_recovery_horizon_count": geometry.recovery_horizon_count,
                    "geometry_resilient_horizon_count": geometry.resilient_horizon_count,
                    "futures_state": futures.state.value,
                    "futures_terminal_evidence_bps": futures.terminal_evidence_bps,
                    "futures_recovery_evidence_bps": futures.recovery_evidence_bps,
                    "futures_separation_margin_bps": futures.separation_margin_bps,
                    "futures_horizon_agreement_bps": futures.horizon_agreement_bps,
                }
            )

    decisive = [
        row
        for row in rows
        if row["hypothesis"]
        in {
            StopTargetHypothesis.STOP_LIKELY.value,
            StopTargetHypothesis.TARGET_LIKELY.value,
        }
    ]
    first_decisive = None if not decisive else decisive[0]
    first_stop_forming = next(
        (
            row
            for row in rows
            if row["hypothesis"] == StopTargetHypothesis.STOP_FORMING.value
        ),
        None,
    )
    first_stop = next(
        (
            row
            for row in rows
            if row["hypothesis"] == StopTargetHypothesis.STOP_LIKELY.value
        ),
        None,
    )
    first_target = next(
        (
            row
            for row in rows
            if row["hypothesis"] == StopTargetHypothesis.TARGET_LIKELY.value
        ),
        None,
    )
    first_ccrpc_stop_forming = next(
        (
            row
            for row in rows
            if row["ccrpc_decision"] == CompetingRiskDecision.STOP_FORMING.value
        ),
        None,
    )
    first_ccrpc_stop = next(
        (
            row
            for row in rows
            if row["ccrpc_decision"] == CompetingRiskDecision.STOP_LIKELY.value
        ),
        None,
    )
    first_ccrpc_target = next(
        (
            row
            for row in rows
            if row["ccrpc_decision"] == CompetingRiskDecision.TARGET_LIKELY.value
        ),
        None,
    )
    first_recovery_failed = next(
        (
            row
            for row in rows
            if row["recovery_challenge_state"] == RecoveryChallengeState.RECOVERY_FAILED.value
        ),
        None,
    )
    first_recovery_restored = next(
        (
            row
            for row in rows
            if row["recovery_challenge_state"] == RecoveryChallengeState.RECOVERY_RESTORED.value
        ),
        None,
    )
    first_terminal_confirmed = next(
        (
            row
            for row in rows
            if row["terminal_failure_state"]
            == TerminalFailureState.TERMINAL_CONFIRMED.value
        ),
        None,
    )

    return {
        "trade_id": item.trade_id,
        "market": symbol,
        "signal_at": signal.signal_at.astimezone(UTC).isoformat(),
        "exited_at": item.exited_at.astimezone(UTC).isoformat(),
        "terminal_r": str(terminal_r),
        "actual": actual,
        "entry_hypothesis": entry_shadow.hypothesis.value,
        "first_decisive": first_decisive,
        "first_stop_forming": first_stop_forming,
        "first_stop": first_stop,
        "first_target": first_target,
        "first_ccrpc_stop_forming": first_ccrpc_stop_forming,
        "first_ccrpc_stop": first_ccrpc_stop,
        "first_ccrpc_target": first_ccrpc_target,
        "first_recovery_failed": first_recovery_failed,
        "first_recovery_restored": first_recovery_restored,
        "first_terminal_confirmed": first_terminal_confirmed,
        "hypothesis_counts": dict(
            sorted(Counter(str(row["hypothesis"]) for row in rows).items())
        ),
        "ccrpc_decision_counts": dict(
            sorted(Counter(str(row["ccrpc_decision"]) for row in rows).items())
        ),
        "recovery_challenge_counts": dict(
            sorted(
                Counter(str(row["recovery_challenge_state"]) for row in rows).items()
            )
        ),
        "terminal_failure_counts": dict(
            sorted(
                Counter(str(row["terminal_failure_state"]) for row in rows).items()
            )
        ),
        "competing_risk_summary": {
            "max_stop_hazard_proxy_bps": max(
                int(row["stop_hazard_proxy_bps"]) for row in rows
            ),
            "max_stop_formation_bps": max(
                int(row["stop_formation_bps"]) for row in rows
            ),
            "max_target_hazard_proxy_bps": max(
                int(row["target_hazard_proxy_bps"]) for row in rows
            ),
            "max_recovery_strength_bps": max(
                int(row["recovery_strength_bps"]) for row in rows
            ),
            "min_uncertainty_bps": min(
                int(row["uncertainty_bps"]) for row in rows
            ),
            "max_separation_margin_bps": max(
                int(row["risk_separation_margin_bps"]) for row in rows
            ),
        },
        "observations": rows,
    }


def _safe_ratio(numerator: int, denominator: int) -> str:
    if denominator <= 0:
        return "0"
    return str(Decimal(numerator) / Decimal(denominator))


def _window(
    *,
    roots: dict[str, Path],
    window_id: str,
) -> dict[str, object]:
    source_window_id = {
        "five_year": "5Y",
        "recent_two_year": "2Y",
        "r66_consumed_failed_holdout": "R66",
    }[window_id]
    canonical, bars_raw, provenance = v3.v2.r74._load_window(
        roots=roots,
        window_id=source_window_id,
    )
    start_date, end_date, expected = v3.v2.r74._window_contract(source_window_id)
    bars_by_symbol = {
        symbol: tuple(rows)
        for symbol, rows in bars_raw.items()
    }
    opened_by_symbol = {
        symbol: tuple(bar.opened_at.astimezone(UTC) for bar in rows)
        for symbol, rows in bars_by_symbol.items()
    }
    closed_by_symbol = {
        symbol: tuple(bar.closed_at.astimezone(UTC) for bar in rows)
        for symbol, rows in bars_by_symbol.items()
    }
    base, _ = v3.v2.r58._exact_r47(
        tuple(canonical),
        bars_by_symbol=bars_by_symbol,
    )
    control, _ = v3.v2.r102._apply_confidence_policy(
        tuple(base),
        bars_by_symbol=bars_by_symbol,
        policy_id=v3.v2.r102.POLICY_EXPLICIT_FULL,
    )
    control = v3.v2._unitize(tuple(control))
    if len(control) != expected:
        raise ValueError(f"VT08 Shared stop-target {window_id} density drift")

    rows = tuple(
        _shadow_trade(
            item,
            bars_by_symbol=bars_by_symbol,
            closed_by_symbol=closed_by_symbol,
        )
        for item in control
    )
    baseline = v3.v2.r108._bundle(
        control,
        bars_by_symbol=bars_by_symbol,
        opened_by_symbol=opened_by_symbol,
        window_id=source_window_id,
        start_date=start_date,
        end_date=end_date,
    )

    losses = [row for row in rows if row["actual"] == "LOSS"]
    winners = [row for row in rows if row["actual"] == "WIN"]
    decisive = [row for row in rows if row["first_decisive"] is not None]
    predicted_stop = [
        row
        for row in decisive
        if row["first_decisive"]["hypothesis"]
        == StopTargetHypothesis.STOP_LIKELY.value
    ]
    predicted_target = [
        row
        for row in decisive
        if row["first_decisive"]["hypothesis"]
        == StopTargetHypothesis.TARGET_LIKELY.value
    ]
    true_stop = [row for row in predicted_stop if row["actual"] == "LOSS"]
    false_stop = [row for row in predicted_stop if row["actual"] == "WIN"]
    true_target = [row for row in predicted_target if row["actual"] == "WIN"]
    false_target = [row for row in predicted_target if row["actual"] == "LOSS"]
    stop_forming = [row for row in rows if row["first_stop_forming"] is not None]
    true_stop_forming = [row for row in stop_forming if row["actual"] == "LOSS"]
    false_stop_forming = [row for row in stop_forming if row["actual"] == "WIN"]
    losses_detected = [row for row in losses if row["first_stop"] is not None]
    losses_forming = [row for row in losses if row["first_stop_forming"] is not None]
    winners_detected = [row for row in winners if row["first_target"] is not None]
    winner_false_stop_any = [row for row in winners if row["first_stop"] is not None]
    loss_false_target_any = [row for row in losses if row["first_target"] is not None]

    ccrpc_stop_forming = [
        row for row in rows if row["first_ccrpc_stop_forming"] is not None
    ]
    ccrpc_forming_losses = [row for row in ccrpc_stop_forming if row["actual"] == "LOSS"]
    ccrpc_forming_winners = [row for row in ccrpc_stop_forming if row["actual"] == "WIN"]
    ccrpc_predicted_stop = [row for row in rows if row["first_ccrpc_stop"] is not None]
    ccrpc_predicted_target = [row for row in rows if row["first_ccrpc_target"] is not None]
    ccrpc_true_stop = [row for row in ccrpc_predicted_stop if row["actual"] == "LOSS"]
    ccrpc_false_stop = [row for row in ccrpc_predicted_stop if row["actual"] == "WIN"]
    ccrpc_true_target = [row for row in ccrpc_predicted_target if row["actual"] == "WIN"]
    ccrpc_false_target = [row for row in ccrpc_predicted_target if row["actual"] == "LOSS"]
    recovery_failed = [row for row in rows if row["first_recovery_failed"] is not None]
    recovery_failed_losses = [row for row in recovery_failed if row["actual"] == "LOSS"]
    recovery_failed_winners = [row for row in recovery_failed if row["actual"] == "WIN"]
    recovery_restored_winners = [
        row for row in winners if row["first_recovery_restored"] is not None
    ]
    terminal_confirmed = [
        row for row in rows if row["first_terminal_confirmed"] is not None
    ]
    terminal_confirmed_losses = [
        row for row in terminal_confirmed if row["actual"] == "LOSS"
    ]
    terminal_confirmed_winners = [
        row for row in terminal_confirmed if row["actual"] == "WIN"
    ]

    stop_forming_leads = [
        int(row["first_stop_forming"]["bars_before_canonical_exit"])
        for row in losses_forming
    ]
    loss_stop_hazards = [
        int(row["competing_risk_summary"]["max_stop_hazard_proxy_bps"])
        for row in losses
    ]
    winner_stop_hazards = [
        int(row["competing_risk_summary"]["max_stop_hazard_proxy_bps"])
        for row in winners
    ]
    winner_target_hazards = [
        int(row["competing_risk_summary"]["max_target_hazard_proxy_bps"])
        for row in winners
    ]
    loss_target_hazards = [
        int(row["competing_risk_summary"]["max_target_hazard_proxy_bps"])
        for row in losses
    ]
    winner_recovery = [
        int(row["competing_risk_summary"]["max_recovery_strength_bps"])
        for row in winners
    ]
    loss_recovery = [
        int(row["competing_risk_summary"]["max_recovery_strength_bps"])
        for row in losses
    ]

    ccrpc_forming_leads = [
        int(row["first_ccrpc_stop_forming"]["bars_before_canonical_exit"])
        for row in ccrpc_forming_losses
    ]
    recovery_failed_leads = [
        int(row["first_recovery_failed"]["bars_before_canonical_exit"])
        for row in recovery_failed_losses
    ]
    terminal_confirmed_leads = [
        int(row["first_terminal_confirmed"]["bars_before_canonical_exit"])
        for row in terminal_confirmed_losses
    ]
    stop_leads = [
        int(row["first_stop"]["bars_before_canonical_exit"])
        for row in losses_detected
    ]
    target_leads = [
        int(row["first_target"]["bars_before_canonical_exit"])
        for row in winners_detected
    ]

    return {
        "window_id": window_id,
        "sample": len(rows),
        "canonical_expected": expected,
        "density_retained_shadow": "1",
        "baseline": baseline,
        "phase_1_contract": {
            "shadow_only": True,
            "stop_mutation_used": False,
            "target_mutation_used": False,
            "trailing_used": False,
            "target_extension_used": False,
            "sizing_used": False,
            "risk_weighting_used": False,
            "signal_suppression_used": False,
            "future_outcome_input_used": False,
            "realized_outcome_used_for_scoring_only": True,
            "canonical_exit_bar_excluded_from_runtime_classification": True,
        },
        "discrimination": {
            "losses": len(losses),
            "winners": len(winners),
            "decisive_trades": len(decisive),
            "decisive_coverage": _safe_ratio(len(decisive), len(rows)),
            "stop_forming_trades": len(stop_forming),
            "stop_forming_true_loss": len(true_stop_forming),
            "stop_forming_false_winner": len(false_stop_forming),
            "stop_forming_precision": _safe_ratio(
                len(true_stop_forming),
                len(stop_forming),
            ),
            "loss_stop_forming_recall": _safe_ratio(
                len(losses_forming),
                len(losses),
            ),
            "winner_false_stop_forming_rate_anytime": _safe_ratio(
                len(false_stop_forming),
                len(winners),
            ),
            "median_stop_forming_lead_bars": (
                None if not stop_forming_leads else str(median(stop_forming_leads))
            ),
            "predicted_stop": len(predicted_stop),
            "predicted_target": len(predicted_target),
            "stop_true_positive": len(true_stop),
            "stop_false_positive": len(false_stop),
            "stop_precision": _safe_ratio(len(true_stop), len(predicted_stop)),
            "loss_stop_recall": _safe_ratio(len(losses_detected), len(losses)),
            "target_true_positive": len(true_target),
            "target_false_positive": len(false_target),
            "target_precision": _safe_ratio(len(true_target), len(predicted_target)),
            "winner_target_recall": _safe_ratio(len(winners_detected), len(winners)),
            "winner_false_stop_rate_anytime": _safe_ratio(
                len(winner_false_stop_any),
                len(winners),
            ),
            "loss_false_target_rate_anytime": _safe_ratio(
                len(loss_false_target_any),
                len(losses),
            ),
            "median_stop_lead_bars": None if not stop_leads else str(median(stop_leads)),
            "median_target_lead_bars": None if not target_leads else str(median(target_leads)),
        },
        "competing_risk_diagnostics": {
            "calibrated_probability": False,
            "management_authority": False,
            "stop_forming_count": len(ccrpc_stop_forming),
            "stop_forming_loss_recall": _safe_ratio(
                len(ccrpc_forming_losses), len(losses)
            ),
            "stop_forming_winner_mark_rate": _safe_ratio(
                len(ccrpc_forming_winners), len(winners)
            ),
            "stop_forming_precision_for_diagnostics_only": _safe_ratio(
                len(ccrpc_forming_losses), len(ccrpc_stop_forming)
            ),
            "median_stop_forming_lead_bars": (
                None
                if not ccrpc_forming_leads
                else str(median(ccrpc_forming_leads))
            ),
            "recovery_failed_count": len(recovery_failed),
            "recovery_failed_loss_recall": _safe_ratio(
                len(recovery_failed_losses), len(losses)
            ),
            "recovery_failed_winner_mark_rate": _safe_ratio(
                len(recovery_failed_winners), len(winners)
            ),
            "recovery_failed_precision_for_diagnostics_only": _safe_ratio(
                len(recovery_failed_losses), len(recovery_failed)
            ),
            "median_recovery_failed_lead_bars": (
                None
                if not recovery_failed_leads
                else str(median(recovery_failed_leads))
            ),
            "winners_with_recovery_restored": len(recovery_restored_winners),
            "terminal_confirmed_count": len(terminal_confirmed),
            "terminal_confirmed_loss_recall": _safe_ratio(
                len(terminal_confirmed_losses), len(losses)
            ),
            "terminal_confirmed_winner_mark_rate": _safe_ratio(
                len(terminal_confirmed_winners), len(winners)
            ),
            "terminal_confirmed_precision_for_diagnostics_only": _safe_ratio(
                len(terminal_confirmed_losses), len(terminal_confirmed)
            ),
            "median_terminal_confirmed_lead_bars": (
                None
                if not terminal_confirmed_leads
                else str(median(terminal_confirmed_leads))
            ),
            "confirmed_stop_count": len(ccrpc_predicted_stop),
            "confirmed_stop_precision": _safe_ratio(
                len(ccrpc_true_stop), len(ccrpc_predicted_stop)
            ),
            "confirmed_stop_false_positive_rate_on_winners": _safe_ratio(
                len(ccrpc_false_stop), len(winners)
            ),
            "confirmed_target_count": len(ccrpc_predicted_target),
            "confirmed_target_precision": _safe_ratio(
                len(ccrpc_true_target), len(ccrpc_predicted_target)
            ),
            "confirmed_target_false_positive_rate_on_losses": _safe_ratio(
                len(ccrpc_false_target), len(losses)
            ),
            "median_max_stop_hazard_loss_bps": (
                None if not loss_stop_hazards else str(median(loss_stop_hazards))
            ),
            "median_max_stop_hazard_win_bps": (
                None if not winner_stop_hazards else str(median(winner_stop_hazards))
            ),
            "median_max_target_hazard_win_bps": (
                None if not winner_target_hazards else str(median(winner_target_hazards))
            ),
            "median_max_target_hazard_loss_bps": (
                None if not loss_target_hazards else str(median(loss_target_hazards))
            ),
            "median_max_recovery_win_bps": (
                None if not winner_recovery else str(median(winner_recovery))
            ),
            "median_max_recovery_loss_bps": (
                None if not loss_recovery else str(median(loss_recovery))
            ),
        },
        "entry_hypothesis_counts": dict(
            sorted(Counter(str(row["entry_hypothesis"]) for row in rows).items())
        ),
        "rows": list(rows),
        "provenance": provenance,
    }


def run(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, object]:
    roots = {
        "NAS100": nas100_root,
        "SP500": sp500_root,
        "US30": us30_root,
    }
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "challenge": {
            "source_pr": 604,
            "source_head": v3.VT08_HEAD,
            "shared_is_only_cognitive_engine": True,
            "vt08_role": "METHODOLOGY_VALID_FALSIFICATION_SURFACE_ONLY",
            "vt08_cognition_used_by_shared": False,
            "vt31_cognition_used_by_shared": False,
            "phase": "PHASE_1_NATURAL_DD_DISCRIMINATION",
            "management_actuation_forbidden": True,
            "stop_target_discrimination_required": True,
            "same_opportunity_universe": True,
            "same_initial_position_size": True,
            "sizing_used": False,
        },
        "five_year": _window(roots=roots, window_id="five_year"),
        "recent_two_year": _window(roots=roots, window_id="recent_two_year"),
        "r66_consumed_failed_holdout": _window(
            roots=roots,
            window_id="r66_consumed_failed_holdout",
        ),
        "governance": {
            "research_only": True,
            "consumed_evidence_only": True,
            "fresh_holdout_opened": False,
            "trailing_used": False,
            "target_extension_used": False,
            "sizing_used": False,
            "live_authorized": False,
            "production_authorized": False,
            "real_capital_authorized": False,
            "merge_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nas100-root", type=Path, required=True)
    parser.add_argument("--sp500-root", type=Path, required=True)
    parser.add_argument("--us30-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    payload = run(
        nas100_root=args.nas100_root,
        sp500_root=args.sp500_root,
        us30_root=args.us30_root,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(v3._jsonable(payload), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "identity": payload["identity"],
                "five_year": payload["five_year"]["discrimination"],
                "recent_two_year": payload["recent_two_year"]["discrimination"],
                "r66": payload["r66_consumed_failed_holdout"]["discrimination"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
