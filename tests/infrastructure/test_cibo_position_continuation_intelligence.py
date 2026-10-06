from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.cibo_position_continuation_intelligence import (
    CiboPositionContinuationInput,
    estimate_position_continuation,
)


T0 = datetime(2026, 10, 4, 12, 0, tzinfo=UTC)


def _input(*, observed_at: datetime) -> CiboPositionContinuationInput:
    return CiboPositionContinuationInput(
        signal_fingerprint="position-1",
        observed_at=observed_at,
        entry_at=T0,
        planned_exit_at=T0 + timedelta(minutes=60),
        entry_expected_net_value_usd=Decimal("6"),
        entry_expected_capital_minutes=Decimal("60"),
        current_stop_risk_usd=Decimal("1"),
        current_margin_usd=Decimal("2"),
        expectation_evidence_sha256="sha256:" + "a" * 64,
    )


def test_continuation_value_decays_only_with_causal_remaining_time() -> None:
    estimate = estimate_position_continuation(
        _input(observed_at=T0 + timedelta(minutes=15))
    )

    assert estimate.remaining_capital_minutes == Decimal("45")
    assert estimate.elapsed_minutes == Decimal("15")
    assert estimate.remaining_fraction_of_entry_horizon == Decimal("0.75")
    assert estimate.expected_continuation_net_value_usd == Decimal("4.50")
    assert estimate.continuation_utility_per_minute == Decimal("0.10")
    assert estimate.value_identified is True
    assert estimate.outcome_used is False


def test_continuation_never_increases_above_entry_expectation() -> None:
    estimate = estimate_position_continuation(
        CiboPositionContinuationInput(
            signal_fingerprint="position-2",
            observed_at=T0,
            entry_at=T0,
            planned_exit_at=T0 + timedelta(minutes=120),
            entry_expected_net_value_usd=Decimal("6"),
            entry_expected_capital_minutes=Decimal("60"),
            current_stop_risk_usd=Decimal("1"),
            current_margin_usd=Decimal("2"),
            expectation_evidence_sha256="sha256:" + "b" * 64,
        )
    )

    assert estimate.remaining_fraction_of_entry_horizon == Decimal("1")
    assert estimate.expected_continuation_net_value_usd == Decimal("6")


def test_continuation_is_zero_and_not_actionable_at_horizon() -> None:
    estimate = estimate_position_continuation(
        _input(observed_at=T0 + timedelta(minutes=60))
    )

    assert estimate.remaining_capital_minutes == Decimal("0")
    assert estimate.expected_continuation_net_value_usd == Decimal("0")
    assert estimate.continuation_utility_per_minute == Decimal("0")
    assert estimate.value_identified is False
