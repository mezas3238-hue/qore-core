from qore.infrastructure.cibo_ce2i_phase20_mechanism_certification import (
    Phase20MechanismCertificationStatus,
    run_phase20f_operational_mechanism_certification,
)


def test_phase20f_operational_certifies_exact_second_tranche() -> None:
    report = run_phase20f_operational_mechanism_certification()

    assert report.identity == "CIBO_PHASE20F_OPERATIONAL_MECHANISM_CERTIFICATION_V1"
    assert tuple(item.tool_code for item in report.certifications) == (
        "T11",
        "T12",
        "T14",
        "T15",
    )
    assert all(
        item.status is Phase20MechanismCertificationStatus.CONTRACT_CERTIFIED
        for item in report.certifications
    )


def test_phase20f_operational_proves_predeclared_invariants() -> None:
    report = run_phase20f_operational_mechanism_certification()

    assert {item.invariant_id for item in report.proofs} == {
        "T11_NON_POSITIVE_LINEAR_EDGE_BLOCKS_EXPANSION",
        "T11_NEGATIVE_MARGINAL_STEP_CAPS_VOLUME",
        "T12_STALE_EVIDENCE_FAILS_CLOSED_TO_RELEASE",
        "T12_RECOVERY_POSTURE_BLOCKS_EXPANSION",
        "T14_MINIMUM_STEP_ALIGNED_REDUCTION",
        "T14_TRADER_INVALIDATION_RELEASES_ALL",
        "T15_DEFENSIVE_PRESERVES_CHEAPEST_KNOWN_OPTION",
        "T15_RECOVERY_PRESERVES_ALL_REMAINING_CAPACITY",
    }
    assert all(item.passed for item in report.proofs)


def test_phase20f_operational_grants_no_policy_or_runtime_authority() -> None:
    report = run_phase20f_operational_mechanism_certification()

    assert report.synthetic_contract_evidence_only is True
    assert report.historical_provider_economics_claimed is False
    assert report.phase19j_burned_validation_reused is False
    assert report.policy_certified is False
    assert report.allocation_authority is False
    assert report.risk_authority is False
    assert report.execution_authority is False
    assert report.demo_execution_authorized is False
    assert report.live_authorized is False
    assert report.real_capital_authorized is False
    assert report.merge_authorized is False
