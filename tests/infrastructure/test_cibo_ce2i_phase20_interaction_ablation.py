from pathlib import Path

from qore.infrastructure.cibo_ce2i_phase20_interaction_ablation import (
    run_phase20g_structural_ablation,
)


def test_phase20g_structural_ablation_passes_all_predeclared_cases(
    tmp_path: Path,
) -> None:
    report = run_phase20g_structural_ablation(root=tmp_path)

    assert report.identity == "CIBO_PHASE20G_STRUCTURAL_ABLATION_V1"
    assert len(report.cases) == 7
    assert all(item.passed for item in report.cases)


def test_phase20g_structural_ablation_covers_safe_composition_laws(
    tmp_path: Path,
) -> None:
    report = run_phase20g_structural_ablation(root=tmp_path)

    assert {item.case_id for item in report.cases} == {
        "G01_T11_EXECUTION_CAP_ABLATION",
        "G02_T12_STALE_REGIME_DOMINATES_POSITIVE_EXECUTION_CAP",
        "G03_T06_T11_FUNDING_AND_EXECUTION_ARE_ORTHOGONAL",
        "G04_T15_OPTIONALITY_RESERVES_DISTINCT_FUTURE_CAPACITY",
        "G05_T14_DERISKING_REDUCES_EXISTING_EXPOSURE",
        "G06_RECOVERY_COMPOSES_RESERVE_AND_DERISKING",
        "G07_T09_T18_COMPETITION_IS_INPUT_ORDER_INVARIANT",
    }


def test_phase20g_structural_ablation_grants_no_empirical_or_runtime_authority(
    tmp_path: Path,
) -> None:
    report = run_phase20g_structural_ablation(root=tmp_path)

    assert report.synthetic_contract_evidence_only is True
    assert report.empirical_value_claimed is False
    assert report.historical_provider_economics_claimed is False
    assert report.phase19j_burned_validation_reused is False
    assert report.policy_selected is False
    assert report.allocation_authority is False
    assert report.risk_authority is False
    assert report.execution_authority is False
    assert report.live_authorized is False
    assert report.real_capital_authorized is False
