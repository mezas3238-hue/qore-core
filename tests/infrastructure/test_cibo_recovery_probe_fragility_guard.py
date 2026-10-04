from qore.infrastructure.cibo_recovery_probe_fragility_guard import (
    evaluate_recovery_probe_fragility,
)


def test_recovery_fragility_guard_rejects_extreme_m5_volatility() -> None:
    decision = evaluate_recovery_probe_fragility(
        decision_context=(("reg_m5_volatility_state", "extreme"),),
    )

    assert decision.admitted is False
    assert decision.reason == "M5_EXTREME_VOLATILITY_FRAGILITY_REJECT"
    assert decision.outcome_used is False
    assert decision.risk_authority is False
    assert decision.execution_authority is False


def test_recovery_fragility_guard_allows_non_extreme_state() -> None:
    decision = evaluate_recovery_probe_fragility(
        decision_context=(("reg_m5_volatility_state", "expanded"),),
    )

    assert decision.admitted is True


def test_recovery_fragility_guard_does_not_invent_missing_state() -> None:
    decision = evaluate_recovery_probe_fragility(
        decision_context=(("ctx_timeframe", "M1"),),
    )

    assert decision.admitted is True
    assert decision.m5_volatility_state is None
    assert decision.certification_claimed is False
