from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_causal_expectation import (
    CausalExpectationBasis,
    CausalOpportunityExpectation,
    validate_expectation_before_decision,
)

NOW = datetime(2026, 9, 26, 18, 0, tzinfo=UTC)


def _expectation(**overrides: object) -> CausalOpportunityExpectation:
    values: dict[str, object] = {
        "evidence_id": "frozen-prior:v1",
        "as_of": NOW,
        "basis": CausalExpectationBasis.FROZEN_HISTORICAL_PRIOR,
        "expected_net_value_usd": Decimal("12"),
        "expected_capital_minutes": Decimal("30"),
    }
    values.update(overrides)
    return CausalOpportunityExpectation(**values)  # type: ignore[arg-type]


def test_causal_expectation_accepts_predecision_forecast() -> None:
    expectation = _expectation()
    validate_expectation_before_decision(
        expectation=expectation,
        decision_as_of=NOW,
    )
    assert expectation.expected_net_value_usd == Decimal("12")
    assert expectation.expected_capital_minutes == Decimal("30")


def test_forecast_created_after_decision_is_rejected() -> None:
    expectation = _expectation(as_of=NOW + timedelta(seconds=1))
    with pytest.raises(CiboCapitalManagementError, match="postdate"):
        validate_expectation_before_decision(
            expectation=expectation,
            decision_as_of=NOW,
        )


@pytest.mark.parametrize(
    "field",
    (
        "future_market_used",
        "outcome_used",
        "pnl_used",
        "post_entry_path_used",
    ),
)
def test_outcome_or_future_evidence_is_forbidden(field: str) -> None:
    with pytest.raises(CiboCapitalManagementError, match="future/outcome/PnL"):
        _expectation(**{field: True})


@pytest.mark.parametrize(
    "field",
    (
        "sizing_authority",
        "risk_authority",
        "order_authority",
        "execution_authority",
    ),
)
def test_expectation_cannot_carry_trading_authority(field: str) -> None:
    with pytest.raises(CiboCapitalManagementError, match="trading authority"):
        _expectation(**{field: True})


def test_naive_expectation_timestamp_fails_closed() -> None:
    with pytest.raises(CiboCapitalManagementError, match="timezone-aware"):
        _expectation(as_of=datetime(2026, 9, 26, 18, 0))
