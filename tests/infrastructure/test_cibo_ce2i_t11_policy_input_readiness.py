from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_provider_economics_evidence import (
    CURRENT_CTRADER_DEMO_PROVIDER_ECONOMICS,
)
from qore.infrastructure.cibo_ce2i_t11_execution_cost_calibration import (
    CiboT11ExecutionCostCalibration,
    T11SymbolLinearExecutionCost,
)
from qore.infrastructure.cibo_ce2i_t11_policy_input_readiness import (
    T11GrossEdgeModelEvidence,
    T11MarketImpactModelEvidence,
    assess_t11_policy_input_readiness,
)

T0 = datetime(2026, 10, 1, 3, 0, tzinfo=UTC)
SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64


def _symbols() -> tuple[str, ...]:
    return tuple(sorted(CURRENT_CTRADER_DEMO_PROVIDER_ECONOMICS.symbols))


def _linear_cost(*, ready: bool = True) -> CiboT11ExecutionCostCalibration:
    rows = tuple(
        T11SymbolLinearExecutionCost(
            qore_symbol=symbol,
            observation_count=8,
            p95_quoted_spread_cost_per_volume_usd=Decimal("1"),
            p95_commission_cost_per_volume_usd=Decimal("0.5"),
            p95_adverse_slippage_cost_per_volume_usd=Decimal("0.25"),
            p95_linear_execution_cost_per_volume_usd=Decimal("1.75"),
        )
        for symbol in _symbols()
    )
    return CiboT11ExecutionCostCalibration(
        manifest_sha256=SHA_A,
        execution_calibration_sha256=SHA_B,
        symbols=rows,
        required_symbol_coverage_met=True,
        provider_execution_model_ready=ready,
        linear_cost_model_ready=ready,
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


def _gross(
    symbol: str,
    *,
    ready: bool = True,
) -> T11GrossEdgeModelEvidence:
    return T11GrossEdgeModelEvidence(
        qore_symbol=symbol,
        as_of=T0 - timedelta(seconds=1),
        gross_edge_per_volume_usd=Decimal("5"),
        calibration_observations=100 if ready else 0,
        calibration_artifact_sha256=SHA_A,
        model_artifact_sha256=SHA_B,
        calibrated=ready,
        fresh_oos_validated=ready,
        temporal_stability_validated=ready,
    )


def _impact(
    symbol: str,
    *,
    ready: bool = True,
) -> T11MarketImpactModelEvidence:
    return T11MarketImpactModelEvidence(
        qore_symbol=symbol,
        frozen_at=T0 - timedelta(seconds=1),
        impact_cost_per_volume_squared_usd=Decimal("0.10"),
        empirical_observations=100 if ready else 0,
        distinct_volume_levels=4 if ready else 1,
        provider_execution_artifact_sha256=SHA_A,
        model_artifact_sha256=SHA_B,
        provider_bound=ready,
        calibrated=ready,
        fresh_oos_validated=ready,
    )


def test_complete_independent_inputs_can_be_ready_without_promoting_t11() -> None:
    symbols = _symbols()
    report = assess_t11_policy_input_readiness(
        linear_cost=_linear_cost(),
        gross_edge_evidence=tuple(_gross(symbol) for symbol in symbols),
        market_impact_evidence=tuple(_impact(symbol) for symbol in symbols),
        frozen_at=T0,
    )

    assert report.required_symbols == symbols
    assert report.linear_cost_model_ready is True
    assert report.gross_edge_model_ready is True
    assert report.market_impact_model_ready is True
    assert report.t11_policy_inputs_ready is True
    assert report.historical_2017_execution_terms_proven is False
    assert report.productive_authority is False
    assert report.blockers == (
        "T11_HISTORICAL_2017_EXECUTION_TERMS_NOT_PROVEN",
    )


def test_missing_gross_edge_and_impact_stay_machine_readable() -> None:
    report = assess_t11_policy_input_readiness(
        linear_cost=_linear_cost(),
        gross_edge_evidence=(),
        market_impact_evidence=(),
        frozen_at=T0,
    )

    assert report.gross_edge_model_ready is False
    assert report.market_impact_model_ready is False
    assert report.t11_policy_inputs_ready is False
    assert "T11_GROSS_EDGE_MODEL_NOT_IDENTIFIED" in report.blockers
    assert "T11_MARKET_IMPACT_MODEL_NOT_IDENTIFIED" in report.blockers


def test_unvalidated_symbol_evidence_does_not_count_as_ready() -> None:
    symbols = _symbols()
    gross = tuple(
        _gross(symbol, ready=symbol != symbols[0])
        for symbol in symbols
    )
    impact = tuple(
        _impact(symbol, ready=symbol != symbols[1])
        for symbol in symbols
    )

    report = assess_t11_policy_input_readiness(
        linear_cost=_linear_cost(),
        gross_edge_evidence=gross,
        market_impact_evidence=impact,
        frozen_at=T0,
    )

    assert report.gross_edge_model_ready is False
    assert report.market_impact_model_ready is False


def test_future_evidence_is_rejected() -> None:
    symbol = _symbols()[0]
    with pytest.raises(
        CiboCapitalManagementError,
        match="gross-edge evidence postdates freeze",
    ):
        assess_t11_policy_input_readiness(
            linear_cost=_linear_cost(),
            gross_edge_evidence=(
                replace(_gross(symbol), as_of=T0 + timedelta(seconds=1)),
            ),
            market_impact_evidence=(),
            frozen_at=T0,
        )


def test_duplicate_symbol_evidence_is_rejected() -> None:
    row = _gross(_symbols()[0])
    with pytest.raises(
        CiboCapitalManagementError,
        match="duplicates symbol",
    ):
        assess_t11_policy_input_readiness(
            linear_cost=_linear_cost(),
            gross_edge_evidence=(row, row),
            market_impact_evidence=(),
            frozen_at=T0,
        )


def test_leakage_flags_are_rejected_at_contract_boundary() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="leakage/authority",
    ):
        replace(_gross(_symbols()[0]), outcome_leakage_detected=True)

    with pytest.raises(
        CiboCapitalManagementError,
        match="target/holdout/authority",
    ):
        replace(_impact(_symbols()[0]), holdout_outcomes_used=True)


def test_out_of_scope_symbol_evidence_is_rejected() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="outside frozen symbol universe",
    ):
        assess_t11_policy_input_readiness(
            linear_cost=_linear_cost(),
            gross_edge_evidence=(_gross("NOT_IN_FROZEN_UNIVERSE"),),
            market_impact_evidence=(),
            frozen_at=T0,
        )
