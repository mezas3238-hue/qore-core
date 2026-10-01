"""Phase 22 sealed-holdout lineage gate for CIBO.

This gate proves only that a holdout population is fresh, disjoint and bound to
an exact Phase21-frozen policy. It does not invent economic thresholds and does
not claim holdout PASS. A separate pre-registered Phase22 evaluation plan is
still required before economic certification.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_holdout_registry import (
    PREREGISTERED_USD60_HOLDOUT,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_policy_store import (
    VersionedPhase20ForwardPolicyBook,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    VersionedPhase20ForwardEvidenceBook,
)
from qore.infrastructure.cibo_ce2i_phase21_policy_freeze import (
    Phase21PolicyFreezeManifest,
)

_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class Phase22HoldoutLineageAssessment:
    lineage_valid: bool
    reasons: tuple[str, ...]
    decision_epochs: int
    policy_decisions: int
    outcomes: int
    collector_git_shas: tuple[str, ...]
    earliest_decision_at: datetime | None
    latest_decision_at: datetime | None
    economic_holdout_passed: bool = False

    def __post_init__(self) -> None:
        if self.economic_holdout_passed:
            raise CiboCapitalManagementError(
                "Phase22 lineage gate cannot claim economic holdout PASS"
            )


def assess_phase22_holdout_lineage(
    *,
    phase21_manifest: Phase21PolicyFreezeManifest,
    qualification_evidence_book: VersionedPhase20ForwardEvidenceBook,
    holdout_evidence_book: VersionedPhase20ForwardEvidenceBook,
    holdout_policy_book: VersionedPhase20ForwardPolicyBook,
    qualification_evidence_store_sha256: str,
    qualification_policy_store_sha256: str,
    holdout_evidence_store_sha256: str,
    holdout_policy_store_sha256: str,
) -> Phase22HoldoutLineageAssessment:
    if not isinstance(phase21_manifest, Phase21PolicyFreezeManifest):
        raise CiboCapitalManagementError(
            "Phase22 requires canonical Phase21 freeze manifest"
        )
    if not isinstance(
        qualification_evidence_book,
        VersionedPhase20ForwardEvidenceBook,
    ):
        raise CiboCapitalManagementError(
            "Phase22 qualification evidence book must be canonical"
        )
    if not isinstance(
        holdout_evidence_book,
        VersionedPhase20ForwardEvidenceBook,
    ):
        raise CiboCapitalManagementError(
            "Phase22 holdout evidence book must be canonical"
        )
    if not isinstance(
        holdout_policy_book,
        VersionedPhase20ForwardPolicyBook,
    ):
        raise CiboCapitalManagementError(
            "Phase22 holdout policy book must be canonical"
        )

    for name, value in (
        (
            "qualification_evidence_store_sha256",
            qualification_evidence_store_sha256,
        ),
        (
            "qualification_policy_store_sha256",
            qualification_policy_store_sha256,
        ),
        ("holdout_evidence_store_sha256", holdout_evidence_store_sha256),
        ("holdout_policy_store_sha256", holdout_policy_store_sha256),
    ):
        _require_sha256(value, name)

    reasons: list[str] = []
    qualification = phase21_manifest.qualification
    if (
        qualification_evidence_store_sha256
        != qualification.evidence_store_sha256
    ):
        reasons.append("QUALIFICATION_EVIDENCE_STORE_LINEAGE_MISMATCH")
    if (
        qualification_policy_store_sha256
        != qualification.policy_store_sha256
    ):
        reasons.append("QUALIFICATION_POLICY_STORE_LINEAGE_MISMATCH")
    if holdout_evidence_store_sha256 == qualification_evidence_store_sha256:
        reasons.append("HOLDOUT_EVIDENCE_STORE_REUSED")
    if holdout_policy_store_sha256 == qualification_policy_store_sha256:
        reasons.append("HOLDOUT_POLICY_STORE_REUSED")

    decisions = holdout_evidence_book.decisions
    if not decisions:
        reasons.append("HOLDOUT_DECISION_POPULATION_EMPTY")

    qualification_shas = {
        item.evidence_sha256 for item in qualification_evidence_book.decisions
    }
    holdout_shas = {item.evidence_sha256 for item in decisions}
    if qualification_shas.intersection(holdout_shas):
        reasons.append("QUALIFICATION_DECISION_REUSED_IN_HOLDOUT")

    collector_shas: set[str] = set()
    decision_by_sha = {}
    holdout = PREREGISTERED_USD60_HOLDOUT
    for decision in decisions:
        decision_by_sha[decision.evidence_sha256] = decision
        if not (
            holdout.start_at
            <= decision.decision_at
            < holdout.end_exclusive_at
        ):
            reasons.append("HOLDOUT_DECISION_OUTSIDE_PREREGISTERED_WINDOW")
        if (
            decision.sealed_at is None
            or decision.sealed_at <= phase21_manifest.frozen_at
        ):
            reasons.append("HOLDOUT_DECISION_SEAL_NOT_POST_PHASE21_FREEZE")
        if decision.candidate_id != phase21_manifest.candidate_id:
            reasons.append("HOLDOUT_CANDIDATE_IDENTITY_DRIFT")
        if decision.code_sha != phase21_manifest.candidate_code_sha:
            reasons.append("HOLDOUT_POLICY_CODE_SHA_DRIFT")
        if (
            decision.parameter_sha256
            != phase21_manifest.candidate_parameter_sha256
        ):
            reasons.append("HOLDOUT_PARAMETER_DIGEST_DRIFT")
        if not decision.sealed_within_deadline:
            reasons.append("HOLDOUT_DECISION_NOT_CAUSALLY_SEALED")
        if decision.collector_git_sha is None:
            reasons.append("HOLDOUT_COLLECTOR_GIT_LINEAGE_INCOMPLETE")
        else:
            collector_shas.add(decision.collector_git_sha)

    if len(collector_shas) > 1:
        reasons.append("HOLDOUT_COLLECTOR_GIT_LINEAGE_NOT_SINGLE_SHA")

    policy_shas = {
        item.evidence_sha256 for item in holdout_policy_book.decisions
    }
    if policy_shas != holdout_shas:
        reasons.append("HOLDOUT_POLICY_DECISION_SET_MISMATCH")

    for outcome in holdout_evidence_book.outcomes:
        outcome_decision = decision_by_sha.get(
            outcome.decision_evidence_sha256
        )
        if outcome_decision is None:
            reasons.append("HOLDOUT_OUTCOME_WITHOUT_DECISION")
            continue
        if (
            outcome.signal_fingerprint
            not in outcome_decision.signal_fingerprints
        ):
            reasons.append("HOLDOUT_OUTCOME_SIGNAL_NOT_IN_DECISION")
        if outcome.observed_at <= outcome_decision.decision_at:
            reasons.append("HOLDOUT_OUTCOME_NOT_POST_DECISION")

    ordered_times = tuple(item.decision_at for item in decisions)
    unique_reasons = tuple(dict.fromkeys(reasons))
    return Phase22HoldoutLineageAssessment(
        lineage_valid=not unique_reasons,
        reasons=unique_reasons,
        decision_epochs=len(decisions),
        policy_decisions=len(holdout_policy_book.decisions),
        outcomes=len(holdout_evidence_book.outcomes),
        collector_git_shas=tuple(sorted(collector_shas)),
        earliest_decision_at=min(ordered_times) if ordered_times else None,
        latest_decision_at=max(ordered_times) if ordered_times else None,
    )


def _require_sha256(value: str, name: str) -> None:
    if _SHA256_RE.fullmatch(value) is None:
        raise CiboCapitalManagementError(
            f"Phase22 {name} must be sha256: plus 64 lowercase hex"
        )
