"""Read-only MetaTrader 5 interface for QDLE.

No order_send, symbol_select, login, credential storage, or position mutation.
Account-state extraction is separated from QORE's treasury authority: MT5 does
NOT expose sovereign/cushion capital segmentation. Such values must be supplied
by the QORE economic ledger, never inferred from an MT5 balance.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Callable, Mapping

from qore.infrastructure.qore_dynamic_lot_engine import (
    BrokerValuation, Position, QDLEAccount, QDLEError, QDLEIntent, QDLESymbol,
)


def _money(value: object, label: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (ValueError, TypeError) as exc:
        raise QDLEError(f"MT5 {label} missing") from exc
    if not result.is_finite():
        raise QDLEError(f"MT5 {label} is not finite")
    return result


@dataclass(frozen=True)
class VerifiedFee:
    usd_per_lot: Decimal
    evidence: str

    def __post_init__(self) -> None:
        if not self.evidence or self.evidence == "ASSUMED":
            raise QDLEError("account-specific fee schedule evidence required")
        if self.usd_per_lot < 0 or not self.usd_per_lot.is_finite():
            raise QDLEError("invalid verified fee")


class MT5ReadOnlyCalculator:
    def __init__(self, mt5: object, account_id: str) -> None:
        self.mt5 = mt5
        self.account_id = account_id

    def _account(self):
        info = self.mt5.account_info()
        if info is None or str(info.login) != self.account_id:
            raise QDLEError("MT5 unavailable or account switched")
        if info.currency != "USD":
            raise QDLEError("MT5 non-USD account requires explicit conversion model")
        return info

    def value(self, instrument: QDLESymbol, intent: QDLEIntent,
              now: datetime) -> BrokerValuation:
        self._account()
        direction = (self.mt5.ORDER_TYPE_BUY if intent.side == "BUY"
                     else self.mt5.ORDER_TYPE_SELL)
        # The probe volume must be on the broker lot grid and inside the max.
        from decimal import ROUND_FLOOR, localcontext
        with localcontext() as ctx:
            ctx.prec = 100
            probe_steps = (min(Decimal(1), instrument.max_lot)
                           / instrument.lot_step).to_integral_value(rounding=ROUND_FLOOR)
            probe = max(instrument.min_lot, probe_steps * instrument.lot_step)
            if probe > instrument.max_lot:
                raise QDLEError("no valid MT5 broker volume for valuation")
        pnl = self.mt5.order_calc_profit(direction, instrument.broker_symbol,
                                         float(probe), float(intent.entry_price),
                                         float(intent.stop_price))
        margin = self.mt5.order_calc_margin(direction, instrument.broker_symbol,
                                            float(probe), float(intent.entry_price))
        if pnl is None or margin is None:
            raise QDLEError(f"MT5 failed profit/margin calculation: {self.mt5.last_error()}")
        pnl_usd, margin_usd = _money(pnl, "stop PnL"), _money(margin, "margin")
        if pnl_usd >= 0 or margin_usd <= 0:
            raise QDLEError("adverse stop must lose money; MT5 margin positive")
        with localcontext() as ctx:
            ctx.prec = 100
            stop_per_lot = -pnl_usd / probe
            margin_per_lot = margin_usd / probe
        return BrokerValuation(stop_per_lot, margin_per_lot,
                               now, "MT5_ORDER_CALC_PROFIT_AND_MARGIN")

    def check_volume(self, instrument: QDLESymbol, intent: QDLEIntent,
                     lots: Decimal) -> None:
        """Non-mutating order_check as an additional gate; not execution proof."""
        self._account()
        side = (self.mt5.ORDER_TYPE_BUY if intent.side == "BUY"
                else self.mt5.ORDER_TYPE_SELL)
        request = {
            "action": self.mt5.TRADE_ACTION_DEAL,
            "symbol": instrument.broker_symbol,
            "type": side,
            "volume": float(lots),
            "price": float(intent.entry_price),
            "sl": float(intent.stop_price),
        }
        result = self.mt5.order_check(request)
        if result is None or int(result.retcode) != 0:
            raise QDLEError(f"MT5 order_check failed: {self.mt5.last_error()}")
        # The broker can still reject later due to price movement or conditions.


def read_mt5_symbols(
    mt5: object,
    aliases_to_symbols: Mapping[str, str],
    fee_quote: Callable[[str, object], VerifiedFee],
    as_of: datetime | None = None,
) -> tuple[QDLESymbol, ...]:
    """Read exactly the resolved MT5 symbols; never guess NAS100 vs NDX100."""
    as_of = as_of or datetime.now(timezone.utc)
    grouped: dict[str, set[str]] = {}
    for alias, symbol in aliases_to_symbols.items():
        if not alias or not symbol:
            raise QDLEError("empty MT5 alias mapping")
        grouped.setdefault(symbol, set()).add(alias)
    instruments = []
    for symbol, aliases in sorted(grouped.items()):
        info = mt5.symbol_info(symbol)
        if info is None:
            raise QDLEError(f"symbol not provided by this MT5 account: {symbol}")
        fee = fee_quote(symbol, info)
        if not isinstance(fee, VerifiedFee):
            raise QDLEError("verified broker fee quote missing")
        instruments.append(QDLESymbol(
            broker_symbol=symbol, aliases=tuple(sorted(aliases | {symbol})),
            min_lot=_money(info.volume_min, "volume_min"),
            max_lot=_money(info.volume_max, "volume_max"),
            lot_step=_money(info.volume_step, "volume_step"),
            directional_volume_limit=_money(info.volume_limit, "volume_limit"),
            tick_size=_money(info.trade_tick_size, "tick_size"),
            tick_value_loss_usd=_money(info.trade_tick_value_loss, "tick_value_loss"),
            contract_size=_money(info.trade_contract_size, "contract_size"),
            currency_profit=str(info.currency_profit),
            fee_usd_per_lot=fee.usd_per_lot, fee_provenance=fee.evidence,
            as_of=as_of,
            tradable=bool(info.visible and info.trade_mode == mt5.SYMBOL_TRADE_MODE_FULL),
        ))
    return tuple(instruments)


def read_mt5_account_with_qore_treasury(
    mt5: object, *, account_id: str, sequence: int,
    qore_unreserved_risk_usd: Decimal,
    sovereign_free_source_usd: Decimal,
    cushion_free_source_usd: Decimal,
    covered_fill_tickets: tuple[str, ...] = (),
    as_of: datetime | None = None,
) -> QDLEAccount:
    """Read broker account and positions, requiring *separate* QORE ledger cash.

    Every pending order is added to the directional exposure count. Margin for
    already-open positions is included in MT5 margin_free. QORE risk/source
    headroom MUST already account for those broker positions and pending orders.
    """
    info = mt5.account_info()
    if info is None or str(info.login) != account_id:
        raise QDLEError("MT5 login mismatch or disconnected")
    raw_positions = mt5.positions_get()
    raw_orders = mt5.orders_get()
    if raw_positions is None or raw_orders is None:
        raise QDLEError("MT5 positions/orders unavailable")
    pos = []
    for p in raw_positions:
        side = "BUY" if p.type == mt5.POSITION_TYPE_BUY else "SELL" if p.type == mt5.POSITION_TYPE_SELL else None
        if side is None:
            raise QDLEError("unrecognized broker position type")
        pos.append(Position(str(p.ticket), str(p.symbol), side, _money(p.volume, "position volume")))
    for p in raw_orders:
        # Pending BUY_LIMIT, BUY_STOP, BUY_STOP_LIMIT; analogous SELL types.
        buys = (mt5.ORDER_TYPE_BUY_LIMIT, mt5.ORDER_TYPE_BUY_STOP,
                mt5.ORDER_TYPE_BUY_STOP_LIMIT)
        sells = (mt5.ORDER_TYPE_SELL_LIMIT, mt5.ORDER_TYPE_SELL_STOP,
                 mt5.ORDER_TYPE_SELL_STOP_LIMIT)
        side = "BUY" if p.type in buys else "SELL" if p.type in sells else None
        if side is None:
            raise QDLEError("unknown MT5 pending order type")
        pos.append(Position("order:" + str(p.ticket), str(p.symbol),
                            side, _money(p.volume_current, "pending volume")))
    return QDLEAccount(
        account_id=account_id, provider="FundedNext", currency=str(info.currency),
        sequence=sequence, as_of=as_of or datetime.now(timezone.utc),
        balance=_money(info.balance, "balance"), equity=_money(info.equity, "equity"),
        free_margin=_money(info.margin_free, "margin free"),
        qore_unreserved_risk_usd=qore_unreserved_risk_usd,
        sovereign_free_source_usd=sovereign_free_source_usd,
        cushion_free_source_usd=cushion_free_source_usd,
        positions=tuple(pos), covered_fill_tickets=covered_fill_tickets,
    )
