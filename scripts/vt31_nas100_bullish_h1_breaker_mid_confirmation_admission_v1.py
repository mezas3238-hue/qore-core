"""VT31 NAS100 bullish-H1 Breaker MID-confirmation admission frontier V1.

Consumed-evidence development only.

Fixed base:
    VT31_AB_COMP007_RAPID_BREAKER_UNION_SURVIVOR

Only degree of freedom:
- abstain Breaker SHORT when prior-day, cash-open and H1 are all bullish AND
  the pre-existing confirmation-latency bucket is MID_6_10M.

The 6-10 minute bucket pre-existed this hypothesis. No new threshold is added.

No outcome, fold/date identity, sizing, leverage, compounding, portfolio or
capital state can influence action.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import cast

import vt31_nas100_adverse_journey_cognitive_exit_frontier_v1 as adverse
import vt31_nas100_bullish_h1_breaker_conflict_admission_v1 as broad
import vt31_nas100_comp007_residual_dd_forensics_v1 as comp007

SCHEMA = (
    "qore.vt31.nas100.bullish_h1_breaker_mid_confirmation_admission.v1"
)
COMPARATOR_ID = "VT31_AB_COMP007_RAPID_BREAKER_UNION_SURVIVOR"
VARIANTS = (
    "COMP007_CONTROL",
    "COMP007_PLUS_BULLISH_H1_BREAKER_SHORT_MID_CONFIRMATION_CONFLICT",
)


def _mid_confirmation_conflict(row: dict[str, object]) -> bool:
    if not broad._conflict(row):
        return False
    context = cast(dict[str, object], row.get("entry_context", {}))
    return (
        adverse._confirmation_latency_state(
            context.get("confirmation_latency_minutes")
        )
        == "MID_6_10M"
    )


def replay(evidence_path: Path) -> dict[str, object]:
    structural_rows, comparator = comp007._build_union_rows(evidence_path)
    candidate = [
        row for row in comparator if not _mid_confirmation_conflict(row)
    ]

    reports = {
        "COMP007_CONTROL": broad._report(
            structural_count=len(structural_rows),
            comparator=comparator,
            rows=comparator,
        ),
        (
            "COMP007_PLUS_BULLISH_H1_BREAKER_SHORT_"
            "MID_CONFIRMATION_CONFLICT"
        ): broad._report(
            structural_count=len(structural_rows),
            comparator=comparator,
            rows=candidate,
        ),
    }

    return {
        "schema": SCHEMA,
        "market": "NAS100",
        "comparator_id": COMPARATOR_ID,
        "variants": reports,
        "governance": {
            "consumed_evidence_only": True,
            "same_position_logic_all_variants": True,
            "only_admission_degree_of_freedom": True,
            "conflict_entry_time_only": True,
            "confirmation_latency_bucket_preexisting": True,
            "confirmation_latency_bucket": "MID_6_10M",
            "new_numeric_threshold_added": False,
            "outcome_used_for_action": False,
            "fold_identity_used_for_action": False,
            "date_identity_used_for_action": False,
            "position_sizing_used": False,
            "dynamic_sizing_used": False,
            "leverage_used": False,
            "compounding_used": False,
            "capital_weighting_used": False,
            "absolute_volume_used": False,
            "fresh_holdout_opened": False,
            "policy_promoted": False,
            "candidate_frozen": False,
            "candidate_certified": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    payload = replay(args.evidence)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
