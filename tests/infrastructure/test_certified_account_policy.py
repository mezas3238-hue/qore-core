from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

import qore.infrastructure.account_policy as account_policy
import qore.infrastructure.certified_account_policy as certified
import qore.infrastructure.client_accounts as client_accounts
import qore.infrastructure.proprietary_accounts as proprietary_accounts
import qore.kernel.result as result

_ACCOUNT = client_accounts.TradingAccountId(
    UUID("71000000-0000-0000-0000-000000000001")
)
_OTHER_ACCOUNT = client_accounts.TradingAccountId(
    UUID("71000000-0000-0000-0000-000000000002")
)
_POLICY_REF = client_accounts.AccountPolicyReference(
    UUID("71000000-0000-0000-0000-000000000101")
)
_SNAPSHOT_ID = account_policy.AccountPolicySnapshotId(
    UUID("71000000-0000-0000-0000-000000000201")
)
_FIRM_REF = account_policy.PropFirmReference(
    UUID("71000000-0000-0000-0000-000000000301")
)
_OTHER_FIRM_REF = account_policy.PropFirmReference(
    UUID("71000000-0000-0000-0000-000000000302")
)
_PROGRAM_REF = account_policy.PropProgramReference(
    UUID("71000000-0000-0000-0000-000000000401")
)
_OTHER_PROGRAM_REF = account_policy.PropProgramReference(
    UUID("71000000-0000-0000-0000-000000000402")
)
_SOURCE_ID = certified.PolicySourceEvidenceId(
    UUID("71000000-0000-0000-0000-000000000501")
)
_SOURCE_CERT_ID = certified.PolicySourceCertificateId(
    UUID("71000000-0000-0000-0000-000000000601")
)
_POLICY_CERT_ID = certified.PolicyCertificationId(
    UUID("71000000-0000-0000-0000-000000000701")
)
_VERIFIER_REF = certified.PolicyVerifierReference(
    UUID("71000000-0000-0000-0000-000000000801")
)
_SOURCE_VERIFIER_REF = certified.PolicyVerifierReference(
    UUID("71000000-0000-0000-0000-000000000802")
)
_T0 = datetime(2026, 9, 20, 12, 0, tzinfo=UTC)
_USD = proprietary_accounts.CurrencyCode("USD")


def _policy(
    *,
    account_id: client_accounts.TradingAccountId = _ACCOUNT,
    policy_ref: client_accounts.AccountPolicyReference = _POLICY_REF,
    snapshot_id: account_policy.AccountPolicySnapshotId = _SNAPSHOT_ID,
    firm_ref: account_policy.PropFirmReference = _FIRM_REF,
    program_ref: account_policy.PropProgramReference = _PROGRAM_REF,
    drawdown_mode: account_policy.DrawdownMode = account_policy.DrawdownMode.TRAILING,
) -> account_policy.AccountPropPolicySnapshot:
    return account_policy.AccountPropPolicySnapshot(
        snapshot_id=snapshot_id,
        policy_ref=policy_ref,
        account_id=account_id,
        account_kind=client_accounts.TradingAccountKind.PROP_FIRM,
        version=account_policy.AccountPolicyVersion(1),
        effective_at=_T0,
        expires_at=None,
        account_size=proprietary_accounts.MoneyAmount(_USD, Decimal("2000")),
        max_drawdown=proprietary_accounts.DrawdownBps(600),
        daily_loss_limit=proprietary_accounts.DrawdownBps(0),
        drawdown_mode=drawdown_mode,
        phase=account_policy.AccountPhase.FUNDED,
        client_profit_split=account_policy.ProfitSplitBps(7000),
        firm_ref=firm_ref,
        program_ref=program_ref,
        rules=(
            account_policy.AccountPolicyRule(
                code="EA_TRADING",
                scope=account_policy.PolicyRuleScope.TRADING,
                disposition=account_policy.PolicyRuleDisposition.ALLOW,
            ),
        ),
    )


def _source(
    *,
    firm_ref: account_policy.PropFirmReference | None = _FIRM_REF,
    program_ref: account_policy.PropProgramReference | None = _PROGRAM_REF,
    verifier_ref: certified.PolicyVerifierReference = _SOURCE_VERIFIER_REF,
    authority: certified.PolicySourceAuthority = (
        certified.PolicySourceAuthority.OFFICIAL_PROVIDER_TERMS
    ),
    certified_at: datetime = _T0 - timedelta(minutes=10),
    valid_until: datetime = _T0 + timedelta(days=30),
    revoked_at: datetime | None = None,
) -> certified.CertifiedPolicySourceEvidence:
    return certified.CertifiedPolicySourceEvidence(
        evidence_id=_SOURCE_ID,
        certificate_id=_SOURCE_CERT_ID,
        verifier_ref=verifier_ref,
        authority=authority,
        locator=certified.PolicySourceLocator(
            "https://provider.example/legal/stellar-instant-rules"
        ),
        content_sha256=certified.Sha256Digest("a" * 64),
        observed_at=_T0 - timedelta(minutes=20),
        certified_at=certified_at,
        valid_until=valid_until,
        firm_ref=firm_ref,
        program_ref=program_ref,
        revoked_at=revoked_at,
    )


def _verifier_registry() -> certified.PolicyVerifierRegistrySnapshot:
    return certified.PolicyVerifierRegistrySnapshot(
        (
            certified.CertifiedPolicyVerifier(
                verifier_ref=_VERIFIER_REF,
                authorized_at=_T0 - timedelta(days=1),
                valid_until=_T0 + timedelta(days=60),
                may_certify_policies=True,
                source_authorities=(),
            ),
            certified.CertifiedPolicyVerifier(
                verifier_ref=_SOURCE_VERIFIER_REF,
                authorized_at=_T0 - timedelta(days=1),
                valid_until=_T0 + timedelta(days=60),
                may_certify_policies=False,
                source_authorities=(
                    certified.PolicySourceAuthority.OFFICIAL_PROVIDER_TERMS,
                ),
            ),
        )
    )


def _certified_policy(
    *,
    policy: account_policy.AccountPropPolicySnapshot | None = None,
    source: certified.CertifiedPolicySourceEvidence | None = None,
    policy_sha256: certified.Sha256Digest | None = None,
    certified_at: datetime = _T0 - timedelta(minutes=5),
    valid_until: datetime = _T0 + timedelta(days=20),
) -> certified.CertifiedAccountPolicy:
    current_policy = _policy() if policy is None else policy
    return certified.CertifiedAccountPolicy(
        certification_id=_POLICY_CERT_ID,
        verifier_ref=_VERIFIER_REF,
        policy=current_policy,
        policy_sha256=(
            certified.derive_account_policy_sha256(current_policy)
            if policy_sha256 is None
            else policy_sha256
        ),
        sources=(_source() if source is None else source,),
        certified_at=certified_at,
        valid_until=valid_until,
    )


def test_policy_digest_is_deterministic_and_content_bound() -> None:
    first = _policy()
    second = _policy()
    changed = _policy(drawdown_mode=account_policy.DrawdownMode.STATIC)

    assert certified.derive_account_policy_sha256(first) == (
        certified.derive_account_policy_sha256(second)
    )
    assert certified.derive_account_policy_sha256(first) != (
        certified.derive_account_policy_sha256(changed)
    )


def test_source_locator_and_certification_time_are_strict() -> None:
    with pytest.raises(certified.CertifiedPolicyValidationError):
        certified.PolicySourceLocator("http://provider.example/rules")
    with pytest.raises(certified.CertifiedPolicyValidationError):
        certified.PolicySourceLocator("https://user:secret@provider.example/rules")
    with pytest.raises(certified.CertifiedPolicyValidationError):
        _source(certified_at=_T0 - timedelta(minutes=30))


def test_certified_policy_rejects_digest_mismatch() -> None:
    with pytest.raises(certified.CertifiedPolicyValidationError):
        _certified_policy(policy_sha256=certified.Sha256Digest("b" * 64))


def test_certified_policy_rejects_wrong_provider_or_program_source() -> None:
    with pytest.raises(certified.CertifiedPolicyValidationError):
        _certified_policy(source=_source(firm_ref=_OTHER_FIRM_REF))
    with pytest.raises(certified.CertifiedPolicyValidationError):
        _certified_policy(source=_source(program_ref=_OTHER_PROGRAM_REF))


def test_certification_cannot_outlive_supporting_source() -> None:
    short_source = _source(valid_until=_T0 + timedelta(days=2))

    with pytest.raises(certified.CertifiedPolicyValidationError):
        _certified_policy(
            source=short_source,
            valid_until=_T0 + timedelta(days=3),
        )


def test_risk_registry_resolves_only_certified_current_policy() -> None:
    certified_policy = _certified_policy()
    registry = certified.CertifiedAccountPolicyRegistrySnapshot(
        (certified_policy,),
        _verifier_registry(),
    )

    resolved = registry.resolve_for_risk(
        account_id=_ACCOUNT,
        policy_ref=_POLICY_REF,
        evaluated_at=_T0,
    )

    assert isinstance(resolved, result.Success)
    assert resolved.value == certified_policy.policy
    assert resolved.value.drawdown_mode is account_policy.DrawdownMode.TRAILING
    assert resolved.value.max_drawdown.logical_values() == (600,)


def test_risk_registry_rejects_raw_uncertified_policy_objects() -> None:
    registry = object.__new__(certified.CertifiedAccountPolicyRegistrySnapshot)
    object.__setattr__(registry, "policies", (_policy(),))
    object.__setattr__(registry, "verifiers", _verifier_registry())

    with pytest.raises(certified.CertifiedPolicyValidationError):
        registry.__post_init__()


def test_risk_registry_fails_closed_for_untrusted_source_verifier() -> None:
    untrusted_ref = certified.PolicyVerifierReference(
        UUID("71000000-0000-0000-0000-000000000803")
    )
    certified_policy = _certified_policy(
        source=_source(verifier_ref=untrusted_ref),
    )
    registry = certified.CertifiedAccountPolicyRegistrySnapshot(
        (certified_policy,),
        _verifier_registry(),
    )

    resolved = registry.resolve_for_risk(
        account_id=_ACCOUNT,
        policy_ref=_POLICY_REF,
        evaluated_at=_T0,
    )

    assert isinstance(resolved, result.Failure)
    assert str(resolved.error) == "policy verifier is not trusted"


def test_risk_registry_enforces_verifier_source_authority_scope() -> None:
    certified_policy = _certified_policy(
        source=_source(
            authority=certified.PolicySourceAuthority.OFFICIAL_PROVIDER_HELP_CENTER,
        ),
    )
    registry = certified.CertifiedAccountPolicyRegistrySnapshot(
        (certified_policy,),
        _verifier_registry(),
    )

    resolved = registry.resolve_for_risk(
        account_id=_ACCOUNT,
        policy_ref=_POLICY_REF,
        evaluated_at=_T0,
    )

    assert isinstance(resolved, result.Failure)
    assert str(resolved.error) == (
        "trusted verifier is not authorized for source authority"
    )


def test_risk_registry_fails_closed_when_source_is_revoked() -> None:
    source = _source(revoked_at=_T0 - timedelta(minutes=1))
    certified_policy = _certified_policy(source=source)
    registry = certified.CertifiedAccountPolicyRegistrySnapshot(
        (certified_policy,),
        _verifier_registry(),
    )

    resolved = registry.resolve_for_risk(
        account_id=_ACCOUNT,
        policy_ref=_POLICY_REF,
        evaluated_at=_T0,
    )

    assert isinstance(resolved, result.Failure)
    assert str(resolved.error) == (
        "certified policy source evidence is stale, revoked or not yet valid"
    )


def test_risk_registry_fails_closed_after_certification_expiry() -> None:
    certified_policy = _certified_policy(
        valid_until=_T0 + timedelta(hours=1),
    )
    registry = certified.CertifiedAccountPolicyRegistrySnapshot(
        (certified_policy,),
        _verifier_registry(),
    )

    resolved = registry.resolve_for_risk(
        account_id=_ACCOUNT,
        policy_ref=_POLICY_REF,
        evaluated_at=_T0 + timedelta(hours=1),
    )

    assert isinstance(resolved, result.Failure)
    assert str(resolved.error) == (
        "certified policy source evidence is stale, revoked or not yet valid"
    )


def test_risk_registry_preserves_underlying_fail_closed_semantics() -> None:
    unresolved_policy = _policy(drawdown_mode=account_policy.DrawdownMode.UNKNOWN)
    certified_policy = _certified_policy(policy=unresolved_policy)
    registry = certified.CertifiedAccountPolicyRegistrySnapshot(
        (certified_policy,),
        _verifier_registry(),
    )

    resolved = registry.resolve_for_risk(
        account_id=_ACCOUNT,
        policy_ref=_POLICY_REF,
        evaluated_at=_T0,
    )

    assert isinstance(resolved, result.Failure)
    assert str(resolved.error) == "mandatory account-policy semantics are unresolved"


def test_risk_registry_rejects_wrong_account_and_missing_policy() -> None:
    registry = certified.CertifiedAccountPolicyRegistrySnapshot(
        (_certified_policy(),),
        _verifier_registry(),
    )

    wrong_account = registry.resolve_for_risk(
        account_id=_OTHER_ACCOUNT,
        policy_ref=_POLICY_REF,
        evaluated_at=_T0,
    )
    missing = registry.resolve_for_risk(
        account_id=_ACCOUNT,
        policy_ref=client_accounts.AccountPolicyReference(
            UUID("71000000-0000-0000-0000-000000000102")
        ),
        evaluated_at=_T0,
    )

    assert isinstance(wrong_account, result.Failure)
    assert str(wrong_account.error) == (
        "certified policy reference belongs to a different account"
    )
    assert isinstance(missing, result.Failure)
    assert str(missing.error) == "certified policy reference not found"
