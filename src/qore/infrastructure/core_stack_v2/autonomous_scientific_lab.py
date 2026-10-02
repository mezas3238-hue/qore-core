"""MC-22 Autonomous Scientific Laboratory governance state machine."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import IntEnum, StrEnum


class ScientificLabStage(IntEnum):
    OBSERVATION = 1
    PREDICTION_ERROR_OR_ANOMALY = 2
    RESEARCH_QUESTION = 3
    COMPETING_HYPOTHESES = 4
    EXPERIMENT_DESIGN = 5
    LEAKAGE_CONTROLS = 6
    HISTORICAL_TEST = 7
    FALSIFICATION = 8
    REPLICATION = 9
    HOLDOUT = 10
    STRESS = 11
    SHADOW = 12
    KNOWLEDGE_DECISION = 13


class ScientificResearchOutcome(StrEnum):
    REJECT = "REJECT"
    RESEARCH_ONLY = "RESEARCH_ONLY"
    VALIDATED = "VALIDATED"
    CERTIFICATION_CANDIDATE = "CERTIFICATION_CANDIDATE"


@dataclass(frozen=True, slots=True)
class ScientificLabEvidence:
    stage: ScientificLabStage
    evidence_ref: str
    passed: bool
    consumed_window: str | None = None
    fresh_evidence: bool = False

    def __post_init__(self) -> None:
        if not self.evidence_ref.strip():
            raise ValueError("scientific lab evidence_ref must be explicit")
        if self.fresh_evidence and self.consumed_window is None:
            raise ValueError("fresh evidence must carry explicit window identity")


@dataclass(frozen=True, slots=True)
class ScientificExperimentRecord:
    experiment_id: str
    version: str
    evidence: tuple[ScientificLabEvidence, ...]
    outcome: ScientificResearchOutcome
    certified_runtime_mutation: bool = False
    promotion_authority: bool = False
    rollback_ref: str | None = None

    def __post_init__(self) -> None:
        if not self.experiment_id.strip() or not self.version.strip():
            raise ValueError("experiment identity/version required")
        if not self.evidence:
            raise ValueError("experiment requires evidence")
        stages = tuple(item.stage for item in self.evidence)
        if stages != tuple(sorted(stages)):
            raise ValueError("scientific lab stages must be monotonic")
        if len(set(stages)) != len(stages):
            raise ValueError("scientific lab stage may appear only once")
        for left, right in zip(stages, stages[1:], strict=False):
            if int(right) != int(left) + 1:
                raise ValueError("scientific lab cannot skip required stages")
        if self.certified_runtime_mutation or self.promotion_authority:
            raise ValueError("research record cannot directly mutate certified runtime")
        if self.outcome is ScientificResearchOutcome.CERTIFICATION_CANDIDATE:
            if stages[-1] is not ScientificLabStage.KNOWLEDGE_DECISION:
                raise ValueError("certification candidate requires full lab loop")
            if not all(item.passed for item in self.evidence):
                raise ValueError("certification candidate requires all stages pass")
        if self.outcome is ScientificResearchOutcome.REJECT:
            if all(item.passed for item in self.evidence):
                raise ValueError("reject requires at least one failed stage")
        if (
            self.outcome is ScientificResearchOutcome.VALIDATED
            and ScientificLabStage.HOLDOUT not in stages
        ):
            raise ValueError("validated requires holdout evidence")

    @property
    def last_stage(self) -> ScientificLabStage:
        return self.evidence[-1].stage

    def fingerprint(self) -> str:
        payload = asdict(self)
        payload["outcome"] = self.outcome.value
        payload["evidence"] = tuple(
            {
                **asdict(item),
                "stage": item.stage.name,
            }
            for item in self.evidence
        )
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()


def conservative_lab_outcome(
    evidence: tuple[ScientificLabEvidence, ...],
) -> ScientificResearchOutcome:
    if not evidence:
        raise ValueError("scientific lab outcome requires evidence")
    if any(not item.passed for item in evidence):
        return ScientificResearchOutcome.REJECT
    stages = {item.stage for item in evidence}
    if ScientificLabStage.KNOWLEDGE_DECISION in stages:
        return ScientificResearchOutcome.CERTIFICATION_CANDIDATE
    if {
        ScientificLabStage.HOLDOUT,
        ScientificLabStage.REPLICATION,
    }.issubset(stages):
        return ScientificResearchOutcome.VALIDATED
    return ScientificResearchOutcome.RESEARCH_ONLY
