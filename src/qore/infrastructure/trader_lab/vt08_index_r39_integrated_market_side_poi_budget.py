"""VT08 Index R39 — integrated causal market-side-POI budget governor.

Preregistered before R38 forensics are read. R39 established that market-side
health is too coarse. R39 composes the two already-existing causal dimensions:
(symbol, side) and source POI family. The resulting (symbol, side, POI) memory
acts before portfolio batch allocation.

Only prior completed raw outcomes update health. R34 formation and global POI
health remain unchanged. Every structural signal remains present at a strict
0.005R minimum. No calendar/year label is available to runtime.
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

from qore.infrastructure.trader_lab import (
    vt08_index_cibo_2y_density_round4 as r4,
)
from qore.infrastructure.trader_lab import (
    vt08_index_cibo_2y_management_round5 as r5,
)
from qore.infrastructure.trader_lab import (
    vt08_index_concurrent_market_contract as contract,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r6_5y_failure_forensics as fx,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r10_contextual_risk as r10,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r15_concurrent_portfolio_validation as r15,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r22_concurrent_stable_formation as r22,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r24_open_position_pressure as r24,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r25_r23_failure_forensics as r25,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r26_formation_health_governor as r26,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r29_candidate_freeze as r29,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r31_source_complete_structural_concurrency as r31,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r33_causal_poi_health_governor as r33,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r34_hybrid_formation_poi_health as r34,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r35_five_year_temporal_contract as r35,
)

SCHEMA = "qore.trader_lab.vt08_index_r39_integrated_market_side_poi_budget.v1"
IDENTITY = "VT08_INDEX_R39_INTEGRATED_MARKET_SIDE_POI_BUDGET_001"

PRIMARY_STRESS = Decimal("0.05")
SECONDARY_STRESS = Decimal("0.10")
PF_PRIMARY_MIN = Decimal("1.50")
PF_SECONDARY_MIN = Decimal("1.30")
PORTFOLIO_DD_MAX = Decimal("6")
MIN_EFFECTIVE_WEIGHT = Decimal("0.005")

BASE_POI_OVERLAY = r34.PoiOverlayProfile(
    rolling_family_trades=10,
    min_observations=5,
    cold_multiplier=Decimal("0.50"),
    weak_multiplier=Decimal("0.50"),
    healthy_mean_threshold_r=Decimal("0.05"),
)


@dataclass(frozen=True, slots=True)
class MarketSidePoiProfile:
    rolling_group_trades: int
    min_observations: int
    cold_multiplier: Decimal
    weak_multiplier: Decimal
    healthy_mean_threshold_r: Decimal

    @property
    def profile_id(self) -> str:
        return (
            "IMSP-"
            f"W{self.rolling_group_trades}-"
            f"N{self.min_observations}-"
            f"C{self.cold_multiplier}-"
            f"WEAK{self.weak_multiplier}-"
            f"T{self.healthy_mean_threshold_r}"
        )

    def payload(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "rolling_group_trades": self.rolling_group_trades,
            "min_observations": self.min_observations,
            "cold_multiplier": str(self.cold_multiplier),
            "weak_multiplier": str(self.weak_multiplier),
            "healthy_mean_threshold_r": str(self.healthy_mean_threshold_r),
        }


def _profiles() -> tuple[MarketSidePoiProfile, ...]:
    return tuple(
        MarketSidePoiProfile(window, minimum, cold, weak, threshold)
        for window, minimum, cold, weak, threshold in itertools.product(
            (8, 16, 32),
            (4, 8),
            (Decimal("0.50"), Decimal("1.00")),
            (Decimal("0.25"), Decimal("0.50"), Decimal("0.75")),
            (Decimal("0.00"), Decimal("0.05")),
        )
        if minimum <= window
    )


def _group_key(opportunity: r4.ExpandedOpportunity) -> str:
    signal = opportunity.signal
    return (
        f"{signal.symbol}|{signal.side.value}|"
        f"{opportunity.source_poi_kind}"
    )


def _assign(
    stream: Sequence[tuple[r4.ExpandedOpportunity, r5.ManagedTrade]],
    *,
    profile: MarketSidePoiProfile,
) -> tuple[tuple[r15.AssignedTrade, ...], dict[str, Any]]:
    formation = r29.frozen_formation_health_profile()
    equity = Decimal()
    history: deque[Decimal] = deque(
        [Decimal()],
        maxlen=r24.BASE_RISK.rolling_trades + 1,
    )
    tier_histories: dict[str, deque[Decimal]] = {
        tier: deque(maxlen=formation.rolling_tier_trades)
        for tier in r26.ADAPTIVE_TIERS
    }
    poi_histories: dict[str, deque[Decimal]] = {
        family: deque(maxlen=BASE_POI_OVERLAY.rolling_family_trades)
        for family in r33.POI_FAMILIES
    }
    structural_group_histories: dict[str, deque[Decimal]] = {}
    loss_streak = 0

    exit_heap: list[
        tuple[datetime, int, Decimal, str, str, str, Decimal]
    ] = []
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
    structural_group_states = {"COLD": 0, "WEAK": 0, "HEALTHY": 0}

    def structural_group_history(key: str) -> deque[Decimal]:
        if key not in structural_group_histories:
            structural_group_histories[key] = deque(
                maxlen=profile.rolling_group_trades
            )
        return structural_group_histories[key]

    def settle(until: datetime) -> None:
        nonlocal equity, loss_streak
        while exit_heap and exit_heap[0][0] <= until:
            (
                _exit_at,
                trade_id,
                weighted_value,
                tier,
                family,
                group,
                raw_value,
            ) = heapq.heappop(exit_heap)
            active.pop(trade_id, None)
            equity += weighted_value
            history.append(equity)
            if weighted_value < 0:
                loss_streak += 1
            else:
                loss_streak = 0
            if tier in tier_histories:
                tier_histories[tier].append(raw_value)
            poi_histories[family].append(raw_value)
            structural_group_history(group).append(raw_value)

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
        metadata: list[tuple[str, str, str]] = []

        for opportunity, _outcome in batch:
            tier = r25._quality_tier(opportunity)
            family = str(opportunity.source_poi_kind)
            group = _group_key(opportunity)

            weight = r22._quality_weight(
                opportunity,
                r24.BASE_QUALITY,
            )

            if tier in tier_histories:
                tier_mult, _tier_state = r26._health_multiplier(
                    tuple(tier_histories[tier]),
                    profile=formation,
                )
                weight *= tier_mult

            poi_mult, _poi_state = r34._health(
                tuple(poi_histories[family]),
                minimum=BASE_POI_OVERLAY.min_observations,
                cold=BASE_POI_OVERLAY.cold_multiplier,
                weak=BASE_POI_OVERLAY.weak_multiplier,
                threshold=BASE_POI_OVERLAY.healthy_mean_threshold_r,
            )
            weight *= poi_mult

            group_mult, group_state = r34._health(
                tuple(structural_group_history(group)),
                minimum=profile.min_observations,
                cold=profile.cold_multiplier,
                weak=profile.weak_multiplier,
                threshold=profile.healthy_mean_threshold_r,
            )
            weight *= group_mult
            structural_group_states[group_state] += 1

            if dd_before >= r24.BASE_RISK.hard_dd_r:
                weight *= r24.BASE_RISK.hard_multiplier
            elif dd_before >= r24.BASE_RISK.warn_dd_r:
                weight *= r24.BASE_RISK.warn_multiplier
            if loss_streak >= 2:
                weight *= r24.BASE_RISK.loss_multiplier

            requested.append(max(MIN_EFFECTIVE_WEIGHT, weight))
            metadata.append((tier, family, group))

        active_risk = sum(
            (item.weight for item in active.values()),
            Decimal(),
        )
        weights, scaled = r22._allocate_batch(
            requested,
            active_risk=active_risk,
            budget=r24.BASE_RISK.portfolio_risk_budget_r,
        )
        budget_scaled_batches += int(scaled)
        if (
            active_risk + sum(weights, Decimal())
            > r24.BASE_RISK.portfolio_risk_budget_r
        ):
            floor_overage_batches += 1

        for ((opportunity, outcome), weight, meta) in zip(
            batch,
            weights,
            metadata,
            strict=True,
        ):
            tier, family, group = meta
            overlap_entries += int(bool(active))
            item = r15.AssignedTrade(
                trade_id=next_trade_id,
                opportunity=opportunity,
                outcome=outcome,
                context=r10.Context(
                    previous_source_day_body_opposed=False,
                    rearm=int(opportunity.rearm_index) > 0,
                    c2_expansion=False,
                    short=False,
                ),
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
                    tier,
                    family,
                    group,
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
        raise ValueError("R39 changed source-complete trade count")

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
        "structural_group_state_counts": structural_group_states,
        "structural_group_count": len(structural_group_histories),
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


def _row(
    stream: Sequence[tuple[r4.ExpandedOpportunity, r5.ManagedTrade]],
    *,
    profile: MarketSidePoiProfile,
) -> tuple[dict[str, Any], tuple[r15.AssignedTrade, ...]]:
    assigned, diagnostics = _assign(stream, profile=profile)
    primary = fx._metrics(
        r15._realized_values(assigned, stress=PRIMARY_STRESS)
    )
    secondary = fx._metrics(
        r15._realized_values(assigned, stress=SECONDARY_STRESS)
    )
    primary_blocks = r35._five_full_year_blocks(
        assigned,
        stress=PRIMARY_STRESS,
    )
    secondary_blocks = r35._five_full_year_blocks(
        assigned,
        stress=SECONDARY_STRESS,
    )
    return (
        {
            "profile": profile.payload(),
            "sample": len(assigned),
            "primary": primary,
            "secondary": secondary,
            "five_year_blocks_primary": primary_blocks,
            "five_year_blocks_secondary": secondary_blocks,
            "all_five_primary_blocks_positive": (
                r35._all_blocks_positive(primary_blocks)
            ),
            "all_five_secondary_blocks_positive": (
                r35._all_blocks_positive(secondary_blocks)
            ),
            "diagnostics": diagnostics,
        },
        assigned,
    )


def _rank(
    row: dict[str, Any],
) -> tuple[int, int, Decimal, Decimal, Decimal]:
    temporal = (
        bool(row["all_five_primary_blocks_positive"])
        and bool(row["all_five_secondary_blocks_positive"])
    )
    primary = row["primary"]
    secondary = row["secondary"]
    economic = (
        Decimal(str(primary["profit_factor"] or "0")) >= PF_PRIMARY_MIN
        and Decimal(str(secondary["profit_factor"] or "0"))
        >= PF_SECONDARY_MIN
    )
    weakest_secondary = min(
        Decimal(str(block["total_r"]))
        for block in row["five_year_blocks_secondary"].values()
    )
    return (
        int(temporal and economic),
        int(temporal),
        weakest_secondary,
        Decimal(str(primary["profit_factor"] or "0")),
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
    stream, bars_by_symbol, opened_by_symbol, provenance = (
        r31._build_source_complete_stream(roots=roots)
    )
    if not contract.validates_trade_count(years=5, sample=len(stream)):
        raise ValueError(f"R39 density drift: {len(stream)}")

    raw_primary = r31._raw_metrics(
        stream,
        stress=PRIMARY_STRESS,
    )
    raw_edge_pass = (
        Decimal(str(raw_primary["profit_factor"] or "0")) >= Decimal("1")
        and Decimal(str(raw_primary["total_r"])) > 0
    )

    search = [_row(stream, profile=profile) for profile in _profiles()]
    search.sort(key=lambda item: _rank(item[0]), reverse=True)

    finalists: list[dict[str, Any]] = []
    for row, assigned in search:
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
        goal_pass = (
            raw_edge_pass
            and contract.validates_trade_count(
                years=5,
                sample=len(assigned),
            )
            and Decimal(str(primary["profit_factor"] or "0"))
            >= PF_PRIMARY_MIN
            and Decimal(str(secondary["profit_factor"] or "0"))
            >= PF_SECONDARY_MIN
            and Decimal(primary_mtm["max_drawdown_r"])
            <= PORTFOLIO_DD_MAX
            and Decimal(secondary_mtm["max_drawdown_r"])
            <= PORTFOLIO_DD_MAX
            and bool(row["all_five_primary_blocks_positive"])
            and bool(row["all_five_secondary_blocks_positive"])
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
            *_rank(row),
            -max(
                Decimal(
                    row["primary_conservative_mark_to_market"][
                        "max_drawdown_r"
                    ]
                ),
                Decimal(
                    row["secondary_conservative_mark_to_market"][
                        "max_drawdown_r"
                    ]
                ),
            ),
        ),
        reverse=True,
    )
    goals = [row for row in finalists if bool(row["goal_pass"])]

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "sample": len(stream),
        "evaluated_profile_count": len(_profiles()),
        "base_poi_overlay": BASE_POI_OVERLAY.payload(),
        "raw_primary": raw_primary,
        "raw_edge_pass": raw_edge_pass,
        "goal_candidate_count": len(goals),
        "best": finalists[0],
        "top_10": finalists[:10],
        "goal_candidates": goals[:10],
        "temporal_contract": {
            "boundaries": [
                x.isoformat() for x in r35._annual_boundaries()
            ],
            "full_year_block_count": 5,
            "calendar_year_used_for_runtime_decision": False,
        },
        "contract": {
            "five_year_trade_range": list(
                contract.FIVE_YEAR_TRADE_RANGE
            ),
            "two_year_min_trades": contract.TWO_YEAR_MIN_TRADES,
            "primary_pf_minimum": str(PF_PRIMARY_MIN),
            "secondary_pf_minimum": str(PF_SECONDARY_MIN),
            "portfolio_dd_max_r": str(PORTFOLIO_DD_MAX),
            "five_full_blocks_positive_both_stresses": True,
            "all_signals_preserved": True,
        },
        "provenance": provenance,
        "governance": {
            "development_only": True,
            "consumed_window": True,
            "preregistered_before_r38_result": True,
            "fresh_holdout_claim": False,
            "new_dimension": (
                "preallocation_causal_market_side_poi_completed_trade_health"
            ),
            "r34_formation_and_poi_layers_preserved": True,
            "calendar_or_year_feature_used_for_runtime": False,
            "health_uses_only_prior_completed_raw_outcomes": True,
            "same_timestamp_signals_share_pre_batch_memory": True,
            "future_outcome_used_for_current_risk": False,
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
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "identity": IDENTITY,
                "sample": report["sample"],
                "goal_candidate_count": report["goal_candidate_count"],
                "best": report["best"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
