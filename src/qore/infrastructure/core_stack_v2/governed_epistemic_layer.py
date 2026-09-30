"""WP-08 governed epistemic integration.

Belief calibration, uncertainty, contradiction, novelty, and missing evidence
remain distinct epistemic quantities. Uncertainty and novelty research indices
are not silently reinterpreted as calibrated probabilities.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class EpistemicSituation(StrEnum):
    CALIBRATED = "CALIBRATED"
    CONTESTED = "CONTESTED"
    INSUFFICIENT = "INSUFFICIENT"
    NOVELTY_ALERT = "NOVELTY_ALERT"


@dataclass(frozen=True, slots=True)
class GovernedEpistemicEvidence:
    calibration_error_bps: int
    uncertainty_index_bps: int
    contradiction_bps: int
    novelty_index_bps: int
    missing_evidence_bps: int
    evidence_refs: tuple[str, ...]
    belief_probability_calibrated: bool
    uncertainty_is_calibrated_probability: bool = False
    novelty_is_calibrated_probability: bool = False

    def __post_init__(self) -> None:
        for name in (
            "calibration_error_bps",
            "uncertainty_index_bps",
            "contradiction_bps",
            "novelty_index_bps",
            "missing_evidence_bps",
        ):
            value = getattr(self, name)
            if type(value) is not int or not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be int within 0..10000")
        if (
            not self.evidence_refs
            or self.evidence_refs != tuple(sorted(set(self.evidence_refs)))
        ):
            raise ValueError("epistemic evidence refs must be canonical")
        if not self.belief_probability_calibrated:
            raise ValueError("WP08 requires calibrated belief evidence")
        if self.uncertainty_is_calibrated_probability:
            raise ValueError("uncertainty research index cannot masquerade as probability")
        if self.novelty_is_calibrated_probability:
            raise ValueError("novelty research index cannot masquerade as probability")


@dataclass(frozen=True, slots=True)
class GovernedEpistemicState:
    state: EpistemicSituation
    assertiveness_ceiling_bps: int
    calibration_error_bps: int
    uncertainty_index_bps: int
    contradiction_bps: int
    novelty_index_bps: int
    missing_evidence_bps: int
    reason_codes: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    trading_command: bool = False
    methodology_authority: bool = False
    sizing_authority: bool = False
    capital_authority: bool = False
    risk_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        if type(self.assertiveness_ceiling_bps) is not int:
            raise ValueError("assertiveness ceiling must be an integer")
        if not 0 <= self.assertiveness_ceiling_bps <= 10_000:
            raise ValueError("assertiveness ceiling must be within 0..10000")
        if not self.reason_codes:
            raise ValueError("epistemic state requires reason codes")
        if (
            self.trading_command
            or self.methodology_authority
            or self.sizing_authority
            or self.capital_authority
            or self.risk_authority
            or self.execution_authority
        ):
            raise ValueError("epistemic state cannot carry downstream authority")


def assess_governed_epistemics(
    evidence: GovernedEpistemicEvidence,
) -> GovernedEpistemicState:
    """Reconcile distinct epistemic quantities without hiding adverse evidence."""

    risks = (
        evidence.calibration_error_bps,
        evidence.uncertainty_index_bps,
        evidence.contradiction_bps,
        evidence.novelty_index_bps,
        evidence.missing_evidence_bps,
    )
    ceiling = max(0, 10_000 - max(risks))
    reasons: list[str] = []

    if evidence.missing_evidence_bps >= 6_500:
        state = EpistemicSituation.INSUFFICIENT
        ceiling = min(ceiling, 1_500)
        reasons.append("MATERIAL_EVIDENCE_MISSING")
    elif evidence.novelty_index_bps >= 7_000:
        state = EpistemicSituation.NOVELTY_ALERT
        ceiling = min(ceiling, 2_000)
        reasons.append("NOVEL_WORLD_STRUCTURE")
    elif evidence.contradiction_bps >= 5_000:
        state = EpistemicSituation.CONTESTED
        ceiling = min(ceiling, 2_500)
        reasons.append("MATERIAL_CONTRADICTION")
    elif (
        evidence.uncertainty_index_bps >= 6_000
        or evidence.calibration_error_bps >= 2_500
    ):
        state = EpistemicSituation.CONTESTED
        reasons.append("EPISTEMIC_UNCERTAINTY")
    else:
        state = EpistemicSituation.CALIBRATED
        reasons.append("EPISTEMIC_EVIDENCE_COHERENT")

    return GovernedEpistemicState(
        state=state,
        assertiveness_ceiling_bps=ceiling,
        calibration_error_bps=evidence.calibration_error_bps,
        uncertainty_index_bps=evidence.uncertainty_index_bps,
        contradiction_bps=evidence.contradiction_bps,
        novelty_index_bps=evidence.novelty_index_bps,
        missing_evidence_bps=evidence.missing_evidence_bps,
        reason_codes=tuple(sorted(reasons)),
        evidence_refs=evidence.evidence_refs,
    )
