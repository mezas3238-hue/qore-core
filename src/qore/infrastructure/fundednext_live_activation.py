"""Strict loader/verifier for FundedNext production activation evidence."""

from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from qore.infrastructure.fundednext_live_authorization import (
    FundedNextLiveAccountAuthorization,
    FundedNextLiveAuthorizationError,
)
from qore.infrastructure.fundednext_stellar_instant import (
    AutomationVerificationState,
    RuleVerificationState,
    StellarInstantRuleVerification,
)
from qore.infrastructure.market_test_environment import MarketTestAccountIdentity

_ZERO_HASH = "0" * 64


@dataclass(frozen=True, slots=True)
class FundedNextLiveActivationBundle:
    authorization: FundedNextLiveAccountAuthorization
    rules: StellarInstantRuleVerification


def sha256_file(path: Path) -> str:
    if not path.is_file():
        raise FundedNextLiveAuthorizationError(f"activation evidence missing: {path.name}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assert_tracked_worktree_clean(root: Path) -> None:
    result = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    if result.stdout.strip():
        raise FundedNextLiveAuthorizationError("tracked-worktree-is-not-clean")


def load_verified_live_activation(
    *,
    root: Path,
    activation_path: Path,
    account: MarketTestAccountIdentity,
    runtime_git_sha: str,
    account_identity_fingerprint: str,
    server: str,
) -> FundedNextLiveActivationBundle:
    assert_tracked_worktree_clean(root)
    payload = _object(_read_json(activation_path), "activation")
    git_sha = _text(payload, "git_sha")
    fingerprint = _text(payload, "account_identity_fingerprint")
    expected_server = _text(payload, "expected_server")
    if git_sha != runtime_git_sha:
        raise FundedNextLiveAuthorizationError("activation git SHA mismatch")
    if fingerprint != account_identity_fingerprint:
        raise FundedNextLiveAuthorizationError("activation account fingerprint mismatch")
    if expected_server != server:
        raise FundedNextLiveAuthorizationError("activation server mismatch")

    provider_path = root / "src/qore/infrastructure/fundednext_stellar_instant.py"
    provider_hash = _text(payload, "provider_rules_fingerprint")
    if provider_hash != sha256_file(provider_path):
        raise FundedNextLiveAuthorizationError("provider rules fingerprint mismatch")

    no_send_path = root / "artifacts/fundednext_mt5_no_send_probe.json"
    shadow_path = root / "artifacts/fundednext_mt5_order_check_probe.json"
    restart_path = root / "artifacts/fundednext_restart_recovery.json"
    _verify_probe(
        path=no_send_path,
        expected_hash=_text(payload, "no_send_evidence_sha256"),
        expected_sha=git_sha,
        expected_fingerprint=fingerprint,
        kind="no-send",
    )
    _verify_probe(
        path=shadow_path,
        expected_hash=_text(payload, "shadow_evidence_sha256"),
        expected_sha=git_sha,
        expected_fingerprint=fingerprint,
        kind="shadow",
    )

    restart_passed = _bool(payload, "restart_recovery_passed")
    restart_hash = _text(payload, "restart_recovery_evidence_sha256")
    if restart_passed:
        _verify_restart(
            path=restart_path,
            expected_hash=restart_hash,
            expected_sha=git_sha,
            expected_fingerprint=fingerprint,
        )
    elif restart_hash != _ZERO_HASH:
        raise FundedNextLiveAuthorizationError(
            "restart evidence hash must be zero before restart proof"
        )

    auth = FundedNextLiveAccountAuthorization(
        account=account,
        git_sha=git_sha,
        account_identity_fingerprint=fingerprint,
        expected_server=expected_server,
        provider_rules_fingerprint=provider_hash,
        no_send_evidence_sha256=_text(payload, "no_send_evidence_sha256"),
        shadow_evidence_sha256=_text(payload, "shadow_evidence_sha256"),
        restart_recovery_evidence_sha256=restart_hash,
        ea_entitlement_verified=_bool(payload, "ea_entitlement_verified"),
        vps_entitlement_verified=_bool(payload, "vps_entitlement_verified"),
        provider_rules_current=_bool(payload, "provider_rules_current"),
        no_send_passed=_bool(payload, "no_send_passed"),
        shadow_passed=_bool(payload, "shadow_passed"),
        service_24_7_verified=_bool(payload, "service_24_7_verified"),
        restart_recovery_passed=restart_passed,
        activation_timestamp=_timestamp(payload, "activation_timestamp"),
        order_submission_authorized=_bool(payload, "order_submission_authorized"),
    )
    rules = StellarInstantRuleVerification(
        verification_state=(
            RuleVerificationState.CURRENT
            if auth.provider_rules_current
            else RuleVerificationState.STALE
        ),
        automation_state=(
            AutomationVerificationState.VERIFIED
            if auth.ea_entitlement_verified
            else AutomationVerificationState.UNVERIFIED
        ),
        ea_addon_verified=auth.ea_entitlement_verified,
        platform_verified=True,
        exact_product_verified=True,
    )
    auth.assert_matches(
        account=account,
        git_sha=runtime_git_sha,
        account_identity_fingerprint=account_identity_fingerprint,
        server=server,
    )
    return FundedNextLiveActivationBundle(authorization=auth, rules=rules)


def _verify_probe(
    *,
    path: Path,
    expected_hash: str,
    expected_sha: str,
    expected_fingerprint: str,
    kind: str,
) -> None:
    if sha256_file(path) != expected_hash:
        raise FundedNextLiveAuthorizationError(f"{kind} evidence digest mismatch")
    payload = _object(_read_json(path), kind)
    if payload.get("git_sha") != expected_sha:
        raise FundedNextLiveAuthorizationError(f"{kind} evidence SHA mismatch")
    if kind == "no-send":
        account = _object(payload.get("account"), "no-send.account")
        observed = account.get("identity_fingerprint")
        safety = _object(payload.get("safety"), "no-send.safety")
        if safety.get("order_send_called") is not False:
            raise FundedNextLiveAuthorizationError("no-send evidence mutated broker")
        if payload.get("ok") is not True:
            raise FundedNextLiveAuthorizationError("no-send evidence not successful")
    else:
        observed = payload.get("account_identity_fingerprint")
        if payload.get("order_send_called") is not False or payload.get("ok") is not True:
            raise FundedNextLiveAuthorizationError("shadow evidence is not clean")
    if observed != expected_fingerprint:
        raise FundedNextLiveAuthorizationError(f"{kind} account fingerprint mismatch")


def _verify_restart(
    *,
    path: Path,
    expected_hash: str,
    expected_sha: str,
    expected_fingerprint: str,
) -> None:
    if sha256_file(path) != expected_hash:
        raise FundedNextLiveAuthorizationError("restart evidence digest mismatch")
    payload = _object(_read_json(path), "restart")
    if payload.get("ok") is not True:
        raise FundedNextLiveAuthorizationError("restart evidence not successful")
    if payload.get("git_sha") != expected_sha:
        raise FundedNextLiveAuthorizationError("restart evidence SHA mismatch")
    if payload.get("account_identity_fingerprint") != expected_fingerprint:
        raise FundedNextLiveAuthorizationError("restart evidence account mismatch")
    if payload.get("order_submission_authorized") is not False:
        raise FundedNextLiveAuthorizationError("restart proof must be no-send")


def _read_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as error:
        raise FundedNextLiveAuthorizationError(
            f"cannot read activation evidence: {path.name}"
        ) from error


def _object(value: object, name: str) -> dict[str, object]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise FundedNextLiveAuthorizationError(f"{name} must be JSON object")
    return value


def _text(payload: dict[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise FundedNextLiveAuthorizationError(f"activation {key} must be text")
    return value


def _bool(payload: dict[str, object], key: str) -> bool:
    value = payload.get(key)
    if type(value) is not bool:
        raise FundedNextLiveAuthorizationError(f"activation {key} must be bool")
    return value


def _timestamp(payload: dict[str, object], key: str) -> datetime:
    raw = _text(payload, key)
    try:
        value = datetime.fromisoformat(raw)
    except ValueError as error:
        raise FundedNextLiveAuthorizationError(f"activation {key} invalid") from error
    if value.tzinfo is None or value.utcoffset() is None:
        raise FundedNextLiveAuthorizationError(f"activation {key} must be timezone-aware")
    return value
