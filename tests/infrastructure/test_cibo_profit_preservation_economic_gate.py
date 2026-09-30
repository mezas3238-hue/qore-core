from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError
from qore.infrastructure.cibo_profit_preservation_economic_gate import (
    GENC7_ECONOMIC_GATE_SHA256,
    Genc7CausalEconomicObservation,
    Genc7EconomicGateStatus,
    Genc7EconomicRole,
    evaluate_genc7_economic_gate,
)
from qore.infrastructure.cibo_profit_preservation_shadow import (
    Genc7Action,
    genc7_policy_sha256,
)

START = datetime(2026, 9, 30, 20, 0, tzinfo=UTC)
END = datetime(2026, 9, 30, 21, 0, tzinfo=UTC)


def _observation(
    *,
    candidate_id: str,
    role: Genc7EconomicRole,
    action: Genc7Action,
    capital_delta: str = "10",
    profit_delta: str = "8",
    floor: str = "20",
    min_base: str = "90",
    min_compound: str = "15",
    max_dd: str = "5",
    p99_dd: str = "4.5",
    plausible_loss: str = "6",
    provider_cost: str = "2",
    optionality: str = "12",
    retention: str = "0.8",
    giveback: str = "4",
    productivity: str = "1.2",
    population: str = "1",
    causal: bool = True,
) -> Genc7CausalEconomicObservation:
    return Genc7CausalEconomicObservation(
        candidate_id=candidate_id,
        role=role,
        action=action,
        policy_sha256=genc7_policy_sha256(),
        population_sha256="sha256:" + population * 64,
        provider_surface_sha256="sha256:" + "2" * 64,
        fold_ids=("WF1", "WF2", "WF3", "WF4"),
        horizon_start=START,
        horizon_end=END,
        realized_capital_delta_usd=Decimal(capital_delta),
        realized_profit_delta_usd=Decimal(profit_delta),
        ending_protected_floor_usd=Decimal(floor),
        minimum_base_capital_usd=Decimal(min_base),
        minimum_compound_capital_usd=Decimal(min_compound),
        maximum_drawdown_usd=Decimal(max_dd),
        p99_drawdown_usd=Decimal(p99_dd),
        peak_plausible_loss_usd=Decimal(plausible_loss),
        provider_cost_usd=Decimal(provider_cost),
        minimum_optionality_usd=Decimal(optionality),
        profit_retention_ratio=Decimal(retention),
        giveback_usd=Decimal(giveback),
        capital_risk_time_productivity=Decimal(productivity),
        causal_effect_identified=causal,
    )


def _control() -> Genc7CausalEconomicObservation:
    return _observation(
        candidate_id="control",
        role=Genc7EconomicRole.CONTROL,
        action=Genc7Action.HOLD_CURRENT_CAPITAL_STATE,
    )


def test_genc7_economic_gate_digest_is_frozen() -> None:
    assert GENC7_ECONOMIC_GATE_SHA256 == (
        "sha256:68d5e74113c51f8724a50e795e7f24df9f1bebab17ab405d82b492595f107063"
    )


def test_genc7_safe_protect_treatment_is_research_eligible() -> None:
    treatment = _observation(
        candidate_id="protect",
        role=Genc7EconomicRole.TREATMENT,
        action=Genc7Action.PROTECT,
        floor="25",
        retention="0.85",
        giveback="3",
    )
    row = evaluate_genc7_economic_gate((_control(), treatment)).rows[1]
    assert row.status is Genc7EconomicGateStatus.ELIGIBLE_FOR_FURTHER_RESEARCH
    assert row.safety_no_worse is True
    assert row.strict_economic_improvement is True


def test_more_profit_cannot_compensate_worse_base_survival() -> None:
    treatment = _observation(
        candidate_id="compound",
        role=Genc7EconomicRole.TREATMENT,
        action=Genc7Action.COMPOUND,
        capital_delta="50",
        profit_delta="50",
        min_base="89",
    )
    row = evaluate_genc7_economic_gate((_control(), treatment)).rows[1]
    assert row.status is Genc7EconomicGateStatus.REJECTED_SAFETY_DETERIORATION
    assert "minimum_base_capital_usd" in row.failed_dimensions


def test_observed_path_without_causal_effect_is_illegal_for_gate() -> None:
    with pytest.raises(
        CiboCompoundCapitalError,
        match="governance/causal drift",
    ):
        _observation(
            candidate_id="descriptive-only",
            role=Genc7EconomicRole.TREATMENT,
            action=Genc7Action.PROTECT,
            causal=False,
        )


def test_genc7_rejects_mismatched_population() -> None:
    treatment = _observation(
        candidate_id="protect",
        role=Genc7EconomicRole.TREATMENT,
        action=Genc7Action.PROTECT,
        population="9",
        floor="25",
    )
    with pytest.raises(
        CiboCompoundCapitalError,
        match="identical causal comparison surface",
    ):
        evaluate_genc7_economic_gate((_control(), treatment))


def test_treatment_cannot_masquerade_as_hold_control() -> None:
    with pytest.raises(
        CiboCompoundCapitalError,
        match="cannot masquerade",
    ):
        _observation(
            candidate_id="bad",
            role=Genc7EconomicRole.TREATMENT,
            action=Genc7Action.HOLD_CURRENT_CAPITAL_STATE,
        )
