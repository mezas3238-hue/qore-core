from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from qore.infrastructure.proprietary_accounts import MoneyAmount
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success


class CommercialProductError(InfrastructureError):
    """Base error for QORE commercial product contracts."""

    __slots__ = ()


class CommercialProductValidationError(CommercialProductError):
    """Violation of a product/plan invariant."""

    __slots__ = ()


def _validate_uuid(value: UUID, *, field_name: str) -> None:
    if not isinstance(value, UUID):
        raise CommercialProductValidationError(f"{field_name} must be UUID")


@dataclass(frozen=True, slots=True)
class CommercialProductId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="commercial product id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class CommercialPlanId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="commercial plan id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class CommercialPlanVersion:
    value: int

    def __post_init__(self) -> None:
        if type(self.value) is not int or self.value <= 0:
            raise CommercialProductValidationError(
                "commercial plan version must be a positive integer"
            )

    def logical_values(self) -> tuple[int, ...]:
        return (self.value,)


class CommercialProductKind(StrEnum):
    CLIENT_EXECUTION_AGENT = "client_execution_agent"
    CLIENT_WIDGET = "client_widget"
    CORE_SERVICES = "core_services"
    MANAGED_HOSTING = "managed_hosting"
    MANAGED_FUTURES = "managed_futures"


class CommercialProductAvailability(StrEnum):
    CONFIRMED = "confirmed"
    VALIDATION_REQUIRED = "validation_required"


class CommercialBillingUnit(StrEnum):
    ACCOUNT = "account"
    CLIENT = "client"
    SERVICE = "service"


class CommercialBillingCadence(StrEnum):
    MONTHLY = "monthly"


@dataclass(frozen=True, slots=True)
class CommercialProduct:
    product_id: CommercialProductId
    kind: CommercialProductKind
    availability: CommercialProductAvailability

    def __post_init__(self) -> None:
        if not isinstance(self.product_id, CommercialProductId):
            raise CommercialProductValidationError(
                "product_id must be CommercialProductId"
            )
        if not isinstance(self.kind, CommercialProductKind):
            raise CommercialProductValidationError(
                "product kind must be CommercialProductKind"
            )
        if not isinstance(self.availability, CommercialProductAvailability):
            raise CommercialProductValidationError(
                "product availability must be CommercialProductAvailability"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.product_id.logical_values(),
            self.kind.value,
            self.availability.value,
        )


@dataclass(frozen=True, slots=True)
class CommercialPlan:
    """Versioned pricing contract for one independently billable product."""

    plan_id: CommercialPlanId
    version: CommercialPlanVersion
    product: CommercialProduct
    billing_unit: CommercialBillingUnit
    cadence: CommercialBillingCadence
    price: MoneyAmount | None

    def __post_init__(self) -> None:
        if not isinstance(self.plan_id, CommercialPlanId):
            raise CommercialProductValidationError("plan_id must be CommercialPlanId")
        if not isinstance(self.version, CommercialPlanVersion):
            raise CommercialProductValidationError(
                "plan version must be CommercialPlanVersion"
            )
        if not isinstance(self.product, CommercialProduct):
            raise CommercialProductValidationError(
                "plan product must be CommercialProduct"
            )
        if not isinstance(self.billing_unit, CommercialBillingUnit):
            raise CommercialProductValidationError(
                "plan billing_unit must be CommercialBillingUnit"
            )
        if not isinstance(self.cadence, CommercialBillingCadence):
            raise CommercialProductValidationError(
                "plan cadence must be CommercialBillingCadence"
            )
        if self.price is not None and not isinstance(self.price, MoneyAmount):
            raise CommercialProductValidationError(
                "plan price must be MoneyAmount or None"
            )
        if self.price is not None and self.price.amount <= 0:
            raise CommercialProductValidationError(
                "commercial plan price must be positive"
            )
        if self.product.availability is CommercialProductAvailability.CONFIRMED:
            if self.price is None:
                raise CommercialProductValidationError(
                    "confirmed product plan requires explicit price"
                )
        elif self.price is not None:
            raise CommercialProductValidationError(
                "validation-required product must not carry canonical price"
            )
        self._validate_unit()

    def _validate_unit(self) -> None:
        if (
            self.product.kind is CommercialProductKind.CLIENT_EXECUTION_AGENT
            and self.billing_unit is not CommercialBillingUnit.ACCOUNT
        ):
            raise CommercialProductValidationError(
                "Client Execution Agent must be billed per account"
            )
        if (
            self.product.kind is CommercialProductKind.CLIENT_WIDGET
            and self.billing_unit is not CommercialBillingUnit.CLIENT
        ):
            raise CommercialProductValidationError(
                "Client Widget must be billed per client"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.plan_id.logical_values(),
            self.version.logical_values(),
            self.product.logical_values(),
            self.billing_unit.value,
            self.cadence.value,
            self.price.logical_values() if self.price is not None else None,
        )


@dataclass(frozen=True, slots=True)
class CommercialCatalog:
    products: tuple[CommercialProduct, ...]
    plans: tuple[CommercialPlan, ...]

    def __post_init__(self) -> None:
        product_ids = [product.product_id for product in self.products]
        if len(product_ids) != len(set(product_ids)):
            raise CommercialProductValidationError(
                "commercial product ids must be unique"
            )
        product_kinds = [product.kind for product in self.products]
        if len(product_kinds) != len(set(product_kinds)):
            raise CommercialProductValidationError(
                "commercial product kinds must be unique"
            )
        plan_keys = [(plan.plan_id, plan.version) for plan in self.plans]
        if len(plan_keys) != len(set(plan_keys)):
            raise CommercialProductValidationError(
                "commercial plan id/version pairs must be unique"
            )
        known_products = set(product_ids)
        if any(plan.product.product_id not in known_products for plan in self.plans):
            raise CommercialProductValidationError(
                "commercial plans must reference catalog products"
            )

    def plan_for(
        self,
        kind: CommercialProductKind,
        version: CommercialPlanVersion,
    ) -> Result[CommercialPlan, CommercialProductError]:
        matches = tuple(
            plan
            for plan in self.plans
            if plan.product.kind is kind and plan.version == version
        )
        if len(matches) != 1:
            return Failure(
                CommercialProductValidationError(
                    "exact commercial product plan version not found"
                )
            )
        return Success(matches[0])

    def logical_values(self) -> tuple[object, ...]:
        return (
            tuple(product.logical_values() for product in self.products),
            tuple(plan.logical_values() for plan in self.plans),
        )
