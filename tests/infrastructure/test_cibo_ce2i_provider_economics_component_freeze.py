from datetime import UTC, datetime

from qore.infrastructure.cibo_arch_b_forward_economic_manifest import (
    ARCH_B_FORWARD_ECONOMIC_MANIFEST_ID,
    ArchBForwardEconomicManifest,
)
from qore.infrastructure.cibo_ce2i_phase20_execution_risk_store import (
    VersionedPhase20ExecutedRiskBook,
)
from qore.infrastructure.cibo_ce2i_phase20_policy_candidate import (
    FROZEN_PHASE20_POLICY_CANDIDATE,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification_plan import (
    FROZEN_PHASE20D_QUALIFICATION_PLAN,
    phase20d_qualification_plan_sha256,
)
from qore.infrastructure.cibo_ce2i_provider_economics_component_freeze import (
    freeze_current_ctrader_demo_provider_economics,
)
from qore.infrastructure.cibo_ce2i_provider_execution_calibration import (
    calibrate_ctrader_demo_forward_execution,
)


def _empty_manifest() -> ArchBForwardEconomicManifest:
    frozen = FROZEN_PHASE20_POLICY_CANDIDATE
    plan = FROZEN_PHASE20D_QUALIFICATION_PLAN
    return ArchBForwardEconomicManifest(
        manifest_id=ARCH_B_FORWARD_ECONOMIC_MANIFEST_ID,
        frozen_candidate_id=frozen.candidate_id,
        frozen_code_sha=frozen.code_sha,
        frozen_parameter_sha256=frozen.parameter_sha256(),
        qualification_plan_id=plan.plan_id,
        qualification_plan_sha256=phase20d_qualification_plan_sha256(),
        baseline_policy_id=plan.baseline_policy_id,
        qualification_status="NOT_READY",
        decision_epochs=0,
        candidate_rows=0,
        complete_lineage_rows=0,
        rows=(),
        gaps=(),
        ready_for_scientific_consumption=False,
    )


def test_current_provider_terms_freeze_without_overclaiming_slippage() -> None:
    freeze = freeze_current_ctrader_demo_provider_economics(
        frozen_at=datetime(2026, 9, 30, 20, 15, tzinfo=UTC)
    )

    assert freeze.point_in_time_terms_frozen is True
    assert freeze.spread_terms_frozen is True
    assert freeze.commission_terms_frozen is True
    assert freeze.expected_margin_terms_frozen is True
    assert freeze.volume_contract_terms_frozen is True
    assert freeze.empirical_slippage_frozen is False
    assert freeze.execution_model_frozen is False
    assert freeze.historical_2017_exact_claimed is False
    assert freeze.holdout_outcomes_used is False
    assert freeze.target_aware is False
    assert freeze.broker_mutation_performed is False
    assert freeze.pre_holdout_provider_economics_ready is False
    assert freeze.execution_calibration_sha256 is None
    assert freeze.productive_authority is False
    assert freeze.blockers == (
        "EMPIRICAL_SLIPPAGE_NOT_FROZEN",
        "EXECUTION_MODEL_NOT_FROZEN",
    )
    assert "artifact:11104595302" in freeze.source_evidence_ref


def test_not_ready_execution_calibration_is_bound_without_promoting_readiness() -> None:
    calibration = calibrate_ctrader_demo_forward_execution(
        manifest=_empty_manifest(),
        executed_risk_book=VersionedPhase20ExecutedRiskBook(generation=0),
        frozen_at=datetime(2026, 9, 30, 20, 20, tzinfo=UTC),
    )

    freeze = freeze_current_ctrader_demo_provider_economics(
        frozen_at=datetime(2026, 9, 30, 20, 30, tzinfo=UTC),
        execution_calibration=calibration,
    )

    assert calibration.empirical_slippage_calibrated is False
    assert calibration.execution_model_ready is False
    assert freeze.execution_calibration_sha256 == calibration.fingerprint()
    assert freeze.empirical_slippage_frozen is False
    assert freeze.execution_model_frozen is False
    assert freeze.pre_holdout_provider_economics_ready is False
    assert freeze.blockers == (
        "EMPIRICAL_SLIPPAGE_NOT_FROZEN",
        "EXECUTION_MODEL_NOT_FROZEN",
    )


def test_ready_execution_calibration_promotes_pre_holdout_readiness() -> None:
    from decimal import Decimal

    from qore.infrastructure.cibo_ce2i_provider_execution_calibration import (
        PROVIDER_EXECUTION_CALIBRATION_ID,
        CiboProviderExecutionCalibration,
        CiboProviderExecutionObservation,
        CiboProviderExecutionSymbolSummary,
    )

    symbols = (
        "AUDJPY",
        "EURUSD",
        "GBPJPY",
        "GBPUSD",
        "NAS100",
        "XAUUSD",
    )
    observations = []
    counts = {symbol: 0 for symbol in symbols}
    for index in range(200):
        symbol = symbols[index % len(symbols)]
        counts[symbol] += 1
        observations.append(
            CiboProviderExecutionObservation(
                decision_evidence_sha256="sha256:" + f"{index + 1:064x}",
                signal_fingerprint=f"signal-{index}",
                qore_symbol=symbol,
                side="long",
                provider_quote_price=Decimal("100"),
                weighted_fill_price=Decimal("100"),
                signed_slippage_price=Decimal("0"),
                signed_slippage_bps=Decimal("0"),
                adverse_slippage_bps=Decimal("0"),
                signed_slippage_cost_per_volume_usd=Decimal("0"),
                adverse_slippage_cost_per_volume_usd=Decimal("0"),
                provider_quote_age_ms=Decimal("10"),
                decision_to_fill_ms=Decimal("20"),
                fill_to_risk_reconciliation_ms=Decimal("30"),
                fill_evidence_refs=(f"fill:{index}",),
            )
        )

    summaries = tuple(
        CiboProviderExecutionSymbolSummary(
            qore_symbol=symbol,
            observation_count=counts[symbol],
            mean_signed_slippage_bps=Decimal("0"),
            p95_adverse_slippage_bps=Decimal("0"),
            worst_adverse_slippage_bps=Decimal("0"),
            p95_adverse_slippage_cost_per_volume_usd=Decimal("0"),
            worst_adverse_slippage_cost_per_volume_usd=Decimal("0"),
            p95_provider_quote_age_ms=Decimal("10"),
            p95_decision_to_fill_ms=Decimal("20"),
            p95_fill_to_risk_reconciliation_ms=Decimal("30"),
        )
        for symbol in symbols
    )
    calibration = CiboProviderExecutionCalibration(
        calibration_id=PROVIDER_EXECUTION_CALIBRATION_ID,
        provider_key="ctrader-demo",
        environment="demo",
        manifest_sha256="sha256:" + "1" * 64,
        manifest_candidate_rows=200,
        manifest_complete_lineage_rows=200,
        frozen_at=datetime(2026, 9, 30, 20, 20, tzinfo=UTC),
        total_observations=200,
        observations=tuple(observations),
        symbol_summaries=summaries,
        manifest_scientifically_ready=True,
        all_complete_rows_reconciled=True,
        required_symbol_coverage_met=True,
        minimum_symbol_observations_met=True,
        empirical_slippage_calibrated=True,
        execution_model_ready=True,
        historical_2017_exact_claimed=False,
        holdout_outcomes_used=False,
        target_aware=False,
        productive_authority=False,
        blockers=(),
    )

    freeze = freeze_current_ctrader_demo_provider_economics(
        frozen_at=datetime(2026, 9, 30, 20, 30, tzinfo=UTC),
        execution_calibration=calibration,
    )

    assert freeze.empirical_slippage_frozen is True
    assert freeze.execution_model_frozen is True
    assert freeze.pre_holdout_provider_economics_ready is True
    assert freeze.blockers == ()
    assert freeze.execution_calibration_sha256 == calibration.fingerprint()
    assert freeze.historical_2017_exact_claimed is False
    assert freeze.productive_authority is False
