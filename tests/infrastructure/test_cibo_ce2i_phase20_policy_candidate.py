from datetime import timedelta
from decimal import Decimal

from qore.infrastructure.cibo_ce2i_phase20_policy_candidate import (
    FROZEN_PHASE20_POLICY_CANDIDATE,
)
from qore.infrastructure.cibo_ce2i_regime_selector import (
    CiboCapitalRegimeState,
    CiboRegimePosture,
    CorrelationState,
    LiquidityState,
    ProviderCondition,
    VolatilityState,
    _posture,
)


def _state(
    *,
    drawdown: str = "0",
    risk: str = "0",
    margin: str = "0",
) -> CiboCapitalRegimeState:
    return CiboCapitalRegimeState(
        liquidity=LiquidityState.NORMAL,
        volatility=VolatilityState.NORMAL,
        correlation=CorrelationState.NORMAL,
        provider_condition=ProviderCondition.HEALTHY,
        risk_utilization=Decimal(risk),
        margin_utilization=Decimal(margin),
        drawdown_utilization=Decimal(drawdown),
        opportunity_count=1,
    )


def test_phase20_candidate_parameter_digest_is_stable() -> None:
    candidate = FROZEN_PHASE20_POLICY_CANDIDATE

    assert candidate.code_sha == (
        "a0a9759a5bbe30fb21e1aee154fadc6509136937"
    )
    assert candidate.parameter_sha256().startswith("sha256:")
    assert len(candidate.parameter_sha256()) == 71
    assert candidate.mpc_horizon_steps == 2
    assert candidate.snapshot_max_age_seconds == Decimal("2")
    assert candidate.current_forecast_max_age_seconds == Decimal("2")
    assert candidate.phase19j_burned_validation_reused is False
    assert candidate.policy_certified is False


def test_phase20_candidate_freeze_predates_future_qualification_only() -> None:
    candidate = FROZEN_PHASE20_POLICY_CANDIDATE
    assert candidate.frozen_at + timedelta(seconds=1) > candidate.frozen_at


def test_phase20_candidate_regime_thresholds_match_selector_contract() -> None:
    assert _posture(_state(drawdown="0.499"))[0] is CiboRegimePosture.STABLE
    assert _posture(_state(drawdown="0.50"))[0] is CiboRegimePosture.DEFENSIVE
    assert _posture(_state(drawdown="0.75"))[0] is CiboRegimePosture.RECOVERY
    assert _posture(_state(risk="0.70"))[0] is CiboRegimePosture.DEFENSIVE
    assert _posture(_state(risk="0.85"))[0] is CiboRegimePosture.RECOVERY
    assert _posture(_state(margin="0.80"))[0] is CiboRegimePosture.DEFENSIVE
