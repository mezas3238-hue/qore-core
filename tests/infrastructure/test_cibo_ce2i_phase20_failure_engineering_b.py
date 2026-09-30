from qore.infrastructure.cibo_ce2i_phase20_failure_engineering import (
    Phase20FailureDisposition,
    run_phase20j_provider_cluster_failure_engineering,
)


def test_phase20j_b_passes_all_predeclared_provider_cluster_probes() -> None:
    report = run_phase20j_provider_cluster_failure_engineering()

    assert report.identity == "CIBO_PHASE20J_B_PROVIDER_CLUSTER_FAILURE_V1"
    assert len(report.probes) == 7
    assert all(item.passed for item in report.probes)


def test_phase20j_b_covers_provider_cluster_and_loss_pressure() -> None:
    report = run_phase20j_provider_cluster_failure_engineering()

    assert {item.probe_id for item in report.probes} == {
        "J16_SPREAD_EXPANSION_NON_IMPROVING",
        "J17_SLIPPAGE_RESERVE_NON_IMPROVING",
        "J18_MARGIN_EXPANSION_NON_IMPROVING",
        "J19_EXECUTION_DELAY_FLOOR_PRESERVED",
        "J20_CORRELATION_CONCENTRATION_BLOCKS_SECOND_USE",
        "J21_SIMULTANEOUS_CLUSTER_RESPECTS_STOP_RISK_CAPACITY",
        "J22_SIMULTANEOUS_FULL_LOSSES_PRESERVE_CAPITAL_CONSERVATION",
    }
    assert any(
        item.disposition is Phase20FailureDisposition.FAIL_CLOSED
        for item in report.probes
    )
    assert any(
        item.disposition is Phase20FailureDisposition.STATE_PRESERVED
        for item in report.probes
    )


def test_phase20j_b_grants_no_authority_or_empirical_claim() -> None:
    report = run_phase20j_provider_cluster_failure_engineering()

    assert report.synthetic_contract_evidence_only is True
    assert report.market_probability_claimed is False
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
