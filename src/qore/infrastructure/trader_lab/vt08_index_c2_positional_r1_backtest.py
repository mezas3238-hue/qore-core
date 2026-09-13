"""Exploratory retained-evidence replay for VT-08 Index C2 Positional R1."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import cast
from zoneinfo import ZoneInfo

from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    AUTHORIZED_MARKETS,
    DAILY_SELECTION_POLICY,
    LTF_PROFILE,
    METHODOLOGY_ID,
    METHODOLOGY_VERSION,
    OPERATIONAL_CONTAINMENTS,
    OWNER_ENTRY_ANCHORS_NY,
    TARGET_POLICY,
    TRADER_CODE,
    TRADER_VERSION,
    Vt08IndexC2R1Bar,
    Vt08IndexC2R1Candidate,
    evaluate_at_entry_indexed,
    methodology_fingerprint,
)
from qore.kernel.errors import InfrastructureError

SCHEMA = "qore.trader_lab.vt08_index_c2_positional_r1_backtest.v1"
SOURCE_RUN_ID = 34661791159
SOURCE_SOFTWARE_SHA = "a5b9c6e0d65539c1f755dda8bb3d7ce7b1a839b0"
EXPECTED_PROVIDER_SYMBOLS = {
    "NAS100": "USTEC",
    "SP500": "US500",
    "US30": "US30",
}
_NY = ZoneInfo("America/New_York")


class Vt08IndexC2R1BacktestError(InfrastructureError):
    __slots__ = ()


@dataclass(frozen=True, slots=True)
class ModeledTrade:
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
    return_rate: Decimal

    def payload(self) -> dict[str, object]:
        return {
            "symbol": self.symbol,
            "signal_at": self.signal_at.astimezone(UTC).isoformat(),
            "exited_at": self.exited_at.astimezone(UTC).isoformat(),
            "anchor_hour_new_york": self.anchor_hour_ny,
            "side": self.side.value,
            "entry": format(self.entry, "f"),
            "stop": format(self.stop, "f"),
            "target": format(self.target, "f"),
            "exit_price": format(self.exit_price, "f"),
            "exit_reason": self.exit_reason,
            "r_multiple": format(self.r_multiple, "f"),
            "return_rate": format(self.return_rate, "f"),
        }


@dataclass(frozen=True, slots=True)
class MarketReplay:
    symbol: str
    provider_symbol: str
    account_fingerprint: str
    checked_at: datetime
    candidate_count: int
    candidates_by_anchor: tuple[tuple[int, int], ...]
    abstain_reasons: tuple[tuple[str, int], ...]
    single_candidate_day_count: int
    multiple_candidate_day_count: int
    incomplete_exit_window_count: int
    trades: tuple[ModeledTrade, ...]

    def payload(self) -> dict[str, object]:
        return {
            "symbol": self.symbol,
            "provider_symbol": self.provider_symbol,
            "account_fingerprint": self.account_fingerprint,
            "checked_at": self.checked_at.astimezone(UTC).isoformat(),
            "candidate_count": self.candidate_count,
            "candidates_by_anchor_new_york": {
                f"{hour:02d}:00": count for hour, count in self.candidates_by_anchor
            },
            "abstain_reasons": dict(self.abstain_reasons),
            "single_candidate_day_count": self.single_candidate_day_count,
            "multiple_candidate_day_count": self.multiple_candidate_day_count,
            "incomplete_exit_window_count": self.incomplete_exit_window_count,
            "economics": summarize_trades(self.trades),
            "by_anchor_new_york": {
                f"{hour:02d}:00": summarize_trades(
                    tuple(item for item in self.trades if item.anchor_hour_ny == hour)
                )
                for hour in OWNER_ENTRY_ANCHORS_NY
            },
            "trades": [item.payload() for item in self.trades],
        }


def _object(value: object, *, name: str) -> dict[str, object]:
    if type(value) is not dict or any(type(key) is not str for key in value):
        raise Vt08IndexC2R1BacktestError(f"{name} must be an object")
    return cast(dict[str, object], value)


def _array(value: object, *, name: str) -> list[object]:
    if type(value) is not list:
        raise Vt08IndexC2R1BacktestError(f"{name} must be an array")
    return cast(list[object], value)


def _text(value: object, *, name: str) -> str:
    if type(value) is not str or not value:
        raise Vt08IndexC2R1BacktestError(f"{name} must be non-empty text")
    return value


def _bool(value: object, *, name: str) -> bool:
    if type(value) is not bool:
        raise Vt08IndexC2R1BacktestError(f"{name} must be bool")
    return value


def _timestamp(value: object, *, name: str) -> datetime:
    raw = _text(value, name=name)
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as error:
        raise Vt08IndexC2R1BacktestError(f"{name} must be RFC3339") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise Vt08IndexC2R1BacktestError(f"{name} must be timezone-aware")
    return parsed.astimezone(UTC)


def _decimal(value: object, *, name: str) -> Decimal:
    raw = _text(value, name=name)
    try:
        parsed = Decimal(raw)
    except InvalidOperation as error:
        raise Vt08IndexC2R1BacktestError(f"{name} must be Decimal text") from error
    if not parsed.is_finite() or parsed <= 0:
        raise Vt08IndexC2R1BacktestError(
            f"{name} must be a positive finite Decimal"
        )
    return parsed


def _parse_m15(row: object) -> Vt08IndexC2R1Bar:
    payload = _object(row, name="M15 bar")
    if payload.get("period") != "M15":
        raise Vt08IndexC2R1BacktestError("bar period must be M15")
    return Vt08IndexC2R1Bar(
        opened_at=_timestamp(payload.get("opened_at"), name="opened_at"),
        closed_at=_timestamp(payload.get("closed_at"), name="closed_at"),
        open=_decimal(payload.get("open"), name="open"),
        high=_decimal(payload.get("high"), name="high"),
        low=_decimal(payload.get("low"), name="low"),
        close=_decimal(payload.get("close"), name="close"),
    )


def _load_market(
    path: Path,
    *,
    expected_symbol: str,
) -> tuple[str, str, datetime, tuple[Vt08IndexC2R1Bar, ...]]:
    try:
        decoded: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise Vt08IndexC2R1BacktestError("cannot read market evidence") from error
    payload = _object(decoded, name="market evidence")
    if payload.get("environment") != "demo":
        raise Vt08IndexC2R1BacktestError("market evidence must be DEMO")
    if not _bool(payload.get("read_only"), name="read_only"):
        raise Vt08IndexC2R1BacktestError("market evidence must be read-only")
    if _bool(payload.get("account_is_live"), name="account_is_live"):
        raise Vt08IndexC2R1BacktestError("LIVE evidence is prohibited")
    if _text(payload.get("canonical_symbol"), name="canonical_symbol") != expected_symbol:
        raise Vt08IndexC2R1BacktestError("canonical symbol mismatch")
    if expected_symbol not in AUTHORIZED_MARKETS:
        raise Vt08IndexC2R1BacktestError("symbol is outside R1 scope")
    if _text(payload.get("software_sha"), name="software_sha") != SOURCE_SOFTWARE_SHA:
        raise Vt08IndexC2R1BacktestError("retained evidence software SHA drifted")
    provider_symbol = _text(
        payload.get("provider_symbol_name"),
        name="provider_symbol_name",
    )
    if provider_symbol != EXPECTED_PROVIDER_SYMBOLS[expected_symbol]:
        raise Vt08IndexC2R1BacktestError("provider symbol mapping drifted")
    fingerprint = _text(
        payload.get("account_fingerprint"),
        name="account_fingerprint",
    )
    if len(fingerprint) != 64:
        raise Vt08IndexC2R1BacktestError("account fingerprint must be SHA-256")
    checked_at = _timestamp(payload.get("checked_at"), name="checked_at")

    primary_hash = _text(
        payload.get("primary_source_sha256"),
        name="primary_source_sha256",
    )
    if re.fullmatch(r"[0-9a-f]{64}", primary_hash) is None:
        raise Vt08IndexC2R1BacktestError("primary source hash is invalid")

    periods = _object(payload.get("periods"), name="periods")
    rows = _array(periods.get("M15"), name="periods.M15")
    bars = tuple(_parse_m15(row) for row in rows)
    if not bars:
        raise Vt08IndexC2R1BacktestError("M15 evidence is empty")
    if bars != tuple(sorted(bars, key=lambda item: item.opened_at)):
        raise Vt08IndexC2R1BacktestError("M15 evidence must be chronological")
    if len({item.opened_at for item in bars}) != len(bars):
        raise Vt08IndexC2R1BacktestError("M15 evidence contains duplicate opens")
    if bars[-1].closed_at - bars[0].opened_at < timedelta(days=730):
        raise Vt08IndexC2R1BacktestError("M15 evidence must span at least 730 days")
    return fingerprint, provider_symbol, checked_at, bars


def _touches(bar: Vt08IndexC2R1Bar, price: Decimal) -> bool:
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


def _r_multiple(
    *,
    side: DemoTradingSetupSide,
    entry: Decimal,
    stop: Decimal,
    exit_price: Decimal,
) -> Decimal:
    risk = entry - stop if side is DemoTradingSetupSide.LONG else stop - entry
    if risk <= 0:
        raise Vt08IndexC2R1BacktestError("modeled trade risk must be positive")
    pnl = (
        exit_price - entry
        if side is DemoTradingSetupSide.LONG
        else entry - exit_price
    )
    return pnl / risk


def _model_trade(
    candidate: Vt08IndexC2R1Candidate,
    *,
    bars_by_open: dict[datetime, Vt08IndexC2R1Bar],
) -> ModeledTrade | None:
    start = candidate.decision_at.astimezone(UTC)
    retained: list[Vt08IndexC2R1Bar] = []
    cursor = start
    for _ in range(16):
        bar = bars_by_open.get(cursor)
        if bar is None or bar.closed_at.astimezone(UTC) != cursor + timedelta(minutes=15):
            return None
        retained.append(bar)
        cursor += timedelta(minutes=15)

    setup = candidate.setup
    exit_price = retained[-1].close
    exited_at = retained[-1].closed_at
    reason = "h4_containment_exit"
    for bar in retained:
        stop_hit = _touches(bar, setup.invalidation_price)
        target_hit = _touches(bar, setup.take_profit_price)
        if stop_hit:
            exit_price = setup.invalidation_price
            exited_at = bar.closed_at
            reason = "stop"
            break
        if target_hit:
            exit_price = setup.take_profit_price
            exited_at = bar.closed_at
            reason = "target"
            break

    return ModeledTrade(
        symbol=candidate.symbol,
        signal_at=start,
        exited_at=exited_at,
        anchor_hour_ny=candidate.entry_anchor_hour,
        side=candidate.side,
        entry=setup.entry_price,
        stop=setup.invalidation_price,
        target=setup.take_profit_price,
        exit_price=exit_price,
        exit_reason=reason,
        r_multiple=_r_multiple(
            side=candidate.side,
            entry=setup.entry_price,
            stop=setup.invalidation_price,
            exit_price=exit_price,
        ),
        return_rate=_return_rate(
            side=candidate.side,
            entry=setup.entry_price,
            exit_price=exit_price,
        ),
    )


def _max_drawdown_r(values: tuple[Decimal, ...]) -> Decimal:
    equity = Decimal(0)
    peak = Decimal(0)
    drawdown = Decimal(0)
    for value in values:
        equity += value
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
    return drawdown


def _max_losing_streak(values: tuple[Decimal, ...]) -> int:
    best = 0
    current = 0
    for value in values:
        if value < 0:
            current += 1
            best = max(best, current)
        else:
            current = 0
    return best


def summarize_trades(trades: tuple[ModeledTrade, ...]) -> dict[str, object]:
    values = tuple(item.r_multiple for item in trades)
    sample = len(values)
    wins = sum(value > 0 for value in values)
    losses = sum(value < 0 for value in values)
    flat = sample - wins - losses
    gross_profit = sum((value for value in values if value > 0), Decimal(0))
    gross_loss = -sum((value for value in values if value < 0), Decimal(0))
    total = sum(values, Decimal(0))
    mean = total / Decimal(sample) if sample else Decimal(0)
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else None
    return {
        "sample_size": sample,
        "winning_trades": wins,
        "losing_trades": losses,
        "flat_trades": flat,
        "win_rate": format(Decimal(wins) / Decimal(sample), "f") if sample else "0",
        "gross_profit_r": format(gross_profit, "f"),
        "gross_loss_r": format(gross_loss, "f"),
        "profit_factor": format(profit_factor, "f") if profit_factor is not None else None,
        "total_r": format(total, "f"),
        "mean_r": format(mean, "f"),
        "max_drawdown_r": format(_max_drawdown_r(values), "f"),
        "max_losing_streak": _max_losing_streak(values),
        "long_count": sum(item.side is DemoTradingSetupSide.LONG for item in trades),
        "short_count": sum(item.side is DemoTradingSetupSide.SHORT for item in trades),
        "stop_count": sum(item.exit_reason == "stop" for item in trades),
        "target_count": sum(item.exit_reason == "target" for item in trades),
        "h4_containment_exit_count": sum(
            item.exit_reason == "h4_containment_exit" for item in trades
        ),
    }


def run_market(path: Path, *, expected_symbol: str) -> MarketReplay:
    fingerprint, provider_symbol, checked_at, bars = _load_market(
        path,
        expected_symbol=expected_symbol,
    )
    bars_by_open = {item.opened_at.astimezone(UTC): item for item in bars}
    abstains: Counter[str] = Counter()
    candidates_by_day: dict[date, list[Vt08IndexC2R1Candidate]] = defaultdict(list)
    candidates_by_anchor: Counter[int] = Counter()

    for bar in bars:
        local = bar.opened_at.astimezone(_NY)
        if local.minute != 0 or local.hour not in OWNER_ENTRY_ANCHORS_NY:
            continue
        result = evaluate_at_entry_indexed(
            symbol=expected_symbol,
            bars_by_open=bars_by_open,
            decision_at=bar.opened_at,
        )
        if result.candidate is None:
            assert result.abstain_reason is not None
            abstains[result.abstain_reason.value] += 1
            continue
        candidate = result.candidate
        candidates_by_day[local.date()].append(candidate)
        candidates_by_anchor[candidate.entry_anchor_hour] += 1

    candidate_count = sum(len(items) for items in candidates_by_day.values())
    single_days = 0
    multiple_days = 0
    incomplete_exit = 0
    trades: list[ModeledTrade] = []
    for day in sorted(candidates_by_day):
        candidates = candidates_by_day[day]
        if len(candidates) != 1:
            multiple_days += 1
            continue
        single_days += 1
        modeled = _model_trade(candidates[0], bars_by_open=bars_by_open)
        if modeled is None:
            incomplete_exit += 1
            continue
        trades.append(modeled)

    return MarketReplay(
        symbol=expected_symbol,
        provider_symbol=provider_symbol,
        account_fingerprint=fingerprint,
        checked_at=checked_at,
        candidate_count=candidate_count,
        candidates_by_anchor=tuple(
            (hour, candidates_by_anchor[hour]) for hour in OWNER_ENTRY_ANCHORS_NY
        ),
        abstain_reasons=tuple(sorted(abstains.items())),
        single_candidate_day_count=single_days,
        multiple_candidate_day_count=multiple_days,
        incomplete_exit_window_count=incomplete_exit,
        trades=tuple(trades),
    )


def build_report(
    *,
    nas100: Path,
    sp500: Path,
    us30: Path,
) -> dict[str, object]:
    markets = (
        run_market(nas100, expected_symbol="NAS100"),
        run_market(sp500, expected_symbol="SP500"),
        run_market(us30, expected_symbol="US30"),
    )
    all_trades = tuple(
        sorted(
            (trade for market in markets for trade in market.trades),
            key=lambda item: (item.signal_at, item.symbol),
        )
    )
    return {
        "schema": SCHEMA,
        "environment": "demo",
        "read_only": True,
        "research_only": True,
        "consumed_evidence": True,
        "fresh_holdout": False,
        "source_run_id": SOURCE_RUN_ID,
        "source_software_sha": SOURCE_SOFTWARE_SHA,
        "trader_code": TRADER_CODE,
        "trader_version": TRADER_VERSION,
        "methodology_id": METHODOLOGY_ID,
        "methodology_version": METHODOLOGY_VERSION,
        "methodology_fingerprint": methodology_fingerprint(),
        "ltf_profile": LTF_PROFILE,
        "owner_entry_anchors_new_york": list(OWNER_ENTRY_ANCHORS_NY),
        "target_policy": TARGET_POLICY,
        "daily_selection_policy": DAILY_SELECTION_POLICY,
        "cost_model": "zero-cost-structural-r-replay",
        "operational_containments": list(OPERATIONAL_CONTAINMENTS),
        "markets": [market.payload() for market in markets],
        "aggregate_equal_risk_trade_economics": summarize_trades(all_trades),
        "aggregate_by_anchor_new_york": {
            f"{hour:02d}:00": summarize_trades(
                tuple(item for item in all_trades if item.anchor_hour_ny == hour)
            )
            for hour in OWNER_ENTRY_ANCHORS_NY
        },
        "governance": {
            "pre_economic_freeze_commit": "31bee8643cb09659a66e9ed793c1cb2bf9ba6353",
            "rules_selected_from_retained_economic_outcomes": False,
            "retained_window_is_independent_validation": False,
            "fresh_unseen_validation_required": True,
            "demo_eligible": False,
            "live_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nas100", type=Path, required=True)
    parser.add_argument("--sp500", type=Path, required=True)
    parser.add_argument("--us30", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = build_report(
        nas100=args.nas100,
        sp500=args.sp500,
        us30=args.us30,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(
        report,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    args.out.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)


if __name__ == "__main__":
    main()
