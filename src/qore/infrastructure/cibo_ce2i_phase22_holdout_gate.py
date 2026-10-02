"""Phase 22 sealed-holdout lineage gate for CIBO.

This gate proves only that a holdout population is fresh, disjoint and bound to
an exact Phase21-frozen policy. It does not invent economic thresholds and does
not claim holdout PASS. A separate pre-registered Phase22 evaluation plan is
still required before economic certification.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_holdout_registry import (
    ACTIVE_USD60_HOLDOUT_CANDIDATE,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_policy_store import (
    VersionedPhase20ForwardPolicyBook,
)
from qore.infrastructure.cibo_ce2i_phase21_policy_freeze import (
    Phase21PolicyFreezeManifest,
)
from qore.infrastructure.cibo_phase21_shadow_qualification_lineage import (
    Phase21ShadowQualificationLineageReceipt,
)
from qore.infrastructure.cibo_ce2i_qualification_evidence_protocol import (
    Phase20QualificationEvidenceBook,
    require_qualification_evidence_book,
)
from qore.infrastructure.cibo_phase22_holdout_v2_source_receipt import (
    V2_SOURCE_BINDINGS,
    phase22_v2_holdout_source_receipt_sha256,
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
    phase21_manifest: (
        Phase21PolicyFreezeManifest
        | Phase21ShadowQualificationLineageReceipt
    ),
    qualification_evidence_book: Phase20QualificationEvidenceBook | None,
    holdout_evidence_book: Phase20QualificationEvidenceBook,
    holdout_policy_book: VersionedPhase20ForwardPolicyBook,
    qualification_evidence_store_sha256: str | None,
    qualification_policy_store_sha256: str | None,
    holdout_evidence_store_sha256: str,
    holdout_policy_store_sha256: str,
) -> Phase22HoldoutLineageAssessment:
    canonical_phase21 = isinstance(
        phase21_manifest,
        Phase21PolicyFreezeManifest,
    )
    shadow_phase21 = isinstance(
        phase21_manifest,
        Phase21ShadowQualificationLineageReceipt,
    )
    if not canonical_phase21 and not shadow_phase21:
        raise CiboCapitalManagementError(
            "Phase22 requires a recognized Phase21 frozen-policy lineage"
        )
    if canonical_phase21:
        qualification_evidence_book = require_qualification_evidence_book(
            qualification_evidence_book,
            context="Phase22 qualification evidence",
        )
        if (
            qualification_evidence_store_sha256 is None
            or qualification_policy_store_sha256 is None
        ):
            raise CiboCapitalManagementError(
                "canonical Phase21 lineage requires qualification store digests"
            )
    else:
        if (
            qualification_evidence_book is not None
            or qualification_evidence_store_sha256 is not None
            or qualification_policy_store_sha256 is not None
        ):
            raise CiboCapitalManagementError(
                "historical-shadow Phase21 lineage forbids forward "
                "qualification relabelling"
            )
    holdout_evidence_book = require_qualification_evidence_book(
        holdout_evidence_book,
        context="Phase22 holdout evidence",
    )
    if not isinstance(
        holdout_policy_book,
        VersionedPhase20ForwardPolicyBook,
    ):
        raise CiboCapitalManagementError(
            "Phase22 holdout policy book must be canonical"
        )

    _require_sha256(
        holdout_evidence_store_sha256,
        "holdout_evidence_store_sha256",
    )
    _require_sha256(
        holdout_policy_store_sha256,
        "holdout_policy_store_sha256",
    )

    reasons: list[str] = []
    if canonical_phase21:
        assert isinstance(phase21_manifest, Phase21PolicyFreezeManifest)
        assert qualification_evidence_store_sha256 is not None
        assert qualification_policy_store_sha256 is not None
        qualification = phase21_manifest.qualification
        _require_sha256(
            qualification_evidence_store_sha256,
            "qualification_evidence_store_sha256",
        )
        _require_sha256(
            qualification_policy_store_sha256,
            "qualification_policy_store_sha256",
        )
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
    else:
        assert isinstance(
            phase21_manifest,
            Phase21ShadowQualificationLineageReceipt,
        )
        if (
            holdout_evidence_store_sha256
            in phase21_manifest.protected_source_digests
        ):
            reasons.append("HOLDOUT_EVIDENCE_REUSES_SHADOW_SOURCE")
        if (
            holdout_policy_store_sha256
            in phase21_manifest.protected_source_digests
        ):
            reasons.append("HOLDOUT_POLICY_REUSES_SHADOW_SOURCE")

    decisions = holdout_evidence_book.decisions
    if not decisions:
        reasons.append("HOLDOUT_DECISION_POPULATION_EMPTY")

    holdout_shas = {item.evidence_sha256 for item in decisions}
    if canonical_phase21:
        assert qualification_evidence_book is not None
        qualification_shas = {
            item.evidence_sha256 for item in qualification_evidence_book.decisions
        }
        if qualification_shas.intersection(holdout_shas):
            reasons.append("QUALIFICATION_DECISION_REUSED_IN_HOLDOUT")

    historical_replay = (
        getattr(
            holdout_evidence_book,
            "qualification_evidence_kind",
            "FORWARD_OBSERVED",
        )
        == "HISTORICAL_REPLAY_OBSERVED"
    )
    expected_source_collectors = tuple(
        sorted({item.collector_git_sha for item in V2_SOURCE_BINDINGS})
    )
    collector_shas: set[str] = set()
    if historical_replay:
        if (
            getattr(holdout_evidence_book, "source_receipt_sha256", None)
            != phase22_v2_holdout_source_receipt_sha256()
        ):
            reasons.append("HOLDOUT_SOURCE_RECEIPT_LINEAGE_MISMATCH")
        if (
            tuple(
                getattr(
                    holdout_evidence_book,
                    "source_collector_git_shas",
                    (),
                )
            )
            != expected_source_collectors
        ):
            reasons.append("HOLDOUT_SOURCE_COLLECTOR_LINEAGE_MISMATCH")
        collector_shas.update(expected_source_collectors)
    decision_by_sha = {}
    holdout = ACTIVE_USD60_HOLDOUT_CANDIDATE
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
        if historical_replay:
            try:
                payload = json.loads(decision.canonical_payload_json)
            except json.JSONDecodeError:
                payload = {}
            source_lineage = (
                payload.get("source_lineage")
                if isinstance(payload, dict)
                else None
            )
            if not isinstance(source_lineage, dict):
                reasons.append("HOLDOUT_DECISION_SOURCE_LINEAGE_INCOMPLETE")
            else:
                raw_collectors = source_lineage.get("collector_git_shas")
                if (
                    source_lineage.get("source_receipt_sha256")
                    != phase22_v2_holdout_source_receipt_sha256()
                    or not isinstance(raw_collectors, list)
                    or tuple(raw_collectors) != expected_source_collectors
                ):
                    reasons.append("HOLDOUT_DECISION_SOURCE_LINEAGE_MISMATCH")
        elif decision.collector_git_sha is None:
            reasons.append("HOLDOUT_COLLECTOR_GIT_LINEAGE_INCOMPLETE")
        else:
            collector_shas.add(decision.collector_git_sha)

    if not historical_replay and len(collector_shas) > 1:
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
