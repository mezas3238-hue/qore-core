"""Topology-aware routing lab for Turtle Soup XAUUSD.

This lab asks a narrow causal question over already-consumed evidence: can CIBO
recover recent journey completion by routing the same Turtle Soup setups using
pre-entry raid/reclaim/risk topology, without adding a positive-score trade
filter or a learned abstention? Three pre-registered routing-state variants are
compared. No fresh holdout is consumed and no variant is promoted here.
"""
from __future__ import annotations

import json
import sys
from collections.abc import Callable
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import turtle_soup_xauusd_r3_cibo_journey as r3
from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_r3_cibo_journey_binding_repair as repair,
)

IDENTITY = "TURTLE_SOUP_XAUUSD_R4_TOPOLOGY_ROUTER_LAB_V1"
EVIDENCE_STATUS = "CONSUMED_CIBO_10Y_TOPOLOGY_ROUTING_RESEARCH_NOT_FRESH_HOLDOUT"


def _state_raid(setup: r3.Setup) -> tuple[str, ...]:
    c = setup.context
    return (
        c.timeframe,
        c.side,
        c.prior_body_alignment,
        c.cisd_progress_bucket,
        c.source_range_state_bucket,
        c.raid_depth_range_bucket,
    )


def _state_raid_reclaim(setup: r3.Setup) -> tuple[str, ...]:
    return (*_state_raid(setup), setup.context.reclaim_latency_bucket)


def _state_raid_reclaim_risk(setup: r3.Setup) -> tuple[str, ...]:
    return (*_state_raid_reclaim(setup), setup.context.protected_risk_range_bucket)


VARIANTS: dict[str, tuple[Callable[[r3.Setup], tuple[str, ...]], list[str]]] = {
    "R4A_RAID": (
        _state_raid,
        [
            "source_timeframe", "side", "prior_body_alignment", "cisd_progress_bucket",
            "source_range_state_bucket", "raid_depth_range_bucket",
        ],
    ),
    "R4B_RAID_RECLAIM": (
        _state_raid_reclaim,
        [
            "source_timeframe", "side", "prior_body_alignment", "cisd_progress_bucket",
            "source_range_state_bucket", "raid_depth_range_bucket", "reclaim_latency_bucket",
        ],
    ),
    "R4C_RAID_RECLAIM_RISK": (
        _state_raid_reclaim_risk,
        [
            "source_timeframe", "side", "prior_body_alignment", "cisd_progress_bucket",
            "source_range_state_bucket", "raid_depth_range_bucket", "reclaim_latency_bucket",
            "protected_risk_range_bucket",
        ],
    ),
}


def _trade_stat(rows: list[dict[str, Any]]) -> dict[str, Any]:
    values = [Decimal(str(row["primary_net_r"])) for row in rows]
    gross_profit = sum((v for v in values if v > 0), Decimal(0))
    gross_loss = -sum((v for v in values if v < 0), Decimal(0))
    return {
        "trades": len(rows),
        "total_primary_r": str(sum(values, Decimal(0))),
        "mean_primary_r": str(sum(values, Decimal(0)) / len(values)) if values else None,
        "profit_factor": None if gross_loss == 0 else str(gross_profit / gross_loss),
    }


def _run_variant(
    source_root: Path,
    target_root: Path,
    output: Path,
    name: str,
    state_fn: Callable[[r3.Setup], tuple[str, ...]],
    state_names: list[str],
) -> dict[str, Any]:
    variant_output = output / name.lower()
    original_state = r3._route_state
    original_loader = r3._load_targets
    original_identity = r3.IDENTITY
    try:
        r3._route_state = state_fn
        r3._load_targets = repair._load_targets_fail_closed
        r3.IDENTITY = f"TURTLE_SOUP_XAUUSD_{name}_TOPOLOGY_ROUTER"
        payload = r3.run(source_root, target_root, variant_output)
    finally:
        r3._route_state = original_state
        r3._load_targets = original_loader
        r3.IDENTITY = original_identity

    payload["router"]["routing_state"] = state_names
    payload["topology_lab"] = {
        "lab_identity": IDENTITY,
        "variant": name,
        "routing_state": state_names,
        "positive_score_trade_filter": False,
        "learned_abstention": False,
        "economic_mechanics_otherwise_changed": False,
    }
    (variant_output / "router.json").write_text(json.dumps(payload["router"], indent=2, sort_keys=True) + "\n")
    (variant_output / "report.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

    trades = json.loads((variant_output / "trades-full.json").read_text())
    recent = [row for row in trades if 2024 <= int(str(row["entry_at"])[:4]) <= 2026]
    recent_by_year = {
        str(year): _trade_stat([row for row in recent if int(str(row["entry_at"])[:4]) == year])
        for year in (2024, 2025, 2026)
    }
    return {
        "identity": payload["identity"],
        "routing_state": state_names,
        "executed_trades": payload["executed_trades"],
        "training_primary": payload["training_primary"],
        "validation_primary": payload["validation_primary"],
        "validation_stress_010r": payload["validation_stress_010r"],
        "full_primary": payload["full_primary"],
        "recent_2024_2026": _trade_stat(recent),
        "recent_by_year": recent_by_year,
        "full_by_side": payload["full_by_side"],
        "full_by_source_timeframe": payload["full_by_source_timeframe"],
        "full_by_target_route": payload["full_by_target_route"],
        "route_counts": payload["route_counts"],
        "abstentions": payload["abstentions"],
        "natural_no_fill": payload["natural_no_fill"],
    }


def run(source_root: Path, target_root: Path, output: Path) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    variants: dict[str, Any] = {}
    for name, (state_fn, state_names) in VARIANTS.items():
        variants[name] = _run_variant(source_root, target_root, output, name, state_fn, state_names)

    payload = {
        "schema": "qore.turtle_soup_xauusd_r4.topology_router_lab.v1",
        "identity": IDENTITY,
        "evidence_status": EVIDENCE_STATUS,
        "question": "Can richer causal topology improve CIBO routing without learned trade rejection?",
        "variants": variants,
        "governance": {
            "fresh_holdout": False,
            "validation_block_used_for_fit": False,
            "positive_score_trade_filter": False,
            "learned_abstention": False,
            "automatic_promotion_allowed": False,
            "demo_eligible": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }
    (output / "topology-router-lab.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return payload


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit("usage: module SOURCE_ROOT TARGET_ROOT OUTPUT_DIR")
    print(json.dumps(run(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])), sort_keys=True))


if __name__ == "__main__":
    main()
