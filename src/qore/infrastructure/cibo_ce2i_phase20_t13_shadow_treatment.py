"""Causal T13 shadow treatment allocation for fresh OOS evaluation.

The treatment reuses the exact sealed Phase20D evidence and the same frozen
Phase20I -> Phase20H baseline. It changes only the stop-risk headroom delivered
to Phase20H by subtracting the preregistered T13 shadow reserve. Margin
headroom, regime, candidate set, expectations, concentration limits and every
other allocator input remain unchanged.

No outcome is accepted as input. No runtime sizing, Risk or execution authority
is granted. The resulting baseline/treatment selections are intended to be
sealed before outcomes and evaluated later only where canonical candidate
outcomes actually exist.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_evidence import (
    Phase20ForwardDecisionEvidence,
    Phase20ForwardEvidenceKind,
    build_phase20_forward_decision_record,
    phase20_forward_decision_record_sha256,
    phase20_forward_evidence_sha256,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_policy_store import (
    Phase20ForwardPolicyDecisionSeal,
)
from qore.infrastructure.cibo_ce2i_phase20_robust_allocator import (
    Phase20RobustAllocatorDecision,
    propose_phase20h_robust_allocation,
)
from qore.infrastructure.cibo_ce2i_phase20_t13_shadow_policy import (
    T13_SHADOW_POLICY_FROZEN_AT,
    Phase20T13ShadowRecommendation,
    t13_shadow_policy_sha256,
)


@dataclass(frozen=True, slots=True)
class Phase20T13ShadowTreatmentDecision:
    decision_epoch_id: str
    decision_evidence_sha256: str
    baseline_policy_record_sha256: str
    t13_policy_sha256: str
    reserve_triggered: bool
    shadow_reserved_risk_usd: Decimal
    baseline_allocator_input_stop_risk_usd: Decimal
    treatment_allocator_input_stop_risk_usd: Decimal
    allocator_input_margin_usd: Decimal
    baseline_selected_signal_fingerprints: tuple[str, ...]
    treatment_selected_signal_fingerprints: tuple[str, ...]
    baseline_only_signal_fingerprints: tuple[str, ...]
    treatment_only_signal_fingerprints: tuple[str, ...]
    treatment_allocator: Phase20RobustAllocatorDecision
    selection_changed: bool
    outcome_aware: bool
    runtime_authority: bool

    def __post_init__(self) -> None:
        if not self.decision_epoch_id:
            raise CiboCapitalManagementError(
                "Phase20 T13 treatment epoch id is required"
            )
        for name in (
            "decision_evidence_sha256",
            "baseline_policy_record_sha256",
            "t13_policy_sha256",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, str)
                or not value.startswith("sha256:")
                or len(value) != 71
            ):
                raise CiboCapitalManagementError(
                    f"Phase20 T13 treatment {name} must be SHA-256"
                )
        if self.t13_policy_sha256 != t13_shadow_policy_sha256():
            raise CiboCapitalManagementError(
                "Phase20 T13 treatment policy digest drift"
            )
        for name in (
            "shadow_reserved_risk_usd",
            "baseline_allocator_input_stop_risk_usd",
            "treatment_allocator_input_stop_risk_usd",
            "allocator_input_margin_usd",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value < 0
            ):
                raise CiboCapitalManagementError(
                    f"Phase20 T13 treatment {name} must be finite non-negative"
                )
        expected = max(
            Decimal(0),
            self.baseline_allocator_input_stop_risk_usd
            - self.shadow_reserved_risk_usd,
        )
        if self.treatment_allocator_input_stop_risk_usd != expected:
            raise CiboCapitalManagementError(
                "Phase20 T13 treatment risk headroom accounting drift"
            )
        if (
            self.treatment_allocator.deployable_stop_risk_usd
            > self.treatment_allocator_input_stop_risk_usd
            or self.treatment_allocator.deployable_margin_usd
            > self.allocator_input_margin_usd
        ):
            raise CiboCapitalManagementError(
                "Phase20 T13 treatment allocator exceeds shadow inputs"
            )
        for name in (
            "reserve_triggered",
            "selection_changed",
            "outcome_aware",
            "runtime_authority",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(
                    f"Phase20 T13 treatment {name} must be bool"
                )
        if self.outcome_aware or self.runtime_authority:
            raise CiboCapitalManagementError(
                "Phase20 T13 treatment cannot use outcomes or runtime authority"
            )
        baseline = set(self.baseline_selected_signal_fingerprints)
        treatment = set(self.treatment_selected_signal_fingerprints)
        if len(baseline) != len(self.baseline_selected_signal_fingerprints):
            raise CiboCapitalManagementError(
                "Phase20 T13 baseline selection must be unique"
            )
        if len(treatment) != len(self.treatment_selected_signal_fingerprints):
            raise CiboCapitalManagementError(
                "Phase20 T13 treatment selection must be unique"
            )
        if set(self.baseline_only_signal_fingerprints) != baseline - treatment:
            raise CiboCapitalManagementError(
                "Phase20 T13 baseline-only selection accounting drift"
            )
        if set(self.treatment_only_signal_fingerprints) != treatment - baseline:
            raise CiboCapitalManagementError(
                "Phase20 T13 treatment-only selection accounting drift"
            )
        if self.selection_changed != (baseline != treatment):
            raise CiboCapitalManagementError(
                "Phase20 T13 selection-change flag drift"
            )
        if not self.reserve_triggered and (
            self.shadow_reserved_risk_usd != 0
            or self.selection_changed
        ):
            raise CiboCapitalManagementError(
                "Phase20 T13 inactive reserve must reproduce baseline selection"
            )


def build_phase20_t13_shadow_treatment(
    *,
    evidence: Phase20ForwardDecisionEvidence,
    baseline_policy: Phase20ForwardPolicyDecisionSeal,
    recommendation: Phase20T13ShadowRecommendation,
) -> Phase20T13ShadowTreatmentDecision:
    """Re-run frozen Phase20H with only T13 risk headroom reserved."""

    if not isinstance(evidence, Phase20ForwardDecisionEvidence):
        raise CiboCapitalManagementError(
            "Phase20 T13 treatment requires canonical forward evidence"
        )
    if (
        evidence.evidence_kind
        is not Phase20ForwardEvidenceKind.FORWARD_OBSERVED
    ):
        raise CiboCapitalManagementError(
            "Phase20 T13 treatment requires FORWARD_OBSERVED evidence"
        )
    if evidence.decision_at < T13_SHADOW_POLICY_FROZEN_AT:
        raise CiboCapitalManagementError(
            "Phase20 T13 treatment cannot use pre-freeze evidence"
        )
    if not isinstance(
        baseline_policy,
        Phase20ForwardPolicyDecisionSeal,
    ):
        raise CiboCapitalManagementError(
            "Phase20 T13 treatment requires sealed baseline policy"
        )
    if not isinstance(
        recommendation,
        Phase20T13ShadowRecommendation,
    ):
        raise CiboCapitalManagementError(
            "Phase20 T13 treatment requires canonical recommendation"
        )

    evidence_sha = phase20_forward_evidence_sha256(evidence)
    if baseline_policy.evidence_sha256 != evidence_sha:
        raise CiboCapitalManagementError(
            "Phase20 T13 baseline policy evidence binding mismatch"
        )
    if (
        recommendation.decision_evidence_sha256 != evidence_sha
        or recommendation.decision_epoch_id != evidence.decision_epoch_id
        or recommendation.decision_at != evidence.decision_at
    ):
        raise CiboCapitalManagementError(
            "Phase20 T13 recommendation evidence binding mismatch"
        )
    if recommendation.policy_sha256 != t13_shadow_policy_sha256():
        raise CiboCapitalManagementError(
            "Phase20 T13 recommendation policy digest drift"
        )

    baseline_record = build_phase20_forward_decision_record(evidence)
    baseline_record_sha = phase20_forward_decision_record_sha256(
        baseline_record
    )
    if baseline_record_sha != baseline_policy.policy_record_sha256:
        raise CiboCapitalManagementError(
            "Phase20 T13 baseline policy cannot be reproduced exactly"
        )
    baseline_selected = _selected(
        baseline_record.allocator_decision
    )
    if (
        baseline_selected
        != baseline_policy.selected_signal_fingerprints
        or baseline_record.allocator_decision.disposition.value
        != baseline_policy.allocator_disposition
    ):
        raise CiboCapitalManagementError(
            "Phase20 T13 sealed baseline policy selection drift"
        )

    baseline_risk = (
        baseline_record.allocator_input_stop_risk_headroom_usd
    )
    treatment_risk = max(
        Decimal(0),
        baseline_risk - recommendation.reserved_risk_usd,
    )
    margin = baseline_record.allocator_input_margin_headroom_usd
    treatment_allocator = propose_phase20h_robust_allocation(
        mission=evidence.mission,
        regime=baseline_record.regime,
        hard_risk_headroom_usd=treatment_risk,
        margin_headroom_usd=margin,
        concentration_limit_by_group=(
            evidence.concentration_limit_by_group
        ),
        candidates=tuple(
            item.candidate for item in evidence.candidates
        ),
        known_options=(),
    )
    treatment_selected = _selected(treatment_allocator)
    candidate_signals = {
        item.candidate.signal_fingerprint
        for item in evidence.candidates
    }
    if (
        not set(baseline_selected).issubset(candidate_signals)
        or not set(treatment_selected).issubset(candidate_signals)
    ):
        raise CiboCapitalManagementError(
            "Phase20 T13 shadow selection escaped sealed candidates"
        )

    baseline_set = set(baseline_selected)
    treatment_set = set(treatment_selected)
    return Phase20T13ShadowTreatmentDecision(
        decision_epoch_id=evidence.decision_epoch_id,
        decision_evidence_sha256=evidence_sha,
        baseline_policy_record_sha256=baseline_record_sha,
        t13_policy_sha256=recommendation.policy_sha256,
        reserve_triggered=recommendation.reserve_triggered,
        shadow_reserved_risk_usd=recommendation.reserved_risk_usd,
        baseline_allocator_input_stop_risk_usd=baseline_risk,
        treatment_allocator_input_stop_risk_usd=treatment_risk,
        allocator_input_margin_usd=margin,
        baseline_selected_signal_fingerprints=baseline_selected,
        treatment_selected_signal_fingerprints=treatment_selected,
        baseline_only_signal_fingerprints=tuple(
            signal
            for signal in baseline_selected
            if signal not in treatment_set
        ),
        treatment_only_signal_fingerprints=tuple(
            signal
            for signal in treatment_selected
            if signal not in baseline_set
        ),
        treatment_allocator=treatment_allocator,
        selection_changed=baseline_set != treatment_set,
        outcome_aware=False,
        runtime_authority=False,
    )


def _selected(
    decision: Phase20RobustAllocatorDecision,
) -> tuple[str, ...]:
    if decision.allocation is None:
        return ()
    return decision.allocation.selected_signal_fingerprints
