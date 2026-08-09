from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

import qore.infrastructure.account_policy as account_policy
import qore.infrastructure.client_accounts as client_accounts
import qore.infrastructure.proprietary_accounts as proprietary_accounts
import qore.kernel.result as result

_ACCOUNT = client_accounts.TradingAccountId(
    UUID("32000000-0000-0000-0000-000000000001")
)
_OTHER_ACCOUNT = client_accounts.TradingAccountId(
    UUID("32000000-0000-0000-0000-000000000002")
)
_POLICY_REF = client_accounts.AccountPolicyReference(
    UUID("32000000-0000-0000-0000-000000000101")
)
_OTHER_POLICY_REF = client_accounts.AccountPolicyReference(
    UUID("32000000-0000-0000-0000-000000000102")
)
_SNAPSHOT_ID = account_policy.AccountPolicySnapshotId(
    UUID("32000000-0000-0000-0000-000000000201")
)
_FIRM_REF = account_policy.PropFirmReference(
    UUID("32000000-0000-0000-0000-000000000301")
)
_PROGRAM_REF = account_policy.PropProgramReference(
    UUID("32000000-0000-0000-0000-000000000401")
)
_EFFECTIVE_AT = datetime(2026, 8, 9, 5, 0, tzinfo=UTC)
_USD = proprietary_accounts.CurrencyCode("USD")


def _rule(
    code: str,
    *,
    scope: account_policy.PolicyRuleScope = account_policy.PolicyRuleScope.TRADING,
    disposition: account_policy.PolicyRuleDisposition = (
        account_policy.PolicyRuleDisposition.PROHIBIT
    ),
) -> account_policy.AccountPolicyRule:
    return account_policy.AccountPolicyRule(
        code=code,
        scope=scope,
        disposition=disposition,
    )


def _policy(
    *,
    snapshot_id: account_policy.AccountPolicySnapshotId = _SNAPSHOT_ID,
    policy_ref: client_accounts.AccountPolicyReference = _POLICY_REF,
    account_id: client_accounts.TradingAccountId = _ACCOUNT,
    account_kind: client_accounts.TradingAccountKind = client_accounts.TradingAccountKind.PROP_FIRM,
    version: int = 3,
    effective_at: datetime = _EFFECTIVE_AT,
    expires_at: datetime | None = None,
    account_size: Decimal = Decimal("100000"),
    drawdown_mode: account_policy.DrawdownMode = account_policy.DrawdownMode.STATIC,
    phase: account_policy.AccountPhase = account_policy.AccountPhase.FUNDED,
    firm_ref: account_policy.PropFirmReference | None = _FIRM_REF,
    program_ref: account_policy.PropProgramReference | None = _PROGRAM_REF,
    rules: tuple[account_policy.AccountPolicyRule, ...] = (
        account_policy.AccountPolicyRule(
            code="NEWS_TRADING",
            scope=account_policy.PolicyRuleScope.TRADING,
            disposition=account_policy.PolicyRuleDisposition.PROHIBIT,
        ),
        account_policy.AccountPolicyRule(
            code="PAYOUT_CONFIRMATION",
            scope=account_policy.PolicyRuleScope.PAYOUT,
            disposition=account_policy.PolicyRuleDisposition.REQUIRE,
        ),
    ),
) -> account_policy.AccountPropPolicySnapshot:
    return account_policy.AccountPropPolicySnapshot(
        snapshot_id=snapshot_id,
        policy_ref=policy_ref,
        account_id=account_id,
        account_kind=account_kind,
        version=account_policy.AccountPolicyVersion(version),
        effective_at=effective_at,
        expires_at=expires_at,
        account_size=proprietary_accounts.MoneyAmount(_USD, account_size),
        max_drawdown=proprietary_accounts.DrawdownBps(1000),
        daily_loss_limit=proprietary_accounts.DrawdownBps(500),
        drawdown_mode=drawdown_mode,
        phase=phase,
        client_profit_split=account_policy.ProfitSplitBps(8000),
        firm_ref=firm_ref,
        program_ref=program_ref,
        rules=rules,
    )


def _policy_with_runtime_rules(value: object) -> account_policy.AccountPropPolicySnapshot:
    instance = object.__new__(account_policy.AccountPropPolicySnapshot)
    valid = _policy()
    for field_name in valid.__dataclass_fields__:
        object.__setattr__(instance, field_name, getattr(valid, field_name))
    object.__setattr__(instance, "rules", value)
    return instance


def test_policy_identity_version_and_profit_split_values_are_strict() -> None:
    assert _SNAPSHOT_ID.logical_values() == (
        "32000000-0000-0000-0000-000000000201",
    )
    assert _FIRM_REF.logical_values() == ("32000000-0000-0000-0000-000000000301",)
    assert _PROGRAM_REF.logical_values() == (
        "32000000-0000-0000-0000-000000000401",
    )
    assert account_policy.AccountPolicyVersion(2).logical_values() == (2,)
    assert account_policy.ProfitSplitBps(8000).logical_values() == (8000,)

    with pytest.raises(account_policy.AccountPolicyValidationError):
        account_policy.AccountPolicyVersion(0)
    with pytest.raises(account_policy.AccountPolicyValidationError):
        account_policy.AccountPolicyVersion(True)
    with pytest.raises(account_policy.AccountPolicyValidationError):
        account_policy.ProfitSplitBps(10_001)


def test_policy_rules_are_provider_neutral_typed_and_sorted() -> None:
    payout = _rule(
        "PAYOUT_CONFIRMATION",
        scope=account_policy.PolicyRuleScope.PAYOUT,
        disposition=account_policy.PolicyRuleDisposition.REQUIRE,
    )
    trading = _rule("NEWS_TRADING")
    policy = _policy(rules=(trading, payout))

    assert policy.rules == (payout, trading)
    assert payout.logical_values() == (
        "PAYOUT_CONFIRMATION",
        "payout",
        "require",
    )

    with pytest.raises(account_policy.AccountPolicyValidationError):
        _rule("bad-rule")
    with pytest.raises(account_policy.AccountPolicyValidationError):
        _policy(rules=(trading, trading))


def test_policy_reuses_canonical_money_and_drawdown_contracts() -> None:
    policy = _policy()

    assert isinstance(policy.account_size, proprietary_accounts.MoneyAmount)
    assert isinstance(policy.max_drawdown, proprietary_accounts.DrawdownBps)
    assert isinstance(policy.daily_loss_limit, proprietary_accounts.DrawdownBps)
    assert policy.account_size.logical_values() == ("USD", "100000")
    assert policy.max_drawdown.logical_values() == (1000,)
    assert policy.daily_loss_limit.logical_values() == (500,)
    assert not hasattr(policy, "broker_password")
    assert not hasattr(policy, "execute")
    assert not hasattr(policy, "can_trade")


def test_prop_firm_policy_requires_firm_program_and_applicable_phase() -> None:
    with pytest.raises(account_policy.AccountPolicyValidationError):
        _policy(firm_ref=None)
    with pytest.raises(account_policy.AccountPolicyValidationError):
        _policy(program_ref=None)
    with pytest.raises(account_policy.AccountPolicyValidationError):
        _policy(phase=account_policy.AccountPhase.NOT_APPLICABLE)


def test_brokerage_policy_carries_no_prop_firm_identity() -> None:
    policy = _policy(
        account_kind=client_accounts.TradingAccountKind.BROKERAGE,
        phase=account_policy.AccountPhase.NOT_APPLICABLE,
        firm_ref=None,
        program_ref=None,
    )

    assert policy.account_kind is client_accounts.TradingAccountKind.BROKERAGE
    assert policy.firm_ref is None
    assert policy.program_ref is None
    assert policy.is_complete_for_new_trading()

    with pytest.raises(account_policy.AccountPolicyValidationError):
        _policy(
            account_kind=client_accounts.TradingAccountKind.BROKERAGE,
            phase=account_policy.AccountPhase.NOT_APPLICABLE,
            firm_ref=_FIRM_REF,
            program_ref=None,
        )


def test_unknown_account_policy_is_representable_but_incomplete() -> None:
    policy = _policy(
        account_kind=client_accounts.TradingAccountKind.UNKNOWN,
        drawdown_mode=account_policy.DrawdownMode.UNKNOWN,
        phase=account_policy.AccountPhase.UNKNOWN,
        firm_ref=None,
        program_ref=None,
    )

    assert not policy.is_complete_for_new_trading()

    with pytest.raises(account_policy.AccountPolicyValidationError):
        _policy(
            account_kind=client_accounts.TradingAccountKind.UNKNOWN,
            phase=account_policy.AccountPhase.FUNDED,
            firm_ref=None,
            program_ref=None,
        )


def test_unknown_rule_disposition_fails_policy_completeness() -> None:
    policy = _policy(
        rules=(
            _rule(
                "NEWS_TRADING",
                disposition=account_policy.PolicyRuleDisposition.UNKNOWN,
            ),
        )
    )

    assert not policy.is_complete_for_new_trading()


def test_policy_validates_identity_time_and_account_size_invariants() -> None:
    with pytest.raises(account_policy.AccountPolicyValidationError):
        _policy(snapshot_id=account_policy.AccountPolicySnapshotId(_POLICY_REF.value))
    with pytest.raises(account_policy.AccountPolicyValidationError):
        _policy(effective_at=datetime(2026, 8, 9, 5, 0))
    with pytest.raises(account_policy.AccountPolicyValidationError):
        _policy(expires_at=_EFFECTIVE_AT)
    with pytest.raises(account_policy.AccountPolicyValidationError):
        _policy(account_size=Decimal("0"))


def test_policy_rejects_runtime_non_tuple_rules_without_suppression() -> None:
    invalid = _policy_with_runtime_rules([_rule("NEWS_TRADING")])

    with pytest.raises(account_policy.AccountPolicyValidationError):
        invalid.__post_init__()


def test_registry_rejects_duplicate_policy_reference_or_account() -> None:
    first = _policy()
    duplicate_policy_ref = _policy(
        snapshot_id=account_policy.AccountPolicySnapshotId(
            UUID("32000000-0000-0000-0000-000000000202")
        ),
        account_id=_OTHER_ACCOUNT,
    )
    duplicate_account = _policy(
        snapshot_id=account_policy.AccountPolicySnapshotId(
            UUID("32000000-0000-0000-0000-000000000203")
        ),
        policy_ref=_OTHER_POLICY_REF,
    )

    with pytest.raises(account_policy.AccountPolicyValidationError):
        account_policy.AccountPolicyRegistrySnapshot((first, duplicate_policy_ref))
    with pytest.raises(account_policy.AccountPolicyValidationError):
        account_policy.AccountPolicyRegistrySnapshot((first, duplicate_account))


def test_registry_orders_policies_and_resolves_exact_current_policy() -> None:
    other = _policy(
        snapshot_id=account_policy.AccountPolicySnapshotId(
            UUID("32000000-0000-0000-0000-000000000202")
        ),
        policy_ref=_OTHER_POLICY_REF,
        account_id=_OTHER_ACCOUNT,
    )
    current = _policy()
    registry = account_policy.AccountPolicyRegistrySnapshot((other, current))

    resolved = registry.resolve_for_new_trading(
        account_id=_ACCOUNT,
        policy_ref=_POLICY_REF,
        evaluated_at=_EFFECTIVE_AT,
    )

    assert registry.policies == (current, other)
    assert registry.logical_values() == registry.logical_values()
    assert isinstance(resolved, result.Success)
    assert resolved.value == current


def test_policy_resolution_fails_closed_for_wrong_account_or_missing_reference() -> None:
    registry = account_policy.AccountPolicyRegistrySnapshot((_policy(),))

    wrong_account = registry.resolve_for_new_trading(
        account_id=_OTHER_ACCOUNT,
        policy_ref=_POLICY_REF,
        evaluated_at=_EFFECTIVE_AT,
    )
    missing = registry.resolve_for_new_trading(
        account_id=_ACCOUNT,
        policy_ref=_OTHER_POLICY_REF,
        evaluated_at=_EFFECTIVE_AT,
    )

    assert isinstance(wrong_account, result.Failure)
    assert str(wrong_account.error) == (
        "policy reference belongs to a different trading account"
    )
    assert isinstance(missing, result.Failure)
    assert str(missing.error) == "policy reference not found"


def test_policy_resolution_fails_closed_before_effective_or_after_expiry() -> None:
    expiring = _policy(expires_at=_EFFECTIVE_AT + timedelta(days=30))
    registry = account_policy.AccountPolicyRegistrySnapshot((expiring,))

    before = registry.resolve_for_new_trading(
        account_id=_ACCOUNT,
        policy_ref=_POLICY_REF,
        evaluated_at=_EFFECTIVE_AT - timedelta(microseconds=1),
    )
    expired = registry.resolve_for_new_trading(
        account_id=_ACCOUNT,
        policy_ref=_POLICY_REF,
        evaluated_at=_EFFECTIVE_AT + timedelta(days=30),
    )

    assert isinstance(before, result.Failure)
    assert str(before.error) == "policy is not yet effective"
    assert isinstance(expired, result.Failure)
    assert str(expired.error) == "policy is expired"


def test_policy_resolution_fails_closed_when_mandatory_semantics_are_unknown() -> None:
    unresolved = _policy(
        drawdown_mode=account_policy.DrawdownMode.UNKNOWN,
    )
    registry = account_policy.AccountPolicyRegistrySnapshot((unresolved,))

    resolved = registry.resolve_for_new_trading(
        account_id=_ACCOUNT,
        policy_ref=_POLICY_REF,
        evaluated_at=_EFFECTIVE_AT,
    )

    assert isinstance(resolved, result.Failure)
    assert str(resolved.error) == "mandatory account-policy semantics are unresolved"


def test_policy_resolution_requires_timezone_aware_evaluation_time() -> None:
    registry = account_policy.AccountPolicyRegistrySnapshot((_policy(),))

    resolved = registry.resolve_for_new_trading(
        account_id=_ACCOUNT,
        policy_ref=_POLICY_REF,
        evaluated_at=datetime(2026, 8, 9, 5, 0),
    )

    assert isinstance(resolved, result.Failure)
    assert str(resolved.error) == "policy evaluated_at must be timezone-aware"


def test_policy_readiness_never_grants_trading_authority() -> None:
    policy = _policy()

    assert policy.is_complete_for_new_trading()
    assert not hasattr(policy, "core_decision")
    assert not hasattr(policy, "trading_authority")
    assert not hasattr(policy, "submit_order")
