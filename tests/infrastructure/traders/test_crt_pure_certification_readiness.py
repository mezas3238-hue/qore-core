import pytest

from qore.infrastructure.traders.crt_pure_certification_readiness import (
    CrtPureCertificationEvidence,
    CrtPureCertificationReadiness,
    CrtPureCertificationStage,
    evaluate_certification_readiness,
)


def _current_evidence() -> CrtPureCertificationEvidence:
    return CrtPureCertificationEvidence(
        source_identity_closed=False,
        audusd_history_verified=False,
        usdjpy_history_verified=False,
        btcusd_history_verified=False,
    )


def test_current_lineage_is_source_open_and_not_certified() -> None:
    result = evaluate_certification_readiness(_current_evidence())
    assert result.stage is CrtPureCertificationStage.SOURCE_OPEN
    assert result.certified is False
    assert result.blockers == ("CRT_PRIMARY_SOURCE_AND_STRATEGY_IDENTITY_NOT_CLOSED",)


def test_readiness_cannot_grant_deployment_authority() -> None:
    with pytest.raises(ValueError, match="cannot grant deployment authority"):
        CrtPureCertificationReadiness(
            stage=CrtPureCertificationStage.SOURCE_OPEN,
            blockers=("example",),
            live_authorized=True,
        )


def test_certified_flag_cannot_be_forged() -> None:
    with pytest.raises(ValueError, match="must match"):
        CrtPureCertificationReadiness(
            stage=CrtPureCertificationStage.SOURCE_OPEN,
            blockers=("example",),
            certified=True,
        )


def test_all_validation_flags_are_required_for_certified_stage() -> None:
    evidence = CrtPureCertificationEvidence(
        source_identity_closed=True,
        audusd_history_verified=True,
        usdjpy_history_verified=True,
        btcusd_history_verified=True,
        deterministic_replay_green=True,
        per_market_forensics_closed=True,
        exact_candidate_frozen=True,
        walk_forward_green=True,
        monte_carlo_green=True,
        stress_green=True,
        slippage_green=True,
        robustness_green=True,
        fresh_holdout_green=True,
        combined_three_market_validation_green=True,
        full_qore_green=True,
    )
    # Strategy Identity is still source-open in the actual lineage, therefore
    # even a forged all-green economic payload cannot jump the source gate.
    result = evaluate_certification_readiness(evidence)
    assert result.stage is CrtPureCertificationStage.SOURCE_OPEN
    assert result.certified is False
