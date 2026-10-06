from decimal import Decimal

from qore.infrastructure.cibo_engine_efficiency_sensor import (
    CiboEngineEfficiencyClass,
    CiboEngineEfficiencyEvidence,
    measure_engine_efficiency,
    rank_engine_efficiency,
)


def test_engine_running_but_not_actuating_is_exposed() -> None:
    report = measure_engine_efficiency(
        CiboEngineEfficiencyEvidence(
            engine_id="GEN-C11",
            eligible_count=100,
            invoked_count=100,
            output_consumed_count=100,
            decision_changed_count=10,
            economically_effective_count=5,
            blocked_count=0,
            marginal_value_usd=Decimal("5"),
            opportunity_value_available_usd=Decimal("100"),
        )
    )

    assert report.classification is CiboEngineEfficiencyClass.LOW_ACTUATION
    assert report.actuation_efficiency == Decimal("0.1")
    assert report.engine_efficiency == Decimal("0.05")


def test_destructive_engine_is_ranked_as_failure_even_if_highly_active() -> None:
    report = measure_engine_efficiency(
        CiboEngineEfficiencyEvidence(
            engine_id="POSITION_LIFECYCLE",
            eligible_count=100,
            invoked_count=100,
            output_consumed_count=100,
            decision_changed_count=90,
            economically_effective_count=90,
            blocked_count=0,
            marginal_value_usd=Decimal("0"),
            opportunity_value_available_usd=Decimal("100"),
            destructive_value_usd=Decimal("40"),
        )
    )

    assert report.classification is CiboEngineEfficiencyClass.DESTRUCTIVE
    assert report.causal_loss_usd == Decimal("140")
    assert report.engine_efficiency == Decimal("0")


def test_blocked_engine_is_identified_separately_from_near_zero() -> None:
    blocked = measure_engine_efficiency(
        CiboEngineEfficiencyEvidence(
            engine_id="T14",
            eligible_count=50,
            invoked_count=0,
            output_consumed_count=0,
            decision_changed_count=0,
            economically_effective_count=0,
            blocked_count=50,
            marginal_value_usd=Decimal("0"),
            opportunity_value_available_usd=Decimal("20"),
        )
    )
    near_zero = measure_engine_efficiency(
        CiboEngineEfficiencyEvidence(
            engine_id="PORTFOLIO",
            eligible_count=50,
            invoked_count=50,
            output_consumed_count=50,
            decision_changed_count=1,
            economically_effective_count=0,
            blocked_count=0,
            marginal_value_usd=Decimal("0"),
            opportunity_value_available_usd=Decimal("20"),
        )
    )

    assert blocked.classification is CiboEngineEfficiencyClass.BLOCKED
    assert near_zero.classification is CiboEngineEfficiencyClass.NEAR_ZERO
    ranked = rank_engine_efficiency((near_zero, blocked))
    assert {item.engine_id for item in ranked} == {"T14", "PORTFOLIO"}
