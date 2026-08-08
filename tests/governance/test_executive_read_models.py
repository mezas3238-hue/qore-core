from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from qore.governance.executive_control import ExecutiveReadScope
from qore.governance.executive_ports import ExecutiveEvidenceRef
from qore.governance.executive_read_models import (
    ExecutiveAttentionLevel,
    ExecutiveCiboAuthorizationState,
    ExecutiveCiboConfidenceState,
    ExecutiveCiboJudgment,
    ExecutiveCiboOperationalState,
    ExecutiveCiboReadModel,
    ExecutiveComponentHealth,
    ExecutiveComponentHealthState,
    ExecutivePolicyVersionRef,
    ExecutiveProjectionId,
    ExecutiveProjectionMetadata,
    ExecutiveProjectionVersion,
    ExecutiveReadModelValidationError,
    ExecutiveReadinessState,
    ExecutiveSourceFreshness,
    ExecutiveSystemHealthReadModel,
    ExecutiveSystemHealthState,
    ExecutiveUncertaintyState,
)

_NOW = datetime(2026, 8, 8, 21, 0, tzinfo=UTC)


def _metadata(scope: ExecutiveReadScope) -> ExecutiveProjectionMetadata:
    return ExecutiveProjectionMetadata(
        projection_id=ExecutiveProjectionId(
            UUID("29000000-0000-0000-0000-000000000001")
        ),
        projection_version=ExecutiveProjectionVersion("executive-read.v1"),
        scope=scope,
        source_observed_at=_NOW,
        projected_at=_NOW + timedelta(seconds=1),
        freshness=ExecutiveSourceFreshness.FRESH,
        evidence_refs=(ExecutiveEvidenceRef("evidence:executive/001"),),
        policy_versions=(
            ExecutivePolicyVersionRef("governance.v2"),
            ExecutivePolicyVersionRef("risk.v4"),
        ),
    )


def test_projection_metadata_preserves_explicit_provenance() -> None:
    metadata = _metadata(ExecutiveReadScope.SYSTEM_HEALTH)

    assert metadata.scope is ExecutiveReadScope.SYSTEM_HEALTH
    assert metadata.source_observed_at == _NOW
    assert metadata.projected_at == _NOW + timedelta(seconds=1)
    assert tuple(item.value for item in metadata.policy_versions) == (
        "governance.v2",
        "risk.v4",
    )


def test_projection_metadata_rejects_naive_or_backdated_times() -> None:
    with pytest.raises(ExecutiveReadModelValidationError):
        ExecutiveProjectionMetadata(
            projection_id=ExecutiveProjectionId(
                UUID("29000000-0000-0000-0000-000000000002")
            ),
            projection_version=ExecutiveProjectionVersion("executive-read.v1"),
            scope=ExecutiveReadScope.SYSTEM_HEALTH,
            source_observed_at=datetime(2026, 8, 8, 21, 0),
            projected_at=_NOW,
            freshness=ExecutiveSourceFreshness.UNKNOWN,
        )

    with pytest.raises(ExecutiveReadModelValidationError):
        ExecutiveProjectionMetadata(
            projection_id=ExecutiveProjectionId(
                UUID("29000000-0000-0000-0000-000000000003")
            ),
            projection_version=ExecutiveProjectionVersion("executive-read.v1"),
            scope=ExecutiveReadScope.SYSTEM_HEALTH,
            source_observed_at=_NOW + timedelta(seconds=2),
            projected_at=_NOW + timedelta(seconds=1),
            freshness=ExecutiveSourceFreshness.STALE,
        )


def test_projection_metadata_sorts_refs_and_rejects_duplicates() -> None:
    metadata = ExecutiveProjectionMetadata(
        projection_id=ExecutiveProjectionId(
            UUID("29000000-0000-0000-0000-000000000004")
        ),
        projection_version=ExecutiveProjectionVersion("executive-read.v1"),
        scope=ExecutiveReadScope.SYSTEM_HEALTH,
        source_observed_at=_NOW,
        projected_at=_NOW,
        freshness=ExecutiveSourceFreshness.FRESH,
        evidence_refs=(
            ExecutiveEvidenceRef("evidence:z/002"),
            ExecutiveEvidenceRef("evidence:a/001"),
        ),
        policy_versions=(
            ExecutivePolicyVersionRef("risk.v4"),
            ExecutivePolicyVersionRef("governance.v2"),
        ),
    )

    assert tuple(item.value for item in metadata.evidence_refs) == (
        "evidence:a/001",
        "evidence:z/002",
    )
    assert tuple(item.value for item in metadata.policy_versions) == (
        "governance.v2",
        "risk.v4",
    )

    with pytest.raises(ExecutiveReadModelValidationError):
        ExecutiveProjectionMetadata(
            projection_id=ExecutiveProjectionId(
                UUID("29000000-0000-0000-0000-000000000005")
            ),
            projection_version=ExecutiveProjectionVersion("executive-read.v1"),
            scope=ExecutiveReadScope.SYSTEM_HEALTH,
            source_observed_at=_NOW,
            projected_at=_NOW,
            freshness=ExecutiveSourceFreshness.FRESH,
            evidence_refs=(
                ExecutiveEvidenceRef("evidence:duplicate/001"),
                ExecutiveEvidenceRef("evidence:duplicate/001"),
            ),
        )


def test_system_health_projection_is_scope_bound_and_deterministic() -> None:
    model = ExecutiveSystemHealthReadModel(
        metadata=_metadata(ExecutiveReadScope.SYSTEM_HEALTH),
        health=ExecutiveSystemHealthState.DEGRADED,
        readiness=ExecutiveReadinessState.NOT_READY,
        attention=ExecutiveAttentionLevel.IMPORTANT,
        reason_codes=("runtime.residual-components",),
        components=(
            ExecutiveComponentHealth(
                component_id="risk",
                state=ExecutiveComponentHealthState.HEALTHY,
            ),
            ExecutiveComponentHealth(
                component_id="runtime",
                state=ExecutiveComponentHealthState.DEGRADED,
                reason_codes=("runtime.residual-components",),
            ),
        ),
    )

    assert model.logical_values() == model.logical_values()
    assert model.metadata.scope is ExecutiveReadScope.SYSTEM_HEALTH
    assert tuple(item.component_id for item in model.components) == ("risk", "runtime")
    assert not hasattr(model, "runtime_snapshot")
    assert not hasattr(model, "provider_credentials")


def test_system_health_projection_rejects_wrong_scope() -> None:
    with pytest.raises(ExecutiveReadModelValidationError):
        ExecutiveSystemHealthReadModel(
            metadata=_metadata(ExecutiveReadScope.RISK),
            health=ExecutiveSystemHealthState.HEALTHY,
            readiness=ExecutiveReadinessState.READY,
            attention=ExecutiveAttentionLevel.INFORMATION,
            reason_codes=(),
            components=(),
        )


def test_cibo_projection_requires_structured_support_for_judgment() -> None:
    metadata = ExecutiveProjectionMetadata(
        projection_id=ExecutiveProjectionId(
            UUID("29000000-0000-0000-0000-000000000006")
        ),
        projection_version=ExecutiveProjectionVersion("executive-read.v1"),
        scope=ExecutiveReadScope.CIBO_STATE,
        source_observed_at=_NOW,
        projected_at=_NOW,
        freshness=ExecutiveSourceFreshness.FRESH,
    )

    with pytest.raises(ExecutiveReadModelValidationError):
        ExecutiveCiboReadModel(
            metadata=metadata,
            state=ExecutiveCiboOperationalState.ACTIVE,
            judgment=ExecutiveCiboJudgment.REJECT,
            confidence=ExecutiveCiboConfidenceState.CONCERNED,
            uncertainty=ExecutiveUncertaintyState.MODERATE,
            attention=ExecutiveAttentionLevel.IMPORTANT,
            authorization_state=ExecutiveCiboAuthorizationState.NOT_AUTHORIZED,
            reason_codes=("risk.correlation",),
            counter_evidence_refs=(),
            risk_factor_codes=("portfolio.correlation",),
            recommendation_code="no-action",
        )


def test_cibo_projection_exposes_evidence_not_private_reasoning() -> None:
    model = ExecutiveCiboReadModel(
        metadata=_metadata(ExecutiveReadScope.CIBO_STATE),
        state=ExecutiveCiboOperationalState.ACTIVE,
        judgment=ExecutiveCiboJudgment.REJECT,
        confidence=ExecutiveCiboConfidenceState.CONCERNED,
        uncertainty=ExecutiveUncertaintyState.MODERATE,
        attention=ExecutiveAttentionLevel.IMPORTANT,
        authorization_state=ExecutiveCiboAuthorizationState.NOT_AUTHORIZED,
        reason_codes=("regime.mismatch", "risk.correlation"),
        counter_evidence_refs=(ExecutiveEvidenceRef("evidence:cibo/counter-001"),),
        risk_factor_codes=("portfolio.correlation",),
        recommendation_code="no-action",
    )

    assert model.metadata.scope is ExecutiveReadScope.CIBO_STATE
    assert model.judgment is ExecutiveCiboJudgment.REJECT
    assert model.reason_codes == ("regime.mismatch", "risk.correlation")
    assert not hasattr(model, "chain_of_thought")
    assert not hasattr(model, "private_reasoning")
    assert not hasattr(model, "prompt")


def test_cibo_projection_rejects_same_support_and_counter_evidence() -> None:
    shared = ExecutiveEvidenceRef("evidence:executive/001")

    with pytest.raises(ExecutiveReadModelValidationError):
        ExecutiveCiboReadModel(
            metadata=_metadata(ExecutiveReadScope.CIBO_STATE),
            state=ExecutiveCiboOperationalState.ACTIVE,
            judgment=ExecutiveCiboJudgment.HOLD,
            confidence=ExecutiveCiboConfidenceState.CAUTIOUS,
            uncertainty=ExecutiveUncertaintyState.HIGH,
            attention=ExecutiveAttentionLevel.ATTENTION,
            authorization_state=ExecutiveCiboAuthorizationState.BLOCKED,
            reason_codes=("evidence.conflict",),
            counter_evidence_refs=(shared,),
            risk_factor_codes=("evidence.conflict",),
            recommendation_code="hold",
        )


def test_canonical_codes_cannot_carry_secret_material() -> None:
    with pytest.raises(ExecutiveReadModelValidationError):
        ExecutiveSystemHealthReadModel(
            metadata=_metadata(ExecutiveReadScope.SYSTEM_HEALTH),
            health=ExecutiveSystemHealthState.UNHEALTHY,
            readiness=ExecutiveReadinessState.NOT_READY,
            attention=ExecutiveAttentionLevel.CRITICAL,
            reason_codes=("token=secret",),
            components=(),
        )


def test_read_models_do_not_merge_proprietary_or_corporate_finance() -> None:
    system = ExecutiveSystemHealthReadModel(
        metadata=_metadata(ExecutiveReadScope.SYSTEM_HEALTH),
        health=ExecutiveSystemHealthState.HEALTHY,
        readiness=ExecutiveReadinessState.READY,
        attention=ExecutiveAttentionLevel.INFORMATION,
        reason_codes=(),
        components=(),
    )

    assert not hasattr(system, "balance")
    assert not hasattr(system, "client_profit_share")
    assert not hasattr(system, "settlement")
