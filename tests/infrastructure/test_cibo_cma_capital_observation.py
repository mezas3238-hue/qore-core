"""Passive CMA capital-observation invariants."""
# ruff: noqa: I001

from decimal import Decimal

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import CapitalStage
from qore.infrastructure.cibo_cma_capital_observation import (
    CmaCapitalObservationInput,
    observe_capital_state,
)


def _evidence(**overrides: object) -> CmaCapitalObservationInput:
    values: dict[str, object] = {
        "trader_id": TraderLineage.R38_EURUSD,
        "signal_fingerprint": "signal-1",
        "qore_symbol": "EURUSD",
        "position_id": 101,
        "seed_deployed": True,
        "position_open": True,
        "realized_net_pnl_usd": Decimal("0"),
        "remaining_stop_worst_case_pnl_usd": Decimal("-5"),
        "future_cost_reserve_usd": Decimal("0"),
        "slippage_reserve_usd": Decimal("0"),
        "broker_position_reconciled": True,
        "protection_reconciled": True,
        "mutation_outcome_unknown": False,
    }
    values.update(overrides)
    return CmaCapitalObservationInput(**values)  # type: ignore[arg-type]


def test_open_negative_floor_stays_protect_base() -> None:
    observation = observe_capital_state(_evidence())

    assert observation.stage is CapitalStage.PROTECT_BASE
    assert observation.evidence_sufficient is True
    assert observation.expansion_eligible is False
    assert observation.base_capital_at_risk_usd == Decimal("5")


def test_recovered_open_floor_can_only_become_shadow_eligible() -> None:
    observation = observe_capital_state(
        _evidence(
            realized_net_pnl_usd=Decimal("10"),
            remaining_stop_worst_case_pnl_usd=Decimal("-2"),
        )
    )

    assert observation.stage is CapitalStage.CAPITALIZE
    assert observation.evidence_sufficient is True
    assert observation.expansion_eligible is True
    assert observation.self_financing_capacity_usd == Decimal("8")
    payload = observation.as_payload()
    assert payload["mutation_authority"] == "NONE_OBSERVATIONAL"
    assert payload["capital_management_authority"] == "CIBO_CMA"


def test_missing_remaining_stop_fails_closed_to_observe() -> None:
    observation = observe_capital_state(
        _evidence(remaining_stop_worst_case_pnl_usd=None)
    )

    assert observation.stage is CapitalStage.OBSERVE
    assert observation.evidence_sufficient is False
    assert observation.expansion_eligible is False


def test_unknown_mutation_never_becomes_expansion_eligible() -> None:
    observation = observe_capital_state(
        _evidence(
            realized_net_pnl_usd=Decimal("20"),
            remaining_stop_worst_case_pnl_usd=Decimal("5"),
            mutation_outcome_unknown=True,
        )
    )

    assert observation.evidence_sufficient is False
    assert observation.expansion_eligible is False


def test_closed_position_moves_to_release_even_after_profit() -> None:
    observation = observe_capital_state(
        _evidence(
            position_open=False,
            realized_net_pnl_usd=Decimal("12"),
            remaining_stop_worst_case_pnl_usd=None,
        )
    )

    assert observation.stage is CapitalStage.RELEASE
    assert observation.evidence_sufficient is True
    assert observation.expansion_eligible is False
    assert observation.self_financing_capacity_usd == Decimal("12")


def test_unreconciled_realized_settlement_fails_closed() -> None:
    observation = observe_capital_state(
        _evidence(
            realized_net_pnl_usd=Decimal("20"),
            remaining_stop_worst_case_pnl_usd=Decimal("5"),
            settlement_reconciled=False,
        )
    )

    assert observation.stage is CapitalStage.OBSERVE
    assert observation.evidence_sufficient is False
    assert observation.expansion_eligible is False
