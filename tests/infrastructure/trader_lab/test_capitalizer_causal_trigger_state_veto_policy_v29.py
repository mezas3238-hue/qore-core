from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_causal_trigger_state_veto_policy_v29 as v29,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_r_milestone_protection_2r_v1 as milestone,
)
from qore.infrastructure.trader_lab import (
    capitalizer_regularized_causal_state_space_v25 as v25,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)


def _trade(
    *,
    mode: str = "ORIGINAL",
    first_protection_at: str | None = None,
) -> milestone.SimulatedTrade:
    return milestone.SimulatedTrade(
        symbol="EURUSD",
        session="LONDON",
        operating_date="2026-01-05",
        side="LONG",
        entry_at="2026-01-05T08:00:00+00:00",
        exit_at="2026-01-05T09:00:00+00:00",
        entry_price="100",
        original_stop_price="99",
        final_stop_price="99",
        target_price="102",
        realized_gross_r="1",
        exit_reason="TIME_EXIT",
        mode=mode,
        protection_updates=0,
        first_protection_at=first_protection_at,
        max_milestone_r_seen_before_exit="1",
        same_minute_stop_target_ambiguity=False,
    )


def _bar(
    minute: int,
    *,
    open_: str,
    high: str,
    low: str,
    close: str,
) -> CapitalizerM1Bar:
    opened = datetime(2026, 1, 5, 8, minute, tzinfo=UTC)
    return CapitalizerM1Bar(
        symbol="EURUSD",
        opened_at=opened,
        closed_at=opened + timedelta(minutes=1),
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=100,
        digits=5,
    )


def _model(intercept: float, dimension: int) -> v25.RidgeModel:
    return v25.RidgeModel(
        period="TRAIN",
        feature_mean=tuple(0.0 for _ in range(dimension)),
        feature_scale=tuple(1.0 for _ in range(dimension)),
        coefficients=(intercept, *tuple(0.0 for _ in range(dimension))),
        unique_training_trades=50,
        weighted_observations=50.0,
        feature_dimension=dimension,
        weighted_target_mean=intercept,
        weighted_training_rmse=0.1,
        coefficient_l2_norm=abs(intercept),
    )


def test_trajectory_vector_uses_completed_native_m1_path() -> None:
    trade = _trade()
    bars = [
        _bar(0, open_="100", high="100.20", low="99.90", close="100.10"),
        _bar(1, open_="100.10", high="100.55", low="100.00", close="100.40"),
        _bar(2, open_="100.40", high="100.60", low="100.25", close="100.30"),
    ]

    vector = v29._trajectory_vector(trade, bars)

    assert len(vector) == v29.TRAJECTORY_FEATURE_DIMENSION == 19
    assert vector[0] == 3.0
    assert vector[1] == 0.30
    assert vector[2] == 0.60
    assert vector[3] == 0.10
    assert vector[4] == 0.30
    assert vector[6] == 1.0
    assert vector[8] == 1.0
    assert vector[9] == 0.0
    assert vector[15] == 0.05


def test_veto_is_available_only_at_surface_first_activation() -> None:
    key = ("EURUSD", "2026-01-05T08:00:00+00:00")
    original = _trade()
    protected = _trade(
        mode="BE_AFTER_050",
        first_protection_at="2026-01-05T08:03:00+00:00",
    )
    modes = {
        milestone.ProtectionMode.ORIGINAL.value: {key: original},
        milestone.ProtectionMode.BE_AFTER_050.value: {key: protected},
    }

    assert v29._veto_eligible(
        key=key,
        surface_mode=milestone.ProtectionMode.BE_AFTER_050.value,
        trigger_at="2026-01-05T08:03:00+00:00",
        modes=modes,
    )
    assert not v29._veto_eligible(
        key=key,
        surface_mode=milestone.ProtectionMode.BE_AFTER_050.value,
        trigger_at="2026-01-05T08:04:00+00:00",
        modes=modes,
    )
    assert not v29._veto_eligible(
        key=key,
        surface_mode=milestone.ProtectionMode.ORIGINAL.value,
        trigger_at="2026-01-05T08:03:00+00:00",
        modes=modes,
    )


def test_robust_action_selector_can_choose_veto() -> None:
    features = (0.0, 0.0, 0.0)
    be_total = _model(0.20, len(features))
    be_downside = _model(0.10, len(features))
    veto_total_a = _model(0.50, len(features))
    veto_total_b = _model(0.40, len(features))
    veto_downside = _model(0.20, len(features))

    action, score, predictions = v29._choose_action(
        features=features,
        surface_mode="STAGED_050_100_150",
        actions=("BE_AFTER_050", v29.VETO_ACTION),
        model_a={
            "BE_AFTER_050": (be_total, be_downside),
            v29.VETO_ACTION: (veto_total_a, veto_downside),
        },
        model_b={
            "BE_AFTER_050": (be_total, be_downside),
            v29.VETO_ACTION: (veto_total_b, veto_downside),
        },
    )

    assert action == v29.VETO_ACTION
    assert score == 0.40
    assert predictions == (0.50, 0.40, 0.20, 0.20)


def test_v29_frozen_contract() -> None:
    assert v29.IDENTITY == "QORE_CAPITALIZER_CAUSAL_TRIGGER_STATE_VETO_POLICY_V29"
    assert v29.POLICY == "TRIGGER_STATE_ROBUST_POSDELTA_NONDOWNSIDE_WITH_VETO"
    assert v29.VETO_ACTION == "VETO_TO_ORIGINAL"
    assert v29.VETO_ACTION not in {mode.value for mode in milestone.ProtectionMode}
    assert v29.L2_PRIOR_STRENGTH == 12.0
    assert set(v29.FAMILIES) == {"TRIGGER_050", "TRIGGER_075", "TRIGGER_100"}
    assert v29.SOURCE_M1_RUN_ID == 35548099334
    assert v29.SOURCE_M1_SHA == "18c338aedd5013ce65a6cb6408ffbc2e904a6217"
