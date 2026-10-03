from decimal import Decimal

import pytest

from qore.infrastructure.cibo_protected_reinvestment_policy import (
    DYNAMIC_CURRENT_CAPITAL_SCALING,
    ELIGIBLE_SIDES,
    LONG_MAX_EXPECTED_CAPITAL_MINUTES,
    LONG_MIN_EXPECTED_NET_VALUE_USD,
    MAX_CAPITAL_NEED_TO_CURRENT_CAPITAL_RATIO,
    PROTECTED_LOSS_RESERVE_STOP_RISK_RATIO,
    SHORT_MAX_EXPECTED_CAPITAL_MINUTES,
    SHORT_MIN_EXPECTED_NET_VALUE_USD,
    USD60_MAX_CAPITAL_NEED_USD,
    maximum_reinvestment_capital_need_usd,
    protected_loss_reserve_usd,
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


def test_v2_reference_limits() -> None:
    assert MAX_CAPITAL_NEED_TO_CURRENT_CAPITAL_RATIO == Decimal("0.04")
    assert USD60_MAX_CAPITAL_NEED_USD == Decimal("2.40")
    assert maximum_reinvestment_capital_need_usd(
        Decimal("60")
    ) == Decimal("2.40")
    assert maximum_reinvestment_capital_need_usd(
        Decimal("100")
    ) == Decimal("4.00")


def test_v2_long_gate_is_causal_and_fail_closed() -> None:
    assert ELIGIBLE_SIDES == ("long", "short")
    assert protected_reinvestment_candidate_allowed(
        side="long",
        capital_need_usd=Decimal("2.40"),
        eligible_current_capital_usd=Decimal("60"),
        entry_type="market",
        expected_net_value_usd=LONG_MIN_EXPECTED_NET_VALUE_USD,
        expected_capital_minutes=LONG_MAX_EXPECTED_CAPITAL_MINUTES,
    )
    assert not protected_reinvestment_candidate_allowed(
        side="long",
        capital_need_usd=Decimal("2.40"),
        eligible_current_capital_usd=Decimal("60"),
    )
    assert not protected_reinvestment_candidate_allowed(
        side="long",
        capital_need_usd=Decimal("2.40"),
        eligible_current_capital_usd=Decimal("60"),
        entry_type="limit",
        expected_net_value_usd=LONG_MIN_EXPECTED_NET_VALUE_USD,
        expected_capital_minutes=LONG_MAX_EXPECTED_CAPITAL_MINUTES,
    )
    assert not protected_reinvestment_candidate_allowed(
        side="long",
        capital_need_usd=Decimal("2.40"),
        eligible_current_capital_usd=Decimal("60"),
        entry_type="market",
        expected_net_value_usd=LONG_MIN_EXPECTED_NET_VALUE_USD
        - Decimal("0.000001"),
        expected_capital_minutes=LONG_MAX_EXPECTED_CAPITAL_MINUTES,
    )
    assert not protected_reinvestment_candidate_allowed(
        side="long",
        capital_need_usd=Decimal("2.40"),
        eligible_current_capital_usd=Decimal("60"),
        entry_type="market",
        expected_net_value_usd=LONG_MIN_EXPECTED_NET_VALUE_USD,
        expected_capital_minutes=LONG_MAX_EXPECTED_CAPITAL_MINUTES
        + Decimal("0.000001"),
    )


def test_v2_short_gate_is_causal_and_fail_closed() -> None:
    assert protected_reinvestment_candidate_allowed(
        side="short",
        capital_need_usd=Decimal("2.40"),
        eligible_current_capital_usd=Decimal("60"),
        entry_type="market",
        expected_net_value_usd=SHORT_MIN_EXPECTED_NET_VALUE_USD,
        expected_capital_minutes=SHORT_MAX_EXPECTED_CAPITAL_MINUTES,
    )
    assert not protected_reinvestment_candidate_allowed(
        side="short",
        capital_need_usd=Decimal("2.40"),
        eligible_current_capital_usd=Decimal("60"),
        entry_type="market",
        expected_net_value_usd=SHORT_MIN_EXPECTED_NET_VALUE_USD
        - Decimal("0.000001"),
        expected_capital_minutes=SHORT_MAX_EXPECTED_CAPITAL_MINUTES,
    )
    assert not protected_reinvestment_candidate_allowed(
        side="short",
        capital_need_usd=Decimal("2.40"),
        eligible_current_capital_usd=Decimal("60"),
        entry_type="market",
        expected_net_value_usd=SHORT_MIN_EXPECTED_NET_VALUE_USD,
        expected_capital_minutes=SHORT_MAX_EXPECTED_CAPITAL_MINUTES
        + Decimal("0.000001"),
    )


def test_v2_capital_limit_remains_binding_for_both_sides() -> None:
    for side, expected_net, minutes in (
        (
            "long",
            LONG_MIN_EXPECTED_NET_VALUE_USD,
            LONG_MAX_EXPECTED_CAPITAL_MINUTES,
        ),
        (
            "short",
            SHORT_MIN_EXPECTED_NET_VALUE_USD,
            SHORT_MAX_EXPECTED_CAPITAL_MINUTES,
        ),
    ):
        assert not protected_reinvestment_candidate_allowed(
            side=side,
            capital_need_usd=Decimal("2.40000001"),
            eligible_current_capital_usd=Decimal("60"),
            entry_type="market",
            expected_net_value_usd=expected_net,
            expected_capital_minutes=minutes,
        )


def test_protected_loss_reserve_is_not_deployed_capital() -> None:
    assert PROTECTED_LOSS_RESERVE_STOP_RISK_RATIO == Decimal("0.25")
    assert protected_loss_reserve_usd(Decimal("1.21")) == Decimal("0.3025")
    assert protected_loss_reserve_usd(Decimal("0")) == Decimal("0.00")


@pytest.mark.parametrize(
    "value",
    (Decimal("-1"), Decimal("NaN"), Decimal("Infinity")),
)
def test_protected_loss_reserve_rejects_invalid_stop_risk(
    value: Decimal,
) -> None:
    with pytest.raises(ValueError, match="stop risk"):
        protected_loss_reserve_usd(value)


@pytest.mark.parametrize(
    "value",
    (Decimal("0"), Decimal("-1"), Decimal("NaN"), Decimal("Infinity")),
)
def test_current_capital_must_be_finite_positive(value: Decimal) -> None:
    with pytest.raises(ValueError, match="eligible current capital"):
        maximum_reinvestment_capital_need_usd(value)
