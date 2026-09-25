"""VT08 Index R33 — causal POI-family health governor.

R32 showed that density restoration is not the source of the 2019 failure:
additional source-complete signals were positive in 2019 and occupancy-suppressed
signals were strongly positive. The inherited R28/R29 static FVG-heavy quality
hierarchy is the mismatch.

R33 keeps all 2,448 structural signals, the 2.5R lifecycle, same-symbol distinct
structural concurrency, and the existing portfolio risk defense. It removes the
static retrospective quality hierarchy and replaces it with a causal rolling
experience memory per methodology POI family:

    CISD / FVG / relevant-swing

Only completed prior trades of the same POI family can affect the risk requested
by a new signal. Same-timestamp siblings see identical pre-batch state. No
calendar year, future result, market deletion, side deletion, or trade
suppression is allowed.
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
from qore.infrastructure.trader_lab import vt08_index_concurrent_market_contract as contract
from qore.infrastructure.trader_lab import vt08_index_r6_5y_failure_forensics as fx
from qore.infrastructure.trader_lab import vt08_index_r10_contextual_risk as r10
from qore.infrastructure.trader_lab import vt08_index_r15_concurrent_portfolio_validation as r15
from qore.infrastructure.trader_lab import vt08_index_r22_concurrent_stable_formation as r22
from qore.infrastructure.trader_lab import vt08_index_r24_open_position_pressure as r24
from qore.infrastructure.trader_lab import (
    vt08_index_r31_source_complete_structural_concurrency as r31,
)

SCHEMA = "qore.trader_lab.vt08_index_r33_causal_poi_health_governor.v1"
IDENTITY = "VT08_INDEX_R33_CAUSAL_POI_HEALTH_GOVERNOR_001"

PRIMARY_STRESS = Decimal("0.05")
SECONDARY_STRESS = Decimal("0.10")
PF_PRIMARY_MIN = Decimal("1.50")
PF_SECONDARY_MIN = Decimal("1.30")
PORTFOLIO_DD_MAX = Decimal("6")
MIN_EFFECTIVE_WEIGHT = Decimal("0.005")
POI_FAMILIES = ("cisd", "fvg", "relevant-swing")


@dataclass(frozen=True, slots=True)
class PoiHealthProfile:
    base_weight: Decimal
    rolling_family_trades: int
    min_observations: int
    cold_multiplier: Decimal
    weak_multiplier: Decimal
    healthy_mean_threshold_r: Decimal

    @property
    def profile_id(self) -> str:
        return (
            "PH-"
            f"B{self.base_weight}-"
            f"W{self.rolling_family_trades}-"
            f"N{self.min_observations}-"
            f"C{self.cold_multiplier}-"
            f"WEAK{self.weak_multiplier}-"
            f"T{self.healthy_mean_threshold_r}"
        )

    def payload(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "base_weight": str(self.base_weight),
            "rolling_family_trades": self.rolling_family_trades,
            "min_observations": self.min_observations,
            "cold_multiplier": str(self.cold_multiplier),
            "weak_multiplier": str(self.weak_multiplier),
            "healthy_mean_threshold_r": str(self.healthy_mean_threshold_r),
        }


def _profiles() -> tuple[PoiHealthProfile, ...]:
    return tuple(
        PoiHealthProfile(base, window, minimum, cold, weak, threshold)
        for base, window, minimum, cold, weak, threshold in itertools.product(
            (Decimal("0.05"), Decimal("0.10"), Decimal("0.20")),
            (10, 20, 40),
            (5, 10),
            (Decimal("0.25"), Decimal("0.50")),
            (Decimal("0.05"), Decimal("0.10"), Decimal("0.25")),
            (Decimal("0.00"), Decimal("0.05")),
        )
        if minimum <= window
    )


def _health_multiplier(
    history: Sequence[Decimal],
    *,
    profile: PoiHealthProfile,
) -> tuple[Decimal, str]:
    if len(history) < profile.min_observations:
        return profile.cold_multiplier, "COLD"
    mean_r = sum(history, Decimal()) / len(history)
    if mean_r >= profile.healthy_mean_threshold_r:
        return Decimal("1"), "HEALTHY"
    return profile.weak_multiplier, "WEAK"


def _assign(
    stream: Sequence[tuple[r4.ExpandedOpportunity, r5.ManagedTrade]],
    *,
    profile: PoiHealthProfile,
) -> tuple[tuple[r15.AssignedTrade, ...], dict[str, Any]]:
    equity = Decimal()
    history: deque[Decimal] = deque(
        [Decimal()],
        maxlen=r24.BASE_RISK.rolling_trades + 1,
    )
    family_histories: dict[str, deque[Decimal]] = {
        family: deque(maxlen=profile.rolling_family_trades)
        for family in POI_FAMILIES
    }
    loss_streak = 0

    exit_heap: list[tuple[datetime, int, Decimal, str, Decimal]] = []
    active: dict[int, r15.AssignedTrade] = {}
    assigned: list[r15.AssignedTrade] = []
    cursor = 0
    next_trade_id = 0

    max_concurrent = 0
    max_committed = Decimal()
    overlap_entries = 0
    same_time_batches = 0
    same_time_batch_trades = 0
    budget_scaled_batches = 0
    floor_overage_batches = 0
    cold_allocations = 0
    weak_allocations = 0
    healthy_allocations = 0
    warn_allocations = 0
    hard_allocations = 0
    loss_allocations = 0
    family_state_counts: dict[str, dict[str, int]] = {
        family: {"COLD": 0, "WEAK": 0, "HEALTHY": 0}
        for family in POI_FAMILIES
    }

    def settle(until: datetime) -> None:
        nonlocal equity, loss_streak
        while exit_heap and exit_heap[0][0] <= until:
            _exit_at, trade_id, weighted_value, family, raw_value = heapq.heappop(
                exit_heap
            )
            active.pop(trade_id, None)
            equity += weighted_value
            history.append(equity)
            if weighted_value < 0:
                loss_streak += 1
            else:
                loss_streak = 0
            family_histories[family].append(raw_value)

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

        dd_before = max(history) - equity
        requested: list[Decimal] = []
        metadata: list[tuple[str, str, bool, bool, bool]] = []

        for opportunity, _outcome in batch:
            family = str(opportunity.source_poi_kind)
            if family not in family_histories:
                raise ValueError(f"unexpected POI family: {family}")
            family_multiplier, state = _health_multiplier(
                tuple(family_histories[family]),
                profile=profile,
            )
            weight = profile.base_weight * family_multiplier
            family_state_counts[family][state] += 1
            cold_allocations += int(state == "COLD")
            weak_allocations += int(state == "WEAK")
            healthy_allocations += int(state == "HEALTHY")

            realized_warn = realized_hard = realized_loss = False
            if dd_before >= r24.BASE_RISK.hard_dd_r:
                weight *= r24.BASE_RISK.hard_multiplier
                realized_hard = True
            elif dd_before >= r24.BASE_RISK.warn_dd_r:
                weight *= r24.BASE_RISK.warn_multiplier
                realized_warn = True

            if loss_streak >= 2:
                weight *= r24.BASE_RISK.loss_multiplier
                realized_loss = True

            requested.append(max(MIN_EFFECTIVE_WEIGHT, weight))
            metadata.append(
                (family, state, realized_warn, realized_hard, realized_loss)
            )

        active_risk = sum((item.weight for item in active.values()), Decimal())
        weights, scaled = r22._allocate_batch(
            requested,
            active_risk=active_risk,
            budget=r24.BASE_RISK.portfolio_risk_budget_r,
        )
        budget_scaled_batches += int(scaled)
        if active_risk + sum(weights, Decimal()) > r24.BASE_RISK.portfolio_risk_budget_r:
            floor_overage_batches += 1

        for ((opportunity, outcome), weight, meta) in zip(
            batch,
            weights,
            metadata,
            strict=True,
        ):
            family, _state, realized_warn, realized_hard, realized_loss = meta
            warn_allocations += int(realized_warn)
            hard_allocations += int(realized_hard)
            loss_allocations += int(realized_loss)
            overlap_entries += int(bool(active))

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

            raw_value = outcome.r_multiple - PRIMARY_STRESS
            weighted_value = raw_value * weight
            heapq.heappush(
                exit_heap,
                (
                    item.exited_at,
                    item.trade_id,
                    weighted_value,
                    family,
                    raw_value,
                ),
            )

        max_concurrent = max(max_concurrent, len(active))
        max_committed = max(
            max_committed,
            sum((item.weight for item in active.values()), Decimal()),
        )
        cursor = end

    settle(datetime.max.replace(tzinfo=UTC))
    if len(assigned) != len(stream):
        raise ValueError("R33 assignment changed source-complete trade count")

    return tuple(assigned), {
        "assigned_trade_count": len(assigned),
        "suppressed_trade_count": 0,
        "max_concurrent_open_positions": max_concurrent,
        "max_committed_structural_risk_r": str(max_committed),
        "overlap_entry_count": overlap_entries,
        "same_timestamp_signal_batches": same_time_batches,
        "same_timestamp_signal_trades": same_time_batch_trades,
        "budget_scaled_batches": budget_scaled_batches,
        "budget_floor_overage_batches": floor_overage_batches,
        "cold_allocations": cold_allocations,
        "weak_allocations": weak_allocations,
        "healthy_allocations": healthy_allocations,
        "family_state_counts": family_state_counts,
        "warn_allocations": warn_allocations,
        "hard_allocations": hard_allocations,
        "loss_defense_allocations": loss_allocations,
        "minimum_effective_weight": str(min(item.weight for item in assigned)),
        "maximum_effective_weight": str(max(item.weight for item in assigned)),
        "mean_effective_weight": str(
            sum((item.weight for item in assigned), Decimal()) / len(assigned)
        ),
    }


def _row(
    stream: Sequence[tuple[r4.ExpandedOpportunity, r5.ManagedTrade]],
    *,
    profile: PoiHealthProfile,
) -> tuple[dict[str, Any], tuple[r15.AssignedTrade, ...]]:
    assigned, diagnostics = _assign(stream, profile=profile)
    primary = fx._metrics(r15._realized_values(assigned, stress=PRIMARY_STRESS))
    secondary = fx._metrics(r15._realized_values(assigned, stress=SECONDARY_STRESS))
    yearly_primary = r24._yearly(assigned, stress=PRIMARY_STRESS)
    yearly_secondary = r24._yearly(assigned, stress=SECONDARY_STRESS)
    return (
        {
            "profile": profile.payload(),
            "sample": len(assigned),
            "primary": primary,
            "secondary": secondary,
            "yearly_primary": yearly_primary,
            "yearly_secondary": yearly_secondary,
            "positive_primary_years": sum(
                Decimal(str(item["total_r"])) > 0
                for item in yearly_primary.values()
            ),
            "positive_secondary_years": sum(
                Decimal(str(item["total_r"])) > 0
                for item in yearly_secondary.values()
            ),
            "all_primary_years_positive": r24._all_years_positive(yearly_primary),
            "all_secondary_years_positive": r24._all_years_positive(
                yearly_secondary
            ),
            "diagnostics": diagnostics,
        },
        assigned,
    )


def _realized_rank(row: dict[str, Any]) -> tuple[int, int, Decimal, Decimal, Decimal]:
    p = row["primary"]
    s = row["secondary"]
    pre_mtm = (
        Decimal(str(p["profit_factor"] or "0")) >= PF_PRIMARY_MIN
        and Decimal(str(s["profit_factor"] or "0")) >= PF_SECONDARY_MIN
        and bool(row["all_primary_years_positive"])
        and bool(row["all_secondary_years_positive"])
    )
    return (
        int(pre_mtm),
        int(row["positive_secondary_years"]),
        Decimal(str(p["profit_factor"] or "0")),
        -max(
            Decimal(str(p["max_drawdown_r"])),
            Decimal(str(s["max_drawdown_r"])),
        ),
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
    stream, bars_by_symbol, opened_by_symbol, provenance = (
        r31._build_source_complete_stream(roots=roots)
    )
    if not contract.validates_trade_count(years=5, sample=len(stream)):
        raise ValueError(f"R33 density drift: {len(stream)}")

    raw_primary = r31._raw_metrics(stream, stress=PRIMARY_STRESS)
    raw_edge_pass = (
        Decimal(str(raw_primary["profit_factor"] or "0")) >= Decimal("1")
        and Decimal(str(raw_primary["total_r"])) > 0
    )

    search = [_row(stream, profile=profile) for profile in _profiles()]
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
        p = row["primary"]
        s = row["secondary"]
        goal_pass = (
            raw_edge_pass
            and len(assigned) == len(stream)
            and Decimal(str(p["profit_factor"] or "0")) >= PF_PRIMARY_MIN
            and Decimal(str(s["profit_factor"] or "0")) >= PF_SECONDARY_MIN
            and Decimal(primary_mtm["max_drawdown_r"]) <= PORTFOLIO_DD_MAX
            and Decimal(secondary_mtm["max_drawdown_r"]) <= PORTFOLIO_DD_MAX
            and bool(row["all_primary_years_positive"])
            and bool(row["all_secondary_years_positive"])
            and int(row["diagnostics"]["suppressed_trade_count"]) == 0
        )
        final = dict(row)
        final["primary_conservative_mark_to_market"] = primary_mtm
        final["secondary_conservative_mark_to_market"] = secondary_mtm
        final["goal_pass"] = goal_pass
        finalists.append(final)

    finalists.sort(
        key=lambda row: (
            int(bool(row["goal_pass"])),
            int(row["positive_secondary_years"]),
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
        "raw_primary": raw_primary,
        "raw_edge_pass": raw_edge_pass,
        "goal_candidate_count": len(goals),
        "best": finalists[0] if finalists else None,
        "top_10": finalists[:10],
        "goal_candidates": goals[:10],
        "contract": {
            "five_year_trade_range": list(contract.FIVE_YEAR_TRADE_RANGE),
            "two_year_min_trades": contract.TWO_YEAR_MIN_TRADES,
            "primary_pf_minimum": str(PF_PRIMARY_MIN),
            "secondary_pf_minimum": str(PF_SECONDARY_MIN),
            "portfolio_dd_max_r": str(PORTFOLIO_DD_MAX),
            "all_years_positive_both_stresses": True,
            "all_signals_preserved": True,
        },
        "provenance": provenance,
        "governance": {
            "development_only": True,
            "consumed_window": True,
            "fresh_holdout_claim": False,
            "calendar_year_used_for_decision": False,
            "future_outcome_used_for_new_signal_risk": False,
            "static_r28_fvg_quality_hierarchy_used": False,
            "experience_memory_dimension": "poi_family_rolling_health",
            "all_structural_signals_preserved": True,
            "signal_suppression_allowed": False,
            "zero_risk_allowed": False,
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
