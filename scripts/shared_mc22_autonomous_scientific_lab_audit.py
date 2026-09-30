#!/usr/bin/env python3
"""Bind real Shared research history into MC-22 scientific-lab audit."""

from __future__ import annotations

import json
from pathlib import Path

from qore.infrastructure.core_stack_v2.autonomous_scientific_lab import (
    ScientificExperimentRecord,
    ScientificLabEvidence,
    ScientificLabStage,
    ScientificResearchOutcome,
    conservative_lab_outcome,
)

IDENTITY = "QORE_SHARED_MC22_AUTONOMOUS_SCIENTIFIC_LAB_AUDIT_001"


def _record(
    experiment_id: str,
    evidence: tuple[ScientificLabEvidence, ...],
) -> ScientificExperimentRecord:
    return ScientificExperimentRecord(
        experiment_id=experiment_id,
        version="001",
        evidence=evidence,
        outcome=conservative_lab_outcome(evidence),
    )


def main() -> None:
    mc09_v1 = _record(
        "MC09_RAW_BELIEF_CALIBRATION_V1",
        tuple(
            [
                ScientificLabEvidence(ScientificLabStage.OBSERVATION, "run:36746172379", True),
                ScientificLabEvidence(ScientificLabStage.PREDICTION_ERROR_OR_ANOMALY, "run:36753425521", True),
                ScientificLabEvidence(ScientificLabStage.RESEARCH_QUESTION, "mc09:raw-mass-calibration-question", True),
                ScientificLabEvidence(ScientificLabStage.COMPETING_HYPOTHESES, "mc09:ordinal-vs-probability", True),
                ScientificLabEvidence(ScientificLabStage.EXPERIMENT_DESIGN, "prereg:MC09_CALIBRATION_V1", True),
                ScientificLabEvidence(ScientificLabStage.LEAKAGE_CONTROLS, "mc09:oos-not-fit", True),
                ScientificLabEvidence(ScientificLabStage.HISTORICAL_TEST, "run:36753425521", True),
                ScientificLabEvidence(ScientificLabStage.FALSIFICATION, "run:36753425521", False),
            ]
        ),
    )
    mc09_v2 = _record(
        "MC09_PLATT_CALIBRATION_V2",
        tuple(
            ScientificLabEvidence(stage, ref, True)
            for stage, ref in (
                (ScientificLabStage.OBSERVATION, "run:36753425521"),
                (ScientificLabStage.PREDICTION_ERROR_OR_ANOMALY, "mc09:v1-under-calibration"),
                (ScientificLabStage.RESEARCH_QUESTION, "mc09:ordinal-score-calibration"),
                (ScientificLabStage.COMPETING_HYPOTHESES, "mc09:platt-vs-raw"),
                (ScientificLabStage.EXPERIMENT_DESIGN, "prereg:MC09_CALIBRATION_V2"),
                (ScientificLabStage.LEAKAGE_CONTROLS, "mc09:v2-oos-not-fit"),
                (ScientificLabStage.HISTORICAL_TEST, "run:36754966932"),
                (ScientificLabStage.FALSIFICATION, "mc09:v2-survived-falsification"),
                (ScientificLabStage.REPLICATION, "mc09:temporal-oos-2022-2024"),
                (ScientificLabStage.HOLDOUT, "artifact:11116522138"),
            )
        ),
    )
    wp04_v3b = _record(
        "WP04_V3B_LATENT_REPRESENTATION",
        tuple(
            ScientificLabEvidence(stage, ref, True)
            for stage, ref in (
                (ScientificLabStage.OBSERVATION, "run:36258083080"),
                (ScientificLabStage.PREDICTION_ERROR_OR_ANOMALY, "run:36258083044"),
                (ScientificLabStage.RESEARCH_QUESTION, "wp04:nonlinear-decoder-question"),
                (ScientificLabStage.COMPETING_HYPOTHESES, "wp04:v3-vs-v3b"),
                (ScientificLabStage.EXPERIMENT_DESIGN, "run:36244726347"),
                (ScientificLabStage.LEAKAGE_CONTROLS, "artifact:10906064254"),
                (ScientificLabStage.HISTORICAL_TEST, "run:36258083075"),
                (ScientificLabStage.FALSIFICATION, "wp04:v3b-survived-consumed"),
                (ScientificLabStage.REPLICATION, "run:36248025384"),
                (ScientificLabStage.HOLDOUT, "run:36247407353"),
            )
        ),
    )

    records = (mc09_v1, mc09_v2, wp04_v3b)
    payload = {
        "identity": IDENTITY,
        "status": "MC22_AUTONOMOUS_SCIENTIFIC_LAB_FOUNDATION_PASS",
        "real_research_lineage_count": len(records),
        "records": [
            {
                "experiment_id": item.experiment_id,
                "outcome": item.outcome.value,
                "last_stage": item.last_stage.name,
                "fingerprint": item.fingerprint(),
            }
            for item in records
        ],
        "falsification_preserved": (
            mc09_v1.outcome is ScientificResearchOutcome.REJECT
        ),
        "validated_without_auto_promotion": (
            mc09_v2.outcome is ScientificResearchOutcome.VALIDATED
            and wp04_v3b.outcome is ScientificResearchOutcome.VALIDATED
        ),
        "full_shadow_to_knowledge_decision_loop_bound": False,
        "certified_runtime_mutation_from_research": False,
        "mc22_completed_and_proven": False,
        "next_gate": "BIND_STRESS_SHADOW_KNOWLEDGE_DECISION_LINEAGE",
        "protected_certification_holdout_opened": False,
    }
    Path("result").mkdir(exist_ok=True)
    Path("result/mc22-autonomous-scientific-lab-audit.json").write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n"
    )
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
