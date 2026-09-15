from __future__ import annotations

from datetime import UTC, datetime

import pytest

from qore.infrastructure.fundednext_production_binding import (
    FUNDEDNEXT_MT5_PROVIDER_KEY,
    FUNDEDNEXT_STELLAR_INSTANT_SERVER,
    FundedNextProductionAccountBinding,
    FundedNextProductionBindingError,
    validate_fundednext_gateway_account,
)
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
    MarketTestAccountIdentity,
)

_NOW = datetime(2026, 9, 15, 9, 0, tzinfo=UTC)
_FINGERPRINT = "a" * 64


def _account(environment: MarketRuntimeEnvironment) -> MarketTestAccountIdentity:
    return MarketTestAccountIdentity(
        provider_key=FUNDEDNEXT_MT5_PROVIDER_KEY,
        account_ref="fn-si-production-001",
        environment=environment,
    )


def _binding() -> FundedNextProductionAccountBinding:
    account = _account(MarketRuntimeEnvironment.PRODUCTION)
    return FundedNextProductionAccountBinding(
        account=account,
        expected_server=FUNDEDNEXT_STELLAR_INSTANT_SERVER,
        account_identity_fingerprint=_FINGERPRINT,
        verified_at=_NOW,
        activation_record_id="fn-first-execution-20260915",
    )


def test_production_account_requires_explicit_matching_binding() -> None:
    account = _account(MarketRuntimeEnvironment.PRODUCTION)
    with pytest.raises(FundedNextProductionBindingError, match="requires explicit"):
        validate_fundednext_gateway_account(account, production_binding=None)

    binding = _binding()
    validate_fundednext_gateway_account(account, production_binding=binding)


def test_test_and_demo_remain_supported_without_production_binding() -> None:
    for environment in (
        MarketRuntimeEnvironment.TEST,
        MarketRuntimeEnvironment.DEMO,
    ):
        validate_fundednext_gateway_account(
            _account(environment),
            production_binding=None,
        )


def test_binding_cannot_be_attached_to_nonproduction_account() -> None:
    with pytest.raises(FundedNextProductionBindingError, match="cannot be attached"):
        validate_fundednext_gateway_account(
            _account(MarketRuntimeEnvironment.TEST),
            production_binding=_binding(),
        )


def test_binding_rejects_wrong_server_or_fingerprint() -> None:
    account = _account(MarketRuntimeEnvironment.PRODUCTION)
    with pytest.raises(FundedNextProductionBindingError, match="server"):
        FundedNextProductionAccountBinding(
            account=account,
            expected_server="Other-Server",
            account_identity_fingerprint=_FINGERPRINT,
            verified_at=_NOW,
            activation_record_id="fn-first-execution-20260915",
        )
    with pytest.raises(FundedNextProductionBindingError, match="sha256"):
        FundedNextProductionAccountBinding(
            account=account,
            expected_server=FUNDEDNEXT_STELLAR_INSTANT_SERVER,
            account_identity_fingerprint="bad",
            verified_at=_NOW,
            activation_record_id="fn-first-execution-20260915",
        )
