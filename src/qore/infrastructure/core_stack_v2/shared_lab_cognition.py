"""Uncertainty calibration and contradiction-resolution evidence for Shared Lab."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from math import isfinite


class ContradictionDisposition(StrEnum):
    RESOLVED = "RESOLVED"
    ABSTAIN = "ABSTAIN"
    UNRESOLVED = "UNRESOLVED"


@dataclass(frozen=True, slots=True)
class CalibrationBin:
    confidence: float
    observations: int
    realized_rate: float

    def __post_init__(self) -> None:
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("confidence must be in [0,1]")
        if self.observations <= 0:
            raise ValueError("calibration bin requires observations")
        if not (0.0 <= self.realized_rate <= 1.0):
            raise ValueError("realized rate must be in [0,1]")

    @property
    def absolute_error(self) -> float:
        return abs(self.confidence - self.realized_rate)


@dataclass(frozen=True, slots=True)
class UncertaintyCalibrationReceipt:
    capability_id: str
    bins: tuple[CalibrationBin, ...]
    max_allowed_weighted_error: float
    high_confidence_threshold: float = 0.8
    max_high_confidence_wrong_rate: float = 0.25

    def __post_init__(self) -> None:
        if not self.capability_id.strip() or not self.bins:
            raise ValueError("uncertainty calibration requires identity and bins")
        if self.max_allowed_weighted_error < 0:
            raise ValueError("calibration tolerance cannot be negative")

    @property
    def weighted_error(self) -> float:
        total = sum(item.observations for item in self.bins)
        return sum(item.absolute_error * item.observations for item in self.bins) / total

    @property
    def high_confidence_wrong_rate(self) -> float:
        high = tuple(
            item
            for item in self.bins
            if item.confidence >= self.high_confidence_threshold
        )
        if not high:
            return 0.0
        total = sum(item.observations for item in high)
        wrong = sum((1.0 - item.realized_rate) * item.observations for item in high)
        return wrong / total

    @property
    def passed(self) -> bool:
        return (
            isfinite(self.weighted_error)
            and self.weighted_error <= self.max_allowed_weighted_error
            and self.high_confidence_wrong_rate <= self.max_high_confidence_wrong_rate
        )


@dataclass(frozen=True, slots=True)
class ContradictionEvidence:
    source_id: str
    claim: str
    confidence: float
    physics_valid: bool
    causal_support: float

    def __post_init__(self) -> None:
        if not self.source_id.strip() or not self.claim.strip():
            raise ValueError("contradiction evidence requires source and claim")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("confidence must be in [0,1]")
        if not (0.0 <= self.causal_support <= 1.0):
            raise ValueError("causal support must be in [0,1]")


@dataclass(frozen=True, slots=True)
class ContradictionResolutionReceipt:
    capability_id: str
    evidence: tuple[ContradictionEvidence, ...]
    disposition: ContradictionDisposition
    selected_claim: str | None
    uncertainty_increased: bool
    impossible_world_rejected: bool

    @property
    def conflicting_claims(self) -> bool:
        return len({item.claim for item in self.evidence}) > 1

    @property
    def passed(self) -> bool:
        if not self.evidence or not self.conflicting_claims:
            return False
        if not self.uncertainty_increased:
            return False
        invalid_exists = any(not item.physics_valid for item in self.evidence)
        if invalid_exists and not self.impossible_world_rejected:
            return False
        if self.disposition is ContradictionDisposition.UNRESOLVED:
            return False
        if self.disposition is ContradictionDisposition.RESOLVED:
            if self.selected_claim is None:
                return False
            valid_claims = {
                item.claim
                for item in self.evidence
                if item.physics_valid and item.causal_support > 0
            }
            return self.selected_claim in valid_claims
        return self.selected_claim is None
