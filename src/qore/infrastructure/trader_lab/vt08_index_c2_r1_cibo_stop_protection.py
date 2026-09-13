"""CIBO intratrade stop-protection transfer study for frozen VT-08 Index R1.

The exact R1 signal stream remains immutable.  This module applies only the
pre-existing R3.16 CIBO stop-ratchet families to retained M15 paths.  It grants
no Trader, Risk, Execution, DEMO, LIVE or production authority.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from pathlib import Path
from typing import cast
from zoneinfo import ZoneInfo

from qore.kernel.errors import InfrastructureError

SCHEMA = "qore.trader_lab.vt08_index_c2_r1_cibo_stop_protection.v1"
EXPECTED_R1_SCHEMA = "qore.trader_lab.vt08_index_c2_positional_r1_backtest.v1"
EXPECTED_R1_HEAD = "5232540cdb444473ddf0bfae01beb2e672cea344"
EXPECTED_R1_ARTIFACT_ID = 10323025742
EXPECTED_R1_FREEZE = "31bee8643cb09659a66e9ed793c1cb2bf9ba6353"
TRANSFER_FREEZE = "404b163b096b9927b145d5ea446755d50e2d99e3"
EXPECTED_SOURCE_SHA = "a5b9c6e0d65539c1f755dda8bb3d7ce7b1a839b0"
EXPECTED_SIGNAL_COUNT = 152
EXPECTED_SIGNAL_IDENTITY_SHA256 = (
    "f29bb0c1877b38f535671730c34623df9210465ae7743b640dac2c2d2c8e7d7d"
)
EXPECTED_MARKETS = ("NAS100", "SP500", "US30")
EXPECTED_ANCHORS = (2, 6, 10)
EXPECTED_PROVIDER_SYMBOLS = {
    "NAS100": "USTEC",
    "SP500": "US500",
    "US30": "US30",
}
_NY = ZoneInfo("America/New_York")


class Vt08IndexC2R1CiboProtectionError(InfrastructureError):
    __slots__ = ()


@dataclass(frozen=True, slots=True)
class StopPolicy:
    name: str
    ratchets: tuple[tuple[Decimal, Decimal], ...]

    def __post_init__(self) -> None:
        previous_trigger = Decimal("-Infinity")
        previous_lock = Decimal("-Infinity")
        for trigger, lock in self.ratchets:
            if not trigger.is_finite() or not lock.is_finite():
                raise Vt08IndexC2R1CiboProtectionError("ratchets must be finite")
            if trigger <= previous_trigger or lock <= previous_lock:
                raise Vt08IndexC2R1CiboProtectionError(
                    "ratchets must increase monotonically"
                )
            previous_trigger = trigger
            previous_lock = lock


STOP_POLICIES = (
    StopPolicy("off", ()),
    StopPolicy(
        "soft",
        (
            (Decimal("0.75"), Decimal("-0.50")),
            (Decimal("1.25"), Decimal("0.00")),
            (Decimal("1.60"), Decimal("0.50")),
        ),
    ),
    StopPolicy(
        "be050-lock050-at100",
        (
            (Decimal("0.50"), Decimal("0.00")),
            (Decimal("1.00"), Decimal("0.50")),
        ),
    ),
    StopPolicy(
        "aggressive",
        (
            (Decimal("0.50"), Decimal("0.00")),
            (Decimal("1.00"), Decimal("0.50")),
            (Decimal("1.50"), Decimal("1.00")),
        ),
    ),
)


@dataclass(frozen=True, slots=True)
class Bar:
    opened_at: datetime
    closed_at: datetime
    high: Decimal
    low: Decimal
    close: Decimal


@dataclass(frozen=True, slots=True)
class R1Trade:
    symbol: str
    signal_at: datetime
    baseline_exited_at: datetime
    anchor_hour_ny: int
    side: str
    entry: Decimal
    stop: Decimal
    target: Decimal
    baseline_exit_price: Decimal
    baseline_exit_reason: str
    baseline_r: Decimal

    @property
    def risk_price(self) -> Decimal:
        return abs(self.entry - self.stop)

    @property
    def signal_key(self) -> tuple[str, str, str]:
        return (self.signal_at.astimezone(UTC).isoformat(), self.symbol, self.side)


@dataclass(frozen=True, slots=True)
class PolicyTrade:
    signal_key: tuple[str, str, str]
    symbol: str
    signal_at: datetime
    exited_at: datetime
    anchor_hour_ny: int
    side: str
    exit_reason: str
    exit_price: Decimal
    r_multiple: Decimal
    baseline_exit_reason: str
    baseline_r: Decimal

    def payload(self) -> dict[str, object]:
        return {
            "signal_key": list(self.signal_key),
            "symbol": self.symbol,
            "signal_at": self.signal_at.astimezone(UTC).isoformat(),
            "exited_at": self.exited_at.astimezone(UTC).isoformat(),
            "anchor_hour_new_york": self.anchor_hour_ny,
            "side": self.side,
            "exit_reason": self.exit_reason,
            "exit_price": format(self.exit_price, "f"),
            "r_multiple": format(self.r_multiple, "f"),
            "baseline_exit_reason": self.baseline_exit_reason,
            "baseline_r": format(self.baseline_r, "f"),
        }


def _object(value: object, *, name: str) -> dict[str, object]:
    if type(value) is not dict or any(type(key) is not str for key in value):
        raise Vt08IndexC2R1CiboProtectionError(f"{name} must be an object")
    return cast(dict[str, object], value)


def _array(value: object, *, name: str) -> list[object]:
    if type(value) is not list:
        raise Vt08IndexC2R1CiboProtectionError(f"{name} must be an array")
    return cast(list[object], value)


def _text(value: object, *, name: str) -> str:
    if type(value) is not str or not value:
        raise Vt08IndexC2R1CiboProtectionError(f"{name} must be non-empty text")
    return value


def _integer(value: object, *, name: str) -> int:
    if type(value) is not int:
        raise Vt08IndexC2R1CiboProtectionError(f"{name} must be int")
    return value


def _decimal(value: object, *, name: str) -> Decimal:
    raw = _text(value, name=name)
    try:
        parsed = Decimal(raw)
    except InvalidOperation as error:
        raise Vt08IndexC2R1CiboProtectionError(f"{name} must be Decimal text") from error
    if not parsed.is_finite():
        raise Vt08IndexC2R1CiboProtectionError(f"{name} must be finite")
    return parsed


def _timestamp(value: object, *, name: str) -> datetime:
    raw = _text(value, name=name)
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as error:
        raise Vt08IndexC2R1CiboProtectionError(f"{name} must be RFC3339") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise Vt08IndexC2R1CiboProtectionError(f"{name} must be timezone-aware")
    return parsed.astimezone(UTC)


def _read_json(path: Path, *, name: str) -> dict[str, object]:
    try:
        decoded: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise Vt08IndexC2R1CiboProtectionError(f"cannot read {name}") from error
    return _object(decoded, name=name)


def signal_identity_sha256(trades: Iterable[R1Trade]) -> str:
    keys = sorted(item.signal_key for item in trades)
    encoded = json.dumps(
        keys,
        ensure_ascii=True,
        sort_keys=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def load_r1(path: Path) -> tuple[R1Trade, ...]:
    payload = _read_json(path, name="R1 artifact")
    if payload.get("schema") != EXPECTED_R1_SCHEMA:
        raise Vt08IndexC2R1CiboProtectionError("unexpected R1 schema")
    if payload.get("source_software_sha") != EXPECTED_SOURCE_SHA:
        raise Vt08IndexC2R1CiboProtectionError("R1 source SHA drifted")
    if payload.get("owner_entry_anchors_new_york") != list(EXPECTED_ANCHORS):
        raise Vt08IndexC2R1CiboProtectionError("R1 anchor set drifted")
    if payload.get("research_only") is not True:
        raise Vt08IndexC2R1CiboProtectionError("R1 must remain research-only")
    if payload.get("consumed_evidence") is not True or payload.get("fresh_holdout") is not False:
        raise Vt08IndexC2R1CiboProtectionError("R1 evidence governance drifted")
    governance = _object(payload.get("governance"), name="R1 governance")
    if governance.get("pre_economic_freeze_commit") != EXPECTED_R1_FREEZE:
        raise Vt08IndexC2R1CiboProtectionError("R1 freeze binding drifted")
    if any(
        governance.get(key) is not False
        for key in ("demo_eligible", "live_authorized", "production_authorized")
    ):
        raise Vt08IndexC2R1CiboProtectionError("R1 has forbidden authority")

    markets = _array(payload.get("markets"), name="R1 markets")
    trades: list[R1Trade] = []
    seen_markets: set[str] = set()
    for market_raw in markets:
        market = _object(market_raw, name="R1 market")
        symbol = _text(market.get("symbol"), name="R1 market symbol")
        seen_markets.add(symbol)
        for raw_trade in _array(market.get("trades"), name=f"{symbol}.trades"):
            trade = _object(raw_trade, name="R1 trade")
            if _text(trade.get("symbol"), name="trade.symbol") != symbol:
                raise Vt08IndexC2R1CiboProtectionError("trade/market mismatch")
            side = _text(trade.get("side"), name="trade.side")
            if side not in {"long", "short"}:
                raise Vt08IndexC2R1CiboProtectionError("unexpected R1 side")
            anchor = _integer(
                trade.get("anchor_hour_new_york"),
                name="anchor_hour_new_york",
            )
            if anchor not in EXPECTED_ANCHORS:
                raise Vt08IndexC2R1CiboProtectionError("unexpected R1 anchor")
            item = R1Trade(
                symbol=symbol,
                signal_at=_timestamp(trade.get("signal_at"), name="signal_at"),
                baseline_exited_at=_timestamp(
                    trade.get("exited_at"),
                    name="exited_at",
                ),
                anchor_hour_ny=anchor,
                side=side,
                entry=_decimal(trade.get("entry"), name="entry"),
                stop=_decimal(trade.get("stop"), name="stop"),
                target=_decimal(trade.get("target"), name="target"),
                baseline_exit_price=_decimal(
                    trade.get("exit_price"),
                    name="exit_price",
                ),
                baseline_exit_reason=_text(
                    trade.get("exit_reason"),
                    name="exit_reason",
                ),
                baseline_r=_decimal(trade.get("r_multiple"), name="r_multiple"),
            )
            if item.risk_price <= 0:
                raise Vt08IndexC2R1CiboProtectionError("R1 risk distance must be positive")
            trades.append(item)

    if tuple(sorted(seen_markets)) != EXPECTED_MARKETS:
        raise Vt08IndexC2R1CiboProtectionError("R1 market set drifted")
    ordered = tuple(sorted(trades, key=lambda item: (item.signal_at, item.symbol)))
    if len(ordered) != EXPECTED_SIGNAL_COUNT:
        raise Vt08IndexC2R1CiboProtectionError("R1 signal count drifted")
    if len({item.signal_key for item in ordered}) != len(ordered):
        raise Vt08IndexC2R1CiboProtectionError("R1 signal identity contains duplicates")
    if signal_identity_sha256(ordered) != EXPECTED_SIGNAL_IDENTITY_SHA256:
        raise Vt08IndexC2R1CiboProtectionError("R1 signal identity hash drifted")
    return ordered


def load_market_bars(path: Path, *, expected_symbol: str) -> dict[datetime, Bar]:
    payload = _read_json(path, name=f"{expected_symbol} market evidence")
    if payload.get("environment") != "demo" or payload.get("read_only") is not True:
        raise Vt08IndexC2R1CiboProtectionError("market evidence must be DEMO/read-only")
    if payload.get("account_is_live") is not False:
        raise Vt08IndexC2R1CiboProtectionError("LIVE market evidence is prohibited")
    if payload.get("software_sha") != EXPECTED_SOURCE_SHA:
        raise Vt08IndexC2R1CiboProtectionError("market evidence SHA drifted")
    if payload.get("canonical_symbol") != expected_symbol:
        raise Vt08IndexC2R1CiboProtectionError("canonical symbol mismatch")
    if payload.get("provider_symbol_name") != EXPECTED_PROVIDER_SYMBOLS[expected_symbol]:
        raise Vt08IndexC2R1CiboProtectionError("provider symbol mapping drifted")
    periods = _object(payload.get("periods"), name="periods")
    rows = _array(periods.get("M15"), name="periods.M15")
    result: dict[datetime, Bar] = {}
    for row_raw in rows:
        row = _object(row_raw, name="M15 row")
        if row.get("period") != "M15":
            raise Vt08IndexC2R1CiboProtectionError("retained bar must be M15")
        opened_at = _timestamp(row.get("opened_at"), name="opened_at")
        if opened_at in result:
            raise Vt08IndexC2R1CiboProtectionError("duplicate M15 open")
        bar = Bar(
            opened_at=opened_at,
            closed_at=_timestamp(row.get("closed_at"), name="closed_at"),
            high=_decimal(row.get("high"), name="high"),
            low=_decimal(row.get("low"), name="low"),
            close=_decimal(row.get("close"), name="close"),
        )
        if bar.closed_at != bar.opened_at + timedelta(minutes=15):
            raise Vt08IndexC2R1CiboProtectionError("M15 close boundary drifted")
        if bar.low > bar.high:
            raise Vt08IndexC2R1CiboProtectionError("invalid M15 high/low")
        result[opened_at] = bar
    if not result:
        raise Vt08IndexC2R1CiboProtectionError("market evidence has no M15 bars")
    return result


def _stop_price(trade: R1Trade, stop_r: Decimal) -> Decimal:
    if trade.side == "long":
        return trade.entry + stop_r * trade.risk_price
    return trade.entry - stop_r * trade.risk_price


def _stop_touched(trade: R1Trade, stop_price: Decimal, bar: Bar) -> bool:
    return bar.low <= stop_price if trade.side == "long" else bar.high >= stop_price


def _target_touched(trade: R1Trade, bar: Bar) -> bool:
    return bar.high >= trade.target if trade.side == "long" else bar.low <= trade.target


def _favorable_r(trade: R1Trade, bar: Bar) -> Decimal:
    if trade.side == "long":
        return (bar.high - trade.entry) / trade.risk_price
    return (trade.entry - bar.low) / trade.risk_price


def _close_r(trade: R1Trade, close: Decimal) -> Decimal:
    if trade.side == "long":
        return (close - trade.entry) / trade.risk_price
    return (trade.entry - close) / trade.risk_price


def replay_trade(
    trade: R1Trade,
    bars: Mapping[datetime, Bar],
    policy: StopPolicy,
) -> PolicyTrade:
    current_stop_r = Decimal("-1")
    cursor = trade.signal_at.astimezone(UTC)
    last: Bar | None = None
    for _ in range(16):
        bar = bars.get(cursor)
        if bar is None:
            raise Vt08IndexC2R1CiboProtectionError(
                f"missing M15 bar for {trade.signal_key} at {cursor.isoformat()}"
            )
        last = bar
        stop_price = _stop_price(trade, current_stop_r)
        if _stop_touched(trade, stop_price, bar):
            reason = "stop" if current_stop_r <= Decimal("-1") else "cibo_protected_stop"
            return PolicyTrade(
                signal_key=trade.signal_key,
                symbol=trade.symbol,
                signal_at=trade.signal_at,
                exited_at=bar.closed_at,
                anchor_hour_ny=trade.anchor_hour_ny,
                side=trade.side,
                exit_reason=reason,
                exit_price=stop_price,
                r_multiple=current_stop_r,
                baseline_exit_reason=trade.baseline_exit_reason,
                baseline_r=trade.baseline_r,
            )
        if _target_touched(trade, bar):
            return PolicyTrade(
                signal_key=trade.signal_key,
                symbol=trade.symbol,
                signal_at=trade.signal_at,
                exited_at=bar.closed_at,
                anchor_hour_ny=trade.anchor_hour_ny,
                side=trade.side,
                exit_reason="target",
                exit_price=trade.target,
                r_multiple=Decimal("2"),
                baseline_exit_reason=trade.baseline_exit_reason,
                baseline_r=trade.baseline_r,
            )
        favorable = _favorable_r(trade, bar)
        for trigger_r, lock_r in policy.ratchets:
            if favorable >= trigger_r and lock_r > current_stop_r:
                current_stop_r = lock_r
        cursor += timedelta(minutes=15)

    if last is None:
        raise Vt08IndexC2R1CiboProtectionError("trade has no replay bars")
    return PolicyTrade(
        signal_key=trade.signal_key,
        symbol=trade.symbol,
        signal_at=trade.signal_at,
        exited_at=last.closed_at,
        anchor_hour_ny=trade.anchor_hour_ny,
        side=trade.side,
        exit_reason="h4_containment_exit",
        exit_price=last.close,
        r_multiple=_close_r(trade, last.close),
        baseline_exit_reason=trade.baseline_exit_reason,
        baseline_r=trade.baseline_r,
    )


def _max_drawdown(values: Iterable[Decimal]) -> Decimal:
    equity = Decimal(0)
    peak = Decimal(0)
    maximum = Decimal(0)
    for value in values:
        equity += value
        peak = max(peak, equity)
        maximum = max(maximum, peak - equity)
    return maximum


def _max_losing_streak(values: Iterable[Decimal]) -> int:
    maximum = 0
    current = 0
    for value in values:
        if value < 0:
            current += 1
            maximum = max(maximum, current)
        else:
            current = 0
    return maximum


def summarize(trades: tuple[PolicyTrade, ...]) -> dict[str, object]:
    values = tuple(item.r_multiple for item in trades)
    sample = len(values)
    wins = sum(value > 0 for value in values)
    losses = sum(value < 0 for value in values)
    flats = sample - wins - losses
    gross_profit = sum((value for value in values if value > 0), Decimal(0))
    gross_loss = -sum((value for value in values if value < 0), Decimal(0))
    total = sum(values, Decimal(0))
    mean = total / Decimal(sample) if sample else Decimal(0)
    pf = gross_profit / gross_loss if gross_loss > 0 else None
    return {
        "sample_size": sample,
        "winning_trades": wins,
        "losing_trades": losses,
        "flat_trades": flats,
        "win_rate": format(Decimal(wins) / Decimal(sample), "f") if sample else "0",
        "gross_profit_r": format(gross_profit, "f"),
        "gross_loss_r": format(gross_loss, "f"),
        "profit_factor": format(pf, "f") if pf is not None else None,
        "total_r": format(total, "f"),
        "mean_r": format(mean, "f"),
        "max_drawdown_r": format(_max_drawdown(values), "f"),
        "max_losing_streak": _max_losing_streak(values),
        "full_stop_count": sum(item.exit_reason == "stop" for item in trades),
        "cibo_protected_stop_count": sum(
            item.exit_reason == "cibo_protected_stop" for item in trades
        ),
        "target_count": sum(item.exit_reason == "target" for item in trades),
        "h4_containment_exit_count": sum(
            item.exit_reason == "h4_containment_exit" for item in trades
        ),
    }


def _group(
    trades: tuple[PolicyTrade, ...],
    key: Callable[[PolicyTrade], str],
) -> dict[str, object]:
    buckets: dict[str, list[PolicyTrade]] = defaultdict(list)
    for trade in trades:
        buckets[key(trade)].append(trade)
    return {
        label: summarize(tuple(rows))
        for label, rows in sorted(buckets.items())
    }


def _chronological_halves(
    trades: tuple[PolicyTrade, ...],
) -> dict[str, object]:
    ordered = tuple(sorted(trades, key=lambda item: (item.signal_at, item.symbol)))
    middle = len(ordered) // 2
    return {
        "first": summarize(ordered[:middle]),
        "second": summarize(ordered[middle:]),
    }


def _policy_payload(
    policy: StopPolicy,
    trades: tuple[PolicyTrade, ...],
) -> dict[str, object]:
    return {
        "policy": policy.name,
        "ratchets": [
            {"trigger_r": format(trigger, "f"), "lock_r": format(lock, "f")}
            for trigger, lock in policy.ratchets
        ],
        "signal_count": len(trades),
        "signal_identity_sha256": EXPECTED_SIGNAL_IDENTITY_SHA256,
        "aggregate": summarize(trades),
        "by_market": _group(trades, lambda item: item.symbol),
        "by_anchor_new_york": _group(
            trades,
            lambda item: f"{item.anchor_hour_ny:02d}:00",
        ),
        "by_side": _group(trades, lambda item: item.side),
        "by_year_new_york": _group(
            trades,
            lambda item: str(item.signal_at.astimezone(_NY).year),
        ),
        "chronological_halves": _chronological_halves(trades),
        "trades": [item.payload() for item in trades],
    }


def _decimal_from_summary(summary: Mapping[str, object], key: str) -> Decimal:
    return Decimal(_text(summary.get(key), name=key))


def build_report(
    *,
    r1_path: Path,
    nas100: Path,
    sp500: Path,
    us30: Path,
) -> dict[str, object]:
    r1_trades = load_r1(r1_path)
    bars = {
        "NAS100": load_market_bars(nas100, expected_symbol="NAS100"),
        "SP500": load_market_bars(sp500, expected_symbol="SP500"),
        "US30": load_market_bars(us30, expected_symbol="US30"),
    }

    results: dict[str, dict[str, object]] = {}
    replayed: dict[str, tuple[PolicyTrade, ...]] = {}
    for policy in STOP_POLICIES:
        policy_trades = tuple(
            replay_trade(item, bars[item.symbol], policy)
            for item in r1_trades
        )
        if tuple(item.signal_key for item in policy_trades) != tuple(
            item.signal_key for item in r1_trades
        ):
            raise Vt08IndexC2R1CiboProtectionError("CIBO changed R1 signal identity")
        replayed[policy.name] = policy_trades
        results[policy.name] = _policy_payload(policy, policy_trades)

    off = replayed["off"]
    for baseline, replay in zip(r1_trades, off, strict=True):
        if replay.r_multiple != baseline.baseline_r:
            raise Vt08IndexC2R1CiboProtectionError(
                f"off policy failed R1 R reconciliation for {baseline.signal_key}"
            )
        if replay.exit_reason != baseline.baseline_exit_reason:
            raise Vt08IndexC2R1CiboProtectionError(
                f"off policy failed R1 exit reconciliation for {baseline.signal_key}"
            )
        if replay.exit_price != baseline.baseline_exit_price:
            raise Vt08IndexC2R1CiboProtectionError(
                f"off policy failed R1 price reconciliation for {baseline.signal_key}"
            )
        if replay.exited_at != baseline.baseline_exited_at:
            raise Vt08IndexC2R1CiboProtectionError(
                f"off policy failed R1 time reconciliation for {baseline.signal_key}"
            )

    off_summary = cast(dict[str, object], results["off"]["aggregate"])
    deltas: dict[str, object] = {}
    for policy in STOP_POLICIES:
        summary = cast(dict[str, object], results[policy.name]["aggregate"])
        deltas[policy.name] = {
            "full_stops_avoided_vs_off": (
                _integer(off_summary.get("full_stop_count"), name="off full stops")
                - _integer(summary.get("full_stop_count"), name="policy full stops")
            ),
            "protected_exits_added_vs_off": (
                _integer(
                    summary.get("cibo_protected_stop_count"),
                    name="protected stops",
                )
                - _integer(
                    off_summary.get("cibo_protected_stop_count"),
                    name="off protected stops",
                )
            ),
            "total_r_delta_vs_off": format(
                _decimal_from_summary(summary, "total_r")
                - _decimal_from_summary(off_summary, "total_r"),
                "f",
            ),
            "mean_r_delta_vs_off": format(
                _decimal_from_summary(summary, "mean_r")
                - _decimal_from_summary(off_summary, "mean_r"),
                "f",
            ),
            "max_drawdown_r_delta_vs_off": format(
                _decimal_from_summary(summary, "max_drawdown_r")
                - _decimal_from_summary(off_summary, "max_drawdown_r"),
                "f",
            ),
        }

    return {
        "schema": SCHEMA,
        "research_only": True,
        "consumed_evidence": True,
        "fresh_holdout": False,
        "parent_r1_head": EXPECTED_R1_HEAD,
        "parent_r1_artifact_id": EXPECTED_R1_ARTIFACT_ID,
        "parent_r1_freeze": EXPECTED_R1_FREEZE,
        "cibo_transfer_freeze": TRANSFER_FREEZE,
        "source_software_sha": EXPECTED_SOURCE_SHA,
        "signal_count": EXPECTED_SIGNAL_COUNT,
        "signal_identity_sha256": EXPECTED_SIGNAL_IDENTITY_SHA256,
        "policy_provenance": "pre-existing-vt08-cibo-r3.16-transfer-hypotheses",
        "same_bar_policy": (
            "active-stop-before-target; ratchet-observed-in-bar-applies-from-next-bar"
        ),
        "off_reconciles_parent_r1_exactly": True,
        "policies": results,
        "deltas_vs_off": deltas,
        "governance": {
            "trader_signal_mutation": False,
            "market_filtering_authorized": False,
            "anchor_filtering_authorized": False,
            "direction_filtering_authorized": False,
            "policy_selection_from_consumed_result_authorized": False,
            "fresh_unseen_validation_required": True,
            "cibo_decision_is_risk_authorization": False,
            "demo_eligible": False,
            "live_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--r1", type=Path, required=True)
    parser.add_argument("--nas100", type=Path, required=True)
    parser.add_argument("--sp500", type=Path, required=True)
    parser.add_argument("--us30", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = build_report(
        r1_path=args.r1,
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
