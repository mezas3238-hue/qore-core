from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from qore.functional.decisions import (
    DecisionId,
    DecisionOutcome,
    DecisionStatus,
    FunctionalDecision,
)
from qore.infrastructure.account_policy import (
    AccountPolicySnapshotId,
    AccountPropPolicySnapshot,
)
from qore.infrastructure.client_accounts import (
    AccountPolicyReference,
    ClientId,
    ClientTradingAccountBinding,
    ExecutionRuntimeReference,
    ProductEntitlementReference,
    TradingAccountId,
    TradingAccountLifecycleState,
)
from qore.infrastructure.order_intent import (
    ExecutionInstrument,
    OrderPrice,
    OrderQuantity,
    OrderSide,
    OrderType,
)
from qore.infrastructure.proprietary_accounts import DrawdownBps, MoneyAmount
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success


class ClientExecutionAgentError(InfrastructureError):
    """Base error for platform-neutral Client Execution Agent contracts."""

    __slots__ = ()


class ClientExecutionAgentValidationError(ClientExecutionAgentError):
    """Violation of a Client Execution Agent contract invariant."""

    __slots__ = ()


def _validate_uuid(value: UUID, *, field_name: str) -> None:
    if not isinstance(value, UUID):
        raise ClientExecutionAgentValidationError(f"{field_name} must be a UUID")


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise ClientExecutionAgentValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ClientExecutionAgentValidationError(f"{field_name} must be timezone-aware")


@dataclass(frozen=True, slots=True)
class ClientAccountObservationId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="client account observation id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ClientExecutionPolicyId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="client execution policy id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class SizingPolicyReference:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="sizing policy reference")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ProtectionPolicyReference:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="protection policy reference")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class TrailingPolicyReference:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="trailing policy reference")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class DecisionSecurityEvidenceReference:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="decision security evidence reference")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


class DecisionSecurityStatus(StrEnum):
    VERIFIED = "verified"
    REJECTED = "rejected"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class DecisionSecurityAttestation:
    """Output contract expected from the later decision-security boundary.

    This delivery does not perform cryptographic verification. Non-production tests may construct
    attestations only to prove downstream fail-closed composition semantics.
    """

    decision_id: DecisionId
    account_id: TradingAccountId
    runtime_ref: ExecutionRuntimeReference
    status: DecisionSecurityStatus
    evidence_ref: DecisionSecurityEvidenceReference
    verified_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.decision_id, DecisionId):
            raise ClientExecutionAgentValidationError(
                "security attestation decision_id must be DecisionId"
            )
        if not isinstance(self.decision_id.value, UUID):
            raise ClientExecutionAgentValidationError(
                "security attestation decision id value must be UUID"
            )
        if not isinstance(self.account_id, TradingAccountId):
            raise ClientExecutionAgentValidationError(
                "security attestation account_id must be TradingAccountId"
            )
        if not isinstance(self.runtime_ref, ExecutionRuntimeReference):
            raise ClientExecutionAgentValidationError(
                "security attestation runtime_ref must be ExecutionRuntimeReference"
            )
        if not isinstance(self.status, DecisionSecurityStatus):
            raise ClientExecutionAgentValidationError(
                "security attestation status must be DecisionSecurityStatus"
            )
        if not isinstance(self.evidence_ref, DecisionSecurityEvidenceReference):
            raise ClientExecutionAgentValidationError(
                "security attestation evidence_ref must be DecisionSecurityEvidenceReference"
            )
        _validate_timestamp(self.verified_at, field_name="security attestation verified_at")

    def logical_values(self) -> tuple[object, ...]:
        return (
            str(self.decision_id.value),
            self.account_id.logical_values(),
            self.runtime_ref.logical_values(),
            self.status.value,
            self.evidence_ref.logical_values(),
            self.verified_at.isoformat(),
        )


@dataclass(frozen=True, slots=True)
class CoreTradeDecision:
    """Strategic Core decision projected into provider-neutral trade semantics.

    Quantity and account-local protection are deliberately absent. Those are delegated deterministic
    calculations performed from this decision plus authorized account policies and observed state.
    """

    decision: FunctionalDecision
    instrument: ExecutionInstrument
    side: OrderSide
    order_type: OrderType
    expires_at: datetime
    limit_price: OrderPrice | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.decision, FunctionalDecision):
            raise ClientExecutionAgentValidationError(
                "core trade decision requires FunctionalDecision"
            )
        if not isinstance(self.decision.decision_id, DecisionId) or not isinstance(
            self.decision.decision_id.value, UUID
        ):
            raise ClientExecutionAgentValidationError(
                "core trade decision requires UUID-backed DecisionId"
            )
        if self.decision.decision_type.value != "core.trade":
            raise ClientExecutionAgentValidationError(
                "core trade decision type must be core.trade"
            )
        _validate_timestamp(self.decision.timestamp, field_name="core decision timestamp")
        if not isinstance(self.instrument, ExecutionInstrument):
            raise ClientExecutionAgentValidationError(
                "core trade decision instrument must be ExecutionInstrument"
            )
        if not isinstance(self.side, OrderSide):
            raise ClientExecutionAgentValidationError(
                "core trade decision side must be OrderSide"
            )
        if not isinstance(self.order_type, OrderType):
            raise ClientExecutionAgentValidationError(
                "core trade decision order_type must be OrderType"
            )
        _validate_timestamp(self.expires_at, field_name="core decision expires_at")
        if self.expires_at <= self.decision.timestamp:
            raise ClientExecutionAgentValidationError(
                "core trade decision expires_at must be after decision timestamp"
            )
        if self.limit_price is not None and not isinstance(self.limit_price, OrderPrice):
            raise ClientExecutionAgentValidationError(
                "core trade decision limit_price must be OrderPrice or None"
            )
        if self.order_type is OrderType.MARKET and self.limit_price is not None:
            raise ClientExecutionAgentValidationError(
                "market core trade decision must not carry limit_price"
            )
        if self.order_type is OrderType.LIMIT and self.limit_price is None:
            raise ClientExecutionAgentValidationError(
                "limit core trade decision requires limit_price"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.decision.logical_values(),
            self.instrument.logical_values(),
            self.side.value,
            self.order_type.value,
            self.expires_at.isoformat(),
            self.limit_price.logical_values() if self.limit_price is not None else None,
        )


@dataclass(frozen=True, slots=True)
class ClientAccountObservedState:
    """Account-local state consumed by deterministic execution evaluation."""

    observation_id: ClientAccountObservationId
    account_id: TradingAccountId
    observed_at: datetime
    balance: MoneyAmount
    equity: MoneyAmount
    current_drawdown: DrawdownBps
    daily_loss: DrawdownBps
    open_positions: int

    def __post_init__(self) -> None:
        if not isinstance(self.observation_id, ClientAccountObservationId):
            raise ClientExecutionAgentValidationError(
                "account observation_id must be ClientAccountObservationId"
            )
        if not isinstance(self.account_id, TradingAccountId):
            raise ClientExecutionAgentValidationError(
                "account observation account_id must be TradingAccountId"
            )
        _validate_timestamp(self.observed_at, field_name="account observed_at")
        if not isinstance(self.balance, MoneyAmount):
            raise ClientExecutionAgentValidationError(
                "account observation balance must be MoneyAmount"
            )
        if not isinstance(self.equity, MoneyAmount):
            raise ClientExecutionAgentValidationError(
                "account observation equity must be MoneyAmount"
            )
        if self.balance.currency != self.equity.currency:
            raise ClientExecutionAgentValidationError(
                "account balance and equity must use the same currency"
            )
        if not isinstance(self.current_drawdown, DrawdownBps):
            raise ClientExecutionAgentValidationError(
                "account current_drawdown must be DrawdownBps"
            )
        if not isinstance(self.daily_loss, DrawdownBps):
            raise ClientExecutionAgentValidationError(
                "account daily_loss must be DrawdownBps"
            )
        if type(self.open_positions) is not int or self.open_positions < 0:
            raise ClientExecutionAgentValidationError(
                "account open_positions must be a non-negative integer"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.observation_id.logical_values(),
            self.account_id.logical_values(),
            self.observed_at.isoformat(),
            self.balance.logical_values(),
            self.equity.logical_values(),
            self.current_drawdown.logical_values(),
            self.daily_loss.logical_values(),
            self.open_positions,
        )


class ClientAgentEntitlementState(StrEnum):
    ENABLED = "enabled"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ClientAgentEntitlementSnapshot:
    """Minimal execution-entitlement input; billing semantics are defined later."""

    entitlement_ref: ProductEntitlementReference
    account_id: TradingAccountId
    state: ClientAgentEntitlementState
    evaluated_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.entitlement_ref, ProductEntitlementReference):
            raise ClientExecutionAgentValidationError(
                "agent entitlement_ref must be ProductEntitlementReference"
            )
        if not isinstance(self.account_id, TradingAccountId):
            raise ClientExecutionAgentValidationError(
                "agent entitlement account_id must be TradingAccountId"
            )
        if not isinstance(self.state, ClientAgentEntitlementState):
            raise ClientExecutionAgentValidationError(
                "agent entitlement state must be ClientAgentEntitlementState"
            )
        _validate_timestamp(self.evaluated_at, field_name="agent entitlement evaluated_at")

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.entitlement_ref.logical_values(),
            self.account_id.logical_values(),
            self.state.value,
            self.evaluated_at.isoformat(),
        )


@dataclass(frozen=True, slots=True)
class ClientExecutionPolicy:
    """Authorized account-local deterministic execution-calculation policy."""

    policy_id: ClientExecutionPolicyId
    sizing_policy_ref: SizingPolicyReference
    protection_policy_ref: ProtectionPolicyReference
    trailing_policy_ref: TrailingPolicyReference | None
    max_risk_per_trade: DrawdownBps
    max_account_state_age_seconds: int
    max_entitlement_age_seconds: int
    max_security_attestation_age_seconds: int

    def __post_init__(self) -> None:
        if not isinstance(self.policy_id, ClientExecutionPolicyId):
            raise ClientExecutionAgentValidationError(
                "client execution policy_id must be ClientExecutionPolicyId"
            )
        if not isinstance(self.sizing_policy_ref, SizingPolicyReference):
            raise ClientExecutionAgentValidationError(
                "client execution sizing_policy_ref must be SizingPolicyReference"
            )
        if not isinstance(self.protection_policy_ref, ProtectionPolicyReference):
            raise ClientExecutionAgentValidationError(
                "client execution protection_policy_ref must be ProtectionPolicyReference"
            )
        if self.trailing_policy_ref is not None and not isinstance(
            self.trailing_policy_ref, TrailingPolicyReference
        ):
            raise ClientExecutionAgentValidationError(
                "client execution trailing_policy_ref must be TrailingPolicyReference or None"
            )
        if not isinstance(self.max_risk_per_trade, DrawdownBps):
            raise ClientExecutionAgentValidationError(
                "client execution max_risk_per_trade must be DrawdownBps"
            )
        for field_name, value in (
            ("max_account_state_age_seconds", self.max_account_state_age_seconds),
            ("max_entitlement_age_seconds", self.max_entitlement_age_seconds),
            (
                "max_security_attestation_age_seconds",
                self.max_security_attestation_age_seconds,
            ),
        ):
            if type(value) is not int or value <= 0:
                raise ClientExecutionAgentValidationError(
                    f"client execution {field_name} must be a positive integer"
                )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.policy_id.logical_values(),
            self.sizing_policy_ref.logical_values(),
            self.protection_policy_ref.logical_values(),
            (
                self.trailing_policy_ref.logical_values()
                if self.trailing_policy_ref is not None
                else None
            ),
            self.max_risk_per_trade.logical_values(),
            self.max_account_state_age_seconds,
            self.max_entitlement_age_seconds,
            self.max_security_attestation_age_seconds,
        )


@dataclass(frozen=True, slots=True)
class ClientExecutionCalculation:
    """Deterministic output from account-local sizing/protection calculators."""

    decision_id: DecisionId
    account_id: TradingAccountId
    calculated_at: datetime
    quantity: OrderQuantity
    entry_reference_price: OrderPrice
    stop_loss: OrderPrice
    take_profit: OrderPrice
    estimated_risk: DrawdownBps
    sizing_policy_ref: SizingPolicyReference
    protection_policy_ref: ProtectionPolicyReference
    trailing_policy_ref: TrailingPolicyReference | None

    def __post_init__(self) -> None:
        if not isinstance(self.decision_id, DecisionId) or not isinstance(
            self.decision_id.value, UUID
        ):
            raise ClientExecutionAgentValidationError(
                "execution calculation decision_id must be UUID-backed DecisionId"
            )
        if not isinstance(self.account_id, TradingAccountId):
            raise ClientExecutionAgentValidationError(
                "execution calculation account_id must be TradingAccountId"
            )
        _validate_timestamp(self.calculated_at, field_name="execution calculated_at")
        if not isinstance(self.quantity, OrderQuantity):
            raise ClientExecutionAgentValidationError(
                "execution calculation quantity must be OrderQuantity"
            )
        if not isinstance(self.entry_reference_price, OrderPrice):
            raise ClientExecutionAgentValidationError(
                "execution entry_reference_price must be OrderPrice"
            )
        if not isinstance(self.stop_loss, OrderPrice):
            raise ClientExecutionAgentValidationError(
                "execution stop_loss must be OrderPrice"
            )
        if not isinstance(self.take_profit, OrderPrice):
            raise ClientExecutionAgentValidationError(
                "execution take_profit must be OrderPrice"
            )
        if not isinstance(self.estimated_risk, DrawdownBps):
            raise ClientExecutionAgentValidationError(
                "execution estimated_risk must be DrawdownBps"
            )
        if not isinstance(self.sizing_policy_ref, SizingPolicyReference):
            raise ClientExecutionAgentValidationError(
                "execution sizing_policy_ref must be SizingPolicyReference"
            )
        if not isinstance(self.protection_policy_ref, ProtectionPolicyReference):
            raise ClientExecutionAgentValidationError(
                "execution protection_policy_ref must be ProtectionPolicyReference"
            )
        if self.trailing_policy_ref is not None and not isinstance(
            self.trailing_policy_ref, TrailingPolicyReference
        ):
            raise ClientExecutionAgentValidationError(
                "execution trailing_policy_ref must be TrailingPolicyReference or None"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            str(self.decision_id.value),
            self.account_id.logical_values(),
            self.calculated_at.isoformat(),
            self.quantity.logical_values(),
            self.entry_reference_price.logical_values(),
            self.stop_loss.logical_values(),
            self.take_profit.logical_values(),
            self.estimated_risk.logical_values(),
            self.sizing_policy_ref.logical_values(),
            self.protection_policy_ref.logical_values(),
            (
                self.trailing_policy_ref.logical_values()
                if self.trailing_policy_ref is not None
                else None
            ),
        )


class ClientExecutionCalculator(Protocol):
    """Deterministic sizing/SL/TP calculation boundary for a concrete Agent runtime."""

    def calculate(
        self,
        decision: CoreTradeDecision,
        binding: ClientTradingAccountBinding,
        account_policy: AccountPropPolicySnapshot,
        observed_state: ClientAccountObservedState,
        execution_policy: ClientExecutionPolicy,
        *,
        calculated_at: datetime,
    ) -> Result[ClientExecutionCalculation, ClientExecutionAgentError]: ...


class ClientExecutionVerdict(StrEnum):
    EXECUTE = "execute"
    DECISION_BLOCKED = "decision_blocked"
    SECURITY_BLOCKED = "security_blocked"
    ACCOUNT_BLOCKED = "account_blocked"
    PROP_POLICY_BLOCKED = "prop_policy_blocked"
    RISK_BLOCKED = "risk_blocked"
    ENTITLEMENT_BLOCKED = "entitlement_blocked"
    UNRESOLVED = "unresolved"


class ClientExecutionReason(StrEnum):
    READY = "ready"
    CORE_DECISION_NOT_APPROVED = "core_decision_not_approved"
    CORE_DECISION_EXPIRED = "core_decision_expired"
    SECURITY_NOT_VERIFIED = "security_not_verified"
    SECURITY_BINDING_MISMATCH = "security_binding_mismatch"
    SECURITY_ATTESTATION_INVALID_TIME = "security_attestation_invalid_time"
    SECURITY_ATTESTATION_STALE = "security_attestation_stale"
    ACCOUNT_NOT_ACTIVE = "account_not_active"
    ACCOUNT_POLICY_BINDING_MISMATCH = "account_policy_binding_mismatch"
    ACCOUNT_POLICY_NOT_EFFECTIVE = "account_policy_not_effective"
    ACCOUNT_POLICY_EXPIRED = "account_policy_expired"
    ACCOUNT_POLICY_UNRESOLVED = "account_policy_unresolved"
    ACCOUNT_STATE_BINDING_MISMATCH = "account_state_binding_mismatch"
    ACCOUNT_STATE_INVALID_TIME = "account_state_invalid_time"
    ACCOUNT_STATE_STALE = "account_state_stale"
    ACCOUNT_CURRENCY_MISMATCH = "account_currency_mismatch"
    ACCOUNT_EQUITY_NON_POSITIVE = "account_equity_non_positive"
    MAX_DRAWDOWN_REACHED = "max_drawdown_reached"
    DAILY_LOSS_REACHED = "daily_loss_reached"
    ENTITLEMENT_BINDING_MISMATCH = "entitlement_binding_mismatch"
    ENTITLEMENT_NOT_ENABLED = "entitlement_not_enabled"
    ENTITLEMENT_INVALID_TIME = "entitlement_invalid_time"
    ENTITLEMENT_STALE = "entitlement_stale"
    CALCULATION_BINDING_MISMATCH = "calculation_binding_mismatch"
    CALCULATION_INVALID_TIME = "calculation_invalid_time"
    CALCULATION_POLICY_MISMATCH = "calculation_policy_mismatch"
    CALCULATED_RISK_EXCEEDS_POLICY = "calculated_risk_exceeds_policy"
    LIMIT_PRICE_MISMATCH = "limit_price_mismatch"
    INVALID_PROTECTION_GEOMETRY = "invalid_protection_geometry"


@dataclass(frozen=True, slots=True)
class ClientExecutionPlan:
    """Auditable account-local plan. It is not an order submission or broker command."""

    client_id: ClientId
    account_id: TradingAccountId
    decision_id: DecisionId
    instrument: ExecutionInstrument
    side: OrderSide
    order_type: OrderType
    quantity: OrderQuantity
    entry_reference_price: OrderPrice
    limit_price: OrderPrice | None
    stop_loss: OrderPrice
    take_profit: OrderPrice
    trailing_policy_ref: TrailingPolicyReference | None
    account_policy_ref: AccountPolicyReference
    account_policy_snapshot_id: AccountPolicySnapshotId
    execution_policy_id: ClientExecutionPolicyId
    sizing_policy_ref: SizingPolicyReference
    protection_policy_ref: ProtectionPolicyReference
    entitlement_ref: ProductEntitlementReference
    runtime_ref: ExecutionRuntimeReference
    account_observation_id: ClientAccountObservationId
    security_evidence_ref: DecisionSecurityEvidenceReference
    created_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.client_id, ClientId):
            raise ClientExecutionAgentValidationError("plan client_id must be ClientId")
        if not isinstance(self.account_id, TradingAccountId):
            raise ClientExecutionAgentValidationError(
                "plan account_id must be TradingAccountId"
            )
        if not isinstance(self.decision_id, DecisionId) or not isinstance(
            self.decision_id.value, UUID
        ):
            raise ClientExecutionAgentValidationError(
                "plan decision_id must be UUID-backed DecisionId"
            )
        if not isinstance(self.instrument, ExecutionInstrument):
            raise ClientExecutionAgentValidationError(
                "plan instrument must be ExecutionInstrument"
            )
        if not isinstance(self.side, OrderSide):
            raise ClientExecutionAgentValidationError("plan side must be OrderSide")
        if not isinstance(self.order_type, OrderType):
            raise ClientExecutionAgentValidationError(
                "plan order_type must be OrderType"
            )
        if not isinstance(self.quantity, OrderQuantity):
            raise ClientExecutionAgentValidationError(
                "plan quantity must be OrderQuantity"
            )
        for field_name, value in (
            ("entry_reference_price", self.entry_reference_price),
            ("stop_loss", self.stop_loss),
            ("take_profit", self.take_profit),
        ):
            if not isinstance(value, OrderPrice):
                raise ClientExecutionAgentValidationError(
                    f"plan {field_name} must be OrderPrice"
                )
        if self.limit_price is not None and not isinstance(self.limit_price, OrderPrice):
            raise ClientExecutionAgentValidationError(
                "plan limit_price must be OrderPrice or None"
            )
        if self.trailing_policy_ref is not None and not isinstance(
            self.trailing_policy_ref, TrailingPolicyReference
        ):
            raise ClientExecutionAgentValidationError(
                "plan trailing_policy_ref must be TrailingPolicyReference or None"
            )
        if not isinstance(self.account_policy_ref, AccountPolicyReference):
            raise ClientExecutionAgentValidationError(
                "plan account_policy_ref must be AccountPolicyReference"
            )
        if not isinstance(self.account_policy_snapshot_id, AccountPolicySnapshotId):
            raise ClientExecutionAgentValidationError(
                "plan account_policy_snapshot_id must be AccountPolicySnapshotId"
            )
        if not isinstance(self.execution_policy_id, ClientExecutionPolicyId):
            raise ClientExecutionAgentValidationError(
                "plan execution_policy_id must be ClientExecutionPolicyId"
            )
        if not isinstance(self.sizing_policy_ref, SizingPolicyReference):
            raise ClientExecutionAgentValidationError(
                "plan sizing_policy_ref must be SizingPolicyReference"
            )
        if not isinstance(self.protection_policy_ref, ProtectionPolicyReference):
            raise ClientExecutionAgentValidationError(
                "plan protection_policy_ref must be ProtectionPolicyReference"
            )
        if not isinstance(self.entitlement_ref, ProductEntitlementReference):
            raise ClientExecutionAgentValidationError(
                "plan entitlement_ref must be ProductEntitlementReference"
            )
        if not isinstance(self.runtime_ref, ExecutionRuntimeReference):
            raise ClientExecutionAgentValidationError(
                "plan runtime_ref must be ExecutionRuntimeReference"
            )
        if not isinstance(self.account_observation_id, ClientAccountObservationId):
            raise ClientExecutionAgentValidationError(
                "plan account_observation_id must be ClientAccountObservationId"
            )
        if not isinstance(self.security_evidence_ref, DecisionSecurityEvidenceReference):
            raise ClientExecutionAgentValidationError(
                "plan security_evidence_ref must be DecisionSecurityEvidenceReference"
            )
        _validate_timestamp(self.created_at, field_name="plan created_at")

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.client_id.logical_values(),
            self.account_id.logical_values(),
            str(self.decision_id.value),
            self.instrument.logical_values(),
            self.side.value,
            self.order_type.value,
            self.quantity.logical_values(),
            self.entry_reference_price.logical_values(),
            self.limit_price.logical_values() if self.limit_price is not None else None,
            self.stop_loss.logical_values(),
            self.take_profit.logical_values(),
            (
                self.trailing_policy_ref.logical_values()
                if self.trailing_policy_ref is not None
                else None
            ),
            self.account_policy_ref.logical_values(),
            self.account_policy_snapshot_id.logical_values(),
            self.execution_policy_id.logical_values(),
            self.sizing_policy_ref.logical_values(),
            self.protection_policy_ref.logical_values(),
            self.entitlement_ref.logical_values(),
            self.runtime_ref.logical_values(),
            self.account_observation_id.logical_values(),
            self.security_evidence_ref.logical_values(),
            self.created_at.isoformat(),
        )


@dataclass(frozen=True, slots=True)
class ClientExecutionEvaluation:
    decision_id: DecisionId
    account_id: TradingAccountId
    verdict: ClientExecutionVerdict
    reason: ClientExecutionReason
    evaluated_at: datetime
    plan: ClientExecutionPlan | None

    def __post_init__(self) -> None:
        if not isinstance(self.decision_id, DecisionId) or not isinstance(
            self.decision_id.value, UUID
        ):
            raise ClientExecutionAgentValidationError(
                "evaluation decision_id must be UUID-backed DecisionId"
            )
        if not isinstance(self.account_id, TradingAccountId):
            raise ClientExecutionAgentValidationError(
                "evaluation account_id must be TradingAccountId"
            )
        if not isinstance(self.verdict, ClientExecutionVerdict):
            raise ClientExecutionAgentValidationError(
                "evaluation verdict must be ClientExecutionVerdict"
            )
        if not isinstance(self.reason, ClientExecutionReason):
            raise ClientExecutionAgentValidationError(
                "evaluation reason must be ClientExecutionReason"
            )
        _validate_timestamp(self.evaluated_at, field_name="evaluation evaluated_at")
        if self.verdict is ClientExecutionVerdict.EXECUTE:
            if not isinstance(self.plan, ClientExecutionPlan):
                raise ClientExecutionAgentValidationError(
                    "EXECUTE evaluation requires ClientExecutionPlan"
                )
            if self.reason is not ClientExecutionReason.READY:
                raise ClientExecutionAgentValidationError(
                    "EXECUTE evaluation requires READY reason"
                )
        elif self.plan is not None:
            raise ClientExecutionAgentValidationError(
                "blocked evaluation must not carry an execution plan"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            str(self.decision_id.value),
            self.account_id.logical_values(),
            self.verdict.value,
            self.reason.value,
            self.evaluated_at.isoformat(),
            self.plan.logical_values() if self.plan is not None else None,
        )


def _blocked(
    decision_id: DecisionId,
    account_id: TradingAccountId,
    *,
    verdict: ClientExecutionVerdict,
    reason: ClientExecutionReason,
    evaluated_at: datetime,
) -> Success[ClientExecutionEvaluation]:
    return Success(
        ClientExecutionEvaluation(
            decision_id=decision_id,
            account_id=account_id,
            verdict=verdict,
            reason=reason,
            evaluated_at=evaluated_at,
            plan=None,
        )
    )


def _age_seconds(*, newer: datetime, older: datetime) -> float:
    return (newer - older).total_seconds()


def _protection_geometry_is_valid(
    *,
    side: OrderSide,
    entry: OrderPrice,
    stop_loss: OrderPrice,
    take_profit: OrderPrice,
) -> bool:
    if side is OrderSide.BUY:
        return stop_loss.value < entry.value < take_profit.value
    return take_profit.value < entry.value < stop_loss.value


def evaluate_client_execution(
    decision: CoreTradeDecision,
    security: DecisionSecurityAttestation,
    binding: ClientTradingAccountBinding,
    account_policy: AccountPropPolicySnapshot,
    observed_state: ClientAccountObservedState,
    entitlement: ClientAgentEntitlementSnapshot,
    execution_policy: ClientExecutionPolicy,
    calculation: ClientExecutionCalculation,
    *,
    evaluated_at: datetime,
) -> Result[ClientExecutionEvaluation, ClientExecutionAgentError]:
    """Evaluate one account independently without submitting an order.

    Business/policy blocks are successful typed evaluations. Structurally invalid arguments return
    Failure. `EXECUTE` means the non-production Agent contract is locally ready; it does not submit,
    dispatch, retry, or bypass the repository's canonical pre-trade/execution boundaries.
    """

    expected_types = (
        (decision, CoreTradeDecision, "decision"),
        (security, DecisionSecurityAttestation, "security"),
        (binding, ClientTradingAccountBinding, "binding"),
        (account_policy, AccountPropPolicySnapshot, "account_policy"),
        (observed_state, ClientAccountObservedState, "observed_state"),
        (entitlement, ClientAgentEntitlementSnapshot, "entitlement"),
        (execution_policy, ClientExecutionPolicy, "execution_policy"),
        (calculation, ClientExecutionCalculation, "calculation"),
    )
    for value, expected_type, field_name in expected_types:
        if not isinstance(value, expected_type):
            return Failure(
                ClientExecutionAgentValidationError(
                    f"{field_name} must be {expected_type.__name__}"
                )
            )
    try:
        _validate_timestamp(evaluated_at, field_name="evaluated_at")
    except ClientExecutionAgentError as error:
        return Failure(error)

    decision_id = decision.decision.decision_id
    account_id = binding.account_id

    if (
        decision.decision.status is not DecisionStatus.RESOLVED
        or decision.decision.outcome is not DecisionOutcome.APPROVED
    ):
        return _blocked(
            decision_id,
            account_id,
            verdict=ClientExecutionVerdict.DECISION_BLOCKED,
            reason=ClientExecutionReason.CORE_DECISION_NOT_APPROVED,
            evaluated_at=evaluated_at,
        )
    if evaluated_at >= decision.expires_at:
        return _blocked(
            decision_id,
            account_id,
            verdict=ClientExecutionVerdict.DECISION_BLOCKED,
            reason=ClientExecutionReason.CORE_DECISION_EXPIRED,
            evaluated_at=evaluated_at,
        )

    if (
        security.decision_id != decision_id
        or security.account_id != account_id
        or security.runtime_ref != binding.runtime_ref
    ):
        return _blocked(
            decision_id,
            account_id,
            verdict=ClientExecutionVerdict.SECURITY_BLOCKED,
            reason=ClientExecutionReason.SECURITY_BINDING_MISMATCH,
            evaluated_at=evaluated_at,
        )
    if security.status is not DecisionSecurityStatus.VERIFIED:
        return _blocked(
            decision_id,
            account_id,
            verdict=ClientExecutionVerdict.SECURITY_BLOCKED,
            reason=ClientExecutionReason.SECURITY_NOT_VERIFIED,
            evaluated_at=evaluated_at,
        )
    if security.verified_at < decision.decision.timestamp or security.verified_at > evaluated_at:
        return _blocked(
            decision_id,
            account_id,
            verdict=ClientExecutionVerdict.SECURITY_BLOCKED,
            reason=ClientExecutionReason.SECURITY_ATTESTATION_INVALID_TIME,
            evaluated_at=evaluated_at,
        )
    if _age_seconds(newer=evaluated_at, older=security.verified_at) > (
        execution_policy.max_security_attestation_age_seconds
    ):
        return _blocked(
            decision_id,
            account_id,
            verdict=ClientExecutionVerdict.SECURITY_BLOCKED,
            reason=ClientExecutionReason.SECURITY_ATTESTATION_STALE,
            evaluated_at=evaluated_at,
        )

    if binding.lifecycle_state is not TradingAccountLifecycleState.ACTIVE:
        return _blocked(
            decision_id,
            account_id,
            verdict=ClientExecutionVerdict.ACCOUNT_BLOCKED,
            reason=ClientExecutionReason.ACCOUNT_NOT_ACTIVE,
            evaluated_at=evaluated_at,
        )

    if (
        account_policy.account_id != account_id
        or account_policy.policy_ref != binding.policy_ref
        or account_policy.account_kind != binding.account_kind
    ):
        return _blocked(
            decision_id,
            account_id,
            verdict=ClientExecutionVerdict.PROP_POLICY_BLOCKED,
            reason=ClientExecutionReason.ACCOUNT_POLICY_BINDING_MISMATCH,
            evaluated_at=evaluated_at,
        )
    if evaluated_at < account_policy.effective_at:
        return _blocked(
            decision_id,
            account_id,
            verdict=ClientExecutionVerdict.PROP_POLICY_BLOCKED,
            reason=ClientExecutionReason.ACCOUNT_POLICY_NOT_EFFECTIVE,
            evaluated_at=evaluated_at,
        )
    if account_policy.expires_at is not None and evaluated_at >= account_policy.expires_at:
        return _blocked(
            decision_id,
            account_id,
            verdict=ClientExecutionVerdict.PROP_POLICY_BLOCKED,
            reason=ClientExecutionReason.ACCOUNT_POLICY_EXPIRED,
            evaluated_at=evaluated_at,
        )
    if (
        not account_policy.is_complete_for_new_trading()
        or account_policy.max_drawdown.value == 0
        or account_policy.daily_loss_limit.value == 0
    ):
        return _blocked(
            decision_id,
            account_id,
            verdict=ClientExecutionVerdict.PROP_POLICY_BLOCKED,
            reason=ClientExecutionReason.ACCOUNT_POLICY_UNRESOLVED,
            evaluated_at=evaluated_at,
        )

    if observed_state.account_id != account_id:
        return _blocked(
            decision_id,
            account_id,
            verdict=ClientExecutionVerdict.UNRESOLVED,
            reason=ClientExecutionReason.ACCOUNT_STATE_BINDING_MISMATCH,
            evaluated_at=evaluated_at,
        )
    if observed_state.observed_at > evaluated_at:
        return _blocked(
            decision_id,
            account_id,
            verdict=ClientExecutionVerdict.UNRESOLVED,
            reason=ClientExecutionReason.ACCOUNT_STATE_INVALID_TIME,
            evaluated_at=evaluated_at,
        )
    if _age_seconds(newer=evaluated_at, older=observed_state.observed_at) > (
        execution_policy.max_account_state_age_seconds
    ):
        return _blocked(
            decision_id,
            account_id,
            verdict=ClientExecutionVerdict.UNRESOLVED,
            reason=ClientExecutionReason.ACCOUNT_STATE_STALE,
            evaluated_at=evaluated_at,
        )
    if observed_state.equity.currency != account_policy.account_size.currency:
        return _blocked(
            decision_id,
            account_id,
            verdict=ClientExecutionVerdict.UNRESOLVED,
            reason=ClientExecutionReason.ACCOUNT_CURRENCY_MISMATCH,
            evaluated_at=evaluated_at,
        )
    if observed_state.equity.amount <= 0:
        return _blocked(
            decision_id,
            account_id,
            verdict=ClientExecutionVerdict.RISK_BLOCKED,
            reason=ClientExecutionReason.ACCOUNT_EQUITY_NON_POSITIVE,
            evaluated_at=evaluated_at,
        )
    if observed_state.current_drawdown.value >= account_policy.max_drawdown.value:
        return _blocked(
            decision_id,
            account_id,
            verdict=ClientExecutionVerdict.RISK_BLOCKED,
            reason=ClientExecutionReason.MAX_DRAWDOWN_REACHED,
            evaluated_at=evaluated_at,
        )
    if observed_state.daily_loss.value >= account_policy.daily_loss_limit.value:
        return _blocked(
            decision_id,
            account_id,
            verdict=ClientExecutionVerdict.RISK_BLOCKED,
            reason=ClientExecutionReason.DAILY_LOSS_REACHED,
            evaluated_at=evaluated_at,
        )

    if (
        entitlement.account_id != account_id
        or entitlement.entitlement_ref != binding.product_entitlement_ref
    ):
        return _blocked(
            decision_id,
            account_id,
            verdict=ClientExecutionVerdict.ENTITLEMENT_BLOCKED,
            reason=ClientExecutionReason.ENTITLEMENT_BINDING_MISMATCH,
            evaluated_at=evaluated_at,
        )
    if entitlement.state is not ClientAgentEntitlementState.ENABLED:
        return _blocked(
            decision_id,
            account_id,
            verdict=ClientExecutionVerdict.ENTITLEMENT_BLOCKED,
            reason=ClientExecutionReason.ENTITLEMENT_NOT_ENABLED,
            evaluated_at=evaluated_at,
        )
    if entitlement.evaluated_at > evaluated_at:
        return _blocked(
            decision_id,
            account_id,
            verdict=ClientExecutionVerdict.ENTITLEMENT_BLOCKED,
            reason=ClientExecutionReason.ENTITLEMENT_INVALID_TIME,
            evaluated_at=evaluated_at,
        )
    if _age_seconds(newer=evaluated_at, older=entitlement.evaluated_at) > (
        execution_policy.max_entitlement_age_seconds
    ):
        return _blocked(
            decision_id,
            account_id,
            verdict=ClientExecutionVerdict.ENTITLEMENT_BLOCKED,
            reason=ClientExecutionReason.ENTITLEMENT_STALE,
            evaluated_at=evaluated_at,
        )

    if calculation.decision_id != decision_id or calculation.account_id != account_id:
        return _blocked(
            decision_id,
            account_id,
            verdict=ClientExecutionVerdict.UNRESOLVED,
            reason=ClientExecutionReason.CALCULATION_BINDING_MISMATCH,
            evaluated_at=evaluated_at,
        )
    if (
        calculation.calculated_at < observed_state.observed_at
        or calculation.calculated_at < security.verified_at
        or calculation.calculated_at > evaluated_at
    ):
        return _blocked(
            decision_id,
            account_id,
            verdict=ClientExecutionVerdict.UNRESOLVED,
            reason=ClientExecutionReason.CALCULATION_INVALID_TIME,
            evaluated_at=evaluated_at,
        )
    if (
        calculation.sizing_policy_ref != execution_policy.sizing_policy_ref
        or calculation.protection_policy_ref != execution_policy.protection_policy_ref
        or calculation.trailing_policy_ref != execution_policy.trailing_policy_ref
    ):
        return _blocked(
            decision_id,
            account_id,
            verdict=ClientExecutionVerdict.UNRESOLVED,
            reason=ClientExecutionReason.CALCULATION_POLICY_MISMATCH,
            evaluated_at=evaluated_at,
        )
    if calculation.estimated_risk.value > execution_policy.max_risk_per_trade.value:
        return _blocked(
            decision_id,
            account_id,
            verdict=ClientExecutionVerdict.RISK_BLOCKED,
            reason=ClientExecutionReason.CALCULATED_RISK_EXCEEDS_POLICY,
            evaluated_at=evaluated_at,
        )
    if (
        decision.order_type is OrderType.LIMIT
        and calculation.entry_reference_price != decision.limit_price
    ):
        return _blocked(
            decision_id,
            account_id,
            verdict=ClientExecutionVerdict.UNRESOLVED,
            reason=ClientExecutionReason.LIMIT_PRICE_MISMATCH,
            evaluated_at=evaluated_at,
        )
    if not _protection_geometry_is_valid(
        side=decision.side,
        entry=calculation.entry_reference_price,
        stop_loss=calculation.stop_loss,
        take_profit=calculation.take_profit,
    ):
        return _blocked(
            decision_id,
            account_id,
            verdict=ClientExecutionVerdict.RISK_BLOCKED,
            reason=ClientExecutionReason.INVALID_PROTECTION_GEOMETRY,
            evaluated_at=evaluated_at,
        )

    try:
        plan = ClientExecutionPlan(
            client_id=binding.client_id,
            account_id=account_id,
            decision_id=decision_id,
            instrument=decision.instrument,
            side=decision.side,
            order_type=decision.order_type,
            quantity=calculation.quantity,
            entry_reference_price=calculation.entry_reference_price,
            limit_price=decision.limit_price,
            stop_loss=calculation.stop_loss,
            take_profit=calculation.take_profit,
            trailing_policy_ref=calculation.trailing_policy_ref,
            account_policy_ref=account_policy.policy_ref,
            account_policy_snapshot_id=account_policy.snapshot_id,
            execution_policy_id=execution_policy.policy_id,
            sizing_policy_ref=calculation.sizing_policy_ref,
            protection_policy_ref=calculation.protection_policy_ref,
            entitlement_ref=entitlement.entitlement_ref,
            runtime_ref=binding.runtime_ref,
            account_observation_id=observed_state.observation_id,
            security_evidence_ref=security.evidence_ref,
            created_at=evaluated_at,
        )
        return Success(
            ClientExecutionEvaluation(
                decision_id=decision_id,
                account_id=account_id,
                verdict=ClientExecutionVerdict.EXECUTE,
                reason=ClientExecutionReason.READY,
                evaluated_at=evaluated_at,
                plan=plan,
            )
        )
    except ClientExecutionAgentError as error:
        return Failure(error)
