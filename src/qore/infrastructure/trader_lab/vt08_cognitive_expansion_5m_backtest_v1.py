"""Five-market replay harness for VT08 Cognitive Expansion 5M V1.

Consumes the same sanitized DEMO/read-only M15 evidence shape as the frozen VT08
B01 backtest, but accepts only the frozen 5M research universe. It reports R-based
economics and market x anchor diagnostics without granting promotion authority.
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import cast
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_evaluator_v1 import (
    Vt08ExpansionCandidate,
    evaluate_expansion_at_entry_indexed,
    expansion_evaluator_fingerprint,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_v1 import (
    ANCHORS_NY,
    EXPANSION_MARKETS,
    RESEARCH_GATES,
    program_fingerprint,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_b01_r3_8 import Vt08B01Bar

_NY = ZoneInfo("America/New_York")
_SCHEMA = "qore.trader_lab.vt08_cognitive_expansion_5m.backtest.v1"


class Vt08ExpansionBacktestError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ExpansionTrade:
    symbol: str
    signal_at: datetime
    exited_at: datetime
    anchor_hour_ny: int
    side: DemoTradingSetupSide
    entry: Decimal
    stop: Decimal
    target: Decimal
    exit_price: Decimal
    exit_reason: str
    r_multiple: Decimal

    def payload(self) -> dict[str, object]:
        return {
            "symbol": self.symbol,
            "signal_at": self.signal_at.astimezone(UTC).isoformat(),
            "exited_at": self.exited_at.astimezone(UTC).isoformat(),
            "anchor_hour_ny": self.anchor_hour_ny,
            "side": self.side.value,
            "entry": format(self.entry, "f"),
            "stop": format(self.stop, "f"),
            "target": format(self.target, "f"),
            "exit_price": format(self.exit_price, "f"),
            "exit_reason": self.exit_reason,
            "r_multiple": format(self.r_multiple, "f"),
        }


def _object(value: object, *, name: str) -> dict[str, object]:
    if type(value) is not dict or any(type(key) is not str for key in value):
        raise Vt08ExpansionBacktestError(f"{name} must be an object")
    return cast(dict[str, object], value)


def _array(value: object, *, name: str) -> list[object]:
    if type(value) is not list:
        raise Vt08ExpansionBacktestError(f"{name} must be an array")
    return cast(list[object], value)


def _text(value: object, *, name: str) -> str:
    if type(value) is not str or not value:
        raise Vt08ExpansionBacktestError(f"{name} must be non-empty text")
    return value


def _boolean(value: object, *, name: str) -> bool:
    if type(value) is not bool:
        raise Vt08ExpansionBacktestError(f"{name} must be bool")
    return value


def _integer(value: object, *, name: str) -> int:
    if type(value) is not int:
        raise Vt08ExpansionBacktestError(f"{name} must be int")
    return value


def _timestamp(value: object, *, name: str) -> datetime:
    raw = _text(value, name=name)
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as error:
        raise Vt08ExpansionBacktestError(f"{name} must be RFC3339") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise Vt08ExpansionBacktestError(f"{name} must be timezone-aware")
    return parsed.astimezone(UTC)


def _decimal(value: object, *, name: str) -> Decimal:
    raw = _text(value, name=name)
    try:
        parsed = Decimal(raw)
    except InvalidOperation as error:
        raise Vt08ExpansionBacktestError(f"{name} must be Decimal text") from error
    if not parsed.is_finite() or parsed <= 0:
        raise Vt08ExpansionBacktestError(f"{name} must be positive finite Decimal")
    return parsed


def _parse_bar(value: object) -> Vt08B01Bar:
    row = _object(value, name="M15 bar")
    return Vt08B01Bar(
        opened_at=_timestamp(row.get("opened_at"), name="opened_at"),
        closed_at=_timestamp(row.get("closed_at"), name="closed_at"),
        open=_decimal(row.get("open"), name="open"),
        high=_decimal(row.get("high"), name="high"),
        low=_decimal(row.get("low"), name="low"),
        close=_decimal(row.get("close"), name="close"),
    )


def load_market_evidence(
    path: Path,
) -> tuple[str, str, datetime, str, tuple[Vt08B01Bar, ...]]:
    try:
        decoded: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise Vt08ExpansionBacktestError("cannot read market evidence") from error
    payload = _object(decoded, name="market evidence")
    if _text(payload.get("environment"), name="environment") != "demo":
        raise Vt08ExpansionBacktestError("market evidence must be DEMO")
    if not _boolean(payload.get("read_only"), name="read_only"):
        raise Vt08ExpansionBacktestError("market evidence must be read-only")
    if _boolean(payload.get("account_is_live"), name="account_is_live"):
        raise Vt08ExpansionBacktestError("LIVE evidence is prohibited")
    fingerprint = _text(payload.get("account_fingerprint"), name="account_fingerprint")
    if re.fullmatch(r"[0-9a-f]{64}", fingerprint) is None:
        raise Vt08ExpansionBacktestError("account fingerprint must be SHA-256")
    symbol_payload = _object(payload.get("symbol"), name="symbol")
    symbol = _text(symbol_payload.get("symbol_name"), name="symbol_name")
    if symbol not in EXPANSION_MARKETS:
        raise Vt08ExpansionBacktestError("market outside frozen VT08 5M universe")
    checked_at = _timestamp(payload.get("checked_at"), name="checked_at")
    software_sha = _text(payload.get("software_sha"), name="software_sha")
    if re.fullmatch(r"[0-9a-f]{40}", software_sha) is None:
        raise Vt08ExpansionBacktestError("software_sha must be exact lowercase Git SHA")
    periods = _object(payload.get("periods"), name="periods")
    bars = tuple(_parse_bar(item) for item in _array(periods.get("M15"), name="M15"))
    if not bars:
        raise Vt08ExpansionBacktestError("M15 evidence is empty")
    if bars != tuple(sorted(bars, key=lambda item: item.opened_at)):
        raise Vt08ExpansionBacktestError("M15 evidence must be chronological")
    if len({item.opened_at for item in bars}) != len(bars):
        raise Vt08ExpansionBacktestError("M15 evidence contains duplicate bars")
    if bars[-1].closed_at - bars[0].opened_at < timedelta(days=730):
        raise Vt08ExpansionBacktestError("M15 evidence must span at least 730 days")
    return fingerprint, symbol, checked_at, software_sha, bars


def _touches(bar: Vt08B01Bar, price: Decimal) -> bool:
    return bar.low <= price <= bar.high


def _r_multiple(
    *,
    side: DemoTradingSetupSide,
    entry: Decimal,
    stop: Decimal,
    exit_price: Decimal,
) -> Decimal:
    risk = entry - stop if side is DemoTradingSetupSide.LONG else stop - entry
    if risk <= 0:
        raise Vt08ExpansionBacktestError("trade risk must be positive")
    if side is DemoTradingSetupSide.LONG:
        return (exit_price - entry) / risk
    return (entry - exit_price) / risk


def model_trade(
    candidate: Vt08ExpansionCandidate,
    *,
    bars_by_open: dict[datetime, Vt08B01Bar],
) -> ExpansionTrade | None:
    start = candidate.decision_at.astimezone(UTC)
    end = (start.astimezone(_NY) + timedelta(hours=4)).astimezone(UTC)
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
    if not retained or cursor != end:
        return None

    setup = candidate.setup
    exit_price = retained[-1].close
    exited_at = retained[-1].closed_at
    exit_reason = "h4_containment_exit"
    for bar in retained:
        if _touches(bar, setup.invalidation_price):
            exit_price = setup.invalidation_price
            exited_at = bar.closed_at
            exit_reason = "stop"
            break
        if _touches(bar, setup.take_profit_price):
            exit_price = setup.take_profit_price
            exited_at = bar.closed_at
            exit_reason = "target"
            break

    return ExpansionTrade(
        symbol=candidate.symbol,
        signal_at=start,
        exited_at=exited_at,
        anchor_hour_ny=candidate.entry_anchor_hour,
        side=candidate.side,
        entry=setup.entry_price,
        stop=setup.invalidation_price,
        target=setup.take_profit_price,
        exit_price=exit_price,
        exit_reason=exit_reason,
        r_multiple=_r_multiple(
            side=candidate.side,
            entry=setup.entry_price,
            stop=setup.invalidation_price,
            exit_price=exit_price,
        ),
    )


def metrics(trades: tuple[ExpansionTrade, ...]) -> dict[str, object]:
    values = tuple(item.r_multiple for item in trades)
    sample = len(values)
    wins = sum(value > 0 for value in values)
    losses = sum(value < 0 for value in values)
    flats = sample - wins - losses
    gross_profit = sum((value for value in values if value > 0), Decimal(0))
    gross_loss = -sum((value for value in values if value < 0), Decimal(0))
    total = sum(values, Decimal(0))
    mean = total / Decimal(sample) if sample else Decimal(0)
    equity = Decimal(0)
    peak = Decimal(0)
    max_dd = Decimal(0)
    streak = 0
    max_streak = 0
    for value in values:
        equity += value
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
        if value < 0:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0
    pf = None if gross_loss == 0 else gross_profit / gross_loss
    return {
        "sample_size": sample,
        "wins": wins,
        "losses": losses,
        "flats": flats,
        "win_rate": "0" if not sample else format(Decimal(wins) / Decimal(sample), "f"),
        "gross_profit_r": format(gross_profit, "f"),
        "gross_loss_r": format(gross_loss, "f"),
        "profit_factor": None if pf is None else format(pf, "f"),
        "total_r": format(total, "f"),
        "mean_r": format(mean, "f"),
        "max_drawdown_r": format(max_dd, "f"),
        "max_losing_streak": max_streak,
    }


def run_market_backtest(path: Path) -> dict[str, object]:
    fingerprint, symbol, checked_at, software_sha, bars = load_market_evidence(path)
    bars_by_open = {item.opened_at: item for item in bars}
    candidates_by_day: dict[date, list[Vt08ExpansionCandidate]] = defaultdict(list)
    abstains: Counter[str] = Counter()

    for bar in bars:
        local = bar.opened_at.astimezone(_NY)
        if local.minute != 0 or local.hour not in ANCHORS_NY:
            continue
        result = evaluate_expansion_at_entry_indexed(
            symbol=symbol,
            bars_by_open=bars_by_open,
            decision_at=bar.opened_at,
        )
        if result.candidate is None:
            assert result.abstain_reason is not None
            abstains[result.abstain_reason.value] += 1
        else:
            candidates_by_day[local.date()].append(result.candidate)

    multiple_days = 0
    incomplete_exit = 0
    trades: list[ExpansionTrade] = []
    for day in sorted(candidates_by_day):
        items = candidates_by_day[day]
        if len(items) != 1:
            multiple_days += 1
            continue
        trade = model_trade(items[0], bars_by_open=bars_by_open)
        if trade is None:
            incomplete_exit += 1
            continue
        trades.append(trade)

    ordered = tuple(sorted(trades, key=lambda item: item.signal_at))
    by_anchor = {
        str(anchor): metrics(
            tuple(item for item in ordered if item.anchor_hour_ny == anchor)
        )
        for anchor in ANCHORS_NY
    }
    by_side = {
        side: metrics(tuple(item for item in ordered if item.side.value == side))
        for side in ("long", "short")
    }
    return {
        "schema": _SCHEMA,
        "program_fingerprint": program_fingerprint(),
        "evaluator_fingerprint": expansion_evaluator_fingerprint(),
        "research_only": True,
        "demo_eligible": False,
        "live_authorized": False,
        "production_authorized": False,
        "real_capital_authorized": False,
        "symbol": symbol,
        "account_fingerprint": fingerprint,
        "checked_at": checked_at.astimezone(UTC).isoformat(),
        "software_sha": software_sha,
        "candidate_count": sum(len(items) for items in candidates_by_day.values()),
        "multiple_candidate_day_count": multiple_days,
        "incomplete_exit_window_count": incomplete_exit,
        "abstain_reasons": dict(sorted(abstains.items())),
        "economics": metrics(ordered),
        "by_anchor_ny": by_anchor,
        "by_side": by_side,
        "research_gates": RESEARCH_GATES,
        "trades": [item.payload() for item in ordered],
    }


def run_five_market_matrix(paths: tuple[Path, ...]) -> dict[str, object]:
    if len(paths) != len(EXPANSION_MARKETS):
        raise Vt08ExpansionBacktestError("exactly five market-evidence files required")
    reports = tuple(run_market_backtest(path) for path in paths)
    symbols = tuple(sorted(str(item["symbol"]) for item in reports))
    if symbols != tuple(sorted(EXPANSION_MARKETS)):
        raise Vt08ExpansionBacktestError("five-market evidence set incomplete or duplicated")
    all_trades: list[ExpansionTrade] = []
    for report in reports:
        for raw in cast(list[dict[str, object]], report["trades"]):
            all_trades.append(
                ExpansionTrade(
                    symbol=str(raw["symbol"]),
                    signal_at=_timestamp(raw["signal_at"], name="signal_at"),
                    exited_at=_timestamp(raw["exited_at"], name="exited_at"),
                    anchor_hour_ny=_integer(raw["anchor_hour_ny"], name="anchor_hour_ny"),
                    side=DemoTradingSetupSide(str(raw["side"])),
                    entry=Decimal(str(raw["entry"])),
                    stop=Decimal(str(raw["stop"])),
                    target=Decimal(str(raw["target"])),
                    exit_price=Decimal(str(raw["exit_price"])),
                    exit_reason=str(raw["exit_reason"]),
                    r_multiple=Decimal(str(raw["r_multiple"])),
                )
            )
    pooled = tuple(sorted(all_trades, key=lambda item: (item.signal_at, item.symbol)))
    return {
        "schema": "qore.trader_lab.vt08_cognitive_expansion_5m.matrix.v1",
        "program_fingerprint": program_fingerprint(),
        "research_only": True,
        "market_count": len(reports),
        "markets": list(EXPANSION_MARKETS),
        "pooled_economics": metrics(pooled),
        "market_reports": list(reports),
        "selection_authorized": False,
        "next_stage": "FAILURE_FORENSICS_THEN_TEMPORAL_VALIDATION",
    }
