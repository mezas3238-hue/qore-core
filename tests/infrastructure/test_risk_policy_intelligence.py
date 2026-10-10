from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from qore.infrastructure.account_policy import (
    AccountPhase,
    AccountPolicyRule,
    AccountPolicySnapshotId,
    AccountPolicyVersion,
    AccountPropPolicySnapshot,
    DrawdownMode,
    PolicyRuleDisposition,
    PolicyRuleScope,
    ProfitSplitBps,
    PropFirmReference,
    PropProgramReference,
)
from qore.infrastructure.client_accounts import (
    AccountPolicyReference,
    TradingAccountId,
    TradingAccountKind,
)
from qore.infrastructure.proprietary_accounts import (
    CurrencyCode,
    DrawdownBps,
    MoneyAmount,
)
from qore.infrastructure.risk_authority import RiskFingerprint, compute_fingerprint
from qore.infrastructure.risk_policy_intelligence import (
    AdmittedPolicyRule,
    CandidatePolicyRule,
    PolicyAuthorityRank,
    PolicyChangeVerdict,
    PolicyRuleParameter,
    PolicySourceKind,
    PolicySourceObservation,
    RiskPolicyIntelligenceError,
    RiskPolicyIntelligenceResolutionError,
    RiskPolicyIntelligenceValidationError,
    RuleCode,
    admit_policy_rules,
    authority_rank_for_kind,
    compose_policy_snapshot,
    compute_policy_fingerprint,
    detect_policy_change,
    detect_rule_set_change,
)
from qore.kernel.result import Failure, Result, Success

_NOW = datetime(2026, 8, 9, 5, 0, tzinfo=UTC)
_USD = CurrencyCode("USD")

_OBS_ID = UUID("41000000-0000-0000-0000-000000000001")
_RULE_ID = UUID("41000000-0000-0000-0000-000000000101")
_RULE_ID_2 = UUID("41000000-0000-0000-0000-000000000102")
_RULE_ID_3 = UUID("41000000-0000-0000-0000-000000000103")
_SNAPSHOT_ID = AccountPolicySnapshotId(UUID("41000000-0000-0000-0000-000000000201"))
_SNAPSHOT_ID_2 = AccountPolicySnapshotId(UUID("41000000-0000-0000-0000-000000000202"))
_POLICY_REF = AccountPolicyReference(UUID("41000000-0000-0000-0000-000000000301"))
_ACCOUNT_ID = TradingAccountId(UUID("41000000-0000-0000-0000-000000000401"))
_FIRM_REF = PropFirmReference(UUID("41000000-0000-0000-0000-000000000501"))
_PROGRAM_REF = PropProgramReference(UUID("41000000-0000-0000-0000-000000000601"))


def _fp(*parts: object) -> RiskFingerprint:
    return compute_fingerprint(*parts)


def _param(name: str, value: str, unit: str | None = None) -> PolicyRuleParameter:
    return PolicyRuleParameter(name=name, value=value, unit=unit)


def _source(
    *,
    kind: PolicySourceKind = PolicySourceKind.PLATFORM_API,
    version: int = 1,
    content: str = "base",
    observed_at: datetime = _NOW,
    observation_id: UUID = _OBS_ID,
) -> PolicySourceObservation:
    return PolicySourceObservation(
        observation_id=observation_id,
        kind=kind,
        rank=authority_rank_for_kind(kind),
        version=version,
        fingerprint=_fp("source", content),
        content_digest=_fp("content", content),
        observed_at=observed_at,
        descriptor=None,
    )


def _candidate(
    *,
    code: RuleCode = RuleCode.DAILY_RESET_TIMEZONE,
    scope: PolicyRuleScope = PolicyRuleScope.TRADING,
    disposition: PolicyRuleDisposition = PolicyRuleDisposition.REQUIRE,
    parameters: tuple[PolicyRuleParameter, ...] = (),
    source: PolicySourceObservation | None = None,
    mandatory: bool = False,
    rule_id: UUID = _RULE_ID,
) -> CandidatePolicyRule:
    return CandidatePolicyRule(
        rule_id=rule_id,
        code=code,
        scope=scope,
        disposition=disposition,
        parameters=parameters,
        source=source if source is not None else _source(),
        mandatory=mandatory,
    )


def _admitted(
    *,
    code: RuleCode = RuleCode.DAILY_RESET_TIMEZONE,
    scope: PolicyRuleScope = PolicyRuleScope.TRADING,
    disposition: PolicyRuleDisposition = PolicyRuleDisposition.REQUIRE,
    parameters: tuple[PolicyRuleParameter, ...] = (),
    source: PolicySourceObservation | None = None,
    rule_id: UUID = _RULE_ID,
) -> AdmittedPolicyRule:
    return AdmittedPolicyRule(
        rule_id=rule_id,
        code=code,
        scope=scope,
        disposition=disposition,
        parameters=parameters,
        source=source if source is not None else _source(),
    )


def _snapshot(
    *,
    snapshot_id: AccountPolicySnapshotId = _SNAPSHOT_ID,
    version: int = 3,
    effective_at: datetime = _NOW,
    expires_at: datetime | None = None,
    drawdown_mode: DrawdownMode = DrawdownMode.STATIC,
    phase: AccountPhase = AccountPhase.FUNDED,
    rules: tuple[AccountPolicyRule, ...] = (),
) -> AccountPropPolicySnapshot:
    return AccountPropPolicySnapshot(
        snapshot_id=snapshot_id,
        policy_ref=_POLICY_REF,
        account_id=_ACCOUNT_ID,
        account_kind=TradingAccountKind.PROP_FIRM,
        version=AccountPolicyVersion(version),
        effective_at=effective_at,
        expires_at=expires_at,
        account_size=MoneyAmount(_USD, Decimal("100000")),
        max_drawdown=DrawdownBps(1000),
        daily_loss_limit=DrawdownBps(500),
        drawdown_mode=drawdown_mode,
        phase=phase,
        client_profit_split=ProfitSplitBps(8000),
        firm_ref=_FIRM_REF,
        program_ref=_PROGRAM_REF,
        rules=rules,
    )


def _compose(
    *,
    account_kind: TradingAccountKind = TradingAccountKind.PROP_FIRM,
    phase: AccountPhase = AccountPhase.FUNDED,
    firm_ref: PropFirmReference | None = _FIRM_REF,
    program_ref: PropProgramReference | None = _PROGRAM_REF,
    drawdown_mode: DrawdownMode = DrawdownMode.STATIC,
    admitted_rules: tuple[AdmittedPolicyRule, ...] = (),
) -> Result[AccountPropPolicySnapshot, RiskPolicyIntelligenceError]:
    return compose_policy_snapshot(
        snapshot_id=_SNAPSHOT_ID,
        policy_ref=_POLICY_REF,
        account_id=_ACCOUNT_ID,
        account_kind=account_kind,
        version=AccountPolicyVersion(3),
        effective_at=_NOW,
        expires_at=None,
        account_size=MoneyAmount(_USD, Decimal("100000")),
        max_drawdown=DrawdownBps(1000),
        daily_loss_limit=DrawdownBps(500),
        drawdown_mode=drawdown_mode,
        phase=phase,
        client_profit_split=ProfitSplitBps(8000),
        firm_ref=firm_ref,
        program_ref=program_ref,
        admitted_rules=admitted_rules,
    )


def test_authority_rank_for_kind_maps_all_kinds() -> None:
    assert authority_rank_for_kind(PolicySourceKind.PLATFORM_API) is (
        PolicyAuthorityRank.PLATFORM_API
    )
    assert authority_rank_for_kind(PolicySourceKind.ACCOUNT_METADATA) is (
        PolicyAuthorityRank.ACCOUNT_METADATA
    )
    assert authority_rank_for_kind(PolicySourceKind.VERSIONED_RULE_DOCUMENT) is (
        PolicyAuthorityRank.VERSIONED_RULE_DOCUMENT
    )
    assert authority_rank_for_kind(PolicySourceKind.FIRM_WEBSITE) is (
        PolicyAuthorityRank.FIRM_WEBSITE
    )
    assert authority_rank_for_kind(PolicySourceKind.UNRESOLVED) is (
        PolicyAuthorityRank.UNRESOLVED
    )


def test_compute_policy_fingerprint_is_deterministic() -> None:
    left = compute_policy_fingerprint("daily_loss_limit", "5", "percent")
    right = compute_policy_fingerprint("daily_loss_limit", "5", "percent")
    other = compute_policy_fingerprint("daily_loss_limit", "10", "percent")

    assert left == right
    assert left != other


def test_untrusted_source_admission_is_rejected() -> None:
    candidate = _candidate(source=_source(kind=PolicySourceKind.UNRESOLVED))
    result = admit_policy_rules((candidate,), observed_at=_NOW)

    assert isinstance(result, Failure)
    assert isinstance(result.error, RiskPolicyIntelligenceResolutionError)


def test_firm_website_is_authoritative_lowest_rank() -> None:
    candidate = _candidate(source=_source(kind=PolicySourceKind.FIRM_WEBSITE))
    result = admit_policy_rules((candidate,), observed_at=_NOW)

    assert isinstance(result, Success)
    assert result.value[0].source.rank is PolicyAuthorityRank.FIRM_WEBSITE


def test_conflicting_authoritative_sources_fail_closed() -> None:
    prohibit = _candidate(
        code=RuleCode.NEWS_RESTRICTION,
        disposition=PolicyRuleDisposition.PROHIBIT,
    )
    require = _candidate(
        code=RuleCode.NEWS_RESTRICTION,
        disposition=PolicyRuleDisposition.REQUIRE,
        rule_id=_RULE_ID_2,
    )
    conflict = admit_policy_rules((prohibit, require), observed_at=_NOW)
    assert isinstance(conflict, Failure)
    assert isinstance(conflict.error, RiskPolicyIntelligenceResolutionError)

    five = _candidate(
        code=RuleCode.MAX_QUANTITY,
        parameters=(_param("quantity", "5", "lots"),),
    )
    ten = _candidate(
        code=RuleCode.MAX_QUANTITY,
        parameters=(_param("quantity", "10", "lots"),),
        rule_id=_RULE_ID_2,
    )
    param_conflict = admit_policy_rules((five, ten), observed_at=_NOW)
    assert isinstance(param_conflict, Failure)
    assert isinstance(param_conflict.error, RiskPolicyIntelligenceResolutionError)


def test_unknown_disposition_and_ambiguous_mandatory_fail_closed() -> None:
    unknown = _candidate(disposition=PolicyRuleDisposition.UNKNOWN)
    assert isinstance(admit_policy_rules((unknown,), observed_at=_NOW), Failure)

    empty_mandatory = _candidate(mandatory=True, parameters=())
    assert isinstance(admit_policy_rules((empty_mandatory,), observed_at=_NOW), Failure)

    conflicting_mandatory = _candidate(
        mandatory=True,
        parameters=(_param("window", "5", "min"), _param("window", "10", "min")),
    )
    assert isinstance(admit_policy_rules((conflicting_mandatory,), observed_at=_NOW), Failure)


def test_admission_deduplicates_agreeing_candidates_and_orders_by_rule_id() -> None:
    big = _candidate(code=RuleCode.MAX_QUANTITY, rule_id=_RULE_ID_2)
    small = _candidate(code=RuleCode.MAX_QUANTITY, rule_id=_RULE_ID)

    result = admit_policy_rules((big, small), observed_at=_NOW)

    assert isinstance(result, Success)
    assert len(result.value) == 1
    assert result.value[0].rule_id == _RULE_ID


def test_admission_orders_admitted_rules_by_rule_id() -> None:
    big = _candidate(code=RuleCode.MAX_QUANTITY, rule_id=_RULE_ID_2)
    small = _candidate(code=RuleCode.NEWS_RESTRICTION, rule_id=_RULE_ID)

    result = admit_policy_rules((big, small), observed_at=_NOW)

    assert isinstance(result, Success)
    assert [rule.code for rule in result.value] == [
        RuleCode.NEWS_RESTRICTION,
        RuleCode.MAX_QUANTITY,
    ]


def test_admitted_rule_maps_to_account_policy_rule() -> None:
    admitted = _admitted(
        code=RuleCode.DAILY_RESET_TIMEZONE,
        scope=PolicyRuleScope.TRADING,
        disposition=PolicyRuleDisposition.REQUIRE,
    )

    mapped = admitted.to_account_policy_rule()

    assert isinstance(mapped, AccountPolicyRule)
    assert mapped.code == "DAILY_RESET_TIMEZONE"
    assert mapped.scope is PolicyRuleScope.TRADING
    assert mapped.disposition is PolicyRuleDisposition.REQUIRE


def test_compose_produces_valid_snapshot_with_mapped_rules_and_ordering() -> None:
    news = _candidate(
        code=RuleCode.NEWS_RESTRICTION,
        disposition=PolicyRuleDisposition.PROHIBIT,
    )
    payout = _candidate(
        code=RuleCode.PAYOUT_CONSTRAINT,
        scope=PolicyRuleScope.PAYOUT,
        disposition=PolicyRuleDisposition.REQUIRE,
        rule_id=_RULE_ID_2,
    )
    admitted_result = admit_policy_rules((news, payout), observed_at=_NOW)
    assert isinstance(admitted_result, Success)

    result = _compose(admitted_rules=admitted_result.value)

    assert isinstance(result, Success)
    snapshot = result.value
    assert isinstance(snapshot, AccountPropPolicySnapshot)
    assert all(isinstance(rule, AccountPolicyRule) for rule in snapshot.rules)
    assert [rule.code for rule in snapshot.rules] == [
        "PAYOUT_CONSTRAINT",
        "NEWS_RESTRICTION",
    ]
    assert snapshot.rules[0].scope is PolicyRuleScope.PAYOUT
    assert snapshot.rules[1].disposition is PolicyRuleDisposition.PROHIBIT


def test_compose_fails_closed_on_account_program_phase_mismatch() -> None:
    missing_firm = _compose(firm_ref=None)
    assert isinstance(missing_firm, Failure)

    not_applicable = _compose(phase=AccountPhase.NOT_APPLICABLE)
    assert isinstance(not_applicable, Failure)

    brokerage_with_firm = _compose(
        account_kind=TradingAccountKind.BROKERAGE,
        phase=AccountPhase.NOT_APPLICABLE,
        program_ref=None,
    )
    assert isinstance(brokerage_with_firm, Failure)


def test_compose_fails_closed_on_duplicate_mapped_rule_codes() -> None:
    first = _admitted(code=RuleCode.MAX_QUANTITY, rule_id=_RULE_ID)
    second = _admitted(code=RuleCode.MAX_QUANTITY, rule_id=_RULE_ID_2)

    result = _compose(admitted_rules=(first, second))

    assert isinstance(result, Failure)
    assert isinstance(result.error, RiskPolicyIntelligenceResolutionError)


def test_detect_policy_change_with_no_prior_snapshot_is_changed() -> None:
    result = detect_policy_change(None, _snapshot(), evaluated_at=_NOW)

    assert isinstance(result, Success)
    assert result.value is PolicyChangeVerdict.CHANGED


def test_unchanged_equivalent_content_is_unchanged() -> None:
    current = _snapshot(snapshot_id=_SNAPSHOT_ID, version=3)
    candidate = _snapshot(snapshot_id=_SNAPSHOT_ID_2, version=4)

    result = detect_policy_change(current, candidate, evaluated_at=_NOW)

    assert isinstance(result, Success)
    assert result.value is PolicyChangeVerdict.UNCHANGED


def test_effective_and_expiry_boundary_changes_are_detected() -> None:
    base = _snapshot()

    later_effective = _snapshot(effective_at=_NOW + timedelta(hours=1))
    effective_result = detect_policy_change(base, later_effective, evaluated_at=_NOW)
    assert isinstance(effective_result, Success)
    assert effective_result.value is PolicyChangeVerdict.CHANGED

    expiring = _snapshot(expires_at=_NOW + timedelta(days=30))
    expiry_result = detect_policy_change(base, expiring, evaluated_at=_NOW)
    assert isinstance(expiry_result, Success)
    assert expiry_result.value is PolicyChangeVerdict.CHANGED


def test_changed_drawdown_mode_is_detected() -> None:
    static = _snapshot(drawdown_mode=DrawdownMode.STATIC)
    trailing = _snapshot(drawdown_mode=DrawdownMode.TRAILING)

    result = detect_policy_change(static, trailing, evaluated_at=_NOW)

    assert isinstance(result, Success)
    assert result.value is PolicyChangeVerdict.CHANGED


def test_source_version_change_is_detected_as_changed() -> None:
    prior = _admitted(source=_source(version=1))
    candidate = _admitted(source=_source(version=2))

    result = detect_rule_set_change((prior,), (candidate,), evaluated_at=_NOW)

    assert isinstance(result, Success)
    assert result.value is PolicyChangeVerdict.CHANGED


def test_semantic_rule_change_with_same_label_is_detected() -> None:
    prior = _admitted(
        code=RuleCode.MAX_QUANTITY,
        disposition=PolicyRuleDisposition.ALLOW,
        parameters=(_param("quantity", "5", "lots"),),
    )
    candidate = _admitted(
        code=RuleCode.MAX_QUANTITY,
        disposition=PolicyRuleDisposition.ALLOW,
        parameters=(_param("quantity", "10", "lots"),),
    )

    result = detect_rule_set_change((prior,), (candidate,), evaluated_at=_NOW)

    assert isinstance(result, Success)
    assert result.value is PolicyChangeVerdict.CHANGED


def test_changed_reset_timezone_parameter_is_detected() -> None:
    prior = _admitted(
        code=RuleCode.DAILY_RESET_TIMEZONE,
        parameters=(_param("timezone", "UTC"),),
    )
    candidate = _admitted(
        code=RuleCode.DAILY_RESET_TIMEZONE,
        parameters=(_param("timezone", "America/New_York"),),
    )

    result = detect_rule_set_change((prior,), (candidate,), evaluated_at=_NOW)

    assert isinstance(result, Success)
    assert result.value is PolicyChangeVerdict.CHANGED


def test_changed_drawdown_mode_parameter_is_detected() -> None:
    prior = _admitted(
        code=RuleCode.DRAWDOWN_MODE,
        parameters=(_param("mode", "static"),),
    )
    candidate = _admitted(
        code=RuleCode.DRAWDOWN_MODE,
        parameters=(_param("mode", "trailing"),),
    )

    result = detect_rule_set_change((prior,), (candidate,), evaluated_at=_NOW)

    assert isinstance(result, Success)
    assert result.value is PolicyChangeVerdict.CHANGED


def test_equivalent_rule_sets_are_unchanged() -> None:
    prior = _admitted(
        code=RuleCode.DAILY_RESET_TIMEZONE,
        parameters=(_param("timezone", "UTC"),),
    )
    candidate = _admitted(
        code=RuleCode.DAILY_RESET_TIMEZONE,
        parameters=(_param("timezone", "UTC"),),
    )

    result = detect_rule_set_change((prior,), (candidate,), evaluated_at=_NOW)

    assert isinstance(result, Success)
    assert result.value is PolicyChangeVerdict.UNCHANGED


def test_exact_type_validation_rejects_bool_as_int() -> None:
    with pytest.raises(RiskPolicyIntelligenceValidationError):
        PolicySourceObservation(
            observation_id=_OBS_ID,
            kind=PolicySourceKind.PLATFORM_API,
            rank=PolicyAuthorityRank.PLATFORM_API,
            version=True,
            fingerprint=_fp("f"),
            content_digest=_fp("c"),
            observed_at=_NOW,
            descriptor=None,
        )


def test_exact_type_validation_rejects_timezone_naive_datetime() -> None:
    naive = datetime(2026, 8, 9, 5, 0)

    with pytest.raises(RiskPolicyIntelligenceValidationError):
        PolicySourceObservation(
            observation_id=_OBS_ID,
            kind=PolicySourceKind.PLATFORM_API,
            rank=PolicyAuthorityRank.PLATFORM_API,
            version=1,
            fingerprint=_fp("f"),
            content_digest=_fp("c"),
            observed_at=naive,
            descriptor=None,
        )

    assert isinstance(admit_policy_rules((_candidate(),), observed_at=naive), Failure)
    assert isinstance(
        detect_policy_change(_snapshot(), _snapshot(), evaluated_at=naive), Failure
    )
    assert isinstance(detect_rule_set_change((), (), evaluated_at=naive), Failure)
