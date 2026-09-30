from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from qore.infrastructure.cibo_adaptive_compound_speed_economic_gate import (
    GENC8_ECONOMIC_GATE_SHA256,
    Genc8EconomicGateStatus,
    Genc8EconomicObservation,
    Genc8EconomicRole,
    evaluate_genc8_economic_gate,
)
from qore.infrastructure.cibo_adaptive_compound_speed_shadow import (
    genc8_policy_sha256,
)
from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError

START = datetime(2026, 9, 30, 19, 0, tzinfo=UTC)
END = datetime(2026, 9, 30, 20, 0, tzinfo=UTC)


def _observation(
    *,
    candidate_id: str,
    role: Genc8EconomicRole,
    ending: str = "110",
    growth: str = "1.10",
    max_dd: str = "5",
    p95_dd: str = "4",
    p99_dd: str = "4.5",
    underwater: str = "100",
    recovery: str = "50",
    productivity: str = "1.2",
    retention: str = "20",
    reserve: str = "15",
    optionality: str = "10",
    provider_cost: str = "2",
    tail_capture: str = "8",
    unnecessary: int = 2,
    missed: int = 4,
    population: str = "1",
) -> Genc8EconomicObservation:
    return Genc8EconomicObservation(
        candidate_id=candidate_id,
        role=role,
        policy_sha256=genc8_policy_sha256(),
        population_sha256="sha256:" + population * 64,
        provider_surface_sha256="sha256:" + "2" * 64,
        fold_ids=("WF1", "WF2", "WF3", "WF4"),
        horizon_start=START,
        horizon_end=END,
        ending_realized_capital_usd=Decimal(ending),
        geometric_growth_factor=Decimal(growth),
        maximum_drawdown_usd=Decimal(max_dd),
        p95_drawdown_usd=Decimal(p95_dd),
        p99_drawdown_usd=Decimal(p99_dd),
        maximum_time_underwater_minutes=Decimal(underwater),
        p95_recovery_minutes=Decimal(recovery),
        capital_risk_time_productivity=Decimal(productivity),
        profit_retention_usd=Decimal(retention),
        minimum_liquid_reserve_usd=Decimal(reserve),
        minimum_optionality_usd=Decimal(optionality),
        provider_cost_usd=Decimal(provider_cost),
        positive_tail_capture_usd=Decimal(tail_capture),
        unnecessary_acceleration_count=unnecessary,
        over_defensive_missed_opportunity_count=missed,
    )


def _gate(treatment: Genc8EconomicObservation):
    control = _observation(
        candidate_id="control",
        role=Genc8EconomicRole.CONTROL,
    )
    return evaluate_genc8_economic_gate((control, treatment))


def test_genc8_economic_gate_digest_is_frozen() -> None:
    assert GENC8_ECONOMIC_GATE_SHA256 == (
        "sha256:57e2434ccf3b7a8aa34fe414366a419bd9924e50c5546cf658cffb6d130bd3a3"
    )


def test_genc8_safe_strict_improvement_is_research_eligible() -> None:
    treatment = _observation(
        candidate_id="treatment",
        role=Genc8EconomicRole.TREATMENT,
        ending="112",
        growth="1.12",
        productivity="1.3",
        missed=3,
    )
    row = _gate(treatment).rows[1]
    assert row.status is Genc8EconomicGateStatus.ELIGIBLE_FOR_FURTHER_RESEARCH
    assert row.safety_no_worse is True
    assert row.strict_economic_improvement is True


def test_genc8_more_growth_cannot_compensate_worse_tail_dd() -> None:
    treatment = _observation(
        candidate_id="treatment",
        role=Genc8EconomicRole.TREATMENT,
        ending="200",
        growth="2",
        p99_dd="4.6",
    )
    row = _gate(treatment).rows[1]
    assert row.status is Genc8EconomicGateStatus.REJECTED_SAFETY_DETERIORATION
    assert "p99_drawdown_usd" in row.failed_dimensions


def test_genc8_more_growth_cannot_compensate_unnecessary_acceleration() -> None:
    treatment = _observation(
        candidate_id="treatment",
        role=Genc8EconomicRole.TREATMENT,
        ending="200",
        growth="2",
        unnecessary=3,
    )
    row = _gate(treatment).rows[1]
    assert row.status is Genc8EconomicGateStatus.REJECTED_SAFETY_DETERIORATION
    assert "unnecessary_acceleration_count" in row.failed_dimensions


def test_genc8_requires_strict_economic_improvement() -> None:
    treatment = _observation(
        candidate_id="treatment",
        role=Genc8EconomicRole.TREATMENT,
    )
    row = _gate(treatment).rows[1]
    assert row.status is (
        Genc8EconomicGateStatus.REJECTED_NO_STRICT_ECONOMIC_IMPROVEMENT
    )


def test_genc8_rejects_different_population() -> None:
    control = _observation(
        candidate_id="control",
        role=Genc8EconomicRole.CONTROL,
    )
    treatment = _observation(
        candidate_id="treatment",
        role=Genc8EconomicRole.TREATMENT,
        ending="112",
        population="9",
    )
    with pytest.raises(
        CiboCompoundCapitalError,
        match="identical causal comparison surface",
    ):
        evaluate_genc8_economic_gate((control, treatment))


def test_genc8_rejects_hindsight_retuning() -> None:
    with pytest.raises(
        CiboCompoundCapitalError,
        match="governance drift",
    ):
        base = _observation(
            candidate_id="bad",
            role=Genc8EconomicRole.TREATMENT,
        )
        Genc8EconomicObservation(
            **{
                name: getattr(base, name)
                for name in base.__dataclass_fields__
                if name != "hindsight_retuned"
            },
            hindsight_retuned=True,
        )
