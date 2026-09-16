"""Explicit live-capital activation contract for the FundedNext MT5 runtime.

This module is intentionally separate from MISSION-02 TEST/DEMO authorization.
A PRODUCTION account may reach the live MT5 mutation boundary only when the
runtime presents one exact-SHA, account-bound activation record whose required
operational evidence is complete. The record contains no login or password.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from re import fullmatch

from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
    MarketTestAccountIdentity,
)
from qore.kernel.errors import InfrastructureError


class FundedNextLiveAuthorizationError(InfrastructureError):
    __slots__ = ()


@dataclass(frozen=True, slots=True)
class FundedNextLiveAccountAuthorization:
    account: MarketTestAccountIdentity
    git_sha: str
    account_identity_fingerprint: str
    expected_server: str
    provider_rules_fingerprint: str
    no_send_evidence_sha256: str
    shadow_evidence_sha256: str
    restart_recovery_evidence_sha256: str
    ea_entitlement_verified: bool
    vps_entitlement_verified: bool
    provider_rules_current: bool
    no_send_passed: bool
    shadow_passed: bool
    service_24_7_verified: bool
    restart_recovery_passed: bool
    activation_timestamp: datetime
    order_submission_authorized: bool

    def __post_init__(self) -> None:
        if not isinstance(self.account, MarketTestAccountIdentity):
            raise FundedNextLiveAuthorizationError("live account identity is required")
        if self.account.environment is not MarketRuntimeEnvironment.PRODUCTION:
            raise FundedNextLiveAuthorizationError(
                "FundedNext live authorization requires PRODUCTION account identity"
            )
        if self.account.provider_key != "fundednext-stellar-instant-mt5":
            raise FundedNextLiveAuthorizationError("live provider identity mismatch")
        if fullmatch(r"[0-9a-f]{40}", self.git_sha) is None:
            raise FundedNextLiveAuthorizationError(
                "live git_sha must be full lowercase SHA"
            )
        hash_fields: tuple[tuple[str, str], ...] = (
            ("account_identity_fingerprint", self.account_identity_fingerprint),
            ("provider_rules_fingerprint", self.provider_rules_fingerprint),
            ("no_send_evidence_sha256", self.no_send_evidence_sha256),
            ("shadow_evidence_sha256", self.shadow_evidence_sha256),
            ("restart_recovery_evidence_sha256", self.restart_recovery_evidence_sha256),
        )
        for hash_name, hash_value in hash_fields:
            if fullmatch(r"[0-9a-f]{64}", hash_value) is None:
                raise FundedNextLiveAuthorizationError(
                    f"{hash_name} must be SHA-256 hex"
                )
        if not isinstance(self.expected_server, str) or not self.expected_server.strip():
            raise FundedNextLiveAuthorizationError("expected_server is required")
        if (
            self.activation_timestamp.tzinfo is None
            or self.activation_timestamp.utcoffset() is None
        ):
            raise FundedNextLiveAuthorizationError(
                "activation_timestamp must be timezone-aware"
            )
        bool_fields: tuple[tuple[str, bool], ...] = (
            ("ea_entitlement_verified", self.ea_entitlement_verified),
            ("vps_entitlement_verified", self.vps_entitlement_verified),
            ("provider_rules_current", self.provider_rules_current),
            ("no_send_passed", self.no_send_passed),
            ("shadow_passed", self.shadow_passed),
            ("service_24_7_verified", self.service_24_7_verified),
            ("restart_recovery_passed", self.restart_recovery_passed),
            ("order_submission_authorized", self.order_submission_authorized),
        )
        for bool_name, bool_value in bool_fields:
            if type(bool_value) is not bool:
                raise FundedNextLiveAuthorizationError(f"{bool_name} must be bool")

    @property
    def can_submit(self) -> bool:
        return all(
            (
                self.ea_entitlement_verified,
                self.vps_entitlement_verified,
                self.provider_rules_current,
                self.no_send_passed,
                self.shadow_passed,
                self.service_24_7_verified,
                self.restart_recovery_passed,
                self.order_submission_authorized,
            )
        )

    def assert_identity_matches(
        self,
        *,
        account: MarketTestAccountIdentity,
        git_sha: str,
        account_identity_fingerprint: str,
        server: str,
    ) -> None:
        if account != self.account:
            raise FundedNextLiveAuthorizationError("live account binding mismatch")
        if git_sha != self.git_sha:
            raise FundedNextLiveAuthorizationError("live git SHA mismatch")
        if account_identity_fingerprint != self.account_identity_fingerprint:
            raise FundedNextLiveAuthorizationError("live account fingerprint mismatch")
        if server != self.expected_server:
            raise FundedNextLiveAuthorizationError("live MT5 server mismatch")

    def assert_matches(
        self,
        *,
        account: MarketTestAccountIdentity,
        git_sha: str,
        account_identity_fingerprint: str,
        server: str,
    ) -> None:
        """Validate identity for both SHADOW and LIVE construction."""
        self.assert_identity_matches(
            account=account,
            git_sha=git_sha,
            account_identity_fingerprint=account_identity_fingerprint,
            server=server,
        )

    def assert_can_submit(
        self,
        *,
        account: MarketTestAccountIdentity,
        git_sha: str,
        account_identity_fingerprint: str,
        server: str,
    ) -> None:
        self.assert_identity_matches(
            account=account,
            git_sha=git_sha,
            account_identity_fingerprint=account_identity_fingerprint,
            server=server,
        )
        if not self.can_submit:
            raise FundedNextLiveAuthorizationError(
                "live activation evidence is incomplete"
            )
