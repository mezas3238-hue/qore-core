"""R2 entry-family router for VT08 CRT PURE.

The router is source-first and fail-closed.  A valid parent CRT is not itself an
entry authorization.  The current R2 research path waits for one source-authorized
entry family and never falls back to the R1 C3-open baseline.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.traders.crt_pure_cognitive_contract import (
    CrtPureReasoningAction,
)
from qore.infrastructure.traders.crt_pure_methodology_candidate import (
    CrtPureCandidateDirection,
)
from qore.infrastructure.traders.crt_pure_model1 import (
    CrtPureModel1Confirmation,
    CrtPureModel1Direction,
    CrtPureModel1State,
)


class CrtPureR2EntryFamily(StrEnum):
    MODEL_1 = "MODEL_1"
    OTE = "OTE"
    TIME_BASED = "TIME_BASED"
    OTHER_SOURCE_AUTHORIZED = "OTHER_SOURCE_AUTHORIZED"


class CrtPureR2EntryState(StrEnum):
    UNRESOLVED = "UNRESOLVED"
    AWAITING_CONFIRMATION = "AWAITING_CONFIRMATION"
    CONFIRMED = "CONFIRMED"
    CONFLICTED = "CONFLICTED"


@dataclass(frozen=True, slots=True)
class CrtPureR2EntryAssessment:
    family: CrtPureR2EntryFamily
    state: CrtPureR2EntryState
    action: CrtPureReasoningAction
    evidence_tokens: tuple[str, ...]
    why: tuple[str, ...]
    grants_execution_authority: bool = False
    grants_capital_authority: bool = False

    def __post_init__(self) -> None:
        if self.grants_execution_authority:
            raise ValueError("R2 entry router cannot bypass full CRT/QORE decision gates")
        if self.grants_capital_authority:
            raise ValueError("R2 entry router cannot grant capital authority")
        if not self.why:
            raise ValueError("R2 entry assessment requires auditable WHY")


def _directions_match(
    parent_direction: CrtPureCandidateDirection,
    model1_direction: CrtPureModel1Direction,
) -> bool:
    return parent_direction.value == model1_direction.value


def assess_model1_entry_family(
    *,
    parent_direction: CrtPureCandidateDirection,
    confirmation: CrtPureModel1Confirmation | None,
) -> CrtPureR2EntryAssessment:
    """Route a parent CRT through Model #1 without any fallback entry."""

    if confirmation is None:
        return CrtPureR2EntryAssessment(
            family=CrtPureR2EntryFamily.MODEL_1,
            state=CrtPureR2EntryState.AWAITING_CONFIRMATION,
            action=CrtPureReasoningAction.WAIT,
            evidence_tokens=(),
            why=(
                "PARENT_CRT_PRESENT",
                "MODEL_1_NOT_YET_OBSERVED",
                "NO_C3_OPEN_FALLBACK",
            ),
        )

    candidate = confirmation.candidate
    evidence = (
        f"MODEL1_REFERENCE:{candidate.reference.evidence_id}",
        f"MODEL1_DIRECTION:{candidate.direction.value}",
        f"MODEL1_CONFIRMATION_STATE:{confirmation.state.value}",
    )

    if not _directions_match(parent_direction, candidate.direction):
        return CrtPureR2EntryAssessment(
            family=CrtPureR2EntryFamily.MODEL_1,
            state=CrtPureR2EntryState.CONFLICTED,
            action=CrtPureReasoningAction.ABSTAIN,
            evidence_tokens=evidence,
            why=(
                "MODEL_1_OPPOSES_PARENT_CRT_DIRECTION",
                "BIAS_REEVALUATION_REQUIRED",
                "NO_SAME_HYPOTHESIS_EXECUTION",
            ),
        )

    if confirmation.state is not CrtPureModel1State.CONFIRMED:
        return CrtPureR2EntryAssessment(
            family=CrtPureR2EntryFamily.MODEL_1,
            state=CrtPureR2EntryState.AWAITING_CONFIRMATION,
            action=CrtPureReasoningAction.WAIT,
            evidence_tokens=evidence,
            why=(
                "MODEL_1_SOURCE_CANDLE_PRESENT",
                "MODEL_1_BODY_CLOSE_CONFIRMATION_MISSING",
                "NO_C3_OPEN_FALLBACK",
            ),
        )

    return CrtPureR2EntryAssessment(
        family=CrtPureR2EntryFamily.MODEL_1,
        state=CrtPureR2EntryState.CONFIRMED,
        action=CrtPureReasoningAction.EXECUTE,
        evidence_tokens=evidence,
        why=(
            "PARENT_CRT_DIRECTION_ALIGNED",
            "MODEL_1_SOURCE_CANDLE_PRESENT",
            "MODEL_1_BODY_CLOSE_CONFIRMED",
            "ENTRY_FAMILY_SOURCE_CLOSED",
            "FULL_CRT_AND_QORE_GATES_STILL_REQUIRED",
        ),
    )


def assess_unclosed_entry_family(
    family: CrtPureR2EntryFamily,
) -> CrtPureR2EntryAssessment:
    """Fail closed for entry families whose exact machine contract is still open."""

    if family is CrtPureR2EntryFamily.MODEL_1:
        raise ValueError("MODEL_1 must use assess_model1_entry_family")
    return CrtPureR2EntryAssessment(
        family=family,
        state=CrtPureR2EntryState.UNRESOLVED,
        action=CrtPureReasoningAction.WAIT,
        evidence_tokens=(),
        why=(
            f"{family.value}_SOURCE_MACHINE_CONTRACT_NOT_CLOSED",
            "NO_FALLBACK_ENTRY",
        ),
    )
