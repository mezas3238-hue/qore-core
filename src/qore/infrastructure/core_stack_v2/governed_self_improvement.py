"""MC-25 Governed Self-Improvement promotion chain."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, StrEnum


class ImprovementStage(IntEnum):
    DISCOVERY = 1
    SANDBOX = 2
    FALSIFICATION = 3
    REPLICATION = 4
    HOLDOUT = 5
    STRESS = 6
    SHADOW = 7
    CERTIFICATION = 8
    PROMOTION = 9


class ImprovementTarget(StrEnum):
    MODEL = "MODEL"
    REPRESENTATION = "REPRESENTATION"
    ONTOLOGY = "ONTOLOGY"
    CALIBRATION = "CALIBRATION"
    RESEARCH_METHOD = "RESEARCH_METHOD"
    SPECIALIST_COMPOSITION = "SPECIALIST_COMPOSITION"
    COMPUTATIONAL_POLICY = "COMPUTATIONAL_POLICY"


@dataclass(frozen=True, slots=True)
class ImprovementStageEvidence:
    stage: ImprovementStage
    evidence_ref: str
    passed: bool
    dataset_window_id: str

    def __post_init__(self) -> None:
        if not self.evidence_ref or not self.dataset_window_id:
            raise ValueError("improvement stage needs evidence and dataset/window identity")


@dataclass(frozen=True, slots=True)
class GovernedImprovementProposal:
    proposal_id: str
    version: str
    target: ImprovementTarget
    rollback_ref: str
    provenance_refs: tuple[str, ...]
    reproducibility_ref: str
    stages: tuple[ImprovementStageEvidence, ...]
    direct_experimental_to_certified: bool = False

    def __post_init__(self) -> None:
        for value in (
            self.proposal_id,
            self.version,
            self.rollback_ref,
            self.reproducibility_ref,
        ):
            if not value.strip():
                raise ValueError("self-improvement identity controls are mandatory")
        if (
            not self.provenance_refs
            or self.provenance_refs != tuple(sorted(set(self.provenance_refs)))
        ):
            raise ValueError("self-improvement provenance must be canonical")
        if self.direct_experimental_to_certified:
            raise ValueError("direct experimental-to-certified promotion is forbidden")
        if not self.stages:
            raise ValueError("self-improvement requires governed stages")
        ordered = tuple(item.stage for item in self.stages)
        if ordered != tuple(sorted(ordered)) or len(set(ordered)) != len(ordered):
            raise ValueError("improvement stages must be unique and ordered")
        for left, right in zip(ordered, ordered[1:], strict=False):
            if int(right) != int(left) + 1:
                raise ValueError("self-improvement cannot skip promotion stages")

    @property
    def promotion_allowed(self) -> bool:
        return (
            self.stages[-1].stage is ImprovementStage.PROMOTION
            and all(item.passed for item in self.stages)
        )

    @property
    def highest_completed_stage(self) -> ImprovementStage:
        passed = [item.stage for item in self.stages if item.passed]
        return max(passed) if passed else ImprovementStage.DISCOVERY
