from datetime import UTC, datetime

import pytest

from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
    MarketTestAccountIdentity,
    MarketTestEnvironmentAuthorization,
    MarketTestEnvironmentBlockedError,
    MarketTestEnvironmentPolicy,
    MarketTestEnvironmentValidationError,
    authorize_market_test_account,
)
from qore.kernel.result import Failure, Success


def _account(environment: MarketRuntimeEnvironment) -> MarketTestAccountIdentity:
    return MarketTestAccountIdentity(
        provider_key="reference-provider",
        account_ref="demo-account-01",
        environment=environment,
    )


def test_default_policy_authorizes_test_and_demo_only() -> None:
    policy = MarketTestEnvironmentPolicy(policy_id="mission02-test-policy")
    at = datetime(2026, 8, 8, 10, 15, tzinfo=UTC)

    test_result = authorize_market_test_account(
        _account(MarketRuntimeEnvironment.TEST),
        policy=policy,
        authorized_at=at,
    )
    demo_result = authorize_market_test_account(
        _account(MarketRuntimeEnvironment.DEMO),
        policy=policy,
        authorized_at=at,
    )

    assert isinstance(test_result, Success)
    assert isinstance(demo_result, Success)
    assert isinstance(test_result.value, MarketTestEnvironmentAuthorization)
    assert test_result.value.account.environment is MarketRuntimeEnvironment.TEST
    assert demo_result.value.account.environment is MarketRuntimeEnvironment.DEMO


def test_production_environment_fails_closed() -> None:
    result = authorize_market_test_account(
        _account(MarketRuntimeEnvironment.PRODUCTION),
        policy=MarketTestEnvironmentPolicy(policy_id="mission02-test-policy"),
        authorized_at=datetime(2026, 8, 8, 10, 16, tzinfo=UTC),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, MarketTestEnvironmentBlockedError)


def test_sandbox_environment_is_not_external_test_execution() -> None:
    result = authorize_market_test_account(
        _account(MarketRuntimeEnvironment.SANDBOX),
        policy=MarketTestEnvironmentPolicy(policy_id="mission02-test-policy"),
        authorized_at=datetime(2026, 8, 8, 10, 17, tzinfo=UTC),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, MarketTestEnvironmentBlockedError)


def test_policy_cannot_allow_production() -> None:
    with pytest.raises(MarketTestEnvironmentValidationError):
        MarketTestEnvironmentPolicy(
            policy_id="unsafe-policy",
            allowed_environments=(MarketRuntimeEnvironment.PRODUCTION,),
        )


def test_policy_requires_stable_sorted_environment_order() -> None:
    with pytest.raises(MarketTestEnvironmentValidationError):
        MarketTestEnvironmentPolicy(
            policy_id="unstable-policy",
            allowed_environments=(
                MarketRuntimeEnvironment.TEST,
                MarketRuntimeEnvironment.DEMO,
            ),
        )


def test_authorization_requires_timezone_aware_timestamp() -> None:
    with pytest.raises(MarketTestEnvironmentValidationError):
        MarketTestEnvironmentAuthorization(
            account=_account(MarketRuntimeEnvironment.DEMO),
            policy_id="mission02-test-policy",
            authorized_at=datetime(2026, 8, 8, 10, 18),
        )


def test_account_identity_and_authorization_have_deterministic_logical_values() -> None:
    account = _account(MarketRuntimeEnvironment.DEMO)
    at = datetime(2026, 8, 8, 10, 19, tzinfo=UTC)
    authorization = MarketTestEnvironmentAuthorization(
        account=account,
        policy_id="mission02-test-policy",
        authorized_at=at,
    )

    assert account.logical_values() == (
        "reference-provider",
        "demo-account-01",
        "demo",
    )
    assert authorization.logical_values() == (
        account.logical_values(),
        "mission02-test-policy",
        at.isoformat(),
    )
