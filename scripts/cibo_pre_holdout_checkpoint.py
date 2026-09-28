"""Emit the CIBO pre-holdout calibration checkpoint without reading 2017H1."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from qore.infrastructure.cibo_ce2i_calibration_matrix import (
    CIBO_T01_T20_CALIBRATION_MATRIX,
)
from qore.infrastructure.cibo_ce2i_holdout_registry import (
    CONFIRMED_CIBO_BURNS,
    PREREGISTERED_USD60_HOLDOUT,
)
from qore.infrastructure.cibo_ce2i_pre_holdout_gate import (
    calibration_matrix_sha256,
    evaluate_pre_holdout_readiness,
)
from qore.infrastructure.cibo_ce2i_usd60_six_month_certification import (
    FROZEN_CIBO_USD60_SIX_MONTH_PROTOCOL,
)


def _protocol_payload() -> dict[str, object]:
    protocol = FROZEN_CIBO_USD60_SIX_MONTH_PROTOCOL
    return {
        "protocol_id": protocol.protocol_id,
        "initial_capital_usd": str(protocol.initial_capital_usd),
        "duration_months": protocol.duration_months,
        "trader_lineage_count": protocol.trader_lineage_count,
        "tool_codes": list(protocol.tool_codes),
        "economic_target_usd": (
            None
            if protocol.economic_target_usd is None
            else str(protocol.economic_target_usd)
        ),
        "milestones_usd": [str(item) for item in protocol.milestones_usd],
        "baselines": list(protocol.baselines),
        "stress_scenarios": list(protocol.stress_scenarios),
        "monte_carlo_dimensions": list(protocol.monte_carlo_dimensions),
        "failure_scenarios": list(protocol.failure_scenarios),
        "mandatory_metrics": list(protocol.mandatory_metrics),
        "frozen_at": protocol.frozen_at.isoformat(),
    }


def _sha256(value: object) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode()
    return hashlib.sha256(raw).hexdigest()


def build_report(
    *,
    git_sha: str,
    provider_economics_status: str,
) -> dict[str, Any]:
    if not git_sha:
        raise ValueError("git sha is required")
    if not provider_economics_status:
        raise ValueError("provider economics status is required")

    readiness = evaluate_pre_holdout_readiness(
        provider_economics_frozen=False,
        calibration_freeze_manifest_sealed=False,
    )
    matrix = [
        {
            "tool": row.tool_code,
            "implemented": row.implemented,
            "calibrated": row.calibrated,
            "source": list(row.calibration_source),
            "calibration_type": row.calibration_type.value,
            "provider_economics_required": row.provider_economics_required,
            "fail_closed": row.fail_closed,
            "oos_ready": row.oos_ready,
            "certification_ready": row.certification_ready,
            "classification": row.classification.value,
            "blocker": list(row.blocker),
            "calibration_artifact_sha256": row.calibration_artifact_sha256,
        }
        for row in CIBO_T01_T20_CALIBRATION_MATRIX
    ]
    protocol = _protocol_payload()
    burns = [
        {
            "burn_id": item.burn_id,
            "lineage": None if item.lineage is None else item.lineage.value,
            "start_at": item.start_at.isoformat(),
            "end_exclusive_at": item.end_exclusive_at.isoformat(),
            "reason": item.reason,
            "evidence_ref": item.evidence_ref,
        }
        for item in CONFIRMED_CIBO_BURNS
    ]
    candidate = PREREGISTERED_USD60_HOLDOUT

    return {
        "schema": "qore.cibo.pre_holdout_checkpoint.v1",
        "identity": "CIBO_PRE_HOLDOUT_FREEZE_CHECKPOINT",
        "status": "PRE_HOLDOUT_NOT_READY",
        "git_sha": git_sha,
        "config_sha256": _sha256(protocol),
        "calibration_matrix_sha256": calibration_matrix_sha256(),
        "burn_registry_sha256": _sha256(burns),
        "provider_economics_status": provider_economics_status,
        "ready_to_unseal_2017h1": False,
        "pre_holdout_blockers": list(readiness.blockers),
        "protocol": protocol,
        "t01_t20_matrix": matrix,
        "burned_datasets": burns,
        "fresh_holdout": {
            "candidate_id": candidate.candidate_id,
            "start_at": candidate.start_at.isoformat(),
            "end_exclusive_at": candidate.end_exclusive_at.isoformat(),
            "status": candidate.status.value,
            "selection_rule": candidate.selection_rule,
            "outcomes_inspected": False,
            "market_data_read_by_this_checkpoint": False,
            "untouched_confirmation": True,
        },
        "governance": {
            "holdout_used_for_calibration": False,
            "target_aware": False,
            "vps_used": False,
            "live_mutation_performed": False,
            "economic_certification_claimed": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--git-sha", required=True)
    parser.add_argument(
        "--provider-economics-status",
        default="PENDING_PROVIDER_ECONOMICS_EVIDENCE",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report = build_report(
        git_sha=args.git_sha,
        provider_economics_status=args.provider_economics_status,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
