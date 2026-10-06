from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase19_dependence import (
    Phase19GeometryOutcome,
    measure_phase19_overlap_dependence,
)
from qore.infrastructure.cibo_ce2i_phase19_portfolio_replay import (
    PHASE19_REQUIRED_TRADERS,
    Phase19ChronologicalOpportunity,
)


def _observation(
    trader: TraderLineage,
    *,
    signal: str,
    entry: datetime,
    duration_minutes: int,
    outcome: str,
) -> Phase19GeometryOutcome:
    opportunity = Phase19ChronologicalOpportunity(
        trader_id=trader,
        signal_fingerprint=signal,
        qore_symbol="TEST",
        entry_at=entry,
        exit_at=entry + timedelta(minutes=duration_minutes),
    )
    return Phase19GeometryOutcome(
        opportunity=opportunity,
        normalized_outcome_r=Decimal(outcome),
        evidence_id=f"evidence:{signal}",
    )


def test_dependence_measures_joint_loss_without_sizing_or_usd() -> None:
    at = datetime(2022, 1, 3, 12, 0, tzinfo=UTC)
    outcomes = ("-1", "-1", "1", "1", "-0.5", "0", "2")
    observations = tuple(
        _observation(
            trader,
            signal=f"s{index}",
            entry=at,
            duration_minutes=30,
            outcome=outcomes[index],
        )
        for index, trader in enumerate(PHASE19_REQUIRED_TRADERS)
    )

    result = measure_phase19_overlap_dependence(observations)

    assert result.total_cross_trader_overlap_pairs == 21
    assert result.outcomes_used is True
    assert result.historical_sizing_used is False
    assert result.usd_pnl_used is False
    assert result.provider_economics_used is False
    assert result.descriptive_only is True
    assert result.allocation_authority is False
    assert result.risk_authority is False
    assert result.execution_authority is False

    first_pair = result.pair_evidence[0]
    assert first_pair.overlapping_pairs == 1
    assert first_pair.left_loss_pairs == 1
    assert first_pair.right_loss_pairs == 1
    assert first_pair.joint_loss_pairs == 1
    assert first_pair.joint_loss_rate == Decimal("1")
    assert first_pair.independent_joint_loss_rate == Decimal("1")
    assert first_pair.joint_loss_excess == Decimal("0")
    assert first_pair.same_nonzero_sign_rate == Decimal("1")


def test_dependence_keeps_zero_overlap_pairs_unscored() -> None:
    base = datetime(2022, 1, 3, 12, 0, tzinfo=UTC)
    observations = tuple(
        _observation(
            trader,
            signal=f"s{index}",
            entry=base + timedelta(hours=index * 2),
            duration_minutes=10,
            outcome="1",
        )
        for index, trader in enumerate(PHASE19_REQUIRED_TRADERS)
    )

    result = measure_phase19_overlap_dependence(observations)

    assert result.total_cross_trader_overlap_pairs == 0
    assert all(item.overlapping_pairs == 0 for item in result.pair_evidence)
    assert all(item.joint_loss_rate is None for item in result.pair_evidence)
    assert all(item.joint_loss_excess is None for item in result.pair_evidence)


def test_dependence_requires_complete_population() -> None:
    at = datetime(2022, 1, 3, 12, 0, tzinfo=UTC)
    observations = tuple(
        _observation(
            trader,
            signal=f"s{index}",
            entry=at,
            duration_minutes=30,
            outcome="1",
        )
        for index, trader in enumerate(PHASE19_REQUIRED_TRADERS[:-1])
    )

    with pytest.raises(CiboCapitalManagementError, match="seven-Trader"):
        measure_phase19_overlap_dependence(observations)


def test_dependence_rejects_duplicate_identity() -> None:
    at = datetime(2022, 1, 3, 12, 0, tzinfo=UTC)
    observations = [
        _observation(
            trader,
            signal=f"s{index}",
            entry=at,
            duration_minutes=30,
            outcome="1",
        )
        for index, trader in enumerate(PHASE19_REQUIRED_TRADERS)
    ]
    duplicate = Phase19GeometryOutcome(
        opportunity=observations[0].opportunity,
        normalized_outcome_r=Decimal("2"),
        evidence_id="other",
    )

    with pytest.raises(CiboCapitalManagementError, match="duplicate"):
        measure_phase19_overlap_dependence(tuple(observations) + (duplicate,))
