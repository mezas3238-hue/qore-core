from decimal import Decimal

import pytest

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_single_account_maximum_capability import (
    CIBO_MAXIMUM_CAPABILITY_INITIAL_CAPITAL_USD,
    CIBO_MAXIMUM_CAPABILITY_TRADERS,
    CiboMaximumCapabilityRunEvidence,
    CiboSingleAccountMaximumCapabilityProtocol,
    DEFAULT_CIBO_SINGLE_ACCOUNT_MAXIMUM_CAPABILITY_PROTOCOL,
)


def test_protocol_is_one_shared_usd60_account_for_exact_seven_traders() -> None:
    protocol = DEFAULT_CIBO_SINGLE_ACCOUNT_MAXIMUM_CAPABILITY_PROTOCOL

    assert protocol.initial_capital_usd == Decimal("60")
    assert protocol.account_count == 1
    assert protocol.trader_ids == CIBO_MAXIMUM_CAPABILITY_TRADERS
    assert len(protocol.trader_ids) == 7
    assert protocol.capital_reset_allowed is False
    assert protocol.continuous_realized_profit_compound is True
    assert protocol.shared_portfolio_state is True
    assert protocol.shared_qore_risk_state is True
    assert protocol.sovereign_cibo_required is True
    assert protocol.full_cognitive_semantics_required is True
    assert protocol.target_capital_used_for_tuning is False


def test_protocol_rejects_capital_reset() -> None:
    with pytest.raises(CiboCapitalManagementError):
        CiboSingleAccountMaximumCapabilityProtocol(
            capital_reset_allowed=True,
        )


def test_protocol_rejects_trader_surface_drift() -> None:
    with pytest.raises(CiboCapitalManagementError):
        CiboSingleAccountMaximumCapabilityProtocol(
            trader_ids=(
                TraderLineage.VT08_FOREX,
                TraderLineage.R34_XAUUSD,
            ),
        )


def test_run_evidence_requires_every_decision_to_use_sovereign_cibo() -> None:
    with pytest.raises(CiboCapitalManagementError):
        CiboMaximumCapabilityRunEvidence(
            protocol=DEFAULT_CIBO_SINGLE_ACCOUNT_MAXIMUM_CAPABILITY_PROTOCOL,
            account_identity="research:single-account",
            opportunity_decision_count=3368,
            sovereign_runtime_evaluation_count=3367,
            full_semantic_decision_count=3368,
            trader_ids_observed=CIBO_MAXIMUM_CAPABILITY_TRADERS,
            account_reset_count=0,
            economic_era_reset_count=0,
            ending_capital_usd=Decimal("100"),
            peak_capital_usd=Decimal("110"),
            maximum_drawdown_usd=Decimal("10"),
            settled_operation_count=100,
            qore_risk_reduce_count=1,
            qore_risk_reject_count=1,
            compound_reinvestment_count=10,
            portfolio_compound_reinvestment_count=5,
        )


def test_run_evidence_rejects_era_reset_even_if_final_capital_is_large() -> None:
    with pytest.raises(CiboCapitalManagementError):
        CiboMaximumCapabilityRunEvidence(
            protocol=DEFAULT_CIBO_SINGLE_ACCOUNT_MAXIMUM_CAPABILITY_PROTOCOL,
            account_identity="research:single-account",
            opportunity_decision_count=3368,
            sovereign_runtime_evaluation_count=3368,
            full_semantic_decision_count=3368,
            trader_ids_observed=CIBO_MAXIMUM_CAPABILITY_TRADERS,
            account_reset_count=0,
            economic_era_reset_count=1,
            ending_capital_usd=Decimal("50000"),
            peak_capital_usd=Decimal("52000"),
            maximum_drawdown_usd=Decimal("2000"),
            settled_operation_count=2200,
            qore_risk_reduce_count=10,
            qore_risk_reject_count=10,
            compound_reinvestment_count=1000,
            portfolio_compound_reinvestment_count=800,
        )


def test_valid_run_reports_multiple_and_drawdown_fraction() -> None:
    evidence = CiboMaximumCapabilityRunEvidence(
        protocol=DEFAULT_CIBO_SINGLE_ACCOUNT_MAXIMUM_CAPABILITY_PROTOCOL,
        account_identity="research:single-account",
        opportunity_decision_count=3368,
        sovereign_runtime_evaluation_count=3368,
        full_semantic_decision_count=3368,
        trader_ids_observed=CIBO_MAXIMUM_CAPABILITY_TRADERS,
        account_reset_count=0,
        economic_era_reset_count=0,
        ending_capital_usd=Decimal("50000"),
        peak_capital_usd=Decimal("52000"),
        maximum_drawdown_usd=Decimal("2000"),
        settled_operation_count=2200,
        qore_risk_reduce_count=10,
        qore_risk_reject_count=10,
        compound_reinvestment_count=1000,
        portfolio_compound_reinvestment_count=800,
    )

    assert evidence.capital_multiple == Decimal("50000") / Decimal("60")
    assert evidence.maximum_drawdown_fraction_of_peak == Decimal("2000") / Decimal("52000")
    assert evidence.geometric_growth_per_settled_operation is not None
    assert CIBO_MAXIMUM_CAPABILITY_INITIAL_CAPITAL_USD == Decimal("60")
