from pathlib import Path

from qore.infrastructure.cibo_ce2i_phase20_mechanism_certification import (
    Phase20MechanismCertificationStatus,
    run_phase20f_capital_action_certification,
)


def test_phase20f_capital_action_certifies_exact_third_tranche(
    tmp_path: Path,
) -> None:
    report = run_phase20f_capital_action_certification(root=tmp_path)

    assert report.identity == "CIBO_PHASE20F_CAPITAL_ACTION_CERTIFICATION_V1"
    assert tuple(item.tool_code for item in report.certifications) == (
        "T01",
        "T06",
        "T07",
        "T09",
        "T13",
        "T18",
    )
    assert all(
        item.status is Phase20MechanismCertificationStatus.CONTRACT_CERTIFIED
        for item in report.certifications
    )


def test_phase20f_capital_action_proves_predeclared_invariants(
    tmp_path: Path,
) -> None:
    report = run_phase20f_capital_action_certification(root=tmp_path)

    assert {item.invariant_id for item in report.proofs} == {
        "T01_USES_PROVIDER_MINIMUM_EXECUTABLE_SEED",
        "T01_FAILS_CLOSED_BELOW_MINIMUM_MARGIN",
        "T06_REALIZED_PROFIT_BOUNDS_EXPANSION",
        "T06_ORIGINAL_BASE_CAPITAL_NOT_EXPANSION_SOURCE",
        "T07_PROTECTED_FLOOR_BOUNDS_EXPANSION",
        "T09_SCARCE_CAPITAL_COMPETES_BY_CAUSAL_EFFICIENCY",
        "T13_DRAWDOWN_RECOVERY_RESERVES_ALL_CAPACITY",
        "T18_TRADER_IDENTITY_DOES_NOT_CREATE_PRIORITY",
    }
    assert all(item.passed for item in report.proofs)


def test_phase20f_capital_action_grants_no_policy_or_runtime_authority(
    tmp_path: Path,
) -> None:
    report = run_phase20f_capital_action_certification(root=tmp_path)

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
