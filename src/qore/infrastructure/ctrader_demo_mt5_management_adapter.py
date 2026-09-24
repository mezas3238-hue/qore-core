from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from qore.infrastructure.ctrader_demo_free_position_service import CTraderDemoFreePositionService
from qore.infrastructure.ctrader_demo_trade_registry import CTraderDemoTradeRegistry


def _magic(client_order_id: str) -> int:
    digest = hashlib.sha256(client_order_id.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") & 0x7FFFFFFF


class CTraderDemoMt5ManagementAdapter:
    """Expose the narrow MT5 management surface used by frozen Trader logic.

    Reads of market metadata remain delegated to MT5. Position/deal reads and
    SL/TP mutations are translated to the authenticated cTrader DEMO account.
    """

    TRADE_ACTION_DEAL = 1
    TRADE_ACTION_SLTP = 6
    TRADE_RETCODE_PLACED = 10008
    TRADE_RETCODE_DONE = 10009
    TRADE_RETCODE_DONE_PARTIAL = 10010
    TRADE_RETCODE_TIMEOUT = 10012
    TRADE_RETCODE_CONNECTION = 10031
    POSITION_TYPE_BUY = 0
    POSITION_TYPE_SELL = 1
    ORDER_TYPE_BUY = 0
    ORDER_TYPE_SELL = 1
    ORDER_TIME_GTC = 0
    ORDER_FILLING_FOK = 0
    ORDER_FILLING_IOC = 1
    ORDER_FILLING_RETURN = 2
    SYMBOL_TRADE_EXECUTION_MARKET = 2
    DEAL_ENTRY_IN = 0
    DEAL_ENTRY_OUT = 1

    def __init__(
        self,
        *,
        mt5_market_api: Any,
        positions: CTraderDemoFreePositionService,
        registry: CTraderDemoTradeRegistry,
        binding_path: Path,
    ) -> None:
        self._mt5 = mt5_market_api
        self._positions = positions
        self._registry = registry
        raw = json.loads(binding_path.read_text(encoding="utf-8"))
        self._source_contract = {
            str(row["qore_symbol"]): Decimal(str(row["source_contract_size_units"]))
            for row in raw["contracts"]
        }

    def _sync_registry(self) -> tuple[object, ...]:
        rows = self._positions.positions()
        for item in rows:
            known = self._registry.by_position(item.position_id)
            if known is not None:
                continue
            candidates = [
                entry
                for entry in self._registry.entries()
                if entry.position_id is None
                and entry.trader == item.trader_id.value
                and entry.qore_symbol == item.qore_symbol
                and datetime.fromisoformat(entry.submitted_at) <= item.opened_at
            ]
            if candidates:
                latest = max(
                    candidates,
                    key=lambda entry: datetime.fromisoformat(entry.submitted_at),
                )
                self._registry.bind_position(latest.client_order_id, item.position_id)
        return rows

    def positions_get(self, *args: object, **kwargs: object) -> tuple[object, ...]:
        rows = self._sync_registry()
        unrealized_reader = getattr(self._positions, "unrealized_by_position", None)
        unrealized = unrealized_reader() if callable(unrealized_reader) else {}
        out: list[object] = []
        symbol_filter = kwargs.get("symbol")
        for item in rows:
            if symbol_filter is not None:
                norm = "NAS100" if str(symbol_filter) == "NDX100" else str(symbol_filter)
                if item.qore_symbol != norm:
                    continue
            reg = self._registry.by_position(item.position_id)
            if reg is None:
                continue
            source_contract = self._source_contract.get(item.qore_symbol, Decimal("1"))
            source_lots = item.volume_units / source_contract
            out.append(
                SimpleNamespace(
                    ticket=item.position_id,
                    magic=_magic(reg.client_order_id),
                    symbol=item.qore_symbol,
                    type=self.POSITION_TYPE_BUY if item.side == "long" else self.POSITION_TYPE_SELL,
                    sl=float(item.stop_loss or Decimal("0")),
                    tp=float(item.take_profit or Decimal("0")),
                    price_open=float(item.entry_price),
                    volume=float(source_lots),
                    time=int(item.opened_at.timestamp()),
                    time_msc=int(item.opened_at.timestamp() * 1000),
                    profit=float(unrealized.get(item.position_id, Decimal("0"))),
                )
            )
        return tuple(out)

    def history_deals_get(self, start: datetime, end: datetime) -> tuple[object, ...]:
        rows = self._positions.deals(opened_at=start, closed_at=end, max_rows=1000)
        out: list[object] = []
        for item in rows:
            reg = self._registry.by_position(item.position_id)
            if reg is None:
                continue
            closed = item.net_profit is not None
            out.append(
                SimpleNamespace(
                    ticket=item.deal_id,
                    order=item.order_id,
                    position_id=item.position_id,
                    magic=_magic(reg.client_order_id),
                    entry=self.DEAL_ENTRY_OUT if closed else self.DEAL_ENTRY_IN,
                    profit=float(item.net_profit or Decimal("0")),
                    commission=0.0,
                    swap=0.0,
                    time=int(item.executed_at.timestamp()),
                    time_msc=int(item.executed_at.timestamp() * 1000),
                )
            )
        return tuple(out)

    def symbol_info(self, symbol: str) -> object | None:
        provider = "NDX100" if symbol == "NAS100" else symbol
        return self._mt5.symbol_info(provider)

    def symbol_info_tick(self, symbol: str) -> object | None:
        provider = "NDX100" if symbol == "NAS100" else symbol
        return self._mt5.symbol_info_tick(provider)

    def copy_rates_from_pos(self, *args: object, **kwargs: object) -> object:
        return self._mt5.copy_rates_from_pos(*args, **kwargs)

    def copy_rates_range(self, *args: object, **kwargs: object) -> object:
        return self._mt5.copy_rates_range(*args, **kwargs)

    def order_check(self, request: dict[str, object]) -> object:
        action = int(request.get("action", -1))
        position_id = int(request.get("position", 0) or 0)
        known = {int(getattr(item, "ticket")): item for item in self.positions_get()}
        position = known.get(position_id)
        if position is None:
            return SimpleNamespace(retcode=1, comment="unknown cTrader DEMO position")
        if action == self.TRADE_ACTION_SLTP:
            sl = Decimal(str(request.get("sl", 0)))
            tp = Decimal(str(request.get("tp", 0)))
            ok = sl > 0 and tp > 0 and sl != tp
            return SimpleNamespace(retcode=0 if ok else 1, comment="OK" if ok else "invalid SLTP")
        if action == self.TRADE_ACTION_DEAL:
            volume = Decimal(str(request.get("volume", 0)))
            ok = volume > 0 and volume <= Decimal(str(position.volume))
            return SimpleNamespace(retcode=0 if ok else 1, comment="OK" if ok else "invalid close")
        return SimpleNamespace(retcode=1, comment="unsupported cTrader DEMO mutation")

    def order_send(self, request: dict[str, object]) -> object:
        action = int(request.get("action", -1))
        position_id = int(request["position"])
        if action == self.TRADE_ACTION_SLTP:
            self._positions.amend_protection(
                position_id=position_id,
                stop_loss=Decimal(str(request["sl"])),
                take_profit=Decimal(str(request["tp"])),
            )
            return SimpleNamespace(
                retcode=self.TRADE_RETCODE_DONE,
                order=position_id,
                deal=0,
                comment="cTrader DEMO SLTP amended",
            )
        if action == self.TRADE_ACTION_DEAL:
            synthetic = next(
                item for item in self.positions_get()
                if int(getattr(item, "ticket")) == position_id
            )
            qore_symbol = str(getattr(synthetic, "symbol"))
            source_lots = Decimal(str(request["volume"]))
            volume_units = source_lots * self._source_contract[qore_symbol]
            native = next(
                item for item in self._positions.positions()
                if item.position_id == position_id
            )
            if volume_units > native.volume_units:
                return SimpleNamespace(retcode=1, comment="close exceeds DEMO position")
            self._positions.close_position(
                position_id=position_id,
                volume_units=volume_units,
            )
            retcode = (
                self.TRADE_RETCODE_DONE
                if volume_units == native.volume_units
                else self.TRADE_RETCODE_DONE_PARTIAL
            )
            return SimpleNamespace(
                retcode=retcode,
                order=position_id,
                deal=position_id,
                comment="cTrader DEMO position close accepted",
            )
        return SimpleNamespace(retcode=1, comment="forbidden DEMO mutation")

    def pending_order_status(self, provider_order_ref: str) -> int:
        try:
            order_id = int(provider_order_ref)
        except ValueError as error:
            raise RuntimeError("cTrader DEMO provider order ref must be numeric") from error
        return self._positions.order_status(order_id=order_id)

    def cancel_pending_order(self, provider_order_ref: str) -> None:
        try:
            order_id = int(provider_order_ref)
        except ValueError as error:
            raise RuntimeError("cTrader DEMO provider order ref must be numeric") from error
        self._positions.cancel_order(order_id=order_id)

    def close_position_for_magic(self, magic: int) -> bool:
        matches = [item for item in self.positions_get() if int(item.magic) == int(magic)]
        if len(matches) != 1:
            return False
        synthetic = matches[0]
        native = next(
            item for item in self._positions.positions()
            if item.position_id == int(synthetic.ticket)
        )
        self._positions.close_position(
            position_id=native.position_id,
            volume_units=native.volume_units,
        )
        return True
