"""VT-08 R3.11 consumed-evidence Risk-aware economic replay.

Research-only. This module does not issue a production RiskAuthorization and does
not mutate VT-08 methodology. It projects already-consumed VT-08 B01 trades
through deterministic fixed-loss sizing, broker volume constraints, portfolio
heat, currency conversion, and price-cost stress.

The primary research policy is frozen independently of outcomes:
* normalized starting equity: USD 100,000;
* desired loss at stop: 50 bps of current equity per trade;
* aggregate open bounded-loss heat: 150 bps of current equity;
* cTrader protocol volume_step: 0.01 base units per protocol unit;
* broker min/max/step are taken from the historical market-evidence artifact;
* cost_bps is a stress proxy, not a claim about realized cTrader spread/fees.

Only the two consumed economic windows are admitted. Any trade before
2022-08-13T00:00:00Z is rejected at load time so the protected 2020-2022
candidate holdout cannot be consumed by this replay.
"""

from __future__ import annotations

import argparse
import json
from bisect import bisect_right
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import ROUND_FLOOR, Decimal
from pathlib import Path

CONSUMED_EVIDENCE_FLOOR = datetime(2022, 8, 13, tzinfo=UTC)
BASELINE_RUN_ID = 34693803930
FRESH_RUN_ID = 34707771460
CTRADER_VOLUME_STEP = Decimal("0.01")
PRIMARY_STARTING_EQUITY_USD = Decimal("100000")
PRIMARY_PER_TRADE_RISK_BPS = 50
PRIMARY_PORTFOLIO_HEAT_BPS = 150
PRIMARY_COST_BPS = Decimal("0")
COST_STRESS_GRID_BPS = (
    Decimal("0"),
    Decimal("0.1"),
    Decimal("0.25"),
    Decimal("0.5"),
    Decimal("1"),
    Decimal("2"),
)
EXPECTED_MARKETS = frozenset(
    {"AUDJPY", "AUDUSD", "EURUSD", "GBPJPY", "GBPUSD", "USDCAD", "USDJPY"}
)


class RiskEconomicReplayError(ValueError):
    """Raised when consumed evidence cannot be replayed safely."""


@dataclass(frozen=True, slots=True)
class BrokerVolumeConstraints:
    symbol: str
    min_quantity: Decimal
    max_quantity: Decimal
    step_quantity: Decimal

    @classmethod
    def from_market_evidence(
        cls, payload: Mapping[str, object]
    ) -> BrokerVolumeConstraints:
        symbol_raw = payload.get("symbol")
        if not isinstance(symbol_raw, Mapping):
            raise RiskEconomicReplayError("market evidence missing symbol metadata")
        symbol = str(symbol_raw["symbol_name"])
        return cls(
            symbol=symbol,
            min_quantity=(
                CTRADER_VOLUME_STEP * Decimal(str(symbol_raw["min_volume_units"]))
            ),
            max_quantity=(
                CTRADER_VOLUME_STEP * Decimal(str(symbol_raw["max_volume_units"]))
            ),
            step_quantity=(
                CTRADER_VOLUME_STEP * Decimal(str(symbol_raw["step_volume_units"]))
            ),
        )


@dataclass(frozen=True, slots=True)
class TradeObservation:
    window: str
    symbol: str
    side: str
    signal_at: datetime
    exited_at: datetime
    entry: Decimal
    stop: Decimal
    target: Decimal
    exit_price: Decimal
    exit_reason: str

    @property
    def risk_price(self) -> Decimal:
        return abs(self.entry - self.stop)


@dataclass(frozen=True, slots=True)
class RiskReplayPolicy:
    starting_equity_usd: Decimal = PRIMARY_STARTING_EQUITY_USD
    per_trade_risk_bps: int = PRIMARY_PER_TRADE_RISK_BPS
    portfolio_heat_bps: int = PRIMARY_PORTFOLIO_HEAT_BPS
    price_cost_bps: Decimal = PRIMARY_COST_BPS

    def __post_init__(self) -> None:
        if self.starting_equity_usd <= 0:
            raise RiskEconomicReplayError("starting equity must be positive")
        if not 0 < self.per_trade_risk_bps <= 10_000:
            raise RiskEconomicReplayError("per-trade risk bps must be in (0, 10000]")
        if not 0 < self.portfolio_heat_bps <= 10_000:
            raise RiskEconomicReplayError("portfolio heat bps must be in (0, 10000]")
        if self.portfolio_heat_bps < self.per_trade_risk_bps:
            raise RiskEconomicReplayError("portfolio heat cannot be below per-trade risk")
        if self.price_cost_bps < 0:
            raise RiskEconomicReplayError("price cost bps must not be negative")


@dataclass(frozen=True, slots=True)
class SizedTrade:
    observation: TradeObservation
    risk_outcome: str
    quantity: Decimal
    bounded_loss_usd: Decimal
    quote_to_usd_at_entry: Decimal
    gross_pnl_usd: Decimal
    cost_usd: Decimal
    net_pnl_usd: Decimal
    gross_r: Decimal
    net_r: Decimal


@dataclass(frozen=True, slots=True)
class OpenRisk:
    exit_at: datetime
    trade: SizedTrade


def _parse_time(value: object) -> datetime:
    if not isinstance(value, str):
        raise RiskEconomicReplayError("timestamp must be a string")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None or result.utcoffset() is None:
        raise RiskEconomicReplayError("timestamp must be timezone-aware")
    return result.astimezone(UTC)


def _read_json(path: Path) -> dict[str, object]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise RiskEconomicReplayError(f"{path} must contain a JSON object")
    return loaded


def _load_window(
    root: Path,
    *,
    window: str,
    trade_filename: str,
) -> tuple[
    list[TradeObservation],
    dict[str, BrokerVolumeConstraints],
    dict[str, dict[datetime, Decimal]],
]:
    trades: list[TradeObservation] = []
    constraints: dict[str, BrokerVolumeConstraints] = {}
    conversion_bars: dict[str, dict[datetime, Decimal]] = {}
    seen_symbols: set[str] = set()

    for trade_path in sorted(root.rglob(trade_filename)):
        payload = _read_json(trade_path)
        symbol = str(payload.get("symbol", ""))
        if symbol not in EXPECTED_MARKETS:
            continue
        if symbol in seen_symbols:
            raise RiskEconomicReplayError(f"duplicate {window} artifact for {symbol}")
        seen_symbols.add(symbol)
        evidence_path = trade_path.with_name("market-evidence.json")
        if not evidence_path.exists():
            raise RiskEconomicReplayError(f"market evidence missing beside {trade_path}")
        evidence = _read_json(evidence_path)
        constraint = BrokerVolumeConstraints.from_market_evidence(evidence)
        if constraint.symbol != symbol:
            raise RiskEconomicReplayError(f"symbol mismatch for {trade_path}")
        constraints[symbol] = constraint

        periods = evidence.get("periods")
        if not isinstance(periods, Mapping):
            raise RiskEconomicReplayError(f"periods missing for {symbol}")
        m15 = periods.get("M15")
        if not isinstance(m15, list):
            raise RiskEconomicReplayError(f"M15 evidence missing for {symbol}")
        bars: dict[datetime, Decimal] = {}
        for row in m15:
            if not isinstance(row, Mapping):
                continue
            bars[_parse_time(row["opened_at"])] = Decimal(str(row["open"]))
        conversion_bars[symbol] = bars

        raw_trades = payload.get("trades")
        if not isinstance(raw_trades, list):
            raise RiskEconomicReplayError(f"trades missing for {symbol}")
        for row in raw_trades:
            if not isinstance(row, Mapping):
                raise RiskEconomicReplayError("trade row must be an object")
            signal_at = _parse_time(row["signal_at"])
            if signal_at < CONSUMED_EVIDENCE_FLOOR:
                raise RiskEconomicReplayError(
                    "protected pre-2022-08-13 evidence access refused: "
                    f"{symbol} {signal_at.isoformat()}"
                )
            trades.append(
                TradeObservation(
                    window=window,
                    symbol=symbol,
                    side=str(row["side"]),
                    signal_at=signal_at,
                    exited_at=_parse_time(row["exited_at"]),
                    entry=Decimal(str(row["entry"])),
                    stop=Decimal(str(row["stop"])),
                    target=Decimal(str(row["target"])),
                    exit_price=Decimal(str(row["exit_price"])),
                    exit_reason=str(row["exit_reason"]),
                )
            )

    if seen_symbols != EXPECTED_MARKETS:
        missing = sorted(EXPECTED_MARKETS - seen_symbols)
        raise RiskEconomicReplayError(f"{window} missing expected markets: {missing}")
    return trades, constraints, conversion_bars


def load_consumed_evidence(
    baseline_root: Path,
    fresh_root: Path,
) -> tuple[
    list[TradeObservation],
    dict[str, BrokerVolumeConstraints],
    dict[str, dict[datetime, Decimal]],
]:
    baseline, baseline_constraints, baseline_bars = _load_window(
        baseline_root,
        window="baseline-2024-2026",
        trade_filename="b01-backtest.json",
    )
    fresh, fresh_constraints, fresh_bars = _load_window(
        fresh_root,
        window="fresh-2022-2024",
        trade_filename="holdout-market.json",
    )
    constraints = dict(baseline_constraints)
    for symbol, item in fresh_constraints.items():
        old = constraints.get(symbol)
        if old is not None and old != item:
            raise RiskEconomicReplayError(
                f"broker volume constraints changed across windows for {symbol}"
            )
        constraints[symbol] = item
    merged_bars: dict[str, dict[datetime, Decimal]] = {}
    for source in (baseline_bars, fresh_bars):
        for symbol, bars in source.items():
            merged_bars.setdefault(symbol, {}).update(bars)
    all_trades = baseline + fresh
    if len(all_trades) != 809:
        raise RiskEconomicReplayError(
            f"expected exactly 809 consumed trades, got {len(all_trades)}"
        )
    return all_trades, constraints, merged_bars


def _floor_to_step(value: Decimal, step: Decimal) -> Decimal:
    if value <= 0 or step <= 0:
        return Decimal(0)
    return (value / step).to_integral_value(rounding=ROUND_FLOOR) * step


def broker_valid_fixed_risk_quantity(
    *,
    desired_loss_usd: Decimal,
    per_unit_loss_usd: Decimal,
    constraints: BrokerVolumeConstraints,
) -> tuple[str, Decimal, Decimal]:
    if desired_loss_usd <= 0 or per_unit_loss_usd <= 0:
        return "REJECT", Decimal(0), Decimal(0)
    raw = desired_loss_usd / per_unit_loss_usd
    status = "ALLOW"
    if raw > constraints.max_quantity:
        raw = constraints.max_quantity
        status = "REDUCE"
    quantity = _floor_to_step(raw, constraints.step_quantity)
    if quantity < constraints.min_quantity:
        return "REJECT", Decimal(0), Decimal(0)
    actual_loss = quantity * per_unit_loss_usd
    return status, quantity, actual_loss


def _build_time_index(
    bars: Mapping[datetime, Decimal],
) -> tuple[list[datetime], list[Decimal]]:
    ordered = sorted(bars.items())
    return [item[0] for item in ordered], [item[1] for item in ordered]


def _price_at_or_before(
    index: tuple[list[datetime], list[Decimal]], at: datetime
) -> Decimal:
    times, prices = index
    pos = bisect_right(times, at) - 1
    if pos < 0:
        raise RiskEconomicReplayError(f"no conversion bar at or before {at.isoformat()}")
    return prices[pos]


def quote_to_usd_factor(
    symbol: str,
    at: datetime,
    *,
    instrument_price: Decimal,
    indices: Mapping[str, tuple[list[datetime], list[Decimal]]],
) -> Decimal:
    base = symbol[:3]
    quote = symbol[3:]
    if quote == "USD":
        return Decimal(1)
    if base == "USD":
        if instrument_price <= 0:
            raise RiskEconomicReplayError("instrument price must be positive")
        return Decimal(1) / instrument_price
    if quote == "JPY":
        usdjpy = indices.get("USDJPY")
        if usdjpy is None:
            raise RiskEconomicReplayError(
                "USDJPY conversion evidence is required for JPY crosses"
            )
        px = _price_at_or_before(usdjpy, at)
        if px <= 0:
            raise RiskEconomicReplayError("USDJPY conversion price must be positive")
        return Decimal(1) / px
    raise RiskEconomicReplayError(f"unsupported quote currency conversion for {symbol}")


def _gross_quote_pnl(trade: TradeObservation, quantity: Decimal) -> Decimal:
    delta = trade.exit_price - trade.entry
    if trade.side == "short":
        delta = -delta
    elif trade.side != "long":
        raise RiskEconomicReplayError(f"unsupported side {trade.side}")
    return quantity * delta


def _candidate_filter(name: str, trade: TradeObservation) -> bool:
    if name == "broad":
        return True
    if name == "candidate-a":
        return trade.side == "short" and trade.symbol in {"AUDJPY", "GBPUSD"}
    if name == "candidate-b":
        return trade.symbol == "GBPJPY" or (
            trade.side == "short" and trade.symbol in {"AUDJPY", "GBPUSD"}
        )
    raise RiskEconomicReplayError(f"unknown candidate {name}")


def replay_account(
    *,
    trades: Sequence[TradeObservation],
    constraints: Mapping[str, BrokerVolumeConstraints],
    conversion_bars: Mapping[str, Mapping[datetime, Decimal]],
    candidate: str,
    policy: RiskReplayPolicy,
) -> dict[str, object]:
    selected = sorted(
        (trade for trade in trades if _candidate_filter(candidate, trade)),
        key=lambda item: (item.signal_at, item.symbol, item.side),
    )
    indices = {
        symbol: _build_time_index(bars) for symbol, bars in conversion_bars.items()
    }
    equity = policy.starting_equity_usd
    peak = equity
    max_drawdown = Decimal(0)
    open_risk: list[OpenRisk] = []
    closed: list[SizedTrade] = []
    counts = {"ALLOW": 0, "REDUCE": 0, "REJECT": 0}
    max_open_positions = 0
    max_open_heat_usd = Decimal(0)
    max_open_heat_bps = Decimal(0)

    def close_due(until: datetime) -> None:
        nonlocal equity, peak, max_drawdown, open_risk
        due = sorted(
            (item for item in open_risk if item.exit_at <= until),
            key=lambda item: item.exit_at,
        )
        for item in due:
            equity += item.trade.net_pnl_usd
            closed.append(item.trade)
            if equity > peak:
                peak = equity
            dd = peak - equity
            if dd > max_drawdown:
                max_drawdown = dd
        if due:
            due_ids = {id(item) for item in due}
            open_risk = [item for item in open_risk if id(item) not in due_ids]

    for observation in selected:
        close_due(observation.signal_at)
        desired_loss = equity * Decimal(policy.per_trade_risk_bps) / Decimal(10_000)
        heat_limit = equity * Decimal(policy.portfolio_heat_bps) / Decimal(10_000)
        committed_loss = sum(
            (item.trade.bounded_loss_usd for item in open_risk), Decimal(0)
        )
        available_loss = heat_limit - committed_loss
        if available_loss <= 0:
            counts["REJECT"] += 1
            continue
        if available_loss < desired_loss:
            desired_loss = available_loss
            pre_status = "REDUCE"
        else:
            pre_status = "ALLOW"

        factor_entry = quote_to_usd_factor(
            observation.symbol,
            observation.signal_at,
            instrument_price=observation.entry,
            indices=indices,
        )
        per_unit_loss = observation.risk_price * factor_entry
        status, quantity, bounded_loss = broker_valid_fixed_risk_quantity(
            desired_loss_usd=desired_loss,
            per_unit_loss_usd=per_unit_loss,
            constraints=constraints[observation.symbol],
        )
        if status == "REJECT":
            counts["REJECT"] += 1
            continue
        if pre_status == "REDUCE":
            status = "REDUCE"

        factor_exit = quote_to_usd_factor(
            observation.symbol,
            observation.exited_at,
            instrument_price=observation.exit_price,
            indices=indices,
        )
        gross_pnl = _gross_quote_pnl(observation, quantity) * factor_exit
        price_cost = observation.entry * policy.price_cost_bps / Decimal(10_000)
        cost_usd = quantity * price_cost * factor_entry
        net_pnl = gross_pnl - cost_usd
        gross_r = gross_pnl / bounded_loss
        net_r = net_pnl / bounded_loss
        sized = SizedTrade(
            observation=observation,
            risk_outcome=status,
            quantity=quantity,
            bounded_loss_usd=bounded_loss,
            quote_to_usd_at_entry=factor_entry,
            gross_pnl_usd=gross_pnl,
            cost_usd=cost_usd,
            net_pnl_usd=net_pnl,
            gross_r=gross_r,
            net_r=net_r,
        )
        counts[status] += 1
        open_risk.append(OpenRisk(observation.exited_at, sized))
        max_open_positions = max(max_open_positions, len(open_risk))
        open_heat = sum(
            (item.trade.bounded_loss_usd for item in open_risk), Decimal(0)
        )
        max_open_heat_usd = max(max_open_heat_usd, open_heat)
        if equity > 0:
            max_open_heat_bps = max(
                max_open_heat_bps, open_heat / equity * Decimal(10_000)
            )

    close_due(datetime.max.replace(tzinfo=UTC))
    if len(closed) != counts["ALLOW"] + counts["REDUCE"]:
        raise RiskEconomicReplayError("closed-trade accounting mismatch")

    gross_total = sum((item.gross_pnl_usd for item in closed), Decimal(0))
    net_total = sum((item.net_pnl_usd for item in closed), Decimal(0))
    positive = sum(
        (item.net_pnl_usd for item in closed if item.net_pnl_usd > 0), Decimal(0)
    )
    negative = -sum(
        (item.net_pnl_usd for item in closed if item.net_pnl_usd < 0), Decimal(0)
    )
    net_pf = positive / negative if negative > 0 else None
    gross_r = sum((item.gross_r for item in closed), Decimal(0))
    net_r = sum((item.net_r for item in closed), Decimal(0))
    accepted = len(closed)

    by_window: dict[str, dict[str, object]] = {}
    for window in ("fresh-2022-2024", "baseline-2024-2026"):
        subset = [item for item in closed if item.observation.window == window]
        by_window[window] = _trade_metrics(subset)

    return {
        "candidate": candidate,
        "signal_count": len(selected),
        "risk_outcomes": counts,
        "accepted_count": accepted,
        "starting_equity_usd": policy.starting_equity_usd,
        "ending_equity_usd": equity,
        "net_return_pct": (
            equity / policy.starting_equity_usd - Decimal(1)
        ) * Decimal(100),
        "gross_pnl_usd": gross_total,
        "net_pnl_usd": net_total,
        "gross_r": gross_r,
        "net_r": net_r,
        "net_expectancy_r": net_r / Decimal(accepted) if accepted else None,
        "net_profit_factor": net_pf,
        "max_drawdown_usd": max_drawdown,
        "max_drawdown_pct_of_start": (
            max_drawdown / policy.starting_equity_usd * Decimal(100)
        ),
        "max_open_positions": max_open_positions,
        "max_open_heat_usd": max_open_heat_usd,
        "max_open_heat_bps_observed": max_open_heat_bps,
        "by_window": by_window,
    }


def _trade_metrics(trades: Sequence[SizedTrade]) -> dict[str, object]:
    net = sum((item.net_pnl_usd for item in trades), Decimal(0))
    gross_r = sum((item.gross_r for item in trades), Decimal(0))
    net_r = sum((item.net_r for item in trades), Decimal(0))
    pos = sum(
        (item.net_pnl_usd for item in trades if item.net_pnl_usd > 0), Decimal(0)
    )
    neg = -sum(
        (item.net_pnl_usd for item in trades if item.net_pnl_usd < 0), Decimal(0)
    )
    return {
        "trades": len(trades),
        "net_pnl_usd": net,
        "gross_r": gross_r,
        "net_r": net_r,
        "net_expectancy_r": net_r / Decimal(len(trades)) if trades else None,
        "net_profit_factor": pos / neg if neg > 0 else None,
    }


def _break_even_cost_bps(
    *,
    trades: Sequence[TradeObservation],
    constraints: Mapping[str, BrokerVolumeConstraints],
    conversion_bars: Mapping[str, Mapping[datetime, Decimal]],
    candidate: str,
) -> Decimal | None:
    zero = replay_account(
        trades=trades,
        constraints=constraints,
        conversion_bars=conversion_bars,
        candidate=candidate,
        policy=RiskReplayPolicy(price_cost_bps=Decimal(0)),
    )
    if Decimal(str(zero["net_pnl_usd"])) <= 0:
        return Decimal(0)
    low = Decimal(0)
    high = Decimal(10)
    high_result = replay_account(
        trades=trades,
        constraints=constraints,
        conversion_bars=conversion_bars,
        candidate=candidate,
        policy=RiskReplayPolicy(price_cost_bps=high),
    )
    if Decimal(str(high_result["net_pnl_usd"])) > 0:
        return None
    for _ in range(24):
        mid = (low + high) / Decimal(2)
        result = replay_account(
            trades=trades,
            constraints=constraints,
            conversion_bars=conversion_bars,
            candidate=candidate,
            policy=RiskReplayPolicy(price_cost_bps=mid),
        )
        if Decimal(str(result["net_pnl_usd"])) > 0:
            low = mid
        else:
            high = mid
    return (low + high) / Decimal(2)


def _jsonable(value: object) -> object:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    return value


def build_report(baseline_root: Path, fresh_root: Path) -> dict[str, object]:
    trades, constraints, bars = load_consumed_evidence(baseline_root, fresh_root)
    primary = RiskReplayPolicy()
    primary_results = {
        candidate: replay_account(
            trades=trades,
            constraints=constraints,
            conversion_bars=bars,
            candidate=candidate,
            policy=primary,
        )
        for candidate in ("broad", "candidate-a", "candidate-b")
    }
    stress: dict[str, dict[str, object]] = {}
    break_even: dict[str, dict[str, object]] = {}
    windows = {
        "combined": trades,
        "fresh-2022-2024": [
            item for item in trades if item.window == "fresh-2022-2024"
        ],
        "baseline-2024-2026": [
            item for item in trades if item.window == "baseline-2024-2026"
        ],
    }
    for candidate in ("candidate-a", "candidate-b"):
        stress[candidate] = {}
        for cost in COST_STRESS_GRID_BPS:
            policy = RiskReplayPolicy(price_cost_bps=cost)
            stress[candidate][format(cost, "f")] = {
                name: replay_account(
                    trades=window_trades,
                    constraints=constraints,
                    conversion_bars=bars,
                    candidate=candidate,
                    policy=policy,
                )
                for name, window_trades in windows.items()
            }
        break_even[candidate] = {
            name: _break_even_cost_bps(
                trades=window_trades,
                constraints=constraints,
                conversion_bars=bars,
                candidate=candidate,
            )
            for name, window_trades in windows.items()
        }
    return {
        "schema": "qore.vt08.r3.11.risk-economic-replay.v1",
        "research_only": True,
        "demo_eligible": False,
        "protected_holdout_2020_2022_accessed": False,
        "consumed_run_ids": [FRESH_RUN_ID, BASELINE_RUN_ID],
        "consumed_evidence_floor": CONSUMED_EVIDENCE_FLOOR,
        "trade_count": len(trades),
        "policy": {
            "starting_equity_usd": primary.starting_equity_usd,
            "per_trade_risk_bps": primary.per_trade_risk_bps,
            "portfolio_heat_bps": primary.portfolio_heat_bps,
            "cost_model": (
                "total completed-trade price-bps stress proxy; "
                "not realized cTrader costs"
            ),
            "cTrader_volume_step": CTRADER_VOLUME_STEP,
        },
        "primary_zero_cost": primary_results,
        "cost_stress_bps": stress,
        "break_even_price_cost_bps": break_even,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-root", type=Path, required=True)
    parser.add_argument("--fresh-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    report = build_report(args.baseline_root, args.fresh_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(_jsonable(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
