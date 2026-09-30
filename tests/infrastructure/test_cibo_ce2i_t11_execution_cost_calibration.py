from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.cibo_arch_b_forward_economic_manifest import (
    ARCH_B_FORWARD_ECONOMIC_MANIFEST_ID,
    ArchBForwardEconomicManifest,
    ArchBForwardEconomicManifestRow,
)
from qore.infrastructure.cibo_ce2i_phase20_policy_candidate import (
    FROZEN_PHASE20_POLICY_CANDIDATE,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification_plan import (
    FROZEN_PHASE20D_QUALIFICATION_PLAN,
    phase20d_qualification_plan_sha256,
)
from qore.infrastructure.cibo_ce2i_provider_execution_calibration import (
    CiboProviderExecutionCalibration,
    CiboProviderExecutionObservation,
    CiboProviderExecutionSymbolSummary,
    PROVIDER_EXECUTION_CALIBRATION_ID,
)
from qore.infrastructure.cibo_ce2i_t11_execution_cost_calibration import (
    calibrate_t11_linear_execution_cost,
)

T0 = datetime(2026, 9, 30, 22, 30, tzinfo=UTC)


def _manifest() -> ArchBForwardEconomicManifest:
    frozen = FROZEN_PHASE20_POLICY_CANDIDATE
    plan = FROZEN_PHASE20D_QUALIFICATION_PLAN
    row = ArchBForwardEconomicManifestRow(
        decision_epoch_id="epoch-t11",
        decision_evidence_sha256="sha256:" + "1" * 64,
        decision_at=T0,
        fold_id="WF1",
        signal_fingerprint="signal-t11",
        trader_id="VT31_NAS100",
        candidate_id=frozen.candidate_id,
        code_sha=frozen.code_sha,
        parameter_sha256=frozen.parameter_sha256(),
        collector_git_sha="a" * 40,
        provider_key="ctrader-demo",
        account_ref="12345",
        environment="demo",
        provider_evidence_id="provider-t11",
        qore_symbol="NAS100",
        provider_symbol="US100",
        provider_economics_sha256="sha256:" + "2" * 64,
        provider_observed_at=(T0 - timedelta(milliseconds=100)).isoformat(),
        provider_contract_size=Decimal("1"),
        provider_tick_size=Decimal("0.01"),
        provider_tick_value=Decimal("1"),
        provider_minimum_volume=Decimal("0.01"),
        provider_volume_step=Decimal("0.01"),
        provider_margin_per_volume_usd=Decimal("1"),
        provider_commission_per_volume_usd=Decimal("2"),
        provider_slippage_reserve_per_volume_usd=Decimal("0"),
        provider_bid=Decimal("100"),
        provider_ask=Decimal("101"),
        policy_record_sha256="sha256:" + "3" * 64,
        policy_selected=True,
        baseline_policy_id=plan.baseline_policy_id,
        baseline_selected=True,
        execution_risk_evidence_id="risk-t11",
        executed_risk_sha256="sha256:" + "4" * 64,
        executed_source_volume=Decimal("0.01"),
        executed_initial_stop_risk_usd=Decimal("1"),
        settlement_sha256="sha256:" + "5" * 64,
        settlement_deal_ids=(1,),
        realized_net_pnl_usd=Decimal("1"),
        outcome_observed_at=T0 + timedelta(minutes=10),
        release_evidence_sha256="sha256:" + "6" * 64,
        release_chain_sha256="sha256:" + "7" * 64,
        released_stop_risk_capacity_usd=Decimal("1"),
        released_margin_capacity_usd=Decimal("1"),
        terminal_release_at=T0 + timedelta(minutes=9),
        capital_minutes=Decimal("9"),
    )
    return ArchBForwardEconomicManifest(
        manifest_id=ARCH_B_FORWARD_ECONOMIC_MANIFEST_ID,
        frozen_candidate_id=frozen.candidate_id,
        frozen_code_sha=frozen.code_sha,
        frozen_parameter_sha256=frozen.parameter_sha256(),
        qualification_plan_id=plan.plan_id,
        qualification_plan_sha256=phase20d_qualification_plan_sha256(),
        baseline_policy_id=plan.baseline_policy_id,
        qualification_status="NOT_READY",
        decision_epochs=1,
        candidate_rows=1,
        complete_lineage_rows=1,
        rows=(row,),
        gaps=(),
        ready_for_scientific_consumption=False,
    )


def _calibration(manifest: ArchBForwardEconomicManifest) -> CiboProviderExecutionCalibration:
    observation = CiboProviderExecutionObservation(
        decision_evidence_sha256=manifest.rows[0].decision_evidence_sha256,
        signal_fingerprint="signal-t11",
        qore_symbol="NAS100",
        side="long",
        provider_quote_price=Decimal("101"),
        weighted_fill_price=Decimal("101.03"),
        signed_slippage_price=Decimal("0.03"),
        signed_slippage_bps=Decimal("0.3"),
        adverse_slippage_bps=Decimal("0.3"),
        signed_slippage_cost_per_volume_usd=Decimal("3"),
        adverse_slippage_cost_per_volume_usd=Decimal("3"),
        provider_quote_age_ms=Decimal("100"),
        decision_to_fill_ms=Decimal("1000"),
        fill_to_risk_reconciliation_ms=Decimal("500"),
        fill_evidence_refs=("fill:t11",),
    )
    summary = CiboProviderExecutionSymbolSummary(
        qore_symbol="NAS100",
        observation_count=1,
        mean_signed_slippage_bps=Decimal("0.3"),
        p95_adverse_slippage_bps=Decimal("0.3"),
        worst_adverse_slippage_bps=Decimal("0.3"),
        p95_adverse_slippage_cost_per_volume_usd=Decimal("3"),
        worst_adverse_slippage_cost_per_volume_usd=Decimal("3"),
        p95_provider_quote_age_ms=Decimal("100"),
        p95_decision_to_fill_ms=Decimal("1000"),
        p95_fill_to_risk_reconciliation_ms=Decimal("500"),
    )
    return CiboProviderExecutionCalibration(
        calibration_id=PROVIDER_EXECUTION_CALIBRATION_ID,
        provider_key="ctrader-demo",
        environment="demo",
        manifest_sha256=manifest.fingerprint(),
        manifest_candidate_rows=1,
        manifest_complete_lineage_rows=1,
        frozen_at=T0 + timedelta(minutes=11),
        total_observations=1,
        observations=(observation,),
        symbol_summaries=(summary,),
        manifest_scientifically_ready=False,
        all_complete_rows_reconciled=True,
        required_symbol_coverage_met=False,
        minimum_symbol_observations_met=False,
        empirical_slippage_calibrated=False,
        execution_model_ready=False,
        historical_2017_exact_claimed=False,
        holdout_outcomes_used=False,
        target_aware=False,
        productive_authority=False,
        blockers=("FORWARD_MANIFEST_NOT_SCIENTIFICALLY_READY",),
    )


def test_t11_linear_cost_uses_provider_native_tick_geometry() -> None:
    manifest = _manifest()
    report = calibrate_t11_linear_execution_cost(
        manifest=manifest,
        execution_calibration=_calibration(manifest),
    )

    assert len(report.symbols) == 1
    row = report.symbols[0]
    assert row.qore_symbol == "NAS100"
    assert row.p95_quoted_spread_cost_per_volume_usd == Decimal("100")
    assert row.p95_commission_cost_per_volume_usd == Decimal("2")
    assert row.p95_adverse_slippage_cost_per_volume_usd == Decimal("3")
    assert row.p95_linear_execution_cost_per_volume_usd == Decimal("105")


def test_t11_linear_cost_cannot_promote_unresolved_policy_inputs() -> None:
    manifest = _manifest()
    report = calibrate_t11_linear_execution_cost(
        manifest=manifest,
        execution_calibration=_calibration(manifest),
    )

    assert report.linear_cost_model_ready is False
    assert report.gross_edge_model_ready is False
    assert report.market_impact_model_ready is False
    assert report.historical_2017_execution_terms_proven is False
    assert report.t11_policy_ready is False
    assert report.productive_authority is False
    assert "T11_FORWARD_MANIFEST_NOT_SCIENTIFICALLY_READY" in report.blockers
    assert "T11_PROVIDER_EXECUTION_MODEL_NOT_READY" in report.blockers
    assert "T11_REQUIRED_SYMBOL_COST_COVERAGE_INCOMPLETE" in report.blockers
    assert "T11_GROSS_EDGE_MODEL_NOT_IDENTIFIED" in report.blockers
    assert "T11_MARKET_IMPACT_MODEL_NOT_IDENTIFIED" in report.blockers
    assert "T11_HISTORICAL_2017_EXECUTION_TERMS_NOT_PROVEN" in report.blockers
