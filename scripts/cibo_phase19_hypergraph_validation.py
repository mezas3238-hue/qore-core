"""Bind Phase 19H temporal/resource hypergraph to sealed seven-Trader evidence."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_ce2i_phase19_capital_collision import (
    measure_phase19_capital_collisions,
)
from qore.infrastructure.cibo_ce2i_phase19_hypergraph import (
    build_phase19_collision_hyperedges,
    build_phase19_temporal_hyperedges,
)
from qore.infrastructure.cibo_ce2i_phase19_normalized_capital import (
    Phase19CapitalNumeraireContract,
    Phase19NormalizedReplayTrade,
    replay_phase19_normalized_capital,
)
from qore.infrastructure.cibo_ce2i_phase19_portfolio_replay import (
    PHASE19_REQUIRED_TRADERS,
)
from cibo_phase19_capital_collision_stress import (
    CAPACITY_SCENARIOS_NCU,
    CONTRACT_ID,
)
from cibo_phase19_integrated_chronology_replay import (
    EXPECTED_COMMON_END,
    EXPECTED_COMMON_ROWS,
    EXPECTED_COMMON_START,
    EXPECTED_MAX_CONCURRENCY,
    EXPECTED_SOURCE_ROWS,
    SOURCE_SPECS,
    _jsonl,
)
from cibo_phase19_normalized_capital_mechanics import _parse_trade
from cibo_phase19_temporal_stability_validation import (
    EXPECTED_SPLIT_AT,
    EXPECTED_TRAINING_OPPORTUNITIES,
    EXPECTED_VALIDATION_OPPORTUNITIES,
)


def _temporal_summary(
    trades: tuple[Phase19NormalizedReplayTrade, ...],
) -> dict[str, Any]:
    edges = build_phase19_temporal_hyperedges(
        tuple(item.opportunity for item in trades)
    )
    cardinalities = Counter(len(item.members) for item in edges)
    trader_cardinalities = Counter(item.distinct_trader_count for item in edges)
    total_seconds = sum(
        (item.duration_seconds for item in edges),
        Decimal(0),
    )
    trader_sets = Counter(
        "|".join(
            sorted({member.trader_id.value for member in item.members})
        )
        for item in edges
    )
    max_cardinality = max(
        (len(item.members) for item in edges),
        default=0,
    )
    if max_cardinality > EXPECTED_MAX_CONCURRENCY:
        raise ValueError(
            "Phase 19H hypergraph exceeds chronology max concurrency"
        )
    return {
        "opportunities": len(trades),
        "hyperedges": len(edges),
        "max_cardinality": max_cardinality,
        "max_distinct_traders": max(
            (item.distinct_trader_count for item in edges),
            default=0,
        ),
        "total_hyperedge_seconds": str(total_seconds),
        "cardinality_distribution": {
            str(key): value for key, value in sorted(cardinalities.items())
        },
        "distinct_trader_distribution": {
            str(key): value
            for key, value in sorted(trader_cardinalities.items())
        },
        "trader_set_counts": dict(sorted(trader_sets.items())),
    }


def _collision_summary(
    *,
    trades: tuple[Phase19NormalizedReplayTrade, ...],
    contract: Phase19CapitalNumeraireContract,
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for capacity in CAPACITY_SCENARIOS_NCU:
        replay = replay_phase19_normalized_capital(
            contract=contract,
            initial_capital_ncu=capacity,
            trades=trades,
        )
        evidence = measure_phase19_capital_collisions(
            replay=replay,
            trades=trades,
        )
        edges = build_phase19_collision_hyperedges(
            evidence=evidence,
            trades=trades,
        )
        cardinalities = Counter(item.cardinality for item in edges)
        trader_sets = Counter(
            "|".join(
                sorted({member.trader_id.value for member in item.members})
            )
            for item in edges
        )
        output.append(
            {
                "initial_capital_ncu": str(capacity),
                "collision_hyperedges": len(edges),
                "max_collision_cardinality": max(
                    (item.cardinality for item in edges),
                    default=0,
                ),
                "cardinality_distribution": {
                    str(key): value
                    for key, value in sorted(cardinalities.items())
                },
                "trader_set_counts": dict(sorted(trader_sets.items())),
                "depletion_only_rejections": (
                    evidence.depletion_only_rejections
                ),
                "rejected_insolvent_capital": (
                    evidence.rejected_insolvent_capital
                ),
            }
        )
    return output


def validate(
    *,
    paths: dict[str, Path],
    output_path: Path,
) -> dict[str, Any]:
    if set(paths) != set(SOURCE_SPECS):
        raise ValueError("Phase 19H source set drift")

    parsed: dict[
        TraderLineage,
        list[Phase19NormalizedReplayTrade],
    ] = {}
    for key, spec in SOURCE_SPECS.items():
        rows = _jsonl(paths[key])
        if len(rows) != EXPECTED_SOURCE_ROWS[spec.trader_id]:
            raise ValueError(
                f"{spec.trader_id.value} Phase-19H source row-count drift"
            )
        parsed[spec.trader_id] = [
            _parse_trade(row, spec=spec) for row in rows
        ]

    if set(parsed) != set(PHASE19_REQUIRED_TRADERS):
        raise ValueError("Phase 19H Trader population drift")

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
                f"{trader.value} Phase-19H common-window row drift"
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
        raise ValueError("Phase 19H training row-count drift")
    if len(validation) != EXPECTED_VALIDATION_OPPORTUNITIES:
        raise ValueError("Phase 19H validation row-count drift")
    if crossing != 0:
        raise ValueError("Phase 19H unexpected split-crossing opportunity")

    contract = Phase19CapitalNumeraireContract(contract_id=CONTRACT_ID)
    report: dict[str, Any] = {
        "schema": "qore.cibo.phase19.opportunity_hypergraph.v1",
        "identity": "CIBO_PHASE19H_OPPORTUNITY_HYPERGRAPH_V1",
        "status": "TEMPORAL_AND_RESOURCE_HYPERGRAPH_MEASURED_DESCRIPTIVE_ONLY",
        "common_window": {
            "start": common_start.isoformat(),
            "split_at": split_at.isoformat(),
            "end": common_end.isoformat(),
        },
        "full_window_temporal": _temporal_summary(common),
        "training": {
            "temporal": _temporal_summary(training),
            "resource_collision_by_capacity": _collision_summary(
                trades=training,
                contract=contract,
            ),
        },
        "validation": {
            "temporal": _temporal_summary(validation),
            "resource_collision_by_capacity": _collision_summary(
                trades=validation,
                contract=contract,
            ),
        },
        "governance": {
            "pairwise_only_model_claimed": False,
            "harmful_dependence_claimed": False,
            "correlation_claimed": False,
            "sizing_penalty_authorized": False,
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
