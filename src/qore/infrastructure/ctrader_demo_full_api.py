from __future__ import annotations

import re
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from threading import Event, Lock, Thread
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from qore.infrastructure.ctrader_demo_free_binding import CTraderDemoFreeBinding
from qore.infrastructure.ctrader_demo_free_position_service import CTraderDemoFreePositionService
from qore.infrastructure.ctrader_demo_mt5_management_adapter import CTraderDemoMt5ManagementAdapter
from qore.infrastructure.ctrader_demo_trade_registry import CTraderDemoTradeRegistry
from qore.infrastructure.ctrader_open_api_client import CTraderOpenApiMessageClientBoundary
from qore.infrastructure.ctrader_demo_compat import (
    CTraderDemoAccountState,
    CTraderDemoSymbolSpecification,
)
from qore.kernel.result import Failure

_PRICE_SCALE = Decimal("100000")
_VOLUME_UNIT = Decimal("0.01")
_HELSINKI = ZoneInfo("Europe/Helsinki")
_PERIOD_CODE = {60: 1, 300: 5, 900: 7, 1800: 8, 3600: 9, 14400: 10, 86400: 12}


def _norm(value: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", value.upper())


def _legacy_epoch(value: datetime) -> int:
    local = value.astimezone(_HELSINKI).replace(tzinfo=None)
    return int(local.replace(tzinfo=UTC).timestamp())


def _relative_price(bar: object, field: str) -> Decimal:
    low = int(getattr(bar, "low"))
    deltas = {
        "low": 0,
        "open": int(getattr(bar, "deltaOpen")),
        "high": int(getattr(bar, "deltaHigh")),
        "close": int(getattr(bar, "deltaClose")),
    }
    return Decimal(low + deltas[field]) / _PRICE_SCALE


class CTraderDemoFullApi:
    """MT5-shaped compatibility surface backed only by cTrader DEMO Open API."""

    TIMEFRAME_M1 = 60
    TIMEFRAME_M5 = 300
    TIMEFRAME_M15 = 900
    TIMEFRAME_M30 = 1800
    TIMEFRAME_H1 = 3600
    TIMEFRAME_H4 = 14400
    TIMEFRAME_D1 = 86400

    TRADE_ACTION_DEAL = 1
    TRADE_ACTION_PENDING = 5
    TRADE_ACTION_SLTP = 6
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
    TRADE_RETCODE_PLACED = 10008
    TRADE_RETCODE_DONE = 10009
    TRADE_RETCODE_DONE_PARTIAL = 10010
    TRADE_RETCODE_TIMEOUT = 10012
    TRADE_RETCODE_CONNECTION = 10031
    ORDER_STATE_CANCELED = 4
    ORDER_STATE_PARTIAL = 3
    ORDER_STATE_FILLED = 2
    ORDER_STATE_REJECTED = 5
    POSITION_TYPE_BUY = 0
    POSITION_TYPE_SELL = 1
    DEAL_ENTRY_IN = 0
    DEAL_ENTRY_OUT = 1

    def __init__(
        self,
        *,
        client: CTraderOpenApiMessageClientBoundary,
        binding: CTraderDemoFreeBinding,
        positions: CTraderDemoFreePositionService,
        registry: CTraderDemoTradeRegistry,
        binding_path: Path,
        source_contract_sizes: dict[str, Decimal],
        spot_observer: Callable[
            [str, int, Decimal, Decimal, datetime, datetime],
            None,
        ] | None = None,
    ) -> None:
        self._client = client
        self._binding = binding
        self._positions = positions
        self._registry = registry
        self._source_contract = dict(source_contract_sizes)
        self._spot_observer = spot_observer
        self._management = CTraderDemoMt5ManagementAdapter(
            mt5_market_api=self,
            positions=positions,
            registry=registry,
            binding_path=binding_path,
        )
        self._spot_lock = Lock()
        self._spots: dict[int, tuple[Decimal, Decimal, datetime]] = {}
        self._history: dict[tuple[str, int], list[dict[str, float | int]]] = {}
        self._resident_bars: dict[
            tuple[str, int], dict[int, dict[str, float | int]]
        ] = {}
        self._resident_started_at: datetime | None = None
        self._canonical_by_symbol_id = {
            item.symbol_id: item.qore_symbol for item in self._binding.contracts
        }
        self._weekly_sessions: dict[
            str, tuple[ZoneInfo, tuple[tuple[int, int], ...]]
        ] = {}
        self._session_holidays: dict[
            str, tuple[tuple[int, ZoneInfo, int, int], ...]
        ] = {}
        self._stop = Event()
        self._spot_thread: Thread | None = None
        self._conversion_symbol_id: int | None = None
        self._connected = False

    @property
    def account_id(self) -> int:
        return self._client.account_id

    def initialize(self) -> bool:
        if self._connected and self._client.is_ready:
            return True
        ready = self._client.connect_and_authenticate()
        if isinstance(ready, Failure):
            return False
        self._discover_conversion_symbol()
        ids = [item.symbol_id for item in self._binding.contracts]
        if self._conversion_symbol_id is not None:
            ids.append(self._conversion_symbol_id)
        subscribed = self._client.request(
            "ProtoOASubscribeSpotsReq",
            {
                "ctidTraderAccountId": self.account_id,
                "subscribeToSpotTimestamp": True,
                "symbolId": ids,
            },
            client_msg_id="qore-demo-independent-spots",
            timeout_seconds=10.0,
        )
        if isinstance(subscribed, Failure):
            return False
        self._stop.clear()
        self._resident_started_at = datetime.now(UTC)
        self._spot_thread = Thread(
            target=self._pump_spots,
            name="qore-ctrader-demo-spots",
            daemon=True,
        )
        self._spot_thread.start()
        self._connected = True
        return True

    def shutdown(self) -> None:
        self._stop.set()
        thread = self._spot_thread
        if thread is not None:
            thread.join(timeout=1.0)
        self._spot_thread = None
        self._connected = False

    def last_error(self) -> tuple[int, str]:
        return (0, "")

    def observed_now(self) -> datetime:
        """Return the wall-clock observation time after blocking API reads."""
        return datetime.now(UTC)

    def terminal_info(self) -> object:
        return SimpleNamespace(
            connected=self._client.is_ready,
            trade_allowed=True,
            tradeapi_disabled=False,
        )

    def account_info(self) -> object | None:
        if not self._client.is_ready:
            return None
        snap = self._positions.account_snapshot()
        return SimpleNamespace(
            login=self.account_id,
            server="cTrader-Demo",
            company="Spotware cTrader DEMO",
            currency="USD",
            balance=float(snap.balance),
            equity=float(snap.equity),
            margin=0.0,
            margin_free=float(snap.equity),
            trade_allowed=True,
            trade_expert=True,
        )

    def symbols_get(self) -> tuple[object, ...]:
        names = ("XAUUSD", "EURUSD", "GBPUSD", "GBPJPY", "AUDJPY", "NDX100")
        return tuple(SimpleNamespace(name=name) for name in names)

    def symbol_select(self, symbol: str, enable: bool) -> bool:
        del enable
        return self._canonical(symbol) in {
            item.qore_symbol for item in self._binding.contracts
        }

    def _canonical(self, symbol: str) -> str:
        normalized = _norm(symbol)
        if normalized in {"NAS100", "US100", "USTEC", "NDX100"}:
            return "NAS100"
        for item in self._binding.contracts:
            if normalized in {_norm(item.qore_symbol), _norm(item.symbol_name)}:
                return item.qore_symbol
        return symbol.upper()

    def warm_session_schedules(self) -> bool:
        """Load broker-native weekly sessions and holiday closures once."""
        ids = [item.symbol_id for item in self._binding.contracts]
        result = self._client.request(
            "ProtoOASymbolByIdReq",
            {
                "ctidTraderAccountId": self.account_id,
                "symbolId": ids,
            },
            client_msg_id="qore-demo-session-schedules",
            timeout_seconds=10.0,
        )
        if isinstance(result, Failure):
            return False
        details = {
            int(getattr(item, "symbolId")): item
            for item in tuple(getattr(result.value, "symbol", ()))
            if type(getattr(item, "symbolId", None)) is int
        }
        weekly: dict[
            str, tuple[ZoneInfo, tuple[tuple[int, int], ...]]
        ] = {}
        holidays: dict[
            str, tuple[tuple[int, ZoneInfo, int, int], ...]
        ] = {}
        for contract in self._binding.contracts:
            detail = details.get(contract.symbol_id)
            if detail is None:
                return False
            zone_name = str(
                getattr(detail, "scheduleTimeZone", "") or "UTC"
            )
            try:
                zone = ZoneInfo(zone_name)
            except Exception:
                return False
            rows = tuple(
                (
                    int(getattr(item, "startSecond")),
                    int(getattr(item, "endSecond")),
                )
                for item in tuple(getattr(detail, "schedule", ()))
                if type(getattr(item, "startSecond", None)) is int
                and type(getattr(item, "endSecond", None)) is int
            )
            if not rows:
                return False
            weekly[contract.qore_symbol] = (zone, rows)
            hrows: list[tuple[int, ZoneInfo, int, int]] = []
            for holiday in tuple(getattr(detail, "holiday", ())):
                raw_day = getattr(holiday, "holidayDate", None)
                start = getattr(holiday, "startSecond", None)
                end = getattr(holiday, "endSecond", None)
                if (
                    type(raw_day) is not int
                    or type(start) is not int
                    or type(end) is not int
                ):
                    continue
                holiday_zone_name = str(
                    getattr(holiday, "scheduleTimeZone", "")
                    or zone_name
                )
                try:
                    holiday_zone = ZoneInfo(holiday_zone_name)
                except Exception:
                    continue
                hrows.append((raw_day, holiday_zone, start, end))
            holidays[contract.qore_symbol] = tuple(hrows)
        self._weekly_sessions = weekly
        self._session_holidays = holidays
        return len(weekly) == len(self._binding.contracts)

    @staticmethod
    def _inside_second_range(
        second: int,
        start: int,
        end: int,
    ) -> bool:
        if start <= end:
            return start <= second <= end
        return second >= start or second <= end

    def session_open(
        self,
        symbol: str,
        when: datetime | None = None,
    ) -> bool:
        """Return broker-native session availability for a QORE/provider symbol."""
        current = datetime.now(UTC) if when is None else when
        if current.tzinfo is None or current.utcoffset() is None:
            raise ValueError("session timestamp must be timezone-aware")
        canonical = self._canonical(symbol)
        weekly = getattr(self, "_weekly_sessions", {}).get(canonical)
        if weekly is None:
            # Session metadata is warmed by the DEMO runtime at startup.  Other
            # read-only consumers remain backward-compatible if they do not need it.
            return True
        zone, rows = weekly
        local = current.astimezone(zone)
        day_from_sunday = (local.weekday() + 1) % 7
        weekly_second = (
            day_from_sunday * 86400
            + local.hour * 3600
            + local.minute * 60
            + local.second
        )
        if not any(
            self._inside_second_range(weekly_second, start, end)
            for start, end in rows
        ):
            return False
        epoch_day = datetime(1970, 1, 1).date()
        for raw_day, holiday_zone, start, end in getattr(
            self, "_session_holidays", {}
        ).get(canonical, ()):
            holiday_local = current.astimezone(holiday_zone)
            holiday_day = (holiday_local.date() - epoch_day).days
            if holiday_day != raw_day:
                continue
            if start == 0 and end == 0:
                return False
            holiday_second = (
                holiday_local.hour * 3600
                + holiday_local.minute * 60
                + holiday_local.second
            )
            if self._inside_second_range(
                holiday_second,
                start,
                end,
            ):
                return False
        return True

    def _discover_conversion_symbol(self) -> None:
        result = self._client.request(
            "ProtoOASymbolsListReq",
            {
                "ctidTraderAccountId": self.account_id,
                "includeArchivedSymbols": False,
            },
            client_msg_id="qore-demo-independent-symbols",
            timeout_seconds=10.0,
        )
        if isinstance(result, Failure):
            return
        matches = [
            item
            for item in tuple(getattr(result.value, "symbol", ()))
            if _norm(str(getattr(item, "symbolName", ""))) == "USDJPY"
            and getattr(item, "enabled", None) is True
        ]
        if len(matches) == 1:
            self._conversion_symbol_id = int(getattr(matches[0], "symbolId"))

    def _update_resident_bars_locked(
        self,
        *,
        canonical: str,
        observed: datetime,
        bid: Decimal,
    ) -> None:
        for seconds in (60, 300, 900):
            opened_epoch = int(observed.timestamp()) // seconds * seconds
            key = (canonical, seconds)
            bars = self._resident_bars.setdefault(key, {})
            row = bars.get(opened_epoch)
            if row is None:
                opened = datetime.fromtimestamp(opened_epoch, tz=UTC)
                price = float(bid)
                row = {
                    "utc_time": opened_epoch,
                    "time": _legacy_epoch(opened),
                    "open": price,
                    "high": price,
                    "low": price,
                    "close": price,
                    "tick_volume": 1,
                    "spread": 0,
                    "real_volume": 0,
                }
                bars[opened_epoch] = row
            else:
                price = float(bid)
                row["high"] = max(float(row["high"]), price)
                row["low"] = min(float(row["low"]), price)
                row["close"] = price
                row["tick_volume"] = int(row["tick_volume"]) + 1
            if len(bars) > 32:
                for old_epoch in sorted(bars)[:-32]:
                    del bars[old_epoch]

    def copy_rates_from_pos_resident(
        self,
        symbol: str,
        timeframe: int,
        start_pos: int,
        count: int,
    ) -> list[dict[str, float | int]] | None:
        """Serve incremental hot-path bars without synchronous trendbar requests.

        Only bars whose whole interval began after the resident spot pump started
        may override historical rows. This prevents a restart in the middle of a
        candle from fabricating a partial OHLC bar.
        """
        if start_pos < 0 or count <= 0:
            return None
        canonical = self._canonical(symbol)
        seconds, _ = self._period(timeframe)
        key = (canonical, seconds)
        historical = self._history.get(key)
        if historical is None:
            return self.copy_rates_from_pos(symbol, timeframe, start_pos, count)
        with self._spot_lock:
            started = self._resident_started_at
            resident = [
                dict(row)
                for _, row in sorted(self._resident_bars.get(key, {}).items())
            ]
        if started is None:
            return self.copy_rates_from_pos(symbol, timeframe, start_pos, count)
        full_from = (
            (int(started.timestamp()) + seconds - 1) // seconds
        ) * seconds
        observed = {int(row["utc_time"]): dict(row) for row in historical}
        for row in resident:
            opened = int(row["utc_time"])
            if opened >= full_from:
                observed[opened] = row
        rows = [observed[k] for k in sorted(observed)]
        need = count + start_pos
        if len(rows) < need:
            return rows
        end = len(rows) - start_pos
        start = max(0, end - count)
        return rows[start:end]

    def _pump_spots(self) -> None:
        while not self._stop.is_set() and self._client.is_ready:
            event = self._client.wait_for_event(
                "ProtoOASpotEvent",
                timeout_seconds=1.0,
            )
            if isinstance(event, Failure):
                continue
            item = event.value
            symbol_id = getattr(item, "symbolId", None)
            bid = getattr(item, "bid", None)
            ask = getattr(item, "ask", None)
            if (
                type(symbol_id) is not int
                or type(bid) is not int
                or type(ask) is not int
            ):
                continue
            timestamp = getattr(item, "timestamp", None)
            observed = datetime.now(UTC)
            if type(timestamp) is int and timestamp > 0:
                observed = datetime.fromtimestamp(timestamp / 1000, tz=UTC)
            received_at = datetime.now(UTC)
            with self._spot_lock:
                previous = self._spots.get(symbol_id)
                next_bid = (
                    Decimal(bid) / _PRICE_SCALE
                    if bid > 0
                    else (None if previous is None else previous[0])
                )
                next_ask = (
                    Decimal(ask) / _PRICE_SCALE
                    if ask > 0
                    else (None if previous is None else previous[1])
                )
                # Spotware may publish one-sided incremental spot events with
                # the absent protobuf price encoded as zero.  Preserve the last
                # valid opposite side rather than poisoning the cached quote.
                if (
                    next_bid is None
                    or next_ask is None
                    or next_bid <= 0
                    or next_ask <= 0
                    or next_ask < next_bid
                ):
                    continue
                self._spots[symbol_id] = (
                    next_bid,
                    next_ask,
                    observed,
                )
                canonical = getattr(
                    self, "_canonical_by_symbol_id", {}
                ).get(symbol_id)
                if canonical is not None:
                    self._update_resident_bars_locked(
                        canonical=canonical,
                        observed=observed,
                        bid=next_bid,
                    )
            observer = self._spot_observer
            if canonical is not None and observer is not None:
                try:
                    observer(
                        canonical,
                        symbol_id,
                        next_bid,
                        next_ask,
                        observed,
                        received_at,
                    )
                except Exception:
                    # Market-tape failure must never interrupt the broker feed.
                    pass

    def _spot_for_id(
        self,
        symbol_id: int,
        *,
        wait_seconds: float = 3.0,
    ) -> tuple[Decimal, Decimal, datetime] | None:
        deadline = datetime.now(UTC) + timedelta(seconds=wait_seconds)
        while datetime.now(UTC) < deadline:
            with self._spot_lock:
                found = self._spots.get(symbol_id)
            if found is not None:
                return found
            Event().wait(0.02)
        return None

    def _spot(
        self,
        symbol: str,
        *,
        wait_seconds: float = 3.0,
    ) -> tuple[Decimal, Decimal, datetime] | None:
        canonical = self._canonical(symbol)
        contract = self._binding.contract(canonical)
        return self._spot_for_id(
            contract.symbol_id,
            wait_seconds=wait_seconds,
        )

    def symbol_info_tick(self, symbol: str) -> object | None:
        spot = self._spot(symbol)
        if spot is None:
            return None
        bid, ask, observed = spot
        encoded = _legacy_epoch(observed)
        millis = int(observed.microsecond / 1000)
        return SimpleNamespace(
            bid=float(bid),
            ask=float(ask),
            time=encoded,
            time_msc=encoded * 1000 + millis,
        )

    def _usd_jpy(self) -> Decimal | None:
        if self._conversion_symbol_id is None:
            return None
        spot = self._spot_for_id(self._conversion_symbol_id)
        if spot is None:
            return None
        bid, ask, _ = spot
        return (bid + ask) / Decimal("2")

    def symbol_info(self, symbol: str) -> object | None:
        canonical = self._canonical(symbol)
        try:
            contract = self._binding.contract(canonical)
        except Exception:
            return None
        tick = self.symbol_info_tick(canonical)
        if tick is None:
            return None
        point = Decimal(1).scaleb(-contract.digits)
        source_contract = self._source_contract[canonical]
        tick_value = source_contract * point
        if canonical.endswith("JPY"):
            conversion = self._usd_jpy()
            if conversion is None or conversion <= 0:
                return None
            tick_value /= conversion
        actual_min = Decimal(contract.min_volume_units) * _VOLUME_UNIT
        actual_max = Decimal(contract.max_volume_units) * _VOLUME_UNIT
        actual_step = Decimal(contract.step_volume_units) * _VOLUME_UNIT
        return SimpleNamespace(
            name=("NDX100" if canonical == "NAS100" else canonical),
            digits=contract.digits,
            point=float(point),
            trade_contract_size=float(source_contract),
            trade_tick_size=float(point),
            trade_tick_value=float(tick_value),
            volume_min=float(actual_min / source_contract),
            volume_max=float(actual_max / source_contract),
            volume_step=float(actual_step / source_contract),
            trade_stops_level=0,
            trade_freeze_level=0,
            trade_mode=1,
            filling_mode=2,
            trade_exemode=self.SYMBOL_TRADE_EXECUTION_MARKET,
        )

    def order_calc_margin(
        self,
        order_type: int,
        symbol: str,
        volume: float,
        price: float,
    ) -> float:
        del order_type, price
        canonical = self._canonical(symbol)
        source = self._source_contract.get(canonical, Decimal("1"))
        return float(
            max(
                Decimal("1"),
                source * Decimal(str(volume)) / Decimal("100"),
            )
        )

    def _period(self, timeframe: int) -> tuple[int, int]:
        seconds = int(timeframe)
        code = _PERIOD_CODE.get(seconds)
        if code is None:
            raise ValueError(
                f"unsupported cTrader DEMO timeframe: {timeframe}"
            )
        return seconds, code

    def _closed_rows(
        self,
        canonical: str,
        timeframe: int,
        *,
        count_hint: int,
    ) -> list[dict[str, float | int]]:
        seconds, code = self._period(timeframe)
        key = (canonical, seconds)
        now = datetime.now(UTC)
        current_open = datetime.fromtimestamp(
            int(now.timestamp()) // seconds * seconds,
            tz=UTC,
        )
        expected_last = current_open - timedelta(seconds=seconds)
        cached = self._history.get(key)
        needs = cached is None
        if cached:
            last_real = datetime.fromtimestamp(
                int(cached[-1]["utc_time"]),
                tz=UTC,
            )
            needs = last_real < expected_last
        if needs:
            contract = self._binding.contract(canonical)
            if cached is None:
                # cTrader history is wall-clock sparse outside trading hours.
                # Request enough calendar history to satisfy large bar-count preloads
                # (VT31 requires >=10k M1 bars).
                horizon_seconds = max(
                    seconds * max(count_hint, 64) * 20,
                    120 * 86400,
                )
                start = now - timedelta(seconds=horizon_seconds)
            else:
                last_real = datetime.fromtimestamp(
                    int(cached[-1]["utc_time"]),
                    tz=UTC,
                )
                start = last_real - timedelta(seconds=seconds)
            response = self._client.request(
                "ProtoOAGetTrendbarsReq",
                {
                    "ctidTraderAccountId": self.account_id,
                    "fromTimestamp": int(start.timestamp() * 1000),
                    "period": code,
                    "symbolId": contract.symbol_id,
                    "toTimestamp": int(now.timestamp() * 1000),
                },
                client_msg_id=(
                    f"bars:{contract.symbol_id}:{seconds}:"
                    f"{int(now.timestamp())}"
                ),
                timeout_seconds=15.0,
            )
            if isinstance(response, Failure):
                if cached is None:
                    return []
            else:
                observed: dict[
                    int,
                    dict[str, float | int],
                ] = {}
                if cached:
                    observed.update(
                        {
                            int(row["utc_time"]): row
                            for row in cached
                        }
                    )
                for bar in tuple(
                    getattr(response.value, "trendbar", ())
                ):
                    opened = (
                        int(
                            getattr(
                                bar,
                                "utcTimestampInMinutes",
                            )
                        )
                        * 60
                    )
                    observed[opened] = {
                        "utc_time": opened,
                        "time": _legacy_epoch(
                            datetime.fromtimestamp(
                                opened,
                                tz=UTC,
                            )
                        ),
                        "open": float(
                            _relative_price(bar, "open")
                        ),
                        "high": float(
                            _relative_price(bar, "high")
                        ),
                        "low": float(
                            _relative_price(bar, "low")
                        ),
                        "close": float(
                            _relative_price(bar, "close")
                        ),
                        "tick_volume": 0,
                        "spread": 0,
                        "real_volume": 0,
                    }
                cached = [
                    observed[k]
                    for k in sorted(observed)
                ]
                max_keep = max(
                    50000,
                    count_hint * 2,
                )
                if len(cached) > max_keep:
                    cached = cached[-max_keep:]
                self._history[key] = cached
        return list(
            self._history.get(
                key,
                [],
            )
        )

    def _synthetic_current(
        self,
        canonical: str,
        timeframe: int,
    ) -> dict[str, float | int] | None:
        seconds, _ = self._period(timeframe)
        spot = self._spot(
            canonical,
            wait_seconds=0.3,
        )
        if spot is None:
            return None
        bid, _ask, observed = spot
        if (
            datetime.now(UTC) - observed
            > timedelta(seconds=10)
        ):
            return None
        opened = datetime.fromtimestamp(
            int(datetime.now(UTC).timestamp())
            // seconds
            * seconds,
            tz=UTC,
        )
        price = float(bid)
        return {
            "utc_time": int(opened.timestamp()),
            "time": _legacy_epoch(opened),
            "open": price,
            "high": price,
            "low": price,
            "close": price,
            "tick_volume": 0,
            "spread": 0,
            "real_volume": 0,
        }

    def copy_rates_from_pos(
        self,
        symbol: str,
        timeframe: int,
        start_pos: int,
        count: int,
    ) -> list[dict[str, float | int]] | None:
        if start_pos < 0 or count <= 0:
            return None
        canonical = self._canonical(symbol)
        rows = self._closed_rows(
            canonical,
            timeframe,
            count_hint=count + start_pos,
        )
        current = self._synthetic_current(
            canonical,
            timeframe,
        )
        if (
            current is not None
            and (
                not rows
                or int(rows[-1]["utc_time"])
                < int(current["utc_time"])
            )
        ):
            rows = rows + [current]
        need = count + start_pos
        if len(rows) < need:
            return rows
        end = len(rows) - start_pos
        start = max(0, end - count)
        return rows[start:end]

    def copy_rates_range(
        self,
        symbol: str,
        timeframe: int,
        date_from: datetime,
        date_to: datetime,
    ) -> list[dict[str, float | int]] | None:
        canonical = self._canonical(symbol)
        seconds, code = self._period(timeframe)
        contract = self._binding.contract(canonical)
        response = self._client.request(
            "ProtoOAGetTrendbarsReq",
            {
                "ctidTraderAccountId": self.account_id,
                "fromTimestamp": int(
                    date_from.astimezone(UTC).timestamp()
                    * 1000
                ),
                "period": code,
                "symbolId": contract.symbol_id,
                "toTimestamp": int(
                    date_to.astimezone(UTC).timestamp()
                    * 1000
                ),
            },
            client_msg_id=(
                f"range:{contract.symbol_id}:{seconds}:"
                f"{int(date_to.timestamp())}"
            ),
            timeout_seconds=15.0,
        )
        if isinstance(response, Failure):
            return None
        out: list[
            dict[str, float | int]
        ] = []
        for bar in tuple(
            getattr(response.value, "trendbar", ())
        ):
            opened = (
                int(
                    getattr(
                        bar,
                        "utcTimestampInMinutes",
                    )
                )
                * 60
            )
            out.append(
                {
                    "utc_time": opened,
                    "time": _legacy_epoch(
                        datetime.fromtimestamp(
                            opened,
                            tz=UTC,
                        )
                    ),
                    "open": float(
                        _relative_price(
                            bar,
                            "open",
                        )
                    ),
                    "high": float(
                        _relative_price(
                            bar,
                            "high",
                        )
                    ),
                    "low": float(
                        _relative_price(
                            bar,
                            "low",
                        )
                    ),
                    "close": float(
                        _relative_price(
                            bar,
                            "close",
                        )
                    ),
                    "tick_volume": 0,
                    "spread": 0,
                    "real_volume": 0,
                }
            )
        return out

    def positions_get(
        self,
        *args: object,
        **kwargs: object,
    ) -> tuple[object, ...]:
        return self._management.positions_get(
            *args,
            **kwargs,
        )

    def history_deals_get(
        self,
        start: datetime,
        end: datetime,
    ) -> tuple[object, ...]:
        return self._management.history_deals_get(
            start,
            end,
        )

    def orders_get(
        self,
        *args: object,
        **kwargs: object,
    ) -> tuple[object, ...]:
        del args, kwargs
        return ()

    def history_orders_get(
        self,
        start: datetime,
        end: datetime,
    ) -> tuple[object, ...]:
        del start, end
        return ()

    def order_check(
        self,
        request: dict[str, object],
    ) -> object:
        return self._management.order_check(
            request
        )

    def order_send(
        self,
        request: dict[str, object],
    ) -> object:
        return self._management.order_send(
            request
        )

    def pending_order_status(
        self,
        provider_order_ref: str,
    ) -> int:
        return self._management.pending_order_status(
            provider_order_ref
        )

    def cancel_pending_order(
        self,
        provider_order_ref: str,
    ) -> None:
        self._management.cancel_pending_order(
            provider_order_ref
        )

    def close_position_for_magic(
        self,
        magic: int,
    ) -> bool:
        return self._management.close_position_for_magic(
            magic
        )


class CTraderDemoReadTransport:
    """Read-only account/spec boundary over cTrader DEMO."""

    def __init__(
        self,
        api: CTraderDemoFullApi,
        *,
        account_ref: str,
    ) -> None:
        self._api = api
        self._account_ref = account_ref

    def connected(self) -> bool:
        info = self._api.terminal_info()
        return bool(
            getattr(
                info,
                "connected",
                False,
            )
        )

    def observed_now(self) -> datetime:
        return datetime.now(UTC)

    def account_state(
        self,
        account_ref: str,
    ) -> CTraderDemoAccountState | None:
        if account_ref != self._account_ref:
            return None
        info = self._api.account_info()
        if info is None:
            return None
        return CTraderDemoAccountState(
            balance=Decimal(
                str(info.balance)
            ),
            equity=Decimal(
                str(info.equity)
            ),
            margin=Decimal(
                str(info.margin)
            ),
            free_margin=Decimal(
                str(info.margin_free)
            ),
            observed_at=datetime.now(UTC),
        )

    def available_symbols(self) -> tuple[str, ...]:
        return tuple(
            str(item.name)
            for item in self._api.symbols_get()
        )

    def symbol_info(
        self,
        provider_symbol: str,
    ) -> CTraderDemoSymbolSpecification | None:
        info = self._api.symbol_info(
            provider_symbol
        )
        tick = self._api.symbol_info_tick(
            provider_symbol
        )
        if info is None or tick is None:
            return None
        point = Decimal(str(info.point))
        bid = Decimal(str(tick.bid))
        ask = Decimal(str(tick.ask))
        margin = Decimal(
            str(
                self._api.order_calc_margin(
                    self._api.ORDER_TYPE_BUY,
                    provider_symbol,
                    1.0,
                    float(ask),
                )
            )
        )
        return CTraderDemoSymbolSpecification(
            provider_symbol=provider_symbol,
            bid=bid,
            ask=ask,
            spread_points=(ask - bid) / point,
            digits=int(info.digits),
            point=point,
            contract_size=Decimal(
                str(
                    info.trade_contract_size
                )
            ),
            tick_size=Decimal(
                str(
                    info.trade_tick_size
                )
            ),
            tick_value=Decimal(
                str(
                    info.trade_tick_value
                )
            ),
            minimum_volume=Decimal(
                str(
                    info.volume_min
                )
            ),
            maximum_volume=Decimal(
                str(
                    info.volume_max
                )
            ),
            volume_step=Decimal(
                str(
                    info.volume_step
                )
            ),
            minimum_stop_distance_points=Decimal(
                str(
                    info.trade_stops_level
                )
            ),
            freeze_level_points=Decimal(
                str(
                    info.trade_freeze_level
                )
            ),
            margin_per_volume=margin,
            trade_enabled=True,
            session_open=self._api.session_open(provider_symbol),
            observed_at=datetime.now(UTC),
        )

    def discover_order(
        self,
        client_order_id: str,
    ) -> None:
        del client_order_id
        return None
