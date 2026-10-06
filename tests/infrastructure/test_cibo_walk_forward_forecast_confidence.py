from decimal import Decimal

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_walk_forward_forecast_confidence import (
    CiboWalkForwardMaturity,
    assess_walk_forward_forecast_confidence,
    walk_forward_mature_observation_count,
)


def test_walk_forward_confidence_keeps_five_observation_forecast_provisional() -> None:
    result = assess_walk_forward_forecast_confidence(
        observation_count=5,
        expected_structural_r=Decimal("0.40"),
        chronological_block_means_r=(
            Decimal("-1"),
            Decimal("0.20"),
            Decimal("0.40"),
            Decimal("0.80"),
            Decimal("1.10"),
        ),
    )

    assert result.maturity is CiboWalkForwardMaturity.PROVISIONAL
    assert result.mature_for_capital_consideration is False
    assert result.positive_block_count == 4
    assert result.nonpositive_block_count == 1
    assert result.block_dispersion_r == Decimal("2.10")
    assert result.maturity_fraction == Decimal("0.2")
    assert result.future_outcome_used is False
    assert result.capital_pnl_used is False
    assert result.sizing_authority is False
    assert result.risk_authority is False
    assert result.execution_authority is False


def test_walk_forward_confidence_requires_five_observations_per_block_for_maturity() -> None:
    provisional = assess_walk_forward_forecast_confidence(
        observation_count=24,
        expected_structural_r=Decimal("0.25"),
        chronological_block_means_r=(
            Decimal("0.10"),
            Decimal("0.20"),
            Decimal("0.25"),
            Decimal("0.30"),
            Decimal("0.40"),
        ),
    )
    mature = assess_walk_forward_forecast_confidence(
        observation_count=25,
        expected_structural_r=Decimal("0.25"),
        chronological_block_means_r=(
            Decimal("0.10"),
            Decimal("0.20"),
            Decimal("0.25"),
            Decimal("0.30"),
            Decimal("0.40"),
        ),
    )

    assert walk_forward_mature_observation_count() == 25
    assert provisional.maturity is CiboWalkForwardMaturity.PROVISIONAL
    assert provisional.mature_for_capital_consideration is False
    assert provisional.maturity_fraction == Decimal("0.96")
    assert mature.maturity is CiboWalkForwardMaturity.MATURE
    assert mature.mature_for_capital_consideration is True
    assert mature.maturity_fraction == Decimal(1)


def test_walk_forward_confidence_preserves_explicit_cold_start() -> None:
    result = assess_walk_forward_forecast_confidence(
        observation_count=4,
        expected_structural_r=None,
        chronological_block_means_r=(),
    )

    assert result.maturity is CiboWalkForwardMaturity.COLD_START
    assert result.mature_for_capital_consideration is False
    assert result.maturity_fraction == Decimal(0)


def test_walk_forward_confidence_rejects_forecast_semantics_during_cold_start() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="cold-start confidence received forecast semantics",
    ):
        assess_walk_forward_forecast_confidence(
            observation_count=4,
            expected_structural_r=Decimal("0.1"),
            chronological_block_means_r=(Decimal("0.1"),) * 5,
        )
