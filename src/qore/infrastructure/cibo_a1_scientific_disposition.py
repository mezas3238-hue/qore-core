"""Terminal scientific disposition contract for CIBO Architect A1.

A1 emits sidecar scientific dispositions only. The Integrator owns global
ledger reconciliation and certification sequencing. This module therefore
validates evidence identity, terminal scientific semantics and governance while
granting no merge, runtime, LIVE or real-capital authority.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import asdict, dataclass, replace
from enum import StrEnum

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)

A1_WORKSTREAMS = (
    "T04",
    "T06",
    "T07",
    "T08",
    "T09",
    "T10",
    "T12",
    "T13",
    "T14",
    "T15",
    "T18",
    "GEN-C2",
    "GEN-C3",
    "GEN-C4",
    "GEN-C5",
    "GEN-C6",
    "GEN-C7",
    "TEMPORAL_REPLICATION",
)
_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class A1ScientificStatus(StrEnum):
    COMPLETED_AND_PROVEN = "COMPLETED_AND_PROVEN"
    FALSIFIED_AND_CLOSED = "FALSIFIED_AND_CLOSED"


@dataclass(frozen=True, slots=True)
class A1ScientificDisposition:
    workstream_id: str
    scientific_status: A1ScientificStatus
    hypothesis: str
    mechanism_identity: str
    candidate_id: str
    code_sha: str
    parameter_sha256: str
    source_evidence: tuple[str, ...]
    population_identity: str
    decision_time_boundary: str
    control_baseline: str
    metrics: tuple[tuple[str, str], ...]
    causal_integrity: bool
    capital_conservation: bool
    result: str
    failure_reason: str | None
    proof_reason: str | None
    receipt_sha256: str
    productive_authority: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False
    global_ledger_reconciled: bool = False
    cibo_certified: bool = False

    def __post_init__(self) -> None:
        if self.workstream_id not in A1_WORKSTREAMS:
            raise CiboCapitalManagementError(
                "A1 disposition workstream outside A1 ownership"
            )
        if type(self.scientific_status) is not A1ScientificStatus:
            raise CiboCapitalManagementError(
                "A1 disposition scientific status invalid"
            )
        for name in (
            "hypothesis",
            "mechanism_identity",
            "candidate_id",
            "population_identity",
            "decision_time_boundary",
            "control_baseline",
            "result",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise CiboCapitalManagementError(
                    f"A1 disposition {name} is required"
                )
        if _SHA1_RE.fullmatch(self.code_sha) is None:
            raise CiboCapitalManagementError(
                "A1 disposition code_sha must be 40-char Git SHA"
            )
        _sha256(self.parameter_sha256, "parameter_sha256")
        _sha256(self.receipt_sha256, "receipt_sha256")
        if (
            not isinstance(self.source_evidence, tuple)
            or not self.source_evidence
            or len(self.source_evidence) != len(set(self.source_evidence))
            or any(
                not isinstance(item, str) or not item
                for item in self.source_evidence
            )
        ):
            raise CiboCapitalManagementError(
                "A1 disposition source evidence must be unique/non-empty"
            )
        if (
            not isinstance(self.metrics, tuple)
            or not self.metrics
            or len(self.metrics) != len({key for key, _ in self.metrics})
            or any(
                not isinstance(key, str)
                or not key
                or not isinstance(value, str)
                or not value
                for key, value in self.metrics
            )
        ):
            raise CiboCapitalManagementError(
                "A1 disposition metrics must be unique string pairs"
            )
        if not self.causal_integrity or not self.capital_conservation:
            raise CiboCapitalManagementError(
                "A1 terminal disposition requires causal/capital integrity"
            )

        if self.scientific_status is A1ScientificStatus.COMPLETED_AND_PROVEN:
            if self.failure_reason is not None:
                raise CiboCapitalManagementError(
                    "A1 proven disposition cannot carry failure reason"
                )
            if not self.proof_reason:
                raise CiboCapitalManagementError(
                    "A1 proven disposition requires proof reason"
                )
        else:
            if self.proof_reason is not None:
                raise CiboCapitalManagementError(
                    "A1 falsified disposition cannot carry proof reason"
                )
            if not self.failure_reason:
                raise CiboCapitalManagementError(
                    "A1 falsified disposition requires failure reason"
                )

        prohibited = (
            self.productive_authority,
            self.live_authorized,
            self.real_capital_authorized,
            self.global_ledger_reconciled,
            self.cibo_certified,
        )
        if any(prohibited):
            raise CiboCapitalManagementError(
                "A1 disposition cannot grant integration/certification authority"
            )

    def canonical_payload(self) -> dict[str, object]:
        payload = asdict(self)
        payload["scientific_status"] = self.scientific_status.value
        payload["source_evidence"] = list(self.source_evidence)
        payload["metrics"] = [[key, value] for key, value in self.metrics]
        return payload

    def fingerprint(self) -> str:
        payload = self.canonical_payload()
        payload.pop("receipt_sha256")
        raw = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(raw).hexdigest()

    def receipt_matches_payload(self) -> bool:
        return self.receipt_sha256 == self.fingerprint()


@dataclass(frozen=True, slots=True)
class A1ScientificDispositionPackage:
    source_branch: str
    source_head: str
    canonical_phase22_manifest_sha256: str
    a1_consumption_manifest_sha256: str
    canonical_manifest_bridge_sha256: str
    dispositions: tuple[A1ScientificDisposition, ...]
    complete_handoff: bool
    integrator_owned_reconciliation: bool = True
    merge_authorized: bool = False
    certification_authorized: bool = False

    def __post_init__(self) -> None:
        if not self.source_branch:
            raise CiboCapitalManagementError(
                "A1 disposition package source branch required"
            )
        if _SHA1_RE.fullmatch(self.source_head) is None:
            raise CiboCapitalManagementError(
                "A1 disposition package source head invalid"
            )
        for name in (
            "canonical_phase22_manifest_sha256",
            "a1_consumption_manifest_sha256",
            "canonical_manifest_bridge_sha256",
        ):
            _sha256(getattr(self, name), name)
        ids = tuple(item.workstream_id for item in self.dispositions)
        if len(ids) != len(set(ids)):
            raise CiboCapitalManagementError(
                "A1 disposition package duplicate workstream"
            )
        if any(not item.receipt_matches_payload() for item in self.dispositions):
            raise CiboCapitalManagementError(
                "A1 disposition package receipt/payload mismatch"
            )
        if self.complete_handoff:
            if set(ids) != set(A1_WORKSTREAMS) or len(ids) != len(A1_WORKSTREAMS):
                raise CiboCapitalManagementError(
                    "A1 complete handoff requires exactly 18 terminal dispositions"
                )
        if (
            not self.integrator_owned_reconciliation
            or self.merge_authorized
            or self.certification_authorized
        ):
            raise CiboCapitalManagementError(
                "A1 disposition package governance drift"
            )

    @property
    def terminal_count(self) -> int:
        return len(self.dispositions)

    @property
    def remaining_workstreams(self) -> tuple[str, ...]:
        completed = {item.workstream_id for item in self.dispositions}
        return tuple(item for item in A1_WORKSTREAMS if item not in completed)


def build_a1_scientific_disposition(
    *,
    workstream_id: str,
    scientific_status: A1ScientificStatus,
    hypothesis: str,
    mechanism_identity: str,
    candidate_id: str,
    code_sha: str,
    parameter_sha256: str,
    source_evidence: tuple[str, ...],
    population_identity: str,
    decision_time_boundary: str,
    control_baseline: str,
    metrics: Mapping[str, str],
    result: str,
    failure_reason: str | None = None,
    proof_reason: str | None = None,
) -> A1ScientificDisposition:
    """Build a terminal sidecar and bind its receipt to canonical content."""

    ordered_metrics = tuple(sorted(metrics.items()))
    provisional = A1ScientificDisposition(
        workstream_id=workstream_id,
        scientific_status=scientific_status,
        hypothesis=hypothesis,
        mechanism_identity=mechanism_identity,
        candidate_id=candidate_id,
        code_sha=code_sha,
        parameter_sha256=parameter_sha256,
        source_evidence=source_evidence,
        population_identity=population_identity,
        decision_time_boundary=decision_time_boundary,
        control_baseline=control_baseline,
        metrics=ordered_metrics,
        causal_integrity=True,
        capital_conservation=True,
        result=result,
        failure_reason=failure_reason,
        proof_reason=proof_reason,
        receipt_sha256="sha256:" + ("0" * 64),
    )
    return replace(
        provisional,
        receipt_sha256=provisional.fingerprint(),
    )


def _sha256(value: str, name: str) -> None:
    if _SHA256_RE.fullmatch(value) is None:
        raise CiboCapitalManagementError(
            f"A1 disposition {name} must be sha256:<64 lowercase hex>"
        )
