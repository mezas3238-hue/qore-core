"""MC-11 governed neural-symbolic cognition boundary.

This module does not train a new neural model. It binds an already frozen
learned market representation to calibrated probabilistic belief and symbolic
hard constraints while preserving full provenance. Hard structural violations
always dominate learned support.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import StrEnum

from qore.infrastructure.core_stack_v2.market_physics_constraints import (
    MarketPhysicsAssessment,
)


def _canonical_refs(refs: tuple[str, ...], *, name: str) -> None:
    if not refs or refs != tuple(sorted(set(refs))):
        raise ValueError(f"{name} must be non-empty and canonical")


def _bps(value: int, *, name: str) -> None:
    if type(value) is not int or not 0 <= value <= 10_000:
        raise ValueError(f"{name} must be int within 0..10000")


class NeuralSymbolicDisposition(StrEnum):
    SUPPORTED = "SUPPORTED"
    CONTESTED = "CONTESTED"
    ABSTAIN = "ABSTAIN"
    HARD_CONSTRAINT_VETO = "HARD_CONSTRAINT_VETO"


@dataclass(frozen=True, slots=True)
class FrozenLearnedRepresentationRef:
    representation_fingerprint: str
    concept_ids: tuple[str, ...]
    probe_fingerprints: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    runtime_future_market_used: bool = False
    identity_shortcut_used: bool = False

    def __post_init__(self) -> None:
        if len(self.representation_fingerprint) != 64:
            raise ValueError("representation fingerprint must be sha256")
        int(self.representation_fingerprint, 16)
        if (
            not self.concept_ids
            or self.concept_ids != tuple(sorted(set(self.concept_ids)))
        ):
            raise ValueError("concept_ids must be non-empty and canonical")
        if (
            not self.probe_fingerprints
            or self.probe_fingerprints
            != tuple(sorted(set(self.probe_fingerprints)))
        ):
            raise ValueError("probe_fingerprints must be non-empty and canonical")
        for fingerprint in self.probe_fingerprints:
            if len(fingerprint) != 64:
                raise ValueError("probe fingerprint must be sha256")
            int(fingerprint, 16)
        _canonical_refs(self.evidence_refs, name="representation evidence_refs")
        if self.runtime_future_market_used or self.identity_shortcut_used:
            raise ValueError("runtime learned representation cannot leak future/identity")


@dataclass(frozen=True, slots=True)
class CalibratedBeliefRef:
    calibration_artifact_fingerprint: str
    calibration_ece_bps: int
    temporal_oos_pass: bool
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if len(self.calibration_artifact_fingerprint) != 64:
            raise ValueError("calibration artifact fingerprint must be sha256")
        int(self.calibration_artifact_fingerprint, 16)
        _bps(self.calibration_ece_bps, name="calibration_ece_bps")
        _canonical_refs(self.evidence_refs, name="belief evidence_refs")
        if not self.temporal_oos_pass:
            raise ValueError("MC-11 requires temporally validated belief calibration")


@dataclass(frozen=True, slots=True)
class NeuralSymbolicConclusion:
    disposition: NeuralSymbolicDisposition
    assertiveness_bps: int
    learned_support_bps: int
    learned_contradiction_bps: int
    epistemic_uncertainty_bps: int
    representation_fingerprint: str
    market_physics_fingerprint: str
    supporting_evidence_refs: tuple[str, ...]
    contradicting_evidence_refs: tuple[str, ...]
    causal_path_refs: tuple[str, ...]
    reason_codes: tuple[str, ...]
    hard_constraint_veto: bool
    execution_authority: bool = False
    risk_authority: bool = False
    sizing_authority: bool = False
    capital_authority: bool = False
    methodology_authority: bool = False

    def __post_init__(self) -> None:
        for name in (
            "assertiveness_bps",
            "learned_support_bps",
            "learned_contradiction_bps",
            "epistemic_uncertainty_bps",
        ):
            _bps(getattr(self, name), name=name)
        for fingerprint in (
            self.representation_fingerprint,
            self.market_physics_fingerprint,
        ):
            if len(fingerprint) != 64:
                raise ValueError("neural-symbolic fingerprints must be sha256")
            int(fingerprint, 16)
        _canonical_refs(
            self.supporting_evidence_refs,
            name="supporting_evidence_refs",
        )
        _canonical_refs(
            self.contradicting_evidence_refs,
            name="contradicting_evidence_refs",
        )
        _canonical_refs(self.causal_path_refs, name="causal_path_refs")
        _canonical_refs(self.reason_codes, name="reason_codes")
        if (
            self.execution_authority
            or self.risk_authority
            or self.sizing_authority
            or self.capital_authority
            or self.methodology_authority
        ):
            raise ValueError("MC-11 cannot acquire sovereign authority")
        if self.hard_constraint_veto:
            if (
                self.disposition is not NeuralSymbolicDisposition.HARD_CONSTRAINT_VETO
                or self.assertiveness_bps != 0
            ):
                raise ValueError("hard constraint veto must dominate learned output")

    def fingerprint(self) -> str:
        payload = asdict(self)
        payload["disposition"] = self.disposition.value
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()


def arbitrate_neural_symbolic(
    *,
    representation: FrozenLearnedRepresentationRef,
    belief_calibration: CalibratedBeliefRef,
    physics: MarketPhysicsAssessment,
    learned_support_bps: int,
    learned_contradiction_bps: int,
    epistemic_uncertainty_bps: int,
    source_observation_refs: tuple[str, ...],
    contradicting_evidence_refs: tuple[str, ...],
    causal_path_refs: tuple[str, ...],
) -> NeuralSymbolicConclusion:
    del belief_calibration  # validated by construction; kept as required dependency.
    _bps(learned_support_bps, name="learned_support_bps")
    _bps(learned_contradiction_bps, name="learned_contradiction_bps")
    _bps(epistemic_uncertainty_bps, name="epistemic_uncertainty_bps")
    _canonical_refs(source_observation_refs, name="source_observation_refs")
    _canonical_refs(
        contradicting_evidence_refs,
        name="contradicting_evidence_refs",
    )
    _canonical_refs(causal_path_refs, name="causal_path_refs")

    reasons: tuple[str, ...]
    if not physics.hard_constraints_pass:
        disposition = NeuralSymbolicDisposition.HARD_CONSTRAINT_VETO
        assertiveness = 0
        reasons = (
            "HARD_STRUCTURAL_CONSTRAINT_VETO",
            "LEARNED_SUPPORT_SUBORDINATE_TO_SYMBOLIC_CONSTRAINT",
        )
        hard_veto = True
    elif learned_support_bps == 0 and learned_contradiction_bps == 0:
        disposition = NeuralSymbolicDisposition.ABSTAIN
        assertiveness = 0
        reasons = ("NO_MATERIAL_LEARNED_EVIDENCE",)
        hard_veto = False
    elif learned_contradiction_bps >= learned_support_bps:
        disposition = NeuralSymbolicDisposition.CONTESTED
        assertiveness = min(
            learned_contradiction_bps - learned_support_bps,
            10_000 - epistemic_uncertainty_bps,
        )
        reasons = ("CONTRADICTION_AT_LEAST_SUPPORT",)
        hard_veto = False
    else:
        disposition = NeuralSymbolicDisposition.SUPPORTED
        assertiveness = min(
            learned_support_bps - learned_contradiction_bps,
            10_000 - epistemic_uncertainty_bps,
        )
        reasons = ("LEARNED_SUPPORT_SURVIVES_SYMBOLIC_CONSTRAINTS",)
        hard_veto = False

    return NeuralSymbolicConclusion(
        disposition=disposition,
        assertiveness_bps=max(0, assertiveness),
        learned_support_bps=learned_support_bps,
        learned_contradiction_bps=learned_contradiction_bps,
        epistemic_uncertainty_bps=epistemic_uncertainty_bps,
        representation_fingerprint=representation.representation_fingerprint,
        market_physics_fingerprint=physics.fingerprint(),
        supporting_evidence_refs=tuple(sorted(set(source_observation_refs))),
        contradicting_evidence_refs=tuple(
            sorted(set(contradicting_evidence_refs))
        ),
        causal_path_refs=tuple(sorted(set(causal_path_refs))),
        reason_codes=tuple(sorted(reasons)),
        hard_constraint_veto=hard_veto,
    )
