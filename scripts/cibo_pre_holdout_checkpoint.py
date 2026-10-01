"""Emit the CIBO Phase22 V2 pre-holdout checkpoint without fresh execution."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from qore.infrastructure.cibo_ce2i_calibration_matrix import (
    CIBO_T01_T20_CALIBRATION_MATRIX,
)
from qore.infrastructure.cibo_ce2i_calibration_terminal_evidence import (
    ACTIVE_CERTIFICATION_TOOLS,
    QUALIFICATION_FAILED_TOOLS,
    STRUCTURALLY_DISABLED_TOOLS,
    build_terminal_calibration_readiness,
)
from qore.infrastructure.cibo_ce2i_holdout_registry import (
    ACTIVE_USD60_HOLDOUT_CANDIDATE,
    CONFIRMED_CIBO_BURNS,
)
from qore.infrastructure.cibo_ce2i_pre_holdout_freeze_v2 import (
    evaluate_phase22_v2_pre_holdout_readiness,
)
from qore.infrastructure.cibo_ce2i_provider_core_freeze_receipt import (
    PROVIDER_CORE_FREEZE_RECEIPT,
    build_provider_core_component_freeze,
    provider_core_freeze_receipt_payload,
)
from qore.infrastructure.cibo_ce2i_provider_economics_evidence import (
    CURRENT_CTRADER_DEMO_PROVIDER_ECONOMICS,
)
from qore.infrastructure.cibo_ce2i_shadow_certification_receipts import (
    PHASE20_SHADOW_ARTIFACT_DIGEST,
    SHADOW_CERTIFICATION_RECEIPTS,
    shadow_receipt_payload,
)
from qore.infrastructure.cibo_ce2i_usd60_six_month_certification import (
    FROZEN_CIBO_USD60_SIX_MONTH_PROTOCOL,
)
from qore.infrastructure.cibo_phase22_holdout_v2_source_receipt import (
    phase22_v2_holdout_source_receipt_payload,
    phase22_v2_holdout_source_receipt_sha256,
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
) -> dict[str, Any]:
    if not git_sha:
        raise ValueError("git sha is required")

    provider = CURRENT_CTRADER_DEMO_PROVIDER_ECONOMICS
    provider_status = (
        "CURRENT_DEMO_TERMS_READY_"
        "HISTORICAL_EXACT_FALSE_SLIPPAGE_FALSE"
    )

    receipts = SHADOW_CERTIFICATION_RECEIPTS
    provider_receipt = PROVIDER_CORE_FREEZE_RECEIPT
    provider_freeze = build_provider_core_component_freeze()
    calibration = build_terminal_calibration_readiness()
    if calibration.calibration_manifest is None:
        raise RuntimeError("terminal calibration manifest was not sealed")
    readiness = evaluate_phase22_v2_pre_holdout_readiness()
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
    candidate = ACTIVE_USD60_HOLDOUT_CANDIDATE

    return {
        "schema": "qore.cibo.phase22.v2-pre-holdout-checkpoint.v1",
        "identity": "CIBO_PRE_HOLDOUT_FREEZE_CHECKPOINT",
        "status": readiness.state.value,
        "git_sha": git_sha,
        "config_sha256": _sha256(protocol),
        "calibration_matrix_sha256": _sha256(matrix),
        "burn_registry_sha256": _sha256(burns),
        "provider_economics_status": (
            "CORE_PRE_HOLDOUT_READY_PREDECLARED_STRESS_BOUND"
            if provider_receipt.core_pre_holdout_ready
            else provider_status
        ),
        "provider_core_freeze_receipt": provider_core_freeze_receipt_payload(),
        "provider_economics": {
            "workflow_run_id": provider.workflow_run_id,
            "artifact_id": provider.artifact_id,
            "artifact_sha256": provider.artifact_sha256,
            "source_git_sha": provider.source_git_sha,
            "observed_at": provider.observed_at,
            "provider_key": provider.provider_key,
            "symbols": list(provider.symbols),
            "provider_terms_ready": provider.provider_terms_ready,
            "slippage_empirically_calibrated": (
                provider.slippage_empirically_calibrated
            ),
            "historical_exact_claimed": provider.historical_exact_claimed,
            "execution_model_ready": provider.execution_model_ready,
            "broker_mutation_performed": provider.broker_mutation_performed,
            "holdout_outcomes_used": provider.holdout_outcomes_used,
            "target_aware": provider.target_aware,
        },
        "ready_to_unseal_v2": readiness.ready_to_unseal_v2,
        "phase22_v2_source_receipt_sha256": (
            phase22_v2_holdout_source_receipt_sha256()
        ),
        "phase22_v2_source_receipt": (
            phase22_v2_holdout_source_receipt_payload()
        ),
        "phase22_v2_pre_holdout": readiness.as_dict(),
        "phase20d_causal_tool_gate_passed": receipts.phase20_shadow_passed,
        "phase21_policy_freeze_sealed": receipts.phase21_policy_freeze_sealed,
        "shadow_certification_receipts": shadow_receipt_payload(),
        "terminal_calibration": {
            "manifest_fingerprint": calibration.calibration_manifest.fingerprint(),
            "active_certification_tools": list(ACTIVE_CERTIFICATION_TOOLS),
            "qualification_failed_tools": list(QUALIFICATION_FAILED_TOOLS),
            "structurally_disabled_tools": list(STRUCTURALLY_DISABLED_TOOLS),
            "historical_registry_rewritten": False,
        },
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
            "source_stage_outcomes_inspected": False,
            "source_stage_trader_logic_executed": False,
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
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report = build_report(
        git_sha=args.git_sha,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
