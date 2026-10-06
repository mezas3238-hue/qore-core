from pathlib import Path

from qore.infrastructure.cibo_ce2i_phase20_failure_engineering import (
    Phase20FailureDisposition,
    run_phase20j_failure_engineering,
)


def test_phase20j_failure_matrix_passes_all_predeclared_probes(
    tmp_path: Path,
) -> None:
    report = run_phase20j_failure_engineering(root=tmp_path)

    assert report.identity == "CIBO_PHASE20J_A_FAILURE_ENGINEERING_V1"
    assert len(report.probes) == 15
    assert all(item.passed for item in report.probes)


def test_phase20j_failure_matrix_covers_provider_state_and_settlement_faults(
    tmp_path: Path,
) -> None:
    report = run_phase20j_failure_engineering(root=tmp_path)
    ids = {item.probe_id for item in report.probes}

    assert ids == {
        "J01_PROVIDER_LIQUIDITY_UNAVAILABLE",
        "J02_PROVIDER_MINIMUM_VOLUME_CLIFF",
        "J03_PROVIDER_COMBINED_ADVERSE_NON_IMPROVING",
        "J04_RESTART_PRESERVES_UNSETTLED_DEPLOYMENT",
        "J05_DELAYED_SETTLEMENT_RELEASES_ONLY_RECONCILED_RETURN",
        "J06_STALE_CAPITAL_LEDGER_GENERATION",
        "J07_CAPITAL_LEDGER_WRITER_LOCK",
        "J08_CORRUPT_CAPITAL_LEDGER_SNAPSHOT",
        "J09_STALE_PORTFOLIO_RESERVATION_GENERATION",
        "J10_PORTFOLIO_WRITER_LOCK",
        "J11_PORTFOLIO_STATE_SURVIVES_RESTART",
        "J12_EXACT_DUPLICATE_SETTLEMENT_IDEMPOTENT",
        "J13_CONFLICTING_DUPLICATE_SETTLEMENT",
        "J14_TERMINAL_SETTLEMENT_SURVIVES_RESTART",
        "J15_SETTLEMENT_AFTER_TERMINAL_EXIT",
    }
    assert any(
        item.disposition is Phase20FailureDisposition.FAIL_CLOSED
        for item in report.probes
    )
    assert any(
        item.disposition is Phase20FailureDisposition.STATE_PRESERVED
        for item in report.probes
    )
    assert any(
        item.disposition is Phase20FailureDisposition.IDEMPOTENT
        for item in report.probes
    )


def test_phase20j_failure_matrix_grants_no_authority_or_empirical_claim(
    tmp_path: Path,
) -> None:
    report = run_phase20j_failure_engineering(root=tmp_path)

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
