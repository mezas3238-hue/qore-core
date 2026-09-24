"""DEMO-only position, account and deal service for the free-CIBO lab."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Protocol

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.ctrader_demo_execution_configuration import (
    CTraderDemoRuntimeConfiguration,
)
from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiClientError,
    CTraderOpenApiMessageClientBoundary,
)
from qore.infrastructure.market_test_environment import MarketRuntimeEnvironment
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure

_NATIVE_VOLUME_UNIT = Decimal("0.01")


class CTraderDemoFreePositionError(InfrastructureError):
    __slots__ = ()


@dataclass(frozen=True, slots=True)
class DemoAccountSnapshot:
    balance: Decimal
    gross_unrealized_pnl: Decimal
    net_unrealized_pnl: Decimal
    equity: Decimal
    observed_at: datetime
    def __post_init__(self) -> None:
        for name, value in (
            ("balance", self.balance),
            ("gross_unrealized_pnl", self.gross_unrealized_pnl),
            ("net_unrealized_pnl", self.net_unrealized_pnl),
            ("equity", self.equity),
        ):
            if not isinstance(value, Decimal) or not value.is_finite():
                raise CTraderDemoFreePositionError(f"{name} must be finite Decimal")
        if self.balance <= 0:
            raise CTraderDemoFreePositionError("DEMO balance must be positive")
        _aware(self.observed_at, "observed_at")


@dataclass(frozen=True, slots=True)
class DemoPosition:
    position_id: int
    trader_id: TraderLineage
    qore_symbol: str
    provider_symbol: str
    side: str
    volume_units: Decimal
    entry_price: Decimal
    stop_loss: Decimal | None
    take_profit: Decimal | None
    opened_at: datetime
    comment: str | None

    def __post_init__(self) -> None:
        if type(self.position_id) is not int or self.position_id <= 0:
            raise CTraderDemoFreePositionError("position_id must be positive int")
        if type(self.trader_id) is not TraderLineage:
            raise CTraderDemoFreePositionError("trader_id must be TraderLineage")
        if self.side not in {"long", "short"}:
            raise CTraderDemoFreePositionError("position side invalid")
        if self.volume_units <= 0 or self.entry_price <= 0:
            raise CTraderDemoFreePositionError("position volume/price must be positive")
        _aware(self.opened_at, "opened_at")
@dataclass(frozen=True, slots=True)
class DemoDeal:
    deal_id: int
    order_id: int
    position_id: int
    symbol_id: int
    side: str
    volume_units: Decimal
    filled_units: Decimal
    execution_price: Decimal
    executed_at: datetime
    gross_profit: Decimal | None
    swap: Decimal | None
    commission: Decimal
    pnl_conversion_fee: Decimal | None
    net_profit: Decimal | None
    balance_after: Decimal | None

    @property
    def is_closing(self) -> bool:
        return self.gross_profit is not None


def _aware(value: datetime, name: str) -> None:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise CTraderDemoFreePositionError(f"{name} must be timezone-aware")


def _money(value: object, digits: object, name: str) -> Decimal:
    if type(value) is not int or type(digits) is not int or digits < 0:
        raise CTraderDemoFreePositionError(f"invalid {name} money value")
    return Decimal(value).scaleb(-digits)


def _price(value: object, name: str) -> Decimal:
    if not isinstance(value, (float, int)) or value <= 0:
        raise CTraderDemoFreePositionError(f"invalid {name}")
    return Decimal(str(value))


def _timestamp_ms(value: object, name: str) -> datetime:
    if type(value) is not int or value <= 0:
        raise CTraderDemoFreePositionError(f"invalid {name}")
    return datetime.fromtimestamp(value / 1000, tz=UTC)


def _trader_from_label(label: object) -> TraderLineage | None:
    if not isinstance(label, str) or not label.startswith("QORE:"):
        return None
    raw = label.split(":", 1)[1]
    try:
        return TraderLineage(raw)
    except ValueError as error:
        raise CTraderDemoFreePositionError(
            f"unknown QORE trader label in cTrader DEMO: {raw}"
        ) from error


class CTraderDemoFreePositionService:
    """Read/manage QORE positions only on one authenticated cTrader DEMO account."""

    __slots__ = ("_client", "_configuration", "_symbol_by_id")

    def __init__(
        self,
        *,
        client: CTraderOpenApiMessageClientBoundary,
        configuration: CTraderDemoRuntimeConfiguration,
    ) -> None:
        if configuration.environment is not MarketRuntimeEnvironment.DEMO:
            raise CTraderDemoFreePositionError("position service must remain DEMO-only")
        if int(configuration.account.account_ref) != client.account_id:
            raise CTraderDemoFreePositionError("position service account mismatch")
        self._client = client
        self._configuration = configuration
        self._symbol_by_id = {
            item.symbol_id: (item.instrument.value, item.symbol_name)
            for item in configuration.symbol_mappings
        }

    def _ready(self) -> None:
        if self._client.is_ready:
            return
        result = self._client.connect_and_authenticate()
        if isinstance(result, Failure):
            raise CTraderDemoFreePositionError(str(result.error))
        if not self._client.is_ready:
            raise CTraderDemoFreePositionError("cTrader DEMO client is not ready")

    def _request(
        self,
        name: str,
        fields: dict[str, object],
        *,
        client_msg_id: str,
    ) -> object:
        self._ready()
        result = self._client.request(
            name,
            fields,
            client_msg_id=client_msg_id,
            timeout_seconds=10.0,
        )
        if isinstance(result, Failure):
            raise CTraderDemoFreePositionError(str(result.error))
        return result.value

    def account_snapshot(self, *, observed_at: datetime | None = None) -> DemoAccountSnapshot:
        now = observed_at or datetime.now(UTC)
        _aware(now, "observed_at")
        account_id = self._client.account_id
        trader_res = self._request(
            "ProtoOATraderReq",
            {"ctidTraderAccountId": account_id},
            client_msg_id="qore-demo-free-account",
        )
        trader = getattr(trader_res, "trader", None)
        if trader is None:
            raise CTraderDemoFreePositionError("cTrader trader response missing account")
        digits = getattr(trader, "moneyDigits", 0)
        balance = _money(getattr(trader, "balance", None), digits, "balance")

        pnl_res = self._request(
            "ProtoOAGetPositionUnrealizedPnLReq",
            {"ctidTraderAccountId": account_id},
            client_msg_id="qore-demo-free-unrealized-pnl",
        )
        pnl_digits = getattr(pnl_res, "moneyDigits", 0)
        gross = Decimal("0")
        net = Decimal("0")
        for item in tuple(getattr(pnl_res, "positionUnrealizedPnL", ())):
            gross += _money(
                getattr(item, "grossUnrealizedPnL", None),
                pnl_digits,
                "gross unrealized PnL",
            )
            net += _money(
                getattr(item, "netUnrealizedPnL", None),
                pnl_digits,
                "net unrealized PnL",
            )
        return DemoAccountSnapshot(
            balance=balance,
            gross_unrealized_pnl=gross,
            net_unrealized_pnl=net,
            equity=balance + net,
            observed_at=now,
        )

    def unrealized_by_position(self) -> dict[int, Decimal]:
        response = self._request(
            "ProtoOAGetPositionUnrealizedPnLReq",
            {"ctidTraderAccountId": self._client.account_id},
            client_msg_id="qore-demo-free-unrealized-by-position",
        )
        digits = getattr(response, "moneyDigits", 0)
        rows: dict[int, Decimal] = {}
        for item in tuple(getattr(response, "positionUnrealizedPnL", ())):
            position_id = getattr(item, "positionId", None)
            if type(position_id) is not int or position_id <= 0:
                raise CTraderDemoFreePositionError(
                    "invalid unrealized positionId"
                )
            if position_id in rows:
                raise CTraderDemoFreePositionError(
                    "duplicate unrealized positionId"
                )
            rows[position_id] = _money(
                getattr(item, "netUnrealizedPnL", None),
                digits,
                "net unrealized PnL",
            )
        return rows

    def positions(self) -> tuple[DemoPosition, ...]:
        account_id = self._client.account_id
        response = self._request(
            "ProtoOAReconcileReq",
            {"ctidTraderAccountId": account_id},
            client_msg_id="qore-demo-free-reconcile",
        )
        rows: list[DemoPosition] = []
        for native in tuple(getattr(response, "position", ())):
            trade = getattr(native, "tradeData", None)
            if trade is None:
                continue
            trader_id = _trader_from_label(getattr(trade, "label", None))
            if trader_id is None:
                continue
            symbol_id = getattr(trade, "symbolId", None)
            if type(symbol_id) is not int or symbol_id not in self._symbol_by_id:
                raise CTraderDemoFreePositionError("QORE position has unknown symbol id")
            qore_symbol, provider_symbol = self._symbol_by_id[symbol_id]
            side_value = getattr(trade, "tradeSide", None)
            side = "long" if side_value == 1 else "short" if side_value == 2 else None
            if side is None:
                raise CTraderDemoFreePositionError("QORE position tradeSide invalid")
            volume_raw = getattr(trade, "volume", None)
            if type(volume_raw) is not int or volume_raw <= 0:
                raise CTraderDemoFreePositionError("QORE position volume invalid")
            stop_native = getattr(native, "stopLoss", None)
            target_native = getattr(native, "takeProfit", None)
            stop = (
                Decimal(str(stop_native))
                if isinstance(stop_native, (float, int)) and stop_native > 0
                else None
            )
            target = (
                Decimal(str(target_native))
                if isinstance(target_native, (float, int)) and target_native > 0
                else None
            )
            comment = getattr(trade, "comment", None)
            rows.append(
                DemoPosition(
                    position_id=int(getattr(native, "positionId")),
                    trader_id=trader_id,
                    qore_symbol=qore_symbol,
                    provider_symbol=provider_symbol,
                    side=side,
                    volume_units=Decimal(volume_raw) * _NATIVE_VOLUME_UNIT,
                    entry_price=_price(getattr(native, "price", None), "position price"),
                    stop_loss=stop,
                    take_profit=target,
                    opened_at=_timestamp_ms(
                        getattr(trade, "openTimestamp", None),
                        "position openTimestamp",
                    ),
                    comment=comment if isinstance(comment, str) and comment else None,
                )
            )
        return tuple(sorted(rows, key=lambda item: item.position_id))
    def amend_protection(
        self,
        *,
        position_id: int,
        stop_loss: Decimal,
        take_profit: Decimal,
    ) -> None:
        if type(position_id) is not int or position_id <= 0:
            raise CTraderDemoFreePositionError("position_id must be positive int")
        if stop_loss <= 0 or take_profit <= 0 or stop_loss == take_profit:
            raise CTraderDemoFreePositionError("invalid amended protection geometry")
        response = self._request(
            "ProtoOAAmendPositionSLTPReq",
            {
                "ctidTraderAccountId": self._client.account_id,
                "positionId": position_id,
                "stopLoss": float(stop_loss),
                "takeProfit": float(take_profit),
            },
            client_msg_id=f"qore-demo-free-amend-{position_id}",
        )
        if getattr(response, "executionType", None) not in {2, 3, 11}:
            raise CTraderDemoFreePositionError(
                "cTrader DEMO did not accept position protection amendment"
            )

    def order_status(self, *, order_id: int) -> int:
        if type(order_id) is not int or order_id <= 0:
            raise CTraderDemoFreePositionError("order_id must be positive int")
        response = self._request(
            "ProtoOAOrderDetailsReq",
            {
                "ctidTraderAccountId": self._client.account_id,
                "orderId": order_id,
            },
            client_msg_id=f"qore-demo-free-order-status-{order_id}",
        )
        order = getattr(response, "order", None)
        status = getattr(order, "orderStatus", None) if order is not None else None
        if type(status) is not int:
            raise CTraderDemoFreePositionError("cTrader DEMO order status unavailable")
        return status

    def cancel_order(self, *, order_id: int) -> None:
        if type(order_id) is not int or order_id <= 0:
            raise CTraderDemoFreePositionError("order_id must be positive int")
        response = self._request(
            "ProtoOACancelOrderReq",
            {
                "ctidTraderAccountId": self._client.account_id,
                "orderId": order_id,
            },
            client_msg_id=f"qore-demo-free-cancel-{order_id}",
        )
        if getattr(response, "executionType", None) not in {5, 6, 7}:
            raise CTraderDemoFreePositionError(
                "cTrader DEMO did not confirm pending-order cancellation"
            )

    def close_position(
        self,
        *,
        position_id: int,
        volume_units: Decimal,
    ) -> None:
        if type(position_id) is not int or position_id <= 0:
            raise CTraderDemoFreePositionError("position_id must be positive int")
        if (
            not isinstance(volume_units, Decimal)
            or not volume_units.is_finite()
            or volume_units <= 0
        ):
            raise CTraderDemoFreePositionError("close volume must be positive Decimal")
        native = volume_units / _NATIVE_VOLUME_UNIT
        if native != native.to_integral_value():
            raise CTraderDemoFreePositionError("close volume not representable in cTrader cents")
        response = self._request(
            "ProtoOAClosePositionReq",
            {
                "ctidTraderAccountId": self._client.account_id,
                "positionId": position_id,
                "volume": int(native),
            },
            client_msg_id=f"qore-demo-free-close-{position_id}",
        )
        if getattr(response, "executionType", None) not in {2, 3, 11}:
            raise CTraderDemoFreePositionError("cTrader DEMO did not accept close request")

    def deals(
        self,
        *,
        opened_at: datetime,
        closed_at: datetime,
        max_rows: int = 1000,
    ) -> tuple[DemoDeal, ...]:
        _aware(opened_at, "opened_at")
        _aware(closed_at, "closed_at")
        if closed_at <= opened_at:
            raise CTraderDemoFreePositionError("deal window must be positive")
        if type(max_rows) is not int or not 1 <= max_rows <= 1000:
            raise CTraderDemoFreePositionError("max_rows must be in [1,1000]")
        response = self._request(
            "ProtoOADealListReq",
            {
                "ctidTraderAccountId": self._client.account_id,
                "fromTimestamp": int(opened_at.timestamp() * 1000),
                "toTimestamp": int(closed_at.timestamp() * 1000),
                "maxRows": max_rows,
            },
            client_msg_id="qore-demo-free-deals",
        )
        rows: list[DemoDeal] = []
        for native in tuple(getattr(response, "deal", ())):
            close_detail = None
            has_field = getattr(native, "HasField", None)
            if callable(has_field):
                try:
                    if has_field("closePositionDetail"):
                        close_detail = getattr(native, "closePositionDetail", None)
                except ValueError:
                    close_detail = None
            money_digits = getattr(native, "moneyDigits", 0)
            commission = _money(
                getattr(native, "commission", 0),
                money_digits,
                "deal commission",
            )
            gross = swap = pnl_fee = balance_after = net = None
            if close_detail is not None:
                close_digits = getattr(close_detail, "moneyDigits", money_digits)
                gross = _money(
                    getattr(close_detail, "grossProfit", 0),
                    close_digits,
                    "gross profit",
                )
                swap = _money(
                    getattr(close_detail, "swap", 0),
                    close_digits,
                    "swap",
                )
                close_commission = _money(
                    getattr(close_detail, "commission", 0),
                    close_digits,
                    "close commission",
                )
                pnl_fee = _money(
                    getattr(close_detail, "pnlConversionFee", 0),
                    close_digits,
                    "pnl conversion fee",
                )
                balance_after = _money(
                    getattr(close_detail, "balance", 0),
                    close_digits,
                    "balance after",
                )
                net = gross + swap + close_commission + pnl_fee
                commission = close_commission
            side_value = getattr(native, "tradeSide", None)
            side = "long" if side_value == 1 else "short" if side_value == 2 else None
            if side is None:
                raise CTraderDemoFreePositionError("deal tradeSide invalid")
            volume = getattr(native, "volume", None)
            filled = getattr(native, "filledVolume", None)
            if type(volume) is not int or volume <= 0 or type(filled) is not int or filled <= 0:
                raise CTraderDemoFreePositionError("deal volume invalid")
            rows.append(
                DemoDeal(
                    deal_id=int(getattr(native, "dealId")),
                    order_id=int(getattr(native, "orderId")),
                    position_id=int(getattr(native, "positionId")),
                    symbol_id=int(getattr(native, "symbolId")),
                    side=side,
                    volume_units=Decimal(volume) * _NATIVE_VOLUME_UNIT,
                    filled_units=Decimal(filled) * _NATIVE_VOLUME_UNIT,
                    execution_price=_price(
                        getattr(native, "executionPrice", None),
                        "deal executionPrice",
                    ),
                    executed_at=_timestamp_ms(
                        getattr(native, "executionTimestamp", None),
                        "deal executionTimestamp",
                    ),
                    gross_profit=gross,
                    swap=swap,
                    commission=commission,
                    pnl_conversion_fee=pnl_fee,
                    net_profit=net,
                    balance_after=balance_after,
                )
            )
        return tuple(sorted(rows, key=lambda item: (item.executed_at, item.deal_id)))
