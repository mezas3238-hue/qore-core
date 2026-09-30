"""GEN-C14 governed autonomous capital science.

GEN-C14 may formulate and advance falsifiable capital hypotheses through a
strict scientific state machine. It never mutates the productive control,
self-promotes a candidate, opens protected holdouts, or grants runtime
authority.

Research/governance only. Owner/governance promotion remains external.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)

GENC14_POLICY_ID = "CIBO_GENC14_GOVERNED_AUTONOMOUS_CAPITAL_SCIENCE_V1"
GENC14_FROZEN_AT = datetime(2026, 9, 30, 7, 55, tzinfo=UTC)
GENC14_POLICY_SHA256 = (
    "sha256:1a3d3673511f11114907825ab74d26f72f08bea6c115bf27dc8808fb72e9227a"
)


class Genc14ScienceStage(StrEnum):
    HYPOTHESIS = "HYPOTHESIS"
    PREREGISTERED = "PREREGISTERED"
    SIMULATION_PASS = "SIMULATION_PASS"
    OOS_PASS = "OOS_PASS"
    STRESS_PASS = "STRESS_PASS"
    TEMPORAL_REPLICATION_PASS = "TEMPORAL_REPLICATION_PASS"
    OWNER_REVIEW_REQUIRED = "OWNER_REVIEW_REQUIRED"
    FALSIFIED_AND_CLOSED = "FALSIFIED_AND_CLOSED"
    REJECTED_AND_CLOSED = "REJECTED_AND_CLOSED"


class Genc14EvidenceKind(StrEnum):
    PREREGISTRATION = "PREREGISTRATION"
    SIMULATION = "SIMULATION"
    OOS = "OOS"
    STRESS = "STRESS"
    TEMPORAL_REPLICATION = "TEMPORAL_REPLICATION"


_REQUIRED_EVIDENCE_BY_TARGET = {
    Genc14ScienceStage.PREREGISTERED: Genc14EvidenceKind.PREREGISTRATION,
    Genc14ScienceStage.SIMULATION_PASS: Genc14EvidenceKind.SIMULATION,
    Genc14ScienceStage.OOS_PASS: Genc14EvidenceKind.OOS,
    Genc14ScienceStage.STRESS_PASS: Genc14EvidenceKind.STRESS,
    Genc14ScienceStage.TEMPORAL_REPLICATION_PASS:
        Genc14EvidenceKind.TEMPORAL_REPLICATION,
}

_NEXT_PASS_STAGE = {
    Genc14ScienceStage.HYPOTHESIS: Genc14ScienceStage.PREREGISTERED,
    Genc14ScienceStage.PREREGISTERED: Genc14ScienceStage.SIMULATION_PASS,
    Genc14ScienceStage.SIMULATION_PASS: Genc14ScienceStage.OOS_PASS,
    Genc14ScienceStage.OOS_PASS: Genc14ScienceStage.STRESS_PASS,
    Genc14ScienceStage.STRESS_PASS:
        Genc14ScienceStage.TEMPORAL_REPLICATION_PASS,
    Genc14ScienceStage.TEMPORAL_REPLICATION_PASS:
        Genc14ScienceStage.OWNER_REVIEW_REQUIRED,
}

_TERMINAL = {
    Genc14ScienceStage.OWNER_REVIEW_REQUIRED,
    Genc14ScienceStage.FALSIFIED_AND_CLOSED,
    Genc14ScienceStage.REJECTED_AND_CLOSED,
}


def _aware(value: datetime, name: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise CiboCapitalManagementError(
            f"GEN-C14 {name} must be timezone-aware"
        )


def _sha(value: str, name: str) -> None:
    if (
        not isinstance(value, str)
        or not value.startswith("sha256:")
        or len(value) != 71
        or any(char not in "0123456789abcdef" for char in value[7:])
    ):
        raise CiboCapitalManagementError(
            f"GEN-C14 {name} must be canonical SHA-256"
        )


@dataclass(frozen=True, slots=True)
class Genc14CapitalHypothesis:
    hypothesis_id: str
    research_question: str
    candidate_policy_id: str
    candidate_policy_sha256: str
    current_control_policy_id: str
    current_control_policy_sha256: str
    created_at: datetime
    protected_holdout_ref: str | None = None
    outcome_selected: bool = False
    world_cup_target_fitted: bool = False
    productive_control_mutated: bool = False
    auto_promotion_allowed: bool = False

    def __post_init__(self) -> None:
        for name in (
            "hypothesis_id",
            "research_question",
            "candidate_policy_id",
            "current_control_policy_id",
        ):
            if not getattr(self, name):
                raise CiboCapitalManagementError(
                    f"GEN-C14 {name} is required"
                )
        _sha(self.candidate_policy_sha256, "candidate_policy_sha256")
        _sha(
            self.current_control_policy_sha256,
            "current_control_policy_sha256",
        )
        if self.candidate_policy_sha256 == self.current_control_policy_sha256:
            raise CiboCapitalManagementError(
                "GEN-C14 candidate must have distinct semantic identity"
            )
        _aware(self.created_at, "created_at")
        if (
            self.outcome_selected
            or self.world_cup_target_fitted
            or self.productive_control_mutated
            or self.auto_promotion_allowed
        ):
            raise CiboCapitalManagementError(
                "GEN-C14 hypothesis governance drift"
            )


@dataclass(frozen=True, slots=True)
class Genc14ScienceEvidence:
    evidence_id: str
    kind: Genc14EvidenceKind
    candidate_policy_sha256: str
    evaluated_at: datetime
    evidence_sha256: str
    passed: bool
    burned_data_used: bool = False
    protected_holdout_used: bool = False
    future_leakage_used: bool = False
    post_hoc_gate_changed: bool = False

    def __post_init__(self) -> None:
        if not self.evidence_id:
            raise CiboCapitalManagementError(
                "GEN-C14 evidence identity is required"
            )
        if type(self.kind) is not Genc14EvidenceKind:
            raise CiboCapitalManagementError(
                "GEN-C14 evidence kind is invalid"
            )
        _sha(self.candidate_policy_sha256, "candidate_policy_sha256")
        _aware(self.evaluated_at, "evaluated_at")
        _sha(self.evidence_sha256, "evidence_sha256")
        if type(self.passed) is not bool:
            raise CiboCapitalManagementError(
                "GEN-C14 evidence passed must be bool"
            )
        if (
            self.future_leakage_used
            or self.post_hoc_gate_changed
        ):
            raise CiboCapitalManagementError(
                "GEN-C14 evidence leakage/gate mutation is forbidden"
            )
        if self.kind is Genc14EvidenceKind.OOS and self.burned_data_used:
            raise CiboCapitalManagementError(
                "GEN-C14 OOS evidence cannot reuse burned data"
            )
        if (
            self.kind is not Genc14EvidenceKind.OOS
            and self.protected_holdout_used
        ):
            raise CiboCapitalManagementError(
                "GEN-C14 protected holdout cannot be consumed outside OOS gate"
            )


@dataclass(frozen=True, slots=True)
class Genc14ScienceRecord:
    science_id: str
    hypothesis: Genc14CapitalHypothesis
    stage: Genc14ScienceStage
    evidence: tuple[Genc14ScienceEvidence, ...]
    updated_at: datetime
    closure_reason: str | None = None
    current_control_policy_sha256: str = ""
    protected_holdout_opened_by_engine: bool = False
    productive_control_mutated: bool = False
    automatic_promotion: bool = False
    certification_claimed: bool = False
    owner_decision_recorded: bool = False

    def __post_init__(self) -> None:
        if not self.science_id:
            raise CiboCapitalManagementError(
                "GEN-C14 science record identity is required"
            )
        if not isinstance(self.hypothesis, Genc14CapitalHypothesis):
            raise CiboCapitalManagementError(
                "GEN-C14 science hypothesis is invalid"
            )
        if type(self.stage) is not Genc14ScienceStage:
            raise CiboCapitalManagementError(
                "GEN-C14 science stage is invalid"
            )
        _aware(self.updated_at, "updated_at")
        if self.updated_at < self.hypothesis.created_at:
            raise CiboCapitalManagementError(
                "GEN-C14 record cannot predate hypothesis"
            )
        if (
            self.current_control_policy_sha256
            != self.hypothesis.current_control_policy_sha256
        ):
            raise CiboCapitalManagementError(
                "GEN-C14 productive control SHA drift"
            )
        ids = tuple(item.evidence_id for item in self.evidence)
        if len(ids) != len(set(ids)):
            raise CiboCapitalManagementError(
                "GEN-C14 evidence ids must be unique"
            )
        if any(
            item.candidate_policy_sha256
            != self.hypothesis.candidate_policy_sha256
            for item in self.evidence
        ):
            raise CiboCapitalManagementError(
                "GEN-C14 evidence candidate lineage drift"
            )
        if self.stage in {
            Genc14ScienceStage.FALSIFIED_AND_CLOSED,
            Genc14ScienceStage.REJECTED_AND_CLOSED,
        } and not self.closure_reason:
            raise CiboCapitalManagementError(
                "GEN-C14 closed failure requires reason"
            )
        if (
            self.protected_holdout_opened_by_engine
            or self.productive_control_mutated
            or self.automatic_promotion
            or self.certification_claimed
            or self.owner_decision_recorded
        ):
            raise CiboCapitalManagementError(
                "GEN-C14 engine cannot promote/certify/mutate/decide for Owner"
            )

    @property
    def terminal(self) -> bool:
        return self.stage in _TERMINAL

    def fingerprint(self) -> str:
        payload = {
            "science_id": self.science_id,
            "hypothesis_id": self.hypothesis.hypothesis_id,
            "candidate_policy_sha256": (
                self.hypothesis.candidate_policy_sha256
            ),
            "current_control_policy_sha256": (
                self.current_control_policy_sha256
            ),
            "stage": self.stage.value,
            "evidence": [
                {
                    "evidence_id": item.evidence_id,
                    "kind": item.kind.value,
                    "evidence_sha256": item.evidence_sha256,
                    "passed": item.passed,
                }
                for item in self.evidence
            ],
            "updated_at": self.updated_at.isoformat(),
            "closure_reason": self.closure_reason,
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return "sha256:" + hashlib.sha256(raw).hexdigest()


def start_genc14_science(
    *,
    science_id: str,
    hypothesis: Genc14CapitalHypothesis,
) -> Genc14ScienceRecord:
    """Start a governed research lineage without touching current control."""

    if not science_id:
        raise CiboCapitalManagementError(
            "GEN-C14 science_id is required"
        )
    return Genc14ScienceRecord(
        science_id=science_id,
        hypothesis=hypothesis,
        stage=Genc14ScienceStage.HYPOTHESIS,
        evidence=(),
        updated_at=hypothesis.created_at,
        closure_reason=None,
        current_control_policy_sha256=(
            hypothesis.current_control_policy_sha256
        ),
    )


def advance_genc14_science(
    record: Genc14ScienceRecord,
    *,
    evidence: Genc14ScienceEvidence | None,
    advanced_at: datetime,
) -> Genc14ScienceRecord:
    """Advance exactly one scientific gate or close on failed evidence."""

    if not isinstance(record, Genc14ScienceRecord):
        raise CiboCapitalManagementError(
            "GEN-C14 advance requires canonical science record"
        )
    _aware(advanced_at, "advanced_at")
    if advanced_at < record.updated_at:
        raise CiboCapitalManagementError(
            "GEN-C14 advance time cannot move backward"
        )
    if record.terminal:
        raise CiboCapitalManagementError(
            "GEN-C14 terminal science record cannot advance"
        )

    target = _NEXT_PASS_STAGE.get(record.stage)
    if target is None:
        raise CiboCapitalManagementError(
            "GEN-C14 current stage has no legal next gate"
        )
    if target is Genc14ScienceStage.OWNER_REVIEW_REQUIRED:
        if evidence is not None:
            raise CiboCapitalManagementError(
                "GEN-C14 owner-review transition takes no synthetic evidence"
            )
        return replace(
            record,
            stage=target,
            updated_at=advanced_at,
        )

    if evidence is None:
        raise CiboCapitalManagementError(
            "GEN-C14 scientific gate requires evidence"
        )
    if not isinstance(evidence, Genc14ScienceEvidence):
        raise CiboCapitalManagementError(
            "GEN-C14 gate evidence is invalid"
        )
    required_kind = _REQUIRED_EVIDENCE_BY_TARGET[target]
    if evidence.kind is not required_kind:
        raise CiboCapitalManagementError(
            "GEN-C14 cannot skip or reorder scientific gates"
        )
    if evidence.evaluated_at > advanced_at:
        raise CiboCapitalManagementError(
            "GEN-C14 gate evidence comes from the future"
        )
    if evidence.evaluated_at < record.updated_at:
        raise CiboCapitalManagementError(
            "GEN-C14 gate evidence predates current science state"
        )
    if evidence.evidence_id in {
        item.evidence_id for item in record.evidence
    }:
        raise CiboCapitalManagementError(
            "GEN-C14 evidence cannot be reused"
        )

    evidence_rows = record.evidence + (evidence,)
    if not evidence.passed:
        return replace(
            record,
            stage=Genc14ScienceStage.FALSIFIED_AND_CLOSED,
            evidence=evidence_rows,
            updated_at=advanced_at,
            closure_reason=(
                f"{evidence.kind.value} gate failed; candidate falsified"
            ),
        )
    return replace(
        record,
        stage=target,
        evidence=evidence_rows,
        updated_at=advanced_at,
    )


def reject_genc14_science(
    record: Genc14ScienceRecord,
    *,
    rejected_at: datetime,
    reason: str,
) -> Genc14ScienceRecord:
    """Governance/research may reject a non-terminal candidate explicitly."""

    if not isinstance(record, Genc14ScienceRecord):
        raise CiboCapitalManagementError(
            "GEN-C14 reject requires canonical science record"
        )
    _aware(rejected_at, "rejected_at")
    if rejected_at < record.updated_at:
        raise CiboCapitalManagementError(
            "GEN-C14 rejection cannot predate record"
        )
    if record.terminal:
        raise CiboCapitalManagementError(
            "GEN-C14 terminal science record cannot be rejected again"
        )
    if not reason.strip():
        raise CiboCapitalManagementError(
            "GEN-C14 rejection reason is required"
        )
    return replace(
        record,
        stage=Genc14ScienceStage.REJECTED_AND_CLOSED,
        updated_at=rejected_at,
        closure_reason=reason.strip(),
    )
