"""DEMO Risk/Policy deterministic authority (sovereignty core).

This module owns the only plane that may issue formal risk decisions and
authorizations for the DEMO profitability program. It creates no Production or
LIVE authority, no real-capital authority, and no provider credentials.

Everything here is deterministic and fail-closed:

* no ambient clock (every timestamp is caller-supplied and timezone-aware);
* no ambient UUID generation (every identity is caller-supplied);
* exact runtime types (``type(x) is int`` rejects ``bool``, exact enum
  membership, exact ``Decimal`` semantics for money/quantity, no ``float``);
* missing, stale, ambiguous, wrong-account, wrong-version or mismatched state
  never admits new risk.

The cognitive plane (``risk_cognitive``) produces advisory analysis only. It
must never construct a :class:`RiskDecision` or :class:`RiskAuthorization`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from hashlib import sha256
from re import fullmatch
from typing import Protocol, runtime_checkable
from uuid import UUID

from qore.infrastructure.account_policy import (
    AccountPolicySnapshotId,
    AccountPolicyVersion,
)
from qore.infrastructure.client_accounts import AccountPolicyReference, TradingAccountId
from qore.infrastructure.order_intent import (
    ExecutionInstrument,
    OrderIntentId,
    OrderPrice,
    OrderQuantity,
    OrderSide,
)
from qore.infrastructure.proprietary_accounts import DrawdownBps, MoneyAmount
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success

__all__ = [
    "DEFAULT_MAX_EVIDENCE_AGE_SECONDS",
    "OUTCOME_SEVERITY",
    "RiskArm",
    "RiskAuthorization",
    "RiskAuthorizationId",
    "RiskAuthorizationStatus",
    "RiskBudgetEvaluation",
    "RiskBudgetEvaluator",
    "RiskCapacityStore",
    "RiskCounterfactualLedger",
    "RiskCounterfactualRecord",
    "RiskDecision",
    "RiskDecisionId",
    "RiskEnvironment",
    "RiskError",
    "RiskEvidence",
    "RiskFingerprint",
    "RiskMarketEvidence",
    "RiskOpenPosition",
    "RiskOutcome",
    "RiskPolicyId",
    "RiskPolicySnapshot",
    "RiskPolicyVersion",
    "RiskRealizedOutcome",
    "RiskReason",
    "RiskReasonCode",
    "RiskReservation",
    "RiskReservationId",
    "RiskReservationStatus",
    "RiskResolutionError",
    "RiskScopeKind",
    "RiskScopeSnapshot",
    "RiskScopeState",
    "RiskTraderIdentity",
    "RiskValidationError",
    "compute_authorization_fingerprint",
    "compute_evidence_state_fingerprint",
    "compute_fingerprint",
    "evaluate_risk_admission",
    "is_authorization_reusable",
    "link_outcome",
    "recover_scope",
    "transition_scope",
    "void_authorization",
]


class RiskError(InfrastructureError):
    """Base error for the DEMO risk/policy authority."""

    __slots__ = ()


class RiskValidationError(RiskError):
    """Violation of a risk-authority invariant."""

    __slots__ = ()


class RiskResolutionError(RiskError):
    """A risk decision or scope transition cannot be resolved safely."""

    __slots__ = ()


class RiskOutcome(StrEnum):
    ALLOW = "allow"
    REDUCE = "reduce"
    REJECT = "reject"
    FREEZE_TRADER = "freeze_trader"
    CONTAIN_ACCOUNT = "contain_account"
    KILL = "kill"


OUTCOME_SEVERITY: dict[RiskOutcome, int] = {
    RiskOutcome.ALLOW: 0,
    RiskOutcome.REDUCE: 1,
    RiskOutcome.REJECT: 2,
    RiskOutcome.FREEZE_TRADER: 3,
    RiskOutcome.CONTAIN_ACCOUNT: 4,
    RiskOutcome.KILL: 5,
}


class RiskArm(StrEnum):
    TRADERS_RISK_ONLY = "traders_risk_only"
    CIBO_MANAGED_TRADERS_RISK = "cibo_managed_traders_risk"


class RiskEnvironment(StrEnum):
    DEMO = "demo"
    PRACTICE = "practice"
    PRODUCTION = "production"
    UNKNOWN = "unknown"


class RiskScopeState(StrEnum):
    NORMAL = "normal"
    REDUCED_CAPACITY = "reduced_capacity"
    FREEZE_TRADER = "freeze_trader"
    CONTAIN_ACCOUNT = "contain_account"
    KILL = "kill"


_SCOPE_STATE_SEVERITY: dict[RiskScopeState, int] = {
    RiskScopeState.NORMAL: 0,
    RiskScopeState.REDUCED_CAPACITY: 1,
    RiskScopeState.FREEZE_TRADER: 2,
    RiskScopeState.CONTAIN_ACCOUNT: 3,
    RiskScopeState.KILL: 4,
}


class RiskScopeKind(StrEnum):
    TRADER = "trader"
    ACCOUNT = "account"
    PORTFOLIO = "portfolio"


class RiskAuthorizationStatus(StrEnum):
    ISSUED = "issued"
    VOID = "void"


class RiskReservationStatus(StrEnum):
    RESERVED = "reserved"
    COMMITTED = "committed"
    RELEASED = "released"
    EXPIRED = "expired"


class RiskReasonCode(StrEnum):
    admitted = "risk.admitted"
    reduced = "risk.reduced"
    scope_frozen = "risk.rejected.scope-frozen"
    scope_contained = "risk.rejected.scope-contained"
    scope_killed = "risk.rejected.scope-killed"
    evidence_missing = "risk.rejected.evidence-missing"
    evidence_stale = "risk.rejected.evidence-stale"
    account_mismatch = "risk.rejected.account-mismatch"
    policy_version_mismatch = "risk.rejected.policy-version-mismatch"
    policy_expired = "risk.rejected.policy-expired"
    policy_not_effective = "risk.rejected.policy-not-effective"
    policy_ambiguous = "risk.rejected.policy-ambiguous"
    internal_limit_exceeded = "risk.rejected.internal-limit-exceeded"
    external_limit_exceeded = "risk.rejected.external-limit-exceeded"
    budget_exceeded = "risk.rejected.budget-exceeded"
    heat_exceeded = "risk.rejected.heat-exceeded"
    stress_breach = "risk.rejected.stress-breach"
    concentration_exceeded = "risk.rejected.concentration-exceeded"
    missing_stop = "risk.rejected.missing-stop"
    currency_mismatch = "risk.rejected.currency-mismatch"
    capacity_exhausted = "risk.rejected.capacity-exhausted"
    stale_reservation = "risk.rejected.stale-reservation"
    authorization_mutation = "risk.rejected.authorization-mutation"
    arm_mismatch = "risk.rejected.arm-mismatch"
    freeze_trader = "risk.scope.freeze-trader"
    contain_account = "risk.scope.contain-account"
    kill = "risk.scope.kill"
    reduced_capacity = "risk.reduced-capacity"


class RiskRealizedOutcome(StrEnum):
    REJECTED_WINNER = "rejected_winner"
    AVOIDED_LOSER = "avoided_loser"
    REDUCTION_DELTA = "reduction_delta"
    PREVENTED_BREACH = "prevented_breach"
    DRAWdown_REDUCTION = "drawdown_reduction"
    OPPORTUNITY_COST = "opportunity_cost"
    OVER_CONSERVATIVE = "over_conservative"


_SCOPE_BLOCK_REASON: dict[RiskScopeState, RiskReasonCode] = {
    RiskScopeState.FREEZE_TRADER: RiskReasonCode.scope_frozen,
    RiskScopeState.CONTAIN_ACCOUNT: RiskReasonCode.scope_contained,
    RiskScopeState.KILL: RiskReasonCode.scope_killed,
}


_SENSITIVE_PARTS = (
    "bearer ",
    "client_secret",
    "password",
    "secret",
    "token",
)

_MANDATORY_EVIDENCE_FIELDS = (
    "environment",
    "account_id",
    "trader",
    "intent_id",
    "intent_digest",
    "instrument",
    "side",
    "requested_quantity",
    "requested_notional",
    "open_positions",
    "per_trader_exposure",
    "per_instrument_exposure",
    "group_exposure",
    "portfolio_heat",
    "account_state",
    "account_policy_snapshot_id",
    "account_policy_ref",
    "account_policy_version",
    "internal_risk_policy_id",
    "internal_risk_policy_version",
    "market_evidence",
    "committed_capacity",
    "scope",
    "evaluated_at",
    "arm",
)


def _validate_uuid(value: UUID, *, field_name: str) -> None:
    if not isinstance(value, UUID):
        raise RiskValidationError(f"{field_name} must be a UUID")


def _validate_positive_int(value: int, *, field_name: str) -> None:
    if type(value) is not int or value <= 0:
        raise RiskValidationError(f"{field_name} must be a positive integer")


def _validate_non_negative_int(value: int, *, field_name: str) -> None:
    if type(value) is not int or value < 0:
        raise RiskValidationError(f"{field_name} must be a non-negative integer")


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise RiskValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise RiskValidationError(f"{field_name} must be timezone-aware")


def _validate_same_currency(values: tuple[MoneyAmount, ...], *, field_name: str) -> None:
    currencies = {item.currency.value for item in values}
    if len(currencies) != 1:
        raise RiskValidationError(
            f"{field_name} money values must use one canonical currency"
        )


def _validate_reason_summary(value: str, *, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise RiskValidationError(f"{field_name} must be a non-empty string")
    normalized = value.lower()
    if any(part in normalized for part in _SENSITIVE_PARTS):
        raise RiskValidationError(f"{field_name} must not contain sensitive material")


@dataclass(frozen=True, slots=True)
class RiskDecisionId:
    """Explicit identity of one immutable risk decision."""

    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="risk decision id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class RiskAuthorizationId:
    """Explicit identity of one immutable risk authorization."""

    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="risk authorization id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class RiskReservationId:
    """Explicit identity of one immutable risk-capacity reservation."""

    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="risk reservation id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class RiskPolicyId:
    """Explicit identity of one immutable internal risk-policy configuration."""

    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="risk policy id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class RiskPolicyVersion:
    """Monotonic positive version number supplied by the policy publisher."""

    value: int

    def __post_init__(self) -> None:
        _validate_positive_int(self.value, field_name="risk policy version")

    def logical_values(self) -> tuple[int, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class RiskFingerprint:
    """64 lowercase hex characters of a deterministic sha256 digest."""

    value: str

    def __post_init__(self) -> None:
        if type(self.value) is not str or fullmatch(r"[0-9a-f]{64}", self.value) is None:
            raise RiskValidationError(
                "risk fingerprint must be 64 lowercase hex characters"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class RiskReason:
    """Typed, non-secret reason for a risk decision or scope transition."""

    code: RiskReasonCode
    summary: str

    def __post_init__(self) -> None:
        if not isinstance(self.code, RiskReasonCode):
            raise RiskValidationError("risk reason code must be RiskReasonCode")
        _validate_reason_summary(self.summary, field_name="risk reason summary")

    def logical_values(self) -> tuple[str, str]:
        return (self.code.value, self.summary)


@dataclass(frozen=True, slots=True)
class RiskTraderIdentity:
    """Opaque trader identity with version and configuration fingerprint."""

    trader_id: UUID
    trader_version: int
    config_fingerprint: RiskFingerprint

    def __post_init__(self) -> None:
        _validate_uuid(self.trader_id, field_name="risk trader id")
        _validate_positive_int(self.trader_version, field_name="risk trader version")
        if not isinstance(self.config_fingerprint, RiskFingerprint):
            raise RiskValidationError(
                "risk trader config fingerprint must be RiskFingerprint"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            str(self.trader_id),
            self.trader_version,
            self.config_fingerprint.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class RiskOpenPosition:
    """One immutable open-position observation used for exposure accounting."""

    instrument: ExecutionInstrument
    side: OrderSide
    quantity: OrderQuantity
    stop_loss: OrderPrice | None

    def __post_init__(self) -> None:
        if not isinstance(self.instrument, ExecutionInstrument):
            raise RiskValidationError(
                "open position instrument must be ExecutionInstrument"
            )
        if not isinstance(self.side, OrderSide):
            raise RiskValidationError("open position side must be OrderSide")
        if not isinstance(self.quantity, OrderQuantity):
            raise RiskValidationError("open position quantity must be OrderQuantity")
        if self.stop_loss is not None and not isinstance(self.stop_loss, OrderPrice):
            raise RiskValidationError("open position stop_loss must be OrderPrice or None")

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.instrument.logical_values(),
            self.side.value,
            self.quantity.logical_values(),
            self.stop_loss.logical_values() if self.stop_loss is not None else None,
        )


def _position_sort_key(position: RiskOpenPosition) -> tuple[str, str, str, str]:
    stop = position.stop_loss
    return (
        position.instrument.value,
        position.side.value,
        format(position.quantity.value, "f"),
        format(stop.value, "f") if stop is not None else "",
    )


@dataclass(frozen=True, slots=True)
class RiskAccountObservedState:
    """Observed provider-neutral financial state for one trading account."""

    observation_id: UUID
    account_id: TradingAccountId
    observed_at: datetime
    balance: MoneyAmount
    equity: MoneyAmount
    margin_used: MoneyAmount
    drawdown: DrawdownBps
    daily_loss: DrawdownBps

    def __post_init__(self) -> None:
        _validate_uuid(self.observation_id, field_name="account observation id")
        if not isinstance(self.account_id, TradingAccountId):
            raise RiskValidationError("account state account_id must be TradingAccountId")
        _validate_timestamp(self.observed_at, field_name="account state observed_at")
        values = (self.balance, self.equity, self.margin_used)
        if any(not isinstance(item, MoneyAmount) for item in values):
            raise RiskValidationError(
                "account state monetary fields must contain only MoneyAmount values"
            )
        _validate_same_currency(values, field_name="account observed state")
        if self.balance.amount < 0:
            raise RiskValidationError("account state balance must not be negative")
        if self.equity.amount < 0:
            raise RiskValidationError("account state equity must not be negative")
        if self.margin_used.amount < 0:
            raise RiskValidationError("account state margin_used must not be negative")
        if not isinstance(self.drawdown, DrawdownBps):
            raise RiskValidationError("account state drawdown must be DrawdownBps")
        if not isinstance(self.daily_loss, DrawdownBps):
            raise RiskValidationError("account state daily_loss must be DrawdownBps")

    def logical_values(self) -> tuple[object, ...]:
        return (
            str(self.observation_id),
            self.account_id.logical_values(),
            self.observed_at.isoformat(),
            self.balance.logical_values(),
            self.equity.logical_values(),
            self.margin_used.logical_values(),
            self.drawdown.logical_values(),
            self.daily_loss.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class RiskMarketEvidence:
    """Observed market evidence with a caller-supplied deterministic fingerprint."""

    observed_at: datetime
    fingerprint: RiskFingerprint

    def __post_init__(self) -> None:
        _validate_timestamp(self.observed_at, field_name="market evidence observed_at")
        if not isinstance(self.fingerprint, RiskFingerprint):
            raise RiskValidationError("market evidence fingerprint must be RiskFingerprint")

    def logical_values(self) -> tuple[object, ...]:
        return (self.observed_at.isoformat(), self.fingerprint.logical_values())


@dataclass(frozen=True, slots=True)
class RiskScopeSnapshot:
    """Immutable governance scope state for one trader/account/portfolio."""

    state: RiskScopeState
    kind: RiskScopeKind
    scope_id: UUID
    since: datetime
    reason: RiskReasonCode
    generation: int

    def __post_init__(self) -> None:
        if not isinstance(self.state, RiskScopeState):
            raise RiskValidationError("scope state must be RiskScopeState")
        if not isinstance(self.kind, RiskScopeKind):
            raise RiskValidationError("scope kind must be RiskScopeKind")
        _validate_uuid(self.scope_id, field_name="scope id")
        _validate_timestamp(self.since, field_name="scope since")
        if not isinstance(self.reason, RiskReasonCode):
            raise RiskValidationError("scope reason must be RiskReasonCode")
        _validate_non_negative_int(self.generation, field_name="scope generation")

    @property
    def blocks_new_admission(self) -> bool:
        return self.state in {
            RiskScopeState.FREEZE_TRADER,
            RiskScopeState.CONTAIN_ACCOUNT,
            RiskScopeState.KILL,
        }

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.state.value,
            self.kind.value,
            str(self.scope_id),
            self.since.isoformat(),
            self.reason.value,
            self.generation,
        )


@dataclass(frozen=True, slots=True)
class RiskEvidence:
    """Immutable, fully-bound evidence for one DEMO risk admission evaluation."""

    environment: RiskEnvironment
    account_id: TradingAccountId
    trader: RiskTraderIdentity
    intent_id: OrderIntentId
    intent_digest: RiskFingerprint
    instrument: ExecutionInstrument
    side: OrderSide
    requested_quantity: OrderQuantity
    requested_notional: MoneyAmount
    stop_loss: OrderPrice | None
    bounded_loss_at_stop: MoneyAmount | None
    open_positions: tuple[RiskOpenPosition, ...]
    per_trader_exposure: MoneyAmount
    per_instrument_exposure: MoneyAmount
    group_exposure: MoneyAmount
    portfolio_heat: MoneyAmount
    account_state: RiskAccountObservedState
    account_policy_snapshot_id: AccountPolicySnapshotId
    account_policy_ref: AccountPolicyReference
    account_policy_version: AccountPolicyVersion
    internal_risk_policy_id: RiskPolicyId
    internal_risk_policy_version: RiskPolicyVersion
    market_evidence: RiskMarketEvidence
    committed_capacity: MoneyAmount
    scope: RiskScopeSnapshot
    evaluated_at: datetime
    arm: RiskArm

    def __post_init__(self) -> None:
        if not isinstance(self.environment, RiskEnvironment):
            raise RiskValidationError("evidence environment must be RiskEnvironment")
        if not isinstance(self.account_id, TradingAccountId):
            raise RiskValidationError("evidence account_id must be TradingAccountId")
        if not isinstance(self.trader, RiskTraderIdentity):
            raise RiskValidationError("evidence trader must be RiskTraderIdentity")
        if not isinstance(self.intent_id, OrderIntentId):
            raise RiskValidationError("evidence intent_id must be OrderIntentId")
        if not isinstance(self.intent_digest, RiskFingerprint):
            raise RiskValidationError("evidence intent_digest must be RiskFingerprint")
        if not isinstance(self.instrument, ExecutionInstrument):
            raise RiskValidationError("evidence instrument must be ExecutionInstrument")
        if not isinstance(self.side, OrderSide):
            raise RiskValidationError("evidence side must be OrderSide")
        if not isinstance(self.requested_quantity, OrderQuantity):
            raise RiskValidationError(
                "evidence requested_quantity must be OrderQuantity"
            )
        money_fields = (
            self.requested_notional,
            self.per_trader_exposure,
            self.per_instrument_exposure,
            self.group_exposure,
            self.portfolio_heat,
            self.committed_capacity,
        )
        if any(not isinstance(item, MoneyAmount) for item in money_fields):
            raise RiskValidationError(
                "evidence monetary fields must contain only MoneyAmount values"
            )
        if self.stop_loss is not None and not isinstance(self.stop_loss, OrderPrice):
            raise RiskValidationError("evidence stop_loss must be OrderPrice or None")
        if self.stop_loss is None and self.bounded_loss_at_stop is not None:
            raise RiskValidationError(
                "bounded_loss_at_stop requires a stop_loss"
            )
        if self.bounded_loss_at_stop is not None:
            if not isinstance(self.bounded_loss_at_stop, MoneyAmount):
                raise RiskValidationError(
                    "evidence bounded_loss_at_stop must be MoneyAmount or None"
                )
            if self.bounded_loss_at_stop.amount < 0:
                raise RiskValidationError(
                    "evidence bounded_loss_at_stop must not be negative"
                )
        if not isinstance(self.open_positions, tuple):
            raise RiskValidationError("evidence open_positions must be a tuple")
        if any(not isinstance(item, RiskOpenPosition) for item in self.open_positions):
            raise RiskValidationError(
                "evidence open_positions must contain only RiskOpenPosition values"
            )
        if not isinstance(self.account_state, RiskAccountObservedState):
            raise RiskValidationError(
                "evidence account_state must be RiskAccountObservedState"
            )
        if not isinstance(self.account_policy_snapshot_id, AccountPolicySnapshotId):
            raise RiskValidationError(
                "evidence account_policy_snapshot_id must be AccountPolicySnapshotId"
            )
        if not isinstance(self.account_policy_ref, AccountPolicyReference):
            raise RiskValidationError(
                "evidence account_policy_ref must be AccountPolicyReference"
            )
        if not isinstance(self.account_policy_version, AccountPolicyVersion):
            raise RiskValidationError(
                "evidence account_policy_version must be AccountPolicyVersion"
            )
        if not isinstance(self.internal_risk_policy_id, RiskPolicyId):
            raise RiskValidationError(
                "evidence internal_risk_policy_id must be RiskPolicyId"
            )
        if not isinstance(self.internal_risk_policy_version, RiskPolicyVersion):
            raise RiskValidationError(
                "evidence internal_risk_policy_version must be RiskPolicyVersion"
            )
        if not isinstance(self.market_evidence, RiskMarketEvidence):
            raise RiskValidationError(
                "evidence market_evidence must be RiskMarketEvidence"
            )
        if not isinstance(self.scope, RiskScopeSnapshot):
            raise RiskValidationError("evidence scope must be RiskScopeSnapshot")
        _validate_timestamp(self.evaluated_at, field_name="evidence evaluated_at")
        if not isinstance(self.arm, RiskArm):
            raise RiskValidationError("evidence arm must be RiskArm")

        all_money: list[MoneyAmount] = list(money_fields)
        all_money.extend(
            (
                self.account_state.balance,
                self.account_state.equity,
                self.account_state.margin_used,
            )
        )
        if self.bounded_loss_at_stop is not None:
            all_money.append(self.bounded_loss_at_stop)
        _validate_same_currency(tuple(all_money), field_name="evidence monetary")

    def is_complete(self) -> bool:
        """Return False if any mandatory field is missing.

        Construction already validates types strictly, so a fully-populated
        instance is complete. This is a defensive trust-boundary re-check that
        survives reflective corruption of a frozen instance.
        """

        return all(
            getattr(self, field_name, None) is not None
            for field_name in _MANDATORY_EVIDENCE_FIELDS
        )

    def logical_values(self) -> tuple[object, ...]:
        ordered_positions = tuple(
            sorted(self.open_positions, key=_position_sort_key)
        )
        return (
            self.environment.value,
            self.account_id.logical_values(),
            self.trader.logical_values(),
            self.intent_id.logical_values(),
            self.intent_digest.logical_values(),
            self.instrument.logical_values(),
            self.side.value,
            self.requested_quantity.logical_values(),
            self.requested_notional.logical_values(),
            self.stop_loss.logical_values() if self.stop_loss is not None else None,
            (
                self.bounded_loss_at_stop.logical_values()
                if self.bounded_loss_at_stop is not None
                else None
            ),
            tuple(position.logical_values() for position in ordered_positions),
            self.per_trader_exposure.logical_values(),
            self.per_instrument_exposure.logical_values(),
            self.group_exposure.logical_values(),
            self.portfolio_heat.logical_values(),
            self.account_state.logical_values(),
            self.account_policy_snapshot_id.logical_values(),
            self.account_policy_ref.logical_values(),
            self.account_policy_version.logical_values(),
            self.internal_risk_policy_id.logical_values(),
            self.internal_risk_policy_version.logical_values(),
            self.market_evidence.logical_values(),
            self.committed_capacity.logical_values(),
            self.scope.logical_values(),
            self.evaluated_at.isoformat(),
            self.arm.value,
        )


@dataclass(frozen=True, slots=True)
class RiskPolicySnapshot:
    """Immutable internal risk-policy configuration binding."""

    policy_id: RiskPolicyId
    version: RiskPolicyVersion
    fingerprint: RiskFingerprint
    budget_config_fingerprint: RiskFingerprint
    arm: RiskArm

    def __post_init__(self) -> None:
        if not isinstance(self.policy_id, RiskPolicyId):
            raise RiskValidationError("policy snapshot policy_id must be RiskPolicyId")
        if not isinstance(self.version, RiskPolicyVersion):
            raise RiskValidationError("policy snapshot version must be RiskPolicyVersion")
        if not isinstance(self.fingerprint, RiskFingerprint):
            raise RiskValidationError(
                "policy snapshot fingerprint must be RiskFingerprint"
            )
        if not isinstance(self.budget_config_fingerprint, RiskFingerprint):
            raise RiskValidationError(
                "policy snapshot budget_config_fingerprint must be RiskFingerprint"
            )
        if not isinstance(self.arm, RiskArm):
            raise RiskValidationError("policy snapshot arm must be RiskArm")

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.policy_id.logical_values(),
            self.version.logical_values(),
            self.fingerprint.logical_values(),
            self.budget_config_fingerprint.logical_values(),
            self.arm.value,
        )


@dataclass(frozen=True, slots=True)
class RiskBudgetEvaluation:
    """Deterministic budget verdict produced by the L3 budget evaluator."""

    admitted: bool
    reduced: bool
    authorized_quantity: OrderQuantity | None
    bounded_loss_at_stop: MoneyAmount | None
    reason: RiskReason

    def __post_init__(self) -> None:
        if type(self.admitted) is not bool:
            raise RiskValidationError("budget evaluation admitted must be bool")
        if type(self.reduced) is not bool:
            raise RiskValidationError("budget evaluation reduced must be bool")
        if not isinstance(self.reason, RiskReason):
            raise RiskValidationError("budget evaluation reason must be RiskReason")
        if self.admitted:
            if not isinstance(self.authorized_quantity, OrderQuantity):
                raise RiskValidationError(
                    "admitted budget evaluation requires OrderQuantity"
                )
        elif self.authorized_quantity is not None:
            raise RiskValidationError(
                "not-admitted budget evaluation must not carry authorized_quantity"
            )
        if self.reduced and not self.admitted:
            raise RiskValidationError(
                "reduced budget evaluation implies admitted"
            )
        if self.bounded_loss_at_stop is not None and not isinstance(
            self.bounded_loss_at_stop, MoneyAmount
        ):
            raise RiskValidationError(
                "budget evaluation bounded_loss_at_stop must be MoneyAmount or None"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.admitted,
            self.reduced,
            (
                self.authorized_quantity.logical_values()
                if self.authorized_quantity is not None
                else None
            ),
            (
                self.bounded_loss_at_stop.logical_values()
                if self.bounded_loss_at_stop is not None
                else None
            ),
            self.reason.logical_values(),
        )


@runtime_checkable
class RiskBudgetEvaluator(Protocol):
    """Pure budget evaluation seam implemented by the L3 engine."""

    @property
    def policy_fingerprint(self) -> RiskFingerprint:
        """Deterministic fingerprint of the budget configuration in use."""
        ...

    def evaluate(
        self,
        evidence: RiskEvidence,
        policy: RiskPolicySnapshot,
        *,
        evaluated_at: datetime,
    ) -> Result[RiskBudgetEvaluation, RiskError]:
        """Return a deterministic budget verdict without lateral authority."""
        ...


@dataclass(frozen=True, slots=True)
class RiskReservation:
    """Immutable risk-capacity reservation bound to an exact account/intent/policy."""

    reservation_id: RiskReservationId
    generation: int
    account_id: TradingAccountId
    intent_digest: RiskFingerprint
    policy_fingerprint: RiskFingerprint
    state_fingerprint: RiskFingerprint
    authorized_quantity: OrderQuantity
    notional: MoneyAmount
    status: RiskReservationStatus
    reserved_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.reservation_id, RiskReservationId):
            raise RiskValidationError("reservation_id must be RiskReservationId")
        _validate_non_negative_int(self.generation, field_name="reservation generation")
        if not isinstance(self.account_id, TradingAccountId):
            raise RiskValidationError("reservation account_id must be TradingAccountId")
        if not isinstance(self.intent_digest, RiskFingerprint):
            raise RiskValidationError(
                "reservation intent_digest must be RiskFingerprint"
            )
        if not isinstance(self.policy_fingerprint, RiskFingerprint):
            raise RiskValidationError(
                "reservation policy_fingerprint must be RiskFingerprint"
            )
        if not isinstance(self.state_fingerprint, RiskFingerprint):
            raise RiskValidationError(
                "reservation state_fingerprint must be RiskFingerprint"
            )
        if not isinstance(self.authorized_quantity, OrderQuantity):
            raise RiskValidationError(
                "reservation authorized_quantity must be OrderQuantity"
            )
        if not isinstance(self.notional, MoneyAmount):
            raise RiskValidationError("reservation notional must be MoneyAmount")
        if self.notional.amount < 0:
            raise RiskValidationError("reservation notional must not be negative")
        if not isinstance(self.status, RiskReservationStatus):
            raise RiskValidationError("reservation status must be RiskReservationStatus")
        _validate_timestamp(self.reserved_at, field_name="reservation reserved_at")

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.reservation_id.logical_values(),
            self.generation,
            self.account_id.logical_values(),
            self.intent_digest.logical_values(),
            self.policy_fingerprint.logical_values(),
            self.state_fingerprint.logical_values(),
            self.authorized_quantity.logical_values(),
            self.notional.logical_values(),
            self.status.value,
            self.reserved_at.isoformat(),
        )


@runtime_checkable
class RiskCapacityStore(Protocol):
    """Pure capacity lifecycle seam implemented by the L4 engine."""

    def reserve(self, reservation: RiskReservation) -> Result[RiskReservation, RiskError]:
        """Atomically reserve capacity under monotonic generation fencing."""
        ...

    def commit(self, reservation_id: RiskReservationId) -> Result[RiskReservation, RiskError]:
        """Commit a reserved capacity slice."""
        ...

    def release(self, reservation_id: RiskReservationId) -> Result[RiskReservation, RiskError]:
        """Release a reserved or committed capacity slice."""
        ...

    def expire(self, reservation_id: RiskReservationId) -> Result[RiskReservation, RiskError]:
        """Expire a stale reservation."""
        ...

    def get(
        self, reservation_id: RiskReservationId
    ) -> Result[RiskReservation | None, RiskError]:
        """Read a reservation by id, or None when absent."""
        ...


@dataclass(frozen=True, slots=True)
class RiskAuthorization:
    """Immutable risk authorization receipt (only for ALLOW/REDUCE decisions)."""

    authorization_id: RiskAuthorizationId
    decision_id: RiskDecisionId
    account_id: TradingAccountId
    environment: RiskEnvironment
    trader: RiskTraderIdentity
    intent_id: OrderIntentId
    intent_digest: RiskFingerprint
    instrument: ExecutionInstrument
    side: OrderSide
    requested_quantity: OrderQuantity
    authorized_quantity: OrderQuantity
    requested_notional: MoneyAmount
    authorized_notional: MoneyAmount
    stop_loss: OrderPrice | None
    bounded_loss_at_stop: MoneyAmount | None
    account_policy_snapshot_id: AccountPolicySnapshotId
    account_policy_version: AccountPolicyVersion
    internal_risk_policy_id: RiskPolicyId
    internal_risk_policy_version: RiskPolicyVersion
    account_state_fingerprint: RiskFingerprint
    market_evidence_fingerprint: RiskFingerprint
    reservation_id: RiskReservationId
    reservation_generation: int
    scope_generation: int
    issued_at: datetime
    arm: RiskArm
    status: RiskAuthorizationStatus = RiskAuthorizationStatus.ISSUED
    reason_codes: tuple[RiskReasonCode, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.authorization_id, RiskAuthorizationId):
            raise RiskValidationError(
                "authorization_id must be RiskAuthorizationId"
            )
        if not isinstance(self.decision_id, RiskDecisionId):
            raise RiskValidationError("decision_id must be RiskDecisionId")
        if not isinstance(self.account_id, TradingAccountId):
            raise RiskValidationError("account_id must be TradingAccountId")
        if not isinstance(self.environment, RiskEnvironment):
            raise RiskValidationError("environment must be RiskEnvironment")
        if not isinstance(self.trader, RiskTraderIdentity):
            raise RiskValidationError("trader must be RiskTraderIdentity")
        if not isinstance(self.intent_id, OrderIntentId):
            raise RiskValidationError("intent_id must be OrderIntentId")
        if not isinstance(self.intent_digest, RiskFingerprint):
            raise RiskValidationError("intent_digest must be RiskFingerprint")
        if not isinstance(self.instrument, ExecutionInstrument):
            raise RiskValidationError("instrument must be ExecutionInstrument")
        if not isinstance(self.side, OrderSide):
            raise RiskValidationError("side must be OrderSide")
        if not isinstance(self.requested_quantity, OrderQuantity):
            raise RiskValidationError("requested_quantity must be OrderQuantity")
        if not isinstance(self.authorized_quantity, OrderQuantity):
            raise RiskValidationError("authorized_quantity must be OrderQuantity")
        if not isinstance(self.requested_notional, MoneyAmount):
            raise RiskValidationError("requested_notional must be MoneyAmount")
        if not isinstance(self.authorized_notional, MoneyAmount):
            raise RiskValidationError("authorized_notional must be MoneyAmount")
        if self.authorized_notional.amount < 0:
            raise RiskValidationError("authorized_notional must not be negative")
        if self.authorized_notional.amount > self.requested_notional.amount:
            raise RiskValidationError(
                "authorized_notional must not exceed requested_notional"
            )
        if self.authorized_notional.currency != self.requested_notional.currency:
            raise RiskValidationError(
                "authorized_notional and requested_notional must share one currency"
            )
        if self.stop_loss is not None and not isinstance(self.stop_loss, OrderPrice):
            raise RiskValidationError("stop_loss must be OrderPrice or None")
        if self.bounded_loss_at_stop is not None and not isinstance(
            self.bounded_loss_at_stop, MoneyAmount
        ):
            raise RiskValidationError(
                "bounded_loss_at_stop must be MoneyAmount or None"
            )
        if not isinstance(self.account_policy_snapshot_id, AccountPolicySnapshotId):
            raise RiskValidationError(
                "account_policy_snapshot_id must be AccountPolicySnapshotId"
            )
        if not isinstance(self.account_policy_version, AccountPolicyVersion):
            raise RiskValidationError(
                "account_policy_version must be AccountPolicyVersion"
            )
        if not isinstance(self.internal_risk_policy_id, RiskPolicyId):
            raise RiskValidationError(
                "internal_risk_policy_id must be RiskPolicyId"
            )
        if not isinstance(self.internal_risk_policy_version, RiskPolicyVersion):
            raise RiskValidationError(
                "internal_risk_policy_version must be RiskPolicyVersion"
            )
        if not isinstance(self.account_state_fingerprint, RiskFingerprint):
            raise RiskValidationError(
                "account_state_fingerprint must be RiskFingerprint"
            )
        if not isinstance(self.market_evidence_fingerprint, RiskFingerprint):
            raise RiskValidationError(
                "market_evidence_fingerprint must be RiskFingerprint"
            )
        if not isinstance(self.reservation_id, RiskReservationId):
            raise RiskValidationError("reservation_id must be RiskReservationId")
        _validate_non_negative_int(
            self.reservation_generation, field_name="reservation_generation"
        )
        _validate_non_negative_int(self.scope_generation, field_name="scope_generation")
        _validate_timestamp(self.issued_at, field_name="issued_at")
        if not isinstance(self.arm, RiskArm):
            raise RiskValidationError("arm must be RiskArm")
        if not isinstance(self.status, RiskAuthorizationStatus):
            raise RiskValidationError("status must be RiskAuthorizationStatus")
        if not isinstance(self.reason_codes, tuple):
            raise RiskValidationError("reason_codes must be a tuple")
        if any(not isinstance(code, RiskReasonCode) for code in self.reason_codes):
            raise RiskValidationError(
                "reason_codes must contain only RiskReasonCode values"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.authorization_id.logical_values(),
            self.decision_id.logical_values(),
            self.account_id.logical_values(),
            self.environment.value,
            self.trader.logical_values(),
            self.intent_id.logical_values(),
            self.intent_digest.logical_values(),
            self.instrument.logical_values(),
            self.side.value,
            self.requested_quantity.logical_values(),
            self.authorized_quantity.logical_values(),
            self.requested_notional.logical_values(),
            self.authorized_notional.logical_values(),
            self.stop_loss.logical_values() if self.stop_loss is not None else None,
            (
                self.bounded_loss_at_stop.logical_values()
                if self.bounded_loss_at_stop is not None
                else None
            ),
            self.account_policy_snapshot_id.logical_values(),
            self.account_policy_version.logical_values(),
            self.internal_risk_policy_id.logical_values(),
            self.internal_risk_policy_version.logical_values(),
            self.account_state_fingerprint.logical_values(),
            self.market_evidence_fingerprint.logical_values(),
            self.reservation_id.logical_values(),
            self.reservation_generation,
            self.scope_generation,
            self.issued_at.isoformat(),
            self.arm.value,
            self.status.value,
            tuple(code.value for code in self.reason_codes),
        )


@dataclass(frozen=True, slots=True)
class RiskDecision:
    """Immutable deterministic risk decision (the only formal authority output)."""

    decision_id: RiskDecisionId
    outcome: RiskOutcome
    reasons: tuple[RiskReason, ...]
    evidence: RiskEvidence
    evaluated_at: datetime
    arm: RiskArm
    authorization: RiskAuthorization | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.decision_id, RiskDecisionId):
            raise RiskValidationError("decision_id must be RiskDecisionId")
        if not isinstance(self.outcome, RiskOutcome):
            raise RiskValidationError("outcome must be RiskOutcome")
        if not isinstance(self.reasons, tuple) or not self.reasons:
            raise RiskValidationError("reasons must be a non-empty tuple")
        if any(not isinstance(reason, RiskReason) for reason in self.reasons):
            raise RiskValidationError("reasons must contain only RiskReason values")
        if not isinstance(self.evidence, RiskEvidence):
            raise RiskValidationError("evidence must be RiskEvidence")
        _validate_timestamp(self.evaluated_at, field_name="decision evaluated_at")
        if not isinstance(self.arm, RiskArm):
            raise RiskValidationError("arm must be RiskArm")
        if self.outcome in (RiskOutcome.ALLOW, RiskOutcome.REDUCE):
            if not isinstance(self.authorization, RiskAuthorization):
                raise RiskValidationError(
                    "ALLOW/REDUCE decisions require a RiskAuthorization"
                )
            if self.authorization.status is not RiskAuthorizationStatus.ISSUED:
                raise RiskValidationError(
                    "ALLOW/REDUCE decisions require an issued authorization"
                )
            if self.authorization.decision_id != self.decision_id:
                raise RiskValidationError(
                    "authorization decision_id must match the decision"
                )
        elif self.authorization is not None:
            raise RiskValidationError(
                "non-admitting decisions must not carry an authorization"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.decision_id.logical_values(),
            self.outcome.value,
            tuple(reason.logical_values() for reason in self.reasons),
            self.evidence.logical_values(),
            self.evaluated_at.isoformat(),
            self.arm.value,
            self.authorization.logical_values() if self.authorization is not None else None,
        )


@dataclass(frozen=True, slots=True)
class RiskCounterfactualRecord:
    """Immutable binding of a decision to a later-realized outcome (no fabricated evidence)."""

    record_id: UUID
    decision_id: RiskDecisionId
    authorization_id: RiskAuthorizationId | None
    arm: RiskArm
    outcome: RiskOutcome
    reason_codes: tuple[RiskReasonCode, ...]
    intent_digest: RiskFingerprint
    account_id: TradingAccountId
    evaluated_at: datetime
    realized: RiskRealizedOutcome | None = None

    def __post_init__(self) -> None:
        _validate_uuid(self.record_id, field_name="counterfactual record id")
        if not isinstance(self.decision_id, RiskDecisionId):
            raise RiskValidationError("counterfactual decision_id must be RiskDecisionId")
        if self.authorization_id is not None and not isinstance(
            self.authorization_id, RiskAuthorizationId
        ):
            raise RiskValidationError(
                "counterfactual authorization_id must be RiskAuthorizationId or None"
            )
        if not isinstance(self.arm, RiskArm):
            raise RiskValidationError("counterfactual arm must be RiskArm")
        if not isinstance(self.outcome, RiskOutcome):
            raise RiskValidationError("counterfactual outcome must be RiskOutcome")
        if not isinstance(self.reason_codes, tuple):
            raise RiskValidationError("counterfactual reason_codes must be a tuple")
        if any(not isinstance(code, RiskReasonCode) for code in self.reason_codes):
            raise RiskValidationError(
                "counterfactual reason_codes must contain only RiskReasonCode values"
            )
        if not isinstance(self.intent_digest, RiskFingerprint):
            raise RiskValidationError(
                "counterfactual intent_digest must be RiskFingerprint"
            )
        if not isinstance(self.account_id, TradingAccountId):
            raise RiskValidationError("counterfactual account_id must be TradingAccountId")
        _validate_timestamp(self.evaluated_at, field_name="counterfactual evaluated_at")
        if self.realized is not None and not isinstance(
            self.realized, RiskRealizedOutcome
        ):
            raise RiskValidationError(
                "counterfactual realized must be RiskRealizedOutcome or None"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            str(self.record_id),
            self.decision_id.logical_values(),
            (
                self.authorization_id.logical_values()
                if self.authorization_id is not None
                else None
            ),
            self.arm.value,
            self.outcome.value,
            tuple(code.value for code in self.reason_codes),
            self.intent_digest.logical_values(),
            self.account_id.logical_values(),
            self.evaluated_at.isoformat(),
            self.realized.value if self.realized is not None else None,
        )


@dataclass(frozen=True, slots=True)
class RiskCounterfactualLedger:
    """Immutable append-only counterfactual attribution ledger."""

    records: tuple[RiskCounterfactualRecord, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.records, tuple):
            raise RiskValidationError("counterfactual ledger records must be a tuple")
        if any(not isinstance(record, RiskCounterfactualRecord) for record in self.records):
            raise RiskValidationError(
                "counterfactual ledger must contain only RiskCounterfactualRecord values"
            )
        record_ids = [record.record_id for record in self.records]
        if len(set(record_ids)) != len(record_ids):
            raise RiskValidationError(
                "counterfactual ledger record identities must be unique"
            )
        ordered = tuple(sorted(self.records, key=lambda record: record.record_id.int))
        object.__setattr__(self, "records", ordered)

    def append(self, record: RiskCounterfactualRecord) -> RiskCounterfactualLedger:
        """Return a new ledger with one record appended (never mutates)."""

        return RiskCounterfactualLedger(self.records + (record,))

    def logical_values(self) -> tuple[tuple[object, ...], ...]:
        return tuple(record.logical_values() for record in self.records)


def compute_fingerprint(*parts: object) -> RiskFingerprint:
    """Deterministic sha256 fingerprint over the canonical repr of a tuple of parts."""

    canonical = repr(parts).encode("utf-8")
    return RiskFingerprint(sha256(canonical).hexdigest())


def compute_evidence_state_fingerprint(evidence: RiskEvidence) -> RiskFingerprint:
    """Deterministic fingerprint over canonical account + market evidence bytes."""

    if not isinstance(evidence, RiskEvidence):
        raise RiskValidationError("evidence must be RiskEvidence")
    return compute_fingerprint(
        evidence.account_state.logical_values(),
        evidence.market_evidence.logical_values(),
    )


def compute_authorization_fingerprint(auth: RiskAuthorization) -> RiskFingerprint:
    """Deterministic fingerprint over canonical authorization logical values."""

    if not isinstance(auth, RiskAuthorization):
        raise RiskValidationError("authorization must be RiskAuthorization")
    return compute_fingerprint(auth.logical_values())


def transition_scope(
    current: RiskScopeSnapshot,
    target: RiskScopeState,
    *,
    scope_id: UUID,
    kind: RiskScopeKind,
    since: datetime,
    reason: RiskReasonCode,
    generation: int,
) -> Result[RiskScopeSnapshot, RiskError]:
    """Deterministic forward-only scope transition (escalation or re-assertion).

    Recovery (de-escalation) is forbidden here and must go through
    :func:`recover_scope`.
    """

    if not isinstance(current, RiskScopeSnapshot):
        return Failure(RiskValidationError("current must be RiskScopeSnapshot"))
    if not isinstance(target, RiskScopeState):
        return Failure(RiskValidationError("target must be RiskScopeState"))
    try:
        _validate_uuid(scope_id, field_name="scope id")
        if not isinstance(kind, RiskScopeKind):
            raise RiskValidationError("kind must be RiskScopeKind")
        _validate_timestamp(since, field_name="scope since")
        if not isinstance(reason, RiskReasonCode):
            raise RiskValidationError("reason must be RiskReasonCode")
        _validate_non_negative_int(generation, field_name="scope generation")
    except RiskValidationError as error:
        return Failure(error)

    if generation <= current.generation:
        return Failure(
            RiskValidationError("scope generation must strictly increase")
        )
    if _SCOPE_STATE_SEVERITY[target] < _SCOPE_STATE_SEVERITY[current.state]:
        return Failure(
            RiskResolutionError(
                "scope de-escalation requires governed recovery via recover_scope"
            )
        )
    try:
        return Success(
            RiskScopeSnapshot(
                state=target,
                kind=kind,
                scope_id=scope_id,
                since=since,
                reason=reason,
                generation=generation,
            )
        )
    except RiskValidationError as error:
        return Failure(error)


def recover_scope(
    current: RiskScopeSnapshot,
    target: RiskScopeState,
    *,
    scope_id: UUID,
    kind: RiskScopeKind,
    since: datetime,
    reason: RiskReasonCode,
    generation: int,
    evidence_ref: RiskFingerprint,
) -> Result[RiskScopeSnapshot, RiskError]:
    """Governed de-escalation recovery (CONTAIN_ACCOUNT -> REDUCED_CAPACITY -> NORMAL).

    KILL is non-recoverable in DEMO. CIBO/Trader cannot call this to
    self-reactivate: recovery requires an explicit ``evidence_ref`` plus a
    strictly monotonic ``generation`` and is never exposed as a Trader/CIBO
    authority path.
    """

    if not isinstance(current, RiskScopeSnapshot):
        return Failure(RiskValidationError("current must be RiskScopeSnapshot"))
    if not isinstance(target, RiskScopeState):
        return Failure(RiskValidationError("target must be RiskScopeState"))
    try:
        _validate_uuid(scope_id, field_name="scope id")
        if not isinstance(kind, RiskScopeKind):
            raise RiskValidationError("kind must be RiskScopeKind")
        _validate_timestamp(since, field_name="scope since")
        if not isinstance(reason, RiskReasonCode):
            raise RiskValidationError("reason must be RiskReasonCode")
        _validate_non_negative_int(generation, field_name="scope generation")
        if not isinstance(evidence_ref, RiskFingerprint):
            raise RiskValidationError("evidence_ref must be RiskFingerprint")
    except RiskValidationError as error:
        return Failure(error)

    if current.state is RiskScopeState.KILL:
        return Failure(RiskResolutionError("KILL scope is non-recoverable in DEMO"))
    if _SCOPE_STATE_SEVERITY[target] >= _SCOPE_STATE_SEVERITY[current.state]:
        return Failure(
            RiskResolutionError("recovery requires a strict de-escalation")
        )
    if since < current.since:
        return Failure(RiskValidationError("recovery since must not predate current scope"))
    if generation <= current.generation:
        return Failure(
            RiskValidationError("scope generation must strictly increase")
        )
    try:
        return Success(
            RiskScopeSnapshot(
                state=target,
                kind=kind,
                scope_id=scope_id,
                since=since,
                reason=reason,
                generation=generation,
            )
        )
    except RiskValidationError as error:
        return Failure(error)


def void_authorization(
    auth: RiskAuthorization,
    *,
    reason: RiskReason,
    voided_at: datetime,
) -> RiskAuthorization:
    """Return a new VOID authorization copy (the original is never mutated)."""

    if not isinstance(auth, RiskAuthorization):
        raise RiskValidationError("authorization must be RiskAuthorization")
    if not isinstance(reason, RiskReason):
        raise RiskValidationError("reason must be RiskReason")
    if reason.code is not RiskReasonCode.authorization_mutation:
        raise RiskValidationError(
            "void reason code must be authorization_mutation"
        )
    _validate_timestamp(voided_at, field_name="voided_at")
    if voided_at < auth.issued_at:
        raise RiskValidationError("voided_at must not predate issued_at")
    return RiskAuthorization(
        authorization_id=auth.authorization_id,
        decision_id=auth.decision_id,
        account_id=auth.account_id,
        environment=auth.environment,
        trader=auth.trader,
        intent_id=auth.intent_id,
        intent_digest=auth.intent_digest,
        instrument=auth.instrument,
        side=auth.side,
        requested_quantity=auth.requested_quantity,
        authorized_quantity=auth.authorized_quantity,
        requested_notional=auth.requested_notional,
        authorized_notional=auth.authorized_notional,
        stop_loss=auth.stop_loss,
        bounded_loss_at_stop=auth.bounded_loss_at_stop,
        account_policy_snapshot_id=auth.account_policy_snapshot_id,
        account_policy_version=auth.account_policy_version,
        internal_risk_policy_id=auth.internal_risk_policy_id,
        internal_risk_policy_version=auth.internal_risk_policy_version,
        account_state_fingerprint=auth.account_state_fingerprint,
        market_evidence_fingerprint=auth.market_evidence_fingerprint,
        reservation_id=auth.reservation_id,
        reservation_generation=auth.reservation_generation,
        scope_generation=auth.scope_generation,
        issued_at=auth.issued_at,
        arm=auth.arm,
        status=RiskAuthorizationStatus.VOID,
        reason_codes=auth.reason_codes + (reason.code,),
    )


def is_authorization_reusable(
    auth: RiskAuthorization,
    *,
    scope: RiskScopeSnapshot,
    account_policy_version: AccountPolicyVersion,
    evaluated_at: datetime,
) -> bool:
    """Return whether an authorization remains reusable with no wall-clock TTL.

    Reuse is bound to scope-generation equality (no scope escalation since
    issuance), account-policy-version equality, and a non-void status. The
    ``evaluated_at`` argument is accepted for call-site uniformity but is
    deliberately not used as a universal validity bound.
    """

    if not isinstance(auth, RiskAuthorization):
        raise RiskValidationError("authorization must be RiskAuthorization")
    if not isinstance(scope, RiskScopeSnapshot):
        raise RiskValidationError("scope must be RiskScopeSnapshot")
    if not isinstance(account_policy_version, AccountPolicyVersion):
        raise RiskValidationError(
            "account_policy_version must be AccountPolicyVersion"
        )
    _validate_timestamp(evaluated_at, field_name="evaluated_at")
    if auth.status is RiskAuthorizationStatus.VOID:
        return False
    if scope.generation != auth.scope_generation:
        return False
    if account_policy_version.value != auth.account_policy_version.value:
        return False
    return True


def link_outcome(
    record: RiskCounterfactualRecord,
    realized: RiskRealizedOutcome,
    *,
    linked_at: datetime,
) -> RiskCounterfactualRecord:
    """Return a new record with the realized outcome linked (no mutation)."""

    if not isinstance(record, RiskCounterfactualRecord):
        raise RiskValidationError("record must be RiskCounterfactualRecord")
    if not isinstance(realized, RiskRealizedOutcome):
        raise RiskValidationError("realized must be RiskRealizedOutcome")
    _validate_timestamp(linked_at, field_name="linked_at")
    if record.realized is not None:
        raise RiskValidationError(
            "counterfactual record already has a realized outcome"
        )
    return RiskCounterfactualRecord(
        record_id=record.record_id,
        decision_id=record.decision_id,
        authorization_id=record.authorization_id,
        arm=record.arm,
        outcome=record.outcome,
        reason_codes=record.reason_codes,
        intent_digest=record.intent_digest,
        account_id=record.account_id,
        evaluated_at=record.evaluated_at,
        realized=realized,
    )


DEFAULT_MAX_EVIDENCE_AGE_SECONDS = 300


def evaluate_risk_admission(
    evidence: RiskEvidence,
    internal_policy: RiskPolicySnapshot,
    budget_evaluator: RiskBudgetEvaluator,
    capacity: RiskCapacityStore,
    *,
    decision_id: RiskDecisionId,
    authorization_id: RiskAuthorizationId,
    reservation_id: RiskReservationId,
    reservation_generation: int,
    max_evidence_age_seconds: int = DEFAULT_MAX_EVIDENCE_AGE_SECONDS,
) -> Result[RiskDecision, RiskError]:
    """Master fail-closed DEMO admission evaluator (the sovereignty core).

    This is the only path that issues a :class:`RiskDecision`. It never calls a
    provider and never issues execution authority.
    """

    if not isinstance(evidence, RiskEvidence):
        return Failure(RiskValidationError("evidence must be RiskEvidence"))
    if not isinstance(internal_policy, RiskPolicySnapshot):
        return Failure(RiskValidationError("internal_policy must be RiskPolicySnapshot"))
    if not isinstance(budget_evaluator, RiskBudgetEvaluator):
        return Failure(
            RiskValidationError("budget_evaluator must be RiskBudgetEvaluator")
        )
    if not isinstance(capacity, RiskCapacityStore):
        return Failure(RiskValidationError("capacity must be RiskCapacityStore"))
    if not isinstance(decision_id, RiskDecisionId):
        return Failure(RiskValidationError("decision_id must be RiskDecisionId"))
    if not isinstance(authorization_id, RiskAuthorizationId):
        return Failure(
            RiskValidationError("authorization_id must be RiskAuthorizationId")
        )
    if not isinstance(reservation_id, RiskReservationId):
        return Failure(RiskValidationError("reservation_id must be RiskReservationId"))
    if type(reservation_generation) is not int or reservation_generation < 0:
        return Failure(
            RiskValidationError(
                "reservation_generation must be a non-negative integer"
            )
        )
    if type(max_evidence_age_seconds) is not int or max_evidence_age_seconds <= 0:
        return Failure(
            RiskValidationError("max_evidence_age_seconds must be a positive integer")
        )

    evaluated_at = evidence.evaluated_at

    if evidence.environment in (RiskEnvironment.PRODUCTION, RiskEnvironment.UNKNOWN):
        return Success(
            _reject_decision(
                evidence,
                decision_id,
                RiskReason(
                    RiskReasonCode.evidence_missing,
                    "risk admission is unavailable in this environment",
                ),
            )
        )

    if evidence.scope.blocks_new_admission:
        reason_code = _SCOPE_BLOCK_REASON[evidence.scope.state]
        return Success(
            _reject_decision(
                evidence,
                decision_id,
                RiskReason(reason_code, "scope blocks new risk admission"),
            )
        )

    if not evidence.is_complete():
        return Success(
            _reject_decision(
                evidence,
                decision_id,
                RiskReason(RiskReasonCode.evidence_missing, "risk evidence is incomplete"),
            )
        )

    if evidence.account_state.account_id != evidence.account_id:
        return Success(
            _reject_decision(
                evidence,
                decision_id,
                RiskReason(
                    RiskReasonCode.account_mismatch,
                    "account state belongs to a different trading account",
                ),
            )
        )

    max_age = timedelta(seconds=max_evidence_age_seconds)
    if evidence.market_evidence.observed_at > evaluated_at:
        return Success(
            _reject_decision(
                evidence,
                decision_id,
                RiskReason(
                    RiskReasonCode.evidence_stale,
                    "market evidence was observed after evaluation",
                ),
            )
        )
    if evidence.account_state.observed_at > evaluated_at:
        return Success(
            _reject_decision(
                evidence,
                decision_id,
                RiskReason(
                    RiskReasonCode.evidence_stale,
                    "account state was observed after evaluation",
                ),
            )
        )
    if evaluated_at - evidence.market_evidence.observed_at > max_age:
        return Success(
            _reject_decision(
                evidence,
                decision_id,
                RiskReason(RiskReasonCode.evidence_stale, "market evidence is stale"),
            )
        )
    if evaluated_at - evidence.account_state.observed_at > max_age:
        return Success(
            _reject_decision(
                evidence,
                decision_id,
                RiskReason(RiskReasonCode.evidence_stale, "account state is stale"),
            )
        )

    equity_currency = evidence.account_state.equity.currency
    currency_fields = (
        evidence.requested_notional,
        evidence.per_trader_exposure,
        evidence.per_instrument_exposure,
        evidence.group_exposure,
        evidence.portfolio_heat,
        evidence.committed_capacity,
    )
    if any(item.currency != equity_currency for item in currency_fields):
        return Success(
            _reject_decision(
                evidence,
                decision_id,
                RiskReason(
                    RiskReasonCode.currency_mismatch,
                    "evidence monetary fields use mixed currencies",
                ),
            )
        )

    if evidence.internal_risk_policy_id != internal_policy.policy_id:
        return Success(
            _reject_decision(
                evidence,
                decision_id,
                RiskReason(
                    RiskReasonCode.policy_version_mismatch,
                    "internal risk policy identity does not match evidence",
                ),
            )
        )
    if evidence.internal_risk_policy_version != internal_policy.version:
        return Success(
            _reject_decision(
                evidence,
                decision_id,
                RiskReason(
                    RiskReasonCode.policy_version_mismatch,
                    "internal risk policy version does not match evidence",
                ),
            )
        )
    if evidence.arm is not internal_policy.arm:
        return Success(
            _reject_decision(
                evidence,
                decision_id,
                RiskReason(
                    RiskReasonCode.arm_mismatch,
                    "risk policy arm does not match evidence arm",
                ),
            )
        )

    budget_result = budget_evaluator.evaluate(
        evidence, internal_policy, evaluated_at=evaluated_at
    )
    if isinstance(budget_result, Failure):
        return budget_result
    if not isinstance(budget_result, Success):
        return Failure(
            RiskValidationError("budget evaluator returned a non-result value")
        )
    budget: RiskBudgetEvaluation = budget_result.value
    if not isinstance(budget, RiskBudgetEvaluation):
        return Failure(
            RiskValidationError("budget evaluator returned a non-evaluation value")
        )
    if not budget.admitted:
        return Success(_reject_decision(evidence, decision_id, budget.reason))

    authorized_quantity = (
        budget.authorized_quantity
        if budget.authorized_quantity is not None
        else evidence.requested_quantity
    )
    requested_quantity = evidence.requested_quantity.value
    if authorized_quantity.value == requested_quantity:
        authorized_notional = evidence.requested_notional
    else:
        ratio = authorized_quantity.value / requested_quantity
        authorized_notional = MoneyAmount(
            evidence.requested_notional.currency,
            evidence.requested_notional.amount * ratio,
        )
    bounded_loss = (
        budget.bounded_loss_at_stop
        if budget.bounded_loss_at_stop is not None
        else evidence.bounded_loss_at_stop
    )
    reservation = RiskReservation(
        reservation_id=reservation_id,
        generation=reservation_generation,
        account_id=evidence.account_id,
        intent_digest=evidence.intent_digest,
        policy_fingerprint=internal_policy.fingerprint,
        state_fingerprint=compute_evidence_state_fingerprint(evidence),
        authorized_quantity=authorized_quantity,
        notional=authorized_notional,
        status=RiskReservationStatus.RESERVED,
        reserved_at=evaluated_at,
    )
    reserve_result = capacity.reserve(reservation)
    if isinstance(reserve_result, Failure):
        return Success(
            _reject_decision(
                evidence,
                decision_id,
                RiskReason(
                    RiskReasonCode.capacity_exhausted,
                    "risk capacity could not be reserved",
                ),
            )
        )
    if not isinstance(reserve_result, Success):
        return Failure(
            RiskValidationError("capacity store returned a non-result value")
        )
    if not isinstance(reserve_result.value, RiskReservation):
        return Failure(
            RiskValidationError("capacity store returned a non-reservation value")
        )

    authorization = RiskAuthorization(
        authorization_id=authorization_id,
        decision_id=decision_id,
        account_id=evidence.account_id,
        environment=evidence.environment,
        trader=evidence.trader,
        intent_id=evidence.intent_id,
        intent_digest=evidence.intent_digest,
        instrument=evidence.instrument,
        side=evidence.side,
        requested_quantity=evidence.requested_quantity,
        authorized_quantity=authorized_quantity,
        requested_notional=evidence.requested_notional,
        authorized_notional=authorized_notional,
        stop_loss=evidence.stop_loss,
        bounded_loss_at_stop=bounded_loss,
        account_policy_snapshot_id=evidence.account_policy_snapshot_id,
        account_policy_version=evidence.account_policy_version,
        internal_risk_policy_id=evidence.internal_risk_policy_id,
        internal_risk_policy_version=evidence.internal_risk_policy_version,
        account_state_fingerprint=compute_fingerprint(
            evidence.account_state.logical_values()
        ),
        market_evidence_fingerprint=compute_fingerprint(
            evidence.market_evidence.logical_values()
        ),
        reservation_id=reservation_id,
        reservation_generation=reservation_generation,
        scope_generation=evidence.scope.generation,
        issued_at=evaluated_at,
        arm=evidence.arm,
        status=RiskAuthorizationStatus.ISSUED,
        reason_codes=(budget.reason.code,),
    )
    outcome = RiskOutcome.REDUCE if budget.reduced else RiskOutcome.ALLOW
    decision = RiskDecision(
        decision_id=decision_id,
        outcome=outcome,
        reasons=(budget.reason,),
        evidence=evidence,
        evaluated_at=evaluated_at,
        arm=evidence.arm,
        authorization=authorization,
    )
    return Success(decision)


def _reject_decision(
    evidence: RiskEvidence,
    decision_id: RiskDecisionId,
    reason: RiskReason,
) -> RiskDecision:
    """Build a REJECT decision bound to the given reason."""

    return RiskDecision(
        decision_id=decision_id,
        outcome=RiskOutcome.REJECT,
        reasons=(reason,),
        evidence=evidence,
        evaluated_at=evidence.evaluated_at,
        arm=evidence.arm,
        authorization=None,
    )
