from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from qore.infrastructure.client_accounts import ClientId
from qore.infrastructure.client_multiaccount_read_model import ClientMultiAccountReadModel
from qore.infrastructure.commercial_billing import (
    CommercialBillingEvidenceReference,
    CommercialBillingStandingState,
)
from qore.infrastructure.commercial_products import (
    CommercialBillingUnit,
    CommercialPlan,
    CommercialPlanId,
    CommercialPlanVersion,
    CommercialProductKind,
)
from qore.kernel.errors import InfrastructureError


class ClientWidgetError(InfrastructureError):
    """Base error for client multi-account Widget contracts."""

    __slots__ = ()


class ClientWidgetValidationError(ClientWidgetError):
    """Violation of a client Widget invariant."""

    __slots__ = ()


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise ClientWidgetValidationError(f"{field_name} must be datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ClientWidgetValidationError(f"{field_name} must be timezone-aware")


@dataclass(frozen=True, slots=True)
class ClientWidgetId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ClientWidgetValidationError("client widget id must be UUID")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


class ClientWidgetAccessState(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"


@dataclass(frozen=True, slots=True)
class ClientWidgetCommercialStanding:
    """Client-scoped Widget commercial standing, without payment mutation authority."""

    client_id: ClientId
    plan_id: CommercialPlanId
    plan_version: CommercialPlanVersion
    product_kind: CommercialProductKind
    billing_unit: CommercialBillingUnit
    billing_state: CommercialBillingStandingState
    evaluated_at: datetime
    evidence_ref: CommercialBillingEvidenceReference

    def __post_init__(self) -> None:
        if not isinstance(self.client_id, ClientId):
            raise ClientWidgetValidationError(
                "widget standing client_id must be ClientId"
            )
        if not isinstance(self.plan_id, CommercialPlanId):
            raise ClientWidgetValidationError(
                "widget standing plan_id must be CommercialPlanId"
            )
        if not isinstance(self.plan_version, CommercialPlanVersion):
            raise ClientWidgetValidationError(
                "widget standing plan_version must be CommercialPlanVersion"
            )
        if self.product_kind is not CommercialProductKind.CLIENT_WIDGET:
            raise ClientWidgetValidationError(
                "widget standing must bind CLIENT_WIDGET product"
            )
        if self.billing_unit is not CommercialBillingUnit.CLIENT:
            raise ClientWidgetValidationError(
                "widget standing must be CLIENT scoped"
            )
        if not isinstance(self.billing_state, CommercialBillingStandingState):
            raise ClientWidgetValidationError(
                "widget billing_state must be CommercialBillingStandingState"
            )
        _validate_timestamp(self.evaluated_at, field_name="widget standing evaluated_at")
        if not isinstance(self.evidence_ref, CommercialBillingEvidenceReference):
            raise ClientWidgetValidationError(
                "widget standing evidence_ref must be CommercialBillingEvidenceReference"
            )

    @classmethod
    def from_plan(
        cls,
        *,
        client_id: ClientId,
        plan: CommercialPlan,
        billing_state: CommercialBillingStandingState,
        evaluated_at: datetime,
        evidence_ref: CommercialBillingEvidenceReference,
    ) -> ClientWidgetCommercialStanding:
        if not isinstance(plan, CommercialPlan):
            raise ClientWidgetValidationError("CommercialPlan is required")
        return cls(
            client_id=client_id,
            plan_id=plan.plan_id,
            plan_version=plan.version,
            product_kind=plan.product.kind,
            billing_unit=plan.billing_unit,
            billing_state=billing_state,
            evaluated_at=evaluated_at,
            evidence_ref=evidence_ref,
        )

    @property
    def access_state(self) -> ClientWidgetAccessState:
        return (
            ClientWidgetAccessState.ACTIVE
            if self.billing_state is CommercialBillingStandingState.CURRENT
            else ClientWidgetAccessState.SUSPENDED
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.client_id.logical_values(),
            self.plan_id.logical_values(),
            self.plan_version.logical_values(),
            self.product_kind.value,
            self.billing_unit.value,
            self.billing_state.value,
            self.evaluated_at.isoformat(),
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class ClientWidgetViewModel:
    """One presentation-only Widget for one client and N account read snapshots."""

    widget_id: ClientWidgetId
    client_id: ClientId
    access_state: ClientWidgetAccessState
    standing: ClientWidgetCommercialStanding
    read_model: ClientMultiAccountReadModel | None
    generated_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.widget_id, ClientWidgetId):
            raise ClientWidgetValidationError(
                "widget view widget_id must be ClientWidgetId"
            )
        if not isinstance(self.client_id, ClientId):
            raise ClientWidgetValidationError("widget view client_id must be ClientId")
        if not isinstance(self.access_state, ClientWidgetAccessState):
            raise ClientWidgetValidationError(
                "widget access_state must be ClientWidgetAccessState"
            )
        if not isinstance(self.standing, ClientWidgetCommercialStanding):
            raise ClientWidgetValidationError(
                "widget standing must be ClientWidgetCommercialStanding"
            )
        if self.standing.client_id != self.client_id:
            raise ClientWidgetValidationError(
                "widget standing client does not match Widget"
            )
        _validate_timestamp(self.generated_at, field_name="widget generated_at")
        if self.generated_at < self.standing.evaluated_at:
            raise ClientWidgetValidationError(
                "widget generated_at must not predate commercial standing"
            )
        if self.access_state is not self.standing.access_state:
            raise ClientWidgetValidationError(
                "widget access_state must derive from commercial standing"
            )
        if self.access_state is ClientWidgetAccessState.ACTIVE:
            if not isinstance(self.read_model, ClientMultiAccountReadModel):
                raise ClientWidgetValidationError(
                    "ACTIVE Widget requires ClientMultiAccountReadModel"
                )
            if self.read_model.client_id != self.client_id:
                raise ClientWidgetValidationError(
                    "Widget read model client does not match Widget"
                )
            if self.read_model.generated_at > self.generated_at:
                raise ClientWidgetValidationError(
                    "Widget cannot present read model from the future"
                )
        elif self.read_model is not None:
            raise ClientWidgetValidationError(
                "SUSPENDED Widget must not expose client account read model"
            )

    @property
    def account_count(self) -> int:
        return len(self.read_model.accounts) if self.read_model is not None else 0

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.widget_id.logical_values(),
            self.client_id.logical_values(),
            self.access_state.value,
            self.standing.logical_values(),
            self.read_model.logical_values() if self.read_model else None,
            self.generated_at.isoformat(),
        )


def build_client_widget_view_model(
    *,
    widget_id: ClientWidgetId,
    standing: ClientWidgetCommercialStanding,
    read_model: ClientMultiAccountReadModel,
    generated_at: datetime,
) -> ClientWidgetViewModel:
    """Build one client Widget; suspended commercial state hides account read data."""

    if not isinstance(standing, ClientWidgetCommercialStanding):
        raise ClientWidgetValidationError(
            "ClientWidgetCommercialStanding is required"
        )
    if not isinstance(read_model, ClientMultiAccountReadModel):
        raise ClientWidgetValidationError("ClientMultiAccountReadModel is required")
    access = standing.access_state
    return ClientWidgetViewModel(
        widget_id=widget_id,
        client_id=standing.client_id,
        access_state=access,
        standing=standing,
        read_model=(read_model if access is ClientWidgetAccessState.ACTIVE else None),
        generated_at=generated_at,
    )
