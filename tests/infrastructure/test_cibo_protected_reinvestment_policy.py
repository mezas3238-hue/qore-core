from decimal import Decimal

import pytest

from qore.infrastructure.cibo_protected_reinvestment_policy import (
    ELIGIBLE_SIDE,
    MAX_CAPITAL_NEED_TO_BASE_RATIO,
    USD60_MAX_CAPITAL_NEED_USD,
    maximum_reinvestment_capital_need_usd,
    protected_reinvestment_candidate_allowed,
)


def test_usd60_calibrated_limit_identity() -> None:
    assert maximum_reinvestment_capital_need_usd(
        Decimal("60")
    ) == USD60_MAX_CAPITAL_NEED_USD
    assert (
        MAX_CAPITAL_NEED_TO_BASE_RATIO * Decimal("60")
        == USD60_MAX_CAPITAL_NEED_USD
    )


def test_policy_is_predecision_and_side_bound() -> None:
    assert ELIGIBLE_SIDE == "long"
    assert protected_reinvestment_candidate_allowed(
        side="long",
        capital_need_usd=USD60_MAX_CAPITAL_NEED_USD,
        opening_base_capital_usd=Decimal("60"),
    )
    assert not protected_reinvestment_candidate_allowed(
        side="short",
        capital_need_usd=Decimal("0.10"),
        opening_base_capital_usd=Decimal("60"),
    )
    assert not protected_reinvestment_candidate_allowed(
        side="long",
        capital_need_usd=USD60_MAX_CAPITAL_NEED_USD + Decimal("0.00000001"),
        opening_base_capital_usd=Decimal("60"),
    )


@pytest.mark.parametrize(
    "value",
    (Decimal("0"), Decimal("-1")),
)
def test_opening_base_must_be_positive(value: Decimal) -> None:
    with pytest.raises(ValueError, match="opening base capital"):
        maximum_reinvestment_capital_need_usd(value)
