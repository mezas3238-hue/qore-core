from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid5

from qore.infrastructure.account_policy import (
    AccountPhase,
    AccountPolicyRule,
    AccountPolicySnapshotId,
    AccountPolicyVersion,
    DrawdownMode,
    PolicyRuleDisposition,
    PolicyRuleScope,
    ProfitSplitBps,
    PropFirmReference,
    PropProgramReference,
)
from qore.infrastructure.certified_account_policy import (
    CertifiedAccountPolicy,
    CertifiedAccountPolicyRegistrySnapshot,
    CertifiedPolicySourceEvidence,
    CertifiedPolicyVerifier,
    PolicyCertificationId,
    PolicySourceAuthority,
    PolicySourceCertificateId,
    PolicySourceEvidenceId,
    PolicySourceLocator,
    PolicyVerifierReference,
    PolicyVerifierRegistrySnapshot,
    Sha256Digest,
    derive_account_policy_sha256,
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
from qore.kernel.result import Failure

_SCHEMA = "qore.fundednext.provider-rules-refresh.v3"
_SOURCE_VALIDITY = timedelta(hours=7)
_USD = CurrencyCode("USD")

_FIRM_REF = PropFirmReference(
    uuid5(NAMESPACE_URL, "qore:prop-firm:fundednext")
)
_PROGRAM_REF = PropProgramReference(
    uuid5(NAMESPACE_URL, "qore:prop-program:fundednext:stellar-instant")
)
_POLICY_VERIFIER = PolicyVerifierReference(
    uuid5(NAMESPACE_URL, "qore:verifier:account-policy-normalizer:v1")
)
_SOURCE_VERIFIER = PolicyVerifierReference(
    uuid5(NAMESPACE_URL, "qore:verifier:fundednext-official-help-center:v1")
)


@dataclass(frozen=True, slots=True)
class StellarInstantCertifiedFacts:
    maximum_loss_fraction: Decimal
    cumulative_open_risk_fraction: Decimal
    reclassified_open_risk_fraction: Decimal
    no_daily_loss_limit: bool
    trailing_maximum_loss: bool
    stop_loss_required: bool
    quick_strike_seconds: int
    quick_strike_warning_fraction: Decimal
    quick_strike_limit_fraction: Decimal
    news_window_minutes_each_side: int
    news_profit_attribution_fraction: Decimal
    news_mll_equity_extension_fraction: Decimal
    news_mll_equity_extension_max_uses: int
    ea_allowed_mt5: bool
    ea_strategy_allocation_max_usd: Decimal
    ea_duplicate_strategy_prohibited: bool
    copy_same_owner_stellar_instant_allowed: bool
    copy_cross_fundednext_program_prohibited: bool
    reward_split_tier_1_2: Decimal
    reward_split_tier_3_plus: Decimal
    reward_on_demand_growth_fraction: Decimal
    reward_biweekly_days: int
    reward_min_growth_fraction: Decimal
    reward_eod_gate: bool
    inactivity_calendar_days: int
    consistency_rule_present: bool
    max_purchased_allocation_usd: Decimal
    account_merging_allowed: bool
    max_scaled_allocation_usd: Decimal
    vps_allowed: bool

    def assert_frozen_contract(self) -> None:
        expected = {
            "maximum_loss_fraction": Decimal("0.06"),
            "cumulative_open_risk_fraction": Decimal("0.03"),
            "reclassified_open_risk_fraction": Decimal("0.01"),
            "quick_strike_warning_fraction": Decimal("0.20"),
            "quick_strike_limit_fraction": Decimal("0.30"),
            "news_profit_attribution_fraction": Decimal("0.40"),
            "news_mll_equity_extension_fraction": Decimal("0.01"),
            "reward_split_tier_1_2": Decimal("0.70"),
            "reward_split_tier_3_plus": Decimal("0.80"),
            "reward_on_demand_growth_fraction": Decimal("0.05"),
            "reward_min_growth_fraction": Decimal("0.01"),
            "ea_strategy_allocation_max_usd": Decimal("300000"),
            "max_purchased_allocation_usd": Decimal("20000"),
            "max_scaled_allocation_usd": Decimal("2000000"),
        }
        for name, value in expected.items():
            if getattr(self, name) != value:
                raise ValueError(f"certified FundedNext fact mismatch: {name}")
        if not (
            self.no_daily_loss_limit
            and self.trailing_maximum_loss
            and self.stop_loss_required
            and self.ea_allowed_mt5
            and self.ea_duplicate_strategy_prohibited
            and self.copy_same_owner_stellar_instant_allowed
            and self.copy_cross_fundednext_program_prohibited
            and self.reward_eod_gate
            and self.vps_allowed
        ):
            raise ValueError("required FundedNext boolean rule is not certified")
        if self.consistency_rule_present or self.account_merging_allowed:
            raise ValueError("FundedNext negative rule mismatch")
        if self.quick_strike_seconds != 30:
            raise ValueError("Quick Strike duration mismatch")
        if self.news_window_minutes_each_side != 5:
            raise ValueError("news window mismatch")
        if self.news_mll_equity_extension_max_uses != 3:
            raise ValueError("news MLL extension usage cap mismatch")
        if self.reward_biweekly_days != 14:
            raise ValueError("reward biweekly cadence mismatch")
        if self.inactivity_calendar_days != 30:
            raise ValueError("inactivity rule mismatch")


@dataclass(frozen=True, slots=True)
class CertifiedStellarInstantPolicyBundle:
    policy_registry: CertifiedAccountPolicyRegistrySnapshot
    account_id: TradingAccountId
    policy_ref: AccountPolicyReference
    facts: StellarInstantCertifiedFacts
    observed_at: datetime

    def resolve_for_risk(self, now: datetime):
        return self.policy_registry.resolve_for_risk(
            account_id=self.account_id,
            policy_ref=self.policy_ref,
            evaluated_at=now,
        )


def _aware(value: datetime, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")


def _decimal(facts: dict[str, object], key: str) -> Decimal:
    value = facts.get(key)
    if not isinstance(value, str):
        raise ValueError(f"{key} must be decimal text")
    result = Decimal(value)
    if not result.is_finite():
        raise ValueError(f"{key} must be finite")
    return result


def _int(facts: dict[str, object], key: str) -> int:
    value = facts.get(key)
    if type(value) is not int:
        raise ValueError(f"{key} must be int")
    return value


def _bool(facts: dict[str, object], key: str) -> bool:
    value = facts.get(key)
    if type(value) is not bool:
        raise ValueError(f"{key} must be bool")
    return value


def _facts(payload: dict[str, object]) -> StellarInstantCertifiedFacts:
    raw = payload.get("facts")
    if not isinstance(raw, dict) or any(not isinstance(k, str) for k in raw):
        raise ValueError("FundedNext certified facts missing")
    facts = StellarInstantCertifiedFacts(
        maximum_loss_fraction=_decimal(raw, "maximum_loss_fraction"),
        cumulative_open_risk_fraction=_decimal(raw, "cumulative_open_risk_fraction"),
        reclassified_open_risk_fraction=_decimal(
            raw, "reclassified_open_risk_fraction"
        ),
        no_daily_loss_limit=_bool(raw, "no_daily_loss_limit"),
        trailing_maximum_loss=_bool(raw, "trailing_maximum_loss"),
        stop_loss_required=_bool(raw, "stop_loss_required"),
        quick_strike_seconds=_int(raw, "quick_strike_seconds"),
        quick_strike_warning_fraction=_decimal(
            raw, "quick_strike_warning_fraction"
        ),
        quick_strike_limit_fraction=_decimal(raw, "quick_strike_limit_fraction"),
        news_window_minutes_each_side=_int(raw, "news_window_minutes_each_side"),
        news_profit_attribution_fraction=_decimal(
            raw, "news_profit_attribution_fraction"
        ),
        news_mll_equity_extension_fraction=_decimal(
            raw, "news_mll_equity_extension_fraction"
        ),
        news_mll_equity_extension_max_uses=_int(
            raw, "news_mll_equity_extension_max_uses"
        ),
        ea_allowed_mt5=_bool(raw, "ea_allowed_mt5"),
        ea_strategy_allocation_max_usd=_decimal(
            raw, "ea_strategy_allocation_max_usd"
        ),
        ea_duplicate_strategy_prohibited=_bool(
            raw, "ea_duplicate_strategy_prohibited"
        ),
        copy_same_owner_stellar_instant_allowed=_bool(
            raw, "copy_same_owner_stellar_instant_allowed"
        ),
        copy_cross_fundednext_program_prohibited=_bool(
            raw, "copy_cross_fundednext_program_prohibited"
        ),
        reward_split_tier_1_2=_decimal(raw, "reward_split_tier_1_2"),
        reward_split_tier_3_plus=_decimal(raw, "reward_split_tier_3_plus"),
        reward_on_demand_growth_fraction=_decimal(
            raw, "reward_on_demand_growth_fraction"
        ),
        reward_biweekly_days=_int(raw, "reward_biweekly_days"),
        reward_min_growth_fraction=_decimal(raw, "reward_min_growth_fraction"),
        reward_eod_gate=_bool(raw, "reward_eod_gate"),
        inactivity_calendar_days=_int(raw, "inactivity_calendar_days"),
        consistency_rule_present=_bool(raw, "consistency_rule_present"),
        max_purchased_allocation_usd=_decimal(
            raw, "max_purchased_allocation_usd"
        ),
        account_merging_allowed=_bool(raw, "account_merging_allowed"),
        max_scaled_allocation_usd=_decimal(raw, "max_scaled_allocation_usd"),
        vps_allowed=_bool(raw, "vps_allowed"),
    )
    facts.assert_frozen_contract()
    return facts


def _id(label: str, material: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"qore:{label}:{material}")


def load_certified_stellar_instant_policy(
    *,
    refresh_path: Path,
    account_binding_id: str,
    account_size: Decimal,
) -> CertifiedStellarInstantPolicyBundle:
    if len(account_binding_id) != 64:
        raise ValueError("account binding id must be SHA-256 text")
    payload = json.loads(refresh_path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict) or payload.get("schema") != _SCHEMA:
        raise ValueError("FundedNext certified policy schema mismatch")
    observed_raw = payload.get("observed_at")
    if not isinstance(observed_raw, str):
        raise ValueError("FundedNext certified policy observed_at missing")
    observed_at = datetime.fromisoformat(observed_raw)
    _aware(observed_at, "observed_at")
    valid_until = observed_at + _SOURCE_VALIDITY
    facts = _facts(payload)

    sources_raw = payload.get("sources")
    if not isinstance(sources_raw, dict) or not sources_raw:
        raise ValueError("FundedNext certified policy sources missing")

    source_evidence: list[CertifiedPolicySourceEvidence] = []
    for name in sorted(sources_raw):
        value = sources_raw[name]
        if not isinstance(name, str) or not isinstance(value, dict):
            raise ValueError("FundedNext source entry invalid")
        url = value.get("url")
        digest = value.get("sha256")
        if not isinstance(url, str) or not isinstance(digest, str):
            raise ValueError("FundedNext source URL/hash missing")
        material = f"{name}:{url}:{digest}"
        source_evidence.append(
            CertifiedPolicySourceEvidence(
                evidence_id=PolicySourceEvidenceId(_id("source-evidence", material)),
                certificate_id=PolicySourceCertificateId(
                    _id("source-certificate", material)
                ),
                verifier_ref=_SOURCE_VERIFIER,
                authority=PolicySourceAuthority.OFFICIAL_PROVIDER_HELP_CENTER,
                locator=PolicySourceLocator(url),
                content_sha256=Sha256Digest(digest),
                observed_at=observed_at,
                certified_at=observed_at,
                valid_until=valid_until,
                firm_ref=_FIRM_REF,
                program_ref=_PROGRAM_REF,
            )
        )

    account_id = TradingAccountId(_id("trading-account", account_binding_id))
    policy_ref = AccountPolicyReference(_id("account-policy", account_binding_id))
    snapshot_id = AccountPolicySnapshotId(
        _id("account-policy-snapshot", f"{account_binding_id}:{observed_at.isoformat()}")
    )
    policy = __import__(
        "qore.infrastructure.account_policy",
        fromlist=["AccountPropPolicySnapshot"],
    ).AccountPropPolicySnapshot(
        snapshot_id=snapshot_id,
        policy_ref=policy_ref,
        account_id=account_id,
        account_kind=TradingAccountKind.PROP_FIRM,
        version=AccountPolicyVersion(1),
        effective_at=observed_at,
        expires_at=valid_until,
        account_size=MoneyAmount(_USD, account_size),
        max_drawdown=DrawdownBps(600),
        daily_loss_limit=DrawdownBps(0),
        drawdown_mode=DrawdownMode.TRAILING,
        phase=AccountPhase.FUNDED,
        client_profit_split=ProfitSplitBps(7000),
        firm_ref=_FIRM_REF,
        program_ref=_PROGRAM_REF,
        rules=(
            AccountPolicyRule(
                code="EA_TRADING",
                scope=PolicyRuleScope.TRADING,
                disposition=PolicyRuleDisposition.ALLOW,
            ),
            AccountPolicyRule(
                code="STOP_LOSS_REQUIRED",
                scope=PolicyRuleScope.TRADING,
                disposition=PolicyRuleDisposition.REQUIRE,
            ),
            AccountPolicyRule(
                code="NEWS_TRADING",
                scope=PolicyRuleScope.TRADING,
                disposition=PolicyRuleDisposition.ALLOW,
            ),
            AccountPolicyRule(
                code="COPY_SAME_OWNER_INSTANT",
                scope=PolicyRuleScope.TRADING,
                disposition=PolicyRuleDisposition.ALLOW,
            ),
            AccountPolicyRule(
                code="COPY_CROSS_PROGRAM",
                scope=PolicyRuleScope.TRADING,
                disposition=PolicyRuleDisposition.PROHIBIT,
            ),
            AccountPolicyRule(
                code="ACCOUNT_MERGING",
                scope=PolicyRuleScope.TRADING,
                disposition=PolicyRuleDisposition.PROHIBIT,
            ),
            AccountPolicyRule(
                code="EXPLOIT_STRATEGIES",
                scope=PolicyRuleScope.TRADING,
                disposition=PolicyRuleDisposition.PROHIBIT,
            ),
            AccountPolicyRule(
                code="PAYOUT_ELIGIBILITY",
                scope=PolicyRuleScope.PAYOUT,
                disposition=PolicyRuleDisposition.REQUIRE,
            ),
            AccountPolicyRule(
                code="NEWS_PROFIT_ATTRIBUTION",
                scope=PolicyRuleScope.PAYOUT,
                disposition=PolicyRuleDisposition.REQUIRE,
            ),
            AccountPolicyRule(
                code="QUICK_STRIKE_REVIEW",
                scope=PolicyRuleScope.PAYOUT,
                disposition=PolicyRuleDisposition.REQUIRE,
            ),
        ),
    )
    certified = CertifiedAccountPolicy(
        certification_id=PolicyCertificationId(
            _id("policy-certification", f"{account_binding_id}:{observed_at.isoformat()}")
        ),
        verifier_ref=_POLICY_VERIFIER,
        policy=policy,
        policy_sha256=derive_account_policy_sha256(policy),
        sources=tuple(source_evidence),
        certified_at=observed_at,
        valid_until=valid_until,
    )
    verifier_registry = PolicyVerifierRegistrySnapshot(
        (
            CertifiedPolicyVerifier(
                verifier_ref=_POLICY_VERIFIER,
                authorized_at=datetime(2026, 9, 20, tzinfo=UTC),
                valid_until=datetime(2036, 9, 20, tzinfo=UTC),
                may_certify_policies=True,
                source_authorities=(),
            ),
            CertifiedPolicyVerifier(
                verifier_ref=_SOURCE_VERIFIER,
                authorized_at=datetime(2026, 9, 20, tzinfo=UTC),
                valid_until=datetime(2036, 9, 20, tzinfo=UTC),
                may_certify_policies=False,
                source_authorities=(
                    PolicySourceAuthority.OFFICIAL_PROVIDER_HELP_CENTER,
                ),
            ),
        )
    )
    registry = CertifiedAccountPolicyRegistrySnapshot(
        (certified,),
        verifier_registry,
    )
    resolved = registry.resolve_for_risk(
        account_id=account_id,
        policy_ref=policy_ref,
        evaluated_at=observed_at,
    )
    if isinstance(resolved, Failure):
        raise ValueError(f"certified FundedNext policy rejected: {resolved.error}")
    return CertifiedStellarInstantPolicyBundle(
        policy_registry=registry,
        account_id=account_id,
        policy_ref=policy_ref,
        facts=facts,
        observed_at=observed_at,
    )
