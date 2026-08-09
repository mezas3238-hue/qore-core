from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from uuid import UUID

from qore.functional.decisions import DecisionId
from qore.infrastructure.client_accounts import TradingAccountId
from qore.infrastructure.client_position_lifecycle import (
    ClientPositionActionId,
    ClientPositionActionKind,
    ClientPositionId,
    ClientPositionLifecycle,
    ClientPositionState,
)
from qore.infrastructure.proprietary_accounts import CurrencyCode, MoneyAmount
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success


class ClientPerformanceLedgerError(InfrastructureError):
    """Base error for account-scoped client performance accounting."""

    __slots__ = ()


class ClientPerformanceLedgerValidationError(ClientPerformanceLedgerError):
    """Violation of a performance-ledger invariant."""

    __slots__ = ()


class ClientPerformanceLedgerConflictError(ClientPerformanceLedgerError):
    """A requested append conflicts with existing immutable ledger evidence."""

    __slots__ = ()


def _validate_uuid(value: UUID, *, field_name: str) -> None:
    if not isinstance(value, UUID):
        raise ClientPerformanceLedgerValidationError(f"{field_name} must be UUID")


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise ClientPerformanceLedgerValidationError(f"{field_name} must be datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ClientPerformanceLedgerValidationError(
            f"{field_name} must be timezone-aware"
        )


@dataclass(frozen=True, slots=True)
class ClientPerformanceRecordId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="client performance record id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ClientPerformanceEvidenceReference:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="client performance evidence reference")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ClientPayoutEvidenceReference:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="client payout evidence reference")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ClientPayoutPolicyReference:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="client payout policy reference")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ClientRealizedPerformanceRecord:
    """One closed-position realized result. Positive and negative P&L are valid."""

    record_id: ClientPerformanceRecordId
    account_id: TradingAccountId
    position_id: ClientPositionId
    decision_id: DecisionId
    exit_action_id: ClientPositionActionId
    realized_pnl: MoneyAmount
    realized_at: datetime
    evidence_ref: ClientPerformanceEvidenceReference

    def __post_init__(self) -> None:
        if not isinstance(self.record_id, ClientPerformanceRecordId):
            raise ClientPerformanceLedgerValidationError(
                "realized record_id must be ClientPerformanceRecordId"
            )
        if not isinstance(self.account_id, TradingAccountId):
            raise ClientPerformanceLedgerValidationError(
                "realized account_id must be TradingAccountId"
            )
        if not isinstance(self.position_id, ClientPositionId):
            raise ClientPerformanceLedgerValidationError(
                "realized position_id must be ClientPositionId"
            )
        if not isinstance(self.decision_id, DecisionId) or not isinstance(
            self.decision_id.value, UUID
        ):
            raise ClientPerformanceLedgerValidationError(
                "realized decision_id must be UUID-backed DecisionId"
            )
        if not isinstance(self.exit_action_id, ClientPositionActionId):
            raise ClientPerformanceLedgerValidationError(
                "realized exit_action_id must be ClientPositionActionId"
            )
        if not isinstance(self.realized_pnl, MoneyAmount):
            raise ClientPerformanceLedgerValidationError(
                "realized_pnl must be MoneyAmount"
            )
        _validate_timestamp(self.realized_at, field_name="realized_at")
        if not isinstance(self.evidence_ref, ClientPerformanceEvidenceReference):
            raise ClientPerformanceLedgerValidationError(
                "realized evidence_ref must be ClientPerformanceEvidenceReference"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.record_id.logical_values(),
            self.account_id.logical_values(),
            self.position_id.logical_values(),
            str(self.decision_id.value),
            self.exit_action_id.logical_values(),
            self.realized_pnl.logical_values(),
            self.realized_at.isoformat(),
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class ClientPerformanceCorrectionRecord:
    """Append-only delta correction; the original result is never rewritten."""

    record_id: ClientPerformanceRecordId
    account_id: TradingAccountId
    corrects_record_id: ClientPerformanceRecordId
    adjustment: MoneyAmount
    corrected_at: datetime
    evidence_ref: ClientPerformanceEvidenceReference

    def __post_init__(self) -> None:
        if not isinstance(self.record_id, ClientPerformanceRecordId):
            raise ClientPerformanceLedgerValidationError(
                "correction record_id must be ClientPerformanceRecordId"
            )
        if not isinstance(self.account_id, TradingAccountId):
            raise ClientPerformanceLedgerValidationError(
                "correction account_id must be TradingAccountId"
            )
        if not isinstance(self.corrects_record_id, ClientPerformanceRecordId):
            raise ClientPerformanceLedgerValidationError(
                "correction corrects_record_id must be ClientPerformanceRecordId"
            )
        if self.record_id == self.corrects_record_id:
            raise ClientPerformanceLedgerValidationError(
                "correction cannot correct itself"
            )
        if not isinstance(self.adjustment, MoneyAmount):
            raise ClientPerformanceLedgerValidationError(
                "correction adjustment must be MoneyAmount"
            )
        if self.adjustment.amount == 0:
            raise ClientPerformanceLedgerValidationError(
                "correction adjustment must be non-zero"
            )
        _validate_timestamp(self.corrected_at, field_name="corrected_at")
        if not isinstance(self.evidence_ref, ClientPerformanceEvidenceReference):
            raise ClientPerformanceLedgerValidationError(
                "correction evidence_ref must be ClientPerformanceEvidenceReference"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.record_id.logical_values(),
            self.account_id.logical_values(),
            self.corrects_record_id.logical_values(),
            self.adjustment.logical_values(),
            self.corrected_at.isoformat(),
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class ClientEntitledProfitRecord:
    """Profit contractually attributable to the client, not proof of payment."""

    record_id: ClientPerformanceRecordId
    account_id: TradingAccountId
    amount: MoneyAmount
    payout_policy_ref: ClientPayoutPolicyReference
    evaluated_at: datetime
    evidence_ref: ClientPerformanceEvidenceReference

    def __post_init__(self) -> None:
        _validate_profit_record_common(
            self.record_id,
            self.account_id,
            self.amount,
            self.evaluated_at,
        )
        if not isinstance(self.payout_policy_ref, ClientPayoutPolicyReference):
            raise ClientPerformanceLedgerValidationError(
                "entitled profit requires ClientPayoutPolicyReference"
            )
        if not isinstance(self.evidence_ref, ClientPerformanceEvidenceReference):
            raise ClientPerformanceLedgerValidationError(
                "entitled profit evidence must be ClientPerformanceEvidenceReference"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.record_id.logical_values(),
            self.account_id.logical_values(),
            self.amount.logical_values(),
            self.payout_policy_ref.logical_values(),
            self.evaluated_at.isoformat(),
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class ClientPaidProfitRecord:
    """Client payout proven by explicit external payout evidence."""

    record_id: ClientPerformanceRecordId
    account_id: TradingAccountId
    entitlement_record_id: ClientPerformanceRecordId
    amount: MoneyAmount
    paid_at: datetime
    payout_evidence_ref: ClientPayoutEvidenceReference

    def __post_init__(self) -> None:
        _validate_profit_record_common(
            self.record_id,
            self.account_id,
            self.amount,
            self.paid_at,
        )
        if not isinstance(self.entitlement_record_id, ClientPerformanceRecordId):
            raise ClientPerformanceLedgerValidationError(
                "paid profit requires entitlement_record_id"
            )
        if not isinstance(self.payout_evidence_ref, ClientPayoutEvidenceReference):
            raise ClientPerformanceLedgerValidationError(
                "paid profit requires ClientPayoutEvidenceReference"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.record_id.logical_values(),
            self.account_id.logical_values(),
            self.entitlement_record_id.logical_values(),
            self.amount.logical_values(),
            self.paid_at.isoformat(),
            self.payout_evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class EligibleClientPaidProfitRecord:
    """Verified paid client profit eligible for a later QORE performance fee."""

    record_id: ClientPerformanceRecordId
    account_id: TradingAccountId
    paid_profit_record_id: ClientPerformanceRecordId
    amount: MoneyAmount
    payout_policy_ref: ClientPayoutPolicyReference
    evaluated_at: datetime
    evidence_ref: ClientPerformanceEvidenceReference

    def __post_init__(self) -> None:
        _validate_profit_record_common(
            self.record_id,
            self.account_id,
            self.amount,
            self.evaluated_at,
        )
        if not isinstance(self.paid_profit_record_id, ClientPerformanceRecordId):
            raise ClientPerformanceLedgerValidationError(
                "eligible paid profit requires paid_profit_record_id"
            )
        if not isinstance(self.payout_policy_ref, ClientPayoutPolicyReference):
            raise ClientPerformanceLedgerValidationError(
                "eligible paid profit requires ClientPayoutPolicyReference"
            )
        if not isinstance(self.evidence_ref, ClientPerformanceEvidenceReference):
            raise ClientPerformanceLedgerValidationError(
                "eligible paid profit evidence must be ClientPerformanceEvidenceReference"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.record_id.logical_values(),
            self.account_id.logical_values(),
            self.paid_profit_record_id.logical_values(),
            self.amount.logical_values(),
            self.payout_policy_ref.logical_values(),
            self.evaluated_at.isoformat(),
            self.evidence_ref.logical_values(),
        )


def _validate_profit_record_common(
    record_id: ClientPerformanceRecordId,
    account_id: TradingAccountId,
    amount: MoneyAmount,
    event_at: datetime,
) -> None:
    if not isinstance(record_id, ClientPerformanceRecordId):
        raise ClientPerformanceLedgerValidationError(
            "profit record_id must be ClientPerformanceRecordId"
        )
    if not isinstance(account_id, TradingAccountId):
        raise ClientPerformanceLedgerValidationError(
            "profit account_id must be TradingAccountId"
        )
    if not isinstance(amount, MoneyAmount) or amount.amount <= 0:
        raise ClientPerformanceLedgerValidationError(
            "profit amount must be a positive MoneyAmount"
        )
    _validate_timestamp(event_at, field_name="profit event timestamp")


@dataclass(frozen=True, slots=True)
class ClientPerformanceLedger:
    """Immutable account-scoped append-only performance ledger."""

    account_id: TradingAccountId
    currency: CurrencyCode
    realized: tuple[ClientRealizedPerformanceRecord, ...] = ()
    corrections: tuple[ClientPerformanceCorrectionRecord, ...] = ()
    entitled: tuple[ClientEntitledProfitRecord, ...] = ()
    paid: tuple[ClientPaidProfitRecord, ...] = ()
    eligible_paid: tuple[EligibleClientPaidProfitRecord, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.account_id, TradingAccountId):
            raise ClientPerformanceLedgerValidationError(
                "ledger account_id must be TradingAccountId"
            )
        if not isinstance(self.currency, CurrencyCode):
            raise ClientPerformanceLedgerValidationError(
                "ledger currency must be CurrencyCode"
            )
        all_records: tuple[object, ...] = (
            *self.realized,
            *self.corrections,
            *self.entitled,
            *self.paid,
            *self.eligible_paid,
        )
        ids: set[ClientPerformanceRecordId] = set()
        for record in all_records:
            record_id = getattr(record, "record_id", None)
            account_id = getattr(record, "account_id", None)
            amount = getattr(record, "amount", None)
            if record_id in ids:
                raise ClientPerformanceLedgerValidationError(
                    "ledger record ids must be globally unique"
                )
            if not isinstance(record_id, ClientPerformanceRecordId):
                raise ClientPerformanceLedgerValidationError(
                    "ledger contains unsupported record"
                )
            ids.add(record_id)
            if account_id != self.account_id:
                raise ClientPerformanceLedgerValidationError(
                    "ledger records must remain account-scoped"
                )
            money = (
                record.realized_pnl
                if isinstance(record, ClientRealizedPerformanceRecord)
                else record.adjustment
                if isinstance(record, ClientPerformanceCorrectionRecord)
                else amount
            )
            if not isinstance(money, MoneyAmount) or money.currency != self.currency:
                raise ClientPerformanceLedgerValidationError(
                    "ledger records must use ledger currency"
                )
        self._validate_lineage()

    def _validate_lineage(self) -> None:
        realized_by_id = {record.record_id: record for record in self.realized}
        entitled_by_id = {record.record_id: record for record in self.entitled}
        paid_by_id = {record.record_id: record for record in self.paid}
        for correction in self.corrections:
            corrected = realized_by_id.get(correction.corrects_record_id)
            if corrected is None:
                raise ClientPerformanceLedgerValidationError(
                    "correction must reference an existing realized record"
                )
            if correction.corrected_at < corrected.realized_at:
                raise ClientPerformanceLedgerValidationError(
                    "correction must not predate corrected realized record"
                )
        for paid in self.paid:
            entitlement = entitled_by_id.get(paid.entitlement_record_id)
            if entitlement is None:
                raise ClientPerformanceLedgerValidationError(
                    "paid profit must reference an existing entitlement"
                )
            if paid.paid_at < entitlement.evaluated_at:
                raise ClientPerformanceLedgerValidationError(
                    "paid profit must not predate entitlement"
                )
            if paid.amount.currency != entitlement.amount.currency:
                raise ClientPerformanceLedgerValidationError(
                    "paid profit currency must match entitlement"
                )
            if paid.amount.amount > entitlement.amount.amount:
                raise ClientPerformanceLedgerValidationError(
                    "paid profit cannot exceed client entitlement"
                )
        for eligible in self.eligible_paid:
            paid = paid_by_id.get(eligible.paid_profit_record_id)
            if paid is None:
                raise ClientPerformanceLedgerValidationError(
                    "eligible paid profit must reference an existing paid record"
                )
            if eligible.evaluated_at < paid.paid_at:
                raise ClientPerformanceLedgerValidationError(
                    "eligible paid profit must not predate verified payout"
                )
            if eligible.amount.amount > paid.amount.amount:
                raise ClientPerformanceLedgerValidationError(
                    "eligible paid profit cannot exceed verified client payout"
                )

    @property
    def net_realized_pnl(self) -> MoneyAmount:
        amount = sum((record.realized_pnl.amount for record in self.realized), start=0)
        amount += sum((record.adjustment.amount for record in self.corrections), start=0)
        return MoneyAmount(currency=self.currency, amount=amount)

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.account_id.logical_values(),
            self.currency.logical_values(),
            tuple(record.logical_values() for record in self.realized),
            tuple(record.logical_values() for record in self.corrections),
            tuple(record.logical_values() for record in self.entitled),
            tuple(record.logical_values() for record in self.paid),
            tuple(record.logical_values() for record in self.eligible_paid),
        )


def append_realized_performance(
    ledger: ClientPerformanceLedger,
    lifecycle: ClientPositionLifecycle,
    *,
    record_id: ClientPerformanceRecordId,
    realized_pnl: MoneyAmount,
    evidence_ref: ClientPerformanceEvidenceReference,
    recorded_at: datetime,
) -> Result[ClientPerformanceLedger, ClientPerformanceLedgerError]:
    """Append one closed-position realized result without calculating provider P&L."""

    if not isinstance(ledger, ClientPerformanceLedger):
        return Failure(ClientPerformanceLedgerValidationError("ledger is required"))
    if not isinstance(lifecycle, ClientPositionLifecycle):
        return Failure(
            ClientPerformanceLedgerValidationError("closed position lifecycle is required")
        )
    if lifecycle.state is not ClientPositionState.CLOSED or lifecycle.closed_at is None:
        return Failure(
            ClientPerformanceLedgerValidationError(
                "realized performance requires CLOSED position lifecycle"
            )
        )
    if lifecycle.plan.account_id != ledger.account_id:
        return Failure(
            ClientPerformanceLedgerValidationError(
                "realized position account does not match ledger"
            )
        )
    if not isinstance(realized_pnl, MoneyAmount) or realized_pnl.currency != ledger.currency:
        return Failure(
            ClientPerformanceLedgerValidationError(
                "realized P&L must use ledger currency"
            )
        )
    try:
        _validate_timestamp(recorded_at, field_name="realized recorded_at")
        if recorded_at < lifecycle.closed_at:
            raise ClientPerformanceLedgerValidationError(
                "realized record must not predate position close"
            )
        exit_action = lifecycle.actions[-1]
        if exit_action.kind is not ClientPositionActionKind.EXIT:
            raise ClientPerformanceLedgerValidationError(
                "closed lifecycle must end with EXIT action"
            )
        record = ClientRealizedPerformanceRecord(
            record_id=record_id,
            account_id=ledger.account_id,
            position_id=lifecycle.position_id,
            decision_id=lifecycle.plan.decision_id,
            exit_action_id=exit_action.action_id,
            realized_pnl=realized_pnl,
            realized_at=recorded_at,
            evidence_ref=evidence_ref,
        )
        if any(existing.position_id == record.position_id for existing in ledger.realized):
            raise ClientPerformanceLedgerConflictError(
                "position already has a realized performance record"
            )
        return Success(replace(ledger, realized=(*ledger.realized, record)))
    except ClientPerformanceLedgerError as error:
        return Failure(error)


def append_performance_correction(
    ledger: ClientPerformanceLedger,
    correction: ClientPerformanceCorrectionRecord,
) -> Result[ClientPerformanceLedger, ClientPerformanceLedgerError]:
    return _append_typed(ledger, correction, "corrections")


def append_entitled_profit(
    ledger: ClientPerformanceLedger,
    record: ClientEntitledProfitRecord,
) -> Result[ClientPerformanceLedger, ClientPerformanceLedgerError]:
    return _append_typed(ledger, record, "entitled")


def append_paid_profit(
    ledger: ClientPerformanceLedger,
    record: ClientPaidProfitRecord,
) -> Result[ClientPerformanceLedger, ClientPerformanceLedgerError]:
    return _append_typed(ledger, record, "paid")


def append_eligible_paid_profit(
    ledger: ClientPerformanceLedger,
    record: EligibleClientPaidProfitRecord,
) -> Result[ClientPerformanceLedger, ClientPerformanceLedgerError]:
    return _append_typed(ledger, record, "eligible_paid")


def _append_typed(
    ledger: ClientPerformanceLedger,
    record: object,
    field_name: str,
) -> Result[ClientPerformanceLedger, ClientPerformanceLedgerError]:
    if not isinstance(ledger, ClientPerformanceLedger):
        return Failure(ClientPerformanceLedgerValidationError("ledger is required"))
    try:
        current = getattr(ledger, field_name)
        candidate = replace(ledger, **{field_name: (*current, record)})
        return Success(candidate)
    except (ClientPerformanceLedgerError, TypeError) as error:
        if isinstance(error, ClientPerformanceLedgerError):
            return Failure(error)
        return Failure(
            ClientPerformanceLedgerValidationError(
                f"unsupported performance record for {field_name}"
            )
        )
