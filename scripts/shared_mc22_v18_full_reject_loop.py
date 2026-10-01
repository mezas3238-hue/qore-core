#!/usr/bin/env python3
"""MC-22 full autonomous scientific-lab loop bound to real V18 rejection."""

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
    conservative_lab_outcome,
)

IDENTITY = "QORE_SHARED_MC22_V18_FULL_REJECT_LOOP_001"


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain an object")
    return payload


def _evidence(
    stage: ScientificLabStage,
    ref: str,
    passed: bool,
    window: str,
) -> ScientificLabEvidence:
    return ScientificLabEvidence(
        stage=stage,
        evidence_ref=ref,
        passed=passed,
        consumed_window=window,
        fresh_evidence=False,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--v18", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    v18 = _load(args.v18)
    if v18.get("identity") != (
        "QORE_SHARED_AUTONOMOUS_INCREMENTAL_DEFENSE_ECONOMIC_SHADOW_V18"
    ):
        raise AssertionError("unexpected V18 lineage identity")
    if v18.get("consumed_frontier_pass") is not False:
        raise AssertionError("V18 rejection evidence drifted")
    if v18.get("fresh_holdout_opened") is not False:
        raise AssertionError("V18 must not be treated as fresh holdout")
    governance = v18.get("governance")
    if not isinstance(governance, dict):
        raise AssertionError("V18 governance missing")
    for key in (
        "runtime_actuation",
        "live_authorized",
        "production_authorized",
        "real_capital_authorized",
        "merge_authorized",
        "sizing_used",
        "risk_weighting_used",
        "broker_execution_authority",
    ):
        if governance.get(key) is not False:
            raise AssertionError(f"V18 authority invariant violated: {key}")

    windows = v18.get("windows")
    if not isinstance(windows, dict):
        raise AssertionError("V18 windows missing")
    required = {"five_year", "recent_two_year", "r66_consumed_failed_holdout"}
    if set(windows) != required:
        raise AssertionError("V18 window set drifted")
    pass_map = {key: bool(windows[key]["pass_window"]) for key in sorted(required)}
    if pass_map["five_year"] is not False:
        raise AssertionError("V18 five-year falsification disappeared")
    if pass_map["recent_two_year"] is not False:
        raise AssertionError("V18 recent-two-year falsification disappeared")
    if pass_map["r66_consumed_failed_holdout"] is not True:
        raise AssertionError("V18 consumed failed-holdout diagnostic drifted")

    stages = (
        _evidence(
            ScientificLabStage.OBSERVATION,
            "run:36142389500",
            True,
            "V16_CONSUMED_FRONTIER",
        ),
        _evidence(
            ScientificLabStage.PREDICTION_ERROR_OR_ANOMALY,
            "run:36145156033",
            True,
            "V17_CONSUMED_SHADOW",
        ),
        _evidence(
            ScientificLabStage.RESEARCH_QUESTION,
            "v18:incremental-defense-on-v16-untouched-only",
            True,
            "V18_RESEARCH_DESIGN",
        ),
        _evidence(
            ScientificLabStage.COMPETING_HYPOTHESES,
            "v18:frozen-v16-vs-v16-plus-recovery-vetoed-half-risk",
            True,
            "V18_RESEARCH_DESIGN",
        ),
        _evidence(
            ScientificLabStage.EXPERIMENT_DESIGN,
            "commit:9303ce4765e2eba3edd14cb23db4b667bce7e438",
            True,
            "V18_RESEARCH_DESIGN",
        ),
        _evidence(
            ScientificLabStage.LEAKAGE_CONTROLS,
            "run:36146027722:governance",
            True,
            "V18_CONSUMED_EVIDENCE_ONLY",
        ),
        _evidence(
            ScientificLabStage.HISTORICAL_TEST,
            "run:36146027722:five_year",
            True,
            "FIVE_YEAR_CONSUMED",
        ),
        _evidence(
            ScientificLabStage.FALSIFICATION,
            "run:36146027722:five_year:false",
            False,
            "FIVE_YEAR_CONSUMED",
        ),
        _evidence(
            ScientificLabStage.REPLICATION,
            "run:36146027722:recent_two_year:false",
            False,
            "RECENT_TWO_YEAR_CONSUMED",
        ),
        _evidence(
            ScientificLabStage.HOLDOUT,
            "run:36146027722:r66_consumed_failed_holdout",
            False,
            "R66_CONSUMED_FAILED_HOLDOUT",
        ),
        _evidence(
            ScientificLabStage.STRESS,
            "run:36146027722:cross_window_robustness:false",
            False,
            "MULTI_WINDOW_CONSUMED_STRESS",
        ),
        _evidence(
            ScientificLabStage.SHADOW,
            "artifact:10870455251",
            False,
            "V18_ECONOMIC_SHADOW_CONSUMED",
        ),
        _evidence(
            ScientificLabStage.KNOWLEDGE_DECISION,
            "decision:V18_REJECT_AND_DO_NOT_PROMOTE",
            True,
            "V18_GOVERNED_DECISION",
        ),
    )
    outcome = conservative_lab_outcome(stages)
    record = ScientificExperimentRecord(
        experiment_id="AUTONOMOUS_INCREMENTAL_DEFENSE_V18",
        version="001",
        evidence=stages,
        outcome=outcome,
        rollback_ref="V16_FROZEN_FRONTIER",
    )

    full_loop = (
        len(record.evidence) == len(ScientificLabStage)
        and record.last_stage is ScientificLabStage.KNOWLEDGE_DECISION
    )
    completed = (
        full_loop
        and record.outcome is ScientificResearchOutcome.REJECT
        and record.certified_runtime_mutation is False
        and record.promotion_authority is False
    )
    payload = {
        "identity": IDENTITY,
        "status": (
            "MC22_AUTONOMOUS_SCIENTIFIC_LAB_COMPLETED_AND_PROVEN"
            if completed
            else "MC22_V18_FULL_LOOP_BINDING_FAILED"
        ),
        "experiment_id": record.experiment_id,
        "outcome": record.outcome.value,
        "last_stage": record.last_stage.name,
        "stage_count": len(record.evidence),
        "required_stage_count": len(ScientificLabStage),
        "all_required_stages_materialized": full_loop,
        "stage_results": {
            item.stage.name: item.passed for item in record.evidence
        },
        "v18_window_pass_map": pass_map,
        "rejection_preserved": record.outcome is ScientificResearchOutcome.REJECT,
        "failed_experiment_auto_promoted": False,
        "consumed_evidence_misrepresented_as_fresh": False,
        "fresh_holdout_opened_by_mc22": False,
        "certified_runtime_mutation": record.certified_runtime_mutation,
        "promotion_authority": record.promotion_authority,
        "record_fingerprint": record.fingerprint(),
        "mc22_completed_and_proven": completed,
        "master_ledger_mutated": False,
        "protected_certification_holdout_opened": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
