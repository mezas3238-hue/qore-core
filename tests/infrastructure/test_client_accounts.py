from __future__ import annotations

from uuid import UUID

import pytest

from qore.infrastructure.client_accounts import (
    AccountPolicyReference,
    ClientAccountRegistrySnapshot,
    ClientAccountResolutionError,
    ClientAccountValidationError,
    ClientId,
    ClientTradingAccountBinding,
    ExecutionRuntimeReference,
    ProductEntitlementReference,
    TradingAccountId,
    TradingAccountKind,
    TradingAccountLifecycleState,
)
from qore.kernel.result import Failure, Success


_CLIENT_A = ClientId(UUID("31000000-0000-0000-0000-000000000001"))
_CLIENT_B = ClientId(UUID("31000000-0000-0000-0000-000000000002"))
_ACCOUNT_1 = TradingAccountId(UUID("31000000-0000-0000-0000-000000000101"))
_ACCOUNT_2 = TradingAccountId(UUID("31000000-0000-0000-0000-000000000102"))
_ACCOUNT_3 = TradingAccountId(UUID("31000000-0000-0000-0000-000000000103"))


def _binding(
    *,
    client_id: ClientId = _CLIENT_A,
    account_id: TradingAccountId = _ACCOUNT_1,
    account_kind: TradingAccountKind = TradingAccountKind.BROKERAGE,
    lifecycle_state: TradingAccountLifecycleState = TradingAccountLifecycleState.ACTIVE,
    suffix: int = 1,
) -> ClientTradingAccountBinding:
    return ClientTradingAccountBinding(
        client_id=client_id,
        account_id=account_id,
        account_kind=account_kind,
        lifecycle_state=lifecycle_state,
        policy_ref=AccountPolicyReference(
            UUID(f"31000000-0000-0000-0000-000000001{suffix:03d}")
        ),
        product_entitlement_ref=ProductEntitlementReference(
            UUID(f"31000000-0000-0000-0000-000000002{suffix:03d}")
        ),
        runtime_ref=ExecutionRuntimeReference(
            UUID(f"31000000-0000-0000-0000-000000003{suffix:03d}")
        ),
    )


def _client_id_with_runtime_value(value: object) -> ClientId:
    instance = object.__new__(ClientId)
    object.__setattr__(instance, "value", value)
    return instance


def _account_id_with_runtime_value(value: object) -> TradingAccountId:
    instance = object.__new__(TradingAccountId)
    object.__setattr__(instance, "value", value)
    return instance


def _binding_with_runtime_policy_ref(value: object) -> ClientTradingAccountBinding:
    instance = object.__new__(ClientTradingAccountBinding)
    object.__setattr__(instance, "client_id", _CLIENT_A)
    object.__setattr__(instance, "account_id", _ACCOUNT_1)
    object.__setattr__(instance, "account_kind", TradingAccountKind.BROKERAGE)
    object.__setattr__(instance, "lifecycle_state", TradingAccountLifecycleState.ACTIVE)
    object.__setattr__(instance, "policy_ref", value)
    object.__setattr__(
        instance,
        "product_entitlement_ref",
        ProductEntitlementReference(UUID("31000000-0000-0000-0000-000000002888")),
    )
    object.__setattr__(
        instance,
        "runtime_ref",
        ExecutionRuntimeReference(UUID("31000000-0000-0000-0000-000000003888")),
    )
    return instance


def _registry_with_runtime_bindings(value: object) -> ClientAccountRegistrySnapshot:
    instance = object.__new__(ClientAccountRegistrySnapshot)
    object.__setattr__(instance, "bindings", value)
    return instance


def test_client_and_account_identities_are_opaque_typed_and_immutable() -> None:
    assert _CLIENT_A.logical_values() == ("31000000-0000-0000-0000-000000000001",)
    assert _ACCOUNT_1.logical_values() == ("31000000-0000-0000-0000-000000000101",)

    invalid_client = _client_id_with_runtime_value("client-1")
    invalid_account = _account_id_with_runtime_value("account-1")

    with pytest.raises(ClientAccountValidationError):
        invalid_client.__post_init__()

    with pytest.raises(ClientAccountValidationError):
        invalid_account.__post_init__()

    with pytest.raises(AttributeError):
        _CLIENT_A.__setattr__(
            "value",
            UUID("31000000-0000-0000-0000-000000000099"),
        )


def test_binding_contains_only_opaque_account_scoped_references() -> None:
    binding = _binding()

    assert binding.client_id == _CLIENT_A
    assert binding.account_id == _ACCOUNT_1
    assert binding.account_kind is TradingAccountKind.BROKERAGE
    assert binding.lifecycle_state is TradingAccountLifecycleState.ACTIVE
    assert binding.logical_values() == binding.logical_values()
    assert not hasattr(binding, "broker_account_number")
    assert not hasattr(binding, "broker_login")
    assert not hasattr(binding, "password")
    assert not hasattr(binding, "token")
    assert not hasattr(binding, "credentials")
    assert not hasattr(binding, "execute")
    assert not hasattr(binding, "submit_order")


def test_binding_rejects_identity_collision_and_untyped_references() -> None:
    shared = UUID("31000000-0000-0000-0000-000000000777")

    with pytest.raises(ClientAccountValidationError):
        ClientTradingAccountBinding(
            client_id=ClientId(shared),
            account_id=TradingAccountId(shared),
            account_kind=TradingAccountKind.BROKERAGE,
            lifecycle_state=TradingAccountLifecycleState.ACTIVE,
            policy_ref=AccountPolicyReference(
                UUID("31000000-0000-0000-0000-000000001777")
            ),
            product_entitlement_ref=ProductEntitlementReference(
                UUID("31000000-0000-0000-0000-000000002777")
            ),
            runtime_ref=ExecutionRuntimeReference(
                UUID("31000000-0000-0000-0000-000000003777")
            ),
        )

    invalid_binding = _binding_with_runtime_policy_ref("policy-ref")
    with pytest.raises(ClientAccountValidationError):
        invalid_binding.__post_init__()


def test_one_client_can_bind_many_independent_accounts() -> None:
    first = _binding(account_id=_ACCOUNT_1, suffix=1)
    second = _binding(
        account_id=_ACCOUNT_2,
        account_kind=TradingAccountKind.PROP_FIRM,
        lifecycle_state=TradingAccountLifecycleState.RESTRICTED,
        suffix=2,
    )
    registry = ClientAccountRegistrySnapshot((second, first))

    result = registry.accounts_for_client(_CLIENT_A)

    assert isinstance(result, Success)
    assert result.value == (first, second)
    assert result.value[0].policy_ref != result.value[1].policy_ref
    assert result.value[0].runtime_ref != result.value[1].runtime_ref
    assert registry.logical_values() == registry.logical_values()


def test_registry_normalizes_bindings_deterministically() -> None:
    client_b_binding = _binding(
        client_id=_CLIENT_B,
        account_id=_ACCOUNT_3,
        suffix=3,
    )
    account_2_binding = _binding(account_id=_ACCOUNT_2, suffix=2)
    account_1_binding = _binding(account_id=_ACCOUNT_1, suffix=1)

    registry = ClientAccountRegistrySnapshot(
        (client_b_binding, account_2_binding, account_1_binding)
    )

    assert registry.bindings == (
        account_1_binding,
        account_2_binding,
        client_b_binding,
    )


def test_registry_rejects_duplicate_or_cross_client_account_binding() -> None:
    first = _binding(account_id=_ACCOUNT_1, suffix=1)
    duplicate = _binding(account_id=_ACCOUNT_1, suffix=4)
    conflicting_owner = _binding(
        client_id=_CLIENT_B,
        account_id=_ACCOUNT_1,
        suffix=5,
    )

    with pytest.raises(ClientAccountValidationError):
        ClientAccountRegistrySnapshot((first, duplicate))

    with pytest.raises(ClientAccountValidationError):
        ClientAccountRegistrySnapshot((first, conflicting_owner))


def test_registry_rejects_empty_or_non_binding_state() -> None:
    with pytest.raises(ClientAccountValidationError):
        ClientAccountRegistrySnapshot(())

    invalid_registry = _registry_with_runtime_bindings((_CLIENT_A,))
    with pytest.raises(ClientAccountValidationError):
        invalid_registry.__post_init__()


def test_binding_resolution_is_exact_and_fails_closed() -> None:
    first = _binding(account_id=_ACCOUNT_1, suffix=1)
    second = _binding(client_id=_CLIENT_B, account_id=_ACCOUNT_2, suffix=2)
    registry = ClientAccountRegistrySnapshot((first, second))

    found = registry.resolve_binding(client_id=_CLIENT_A, account_id=_ACCOUNT_1)
    wrong_owner = registry.resolve_binding(client_id=_CLIENT_A, account_id=_ACCOUNT_2)
    missing = registry.resolve_binding(client_id=_CLIENT_A, account_id=_ACCOUNT_3)

    assert isinstance(found, Success)
    assert found.value == first

    assert isinstance(wrong_owner, Failure)
    assert isinstance(wrong_owner.error, ClientAccountResolutionError)
    assert str(wrong_owner.error) == "trading account is bound to a different client"

    assert isinstance(missing, Failure)
    assert isinstance(missing.error, ClientAccountResolutionError)
    assert str(missing.error) == "trading account binding not found"


def test_client_lookup_without_accounts_fails_closed() -> None:
    registry = ClientAccountRegistrySnapshot((_binding(),))

    result = registry.accounts_for_client(_CLIENT_B)

    assert isinstance(result, Failure)
    assert isinstance(result.error, ClientAccountResolutionError)
    assert str(result.error) == "no trading accounts are bound to this client"


def test_account_classification_and_lifecycle_are_not_trading_authority() -> None:
    binding = _binding(
        account_kind=TradingAccountKind.UNKNOWN,
        lifecycle_state=TradingAccountLifecycleState.ACTIVE,
    )

    assert binding.account_kind is TradingAccountKind.UNKNOWN
    assert binding.lifecycle_state is TradingAccountLifecycleState.ACTIVE
    assert not hasattr(binding, "authorized")
    assert not hasattr(binding.lifecycle_state, "can_trade")
