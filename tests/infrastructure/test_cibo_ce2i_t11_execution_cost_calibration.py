from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from qore.infrastructure.cibo_arch_b_forward_economic_manifest import (
    ARCH_B_FORWARD_ECONOMIC_MANIFEST_ID,
    ArchBForwardEconomicManifest,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_policy_candidate import (
    FROZEN_PHASE20_POLICY_CANDIDATE,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification_plan import (
    FROZEN_PHASE20D_QUALIFICATION_PLAN,
    phase20d_qualification_plan_sha256,
)
from qore.infrastructure.cibo_ce2i_provider_economics_evidence import (
    CURRENT_CTRADER_DEMO_PROVIDER_ECONOMICS,
)
from qore.infrastructure.cibo_ce2i_provider_execution_calibration import (
    PROVIDER_EXECUTION_CALIBRATION_ID,
    CiboProviderExecutionCalibration,
)
from qore.infrastructure.cibo_ce2i_t11_execution_cost_calibration import (
    CiboT11ExecutionCostCalibration,
    T11SymbolLinearExecutionCost,
    calibrate_t11_linear_execution_cost,
)

T0 = datetime(2026, 9, 30, 22, 0, tzinfo=UTC)
SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64


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


def _empty_execution_calibration(
    manifest: ArchBForwardEconomicManifest,
) -> CiboProviderExecutionCalibration:
    return CiboProviderExecutionCalibration(
        calibration_id=PROVIDER_EXECUTION_CALIBRATION_ID,
        provider_key="ctrader-demo",
        environment="demo",
        manifest_sha256=manifest.fingerprint(),
        manifest_candidate_rows=0,
        manifest_complete_lineage_rows=0,
        frozen_at=T0,
        total_observations=0,
        observations=(),
        symbol_summaries=(),
        manifest_scientifically_ready=False,
        all_complete_rows_reconciled=False,
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


def _linear_symbol(symbol: str) -> T11SymbolLinearExecutionCost:
    return T11SymbolLinearExecutionCost(
        qore_symbol=symbol,
        observation_count=8,
        p95_quoted_spread_cost_per_volume_usd=Decimal("1.25"),
        p95_commission_cost_per_volume_usd=Decimal("0.50"),
        p95_adverse_slippage_cost_per_volume_usd=Decimal("0.25"),
        p95_linear_execution_cost_per_volume_usd=Decimal("2.00"),
    )


def test_linear_cost_summary_requires_exact_component_reconciliation() -> None:
    with pytest.raises(CiboCapitalManagementError, match="total drift"):
        T11SymbolLinearExecutionCost(
            qore_symbol="EURUSD",
            observation_count=8,
            p95_quoted_spread_cost_per_volume_usd=Decimal("1"),
            p95_commission_cost_per_volume_usd=Decimal("1"),
            p95_adverse_slippage_cost_per_volume_usd=Decimal("1"),
            p95_linear_execution_cost_per_volume_usd=Decimal("2"),
        )


def test_linear_model_can_be_ready_without_promoting_t11_policy() -> None:
    symbols = tuple(
        _linear_symbol(symbol)
        for symbol in sorted(CURRENT_CTRADER_DEMO_PROVIDER_ECONOMICS.symbols)
    )
    report = CiboT11ExecutionCostCalibration(
        manifest_sha256=SHA_A,
        execution_calibration_sha256=SHA_B,
        symbols=symbols,
        required_symbol_coverage_met=True,
        provider_execution_model_ready=True,
        linear_cost_model_ready=True,
        gross_edge_model_ready=False,
        market_impact_model_ready=False,
        historical_2017_execution_terms_proven=False,
        t11_policy_ready=False,
        productive_authority=False,
        blockers=(
            "T11_GROSS_EDGE_MODEL_NOT_IDENTIFIED",
            "T11_MARKET_IMPACT_MODEL_NOT_IDENTIFIED",
            "T11_HISTORICAL_2017_EXECUTION_TERMS_NOT_PROVEN",
        ),
    )

    assert report.linear_cost_model_ready is True
    assert report.gross_edge_model_ready is False
    assert report.market_impact_model_ready is False
    assert report.t11_policy_ready is False
    assert report.productive_authority is False


def test_t11_calibration_fails_closed_without_real_forward_population() -> None:
    manifest = _empty_manifest()
    execution = _empty_execution_calibration(manifest)

    report = calibrate_t11_linear_execution_cost(
        manifest=manifest,
        execution_calibration=execution,
    )

    assert report.symbols == ()
    assert report.required_symbol_coverage_met is False
    assert report.provider_execution_model_ready is False
    assert report.linear_cost_model_ready is False
    assert report.gross_edge_model_ready is False
    assert report.market_impact_model_ready is False
    assert report.t11_policy_ready is False
    assert "T11_FORWARD_MANIFEST_NOT_SCIENTIFICALLY_READY" in report.blockers
    assert "T11_PROVIDER_EXECUTION_MODEL_NOT_READY" in report.blockers
    assert "T11_REQUIRED_SYMBOL_COST_COVERAGE_INCOMPLETE" in report.blockers
    assert "T11_GROSS_EDGE_MODEL_NOT_IDENTIFIED" in report.blockers
    assert "T11_MARKET_IMPACT_MODEL_NOT_IDENTIFIED" in report.blockers
