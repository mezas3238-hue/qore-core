"""Build deterministic source-first intake ledger from verified CF-11 science.

No market data, no strategy execution, no LIVE, no OOS opening.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.qore_research_zero_budget_intake_v1 import (
    ResearchIntakeError,
    build_source_first_queue,
    register_unfrozen_proposal,
)

PROPOSALS_SCHEMA = "qore.research.zero-budget.proposals.v1"
PROPOSAL_FIELDS = frozenset({
    "code", "question_code", "data_requirement_code", "research_root_count",
})


def apply_proposals(ledger: Any, manifest: dict[str, Any]) -> Any:
    if (
        not isinstance(manifest, dict)
        or set(manifest) != {"schema", "proposals"}
        or manifest["schema"] != PROPOSALS_SCHEMA
        or not isinstance(manifest["proposals"], list)
        or len(manifest["proposals"]) > 20
    ):
        raise ResearchIntakeError("INVALID_OR_OVERSIZED_PROPOSAL_MANIFEST")
    for entry in manifest["proposals"]:
        if not isinstance(entry, dict) or set(entry) != PROPOSAL_FIELDS:
            raise ResearchIntakeError("INVALID_PROPOSAL_FIELDS_OR_OUTCOME_ATTACHED")
        ledger = register_unfrozen_proposal(ledger, **entry)
    return ledger


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verified-cf11-plan", type=Path, required=True)
    parser.add_argument("--proposals", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    cf11: dict[str, Any] = json.loads(
        args.verified_cf11_plan.read_text(encoding="utf-8")
    )
    manifest: dict[str, Any] = json.loads(args.proposals.read_text(encoding="utf-8"))
    ledger = build_source_first_queue(cf11)
    ledger = apply_proposals(ledger, manifest)
    out = ledger.to_json()
    if out["spent_usd"] != 0 or out["economic_replay_performed"]:
        raise ResearchIntakeError("UNAUTHORIZED_SPEND_OR_ECONOMIC_REPLAY")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    for item in out["entries"]:
        print(
            "RESEARCH_QUEUE",
            item["code"],
            item["status"],
            item["next_action"],
            "runnable=" + str(item["experiment_runnable"]),
        )
    print("QUEUE_SHA256", out["ledger_sha256"])
    print("SOURCE_FIRST_BUDGET_ZERO_HOLDOUT_SEALED_NO_RISK_NO_DEMO")


if __name__ == "__main__":
    main()
