from datetime import timedelta
from decimal import Decimal

from qore.infrastructure.cibo_ce2i_phase20_policy_candidate import (
    FROZEN_PHASE20_POLICY_CANDIDATE,
    SUPERSEDED_PHASE20_POLICY_CANDIDATE_V1,
    SUPERSEDED_PHASE20_POLICY_CANDIDATE_V2,
)
from qore.infrastructure.cibo_ce2i_phase20_train_prior import (
    prior_digest_sha256,
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

    assert candidate.candidate_id == (
        "CIBO_PHASE20_FULL_SURFACE_FORWARD_CANDIDATE_V3"
    )
    assert candidate.code_sha == (
        "edf96722fd0505711aa88bc1d15296b09e6dba6f"
    )
    digest = candidate.parameter_sha256()
    assert digest.startswith("sha256:")
    assert len(digest) == 71
    assert candidate.mpc_horizon_steps == 2
    assert candidate.snapshot_max_age_seconds == Decimal("2")
    assert candidate.current_forecast_max_age_seconds == Decimal("2")
    assert candidate.expectation_prior_sha256 == prior_digest_sha256()
    assert candidate.expectation_policy == (
        "FROZEN_TRAIN_MOM5_STRUCTURAL_R_X_CURRENT_STOP_RISK"
    )
    assert candidate.active_ce2i_tools == tuple(
        f"T{index:02d}" for index in range(1, 21)
    )
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


def test_phase20_candidate_v1_is_preserved_as_superseded_unqualified() -> None:
    assert SUPERSEDED_PHASE20_POLICY_CANDIDATE_V1["status"] == (
        "SUPERSEDED_BEFORE_FORWARD_COLLECTION"
    )
    assert (
        SUPERSEDED_PHASE20_POLICY_CANDIDATE_V1[
            "fresh_forward_observations_collected"
        ]
        == 0
    )


def test_phase20_candidate_v2_is_owner_rejected_before_collection() -> None:
    assert SUPERSEDED_PHASE20_POLICY_CANDIDATE_V2["status"] == (
        "REJECTED_BY_OWNER_BEFORE_FORWARD_COLLECTION"
    )
    assert (
        SUPERSEDED_PHASE20_POLICY_CANDIDATE_V2[
            "fresh_forward_observations_collected"
        ]
        == 0
    )
