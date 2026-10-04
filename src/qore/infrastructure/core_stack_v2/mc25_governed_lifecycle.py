"""MC-25 governed same-lineage lifecycle.

This state machine prevents a performance-stress PASS from silently skipping
formal STRESS, SHADOW or CERTIFICATION. A failed stage terminalizes the exact
configuration; promotion never grants Shared productive authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class MC25Stage(StrEnum):
    FROZEN_CANDIDATE = "FROZEN_CANDIDATE"
    LINEAGE_INTEGRITY = "LINEAGE_INTEGRITY"
    PERFORMANCE_STRESS = "PERFORMANCE_STRESS"
    FORMAL_STRESS = "FORMAL_STRESS"
    SHADOW = "SHADOW"
    CERTIFICATION = "CERTIFICATION"
    PROMOTION = "PROMOTION"
    FALSIFIED = "FALSIFIED"


_NEXT_STAGE = {
    MC25Stage.FROZEN_CANDIDATE: MC25Stage.LINEAGE_INTEGRITY,
    MC25Stage.LINEAGE_INTEGRITY: MC25Stage.PERFORMANCE_STRESS,
    MC25Stage.PERFORMANCE_STRESS: MC25Stage.FORMAL_STRESS,
    MC25Stage.FORMAL_STRESS: MC25Stage.SHADOW,
    MC25Stage.SHADOW: MC25Stage.CERTIFICATION,
    MC25Stage.CERTIFICATION: MC25Stage.PROMOTION,
}


@dataclass(frozen=True, slots=True)
class MC25LifecycleState:
    candidate_id: str
    configuration_fingerprint: str
    stage: MC25Stage
    evidence_refs: tuple[str, ...]
    terminal: bool = False
    promotion_allowed: bool = False
    owner_approval_ref: str | None = None
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if not self.candidate_id:
            raise ValueError("candidate_id must be non-empty")
        if len(self.configuration_fingerprint) != 64:
            raise ValueError("configuration_fingerprint must be sha256")
        int(self.configuration_fingerprint, 16)
        if self.evidence_refs != tuple(sorted(set(self.evidence_refs))):
            raise ValueError("evidence_refs must be canonical")
        if self.productive_authority:
            raise ValueError("MC25 cannot grant Shared productive authority")
        if self.stage is MC25Stage.FALSIFIED and not self.terminal:
            raise ValueError("falsified lifecycle must be terminal")
        if self.stage is MC25Stage.PROMOTION:
            if not self.terminal or not self.promotion_allowed:
                raise ValueError("promotion must be a terminal governed disposition")
            if not self.owner_approval_ref:
                raise ValueError("promotion requires explicit owner approval")
        elif self.promotion_allowed:
            raise ValueError("promotion_allowed is only valid at PROMOTION")


def initial_mc25_state(
    *,
    candidate_id: str,
    configuration_fingerprint: str,
    evidence_refs: tuple[str, ...],
) -> MC25LifecycleState:
    return MC25LifecycleState(
        candidate_id=candidate_id,
        configuration_fingerprint=configuration_fingerprint,
        stage=MC25Stage.FROZEN_CANDIDATE,
        evidence_refs=tuple(sorted(set(evidence_refs))),
    )


def advance_mc25_stage(
    state: MC25LifecycleState,
    *,
    target_stage: MC25Stage,
    stage_passed: bool,
    evidence_refs: tuple[str, ...],
    owner_approval_ref: str | None = None,
) -> MC25LifecycleState:
    if state.terminal:
        raise ValueError("terminal MC25 configuration cannot advance")
    expected = _NEXT_STAGE.get(state.stage)
    if expected is None:
        raise ValueError(f"stage {state.stage.value} has no successor")
    if target_stage is not expected:
        raise ValueError(
            f"MC25 stage skip forbidden: expected {expected.value}, got {target_stage.value}"
        )
    refs = tuple(sorted(set(state.evidence_refs) | set(evidence_refs)))
    if not refs:
        raise ValueError("stage transition requires sealed evidence")
    if not stage_passed:
        return MC25LifecycleState(
            candidate_id=state.candidate_id,
            configuration_fingerprint=state.configuration_fingerprint,
            stage=MC25Stage.FALSIFIED,
            evidence_refs=refs,
            terminal=True,
        )
    if target_stage is MC25Stage.PROMOTION:
        if not owner_approval_ref:
            raise ValueError("governed promotion requires owner approval")
        return MC25LifecycleState(
            candidate_id=state.candidate_id,
            configuration_fingerprint=state.configuration_fingerprint,
            stage=MC25Stage.PROMOTION,
            evidence_refs=refs,
            terminal=True,
            promotion_allowed=True,
            owner_approval_ref=owner_approval_ref,
        )
    return MC25LifecycleState(
        candidate_id=state.candidate_id,
        configuration_fingerprint=state.configuration_fingerprint,
        stage=target_stage,
        evidence_refs=refs,
    )
