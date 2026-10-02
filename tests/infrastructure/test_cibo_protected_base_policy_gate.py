from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_protected_base_overlay import ProtectedBaseClass
from qore.infrastructure.cibo_protected_base_policy_gate import (
    PROTECTED_BASE_GATE_SHA256,
    ProtectedBaseCandidateRole,
    ProtectedBaseEconomicObservation,
    ProtectedBaseGateStatus,
    ProtectedBasePolicyCandidate,
    evaluate_protected_base_gate,
)

FROZEN = datetime(2026, 9, 30, 19, 0, tzinfo=UTC)
START = datetime(2026, 9, 30, 20, 0, tzinfo=UTC)
END = datetime(2026, 9, 30, 21, 0, tzinfo=UTC)


def _candidate(
    *,
    candidate_id: str,
    role: ProtectedBaseCandidateRole,
    amount: str,
    protection_class: ProtectedBaseClass = ProtectedBaseClass.POLICY_PROTECTED,
) -> ProtectedBasePolicyCandidate:
    return ProtectedBasePolicyCandidate(
        candidate_id=candidate_id,
        role=role,
        policy_id=f"policy-{candidate_id}",
        policy_sha256="sha256:" + ("1" if role is ProtectedBaseCandidateRole.CONTROL else "2") * 64,
        frozen_at=FROZEN,
        protected_base_usd=Decimal(amount),
        protection_class=protection_class,
    )


def _observation(
    candidate: ProtectedBasePolicyCandidate,
    *,
    ending: str = "110",
    minimum_base: str = "70",
    max_dd: str = "5",
    p99_dd: str = "4.5",
    plausible_loss: str = "6",
    margin: str = "20",
    recovery: str = "50",
    optionality: str = "15",
    provider_failure: str = "0.01",
    productivity: str = "1.2",
    population: str = "a",
) -> ProtectedBaseEconomicObservation:
    return ProtectedBaseEconomicObservation(
        candidate=candidate,
        population_sha256="sha256:" + population * 64,
        provider_surface_sha256="sha256:" + "b" * 64,
        fold_ids=("WF1", "WF2", "WF3", "WF4"),
        horizon_start=START,
        horizon_end=END,
        ending_realized_capital_usd=Decimal(ending),
        minimum_original_base_usd=Decimal(minimum_base),
        maximum_drawdown_usd=Decimal(max_dd),
        p99_drawdown_usd=Decimal(p99_dd),
        peak_plausible_loss_usd=Decimal(plausible_loss),
        peak_margin_occupancy_usd=Decimal(margin),
        p95_recovery_minutes=Decimal(recovery),
        minimum_optionality_usd=Decimal(optionality),
        provider_failure_incidence=Decimal(provider_failure),
        capital_risk_time_productivity=Decimal(productivity),
    )


def _control() -> ProtectedBaseEconomicObservation:
    return _observation(
        _candidate(
            candidate_id="control",
            role=ProtectedBaseCandidateRole.CONTROL,
            amount="0",
            protection_class=ProtectedBaseClass.ACCOUNTING_PROTECTED,
        )
    )


def test_protected_base_gate_digest_is_frozen() -> None:
    assert PROTECTED_BASE_GATE_SHA256 == (
        "sha256:05fa878b3e6f824851d559550fe7137bf457dd589eb46192547b51d0eb91ebc0"
    )


def test_protected_base_safe_candidate_is_research_eligible() -> None:
    treatment = _observation(
        _candidate(
            candidate_id="protect-60",
            role=ProtectedBaseCandidateRole.TREATMENT,
            amount="60",
        ),
        minimum_base="75",
        max_dd="4.5",
    )
    row = evaluate_protected_base_gate((_control(), treatment)).rows[1]
    assert row.status is ProtectedBaseGateStatus.ELIGIBLE_FOR_FURTHER_RESEARCH
    assert row.safety_no_worse is True
    assert row.strict_improvement is True


def test_more_base_protection_cannot_compensate_lower_ending_capital() -> None:
    treatment = _observation(
        _candidate(
            candidate_id="protect-80",
            role=ProtectedBaseCandidateRole.TREATMENT,
            amount="80",
        ),
        ending="109",
        minimum_base="85",
        max_dd="4",
    )
    row = evaluate_protected_base_gate((_control(), treatment)).rows[1]
    assert row.status is ProtectedBaseGateStatus.REJECTED_SAFETY_DETERIORATION
    assert "ending_realized_capital_usd" in row.failed_dimensions


def test_protected_base_gate_rejects_mismatched_population() -> None:
    treatment = _observation(
        _candidate(
            candidate_id="protect-50",
            role=ProtectedBaseCandidateRole.TREATMENT,
            amount="50",
        ),
        population="c",
        minimum_base="75",
    )
    with pytest.raises(
        CiboCapitalManagementError,
        match="identical causal comparison surface",
    ):
        evaluate_protected_base_gate((_control(), treatment))


def test_broker_guarantee_requires_provider_evidence() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="requires provider evidence",
    ):
        _candidate(
            candidate_id="broker",
            role=ProtectedBaseCandidateRole.TREATMENT,
            amount="50",
            protection_class=ProtectedBaseClass.BROKER_GUARANTEED,
        )


def test_numeric_candidate_must_freeze_before_evaluation() -> None:
    treatment = _candidate(
        candidate_id="late",
        role=ProtectedBaseCandidateRole.TREATMENT,
        amount="50",
    )
    late = replace(treatment, frozen_at=START.replace(hour=20, minute=1))
    with pytest.raises(
        CiboCapitalManagementError,
        match="freeze before evaluation",
    ):
        _observation(late)

def test_protected_base_row_rejects_manual_status_metric_drift() -> None:
    treatment = _observation(
        _candidate(
            candidate_id="protect-60",
            role=ProtectedBaseCandidateRole.TREATMENT,
            amount="60",
        ),
        minimum_base="75",
        max_dd="4.5",
    )
    row = evaluate_protected_base_gate((_control(), treatment)).rows[1]

    with pytest.raises(
        CiboCapitalManagementError,
        match="status/metric drift",
    ):
        replace(row, safety_no_worse=False)



def test_protected_base_candidate_rejects_malformed_numeric_or_bool_fields() -> None:
    control = _candidate(
        candidate_id="control-types",
        role=ProtectedBaseCandidateRole.CONTROL,
        amount="0",
        protection_class=ProtectedBaseClass.ACCOUNTING_PROTECTED,
    )

    with pytest.raises(
        CiboCapitalManagementError,
        match="finite non-negative Decimal",
    ):
        replace(control, protected_base_usd=0.0)

    with pytest.raises(
        CiboCapitalManagementError,
        match="numeric_candidate_frozen must be bool",
    ):
        replace(control, numeric_candidate_frozen=1)


def test_protected_base_observation_rejects_nonfinite_or_untyped_metrics() -> None:
    observation = _control()

    with pytest.raises(
        CiboCapitalManagementError,
        match="maximum_drawdown_usd must be finite non-negative Decimal",
    ):
        replace(observation, maximum_drawdown_usd=Decimal("NaN"))

    with pytest.raises(
        CiboCapitalManagementError,
        match="capital_risk_time_productivity must be finite Decimal",
    ):
        replace(
            observation,
            capital_risk_time_productivity=Decimal("Infinity"),
        )

    with pytest.raises(
        CiboCapitalManagementError,
        match="fold ids must be non-empty unique strings",
    ):
        replace(observation, fold_ids=("WF1", ""))

    with pytest.raises(
        CiboCapitalManagementError,
        match="hindsight_retuned must be bool",
    ):
        replace(observation, hindsight_retuned=0)
