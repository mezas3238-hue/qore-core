"""MC-27 Meta-Cognitive Scientific Intelligence.

Observes Shared's own reasoning quality and emits research priorities. It does
not modify certified knowledge or trading systems.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import StrEnum


class MetaCognitiveConcern(StrEnum):
    PREDICTION_ERROR = "PREDICTION_ERROR"
    MISUNDERSTOOD_MECHANISM = "MISUNDERSTOOD_MECHANISM"
    OVERCONFIDENCE = "OVERCONFIDENCE"
    MODEL_FAILURE = "MODEL_FAILURE"
    SPECIALIST_DOMINANCE = "SPECIALIST_DOMINANCE"
    CONCEPT_DECAY = "CONCEPT_DECAY"
    REGIME_CHANGE = "REGIME_CHANGE"
    FALSIFICATION_GAP = "FALSIFICATION_GAP"
    UNKNOWN_UNKNOWN = "UNKNOWN_UNKNOWN"
    COMPUTE_VALUE = "COMPUTE_VALUE"


@dataclass(frozen=True, slots=True)
class MetaCognitiveObservation:
    prediction_error_bps: int
    calibration_error_bps: int
    model_disagreement_bps: int
    dominant_specialist_share_bps: int
    concept_decay_bps: int
    regime_novelty_bps: int
    information_gap_bps: int
    falsification_coverage_bps: int
    expected_compute_value_bps: int
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in (
            "prediction_error_bps",
            "calibration_error_bps",
            "model_disagreement_bps",
            "dominant_specialist_share_bps",
            "concept_decay_bps",
            "regime_novelty_bps",
            "information_gap_bps",
            "falsification_coverage_bps",
            "expected_compute_value_bps",
        ):
            value = getattr(self, name)
            if type(value) is not int or not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be int within 0..10000")
        if (
            not self.evidence_refs
            or self.evidence_refs != tuple(sorted(set(self.evidence_refs)))
        ):
            raise ValueError("meta-cognitive evidence refs must be canonical")


@dataclass(frozen=True, slots=True)
class MetaCognitiveResearchPriority:
    concern: MetaCognitiveConcern
    priority_bps: int
    question: str
    falsification_requirement: str
    deeper_compute_justified: bool

    def __post_init__(self) -> None:
        if type(self.priority_bps) is not int or not 0 <= self.priority_bps <= 10_000:
            raise ValueError("priority_bps must be int within 0..10000")
        if not self.question or not self.falsification_requirement:
            raise ValueError("meta-cognitive priority needs question/falsification")


@dataclass(frozen=True, slots=True)
class MetaCognitiveAssessment:
    priorities: tuple[MetaCognitiveResearchPriority, ...]
    unknowns_explicit: bool
    self_modification_authority: bool = False
    certified_runtime_mutation: bool = False

    def __post_init__(self) -> None:
        if self.priorities != tuple(
            sorted(
                self.priorities,
                key=lambda item: (-item.priority_bps, item.concern.value),
            )
        ):
            raise ValueError("meta-cognitive priorities must be canonical")
        if not self.unknowns_explicit:
            raise ValueError("meta-cognition must preserve explicit unknowns")
        if self.self_modification_authority or self.certified_runtime_mutation:
            raise ValueError("meta-cognition cannot self-modify certified runtime")

    def fingerprint(self) -> str:
        payload = {
            "priorities": tuple(
                {**asdict(item), "concern": item.concern.value}
                for item in self.priorities
            ),
            "unknowns_explicit": self.unknowns_explicit,
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()


def assess_meta_cognition(
    observation: MetaCognitiveObservation,
) -> MetaCognitiveAssessment:
    rows = [
        (
            MetaCognitiveConcern.PREDICTION_ERROR,
            observation.prediction_error_bps,
            "How well am I predicting?",
            "Independent temporal error must improve without retune.",
        ),
        (
            MetaCognitiveConcern.OVERCONFIDENCE,
            observation.calibration_error_bps,
            "Where am I overconfident?",
            "Calibration error must improve on later OOS.",
        ),
        (
            MetaCognitiveConcern.MODEL_FAILURE,
            observation.model_disagreement_bps,
            "Which model or world is failing?",
            "Competing model must survive falsification and replication.",
        ),
        (
            MetaCognitiveConcern.SPECIALIST_DOMINANCE,
            observation.dominant_specialist_share_bps,
            "Which specialist is dominating incorrectly?",
            "Minority falsification evidence must remain visible.",
        ),
        (
            MetaCognitiveConcern.CONCEPT_DECAY,
            observation.concept_decay_bps,
            "Which concepts no longer explain observed episodes?",
            "Concept retention must beat frozen baseline on later evidence.",
        ),
        (
            MetaCognitiveConcern.REGIME_CHANGE,
            observation.regime_novelty_bps,
            "Has the regime changed?",
            "Novel regime hypothesis requires independent validation.",
        ),
        (
            MetaCognitiveConcern.UNKNOWN_UNKNOWN,
            observation.information_gap_bps,
            "What do I not know?",
            "Missing-information acquisition must precede stronger claims.",
        ),
        (
            MetaCognitiveConcern.FALSIFICATION_GAP,
            10_000 - observation.falsification_coverage_bps,
            "What evidence would falsify me?",
            "Predeclared falsification gate must exist before evaluation.",
        ),
        (
            MetaCognitiveConcern.COMPUTE_VALUE,
            observation.expected_compute_value_bps,
            "Is deeper computation worth its cost?",
            "Extra compute must show measurable information gain.",
        ),
    ]
    priorities = tuple(
        sorted(
            (
                MetaCognitiveResearchPriority(
                    concern=concern,
                    priority_bps=value,
                    question=question,
                    falsification_requirement=requirement,
                    deeper_compute_justified=(
                        concern is MetaCognitiveConcern.COMPUTE_VALUE
                        and value >= 5_000
                    ),
                )
                for concern, value, question, requirement in rows
                if value >= 2_500
            ),
            key=lambda item: (-item.priority_bps, item.concern.value),
        )
    )
    return MetaCognitiveAssessment(
        priorities=priorities,
        unknowns_explicit=True,
    )
