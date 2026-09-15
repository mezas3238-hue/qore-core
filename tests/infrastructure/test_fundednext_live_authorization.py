from __future__ import annotations

from datetime import UTC, datetime

import pytest

from qore.infrastructure.fundednext_live_authorization import (
    FundedNextLiveAccountAuthorization,
    FundedNextLiveAuthorizationError,
)
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
    MarketTestAccountIdentity,
)

_NOW = datetime(2026, 9, 15, 12, 0, tzinfo=UTC)
_SHA = "a" * 40
_HASH = "b" * 64


def _account() -> MarketTestAccountIdentity:
    return MarketTestAccountIdentity(
        provider_key="fundednext-stellar-instant-mt5",
        account_ref="fundednext-stellar-instant-live",
        environment=MarketRuntimeEnvironment.PRODUCTION,
    )


def _authorization(**overrides: object) -> FundedNextLiveAccountAuthorization:
    values: dict[str, object] = {
        "account": _account(),
        "git_sha": _SHA,
        "account_identity_fingerprint": _HASH,
        "expected_server": "FundedNext-Server",
        "provider_rules_fingerprint": _HASH,
        "no_send_evidence_sha256": _HASH,
        "shadow_evidence_sha256": _HASH,
        "restart_recovery_evidence_sha256": _HASH,
        "ea_entitlement_verified": True,
        "vps_entitlement_verified": True,
        "provider_rules_current": True,
        "no_send_passed": True,
        "shadow_passed": True,
        "service_24_7_verified": True,
        "restart_recovery_passed": True,
        "activation_timestamp": _NOW,
        "order_submission_authorized": True,
    }
    values.update(overrides)
    return FundedNextLiveAccountAuthorization(**values)  # type: ignore[arg-type]


def test_complete_live_evidence_can_submit() -> None:
    auth = _authorization()
    assert auth.can_submit is True
    auth.assert_can_submit(
        account=_account(),
        git_sha=_SHA,
        account_identity_fingerprint=_HASH,
        server="FundedNext-Server",
    )


def test_vps_entitlement_is_required_for_submit() -> None:
    auth = _authorization(vps_entitlement_verified=False)
    assert auth.can_submit is False


def test_shadow_identity_can_bind_before_live_authority_exists() -> None:
    auth = _authorization(shadow_passed=False, order_submission_authorized=False)
    assert auth.can_submit is False
    auth.assert_identity_matches(
        account=_account(),
        git_sha=_SHA,
        account_identity_fingerprint=_HASH,
        server="FundedNext-Server",
    )
    with pytest.raises(FundedNextLiveAuthorizationError, match="evidence is incomplete"):
        auth.assert_can_submit(
            account=_account(),
            git_sha=_SHA,
            account_identity_fingerprint=_HASH,
            server="FundedNext-Server",
        )


def test_live_authority_is_exact_sha_and_account_bound() -> None:
    auth = _authorization()
    with pytest.raises(FundedNextLiveAuthorizationError, match="git SHA mismatch"):
        auth.assert_identity_matches(
            account=_account(),
            git_sha="c" * 40,
            account_identity_fingerprint=_HASH,
            server="FundedNext-Server",
        )
