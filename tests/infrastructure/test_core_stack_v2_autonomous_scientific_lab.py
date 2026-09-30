import pytest

from qore.infrastructure.core_stack_v2.autonomous_scientific_lab import (
    ScientificExperimentRecord,
    ScientificLabEvidence,
    ScientificLabStage,
    ScientificResearchOutcome,
    conservative_lab_outcome,
)


def _prefix(end: ScientificLabStage, *, fail_at: ScientificLabStage | None = None):
    return tuple(
        ScientificLabEvidence(
            stage=stage,
            evidence_ref=f"lab:{stage.name}",
            passed=stage is not fail_at,
        )
        for stage in ScientificLabStage
        if int(stage) <= int(end)
    )


def test_stage_skipping_fails_closed() -> None:
    evidence = (
        ScientificLabEvidence(
            stage=ScientificLabStage.OBSERVATION,
            evidence_ref="obs",
            passed=True,
        ),
        ScientificLabEvidence(
            stage=ScientificLabStage.RESEARCH_QUESTION,
            evidence_ref="question",
            passed=True,
        ),
    )
    with pytest.raises(ValueError, match="cannot skip"):
        ScientificExperimentRecord(
            experiment_id="skip-test",
            version="001",
            evidence=evidence,
            outcome=ScientificResearchOutcome.RESEARCH_ONLY,
        )


def test_failed_historical_gate_rejects() -> None:
    evidence = _prefix(
        ScientificLabStage.FALSIFICATION,
        fail_at=ScientificLabStage.FALSIFICATION,
    )
    assert conservative_lab_outcome(evidence) is ScientificResearchOutcome.REJECT


def test_holdout_and_replication_can_be_validated_but_not_certification_candidate() -> None:
    evidence = _prefix(ScientificLabStage.HOLDOUT)
    outcome = conservative_lab_outcome(evidence)
    assert outcome is ScientificResearchOutcome.VALIDATED
    record = ScientificExperimentRecord(
        experiment_id="validated-test",
        version="001",
        evidence=evidence,
        outcome=outcome,
    )
    assert record.promotion_authority is False


def test_full_loop_is_only_certification_candidate_not_promotion() -> None:
    evidence = _prefix(ScientificLabStage.KNOWLEDGE_DECISION)
    outcome = conservative_lab_outcome(evidence)
    assert outcome is ScientificResearchOutcome.CERTIFICATION_CANDIDATE
    record = ScientificExperimentRecord(
        experiment_id="full-loop",
        version="001",
        evidence=evidence,
        outcome=outcome,
    )
    assert record.certified_runtime_mutation is False
    assert record.promotion_authority is False
