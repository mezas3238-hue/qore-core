"""DEMO risk/policy intelligence: source-aware, deterministic policy admission.

This is the L2 engineering lane of the QORE Core DEMO Risk/Policy authority. It
turns raw, source-tagged candidate rules into a deterministic admitted rule set
and composes the existing
:class:`qore.infrastructure.account_policy.AccountPropPolicySnapshot` contract.

It creates no Production or LIVE authority, no real-capital authority, and no
provider credentials. Everything here is deterministic and fail-closed:

* no ambient clock (every timestamp is caller-supplied and timezone-aware);
* no ambient UUID generation (every identity is caller-supplied);
* exact runtime types (``type(x) is int`` rejects ``bool``);
* missing, stale, ambiguous or conflicting state never admits.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from re import fullmatch
from uuid import UUID

from qore.infrastructure.account_policy import (
    AccountPhase,
    AccountPolicyRule,
    AccountPolicySnapshotId,
    AccountPolicyValidationError,
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
from qore.infrastructure.ports import ExternalSourceDescriptor
from qore.infrastructure.proprietary_accounts import DrawdownBps, MoneyAmount
from qore.infrastructure.risk_authority import RiskError, RiskFingerprint, compute_fingerprint
from qore.kernel.result import Failure, Result, Success

__all__ = [
    "PolicySourceKind",
    "PolicyAuthorityRank",
    "RuleCode",
    "PolicyChangeVerdict",
    "PolicyRuleParameter",
    "PolicySourceObservation",
    "CandidatePolicyRule",
    "AdmittedPolicyRule",
    "RiskPolicyIntelligenceError",
    "RiskPolicyIntelligenceValidationError",
    "RiskPolicyIntelligenceResolutionError",
    "authority_rank_for_kind",
    "compute_policy_fingerprint",
    "admit_policy_rules",
    "compose_policy_snapshot",
    "detect_policy_change",
    "detect_rule_set_change",
]


class PolicySourceKind(StrEnum):
    """Closed classification of where one policy observation came from."""

    PLATFORM_API = "platform_api"
    ACCOUNT_METADATA = "account_metadata"
    VERSIONED_RULE_DOCUMENT = "versioned_rule_document"
    FIRM_WEBSITE = "firm_website"
    UNRESOLVED = "unresolved"


class PolicyAuthorityRank(StrEnum):
    """Authority ordering (high to low). UNRESOLVED is never authoritative."""

    PLATFORM_API = "platform_api"
    ACCOUNT_METADATA = "account_metadata"
    VERSIONED_RULE_DOCUMENT = "versioned_rule_document"
    FIRM_WEBSITE = "firm_website"
    UNRESOLVED = "unresolved"


class RuleCode(StrEnum):
    """Canonical uppercase rule families (provider-neutral)."""

    DAILY_LOSS_LIMIT = "DAILY_LOSS_LIMIT"
    DAILY_RESET_TIMEZONE = "DAILY_RESET_TIMEZONE"
    MAX_DRAWDOWN = "MAX_DRAWDOWN"
    DRAWDOWN_MODE = "DRAWDOWN_MODE"
    EQUITY_INCLUSION = "EQUITY_INCLUSION"
    MAX_QUANTITY = "MAX_QUANTITY"
    MAX_NOTIONAL = "MAX_NOTIONAL"
    INSTRUMENT_ALLOW = "INSTRUMENT_ALLOW"
    INSTRUMENT_DENY = "INSTRUMENT_DENY"
    SESSION_HOURS = "SESSION_HOURS"
    OVERNIGHT_HOLD = "OVERNIGHT_HOLD"
    WEEKEND_HOLD = "WEEKEND_HOLD"
    NEWS_RESTRICTION = "NEWS_RESTRICTION"
    MANDATORY_STOP_LOSS = "MANDATORY_STOP_LOSS"
    CONCENTRATION_LIMIT = "CONCENTRATION_LIMIT"
    MAX_LOSS_PER_TRADE = "MAX_LOSS_PER_TRADE"
    PHASE_RULE = "PHASE_RULE"
    CONSISTENCY_RULE = "CONSISTENCY_RULE"
    AUTOMATION_RESTRICTION = "AUTOMATION_RESTRICTION"
    CLOSE_BEFORE_TIME = "CLOSE_BEFORE_TIME"
    PAYOUT_CONSTRAINT = "PAYOUT_CONSTRAINT"


class PolicyChangeVerdict(StrEnum):
    """Deterministic verdict when comparing two policy surfaces."""

    UNCHANGED = "unchanged"
    CHANGED = "changed"
    AMBIGUOUS = "ambiguous"


class RiskPolicyIntelligenceError(RiskError):
    """Base error for the risk/policy intelligence lane."""

    __slots__ = ()


class RiskPolicyIntelligenceValidationError(RiskPolicyIntelligenceError):
    """Violation of a risk/policy-intelligence invariant."""

    __slots__ = ()


class RiskPolicyIntelligenceResolutionError(RiskPolicyIntelligenceError):
    """Candidate policy state cannot be resolved safely."""

    __slots__ = ()


def _validate_uuid(value: UUID, *, field_name: str) -> None:
    if not isinstance(value, UUID):
        raise RiskPolicyIntelligenceValidationError(f"{field_name} must be a UUID")


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise RiskPolicyIntelligenceValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise RiskPolicyIntelligenceValidationError(f"{field_name} must be timezone-aware")


def _validate_positive_int(value: int, *, field_name: str) -> None:
    if type(value) is not int or value <= 0:
        raise RiskPolicyIntelligenceValidationError(f"{field_name} must be a positive integer")


_PARAMETER_NAME_RE = r"[a-z][a-z0-9_]*"


def _parameter_key(parameter: PolicyRuleParameter) -> tuple[str, str, str]:
    return (parameter.name, parameter.value, parameter.unit if parameter.unit is not None else "")


def _parameter_tuple(
    parameters: tuple[PolicyRuleParameter, ...],
) -> tuple[tuple[str, str, str], ...]:
    return tuple(_parameter_key(parameter) for parameter in parameters)


def _parameters_are_ambiguous(parameters: tuple[PolicyRuleParameter, ...]) -> bool:
    """Return True when a parameter set cannot be interpreted deterministically."""
    if not parameters:
        return True
    seen: dict[str, tuple[str, str, str]] = {}
    for parameter in parameters:
        canonical = _parameter_key(parameter)
        previous = seen.get(parameter.name)
        if previous is not None and previous != canonical:
            return True
        seen[parameter.name] = canonical
    return False


_RANK_FOR_KIND: dict[PolicySourceKind, PolicyAuthorityRank] = {
    PolicySourceKind.PLATFORM_API: PolicyAuthorityRank.PLATFORM_API,
    PolicySourceKind.ACCOUNT_METADATA: PolicyAuthorityRank.ACCOUNT_METADATA,
    PolicySourceKind.VERSIONED_RULE_DOCUMENT: PolicyAuthorityRank.VERSIONED_RULE_DOCUMENT,
    PolicySourceKind.FIRM_WEBSITE: PolicyAuthorityRank.FIRM_WEBSITE,
    PolicySourceKind.UNRESOLVED: PolicyAuthorityRank.UNRESOLVED,
}


def authority_rank_for_kind(kind: PolicySourceKind) -> PolicyAuthorityRank:
    """Map one source kind to its deterministic authority rank."""
    if not isinstance(kind, PolicySourceKind):
        raise RiskPolicyIntelligenceValidationError("kind must be PolicySourceKind")
    return _RANK_FOR_KIND[kind]


@dataclass(frozen=True, slots=True)
class PolicyRuleParameter:
    """One canonical, unit-carrying parameter of a policy rule."""

    name: str
    value: str
    unit: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or fullmatch(_PARAMETER_NAME_RE, self.name) is None:
            raise RiskPolicyIntelligenceValidationError(
                "policy rule parameter name must be a lowercase identifier"
            )
        if not isinstance(self.value, str) or not self.value:
            raise RiskPolicyIntelligenceValidationError(
                "policy rule parameter value must be a non-empty string"
            )
        if self.unit is not None and (not isinstance(self.unit, str) or not self.unit.strip()):
            raise RiskPolicyIntelligenceValidationError(
                "policy rule parameter unit must be a non-empty string or None"
            )

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, PolicyRuleParameter):
            raise TypeError("PolicyRuleParameter is only orderable against itself")
        return _parameter_key(self) < _parameter_key(other)

    def logical_values(self) -> tuple[str, str, str | None]:
        return (self.name, self.value, self.unit)


@dataclass(frozen=True, slots=True)
class PolicySourceObservation:
    """Immutable provenance binding for one observed policy surface."""

    observation_id: UUID
    kind: PolicySourceKind
    rank: PolicyAuthorityRank
    version: int
    fingerprint: RiskFingerprint
    content_digest: RiskFingerprint
    observed_at: datetime
    descriptor: ExternalSourceDescriptor | None

    def __post_init__(self) -> None:
        _validate_uuid(self.observation_id, field_name="policy source observation id")
        if not isinstance(self.kind, PolicySourceKind):
            raise RiskPolicyIntelligenceValidationError(
                "policy source kind must be PolicySourceKind"
            )
        if not isinstance(self.rank, PolicyAuthorityRank):
            raise RiskPolicyIntelligenceValidationError(
                "policy source rank must be PolicyAuthorityRank"
            )
        if self.rank is not authority_rank_for_kind(self.kind):
            raise RiskPolicyIntelligenceValidationError(
                "policy source rank must match its kind"
            )
        _validate_positive_int(self.version, field_name="policy source version")
        if not isinstance(self.fingerprint, RiskFingerprint):
            raise RiskPolicyIntelligenceValidationError(
                "policy source fingerprint must be RiskFingerprint"
            )
        if not isinstance(self.content_digest, RiskFingerprint):
            raise RiskPolicyIntelligenceValidationError(
                "policy source content_digest must be RiskFingerprint"
            )
        _validate_timestamp(self.observed_at, field_name="policy source observed_at")
        if self.descriptor is not None and not isinstance(
            self.descriptor, ExternalSourceDescriptor
        ):
            raise RiskPolicyIntelligenceValidationError(
                "policy source descriptor must be ExternalSourceDescriptor or None"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            str(self.observation_id),
            self.kind.value,
            self.rank.value,
            self.version,
            self.fingerprint.logical_values(),
            self.content_digest.logical_values(),
            self.observed_at.isoformat(),
            self.descriptor.logical_values() if self.descriptor is not None else None,
        )


@dataclass(frozen=True, slots=True)
class CandidatePolicyRule:
    """Source-tagged candidate rule. It carries no authority on its own."""

    rule_id: UUID
    code: RuleCode
    scope: PolicyRuleScope
    disposition: PolicyRuleDisposition
    parameters: tuple[PolicyRuleParameter, ...]
    source: PolicySourceObservation
    mandatory: bool

    def __post_init__(self) -> None:
        _validate_uuid(self.rule_id, field_name="candidate policy rule id")
        if not isinstance(self.code, RuleCode):
            raise RiskPolicyIntelligenceValidationError(
                "candidate policy rule code must be RuleCode"
            )
        if not isinstance(self.scope, PolicyRuleScope):
            raise RiskPolicyIntelligenceValidationError(
                "candidate policy rule scope must be PolicyRuleScope"
            )
        if not isinstance(self.disposition, PolicyRuleDisposition):
            raise RiskPolicyIntelligenceValidationError(
                "candidate policy rule disposition must be PolicyRuleDisposition"
            )
        if not isinstance(self.parameters, tuple) or any(
            not isinstance(parameter, PolicyRuleParameter) for parameter in self.parameters
        ):
            raise RiskPolicyIntelligenceValidationError(
                "candidate policy rule parameters must be a tuple of PolicyRuleParameter"
            )
        if not isinstance(self.source, PolicySourceObservation):
            raise RiskPolicyIntelligenceValidationError(
                "candidate policy rule source must be PolicySourceObservation"
            )
        if type(self.mandatory) is not bool:
            raise RiskPolicyIntelligenceValidationError(
                "candidate policy rule mandatory must be bool"
            )
        ordered = tuple(sorted(self.parameters))
        object.__setattr__(self, "parameters", ordered)

    def logical_values(self) -> tuple[object, ...]:
        return (
            str(self.rule_id),
            self.code.value,
            self.scope.value,
            self.disposition.value,
            tuple(parameter.logical_values() for parameter in self.parameters),
            self.source.logical_values(),
            self.mandatory,
        )


@dataclass(frozen=True, slots=True)
class AdmittedPolicyRule:
    """Deterministic admitted form of one policy rule."""

    rule_id: UUID
    code: RuleCode
    scope: PolicyRuleScope
    disposition: PolicyRuleDisposition
    parameters: tuple[PolicyRuleParameter, ...]
    source: PolicySourceObservation

    def __post_init__(self) -> None:
        _validate_uuid(self.rule_id, field_name="admitted policy rule id")
        if not isinstance(self.code, RuleCode):
            raise RiskPolicyIntelligenceValidationError(
                "admitted policy rule code must be RuleCode"
            )
        if not isinstance(self.scope, PolicyRuleScope):
            raise RiskPolicyIntelligenceValidationError(
                "admitted policy rule scope must be PolicyRuleScope"
            )
        if not isinstance(self.disposition, PolicyRuleDisposition):
            raise RiskPolicyIntelligenceValidationError(
                "admitted policy rule disposition must be PolicyRuleDisposition"
            )
        if not isinstance(self.parameters, tuple) or any(
            not isinstance(parameter, PolicyRuleParameter) for parameter in self.parameters
        ):
            raise RiskPolicyIntelligenceValidationError(
                "admitted policy rule parameters must be a tuple of PolicyRuleParameter"
            )
        if not isinstance(self.source, PolicySourceObservation):
            raise RiskPolicyIntelligenceValidationError(
                "admitted policy rule source must be PolicySourceObservation"
            )
        ordered = tuple(sorted(self.parameters))
        object.__setattr__(self, "parameters", ordered)

    def to_account_policy_rule(self) -> AccountPolicyRule:
        """Project this admitted rule onto the existing AccountPolicyRule contract."""
        return AccountPolicyRule(
            code=self.code.value,
            scope=self.scope,
            disposition=self.disposition,
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            str(self.rule_id),
            self.code.value,
            self.scope.value,
            self.disposition.value,
            tuple(parameter.logical_values() for parameter in self.parameters),
            self.source.logical_values(),
        )


def compute_policy_fingerprint(*parts: object) -> RiskFingerprint:
    """Deterministic policy-content fingerprint over canonical parts."""
    return compute_fingerprint(*parts)


def _revalidate_parameter(parameter: PolicyRuleParameter) -> None:
    if not isinstance(parameter, PolicyRuleParameter):
        raise RiskPolicyIntelligenceValidationError("parameter must be PolicyRuleParameter")
    if not isinstance(parameter.name, str) or fullmatch(
        _PARAMETER_NAME_RE, parameter.name
    ) is None:
        raise RiskPolicyIntelligenceValidationError(
            "parameter name must be a lowercase identifier"
        )
    if not isinstance(parameter.value, str) or not parameter.value:
        raise RiskPolicyIntelligenceValidationError(
            "parameter value must be a non-empty string"
        )
    if parameter.unit is not None and (
        not isinstance(parameter.unit, str) or not parameter.unit.strip()
    ):
        raise RiskPolicyIntelligenceValidationError(
            "parameter unit must be a non-empty string or None"
        )


def _revalidate_candidate(candidate: CandidatePolicyRule, observed_at: datetime) -> None:
    _validate_uuid(candidate.rule_id, field_name="candidate rule id")
    if not isinstance(candidate.code, RuleCode):
        raise RiskPolicyIntelligenceValidationError("candidate code must be RuleCode")
    if not isinstance(candidate.scope, PolicyRuleScope):
        raise RiskPolicyIntelligenceValidationError("candidate scope must be PolicyRuleScope")
    if not isinstance(candidate.disposition, PolicyRuleDisposition):
        raise RiskPolicyIntelligenceValidationError(
            "candidate disposition must be PolicyRuleDisposition"
        )
    if type(candidate.mandatory) is not bool:
        raise RiskPolicyIntelligenceValidationError("candidate mandatory must be bool")
    if not isinstance(candidate.parameters, tuple):
        raise RiskPolicyIntelligenceValidationError("candidate parameters must be a tuple")
    for parameter in candidate.parameters:
        _revalidate_parameter(parameter)

    source = candidate.source
    if not isinstance(source, PolicySourceObservation):
        raise RiskPolicyIntelligenceValidationError(
            "candidate source must be PolicySourceObservation"
        )
    _validate_uuid(source.observation_id, field_name="source observation id")
    if not isinstance(source.kind, PolicySourceKind):
        raise RiskPolicyIntelligenceValidationError("source kind must be PolicySourceKind")
    if not isinstance(source.rank, PolicyAuthorityRank):
        raise RiskPolicyIntelligenceValidationError("source rank must be PolicyAuthorityRank")
    _validate_positive_int(source.version, field_name="source version")
    if not isinstance(source.fingerprint, RiskFingerprint):
        raise RiskPolicyIntelligenceValidationError(
            "source fingerprint must be RiskFingerprint"
        )
    if not isinstance(source.content_digest, RiskFingerprint):
        raise RiskPolicyIntelligenceValidationError(
            "source content_digest must be RiskFingerprint"
        )
    _validate_timestamp(source.observed_at, field_name="source observed_at")
    if source.descriptor is not None and not isinstance(
        source.descriptor, ExternalSourceDescriptor
    ):
        raise RiskPolicyIntelligenceValidationError(
            "source descriptor must be ExternalSourceDescriptor or None"
        )
    if source.observed_at > observed_at:
        raise RiskPolicyIntelligenceValidationError(
            "source observed_at must not postdate the admission observation time"
        )


def _candidates_conflict(
    left: CandidatePolicyRule, right: CandidatePolicyRule
) -> bool:
    if left.scope is not right.scope:
        return True
    if left.disposition is not right.disposition:
        return True
    return _parameter_tuple(left.parameters) != _parameter_tuple(right.parameters)


def admit_policy_rules(
    candidates: tuple[CandidatePolicyRule, ...],
    *,
    observed_at: datetime,
) -> Result[tuple[AdmittedPolicyRule, ...], RiskPolicyIntelligenceError]:
    """Admit a deterministic rule set from source-tagged candidates, or fail closed."""
    if not isinstance(candidates, tuple) or any(
        not isinstance(candidate, CandidatePolicyRule) for candidate in candidates
    ):
        return Failure(
            RiskPolicyIntelligenceValidationError(
                "candidates must be a tuple of CandidatePolicyRule"
            )
        )
    try:
        _validate_timestamp(observed_at, field_name="admission observed_at")
    except RiskPolicyIntelligenceValidationError as error:
        return Failure(error)

    for candidate in candidates:
        try:
            _revalidate_candidate(candidate, observed_at)
        except RiskPolicyIntelligenceValidationError as error:
            return Failure(error)

        if candidate.source.rank is PolicyAuthorityRank.UNRESOLVED:
            return Failure(
                RiskPolicyIntelligenceResolutionError(
                    "non-authoritative (UNRESOLVED) source rules are never admitted"
                )
            )
        if candidate.source.kind is PolicySourceKind.UNRESOLVED:
            return Failure(
                RiskPolicyIntelligenceResolutionError(
                    "non-authoritative (UNRESOLVED) source rules are never admitted"
                )
            )
        if candidate.source.rank is not authority_rank_for_kind(candidate.source.kind):
            return Failure(
                RiskPolicyIntelligenceResolutionError(
                    "source authority rank does not match its kind"
                )
            )
        if candidate.disposition is PolicyRuleDisposition.UNKNOWN:
            return Failure(
                RiskPolicyIntelligenceResolutionError(
                    "unknown disposition is never admitted"
                )
            )
        if candidate.mandatory and _parameters_are_ambiguous(candidate.parameters):
            return Failure(
                RiskPolicyIntelligenceResolutionError(
                    "mandatory rule carries ambiguous parameters"
                )
            )

    grouped: dict[RuleCode, list[CandidatePolicyRule]] = {}
    for candidate in candidates:
        grouped.setdefault(candidate.code, []).append(candidate)

    admitted: list[AdmittedPolicyRule] = []
    for code, group in grouped.items():
        representative = min(group, key=lambda item: item.rule_id.int)
        for other in group:
            if other is representative:
                continue
            if _candidates_conflict(representative, other):
                return Failure(
                    RiskPolicyIntelligenceResolutionError(
                        f"conflicting authoritative sources for rule code {code.value}"
                    )
                )
        admitted.append(
            AdmittedPolicyRule(
                rule_id=representative.rule_id,
                code=representative.code,
                scope=representative.scope,
                disposition=representative.disposition,
                parameters=representative.parameters,
                source=representative.source,
            )
        )

    admitted.sort(key=lambda rule: rule.rule_id.int)
    return Success(tuple(admitted))


def compose_policy_snapshot(
    *,
    snapshot_id: AccountPolicySnapshotId,
    policy_ref: AccountPolicyReference,
    account_id: TradingAccountId,
    account_kind: TradingAccountKind,
    version: AccountPolicyVersion,
    effective_at: datetime,
    expires_at: datetime | None,
    account_size: MoneyAmount,
    max_drawdown: DrawdownBps,
    daily_loss_limit: DrawdownBps,
    drawdown_mode: DrawdownMode,
    phase: AccountPhase,
    client_profit_split: ProfitSplitBps,
    firm_ref: PropFirmReference | None,
    program_ref: PropProgramReference | None,
    admitted_rules: tuple[AdmittedPolicyRule, ...],
) -> Result[AccountPropPolicySnapshot, RiskPolicyIntelligenceError]:
    """Compose the existing account-policy snapshot from admitted rules."""
    if not isinstance(admitted_rules, tuple) or any(
        not isinstance(rule, AdmittedPolicyRule) for rule in admitted_rules
    ):
        return Failure(
            RiskPolicyIntelligenceValidationError(
                "admitted_rules must be a tuple of AdmittedPolicyRule"
            )
        )

    try:
        account_rules = tuple(rule.to_account_policy_rule() for rule in admitted_rules)
    except AccountPolicyValidationError as error:
        return Failure(RiskPolicyIntelligenceValidationError(str(error)))

    codes = [rule.code for rule in account_rules]
    if len(set(codes)) != len(codes):
        return Failure(
            RiskPolicyIntelligenceResolutionError(
                "admitted rules map to duplicate rule codes"
            )
        )

    try:
        snapshot = AccountPropPolicySnapshot(
            snapshot_id=snapshot_id,
            policy_ref=policy_ref,
            account_id=account_id,
            account_kind=account_kind,
            version=version,
            effective_at=effective_at,
            expires_at=expires_at,
            account_size=account_size,
            max_drawdown=max_drawdown,
            daily_loss_limit=daily_loss_limit,
            drawdown_mode=drawdown_mode,
            phase=phase,
            client_profit_split=client_profit_split,
            firm_ref=firm_ref,
            program_ref=program_ref,
            rules=account_rules,
        )
    except AccountPolicyValidationError as error:
        return Failure(RiskPolicyIntelligenceValidationError(str(error)))

    return Success(snapshot)


def _snapshot_content_values(snapshot: AccountPropPolicySnapshot) -> tuple[object, ...]:
    return (
        snapshot.policy_ref.logical_values(),
        snapshot.account_id.logical_values(),
        snapshot.account_kind.value,
        snapshot.effective_at.isoformat(),
        snapshot.expires_at.isoformat() if snapshot.expires_at is not None else None,
        snapshot.account_size.logical_values(),
        snapshot.max_drawdown.logical_values(),
        snapshot.daily_loss_limit.logical_values(),
        snapshot.drawdown_mode.value,
        snapshot.phase.value,
        snapshot.client_profit_split.logical_values(),
        snapshot.firm_ref.logical_values() if snapshot.firm_ref is not None else None,
        snapshot.program_ref.logical_values() if snapshot.program_ref is not None else None,
        tuple(rule.logical_values() for rule in snapshot.rules),
    )


def detect_policy_change(
    current: AccountPropPolicySnapshot | None,
    candidate: AccountPropPolicySnapshot,
    *,
    evaluated_at: datetime,
) -> Result[PolicyChangeVerdict, RiskPolicyIntelligenceError]:
    """Compare two account-policy snapshots by deterministic content identity."""
    try:
        _validate_timestamp(evaluated_at, field_name="change evaluated_at")
    except RiskPolicyIntelligenceValidationError as error:
        return Failure(error)

    if current is not None and not isinstance(current, AccountPropPolicySnapshot):
        return Failure(
            RiskPolicyIntelligenceValidationError(
                "current must be AccountPropPolicySnapshot or None"
            )
        )
    if not isinstance(candidate, AccountPropPolicySnapshot):
        return Failure(
            RiskPolicyIntelligenceValidationError(
                "candidate must be AccountPropPolicySnapshot"
            )
        )

    if current is None:
        return Success(PolicyChangeVerdict.CHANGED)

    current_fingerprint = compute_policy_fingerprint(_snapshot_content_values(current))
    candidate_fingerprint = compute_policy_fingerprint(_snapshot_content_values(candidate))

    if current_fingerprint == candidate_fingerprint:
        return Success(PolicyChangeVerdict.UNCHANGED)
    return Success(PolicyChangeVerdict.CHANGED)


def _admitted_rule_content_values(rule: AdmittedPolicyRule) -> tuple[object, ...]:
    return (
        rule.code.value,
        rule.scope.value,
        rule.disposition.value,
        _parameter_tuple(rule.parameters),
        rule.source.version,
        rule.source.fingerprint.value,
        rule.source.content_digest.value,
    )


def _rule_set_content_values(
    rules: tuple[AdmittedPolicyRule, ...],
) -> tuple[tuple[object, ...], ...]:
    return tuple(
        _admitted_rule_content_values(rule)
        for rule in sorted(rules, key=_admitted_rule_content_values)
    )


def detect_rule_set_change(
    prior_rules: tuple[AdmittedPolicyRule, ...],
    candidate_rules: tuple[AdmittedPolicyRule, ...],
    *,
    evaluated_at: datetime,
) -> Result[PolicyChangeVerdict, RiskPolicyIntelligenceError]:
    """Compare two full typed admitted rule sets (parameters and source included)."""
    try:
        _validate_timestamp(evaluated_at, field_name="rule-set evaluated_at")
    except RiskPolicyIntelligenceValidationError as error:
        return Failure(error)

    if not isinstance(prior_rules, tuple) or any(
        not isinstance(rule, AdmittedPolicyRule) for rule in prior_rules
    ):
        return Failure(
            RiskPolicyIntelligenceValidationError(
                "prior_rules must be a tuple of AdmittedPolicyRule"
            )
        )
    if not isinstance(candidate_rules, tuple) or any(
        not isinstance(rule, AdmittedPolicyRule) for rule in candidate_rules
    ):
        return Failure(
            RiskPolicyIntelligenceValidationError(
                "candidate_rules must be a tuple of AdmittedPolicyRule"
            )
        )

    prior_fingerprint = compute_policy_fingerprint(_rule_set_content_values(prior_rules))
    candidate_fingerprint = compute_policy_fingerprint(
        _rule_set_content_values(candidate_rules)
    )

    if prior_fingerprint == candidate_fingerprint:
        return Success(PolicyChangeVerdict.UNCHANGED)
    return Success(PolicyChangeVerdict.CHANGED)
