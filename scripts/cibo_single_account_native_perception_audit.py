#!/usr/bin/env python3
"""Fast causal perception audit for CIBO single-account Maximum Capability.

This audit never executes CF01-CF19 and never reads settlement outcomes. It
checks only whether each archived Trader opportunity carries enough causal
predecision perception to enter the native MAX intelligence gate.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_native_maximum_intelligence import (
    validate_native_maximum_perception,
)
from qore.infrastructure.cibo_single_account_manifest_integrity import (
    validate_single_account_manifest_sha256,
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _opportunity(row: dict[str, Any]) -> TraderOpportunityEnvelope:
    payload = row["trader_opportunity"]
    context = tuple(
        (str(item[0]), str(item[1]))
        for item in payload.get("decision_context", ())
    )
    return TraderOpportunityEnvelope(
        trader_id=TraderLineage(str(row["trader_id"])),
        signal_fingerprint=str(row["signal_fingerprint"]),
        qore_symbol=str(row["qore_symbol"]),
        provider_symbol=str(
            payload.get("provider_symbol") or row["qore_symbol"]
        ),
        side=str(payload["side"]),
        entry_type=str(payload.get("entry_type", "market")),
        intended_entry=_d(payload["intended_entry"]),
        stop_loss=_d(payload["stop_loss"]),
        take_profit=_d(payload["take_profit"]),
        stop_loss_per_volume=_d(payload["stop_loss_per_volume"]),
        margin_per_volume=_d(payload["margin_per_volume"]),
        volume_step=_d(payload["volume_step"]),
        minimum_volume=_d(payload["minimum_volume"]),
        maximum_volume=_d(payload["maximum_volume"]),
        minimum_execution_steps=int(
            payload.get("minimum_execution_steps", 1)
        ),
        decision_context=context,
    )


def audit(manifest: dict[str, Any]) -> dict[str, Any]:
    source_sha = validate_single_account_manifest_sha256(manifest)
    rows = manifest.get("opportunities")
    if not isinstance(rows, list) or not rows:
        raise CiboCapitalManagementError(
            "native perception audit requires manifest opportunities"
        )

    passed: Counter[str] = Counter()
    blocked: Counter[str] = Counter()
    context_counts: dict[str, set[int]] = defaultdict(set)
    complete_markers: Counter[str] = Counter()
    versions: dict[str, Counter[str]] = defaultdict(Counter)
    reasons: Counter[str] = Counter()
    examples: list[dict[str, str]] = []

    for row in rows:
        trader = str(row["trader_id"])
        opportunity = _opportunity(row)
        context = dict(opportunity.decision_context)
        context_counts[trader].add(len(context))
        if context.get("cibo_native_perception_complete") == "true":
            complete_markers[trader] += 1
        versions[trader][
            context.get("cibo_native_perception_version", "<none>")
        ] += 1
        try:
            validate_native_maximum_perception((opportunity,))
            passed[trader] += 1
        except Exception as error:
            blocked[trader] += 1
            message = str(error)
            reasons[message] += 1
            if len(examples) < 30:
                examples.append(
                    {
                        "trader_id": trader,
                        "signal_fingerprint": opportunity.signal_fingerprint,
                        "error": message,
                    }
                )

    return {
        "schema": "qore.cibo.single-account-native-perception-audit.v1",
        "source_manifest_sha256": source_sha,
        "decision_count": len(rows),
        "perception_pass_count": sum(passed.values()),
        "perception_blocked_count": sum(blocked.values()),
        "perception_surface_ready": sum(blocked.values()) == 0,
        "per_trader_pass": dict(sorted(passed.items())),
        "per_trader_blocked": dict(sorted(blocked.items())),
        "per_trader_context_key_counts": {
            trader: sorted(values)
            for trader, values in sorted(context_counts.items())
        },
        "per_trader_complete_marker_count": dict(
            sorted(complete_markers.items())
        ),
        "per_trader_versions": {
            trader: dict(sorted(counter.items()))
            for trader, counter in sorted(versions.items())
        },
        "failure_reasons": dict(reasons.most_common()),
        "failure_examples": examples,
        "governance": {
            "predecision_only": True,
            "settlement_outcome_read": False,
            "external_ai": False,
            "broker_mutation": False,
            "live": False,
            "production": False,
            "real_capital": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    result = audit(manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "decision_count": result["decision_count"],
                "perception_pass_count": result["perception_pass_count"],
                "perception_blocked_count": result[
                    "perception_blocked_count"
                ],
                "perception_surface_ready": result[
                    "perception_surface_ready"
                ],
                "per_trader_pass": result["per_trader_pass"],
                "per_trader_blocked": result["per_trader_blocked"],
                "per_trader_context_key_counts": result[
                    "per_trader_context_key_counts"
                ],
            },
            sort_keys=True,
        )
    )
    return 0 if result["perception_surface_ready"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
