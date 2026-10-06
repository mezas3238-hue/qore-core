#!/usr/bin/env python3
"""Prepare a compact causal CIBO capital ledger for GitHub Trader Lab.

The heavy source-manifest/walk-forward reconstruction is paid only when its
upstream causal dependencies change. Outcomes remain research-only and are
copied solely as future settlement records; they are never used to decide the
same opportunity.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping

from cibo_build_walk_forward_expectation_manifest import build_walk_forward_manifest
from qore.infrastructure.cibo_maximum_capability_frontier import (
    cognitive_multiplier_cap,
)
from qore.infrastructure.cibo_single_account_manifest_economics import (
    manifest_row_to_ceiling_opportunity_evidence,
)
from qore.infrastructure.cibo_single_account_manifest_settlement import (
    manifest_row_to_shadow_outcome_observation,
)


def _dt(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp must be string")
    result = datetime.fromisoformat(value)
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return result


def _mapping(value: object, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be mapping")
    return value


def _regime(row: Mapping[str, Any]) -> dict[str, object]:
    ce2i = _mapping(row.get("ce2i_predecision_evidence"), "ce2i")
    receipts = ce2i.get("runtime_receipts")
    if not isinstance(receipts, (list, tuple)):
        raise ValueError("CE2I runtime receipts missing")
    matches = [
        item
        for item in receipts
        if isinstance(item, Mapping)
        and item.get("engine_name") == "select_ce2i_tools_for_regime"
    ]
    if len(matches) != 1:
        raise ValueError("expected exact CE2I regime receipt")
    payload = _mapping(matches[0].get("input_payload"), "regime input")
    return {
        "liquidity": str(payload["liquidity"]),
        "volatility": str(payload["volatility"]),
        "correlation": str(payload["correlation"]),
        "provider_condition": str(payload["provider_condition"]),
        "position_path_adverse": bool(payload.get("position_path_adverse", False)),
        "evidence_stale": bool(payload.get("evidence_stale", False)),
    }


def _compact_row(row: dict[str, Any]) -> dict[str, object]:
    evidence = manifest_row_to_ceiling_opportunity_evidence(row)
    shadow_outcome = manifest_row_to_shadow_outcome_observation(row)
    opportunity = evidence.opportunity
    expectation = _mapping(row.get("expectation"), "expectation")
    outcome = _mapping(
        row.get("settlement_outcome_research_only"),
        "settlement_outcome_research_only",
    )
    context = dict(opportunity.decision_context)
    cognitive = _mapping(
        row.get("cognitive_orchestration"),
        "cognitive_orchestration",
    )
    frontier_cap, frontier_codes, frontier_reason = cognitive_multiplier_cap(
        cognitive
    )
    minimum_volume = opportunity.minimum_volume * Decimal(
        opportunity.minimum_execution_steps
    )
    return {
        "decision_epoch_id": str(row["decision_epoch_id"]),
        "decision_at": str(row["market_decision_at"]),
        "signal_fingerprint": opportunity.signal_fingerprint,
        "trader_id": opportunity.trader_id.value,
        "qore_symbol": opportunity.qore_symbol,
        "minimum_volume": format(minimum_volume, "f"),
        "volume_step": format(opportunity.volume_step, "f"),
        "maximum_volume": format(opportunity.maximum_volume, "f"),
        "stop_loss_per_volume": format(opportunity.stop_loss_per_volume, "f"),
        "margin_per_volume": format(opportunity.margin_per_volume, "f"),
        "provider_cost_per_volume_usd": format(
            evidence.provider_cost_per_volume_usd,
            "f",
        ),
        "expected_net_value_usd": format(evidence.expected_net_value_usd, "f"),
        "expected_capital_minutes": format(
            evidence.expected_capital_minutes,
            "f",
        ),
        "uncertainty_penalty_usd": format(
            evidence.uncertainty_penalty_usd,
            "f",
        ),
        "expectation_basis": evidence.expectation_basis.value,
        "context_allowed": evidence.context_allowed,
        "provider_viable": evidence.provider_viable,
        "capital_source_eligible": evidence.capital_source_eligible,
        "walk_forward_observation_count": int(
            expectation.get("walk_forward_observation_count", 0)
        ),
        "walk_forward_maturity": str(
            expectation.get("walk_forward_maturity", "COLD_START")
        ),
        "walk_forward_mature": bool(
            expectation.get(
                "walk_forward_mature_for_capital_consideration",
                False,
            )
        ),
        "walk_forward_maturity_fraction": str(
            expectation.get("walk_forward_maturity_fraction", "0")
        ),
        "walk_forward_positive_block_count": int(
            expectation.get("walk_forward_positive_block_count", 0)
        ),
        "walk_forward_nonpositive_block_count": int(
            expectation.get("walk_forward_nonpositive_block_count", 0)
        ),
        "walk_forward_dispersion_r": str(
            expectation.get("walk_forward_block_dispersion_r", "0")
        ),
        "walk_forward_mad_r": str(
            expectation.get("walk_forward_median_absolute_deviation_r", "0")
        ),
        "walk_forward_expected_structural_r": str(
            expectation.get("walk_forward_expected_structural_r", "0")
        ),
        "walk_forward_block_means_r": [
            str(value)
            for value in expectation.get("walk_forward_block_means_r", [])
        ],
        "cibo_expected_net_utility_usd": context.get(
            "cibo_expected_net_utility_usd",
            "0",
        ),
        "maximum_frontier_cap": frontier_cap,
        "maximum_frontier_consumed_codes": list(frontier_codes),
        "maximum_frontier_reason": frontier_reason,
        "regime": _regime(row),
        "settlement": {
            "entry_at": str(outcome["entry_at"]),
            "exit_at": str(outcome["exit_at"]),
            "gross_structural_outcome_r": format(
                shadow_outcome.gross_structural_outcome_r,
                "f",
            ),
            "not_available_to_predecision": bool(
                outcome.get("not_available_to_predecision")
            ),
            "used_for_decision": bool(outcome.get("used_for_decision")),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--cutoff",
        default="2020-04-30T23:59:59+00:00",
    )
    args = parser.parse_args()

    source = json.loads(args.evidence.read_text(encoding="utf-8"))
    transformed, receipt = build_walk_forward_manifest(source)
    cutoff = _dt(args.cutoff)
    rows = [
        _compact_row(row)
        for row in transformed["opportunities"]
        if _dt(row["market_decision_at"]) <= cutoff
    ]
    if not rows:
        raise ValueError("CIBO Trader Lab prepared ledger is empty")
    if any(
        row["settlement"]["used_for_decision"]
        or not row["settlement"]["not_available_to_predecision"]
        for row in rows
    ):
        raise ValueError("CIBO prepared ledger outcome governance violated")

    payload = {
        "schema": "qore.github-trader-lab.cibo-capital-prepared.v1",
        "initial_capital_usd": "60",
        "cutoff": args.cutoff,
        "source_manifest_sha256": receipt["source_manifest_sha256"],
        "walk_forward_manifest_sha256": receipt["manifest_sha256"],
        "opportunity_count": len(rows),
        "decision_epoch_count": len(
            {str(row["decision_epoch_id"]) for row in rows}
        ),
        "rows": rows,
        "governance": {
            "burned_repair_window": True,
            "outcomes_predecision": False,
            "fresh_holdout_opened": False,
            "certification_claimed": False,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, separators=(",", ":"), sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "prepared": True,
                "opportunities": payload["opportunity_count"],
                "epochs": payload["decision_epoch_count"],
                "cutoff": payload["cutoff"],
            },
            sort_keys=True,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
