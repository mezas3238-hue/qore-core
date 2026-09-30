from qore.infrastructure.trader_lab.capitalizer_high_frequency_identity_v49 import (
    LAYERS,
    V49_HIGH_FREQUENCY_SCALPER_IDENTITY,
    V49LayerRole,
    V49Timeframe,
)


def test_v49_stack_is_exactly_h1_m15_m1() -> None:
    assert tuple(layer.timeframe for layer in LAYERS) == (
        V49Timeframe.H1,
        V49Timeframe.M15,
        V49Timeframe.M1,
    )
    assert tuple(layer.role for layer in LAYERS) == (
        V49LayerRole.CONTEXT_STATE,
        V49LayerRole.SETUP_FORMATION,
        V49LayerRole.EXECUTION_TRIGGER,
    )


def test_daily_and_h4_are_forbidden_as_scalper_decision_layers() -> None:
    state = V49_HIGH_FREQUENCY_SCALPER_IDENTITY
    assert state.daily_decision_layer_allowed is False
    assert state.h4_decision_layer_allowed is False


def test_h1_context_is_reusable_for_high_frequency_intraday_opportunities() -> None:
    state = V49_HIGH_FREQUENCY_SCALPER_IDENTITY
    assert state.h1_signal_consumed_after_one_trade is False
    assert state.multiple_m15_setups_per_h1_state_allowed is True
    assert state.multiple_m1_opportunities_per_h1_state_allowed is True


def test_max3_is_ceiling_and_v49_has_no_deployment_authority() -> None:
    state = V49_HIGH_FREQUENCY_SCALPER_IDENTITY
    assert state.max_executions_per_session == 3
    assert state.max3_is_quota is False
    assert state.outcome_aware_candidate_selection_allowed is False
    assert state.fresh_holdout_authorized is False
    assert state.economics_authorized is False
    assert state.live_authorized is False
    assert state.real_capital_authorized is False
