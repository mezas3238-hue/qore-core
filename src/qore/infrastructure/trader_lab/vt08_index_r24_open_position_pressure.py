"""VT08 Index R24 — causal open-position pressure governor.

R24 is a bounded refinement of the R23 concurrent portfolio candidate. It keeps
the exact 1,574-signal opportunity architecture, target/stop mechanics and the
permanent three-market concurrency contract.

The single research question is whether *observable open-position pressure*
can close the remaining conservative mark-to-market drawdown gap without
suppressing valid signals or using future outcomes.

Before each new signal batch, R24 may reduce only the risk of NEW signals using:
- adverse M15 marks from positions already open, using bars closed by that time;
- same-side cross-index exposure already open at that time.

Signals sharing an identical timestamp use the same pre-batch state. Existing
positions are never resized, stops are never widened, every valid signal keeps
strictly positive risk, and no post-entry outcome is consulted before the next
authorization decision.
"""

from __future__ import annotations

import argparse
import bisect
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
from qore.infrastructure.trader_lab import vt08_index_concurrent_market_contract as contract
from qore.infrastructure.trader_lab import vt08_index_r6_5y_failure_forensics as fx
from qore.infrastructure.trader_lab import vt08_index_r10_contextual_risk as r10
from qore.infrastructure.trader_lab import vt08_index_r15_concurrent_portfolio_validation as r15
from qore.infrastructure.trader_lab import vt08_index_r22_concurrent_stable_formation as r22

SCHEMA = "qore.trader_lab.vt08_index_r24_open_position_pressure.v1"
IDENTITY = "VT08_INDEX_R24_OPEN_POSITION_PRESSURE_001"

PRIMARY_STRESS = Decimal("0.05")
SECONDARY_STRESS = Decimal("0.10")
PF_PRIMARY_MIN = Decimal("1.50")
PF_SECONDARY_MIN = Decimal("1.30")
PORTFOLIO_DD_MAX = Decimal("6")
MIN_EFFECTIVE_WEIGHT = Decimal("0.005")

# R23 winner is the fixed starting point. R24 does not reopen R8 opportunity,
# target, stop, formation-feature, or realized-governor optimization.
BASE_QUALITY = r22.QualityProfile(
    base_weight=Decimal("0.005"),
    tier_a_weight=Decimal("1.50"),
    tier_b_weight=Decimal("0.75"),
    tier_c_weight=Decimal("0.10"),
)
BASE_RISK = r22.RiskProfile(
    rolling_trades=60,
    warn_dd_r=Decimal("1.25"),
    warn_multiplier=Decimal("0.05"),
    hard_dd_r=Decimal("1.50"),
    hard_multiplier=Decimal("0.025"),
    loss_multiplier=Decimal("0.05"),
    portfolio_risk_budget_r=Decimal("0.75"),
)


@dataclass(frozen=True, slots=True)
class OpenPressureProfile:
    live_warn_loss_r: Decimal
    live_warn_multiplier: Decimal
    live_hard_loss_r: Decimal
    live_hard_multiplier: Decimal
    same_side_multiplier: Decimal

    @property
    def profile_id(self) -> str:
        return (
            "OP-"
            f"W{self.live_warn_loss_r}x{self.live_warn_multiplier}-"
            f"H{self.live_hard_loss_r}x{self.live_hard_multiplier}-"
            f"SAME{self.same_side_multiplier}"
        )

    def payload(self) -> dict[str, str]:
        return {
            "profile_id": self.profile_id,
            "live_warn_loss_r": str(self.live_warn_loss_r),
            "live_warn_multiplier": str(self.live_warn_multiplier),
            "live_hard_loss_r": str(self.live_hard_loss_r),
            "live_hard_multiplier": str(self.live_hard_multiplier),
            "same_side_multiplier": str(self.same_side_multiplier),
        }


def _profiles() -> tuple[OpenPressureProfile, ...]:
    rows: list[OpenPressureProfile] = []
    for warn, warn_mult, hard, hard_mult, same_side in itertools.product(
        (Decimal("0.05"), Decimal("0.10"), Decimal("0.20")),
        (Decimal("0.25"), Decimal("0.50")),
        (Decimal("0.15"), Decimal("0.25"), Decimal("0.40")),
        (Decimal("0.05"), Decimal("0.10")),
        (
            Decimal("0.25"),
            Decimal("0.50"),
            Decimal("0.75"),
            Decimal("1.00"),
        ),
    ):
        if hard <= warn:
            continue
        rows.append(
            OpenPressureProfile(
                live_warn_loss_r=warn,
                live_warn_multiplier=warn_mult,
                live_hard_loss_r=hard,
                live_hard_multiplier=hard_mult,
                same_side_multiplier=same_side,
            )
        )
    return tuple(rows)


def _pressure_multiplier(
    *,
    open_adverse_loss_r: Decimal,
    same_side_open_count: int,
    profile: OpenPressureProfile,
) -> Decimal:
    multiplier = Decimal("1")
    if open_adverse_loss_r >= profile.live_hard_loss_r:
        multiplier *= profile.live_hard_multiplier
    elif open_adverse_loss_r >= profile.live_warn_loss_r:
        multiplier *= profile.live_warn_multiplier
    if same_side_open_count > 0:
        multiplier *= profile.same_side_multiplier
    if multiplier <= 0:
        raise ValueError("R24 open-pressure multiplier must remain positive")
    return multiplier


def _current_adverse_mark(
    item: r15.AssignedTrade,
    *,
    as_of: datetime,
    bars_by_symbol: dict[str, Sequence[Any]],
    opened_by_symbol: dict[str, tuple[datetime, ...]],
) -> Decimal:
    """Mark an already-open position using only M15 evidence closed by as_of."""

    entry_mark = -PRIMARY_STRESS * item.weight
    opened = opened_by_symbol[item.symbol]
    bars = bars_by_symbol[item.symbol]
    index = bisect.bisect_left(opened, as_of) - 1
    while index >= 0:
        bar = bars[index]
        closed_at = bar.closed_at.astimezone(UTC)
        if closed_at > as_of:
            index -= 1
            continue
        if closed_at <= item.signal_at:
            return entry_mark
        if closed_at >= item.exited_at:
            index -= 1
            continue
        return (r15._signal_adverse_r(item, bar) - PRIMARY_STRESS) * item.weight
    return entry_mark


def _open_pressure(
    *,
    active: Sequence[r15.AssignedTrade],
    as_of: datetime,
    prospective_side: object,
    bars_by_symbol: dict[str, Sequence[Any]],
    opened_by_symbol: dict[str, tuple[datetime, ...]],
) -> tuple[Decimal, int]:
    adverse_loss = Decimal()
    same_side = 0
    for item in active:
        mark = _current_adverse_mark(
            item,
            as_of=as_of,
            bars_by_symbol=bars_by_symbol,
            opened_by_symbol=opened_by_symbol,
        )
        adverse_loss += max(Decimal(), -mark)
        same_side += int(item.opportunity.signal.side is prospective_side)
    return adverse_loss, same_side


def _assign(
    stream: Sequence[tuple[r4.ExpandedOpportunity, r5.ManagedTrade]],
    *,
    profile: OpenPressureProfile,
    bars_by_symbol: dict[str, Sequence[Any]],
    opened_by_symbol: dict[str, tuple[datetime, ...]],
) -> tuple[tuple[r15.AssignedTrade, ...], dict[str, Any]]:
    equity = Decimal()
    history: deque[Decimal] = deque(
        [Decimal()],
        maxlen=BASE_RISK.rolling_trades + 1,
    )
    loss_streak = 0

    exit_heap: list[tuple[datetime, int, Decimal]] = []
    active: dict[int, r15.AssignedTrade] = {}
    assigned: list[r15.AssignedTrade] = []
    cursor = 0
    next_trade_id = 0

    overlap_entries = 0
    same_time_batches = 0
    same_time_batch_trades = 0
    budget_scaled_batches = 0
    floor_overage_batches = 0
    max_concurrent = 0
    max_committed = Decimal()
    max_open_adverse_loss = Decimal()
    pressure_reductions = 0
    same_side_reductions = 0
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
            and stream[end][0].signal.signal_at.astimezone(UTC) == batch_time
        ):
            end += 1
        batch = stream[cursor:end]
        if len(batch) > 1:
            same_time_batches += 1
            same_time_batch_trades += len(batch)

        # Shared pre-batch realized state. No sibling signal can affect another.
        dd_before = max(history) - equity
        active_before = tuple(active.values())
        requested: list[Decimal] = []
        tags: list[tuple[bool, bool, bool, bool, bool]] = []

        for opportunity, _outcome in batch:
            weight = r22._quality_weight(opportunity, BASE_QUALITY)
            realized_warn = realized_hard = realized_loss = False

            if dd_before >= BASE_RISK.hard_dd_r:
                weight *= BASE_RISK.hard_multiplier
                realized_hard = True
            elif dd_before >= BASE_RISK.warn_dd_r:
                weight *= BASE_RISK.warn_multiplier
                realized_warn = True

            if loss_streak >= 2:
                weight *= BASE_RISK.loss_multiplier
                realized_loss = True

            open_loss, same_side = _open_pressure(
                active=active_before,
                as_of=batch_time,
                prospective_side=opportunity.signal.side,
                bars_by_symbol=bars_by_symbol,
                opened_by_symbol=opened_by_symbol,
            )
            max_open_adverse_loss = max(max_open_adverse_loss, open_loss)
            open_multiplier = _pressure_multiplier(
                open_adverse_loss_r=open_loss,
                same_side_open_count=same_side,
                profile=profile,
            )
            pressure_hit = open_loss >= profile.live_warn_loss_r
            same_side_hit = same_side > 0
            weight *= open_multiplier

            requested.append(max(MIN_EFFECTIVE_WEIGHT, weight))
            tags.append(
                (
                    realized_warn,
                    realized_hard,
                    realized_loss,
                    pressure_hit,
                    same_side_hit,
                )
            )

        active_risk = sum((item.weight for item in active_before), Decimal())
        weights, scaled = r22._allocate_batch(
            requested,
            active_risk=active_risk,
            budget=BASE_RISK.portfolio_risk_budget_r,
        )
        budget_scaled_batches += int(scaled)
        if active_risk + sum(weights, Decimal()) > BASE_RISK.portfolio_risk_budget_r:
            floor_overage_batches += 1

        for ((opportunity, outcome), weight, tag) in zip(
            batch,
            weights,
            tags,
            strict=True,
        ):
            realized_warn, realized_hard, realized_loss, pressure_hit, same_side_hit = tag
            warn_allocations += int(realized_warn)
            hard_allocations += int(realized_hard)
            loss_allocations += int(realized_loss)
            pressure_reductions += int(pressure_hit)
            same_side_reductions += int(same_side_hit)
            overlap_entries += int(bool(active_before))

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
            primary_value = (outcome.r_multiple - PRIMARY_STRESS) * weight
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
    if len(assigned) != len(stream):
        raise ValueError("R24 assignment changed the permanent trade count")

    return tuple(assigned), {
        "assigned_trade_count": len(assigned),
        "suppressed_trade_count": 0,
        "overlap_entry_count": overlap_entries,
        "same_timestamp_signal_batches": same_time_batches,
        "same_timestamp_signal_trades": same_time_batch_trades,
        "budget_scaled_batches": budget_scaled_batches,
        "budget_floor_overage_batches": floor_overage_batches,
        "max_concurrent_open_positions": max_concurrent,
        "max_committed_structural_risk_r": str(max_committed),
        "max_observed_open_adverse_loss_r": str(max_open_adverse_loss),
        "open_pressure_reduced_allocations": pressure_reductions,
        "same_side_reduced_allocations": same_side_reductions,
        "minimum_effective_weight": str(min(item.weight for item in assigned)),
        "maximum_effective_weight": str(max(item.weight for item in assigned)),
        "mean_effective_weight": str(
            sum((item.weight for item in assigned), Decimal()) / len(assigned)
        ),
        "warn_allocations": warn_allocations,
        "hard_allocations": hard_allocations,
        "loss_defense_allocations": loss_allocations,
    }


def _yearly(
    assigned: Sequence[r15.AssignedTrade],
    *,
    stress: Decimal,
) -> dict[str, dict[str, Any]]:
    years = sorted({item.exited_at.year for item in assigned})
    result: dict[str, dict[str, Any]] = {}
    for year in years:
        values = tuple(
            (item.outcome.r_multiple - stress) * item.weight
            for item in sorted(
                (row for row in assigned if row.exited_at.year == year),
                key=lambda row: (row.exited_at, row.symbol, row.trade_id),
            )
        )
        result[str(year)] = fx._metrics(values)
    return result


def _all_years_positive(yearly: dict[str, dict[str, Any]]) -> bool:
    return bool(yearly) and all(
        Decimal(str(metrics["total_r"])) > 0 for metrics in yearly.values()
    )


def _realized_row(
    stream: Sequence[tuple[r4.ExpandedOpportunity, r5.ManagedTrade]],
    *,
    profile: OpenPressureProfile,
    bars_by_symbol: dict[str, Sequence[Any]],
    opened_by_symbol: dict[str, tuple[datetime, ...]],
) -> tuple[dict[str, Any], tuple[r15.AssignedTrade, ...]]:
    assigned, diagnostics = _assign(
        stream,
        profile=profile,
        bars_by_symbol=bars_by_symbol,
        opened_by_symbol=opened_by_symbol,
    )
    primary = fx._metrics(r15._realized_values(assigned, stress=PRIMARY_STRESS))
    secondary = fx._metrics(r15._realized_values(assigned, stress=SECONDARY_STRESS))
    yearly_primary = _yearly(assigned, stress=PRIMARY_STRESS)
    yearly_secondary = _yearly(assigned, stress=SECONDARY_STRESS)
    return (
        {
            "profile": profile.payload(),
            "sample": len(assigned),
            "primary": primary,
            "secondary": secondary,
            "yearly_primary": yearly_primary,
            "yearly_secondary": yearly_secondary,
            "all_primary_years_positive": _all_years_positive(yearly_primary),
            "all_secondary_years_positive": _all_years_positive(yearly_secondary),
            "diagnostics": diagnostics,
        },
        assigned,
    )


def _realized_rank(row: dict[str, Any]) -> tuple[int, Decimal, Decimal, Decimal]:
    primary = row["primary"]
    secondary = row["secondary"]
    realized_gate = (
        Decimal(str(primary["profit_factor"] or "0")) >= PF_PRIMARY_MIN
        and Decimal(str(secondary["profit_factor"] or "0")) >= PF_SECONDARY_MIN
        and Decimal(str(primary["max_drawdown_r"])) <= PORTFOLIO_DD_MAX
        and Decimal(str(secondary["max_drawdown_r"])) <= PORTFOLIO_DD_MAX
        and bool(row["all_primary_years_positive"])
    )
    return (
        int(realized_gate),
        Decimal(str(primary["profit_factor"] or "0")),
        -max(
            Decimal(str(primary["max_drawdown_r"])),
            Decimal(str(secondary["max_drawdown_r"])),
        ),
        Decimal(str(primary["total_r"])),
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
        _indexed,
        opened_by_symbol,
        provenance,
    ) = r15._build_five_year_stream(roots=roots)

    if not contract.validates_trade_count(years=5, sample=len(stream)):
        raise ValueError(f"permanent concurrent density drift: {len(stream)} trades")

    search: list[tuple[dict[str, Any], tuple[r15.AssignedTrade, ...]]] = []
    for profile in _profiles():
        search.append(
            _realized_row(
                stream,
                profile=profile,
                bars_by_symbol=bars_by_symbol,
                opened_by_symbol=opened_by_symbol,
            )
        )
    search.sort(key=lambda item: _realized_rank(item[0]), reverse=True)

    finalists: list[dict[str, Any]] = []
    for row, assigned in search[:64]:
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
        primary = row["primary"]
        secondary = row["secondary"]
        diagnostics = row["diagnostics"]
        goal_pass = (
            len(assigned) == len(stream)
            and int(diagnostics["suppressed_trade_count"]) == 0
            and int(diagnostics["max_concurrent_open_positions"]) >= 2
            and Decimal(str(primary["profit_factor"] or "0")) >= PF_PRIMARY_MIN
            and Decimal(str(secondary["profit_factor"] or "0")) >= PF_SECONDARY_MIN
            and Decimal(primary_mtm["max_drawdown_r"]) <= PORTFOLIO_DD_MAX
            and Decimal(secondary_mtm["max_drawdown_r"]) <= PORTFOLIO_DD_MAX
            and bool(row["all_primary_years_positive"])
        )
        final = dict(row)
        final["primary_conservative_mark_to_market"] = primary_mtm
        final["secondary_conservative_mark_to_market"] = secondary_mtm
        final["goal_pass"] = goal_pass
        finalists.append(final)

    finalists.sort(
        key=lambda row: (
            int(bool(row["goal_pass"])),
            Decimal(str(row["primary"]["profit_factor"] or "0")),
            -max(
                Decimal(row["primary_conservative_mark_to_market"]["max_drawdown_r"]),
                Decimal(row["secondary_conservative_mark_to_market"]["max_drawdown_r"]),
            ),
            Decimal(str(row["primary"]["total_r"])),
        ),
        reverse=True,
    )
    goals = [row for row in finalists if bool(row["goal_pass"])]

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "sample": len(stream),
        "profile_count": len(_profiles()),
        "mtm_finalist_count": len(finalists),
        "goal_candidate_count": len(goals),
        "fixed_r23_start": {
            "quality": BASE_QUALITY.payload(),
            "risk": BASE_RISK.payload(),
            "opportunity_architecture_changed": False,
            "target_changed": False,
            "stop_changed": False,
        },
        "contract": {
            "contract_id": contract.CONTRACT_ID,
            "markets": list(contract.MARKETS),
            "global_single_position_rule": False,
            "cross_market_concurrency_required": True,
            "same_timestamp_pre_batch_state": True,
            "signal_suppression_allowed": False,
            "zero_risk_allowed": False,
            "portfolio_dd_max_r": str(PORTFOLIO_DD_MAX),
            "primary_pf_minimum": str(PF_PRIMARY_MIN),
            "secondary_pf_minimum": str(PF_SECONDARY_MIN),
            "all_primary_years_positive_required": True,
            "both_stress_surfaces_conservative_dd_must_pass": True,
        },
        "best": finalists[0] if finalists else None,
        "top_10": finalists[:10],
        "goal_candidates": goals[:10],
        "provenance": provenance,
        "governance": {
            "development_only": True,
            "bounded_r23_refinement": True,
            "research_dimension": "observable_open_position_pressure_only",
            "future_outcome_used_for_new_signal_risk": False,
            "open_marks_use_only_closed_m15_evidence": True,
            "existing_positions_resized": False,
            "stops_widened": False,
            "all_trades_preserved": True,
            "cross_market_concurrency_preserved": True,
            "same_timestamp_batch_allocation": True,
            "signal_suppression_allowed": False,
            "zero_risk_allowed": False,
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
                "sample": report["sample"],
                "profile_count": report["profile_count"],
                "goal_candidate_count": report["goal_candidate_count"],
                "best": report["best"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
