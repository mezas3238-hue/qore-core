from pathlib import Path

from qore.infrastructure.cibo_ce2i_phase20_mechanism_certification import (
    Phase20MechanismCertificationStatus,
    run_phase20f_accounting_core_certification,
)


def test_phase20f_accounting_core_certifies_exact_foundational_tools(
    tmp_path: Path,
) -> None:
    report = run_phase20f_accounting_core_certification(root=tmp_path)

    assert report.identity == "CIBO_PHASE20F_ACCOUNTING_CORE_CERTIFICATION_V1"
    assert tuple(item.tool_code for item in report.certifications) == (
        "T05",
        "T19",
        "T20",
    )
    assert all(
        item.status is Phase20MechanismCertificationStatus.CONTRACT_CERTIFIED
        for item in report.certifications
    )


def test_phase20f_accounting_core_proves_required_invariants(tmp_path: Path) -> None:
    report = run_phase20f_accounting_core_certification(root=tmp_path)

    assert {item.invariant_id for item in report.proofs} == {
        "T05_RECONCILIATION_REQUIRED",
        "T05_DIMENSIONAL_NON_FUNGIBILITY",
        "T05_SETTLEMENT_PERSISTS_AFTER_RESTART",
        "T19_NO_DOUBLE_SPEND",
        "T19_MULTI_SOURCE_ATOMICITY",
        "T19_DURABLE_CAS_STALE_WRITER_REJECTED",
        "T20_RESERVED_ONLY_UNUSED_RELEASE",
        "T20_DEPLOYED_RELEASE_PATH_REJECTED",
        "T20_RETURNED_VS_CONSUMED_ACCOUNTING",
    }
    assert all(item.passed for item in report.proofs)


def test_phase20f_accounting_core_grants_no_policy_or_runtime_authority(
    tmp_path: Path,
) -> None:
    report = run_phase20f_accounting_core_certification(root=tmp_path)

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
