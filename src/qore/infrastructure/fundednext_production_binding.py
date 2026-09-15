"""Explicit production-account binding for FundedNext Stellar Instant.

This contract classifies a real FundedNext account without granting order authority.
The existing owner submission switch, provider-rule verification, Account-Wide Risk,
kill switches, durable mutation fencing, and reconciliation remain mandatory.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from re import fullmatch

from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
    MarketTestAccountIdentity,
)

FUNDEDNEXT_MT5_PROVIDER_KEY = "fundednext-stellar-instant-mt5"
FUNDEDNEXT_STELLAR_INSTANT_SERVER = "FundedNext-Server"


class FundedNextProductionBindingError(ValueError):
    """A production binding is malformed or does not match its account."""


@dataclass(frozen=True, slots=True)
class FundedNextProductionAccountBinding:
    """Non-secret proof that one QORE identity is intentionally PRODUCTION.

    ``account_identity_fingerprint`` is produced from sanitized broker metadata by
    the runtime readiness probe. It is not a credential and must not contain the
    MT5 login or password. Runtime transport still binds the actual login/server on
    every broker interaction.
    """

    account: MarketTestAccountIdentity
    expected_server: str
    account_identity_fingerprint: str
    verified_at: datetime
    activation_record_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.account, MarketTestAccountIdentity):
            raise FundedNextProductionBindingError(
                "production binding account must be MarketTestAccountIdentity"
            )
        if self.account.provider_key != FUNDEDNEXT_MT5_PROVIDER_KEY:
            raise FundedNextProductionBindingError(
                "production binding provider key mismatch"
            )
        if self.account.environment is not MarketRuntimeEnvironment.PRODUCTION:
            raise FundedNextProductionBindingError(
                "production binding requires PRODUCTION environment"
            )
        if self.expected_server != FUNDEDNEXT_STELLAR_INSTANT_SERVER:
            raise FundedNextProductionBindingError(
                "production binding server must be FundedNext-Server"
            )
        if fullmatch(r"[0-9a-f]{64}", self.account_identity_fingerprint) is None:
            raise FundedNextProductionBindingError(
                "account identity fingerprint must be lowercase sha256 hex"
            )
        if not isinstance(self.verified_at, datetime):
            raise FundedNextProductionBindingError("verified_at must be datetime")
        if self.verified_at.tzinfo is None or self.verified_at.utcoffset() is None:
            raise FundedNextProductionBindingError(
                "verified_at must be timezone-aware"
            )
        if fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{7,127}", self.activation_record_id) is None:
            raise FundedNextProductionBindingError(
                "activation_record_id must be a stable non-secret identifier"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.account.logical_values(),
            self.expected_server,
            self.account_identity_fingerprint,
            self.verified_at.isoformat(),
            self.activation_record_id,
        )


def validate_fundednext_gateway_account(
    account: MarketTestAccountIdentity,
    *,
    production_binding: FundedNextProductionAccountBinding | None,
) -> None:
    """Fail closed unless account is test/demo or explicitly bound production."""

    if not isinstance(account, MarketTestAccountIdentity):
        raise FundedNextProductionBindingError("MT5 account identity must be explicit")
    if account.provider_key != FUNDEDNEXT_MT5_PROVIDER_KEY:
        raise FundedNextProductionBindingError(
            "MT5 account must use fundednext-stellar-instant-mt5 provider key"
        )
    if account.environment in {
        MarketRuntimeEnvironment.DEMO,
        MarketRuntimeEnvironment.TEST,
    }:
        if production_binding is not None:
            raise FundedNextProductionBindingError(
                "production binding cannot be attached to TEST/DEMO account"
            )
        return
    if account.environment is not MarketRuntimeEnvironment.PRODUCTION:
        raise FundedNextProductionBindingError(
            "FundedNext gateway environment is not execution-supported"
        )
    if production_binding is None:
        raise FundedNextProductionBindingError(
            "PRODUCTION account requires explicit FundedNext production binding"
        )
    if production_binding.account != account:
        raise FundedNextProductionBindingError(
            "production binding account does not match gateway account"
        )
