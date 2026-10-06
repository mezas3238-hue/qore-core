#!/usr/bin/env python3
"""Extract the causally valid evaluation window for the frozen TRAIN prior.

The frozen Phase20 TRAIN prior did not exist before its training window ended.
This script creates a new resealed research manifest containing only decisions
at or after that evidence-availability timestamp. It never mutates the frozen
source manifest and never reads outcomes to decide inclusion.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_train_prior import (
    frozen_train_prior_available_at,
)
from qore.infrastructure.cibo_single_account_manifest_integrity import (
    reseal_single_account_manifest,
    validate_single_account_manifest_sha256,
)


def _dt(value: object, name: str) -> datetime:
    if not isinstance(value, str):
        raise CiboCapitalManagementError(f"{name} must be string")
    result = datetime.fromisoformat(value)
    if result.tzinfo is None or result.utcoffset() is None:
        raise CiboCapitalManagementError(
            f"{name} must be timezone-aware"
        )
    return result


def extract_causal_prior_window(
    manifest: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    source_sha = validate_single_account_manifest_sha256(manifest)
    rows = manifest.get("opportunities")
    if not isinstance(rows, list) or not rows:
        raise CiboCapitalManagementError(
            "causal prior window requires manifest opportunities"
        )

    available_at = frozen_train_prior_available_at()
    filtered = [
        json.loads(json.dumps(row))
        for row in rows
        if _dt(row.get("market_decision_at"), "market_decision_at")
        >= available_at
    ]
    if not filtered:
        raise CiboCapitalManagementError(
            "causal prior window contains no opportunities"
        )

    for row in filtered:
        expectation = row.get("expectation")
        if not isinstance(expectation, dict):
            raise CiboCapitalManagementError(
                "causal prior window expectation missing"
            )
        if expectation.get("basis") == "FROZEN_HISTORICAL_PRIOR":
            expectation["evidence_available_at"] = (
                available_at.isoformat()
            )

    trader_counts = Counter(str(row["trader_id"]) for row in filtered)
    original_traders = tuple(str(item) for item in manifest["trader_ids"])
    if set(trader_counts) != set(original_traders):
        raise CiboCapitalManagementError(
            "causal prior window must retain every Trader"
        )

    epochs = {
        (str(row["market_decision_at"]), str(row["decision_epoch_id"]))
        for row in filtered
    }
    filtered.sort(
        key=lambda row: (
            str(row["market_decision_at"]),
            str(row["decision_epoch_id"]),
            str(row["signal_fingerprint"]),
        )
    )

    era_groups: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in filtered:
        era_groups[int(row["era_index"])].append(row)
    eras = []
    for era_index, era_rows in sorted(era_groups.items()):
        decision_times = [
            _dt(row["market_decision_at"], "market_decision_at")
            for row in era_rows
        ]
        source_trace_sha256 = {
            str(row["source_trace_sha256"]) for row in era_rows
        }
        if len(source_trace_sha256) != 1:
            raise CiboCapitalManagementError(
                "causal prior window era source trace drift"
            )
        eras.append(
            {
                "era_index": era_index,
                "source_trace_sha256": next(iter(source_trace_sha256)),
                "opportunity_count": len(era_rows),
                "first_market_decision_at": min(
                    decision_times
                ).isoformat(),
                "last_market_decision_at": max(
                    decision_times
                ).isoformat(),
                "capital_reset_at_start": False,
            }
        )

    result = json.loads(json.dumps(manifest))
    result["schema"] = (
        "qore.cibo.single-account-causal-prior-window.v1"
    )
    result["opportunities"] = filtered
    result["opportunity_decision_count"] = len(filtered)
    result["decision_epoch_count"] = len(epochs)
    result["trader_opportunity_counts"] = {
        trader: trader_counts[trader] for trader in original_traders
    }
    result["eras"] = eras
    result["first_market_decision_at"] = filtered[0][
        "market_decision_at"
    ]
    result["last_market_decision_at"] = filtered[-1][
        "market_decision_at"
    ]
    result["causal_expectation_window"] = {
        "source_manifest_sha256": source_sha,
        "expectation_evidence_available_at": available_at.isoformat(),
        "included_opportunity_count": len(filtered),
        "excluded_preavailability_count": len(rows) - len(filtered),
        "inclusion_uses_outcome": False,
        "outcome_aware_tuning": False,
        "fresh_oos_claimed": False,
        "certification_claimed": False,
        "research_only": True,
    }
    governance = dict(result.get("governance", {}))
    governance["causal_expectation_chronology_enforced"] = True
    governance["excluded_preavailability_decisions"] = len(rows) - len(
        filtered
    )
    result["governance"] = governance

    resealed = reseal_single_account_manifest(result)
    receipt = {
        "source_manifest_sha256": source_sha,
        "manifest_sha256": resealed["manifest_sha256"],
        "available_at": available_at.isoformat(),
        "included_opportunity_count": len(filtered),
        "excluded_preavailability_count": len(rows) - len(filtered),
        "decision_epoch_count": len(epochs),
        "first_market_decision_at": resealed[
            "first_market_decision_at"
        ],
        "last_market_decision_at": resealed["last_market_decision_at"],
        "trader_opportunity_counts": resealed[
            "trader_opportunity_counts"
        ],
        "outcome_used_for_inclusion": False,
        "research_only": True,
    }
    return resealed, receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()

    source = json.loads(args.manifest.read_text(encoding="utf-8"))
    result, receipt = extract_causal_prior_window(source)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.receipt.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
