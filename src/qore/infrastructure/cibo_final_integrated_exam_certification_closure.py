"""Deterministic final certification closure and scientific seal for CIBO.

The closure transition is deliberately downstream of both certification exams.
It changes only their two ledger rows from OPEN to COMPLETED_AND_PROVEN.  The
seal is emitted only after the resulting closure HEAD passes STRICT Zero Open.
Neither object grants LIVE, execution, Risk, real-capital or merge authority.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_final_certification import (
    Phase22QualificationReceipt,
)
from qore.infrastructure.cibo_final_integrated_exam import (
    FinalIntegratedExamReport,
    FinalIntegratedExamStatus,
)
from qore.infrastructure.cibo_final_integrated_exam_assembly import (
    FinalIntegratedControlPackage,
)
from qore.infrastructure.cibo_scientific_closure_41 import (
    CANONICAL_PROVIDER_IDENTITY,
)
from qore.infrastructure.cibo_world_cup_maximum_capability_exam import (
    WorldCupMaximumCapabilityReport,
    WorldCupMaximumCapabilityStatus,
    final_integrated_exam_report_sha256,
)
from qore.infrastructure.cibo_world_cup_maximum_capability_exam_assembly import (
    WorldCupControlPackage,
)

CLOSURE_ID = "CIBO_FINAL_CERTIFICATION_CLOSURE_V1"
SEAL_ID = "CIBO_CERTIFICATION_SEAL_V1"
_LEDGER_SCHEMA = "QORE_CIBO_MASTER_OPEN_WORK_LEDGER_V1"
_ZERO_OPEN_SCHEMA = "QORE_CIBO_ZERO_OPEN_WORK_GATE_V1"
_EXAM_IDS = (
    "FINAL_INTEGRATED_CIBO_EXAM",
    "WORLD_CUP_MAXIMUM_CAPABILITY_EXAM",
)
_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_HOLDOUT_ID_RE = re.compile(
    r"^CIBO_USD60_6M_HOLDOUT_\\d{4}-\\d{2}-\\d{2}_"
    r"\\d{4}-\\d{2}-\\d{2}_V\\d+$"
)


class CiboCertificationSealStatus(StrEnum):
    CERTIFIED = "CIBO_CERTIFIED"


def _canonical_sha256(payload: Any) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _world_report_sha256(report: WorldCupMaximumCapabilityReport) -> str:
    payload = asdict(report)
    payload["status"] = report.status.value
    return _canonical_sha256(payload)


def _ledger_sha256(payload: dict[str, Any]) -> str:
    return _canonical_sha256(payload)


@dataclass(frozen=True, slots=True)
class CiboCertificationClosureTransition:
    closure_id: str
    holdout_candidate_id: str
    evidence_head_sha: str
    phase22_qualification_artifact_sha256: str
    final_integrated_package_sha256: str
    final_integrated_report_sha256: str
    world_cup_package_sha256: str
    world_cup_report_sha256: str
    source_truth_receipt_sha256: str
    provider_risk_cma_receipt_sha256: str
    scientific_closure_receipt_sha256: str
    policy_identity_sha256: str
    provider_identity: str
    pre_ledger_sha256: str
    closed_ledger_sha256: str
    changed_workstream_ids: tuple[str, ...]
    mandatory_count: int
    terminal_count: int
    open_count: int
    final_certification_candidate: bool
    production_authority: bool = False

    def __post_init__(self) -> None:
        if self.closure_id != CLOSURE_ID:
            raise CiboCapitalManagementError(
                "CIBO certification closure identity drift"
            )
        if _HOLDOUT_ID_RE.fullmatch(self.holdout_candidate_id) is None:
            raise CiboCapitalManagementError(
                "CIBO certification closure holdout identity invalid"
            )
        if _SHA1_RE.fullmatch(self.evidence_head_sha) is None:
            raise CiboCapitalManagementError(
                "CIBO certification closure evidence HEAD invalid"
            )
        for name in (
            "phase22_qualification_artifact_sha256",
            "final_integrated_package_sha256",
            "final_integrated_report_sha256",
            "world_cup_package_sha256",
            "world_cup_report_sha256",
            "source_truth_receipt_sha256",
            "provider_risk_cma_receipt_sha256",
            "scientific_closure_receipt_sha256",
            "policy_identity_sha256",
            "pre_ledger_sha256",
            "closed_ledger_sha256",
        ):
            if _SHA256_RE.fullmatch(getattr(self, name)) is None:
                raise CiboCapitalManagementError(
                    f"CIBO certification closure {name} invalid"
                )
        if self.provider_identity != CANONICAL_PROVIDER_IDENTITY:
            raise CiboCapitalManagementError(
                "CIBO certification closure provider identity drift"
            )
        if self.changed_workstream_ids != _EXAM_IDS:
            raise CiboCapitalManagementError(
                "CIBO certification closure may change only the two exam rows"
            )
        if (
            self.mandatory_count != 64
            or self.terminal_count != 64
            or self.open_count != 0
            or self.final_certification_candidate is not False
        ):
            raise CiboCapitalManagementError(
                "CIBO certification closure requires 64/64/0 before STRICT promotion"
            )
        if self.production_authority:
            raise CiboCapitalManagementError(
                "CIBO certification closure grants no production authority"
            )

    def fingerprint(self) -> str:
        return _canonical_sha256(asdict(self))


@dataclass(frozen=True, slots=True)
class CiboCertificationSeal:
    seal_id: str
    status: CiboCertificationSealStatus
    holdout_candidate_id: str
    evidence_head_sha: str
    closure_head_sha: str
    phase22_qualification_artifact_sha256: str
    closure_transition_sha256: str
    closed_ledger_sha256: str
    strict_zero_open_artifact_sha256: str
    source_truth_receipt_sha256: str
    provider_risk_cma_receipt_sha256: str
    scientific_closure_receipt_sha256: str
    final_integrated_package_sha256: str
    final_integrated_report_sha256: str
    world_cup_package_sha256: str
    world_cup_report_sha256: str
    policy_identity_sha256: str
    provider_identity: str
    mandatory_count: int
    terminal_count: int
    open_count: int
    certified_at: datetime
    live_authorized: bool = False
    real_capital_authorized: bool = False
    production_authorized: bool = False
    merge_authorized: bool = False
    production_authority: bool = False

    def __post_init__(self) -> None:
        if self.seal_id != SEAL_ID:
            raise CiboCapitalManagementError("CIBO certification seal identity drift")
        if self.status is not CiboCertificationSealStatus.CERTIFIED:
            raise CiboCapitalManagementError("CIBO certification seal status drift")
        if _HOLDOUT_ID_RE.fullmatch(self.holdout_candidate_id) is None:
            raise CiboCapitalManagementError(
                "CIBO certification seal holdout identity invalid"
            )
        for name in ("evidence_head_sha", "closure_head_sha"):
            if _SHA1_RE.fullmatch(getattr(self, name)) is None:
                raise CiboCapitalManagementError(
                    f"CIBO certification seal {name} invalid"
                )
        for name in (
            "phase22_qualification_artifact_sha256",
            "closure_transition_sha256",
            "closed_ledger_sha256",
            "strict_zero_open_artifact_sha256",
            "source_truth_receipt_sha256",
            "provider_risk_cma_receipt_sha256",
            "scientific_closure_receipt_sha256",
            "final_integrated_package_sha256",
            "final_integrated_report_sha256",
            "world_cup_package_sha256",
            "world_cup_report_sha256",
            "policy_identity_sha256",
        ):
            if _SHA256_RE.fullmatch(getattr(self, name)) is None:
                raise CiboCapitalManagementError(
                    f"CIBO certification seal {name} invalid"
                )
        if self.provider_identity != CANONICAL_PROVIDER_IDENTITY:
            raise CiboCapitalManagementError(
                "CIBO certification seal provider identity drift"
            )
        if (
            self.mandatory_count != 64
            or self.terminal_count != 64
            or self.open_count != 0
        ):
            raise CiboCapitalManagementError(
                "CIBO certification seal requires explicit 64/64/0 topology"
            )
        if self.certified_at.tzinfo is None or self.certified_at.utcoffset() is None:
            raise CiboCapitalManagementError(
                "CIBO certification seal certified_at must be timezone-aware"
            )
        if (
            self.live_authorized
            or self.real_capital_authorized
            or self.production_authorized
            or self.merge_authorized
            or self.production_authority
        ):
            raise CiboCapitalManagementError(
                "CIBO certification seal cannot grant operational authority"
            )

    def fingerprint(self) -> str:
        payload = asdict(self)
        payload["status"] = self.status.value
        payload["certified_at"] = self.certified_at.isoformat()
        return _canonical_sha256(payload)


def build_certification_closure_ledger(
    *,
    pre_ledger: dict[str, Any],
    holdout_candidate_id: str,
    final_package: FinalIntegratedControlPackage,
    final_report: FinalIntegratedExamReport,
    world_cup_package: WorldCupControlPackage,
    world_cup_report: WorldCupMaximumCapabilityReport,
) -> tuple[dict[str, Any], CiboCertificationClosureTransition]:
    """Terminalize only the two exam rows after both receipt-bound exams PASS."""

    if _HOLDOUT_ID_RE.fullmatch(holdout_candidate_id) is None:
        raise CiboCapitalManagementError(
            "CIBO certification closure holdout identity invalid"
        )
    if pre_ledger.get("schema") != _LEDGER_SCHEMA:
        raise CiboCapitalManagementError(
            "CIBO certification closure ledger schema drift"
        )
    if not isinstance(final_package, FinalIntegratedControlPackage):
        raise CiboCapitalManagementError(
            "CIBO certification closure requires canonical Final package"
        )
    if not isinstance(final_report, FinalIntegratedExamReport):
        raise CiboCapitalManagementError(
            "CIBO certification closure requires canonical Final report"
        )
    if not isinstance(world_cup_package, WorldCupControlPackage):
        raise CiboCapitalManagementError(
            "CIBO certification closure requires canonical World Cup package"
        )
    if not isinstance(world_cup_report, WorldCupMaximumCapabilityReport):
        raise CiboCapitalManagementError(
            "CIBO certification closure requires canonical World Cup report"
        )
    if final_report.status is not FinalIntegratedExamStatus.PASS or final_report.blockers:
        raise CiboCapitalManagementError(
            "CIBO certification closure requires Final Integrated PASS"
        )
    if (
        world_cup_report.status is not WorldCupMaximumCapabilityStatus.PASS
        or world_cup_report.blockers
    ):
        raise CiboCapitalManagementError(
            "CIBO certification closure requires World Cup PASS"
        )

    evidence_head = final_report.integrated_head_sha
    if (
        final_package.integrated_git_sha != evidence_head
        or world_cup_package.integrated_git_sha != evidence_head
        or world_cup_report.integrated_head_sha != evidence_head
    ):
        raise CiboCapitalManagementError(
            "CIBO certification closure exam/package HEAD drift"
        )
    final_report_sha = final_integrated_exam_report_sha256(final_report)
    if (
        world_cup_package.final_integrated_exam_report_sha256 != final_report_sha
        or world_cup_report.final_integrated_exam_report_sha256 != final_report_sha
    ):
        raise CiboCapitalManagementError(
            "CIBO certification closure Final report lineage drift"
        )

    rows = pre_ledger.get("workstreams")
    summary = pre_ledger.get("current_summary")
    if not isinstance(rows, list) or not isinstance(summary, dict):
        raise CiboCapitalManagementError(
            "CIBO certification closure ledger surface invalid"
        )
    mandatory = [row for row in rows if isinstance(row, dict) and row.get("mandatory") is True]
    terminal = [row for row in mandatory if row.get("terminal_disposition") is not None]
    open_ids = tuple(
        str(row.get("id"))
        for row in mandatory
        if row.get("terminal_disposition") is None
    )
    blocking_external = tuple(
        str(row.get("id"))
        for row in mandatory
        if row.get("terminal_disposition") == "EXTERNAL_DEPENDENCY_BLOCKED"
        and row.get("certification_blocking") is True
    )
    if (
        len(mandatory) != 64
        or len(terminal) != 62
        or open_ids != _EXAM_IDS
        or blocking_external
    ):
        raise CiboCapitalManagementError(
            "CIBO certification closure requires clean 64/62/2 pre-close ledger"
        )
    expected_summary = {
        "mandatory_count": 64,
        "terminal_count": 62,
        "open_count": 2,
        "zero_open_work_pass": False,
        "final_certification_candidate": False,
    }
    if summary != expected_summary:
        raise CiboCapitalManagementError(
            "CIBO certification closure pre-close summary drift"
        )

    closed = copy.deepcopy(pre_ledger)
    by_id = {
        str(row.get("id")): row
        for row in closed["workstreams"]
        if isinstance(row, dict)
    }
    final_row = by_id.get("FINAL_INTEGRATED_CIBO_EXAM")
    world_row = by_id.get("WORLD_CUP_MAXIMUM_CAPABILITY_EXAM")
    if final_row is None or world_row is None:
        raise CiboCapitalManagementError(
            "CIBO certification closure exam rows missing"
        )

    final_package_sha = final_package.fingerprint()
    world_package_sha = world_cup_package.fingerprint()
    world_report_sha = _world_report_sha256(world_cup_report)
    final_receipts = {
        receipt.receipt_id: receipt
        for receipt in final_package.receipts
    }
    source_truth_sha = final_receipts[
        "P1_SOURCE_OF_TRUTH_RECONCILED"
    ].source_artifact_sha256
    provider_risk_cma_sha = final_receipts[
        "P4_PROVIDER_RISK_CMA_FORWARD_TRUTH"
    ].source_artifact_sha256
    scientific_closure_sha = final_receipts[
        "P7_SCIENTIFIC_CLOSURE"
    ].source_artifact_sha256

    final_row["current_maturity"] = "COMPLETED_AND_PROVEN_FINAL_INTEGRATED_PASS"
    final_row["terminal_disposition"] = "COMPLETED_AND_PROVEN"
    final_row["blockers"] = []
    final_row["evidence_refs"] = list(final_row["evidence_refs"]) + [
        f"final-integrated-package:{final_package_sha}",
        f"final-integrated-report:{final_report_sha}",
    ]
    final_row["next_gate"] = (
        "Terminal. World Cup PASS and strict final closure remain downstream."
    )

    world_row["current_maturity"] = "COMPLETED_AND_PROVEN_WORLD_CUP_PASS"
    world_row["terminal_disposition"] = "COMPLETED_AND_PROVEN"
    world_row["blockers"] = []
    world_row["evidence_refs"] = list(world_row["evidence_refs"]) + [
        f"world-cup-package:{world_package_sha}",
        f"world-cup-report:{world_report_sha}",
    ]
    world_row["next_gate"] = (
        "Terminal. Run STRICT Zero Open and emit the certification seal."
    )
    closed["current_summary"] = {
        "mandatory_count": 64,
        "terminal_count": 64,
        "open_count": 0,
        "zero_open_work_pass": True,
        "final_certification_candidate": False,
    }

    transition = CiboCertificationClosureTransition(
        closure_id=CLOSURE_ID,
        holdout_candidate_id=holdout_candidate_id,
        evidence_head_sha=evidence_head,
        phase22_qualification_artifact_sha256=(
            final_package.phase22_qualification_artifact_sha256
        ),
        final_integrated_package_sha256=final_package_sha,
        final_integrated_report_sha256=final_report_sha,
        world_cup_package_sha256=world_package_sha,
        world_cup_report_sha256=world_report_sha,
        source_truth_receipt_sha256=source_truth_sha,
        provider_risk_cma_receipt_sha256=provider_risk_cma_sha,
        scientific_closure_receipt_sha256=scientific_closure_sha,
        policy_identity_sha256=final_package.policy_identity_sha256,
        provider_identity=CANONICAL_PROVIDER_IDENTITY,
        pre_ledger_sha256=_ledger_sha256(pre_ledger),
        closed_ledger_sha256=_ledger_sha256(closed),
        changed_workstream_ids=_EXAM_IDS,
        mandatory_count=64,
        terminal_count=64,
        open_count=0,
        final_certification_candidate=False,
    )
    return closed, transition


def build_cibo_certification_seal(
    *,
    transition: CiboCertificationClosureTransition,
    closed_ledger: dict[str, Any],
    strict_zero_open_artifact_json: str,
    closure_head_sha: str,
    phase22_receipt: Phase22QualificationReceipt,
    certified_at: datetime,
) -> CiboCertificationSeal:
    """Emit the scientific certification seal after STRICT Zero Open PASS."""

    if not isinstance(transition, CiboCertificationClosureTransition):
        raise CiboCapitalManagementError(
            "CIBO certification seal requires canonical closure transition"
        )
    if not isinstance(phase22_receipt, Phase22QualificationReceipt):
        raise CiboCapitalManagementError(
            "CIBO certification seal requires canonical Phase22 receipt"
        )
    if _SHA1_RE.fullmatch(closure_head_sha) is None:
        raise CiboCapitalManagementError(
            "CIBO certification seal closure HEAD invalid"
        )
    if _ledger_sha256(closed_ledger) != transition.closed_ledger_sha256:
        raise CiboCapitalManagementError(
            "CIBO certification seal closed-ledger digest drift"
        )
    if (
        phase22_receipt.qualification_artifact_sha256
        != transition.phase22_qualification_artifact_sha256
    ):
        raise CiboCapitalManagementError(
            "CIBO certification seal Phase22 lineage drift"
        )
    try:
        strict = json.loads(strict_zero_open_artifact_json)
    except json.JSONDecodeError as error:
        raise CiboCapitalManagementError(
            "CIBO certification seal STRICT artifact invalid JSON"
        ) from error
    if not isinstance(strict, dict):
        raise CiboCapitalManagementError(
            "CIBO certification seal STRICT artifact must be object"
        )
    expected_strict = {
        "schema": _ZERO_OPEN_SCHEMA,
        "scope": "STRICT",
        "pass": True,
        "mandatory_workstream_count": 64,
        "terminal_workstream_count": 64,
        "open_workstream_ids": [],
        "certification_blocking_external_dependency_ids": [],
        "missing_required_artifacts": [],
        "high_signal_marker_hits": [],
        "orphan_candidate_paths": [],
        "reasons": [],
    }
    for key, value in expected_strict.items():
        if strict.get(key) != value:
            raise CiboCapitalManagementError(
                f"CIBO certification seal STRICT field mismatch: {key}"
            )
    if certified_at.tzinfo is None or certified_at.utcoffset() is None:
        raise CiboCapitalManagementError(
            "CIBO certification seal certified_at must be timezone-aware"
        )
    if certified_at <= phase22_receipt.qualified_at:
        raise CiboCapitalManagementError(
            "CIBO certification seal must postdate Phase22 qualification"
        )

    strict_sha = "sha256:" + hashlib.sha256(
        strict_zero_open_artifact_json.encode("utf-8")
    ).hexdigest()
    return CiboCertificationSeal(
        seal_id=SEAL_ID,
        status=CiboCertificationSealStatus.CERTIFIED,
        holdout_candidate_id=transition.holdout_candidate_id,
        evidence_head_sha=transition.evidence_head_sha,
        closure_head_sha=closure_head_sha,
        phase22_qualification_artifact_sha256=(
            transition.phase22_qualification_artifact_sha256
        ),
        closure_transition_sha256=transition.fingerprint(),
        closed_ledger_sha256=transition.closed_ledger_sha256,
        strict_zero_open_artifact_sha256=strict_sha,
        source_truth_receipt_sha256=transition.source_truth_receipt_sha256,
        provider_risk_cma_receipt_sha256=(
            transition.provider_risk_cma_receipt_sha256
        ),
        scientific_closure_receipt_sha256=(
            transition.scientific_closure_receipt_sha256
        ),
        final_integrated_package_sha256=(
            transition.final_integrated_package_sha256
        ),
        final_integrated_report_sha256=(
            transition.final_integrated_report_sha256
        ),
        world_cup_package_sha256=transition.world_cup_package_sha256,
        world_cup_report_sha256=transition.world_cup_report_sha256,
        policy_identity_sha256=transition.policy_identity_sha256,
        provider_identity=transition.provider_identity,
        mandatory_count=64,
        terminal_count=64,
        open_count=0,
        certified_at=certified_at,
    )



def promote_certification_candidate_after_seal(
    *,
    closed_ledger: dict[str, Any],
    transition: CiboCertificationClosureTransition,
    seal: CiboCertificationSeal,
) -> dict[str, Any]:
    """Promote candidate=true only after STRICT-backed scientific seal exists."""

    if not isinstance(transition, CiboCertificationClosureTransition):
        raise CiboCapitalManagementError(
            "CIBO candidate promotion requires canonical closure transition"
        )
    if not isinstance(seal, CiboCertificationSeal):
        raise CiboCapitalManagementError(
            "CIBO candidate promotion requires canonical certification seal"
        )
    if seal.status is not CiboCertificationSealStatus.CERTIFIED:
        raise CiboCapitalManagementError(
            "CIBO candidate promotion requires CERTIFIED seal"
        )
    if _ledger_sha256(closed_ledger) != transition.closed_ledger_sha256:
        raise CiboCapitalManagementError(
            "CIBO candidate promotion closed-ledger digest drift"
        )
    if seal.closed_ledger_sha256 != transition.closed_ledger_sha256:
        raise CiboCapitalManagementError(
            "CIBO candidate promotion seal/ledger drift"
        )
    if seal.closure_transition_sha256 != transition.fingerprint():
        raise CiboCapitalManagementError(
            "CIBO candidate promotion seal/transition drift"
        )
    summary = closed_ledger.get("current_summary")
    if not isinstance(summary, dict):
        raise CiboCapitalManagementError(
            "CIBO candidate promotion ledger summary missing"
        )
    expected = {
        "mandatory_count": 64,
        "terminal_count": 64,
        "open_count": 0,
        "zero_open_work_pass": True,
        "final_certification_candidate": False,
    }
    if summary != expected:
        raise CiboCapitalManagementError(
            "CIBO candidate promotion requires pre-promotion 64/64 STRICT topology"
        )

    promoted = copy.deepcopy(closed_ledger)
    promoted["current_summary"]["final_certification_candidate"] = True
    return promoted
