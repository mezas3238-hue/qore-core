"""VT08 Index R36 — causal market-side health overlay.

R35 proved that the source-complete 2,448-trade architecture is economically
strong and positive in all five exact 12-month blocks at -0.05R, while the
first block at -0.10R missed positivity by only 0.0556R.

R36 does not filter a year, market, side, POI, or signal. It keeps the frozen
R35/R34 hybrid baseline and adds one bounded causal confidence layer keyed by
(symbol, side). Confidence uses only PRIOR COMPLETED raw outcomes for that key.
The overlay may only reduce already-assigned R35 risk and every valid signal
retains at least the 0.005R floor. No calendar label is available to runtime.
"""

from __future__ import annotations

import argparse
import heapq
import itertools
import json
from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    vt08_index_concurrent_market_contract as contract,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r6_5y_failure_forensics as fx,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r15_concurrent_portfolio_validation as r15,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r31_source_complete_structural_concurrency as r31,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r34_hybrid_formation_poi_health as r34,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r35_five_year_temporal_contract as r35,
)

SCHEMA = "qore.trader_lab.vt08_index_r36_causal_market_side_health.v1"
IDENTITY = "VT08_INDEX_R36_CAUSAL_MARKET_SIDE_HEALTH_001"

PRIMARY_STRESS = Decimal("0.05")
SECONDARY_STRESS = Decimal("0.10")
PF_PRIMARY_MIN = Decimal("1.50")
PF_SECONDARY_MIN = Decimal("1.30")
PORTFOLIO_DD_MAX = Decimal("6")
MIN_EFFECTIVE_WEIGHT = Decimal("0.005")

BASE_OVERLAY = r34.PoiOverlayProfile(
    rolling_family_trades=10,
    min_observations=5,
    cold_multiplier=Decimal("0.50"),
    weak_multiplier=Decimal("0.50"),
    healthy_mean_threshold_r=Decimal("0.05"),
)


@dataclass(frozen=True, slots=True)
class MarketSideHealthProfile:
    rolling_group_trades: int
    min_observations: int
    cold_multiplier: Decimal
    weak_multiplier: Decimal
    healthy_mean_threshold_r: Decimal

    @property
    def profile_id(self) -> str:
        return (
            "MSH-"
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


def _profiles() -> tuple[MarketSideHealthProfile, ...]:
    return tuple(
        MarketSideHealthProfile(window, minimum, cold, weak, threshold)
        for window, minimum, cold, weak, threshold in itertools.product(
            (8, 16, 32),
            (4, 8),
            (Decimal("0.50"), Decimal("1.00")),
            (Decimal("0.25"), Decimal("0.50"), Decimal("0.75")),
            (Decimal("0.00"), Decimal("0.05")),
        )
        if minimum <= window
    )


def _group_key(item: r15.AssignedTrade) -> str:
    return f"{item.symbol}|{item.opportunity.signal.side.value}"


def _apply_market_side_health(
    baseline: tuple[r15.AssignedTrade, ...],
    *,
    profile: MarketSideHealthProfile,
) -> tuple[tuple[r15.AssignedTrade, ...], dict[str, Any]]:
    histories: dict[str, deque[Decimal]] = {}
    exit_heap: list[tuple[datetime, int, str, Decimal]] = []
    result: list[r15.AssignedTrade] = []
    state_counts = {"COLD": 0, "WEAK": 0, "HEALTHY": 0}
    cursor = 0
    reduced = 0
    unchanged = 0

    def history_for(key: str) -> deque[Decimal]:
        if key not in histories:
            histories[key] = deque(maxlen=profile.rolling_group_trades)
        return histories[key]

    def settle(until: datetime) -> None:
        while exit_heap and exit_heap[0][0] <= until:
            _exited_at, _trade_id, key, raw_value = heapq.heappop(exit_heap)
            history_for(key).append(raw_value)

    while cursor < len(baseline):
        batch_time = baseline[cursor].signal_at.astimezone(UTC)
        settle(batch_time)
        end = cursor + 1
        while end < len(baseline) and baseline[end].signal_at.astimezone(UTC) == batch_time:
            end += 1

        pending: list[tuple[r15.AssignedTrade, str, Decimal]] = []
        for item in baseline[cursor:end]:
            key = _group_key(item)
            multiplier, state = r34._health(
                tuple(history_for(key)),
                minimum=profile.min_observations,
                cold=profile.cold_multiplier,
                weak=profile.weak_multiplier,
                threshold=profile.healthy_mean_threshold_r,
            )
            state_counts[state] += 1
            weight = max(MIN_EFFECTIVE_WEIGHT, item.weight * multiplier)
            if weight > item.weight:
                raise ValueError("R36 overlay may never increase R35 risk")
            reduced += int(weight < item.weight)
            unchanged += int(weight == item.weight)
            result.append(
                r15.AssignedTrade(
                    trade_id=item.trade_id,
                    opportunity=item.opportunity,
                    outcome=item.outcome,
                    context=item.context,
                    weight=weight,
                )
            )
            pending.append(
                (
                    item,
                    key,
                    item.outcome.r_multiple - PRIMARY_STRESS,
                )
            )

        # Same-timestamp signals share the exact same pre-batch memory.
        for item, key, raw_value in pending:
            heapq.heappush(
                exit_heap,
                (item.exited_at.astimezone(UTC), item.trade_id, key, raw_value),
            )
        cursor = end

    settle(datetime.max.replace(tzinfo=UTC))
    if len(result) != len(baseline):
        raise ValueError("R36 changed source-complete trade count")

    base_by_id = {item.trade_id: item.weight for item in baseline}
    return tuple(result), {
        "assigned_trade_count": len(result),
        "suppressed_trade_count": 0,
        "risk_increase_count": sum(
            item.weight > base_by_id[item.trade_id] for item in result
        ),
        "risk_reduced_count": reduced,
        "risk_unchanged_count": unchanged,
        "state_counts": state_counts,
        "group_count": len(histories),
        "minimum_effective_weight": str(min(item.weight for item in result)),
        "maximum_effective_weight": str(max(item.weight for item in result)),
        "mean_effective_weight": str(
            sum((item.weight for item in result), Decimal()) / len(result)
        ),
    }


def _row(
    baseline: tuple[r15.AssignedTrade, ...],
    *,
    profile: MarketSideHealthProfile,
) -> tuple[dict[str, Any], tuple[r15.AssignedTrade, ...]]:
    assigned, diagnostics = _apply_market_side_health(
        baseline,
        profile=profile,
    )
    primary = fx._metrics(r15._realized_values(assigned, stress=PRIMARY_STRESS))
    secondary = fx._metrics(r15._realized_values(assigned, stress=SECONDARY_STRESS))
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
            "all_five_primary_blocks_positive": r35._all_blocks_positive(
                primary_blocks
            ),
            "all_five_secondary_blocks_positive": r35._all_blocks_positive(
                secondary_blocks
            ),
            "diagnostics": diagnostics,
        },
        assigned,
    )


def _rank(row: dict[str, Any]) -> tuple[int, int, Decimal, Decimal, Decimal]:
    temporal = (
        bool(row["all_five_primary_blocks_positive"])
        and bool(row["all_five_secondary_blocks_positive"])
    )
    primary = row["primary"]
    secondary = row["secondary"]
    economic = (
        Decimal(str(primary["profit_factor"] or "0")) >= PF_PRIMARY_MIN
        and Decimal(str(secondary["profit_factor"] or "0")) >= PF_SECONDARY_MIN
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
        raise ValueError(f"R36 density drift: {len(stream)}")

    baseline, baseline_diagnostics = r34._assign(
        stream,
        overlay=BASE_OVERLAY,
    )
    if len(baseline) != len(stream):
        raise ValueError("R36 baseline lost source-complete signals")

    raw_primary = r31._raw_metrics(stream, stress=PRIMARY_STRESS)
    raw_edge_pass = (
        Decimal(str(raw_primary["profit_factor"] or "0")) >= Decimal("1")
        and Decimal(str(raw_primary["total_r"])) > 0
    )

    search = [_row(baseline, profile=profile) for profile in _profiles()]
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
        diagnostics = row["diagnostics"]
        goal_pass = (
            raw_edge_pass
            and contract.validates_trade_count(years=5, sample=len(assigned))
            and Decimal(str(primary["profit_factor"] or "0")) >= PF_PRIMARY_MIN
            and Decimal(str(secondary["profit_factor"] or "0")) >= PF_SECONDARY_MIN
            and Decimal(primary_mtm["max_drawdown_r"]) <= PORTFOLIO_DD_MAX
            and Decimal(secondary_mtm["max_drawdown_r"]) <= PORTFOLIO_DD_MAX
            and bool(row["all_five_primary_blocks_positive"])
            and bool(row["all_five_secondary_blocks_positive"])
            and int(diagnostics["suppressed_trade_count"]) == 0
            and int(diagnostics["risk_increase_count"]) == 0
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
                    row["primary_conservative_mark_to_market"]["max_drawdown_r"]
                ),
                Decimal(
                    row["secondary_conservative_mark_to_market"]["max_drawdown_r"]
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
        "base_overlay": BASE_OVERLAY.payload(),
        "baseline_diagnostics": baseline_diagnostics,
        "raw_primary": raw_primary,
        "raw_edge_pass": raw_edge_pass,
        "goal_candidate_count": len(goals),
        "best": finalists[0],
        "top_10": finalists[:10],
        "goal_candidates": goals[:10],
        "temporal_contract": {
            "boundaries": [x.isoformat() for x in r35._annual_boundaries()],
            "full_year_block_count": 5,
            "calendar_year_used_for_runtime_decision": False,
        },
        "contract": {
            "five_year_trade_range": list(contract.FIVE_YEAR_TRADE_RANGE),
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
            "fresh_holdout_claim": False,
            "base_r35_hybrid_identity_preserved": True,
            "new_dimension": "causal_market_side_completed_trade_health",
            "calendar_or_year_feature_used_for_runtime": False,
            "health_uses_only_prior_completed_raw_outcomes": True,
            "same_timestamp_signals_share_pre_batch_memory": True,
            "future_outcome_used_for_current_risk": False,
            "overlay_can_increase_baseline_risk": False,
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
                "goal_candidate_count": report["goal_candidate_count"],
                "best": report["best"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
