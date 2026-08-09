from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from enum import StrEnum
from uuid import UUID

from qore.functional.decisions import DecisionId
from qore.infrastructure.client_accounts import (
    ProductEntitlementReference,
    TradingAccountId,
)
from qore.infrastructure.client_execution_agent import (
    ClientAgentEntitlementSnapshot,
    ClientAgentEntitlementState,
)
from qore.infrastructure.execution_boundary import ExecutionReceiptId
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success

_TRIAL_DURATION = timedelta(days=14)


class ClientTrialLicensingError(InfrastructureError):
    """Base error for account-scoped trial/licensing contracts."""

    __slots__ = ()


class ClientTrialLicensingValidationError(ClientTrialLicensingError):
    """Violation of a trial/licensing invariant."""

    __slots__ = ()


class ClientTrialLicensingConflictError(ClientTrialLicensingError):
    """A requested licensing transition conflicts with immutable state."""

    __slots__ = ()


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise ClientTrialLicensingValidationError(f"{field_name} must be datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ClientTrialLicensingValidationError(
            f"{field_name} must be timezone-aware"
        )


def _validate_uuid(value: UUID, *, field_name: str) -> None:
    if not isinstance(value, UUID):
        raise ClientTrialLicensingValidationError(f"{field_name} must be UUID")


@dataclass(frozen=True, slots=True)
class TrialEvidenceReference:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="trial evidence reference")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class LicensingEvidenceReference:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="licensing evidence reference")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


class TrialExecutionEligibility(StrEnum):
    ELIGIBLE_LIVE = "eligible_live"
    NOT_ELIGIBLE = "not_eligible"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class FirstEligibleLiveExecutionEvidence:
    """Evidence that can start a trial; it does not itself authorize execution."""

    account_id: TradingAccountId
    entitlement_ref: ProductEntitlementReference
    decision_id: DecisionId
    execution_receipt_id: ExecutionReceiptId
    eligibility: TrialExecutionEligibility
    executed_at: datetime
    evidence_ref: TrialEvidenceReference

    def __post_init__(self) -> None:
        if not isinstance(self.account_id, TradingAccountId):
            raise ClientTrialLicensingValidationError(
                "trial execution account_id must be TradingAccountId"
            )
        if not isinstance(self.entitlement_ref, ProductEntitlementReference):
            raise ClientTrialLicensingValidationError(
                "trial execution entitlement_ref must be ProductEntitlementReference"
            )
        if not isinstance(self.decision_id, DecisionId) or not isinstance(
            self.decision_id.value, UUID
        ):
            raise ClientTrialLicensingValidationError(
                "trial execution decision_id must be UUID-backed DecisionId"
            )
        if not isinstance(self.execution_receipt_id, ExecutionReceiptId):
            raise ClientTrialLicensingValidationError(
                "trial execution receipt must be ExecutionReceiptId"
            )
        if not isinstance(self.eligibility, TrialExecutionEligibility):
            raise ClientTrialLicensingValidationError(
                "trial execution eligibility must be TrialExecutionEligibility"
            )
        _validate_timestamp(self.executed_at, field_name="trial executed_at")
        if not isinstance(self.evidence_ref, TrialEvidenceReference):
            raise ClientTrialLicensingValidationError(
                "trial execution evidence_ref must be TrialEvidenceReference"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.account_id.logical_values(),
            self.entitlement_ref.logical_values(),
            str(self.decision_id.value),
            self.execution_receipt_id.logical_values(),
            self.eligibility.value,
            self.executed_at.isoformat(),
            self.evidence_ref.logical_values(),
        )


class ClientTrialState(StrEnum):
    NOT_STARTED = "not_started"
    ACTIVE = "active"
    EXPIRED = "expired"


class ClientLicenseState(StrEnum):
    TRIAL_PENDING = "trial_pending"
    TRIAL_ACTIVE = "trial_active"
    LICENSED = "licensed"
    SUSPEND_PENDING_FLAT = "suspend_pending_flat"
    SUSPENDED = "suspended"
    UNKNOWN = "unknown"


class CommercialPaymentStanding(StrEnum):
    CURRENT = "current"
    PAYMENT_FAILED = "payment_failed"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ClientAgentLicenseSnapshot:
    """Account-scoped commercial entitlement state, independent of runtime host."""

    account_id: TradingAccountId
    entitlement_ref: ProductEntitlementReference
    trial_state: ClientTrialState
    license_state: ClientLicenseState
    trial_started_at: datetime | None
    trial_expires_at: datetime | None
    first_live_evidence_ref: TrialEvidenceReference | None
    updated_at: datetime
    evidence_ref: LicensingEvidenceReference

    def __post_init__(self) -> None:
        if not isinstance(self.account_id, TradingAccountId):
            raise ClientTrialLicensingValidationError(
                "license account_id must be TradingAccountId"
            )
        if not isinstance(self.entitlement_ref, ProductEntitlementReference):
            raise ClientTrialLicensingValidationError(
                "license entitlement_ref must be ProductEntitlementReference"
            )
        if not isinstance(self.trial_state, ClientTrialState):
            raise ClientTrialLicensingValidationError(
                "license trial_state must be ClientTrialState"
            )
        if not isinstance(self.license_state, ClientLicenseState):
            raise ClientTrialLicensingValidationError(
                "license state must be ClientLicenseState"
            )
        _validate_timestamp(self.updated_at, field_name="license updated_at")
        if not isinstance(self.evidence_ref, LicensingEvidenceReference):
            raise ClientTrialLicensingValidationError(
                "license evidence_ref must be LicensingEvidenceReference"
            )
        self._validate_trial_fields()

    def _validate_trial_fields(self) -> None:
        if self.trial_state is ClientTrialState.NOT_STARTED:
            if any(
                value is not None
                for value in (
                    self.trial_started_at,
                    self.trial_expires_at,
                    self.first_live_evidence_ref,
                )
            ):
                raise ClientTrialLicensingValidationError(
                    "NOT_STARTED trial must not contain trial timestamps/evidence"
                )
            return
        if self.trial_started_at is None or self.trial_expires_at is None:
            raise ClientTrialLicensingValidationError(
                "started trial requires start and expiry timestamps"
            )
        _validate_timestamp(self.trial_started_at, field_name="trial_started_at")
        _validate_timestamp(self.trial_expires_at, field_name="trial_expires_at")
        if self.trial_expires_at - self.trial_started_at != _TRIAL_DURATION:
            raise ClientTrialLicensingValidationError(
                "trial duration must be exactly 14 days"
            )
        if not isinstance(self.first_live_evidence_ref, TrialEvidenceReference):
            raise ClientTrialLicensingValidationError(
                "started trial requires immutable first live evidence"
            )
        if self.updated_at < self.trial_started_at:
            raise ClientTrialLicensingValidationError(
                "license update must not predate trial start"
            )

    @property
    def allows_new_trades(self) -> bool:
        return self.license_state in (
            ClientLicenseState.TRIAL_ACTIVE,
            ClientLicenseState.LICENSED,
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.account_id.logical_values(),
            self.entitlement_ref.logical_values(),
            self.trial_state.value,
            self.license_state.value,
            self.trial_started_at.isoformat() if self.trial_started_at else None,
            self.trial_expires_at.isoformat() if self.trial_expires_at else None,
            (
                self.first_live_evidence_ref.logical_values()
                if self.first_live_evidence_ref is not None
                else None
            ),
            self.updated_at.isoformat(),
            self.evidence_ref.logical_values(),
        )


def start_client_trial(
    snapshot: ClientAgentLicenseSnapshot,
    execution: FirstEligibleLiveExecutionEvidence,
    *,
    evidence_ref: LicensingEvidenceReference,
) -> Result[ClientAgentLicenseSnapshot, ClientTrialLicensingError]:
    """Start the immutable 14-day trial from first eligible live execution only."""

    if not isinstance(snapshot, ClientAgentLicenseSnapshot):
        return Failure(ClientTrialLicensingValidationError("license snapshot is required"))
    if not isinstance(execution, FirstEligibleLiveExecutionEvidence):
        return Failure(
            ClientTrialLicensingValidationError(
                "first eligible live execution evidence is required"
            )
        )
    if snapshot.trial_state is not ClientTrialState.NOT_STARTED:
        return Failure(
            ClientTrialLicensingConflictError("trial has already been started")
        )
    if (
        execution.account_id != snapshot.account_id
        or execution.entitlement_ref != snapshot.entitlement_ref
    ):
        return Failure(
            ClientTrialLicensingValidationError(
                "trial execution account/entitlement binding mismatch"
            )
        )
    if execution.eligibility is not TrialExecutionEligibility.ELIGIBLE_LIVE:
        return Failure(
            ClientTrialLicensingValidationError(
                "trial requires first ELIGIBLE_LIVE execution evidence"
            )
        )
    try:
        return Success(
            replace(
                snapshot,
                trial_state=ClientTrialState.ACTIVE,
                license_state=ClientLicenseState.TRIAL_ACTIVE,
                trial_started_at=execution.executed_at,
                trial_expires_at=execution.executed_at + _TRIAL_DURATION,
                first_live_evidence_ref=execution.evidence_ref,
                updated_at=execution.executed_at,
                evidence_ref=evidence_ref,
            )
        )
    except ClientTrialLicensingError as error:
        return Failure(error)


def evaluate_client_license(
    snapshot: ClientAgentLicenseSnapshot,
    *,
    payment_standing: CommercialPaymentStanding,
    open_positions: int,
    evaluated_at: datetime,
    evidence_ref: LicensingEvidenceReference,
) -> Result[ClientAgentLicenseSnapshot, ClientTrialLicensingError]:
    """Evaluate entry entitlement while preserving authorized open-position lifecycle."""

    if not isinstance(snapshot, ClientAgentLicenseSnapshot):
        return Failure(ClientTrialLicensingValidationError("license snapshot is required"))
    if not isinstance(payment_standing, CommercialPaymentStanding):
        return Failure(
            ClientTrialLicensingValidationError(
                "payment standing must be CommercialPaymentStanding"
            )
        )
    if type(open_positions) is not int or open_positions < 0:
        return Failure(
            ClientTrialLicensingValidationError(
                "open_positions must be a non-negative integer"
            )
        )
    try:
        _validate_timestamp(evaluated_at, field_name="license evaluated_at")
        if evaluated_at < snapshot.updated_at:
            raise ClientTrialLicensingValidationError(
                "license evaluation must not predate current snapshot"
            )
        trial_state = snapshot.trial_state
        license_state = snapshot.license_state
        if (
            trial_state is ClientTrialState.ACTIVE
            and snapshot.trial_expires_at is not None
            and evaluated_at >= snapshot.trial_expires_at
        ):
            trial_state = ClientTrialState.EXPIRED
            license_state = (
                ClientLicenseState.SUSPEND_PENDING_FLAT
                if open_positions > 0
                else ClientLicenseState.SUSPENDED
            )
        if payment_standing is CommercialPaymentStanding.PAYMENT_FAILED:
            license_state = (
                ClientLicenseState.SUSPEND_PENDING_FLAT
                if open_positions > 0
                else ClientLicenseState.SUSPENDED
            )
        elif payment_standing is CommercialPaymentStanding.UNKNOWN:
            license_state = (
                ClientLicenseState.SUSPEND_PENDING_FLAT
                if open_positions > 0
                else ClientLicenseState.SUSPENDED
            )
        elif license_state is ClientLicenseState.SUSPEND_PENDING_FLAT and open_positions == 0:
            license_state = ClientLicenseState.SUSPENDED
        return Success(
            replace(
                snapshot,
                trial_state=trial_state,
                license_state=license_state,
                updated_at=evaluated_at,
                evidence_ref=evidence_ref,
            )
        )
    except ClientTrialLicensingError as error:
        return Failure(error)


def activate_paid_license(
    snapshot: ClientAgentLicenseSnapshot,
    *,
    activated_at: datetime,
    evidence_ref: LicensingEvidenceReference,
) -> Result[ClientAgentLicenseSnapshot, ClientTrialLicensingError]:
    """Activate a paid commercial entitlement; payment verification occurs elsewhere."""

    if not isinstance(snapshot, ClientAgentLicenseSnapshot):
        return Failure(ClientTrialLicensingValidationError("license snapshot is required"))
    try:
        _validate_timestamp(activated_at, field_name="license activated_at")
        if activated_at < snapshot.updated_at:
            raise ClientTrialLicensingValidationError(
                "license activation must not predate current snapshot"
            )
        return Success(
            replace(
                snapshot,
                license_state=ClientLicenseState.LICENSED,
                updated_at=activated_at,
                evidence_ref=evidence_ref,
            )
        )
    except ClientTrialLicensingError as error:
        return Failure(error)


def project_agent_entitlement(
    snapshot: ClientAgentLicenseSnapshot,
    *,
    evaluated_at: datetime,
) -> ClientAgentEntitlementSnapshot:
    """Project commercial state into the existing execution-agent entitlement input."""

    _validate_timestamp(evaluated_at, field_name="entitlement projected_at")
    state = (
        ClientAgentEntitlementState.ENABLED
        if snapshot.allows_new_trades
        else ClientAgentEntitlementState.BLOCKED
    )
    return ClientAgentEntitlementSnapshot(
        entitlement_ref=snapshot.entitlement_ref,
        account_id=snapshot.account_id,
        state=state,
        evaluated_at=evaluated_at,
    )
