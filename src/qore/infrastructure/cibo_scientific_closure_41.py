"""Fail-closed scientific closure package for the 41 CIBO blockers.

This module owns no Phase22 execution, no final exams and no canonical-ledger
write.  It only accepts already-evaluated immutable scientific evidence and
builds the deterministic 41-workstream package that the sovereign Integrator
may later apply to a copy of the master ledger.

PASS is never inferred from implementation readiness.  NOT_READY/INVALID,
synthetic evidence, identity drift, future leakage and outcome-aware evidence
are rejected before a terminal package can exist.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification_plan import (
    phase20d_qualification_plan_sha256,
)
from qore.infrastructure.cibo_ce2i_phase22_qualification_plan import (
    phase22_holdout_qualification_plan_sha256,
)
from qore.infrastructure.cibo_phase22_demo_empirical_provider_receipt import (
    PHASE22_DEMO_EMPIRICAL_PROVIDER_RECEIPT,
)

PACKAGE_SCHEMA = "QORE_CIBO_SCIENTIFIC_CLOSURE_41_PACKAGE_V1"
EVIDENCE_SCHEMA = "QORE_CIBO_SCIENTIFIC_CLOSURE_41_EVIDENCE_V1"
TRANSITION_SCHEMA = "QORE_CIBO_SCIENTIFIC_CLOSURE_41_TRANSITION_V1"
LEDGER_SCHEMA = "QORE_CIBO_MASTER_OPEN_WORK_LEDGER_V1"

COMPLETED = "COMPLETED_AND_PROVEN"
FALSIFIED = "FALSIFIED_AND_CLOSED"
EXTERNAL = "EXTERNAL_DEPENDENCY_BLOCKED"
OPEN_PREIMAGE = "OPEN"

SCIENTIFIC_CLOSURE_41_IDS = (
    "T02",
    "T04",
    "T06",
    "T07",
    "T08",
    "T09",
    "T10",
    "T11",
    "T12",
    "T13",
    "T14",
    "T15",
    "T18",
    "T20",
    "GEN-C2",
    "GEN-C3",
    "GEN-C4",
    "GEN-C5",
    "GEN-C6",
    "GEN-C7",
    "GEN-C8",
    "GEN-C9",
    "GEN-C10",
    "GEN-C11",
    "GEN-C12",
    "GEN-C13",
    "GEN-C14",
    "COMPOUND_ENGINE",
    "COMPOUND_PORTFOLIO",
    "INTERNAL_CAPITAL_MARKET",
    "CAPITAL_GENERATIONS",
    "PROTECTED_BASE_CAPITAL",
    "PROFIT_PROTECTION",
    "PATH_DEPENDENT_MONTE_CARLO",
    "ADVERSARIAL_STRESS",
    "TEMPORAL_REPLICATION",
    "CAPITAL_AMPLIFICATION",
    "AS_IS_ECONOMIC_BASELINE",
    "FRESH_OOS",
    "USD60_CAPABILITY_PROGRAM",
    "INTEGRATED_CAPITAL_TRUTH",
)

FINAL_EXAM_IDS = (
    "FINAL_INTEGRATED_CIBO_EXAM",
    "WORLD_CUP_MAXIMUM_CAPABILITY_EXAM",
)
FRESH_OOS_ID = "FRESH_OOS"
SCIENTIFIC_CLOSURE_EXTERNAL_IDS = tuple(
    workstream_id
    for workstream_id in SCIENTIFIC_CLOSURE_41_IDS
    if workstream_id != FRESH_OOS_ID
)
PRE_CLOSURE_OPEN_IDS = (FRESH_OOS_ID, *FINAL_EXAM_IDS)

# Compatibility default for legacy builders only. Certification truth is no longer
# pinned to V4: V4 is CONSUMED_INVALID and successor fresh cycles must bind their
# actual immutable candidate id into every Closure41 evidence row.
CANONICAL_HOLDOUT_ID = "CIBO_USD60_6M_HOLDOUT_2014-10-19_2015-04-19_V4"
CANONICAL_POLICY_IDENTITY = phase20d_qualification_plan_sha256()
CANONICAL_QUALIFICATION_PLAN_IDENTITY = (
    phase22_holdout_qualification_plan_sha256()
)
_provider = PHASE22_DEMO_EMPIRICAL_PROVIDER_RECEIPT
CANONICAL_PROVIDER_IDENTITY = (
    f"{_provider.provider_key}:{_provider.environment}:"
    f"{_provider.account_fingerprint_sha256}"
)

_ALLOWED_ORIGINS = {
    "PHASE22_IMMUTABLE",
    "PROVIDER_SEALED",
    "CAPITAL_LEDGER_IMMUTABLE",
    "CANONICAL_GATE_RECEIPT",
}
_RESULT_VALUES = {"PASS", "FAIL", "NOT_APPLICABLE"}
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_HOLDOUT_ID_RE = re.compile(
    r"^CIBO_USD60_6M_HOLDOUT_\d{4}-\d{2}-\d{2}_"
    r"\d{4}-\d{2}-\d{2}_V\d+$"
)


def _require_holdout_id(value: str, label: str) -> None:
    if not isinstance(value, str) or _HOLDOUT_ID_RE.fullmatch(value) is None:
        raise CiboCapitalManagementError(
            f"Scientific closure 41 {label} must be a versioned fresh holdout id"
        )


def _require_sha256(value: str, label: str) -> None:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise CiboCapitalManagementError(
            f"Scientific closure 41 {label} must be sha256:<64 lowercase hex>"
        )


def _canonical_sha(payload: Any) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True, slots=True)
class ScientificClosure41Evidence:
    workstream_id: str
    previous_disposition: str
    scientific_hypothesis: str
    evidence_refs: tuple[str, ...]
    evidence_sha256s: tuple[str, ...]
    population_identity: str
    policy_identity: str
    provider_identity: str
    causal_lineage: str
    economic_result: str
    stress_result: str
    temporal_replication_result: str
    integrity_result: str
    source_gate_status: str
    terminal_reason: str
    evaluated_at: datetime
    phase22_manifest_sha256: str
    holdout_id: str = CANONICAL_HOLDOUT_ID
    qualification_plan_identity: str = CANONICAL_QUALIFICATION_PLAN_IDENTITY
    evidence_origin: str = "CANONICAL_GATE_RECEIPT"
    failed_dimensions: tuple[str, ...] = ()
    synthetic_evidence_used: bool = False
    future_leakage_detected: bool = False
    outcome_aware_evidence: bool = False
    post_outcome_retuning_detected: bool = False
    productive_authority: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False
    certification_authorized: bool = False

    def __post_init__(self) -> None:
        if self.workstream_id not in SCIENTIFIC_CLOSURE_41_IDS:
            raise CiboCapitalManagementError(
                "Scientific closure 41 workstream outside exact ownership"
            )
        expected_preimage = (
            OPEN_PREIMAGE if self.workstream_id == FRESH_OOS_ID else EXTERNAL
        )
        if self.previous_disposition != expected_preimage:
            raise CiboCapitalManagementError(
                "Scientific closure 41 previous-disposition preimage drift"
            )
        if not self.scientific_hypothesis.strip():
            raise CiboCapitalManagementError(
                "Scientific closure 41 hypothesis required"
            )
        if (
            not self.evidence_refs
            or len(self.evidence_refs) != len(set(self.evidence_refs))
            or any(not item for item in self.evidence_refs)
        ):
            raise CiboCapitalManagementError(
                "Scientific closure 41 evidence refs must be unique and non-empty"
            )
        if (
            not self.evidence_sha256s
            or len(self.evidence_sha256s) != len(set(self.evidence_sha256s))
        ):
            raise CiboCapitalManagementError(
                "Scientific closure 41 evidence digests required and unique"
            )
        for digest in self.evidence_sha256s:
            _require_sha256(digest, "evidence digest")
        if not self.population_identity.strip():
            raise CiboCapitalManagementError(
                "Scientific closure 41 population identity required"
            )
        if self.policy_identity != CANONICAL_POLICY_IDENTITY:
            raise CiboCapitalManagementError(
                "Scientific closure 41 policy identity drift"
            )
        if self.provider_identity != CANONICAL_PROVIDER_IDENTITY:
            raise CiboCapitalManagementError(
                "Scientific closure 41 provider identity drift"
            )
        _require_sha256(self.causal_lineage, "causal lineage")
        _require_sha256(self.phase22_manifest_sha256, "Phase22 manifest")
        _require_holdout_id(self.holdout_id, "holdout identity")
        if (
            self.qualification_plan_identity
            != CANONICAL_QUALIFICATION_PLAN_IDENTITY
        ):
            raise CiboCapitalManagementError(
                "Scientific closure 41 qualification-plan identity drift"
            )
        if self.evidence_origin not in _ALLOWED_ORIGINS:
            raise CiboCapitalManagementError(
                "Scientific closure 41 evidence origin is not admissible"
            )
        for name in (
            "economic_result",
            "stress_result",
            "temporal_replication_result",
        ):
            if getattr(self, name) not in _RESULT_VALUES:
                raise CiboCapitalManagementError(
                    f"Scientific closure 41 {name} invalid"
                )
        if self.integrity_result not in {"PASS", "FAIL"}:
            raise CiboCapitalManagementError(
                "Scientific closure 41 integrity result invalid"
            )
        if self.source_gate_status not in {"PASS", "FAIL"}:
            raise CiboCapitalManagementError(
                "Scientific closure 41 NOT_READY/INVALID cannot be terminal"
            )
        if self.source_gate_status == "PASS" and (
            self.integrity_result != "PASS"
            or "FAIL"
            in {
                self.economic_result,
                self.stress_result,
                self.temporal_replication_result,
            }
        ):
            raise CiboCapitalManagementError(
                "Scientific closure 41 PASS cannot hide failed dimensions"
            )
        if not self.terminal_reason.strip():
            raise CiboCapitalManagementError(
                "Scientific closure 41 terminal reason required"
            )
        if (
            self.evaluated_at.tzinfo is None
            or self.evaluated_at.utcoffset() is None
        ):
            raise CiboCapitalManagementError(
                "Scientific closure 41 evaluated_at must be timezone-aware"
            )
        if (
            self.synthetic_evidence_used
            or self.future_leakage_detected
            or self.outcome_aware_evidence
            or self.post_outcome_retuning_detected
        ):
            raise CiboCapitalManagementError(
                "Scientific closure 41 contaminated evidence is inadmissible"
            )
        if any(
            (
                self.productive_authority,
                self.live_authorized,
                self.real_capital_authorized,
                self.certification_authorized,
            )
        ):
            raise CiboCapitalManagementError(
                "Scientific closure 41 evidence cannot grant authority"
            )

    @property
    def terminal_disposition(self) -> str:
        if self.source_gate_status == "PASS":
            return COMPLETED
        return FALSIFIED

    def to_machine_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["evaluated_at"] = self.evaluated_at.isoformat()
        payload["terminal_disposition"] = self.terminal_disposition
        return payload

    def fingerprint(self) -> str:
        return _canonical_sha(self.to_machine_dict())


@dataclass(frozen=True, slots=True)
class ScientificClosure41Package:
    schema: str
    phase22_manifest_sha256: str
    holdout_id: str
    policy_identity: str
    provider_identity: str
    workstreams: tuple[ScientificClosure41Evidence, ...]
    completed_ids: tuple[str, ...]
    falsified_ids: tuple[str, ...]
    productive_authority: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False
    certification_claimed: bool = False
    canonical_ledger_modified: bool = False

    def __post_init__(self) -> None:
        if self.schema != PACKAGE_SCHEMA:
            raise CiboCapitalManagementError(
                "Scientific closure 41 package schema drift"
            )
        _require_sha256(self.phase22_manifest_sha256, "package Phase22 manifest")
        _require_holdout_id(self.holdout_id, "package holdout")
        if self.policy_identity != CANONICAL_POLICY_IDENTITY:
            raise CiboCapitalManagementError(
                "Scientific closure 41 package policy drift"
            )
        if self.provider_identity != CANONICAL_PROVIDER_IDENTITY:
            raise CiboCapitalManagementError(
                "Scientific closure 41 package provider drift"
            )
        ids = tuple(item.workstream_id for item in self.workstreams)
        if (
            len(ids) != len(SCIENTIFIC_CLOSURE_41_IDS)
            or len(ids) != len(set(ids))
            or set(ids) != set(SCIENTIFIC_CLOSURE_41_IDS)
        ):
            raise CiboCapitalManagementError(
                "Scientific closure 41 package requires exact 41-workstream surface"
            )
        if ids != SCIENTIFIC_CLOSURE_41_IDS:
            raise CiboCapitalManagementError(
                "Scientific closure 41 package ordering drift"
            )
        if any(
            item.phase22_manifest_sha256 != self.phase22_manifest_sha256
            for item in self.workstreams
        ):
            raise CiboCapitalManagementError(
                "Scientific closure 41 package Phase22 lineage drift"
            )
        if any(item.holdout_id != self.holdout_id for item in self.workstreams):
            raise CiboCapitalManagementError(
                "Scientific closure 41 package cross-holdout lineage drift"
            )
        expected_completed = tuple(
            item.workstream_id
            for item in self.workstreams
            if item.terminal_disposition == COMPLETED
        )
        expected_falsified = tuple(
            item.workstream_id
            for item in self.workstreams
            if item.terminal_disposition == FALSIFIED
        )
        if self.completed_ids != expected_completed:
            raise CiboCapitalManagementError(
                "Scientific closure 41 completed-id drift"
            )
        if self.falsified_ids != expected_falsified:
            raise CiboCapitalManagementError(
                "Scientific closure 41 falsified-id drift"
            )
        if len(self.completed_ids) + len(self.falsified_ids) != 41:
            raise CiboCapitalManagementError(
                "Scientific closure 41 package is not fully terminal"
            )
        if any(
            (
                self.productive_authority,
                self.live_authorized,
                self.real_capital_authorized,
                self.certification_claimed,
                self.canonical_ledger_modified,
            )
        ):
            raise CiboCapitalManagementError(
                "Scientific closure 41 package exceeded scientific authority"
            )

    def to_machine_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "phase22_manifest_sha256": self.phase22_manifest_sha256,
            "holdout_id": self.holdout_id,
            "policy_identity": self.policy_identity,
            "provider_identity": self.provider_identity,
            "workstreams": [item.to_machine_dict() for item in self.workstreams],
            "completed_ids": list(self.completed_ids),
            "falsified_ids": list(self.falsified_ids),
            "productive_authority": self.productive_authority,
            "live_authorized": self.live_authorized,
            "real_capital_authorized": self.real_capital_authorized,
            "certification_claimed": self.certification_claimed,
            "canonical_ledger_modified": self.canonical_ledger_modified,
        }

    def fingerprint(self) -> str:
        return _canonical_sha(self.to_machine_dict())


def build_scientific_closure_41_package(
    *,
    phase22_manifest_sha256: str,
    evidence: tuple[ScientificClosure41Evidence, ...],
) -> ScientificClosure41Package:
    _require_sha256(phase22_manifest_sha256, "Phase22 manifest")
    if not isinstance(evidence, tuple):
        raise CiboCapitalManagementError(
            "Scientific closure 41 evidence collection must be tuple"
        )
    by_id: dict[str, ScientificClosure41Evidence] = {}
    for item in evidence:
        if not isinstance(item, ScientificClosure41Evidence):
            raise CiboCapitalManagementError(
                "Scientific closure 41 evidence item is not canonical"
            )
        if item.workstream_id in by_id:
            raise CiboCapitalManagementError(
                "Scientific closure 41 duplicate workstream evidence"
            )
        by_id[item.workstream_id] = item
    if set(by_id) != set(SCIENTIFIC_CLOSURE_41_IDS):
        missing = tuple(
            item for item in SCIENTIFIC_CLOSURE_41_IDS if item not in by_id
        )
        extra = tuple(item for item in by_id if item not in SCIENTIFIC_CLOSURE_41_IDS)
        raise CiboCapitalManagementError(
            "Scientific closure 41 exact ownership mismatch: "
            f"missing={missing}, extra={extra}"
        )
    ordered = tuple(by_id[item] for item in SCIENTIFIC_CLOSURE_41_IDS)
    if any(
        item.phase22_manifest_sha256 != phase22_manifest_sha256
        for item in ordered
    ):
        raise CiboCapitalManagementError(
            "Scientific closure 41 evidence/manifest mismatch"
        )
    holdout_ids = {item.holdout_id for item in ordered}
    if len(holdout_ids) != 1:
        raise CiboCapitalManagementError(
            "Scientific closure 41 evidence spans multiple fresh holdouts"
        )
    holdout_id = next(iter(holdout_ids))
    _require_holdout_id(holdout_id, "package holdout")
    return ScientificClosure41Package(
        schema=PACKAGE_SCHEMA,
        phase22_manifest_sha256=phase22_manifest_sha256,
        holdout_id=holdout_id,
        policy_identity=CANONICAL_POLICY_IDENTITY,
        provider_identity=CANONICAL_PROVIDER_IDENTITY,
        workstreams=ordered,
        completed_ids=tuple(
            item.workstream_id
            for item in ordered
            if item.terminal_disposition == COMPLETED
        ),
        falsified_ids=tuple(
            item.workstream_id
            for item in ordered
            if item.terminal_disposition == FALSIFIED
        ),
    )


@dataclass(frozen=True, slots=True)
class ScientificClosure41TransitionReceipt:
    schema: str
    package_sha256: str
    pre_ledger_sha256: str
    post_ledger_sha256: str
    applied_ids: tuple[str, ...]
    residual_external_ids: tuple[str, ...]
    open_exam_ids: tuple[str, ...]
    canonical_ledger_modified: bool = False
    certification_claimed: bool = False
    productive_authority: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False
    merge_authority: bool = False

    def __post_init__(self) -> None:
        if self.schema != TRANSITION_SCHEMA:
            raise CiboCapitalManagementError(
                "Scientific closure 41 transition schema drift"
            )
        for name in (
            "package_sha256",
            "pre_ledger_sha256",
            "post_ledger_sha256",
        ):
            _require_sha256(getattr(self, name), name)
        if self.applied_ids != SCIENTIFIC_CLOSURE_41_IDS:
            raise CiboCapitalManagementError(
                "Scientific closure 41 transition ownership drift"
            )
        if self.residual_external_ids:
            raise CiboCapitalManagementError(
                "Scientific closure 41 transition left external blockers"
            )
        if self.open_exam_ids != FINAL_EXAM_IDS:
            raise CiboCapitalManagementError(
                "Scientific closure 41 transition must leave final exams open"
            )
        if any(
            (
                self.canonical_ledger_modified,
                self.certification_claimed,
                self.productive_authority,
                self.live_authorized,
                self.real_capital_authorized,
                self.merge_authority,
            )
        ):
            raise CiboCapitalManagementError(
                "Scientific closure 41 transition exceeded authority"
            )

    def fingerprint(self) -> str:
        return _canonical_sha(asdict(self))


def _mandatory_rows(ledger: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(ledger, dict) or ledger.get("schema") != LEDGER_SCHEMA:
        raise CiboCapitalManagementError(
            "Scientific closure 41 ledger schema drift"
        )
    rows = ledger.get("workstreams")
    if (
        not isinstance(rows, list)
        or any(not isinstance(item, dict) for item in rows)
    ):
        raise CiboCapitalManagementError(
            "Scientific closure 41 ledger workstreams invalid"
        )
    mandatory = [row for row in rows if row.get("mandatory") is True]
    if len(mandatory) != 64:
        raise CiboCapitalManagementError(
            "Scientific closure 41 mandatory ledger surface drift"
        )
    ids = tuple(str(row.get("id")) for row in mandatory)
    if len(ids) != len(set(ids)):
        raise CiboCapitalManagementError(
            "Scientific closure 41 duplicate mandatory ledger ids"
        )
    return mandatory


def validate_scientific_closure_41_preimage(
    ledger: dict[str, Any],
) -> dict[str, object]:
    mandatory = _mandatory_rows(ledger)
    external_ids = tuple(
        str(row.get("id"))
        for row in mandatory
        if row.get("terminal_disposition") == EXTERNAL
    )
    if set(external_ids) != set(SCIENTIFIC_CLOSURE_EXTERNAL_IDS):
        raise CiboCapitalManagementError(
            "Scientific closure 41 ledger external surface is not exact"
        )
    open_ids = tuple(
        str(row.get("id"))
        for row in mandatory
        if not row.get("terminal_disposition")
    )
    if open_ids != PRE_CLOSURE_OPEN_IDS:
        raise CiboCapitalManagementError(
            "Scientific closure 41 preimage open-work topology drift"
        )
    return {
        "mandatory_count": len(mandatory),
        "external_dependency_blocked": len(external_ids),
        "external_ids": list(external_ids),
        "fresh_oos_open": FRESH_OOS_ID in open_ids,
        "open_workstream_ids": list(open_ids),
        "open_exam_ids": list(FINAL_EXAM_IDS),
        "certification": False,
        "productive_authority": False,
    }


def apply_scientific_closure_41_to_ledger_copy(
    *,
    ledger: dict[str, Any],
    package: ScientificClosure41Package,
) -> tuple[dict[str, Any], ScientificClosure41TransitionReceipt]:
    """Apply exact terminal dispositions to a copy, never the canonical ledger."""

    if not isinstance(package, ScientificClosure41Package):
        raise CiboCapitalManagementError(
            "Scientific closure 41 transition requires canonical package"
        )
    validate_scientific_closure_41_preimage(ledger)

    pre_snapshot = json.loads(json.dumps(ledger))
    updated = json.loads(json.dumps(ledger))
    rows = _mandatory_rows(updated)
    by_id = {str(row.get("id")): row for row in rows}
    evidence_by_id = {item.workstream_id: item for item in package.workstreams}

    outside_before = {
        str(row.get("id")): row
        for row in _mandatory_rows(pre_snapshot)
        if str(row.get("id")) not in SCIENTIFIC_CLOSURE_41_IDS
    }

    for workstream_id in SCIENTIFIC_CLOSURE_41_IDS:
        row = by_id[workstream_id]
        evidence = evidence_by_id[workstream_id]
        if workstream_id == FRESH_OOS_ID:
            if row.get("terminal_disposition") not in {None, ""}:
                raise CiboCapitalManagementError(
                    "Scientific closure 41 fresh-OOS preimage is not OPEN"
                )
        elif row.get("terminal_disposition") != EXTERNAL:
            raise CiboCapitalManagementError(
                "Scientific closure 41 cannot reopen or overwrite terminal row"
            )
        row["terminal_disposition"] = evidence.terminal_disposition
        row["current_maturity"] = (
            "SCIENTIFIC_CLOSURE_41_" + evidence.terminal_disposition
        )
        refs = list(row.get("evidence_refs") or [])
        refs.extend(evidence.evidence_refs)
        refs.extend(evidence.evidence_sha256s)
        refs.extend(
            (
                evidence.phase22_manifest_sha256,
                evidence.causal_lineage,
                evidence.fingerprint(),
            )
        )
        row["evidence_refs"] = list(dict.fromkeys(refs))
        row["blockers"] = []
        row["next_gate"] = (
            "Terminal scientific disposition from immutable closure-41 package. "
            + evidence.terminal_reason
        )

    outside_after = {
        str(row.get("id")): row
        for row in _mandatory_rows(updated)
        if str(row.get("id")) not in SCIENTIFIC_CLOSURE_41_IDS
    }
    if outside_after != outside_before:
        raise CiboCapitalManagementError(
            "Scientific closure 41 transition modified out-of-scope workstream"
        )

    residual_external_ids = tuple(
        str(row.get("id"))
        for row in _mandatory_rows(updated)
        if row.get("terminal_disposition") == EXTERNAL
    )
    open_exam_ids = tuple(
        str(row.get("id"))
        for row in _mandatory_rows(updated)
        if not row.get("terminal_disposition")
    )

    receipt = ScientificClosure41TransitionReceipt(
        schema=TRANSITION_SCHEMA,
        package_sha256=package.fingerprint(),
        pre_ledger_sha256=_canonical_sha(pre_snapshot),
        post_ledger_sha256=_canonical_sha(updated),
        applied_ids=SCIENTIFIC_CLOSURE_41_IDS,
        residual_external_ids=residual_external_ids,
        open_exam_ids=open_exam_ids,
    )
    return updated, receipt
