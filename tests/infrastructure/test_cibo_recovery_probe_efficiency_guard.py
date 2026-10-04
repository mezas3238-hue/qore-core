from decimal import Decimal

from qore.infrastructure.cibo_recovery_probe_efficiency_guard import (
    MAX_STOP_RISK_FRACTION_OF_HEADROOM,
    MIN_EXPECTED_VALUE_PER_STOP_RISK,
    evaluate_recovery_probe_efficiency,
)


def test_recovery_probe_guard_accepts_exact_frozen_boundaries() -> None:
    decision = evaluate_recovery_probe_efficiency(
        expected_net_value_usd=Decimal("0.15"),
        stop_risk_usd=Decimal("1"),
        hard_risk_headroom_usd=Decimal("25"),
    )

    assert decision.expected_value_per_stop_risk == MIN_EXPECTED_VALUE_PER_STOP_RISK
    assert (
        decision.stop_risk_fraction_of_headroom
        == MAX_STOP_RISK_FRACTION_OF_HEADROOM
    )
    assert decision.admitted is True
    assert decision.outcome_used is False
    assert decision.risk_authority is False
    assert decision.execution_authority is False


def test_recovery_probe_guard_rejects_weak_value_density() -> None:
    decision = evaluate_recovery_probe_efficiency(
        expected_net_value_usd=Decimal("0.149"),
        stop_risk_usd=Decimal("1"),
        hard_risk_headroom_usd=Decimal("100"),
    )

    assert decision.admitted is False
    assert decision.reason == "EXPECTED_VALUE_PER_STOP_RISK_BELOW_FROZEN_FLOOR"


def test_recovery_probe_guard_rejects_excess_headroom_fraction() -> None:
    decision = evaluate_recovery_probe_efficiency(
        expected_net_value_usd=Decimal("1"),
        stop_risk_usd=Decimal("4.01"),
        hard_risk_headroom_usd=Decimal("100"),
    )

    assert decision.admitted is False
    assert (
        decision.reason
        == "STOP_RISK_FRACTION_OF_HEADROOM_ABOVE_FROZEN_CAP"
    )


def test_recovery_probe_guard_fails_closed_without_capacity() -> None:
    decision = evaluate_recovery_probe_efficiency(
        expected_net_value_usd=Decimal("1"),
        stop_risk_usd=Decimal("1"),
        hard_risk_headroom_usd=Decimal("0"),
    )

    assert decision.admitted is False
    assert decision.scientific_freshness_claimed is False
    assert decision.certification_claimed is False
