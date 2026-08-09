from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success


class ClientAccountFoundationError(InfrastructureError):
    """Base error for client/account foundation contracts."""

    __slots__ = ()


class ClientAccountValidationError(ClientAccountFoundationError):
    """Violation of a client/account identity or binding invariant."""

    __slots__ = ()


class ClientAccountResolutionError(ClientAccountFoundationError):
    """A requested client/account binding cannot be resolved safely."""

    __slots__ = ()


def _validate_uuid(value: UUID, *, field_name: str) -> None:
    if not isinstance(value, UUID):
        raise ClientAccountValidationError(f"{field_name} must be a UUID")


@dataclass(frozen=True, slots=True)
class ClientId:
    """Opaque QORE identity for one commercial client.

    This value is not a civil-identity document, email address or payment identity.
    """

    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="client id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class TradingAccountId:
    """Opaque QORE identity for one client trading account.

    This value is deliberately not a broker login, provider account number or credential.
    """

    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="trading account id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class AccountPolicyReference:
    """Opaque reference to the effective account-policy snapshot."""

    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="account policy reference")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ProductEntitlementReference:
    """Opaque reference to the account-scoped product entitlement."""

    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="product entitlement reference")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ExecutionRuntimeReference:
    """Opaque reference to the execution runtime assigned to an account.

    The reference is identity/provenance only. It is not an execution lease and grants no
    authority by itself.
    """

    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="execution runtime reference")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


class TradingAccountKind(StrEnum):
    """High-level client-account classification without provider-specific assumptions."""

    BROKERAGE = "brokerage"
    PROP_FIRM = "prop_firm"
    UNKNOWN = "unknown"


class TradingAccountLifecycleState(StrEnum):
    """Commercial/operational lifecycle classification for a client account."""

    PROVISIONED = "provisioned"
    ACTIVE = "active"
    RESTRICTED = "restricted"
    SUSPENDED = "suspended"
    CLOSED = "closed"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ClientTradingAccountBinding:
    """Canonical ownership and account-scoped reference binding.

    The binding contains only opaque QORE identities and classifications. It contains no broker
    credential, civil identity, trading strategy or execution command.
    """

    client_id: ClientId
    account_id: TradingAccountId
    account_kind: TradingAccountKind
    lifecycle_state: TradingAccountLifecycleState
    policy_ref: AccountPolicyReference
    product_entitlement_ref: ProductEntitlementReference
    runtime_ref: ExecutionRuntimeReference

    def __post_init__(self) -> None:
        if not isinstance(self.client_id, ClientId):
            raise ClientAccountValidationError("binding client_id must be ClientId")
        if not isinstance(self.account_id, TradingAccountId):
            raise ClientAccountValidationError("binding account_id must be TradingAccountId")
        if self.client_id.value == self.account_id.value:
            raise ClientAccountValidationError(
                "client and trading account identities must be distinct"
            )
        if not isinstance(self.account_kind, TradingAccountKind):
            raise ClientAccountValidationError(
                "binding account_kind must be TradingAccountKind"
            )
        if not isinstance(self.lifecycle_state, TradingAccountLifecycleState):
            raise ClientAccountValidationError(
                "binding lifecycle_state must be TradingAccountLifecycleState"
            )
        if not isinstance(self.policy_ref, AccountPolicyReference):
            raise ClientAccountValidationError(
                "binding policy_ref must be AccountPolicyReference"
            )
        if not isinstance(self.product_entitlement_ref, ProductEntitlementReference):
            raise ClientAccountValidationError(
                "binding product_entitlement_ref must be ProductEntitlementReference"
            )
        if not isinstance(self.runtime_ref, ExecutionRuntimeReference):
            raise ClientAccountValidationError(
                "binding runtime_ref must be ExecutionRuntimeReference"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.client_id.logical_values(),
            self.account_id.logical_values(),
            self.account_kind.value,
            self.lifecycle_state.value,
            self.policy_ref.logical_values(),
            self.product_entitlement_ref.logical_values(),
            self.runtime_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class ClientAccountRegistrySnapshot:
    """Immutable deterministic snapshot of canonical client/account bindings.

    One account may appear exactly once. A client may own one or many independent accounts.
    """

    bindings: tuple[ClientTradingAccountBinding, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.bindings, tuple):
            raise ClientAccountValidationError("registry bindings must be a tuple")
        if not self.bindings:
            raise ClientAccountValidationError("registry bindings must not be empty")
        if any(not isinstance(binding, ClientTradingAccountBinding) for binding in self.bindings):
            raise ClientAccountValidationError(
                "registry bindings must contain only ClientTradingAccountBinding values"
            )

        seen_accounts: set[UUID] = set()
        for binding in self.bindings:
            account_value = binding.account_id.value
            if account_value in seen_accounts:
                raise ClientAccountValidationError(
                    "each trading account must have exactly one canonical client binding"
                )
            seen_accounts.add(account_value)

        ordered = tuple(
            sorted(
                self.bindings,
                key=lambda binding: (
                    binding.client_id.value.hex,
                    binding.account_id.value.hex,
                ),
            )
        )
        object.__setattr__(self, "bindings", ordered)

    def logical_values(self) -> tuple[tuple[object, ...], ...]:
        return tuple(binding.logical_values() for binding in self.bindings)

    def accounts_for_client(
        self,
        client_id: ClientId,
    ) -> Result[tuple[ClientTradingAccountBinding, ...], ClientAccountFoundationError]:
        if not isinstance(client_id, ClientId):
            return Failure(ClientAccountResolutionError("client_id must be ClientId"))

        matches = tuple(
            binding for binding in self.bindings if binding.client_id == client_id
        )
        if not matches:
            return Failure(
                ClientAccountResolutionError("no trading accounts are bound to this client")
            )
        return Success(matches)

    def resolve_binding(
        self,
        *,
        client_id: ClientId,
        account_id: TradingAccountId,
    ) -> Result[ClientTradingAccountBinding, ClientAccountFoundationError]:
        if not isinstance(client_id, ClientId):
            return Failure(ClientAccountResolutionError("client_id must be ClientId"))
        if not isinstance(account_id, TradingAccountId):
            return Failure(
                ClientAccountResolutionError("account_id must be TradingAccountId")
            )

        for binding in self.bindings:
            if binding.account_id != account_id:
                continue
            if binding.client_id != client_id:
                return Failure(
                    ClientAccountResolutionError(
                        "trading account is bound to a different client"
                    )
                )
            return Success(binding)

        return Failure(ClientAccountResolutionError("trading account binding not found"))
