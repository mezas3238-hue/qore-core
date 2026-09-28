"""Emit the canonical T01..T20 calibration matrix without holdout access."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from qore.infrastructure.cibo_ce2i_calibration_matrix import (
    CIBO_T01_T20_CALIBRATION_MATRIX,
)
from qore.infrastructure.cibo_ce2i_holdout_registry import (
    PREREGISTERED_USD60_HOLDOUT,
    candidate_is_burn_clean_for_all_lineages,
)


def build_report() -> dict[str, object]:
    rows = [
        {
            "tool": row.tool_code,
            "implemented": row.implemented,
            "calibrated": row.calibrated,
            "calibration_source": list(row.calibration_source),
            "calibration_type": row.calibration_type.value,
            "provider_economics_required": row.provider_economics_required,
            "fail_closed_status": row.fail_closed,
            "oos_ready": row.oos_ready,
            "certification_ready": row.certification_ready,
            "state": row.classification.value,
            "blocker": list(row.blocker),
        }
        for row in CIBO_T01_T20_CALIBRATION_MATRIX
    ]
    canonical = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()
    holdout = PREREGISTERED_USD60_HOLDOUT
    return {
        "schema": "qore.cibo.ce2i.calibration_matrix.v1",
        "matrix_sha256": hashlib.sha256(canonical).hexdigest(),
        "rows": rows,
        "anti_leakage": {
            "holdout_candidate_id": holdout.candidate_id,
            "holdout_status": holdout.status.value,
            "holdout_outcomes_inspected_at_selection": (
                holdout.outcome_data_inspected_at_selection
            ),
            "holdout_source_validation_complete": holdout.source_validation_complete,
            "holdout_burn_clean_for_all_lineages": (
                candidate_is_burn_clean_for_all_lineages(holdout)
            ),
            "holdout_used_for_calibration": False,
            "target_aware_calibration": False,
        },
        "governance": {
            "engineering_green_is_economic_certification": False,
            "fail_closed_is_capability_certification": False,
            "historical_usd_fabricated": False,
            "fresh_holdout_unsealed": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = build_report()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
