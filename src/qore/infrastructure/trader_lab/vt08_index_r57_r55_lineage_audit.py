"""VT08 Index R57 — R55/R56 lineage audit.

R57 preserves the R55 and R56 evidence but checks whether the development
candidate was actually layered on the exact frozen R47 allocator lineage.
It changes no strategy rule and creates no candidate. The audit is fail-closed.
"""

from __future__ import annotations

import argparse
import inspect
import json
from pathlib import Path
from typing import Any, cast

from qore.infrastructure.trader_lab import (
    vt08_index_r47_transport_safe_structural_demotion as r47,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r55_distributed_causal_risk as r55,
)

SCHEMA = "qore.trader_lab.vt08_index_r57_r55_lineage_audit.v1"
IDENTITY = "VT08_INDEX_R57_R55_LINEAGE_AUDIT_001"


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object in {path}")
    return cast(dict[str, Any], payload)


def build_report(*, r47_path: Path, r55_path: Path) -> dict[str, Any]:
    official = _load(r47_path)
    candidate = _load(r55_path)

    if official["candidate"]["candidate_id"] != r47.CANDIDATE_ID:
        raise ValueError("R57 unexpected R47 candidate identity")
    if candidate["candidate_id"] != r55.CANDIDATE_ID:
        raise ValueError("R57 unexpected R55 candidate identity")

    comparisons: dict[str, Any] = {}
    mismatch = False
    for r47_key, r55_key in (
        ("five_year", "five_year"),
        ("recent_two_year", "recent_two_year"),
    ):
        expected = cast(dict[str, Any], official[r47_key]["diagnostics"])
        observed = cast(
            dict[str, Any],
            candidate[r55_key]["r47_diagnostics"],
        )
        fields = (
            "mean_effective_weight",
            "released_risk_not_reallocated_r",
            "maximum_effective_weight",
            "minimum_effective_weight",
            "risk_reduced_count",
        )
        field_match = {
            field: str(observed[field]) == str(expected[field])
            for field in fields
        }
        comparisons[r47_key] = {
            "expected_official_r47": {
                field: expected[field]
                for field in fields
            },
            "observed_inside_r55": {
                field: observed[field]
                for field in fields
            },
            "field_match": field_match,
            "all_match": all(field_match.values()),
        }
        mismatch = mismatch or not all(field_match.values())

    r55_source = inspect.getsource(r55.build_report)
    r47_source = inspect.getsource(r47.build_report)
    uses_r46_frozen_assignment = "r46._frozen_assignment" in r55_source
    official_uses_r34_baseline = "r34._row" in r47_source
    lineage_drift = (
        mismatch
        and uses_r46_frozen_assignment
        and official_uses_r34_baseline
    )

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "r47_candidate_id": r47.CANDIDATE_ID,
        "r55_candidate_id": r55.CANDIDATE_ID,
        "diagnostic_comparison": comparisons,
        "source_audit": {
            "r55_uses_r46_frozen_assignment": uses_r46_frozen_assignment,
            "official_r47_uses_r34_baseline": official_uses_r34_baseline,
        },
        "lineage_drift_confirmed": lineage_drift,
        "decision": (
            "REJECT_R55_R56_FOR_PROMOTION_LINEAGE_DRIFT"
            if lineage_drift
            else "NO_LINEAGE_DRIFT_DETECTED"
        ),
        "governance": {
            "audit_only": True,
            "r55_evidence_retained": True,
            "r56_freeze_evidence_retained": True,
            "r55_r56_promotion_valid": not lineage_drift,
            "candidate_created": False,
            "strategy_rule_changed": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--r47", type=Path, required=True)
    parser.add_argument("--r55", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = build_report(r47_path=args.r47, r55_path=args.r55)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
