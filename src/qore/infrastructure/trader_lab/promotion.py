"""Independent Trader Lab promotion gate.

``DEMO_ELIGIBLE`` requires evidence-backed completion of the full mandatory
chain (REPLAY -> FAST_FORWARD -> OOS -> STRESS -> MONTE_CARLO -> RISK_REVIEW ->
CIBO_REVIEW -> INDEPENDENT_VALIDATION) plus explicit economic evaluation
evidence. CIBO may recommend but can never self-promote; Risk review cannot be
skipped; independent validation is a distinct final gate; and the Lab grants no
execution or Production authority.

Risk, CIBO, and independent validation are governed by external authorities with
no in-repo producer. When a lifecycle has completed every in-repo stage but is
still missing an external governed gate, promotion fails closed with
``EXTERNAL_EVIDENCE_DEPENDENT`` rather than silently treating the chain as merely
incomplete.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.trader_lab.candidate import (
    TraderLabCandidateBinding,
    TraderLabValidationError,
)
from qore.infrastructure.trader_lab.lifecycle import (
    MANDATORY_STAGES,
    TraderLabLifecycle,
    TraderLabState,
    validate_trader_lab_lifecycle,
)
from qore.infrastructure.trader_lab.stage_evidence import (
    TraderLabEvidenceKind,
    TraderLabEvidenceReference,
    TraderLabStage,
    validate_trader_lab_evidence_reference,
)

_BLOCKING_STATES = frozenset(
    {
        TraderLabState.REJECTED,
        TraderLabState.DEGRADED,
        TraderLabState.SUSPENDED,
    }
)

#: Mandatory stages governed by external authorities (no in-repo producer).
_EXTERNAL_GOVERNED_STAGES = frozenset(
    {
        TraderLabStage.RISK_REVIEW,
        TraderLabStage.CIBO_REVIEW,
        TraderLabStage.INDEPENDENT_VALIDATION,
    }
)

#: Mandatory stages the Lab can legitimately produce/verify in-repo.
_IN_REPO_STAGES = frozenset(MANDATORY_STAGES) - _EXTERNAL_GOVERNED_STAGES


class TraderLabPromotionStatus(StrEnum):
    """Closed promotion-decision outcomes."""

    DEMO_ELIGIBLE = "demo_eligible"
    EXTERNAL_EVIDENCE_DEPENDENT = "external_evidence_dependent"
    NOT_ELIGIBLE_INCOMPLETE = "not_eligible_incomplete"
    NOT_ELIGIBLE_BLOCKED_STATE = "not_eligible_blocked_state"
    NOT_ELIGIBLE_MISSING_ECONOMIC_EVIDENCE = "not_eligible_missing_economic_evidence"
    NOT_ELIGIBLE_INVALID_ECONOMIC_EVIDENCE = "not_eligible_invalid_economic_evidence"


@dataclass(frozen=True, slots=True)
class TraderLabPromotionDecision:
    """Immutable promotion decision for one exact candidate binding."""

    candidate: TraderLabCandidateBinding
    status: TraderLabPromotionStatus
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.candidate, TraderLabCandidateBinding):
            raise TraderLabValidationError("candidate must be TraderLabCandidateBinding")
        if not isinstance(self.status, TraderLabPromotionStatus):
            raise TraderLabValidationError("status must be TraderLabPromotionStatus")
        if not isinstance(self.reasons, tuple) or any(
            not isinstance(reason, str) for reason in self.reasons
        ):
            raise TraderLabValidationError(
                "reasons must be an immutable string tuple"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.candidate.fingerprint.logical_values(),
            self.status.value,
            self.reasons,
        )


def evaluate_demo_eligibility(
    lifecycle: TraderLabLifecycle,
    *,
    economic_evidence: TraderLabEvidenceReference | None = None,
) -> TraderLabPromotionDecision:
    """Evaluate demo eligibility from an exact, fully re-validated lifecycle.

    Economic evaluation evidence is mandatory and must carry the exact
    ``ECONOMIC_EVALUATION`` kind; there is no opt-out, and a risk/replay/CIBO
    reference cannot masquerade as economic evidence.
    """

    if not isinstance(lifecycle, TraderLabLifecycle):
        raise TraderLabValidationError("lifecycle must be TraderLabLifecycle")
    if economic_evidence is not None and not isinstance(
        economic_evidence, TraderLabEvidenceReference
    ):
        raise TraderLabValidationError(
            "economic_evidence must be TraderLabEvidenceReference or None"
        )
    validate_trader_lab_lifecycle(lifecycle)

    state = lifecycle.state
    if state in _BLOCKING_STATES:
        return TraderLabPromotionDecision(
            candidate=lifecycle.candidate,
            status=TraderLabPromotionStatus.NOT_ELIGIBLE_BLOCKED_STATE,
            reasons=(f"candidate is in terminal blocking state {state.value}",),
        )
    if state is not TraderLabState.DEMO_ELIGIBLE:
        completed = set(lifecycle.completed_stages)
        if _IN_REPO_STAGES <= completed:
            return TraderLabPromotionDecision(
                candidate=lifecycle.candidate,
                status=TraderLabPromotionStatus.EXTERNAL_EVIDENCE_DEPENDENT,
                reasons=(
                    "Risk/CIBO/independent-validation evidence is required from "
                    "an owning authority and cannot be produced by the Trader Lab",
                ),
            )
        return TraderLabPromotionDecision(
            candidate=lifecycle.candidate,
            status=TraderLabPromotionStatus.NOT_ELIGIBLE_INCOMPLETE,
            reasons=("candidate has not completed the mandatory qualification chain",),
        )
    if lifecycle.completed_stages != MANDATORY_STAGES:
        return TraderLabPromotionDecision(
            candidate=lifecycle.candidate,
            status=TraderLabPromotionStatus.NOT_ELIGIBLE_INCOMPLETE,
            reasons=("mandatory stage chain is incomplete",),
        )
    if economic_evidence is None:
        return TraderLabPromotionDecision(
            candidate=lifecycle.candidate,
            status=TraderLabPromotionStatus.NOT_ELIGIBLE_MISSING_ECONOMIC_EVIDENCE,
            reasons=(
                "economic evaluation evidence is required for demo eligibility",
            ),
        )
    # Deep-validate the economic reference (exact runtime types, self-
    # authenticating digest, token syntax) before trusting its kind or lineage.
    validate_trader_lab_evidence_reference(economic_evidence)
    if economic_evidence.kind is not TraderLabEvidenceKind.ECONOMIC_EVALUATION:
        return TraderLabPromotionDecision(
            candidate=lifecycle.candidate,
            status=TraderLabPromotionStatus.NOT_ELIGIBLE_INVALID_ECONOMIC_EVIDENCE,
            reasons=(
                "economic evidence must carry the exact ECONOMIC_EVALUATION kind",
            ),
        )
    if (
        economic_evidence.strategy_binding_fingerprint
        != lifecycle.candidate.strategy_binding.binding_fingerprint.value
    ):
        return TraderLabPromotionDecision(
            candidate=lifecycle.candidate,
            status=TraderLabPromotionStatus.NOT_ELIGIBLE_INVALID_ECONOMIC_EVIDENCE,
            reasons=(
                "economic evidence strategy lineage must match the candidate",
            ),
        )
    return TraderLabPromotionDecision(
        candidate=lifecycle.candidate,
        status=TraderLabPromotionStatus.DEMO_ELIGIBLE,
        reasons=(),
    )
