"""VT08 Index R21 — concurrent quality allocation + portfolio risk budget.

Builds on the corrected R15 concurrent architecture.

Hard architectural contract:
- NAS100, SP500 and US30 generate independently.
- One active trade per symbol only; different symbols may overlap.
- Every valid signal is admitted, including simultaneous batches.
- Portfolio capital is allocated pro-rata when concurrent requested structural
  risk exceeds the configured budget. Signals are never ranked or suppressed.
- Formation-quality weighting is pre-entry only.
- Rolling governor state uses only trades already closed before a new signal.
- The same assigned weights are used for primary and secondary stress replay.

The five-year period is consumed development evidence.
"""

from __future__ import annotations

import argparse
import heapq
import itertools
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
from qore.infrastructure.trader_lab import vt08_index_r10_contextual_risk as r10
from qore.infrastructure.trader_lab import vt08_index_r13_rolling_drawdown_governor as r13
from qore.infrastructure.trader_lab import vt08_index_r15_concurrent_portfolio_validation as r15
from qore.infrastructure.trader_lab import vt08_index_r20_static_quality_portfolio as r20

SCHEMA = "qore.trader_lab.vt08_index_r21_concurrent_quality_budget.v1"
IDENTITY = "VT08_INDEX_R21_CONCURRENT_QUALITY_BUDGET_001"
PRIMARY_STRESS = Decimal("0.05")
SECONDARY_STRESS = Decimal("0.10")
MIN_EFFECTIVE_WEIGHT = Decimal("0.005")
PRIMARY_PF_GOAL = Decimal("1.50")
PRIMARY_DD_GOAL = Decimal("6")
SECONDARY_PF_GOAL = Decimal("1.30")
SECONDARY_DD_GOAL = Decimal("8")
FIVE_YEAR_MIN_TRADES = 1500
FIVE_YEAR_MAX_TRADES = 1600


@dataclass(frozen=True, slots=True)
class ConcurrentQualityScheme:
    quality: r20.QualityScheme
    rolling_trades: int
    warn_dd_r: Decimal
    warn_multiplier: Decimal
    hard_dd_r: Decimal
    hard_multiplier: Decimal
    loss_multiplier: Decimal
    portfolio_risk_budget_r: Decimal

    @property
    def scheme_id(self) -> str:
        return (
            "R21-"
            f"{self.quality.scheme_id}-"
            f"W{self.rolling_trades}-"
            f"D{self.warn_dd_r}x{self.warn_multiplier}-"
            f"H{self.hard_dd_r}x{self.hard_multiplier}-"
            f"L2x{self.loss_multiplier}-"
            f"CAP{self.portfolio_risk_budget_r}"
        )

    def payload(self) -> dict[str, Any]:
        return {
            "scheme_id": self.scheme_id,
            "quality": self.quality.payload(),
            "rolling_trades": self.rolling_trades,
            "warn_dd_r": str(self.warn_dd_r),
            "warn_multiplier": str(self.warn_multiplier),
            "hard_dd_r": str(self.hard_dd_r),
            "hard_multiplier": str(self.hard_multiplier),
            "loss_trigger": 2,
            "loss_multiplier": str(self.loss_multiplier),
            "portfolio_risk_budget_r": str(self.portfolio_risk_budget_r),
            "minimum_effective_weight": str(MIN_EFFECTIVE_WEIGHT),
        }


def _quality_schemes() -> tuple[r20.QualityScheme, ...]:
    return (
        r20.QualityScheme(Decimal("0.01"), Decimal("0.50"), Decimal("0.25")),
        r20.QualityScheme(Decimal("0.025"), Decimal("0.50"), Decimal("0.25")),
        r20.QualityScheme(Decimal("0.05"), Decimal("0.50"), Decimal("0.25")),
        r20.QualityScheme(Decimal("0.01"), Decimal("0.75"), Decimal("0.25")),
        r20.QualityScheme(Decimal("0.01"), Decimal("0.50"), Decimal("0.50")),
        r20.QualityScheme(Decimal("0.01"), Decimal("0.75"), Decimal("0.50")),
    )


def _schemes() -> tuple[ConcurrentQualityScheme, ...]:
    rows: list[ConcurrentQualityScheme] = []
    for (
        quality,
        warn_dd,
        warn_mult,
        hard_dd,
        loss_mult,
        cap,
    ) in itertools.product(
        _quality_schemes(),
        (Decimal("1.25"), Decimal("1.50"), Decimal("1.75")),
        (Decimal("0.15"), Decimal("0.25")),
        (Decimal("2.25"), Decimal("2.50"), Decimal("2.75")),
        (Decimal("0.20"), Decimal("0.25")),
        (Decimal("1.50"), Decimal("2.00"), Decimal("2.50"), Decimal("3.00")),
    ):
        if hard_dd <= warn_dd:
            continue
        rows.append(
            ConcurrentQualityScheme(
                quality=quality,
                rolling_trades=60,
                warn_dd_r=warn_dd,
                warn_multiplier=warn_mult,
                hard_dd_r=hard_dd,
                hard_multiplier=Decimal("0.10"),
                loss_multiplier=loss_mult,
                portfolio_risk_budget_r=cap,
            )
        )
    return tuple(rows)


def _rolling_dd(
    equity: Decimal,
    history: deque[Decimal],
) -> Decimal:
    return max(history) - equity


def _allocate_batch(
    requested: Sequence[Decimal],
    *,
    active_risk: Decimal,
    budget: Decimal,
) -> tuple[tuple[Decimal, ...], bool]:
    """Allocate every signal; scale the whole batch pro-rata when necessary."""

    requested_total = sum(requested, Decimal())
    remaining = max(Decimal(), budget - active_risk)
    scaled = requested_total > remaining

    if not scaled:
        return tuple(max(MIN_EFFECTIVE_WEIGHT, value) for value in requested), False

    if remaining <= 0:
        return tuple(MIN_EFFECTIVE_WEIGHT for _ in requested), True

    factor = remaining / requested_total
    assigned = tuple(
        max(MIN_EFFECTIVE_WEIGHT, value * factor)
        for value in requested
    )
    return assigned, True


def _assign(
    stream: Sequence[tuple[r4.ExpandedOpportunity, r5.ManagedTrade]],
    *,
    scheme: ConcurrentQualityScheme,
) -> tuple[tuple[r15.AssignedTrade, ...], dict[str, Any]]:
    equity = Decimal()
    history: deque[Decimal] = deque(
        [Decimal()],
        maxlen=scheme.rolling_trades + 1,
    )
    loss_streak = 0

    exit_heap: list[tuple[datetime, int, Decimal]] = []
    active: dict[int, r15.AssignedTrade] = {}
    assigned: list[r15.AssignedTrade] = []

    next_trade_id = 0
    cursor = 0
    overlap_entries = 0
    same_time_batches = 0
    same_time_batch_trades = 0
    budget_scaled_batches = 0
    budget_floor_overage_batches = 0
    max_concurrent = 0
    max_committed = Decimal()
    warn_allocations = 0
    hard_allocations = 0
    loss_allocations = 0

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

    while cursor < len(stream):
        batch_time = stream[cursor][0].signal.signal_at.astimezone(UTC)
        settle(batch_time)

        end = cursor + 1
        while (
            end < len(stream)
            and stream[end][0].signal.signal_at.astimezone(UTC)
            == batch_time
        ):
            end += 1
        batch = stream[cursor:end]
        if len(batch) > 1:
            same_time_batches += 1
            same_time_batch_trades += len(batch)

        dd_before = _rolling_dd(equity, history)
        requested: list[Decimal] = []
        allocation_tags: list[tuple[bool, bool, bool]] = []

        for opportunity, _outcome in batch:
            weight = r20._weight(opportunity, scheme.quality)
            warn = False
            hard = False
            loss = False

            if dd_before >= scheme.hard_dd_r:
                weight *= scheme.hard_multiplier
                hard = True
            elif dd_before >= scheme.warn_dd_r:
                weight *= scheme.warn_multiplier
                warn = True

            if loss_streak >= 2:
                weight *= scheme.loss_multiplier
                loss = True

            requested.append(max(MIN_EFFECTIVE_WEIGHT, weight))
            allocation_tags.append((warn, hard, loss))

        active_risk = sum((item.weight for item in active.values()), Decimal())
        batch_weights, scaled = _allocate_batch(
            requested,
            active_risk=active_risk,
            budget=scheme.portfolio_risk_budget_r,
        )
        if scaled:
            budget_scaled_batches += 1

        post_batch_risk = active_risk + sum(batch_weights, Decimal())
        if post_batch_risk > scheme.portfolio_risk_budget_r:
            # Only the non-zero floor is allowed to cause a tiny overage.
            budget_floor_overage_batches += 1

        for ((opportunity, outcome), weight, tags) in zip(
            batch,
            batch_weights,
            allocation_tags,
            strict=True,
        ):
            warn, hard, loss = tags
            warn_allocations += int(warn)
            hard_allocations += int(hard)
            loss_allocations += int(loss)

            if active:
                overlap_entries += 1

            # AssignedTrade keeps a context field for shared portfolio tooling.
            # R21 sizing itself uses only r20 formation-quality features.
            context = r10.Context(
                previous_source_day_body_opposed=False,
                rearm=int(opportunity.rearm_index) > 0,
                c2_expansion=False,
                short=False,
            )

            item = r15.AssignedTrade(
                trade_id=next_trade_id,
                opportunity=opportunity,
                outcome=outcome,
                context=context,
                weight=weight,
            )
            next_trade_id += 1
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
        max_committed = max(
            max_committed,
            sum((item.weight for item in active.values()), Decimal()),
        )
        cursor = end

    settle(datetime.max.replace(tzinfo=UTC))

    return tuple(assigned), {
        "assigned_trade_count": len(assigned),
        "suppressed_trade_count": 0,
        "overlap_entry_count": overlap_entries,
        "same_timestamp_signal_batches": same_time_batches,
        "same_timestamp_signal_trades": same_time_batch_trades,
        "budget_scaled_batches": budget_scaled_batches,
        "budget_floor_overage_batches": budget_floor_overage_batches,
        "max_concurrent_open_positions": max_concurrent,
        "max_committed_structural_risk_r": str(max_committed),
        "minimum_effective_weight": str(min(item.weight for item in assigned)),
        "maximum_effective_weight": str(max(item.weight for item in assigned)),
        "mean_effective_weight": str(
            sum((item.weight for item in assigned), Decimal()) / len(assigned)
        ),
        "warn_allocations": warn_allocations,
        "hard_allocations": hard_allocations,
        "loss_defense_allocations": loss_allocations,
    }


def _search_row(
    stream: Sequence[tuple[r4.ExpandedOpportunity, r5.ManagedTrade]],
    *,
    scheme: ConcurrentQualityScheme,
) -> tuple[dict[str, Any], tuple[r15.AssignedTrade, ...]]:
    assigned, diagnostics = _assign(stream, scheme=scheme)
    primary = fx._metrics(
        r15._realized_values(assigned, stress=PRIMARY_STRESS)
    )
    secondary = fx._metrics(
        r15._realized_values(assigned, stress=SECONDARY_STRESS)
    )
    sample = len(assigned)
    realized_gate = (
        FIVE_YEAR_MIN_TRADES <= sample <= FIVE_YEAR_MAX_TRADES
        and Decimal(str(primary["profit_factor"] or "0")) >= PRIMARY_PF_GOAL
        and Decimal(str(primary["max_drawdown_r"])) <= PRIMARY_DD_GOAL
        and Decimal(str(secondary["profit_factor"] or "0")) >= SECONDARY_PF_GOAL
        and Decimal(str(secondary["max_drawdown_r"])) <= SECONDARY_DD_GOAL
        and int(diagnostics["suppressed_trade_count"]) == 0
    )
    return (
        {
            "scheme": scheme.payload(),
            "sample": sample,
            "primary": primary,
            "secondary": secondary,
            "diagnostics": diagnostics,
            "realized_gate_pass": realized_gate,
        },
        assigned,
    )


def _search_rank(row: dict[str, Any]) -> tuple[int, Decimal, Decimal, Decimal]:
    p = row["primary"]
    return (
        int(bool(row["realized_gate_pass"])),
        Decimal(str(p["profit_factor"] or "0")),
        -Decimal(str(p["max_drawdown_r"])),
        Decimal(str(p["total_r"])),
    )


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
        _indexed_by_symbol,
        opened_by_symbol,
        provenance,
    ) = r15._build_five_year_stream(roots=roots)

    search: list[
        tuple[dict[str, Any], tuple[r15.AssignedTrade, ...]]
    ] = []
    for scheme in _schemes():
        search.append(_search_row(stream, scheme=scheme))

    search.sort(key=lambda item: _search_rank(item[0]), reverse=True)

    # Full concurrent MTM is intentionally limited to the strongest realized
    # candidates so the research surface remains computationally bounded.
    finalists: list[dict[str, Any]] = []
    for row, assigned in search[:24]:
        primary_mtm = r15._portfolio_mark_to_market(
            assigned,
            bars_by_symbol=bars_by_symbol,
            opened_by_symbol=opened_by_symbol,
            stress=PRIMARY_STRESS,
            adverse=True,
        )
        secondary_mtm = r15._portfolio_mark_to_market(
            assigned,
            bars_by_symbol=bars_by_symbol,
            opened_by_symbol=opened_by_symbol,
            stress=SECONDARY_STRESS,
            adverse=True,
        )
        final = dict(row)
        final["primary_conservative_mark_to_market"] = primary_mtm
        final["secondary_conservative_mark_to_market"] = secondary_mtm
        final["goal_pass"] = (
            bool(row["realized_gate_pass"])
            and Decimal(primary_mtm["max_drawdown_r"]) <= PRIMARY_DD_GOAL
            and Decimal(secondary_mtm["max_drawdown_r"]) <= SECONDARY_DD_GOAL
        )
        finalists.append(final)

    finalists.sort(
        key=lambda row: (
            int(bool(row["goal_pass"])),
            Decimal(str(row["primary"]["profit_factor"] or "0")),
            -Decimal(
                row["primary_conservative_mark_to_market"]["max_drawdown_r"]
            ),
            Decimal(str(row["primary"]["total_r"])),
        ),
        reverse=True,
    )
    goals = [row for row in finalists if bool(row["goal_pass"])]

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "contract": {
            "five_year_density": [
                FIVE_YEAR_MIN_TRADES,
                FIVE_YEAR_MAX_TRADES,
            ],
            "primary_pf_minimum": str(PRIMARY_PF_GOAL),
            "primary_portfolio_dd_max_r": str(PRIMARY_DD_GOAL),
            "secondary_pf_minimum": str(SECONDARY_PF_GOAL),
            "secondary_portfolio_dd_max_r": str(SECONDARY_DD_GOAL),
            "cross_market_concurrency_required": True,
            "signal_suppression_allowed": False,
            "global_single_position_rule": False,
        },
        "scheme_count": len(search),
        "full_mtm_finalist_count": len(finalists),
        "goal_candidate_count": len(goals),
        "best": finalists[0],
        "top_10": finalists[:10],
        "goal_candidates": goals[:10],
        "provenance": provenance,
        "governance": {
            "development_only": True,
            "all_trades_preserved": True,
            "zero_risk_allowed": False,
            "same_timestamp_batch_allocation": True,
            "pro_rata_portfolio_budget": True,
            "future_outcome_used_for_new_signal_risk": False,
            "pre_entry_quality_only": True,
            "five_year_window_consumed": True,
            "fresh_holdout_claim": False,
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
                "scheme_count": report["scheme_count"],
                "goal_candidate_count": report["goal_candidate_count"],
                "best": report["best"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
