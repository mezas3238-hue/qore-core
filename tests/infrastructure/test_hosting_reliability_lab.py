from __future__ import annotations

from dataclasses import FrozenInstanceError, fields
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

import qore.infrastructure.client_accounts as accounts
import qore.infrastructure.hosting_reliability_lab as lab
import qore.kernel.result as result

_NOW = datetime(2026, 8, 10, 3, 0, tzinfo=UTC)
_ACCOUNT = accounts.TradingAccountId(UUID("55000000-0000-0000-0000-000000000003"))
_RUNTIME = accounts.ExecutionRuntimeReference(
    UUID("55000000-0000-0000-0000-000000000004")
)


def _uuid(suffix: int) -> UUID:
    return UUID(f"55000000-0000-0000-0000-{suffix:012d}")


def _observation(
    *,
    condition: lab.HostingReliabilityCondition = lab.HostingReliabilityCondition.ANOMALOUS,
    severity: lab.HostingReliabilitySeverity = lab.HostingReliabilitySeverity.DEGRADED,
) -> lab.HostingReliabilityObservation:
    return lab.HostingReliabilityObservation(
        observation_id=lab.HostingReliabilityObservationId(_uuid(10)),
        account_id=_ACCOUNT,
        runtime_ref=_RUNTIME,
        boundary=lab.HostingReliabilityBoundary.NETWORK_EGRESS,
        condition=condition,
        severity=severity,
        observed_at=_NOW,
        evidence_ref=lab.HostingReliabilityEvidenceReference(_uuid(11)),
    )


def _policy(
    *actions: lab.HostingReliabilityInfrastructureAction,
    effective_at: datetime = _NOW - timedelta(minutes=1),
    expires_at: datetime | None = None,
) -> lab.HostingReliabilityPolicySnapshot:
    return lab.HostingReliabilityPolicySnapshot(
        policy_ref=lab.HostingReliabilityPolicyReference(_uuid(20)),
        version=1,
        allowed_actions=(lab.HostingReliabilityInfrastructureAction.NO_ACTION, *actions),
        effective_at=effective_at,
        expires_at=expires_at,
    )


def _assessment(
    action: lab.HostingReliabilityInfrastructureAction,
    *,
    observation: lab.HostingReliabilityObservation | None = None,
) -> result.Result[lab.HostingReliabilityAssessment, lab.HostingReliabilityLabError]:
    observed = observation or _observation()
    return lab.assess_hosting_reliability_observation(
        observed,
        _policy(action),
        assessment_id=lab.HostingReliabilityAssessmentId(_uuid(30)),
        authorized_action=action,
        rationale_code=lab.HostingReliabilityRationaleCode("egress.degraded"),
        assessed_at=_NOW + timedelta(seconds=1),
        supporting_evidence_refs=(
            lab.HostingReliabilityEvidenceReference(_uuid(31)),
        ),
    )


def test_anomaly_can_authorize_only_policy_allowed_containment_intent() -> None:
    assessed = _assessment(lab.HostingReliabilityInfrastructureAction.CONTAIN_NEW_WORK)

    assert isinstance(assessed, result.Success)
    assert assessed.value.authorized_action is (
        lab.HostingReliabilityInfrastructureAction.CONTAIN_NEW_WORK
    )
    assert assessed.value.policy_ref == lab.HostingReliabilityPolicyReference(_uuid(20))
    assert assessed.value.observation_id == lab.HostingReliabilityObservationId(_uuid(10))
    assert assessed.value.evidence_refs == (
        lab.HostingReliabilityEvidenceReference(_uuid(11)),
        lab.HostingReliabilityEvidenceReference(_uuid(31)),
    )


def test_no_reliability_evidence_is_impossible_for_assessment_contract() -> None:
    with pytest.raises(lab.HostingReliabilityLabValidationError):
        lab.HostingReliabilityAssessment(
            assessment_id=lab.HostingReliabilityAssessmentId(_uuid(40)),
            observation_id=lab.HostingReliabilityObservationId(_uuid(41)),
            account_id=_ACCOUNT,
            runtime_ref=_RUNTIME,
            policy_ref=lab.HostingReliabilityPolicyReference(_uuid(42)),
            authorized_action=lab.HostingReliabilityInfrastructureAction.NO_ACTION,
            rationale_code=lab.HostingReliabilityRationaleCode("threshold.not_met"),
            evidence_refs=(),
            assessed_at=_NOW,
        )


def test_normal_observation_records_justified_no_action() -> None:
    normal = _observation(
        condition=lab.HostingReliabilityCondition.NORMAL,
        severity=lab.HostingReliabilitySeverity.INFO,
    )
    assessed = lab.assess_hosting_reliability_observation(
        normal,
        _policy(),
        assessment_id=lab.HostingReliabilityAssessmentId(_uuid(50)),
        authorized_action=lab.HostingReliabilityInfrastructureAction.NO_ACTION,
        rationale_code=lab.HostingReliabilityRationaleCode("threshold.not_met"),
        assessed_at=_NOW + timedelta(seconds=1),
    )
    assert isinstance(assessed, result.Success)

    recorded = lab.record_hosting_reliability_action(
        assessed.value,
        action_id=lab.HostingReliabilityActionId(_uuid(51)),
        action=lab.HostingReliabilityInfrastructureAction.NO_ACTION,
        outcome=lab.HostingReliabilityActionOutcome.NO_ACTION_RECORDED,
        occurred_at=_NOW + timedelta(seconds=2),
        evidence_ref=lab.HostingReliabilityEvidenceReference(_uuid(52)),
    )
    assert isinstance(recorded, result.Success)
    assert recorded.value.outcome is lab.HostingReliabilityActionOutcome.NO_ACTION_RECORDED


def test_normal_observation_cannot_authorize_intervention_even_if_policy_lists_it() -> None:
    normal = _observation(
        condition=lab.HostingReliabilityCondition.NORMAL,
        severity=lab.HostingReliabilitySeverity.WARNING,
    )
    assessed = lab.assess_hosting_reliability_observation(
        normal,
        _policy(lab.HostingReliabilityInfrastructureAction.CONTAIN_NEW_WORK),
        assessment_id=lab.HostingReliabilityAssessmentId(_uuid(60)),
        authorized_action=lab.HostingReliabilityInfrastructureAction.CONTAIN_NEW_WORK,
        rationale_code=lab.HostingReliabilityRationaleCode("no_intervention_expected"),
        assessed_at=_NOW + timedelta(seconds=1),
    )

    assert isinstance(assessed, result.Failure)
    assert isinstance(assessed.error, lab.HostingReliabilityLabAuthorizationError)


def test_action_not_authorized_by_policy_fails_closed() -> None:
    assessed = lab.assess_hosting_reliability_observation(
        _observation(),
        _policy(lab.HostingReliabilityInfrastructureAction.CONTAIN_NEW_WORK),
        assessment_id=lab.HostingReliabilityAssessmentId(_uuid(70)),
        authorized_action=lab.HostingReliabilityInfrastructureAction.RUN_STABILIZATION,
        rationale_code=lab.HostingReliabilityRationaleCode("stabilization.requested"),
        assessed_at=_NOW + timedelta(seconds=1),
    )

    assert isinstance(assessed, result.Failure)
    assert isinstance(assessed.error, lab.HostingReliabilityLabAuthorizationError)


def test_expired_policy_cannot_authorize_new_infrastructure_intent() -> None:
    policy = _policy(
        lab.HostingReliabilityInfrastructureAction.CONTAIN_NEW_WORK,
        effective_at=_NOW - timedelta(minutes=5),
        expires_at=_NOW,
    )
    assessed = lab.assess_hosting_reliability_observation(
        _observation(),
        policy,
        assessment_id=lab.HostingReliabilityAssessmentId(_uuid(80)),
        authorized_action=lab.HostingReliabilityInfrastructureAction.CONTAIN_NEW_WORK,
        rationale_code=lab.HostingReliabilityRationaleCode("egress.degraded"),
        assessed_at=_NOW + timedelta(seconds=1),
    )

    assert isinstance(assessed, result.Failure)
    assert isinstance(assessed.error, lab.HostingReliabilityLabAuthorizationError)


def test_recorded_action_must_match_exact_assessment_authorization() -> None:
    assessed = _assessment(lab.HostingReliabilityInfrastructureAction.CONTAIN_NEW_WORK)
    assert isinstance(assessed, result.Success)

    recorded = lab.record_hosting_reliability_action(
        assessed.value,
        action_id=lab.HostingReliabilityActionId(_uuid(90)),
        action=lab.HostingReliabilityInfrastructureAction.RUN_STABILIZATION,
        outcome=lab.HostingReliabilityActionOutcome.SUCCEEDED,
        occurred_at=_NOW + timedelta(seconds=2),
        evidence_ref=lab.HostingReliabilityEvidenceReference(_uuid(91)),
    )

    assert isinstance(recorded, result.Failure)
    assert isinstance(recorded.error, lab.HostingReliabilityLabAuthorizationError)


def test_action_record_is_evidence_only_and_does_not_mutate_provider_or_lease() -> None:
    assessed = _assessment(lab.HostingReliabilityInfrastructureAction.CONTAIN_NEW_WORK)
    assert isinstance(assessed, result.Success)

    recorded = lab.record_hosting_reliability_action(
        assessed.value,
        action_id=lab.HostingReliabilityActionId(_uuid(100)),
        action=lab.HostingReliabilityInfrastructureAction.CONTAIN_NEW_WORK,
        outcome=lab.HostingReliabilityActionOutcome.SUCCEEDED,
        occurred_at=_NOW + timedelta(seconds=2),
        evidence_ref=lab.HostingReliabilityEvidenceReference(_uuid(101)),
    )
    assert isinstance(recorded, result.Success)
    assert recorded.value.account_id == _ACCOUNT
    assert recorded.value.runtime_ref == _RUNTIME
    assert not hasattr(recorded.value, "provider_mutation")
    assert not hasattr(recorded.value, "acquire_lease")
    assert not hasattr(recorded.value, "revoke_lease")


def test_lab_actions_expose_no_direct_failover_or_trading_authority() -> None:
    actions = {action.value for action in lab.HostingReliabilityInfrastructureAction}

    assert actions == {
        "no_action",
        "contain_new_work",
        "run_stabilization",
        "initiate_failover_evaluation",
    }
    assert "failover" not in actions
    assert "switch_server" not in actions
    assert "buy" not in actions
    assert "sell" not in actions
    assert "submit_order" not in actions
    assert "retry_order" not in actions
    assert "redispatch" not in actions

    prohibited = {
        "buy",
        "core_decision",
        "close_position",
        "liquidate",
        "set_risk",
        "submit_order",
        "retry_order",
        "redispatch",
        "provider_sdk",
    }
    for surface in (
        lab.HostingReliabilityObservation,
        lab.HostingReliabilityPolicySnapshot,
        lab.HostingReliabilityAssessment,
        lab.HostingReliabilityActionRecord,
    ):
        assert prohibited.isdisjoint(set(dir(surface)))


def test_lab_contracts_use_canonical_account_and_runtime_types() -> None:
    observation_fields = {
        field.name: field.type for field in fields(lab.HostingReliabilityObservation)
    }
    assessment_fields = {
        field.name: field.type for field in fields(lab.HostingReliabilityAssessment)
    }

    assert observation_fields["account_id"] == "TradingAccountId"
    assert observation_fields["runtime_ref"] == "ExecutionRuntimeReference"
    assert assessment_fields["account_id"] == "TradingAccountId"
    assert assessment_fields["runtime_ref"] == "ExecutionRuntimeReference"


def test_unknown_observation_is_explicit_and_fail_closed() -> None:
    unknown = _observation(
        condition=lab.HostingReliabilityCondition.UNKNOWN,
        severity=lab.HostingReliabilitySeverity.UNKNOWN,
    )
    assessed = lab.assess_hosting_reliability_observation(
        unknown,
        _policy(lab.HostingReliabilityInfrastructureAction.CONTAIN_NEW_WORK),
        assessment_id=lab.HostingReliabilityAssessmentId(_uuid(110)),
        authorized_action=lab.HostingReliabilityInfrastructureAction.CONTAIN_NEW_WORK,
        rationale_code=lab.HostingReliabilityRationaleCode("state.unknown.contain"),
        assessed_at=_NOW + timedelta(seconds=1),
    )

    assert isinstance(assessed, result.Success)
    assert assessed.value.authorized_action is (
        lab.HostingReliabilityInfrastructureAction.CONTAIN_NEW_WORK
    )


def test_temporal_and_outcome_invariants_are_strict() -> None:
    with pytest.raises(lab.HostingReliabilityLabValidationError):
        lab.HostingReliabilityObservation(
            observation_id=lab.HostingReliabilityObservationId(_uuid(120)),
            account_id=_ACCOUNT,
            runtime_ref=_RUNTIME,
            boundary=lab.HostingReliabilityBoundary.RUNTIME,
            condition=lab.HostingReliabilityCondition.NORMAL,
            severity=lab.HostingReliabilitySeverity.INFO,
            observed_at=datetime(2026, 8, 10, 3, 0),
            evidence_ref=lab.HostingReliabilityEvidenceReference(_uuid(121)),
        )

    with pytest.raises(lab.HostingReliabilityLabValidationError):
        lab.HostingReliabilityActionRecord(
            action_id=lab.HostingReliabilityActionId(_uuid(122)),
            assessment_id=lab.HostingReliabilityAssessmentId(_uuid(123)),
            account_id=_ACCOUNT,
            runtime_ref=_RUNTIME,
            action=lab.HostingReliabilityInfrastructureAction.NO_ACTION,
            outcome=lab.HostingReliabilityActionOutcome.SUCCEEDED,
            occurred_at=_NOW,
            evidence_ref=lab.HostingReliabilityEvidenceReference(_uuid(124)),
        )


def test_contracts_are_immutable() -> None:
    observation = _observation()
    attribute_name = "condition"

    with pytest.raises(FrozenInstanceError):
        setattr(observation, attribute_name, lab.HostingReliabilityCondition.NORMAL)
