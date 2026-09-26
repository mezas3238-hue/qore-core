from decimal import Decimal

import pytest

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import CapitalStage
from qore.infrastructure.cibo_capital_state_machine import (
    CmaStateMachineError,
    derive_stage,
    validate_transition,
)
from qore.infrastructure.cibo_economic_floor import EconomicFloorResult


def _floor(
    *,
    sufficient: bool = True,
    base_at_risk: Decimal | None = Decimal("0"),
    capacity: Decimal | None = Decimal("0"),
) -> EconomicFloorResult:
    return EconomicFloorResult(
        trader_id=TraderLineage.R38_EURUSD,
        signal_fingerprint="signal-1",
        evidence_sufficient=sufficient,
        realized_net_pnl_usd=Decimal("0") if sufficient else None,
        net_economic_floor_usd=capacity if sufficient else None,
        base_capital_at_risk_usd=base_at_risk if sufficient else None,
        protected_open_floor_usd=Decimal("0") if sufficient else None,
        proven_self_financing_capacity_usd=capacity if sufficient else None,
        base_recovered=bool(sufficient and base_at_risk == 0),
        reason="test",
    )


def test_no_seed_stays_at_minimum_seed() -> None:
    decision = derive_stage(
        seed_deployed=False,
        position_open=False,
        floor=None,
    )

    assert decision.stage is CapitalStage.MINIMAL_SEED
    assert decision.expansion_eligible is False


def test_open_position_without_reconciled_floor_stays_observe() -> None:
    decision = derive_stage(
        seed_deployed=True,
        position_open=True,
        floor=_floor(sufficient=False, base_at_risk=None, capacity=None),
    )

    assert decision.stage is CapitalStage.OBSERVE
    assert decision.expansion_eligible is False


def test_base_capital_at_risk_forces_protect_base() -> None:
    decision = derive_stage(
        seed_deployed=True,
        position_open=True,
        floor=_floor(base_at_risk=Decimal("5"), capacity=Decimal("0")),
    )

    assert decision.stage is CapitalStage.PROTECT_BASE
    assert decision.expansion_eligible is False


def test_recovered_base_without_capacity_does_not_expand() -> None:
    decision = derive_stage(
        seed_deployed=True,
        position_open=True,
        floor=_floor(base_at_risk=Decimal("0"), capacity=Decimal("0")),
    )

    assert decision.stage is CapitalStage.BASE_RECOVERED
    assert decision.expansion_eligible is False


def test_proven_capacity_after_recovery_enters_capitalize() -> None:
    decision = derive_stage(
        seed_deployed=True,
        position_open=True,
        floor=_floor(base_at_risk=Decimal("0"), capacity=Decimal("7")),
    )

    assert decision.stage is CapitalStage.CAPITALIZE
    assert decision.expansion_eligible is True


def test_closed_position_moves_to_release() -> None:
    decision = derive_stage(
        seed_deployed=True,
        position_open=False,
        floor=None,
    )

    assert decision.stage is CapitalStage.RELEASE


def test_position_cannot_exist_without_seed_evidence() -> None:
    with pytest.raises(CmaStateMachineError, match="cannot be open"):
        derive_stage(
            seed_deployed=False,
            position_open=True,
            floor=None,
        )


def test_illegal_transition_fails_closed() -> None:
    with pytest.raises(CmaStateMachineError, match="illegal CMA transition"):
        validate_transition(CapitalStage.MINIMAL_SEED, CapitalStage.CAPITALIZE)


def test_release_is_terminal_in_v1() -> None:
    validate_transition(CapitalStage.RELEASE, CapitalStage.RELEASE)

    with pytest.raises(CmaStateMachineError):
        validate_transition(CapitalStage.RELEASE, CapitalStage.CAPITALIZE)


def test_capitalize_can_fail_closed_back_to_observe() -> None:
    validate_transition(CapitalStage.CAPITALIZE, CapitalStage.OBSERVE)


def test_capitalize_can_return_to_protect_base_if_floor_deteriorates() -> None:
    validate_transition(CapitalStage.CAPITALIZE, CapitalStage.PROTECT_BASE)


def test_compound_can_return_to_base_recovered_when_capacity_is_exhausted() -> None:
    validate_transition(
        CapitalStage.COMPOUND_OR_RESERVE,
        CapitalStage.BASE_RECOVERED,
    )
