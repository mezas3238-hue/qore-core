"""VT08 Index R15 — concurrent three-market portfolio validation.

Validates the frozen R14 candidate under the Owner's concurrent-market contract:

- NAS100, SP500 and US30 are independent signal engines.
- At most one position per symbol, but positions across different symbols may
  coexist and may be opened at the same timestamp.
- No valid cross-market signal is suppressed because another market is open.
- Risk allocation is computed from information available BEFORE the signal.
  Only trades already closed by that timestamp may update governor state.
- Signals sharing the same timestamp are admitted as one batch from the same
  pre-batch state.
- Portfolio drawdown is measured both on realized equity and with concurrent
  mark-to-market exposure. A conservative intrabar mark sums adverse M15
  excursions for all simultaneously open positions.

This is a validation of the already-frozen R14 contract. It does not retune it
and does not grant live or real-capital authority.
"""

from __future__ import annotations

import argparse
import bisect
import heapq
import json
from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import vt08_index_cibo_2y_density_round4 as r4
from qore.infrastructure.trader_lab import vt08_index_cibo_2y_management_round5 as r5
from qore.infrastructure.trader_lab import vt08_index_r6_5y_failure_forensics as fx
from qore.infrastructure.trader_lab import vt08_index_r6_five_year_validation as v5y
from qore.infrastructure.trader_lab import vt08_index_r8_priority_poi_rearm_reset as r8
from qore.infrastructure.trader_lab import vt08_index_r10_contextual_risk as r10
from qore.infrastructure.trader_lab import vt08_index_r13_rolling_drawdown_governor as r13
from qore.infrastructure.trader_lab import vt08_index_r14_candidate_freeze as freeze
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import Vt08IndexC2R1Bar

SCHEMA = "qore.trader_lab.vt08_index_r15_concurrent_portfolio_validation.v1"
IDENTITY = "VT08_INDEX_R15_CONCURRENT_PORTFOLIO_VALIDATION_001"
PRIMARY_STRESS = Decimal("0.05")
SECONDARY_STRESS = Decimal("0.10")
MAX_PORTFOLIO_DD_R = Decimal("6")
MIN_EFFECTIVE_WEIGHT = Decimal("0.005")


@dataclass(frozen=True, slots=True)
class AssignedTrade:
    trade_id: int
    opportunity: r4.ExpandedOpportunity
    outcome: r5.ManagedTrade
    context: r10.Context
    weight: Decimal

    @property
    def symbol(self) -> str:
        return self.opportunity.signal.symbol

    @property
    def signal_at(self) -> datetime:
        return self.opportunity.signal.signal_at.astimezone(UTC)

    @property
    def exited_at(self) -> datetime:
        return self.outcome.exited_at.astimezone(UTC)


def _build_five_year_stream(
    *,
    roots: dict[str, Path],
) -> tuple[
    tuple[tuple[r4.ExpandedOpportunity, r5.ManagedTrade], ...],
    dict[str, Sequence[Vt08IndexC2R1Bar]],
    dict[str, dict[datetime, Vt08IndexC2R1Bar]],
    dict[str, tuple[datetime, ...]],
    dict[str, Any],
]:
    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]] = {}
    indexed_by_symbol: dict[str, dict[datetime, Vt08IndexC2R1Bar]] = {}
    opened_by_symbol: dict[str, tuple[datetime, ...]] = {}
    opportunities_by_symbol: dict[str, tuple[r4.ExpandedOpportunity, ...]] = {}
    provenance: dict[str, Any] = {}

    for symbol in ("NAS100", "SP500", "US30"):
        bars, source = v5y._load_cibo_m15_5y(roots[symbol], symbol=symbol)
        bars_by_symbol[symbol] = bars
        indexed_by_symbol[symbol] = {
            bar.opened_at.astimezone(UTC): bar for bar in bars
        }
        opened_by_symbol[symbol] = tuple(
            bar.opened_at.astimezone(UTC) for bar in bars
        )
        opportunities_by_symbol[symbol] = r8._opportunities(
            symbol=symbol,
            bars=bars,
        )
        provenance[symbol] = source

    stream = r10._base_stream(
        opportunities_by_symbol=opportunities_by_symbol,
        bars_by_symbol=bars_by_symbol,
    )
    return (
        stream,
        bars_by_symbol,
        indexed_by_symbol,
        opened_by_symbol,
        provenance,
    )


def _rolling_dd(
    *,
    equity: Decimal,
    history: deque[Decimal],
) -> Decimal:
    return max(history) - equity


def _assign_concurrent_weights(
    stream: Sequence[tuple[r4.ExpandedOpportunity, r5.ManagedTrade]],
    *,
    contexts: Sequence[r10.Context],
) -> tuple[tuple[AssignedTrade, ...], dict[str, Any]]:
    """Assign R14 risk causally with cross-symbol concurrency preserved."""

    scheme = freeze.frozen_refined_scheme().as_r13()
    equity = Decimal()
    history: deque[Decimal] = deque(
        [Decimal()],
        maxlen=scheme.rolling_trades + 1,
    )
    loss_streak = 0

    # Completed trades are processed by exit time, never by signal order.
    exit_heap: list[tuple[datetime, int, Decimal]] = []
    assigned: list[AssignedTrade] = []
    active: dict[int, AssignedTrade] = {}

    overlap_entries = 0
    max_concurrent = 0
    max_committed_risk = Decimal()
    same_time_batches = 0
    same_time_batch_trades = 0
    warn_trades = 0
    hard_trades = 0
    loss_defense_trades = 0

    items = list(zip(stream, contexts, strict=True))
    cursor = 0
    next_trade_id = 0

    def settle(until: datetime) -> None:
        nonlocal equity, loss_streak
        while exit_heap and exit_heap[0][0] <= until:
            _exit_at, trade_id, primary_value = heapq.heappop(exit_heap)
            active.pop(trade_id, None)
            equity += primary_value
            history.append(equity)
            if primary_value < 0:
                loss_streak += 1
            else:
                loss_streak = 0

    while cursor < len(items):
        batch_time = items[cursor][0][0].signal.signal_at.astimezone(UTC)
        settle(batch_time)

        end = cursor + 1
        while (
            end < len(items)
            and items[end][0][0].signal.signal_at.astimezone(UTC)
            == batch_time
        ):
            end += 1
        batch = items[cursor:end]
        if len(batch) > 1:
            same_time_batches += 1
            same_time_batch_trades += len(batch)

        dd_before = _rolling_dd(equity=equity, history=history)
        batch_assignments: list[AssignedTrade] = []

        for (opportunity, outcome), context in batch:
            base_weight = r13._base_weight(context, scheme)
            weight = base_weight
            if dd_before >= scheme.hard_dd_r:
                weight *= scheme.hard_multiplier
                hard_trades += 1
            elif dd_before >= scheme.warn_dd_r:
                weight *= scheme.warn_multiplier
                warn_trades += 1

            if (
                scheme.loss_trigger is not None
                and scheme.loss_multiplier is not None
                and loss_streak >= scheme.loss_trigger
            ):
                weight *= scheme.loss_multiplier
                loss_defense_trades += 1

            if weight < MIN_EFFECTIVE_WEIGHT:
                raise ValueError(
                    f"R15 pseudo-skip detected: effective weight {weight}"
                )

            if active:
                overlap_entries += 1

            assigned_trade = AssignedTrade(
                trade_id=next_trade_id,
                opportunity=opportunity,
                outcome=outcome,
                context=context,
                weight=weight,
            )
            next_trade_id += 1
            batch_assignments.append(assigned_trade)

        # Admit the whole batch. No trade in the batch can influence a sibling.
        for item in batch_assignments:
            assigned.append(item)
            active[item.trade_id] = item
            primary_value = (
                item.outcome.r_multiple - PRIMARY_STRESS
            ) * item.weight
            heapq.heappush(
                exit_heap,
                (item.exited_at, item.trade_id, primary_value),
            )

        max_concurrent = max(max_concurrent, len(active))
        max_committed_risk = max(
            max_committed_risk,
            sum((trade.weight for trade in active.values()), Decimal()),
        )
        cursor = end

    settle(datetime.max.replace(tzinfo=UTC))

    if len(assigned) != len(stream):
        raise ValueError("concurrent assignment changed the trade count")

    return tuple(assigned), {
        "input_trade_count": len(stream),
        "assigned_trade_count": len(assigned),
        "suppressed_trade_count": 0,
        "overlap_entry_count": overlap_entries,
        "max_concurrent_open_positions": max_concurrent,
        "max_committed_structural_risk_r": str(max_committed_risk),
        "same_timestamp_signal_batches": same_time_batches,
        "same_timestamp_signal_trades": same_time_batch_trades,
        "warn_allocations": warn_trades,
        "hard_allocations": hard_trades,
        "loss_defense_allocations": loss_defense_trades,
        "minimum_effective_weight": str(
            min(item.weight for item in assigned)
        ),
        "maximum_effective_weight": str(
            max(item.weight for item in assigned)
        ),
        "mean_effective_weight": str(
            sum((item.weight for item in assigned), Decimal())
            / len(assigned)
        ),
    }


def _realized_values(
    assigned: Sequence[AssignedTrade],
    *,
    stress: Decimal,
) -> tuple[Decimal, ...]:
    by_exit = sorted(
        assigned,
        key=lambda item: (item.exited_at, item.symbol, item.trade_id),
    )
    return tuple(
        (item.outcome.r_multiple - stress) * item.weight
        for item in by_exit
    )


def _signal_close_r(
    item: AssignedTrade,
    bar: Vt08IndexC2R1Bar,
) -> Decimal:
    signal = item.opportunity.signal
    risk = abs(signal.entry - signal.stop)
    if signal.side is DemoTradingSetupSide.LONG:
        return (bar.close - signal.entry) / risk
    return (signal.entry - bar.close) / risk


def _signal_adverse_r(
    item: AssignedTrade,
    bar: Vt08IndexC2R1Bar,
) -> Decimal:
    signal = item.opportunity.signal
    risk = abs(signal.entry - signal.stop)
    if signal.side is DemoTradingSetupSide.LONG:
        return (bar.low - signal.entry) / risk
    return (signal.entry - bar.high) / risk


def _portfolio_mark_to_market(
    assigned: Sequence[AssignedTrade],
    *,
    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]],
    opened_by_symbol: dict[str, tuple[datetime, ...]],
    stress: Decimal,
    adverse: bool,
) -> dict[str, Any]:
    """Conservative portfolio DD with all open markets marked concurrently."""

    events: dict[datetime, list[tuple[str, int, Decimal]]] = {}

    for item in assigned:
        # Charge the full stress at entry for conservative capital accounting.
        events.setdefault(item.signal_at, []).append(
            ("entry", item.trade_id, -stress * item.weight)
        )

        bars = bars_by_symbol[item.symbol]
        opened = opened_by_symbol[item.symbol]
        start = bisect.bisect_left(opened, item.signal_at)
        end = bisect.bisect_left(opened, item.exited_at)
        for bar in bars[start:end]:
            if bar.closed_at.astimezone(UTC) >= item.exited_at:
                break
            mark_r = (
                _signal_adverse_r(item, bar)
                if adverse
                else _signal_close_r(item, bar)
            )
            events.setdefault(bar.closed_at.astimezone(UTC), []).append(
                (
                    "mark",
                    item.trade_id,
                    (mark_r - stress) * item.weight,
                )
            )

        events.setdefault(item.exited_at, []).append(
            (
                "exit",
                item.trade_id,
                (item.outcome.r_multiple - stress) * item.weight,
            )
        )

    realized = Decimal()
    open_marks: dict[int, Decimal] = {}
    peak = Decimal()
    max_dd = Decimal()
    max_open = 0

    for timestamp in sorted(events):
        bucket = events[timestamp]
        # Exit first, then mark, then entries at an identical timestamp.
        order = {"exit": 0, "mark": 1, "entry": 2}
        for kind, trade_id, value in sorted(
            bucket,
            key=lambda row: (order[row[0]], row[1]),
        ):
            if kind == "exit":
                open_marks.pop(trade_id, None)
                realized += value
            elif kind == "mark":
                if trade_id in open_marks:
                    open_marks[trade_id] = value
            else:
                open_marks[trade_id] = value

        equity = realized + sum(open_marks.values(), Decimal())
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
        max_open = max(max_open, len(open_marks))

    return {
        "max_drawdown_r": str(max_dd),
        "terminal_realized_r": str(realized),
        "max_concurrent_open_positions": max_open,
        "marking": (
            "M15_ADVERSE_EXTREME_CONSERVATIVE"
            if adverse
            else "M15_CLOSE"
        ),
    }


def _market_counts(
    assigned: Sequence[AssignedTrade],
) -> dict[str, int]:
    return {
        symbol: sum(item.symbol == symbol for item in assigned)
        for symbol in ("NAS100", "SP500", "US30")
    }


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, Any]:
    roots = {
        "NAS100": nas100_root,
        "SP500": sp500_root,
        "US30": us30_root,
    }
    (
        stream,
        bars_by_symbol,
        indexed_by_symbol,
        opened_by_symbol,
        provenance,
    ) = _build_five_year_stream(roots=roots)

    contexts = tuple(
        r10._context(
            opportunity,
            indexed=indexed_by_symbol[opportunity.signal.symbol],
        )
        for opportunity, _outcome in stream
    )
    assigned, concurrency = _assign_concurrent_weights(
        stream,
        contexts=contexts,
    )

    primary_values = _realized_values(assigned, stress=PRIMARY_STRESS)
    secondary_values = _realized_values(assigned, stress=SECONDARY_STRESS)
    primary = fx._metrics(primary_values)
    secondary = fx._metrics(secondary_values)

    primary_close_mtm = _portfolio_mark_to_market(
        assigned,
        bars_by_symbol=bars_by_symbol,
        opened_by_symbol=opened_by_symbol,
        stress=PRIMARY_STRESS,
        adverse=False,
    )
    primary_adverse_mtm = _portfolio_mark_to_market(
        assigned,
        bars_by_symbol=bars_by_symbol,
        opened_by_symbol=opened_by_symbol,
        stress=PRIMARY_STRESS,
        adverse=True,
    )
    secondary_adverse_mtm = _portfolio_mark_to_market(
        assigned,
        bars_by_symbol=bars_by_symbol,
        opened_by_symbol=opened_by_symbol,
        stress=SECONDARY_STRESS,
        adverse=True,
    )

    sample = len(assigned)
    concurrency_pass = (
        sample == freeze.FIVE_YEAR_SAMPLE
        and int(concurrency["suppressed_trade_count"]) == 0
        and int(concurrency["max_concurrent_open_positions"]) >= 2
    )
    dd_pass = (
        Decimal(primary_adverse_mtm["max_drawdown_r"])
        <= MAX_PORTFOLIO_DD_R
    )

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "candidate": {
            "candidate_id": freeze.CANDIDATE_ID,
            "rule_fingerprint": freeze.RULE_FINGERPRINT,
            "frozen_scheme_id": freeze.SCHEME_ID,
            "rules_changed": False,
        },
        "window": {
            "start_date": v5y.START_DATE.isoformat(),
            "end_date_exclusive": v5y.END_DATE_EXCLUSIVE.isoformat(),
            "status": "CONSUMED_CONCURRENT_VALIDATION",
            "fresh_certification_holdout": False,
        },
        "sample": sample,
        "trade_count_by_market": _market_counts(assigned),
        "primary_realized": primary,
        "secondary_realized": secondary,
        "primary_close_mark_to_market": primary_close_mtm,
        "primary_conservative_mark_to_market": primary_adverse_mtm,
        "secondary_conservative_mark_to_market": secondary_adverse_mtm,
        "concurrency": concurrency,
        "decision": {
            "all_three_markets_independent": True,
            "cross_market_concurrency_allowed": True,
            "one_active_position_per_symbol_only": True,
            "global_single_position_rule": False,
            "signal_suppression_allowed": False,
            "concurrency_contract_pass": concurrency_pass,
            "portfolio_dd_limit_r": str(MAX_PORTFOLIO_DD_R),
            "portfolio_dd_pass": dd_pass,
            "contract_pass": concurrency_pass and dd_pass,
        },
        "provenance": provenance,
        "governance": {
            "validation_only": True,
            "no_retuning": True,
            "frozen_candidate_replayed": True,
            "zero_risk_allowed": False,
            "future_outcome_used_for_new_signal_risk": False,
            "same_timestamp_batch_uses_same_pre_batch_state": True,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nas100-root", type=Path, required=True)
    parser.add_argument("--sp500-root", type=Path, required=True)
    parser.add_argument("--us30-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    report = build_report(
        nas100_root=args.nas100_root,
        sp500_root=args.sp500_root,
        us30_root=args.us30_root,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "identity": IDENTITY,
                "sample": report["sample"],
                "primary_realized": report["primary_realized"],
                "primary_conservative_mark_to_market": (
                    report["primary_conservative_mark_to_market"]
                ),
                "concurrency": report["concurrency"],
                "decision": report["decision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
