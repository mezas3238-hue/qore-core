from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from re import fullmatch
from uuid import UUID

from qore.infrastructure.client_accounts import (
    AccountPolicyReference,
    TradingAccountId,
    TradingAccountKind,
)
from qore.infrastructure.proprietary_accounts import DrawdownBps, MoneyAmount
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success


class AccountPolicyError(InfrastructureError):
    """Base error for account/prop-firm policy contracts."""

    __slots__ = ()


class AccountPolicyValidationError(AccountPolicyError):
    """Violation of an account-policy invariant."""

    __slots__ = ()


class AccountPolicyResolutionError(AccountPolicyError):
    """An account policy cannot be resolved safely for new trading."""

    __slots__ = ()


def _validate_uuid(value: UUID, *, field_name: str) -> None:
    if not isinstance(value, UUID):
        raise AccountPolicyValidationError(f"{field_name} must be a UUID")


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise AccountPolicyValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise AccountPolicyValidationError(f"{field_name} must be timezone-aware")


@dataclass(frozen=True, slots=True)
class AccountPolicySnapshotId:
    """Explicit identity of one immutable account-policy snapshot."""

    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="account policy snapshot id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class PropFirmReference:
    """Opaque QORE reference to one prop firm."""

    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="prop firm reference")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class PropProgramReference:
    """Opaque QORE reference to one prop-firm program."""

    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="prop program reference")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class AccountPolicyVersion:
    """Monotonic positive version number supplied by the policy publisher."""

    value: int

    def __post_init__(self) -> None:
        if type(self.value) is not int or self.value <= 0:
            raise AccountPolicyValidationError(
                "account policy version must be a positive integer"
            )

    def logical_values(self) -> tuple[int, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class ProfitSplitBps:
    """Client profit entitlement ratio expressed in basis points."""

    value: int

    def __post_init__(self) -> None:
        if type(self.value) is not int or not 0 <= self.value <= 10_000:
            raise AccountPolicyValidationError(
                "profit split basis points must be an integer between 0 and 10000"
            )

    def logical_values(self) -> tuple[int, ...]:
        return (self.value,)


class AccountPhase(StrEnum):
    EVALUATION = "evaluation"
    VERIFICATION = "verification"
    FUNDED = "funded"
    NOT_APPLICABLE = "not_applicable"
    UNKNOWN = "unknown"


class DrawdownMode(StrEnum):
    STATIC = "static"
    TRAILING = "trailing"
    UNKNOWN = "unknown"


class PolicyRuleScope(StrEnum):
    TRADING = "trading"
    PAYOUT = "payout"


class PolicyRuleDisposition(StrEnum):
    ALLOW = "allow"
    PROHIBIT = "prohibit"
    REQUIRE = "require"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class AccountPolicyRule:
    """Provider-neutral versioned rule declaration.

    Rule codes are canonical QORE identifiers. Firm-specific source text belongs behind the
    policy-adapter boundary and is not embedded in this contract.
    """

    code: str
    scope: PolicyRuleScope
    disposition: PolicyRuleDisposition

    def __post_init__(self) -> None:
        if not isinstance(self.code, str) or fullmatch(
            r"[A-Z][A-Z0-9_]{2,63}", self.code
        ) is None:
            raise AccountPolicyValidationError(
                "policy rule code must be 3-64 uppercase ASCII letters, digits or underscores"
            )
        if not isinstance(self.scope, PolicyRuleScope):
            raise AccountPolicyValidationError(
                "policy rule scope must be PolicyRuleScope"
            )
        if not isinstance(self.disposition, PolicyRuleDisposition):
            raise AccountPolicyValidationError(
                "policy rule disposition must be PolicyRuleDisposition"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (self.code, self.scope.value, self.disposition.value)


@dataclass(frozen=True, slots=True)
class AccountPropPolicySnapshot:
    """Immutable current policy snapshot for one client trading account.

    The snapshot describes account-local constraints only. It never creates a Core Decision or
    trading authority.
    """

    snapshot_id: AccountPolicySnapshotId
    policy_ref: AccountPolicyReference
    account_id: TradingAccountId
    account_kind: TradingAccountKind
    version: AccountPolicyVersion
    effective_at: datetime
    expires_at: datetime | None
    account_size: MoneyAmount
    max_drawdown: DrawdownBps
    daily_loss_limit: DrawdownBps
    drawdown_mode: DrawdownMode
    phase: AccountPhase
    client_profit_split: ProfitSplitBps
    firm_ref: PropFirmReference | None
    program_ref: PropProgramReference | None
    rules: tuple[AccountPolicyRule, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.snapshot_id, AccountPolicySnapshotId):
            raise AccountPolicyValidationError(
                "policy snapshot_id must be AccountPolicySnapshotId"
            )
        if not isinstance(self.policy_ref, AccountPolicyReference):
            raise AccountPolicyValidationError(
                "policy policy_ref must be AccountPolicyReference"
            )
        if not isinstance(self.account_id, TradingAccountId):
            raise AccountPolicyValidationError(
                "policy account_id must be TradingAccountId"
            )
        identities = {
            self.snapshot_id.value,
            self.policy_ref.value,
            self.account_id.value,
        }
        if len(identities) != 3:
            raise AccountPolicyValidationError(
                "policy snapshot, policy reference and account identities must differ"
            )
        if not isinstance(self.account_kind, TradingAccountKind):
            raise AccountPolicyValidationError(
                "policy account_kind must be TradingAccountKind"
            )
        if not isinstance(self.version, AccountPolicyVersion):
            raise AccountPolicyValidationError(
                "policy version must be AccountPolicyVersion"
            )
        _validate_timestamp(self.effective_at, field_name="policy effective_at")
        if self.expires_at is not None:
            _validate_timestamp(self.expires_at, field_name="policy expires_at")
            if self.expires_at <= self.effective_at:
                raise AccountPolicyValidationError(
                    "policy expires_at must be after effective_at"
                )
        if not isinstance(self.account_size, MoneyAmount):
            raise AccountPolicyValidationError("policy account_size must be MoneyAmount")
        if self.account_size.amount <= 0:
            raise AccountPolicyValidationError(
                "policy account_size must be strictly positive"
            )
        if not isinstance(self.max_drawdown, DrawdownBps):
            raise AccountPolicyValidationError(
                "policy max_drawdown must be DrawdownBps"
            )
        if not isinstance(self.daily_loss_limit, DrawdownBps):
            raise AccountPolicyValidationError(
                "policy daily_loss_limit must be DrawdownBps"
            )
        if not isinstance(self.drawdown_mode, DrawdownMode):
            raise AccountPolicyValidationError(
                "policy drawdown_mode must be DrawdownMode"
            )
        if not isinstance(self.phase, AccountPhase):
            raise AccountPolicyValidationError("policy phase must be AccountPhase")
        if not isinstance(self.client_profit_split, ProfitSplitBps):
            raise AccountPolicyValidationError(
                "policy client_profit_split must be ProfitSplitBps"
            )
        if self.firm_ref is not None and not isinstance(self.firm_ref, PropFirmReference):
            raise AccountPolicyValidationError(
                "policy firm_ref must be PropFirmReference or None"
            )
        if self.program_ref is not None and not isinstance(
            self.program_ref, PropProgramReference
        ):
            raise AccountPolicyValidationError(
                "policy program_ref must be PropProgramReference or None"
            )
        if not isinstance(self.rules, tuple):
            raise AccountPolicyValidationError("policy rules must be a tuple")
        if any(not isinstance(rule, AccountPolicyRule) for rule in self.rules):
            raise AccountPolicyValidationError(
                "policy rules must contain only AccountPolicyRule values"
            )
        codes = [rule.code for rule in self.rules]
        if len(set(codes)) != len(codes):
            raise AccountPolicyValidationError("policy rule codes must be unique")

        if self.account_kind is TradingAccountKind.PROP_FIRM:
            if self.firm_ref is None or self.program_ref is None:
                raise AccountPolicyValidationError(
                    "prop-firm policy requires firm_ref and program_ref"
                )
            if self.phase is AccountPhase.NOT_APPLICABLE:
                raise AccountPolicyValidationError(
                    "prop-firm policy phase cannot be NOT_APPLICABLE"
                )
        elif self.account_kind is TradingAccountKind.BROKERAGE:
            if self.firm_ref is not None or self.program_ref is not None:
                raise AccountPolicyValidationError(
                    "brokerage policy must not carry prop-firm references"
                )
            if self.phase is not AccountPhase.NOT_APPLICABLE:
                raise AccountPolicyValidationError(
                    "brokerage policy phase must be NOT_APPLICABLE"
                )
        elif self.account_kind is TradingAccountKind.UNKNOWN:
            if self.firm_ref is not None or self.program_ref is not None:
                raise AccountPolicyValidationError(
                    "unknown account kind must not carry prop-firm references"
                )
            if self.phase is not AccountPhase.UNKNOWN:
                raise AccountPolicyValidationError(
                    "unknown account kind requires UNKNOWN phase"
                )

        ordered_rules = tuple(
            sorted(
                self.rules,
                key=lambda rule: (rule.scope.value, rule.code, rule.disposition.value),
            )
        )
        object.__setattr__(self, "rules", ordered_rules)

    def is_complete_for_new_trading(self) -> bool:
        """Return whether mandatory account-policy semantics are resolved.

        This is only policy completeness. It is never a trading authorization verdict.
        """

        if self.account_kind is TradingAccountKind.UNKNOWN:
            return False
        if self.drawdown_mode is DrawdownMode.UNKNOWN:
            return False
        if self.phase is AccountPhase.UNKNOWN:
            return False
        return all(
            rule.disposition is not PolicyRuleDisposition.UNKNOWN for rule in self.rules
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.snapshot_id.logical_values(),
            self.policy_ref.logical_values(),
            self.account_id.logical_values(),
            self.account_kind.value,
            self.version.logical_values(),
            self.effective_at.isoformat(),
            self.expires_at.isoformat() if self.expires_at is not None else None,
            self.account_size.logical_values(),
            self.max_drawdown.logical_values(),
            self.daily_loss_limit.logical_values(),
            self.drawdown_mode.value,
            self.phase.value,
            self.client_profit_split.logical_values(),
            self.firm_ref.logical_values() if self.firm_ref is not None else None,
            self.program_ref.logical_values() if self.program_ref is not None else None,
            tuple(rule.logical_values() for rule in self.rules),
        )


@dataclass(frozen=True, slots=True)
class AccountPolicyRegistrySnapshot:
    """Immutable current registry of account-scoped policy snapshots."""

    policies: tuple[AccountPropPolicySnapshot, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.policies, tuple):
            raise AccountPolicyValidationError("policy registry policies must be a tuple")
        if not self.policies:
            raise AccountPolicyValidationError(
                "policy registry policies must not be empty"
            )
        if any(not isinstance(policy, AccountPropPolicySnapshot) for policy in self.policies):
            raise AccountPolicyValidationError(
                "policy registry must contain only AccountPropPolicySnapshot values"
            )

        snapshot_ids: set[UUID] = set()
        policy_refs: set[UUID] = set()
        account_ids: set[UUID] = set()
        for policy in self.policies:
            if policy.snapshot_id.value in snapshot_ids:
                raise AccountPolicyValidationError(
                    "policy registry snapshot identities must be unique"
                )
            if policy.policy_ref.value in policy_refs:
                raise AccountPolicyValidationError(
                    "policy registry policy references must be unique"
                )
            if policy.account_id.value in account_ids:
                raise AccountPolicyValidationError(
                    "each trading account must have one current policy snapshot"
                )
            snapshot_ids.add(policy.snapshot_id.value)
            policy_refs.add(policy.policy_ref.value)
            account_ids.add(policy.account_id.value)

        ordered = tuple(
            sorted(
                self.policies,
                key=lambda policy: (
                    policy.account_id.value.hex,
                    policy.policy_ref.value.hex,
                ),
            )
        )
        object.__setattr__(self, "policies", ordered)

    def logical_values(self) -> tuple[tuple[object, ...], ...]:
        return tuple(policy.logical_values() for policy in self.policies)

    def resolve_for_new_trading(
        self,
        *,
        account_id: TradingAccountId,
        policy_ref: AccountPolicyReference,
        evaluated_at: datetime,
    ) -> Result[AccountPropPolicySnapshot, AccountPolicyError]:
        """Resolve a current complete policy or fail closed.

        Success means policy readiness only. A Core Decision and later Agent/Risk/Entitlement
        checks remain independently mandatory before any new trading action.
        """

        if not isinstance(account_id, TradingAccountId):
            return Failure(
                AccountPolicyResolutionError("account_id must be TradingAccountId")
            )
        if not isinstance(policy_ref, AccountPolicyReference):
            return Failure(
                AccountPolicyResolutionError(
                    "policy_ref must be AccountPolicyReference"
                )
            )
        try:
            _validate_timestamp(evaluated_at, field_name="policy evaluated_at")
        except AccountPolicyValidationError as error:
            return Failure(AccountPolicyResolutionError(str(error)))

        for policy in self.policies:
            if policy.policy_ref != policy_ref:
                continue
            if policy.account_id != account_id:
                return Failure(
                    AccountPolicyResolutionError(
                        "policy reference belongs to a different trading account"
                    )
                )
            if evaluated_at < policy.effective_at:
                return Failure(AccountPolicyResolutionError("policy is not yet effective"))
            if policy.expires_at is not None and evaluated_at >= policy.expires_at:
                return Failure(AccountPolicyResolutionError("policy is expired"))
            if not policy.is_complete_for_new_trading():
                return Failure(
                    AccountPolicyResolutionError(
                        "mandatory account-policy semantics are unresolved"
                    )
                )
            return Success(policy)

        return Failure(AccountPolicyResolutionError("policy reference not found"))
