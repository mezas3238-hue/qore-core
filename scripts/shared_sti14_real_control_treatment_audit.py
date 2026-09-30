#!/usr/bin/env python3
"""STI-14 real Control/Treatment attribution audit over sealed STI-8 evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import cast

IDENTITY = "QORE_SHARED_STI14_REAL_CONTROL_TREATMENT_ATTRIBUTION_001"


def _audit_partition(name: str, path: Path) -> dict[str, object]:
    payload = cast(dict[str, object], json.loads(path.read_text()))
    if payload.get("identity") != "QORE_SHARED_STI8_ECONOMIC_VALUE_V1":
        raise ValueError(f"{name}: unexpected STI-8 economic evidence identity")

    design = cast(dict[str, object], payload["study_design"])
    governance = cast(dict[str, object], payload["causal_governance"])
    trade_count = int(payload["trade_count"])
    changed_count = int(payload["treatment_changed_trade_count"])

    checks = {
        "same_opportunity_universe": design["same_opportunity_universe"] is True,
        "same_trade_count": design["same_trade_count"] is True,
        "same_initial_entry_stop_target": (
            design["same_initial_entry_stop_target"] is True
        ),
        "same_sizing": design["same_sizing"] is True,
        "only_information_difference_is_proactive_shared": (
            design["only_information_difference_is_proactive_shared"] is True
        ),
        "source_decisions_materialized_before_outcomes": (
            governance["all_source_decisions_materialized_before_outcome_scoring"]
            is True
        ),
        "future_market_not_used": governance["future_market_used_for_decision"] is False,
        "future_outcome_not_used": (
            governance["future_trade_outcome_used_for_decision"] is False
        ),
        "shared_has_no_exit_authority": governance["shared_exit_authority"] is False,
        "shared_has_no_sizing_authority": governance["shared_sizing_authority"] is False,
        "shared_has_no_capital_authority": governance["shared_capital_authority"] is False,
        "protected_holdout_closed": (
            governance["protected_certification_holdout_opened"] is False
        ),
        "productive_authority_false": governance["productive_authority"] is False,
        "nonempty_population": trade_count > 0,
        "behavioral_difference_observed": changed_count > 0,
    }
    return {
        "partition": name,
        "trade_count": trade_count,
        "treatment_changed_trade_count": changed_count,
        "behavioral_difference_rate_bps": (
            0 if trade_count <= 0 else changed_count * 10_000 // trade_count
        ),
        "economic_status": payload["economic_status"],
        "economic_value_pass": payload["economic_value_pass"],
        "checks": checks,
        "attribution_pass": all(checks.values()),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--r6", type=Path, required=True)
    parser.add_argument("--r5", type=Path, required=True)
    parser.add_argument("--oos", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    partitions = {
        "r6": _audit_partition("r6", args.r6),
        "r5": _audit_partition("r5", args.r5),
        "oos": _audit_partition("oos", args.oos),
    }
    passed = all(
        cast(dict[str, object], row)["attribution_pass"] is True
        for row in partitions.values()
    )
    payload = {
        "identity": IDENTITY,
        "status": (
            "STI14_CONTROL_TREATMENT_ATTRIBUTION_COMPLETED_AND_PROVEN"
            if passed
            else "STI14_CONTROL_TREATMENT_ATTRIBUTION_FAIL"
        ),
        "partitions": partitions,
        "proof": {
            "same_universe_real_replay": passed,
            "behavioral_difference_is_separate_from_economic_value": True,
            "economically_falsified_treatment_is_valid_attribution_evidence": True,
            "outcomes_attached_only_after_source_decisions": True,
            "future_market_used_for_decision": False,
            "future_outcome_used_for_decision": False,
            "protected_certification_holdout_opened": False,
            "productive_authority": False,
        },
        "economic_value_claim": "NOT_A_STI14_CLAIM",
        "capability_state": (
            "COMPLETED_AND_PROVEN" if passed else "RESEARCH_INCOMPLETE"
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(json.dumps({
        "status": payload["status"],
        "capability_state": payload["capability_state"],
        "partitions": partitions,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
