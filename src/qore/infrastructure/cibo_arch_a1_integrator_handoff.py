"""Integrator handoff receipt for the isolated CIBO Architect A1 lane.

The receipt binds A1 engineering readiness and the exact 18-workstream terminal
scientific disposition package. It is intentionally non-authoritative: the
Integrator alone owns ledger reconciliation, merge sequencing and certification.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass

from qore.infrastructure.cibo_a1_scientific_disposition import (
    A1_WORKSTREAMS,
    A1ScientificDispositionPackage,
    A1ScientificStatus,
)
from qore.infrastructure.cibo_arch_a1_internal_readiness import (
    ArchitectA1InternalReadinessReport,
)
from qore.infrastructure.cibo_arch_a1_scientific_closure import (
    ArchitectA1ScientificClosurePacket,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)

SCHEMA = "QORE_CIBO_ARCH_A1_INTEGRATOR_HANDOFF_V1"
ARCH_A_BASE_SHA = "84801346dd7b551b226b624657d6b56622e16bfa"
A1_BRANCH = "agent/cibo-architect-a1-causal-science-001"
_GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class ArchitectA1IntegratorHandoffReceipt:
    schema: str
    branch: str
    arch_a_base_sha: str
    a1_head_sha: str
    canonical_phase22_manifest_sha256: str
    a1_consumption_manifest_sha256: str
    canonical_manifest_bridge_sha256: str
    disposition_package_sha256: str
    canonical_closure_packet_sha256: str
    terminal_count: int
    completed_ids: tuple[str, ...]
    falsified_ids: tuple[str, ...]
    blockers: tuple[str, ...]
    ready_for_integrator: bool
    ledger_update_authority: bool = False
    merge_authority: bool = False
    certification_claimed: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.schema != SCHEMA:
            raise CiboCapitalManagementError(
                "Architect A1 handoff schema drift"
            )
        if self.branch != A1_BRANCH:
            raise CiboCapitalManagementError(
                "Architect A1 handoff branch drift"
            )
        if self.arch_a_base_sha != ARCH_A_BASE_SHA:
            raise CiboCapitalManagementError(
                "Architect A1 handoff base SHA drift"
            )
        if _GIT_SHA_RE.fullmatch(self.a1_head_sha) is None:
            raise CiboCapitalManagementError(
                "Architect A1 handoff HEAD SHA invalid"
            )
        for name in (
            "canonical_phase22_manifest_sha256",
            "a1_consumption_manifest_sha256",
            "canonical_manifest_bridge_sha256",
            "disposition_package_sha256",
            "canonical_closure_packet_sha256",
        ):
            if _SHA256_RE.fullmatch(getattr(self, name)) is None:
                raise CiboCapitalManagementError(
                    f"Architect A1 handoff {name} invalid"
                )
        known = set(A1_WORKSTREAMS)
        if (
            any(item not in known for item in self.completed_ids)
            or any(item not in known for item in self.falsified_ids)
            or len(self.completed_ids) != len(set(self.completed_ids))
            or len(self.falsified_ids) != len(set(self.falsified_ids))
            or set(self.completed_ids) & set(self.falsified_ids)
        ):
            raise CiboCapitalManagementError(
                "Architect A1 handoff terminal partition invalid"
            )
        if self.terminal_count != (
            len(self.completed_ids) + len(self.falsified_ids)
        ):
            raise CiboCapitalManagementError(
                "Architect A1 handoff terminal count drift"
            )
        if (
            not isinstance(self.blockers, tuple)
            or any(not isinstance(item, str) or not item for item in self.blockers)
            or len(self.blockers) != len(set(self.blockers))
        ):
            raise CiboCapitalManagementError(
                "Architect A1 handoff blockers invalid"
            )
        expected_ready = self.terminal_count == 18 and not self.blockers
        if self.ready_for_integrator != expected_ready:
            raise CiboCapitalManagementError(
                "Architect A1 handoff readiness drift"
            )
        if (
            self.ledger_update_authority
            or self.merge_authority
            or self.certification_claimed
            or self.productive_authority
        ):
            raise CiboCapitalManagementError(
                "Architect A1 handoff grants no integration/production authority"
            )

    def fingerprint(self) -> str:
        raw = json.dumps(
            asdict(self),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(raw).hexdigest()


def build_architect_a1_integrator_handoff(
    *,
    a1_head_sha: str,
    readiness: ArchitectA1InternalReadinessReport,
    package: A1ScientificDispositionPackage,
    canonical_closure: ArchitectA1ScientificClosurePacket,
) -> ArchitectA1IntegratorHandoffReceipt:
    """Build the A1 sidecar handoff without changing the canonical ledger."""

    if not isinstance(readiness, ArchitectA1InternalReadinessReport):
        raise CiboCapitalManagementError(
            "Architect A1 handoff requires canonical readiness report"
        )
    if not isinstance(package, A1ScientificDispositionPackage):
        raise CiboCapitalManagementError(
            "Architect A1 handoff requires canonical disposition package"
        )
    if not isinstance(canonical_closure, ArchitectA1ScientificClosurePacket):
        raise CiboCapitalManagementError(
            "Architect A1 handoff requires canonical Phase22 closure packet"
        )
    if _GIT_SHA_RE.fullmatch(a1_head_sha) is None:
        raise CiboCapitalManagementError(
            "Architect A1 handoff HEAD SHA invalid"
        )

    completed = tuple(
        item.workstream_id
        for item in package.dispositions
        if item.scientific_status is A1ScientificStatus.COMPLETED_AND_PROVEN
    )
    falsified = tuple(
        item.workstream_id
        for item in package.dispositions
        if item.scientific_status is A1ScientificStatus.FALSIFIED_AND_CLOSED
    )
    blockers: list[str] = []
    if package.source_branch != A1_BRANCH:
        blockers.append("A1_DISPOSITION_PACKAGE_BRANCH_DRIFT")
    if package.source_head != a1_head_sha:
        blockers.append("A1_DISPOSITION_PACKAGE_HEAD_DRIFT")
    if (
        canonical_closure.phase22_manifest_sha256
        != package.canonical_phase22_manifest_sha256
    ):
        blockers.append("A1_CANONICAL_CLOSURE_MANIFEST_DRIFT")
    if canonical_closure.completed_ids != completed:
        blockers.append("A1_CANONICAL_CLOSURE_COMPLETED_PARTITION_DRIFT")
    if canonical_closure.falsified_ids != falsified:
        blockers.append("A1_CANONICAL_CLOSURE_FALSIFIED_PARTITION_DRIFT")
    if canonical_closure.terminal_count != package.terminal_count:
        blockers.append("A1_CANONICAL_CLOSURE_TERMINAL_COUNT_DRIFT")
    if canonical_closure.missing_ids:
        blockers.append("A1_CANONICAL_CLOSURE_HAS_MISSING_WORKSTREAMS")
    if not canonical_closure.ready_for_integrator:
        blockers.append("A1_CANONICAL_CLOSURE_NOT_READY")
    if not readiness.engineering_ready:
        blockers.append("A1_INTERNAL_READINESS_NOT_GREEN")
    if not package.complete_handoff:
        blockers.append("A1_TERMINAL_SCIENTIFIC_PACKAGE_INCOMPLETE")
    if package.terminal_count != 18:
        blockers.append("A1_EXACT_18_TERMINAL_DISPOSITIONS_REQUIRED")

    return ArchitectA1IntegratorHandoffReceipt(
        schema=SCHEMA,
        branch=A1_BRANCH,
        arch_a_base_sha=ARCH_A_BASE_SHA,
        a1_head_sha=a1_head_sha,
        canonical_phase22_manifest_sha256=(
            package.canonical_phase22_manifest_sha256
        ),
        a1_consumption_manifest_sha256=(
            package.a1_consumption_manifest_sha256
        ),
        canonical_manifest_bridge_sha256=(
            package.canonical_manifest_bridge_sha256
        ),
        disposition_package_sha256=package.fingerprint(),
        canonical_closure_packet_sha256=canonical_closure.fingerprint(),
        terminal_count=package.terminal_count,
        completed_ids=completed,
        falsified_ids=falsified,
        blockers=tuple(blockers),
        ready_for_integrator=not blockers,
    )
