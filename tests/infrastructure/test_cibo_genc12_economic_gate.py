from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_genc12_economic_gate import (
    GENC12_ECONOMIC_GATE_SHA256,
    Genc12CrisisEconomicObservation,
    Genc12EconomicGateStatus,
    Genc12EconomicRole,
    evaluate_genc12_economic_gate,
)

START = datetime(2026, 9, 30, 19, 0, tzinfo=UTC)
END = datetime(2026, 9, 30, 20, 0, tzinfo=UTC)


def _observation(
    *,
    candidate_id: str,
    role: Genc12EconomicRole,
    net_delta: str = "10",
    drawdown: str = "5",
    plausible_loss: str = "6",
    margin: str = "20",
    lockup: str = "100",
    giveback: str = "4",
    clusters: int = 2,
    provider_failure: str = "0.01",
    minimum_capital: str = "90",
    reserve: str = "15",
    population: str = "1",
) -> Genc12CrisisEconomicObservation:
    return Genc12CrisisEconomicObservation(
        candidate_id=candidate_id,
        role=role,
        population_sha256="sha256:" + population * 64,
        provider_surface_sha256="sha256:" + "2" * 64,
        crisis_factor_set_sha256="sha256:" + "3" * 64,
        horizon_start=START,
        horizon_end=END,
        net_delta_usd=Decimal(net_delta),
        maximum_drawdown_usd=Decimal(drawdown),
        peak_plausible_loss_usd=Decimal(plausible_loss),
        peak_margin_occupancy_usd=Decimal(margin),
        capital_lockup_minutes=Decimal(lockup),
        compound_giveback_usd=Decimal(giveback),
        simultaneous_loss_cluster_count=clusters,
        provider_failure_incidence=Decimal(provider_failure),
        minimum_realized_capital_usd=Decimal(minimum_capital),
        minimum_liquid_reserve_usd=Decimal(reserve),
    )


def _gate(treatment: Genc12CrisisEconomicObservation):
    control = _observation(
        candidate_id="control",
        role=Genc12EconomicRole.CONTROL,
    )
    return evaluate_genc12_economic_gate((control, treatment))


def test_genc12_economic_gate_digest_is_frozen() -> None:
    assert GENC12_ECONOMIC_GATE_SHA256 == (
        "sha256:75cfebe62297b84a709359f64d5093138808fa9732a395b8b97c327ab99921a9"
    )


def test_genc12_safe_strict_improvement_is_research_eligible() -> None:
    treatment = _observation(
        candidate_id="treatment",
        role=Genc12EconomicRole.TREATMENT,
        net_delta="12",
        lockup="90",
        giveback="3",
    )
    row = _gate(treatment).rows[1]
    assert row.status is Genc12EconomicGateStatus.ELIGIBLE_FOR_FURTHER_RESEARCH
    assert row.safety_no_worse is True
    assert row.strict_economic_improvement is True


def test_genc12_more_return_cannot_compensate_worse_drawdown() -> None:
    treatment = _observation(
        candidate_id="treatment",
        role=Genc12EconomicRole.TREATMENT,
        net_delta="100",
        drawdown="5.01",
    )
    row = _gate(treatment).rows[1]
    assert row.status is Genc12EconomicGateStatus.REJECTED_SAFETY_DETERIORATION
    assert "maximum_drawdown_usd" in row.failed_dimensions


def test_genc12_requires_strict_economic_improvement() -> None:
    treatment = _observation(
        candidate_id="treatment",
        role=Genc12EconomicRole.TREATMENT,
    )
    row = _gate(treatment).rows[1]
    assert row.status is (
        Genc12EconomicGateStatus.REJECTED_NO_STRICT_ECONOMIC_IMPROVEMENT
    )


def test_genc12_rejects_different_crisis_population() -> None:
    control = _observation(
        candidate_id="control",
        role=Genc12EconomicRole.CONTROL,
    )
    treatment = _observation(
        candidate_id="treatment",
        role=Genc12EconomicRole.TREATMENT,
        population="9",
        net_delta="12",
    )
    with pytest.raises(
        CiboCapitalManagementError,
        match="identical causal comparison surface",
    ):
        evaluate_genc12_economic_gate((control, treatment))


def test_genc12_rejects_productive_authority_claim() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="governance drift",
    ):
        Genc12CrisisEconomicObservation(
            candidate_id="bad",
            role=Genc12EconomicRole.TREATMENT,
            population_sha256="sha256:" + "1" * 64,
            provider_surface_sha256="sha256:" + "2" * 64,
            crisis_factor_set_sha256="sha256:" + "3" * 64,
            horizon_start=START,
            horizon_end=END,
            net_delta_usd=Decimal("1"),
            maximum_drawdown_usd=Decimal("1"),
            peak_plausible_loss_usd=Decimal("1"),
            peak_margin_occupancy_usd=Decimal("1"),
            capital_lockup_minutes=Decimal("1"),
            compound_giveback_usd=Decimal("1"),
            simultaneous_loss_cluster_count=0,
            provider_failure_incidence=Decimal("0"),
            minimum_realized_capital_usd=Decimal("1"),
            minimum_liquid_reserve_usd=Decimal("1"),
            productive_authority=True,
        )

def test_genc12_row_rejects_manual_status_metric_drift() -> None:
    treatment = _observation(
        candidate_id="treatment",
        role=Genc12EconomicRole.TREATMENT,
        net_delta="12",
    )
    row = _gate(treatment).rows[1]
    with pytest.raises(CiboCapitalManagementError, match="status/metric drift"):
        replace(row, safety_no_worse=False)
