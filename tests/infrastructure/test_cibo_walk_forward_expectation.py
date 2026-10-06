from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_causal_expectation import (
    CausalExpectationBasis,
)
from qore.infrastructure.cibo_single_account_manifest_settlement import (
    CiboManifestShadowOutcomeObservation,
)
from qore.infrastructure.cibo_walk_forward_expectation import (
    build_walk_forward_expectation,
)

NOW = datetime(2026, 10, 6, 12, 0, tzinfo=UTC)
TRADER = TraderLineage("UNIVERSAL_TRADER_001")


def _observation(
    index: int,
    *,
    outcome_r: str,
    minutes: int,
    trader: str = "UNIVERSAL_TRADER_001",
) -> CiboManifestShadowOutcomeObservation:
    exit_at = NOW - timedelta(minutes=60 - index)
    return CiboManifestShadowOutcomeObservation(
        signal_fingerprint=f"signal-{index}",
        trader_id=trader,
        decision_at=exit_at - timedelta(minutes=minutes + 1),
        entry_at=exit_at - timedelta(minutes=minutes),
        exit_at=exit_at,
        gross_structural_outcome_r=Decimal(outcome_r),
        capital_minutes=Decimal(minutes),
    )


def test_walk_forward_cold_start_is_explicit_and_non_forecast() -> None:
    history = tuple(
        _observation(
            index,
            outcome_r=str(index),
            minutes=10 + index,
        )
        for index in range(1, 5)
    )

    snapshot = build_walk_forward_expectation(
        trader_id=TRADER,
        decision_at=NOW,
        stop_risk_usd=Decimal("2"),
        completed_observations=history,
    )

    assert snapshot.cold_start is True
    assert snapshot.observation_count == 4
    assert snapshot.expected_structural_r is None
    assert (
        snapshot.expectation.basis
        is CausalExpectationBasis.COLD_START_NO_FORECAST
    )
    assert snapshot.expectation.expected_net_value_usd == 0


def test_walk_forward_uses_only_completed_same_trader_history() -> None:
    history = (
        _observation(1, outcome_r="1", minutes=10),
        _observation(2, outcome_r="2", minutes=20),
        _observation(3, outcome_r="-1", minutes=30),
        _observation(4, outcome_r="3", minutes=40),
        _observation(5, outcome_r="0", minutes=50),
        _observation(
            6,
            outcome_r="100",
            minutes=1,
            trader="OTHER_TRADER",
        ),
    )

    snapshot = build_walk_forward_expectation(
        trader_id=TRADER,
        decision_at=NOW,
        stop_risk_usd=Decimal("2"),
        completed_observations=history,
    )

    assert snapshot.cold_start is False
    assert snapshot.observation_count == 5
    assert snapshot.expected_structural_r == Decimal("1")
    assert snapshot.expected_capital_minutes == Decimal("40")
    assert snapshot.expectation.expected_net_value_usd == Decimal("2")
    assert snapshot.expectation.expected_capital_minutes == Decimal("40")
    assert (
        snapshot.expectation.basis
        is CausalExpectationBasis.WALK_FORWARD_EMPIRICAL_FORECAST
    )


def test_walk_forward_rejects_outcome_not_yet_available() -> None:
    future = CiboManifestShadowOutcomeObservation(
        signal_fingerprint="future-signal",
        trader_id=TRADER.value,
        decision_at=NOW - timedelta(minutes=1),
        entry_at=NOW,
        exit_at=NOW + timedelta(minutes=1),
        gross_structural_outcome_r=Decimal("1"),
        capital_minutes=Decimal("1"),
    )

    with pytest.raises(
        CiboCapitalManagementError,
        match="unavailable future outcome",
    ):
        build_walk_forward_expectation(
            trader_id=TRADER,
            decision_at=NOW,
            stop_risk_usd=Decimal("2"),
            completed_observations=(future,) * 5,
        )
