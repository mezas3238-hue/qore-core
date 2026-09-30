"""Portfolio-level session-flow viability for QORE Capitalizer.

Combines the nine market-specific consumed-development baseline ledgers chronologically and
tests the Owner-amended opportunity budget at the trader level, not per market:

- MAX2 reference;
- MAX3_ANY_VALID;
- MAX3_POSITIVE_REALIZED_CONTINUATION, where the third execution is eligible only after
  prior session PnL has actually been realized positive before the candidate arrives.

Simultaneous candidates are tested under two deterministic, non-outcome tie policies
(SYMBOL_ASC and SYMBOL_DESC) to expose ordering sensitivity. No QORE Risk allocation,
correlation allocator, costs, profit target, candidate freeze, holdout, or promotion is claimed.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import datetime, time, timedelta
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.trader_lab.capitalizer_contract import (
    CapitalizerSession,
    allowed_markets,
)
from qore.infrastructure.trader_lab.capitalizer_session_clock import capitalizer_session_at
from qore.infrastructure.trader_lab.capitalizer_session_flow_viability import (
    NEW_YORK,
    _session_end,
)

IDENTITY = "QORE_CAPITALIZER_PORTFOLIO_SESSION_FLOW_VIABILITY_V1"


@dataclass(frozen=True, slots=True)
class PortfolioFlowTrade:
    symbol: str
    entry_at: datetime
    exit_at: datetime
    realized_r: Decimal

    def __post_init__(self) -> None:
        if not self.symbol or self.symbol != self.symbol.upper():
            raise ValueError("symbol must be uppercase")
        for name, value in (("entry_at", self.entry_at), ("exit_at", self.exit_at)):
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(f"{name} must be timezone-aware")
        if self.exit_at < self.entry_at:
            raise ValueError("exit cannot precede entry")
        if not self.realized_r.is_finite():
            raise ValueError("realized_r must be finite")
        if self.exit_at > _session_end(self.entry_at):
            raise ValueError("portfolio scalp crossed session boundary")


@dataclass(frozen=True, slots=True)
class PortfolioFlowMetrics:
    trades: int
    total_r: str
    mean_r: str
    profit_factor: str | None
    max_drawdown_r: str
    max_losing_streak: int
    mean_monthly_trades: str


@dataclass(frozen=True, slots=True)
class PortfolioFlowVariant:
    name: str
    tie_policy: str
    metrics: PortfolioFlowMetrics


@dataclass(frozen=True, slots=True)
class PortfolioThirdExecution:
    name: str
    tie_policy: str
    trades: int
    total_r: str
    profit_factor: str | None
    max_drawdown_r: str
    prior_realized_positive: int
    prior_realized_nonpositive: int


@dataclass(frozen=True, slots=True)
class PortfolioSessionFlowReport:
    identity: str
    market_count: int
    complete_frozen_universe: bool
    baseline_opportunities: int
    sessions_observed: int
    sessions_with_at_least_three_candidates: int
    variants: tuple[PortfolioFlowVariant, ...]
    third_executions: tuple[PortfolioThirdExecution, ...]
    same_session_exit_verified: bool = True
    positive_pnl_is_not_stop_condition: bool = True
    max_executions_per_session: int = 3
    simultaneous_ordering_sensitivity_tested: bool = True
    qore_risk_allocator_applied: bool = False
    cross_market_exposure_allocator_applied: bool = False
    costs_applied: bool = False
    governed_profit_objective_not_modeled: bool = True
    development_only: bool = True
    candidate_frozen: bool = False
    fresh_holdout_claimed: bool = False
    rule_selected: bool = False
    promotion_allowed: bool = False


def _expected_symbols() -> frozenset[str]:
    result: set[str] = set()
    for session in CapitalizerSession:
        result.update(allowed_markets(session))
    return frozenset(result)


def _load_ledgers(root: Path) -> tuple[PortfolioFlowTrade, ...]:
    paths = sorted(root.rglob("capitalizer-*-session-flow-trades-v1.jsonl"))
    if not paths:
        raise ValueError("no session-flow ledgers found")
    trades: list[PortfolioFlowTrade] = []
    symbols: set[str] = set()
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                row = json.loads(line)
                trade = PortfolioFlowTrade(
                    symbol=str(row["symbol"]),
                    entry_at=datetime.fromisoformat(str(row["entry_at"])),
                    exit_at=datetime.fromisoformat(str(row["exit_at"])),
                    realized_r=Decimal(str(row["realized_gross_r"])),
                )
                symbols.add(trade.symbol)
                trades.append(trade)
    expected = _expected_symbols()
    if symbols != expected:
        raise ValueError(
            f"portfolio universe mismatch missing={sorted(expected - symbols)} "
            f"extra={sorted(symbols - expected)}"
        )
    return tuple(trades)


def _session_key(trade: PortfolioFlowTrade) -> str:
    session = capitalizer_session_at(trade.entry_at)
    if session is None:
        raise ValueError("portfolio candidate must belong to Capitalizer session")
    local = trade.entry_at.astimezone(NEW_YORK)
    day = local.date()
    if session is CapitalizerSession.ASIA and local.time() < time(2, 0):
        day -= timedelta(days=1)
    return f"{session.value}:{day.isoformat()}"


def _ordered(
    trades: Iterable[PortfolioFlowTrade],
    *,
    tie_policy: str,
) -> tuple[PortfolioFlowTrade, ...]:
    if tie_policy not in {"SYMBOL_ASC", "SYMBOL_DESC"}:
        raise ValueError("unsupported tie policy")
    grouped: dict[datetime, list[PortfolioFlowTrade]] = defaultdict(list)
    for trade in trades:
        grouped[trade.entry_at].append(trade)
    ordered: list[PortfolioFlowTrade] = []
    for entry_at in sorted(grouped):
        rows = sorted(
            grouped[entry_at],
            key=lambda item: item.symbol,
            reverse=tie_policy == "SYMBOL_DESC",
        )
        ordered.extend(rows)
    return tuple(ordered)


def _prior_realized(
    accepted: tuple[PortfolioFlowTrade, ...],
    candidate: PortfolioFlowTrade,
) -> Decimal:
    return sum(
        (
            trade.realized_r
            for trade in accepted
            if trade.exit_at <= candidate.entry_at
        ),
        Decimal("0"),
    )


def _select(
    trades: tuple[PortfolioFlowTrade, ...],
    *,
    mode: str,
    tie_policy: str,
) -> tuple[PortfolioFlowTrade, ...]:
    if mode not in {"MAX2", "MAX3_ANY_VALID", "MAX3_POSITIVE_REALIZED_CONTINUATION"}:
        raise ValueError("unsupported portfolio flow mode")
    per_session: dict[str, list[PortfolioFlowTrade]] = defaultdict(list)
    selected: list[PortfolioFlowTrade] = []
    for trade in _ordered(trades, tie_policy=tie_policy):
        accepted = per_session[_session_key(trade)]
        cap = 2 if mode == "MAX2" else 3
        if len(accepted) >= cap:
            continue
        if (
            mode == "MAX3_POSITIVE_REALIZED_CONTINUATION"
            and len(accepted) >= 2
            and _prior_realized(tuple(accepted), trade) <= 0
        ):
            continue
        accepted.append(trade)
        selected.append(trade)
    return tuple(selected)


def _metrics(trades: tuple[PortfolioFlowTrade, ...]) -> PortfolioFlowMetrics:
    if not trades:
        raise ValueError("portfolio metrics require trades")
    gross_profit = sum(
        (item.realized_r for item in trades if item.realized_r > 0),
        Decimal("0"),
    )
    gross_loss = sum(
        (-item.realized_r for item in trades if item.realized_r < 0),
        Decimal("0"),
    )
    total = sum((item.realized_r for item in trades), Decimal("0"))
    exits = sorted(trades, key=lambda item: (item.exit_at, item.entry_at, item.symbol))
    equity = Decimal("0")
    peak = Decimal("0")
    max_dd = Decimal("0")
    streak = 0
    max_streak = 0
    for trade in exits:
        equity += trade.realized_r
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
        if trade.realized_r < 0:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0

    entries = sorted(trades, key=lambda item: item.entry_at)
    first = entries[0].entry_at
    last = entries[-1].entry_at
    months = (last.year - first.year) * 12 + last.month - first.month + 1
    pf = None if gross_loss == 0 else str(gross_profit / gross_loss)
    return PortfolioFlowMetrics(
        trades=len(trades),
        total_r=str(total),
        mean_r=str(total / Decimal(len(trades))),
        profit_factor=pf,
        max_drawdown_r=str(max_dd),
        max_losing_streak=max_streak,
        mean_monthly_trades=str(Decimal(len(trades)) / Decimal(months)),
    )


def _third_execution(
    trades: tuple[PortfolioFlowTrade, ...],
    *,
    mode: str,
    tie_policy: str,
) -> PortfolioThirdExecution:
    selected = _select(trades, mode=mode, tie_policy=tie_policy)
    per_session: dict[str, list[PortfolioFlowTrade]] = defaultdict(list)
    thirds: list[PortfolioFlowTrade] = []
    positive = 0
    nonpositive = 0
    for trade in _ordered(selected, tie_policy=tie_policy):
        accepted = per_session[_session_key(trade)]
        accepted.append(trade)
        if len(accepted) == 3:
            prior = _prior_realized(tuple(accepted[:2]), trade)
            if prior > 0:
                positive += 1
            else:
                nonpositive += 1
            thirds.append(trade)
    metrics = _metrics(tuple(thirds))
    return PortfolioThirdExecution(
        name=f"{mode}_THIRD_EXECUTION",
        tie_policy=tie_policy,
        trades=metrics.trades,
        total_r=metrics.total_r,
        profit_factor=metrics.profit_factor,
        max_drawdown_r=metrics.max_drawdown_r,
        prior_realized_positive=positive,
        prior_realized_nonpositive=nonpositive,
    )


def build_portfolio_session_flow_report(root: Path) -> PortfolioSessionFlowReport:
    trades = _load_ledgers(root)
    session_counts: dict[str, int] = defaultdict(int)
    for trade in trades:
        session_counts[_session_key(trade)] += 1

    variants: list[PortfolioFlowVariant] = []
    thirds: list[PortfolioThirdExecution] = []
    for tie_policy in ("SYMBOL_ASC", "SYMBOL_DESC"):
        for mode in (
            "MAX2",
            "MAX3_ANY_VALID",
            "MAX3_POSITIVE_REALIZED_CONTINUATION",
        ):
            selected = _select(trades, mode=mode, tie_policy=tie_policy)
            variants.append(
                PortfolioFlowVariant(
                    name=mode,
                    tie_policy=tie_policy,
                    metrics=_metrics(selected),
                )
            )
        thirds.append(
            _third_execution(
                trades,
                mode="MAX3_ANY_VALID",
                tie_policy=tie_policy,
            )
        )
        thirds.append(
            _third_execution(
                trades,
                mode="MAX3_POSITIVE_REALIZED_CONTINUATION",
                tie_policy=tie_policy,
            )
        )

    return PortfolioSessionFlowReport(
        identity=IDENTITY,
        market_count=len(_expected_symbols()),
        complete_frozen_universe=True,
        baseline_opportunities=len(trades),
        sessions_observed=len(session_counts),
        sessions_with_at_least_three_candidates=sum(
            count >= 3 for count in session_counts.values()
        ),
        variants=tuple(variants),
        third_executions=tuple(thirds),
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Capitalizer nine-market portfolio session-flow viability"
    )
    parser.add_argument("input_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = build_portfolio_session_flow_report(args.input_root)
    args.output.mkdir(parents=True, exist_ok=True)
    path = args.output / "capitalizer-portfolio-session-flow-viability-v1.json"
    path.write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(asdict(report), sort_keys=True))


if __name__ == "__main__":
    main()
