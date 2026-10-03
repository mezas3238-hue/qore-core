from decimal import Decimal

import pytest

from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError
from qore.infrastructure.cibo_compound_constant_statistics import (
    CompoundConstantObservation,
    CompoundConstantSystem,
    summarize_compound_constants,
)


def test_weighted_constant_is_capital_weighted_not_arithmetic_mean() -> None:
    summary = summarize_compound_constants(
        system=CompoundConstantSystem.CIBO_COMPOUND,
        observations=(
            CompoundConstantObservation(
                observation_id="small",
                source_capital_usd=Decimal("10"),
                useful_output_capital_usd=Decimal("5"),
            ),
            CompoundConstantObservation(
                observation_id="large",
                source_capital_usd=Decimal("90"),
                useful_output_capital_usd=Decimal("90"),
            ),
        ),
    )

    assert summary.minimum_constant == Decimal("0.5")
    assert summary.maximum_constant == Decimal("1")
    assert summary.weighted_average_constant == Decimal("0.95")
    assert summary.weighted_average_constant != Decimal("0.75")
    assert summary.total_source_capital_usd == Decimal("100")
    assert summary.total_useful_output_capital_usd == Decimal("95")
    assert summary.minimum_observation_ids == ("small",)
    assert summary.maximum_observation_ids == ("large",)


def test_same_statistic_applies_to_compound_portfolio() -> None:
    summary = summarize_compound_constants(
        system=CompoundConstantSystem.COMPOUND_PORTFOLIO,
        observations=(
            CompoundConstantObservation(
                observation_id="account-a",
                source_capital_usd=Decimal("40"),
                useful_output_capital_usd=Decimal("30"),
            ),
            CompoundConstantObservation(
                observation_id="account-b",
                source_capital_usd=Decimal("60"),
                useful_output_capital_usd=Decimal("30"),
            ),
        ),
    )

    assert summary.minimum_constant == Decimal("0.5")
    assert summary.maximum_constant == Decimal("0.75")
    assert summary.weighted_average_constant == Decimal("0.6")
    assert summary.system is CompoundConstantSystem.COMPOUND_PORTFOLIO
    assert summary.descriptive_only is True
    assert summary.runtime_authority is False


def test_zero_source_capital_is_rejected() -> None:
    with pytest.raises(CiboCompoundCapitalError, match="source capital must be positive"):
        CompoundConstantObservation(
            observation_id="bad",
            source_capital_usd=Decimal("0"),
            useful_output_capital_usd=Decimal("0"),
        )


def test_negative_output_is_rejected() -> None:
    with pytest.raises(
        CiboCompoundCapitalError,
        match="useful output capital must be nonnegative",
    ):
        CompoundConstantObservation(
            observation_id="bad",
            source_capital_usd=Decimal("10"),
            useful_output_capital_usd=Decimal("-1"),
        )
