"""Run Phase 19G normalized-capacity collision and marginal-value stress.

The policy is the same non-optimized 1-NCU mechanics baseline used by Phase 19D.
Capacity scenarios are predeclared from scarce (2-5 NCU around observed maximum
concurrency) to loose references (10, 100 NCU).

TRAIN and VALIDATION are replayed separately with the frozen Phase-19B split.
This is descriptive counterfactual normalized-capacity research only.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_ce2i_phase19_capital_collision import (
    Phase19CapitalCollisionEvidence,
    compare_phase19_marginal_capacity,
    measure_phase19_capital_collisions,
)
from qore.infrastructure.cibo_ce2i_phase19_normalized_capital import (
    Phase19CapitalNumeraireContract,
    Phase19NormalizedReplayTrade,
    replay_phase19_normalized_capital,
)
from qore.infrastructure.cibo_ce2i_phase19_portfolio_replay import (
    PHASE19_REQUIRED_TRADERS,
)
from cibo_phase19_integrated_chronology_replay import (
    EXPECTED_COMMON_END,
    EXPECTED_COMMON_ROWS,
    EXPECTED_COMMON_START,
    EXPECTED_SOURCE_ROWS,
    SOURCE_SPECS,
    _jsonl,
)
from cibo_phase19_normalized_capital_mechanics import (
    _parse_trade,
)
from cibo_phase19_temporal_stability_validation import (
    EXPECTED_SPLIT_AT,
    EXPECTED_TRAINING_OPPORTUNITIES,
    EXPECTED_VALIDATION_OPPORTUNITIES,
)

CAPACITY_SCENARIOS_NCU = (
    Decimal("2"),
    Decimal("3"),
    Decimal("4"),
    Decimal("5"),
    Decimal("10"),
    Decimal("100"),
)
CONTRACT_ID = "CIBO_PHASE19C_STRUCTURAL_STOP_NCU_V1"


def _collision_pair_counts(
    evidence: Phase19CapitalCollisionEvidence,
) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for collision in evidence.collisions:
        for blocker in collision.blockers:
            if blocker.trader_id is collision.trader_id:
                continue
            left, right = sorted(
                (blocker.trader_id.value, collision.trader_id.value)
            )
            counts[f"{left}|{right}"] += 1
    return dict(sorted(counts.items()))


def _run_segment(
    *,
    trades: tuple[Phase19NormalizedReplayTrade, ...],
    contract: Phase19CapitalNumeraireContract,
) -> dict[str, Any]:
    scenarios: list[dict[str, Any]] = []
    replay_by_capacity = {}

    for capacity in CAPACITY_SCENARIOS_NCU:
        replay = replay_phase19_normalized_capital(
            contract=contract,
            initial_capital_ncu=capacity,
            trades=trades,
        )
        replay_by_capacity[capacity] = replay
        collision = measure_phase19_capital_collisions(
            replay=replay,
            trades=trades,
        )
        scenarios.append(
            {
                "initial_capital_ncu": str(capacity),
                "accepted_opportunities": replay.accepted_opportunities,
                "rejected_opportunities": replay.rejected_opportunities,
                "rejected_insufficient_capacity": (
                    collision.rejected_insufficient_capacity
                ),
                "rejected_insolvent_capital": (
                    collision.rejected_insolvent_capital
                ),
                "capital_collisions": len(collision.collisions),
                "depletion_only_rejections": (
                    collision.depletion_only_rejections
                ),
                "cross_trader_collision_blocker_links": sum(
                    item.cross_trader_blockers
                    for item in collision.collisions
                ),
                "cross_trader_collision_pair_counts": (
                    _collision_pair_counts(collision)
                ),
                "ending_capital_ncu": str(replay.ending_capital_ncu),
                "total_realized_delta_ncu": str(
                    replay.total_realized_delta_ncu
                ),
                "max_drawdown_ncu": str(replay.max_drawdown_ncu),
                "peak_reserved_risk_ncu": str(
                    replay.peak_reserved_risk_ncu
                ),
                "risk_capacity_minutes_ncu": str(
                    replay.risk_capacity_minutes_ncu
                ),
                "capacity_breach_observed": (
                    replay.capacity_breach_observed
                ),
            }
        )

    marginal: list[dict[str, Any]] = []
    for lower, higher in zip(
        CAPACITY_SCENARIOS_NCU,
        CAPACITY_SCENARIOS_NCU[1:],
        strict=True,
    ):
        evidence = compare_phase19_marginal_capacity(
            contract=contract,
            lower_initial_capital_ncu=lower,
            higher_initial_capital_ncu=higher,
            trades=trades,
        )
        marginal.append(
            {
                "lower_initial_capital_ncu": str(lower),
                "higher_initial_capital_ncu": str(higher),
                "capacity_step_ncu": str(evidence.capacity_step_ncu),
                "lower_total_realized_delta_ncu": str(
                    evidence.lower_total_realized_delta_ncu
                ),
                "higher_total_realized_delta_ncu": str(
                    evidence.higher_total_realized_delta_ncu
                ),
                "marginal_realized_delta_ncu": str(
                    evidence.marginal_realized_delta_ncu
                ),
                "marginal_realized_delta_per_ncu": str(
                    evidence.marginal_realized_delta_per_ncu
                ),
                "rejection_reduction": evidence.rejection_reduction,
                "additional_accepted_opportunities": (
                    evidence.additional_accepted_opportunities
                ),
                "ex_post_only": evidence.ex_post_only,
                "causal_forecast": evidence.causal_forecast,
                "true_optimization_dual_claimed": (
                    evidence.true_optimization_dual_claimed
                ),
            }
        )

    return {
        "opportunities": len(trades),
        "capacity_scenarios": scenarios,
        "marginal_capacity_evidence": marginal,
    }


def validate(
    *,
    paths: dict[str, Path],
    output_path: Path,
) -> dict[str, Any]:
    if set(paths) != set(SOURCE_SPECS):
        raise ValueError("Phase 19G source set drift")

    parsed: dict[
        TraderLineage,
        list[Phase19NormalizedReplayTrade],
    ] = {}
    for key, spec in SOURCE_SPECS.items():
        rows = _jsonl(paths[key])
        if len(rows) != EXPECTED_SOURCE_ROWS[spec.trader_id]:
            raise ValueError(
                f"{spec.trader_id.value} Phase-19G source row-count drift"
            )
        parsed[spec.trader_id] = [
            _parse_trade(row, spec=spec) for row in rows
        ]

    if set(parsed) != set(PHASE19_REQUIRED_TRADERS):
        raise ValueError("Phase 19G Trader population drift")

    common_start = datetime.fromisoformat(EXPECTED_COMMON_START)
    common_end = datetime.fromisoformat(EXPECTED_COMMON_END)
    common = tuple(
        item
        for trader in PHASE19_REQUIRED_TRADERS
        for item in parsed[trader]
        if item.opportunity.entry_at >= common_start
        and item.opportunity.exit_at <= common_end
    )
    for trader in PHASE19_REQUIRED_TRADERS:
        count = sum(
            item.opportunity.trader_id is trader for item in common
        )
        if count != EXPECTED_COMMON_ROWS[trader]:
            raise ValueError(
                f"{trader.value} Phase-19G common-window row drift"
            )

    split_at = datetime.fromisoformat(EXPECTED_SPLIT_AT)
    training = tuple(
        item for item in common if item.opportunity.exit_at <= split_at
    )
    validation = tuple(
        item for item in common if item.opportunity.entry_at >= split_at
    )
    crossing = len(common) - len(training) - len(validation)
    if len(training) != EXPECTED_TRAINING_OPPORTUNITIES:
        raise ValueError("Phase 19G training row-count drift")
    if len(validation) != EXPECTED_VALIDATION_OPPORTUNITIES:
        raise ValueError("Phase 19G validation row-count drift")
    if crossing != 0:
        raise ValueError("Phase 19G unexpected split-crossing opportunity")

    contract = Phase19CapitalNumeraireContract(contract_id=CONTRACT_ID)
    report: dict[str, Any] = {
        "schema": "qore.cibo.phase19.capital_collision_stress.v1",
        "identity": "CIBO_PHASE19G_CAPITAL_COLLISION_STRESS_V1",
        "status": "TRAIN_VALIDATION_CAPACITY_COLLISION_MEASURED_DESCRIPTIVE_ONLY",
        "common_window": {
            "start": common_start.isoformat(),
            "split_at": split_at.isoformat(),
            "end": common_end.isoformat(),
            "segment_capital_reset": True,
        },
        "policy": {
            "policy_id": "PHASE19D_EQUAL_ONE_NCU_MECHANICS_BASELINE_V1",
            "optimized": False,
            "training_used_to_choose_policy": False,
            "risk_budget_per_opportunity_ncu": "1",
            "capacity_scenarios_ncu": [
                str(item) for item in CAPACITY_SCENARIOS_NCU
            ],
            "capacity_grid_outcome_tuned": False,
            "grid_basis": (
                "2-5 NCU brackets observed max concurrency 5; "
                "10 and 100 NCU are loose-capacity references"
            ),
        },
        "training": _run_segment(
            trades=training,
            contract=contract,
        ),
        "validation": _run_segment(
            trades=validation,
            contract=contract,
        ),
        "governance": {
            "normalized_counterfactual_capacity_stress": True,
            "historical_usd_claimed": False,
            "historical_provider_economics_claimed": False,
            "raw_cross_trader_r_aggregation": False,
            "marginal_evidence_ex_post_only": True,
            "true_optimization_shadow_price_claimed": False,
            "allocator_policy_certified": False,
            "allocation_authority": False,
            "risk_authority": False,
            "execution_authority": False,
            "demo_execution_authorized": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "merge_authorized": False,
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    for key in SOURCE_SPECS:
        parser.add_argument(f"--{key}", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    paths = {key: getattr(args, key) for key in SOURCE_SPECS}
    print(json.dumps(validate(paths=paths, output_path=args.output), sort_keys=True))


if __name__ == "__main__":
    main()
