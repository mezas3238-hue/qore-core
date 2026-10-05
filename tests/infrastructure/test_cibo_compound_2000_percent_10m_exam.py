from datetime import UTC, datetime
from decimal import Decimal

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_compound_2000_percent_10m_exam import (
    CIBO_2000_PERCENT_MINIMUM_ENDING_CAPITAL_USD,
    CIBO_2000_PERCENT_REQUIRED_NET_RETURN_PERCENT,
    CiboCompound2000PercentTenMonthExamResult,
    DEFAULT_CIBO_COMPOUND_2000_PERCENT_10M_EXAM,
    add_calendar_months,
)


START = datetime(2026, 1, 31, 12, 0, tzinfo=UTC)


def _result(*, ending: str, last: datetime):
    return CiboCompound2000PercentTenMonthExamResult(
        contract=DEFAULT_CIBO_COMPOUND_2000_PERCENT_10M_EXAM,
        first_decision_at=START,
        last_decision_at=last,
        opportunity_decision_count=2000,
        native_max_intelligence_decision_count=2000,
        full_cf_semantic_decision_count=2000,
        external_ai_call_count=0,
        account_reset_count=0,
        economic_era_reset_count=0,
        ending_capital_usd=Decimal(ending),
        peak_capital_usd=Decimal(ending),
        maximum_drawdown_usd=Decimal("10"),
        settled_operation_count=1500,
    )


def test_2000_percent_means_plus_2000_net_return_from_usd60() -> None:
    result = _result(
        ending="1260",
        last=add_calendar_months(START, 10),
    )

    assert CIBO_2000_PERCENT_REQUIRED_NET_RETURN_PERCENT == Decimal("2000")
    assert CIBO_2000_PERCENT_MINIMUM_ENDING_CAPITAL_USD == Decimal("1260")
    assert result.net_return_percent == Decimal("2000")
    assert result.capital_multiple == Decimal("21")
    assert result.passed is True


def test_exam_rejects_twenty_x_capital_as_only_plus_1900_percent() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="below USD1260",
    ):
        _result(
            ending="1200",
            last=add_calendar_months(START, 10),
        )


def test_exam_rejects_result_after_ten_calendar_months() -> None:
    deadline = add_calendar_months(START, 10)
    late = deadline.replace(day=min(deadline.day + 1, 28))

    with pytest.raises(
        CiboCapitalManagementError,
        match="exceeded 10 calendar months",
    ):
        _result(ending="5000", last=late)


def test_calendar_month_math_clamps_end_of_month() -> None:
    deadline = add_calendar_months(START, 1)

    assert deadline == datetime(2026, 2, 28, 12, 0, tzinfo=UTC)


def test_exam_rejects_external_ai_even_if_threshold_and_time_pass() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="forbids external AI",
    ):
        CiboCompound2000PercentTenMonthExamResult(
            contract=DEFAULT_CIBO_COMPOUND_2000_PERCENT_10M_EXAM,
            first_decision_at=START,
            last_decision_at=add_calendar_months(START, 10),
            opportunity_decision_count=2000,
            native_max_intelligence_decision_count=2000,
            full_cf_semantic_decision_count=2000,
            external_ai_call_count=1,
            account_reset_count=0,
            economic_era_reset_count=0,
            ending_capital_usd=Decimal("1260"),
            peak_capital_usd=Decimal("1260"),
            maximum_drawdown_usd=Decimal("10"),
            settled_operation_count=1500,
        )
