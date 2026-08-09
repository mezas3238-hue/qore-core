from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from qore.infrastructure.client_accounts import (
    ExecutionRuntimeReference,
    ProductEntitlementReference,
    TradingAccountId,
)
from qore.infrastructure.client_trial_licensing import CommercialPaymentStanding
from qore.kernel.errors import InfrastructureError


class HostingCommercialSuspensionError(InfrastructureError):
    """Base error for Managed Hosting commercial suspension contracts."""

    __slots__ = ()


class HostingCommercialSuspensionValidationError(
    HostingCommercialSuspensionError
):
    """Violation of hosting commercial suspension invariants."""

    __slots__ = ()


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise HostingCommercialSuspensionValidationError(
            f"{field_name} must be datetime"
        )
    if value.tzinfo is None or value.utcoffset() is None:
        raise HostingCommercialSuspensionValidationError(
            f"{field_name} must be timezone-aware"
        )


@dataclass(frozen=True, slots=True)
class HostingCommercialEvidenceReference:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise HostingCommercialSuspensionValidationError(
                "hosting commercial evidence reference must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


class HostingCommercialState(StrEnum):
    ACTIVE = "active"
    SUSPEND_PENDING_FLAT = "suspend_pending_flat"
    SUSPENDED = "suspended"
    UNKNOWN = "unknown"


class HostingRuntimeCommercialDisposition(StrEnum):
    KEEP_ACTIVE = "keep_active"
    PRESERVE_POSITION_LIFECYCLE = "preserve_position_lifecycle"
    MAY_STOP_WHEN_FLAT = "may_stop_when_flat"


@dataclass(frozen=True, slots=True)
class HostingCommercialSuspensionSnapshot:
    """Commercial hosting gate; never a trading or forced-close authority."""

    account_id: TradingAccountId
    runtime_ref: ExecutionRuntimeReference
    entitlement_ref: ProductEntitlementReference
    payment_standing: CommercialPaymentStanding
    state: HostingCommercialState
    open_positions: int
    disposition: HostingRuntimeCommercialDisposition
    evaluated_at: datetime
    evidence_ref: HostingCommercialEvidenceReference

    def __post_init__(self) -> None:
        if not isinstance(self.account_id, TradingAccountId):
            raise HostingCommercialSuspensionValidationError(
                "account_id must be TradingAccountId"
            )
        if not isinstance(self.runtime_ref, ExecutionRuntimeReference):
            raise HostingCommercialSuspensionValidationError(
                "runtime_ref must be ExecutionRuntimeReference"
            )
        if not isinstance(self.entitlement_ref, ProductEntitlementReference):
            raise HostingCommercialSuspensionValidationError(
                "entitlement_ref must be ProductEntitlementReference"
            )
        if not isinstance(self.payment_standing, CommercialPaymentStanding):
            raise HostingCommercialSuspensionValidationError(
                "payment_standing must be CommercialPaymentStanding"
            )
        if not isinstance(self.state, HostingCommercialState):
            raise HostingCommercialSuspensionValidationError(
                "state must be HostingCommercialState"
            )
        if type(self.open_positions) is not int or self.open_positions < 0:
            raise HostingCommercialSuspensionValidationError(
                "open_positions must be a non-negative integer"
            )
        if not isinstance(self.disposition, HostingRuntimeCommercialDisposition):
            raise HostingCommercialSuspensionValidationError(
                "invalid hosting runtime commercial disposition"
            )
        _validate_timestamp(self.evaluated_at, field_name="commercial evaluated_at")
        if not isinstance(self.evidence_ref, HostingCommercialEvidenceReference):
            raise HostingCommercialSuspensionValidationError(
                "evidence_ref must be HostingCommercialEvidenceReference"
            )
        self._validate_derived_state()

    def _validate_derived_state(self) -> None:
        expected_state, expected_disposition = _derive_state(
            self.payment_standing,
            self.open_positions,
        )
        if self.state is not expected_state or self.disposition is not expected_disposition:
            raise HostingCommercialSuspensionValidationError(
                "commercial state/disposition must derive from payment/open positions"
            )

    @property
    def allows_new_trades(self) -> bool:
        return self.state is HostingCommercialState.ACTIVE

    @property
    def preserve_authorized_position_lifecycle(self) -> bool:
        return self.disposition is (
            HostingRuntimeCommercialDisposition.PRESERVE_POSITION_LIFECYCLE
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.account_id.logical_values(),
            self.runtime_ref.logical_values(),
            self.entitlement_ref.logical_values(),
            self.payment_standing.value,
            self.state.value,
            self.open_positions,
            self.disposition.value,
            self.evaluated_at.isoformat(),
            self.evidence_ref.logical_values(),
        )


def _derive_state(
    payment_standing: CommercialPaymentStanding,
    open_positions: int,
) -> tuple[HostingCommercialState, HostingRuntimeCommercialDisposition]:
    if payment_standing is CommercialPaymentStanding.CURRENT:
        return (
            HostingCommercialState.ACTIVE,
            HostingRuntimeCommercialDisposition.KEEP_ACTIVE,
        )
    if open_positions > 0:
        state = (
            HostingCommercialState.SUSPEND_PENDING_FLAT
            if payment_standing is CommercialPaymentStanding.PAYMENT_FAILED
            else HostingCommercialState.UNKNOWN
        )
        return (
            state,
            HostingRuntimeCommercialDisposition.PRESERVE_POSITION_LIFECYCLE,
        )
    state = (
        HostingCommercialState.SUSPENDED
        if payment_standing is CommercialPaymentStanding.PAYMENT_FAILED
        else HostingCommercialState.UNKNOWN
    )
    return state, HostingRuntimeCommercialDisposition.MAY_STOP_WHEN_FLAT


def evaluate_hosting_commercial_suspension(
    *,
    account_id: TradingAccountId,
    runtime_ref: ExecutionRuntimeReference,
    entitlement_ref: ProductEntitlementReference,
    payment_standing: CommercialPaymentStanding,
    open_positions: int,
    evaluated_at: datetime,
    evidence_ref: HostingCommercialEvidenceReference,
) -> HostingCommercialSuspensionSnapshot:
    """Evaluate hosting entitlement without closing positions or mutating Billing."""

    if type(open_positions) is not int or open_positions < 0:
        raise HostingCommercialSuspensionValidationError(
            "open_positions must be a non-negative integer"
        )
    if not isinstance(payment_standing, CommercialPaymentStanding):
        raise HostingCommercialSuspensionValidationError(
            "payment_standing must be CommercialPaymentStanding"
        )
    state, disposition = _derive_state(payment_standing, open_positions)
    return HostingCommercialSuspensionSnapshot(
        account_id=account_id,
        runtime_ref=runtime_ref,
        entitlement_ref=entitlement_ref,
        payment_standing=payment_standing,
        state=state,
        open_positions=open_positions,
        disposition=disposition,
        evaluated_at=evaluated_at,
        evidence_ref=evidence_ref,
    )
