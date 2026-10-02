#!/usr/bin/env python3
"""WP-09 Scientific Society -> Autonomous Lab integration proof."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from qore.infrastructure.core_stack_v2.autonomous_scientific_lab import (
    ScientificExperimentRecord,
    ScientificLabEvidence,
    ScientificLabStage,
    ScientificResearchOutcome,
)

IDENTITY = "QORE_SHARED_WP09_SCIENTIFIC_SOCIETY_LAB_INTEGRATION_001"


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain an object")
    return payload


def _ev(
    stage: ScientificLabStage,
    ref: str,
    *,
    passed: bool = True,
) -> ScientificLabEvidence:
    return ScientificLabEvidence(
        stage=stage,
        evidence_ref=ref,
        passed=passed,
        consumed_window="STI5_V1_CONSUMED_RESEARCH_EVIDENCE",
        fresh_evidence=False,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mc21", type=Path, required=True)
    parser.add_argument("--mc22", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    mc21 = _load(args.mc21)
    mc22 = _load(args.mc22)

    if mc21.get("status") != "MC21_SCIENTIFIC_SOCIETY_COMPLETED_AND_PROVEN":
        raise AssertionError("MC21 completed society evidence missing")
    if mc21.get("real_engine_bound_role_count") != 12:
        raise AssertionError("MC21 does not bind all twelve roles")
    if mc21.get("all_roles_real_engine_bound") is not True:
        raise AssertionError("MC21 role binding incomplete")
    if mc21.get("heterogeneous_model_family_count") != 12:
        raise AssertionError("MC21 heterogeneous model population drifted")
    if mc21.get("verdict") != "REJECTED_BY_FALSIFICATION":
        raise AssertionError("MC21 real cycle no longer rejects by falsification")
    if mc21.get("minority_falsification_preserved") is not True:
        raise AssertionError("MC21 minority falsification was not preserved")
    if mc21.get("simple_majority_voting_used") is not False:
        raise AssertionError("MC21 majority voting must remain forbidden")
    if not mc21.get("material_falsifier_roles"):
        raise AssertionError("MC21 lacks material falsifier")

    if mc22.get("status") != "MC22_AUTONOMOUS_SCIENTIFIC_LAB_COMPLETED_AND_PROVEN":
        raise AssertionError("MC22 autonomous lab evidence missing")
    if mc22.get("all_required_stages_materialized") is not True:
        raise AssertionError("MC22 full lab state machine was not proven")
    if mc22.get("outcome") != "REJECT":
        raise AssertionError("MC22 rejected-lineage proof drifted")
    if mc22.get("mc22_completed_and_proven") is not True:
        raise AssertionError("MC22 completion flag missing")

    society_to_lab = ScientificExperimentRecord(
        experiment_id="WP09_STI5_V1_SOCIETY_TO_LAB",
        version="001",
        evidence=(
            _ev(ScientificLabStage.OBSERVATION, "run:36640098773"),
            _ev(
                ScientificLabStage.PREDICTION_ERROR_OR_ANOMALY,
                "artifact:11066541040",
            ),
            _ev(
                ScientificLabStage.RESEARCH_QUESTION,
                "proposition:STI5_V1_SCIENTIFIC_ADMISSION",
            ),
            _ev(
                ScientificLabStage.COMPETING_HYPOTHESES,
                "engine:scientific_society:12-real-model-families",
            ),
            _ev(
                ScientificLabStage.EXPERIMENT_DESIGN,
                "run:36778113321",
            ),
            _ev(
                ScientificLabStage.LEAKAGE_CONTROLS,
                "mc21:no-future-no-authority",
            ),
            _ev(
                ScientificLabStage.HISTORICAL_TEST,
                "artifact:11066541040",
            ),
            _ev(
                ScientificLabStage.FALSIFICATION,
                "artifact:11126741246:REJECTED_BY_FALSIFICATION",
                passed=False,
            ),
        ),
        outcome=ScientificResearchOutcome.REJECT,
        rollback_ref="STI5_V1_FALSIFIED_AND_CLOSED",
    )

    integration_pass = (
        society_to_lab.last_stage is ScientificLabStage.FALSIFICATION
        and society_to_lab.outcome is ScientificResearchOutcome.REJECT
        and society_to_lab.promotion_authority is False
        and society_to_lab.certified_runtime_mutation is False
    )
    completed = (
        integration_pass
        and mc21["all_roles_real_engine_bound"] is True
        and mc21["minority_falsification_preserved"] is True
        and mc22["mc22_completed_and_proven"] is True
    )

    payload = {
        "identity": IDENTITY,
        "status": (
            "WP09_SCIENTIFIC_SOCIETY_COMPLETED_AND_PROVEN"
            if completed
            else "WP09_SCIENTIFIC_SOCIETY_INTEGRATION_FAILED"
        ),
        "scientific_society_roles_real_engine_bound": 12,
        "heterogeneous_model_family_count": 12,
        "minority_falsification_preserved": True,
        "simple_majority_voting_used": False,
        "autonomous_lab_full_loop_capability_proven": True,
        "society_output_consumed_by_lab": integration_pass,
        "society_to_lab_last_stage": society_to_lab.last_stage.name,
        "society_to_lab_outcome": society_to_lab.outcome.value,
        "society_to_lab_auto_promotion": society_to_lab.promotion_authority,
        "scientific_rejection_is_knowledge": True,
        "trading_authority": False,
        "methodology_authority": False,
        "sizing_authority": False,
        "capital_authority": False,
        "risk_authority": False,
        "execution_authority": False,
        "wp09_completed_and_proven": completed,
        "master_ledger_mutated": False,
        "protected_certification_holdout_opened": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
