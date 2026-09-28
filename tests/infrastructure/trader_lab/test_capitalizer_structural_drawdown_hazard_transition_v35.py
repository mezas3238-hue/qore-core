from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_r_milestone_protection_2r_v1 as milestone,
)
from qore.infrastructure.trader_lab import (
    capitalizer_regularized_causal_state_space_v25 as v25,
)
from qore.infrastructure.trader_lab import (
    capitalizer_structural_drawdown_hazard_transition_v35 as v35,
)


def _trade(
    *,
    symbol: str,
    entry_at: str,
    exit_at: str,
    realized_r: str,
) -> milestone.SimulatedTrade:
    return milestone.SimulatedTrade(
        symbol=symbol,
        session="NEW_YORK",
        operating_date=entry_at[:10],
        side="LONG",
        entry_at=entry_at,
        exit_at=exit_at,
        entry_price="100",
        original_stop_price="99",
        final_stop_price="99",
        target_price="102",
        realized_gross_r=realized_r,
        exit_reason="TARGET" if Decimal(realized_r) > 0 else "STOP",
        mode="ORIGINAL",
        protection_updates=0,
        first_protection_at=None,
        max_milestone_r_seen_before_exit="0",
        same_minute_stop_target_ambiguity=False,
    )


def _constant_head(value: float, residual: float = 0.0) -> v35.CalibratedHead:
    model = v25.RidgeModel(
        period="TEST",
        feature_mean=(0.0,),
        feature_scale=(1.0,),
        coefficients=(value, 0.0),
        unique_training_trades=20,
        weighted_observations=20.0,
        feature_dimension=1,
        weighted_target_mean=value,
        weighted_training_rmse=0.0,
        coefficient_l2_norm=0.0,
    )
    return v35.CalibratedHead(
        model=model,
        residual_quantile=residual,
        chronological_residual_count=10,
    )


def _heads(
    *,
    hazard: float,
    severity: float,
    total: float,
) -> v35.HazardActionHeads:
    return v35.HazardActionHeads(
        deepening_hazard=_constant_head(hazard),
        additional_trough=_constant_head(severity),
        total_delta=_constant_head(total),
    )


def test_first_passage_target_detects_deeper_trough_before_recovery() -> None:
    control = (
        _trade(
            symbol="A",
            entry_at="2026-01-01T09:00:00+00:00",
            exit_at="2026-01-01T09:10:00+00:00",
            realized_r="2",
        ),
        _trade(
            symbol="B",
            entry_at="2026-01-01T09:20:00+00:00",
            exit_at="2026-01-01T09:30:00+00:00",
            realized_r="-1",
        ),
        _trade(
            symbol="C",
            entry_at="2026-01-01T09:40:00+00:00",
            exit_at="2026-01-01T10:30:00+00:00",
            realized_r="-1",
        ),
        _trade(
            symbol="D",
            entry_at="2026-01-01T10:00:00+00:00",
            exit_at="2026-01-01T11:00:00+00:00",
            realized_r="3",
        ),
    )
    key = ("C", "2026-01-01T09:40:00+00:00")
    target = v35._first_passage_target(
        control,
        key=key,
        trigger_at="2026-01-01T10:00:00+00:00",
        counterfactual=control[2],
    )

    assert target.deepens_before_recovery is True
    assert target.additional_trough_r == "1"
    assert target.recovered_peak is True
    assert target.terminal_event == "DEEPEN_TROUGH"


def test_first_passage_alternative_can_avoid_deepening() -> None:
    control = (
        _trade(
            symbol="A",
            entry_at="2026-01-01T09:00:00+00:00",
            exit_at="2026-01-01T09:10:00+00:00",
            realized_r="2",
        ),
        _trade(
            symbol="B",
            entry_at="2026-01-01T09:20:00+00:00",
            exit_at="2026-01-01T09:30:00+00:00",
            realized_r="-1",
        ),
        _trade(
            symbol="C",
            entry_at="2026-01-01T09:40:00+00:00",
            exit_at="2026-01-01T10:30:00+00:00",
            realized_r="-1",
        ),
        _trade(
            symbol="D",
            entry_at="2026-01-01T10:00:00+00:00",
            exit_at="2026-01-01T11:00:00+00:00",
            realized_r="2",
        ),
    )
    alternative = _trade(
        symbol="C",
        entry_at="2026-01-01T09:40:00+00:00",
        exit_at="2026-01-01T10:30:00+00:00",
        realized_r="0",
    )
    target = v35._first_passage_target(
        control,
        key=("C", "2026-01-01T09:40:00+00:00"),
        trigger_at="2026-01-01T10:00:00+00:00",
        counterfactual=alternative,
    )

    assert target.deepens_before_recovery is False
    assert target.additional_trough_r == "0"
    assert target.recovered_peak is True


def test_dual_world_gate_requires_strict_hazard_and_severity_dominance() -> None:
    surface = milestone.ProtectionMode.BE_AFTER_050.value
    alternative = milestone.ProtectionMode.BE_AFTER_075.value
    models_a = {
        surface: _heads(hazard=0.70, severity=1.5, total=0.0),
        alternative: _heads(hazard=0.40, severity=0.8, total=0.2),
    }
    models_b = {
        surface: _heads(hazard=0.65, severity=1.4, total=0.0),
        alternative: _heads(hazard=0.45, severity=0.9, total=0.1),
    }

    chosen, values, state = v35._choose_action(
        features=(0.0,),
        surface_mode=surface,
        actions=(surface, alternative),
        model_a=models_a,
        model_b=models_b,
    )

    assert chosen == alternative
    assert values is not None
    assert state == "WELL_SUPPORTED"


def test_dual_world_disagreement_keeps_surface() -> None:
    surface = milestone.ProtectionMode.BE_AFTER_050.value
    alternative = milestone.ProtectionMode.BE_AFTER_075.value
    models_a = {
        surface: _heads(hazard=0.70, severity=1.5, total=0.0),
        alternative: _heads(hazard=0.40, severity=0.8, total=0.2),
    }
    models_b = {
        surface: _heads(hazard=0.65, severity=1.4, total=0.0),
        alternative: _heads(hazard=0.80, severity=0.9, total=0.1),
    }

    chosen, values, state = v35._choose_action(
        features=(0.0,),
        surface_mode=surface,
        actions=(surface, alternative),
        model_a=models_a,
        model_b=models_b,
    )

    assert chosen is None
    assert values is None
    assert state == "CONFLICTED"


def test_negative_value_lower_bound_vetoes_tail_override() -> None:
    surface = milestone.ProtectionMode.BE_AFTER_050.value
    alternative = milestone.ProtectionMode.BE_AFTER_075.value
    models_a = {
        surface: _heads(hazard=0.70, severity=1.5, total=0.0),
        alternative: _heads(hazard=0.40, severity=0.8, total=-0.01),
    }
    models_b = {
        surface: _heads(hazard=0.65, severity=1.4, total=0.0),
        alternative: _heads(hazard=0.45, severity=0.9, total=0.1),
    }

    chosen, _values, state = v35._choose_action(
        features=(0.0,),
        surface_mode=surface,
        actions=(surface, alternative),
        model_a=models_a,
        model_b=models_b,
    )

    assert chosen is None
    assert state == "CONFLICTED"
