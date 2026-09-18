"""VT08 Index R22 — concurrent stable-formation capital hierarchy.

R22 keeps the exact R8 2.5R execution stream and the corrected R15 concurrency
model. It uses ONLY the three R17 formation cohorts that were positive in both
consumed development windows:

A) FVG + H4 entry latency 121-180m
B) FVG + CISD latency 4-7
C) FVG + structural risk fraction 0.15-0.30%

All other valid trades remain executable with a small non-zero base allocation.
No signal is suppressed. Simultaneous cross-market batches are funded pro-rata
from a portfolio structural-risk budget. Governor state uses only completed
prior trades.

The 5Y window is consumed development evidence.
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
from qore.infrastructure.trader_lab import vt08_index_r15_concurrent_portfolio_validation as r15
from qore.infrastructure.trader_lab import vt08_index_r17_formation_quality_forensics as r17

SCHEMA = "qore.trader_lab.vt08_index_r22_concurrent_stable_formation.v1"
IDENTITY = "VT08_INDEX_R22_CONCURRENT_STABLE_FORMATION_001"
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
class QualityProfile:
    base_weight: Decimal
    tier_a_weight: Decimal
    tier_b_weight: Decimal
    tier_c_weight: Decimal

    @property
    def profile_id(self) -> str:
        return (
            "Q-"
            f"BASE{self.base_weight}-"
            f"A{self.tier_a_weight}-"
            f"B{self.tier_b_weight}-"
            f"C{self.tier_c_weight}"
        )

    def payload(self) -> dict[str, str]:
        return {
            "profile_id": self.profile_id,
            "base_weight": str(self.base_weight),
            "tier_a_weight": str(self.tier_a_weight),
            "tier_b_weight": str(self.tier_b_weight),
            "tier_c_weight": str(self.tier_c_weight),
        }


@dataclass(frozen=True, slots=True)
class RiskProfile:
    rolling_trades: int
    warn_dd_r: Decimal
    warn_multiplier: Decimal
    hard_dd_r: Decimal
    hard_multiplier: Decimal
    loss_multiplier: Decimal
    portfolio_risk_budget_r: Decimal

    @property
    def profile_id(self) -> str:
        return (
            "R-"
            f"W{self.rolling_trades}-"
            f"D{self.warn_dd_r}x{self.warn_multiplier}-"
            f"H{self.hard_dd_r}x{self.hard_multiplier}-"
            f"L2x{self.loss_multiplier}-"
            f"CAP{self.portfolio_risk_budget_r}"
        )

    def payload(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "rolling_trades": self.rolling_trades,
            "warn_dd_r": str(self.warn_dd_r),
            "warn_multiplier": str(self.warn_multiplier),
            "hard_dd_r": str(self.hard_dd_r),
            "hard_multiplier": str(self.hard_multiplier),
            "loss_trigger": 2,
            "loss_multiplier": str(self.loss_multiplier),
            "portfolio_risk_budget_r": str(self.portfolio_risk_budget_r),
        }


def _quality_profiles() -> tuple[QualityProfile, ...]:
    return tuple(
        QualityProfile(base, tier_a, tier_b, tier_c)
        for base, tier_a, tier_b, tier_c in itertools.product(
            (Decimal("0.005"), Decimal("0.010")),
            (Decimal("1.00"), Decimal("1.25"), Decimal("1.50")),
            (Decimal("0.50"), Decimal("0.75"), Decimal("1.00")),
            (Decimal("0.10"), Decimal("0.25"), Decimal("0.50")),
        )
    )


def _risk_profiles() -> tuple[RiskProfile, ...]:
    rows: list[RiskProfile] = []
    for (
        rolling,
        warn_dd,
        warn_mult,
        hard_dd,
        hard_mult,
        loss_mult,
        cap,
    ) in itertools.product(
        (20, 40, 60),
        (Decimal("0.75"), Decimal("1.00"), Decimal("1.25")),
        (Decimal("0.10"), Decimal("0.20")),
        (Decimal("1.50"), Decimal("1.75"), Decimal("2.00")),
        (Decimal("0.05"), Decimal("0.10")),
        (Decimal("0.10"), Decimal("0.20")),
        (Decimal("1.00"), Decimal("1.25"), Decimal("1.50")),
    ):
        if hard_dd <= warn_dd:
            continue
        rows.append(
            RiskProfile(
                rolling_trades=rolling,
                warn_dd_r=warn_dd,
                warn_multiplier=warn_mult,
                hard_dd_r=hard_dd,
                hard_multiplier=hard_mult,
                loss_multiplier=loss_mult,
                portfolio_risk_budget_r=cap,
            )
        )
    return tuple(rows)


def _quality_weight(
    opportunity: r4.ExpandedOpportunity,
    profile: QualityProfile,
) -> Decimal:
    features = r17._feature_values(opportunity)
    weight = profile.base_weight

    if (
        features["poi"] == "fvg"
        and features["risk_fraction"] == "0.15-0.30%"
    ):
        weight = max(weight, profile.tier_c_weight)

    if features["poi"] == "fvg" and features["cisd_latency"] == "4-7":
        weight = max(weight, profile.tier_b_weight)

    if (
        features["poi"] == "fvg"
        and features["h4_entry_latency"] == "121-180m"
    ):
        weight = max(weight, profile.tier_a_weight)

    return max(MIN_EFFECTIVE_WEIGHT, weight)


def _static_quality_row(
    stream: Sequence[tuple[r4.ExpandedOpportunity, r5.ManagedTrade]],
    *,
    profile: QualityProfile,
) -> dict[str, Any]:
    primary = tuple(
        (outcome.r_multiple - PRIMARY_STRESS)
        * _quality_weight(opportunity, profile)
        for opportunity, outcome in stream
    )
    metrics = fx._metrics(primary)
    return {
        "profile": profile.payload(),
        "primary": metrics,
    }


def _quality_rank(row: dict[str, Any]) -> tuple[Decimal, Decimal, Decimal]:
    p = row["primary"]
    return (
        Decimal(str(p["profit_factor"] or "0")),
        -Decimal(str(p["max_drawdown_r"])),
        Decimal(str(p["total_r"])),
    )


def _allocate_batch(
    requested: Sequence[Decimal],
    *,
    active_risk: Decimal,
    budget: Decimal,
) -> tuple[tuple[Decimal, ...], bool]:
    total = sum(requested, Decimal())
    remaining = max(Decimal(), budget - active_risk)
    if total <= remaining:
        return tuple(max(MIN_EFFECTIVE_WEIGHT, x) for x in requested), False
    if remaining <= 0:
        return tuple(MIN_EFFECTIVE_WEIGHT for _ in requested), True
    factor = remaining / total
    return (
        tuple(
            max(MIN_EFFECTIVE_WEIGHT, x * factor)
            for x in requested
        ),
        True,
    )


def _assign(
    stream: Sequence[tuple[r4.ExpandedOpportunity, r5.ManagedTrade]],
    *,
    quality: QualityProfile,
    risk: RiskProfile,
) -> tuple[tuple[r15.AssignedTrade, ...], dict[str, Any]]:
    equity = Decimal()
    history: deque[Decimal] = deque(
        [Decimal()],
        maxlen=risk.rolling_trades + 1,
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
    floor_overage_batches = 0
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

        dd_before = max(history) - equity
        requested: list[Decimal] = []
        tags: list[tuple[bool, bool, bool]] = []

        for opportunity, _outcome in batch:
            weight = _quality_weight(opportunity, quality)
            warn = hard = loss = False

            if dd_before >= risk.hard_dd_r:
                weight *= risk.hard_multiplier
                hard = True
            elif dd_before >= risk.warn_dd_r:
                weight *= risk.warn_multiplier
                warn = True

            if loss_streak >= 2:
                weight *= risk.loss_multiplier
                loss = True

            requested.append(max(MIN_EFFECTIVE_WEIGHT, weight))
            tags.append((warn, hard, loss))

        active_risk = sum((item.weight for item in active.values()), Decimal())
        weights, scaled = _allocate_batch(
            requested,
            active_risk=active_risk,
            budget=risk.portfolio_risk_budget_r,
        )
        budget_scaled_batches += int(scaled)

        if active_risk + sum(weights, Decimal()) > risk.portfolio_risk_budget_r:
            floor_overage_batches += 1

        for ((opportunity, outcome), weight, tag) in zip(
            batch,
            weights,
            tags,
            strict=True,
        ):
            warn, hard, loss = tag
            warn_allocations += int(warn)
            hard_allocations += int(hard)
            loss_allocations += int(loss)
            overlap_entries += int(bool(active))

            # Context is not used for R22 sizing; keep only structural metadata
            # required by the shared AssignedTrade carrier.
            context = r15.r10.Context(
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
                outcome.r_multiple - PRIMARY_STRESS
            ) * weight
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
        "budget_floor_overage_batches": floor_overage_batches,
        "max_concurrent_open_positions": max_concurrent,
        "max_committed_structural_risk_r": str(max_committed),
        "minimum_effective_weight": str(min(x.weight for x in assigned)),
        "maximum_effective_weight": str(max(x.weight for x in assigned)),
        "mean_effective_weight": str(
            sum((x.weight for x in assigned), Decimal()) / len(assigned)
        ),
        "warn_allocations": warn_allocations,
        "hard_allocations": hard_allocations,
        "loss_defense_allocations": loss_allocations,
    }


def _realized_row(
    stream: Sequence[tuple[r4.ExpandedOpportunity, r5.ManagedTrade]],
    *,
    quality: QualityProfile,
    risk: RiskProfile,
) -> tuple[dict[str, Any], tuple[r15.AssignedTrade, ...]]:
    assigned, diagnostics = _assign(
        stream,
        quality=quality,
        risk=risk,
    )
    primary = fx._metrics(
        r15._realized_values(assigned, stress=PRIMARY_STRESS)
    )
    secondary = fx._metrics(
        r15._realized_values(assigned, stress=SECONDARY_STRESS)
    )
    realized_pass = (
        FIVE_YEAR_MIN_TRADES <= len(assigned) <= FIVE_YEAR_MAX_TRADES
        and Decimal(str(primary["profit_factor"] or "0")) >= PRIMARY_PF_GOAL
        and Decimal(str(primary["max_drawdown_r"])) <= PRIMARY_DD_GOAL
        and Decimal(str(secondary["profit_factor"] or "0")) >= SECONDARY_PF_GOAL
        and Decimal(str(secondary["max_drawdown_r"])) <= SECONDARY_DD_GOAL
    )
    return (
        {
            "quality": quality.payload(),
            "risk": risk.payload(),
            "sample": len(assigned),
            "primary": primary,
            "secondary": secondary,
            "diagnostics": diagnostics,
            "realized_gate_pass": realized_pass,
        },
        assigned,
    )


def _realized_rank(row: dict[str, Any]) -> tuple[int, Decimal, Decimal, Decimal]:
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
        _indexed,
        opened_by_symbol,
        provenance,
    ) = r15._build_five_year_stream(roots=roots)

    quality_rows = [
        _static_quality_row(stream, profile=profile)
        for profile in _quality_profiles()
    ]
    quality_rows.sort(key=_quality_rank, reverse=True)

    selected_quality_ids = {
        row["profile"]["profile_id"]
        for row in quality_rows[:8]
    }
    selected_quality = tuple(
        profile
        for profile in _quality_profiles()
        if profile.profile_id in selected_quality_ids
    )

    search: list[
        tuple[dict[str, Any], tuple[r15.AssignedTrade, ...]]
    ] = []
    for quality, risk in itertools.product(
        selected_quality,
        _risk_profiles(),
    ):
        search.append(
            _realized_row(
                stream,
                quality=quality,
                risk=risk,
            )
        )
    search.sort(key=lambda item: _realized_rank(item[0]), reverse=True)

    finalists: list[dict[str, Any]] = []
    for row, assigned in search[:32]:
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
            and int(row["diagnostics"]["suppressed_trade_count"]) == 0
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
        "quality_profile_count": len(quality_rows),
        "selected_quality_profile_count": len(selected_quality),
        "risk_profile_count": len(_risk_profiles()),
        "realized_combination_count": len(search),
        "mtm_finalist_count": len(finalists),
        "goal_candidate_count": len(goals),
        "stable_feature_contract": {
            "tier_a": "fvg|h4_entry_latency=121-180m",
            "tier_b": "fvg|cisd_latency=4-7",
            "tier_c": "fvg|risk_fraction=0.15-0.30%",
            "all_other_trades_remain_executable": True,
        },
        "contract": {
            "five_year_density": [
                FIVE_YEAR_MIN_TRADES,
                FIVE_YEAR_MAX_TRADES,
            ],
            "primary_pf_minimum": str(PRIMARY_PF_GOAL),
            "primary_portfolio_dd_max_r": str(PRIMARY_DD_GOAL),
            "secondary_pf_minimum": str(SECONDARY_PF_GOAL),
            "secondary_portfolio_dd_max_r": str(SECONDARY_DD_GOAL),
            "signal_suppression_allowed": False,
            "global_single_position_rule": False,
        },
        "best": finalists[0],
        "top_10": finalists[:10],
        "goal_candidates": goals[:10],
        "quality_screen_top_8": quality_rows[:8],
        "provenance": provenance,
        "governance": {
            "development_only": True,
            "r17_cross_window_stable_features_only": True,
            "pre_entry_quality_only": True,
            "future_outcome_used_for_new_signal_risk": False,
            "same_timestamp_batch_allocation": True,
            "all_trades_preserved": True,
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
                "realized_combination_count": report["realized_combination_count"],
                "goal_candidate_count": report["goal_candidate_count"],
                "best": report["best"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
