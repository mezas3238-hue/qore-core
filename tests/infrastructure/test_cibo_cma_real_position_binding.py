from decimal import Decimal

import pytest

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import CapitalStage
from qore.infrastructure.cibo_cma_real_position_binding import (
    CmaOpenPositionEvidence,
    CmaRealPositionBindingError,
    observe_closed_position,
    observe_open_position,
)
from qore.infrastructure.cibo_cma_settlement_ledger import (
    CmaSettlementRecord,
    CmaSettlementState,
    apply_settlement,
)


def _open(**overrides: object) -> CmaOpenPositionEvidence:
    values: dict[str, object] = {
        "trader_id": TraderLineage.R38_EURUSD,
        "signal_fingerprint": "signal-1",
        "qore_symbol": "EURUSD",
        "position_id": 101,
        "side": "long",
        "entry_price": Decimal("100"),
        "current_stop": Decimal("95"),
        "initial_volume": Decimal("0.20"),
        "remaining_volume": Decimal("0.20"),
        "tick_size": Decimal("1"),
        "tick_value": Decimal("10"),
        "broker_position_reconciled": True,
        "broker_stop_reconciled": True,
        "mutation_outcome_unknown": False,
    }
    values.update(overrides)
    return CmaOpenPositionEvidence(**values)  # type: ignore[arg-type]


def _settlement(
    *,
    net: str,
    closed: bool = False,
) -> CmaSettlementState:
    state = CmaSettlementState(
        signal_fingerprint="signal-1",
        position_id=101,
    )
    return apply_settlement(
        state,
        CmaSettlementRecord(
            event=(
                "CTRADER_DEMO_EXIT_SETTLEMENT"
                if closed
                else "CTRADER_DEMO_PARTIAL_SETTLEMENT"
            ),
            deal_id=1,
            signal_fingerprint="signal-1",
            position_id=101,
            net_profit_usd=Decimal(net),
            position_open_after=not closed,
        ),
    )


def test_untouched_seed_uses_zero_realized_and_live_stop_floor() -> None:
    observation = observe_open_position(_open())

    assert observation.stage is CapitalStage.PROTECT_BASE
    assert observation.evidence_sufficient is True
    assert observation.realized_net_pnl_usd == Decimal("0")
    assert observation.base_capital_at_risk_usd == Decimal("10")


def test_protected_stop_can_prove_self_financing_capacity() -> None:
    observation = observe_open_position(
        _open(current_stop=Decimal("103"))
    )

    assert observation.stage is CapitalStage.CAPITALIZE
    assert observation.expansion_eligible is True
    assert observation.self_financing_capacity_usd == Decimal("6")


def test_partial_volume_without_settlement_fails_closed() -> None:
    observation = observe_open_position(
        _open(remaining_volume=Decimal("0.10"))
    )

    assert observation.stage is CapitalStage.OBSERVE
    assert observation.evidence_sufficient is False
    assert observation.expansion_eligible is False


def test_partial_realized_profit_combines_with_remaining_stop_floor() -> None:
    observation = observe_open_position(
        _open(
            remaining_volume=Decimal("0.10"),
            settlement_state=_settlement(net="8"),
        )
    )

    assert observation.realized_net_pnl_usd == Decimal("8")
    assert observation.net_economic_floor_usd == Decimal("3")
    assert observation.stage is CapitalStage.CAPITALIZE
    assert observation.self_financing_capacity_usd == Decimal("3")


def test_missing_broker_stop_never_proves_recovery() -> None:
    observation = observe_open_position(
        _open(current_stop=Decimal("0"))
    )

    assert observation.stage is CapitalStage.OBSERVE
    assert observation.evidence_sufficient is False


def test_unknown_mutation_fails_closed() -> None:
    observation = observe_open_position(
        _open(
            current_stop=Decimal("103"),
            mutation_outcome_unknown=True,
        )
    )

    assert observation.evidence_sufficient is False
    assert observation.expansion_eligible is False


def test_terminal_settlement_closes_lifecycle_to_release() -> None:
    observation = observe_closed_position(
        trader_id=TraderLineage.R38_EURUSD,
        qore_symbol="EURUSD",
        settlement_state=_settlement(net="12", closed=True),
    )

    assert observation.stage is CapitalStage.RELEASE
    assert observation.realized_net_pnl_usd == Decimal("12")
    assert observation.evidence_sufficient is True


def test_open_position_rejects_terminal_settlement_state() -> None:
    with pytest.raises(CmaRealPositionBindingError, match="terminal"):
        _open(settlement_state=_settlement(net="12", closed=True))
