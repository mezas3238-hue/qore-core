"""Assemble a REAL CF-11 experiment closure from verified earlier Actions evidence.

Run only after the already-shipped source-checker has authenticated the original
GitHub Actions run, artifact zip SHA and prereg ancestry in this same job.
"""
from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.qore_eia_cf11_closed_experiment_binding_v1 import (
    bind_closed_eia_to_cf11,
)
from qore.infrastructure.trader_lab.qore_eia_research_science_handoff_v1 import (
    build_handoff_receipt,
)


def _read_dict(path: Path) -> dict[str, Any]:
    value: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("EXPECTED_DICTIONARY")
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--original-result", type=Path, required=True)
    parser.add_argument("--verified-science", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    original = _read_dict(args.original_result)
    verified = _read_dict(args.verified_science)
    if (
        verified.get("github_artifact_digest_verified") is not True
        or verified.get("prereg_ancestor_verified") is not True
        or verified.get("scientific_closure_only_not_eligibility") is not True
    ):
        raise ValueError("GITHUB_SOURCE_PROVENANCE_NOT_VERIFIED")
    receipt = build_handoff_receipt(original)
    normalized_json = json.loads(json.dumps(receipt.to_json(), sort_keys=True))
    payload_receipt = {
        name: value
        for name, value in verified.items()
        if name not in {
            "github_artifact_digest_verified",
            "prereg_ancestor_verified",
            "scientific_closure_only_not_eligibility",
        }
    }
    if normalized_json != payload_receipt:
        raise ValueError("VERIFIED_GITHUB_RECEIPT_DIFFERS_FROM_ORIGINAL_RESULT")
    result = bind_closed_eia_to_cf11(
        original, receipt, verified_source=True, as_of=datetime.now(UTC)
    )
    record = result.to_json()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print("CF11_REAL_RESEARCH_PLAN", record["plan_code"])
    print("CF11_STAGE", record["stage"])
    print("CF11_EVIDENCE", record["evidence_status"])
    print("SCIENTIFIC_DECISION", record["scientific_decision"])
    print("TRADER_LAB_STATUS", record["trader_lab_state"])
    print("NO_AUTHORITY_NO_RISK_NO_LIVE_NO_TRADABLE_PNL")


if __name__ == "__main__":
    main()
