from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from qore.infrastructure.fundednext_mt5 import (
    FundedNextMt5OrderPlan,
    Mt5ExecutionBlockedError,
    Mt5ProviderOutcome,
)
from qore.infrastructure.fundednext_mt5_transport import (
    MetaTrader5FundedNextTransport,
)
from qore.infrastructure.order_intent import OrderSide, OrderType

_NOW = datetime(2026, 9, 14, 4, 0, tzinfo=UTC)


@dataclass
class _Terminal:
    connected: bool = True
    trade_allowed: bool = True
    tradeapi_disabled: bool = False


@dataclass
class _Account:
    login: int = 123456
    server: str = "FundedNext-Server"
    balance: float = 2000.0
    equity: float = 1995.0
    margin: float = 20.0
    margin_free: float = 1975.0
    trade_allowed: bool = True
    trade_expert: bool = True


@dataclass
class _Symbol:
    name: str = "GBPUSD.a"
    digits: int = 5
    point: float = 0.00001
    trade_contract_size: float = 100000.0
    trade_tick_size: float = 0.00001
    trade_tick_value: float = 1.0
    volume_min: float = 0.01
    volume_max: float = 100.0
    volume_step: float = 0.01
    trade_stops_level: int = 10
    trade_freeze_level: int = 0
    trade_mode: int = 1
    filling_mode: int = 2
    trade_exemode: int = 2


@dataclass
class _Tick:
    bid: float = 1.24990
    ask: float = 1.25010


@dataclass
class _Result:
    retcode: int
    order: int = 0
    comment: str = ""


@dataclass
class _Order:
    ticket: int
    magic: int
    comment: str
    state: int


@dataclass
class _Deal:
    order: int
    magic: int
    comment: str


class _Api:
    TRADE_ACTION_DEAL = 1
    TRADE_ACTION_PENDING = 5
    TRADE_ACTION_REMOVE = 8
    ORDER_TYPE_BUY = 0
    ORDER_TYPE_SELL = 1
    ORDER_TYPE_BUY_LIMIT = 2
    ORDER_TYPE_SELL_LIMIT = 3
    ORDER_TIME_GTC = 0
    ORDER_FILLING_FOK = 0
    ORDER_FILLING_IOC = 1
    ORDER_FILLING_RETURN = 2
    SYMBOL_TRADE_MODE_DISABLED = 0
    SYMBOL_TRADE_EXECUTION_MARKET = 2
    TRADE_RETCODE_DONE = 10009
    TRADE_RETCODE_PLACED = 10008
    TRADE_RETCODE_DONE_PARTIAL = 10010
    TRADE_RETCODE_TIMEOUT = 10012
    TRADE_RETCODE_CONNECTION = 10031
    ORDER_STATE_CANCELED = 2
    ORDER_STATE_REJECTED = 3
    ORDER_STATE_FILLED = 4
    ORDER_STATE_PARTIAL = 5

    def __init__(self) -> None:
        self.terminal = _Terminal()
        self.account = _Account()
        self.symbol = _Symbol()
        self.tick = _Tick()
        self.next_result: _Result | None = _Result(self.TRADE_RETCODE_DONE, 9001)
        self.active_orders: tuple[_Order, ...] = ()
        self.history_orders: tuple[_Order, ...] = ()
        self.deals: tuple[_Deal, ...] = ()
        self.last_request: dict[str, object] | None = None

    def terminal_info(self) -> _Terminal | None:
        return self.terminal

    def account_info(self) -> _Account | None:
        return self.account

    def symbols_get(self) -> tuple[_Symbol, ...] | None:
        return (self.symbol,)

    def symbol_select(self, symbol: str, enable: bool) -> bool:
        return enable and symbol == self.symbol.name

    def symbol_info(self, symbol: str) -> _Symbol | None:
        return self.symbol if symbol == self.symbol.name else None

    def symbol_info_tick(self, symbol: str) -> _Tick | None:
        return self.tick if symbol == self.symbol.name else None

    def order_calc_margin(
        self,
        order_type: int,
        symbol: str,
        volume: float,
        price: float,
    ) -> float | None:
        del order_type, symbol, price
        return 50.0 * volume

    def order_send(self, request: dict[str, object]) -> _Result | None:
        self.last_request = request
        return self.next_result

    def orders_get(self) -> tuple[_Order, ...] | None:
        return self.active_orders

    def history_orders_get(
        self,
        date_from: datetime,
        date_to: datetime,
    ) -> tuple[_Order, ...] | None:
        del date_from, date_to
        return self.history_orders

    def history_deals_get(
        self,
        date_from: datetime,
        date_to: datetime,
    ) -> tuple[_Deal, ...] | None:
        del date_from, date_to
        return self.deals


def _transport(api: _Api) -> MetaTrader5FundedNextTransport:
    return MetaTrader5FundedNextTransport(
        api=api,
        qore_account_ref="fn-si-opaque-001",
        expected_login=123456,
        expected_server="FundedNext-Server",
    )


def _plan() -> FundedNextMt5OrderPlan:
    return FundedNextMt5OrderPlan(
        client_order_id="qore-abcdef0123456789",
        qore_symbol="GBPUSD",
        provider_symbol="GBPUSD.a",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        volume=Decimal("0.05"),
        effective_entry=Decimal("1.25010"),
        limit_price=None,
        stop_loss=Decimal("1.24500"),
        take_profit=Decimal("1.26000"),
        margin_required=Decimal("2.50"),
        planned_at=_NOW,
    )


def test_account_and_symbol_are_read_from_bound_terminal() -> None:
    api = _Api()
    transport = _transport(api)
    account = transport.account_state("fn-si-opaque-001")
    assert account is not None
    assert account.equity == Decimal("1995.0")
    assert transport.available_symbols() == ("GBPUSD.a",)
    spec = transport.symbol_info("GBPUSD.a")
    assert spec is not None
    assert spec.tick_size == Decimal("0.00001")
    assert spec.tick_value == Decimal("1.0")
    assert spec.volume_step == Decimal("0.01")
    assert spec.margin_per_volume == Decimal("50.0")


def test_wrong_terminal_identity_fails_closed_before_broker_mutation() -> None:
    api = _Api()
    api.account.login = 999999
    transport = _transport(api)
    assert transport.account_state("fn-si-opaque-001") is None
    with pytest.raises(Mt5ExecutionBlockedError, match="login-mismatch"):
        transport.submit_order(_plan())
    assert api.last_request is None

    api.account.login = 123456
    api.account.server = "Other-Server"
    assert transport.account_state("fn-si-opaque-001") is None
    with pytest.raises(Mt5ExecutionBlockedError, match="server-mismatch"):
        transport.submit_order(_plan())
    assert api.last_request is None


def test_mutation_requires_terminal_python_and_account_trade_permissions() -> None:
    api = _Api()
    transport = _transport(api)

    api.terminal.trade_allowed = False
    with pytest.raises(Mt5ExecutionBlockedError, match="terminal-trading-disabled"):
        transport.submit_order(_plan())
    assert api.last_request is None

    api.terminal.trade_allowed = True
    api.terminal.tradeapi_disabled = True
    with pytest.raises(Mt5ExecutionBlockedError, match="python-trading-disabled"):
        transport.submit_order(_plan())
    assert api.last_request is None

    api.terminal.tradeapi_disabled = False
    api.account.trade_allowed = False
    with pytest.raises(Mt5ExecutionBlockedError, match="account-trading-disabled"):
        transport.submit_order(_plan())
    assert api.last_request is None

    api.account.trade_allowed = True
    api.account.trade_expert = False
    with pytest.raises(Mt5ExecutionBlockedError, match="account-expert-trading-disabled"):
        transport.submit_order(_plan())
    assert api.last_request is None


def test_send_classifies_definitive_and_ambiguous_results() -> None:
    api = _Api()
    transport = _transport(api)
    accepted = transport.submit_order(_plan())
    assert accepted.outcome is Mt5ProviderOutcome.ACCEPTED
    assert accepted.provider_order_ref == "9001"

    api.next_result = _Result(10013)
    rejected = transport.submit_order(_plan())
    assert rejected.outcome is Mt5ProviderOutcome.REJECTED

    api.next_result = _Result(api.TRADE_RETCODE_TIMEOUT)
    timeout = transport.submit_order(_plan())
    assert timeout.outcome is Mt5ProviderOutcome.UNKNOWN

    api.next_result = _Result(api.TRADE_RETCODE_DONE_PARTIAL, 9002)
    partial = transport.submit_order(_plan())
    assert partial.outcome is Mt5ProviderOutcome.UNKNOWN
    assert partial.provider_order_ref == "9002"


def test_cancel_and_discovery_use_same_deterministic_identity() -> None:
    api = _Api()
    transport = _transport(api)
    accepted = transport.submit_order(_plan())
    assert api.last_request is not None
    raw_magic = api.last_request["magic"]
    assert isinstance(raw_magic, int)
    magic = raw_magic
    comment = str(api.last_request["comment"])

    api.active_orders = (
        _Order(ticket=9001, magic=magic, comment=comment, state=1),
    )
    discovered = transport.discover_order(_plan().client_order_id)
    assert discovered is not None
    assert discovered.outcome is Mt5ProviderOutcome.ACCEPTED
    assert discovered.provider_order_ref == accepted.provider_order_ref

    api.next_result = _Result(api.TRADE_RETCODE_DONE, 9001)
    cancelled = transport.cancel_order(
        "9001",
        client_order_id=_plan().client_order_id,
        cancelled_at=_NOW,
    )
    assert cancelled.outcome is Mt5ProviderOutcome.CANCELLED


def test_broker_comment_is_capped_at_fundednext_verified_29_characters() -> None:
    api = _Api()
    transport = _transport(api)
    plan = replace(_plan(), client_order_id="qore-shadow-audjpy-short-probe")
    transport.submit_order(plan)
    assert api.last_request is not None
    comment = str(api.last_request["comment"])
    assert comment == plan.client_order_id[:29]
    assert len(comment) == 29


def test_market_order_uses_live_ioc_when_symbol_advertises_ioc() -> None:
    api = _Api()
    transport = _transport(api)
    transport.submit_order(_plan())
    assert api.last_request is not None
    assert api.last_request["type_filling"] == api.ORDER_FILLING_IOC


def test_market_order_uses_fok_when_symbol_is_fok_only() -> None:
    api = _Api()
    api.symbol.filling_mode = 1
    transport = _transport(api)
    transport.submit_order(_plan())
    assert api.last_request is not None
    assert api.last_request["type_filling"] == api.ORDER_FILLING_FOK


def test_pending_limit_order_uses_return_filling() -> None:
    api = _Api()
    transport = _transport(api)
    plan = replace(
        _plan(),
        order_type=OrderType.LIMIT,
        limit_price=Decimal("1.24900"),
    )
    transport.submit_order(plan)
    assert api.last_request is not None
    assert api.last_request["type_filling"] == api.ORDER_FILLING_RETURN


def test_market_execution_without_ioc_or_fok_fails_closed_before_send() -> None:
    api = _Api()
    api.symbol.filling_mode = 0
    api.symbol.trade_exemode = api.SYMBOL_TRADE_EXECUTION_MARKET
    transport = _transport(api)
    with pytest.raises(Mt5ExecutionBlockedError, match="filling-policy-unavailable"):
        transport.submit_order(_plan())
    assert api.last_request is None


def test_non_market_execution_can_use_return_when_flags_are_absent() -> None:
    api = _Api()
    api.symbol.filling_mode = 0
    api.symbol.trade_exemode = 0
    transport = _transport(api)
    transport.submit_order(_plan())
    assert api.last_request is not None
    assert api.last_request["type_filling"] == api.ORDER_FILLING_RETURN
