"""Governed 62/64 -> 64/64 -> STRICT -> CIBO certification transition.

The transition is deliberately separate from operational deployment. Scientific
certification never grants LIVE, broker mutation, real-capital or merge authority.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_final_integrated_exam import (
    FinalIntegratedExamReport,
    FinalIntegratedExamStatus,
)
from qore.infrastructure.cibo_world_cup_maximum_capability_exam import (
    WorldCupMaximumCapabilityReport,
    WorldCupMaximumCapabilityStatus,
    final_integrated_exam_report_sha256,
)

_LEDGER_SCHEMA = "QORE_CIBO_MASTER_OPEN_WORK_LEDGER_V1"
_STRICT_SCHEMA = "QORE_CIBO_ZERO_OPEN_WORK_GATE_V1"
_SEAL_ID = "CIBO_CERTIFICATION_SEAL_V1"
_FINAL_ID = "FINAL_INTEGRATED_CIBO_EXAM"
_WORLD_ID = "WORLD_CUP_MAXIMUM_CAPABILITY_EXAM"
_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def _canonical_sha(payload: dict[str, Any]) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _ledger_sha(payload: dict[str, Any]) -> str:
    return _canonical_sha(payload)


def _world_cup_report_sha256(
    report: WorldCupMaximumCapabilityReport,
) -> str:
    if not isinstance(report, WorldCupMaximumCapabilityReport):
        raise CiboCapitalManagementError(
            "certification transition requires canonical World Cup report"
        )
    payload = asdict(report)
    payload["status"] = report.status.value
    return _canonical_sha(payload)


def _ledger_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(payload, dict) or payload.get("schema") != _LEDGER_SCHEMA:
        raise CiboCapitalManagementError(
            "certification transition ledger schema drift"
        )
    rows = payload.get("workstreams")
    if (
        not isinstance(rows, list)
        or any(not isinstance(item, dict) for item in rows)
    ):
        raise CiboCapitalManagementError(
            "certification transition ledger rows invalid"
        )
    return rows


def _mandatory_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [item for item in _ledger_rows(payload) if item.get("mandatory") is True]


def _summary(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("current_summary")
    if not isinstance(summary, dict):
        raise CiboCapitalManagementError(
            "certification transition ledger summary missing"
        )
    return summary


def _require_topology(
    payload: dict[str, Any],
    *,
    terminal_count: int,
    open_ids: tuple[str, ...],
) -> None:
    mandatory = _mandatory_rows(payload)
    if len(mandatory) != 64:
        raise CiboCapitalManagementError(
            "certification transition requires exactly 64 mandatory workstreams"
        )
    terminal = [item for item in mandatory if item.get("terminal_disposition") is not None]
    actual_open = tuple(
        str(item.get("id"))
        for item in mandatory
        if item.get("terminal_disposition") is None
    )
    if len(terminal) != terminal_count or actual_open != open_ids:
        raise CiboCapitalManagementError(
            "certification transition ledger topology drift"
        )
    summary = _summary(payload)
    expected = {
        "mandatory_count": 64,
        "terminal_count": terminal_count,
        "open_count": 64 - terminal_count,
        "zero_open_work_pass": terminal_count == 64,
        "final_certification_candidate": False,
    }
    for key, value in expected.items():
        if summary.get(key) != value:
            raise CiboCapitalManagementError(
                f"certification transition summary drift: {key}"
            )


def _require_no_external_blockers(payload: dict[str, Any]) -> None:
    blocking = tuple(
        str(item.get("id"))
        for item in _mandatory_rows(payload)
        if (
            item.get("certification_blocking") is True
            and item.get("terminal_disposition") == "EXTERNAL_DEPENDENCY_BLOCKED"
        )
    )
    if blocking:
        raise CiboCapitalManagementError(
            "certification transition external blockers remain: "
            + ",".join(blocking)
        )


def _row(payload: dict[str, Any], workstream_id: str) -> dict[str, Any]:
    matches = [
        item for item in _ledger_rows(payload)
        if item.get("id") == workstream_id
    ]
    if len(matches) != 1:
        raise CiboCapitalManagementError(
            f"certification transition missing/duplicate row: {workstream_id}"
        )
    return matches[0]


def transition_final_integrated_exam_pass(
    *,
    ledger: dict[str, Any],
    report: FinalIntegratedExamReport,
    integrated_git_sha: str,
) -> dict[str, Any]:
    """Close Final Integrated only after a real PASS and all other blockers clear."""

    if (
        not isinstance(report, FinalIntegratedExamReport)
        or report.status is not FinalIntegratedExamStatus.PASS
        or report.blockers
    ):
        raise CiboCapitalManagementError(
            "cannot close Final Integrated without canonical PASS"
        )
    if report.integrated_head_sha != integrated_git_sha:
        raise CiboCapitalManagementError(
            "Final Integrated transition HEAD drift"
        )
    _require_topology(
        ledger,
        terminal_count=62,
        open_ids=(_FINAL_ID, _WORLD_ID),
    )
    _require_no_external_blockers(ledger)

    result = copy.deepcopy(ledger)
    row = _row(result, _FINAL_ID)
    row["current_maturity"] = "FINAL_INTEGRATED_CIBO_EXAM_PASS_RECEIPT_BOUND"
    row["terminal_disposition"] = "COMPLETED_AND_PROVEN"
    row["blockers"] = []
    row["next_gate"] = (
        "Execute the mandatory World Cup Maximum Capability Exam."
    )
    evidence = list(row.get("evidence_refs", []))
    evidence.append(
        "final-integrated-report:"
        + final_integrated_exam_report_sha256(report)
    )
    row["evidence_refs"] = list(dict.fromkeys(evidence))
    result["current_summary"] = {
        "mandatory_count": 64,
        "terminal_count": 63,
        "open_count": 1,
        "zero_open_work_pass": False,
        "final_certification_candidate": False,
    }
    return result


def transition_world_cup_exam_pass(
    *,
    ledger: dict[str, Any],
    report: WorldCupMaximumCapabilityReport,
    integrated_git_sha: str,
) -> dict[str, Any]:
    """Close World Cup only after Final Integrated is already terminal."""

    if (
        not isinstance(report, WorldCupMaximumCapabilityReport)
        or report.status is not WorldCupMaximumCapabilityStatus.PASS
        or report.blockers
    ):
        raise CiboCapitalManagementError(
            "cannot close World Cup without canonical PASS"
        )
    if report.integrated_head_sha != integrated_git_sha:
        raise CiboCapitalManagementError(
            "World Cup transition HEAD drift"
        )
    _require_topology(
        ledger,
        terminal_count=63,
        open_ids=(_WORLD_ID,),
    )
    _require_no_external_blockers(ledger)
    final_row = _row(ledger, _FINAL_ID)
    if final_row.get("terminal_disposition") != "COMPLETED_AND_PROVEN":
        raise CiboCapitalManagementError(
            "World Cup transition requires terminal Final Integrated PASS"
        )

    result = copy.deepcopy(ledger)
    row = _row(result, _WORLD_ID)
    row["current_maturity"] = "WORLD_CUP_MAXIMUM_CAPABILITY_EXAM_PASS_RECEIPT_BOUND"
    row["terminal_disposition"] = "COMPLETED_AND_PROVEN"
    row["blockers"] = []
    row["next_gate"] = "Run STRICT Zero Open and emit certification seal."
    evidence = list(row.get("evidence_refs", []))
    evidence.append("world-cup-report:" + _world_cup_report_sha256(report))
    row["evidence_refs"] = list(dict.fromkeys(evidence))
    result["current_summary"] = {
        "mandatory_count": 64,
        "terminal_count": 64,
        "open_count": 0,
        "zero_open_work_pass": True,
        "final_certification_candidate": False,
    }
    return result


@dataclass(frozen=True, slots=True)
class CiboCertificationSeal:
    seal_id: str
    integrated_git_sha: str
    final_integrated_exam_sha256: str
    world_cup_exam_sha256: str
    strict_zero_open_sha256: str
    pre_seal_ledger_sha256: str
    certified_at: datetime
    scientifically_certified: bool
    live_authorized: bool = False
    real_capital_authorized: bool = False
    broker_mutation_authorized: bool = False
    merge_authorized: bool = False

    def __post_init__(self) -> None:
        if self.seal_id != _SEAL_ID:
            raise CiboCapitalManagementError(
                "CIBO certification seal identity drift"
            )
        if _SHA1_RE.fullmatch(self.integrated_git_sha) is None:
            raise CiboCapitalManagementError(
                "CIBO certification seal HEAD invalid"
            )
        for name in (
            "final_integrated_exam_sha256",
            "world_cup_exam_sha256",
            "strict_zero_open_sha256",
            "pre_seal_ledger_sha256",
        ):
            if _SHA256_RE.fullmatch(getattr(self, name)) is None:
                raise CiboCapitalManagementError(
                    f"CIBO certification seal {name} invalid"
                )
        if self.certified_at.tzinfo is None or self.certified_at.utcoffset() is None:
            raise CiboCapitalManagementError(
                "CIBO certification seal timestamp must be timezone-aware"
            )
        if type(self.scientifically_certified) is not bool or not self.scientifically_certified:
            raise CiboCapitalManagementError(
                "CIBO certification seal requires scientific certification"
            )
        if any(
            (
                self.live_authorized,
                self.real_capital_authorized,
                self.broker_mutation_authorized,
                self.merge_authorized,
            )
        ):
            raise CiboCapitalManagementError(
                "CIBO certification seal grants no operational authority"
            )

    def fingerprint(self) -> str:
        payload = asdict(self)
        payload["certified_at"] = self.certified_at.isoformat()
        return _canonical_sha(payload)


def build_cibo_certification_seal(
    *,
    ledger: dict[str, Any],
    strict_zero_open_artifact_json: str,
    strict_evidence_git_sha: str,
    final_integrated_exam: FinalIntegratedExamReport,
    world_cup_exam: WorldCupMaximumCapabilityReport,
    integrated_git_sha: str,
    certified_at: datetime,
) -> CiboCertificationSeal:
    """Emit the scientific seal only after exact 64/64 STRICT closure."""

    if _SHA1_RE.fullmatch(strict_evidence_git_sha) is None:
        raise CiboCapitalManagementError(
            "strict zero-open evidence Git SHA invalid"
        )
    if strict_evidence_git_sha != integrated_git_sha:
        raise CiboCapitalManagementError(
            "strict zero-open evidence HEAD drift"
        )
    _require_topology(ledger, terminal_count=64, open_ids=())
    _require_no_external_blockers(ledger)

    if (
        final_integrated_exam.status is not FinalIntegratedExamStatus.PASS
        or final_integrated_exam.blockers
        or final_integrated_exam.integrated_head_sha != integrated_git_sha
    ):
        raise CiboCapitalManagementError(
            "certification seal requires Final Integrated PASS on exact HEAD"
        )
    if (
        world_cup_exam.status is not WorldCupMaximumCapabilityStatus.PASS
        or world_cup_exam.blockers
        or world_cup_exam.integrated_head_sha != integrated_git_sha
    ):
        raise CiboCapitalManagementError(
            "certification seal requires World Cup PASS on exact HEAD"
        )
    if certified_at.tzinfo is None or certified_at.utcoffset() is None:
        raise CiboCapitalManagementError(
            "certification seal timestamp must be timezone-aware"
        )

    try:
        strict = json.loads(strict_zero_open_artifact_json)
    except json.JSONDecodeError as error:
        raise CiboCapitalManagementError(
            "strict zero-open artifact invalid JSON"
        ) from error
    if not isinstance(strict, dict):
        raise CiboCapitalManagementError(
            "strict zero-open artifact must be object"
        )
    canonical = json.dumps(strict, indent=2, sort_keys=True) + "\n"
    if canonical != strict_zero_open_artifact_json:
        raise CiboCapitalManagementError(
            "strict zero-open artifact must use canonical JSON"
        )
    expected = {
        "schema": _STRICT_SCHEMA,
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
    for key, value in expected.items():
        if strict.get(key) != value:
            raise CiboCapitalManagementError(
                f"strict zero-open artifact field mismatch: {key}"
            )
    strict_sha = "sha256:" + hashlib.sha256(
        strict_zero_open_artifact_json.encode("utf-8")
    ).hexdigest()

    return CiboCertificationSeal(
        seal_id=_SEAL_ID,
        integrated_git_sha=integrated_git_sha,
        final_integrated_exam_sha256=(
            final_integrated_exam_report_sha256(final_integrated_exam)
        ),
        world_cup_exam_sha256=_world_cup_report_sha256(world_cup_exam),
        strict_zero_open_sha256=strict_sha,
        pre_seal_ledger_sha256=_ledger_sha(ledger),
        certified_at=certified_at,
        scientifically_certified=True,
    )


def promote_final_certification_candidate(
    *,
    ledger: dict[str, Any],
    seal: CiboCertificationSeal,
) -> dict[str, Any]:
    """Set candidate=true only after the seal references this exact 64/64 ledger."""

    _require_topology(ledger, terminal_count=64, open_ids=())
    _require_no_external_blockers(ledger)
    if seal.pre_seal_ledger_sha256 != _ledger_sha(ledger):
        raise CiboCapitalManagementError(
            "certification candidate promotion ledger/seal drift"
        )
    result = copy.deepcopy(ledger)
    result["current_summary"]["final_certification_candidate"] = True
    return result
