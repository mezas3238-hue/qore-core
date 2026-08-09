from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from re import fullmatch
from uuid import UUID

from qore.domain.events import CorrelationId
from qore.governance.executive_client_session import (
    ExecutiveClientSessionBinding,
    ExecutiveClientSessionId,
    bind_executive_client_session,
)
from qore.governance.executive_client_surface import (
    ExecutiveClientPlatform,
    ExecutiveClientSurfaceId,
)
from qore.governance.executive_control import (
    ExecutiveAuthorityVersion,
    ExecutiveIntentId,
    ExecutivePrincipalId,
    ExecutiveReadScope,
)
from qore.governance.executive_control_plane_resilience import (
    ExecutiveControlPlaneRecoveryRequirement,
)
from qore.governance.executive_governance_ux import (
    ExecutiveGovernanceUxPhase,
    ExecutiveGovernanceUxState,
)
from qore.governance.executive_state_sync import (
    ExecutiveClientStateSnapshotId,
    ExecutiveClientStateStatus,
    ExecutiveClientStateVersion,
    ExecutiveClientStateView,
    evaluate_executive_client_state_snapshot,
)
from qore.kernel.errors import DomainError
from qore.kernel.result import Failure, Result, Success

_SENSITIVE_PARTS = (
    "authorization:",
    "bearer ",
    "client_secret",
    "credential=",
    "password=",
    "private_key",
    "secret=",
    "token=",
)


class ExecutiveMobileSecurityResilienceError(DomainError):
    """Base error for mobile client security and resilience composition."""

    __slots__ = ()


class ExecutiveMobileSecurityResilienceValidationError(
    ExecutiveMobileSecurityResilienceError
):
    """A mobile security/resilience value violates a deterministic invariant."""

    __slots__ = ()


class ExecutiveMobileSecretBoundaryStatus(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


class ExecutiveMobileConnectivityStatus(StrEnum):
    ONLINE = "online"
    OFFLINE = "offline"
    UNKNOWN = "unknown"


class ExecutiveMobileSecurityDisposition(StrEnum):
    READY = "ready"
    READ_ONLY = "read-only"
    BLOCKED = "blocked"
    RECOVERY_REQUIRED = "recovery-required"


class ExecutiveMobileSecurityReason(StrEnum):
    READY = "ready"
    SESSION_INVALID = "session-invalid"
    SECURE_BOUNDARY_UNAVAILABLE = "secure-boundary-unavailable"
    SECURE_BOUNDARY_UNKNOWN = "secure-boundary-unknown"
    COMMAND_PENDING = "command-pending"
    OUTCOME_UNKNOWN = "outcome-unknown"
    OFFLINE = "offline"
    CONNECTIVITY_UNKNOWN = "connectivity-unknown"
    GOVERNANCE_STALE = "governance-stale"
    GOVERNANCE_UNAVAILABLE = "governance-unavailable"
    GOVERNANCE_UNKNOWN = "governance-unknown"
    GOVERNANCE_REFRESH_REQUIRED = "governance-refresh-required"


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise ExecutiveMobileSecurityResilienceValidationError(
            f"{field_name} must be a datetime"
        )
    if value.tzinfo is None or value.utcoffset() is None:
        raise ExecutiveMobileSecurityResilienceValidationError(
            f"{field_name} must be timezone-aware"
        )


def _validate_boundary_ref(value: str) -> str:
    if not isinstance(value, str) or fullmatch(
        r"[a-z][a-z0-9._:/-]*",
        value,
    ) is None:
        raise ExecutiveMobileSecurityResilienceValidationError(
            "mobile secure-boundary ref must use canonical lowercase syntax"
        )
    normalized = value.lower()
    if any(part in normalized for part in _SENSITIVE_PARTS):
        raise ExecutiveMobileSecurityResilienceValidationError(
            "mobile secure-boundary ref must not contain sensitive material"
        )
    return value


@dataclass(frozen=True, slots=True)
class ExecutiveMobileSecurityAssessmentId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ExecutiveMobileSecurityResilienceValidationError(
                "mobile security assessment id must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ExecutiveMobileSecretBoundaryRef:
    """Opaque reference to an external secret-aware mechanism, never a secret."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", _validate_boundary_ref(self.value))

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class ExecutiveMobileSecretBoundaryAssertion:
    """Secret-free status emitted by an external secure-storage/auth boundary."""

    surface_id: ExecutiveClientSurfaceId
    boundary_ref: ExecutiveMobileSecretBoundaryRef
    status: ExecutiveMobileSecretBoundaryStatus
    observed_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.surface_id, ExecutiveClientSurfaceId):
            raise ExecutiveMobileSecurityResilienceValidationError(
                "mobile secret-boundary assertion requires ExecutiveClientSurfaceId"
            )
        if not isinstance(self.boundary_ref, ExecutiveMobileSecretBoundaryRef):
            raise ExecutiveMobileSecurityResilienceValidationError(
                "mobile secret-boundary assertion requires safe boundary ref"
            )
        if not isinstance(self.status, ExecutiveMobileSecretBoundaryStatus):
            raise ExecutiveMobileSecurityResilienceValidationError(
                "mobile secret-boundary assertion requires explicit status"
            )
        _validate_timestamp(self.observed_at, field_name="observed_at")

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.surface_id.logical_values(),
            self.boundary_ref.logical_values(),
            self.status.value,
            self.observed_at.isoformat(),
        )


@dataclass(frozen=True, slots=True)
class ExecutiveMobileConnectivityObservation:
    """Transport-neutral connectivity fact; it carries no network credential or endpoint."""

    surface_id: ExecutiveClientSurfaceId
    status: ExecutiveMobileConnectivityStatus
    observed_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.surface_id, ExecutiveClientSurfaceId):
            raise ExecutiveMobileSecurityResilienceValidationError(
                "mobile connectivity observation requires ExecutiveClientSurfaceId"
            )
        if not isinstance(self.status, ExecutiveMobileConnectivityStatus):
            raise ExecutiveMobileSecurityResilienceValidationError(
                "mobile connectivity observation requires explicit status"
            )
        _validate_timestamp(self.observed_at, field_name="observed_at")

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.surface_id.logical_values(),
            self.status.value,
            self.observed_at.isoformat(),
        )


@dataclass(frozen=True, slots=True)
class ExecutiveMobileGovernanceStateEvidence:
    """Minimal state-freshness evidence derived from the canonical state-sync contract."""

    status: ExecutiveClientStateStatus
    observed_at: datetime
    snapshot_id: ExecutiveClientStateSnapshotId | None = None
    state_version: ExecutiveClientStateVersion | None = None
    source_received_at: datetime | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.status, ExecutiveClientStateStatus):
            raise ExecutiveMobileSecurityResilienceValidationError(
                "mobile governance evidence requires ExecutiveClientStateStatus"
            )
        _validate_timestamp(self.observed_at, field_name="observed_at")
        has_snapshot = self.status in (
            ExecutiveClientStateStatus.CURRENT,
            ExecutiveClientStateStatus.STALE,
        )
        if has_snapshot:
            if not isinstance(self.snapshot_id, ExecutiveClientStateSnapshotId):
                raise ExecutiveMobileSecurityResilienceValidationError(
                    "current/stale mobile governance evidence requires snapshot id"
                )
            if not isinstance(self.state_version, ExecutiveClientStateVersion):
                raise ExecutiveMobileSecurityResilienceValidationError(
                    "current/stale mobile governance evidence requires state version"
                )
            if self.source_received_at is None:
                raise ExecutiveMobileSecurityResilienceValidationError(
                    "current/stale mobile governance evidence requires source receipt time"
                )
            _validate_timestamp(self.source_received_at, field_name="source_received_at")
            if self.observed_at < self.source_received_at:
                raise ExecutiveMobileSecurityResilienceValidationError(
                    "mobile governance observation cannot predate source receipt"
                )
        elif (
            self.snapshot_id is not None
            or self.state_version is not None
            or self.source_received_at is not None
        ):
            raise ExecutiveMobileSecurityResilienceValidationError(
                "unavailable/unknown mobile governance evidence must not fabricate snapshot"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.status.value,
            self.observed_at.isoformat(),
            None if self.snapshot_id is None else self.snapshot_id.logical_values(),
            None if self.state_version is None else self.state_version.logical_values(),
            None if self.source_received_at is None else self.source_received_at.isoformat(),
        )


@dataclass(frozen=True, slots=True)
class ExecutiveMobileGovernanceActivity:
    """Secret-free summary of a governance UX lifecycle relevant to mobile containment."""

    phase: ExecutiveGovernanceUxPhase
    intent_id: ExecutiveIntentId
    principal_id: ExecutivePrincipalId
    authority_version: ExecutiveAuthorityVersion
    correlation_id: CorrelationId
    observed_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.phase, ExecutiveGovernanceUxPhase):
            raise ExecutiveMobileSecurityResilienceValidationError(
                "mobile governance activity requires ExecutiveGovernanceUxPhase"
            )
        if not isinstance(self.intent_id, ExecutiveIntentId):
            raise ExecutiveMobileSecurityResilienceValidationError(
                "mobile governance activity requires ExecutiveIntentId"
            )
        if not isinstance(self.principal_id, ExecutivePrincipalId):
            raise ExecutiveMobileSecurityResilienceValidationError(
                "mobile governance activity requires ExecutivePrincipalId"
            )
        if not isinstance(self.authority_version, ExecutiveAuthorityVersion):
            raise ExecutiveMobileSecurityResilienceValidationError(
                "mobile governance activity requires ExecutiveAuthorityVersion"
            )
        if not isinstance(self.correlation_id, CorrelationId):
            raise ExecutiveMobileSecurityResilienceValidationError(
                "mobile governance activity requires CorrelationId"
            )
        _validate_timestamp(self.observed_at, field_name="observed_at")

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.phase.value,
            self.intent_id.logical_values(),
            self.principal_id.logical_values(),
            self.authority_version.logical_values(),
            str(self.correlation_id.value),
            self.observed_at.isoformat(),
        )


def _expected_disposition(
    reason: ExecutiveMobileSecurityReason,
) -> ExecutiveMobileSecurityDisposition:
    if reason is ExecutiveMobileSecurityReason.READY:
        return ExecutiveMobileSecurityDisposition.READY
    if reason is ExecutiveMobileSecurityReason.OUTCOME_UNKNOWN:
        return ExecutiveMobileSecurityDisposition.RECOVERY_REQUIRED
    if reason in (
        ExecutiveMobileSecurityReason.OFFLINE,
        ExecutiveMobileSecurityReason.CONNECTIVITY_UNKNOWN,
        ExecutiveMobileSecurityReason.GOVERNANCE_STALE,
        ExecutiveMobileSecurityReason.GOVERNANCE_UNAVAILABLE,
        ExecutiveMobileSecurityReason.GOVERNANCE_UNKNOWN,
        ExecutiveMobileSecurityReason.GOVERNANCE_REFRESH_REQUIRED,
    ):
        return ExecutiveMobileSecurityDisposition.READ_ONLY
    return ExecutiveMobileSecurityDisposition.BLOCKED


@dataclass(frozen=True, slots=True)
class ExecutiveMobileSecurityAssessment:
    """Fail-closed mobile readiness result; presentation eligibility is not authority."""

    assessment_id: ExecutiveMobileSecurityAssessmentId
    surface_id: ExecutiveClientSurfaceId
    platform: ExecutiveClientPlatform
    session_id: ExecutiveClientSessionId
    principal_id: ExecutivePrincipalId
    session_current: bool
    secret_boundary: ExecutiveMobileSecretBoundaryAssertion
    connectivity: ExecutiveMobileConnectivityObservation
    governance_state: ExecutiveMobileGovernanceStateEvidence
    assessed_at: datetime
    disposition: ExecutiveMobileSecurityDisposition
    reason: ExecutiveMobileSecurityReason
    governance_activity: ExecutiveMobileGovernanceActivity | None = None
    recovery_requirement: ExecutiveControlPlaneRecoveryRequirement | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.assessment_id, ExecutiveMobileSecurityAssessmentId):
            raise ExecutiveMobileSecurityResilienceValidationError(
                "mobile assessment requires ExecutiveMobileSecurityAssessmentId"
            )
        if not isinstance(self.surface_id, ExecutiveClientSurfaceId):
            raise ExecutiveMobileSecurityResilienceValidationError(
                "mobile assessment requires ExecutiveClientSurfaceId"
            )
        if self.platform not in (
            ExecutiveClientPlatform.IOS,
            ExecutiveClientPlatform.ANDROID,
        ):
            raise ExecutiveMobileSecurityResilienceValidationError(
                "mobile assessment requires IOS or ANDROID platform"
            )
        if not isinstance(self.session_id, ExecutiveClientSessionId):
            raise ExecutiveMobileSecurityResilienceValidationError(
                "mobile assessment requires ExecutiveClientSessionId"
            )
        if not isinstance(self.principal_id, ExecutivePrincipalId):
            raise ExecutiveMobileSecurityResilienceValidationError(
                "mobile assessment requires ExecutivePrincipalId"
            )
        if not isinstance(self.session_current, bool):
            raise ExecutiveMobileSecurityResilienceValidationError(
                "mobile assessment session_current must be bool"
            )
        if not isinstance(self.secret_boundary, ExecutiveMobileSecretBoundaryAssertion):
            raise ExecutiveMobileSecurityResilienceValidationError(
                "mobile assessment requires secret-boundary assertion"
            )
        if not isinstance(self.connectivity, ExecutiveMobileConnectivityObservation):
            raise ExecutiveMobileSecurityResilienceValidationError(
                "mobile assessment requires connectivity observation"
            )
        if not isinstance(self.governance_state, ExecutiveMobileGovernanceStateEvidence):
            raise ExecutiveMobileSecurityResilienceValidationError(
                "mobile assessment requires governance-state evidence"
            )
        _validate_timestamp(self.assessed_at, field_name="assessed_at")
        if self.secret_boundary.surface_id != self.surface_id:
            raise ExecutiveMobileSecurityResilienceValidationError(
                "mobile secret boundary must match assessment surface"
            )
        if self.connectivity.surface_id != self.surface_id:
            raise ExecutiveMobileSecurityResilienceValidationError(
                "mobile connectivity must match assessment surface"
            )
        for field_name, observed_at in (
            ("secret boundary", self.secret_boundary.observed_at),
            ("connectivity", self.connectivity.observed_at),
            ("governance state", self.governance_state.observed_at),
        ):
            if self.assessed_at < observed_at:
                raise ExecutiveMobileSecurityResilienceValidationError(
                    f"mobile assessment cannot predate {field_name} observation"
                )
        if self.governance_activity is not None:
            if not isinstance(self.governance_activity, ExecutiveMobileGovernanceActivity):
                raise ExecutiveMobileSecurityResilienceValidationError(
                    "mobile governance activity has invalid type"
                )
            if self.governance_activity.principal_id != self.principal_id:
                raise ExecutiveMobileSecurityResilienceValidationError(
                    "mobile governance activity principal must match assessment"
                )
            if self.assessed_at < self.governance_activity.observed_at:
                raise ExecutiveMobileSecurityResilienceValidationError(
                    "mobile assessment cannot predate governance activity"
                )
        if not isinstance(self.disposition, ExecutiveMobileSecurityDisposition):
            raise ExecutiveMobileSecurityResilienceValidationError(
                "mobile assessment requires explicit disposition"
            )
        if not isinstance(self.reason, ExecutiveMobileSecurityReason):
            raise ExecutiveMobileSecurityResilienceValidationError(
                "mobile assessment requires explicit reason"
            )
        if self.disposition is not _expected_disposition(self.reason):
            raise ExecutiveMobileSecurityResilienceValidationError(
                "mobile assessment disposition must match canonical reason"
            )
        if self.reason is ExecutiveMobileSecurityReason.OUTCOME_UNKNOWN:
            if (
                self.recovery_requirement
                is not ExecutiveControlPlaneRecoveryRequirement.VERIFY_CONTROL_RECEIPT
            ):
                raise ExecutiveMobileSecurityResilienceValidationError(
                    "unknown mobile outcome requires control-receipt verification"
                )
        elif self.recovery_requirement is not None:
            raise ExecutiveMobileSecurityResilienceValidationError(
                "mobile recovery requirement is reserved for ambiguous outcome"
            )

    @property
    def read_request_eligible(self) -> bool:
        return (
            self.session_current
            and self.secret_boundary.status is ExecutiveMobileSecretBoundaryStatus.AVAILABLE
            and self.connectivity.status is ExecutiveMobileConnectivityStatus.ONLINE
        )

    @property
    def control_request_eligible(self) -> bool:
        return self.disposition is ExecutiveMobileSecurityDisposition.READY

    @property
    def automatic_retry_allowed(self) -> bool:
        return False

    @property
    def automatic_redispatch_allowed(self) -> bool:
        return False

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.assessment_id.logical_values(),
            self.surface_id.logical_values(),
            self.platform.value,
            self.session_id.logical_values(),
            self.principal_id.logical_values(),
            self.session_current,
            self.secret_boundary.logical_values(),
            self.connectivity.logical_values(),
            self.governance_state.logical_values(),
            self.assessed_at.isoformat(),
            self.disposition.value,
            self.reason.value,
            None
            if self.governance_activity is None
            else self.governance_activity.logical_values(),
            None
            if self.recovery_requirement is None
            else self.recovery_requirement.value,
            self.read_request_eligible,
            self.control_request_eligible,
            self.automatic_retry_allowed,
            self.automatic_redispatch_allowed,
        )


def _evaluate_governance_state(
    state_view: ExecutiveClientStateView,
    *,
    assessed_at: datetime,
) -> ExecutiveClientStateView:
    if state_view.scope is not ExecutiveReadScope.GOVERNANCE:
        raise ExecutiveMobileSecurityResilienceValidationError(
            "mobile command readiness requires GOVERNANCE client state"
        )
    if assessed_at < state_view.observed_at:
        raise ExecutiveMobileSecurityResilienceValidationError(
            "mobile assessment cannot predate client state observation"
        )
    if state_view.snapshot is None:
        return ExecutiveClientStateView(
            status=state_view.status,
            scope=state_view.scope,
            observed_at=assessed_at,
            reason_code=state_view.reason_code,
            snapshot=None,
        )
    state_result = evaluate_executive_client_state_snapshot(
        state_view.snapshot,
        evaluated_at=assessed_at,
    )
    if isinstance(state_result, Failure):
        raise ExecutiveMobileSecurityResilienceValidationError(
            "mobile governance state could not be re-evaluated"
        )
    return state_result.value


def _governance_state_evidence(
    state_view: ExecutiveClientStateView,
) -> ExecutiveMobileGovernanceStateEvidence:
    if state_view.snapshot is None:
        return ExecutiveMobileGovernanceStateEvidence(
            status=state_view.status,
            observed_at=state_view.observed_at,
        )
    return ExecutiveMobileGovernanceStateEvidence(
        status=state_view.status,
        observed_at=state_view.observed_at,
        snapshot_id=state_view.snapshot.snapshot_id,
        state_version=state_view.snapshot.version,
        source_received_at=state_view.snapshot.received_at,
    )


def _governance_activity(
    governance_ux: ExecutiveGovernanceUxState | None,
) -> ExecutiveMobileGovernanceActivity | None:
    if governance_ux is None:
        return None
    authorized = governance_ux.authorized
    return ExecutiveMobileGovernanceActivity(
        phase=governance_ux.phase,
        intent_id=authorized.intent.intent_id,
        principal_id=authorized.intent.principal_id,
        authority_version=authorized.grant.authority_version,
        correlation_id=authorized.intent.correlation_id,
        observed_at=governance_ux.observed_at,
    )


def _derive_reason(
    *,
    session_current: bool,
    secret_boundary: ExecutiveMobileSecretBoundaryAssertion,
    connectivity: ExecutiveMobileConnectivityObservation,
    governance_state: ExecutiveMobileGovernanceStateEvidence,
    governance_activity: ExecutiveMobileGovernanceActivity | None,
) -> tuple[ExecutiveMobileSecurityReason, ExecutiveControlPlaneRecoveryRequirement | None]:
    if not session_current:
        return ExecutiveMobileSecurityReason.SESSION_INVALID, None
    if secret_boundary.status is ExecutiveMobileSecretBoundaryStatus.UNAVAILABLE:
        return ExecutiveMobileSecurityReason.SECURE_BOUNDARY_UNAVAILABLE, None
    if secret_boundary.status is ExecutiveMobileSecretBoundaryStatus.UNKNOWN:
        return ExecutiveMobileSecurityReason.SECURE_BOUNDARY_UNKNOWN, None
    if governance_activity is not None:
        if governance_activity.phase is ExecutiveGovernanceUxPhase.OUTCOME_UNKNOWN:
            return (
                ExecutiveMobileSecurityReason.OUTCOME_UNKNOWN,
                ExecutiveControlPlaneRecoveryRequirement.VERIFY_CONTROL_RECEIPT,
            )
        if governance_activity.phase is ExecutiveGovernanceUxPhase.PENDING:
            return ExecutiveMobileSecurityReason.COMMAND_PENDING, None
    if connectivity.status is ExecutiveMobileConnectivityStatus.OFFLINE:
        return ExecutiveMobileSecurityReason.OFFLINE, None
    if connectivity.status is ExecutiveMobileConnectivityStatus.UNKNOWN:
        return ExecutiveMobileSecurityReason.CONNECTIVITY_UNKNOWN, None
    if governance_state.status is ExecutiveClientStateStatus.STALE:
        return ExecutiveMobileSecurityReason.GOVERNANCE_STALE, None
    if governance_state.status is ExecutiveClientStateStatus.UNAVAILABLE:
        return ExecutiveMobileSecurityReason.GOVERNANCE_UNAVAILABLE, None
    if governance_state.status is ExecutiveClientStateStatus.UNKNOWN:
        return ExecutiveMobileSecurityReason.GOVERNANCE_UNKNOWN, None
    if (
        governance_activity is not None
        and governance_state.source_received_at is not None
        and governance_state.source_received_at < governance_activity.observed_at
        and governance_activity.phase
        not in (
            ExecutiveGovernanceUxPhase.PENDING,
            ExecutiveGovernanceUxPhase.OUTCOME_UNKNOWN,
        )
    ):
        return ExecutiveMobileSecurityReason.GOVERNANCE_REFRESH_REQUIRED, None
    return ExecutiveMobileSecurityReason.READY, None


def assess_executive_mobile_security(
    *,
    assessment_id: ExecutiveMobileSecurityAssessmentId,
    session_binding: ExecutiveClientSessionBinding,
    secret_boundary: ExecutiveMobileSecretBoundaryAssertion,
    connectivity: ExecutiveMobileConnectivityObservation,
    governance_state: ExecutiveClientStateView,
    assessed_at: datetime,
    governance_ux: ExecutiveGovernanceUxState | None = None,
) -> Result[ExecutiveMobileSecurityAssessment, ExecutiveMobileSecurityResilienceError]:
    """Re-evaluate mobile safety without granting executive or trading authority."""

    if not isinstance(session_binding, ExecutiveClientSessionBinding):
        return Failure(
            ExecutiveMobileSecurityResilienceValidationError(
                "mobile assessment requires ExecutiveClientSessionBinding"
            )
        )
    if not isinstance(secret_boundary, ExecutiveMobileSecretBoundaryAssertion):
        return Failure(
            ExecutiveMobileSecurityResilienceValidationError(
                "mobile assessment requires secret-boundary assertion"
            )
        )
    if not isinstance(connectivity, ExecutiveMobileConnectivityObservation):
        return Failure(
            ExecutiveMobileSecurityResilienceValidationError(
                "mobile assessment requires connectivity observation"
            )
        )
    if not isinstance(governance_state, ExecutiveClientStateView):
        return Failure(
            ExecutiveMobileSecurityResilienceValidationError(
                "mobile assessment requires ExecutiveClientStateView"
            )
        )
    if governance_ux is not None and not isinstance(governance_ux, ExecutiveGovernanceUxState):
        return Failure(
            ExecutiveMobileSecurityResilienceValidationError(
                "mobile assessment governance_ux has invalid type"
            )
        )
    try:
        _validate_timestamp(assessed_at, field_name="assessed_at")
        surface = session_binding.surface
        if surface.platform not in (
            ExecutiveClientPlatform.IOS,
            ExecutiveClientPlatform.ANDROID,
        ):
            raise ExecutiveMobileSecurityResilienceValidationError(
                "mobile assessment accepts only IOS or ANDROID client surface"
            )
        if secret_boundary.surface_id != surface.surface_id:
            raise ExecutiveMobileSecurityResilienceValidationError(
                "mobile secret boundary must match session surface"
            )
        if connectivity.surface_id != surface.surface_id:
            raise ExecutiveMobileSecurityResilienceValidationError(
                "mobile connectivity must match session surface"
            )
        if assessed_at < secret_boundary.observed_at:
            raise ExecutiveMobileSecurityResilienceValidationError(
                "mobile assessment cannot predate secret-boundary observation"
            )
        if assessed_at < connectivity.observed_at:
            raise ExecutiveMobileSecurityResilienceValidationError(
                "mobile assessment cannot predate connectivity observation"
            )
        if governance_ux is not None:
            if governance_ux.surface_id != surface.surface_id:
                raise ExecutiveMobileSecurityResilienceValidationError(
                    "mobile governance UX must match session surface"
                )
            if governance_ux.authorized.intent.principal_id != session_binding.session.principal_id:
                raise ExecutiveMobileSecurityResilienceValidationError(
                    "mobile governance UX principal must match client session"
                )
            if assessed_at < governance_ux.observed_at:
                raise ExecutiveMobileSecurityResilienceValidationError(
                    "mobile assessment cannot predate governance UX observation"
                )

        evaluated_state = _evaluate_governance_state(
            governance_state,
            assessed_at=assessed_at,
        )
        state_evidence = _governance_state_evidence(evaluated_state)
        activity = _governance_activity(governance_ux)
        refreshed_session = bind_executive_client_session(
            session_binding.session,
            session_binding.surface,
            session_binding.authenticated_principal,
            evaluated_at=assessed_at,
        )
        session_current = isinstance(refreshed_session, Success)
        reason, recovery_requirement = _derive_reason(
            session_current=session_current,
            secret_boundary=secret_boundary,
            connectivity=connectivity,
            governance_state=state_evidence,
            governance_activity=activity,
        )
        return Success(
            ExecutiveMobileSecurityAssessment(
                assessment_id=assessment_id,
                surface_id=surface.surface_id,
                platform=surface.platform,
                session_id=session_binding.session.session_id,
                principal_id=session_binding.session.principal_id,
                session_current=session_current,
                secret_boundary=secret_boundary,
                connectivity=connectivity,
                governance_state=state_evidence,
                assessed_at=assessed_at,
                disposition=_expected_disposition(reason),
                reason=reason,
                governance_activity=activity,
                recovery_requirement=recovery_requirement,
            )
        )
    except ExecutiveMobileSecurityResilienceError as error:
        return Failure(error)
