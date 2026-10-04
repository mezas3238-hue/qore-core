#!/usr/bin/env python3
"""WP-10 prospective Autonomous Scientific Laboratory cycle from MC-27."""

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

IDENTITY = "QORE_SHARED_WP10_PROSPECTIVE_AUTONOMOUS_LAB_CYCLE_001"


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain an object")
    return payload


def _ev(stage: ScientificLabStage, ref: str) -> ScientificLabEvidence:
    return ScientificLabEvidence(
        stage=stage,
        evidence_ref=ref,
        passed=True,
        consumed_window="MC27_PROSPECTIVE_PRE_OOS",
        fresh_evidence=False,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mc27", type=Path, required=True)
    parser.add_argument("--preregistration", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    mc27 = _load(args.mc27)
    prereg = _load(args.preregistration)

    if mc27.get("status") != "MC27_PROSPECTIVE_RESEARCH_PRIORITY_PREREGISTERED":
        raise AssertionError("MC27 prospective priority evidence missing")
    if mc27.get("prospective_priority_generated") is not True:
        raise AssertionError("MC27 did not generate its own priority")
    if mc27.get("future_experiment_preregistered") is not True:
        raise AssertionError("MC27 future experiment was not preregistered")
    if mc27.get("future_oos_opened") is not False:
        raise AssertionError("MC27 future OOS was opened too early")
    if mc27.get("future_oos_improvement_demonstrated") is not False:
        raise AssertionError("MC27 future improvement cannot exist yet")

    if prereg.get("status") != "PREREGISTERED_BEFORE_FUTURE_RESEARCH_OOS":
        raise AssertionError("MC27 preregistration is not frozen")
    future = prereg.get("future_research_oos")
    if not isinstance(future, dict):
        raise AssertionError("future research OOS definition missing")
    if future.get("opened") is not False:
        raise AssertionError("future research OOS must remain unopened")
    if future.get("protected_certification_holdout") is not False:
        raise AssertionError("WP10 prospective OOS must not be final holdout")
    if future.get("start_inclusive") != "2026-10-01T00:00:00+00:00":
        raise AssertionError("prospective OOS start drifted")
    if future.get("end_exclusive") != "2026-11-01T00:00:00+00:00":
        raise AssertionError("prospective OOS end drifted")

    record = ScientificExperimentRecord(
        experiment_id="MC27_MC18_COUNTERFACTUAL_CALIBRATION_PROSPECTIVE",
        version="001",
        evidence=(
            _ev(
                ScientificLabStage.OBSERVATION,
                "artifact:11119876541:MC18_UNCALIBRATED_COUNTERFACTUALS",
            ),
            _ev(
                ScientificLabStage.PREDICTION_ERROR_OR_ANOMALY,
                "artifact:11126275619:MC28_INFORMATION_GAPS",
            ),
            _ev(
                ScientificLabStage.RESEARCH_QUESTION,
                "mc27:counterfactual_probability_calibration",
            ),
            _ev(
                ScientificLabStage.COMPETING_HYPOTHESES,
                "hypotheses:RAW_MC18_VS_FROZEN_CALIBRATED_MC18",
            ),
            _ev(
                ScientificLabStage.EXPERIMENT_DESIGN,
                "prereg:QORE_SHARED_MC27_PROSPECTIVE_META_COGNITIVE_RESEARCH_CYCLE_001",
            ),
            _ev(
                ScientificLabStage.LEAKAGE_CONTROLS,
                "mc27:no-future-fit:no-retune:no-protected-holdout",
            ),
        ),
        outcome=ScientificResearchOutcome.RESEARCH_ONLY,
        rollback_ref="MC18_COUNTERFACTUAL_WORLD_FOUNDATION",
    )

    correct_boundary = (
        record.last_stage is ScientificLabStage.LEAKAGE_CONTROLS
        and record.outcome is ScientificResearchOutcome.RESEARCH_ONLY
        and record.promotion_authority is False
        and record.certified_runtime_mutation is False
    )
    payload = {
        "identity": IDENTITY,
        "status": (
            "WP10_PROSPECTIVE_LAB_PRE_OOS_CHAIN_PASS"
            if correct_boundary
            else "WP10_PROSPECTIVE_LAB_PRE_OOS_CHAIN_FAIL"
        ),
        "experiment_id": record.experiment_id,
        "stage_count": len(record.evidence),
        "highest_stage": record.last_stage.name,
        "outcome": record.outcome.value,
        "prospective_mc27_priority_bound": True,
        "future_research_oos_start": future["start_inclusive"],
        "future_research_oos_end": future["end_exclusive"],
        "future_research_oos_opened": False,
        "protected_certification_holdout": False,
        "historical_test_stage_complete": False,
        "falsification_stage_complete": False,
        "replication_stage_complete": False,
        "holdout_stage_complete": False,
        "stress_stage_complete": False,
        "shadow_stage_complete": False,
        "knowledge_decision_stage_complete": False,
        "certified_runtime_mutation": record.certified_runtime_mutation,
        "promotion_authority": record.promotion_authority,
        "wp10_completed_and_proven": False,
        "next_gate": "EXECUTE_FROZEN_FUTURE_RESEARCH_OOS_AFTER_2026_10_01",
        "master_ledger_mutated": False,
        "protected_certification_holdout_opened": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
