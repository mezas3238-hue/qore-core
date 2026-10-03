from decimal import Decimal

import pytest

from qore.infrastructure.cibo_protected_reinvestment_policy import (
    DYNAMIC_CURRENT_CAPITAL_SCALING,
    ELIGIBLE_SIDE,
    MAX_CAPITAL_NEED_TO_CURRENT_CAPITAL_RATIO,
    USD60_MAX_CAPITAL_NEED_USD,
    maximum_reinvestment_capital_need_usd,
    protected_reinvestment_candidate_allowed,
)


@pytest.mark.parametrize(
    "capital",
    (
        Decimal("60"),
        Decimal("100"),
        Decimal("200"),
        Decimal("500"),
        Decimal("2000"),
        Decimal("5000"),
    ),
)
def test_dynamic_limit_scales_exactly_with_current_realized_capital(
    capital: Decimal,
) -> None:
    assert DYNAMIC_CURRENT_CAPITAL_SCALING is True
    assert maximum_reinvestment_capital_need_usd(capital) == (
        capital * MAX_CAPITAL_NEED_TO_CURRENT_CAPITAL_RATIO
    )


def test_usd60_and_usd100_reference_limits() -> None:
    assert maximum_reinvestment_capital_need_usd(
        Decimal("60")
    ) == USD60_MAX_CAPITAL_NEED_USD
    assert maximum_reinvestment_capital_need_usd(Decimal("100")) == Decimal(
        "3.0069491001082367274812335331333333333333333333333"
    )


def test_policy_is_predecision_and_side_bound() -> None:
    assert ELIGIBLE_SIDE == "long"
    assert protected_reinvestment_candidate_allowed(
        side="long",
        capital_need_usd=USD60_MAX_CAPITAL_NEED_USD,
        eligible_current_capital_usd=Decimal("60"),
    )
    assert not protected_reinvestment_candidate_allowed(
        side="short",
        capital_need_usd=Decimal("0.10"),
        eligible_current_capital_usd=Decimal("60"),
    )
    assert not protected_reinvestment_candidate_allowed(
        side="long",
        capital_need_usd=USD60_MAX_CAPITAL_NEED_USD + Decimal("0.00000001"),
        eligible_current_capital_usd=Decimal("60"),
    )
    assert protected_reinvestment_candidate_allowed(
        side="long",
        capital_need_usd=Decimal("3"),
        eligible_current_capital_usd=Decimal("100"),
    )


@pytest.mark.parametrize(
    "value",
    (Decimal("0"), Decimal("-1"), Decimal("NaN"), Decimal("Infinity")),
)
def test_current_capital_must_be_finite_positive(value: Decimal) -> None:
    with pytest.raises(ValueError, match="eligible current capital"):
        maximum_reinvestment_capital_need_usd(value)
