from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from re import fullmatch

from qore.infrastructure.ports import ExternalPortError
from qore.kernel.result import Failure, Result, Success


class MarketTestEnvironmentError(ExternalPortError):
    """Base error for real-market test environment contracts."""

    __slots__ = ()


class MarketTestEnvironmentValidationError(MarketTestEnvironmentError):
    """Violation of an environment/account invariant."""

    __slots__ = ()


class MarketTestEnvironmentBlockedError(MarketTestEnvironmentError):
    """Fail-closed result for an environment that is not execution-safe."""

    __slots__ = ()


class MarketRuntimeEnvironment(StrEnum):
    """Closed runtime environments known to MISSION-02."""

    SANDBOX = "sandbox"
    TEST = "test"
    DEMO = "demo"
    PRODUCTION = "production"


@dataclass(frozen=True, slots=True)
class MarketTestAccountIdentity:
    """Non-secret provider/account identity with explicit environment classification."""

    provider_key: str
    account_ref: str
    environment: MarketRuntimeEnvironment

    def __post_init__(self) -> None:
        if not isinstance(self.provider_key, str) or fullmatch(
            r"[a-z][a-z0-9._-]*", self.provider_key
        ) is None:
            raise MarketTestEnvironmentValidationError(
                "provider_key must use canonical lowercase identifier syntax"
            )
        if not isinstance(self.account_ref, str) or fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9._-]*", self.account_ref
        ) is None:
            raise MarketTestEnvironmentValidationError(
                "account_ref must be a non-secret stable identifier"
            )
        if not isinstance(self.environment, MarketRuntimeEnvironment):
            raise MarketTestEnvironmentValidationError(
                "environment must be MarketRuntimeEnvironment"
            )

    def logical_values(self) -> tuple[str, str, str]:
        return (self.provider_key, self.account_ref, self.environment.value)


@dataclass(frozen=True, slots=True)
class MarketTestEnvironmentPolicy:
    """Explicit allowlist for environments permitted to receive test executions."""

    policy_id: str
    allowed_environments: tuple[MarketRuntimeEnvironment, ...] = (
        MarketRuntimeEnvironment.DEMO,
        MarketRuntimeEnvironment.TEST,
    )

    def __post_init__(self) -> None:
        if not isinstance(self.policy_id, str) or fullmatch(
            r"[a-z][a-z0-9._-]*", self.policy_id
        ) is None:
            raise MarketTestEnvironmentValidationError(
                "policy_id must use canonical lowercase identifier syntax"
            )
        if not isinstance(self.allowed_environments, tuple):
            raise MarketTestEnvironmentValidationError(
                "allowed_environments must be a tuple"
            )
        if not self.allowed_environments:
            raise MarketTestEnvironmentValidationError(
                "allowed_environments must not be empty"
            )
        if len(set(self.allowed_environments)) != len(self.allowed_environments):
            raise MarketTestEnvironmentValidationError(
                "allowed_environments must not contain duplicates"
            )
        if tuple(sorted(self.allowed_environments, key=lambda item: item.value)) != (
            self.allowed_environments
        ):
            raise MarketTestEnvironmentValidationError(
                "allowed_environments must use stable sorted order"
            )
        for environment in self.allowed_environments:
            if not isinstance(environment, MarketRuntimeEnvironment):
                raise MarketTestEnvironmentValidationError(
                    "allowed_environments entries must be MarketRuntimeEnvironment"
                )
            if environment not in {
                MarketRuntimeEnvironment.DEMO,
                MarketRuntimeEnvironment.TEST,
            }:
                raise MarketTestEnvironmentValidationError(
                    "MISSION-02 policy may allow only TEST or DEMO environments"
                )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.policy_id,
            tuple(environment.value for environment in self.allowed_environments),
        )


@dataclass(frozen=True, slots=True)
class MarketTestEnvironmentAuthorization:
    """Proof that a non-production account was explicitly authorized for test execution."""

    account: MarketTestAccountIdentity
    policy_id: str
    authorized_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.account, MarketTestAccountIdentity):
            raise MarketTestEnvironmentValidationError(
                "authorization account must be MarketTestAccountIdentity"
            )
        if not isinstance(self.policy_id, str) or not self.policy_id:
            raise MarketTestEnvironmentValidationError(
                "authorization policy_id must be non-empty"
            )
        if not isinstance(self.authorized_at, datetime):
            raise MarketTestEnvironmentValidationError(
                "authorized_at must be a datetime"
            )
        if self.authorized_at.tzinfo is None or self.authorized_at.utcoffset() is None:
            raise MarketTestEnvironmentValidationError(
                "authorized_at must be timezone-aware"
            )
        if self.account.environment not in {
            MarketRuntimeEnvironment.DEMO,
            MarketRuntimeEnvironment.TEST,
        }:
            raise MarketTestEnvironmentValidationError(
                "environment authorization is valid only for TEST or DEMO"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.account.logical_values(),
            self.policy_id,
            self.authorized_at.isoformat(),
        )


def authorize_market_test_account(
    account: MarketTestAccountIdentity,
    *,
    policy: MarketTestEnvironmentPolicy,
    authorized_at: datetime,
) -> Result[MarketTestEnvironmentAuthorization, MarketTestEnvironmentError]:
    """Authorize TEST/DEMO only; every other environment fails closed."""
    if not isinstance(account, MarketTestAccountIdentity):
        return Failure(
            MarketTestEnvironmentValidationError(
                "market-test authorization requires MarketTestAccountIdentity"
            )
        )
    if not isinstance(policy, MarketTestEnvironmentPolicy):
        return Failure(
            MarketTestEnvironmentValidationError(
                "market-test authorization requires MarketTestEnvironmentPolicy"
            )
        )
    if account.environment not in policy.allowed_environments:
        return Failure(
            MarketTestEnvironmentBlockedError(
                f"environment {account.environment.value} is not authorized for test execution"
            )
        )
    try:
        authorization = MarketTestEnvironmentAuthorization(
            account=account,
            policy_id=policy.policy_id,
            authorized_at=authorized_at,
        )
    except MarketTestEnvironmentError as error:
        return Failure(error)
    return Success(authorization)
