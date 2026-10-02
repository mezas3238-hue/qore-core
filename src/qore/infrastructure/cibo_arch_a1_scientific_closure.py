"""Architect A1 scientific-closure packet for CIBO Phase22.

A1 owns the causal CE2I / GEN-C2..GEN-C7 / temporal scientific surface. This
module consumes the canonical full Architect-A Phase22 evidence matrix and
scientific disposition receipts, but filters strictly to the isolated A1
ownership partition.

It never edits the Master Ledger, consumes A2 ownership as A1 work, grants
certification, or grants productive authority.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass

from qore.infrastructure.cibo_a1_scientific_disposition import A1_WORKSTREAMS
from qore.infrastructure.cibo_arch_a_internal_readiness import (
    PHASE22_V2_SCIENTIFIC_DISPOSITION_SCHEMA,
    ArchitectAPhase22V2ScientificDispositionReceipt,
    ArchitectAPhase22V2WorkstreamEvidenceMatrix,
    ArchitectAPhase22V2WorkstreamEvidenceState,
    ArchitectAReadinessError,
    _PHASE22_V2_EVIDENCE_REQUIREMENTS_BY_WORKSTREAM,
    evaluate_architect_a_phase22_v2_scientific_outcome,
)

A1_SCIENTIFIC_WAVE_1 = (
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
    "GEN-C4",
    "GEN-C7",
)
A1_SCIENTIFIC_WAVE_2 = ("GEN-C2", "GEN-C5", "GEN-C6")
A1_SCIENTIFIC_WAVE_3 = ("GEN-C3", "TEMPORAL_REPLICATION")
A1_SCIENTIFIC_WAVES = (
    A1_SCIENTIFIC_WAVE_1,
    A1_SCIENTIFIC_WAVE_2,
    A1_SCIENTIFIC_WAVE_3,
)

A2_FORBIDDEN_IDS = (
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


def _sha(value: str, name: str) -> None:
    if (
        not isinstance(value, str)
        or not value.startswith("sha256:")
        or len(value) != 71
        or any(ch not in "0123456789abcdef" for ch in value[7:])
    ):
        raise ArchitectAReadinessError(
            f"Architect A1 {name} must be canonical SHA-256"
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
class ArchitectA1EvidenceView:
    phase22_manifest_sha256: str
    states: tuple[ArchitectAPhase22V2WorkstreamEvidenceState, ...]
    ready_ids: tuple[str, ...]
    blocked_ids: tuple[str, ...]
    all_a1_workstreams_ready: bool
    a2_state_consumed: bool = False
    integration_authority: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        _sha(self.phase22_manifest_sha256, "phase22_manifest_sha256")
        if tuple(item.workstream_id for item in self.states) != A1_WORKSTREAMS:
            raise ArchitectAReadinessError(
                "Architect A1 evidence view coverage drift"
            )
        for state in self.states:
            expected = _PHASE22_V2_EVIDENCE_REQUIREMENTS_BY_WORKSTREAM[
                state.workstream_id
            ]
            if state.required_kinds != expected:
                raise ArchitectAReadinessError(
                    "Architect A1 evidence requirements drift"
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
                "Architect A1 evidence readiness partition drift"
            )
        if self.all_a1_workstreams_ready != (not self.blocked_ids):
            raise ArchitectAReadinessError(
                "Architect A1 evidence readiness flag drift"
            )
        if (
            self.a2_state_consumed
            or self.integration_authority
            or self.productive_authority
        ):
            raise ArchitectAReadinessError(
                "Architect A1 evidence view cannot consume A2/grant authority"
            )

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def view_architect_a1_evidence_matrix(
    matrix: ArchitectAPhase22V2WorkstreamEvidenceMatrix,
) -> ArchitectA1EvidenceView:
    """Filter the canonical full-A matrix without consuming A2-owned state."""

    if not isinstance(matrix, ArchitectAPhase22V2WorkstreamEvidenceMatrix):
        raise ArchitectAReadinessError(
            "Architect A1 evidence view requires canonical full-A matrix"
        )
    by_id = {item.workstream_id: item for item in matrix.states}
    states = tuple(by_id[item] for item in A1_WORKSTREAMS)
    ready = tuple(
        item.workstream_id for item in states if item.ready_for_frozen_evaluation
    )
    blocked = tuple(
        item.workstream_id
        for item in states
        if not item.ready_for_frozen_evaluation
    )
    return ArchitectA1EvidenceView(
        phase22_manifest_sha256=matrix.phase22_manifest_sha256,
        states=states,
        ready_ids=ready,
        blocked_ids=blocked,
        all_a1_workstreams_ready=not blocked,
    )


@dataclass(frozen=True, slots=True)
class ArchitectA1ScientificExecutionPlan:
    phase22_manifest_sha256: str
    wave_1_ids: tuple[str, ...]
    wave_2_ids: tuple[str, ...]
    wave_3_ids: tuple[str, ...]
    ready_now_ids: tuple[str, ...]
    blocked_now_ids: tuple[str, ...]
    exact_a1_surface: bool
    a2_execution_required: bool = False
    integration_authority: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        _sha(self.phase22_manifest_sha256, "phase22_manifest_sha256")
        waves = (
            self.wave_1_ids,
            self.wave_2_ids,
            self.wave_3_ids,
        )
        if waves != A1_SCIENTIFIC_WAVES:
            raise ArchitectAReadinessError(
                "Architect A1 scientific wave identity drift"
            )
        flattened = tuple(item for wave in waves for item in wave)
        exact = (
            len(flattened) == len(set(flattened))
            and set(flattened) == set(A1_WORKSTREAMS)
        )
        if self.exact_a1_surface != exact or not exact:
            raise ArchitectAReadinessError(
                "Architect A1 scientific plan coverage drift"
            )
        if set(self.ready_now_ids) & set(self.blocked_now_ids):
            raise ArchitectAReadinessError(
                "Architect A1 scientific plan readiness overlap"
            )
        if (
            set(self.ready_now_ids) | set(self.blocked_now_ids)
            != set(A1_WORKSTREAMS)
        ):
            raise ArchitectAReadinessError(
                "Architect A1 scientific plan readiness coverage drift"
            )
        if (
            self.a2_execution_required
            or self.integration_authority
            or self.productive_authority
        ):
            raise ArchitectAReadinessError(
                "Architect A1 plan cannot execute A2/grant authority"
            )

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def build_architect_a1_scientific_execution_plan(
    view: ArchitectA1EvidenceView,
) -> ArchitectA1ScientificExecutionPlan:
    if not isinstance(view, ArchitectA1EvidenceView):
        raise ArchitectAReadinessError(
            "Architect A1 scientific plan requires canonical evidence view"
        )
    return ArchitectA1ScientificExecutionPlan(
        phase22_manifest_sha256=view.phase22_manifest_sha256,
        wave_1_ids=A1_SCIENTIFIC_WAVE_1,
        wave_2_ids=A1_SCIENTIFIC_WAVE_2,
        wave_3_ids=A1_SCIENTIFIC_WAVE_3,
        ready_now_ids=view.ready_ids,
        blocked_now_ids=view.blocked_ids,
        exact_a1_surface=True,
        a2_execution_required=False,
    )


def evaluate_architect_a1_scientific_outcomes(
    *,
    matrix: ArchitectAPhase22V2WorkstreamEvidenceMatrix,
    payloads: tuple[dict[str, object], ...],
) -> tuple[ArchitectAPhase22V2ScientificDispositionReceipt, ...]:
    """Evaluate only evidence-ready A1 outcomes via canonical Phase22 law."""

    if not isinstance(matrix, ArchitectAPhase22V2WorkstreamEvidenceMatrix):
        raise ArchitectAReadinessError(
            "Architect A1 outcome evaluation requires canonical evidence matrix"
        )
    if (
        not isinstance(payloads, tuple)
        or any(not isinstance(item, dict) for item in payloads)
    ):
        raise ArchitectAReadinessError(
            "Architect A1 outcome payloads must be object tuple"
        )

    view = view_architect_a1_evidence_matrix(matrix)
    ready = set(view.ready_ids)
    by_id: dict[str, dict[str, object]] = {}
    for payload in payloads:
        raw_id = payload.get("workstream_id")
        if not isinstance(raw_id, str) or not raw_id:
            raise ArchitectAReadinessError(
                "Architect A1 outcome workstream id required"
            )
        if raw_id in A2_FORBIDDEN_IDS:
            raise ArchitectAReadinessError(
                "Architect A1 cannot evaluate A2-owned workstream: " + raw_id
            )
        if raw_id not in A1_WORKSTREAMS:
            raise ArchitectAReadinessError(
                "Architect A1 outcome outside owned workstream surface"
            )
        if raw_id not in ready:
            raise ArchitectAReadinessError(
                "Architect A1 outcome lacks frozen evidence readiness: " + raw_id
            )
        if raw_id in by_id:
            raise ArchitectAReadinessError(
                "Architect A1 duplicate scientific outcome payload"
            )
        by_id[raw_id] = payload

    receipts: list[ArchitectAPhase22V2ScientificDispositionReceipt] = []
    for workstream_id in A1_WORKSTREAMS:
        payload = by_id.get(workstream_id)
        if payload is None:
            continue
        receipts.append(
            evaluate_architect_a_phase22_v2_scientific_outcome(
                payload,
                matrix,
            )
        )
    return tuple(receipts)


@dataclass(frozen=True, slots=True)
class ArchitectA1ScientificClosurePacket:
    phase22_manifest_sha256: str
    receipt_count: int
    terminal_count: int
    completed_ids: tuple[str, ...]
    falsified_ids: tuple[str, ...]
    missing_ids: tuple[str, ...]
    exact_a1_surface: bool
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
                or not 0 <= value <= len(A1_WORKSTREAMS)
            ):
                raise ArchitectAReadinessError(
                    f"Architect A1 {name} invalid"
                )
        groups = (self.completed_ids, self.falsified_ids, self.missing_ids)
        known = set(A1_WORKSTREAMS)
        sets: list[set[str]] = []
        for values in groups:
            if (
                not isinstance(values, tuple)
                or any(item not in known for item in values)
                or len(values) != len(set(values))
            ):
                raise ArchitectAReadinessError(
                    "Architect A1 closure workstream ids invalid"
                )
            sets.append(set(values))
        for index, left in enumerate(sets):
            for right in sets[index + 1 :]:
                if left & right:
                    raise ArchitectAReadinessError(
                        "Architect A1 closure disposition overlap"
                    )
        exact = set().union(*sets) == known
        if self.exact_a1_surface != exact or not exact:
            raise ArchitectAReadinessError(
                "Architect A1 closure must cover exact 18-workstream surface"
            )
        if self.receipt_count != len(self.completed_ids) + len(self.falsified_ids):
            raise ArchitectAReadinessError(
                "Architect A1 closure receipt partition drift"
            )
        if self.terminal_count != self.receipt_count:
            raise ArchitectAReadinessError(
                "Architect A1 closure terminal count drift"
            )
        expected_ready = (
            self.terminal_count == len(A1_WORKSTREAMS)
            and not self.missing_ids
        )
        if self.ready_for_integrator != expected_ready:
            raise ArchitectAReadinessError(
                "Architect A1 closure integrator-readiness drift"
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
                "Architect A1 closure grants no integration/production authority"
            )

    def as_dict(self) -> dict[str, object]:
        return asdict(self)

    def fingerprint(self) -> str:
        return _canonical_sha(self.as_dict())


def reconcile_architect_a1_scientific_dispositions(
    *,
    phase22_manifest_sha256: str,
    receipts: tuple[ArchitectAPhase22V2ScientificDispositionReceipt, ...],
) -> ArchitectA1ScientificClosurePacket:
    """Reconcile only A1 terminal receipts; never consume/close A2 work."""

    _sha(phase22_manifest_sha256, "phase22_manifest_sha256")
    if (
        not isinstance(receipts, tuple)
        or any(
            not isinstance(item, ArchitectAPhase22V2ScientificDispositionReceipt)
            for item in receipts
        )
    ):
        raise ArchitectAReadinessError(
            "Architect A1 receipts must be canonical tuple"
        )

    by_id: dict[str, ArchitectAPhase22V2ScientificDispositionReceipt] = {}
    for receipt in receipts:
        if receipt.schema != PHASE22_V2_SCIENTIFIC_DISPOSITION_SCHEMA:
            raise ArchitectAReadinessError(
                "Architect A1 receipt schema drift"
            )
        if receipt.workstream_id in A2_FORBIDDEN_IDS:
            raise ArchitectAReadinessError(
                "Architect A1 cannot consume A2-owned workstream receipt: "
                + receipt.workstream_id
            )
        if receipt.workstream_id not in A1_WORKSTREAMS:
            raise ArchitectAReadinessError(
                "Architect A1 receipt outside owned workstream surface"
            )
        if receipt.phase22_manifest_sha256 != phase22_manifest_sha256:
            raise ArchitectAReadinessError(
                "Architect A1 receipt manifest lineage drift"
            )
        if receipt.workstream_id in by_id:
            raise ArchitectAReadinessError(
                "Architect A1 duplicate workstream receipt"
            )
        by_id[receipt.workstream_id] = receipt

    completed: list[str] = []
    falsified: list[str] = []
    missing: list[str] = []
    for workstream_id in A1_WORKSTREAMS:
        receipt = by_id.get(workstream_id)
        if receipt is None:
            missing.append(workstream_id)
            continue
        if receipt.recommended_disposition == "COMPLETED_AND_PROVEN":
            completed.append(workstream_id)
        elif receipt.recommended_disposition == "FALSIFIED_AND_CLOSED":
            falsified.append(workstream_id)
        else:
            raise ArchitectAReadinessError(
                "Architect A1 terminal closure cannot accept non-terminal receipt"
            )

    terminal_count = len(completed) + len(falsified)
    return ArchitectA1ScientificClosurePacket(
        phase22_manifest_sha256=phase22_manifest_sha256,
        receipt_count=len(receipts),
        terminal_count=terminal_count,
        completed_ids=tuple(completed),
        falsified_ids=tuple(falsified),
        missing_ids=tuple(missing),
        exact_a1_surface=True,
        ready_for_integrator=(
            terminal_count == len(A1_WORKSTREAMS) and not missing
        ),
    )


def assert_architect_a1_ownership_partition() -> None:
    a1 = set(A1_WORKSTREAMS)
    a2 = set(A2_FORBIDDEN_IDS)
    if a1 & a2:
        raise ArchitectAReadinessError(
            "Architect A1/A2 ownership overlap"
        )
    if len(a1) != 18 or len(a2) != 17:
        raise ArchitectAReadinessError(
            "Architect A1/A2 ownership cardinality drift"
        )


assert_architect_a1_ownership_partition()
