from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_demo_settlement_observer import (
    DurablePhase20DemoSettlementCursorStore,
    observe_ctrader_demo_phase20_settlements,
)
from qore.infrastructure.cibo_cma_settlement_store import DurableCmaSettlementStore
from qore.infrastructure.ctrader_demo_free_position_service import (
    DemoDeal,
    DemoPosition,
)
from qore.infrastructure.ctrader_demo_trade_registry import (
    CTraderDemoTradeRegistry,
    DemoTradeRegistryEntry,
)

START = datetime(2026, 9, 27, 19, 0, tzinfo=UTC)
POSITION_ID = 901


class _Source:
    def __init__(
        self,
        *,
        positions: tuple[DemoPosition, ...],
        deals: tuple[DemoDeal, ...],
    ) -> None:
        self._positions = positions
        self._deals = deals

    def positions(self) -> tuple[DemoPosition, ...]:
        return self._positions

    def deals(
        self,
        *,
        opened_at: datetime,
        closed_at: datetime,
        max_rows: int = 1000,
    ) -> tuple[DemoDeal, ...]:
        del max_rows
        return tuple(
            item
            for item in self._deals
            if opened_at <= item.executed_at <= closed_at
        )


def _entry(
    *,
    client_order_id: str = "client-901",
    signal: str = "signal-901",
) -> DemoTradeRegistryEntry:
    return DemoTradeRegistryEntry(
        trader=TraderLineage.R34_XAUUSD.value,
        signal_fingerprint=signal,
        request_id=f"request-{client_order_id}",
        client_order_id=client_order_id,
        provider_order_ref=f"provider-{client_order_id}",
        qore_symbol="XAUUSD",
        requested_volume="1",
        requested_stop_risk="10",
        submitted_at=(START + timedelta(seconds=1)).isoformat(),
        expires_at=(START + timedelta(minutes=1)).isoformat(),
        position_id=POSITION_ID,
    )


def _registry(path: Path) -> CTraderDemoTradeRegistry:
    registry = CTraderDemoTradeRegistry(path)
    registry.register(_entry())
    return registry


def _deal(
    deal_id: int,
    *,
    at_seconds: int,
    commission: str,
    gross: str | None,
    net: str | None,
) -> DemoDeal:
    return DemoDeal(
        deal_id=deal_id,
        order_id=deal_id + 1000,
        position_id=POSITION_ID,
        symbol_id=1,
        side="long",
        volume_units=Decimal("1"),
        filled_units=Decimal("1"),
        execution_price=Decimal("100"),
        executed_at=START + timedelta(seconds=at_seconds),
        gross_profit=None if gross is None else Decimal(gross),
        swap=None if gross is None else Decimal("0"),
        commission=Decimal(commission),
        pnl_conversion_fee=None if gross is None else Decimal("0"),
        net_profit=None if net is None else Decimal(net),
        balance_after=None,
    )


def _open_position() -> DemoPosition:
    return DemoPosition(
        position_id=POSITION_ID,
        trader_id=TraderLineage.R34_XAUUSD,
        qore_symbol="XAUUSD",
        provider_symbol="XAUUSD",
        side="long",
        volume_units=Decimal("1"),
        entry_price=Decimal("100"),
        stop_loss=Decimal("99"),
        take_profit=Decimal("102"),
        opened_at=START + timedelta(seconds=1),
        comment="QORE",
    )


def test_settlement_observer_accumulates_entry_partial_and_terminal_cash(
    tmp_path: Path,
) -> None:
    settlement_store = DurableCmaSettlementStore(tmp_path / "settlements.json")
    cursor_store = DurablePhase20DemoSettlementCursorStore(
        tmp_path / "cursor.json"
    )
    source = _Source(
        positions=(),
        deals=(
            _deal(1, at_seconds=1, commission="-2", gross=None, net=None),
            _deal(2, at_seconds=20, commission="-1", gross="6", net="5"),
            _deal(3, at_seconds=40, commission="-1", gross="21", net="20"),
        ),
    )

    observed = observe_ctrader_demo_phase20_settlements(
        source=source,
        registry=_registry(tmp_path / "registry.json"),
        settlement_store=settlement_store,
        cursor_store=cursor_store,
        initial_cursor=START,
        observed_at=START + timedelta(minutes=1),
    )

    assert observed.entry_cost_deal_ids == (1,)
    assert observed.partial_deal_ids == (2,)
    assert observed.terminal_deal_ids == (3,)
    state = settlement_store.load().state_for(
        signal_fingerprint="signal-901",
        position_id=POSITION_ID,
    )
    assert state is not None
    assert state.position_closed is True
    assert state.realized_net_pnl_usd == Decimal("23")
    assert [item.event for item in state.records] == [
        "CTRADER_DEMO_ENTRY_COST_SETTLEMENT",
        "CTRADER_DEMO_PARTIAL_SETTLEMENT",
        "CTRADER_DEMO_EXIT_SETTLEMENT",
    ]
    assert CTraderDemoTradeRegistry(
        tmp_path / "registry.json"
    ).committed_stop_risk(
        now=START + timedelta(minutes=1),
        provider_order_status=lambda _provider_order_ref: 3,
    ) == Decimal("0")


def test_settlement_observer_restart_is_idempotent(tmp_path: Path) -> None:
    settlement_store = DurableCmaSettlementStore(tmp_path / "settlements.json")
    cursor_store = DurablePhase20DemoSettlementCursorStore(
        tmp_path / "cursor.json"
    )
    registry = _registry(tmp_path / "registry.json")
    source = _Source(
        positions=(),
        deals=(
            _deal(11, at_seconds=1, commission="-2", gross=None, net=None),
            _deal(12, at_seconds=40, commission="-1", gross="21", net="20"),
        ),
    )
    first = observe_ctrader_demo_phase20_settlements(
        source=source,
        registry=registry,
        settlement_store=settlement_store,
        cursor_store=cursor_store,
        initial_cursor=START,
        observed_at=START + timedelta(minutes=1),
    )
    generation = settlement_store.load().generation

    second = observe_ctrader_demo_phase20_settlements(
        source=source,
        registry=CTraderDemoTradeRegistry(tmp_path / "registry.json"),
        settlement_store=DurableCmaSettlementStore(
            tmp_path / "settlements.json"
        ),
        cursor_store=DurablePhase20DemoSettlementCursorStore(
            tmp_path / "cursor.json"
        ),
        initial_cursor=START,
        observed_at=START + timedelta(minutes=2),
    )

    assert first.applied_deal_ids == (11, 12)
    assert second.applied_deal_ids == ()
    assert settlement_store.load().generation == generation


def test_settlement_cursor_does_not_skip_incomplete_close_economics(
    tmp_path: Path,
) -> None:
    incomplete_at = START + timedelta(seconds=30)
    cursor_store = DurablePhase20DemoSettlementCursorStore(
        tmp_path / "cursor.json"
    )
    observed = observe_ctrader_demo_phase20_settlements(
        source=_Source(
            positions=(_open_position(),),
            deals=(
                _deal(
                    21,
                    at_seconds=30,
                    commission="-1",
                    gross="1",
                    net=None,
                ),
            ),
        ),
        registry=_registry(tmp_path / "registry.json"),
        settlement_store=DurableCmaSettlementStore(
            tmp_path / "settlements.json"
        ),
        cursor_store=cursor_store,
        initial_cursor=START,
        observed_at=START + timedelta(minutes=1),
    )

    assert observed.applied_deal_ids == ()
    assert observed.cursor_at == incomplete_at
    assert cursor_store.load(initial_cursor=START).cursor_at == incomplete_at


def test_settlement_observer_rejects_ambiguous_netted_multi_leg_position(
    tmp_path: Path,
) -> None:
    registry = _registry(tmp_path / "registry.json")
    registry.register(
        _entry(
            client_order_id="client-902",
            signal="signal-902",
        )
    )

    with pytest.raises(
        CiboCapitalManagementError,
        match="netted multi-leg",
    ):
        observe_ctrader_demo_phase20_settlements(
            source=_Source(
                positions=(),
                deals=(
                    _deal(
                        31,
                        at_seconds=40,
                        commission="-1",
                        gross="21",
                        net="20",
                    ),
                ),
            ),
            registry=registry,
            settlement_store=DurableCmaSettlementStore(
                tmp_path / "settlements.json"
            ),
            cursor_store=DurablePhase20DemoSettlementCursorStore(
                tmp_path / "cursor.json"
            ),
            initial_cursor=START,
            observed_at=START + timedelta(minutes=1),
        )
