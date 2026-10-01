"""Architect A2 scientific-closure packet for CIBO Phase22.

A2 owns only the capital-science half of Architect A's externally blocked
surface. It consumes canonical Architect-A Phase22 scientific-disposition
receipts and produces a sidecar packet for the Integrator. It never edits the
master ledger, closes A1 work, grants certification, or grants productive
authority.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass

from qore.infrastructure.cibo_arch_a_internal_readiness import (
    _PHASE22_V2_EVIDENCE_REQUIREMENTS_BY_WORKSTREAM,
    PHASE22_V2_SCIENTIFIC_DISPOSITION_SCHEMA,
    ArchitectAPhase22V2ScientificDispositionReceipt,
    ArchitectAPhase22V2WorkstreamEvidenceMatrix,
    ArchitectAPhase22V2WorkstreamEvidenceState,
    ArchitectAReadinessError,
)

A2_WORKSTREAM_IDS = (
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
    "CAPITAL_AMPLIFICATION",
    "AS_IS_ECONOMIC_BASELINE",
)

A1_RESERVED_WORKSTREAM_IDS = (
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


def _sha(value: str, name: str) -> None:
    if (
        not isinstance(value, str)
        or not value.startswith("sha256:")
        or len(value) != 71
        or any(ch not in "0123456789abcdef" for ch in value[7:])
    ):
        raise ArchitectAReadinessError(
            f"Architect A2 {name} must be canonical SHA-256"
        )


def _canonical_sha(payload: object) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True, slots=True)
class ArchitectA2EvidenceView:
    phase22_manifest_sha256: str
    states: tuple[ArchitectAPhase22V2WorkstreamEvidenceState, ...]
    ready_ids: tuple[str, ...]
    blocked_ids: tuple[str, ...]
    all_a2_workstreams_ready: bool
    a1_state_consumed: bool = False
    integration_authority: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        _sha(self.phase22_manifest_sha256, "phase22_manifest_sha256")
        if tuple(item.workstream_id for item in self.states) != A2_WORKSTREAM_IDS:
            raise ArchitectAReadinessError(
                "Architect A2 evidence view coverage drift"
            )
        for state in self.states:
            expected = _PHASE22_V2_EVIDENCE_REQUIREMENTS_BY_WORKSTREAM[
                state.workstream_id
            ]
            if state.required_kinds != expected:
                raise ArchitectAReadinessError(
                    "Architect A2 evidence requirements drift"
                )
        expected_ready = tuple(
            item.workstream_id
            for item in self.states
            if item.ready_for_frozen_evaluation
        )
        expected_blocked = tuple(
            item.workstream_id
            for item in self.states
            if not item.ready_for_frozen_evaluation
        )
        if self.ready_ids != expected_ready or self.blocked_ids != expected_blocked:
            raise ArchitectAReadinessError(
                "Architect A2 evidence readiness partition drift"
            )
        if self.all_a2_workstreams_ready != (not self.blocked_ids):
            raise ArchitectAReadinessError(
                "Architect A2 evidence readiness flag drift"
            )
        if (
            self.a1_state_consumed
            or self.integration_authority
            or self.productive_authority
        ):
            raise ArchitectAReadinessError(
                "Architect A2 evidence view cannot consume A1/grant authority"
            )

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def view_architect_a2_evidence_matrix(
    matrix: ArchitectAPhase22V2WorkstreamEvidenceMatrix,
) -> ArchitectA2EvidenceView:
    """Filter the canonical full-A matrix without depending on A1 readiness."""

    if not isinstance(matrix, ArchitectAPhase22V2WorkstreamEvidenceMatrix):
        raise ArchitectAReadinessError(
            "Architect A2 evidence view requires canonical full-A matrix"
        )
    by_id = {item.workstream_id: item for item in matrix.states}
    states = tuple(by_id[item] for item in A2_WORKSTREAM_IDS)
    ready = tuple(
        item.workstream_id for item in states if item.ready_for_frozen_evaluation
    )
    blocked = tuple(
        item.workstream_id for item in states if not item.ready_for_frozen_evaluation
    )
    return ArchitectA2EvidenceView(
        phase22_manifest_sha256=matrix.phase22_manifest_sha256,
        states=states,
        ready_ids=ready,
        blocked_ids=blocked,
        all_a2_workstreams_ready=not blocked,
        a1_state_consumed=False,
    )


@dataclass(frozen=True, slots=True)
class ArchitectA2ScientificClosurePacket:
    phase22_manifest_sha256: str
    receipt_count: int
    terminal_count: int
    completed_ids: tuple[str, ...]
    falsified_ids: tuple[str, ...]
    external_ids: tuple[str, ...]
    missing_ids: tuple[str, ...]
    exact_a2_surface: bool
    ready_for_integrator: bool
    ledger_update_authority: bool = False
    certification_claimed: bool = False
    productive_authority: bool = False
    merge_authority: bool = False

    def __post_init__(self) -> None:
        _sha(self.phase22_manifest_sha256, "phase22_manifest_sha256")
        for name in ("receipt_count", "terminal_count"):
            value = getattr(self, name)
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or not 0 <= value <= len(A2_WORKSTREAM_IDS)
            ):
                raise ArchitectAReadinessError(
                    f"Architect A2 {name} is invalid"
                )
        groups = (
            self.completed_ids,
            self.falsified_ids,
            self.external_ids,
            self.missing_ids,
        )
        known = set(A2_WORKSTREAM_IDS)
        sets: list[set[str]] = []
        for values in groups:
            if (
                not isinstance(values, tuple)
                or any(item not in known for item in values)
                or len(values) != len(set(values))
            ):
                raise ArchitectAReadinessError(
                    "Architect A2 packet workstream ids invalid"
                )
            sets.append(set(values))
        for index, left in enumerate(sets):
            for right in sets[index + 1 :]:
                if left & right:
                    raise ArchitectAReadinessError(
                        "Architect A2 packet disposition overlap"
                    )
        exact = set().union(*sets) == known
        if self.exact_a2_surface != exact or not exact:
            raise ArchitectAReadinessError(
                "Architect A2 packet must cover exact 17-workstream surface"
            )
        expected_receipts = (
            len(self.completed_ids)
            + len(self.falsified_ids)
            + len(self.external_ids)
        )
        expected_terminal = len(self.completed_ids) + len(self.falsified_ids)
        if self.receipt_count != expected_receipts:
            raise ArchitectAReadinessError(
                "Architect A2 packet receipt partition drift"
            )
        if self.terminal_count != expected_terminal:
            raise ArchitectAReadinessError(
                "Architect A2 packet terminal partition drift"
            )
        expected_ready = (
            expected_terminal == len(A2_WORKSTREAM_IDS)
            and not self.external_ids
            and not self.missing_ids
        )
        if self.ready_for_integrator != expected_ready:
            raise ArchitectAReadinessError(
                "Architect A2 packet integrator-readiness drift"
            )
        if any(
            (
                self.ledger_update_authority,
                self.certification_claimed,
                self.productive_authority,
                self.merge_authority,
            )
        ):
            raise ArchitectAReadinessError(
                "Architect A2 packet grants no integration/production authority"
            )

    def as_dict(self) -> dict[str, object]:
        return asdict(self)

    def fingerprint(self) -> str:
        return _canonical_sha(self.as_dict())


def reconcile_architect_a2_scientific_dispositions(
    *,
    phase22_manifest_sha256: str,
    receipts: tuple[ArchitectAPhase22V2ScientificDispositionReceipt, ...],
) -> ArchitectA2ScientificClosurePacket:
    """Reconcile only A2 receipts; never consume or close the A1 surface."""

    _sha(phase22_manifest_sha256, "phase22_manifest_sha256")
    if (
        not isinstance(receipts, tuple)
        or any(
            not isinstance(
                item,
                ArchitectAPhase22V2ScientificDispositionReceipt,
            )
            for item in receipts
        )
    ):
        raise ArchitectAReadinessError(
            "Architect A2 receipts must be canonical tuple"
        )

    by_id: dict[str, ArchitectAPhase22V2ScientificDispositionReceipt] = {}
    for receipt in receipts:
        if receipt.schema != PHASE22_V2_SCIENTIFIC_DISPOSITION_SCHEMA:
            raise ArchitectAReadinessError(
                "Architect A2 receipt schema drift"
            )
        if receipt.workstream_id in A1_RESERVED_WORKSTREAM_IDS:
            raise ArchitectAReadinessError(
                "Architect A2 cannot consume A1-owned workstream receipt: "
                + receipt.workstream_id
            )
        if receipt.workstream_id not in A2_WORKSTREAM_IDS:
            raise ArchitectAReadinessError(
                "Architect A2 receipt outside owned workstream surface"
            )
        if receipt.phase22_manifest_sha256 != phase22_manifest_sha256:
            raise ArchitectAReadinessError(
                "Architect A2 receipt manifest lineage drift"
            )
        if receipt.workstream_id in by_id:
            raise ArchitectAReadinessError(
                "Architect A2 duplicate workstream receipt"
            )
        by_id[receipt.workstream_id] = receipt

    completed: list[str] = []
    falsified: list[str] = []
    external: list[str] = []
    missing: list[str] = []
    for workstream_id in A2_WORKSTREAM_IDS:
        receipt = by_id.get(workstream_id)
        if receipt is None:
            missing.append(workstream_id)
            continue
        if receipt.recommended_disposition == "COMPLETED_AND_PROVEN":
            completed.append(workstream_id)
        elif receipt.recommended_disposition == "FALSIFIED_AND_CLOSED":
            falsified.append(workstream_id)
        elif receipt.recommended_disposition == "EXTERNAL_DEPENDENCY_BLOCKED":
            external.append(workstream_id)
        else:
            raise ArchitectAReadinessError(
                "Architect A2 receipt disposition invalid"
            )

    terminal_count = len(completed) + len(falsified)
    return ArchitectA2ScientificClosurePacket(
        phase22_manifest_sha256=phase22_manifest_sha256,
        receipt_count=len(receipts),
        terminal_count=terminal_count,
        completed_ids=tuple(completed),
        falsified_ids=tuple(falsified),
        external_ids=tuple(external),
        missing_ids=tuple(missing),
        exact_a2_surface=True,
        ready_for_integrator=(
            terminal_count == len(A2_WORKSTREAM_IDS)
            and not external
            and not missing
        ),
    )


def assert_architect_a2_ownership_partition() -> None:
    """Fail closed if the A1/A2 ownership boundary ever overlaps."""

    a1 = set(A1_RESERVED_WORKSTREAM_IDS)
    a2 = set(A2_WORKSTREAM_IDS)
    if a1 & a2:
        raise ArchitectAReadinessError(
            "Architect A1/A2 ownership overlap"
        )
    if len(a1) != 18 or len(a2) != 17:
        raise ArchitectAReadinessError(
            "Architect A1/A2 ownership cardinality drift"
        )


assert_architect_a2_ownership_partition()
