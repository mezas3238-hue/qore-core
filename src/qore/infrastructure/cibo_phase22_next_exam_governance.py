"""Fail-closed governance for any Phase22 examination after consumed V2.

The consumed V2 one-shot is immutable and may never be replayed as fresh.
This module preregisters the deterministic next candidate window without
accessing market data or outcomes, and requires all execution-critical
prerequisites to be receipt-bound before another one-shot can be authorized.

It grants no source-read, Trader replay, broker mutation, LIVE, production,
real-capital, merge, or execution authority.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import StrEnum

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_holdout_registry import (
    CiboHoldoutCandidate,
    CiboHoldoutCandidateStatus,
    candidate_is_burn_clean_for_all_lineages,
)

CONSUMED_V2_CANDIDATE_ID = (
    "CIBO_USD60_6M_HOLDOUT_2015-10-19_2016-04-19_V2"
)
NEXT_CANDIDATE_ID = "CIBO_USD60_6M_HOLDOUT_2015-04-19_2015-10-19_V3"

NEXT_PHASE22_CANDIDATE = CiboHoldoutCandidate(
    candidate_id=NEXT_CANDIDATE_ID,
    start_at=datetime(2015, 4, 19, tzinfo=UTC),
    end_exclusive_at=datetime(2015, 10, 19, tzinfo=UTC),
    status=CiboHoldoutCandidateStatus.SOURCE_VALIDATION_PENDING,
    selection_rule=(
        "immediately preceding exact six-calendar-month block ending at the "
        "consumed V2 start boundary; selected mechanically without reading "
        "candidate source data or outcomes"
    ),
    outcome_data_inspected_at_selection=False,
    source_validation_complete=False,
)

_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


class NextPhase22ReadinessStatus(StrEnum):
    READY = "READY"
    NOT_READY = "NOT_READY"
    INVALID = "INVALID"


@dataclass(frozen=True, slots=True)
class NextPhase22ExamEvidence:
    """Receipt identities required before a new one-shot may be authorized."""

    candidate_id: str
    turtle_window_integrity_run_id: int | None = None
    turtle_window_integrity_head_sha: str | None = None
    advanced_predecision_evidence_freeze_sha256: str | None = None
    policy_code_bundle_lineage_sha256: str | None = None
    source_receipt_sha256: str | None = None
    source_validation_complete: bool = False
    source_outcomes_inspected: bool = False
    owner_authorization_id: str | None = None
    second_v2_execution_requested: bool = False
    broker_mutation_authorized: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False
    production_authorized: bool = False
    merge_authorized: bool = False

    def __post_init__(self) -> None:
        if not self.candidate_id:
            raise CiboCapitalManagementError(
                "next Phase22 candidate identity required"
            )
        if self.turtle_window_integrity_run_id is not None:
            if (
                not isinstance(self.turtle_window_integrity_run_id, int)
                or isinstance(self.turtle_window_integrity_run_id, bool)
                or self.turtle_window_integrity_run_id <= 0
            ):
                raise CiboCapitalManagementError(
                    "next Phase22 Turtle CI run id invalid"
                )
        if (
            self.turtle_window_integrity_head_sha is not None
            and _GIT_SHA_RE.fullmatch(self.turtle_window_integrity_head_sha)
            is None
        ):
            raise CiboCapitalManagementError(
                "next Phase22 Turtle CI head SHA invalid"
            )
        for name in (
            "advanced_predecision_evidence_freeze_sha256",
            "policy_code_bundle_lineage_sha256",
            "source_receipt_sha256",
        ):
            value = getattr(self, name)
            if value is not None and _SHA256_RE.fullmatch(value) is None:
                raise CiboCapitalManagementError(
                    f"next Phase22 {name} invalid"
                )
        for name in (
            "source_validation_complete",
            "source_outcomes_inspected",
            "second_v2_execution_requested",
            "broker_mutation_authorized",
            "live_authorized",
            "real_capital_authorized",
            "production_authorized",
            "merge_authorized",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(
                    f"next Phase22 {name} must be bool"
                )


@dataclass(frozen=True, slots=True)
class NextPhase22ExamReadiness:
    status: NextPhase22ReadinessStatus
    candidate_id: str
    blockers: tuple[str, ...]
    burn_clean: bool
    second_v2_execution_authorized: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.status is NextPhase22ReadinessStatus.READY and self.blockers:
            raise CiboCapitalManagementError(
                "next Phase22 READY cannot contain blockers"
            )
        if self.status is not NextPhase22ReadinessStatus.READY and not self.blockers:
            raise CiboCapitalManagementError(
                "next Phase22 non-ready status requires blockers"
            )
        if self.second_v2_execution_authorized or self.productive_authority:
            raise CiboCapitalManagementError(
                "next Phase22 readiness grants forbidden authority"
            )

    def payload(self) -> dict[str, object]:
        return {
            "schema": "qore.cibo.phase22.next-exam-readiness.v1",
            "status": self.status.value,
            "candidate_id": self.candidate_id,
            "blockers": list(self.blockers),
            "burn_clean": self.burn_clean,
            "second_v2_execution_authorized": False,
            "productive_authority": False,
        }

    def fingerprint(self) -> str:
        return _sha(self.payload())


def assess_next_phase22_exam(
    evidence: NextPhase22ExamEvidence,
) -> NextPhase22ExamReadiness:
    """Require every preregistered prerequisite; never rehabilitate consumed V2."""

    if not isinstance(evidence, NextPhase22ExamEvidence):
        raise CiboCapitalManagementError(
            "canonical next Phase22 evidence required"
        )

    burn_clean = candidate_is_burn_clean_for_all_lineages(
        NEXT_PHASE22_CANDIDATE
    )
    blockers: list[str] = []

    if (
        evidence.candidate_id == CONSUMED_V2_CANDIDATE_ID
        or evidence.second_v2_execution_requested
    ):
        blockers.append("CONSUMED_V2_SECOND_FRESH_EXECUTION_FORBIDDEN")

    if evidence.candidate_id != NEXT_CANDIDATE_ID:
        blockers.append("NEXT_CANDIDATE_IDENTITY_MISMATCH")

    if (
        evidence.turtle_window_integrity_run_id is None
        or evidence.turtle_window_integrity_head_sha is None
    ):
        blockers.append("TURTLE_SUBORDINATE_WINDOW_INTEGRITY_CI_REQUIRED")

    if evidence.advanced_predecision_evidence_freeze_sha256 is None:
        blockers.append(
            "ADVANCED_CE2I_PREDECISION_EVIDENCE_OR_ABSTENTION_FREEZE_REQUIRED"
        )

    if evidence.policy_code_bundle_lineage_sha256 is None:
        blockers.append("FROZEN_POLICY_CODE_BUNDLE_LINEAGE_REQUIRED")

    if (
        evidence.source_receipt_sha256 is None
        or not evidence.source_validation_complete
    ):
        blockers.append("NEW_HOLDOUT_SOURCE_VALIDATION_REQUIRED")

    if evidence.source_outcomes_inspected:
        blockers.append("NEW_HOLDOUT_OUTCOME_CONTAMINATION_FORBIDDEN")

    if not burn_clean:
        blockers.append("NEW_HOLDOUT_CONFIRMED_BURN_OVERLAP")

    if evidence.owner_authorization_id is None:
        blockers.append("NEW_ONE_SHOT_OWNER_AUTHORIZATION_REQUIRED")

    if any(
        (
            evidence.broker_mutation_authorized,
            evidence.live_authorized,
            evidence.real_capital_authorized,
            evidence.production_authorized,
            evidence.merge_authorized,
        )
    ):
        blockers.append("FORBIDDEN_PRODUCTIVE_AUTHORITY_PRESENT")

    blockers = list(dict.fromkeys(blockers))
    if (
        "CONSUMED_V2_SECOND_FRESH_EXECUTION_FORBIDDEN" in blockers
        or "NEW_HOLDOUT_OUTCOME_CONTAMINATION_FORBIDDEN" in blockers
        or "FORBIDDEN_PRODUCTIVE_AUTHORITY_PRESENT" in blockers
    ):
        status = NextPhase22ReadinessStatus.INVALID
    elif blockers:
        status = NextPhase22ReadinessStatus.NOT_READY
    else:
        status = NextPhase22ReadinessStatus.READY

    return NextPhase22ExamReadiness(
        status=status,
        candidate_id=evidence.candidate_id,
        blockers=tuple(blockers),
        burn_clean=burn_clean,
    )


CURRENT_NEXT_PHASE22_EVIDENCE = NextPhase22ExamEvidence(
    candidate_id=NEXT_CANDIDATE_ID,
    turtle_window_integrity_run_id=37016818566,
    turtle_window_integrity_head_sha=(
        "f8f2bfde3fed00750fd14a226bbb22b09da24bc0"
    ),
)

CURRENT_NEXT_PHASE22_READINESS = assess_next_phase22_exam(
    CURRENT_NEXT_PHASE22_EVIDENCE
)


def next_phase22_governance_payload() -> dict[str, object]:
    candidate = NEXT_PHASE22_CANDIDATE
    return {
        "schema": "qore.cibo.phase22.next-exam-governance.v1",
        "consumed_v2_candidate_id": CONSUMED_V2_CANDIDATE_ID,
        "consumed_v2_rerun_authorized": False,
        "candidate": {
            "candidate_id": candidate.candidate_id,
            "start_at": candidate.start_at.isoformat(),
            "end_exclusive_at": candidate.end_exclusive_at.isoformat(),
            "status": candidate.status.value,
            "selection_rule": candidate.selection_rule,
            "outcome_data_inspected_at_selection": False,
            "source_validation_complete": False,
            "burn_clean_against_confirmed_registry": (
                candidate_is_burn_clean_for_all_lineages(candidate)
            ),
        },
        "current_evidence": asdict(CURRENT_NEXT_PHASE22_EVIDENCE),
        "current_readiness": CURRENT_NEXT_PHASE22_READINESS.payload(),
        "hard_requirements": [
            "TURTLE_SUBORDINATE_WINDOW_INTEGRITY_CI",
            "ADVANCED_CE2I_PREDECISION_EVIDENCE_OR_EXPLICIT_ABSTENTION_FREEZE",
            "FROZEN_POLICY_CODE_BUNDLE_LINEAGE",
            "NEW_HOLDOUT_SOURCE_VALIDATION_WITHOUT_OUTCOME_INSPECTION",
            "NEW_ONE_SHOT_OWNER_AUTHORIZATION",
        ],
        "broker_mutation_authorized": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
        "merge_authorized": False,
        "productive_authority": False,
    }


def next_phase22_governance_sha256() -> str:
    return _sha(next_phase22_governance_payload())


def _sha(payload: object) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()
