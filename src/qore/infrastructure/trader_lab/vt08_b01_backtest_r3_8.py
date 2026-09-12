"""Fresh historical replay for the VT-08 R3.8 narrow B01 Forex subset."""

from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import cast
from zoneinfo import ZoneInfo

from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_b01_r3_8 import (
    AUTHORIZED_FOREX_MARKETS,
    DAILY_SELECTION_POLICY,
    OPERATIONAL_CONTAINMENTS,
    OWNER_FOREX_ENTRY_ANCHORS,
    TARGET_POLICY,
    Vt08B01Bar,
    Vt08B01Candidate,
    evaluate_b01_at_entry_indexed,
    methodology_fingerprint,
)
from qore.kernel.errors import InfrastructureError

_SCHEMA = "qore.trader_lab.vt08_b01_backtest.r3.8.v1"
_EXECUTION_MODEL = "b01-open-fill-ps-no-offset-2r-h4-close-containment-v1"
_NY = ZoneInfo("America/New_York")


class Vt08B01BacktestError(InfrastructureError):
    __slots__ = ()


@dataclass(frozen=True, slots=True)
class Vt08B01BacktestTrade:
    signal_at: datetime
    exited_at: datetime
    side: DemoTradingSetupSide
    entry: Decimal
    stop: Decimal
    target: Decimal
    exit_price: Decimal
    exit_reason: str
    return_rate: Decimal

    def payload(self) -> dict[str, object]:
        return {
            "signal_at": self.signal_at.astimezone(UTC).isoformat(),
            "exited_at": self.exited_at.astimezone(UTC).isoformat(),
            "side": self.side.value,
            "entry": format(self.entry, "f"),
            "stop": format(self.stop, "f"),
            "target": format(self.target, "f"),
            "exit_price": format(self.exit_price, "f"),
            "exit_reason": self.exit_reason,
            "return_rate": format(self.return_rate, "f"),
        }


@dataclass(frozen=True, slots=True)
class Vt08B01BacktestReport:
    symbol: str
    account_fingerprint: str
    checked_at: datetime
    software_sha: str
    candidate_count: int
    single_candidate_day_count: int
    multiple_candidate_day_count: int
    incomplete_exit_window_count: int
    abstain_reasons: tuple[tuple[str, int], ...]
    trades: tuple[Vt08B01BacktestTrade, ...]

    def payload(self) -> dict[str, object]:
        values = tuple(item.return_rate for item in self.trades)
        sample = len(values)
        mean = sum(values, Decimal(0)) / Decimal(sample) if sample else Decimal(0)
        wins = sum(value > 0 for value in values)
        losses = sum(value < 0 for value in values)
        flat = sample - wins - losses
        return {
            "schema": _SCHEMA,
            "environment": "demo",
            "read_only": True,
            "research_only": True,
            "profile": "author-clarified",
            "trader_code": "vt-08",
            "bundle_id": "B01_SOURCE_FAITHFUL_HISTORICAL_REPLAY_V1",
            "symbol": self.symbol,
            "account_fingerprint": self.account_fingerprint,
            "checked_at": self.checked_at.astimezone(UTC).isoformat(),
            "software_sha": self.software_sha,
            "methodology_fingerprint": methodology_fingerprint(),
            "execution_model": _EXECUTION_MODEL,
            "target_policy": TARGET_POLICY,
            "daily_selection_policy": DAILY_SELECTION_POLICY,
            "operational_containments": list(OPERATIONAL_CONTAINMENTS),
            "futures_status": "excluded-from-r3.8-first-replay",
            "candidate_count": self.candidate_count,
            "single_candidate_day_count": self.single_candidate_day_count,
            "multiple_candidate_day_count": self.multiple_candidate_day_count,
            "daily_cardinality_violations": 0,
            "incomplete_exit_window_count": self.incomplete_exit_window_count,
            "abstain_reasons": dict(self.abstain_reasons),
            "sample_size": sample,
            "winning_trades": wins,
            "losing_trades": losses,
            "flat_trades": flat,
            "mean_return": format(mean, "f"),
            "trades": [item.payload() for item in self.trades],
        }

    def to_json(self) -> str:
        return json.dumps(
            self.payload(),
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )


def _obj(value: object, *, name: str) -> dict[str, object]:
    if type(value) is not dict or any(type(key) is not str for key in value):
        raise Vt08B01BacktestError(f"{name} must be an object")
    return cast(dict[str, object], value)


def _arr(value: object, *, name: str) -> list[object]:
    if type(value) is not list:
        raise Vt08B01BacktestError(f"{name} must be an array")
    return cast(list[object], value)


def _text(value: object, *, name: str) -> str:
    if type(value) is not str or not value:
        raise Vt08B01BacktestError(f"{name} must be non-empty text")
    return value


def _bool(value: object, *, name: str) -> bool:
    if type(value) is not bool:
        raise Vt08B01BacktestError(f"{name} must be bool")
    return value


def _timestamp(value: object, *, name: str) -> datetime:
    raw = _text(value, name=name)
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as error:
        raise Vt08B01BacktestError(f"{name} must be RFC3339") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise Vt08B01BacktestError(f"{name} must be timezone-aware")
    return parsed.astimezone(UTC)


def _decimal(value: object, *, name: str) -> Decimal:
    raw = _text(value, name=name)
    try:
        parsed = Decimal(raw)
    except InvalidOperation as error:
        raise Vt08B01BacktestError(f"{name} must be Decimal text") from error
    if not parsed.is_finite() or parsed <= 0:
        raise Vt08B01BacktestError(f"{name} must be positive finite Decimal")
    return parsed


def _parse_m15(row: object) -> Vt08B01Bar:
    payload = _obj(row, name="M15 bar")
    return Vt08B01Bar(
        opened_at=_timestamp(payload.get("opened_at"), name="opened_at"),
        closed_at=_timestamp(payload.get("closed_at"), name="closed_at"),
        open=_decimal(payload.get("open"), name="open"),
        high=_decimal(payload.get("high"), name="high"),
        low=_decimal(payload.get("low"), name="low"),
        close=_decimal(payload.get("close"), name="close"),
    )


def _load(path: Path) -> tuple[str, str, datetime, str, tuple[Vt08B01Bar, ...]]:
    try:
        decoded: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise Vt08B01BacktestError("cannot read market evidence") from error
    payload = _obj(decoded, name="market evidence")
    if _text(payload.get("environment"), name="environment") != "demo":
        raise Vt08B01BacktestError("market evidence must be DEMO")
    if not _bool(payload.get("read_only"), name="read_only"):
        raise Vt08B01BacktestError("market evidence must be read-only")
    if _bool(payload.get("account_is_live"), name="account_is_live"):
        raise Vt08B01BacktestError("LIVE evidence is prohibited")
    fingerprint = _text(
        payload.get("account_fingerprint"),
        name="account_fingerprint",
    )
    if len(fingerprint) != 64:
        raise Vt08B01BacktestError("account fingerprint must have SHA-256 length")
    symbol_payload = _obj(payload.get("symbol"), name="symbol")
    symbol = _text(symbol_payload.get("symbol_name"), name="symbol_name")
    if symbol not in AUTHORIZED_FOREX_MARKETS:
        raise Vt08B01BacktestError(
            "R3.8 first replay accepts only authorized Forex markets"
        )
    checked_at = _timestamp(payload.get("checked_at"), name="checked_at")
    software_sha = _text(payload.get("software_sha"), name="software_sha")
    if re.fullmatch(r"[0-9a-f]{40}", software_sha) is None:
        raise Vt08B01BacktestError(
            "software_sha must be an exact lowercase Git SHA"
        )
    periods = _obj(payload.get("periods"), name="periods")
    rows = _arr(periods.get("M15"), name="M15")
    bars = tuple(_parse_m15(row) for row in rows)
    if not bars:
        raise Vt08B01BacktestError("M15 evidence is empty")
    if bars != tuple(sorted(bars, key=lambda item: item.opened_at)):
        raise Vt08B01BacktestError("M15 evidence must be chronological")
    if len({item.opened_at for item in bars}) != len(bars):
        raise Vt08B01BacktestError("M15 evidence contains duplicate bars")
    if bars[-1].closed_at - bars[0].opened_at < timedelta(days=730):
        raise Vt08B01BacktestError("M15 evidence must span at least 730 days")
    return fingerprint, symbol, checked_at, software_sha, bars


def _touches(bar: Vt08B01Bar, price: Decimal) -> bool:
    return bar.low <= price <= bar.high


def _return_rate(
    *,
    side: DemoTradingSetupSide,
    entry: Decimal,
    exit_price: Decimal,
) -> Decimal:
    if side is DemoTradingSetupSide.LONG:
        return (exit_price - entry) / entry
    return (entry - exit_price) / entry


def _model_trade(
    candidate: Vt08B01Candidate,
    *,
    bars_by_open: dict[datetime, Vt08B01Bar],
) -> Vt08B01BacktestTrade | None:
    start = candidate.decision_at.astimezone(UTC)
    local = start.astimezone(_NY)
    end = (local + timedelta(hours=4)).astimezone(UTC)
    if end - start != timedelta(hours=4):
        return None
    retained: list[Vt08B01Bar] = []
    cursor = start
    while cursor < end:
        bar = bars_by_open.get(cursor)
        if bar is None or bar.closed_at != cursor + timedelta(minutes=15):
            return None
        retained.append(bar)
        cursor += timedelta(minutes=15)
    if cursor != end or not retained:
        return None

    setup = candidate.setup
    exit_price = retained[-1].close
    exited_at = retained[-1].closed_at
    reason = "h4_containment_exit"
    for bar in retained:
        if _touches(bar, setup.invalidation_price):
            exit_price = setup.invalidation_price
            exited_at = bar.closed_at
            reason = "stop"
            break
        if _touches(bar, setup.take_profit_price):
            exit_price = setup.take_profit_price
            exited_at = bar.closed_at
            reason = "target"
            break
    return Vt08B01BacktestTrade(
        signal_at=start,
        exited_at=exited_at,
        side=candidate.side,
        entry=setup.entry_price,
        stop=setup.invalidation_price,
        target=setup.take_profit_price,
        exit_price=exit_price,
        exit_reason=reason,
        return_rate=_return_rate(
            side=candidate.side,
            entry=setup.entry_price,
            exit_price=exit_price,
        ),
    )


def run_vt08_b01_backtest(path: Path) -> Vt08B01BacktestReport:
    fingerprint, symbol, checked_at, software_sha, bars = _load(path)
    bars_by_open = {item.opened_at: item for item in bars}
    abstains: Counter[str] = Counter()
    candidates_by_day: dict[date, list[Vt08B01Candidate]] = defaultdict(list)

    for bar in bars:
        local = bar.opened_at.astimezone(_NY)
        if local.minute != 0 or local.hour not in OWNER_FOREX_ENTRY_ANCHORS:
            continue
        result = evaluate_b01_at_entry_indexed(
            symbol=symbol,
            bars_by_open=bars_by_open,
            decision_at=bar.opened_at,
        )
        if result.candidate is None:
            assert result.abstain_reason is not None
            abstains[result.abstain_reason.value] += 1
            continue
        candidates_by_day[local.date()].append(result.candidate)

    all_candidates = sum(len(items) for items in candidates_by_day.values())
    single_days = 0
    multiple_days = 0
    incomplete_exit = 0
    trades: list[Vt08B01BacktestTrade] = []
    for day in sorted(candidates_by_day):
        day_candidates = candidates_by_day[day]
        if len(day_candidates) != 1:
            multiple_days += 1
            continue
        single_days += 1
        modeled = _model_trade(day_candidates[0], bars_by_open=bars_by_open)
        if modeled is None:
            incomplete_exit += 1
            continue
        trades.append(modeled)

    return Vt08B01BacktestReport(
        symbol=symbol,
        account_fingerprint=fingerprint,
        checked_at=checked_at,
        software_sha=software_sha,
        candidate_count=all_candidates,
        single_candidate_day_count=single_days,
        multiple_candidate_day_count=multiple_days,
        incomplete_exit_window_count=incomplete_exit,
        abstain_reasons=tuple(sorted(abstains.items())),
        trades=tuple(trades),
    )


def main() -> None:
    if len(sys.argv) != 2:
        raise Vt08B01BacktestError(
            "usage: vt08_b01_backtest_r3_8 <market-evidence.json>"
        )
    print(run_vt08_b01_backtest(Path(sys.argv[1])).to_json())


if __name__ == "__main__":
    main()
