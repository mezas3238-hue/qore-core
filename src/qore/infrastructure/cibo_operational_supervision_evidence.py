from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from re import fullmatch
from typing import cast

from qore.infrastructure.cibo_supervised_runtime import (
    CiboSupervisionBlockedError,
    CiboSupervisionAuthorization,
    SupervisedCiboDecisionBoundary,
)
from qore.infrastructure.market_data import MarketDataSnapshotId
from qore.infrastructure.order_intent import OrderIntent, OrderIntentId
from qore.infrastructure.ports import ExternalPortError, ExternalRequestMetadata
from qore.infrastructure.real_market_decision_runtime import (
    RealMarketDecisionBoundary,
    RealMarketDecisionContext,
)
from qore.kernel.result import Failure, Result, Success

_SENSITIVE_PARTS = (
    "authorization:",
    "bearer ",
    "client_secret",
    "password=",
    "secret=",
    "token=",
)


class CiboOperationalSupervisionEvidenceError(ExternalPortError):
    """Base error for MISSION-03 CIBO supervision evidence preparation."""

    __slots__ = ()


class CiboOperationalSupervisionEvidenceValidationError(
    CiboOperationalSupervisionEvidenceError
):
    """A CIBO operational supervision evidence invariant was violated."""

    __slots__ = ()


class CiboOperationalSupervisionOutcome(StrEnum):
    BLOCKED = "blocked"
    NO_ACTION = "no-action"
    DELEGATED = "delegated"
    FAILED = "failed"


class CiboOperationalSupervisionReason(StrEnum):
    SUPERVISION_BLOCKED = "supervision.blocked"
    DECISION_NO_ACTION = "decision.no-action"
    DECISION_DELEGATED = "decision.delegated"
    DELEGATE_FAILED = "delegate.failed"


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise CiboOperationalSupervisionEvidenceValidationError(
            f"{field_name} must be datetime"
        )
    if value.tzinfo is None or value.utcoffset() is None:
        raise CiboOperationalSupervisionEvidenceValidationError(
            f"{field_name} must be timezone-aware"
        )


def _account_fingerprint(account_ref: str) -> str:
    digest = hashlib.sha256(account_ref.encode("utf-8")).hexdigest()
    return f"sha256:{digest[:24]}"


def _attempt_ref(
    *,
    correlation_id: str,
    snapshot_id: str,
    decided_at: datetime,
) -> str:
    raw = f"{correlation_id}|{snapshot_id}|{decided_at.isoformat()}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return f"sha256:{digest[:24]}"


def _validate_fingerprint(value: str, *, field_name: str) -> str:
    if not isinstance(value, str) or fullmatch(r"sha256:[0-9a-f]{24}", value) is None:
        raise CiboOperationalSupervisionEvidenceValidationError(
            f"{field_name} must be a truncated sha256 fingerprint"
        )
    return value


def _validate_public_code(value: str, *, field_name: str) -> str:
    if not isinstance(value, str) or fullmatch(r"[a-z][a-z0-9._-]*", value) is None:
        raise CiboOperationalSupervisionEvidenceValidationError(
            f"{field_name} must use canonical lowercase syntax"
        )
    normalized = value.lower()
    if any(part in normalized for part in _SENSITIVE_PARTS):
        raise CiboOperationalSupervisionEvidenceValidationError(
            f"{field_name} must not contain sensitive material"
        )
    return value


@dataclass(frozen=True, slots=True)
class CiboOperationalSupervisionRecord:
    """Sanitized evidence for one supervised CIBO decision attempt."""

    attempt_ref: str
    supervisor_id: str
    provider_key: str
    environment: str
    account_fingerprint: str
    market_snapshot_id: MarketDataSnapshotId
    instrument: str
    correlation_id: str
    decided_at: datetime
    supervision_expires_at: datetime
    outcome: CiboOperationalSupervisionOutcome
    reason: CiboOperationalSupervisionReason
    intent_id: OrderIntentId | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "attempt_ref",
            _validate_fingerprint(self.attempt_ref, field_name="attempt_ref"),
        )
        object.__setattr__(
            self,
            "supervisor_id",
            _validate_public_code(self.supervisor_id, field_name="supervisor_id"),
        )
        if self.provider_key != "oanda-v20":
            raise CiboOperationalSupervisionEvidenceValidationError(
                "CIBO operational supervision provider must be oanda-v20"
            )
        if self.environment not in {"test", "demo"}:
            raise CiboOperationalSupervisionEvidenceValidationError(
                "CIBO operational supervision environment must be TEST/DEMO"
            )
        object.__setattr__(
            self,
            "account_fingerprint",
            _validate_fingerprint(
                self.account_fingerprint,
                field_name="account_fingerprint",
            ),
        )
        if not isinstance(self.market_snapshot_id, MarketDataSnapshotId):
            raise CiboOperationalSupervisionEvidenceValidationError(
                "CIBO supervision record requires MarketDataSnapshotId"
            )
        if not isinstance(self.instrument, str) or fullmatch(
            r"[A-Z0-9][A-Z0-9._/-]*",
            self.instrument,
        ) is None:
            raise CiboOperationalSupervisionEvidenceValidationError(
                "CIBO supervision instrument must use canonical market syntax"
            )
        if not isinstance(self.correlation_id, str) or fullmatch(
            r"[0-9a-f-]{36}",
            self.correlation_id,
        ) is None:
            raise CiboOperationalSupervisionEvidenceValidationError(
                "CIBO supervision correlation id must be canonical UUID text"
            )
        _validate_timestamp(self.decided_at, field_name="decided_at")
        _validate_timestamp(
            self.supervision_expires_at,
            field_name="supervision_expires_at",
        )
        if self.supervision_expires_at < self.decided_at:
            if self.outcome is not CiboOperationalSupervisionOutcome.BLOCKED:
                raise CiboOperationalSupervisionEvidenceValidationError(
                    "expired supervision may only produce BLOCKED evidence"
                )
        if not isinstance(self.outcome, CiboOperationalSupervisionOutcome):
            raise CiboOperationalSupervisionEvidenceValidationError(
                "CIBO supervision record requires explicit outcome"
            )
        if not isinstance(self.reason, CiboOperationalSupervisionReason):
            raise CiboOperationalSupervisionEvidenceValidationError(
                "CIBO supervision record requires explicit reason"
            )
        expected_reasons = {
            CiboOperationalSupervisionOutcome.BLOCKED: (
                CiboOperationalSupervisionReason.SUPERVISION_BLOCKED
            ),
            CiboOperationalSupervisionOutcome.NO_ACTION: (
                CiboOperationalSupervisionReason.DECISION_NO_ACTION
            ),
            CiboOperationalSupervisionOutcome.DELEGATED: (
                CiboOperationalSupervisionReason.DECISION_DELEGATED
            ),
            CiboOperationalSupervisionOutcome.FAILED: (
                CiboOperationalSupervisionReason.DELEGATE_FAILED
            ),
        }
        if self.reason is not expected_reasons[self.outcome]:
            raise CiboOperationalSupervisionEvidenceValidationError(
                "CIBO supervision reason must match outcome"
            )
        if self.outcome is CiboOperationalSupervisionOutcome.DELEGATED:
            if not isinstance(self.intent_id, OrderIntentId):
                raise CiboOperationalSupervisionEvidenceValidationError(
                    "delegated CIBO supervision record requires intent id"
                )
        elif self.intent_id is not None:
            raise CiboOperationalSupervisionEvidenceValidationError(
                "non-delegated CIBO supervision record must not carry intent id"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.attempt_ref,
            self.supervisor_id,
            self.provider_key,
            self.environment,
            self.account_fingerprint,
            str(self.market_snapshot_id.value),
            self.instrument,
            self.correlation_id,
            self.decided_at.isoformat(),
            self.supervision_expires_at.isoformat(),
            self.outcome.value,
            self.reason.value,
            self.intent_id.logical_values() if self.intent_id is not None else None,
        )

    def public_payload(self) -> dict[str, object]:
        return {
            "attempt_ref": self.attempt_ref,
            "supervisor_id": self.supervisor_id,
            "provider": self.provider_key,
            "environment": self.environment,
            "account_fingerprint": self.account_fingerprint,
            "market_snapshot_id": str(self.market_snapshot_id.value),
            "instrument": self.instrument,
            "correlation_id": self.correlation_id,
            "decided_at": self.decided_at.isoformat(),
            "supervision_expires_at": self.supervision_expires_at.isoformat(),
            "outcome": self.outcome.value,
            "reason": self.reason.value,
            "intent_id": (
                str(self.intent_id.value) if self.intent_id is not None else None
            ),
        }


def _build_record(
    *,
    supervision: CiboSupervisionAuthorization,
    context: RealMarketDecisionContext,
    metadata: ExternalRequestMetadata,
    outcome: CiboOperationalSupervisionOutcome,
    reason: CiboOperationalSupervisionReason,
    intent: OrderIntent | None = None,
) -> CiboOperationalSupervisionRecord:
    account = supervision.environment_authorization.account
    correlation_id = str(metadata.correlation_id.value)
    snapshot_id = str(context.quote.snapshot_id.value)
    return CiboOperationalSupervisionRecord(
        attempt_ref=_attempt_ref(
            correlation_id=correlation_id,
            snapshot_id=snapshot_id,
            decided_at=context.decided_at,
        ),
        supervisor_id=supervision.supervisor_id.value,
        provider_key=account.provider_key,
        environment=account.environment.value,
        account_fingerprint=_account_fingerprint(account.account_ref),
        market_snapshot_id=context.quote.snapshot_id,
        instrument=context.quote.instrument.symbol,
        correlation_id=correlation_id,
        decided_at=context.decided_at,
        supervision_expires_at=supervision.expires_at,
        outcome=outcome,
        reason=reason,
        intent_id=intent.intent_id if intent is not None else None,
    )


class ObservedSupervisedCiboDecisionBoundary:
    """Supervised decision boundary that records sanitized evidence for every valid attempt."""

    __slots__ = ("_delegate", "_records", "_supervision")

    def __init__(
        self,
        *,
        delegate: RealMarketDecisionBoundary,
        supervision: CiboSupervisionAuthorization,
    ) -> None:
        if not isinstance(supervision, CiboSupervisionAuthorization):
            raise CiboOperationalSupervisionEvidenceValidationError(
                "observed CIBO boundary requires CiboSupervisionAuthorization"
            )
        if not callable(getattr(delegate, "decide", None)):
            raise CiboOperationalSupervisionEvidenceValidationError(
                "observed CIBO boundary requires RealMarketDecisionBoundary"
            )
        self._delegate = delegate
        self._supervision = supervision
        self._records: list[CiboOperationalSupervisionRecord] = []

    @property
    def supervision(self) -> CiboSupervisionAuthorization:
        return self._supervision

    @property
    def records(self) -> tuple[CiboOperationalSupervisionRecord, ...]:
        return tuple(self._records)

    def decide(
        self,
        context: RealMarketDecisionContext,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[OrderIntent | None, ExternalPortError]:
        if not isinstance(context, RealMarketDecisionContext):
            return Failure(
                CiboOperationalSupervisionEvidenceValidationError(
                    "observed CIBO decision requires RealMarketDecisionContext"
                )
            )
        if not isinstance(metadata, ExternalRequestMetadata):
            return Failure(
                CiboOperationalSupervisionEvidenceValidationError(
                    "observed CIBO decision requires ExternalRequestMetadata"
                )
            )
        supervised = SupervisedCiboDecisionBoundary(
            delegate=self._delegate,
            supervision=self.supervision,
        )
        result = supervised.decide(context, metadata=metadata)
        if isinstance(result, Failure):
            if isinstance(result.error, CiboSupervisionBlockedError):
                outcome = CiboOperationalSupervisionOutcome.BLOCKED
                reason = CiboOperationalSupervisionReason.SUPERVISION_BLOCKED
            else:
                outcome = CiboOperationalSupervisionOutcome.FAILED
                reason = CiboOperationalSupervisionReason.DELEGATE_FAILED
            try:
                record = _build_record(
                    supervision=self.supervision,
                    context=context,
                    metadata=metadata,
                    outcome=outcome,
                    reason=reason,
                )
            except CiboOperationalSupervisionEvidenceError as error:
                return Failure(error)
            self._records.append(record)
            return Failure(result.error)
        intent = result.value
        if intent is None:
            outcome = CiboOperationalSupervisionOutcome.NO_ACTION
            reason = CiboOperationalSupervisionReason.DECISION_NO_ACTION
        else:
            outcome = CiboOperationalSupervisionOutcome.DELEGATED
            reason = CiboOperationalSupervisionReason.DECISION_DELEGATED
        try:
            record = _build_record(
                supervision=self.supervision,
                context=context,
                metadata=metadata,
                outcome=outcome,
                reason=reason,
                intent=cast(OrderIntent | None, intent),
            )
        except CiboOperationalSupervisionEvidenceError as error:
            return Failure(error)
        self._records.append(record)
        return Success(intent)
