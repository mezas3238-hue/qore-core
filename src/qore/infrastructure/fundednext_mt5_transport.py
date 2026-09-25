"""Concrete, secret-free MetaTrader5 adapter for the FundedNext execution port.

Credentials and terminal initialization stay outside QORE Core. The adapter is
constructed with an already initialized MetaTrader5-compatible API object plus
the runtime account identity expected by the Owner activation procedure. Every
mutation re-checks login and server, uses deterministic magic/comment identity,
and classifies timeout/connection/partial-fill acknowledgements as UNKNOWN so
QORE must reconcile before retrying. New orders resolve the broker-advertised
fill policy immediately before submission instead of hard-coding IOC.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from hashlib import sha256
from typing import Protocol

from qore.infrastructure.fundednext_mt5 import (
    FundedNextMt5OrderPlan,
    FundedNextMt5TransportReceipt,
    Mt5AccountState,
    Mt5ExecutionBlockedError,
    Mt5ExecutionValidationError,
    Mt5ProviderOutcome,
    Mt5SymbolSpecification,
)
from qore.infrastructure.order_intent import OrderSide, OrderType

_DISCOVERY_WINDOW = timedelta(days=7)
_SYMBOL_FILLING_FOK_FLAG = 1
_SYMBOL_FILLING_IOC_FLAG = 2


class Mt5TerminalInfoLike(Protocol):
    connected: bool
    trade_allowed: bool
    tradeapi_disabled: bool


class Mt5AccountInfoLike(Protocol):
    login: int
    server: str
    balance: float
    equity: float
    margin: float
    margin_free: float
    trade_allowed: bool
    trade_expert: bool


class Mt5SymbolInfoLike(Protocol):
    name: str
    digits: int
    point: float
    trade_contract_size: float
    trade_tick_size: float
    trade_tick_value: float
    volume_min: float
    volume_max: float
    volume_step: float
    trade_stops_level: int
    trade_freeze_level: int
    trade_mode: int
    filling_mode: int
    trade_exemode: int


class Mt5TickLike(Protocol):
    bid: float
    ask: float


class Mt5OrderResultLike(Protocol):
    retcode: int
    order: int
    comment: str


class Mt5OrderLike(Protocol):
    ticket: int
    magic: int
    comment: str
    state: int


class Mt5DealLike(Protocol):
    order: int
    magic: int
    comment: str


class MetaTrader5Api(Protocol):
    TRADE_ACTION_DEAL: int
    TRADE_ACTION_PENDING: int
    TRADE_ACTION_REMOVE: int
    ORDER_TYPE_BUY: int
    ORDER_TYPE_SELL: int
    ORDER_TYPE_BUY_LIMIT: int
    ORDER_TYPE_SELL_LIMIT: int
    ORDER_TIME_GTC: int
    ORDER_FILLING_FOK: int
    ORDER_FILLING_IOC: int
    ORDER_FILLING_RETURN: int
    SYMBOL_TRADE_MODE_DISABLED: int
    SYMBOL_TRADE_EXECUTION_MARKET: int
    TRADE_RETCODE_DONE: int
    TRADE_RETCODE_PLACED: int
    TRADE_RETCODE_DONE_PARTIAL: int
    TRADE_RETCODE_TIMEOUT: int
    TRADE_RETCODE_CONNECTION: int
    ORDER_STATE_CANCELED: int
    ORDER_STATE_REJECTED: int
    ORDER_STATE_FILLED: int
    ORDER_STATE_PARTIAL: int

    def terminal_info(self) -> Mt5TerminalInfoLike | None: ...

    def account_info(self) -> Mt5AccountInfoLike | None: ...

    def symbols_get(self) -> tuple[Mt5SymbolInfoLike, ...] | None: ...

    def symbol_select(self, symbol: str, enable: bool) -> bool: ...

    def symbol_info(self, symbol: str) -> Mt5SymbolInfoLike | None: ...

    def symbol_info_tick(self, symbol: str) -> Mt5TickLike | None: ...

    def order_calc_margin(
        self,
        order_type: int,
        symbol: str,
        volume: float,
        price: float,
    ) -> float | None: ...

    def order_send(self, request: dict[str, object]) -> Mt5OrderResultLike | None: ...

    def orders_get(self) -> tuple[Mt5OrderLike, ...] | None: ...

    def history_orders_get(
        self,
        date_from: datetime,
        date_to: datetime,
    ) -> tuple[Mt5OrderLike, ...] | None: ...

    def history_deals_get(
        self,
        date_from: datetime,
        date_to: datetime,
    ) -> tuple[Mt5DealLike, ...] | None: ...


class MetaTrader5FundedNextTransport:
    """Account-bound implementation of FundedNextMt5TransportBoundary."""

    def __init__(
        self,
        *,
        api: MetaTrader5Api,
        qore_account_ref: str,
        expected_login: int,
        expected_server: str,
    ) -> None:
        if not isinstance(qore_account_ref, str) or not qore_account_ref:
            raise Mt5ExecutionValidationError("QORE account ref is required")
        if type(expected_login) is not int or expected_login <= 0:
            raise Mt5ExecutionValidationError("expected MT5 login must be positive int")
        if not isinstance(expected_server, str) or not expected_server.strip():
            raise Mt5ExecutionValidationError("expected MT5 server is required")
        self._api = api
        self._qore_account_ref = qore_account_ref
        self._expected_login = expected_login
        self._expected_server = expected_server.strip()

    def connected(self) -> bool:
        terminal = self._api.terminal_info()
        return terminal is not None and bool(terminal.connected)

    def account_state(self, account_ref: str) -> Mt5AccountState | None:
        if account_ref != self._qore_account_ref or not self.connected():
            return None
        account = self._bound_account()
        if account is None:
            return None
        return Mt5AccountState(
            balance=_decimal(account.balance, "balance"),
            equity=_decimal(account.equity, "equity"),
            margin=_decimal(account.margin, "margin"),
            free_margin=_decimal(account.margin_free, "margin_free"),
            observed_at=datetime.now(UTC),
        )

    def available_symbols(self) -> tuple[str, ...]:
        self._require_bound_account()
        symbols = self._api.symbols_get()
        if symbols is None:
            raise Mt5ExecutionBlockedError("mt5-symbol-catalog-unavailable")
        names = tuple(symbol.name for symbol in symbols if symbol.name)
        if not names:
            raise Mt5ExecutionBlockedError("mt5-symbol-catalog-empty")
        return names

    def symbol_info(self, provider_symbol: str) -> Mt5SymbolSpecification | None:
        self._require_bound_account()
        if not self._api.symbol_select(provider_symbol, True):
            return None
        info = self._api.symbol_info(provider_symbol)
        tick = self._api.symbol_info_tick(provider_symbol)
        if info is None or tick is None:
            return None
        bid = _decimal(tick.bid, "bid")
        ask = _decimal(tick.ask, "ask")
        point = _decimal(info.point, "point")
        if point <= 0:
            raise Mt5ExecutionValidationError("MT5 point must be positive")
        spread_points = (ask - bid) / point
        order_type = self._api.ORDER_TYPE_BUY
        margin = self._api.order_calc_margin(order_type, provider_symbol, 1.0, float(ask))
        if margin is None:
            raise Mt5ExecutionBlockedError("mt5-margin-probe-unavailable")
        trade_enabled = info.trade_mode != self._api.SYMBOL_TRADE_MODE_DISABLED
        session_open = bid > 0 and ask > 0
        return Mt5SymbolSpecification(
            provider_symbol=provider_symbol,
            bid=bid,
            ask=ask,
            spread_points=spread_points,
            digits=info.digits,
            point=point,
            contract_size=_decimal(info.trade_contract_size, "contract_size"),
            tick_size=_decimal(info.trade_tick_size, "tick_size"),
            tick_value=_decimal(info.trade_tick_value, "tick_value"),
            minimum_volume=_decimal(info.volume_min, "volume_min"),
            maximum_volume=_decimal(info.volume_max, "volume_max"),
            volume_step=_decimal(info.volume_step, "volume_step"),
            minimum_stop_distance_points=Decimal(info.trade_stops_level),
            freeze_level_points=Decimal(info.trade_freeze_level),
            margin_per_volume=_decimal(margin, "margin_per_volume"),
            trade_enabled=trade_enabled,
            session_open=session_open,
            observed_at=datetime.now(UTC),
        )

    def submit_order(
        self,
        plan: FundedNextMt5OrderPlan,
    ) -> FundedNextMt5TransportReceipt:
        self._require_mutation_permission()
        if not isinstance(plan, FundedNextMt5OrderPlan):
            raise Mt5ExecutionValidationError("MT5 transport requires canonical plan")
        request = self._submission_payload(plan)
        result = self._api.order_send(request)
        recorded_at = datetime.now(UTC)
        if result is None:
            return FundedNextMt5TransportReceipt(
                client_order_id=plan.client_order_id,
                outcome=Mt5ProviderOutcome.UNKNOWN,
                recorded_at=recorded_at,
                reason="mt5-order-send-no-result",
            )
        if result.retcode in {
            self._api.TRADE_RETCODE_TIMEOUT,
            self._api.TRADE_RETCODE_CONNECTION,
            self._api.TRADE_RETCODE_DONE_PARTIAL,
        }:
            return FundedNextMt5TransportReceipt(
                client_order_id=plan.client_order_id,
                outcome=Mt5ProviderOutcome.UNKNOWN,
                recorded_at=recorded_at,
                provider_order_ref=(str(result.order) if result.order > 0 else None),
                reason=f"mt5-nondefinitive-retcode-{result.retcode}",
            )
        if result.retcode in {
            self._api.TRADE_RETCODE_DONE,
            self._api.TRADE_RETCODE_PLACED,
        }:
            if result.order <= 0:
                return FundedNextMt5TransportReceipt(
                    client_order_id=plan.client_order_id,
                    outcome=Mt5ProviderOutcome.UNKNOWN,
                    recorded_at=recorded_at,
                    reason="mt5-success-missing-order-ticket",
                )
            return FundedNextMt5TransportReceipt(
                client_order_id=plan.client_order_id,
                outcome=Mt5ProviderOutcome.ACCEPTED,
                recorded_at=recorded_at,
                provider_order_ref=str(result.order),
            )
        return FundedNextMt5TransportReceipt(
            client_order_id=plan.client_order_id,
            outcome=Mt5ProviderOutcome.REJECTED,
            recorded_at=recorded_at,
            reason=f"mt5-rejected-retcode-{result.retcode}",
        )

    def cancel_order(
        self,
        provider_order_ref: str,
        *,
        client_order_id: str,
        cancelled_at: datetime,
    ) -> FundedNextMt5TransportReceipt:
        self._require_mutation_permission()
        try:
            ticket = int(provider_order_ref)
        except ValueError as error:
            raise Mt5ExecutionValidationError("MT5 order ref must be numeric") from error
        result = self._api.order_send(
            {
                "action": self._api.TRADE_ACTION_REMOVE,
                "order": ticket,
                "magic": _magic(client_order_id),
                "comment": _client_comment(client_order_id),
            }
        )
        if result is not None and result.retcode == self._api.TRADE_RETCODE_DONE:
            return FundedNextMt5TransportReceipt(
                client_order_id=client_order_id,
                outcome=Mt5ProviderOutcome.CANCELLED,
                recorded_at=cancelled_at,
                provider_order_ref=provider_order_ref,
            )
        return FundedNextMt5TransportReceipt(
            client_order_id=client_order_id,
            outcome=Mt5ProviderOutcome.UNKNOWN,
            recorded_at=cancelled_at,
            provider_order_ref=provider_order_ref,
            reason=(
                "mt5-cancel-no-result"
                if result is None
                else f"mt5-cancel-retcode-{result.retcode}"
            ),
        )

    def discover_order(
        self,
        client_order_id: str,
    ) -> FundedNextMt5TransportReceipt | None:
        self._require_bound_account()
        now = datetime.now(UTC)
        magic = _magic(client_order_id)
        comment = _client_comment(client_order_id)

        active = self._api.orders_get()
        if active is None:
            return FundedNextMt5TransportReceipt(
                client_order_id=client_order_id,
                outcome=Mt5ProviderOutcome.UNKNOWN,
                recorded_at=now,
                reason="mt5-order-discovery-active-unavailable",
            )
        for order in active:
            if _matches(order.magic, order.comment, magic, comment):
                return FundedNextMt5TransportReceipt(
                    client_order_id=client_order_id,
                    outcome=Mt5ProviderOutcome.ACCEPTED,
                    recorded_at=now,
                    provider_order_ref=str(order.ticket),
                )

        history = self._api.history_orders_get(now - _DISCOVERY_WINDOW, now)
        if history is None:
            return FundedNextMt5TransportReceipt(
                client_order_id=client_order_id,
                outcome=Mt5ProviderOutcome.UNKNOWN,
                recorded_at=now,
                reason="mt5-order-discovery-history-unavailable",
            )
        for order in reversed(history):
            if not _matches(order.magic, order.comment, magic, comment):
                continue
            if order.state == self._api.ORDER_STATE_CANCELED:
                outcome = Mt5ProviderOutcome.CANCELLED
            elif order.state == self._api.ORDER_STATE_REJECTED:
                outcome = Mt5ProviderOutcome.REJECTED
            elif order.state in {
                self._api.ORDER_STATE_FILLED,
                self._api.ORDER_STATE_PARTIAL,
            }:
                outcome = Mt5ProviderOutcome.ACCEPTED
            else:
                outcome = Mt5ProviderOutcome.UNKNOWN
            return FundedNextMt5TransportReceipt(
                client_order_id=client_order_id,
                outcome=outcome,
                recorded_at=now,
                provider_order_ref=(
                    str(order.ticket)
                    if outcome in {
                        Mt5ProviderOutcome.ACCEPTED,
                        Mt5ProviderOutcome.CANCELLED,
                    }
                    else None
                ),
                reason=(
                    None
                    if outcome is not Mt5ProviderOutcome.UNKNOWN
                    else "mt5-history-state-unknown"
                ),
            )

        deals = self._api.history_deals_get(now - _DISCOVERY_WINDOW, now)
        if deals is None:
            return FundedNextMt5TransportReceipt(
                client_order_id=client_order_id,
                outcome=Mt5ProviderOutcome.UNKNOWN,
                recorded_at=now,
                reason="mt5-order-discovery-deals-unavailable",
            )
        for deal in reversed(deals):
            if _matches(deal.magic, deal.comment, magic, comment):
                return FundedNextMt5TransportReceipt(
                    client_order_id=client_order_id,
                    outcome=Mt5ProviderOutcome.ACCEPTED,
                    recorded_at=now,
                    provider_order_ref=str(deal.order),
                )

        return FundedNextMt5TransportReceipt(
            client_order_id=client_order_id,
            outcome=Mt5ProviderOutcome.UNKNOWN,
            recorded_at=now,
            reason="mt5-order-not-found-conclusive",
        )

    def _bound_account(self) -> Mt5AccountInfoLike | None:
        account = self._api.account_info()
        if account is None:
            return None
        if account.login != self._expected_login:
            return None
        if account.server != self._expected_server:
            return None
        return account

    def _require_bound_account(self) -> Mt5AccountInfoLike:
        if not self.connected():
            raise Mt5ExecutionBlockedError("mt5-disconnected")
        account = self._api.account_info()
        if account is None:
            raise Mt5ExecutionBlockedError("mt5-account-state-unavailable")
        if account.login != self._expected_login:
            raise Mt5ExecutionBlockedError("mt5-account-login-mismatch")
        if account.server != self._expected_server:
            raise Mt5ExecutionBlockedError("mt5-account-server-mismatch")
        return account

    def _require_mutation_permission(self) -> Mt5AccountInfoLike:
        terminal = self._api.terminal_info()
        if terminal is None or not bool(terminal.connected):
            raise Mt5ExecutionBlockedError("mt5-disconnected")
        if not bool(terminal.trade_allowed):
            raise Mt5ExecutionBlockedError("mt5-terminal-trading-disabled")
        if bool(terminal.tradeapi_disabled):
            raise Mt5ExecutionBlockedError("mt5-python-trading-disabled")
        account = self._require_bound_account()
        if not bool(account.trade_allowed):
            raise Mt5ExecutionBlockedError("mt5-account-trading-disabled")
        if not bool(account.trade_expert):
            raise Mt5ExecutionBlockedError("mt5-account-expert-trading-disabled")
        return account

    def _submission_payload(self, plan: FundedNextMt5OrderPlan) -> dict[str, object]:
        if plan.order_type is OrderType.LIMIT:
            action = self._api.TRADE_ACTION_PENDING
            order_type = (
                self._api.ORDER_TYPE_BUY_LIMIT
                if plan.side is OrderSide.BUY
                else self._api.ORDER_TYPE_SELL_LIMIT
            )
            price = plan.limit_price
            assert price is not None
        else:
            action = self._api.TRADE_ACTION_DEAL
            order_type = (
                self._api.ORDER_TYPE_BUY
                if plan.side is OrderSide.BUY
                else self._api.ORDER_TYPE_SELL
            )
            price = plan.effective_entry
        return {
            "action": action,
            "symbol": plan.provider_symbol,
            "volume": float(plan.volume),
            "type": order_type,
            "price": float(price),
            "sl": float(plan.stop_loss),
            "tp": float(plan.take_profit),
            "magic": _magic(plan.client_order_id),
            "comment": _client_comment(plan.client_order_id),
            "type_time": self._api.ORDER_TIME_GTC,
            "type_filling": self._resolve_order_filling(plan),
        }

    def _resolve_order_filling(self, plan: FundedNextMt5OrderPlan) -> int:
        """Resolve a broker-compatible fill mode from fresh live symbol metadata."""

        if plan.order_type is OrderType.LIMIT:
            return self._api.ORDER_FILLING_RETURN
        info = self._api.symbol_info(plan.provider_symbol)
        if info is None:
            raise Mt5ExecutionBlockedError("mt5-filling-policy-symbol-info-unavailable")
        filling_mode = int(info.filling_mode)
        if filling_mode & _SYMBOL_FILLING_IOC_FLAG:
            return self._api.ORDER_FILLING_IOC
        if filling_mode & _SYMBOL_FILLING_FOK_FLAG:
            return self._api.ORDER_FILLING_FOK
        if int(info.trade_exemode) != int(self._api.SYMBOL_TRADE_EXECUTION_MARKET):
            return self._api.ORDER_FILLING_RETURN
        raise Mt5ExecutionBlockedError("mt5-filling-policy-unavailable")


def _client_comment(client_order_id: str) -> str:
    # FundedNext MT5 rejects 30+ character comments; 29 is broker-verified.
    return client_order_id[:29]


def _magic(client_order_id: str) -> int:
    digest = sha256(client_order_id.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") & 0x7FFFFFFF


def _matches(
    actual_magic: int,
    actual_comment: str,
    expected_magic: int,
    expected_comment: str,
) -> bool:
    return actual_magic == expected_magic and actual_comment == expected_comment


def _decimal(value: float, name: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except ValueError as error:
        raise Mt5ExecutionValidationError(f"MT5 {name} is invalid") from error
    if not result.is_finite():
        raise Mt5ExecutionValidationError(f"MT5 {name} must be finite")
    return result
