"""Pre-outcome runtime composition for CE2I T12 shadow evidence.

The canonical V3 policy decision is sealed first. This module then evaluates
the preregistered T12 tool-eligibility control from the exact same causal
evidence and persists the comparison in the durable T12 shadow ledger before
any same-epoch outcome exists.

It never rewrites the baseline policy, never changes sizing/Risk/execution and
has no broker mutation path. Existing complete shadow seals are returned
idempotently on restart.
"""

from __future__ import annotations

from dataclasses import dataclass

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_evidence import (
    Phase20ForwardDecisionEvidence,
    Phase20ForwardDecisionRecord,
    phase20_forward_evidence_sha256,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_policy_store import (
    VersionedPhase20ForwardPolicyBook,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    VersionedPhase20ForwardEvidenceBook,
)
from qore.infrastructure.cibo_ce2i_phase20_t12_shadow_policy import (
    T12_SHADOW_POLICY_FROZEN_AT,
    evaluate_phase20_t12_shadow_decision,
)
from qore.infrastructure.cibo_ce2i_phase20_t12_shadow_store import (
    DurableT12ShadowDecisionStore,
    T12ShadowDecisionSeal,
)


@dataclass(frozen=True, slots=True)
class Phase20T12RuntimeShadowSeal:
    decision_evidence_sha256: str
    shadow_generation: int
    shadow_decision_sha256: str
    baseline_policy_record_sha256: str
    selection_changed: bool
    allocator_changed: bool
    treatment_selected_signal_fingerprints: tuple[str, ...]
    control_selected_signal_fingerprints: tuple[str, ...]
    broker_mutation_performed: bool = False
    runtime_authority: bool = False
    risk_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        for name in (
            "decision_evidence_sha256",
            "shadow_decision_sha256",
            "baseline_policy_record_sha256",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, str)
                or not value.startswith("sha256:")
                or len(value) != 71
            ):
                raise CiboCapitalManagementError(
                    f"Phase20 T12 runtime {name} must be canonical SHA-256"
                )
        if (
            not isinstance(self.shadow_generation, int)
            or isinstance(self.shadow_generation, bool)
            or self.shadow_generation < 1
        ):
            raise CiboCapitalManagementError(
                "Phase20 T12 runtime shadow_generation must be positive int"
            )
        for name in (
            "selection_changed",
            "allocator_changed",
            "broker_mutation_performed",
            "runtime_authority",
            "risk_authority",
            "execution_authority",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(
                    f"Phase20 T12 runtime {name} must be bool"
                )
        for name in (
            "treatment_selected_signal_fingerprints",
            "control_selected_signal_fingerprints",
        ):
            values = getattr(self, name)
            if len(values) != len(set(values)):
                raise CiboCapitalManagementError(
                    f"Phase20 T12 runtime {name} must be unique"
                )
        expected_changed = (
            self.treatment_selected_signal_fingerprints
            != self.control_selected_signal_fingerprints
        )
        if self.selection_changed != expected_changed:
            raise CiboCapitalManagementError(
                "Phase20 T12 runtime selection flag drift"
            )
        if (
            self.broker_mutation_performed
            or self.runtime_authority
            or self.risk_authority
            or self.execution_authority
        ):
            raise CiboCapitalManagementError(
                "Phase20 T12 runtime shadow cannot gain operational authority"
            )


def seal_phase20_t12_runtime_shadow(
    *,
    evidence: Phase20ForwardDecisionEvidence,
    decision_record: Phase20ForwardDecisionRecord,
    evidence_book: VersionedPhase20ForwardEvidenceBook,
    policy_book: VersionedPhase20ForwardPolicyBook,
    shadow_store: DurableT12ShadowDecisionStore,
) -> Phase20T12RuntimeShadowSeal | None:
    """Seal one T12 treatment/control decision after baseline, before outcome."""

    if not isinstance(evidence, Phase20ForwardDecisionEvidence):
        raise CiboCapitalManagementError(
            "Phase20 T12 runtime requires canonical forward evidence"
        )
    if not isinstance(decision_record, Phase20ForwardDecisionRecord):
        raise CiboCapitalManagementError(
            "Phase20 T12 runtime requires canonical policy record"
        )
    if not isinstance(evidence_book, VersionedPhase20ForwardEvidenceBook):
        raise CiboCapitalManagementError(
            "Phase20 T12 runtime requires canonical evidence book"
        )
    if not isinstance(policy_book, VersionedPhase20ForwardPolicyBook):
        raise CiboCapitalManagementError(
            "Phase20 T12 runtime requires canonical policy book"
        )
    if not isinstance(shadow_store, DurableT12ShadowDecisionStore):
        raise CiboCapitalManagementError(
            "Phase20 T12 runtime shadow store is invalid"
        )
    if evidence.decision_at < T12_SHADOW_POLICY_FROZEN_AT:
        return None

    evidence_sha = phase20_forward_evidence_sha256(evidence)
    if decision_record.evidence_sha256 != evidence_sha:
        raise CiboCapitalManagementError(
            "Phase20 T12 runtime policy/evidence digest drift"
        )
    durable_decision = evidence_book.decision_for_sha(evidence_sha)
    if durable_decision is None:
        raise CiboCapitalManagementError(
            "Phase20 T12 runtime requires durable forward decision"
        )
    if durable_decision.decision_epoch_id != evidence.decision_epoch_id:
        raise CiboCapitalManagementError(
            "Phase20 T12 runtime durable decision epoch drift"
        )
    baseline = policy_book.decision_for_evidence(evidence_sha)
    if baseline is None:
        raise CiboCapitalManagementError(
            "Phase20 T12 runtime requires durable baseline policy"
        )

    current = shadow_store.load()
    existing = current.decision_for_evidence(evidence_sha)
    if existing is not None:
        return _runtime_seal(
            shadow=existing,
            baseline_policy_record_sha256=baseline.policy_record_sha256,
            shadow_generation=current.generation,
        )

    shadow, _ = evaluate_phase20_t12_shadow_decision(
        evidence=evidence,
        treatment_record=decision_record,
    )
    updated = shadow_store.seal_shadow_decision(
        shadow,
        evidence_book=evidence_book,
        policy_book=policy_book,
        expected_generation=current.generation,
    )
    existing = updated.decision_for_evidence(evidence_sha)
    if existing is None:
        raise CiboCapitalManagementError(
            "Phase20 T12 runtime shadow seal missing after write"
        )
    return _runtime_seal(
        shadow=existing,
        baseline_policy_record_sha256=baseline.policy_record_sha256,
        shadow_generation=updated.generation,
    )


def _runtime_seal(
    *,
    shadow: T12ShadowDecisionSeal,
    baseline_policy_record_sha256: str,
    shadow_generation: int,
) -> Phase20T12RuntimeShadowSeal:
    if shadow.baseline_policy_record_sha256 != baseline_policy_record_sha256:
        raise CiboCapitalManagementError(
            "Phase20 T12 runtime baseline durable binding drift"
        )
    return Phase20T12RuntimeShadowSeal(
        decision_evidence_sha256=shadow.decision_evidence_sha256,
        shadow_generation=shadow_generation,
        shadow_decision_sha256=shadow.shadow_decision_sha256,
        baseline_policy_record_sha256=shadow.baseline_policy_record_sha256,
        selection_changed=shadow.selection_changed,
        allocator_changed=shadow.allocator_changed,
        treatment_selected_signal_fingerprints=(
            shadow.treatment_selected_signal_fingerprints
        ),
        control_selected_signal_fingerprints=(
            shadow.control_selected_signal_fingerprints
        ),
        broker_mutation_performed=False,
        runtime_authority=False,
        risk_authority=False,
        execution_authority=False,
    )
