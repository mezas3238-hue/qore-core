from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
)
from qore.infrastructure.cibo_capital_efficient_exposure import (
    CiboCapitalEfficientExposureState,
)
from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError
from qore.infrastructure.cibo_marginal_capital_utility_evidence import (
    MarginalCapitalUtilityEvidence,
)
from qore.infrastructure.cibo_marginal_leverage_utility import (
    CiboMarginalLeverageDisposition,
    CiboMarginalLeveragePolicy,
    assess_marginal_leverage_utility,
)
from qore.infrastructure.market_test_environment import MarketRuntimeEnvironment

NOW = datetime(2026, 9, 29, 23, 10, tzinfo=UTC)


def _exposure(**overrides: object) -> CiboCapitalEfficientExposureState:
    values: dict[str, object] = {
        "state_id": "cel5-exposure-001",
        "decision_at": NOW,
        "provider_key": "ctrader-demo",
        "qore_symbol": "EURUSD",
        "provider_symbol": "EURUSD",
        "executable_volume": Decimal("0.01"),
        "notional_exposure_usd": Decimal("1100"),
        "margin_occupancy_usd": Decimal("10"),
        "structural_stop_loss_usd": Decimal("1"),
        "normal_execution_cost_usd": Decimal("0.10"),
        "base_plausible_loss_usd": Decimal("1.10"),
        "stressed_economic_loss_usd": Decimal("2"),
        "gap_scenario_loss_usd": Decimal("1.50"),
        "liquidity_scenario_loss_usd": Decimal("1.75"),
        "convergence_scenario_loss_usd": Decimal("2"),
        "liquidation_scenario_loss_usd": Decimal("1.80"),
        "notional_to_margin": Decimal("110"),
        "notional_to_stressed_loss": Decimal("550"),
        "margin_to_stressed_loss": Decimal("5"),
        "provider_evidence_sha256": "sha256:" + "1" * 64,
        "marginal_evidence_sha256": "sha256:" + "2" * 64,
        "stress_evidence_sha256": "sha256:" + "3" * 64,
    }
    values.update(overrides)
    return CiboCapitalEfficientExposureState(**values)  # type: ignore[arg-type]


def _marginal(**overrides: object) -> MarginalCapitalUtilityEvidence:
    values: dict[str, object] = {
        "evidence_id": "cel5-marginal-001",
        "decision_at": NOW,
        "account_identity": CiboAccountCapitalIdentity(
            provider_key="ctrader-demo",
            account_ref="cel5-research",
            environment=MarketRuntimeEnvironment.DEMO,
        ),
        "trader_id": TraderLineage.R38_EURUSD,
        "signal_fingerprint": "cel5-signal",
        "source_opportunity_decision_sha256": "sha256:" + "4" * 64,
        "source_baseline_policy_record_sha256": "sha256:" + "5" * 64,
        "current_compound_capacity_usd": Decimal("60"),
        "requested_incremental_capital_usd": Decimal("20"),
        "expected_incremental_return_usd": Decimal("4"),
        "incremental_stop_risk_usd": Decimal("1"),
        "incremental_margin_usd": Decimal("10"),
        "incremental_execution_cost_usd": Decimal("0.10"),
        "incremental_concentration_risk_usd": Decimal("0.50"),
        "incremental_drawdown_risk_proxy_usd": Decimal("0.50"),
        "incremental_optionality_consumed_usd": Decimal("0.20"),
        "expected_capital_minutes": Decimal("30"),
        "epistemic_uncertainty": Decimal("0.10"),
        "provider_evidence_sha256": "sha256:" + "6" * 64,
        "expectation_evidence_sha256": "sha256:" + "7" * 64,
        "factor_evidence_sha256": "sha256:" + "8" * 64,
        "duration_evidence_sha256": "sha256:" + "9" * 64,
        "execution_evidence_sha256": "sha256:" + "a" * 64,
        "optionality_evidence_sha256": "sha256:" + "b" * 64,
    }
    values.update(overrides)
    return MarginalCapitalUtilityEvidence(**values)  # type: ignore[arg-type]


def _policy() -> CiboMarginalLeveragePolicy:
    return CiboMarginalLeveragePolicy(
        policy_id="cel5-source-only-v1",
        minimum_net_return_per_stressed_loss=Decimal("1.0"),
        minimum_net_return_per_requested_capital=Decimal("0.10"),
        maximum_stressed_loss_headroom_pressure=Decimal("0.50"),
        maximum_margin_headroom_pressure=Decimal("0.50"),
        maximum_concentration_per_requested_capital=Decimal("0.10"),
        maximum_drawdown_proxy_per_requested_capital=Decimal("0.10"),
        maximum_epistemic_uncertainty=Decimal("0.25"),
        maximum_capital_minutes=Decimal("60"),
        source_only_calibration=True,
        evidence_refs=("cel5-preregistered-hurdles",),
    )


def test_next_increment_can_be_eligible_for_existing_internal_market() -> None:
    assessment = assess_marginal_leverage_utility(
        candidate_id="candidate-eligible",
        exposure=_exposure(),
        marginal=_marginal(),
        hard_risk_headroom_usd=Decimal("10"),
        margin_headroom_usd=Decimal("40"),
        reserve_utility_per_capital=Decimal("0.05"),
        policy=_policy(),
    )

    assert assessment.disposition is (
        CiboMarginalLeverageDisposition.ELIGIBLE_FOR_INTERNAL_CAPITAL_MARKET
    )
    assert assessment.net_return_per_stressed_loss > Decimal("1")
    assert assessment.allocation_authority is False
    assert assessment.sizing_authority is False
    assert assessment.risk_authority is False
    assert assessment.execution_authority is False


def test_high_stressed_loss_requests_smaller_increment_not_more_leverage() -> None:
    assessment = assess_marginal_leverage_utility(
        candidate_id="candidate-reduce",
        exposure=_exposure(stressed_economic_loss_usd=Decimal("8")),
        marginal=_marginal(),
        hard_risk_headroom_usd=Decimal("10"),
        margin_headroom_usd=Decimal("40"),
        reserve_utility_per_capital=Decimal("0.05"),
        policy=_policy(),
    )

    assert assessment.disposition is (
        CiboMarginalLeverageDisposition.REDUCE_INCREMENT
    )
    assert "STRESSED_LOSS_PRESSURE_TOO_HIGH" in assessment.reason_codes


def test_reserve_can_dominate_positive_expected_increment() -> None:
    assessment = assess_marginal_leverage_utility(
        candidate_id="candidate-reserve",
        exposure=_exposure(),
        marginal=_marginal(),
        hard_risk_headroom_usd=Decimal("10"),
        margin_headroom_usd=Decimal("40"),
        reserve_utility_per_capital=Decimal("0.30"),
        policy=_policy(),
    )

    assert assessment.net_expected_return_usd > 0
    assert assessment.disposition is (
        CiboMarginalLeverageDisposition.RESERVE_DOMINATED
    )
    assert "RESERVE_UTILITY_DOMINATES" in assessment.reason_codes


def test_high_uncertainty_returns_insufficient_not_forced_deployment() -> None:
    assessment = assess_marginal_leverage_utility(
        candidate_id="candidate-uncertain",
        exposure=_exposure(),
        marginal=_marginal(epistemic_uncertainty=Decimal("0.40")),
        hard_risk_headroom_usd=Decimal("10"),
        margin_headroom_usd=Decimal("40"),
        reserve_utility_per_capital=Decimal("0.05"),
        policy=_policy(),
    )

    assert assessment.disposition is CiboMarginalLeverageDisposition.INSUFFICIENT


def test_cel5_forbids_outcome_aware_marginal_evidence() -> None:
    with pytest.raises(
        CiboCompoundCapitalError,
        match="cannot contain outcomes, utility or authority",
    ):
        replace(_marginal(), outcome_present=True)
