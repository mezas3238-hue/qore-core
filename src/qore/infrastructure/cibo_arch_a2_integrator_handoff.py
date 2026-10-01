"""Integrator handoff receipt for the isolated CIBO Architect A2 lane."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass

from qore.infrastructure.cibo_arch_a2_internal_readiness import (
    ArchitectA2InternalReadinessReport,
)
from qore.infrastructure.cibo_arch_a2_scientific_closure import (
    A2_WORKSTREAM_IDS,
    ArchitectA2ScientificClosurePacket,
)
from qore.infrastructure.cibo_arch_a_internal_readiness import (
    ArchitectAReadinessError,
)

SCHEMA = "QORE_CIBO_ARCH_A2_INTEGRATOR_HANDOFF_V1"
ARCH_A_BASE_SHA = "84801346dd7b551b226b624657d6b56622e16bfa"
A2_BRANCH = "agent/cibo-architect-a2-capital-science-001"
_GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def _sha(value: str, name: str) -> None:
    if (
        not isinstance(value, str)
        or not value.startswith("sha256:")
        or len(value) != 71
        or any(ch not in "0123456789abcdef" for ch in value[7:])
    ):
        raise ArchitectAReadinessError(
            f"Architect A2 handoff {name} must be canonical SHA-256"
        )


@dataclass(frozen=True, slots=True)
class ArchitectA2IntegratorHandoffReceipt:
    schema: str
    branch: str
    arch_a_base_sha: str
    a2_head_sha: str
    phase22_manifest_sha256: str
    closure_packet_sha256: str
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
            raise ArchitectAReadinessError(
                "Architect A2 handoff schema drift"
            )
        if self.branch != A2_BRANCH:
            raise ArchitectAReadinessError(
                "Architect A2 handoff branch drift"
            )
        if self.arch_a_base_sha != ARCH_A_BASE_SHA:
            raise ArchitectAReadinessError(
                "Architect A2 handoff base SHA drift"
            )
        if _GIT_SHA_RE.fullmatch(self.a2_head_sha) is None:
            raise ArchitectAReadinessError(
                "Architect A2 handoff HEAD SHA invalid"
            )
        _sha(self.phase22_manifest_sha256, "phase22_manifest_sha256")
        _sha(self.closure_packet_sha256, "closure_packet_sha256")
        if (
            not isinstance(self.terminal_count, int)
            or isinstance(self.terminal_count, bool)
            or not 0 <= self.terminal_count <= len(A2_WORKSTREAM_IDS)
        ):
            raise ArchitectAReadinessError(
                "Architect A2 handoff terminal count invalid"
            )
        known = set(A2_WORKSTREAM_IDS)
        if (
            any(item not in known for item in self.completed_ids)
            or any(item not in known for item in self.falsified_ids)
            or len(self.completed_ids) != len(set(self.completed_ids))
            or len(self.falsified_ids) != len(set(self.falsified_ids))
            or set(self.completed_ids) & set(self.falsified_ids)
        ):
            raise ArchitectAReadinessError(
                "Architect A2 handoff terminal partition invalid"
            )
        if self.terminal_count != (
            len(self.completed_ids) + len(self.falsified_ids)
        ):
            raise ArchitectAReadinessError(
                "Architect A2 handoff terminal count drift"
            )
        if (
            not isinstance(self.blockers, tuple)
            or any(not isinstance(item, str) or not item for item in self.blockers)
            or len(self.blockers) != len(set(self.blockers))
        ):
            raise ArchitectAReadinessError(
                "Architect A2 handoff blockers invalid"
            )
        expected_ready = (
            self.terminal_count == len(A2_WORKSTREAM_IDS)
            and not self.blockers
        )
        if self.ready_for_integrator != expected_ready:
            raise ArchitectAReadinessError(
                "Architect A2 handoff readiness drift"
            )
        if any(
            (
                self.ledger_update_authority,
                self.merge_authority,
                self.certification_claimed,
                self.productive_authority,
            )
        ):
            raise ArchitectAReadinessError(
                "Architect A2 handoff grants no integration/production authority"
            )

    def as_dict(self) -> dict[str, object]:
        return asdict(self)

    def fingerprint(self) -> str:
        raw = json.dumps(
            self.as_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(raw).hexdigest()


def build_architect_a2_integrator_handoff(
    *,
    a2_head_sha: str,
    readiness: ArchitectA2InternalReadinessReport,
    closure: ArchitectA2ScientificClosurePacket,
) -> ArchitectA2IntegratorHandoffReceipt:
    """Bind A2 science without changing the canonical master ledger."""

    if not isinstance(readiness, ArchitectA2InternalReadinessReport):
        raise ArchitectAReadinessError(
            "Architect A2 handoff requires canonical readiness report"
        )
    if not isinstance(closure, ArchitectA2ScientificClosurePacket):
        raise ArchitectAReadinessError(
            "Architect A2 handoff requires canonical closure packet"
        )
    if _GIT_SHA_RE.fullmatch(a2_head_sha) is None:
        raise ArchitectAReadinessError(
            "Architect A2 handoff HEAD SHA invalid"
        )

    blockers: list[str] = []
    if not readiness.passed:
        blockers.append("A2_INTERNAL_READINESS_NOT_GREEN")
    if not closure.ready_for_integrator:
        blockers.append("A2_SCIENTIFIC_CLOSURE_INCOMPLETE")

    return ArchitectA2IntegratorHandoffReceipt(
        schema=SCHEMA,
        branch=A2_BRANCH,
        arch_a_base_sha=ARCH_A_BASE_SHA,
        a2_head_sha=a2_head_sha,
        phase22_manifest_sha256=closure.phase22_manifest_sha256,
        closure_packet_sha256=closure.fingerprint(),
        terminal_count=closure.terminal_count,
        completed_ids=closure.completed_ids,
        falsified_ids=closure.falsified_ids,
        blockers=tuple(blockers),
        ready_for_integrator=not blockers,
    )
