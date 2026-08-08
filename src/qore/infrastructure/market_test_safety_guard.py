from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from re import fullmatch

from qore.infrastructure.execution_boundary import (
    ExecutionBoundaryConflictError,
    ExecutionBoundaryError,
    ExecutionCancellation,
    ExecutionReceipt,
    ExecutionReceiptId,
    ExecutionSubmission,
)
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
    MarketTestAccountIdentity,
    MarketTestEnvironmentAuthorization,
)
from qore.infrastructure.order_intent import ExecutionInstrument
from qore.infrastructure.test_execution_adapter import AuthorizedTestExecutionAdapter
from qore.kernel.result import Failure, Result, Success


class MarketTestSafetyError(ExecutionBoundaryError):
    """Base error for MISSION-02 account/capital execution safety."""

    __slots__ = ()


class MarketTestSafetyValidationError(MarketTestSafetyError):
    """Violation of a market-test safety contract invariant."""

    __slots__ = ()


class MarketTestSafetyBlockedError(MarketTestSafetyError):
    """Typed fail-closed result when a test execution is not allowlisted."""

    __slots__ = ()


@dataclass(frozen=True, slots=True)
class MarketTestSafetyPolicy:
    """Explicit account, instrument and quantity limits for TEST/DEMO execution."""

    policy_id: str
    allowed_accounts: tuple[MarketTestAccountIdentity, ...]
    allowed_instruments: tuple[ExecutionInstrument, ...]
    max_order_quantity: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.policy_id, str) or fullmatch(
            r"[a-z][a-z0-9._-]*", self.policy_id
        ) is None:
            raise MarketTestSafetyValidationError(
                "market-test safety policy_id must use canonical lowercase syntax"
            )
        if not isinstance(self.allowed_accounts, tuple) or not self.allowed_accounts:
            raise MarketTestSafetyValidationError(
                "market-test safety allowed_accounts must be a non-empty tuple"
            )
        if any(
            not isinstance(account, MarketTestAccountIdentity)
            for account in self.allowed_accounts
        ):
            raise MarketTestSafetyValidationError(
                "market-test safety allowed_accounts entries must be account identities"
            )
        if any(
            account.environment
            not in {MarketRuntimeEnvironment.DEMO, MarketRuntimeEnvironment.TEST}
            for account in self.allowed_accounts
        ):
            raise MarketTestSafetyValidationError(
                "market-test safety policy may allow only TEST or DEMO accounts"
            )
        if len(set(self.allowed_accounts)) != len(self.allowed_accounts):
            raise MarketTestSafetyValidationError(
                "market-test safety allowed_accounts must not contain duplicates"
            )
        if tuple(
            sorted(self.allowed_accounts, key=lambda account: account.logical_values())
        ) != self.allowed_accounts:
            raise MarketTestSafetyValidationError(
                "market-test safety allowed_accounts must use stable sorted order"
            )
        if not isinstance(self.allowed_instruments, tuple) or not self.allowed_instruments:
            raise MarketTestSafetyValidationError(
                "market-test safety allowed_instruments must be a non-empty tuple"
            )
        if any(
            not isinstance(instrument, ExecutionInstrument)
            for instrument in self.allowed_instruments
        ):
            raise MarketTestSafetyValidationError(
                "market-test safety instruments must be ExecutionInstrument values"
            )
        if len(set(self.allowed_instruments)) != len(self.allowed_instruments):
            raise MarketTestSafetyValidationError(
                "market-test safety allowed_instruments must not contain duplicates"
            )
        if tuple(
            sorted(self.allowed_instruments, key=lambda instrument: instrument.value)
        ) != self.allowed_instruments:
            raise MarketTestSafetyValidationError(
                "market-test safety instruments must use stable sorted order"
            )
        if not isinstance(self.max_order_quantity, Decimal):
            raise MarketTestSafetyValidationError(
                "market-test safety max_order_quantity must be Decimal"
            )
        if (
            not self.max_order_quantity.is_finite()
            or self.max_order_quantity <= Decimal("0")
        ):
            raise MarketTestSafetyValidationError(
                "market-test safety max_order_quantity must be finite and positive"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.policy_id,
            tuple(account.logical_values() for account in self.allowed_accounts),
            tuple(instrument.value for instrument in self.allowed_instruments),
            format(self.max_order_quantity, "f"),
        )


@dataclass(frozen=True, slots=True)
class MarketTestSafetyPermit:
    """Immutable evidence that one exact submission passed the market-test guard."""

    policy_id: str
    account: MarketTestAccountIdentity
    instrument: ExecutionInstrument
    quantity: Decimal
    receipt_id: ExecutionReceiptId
    evaluated_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.policy_id, str) or not self.policy_id:
            raise MarketTestSafetyValidationError("safety permit policy_id must be non-empty")
        if not isinstance(self.account, MarketTestAccountIdentity):
            raise MarketTestSafetyValidationError(
                "safety permit account must be MarketTestAccountIdentity"
            )
        if self.account.environment not in {
            MarketRuntimeEnvironment.DEMO,
            MarketRuntimeEnvironment.TEST,
        }:
            raise MarketTestSafetyValidationError(
                "safety permit account must be TEST or DEMO"
            )
        if not isinstance(self.instrument, ExecutionInstrument):
            raise MarketTestSafetyValidationError(
                "safety permit instrument must be ExecutionInstrument"
            )
        if not isinstance(self.quantity, Decimal):
            raise MarketTestSafetyValidationError("safety permit quantity must be Decimal")
        if not self.quantity.is_finite() or self.quantity <= Decimal("0"):
            raise MarketTestSafetyValidationError(
                "safety permit quantity must be finite and positive"
            )
        if not isinstance(self.receipt_id, ExecutionReceiptId):
            raise MarketTestSafetyValidationError(
                "safety permit receipt_id must be ExecutionReceiptId"
            )
        if not isinstance(self.evaluated_at, datetime):
            raise MarketTestSafetyValidationError("safety permit evaluated_at must be datetime")
        if self.evaluated_at.tzinfo is None or self.evaluated_at.utcoffset() is None:
            raise MarketTestSafetyValidationError(
                "safety permit evaluated_at must be timezone-aware"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.policy_id,
            self.account.logical_values(),
            self.instrument.value,
            format(self.quantity, "f"),
            str(self.receipt_id.value),
            self.evaluated_at.isoformat(),
        )


def evaluate_market_test_safety(
    submission: ExecutionSubmission,
    *,
    environment_authorization: MarketTestEnvironmentAuthorization,
    policy: MarketTestSafetyPolicy,
    evaluated_at: datetime,
) -> Result[MarketTestSafetyPermit, MarketTestSafetyError]:
    """Evaluate all allowlists before any external execution gateway is called."""
    if not isinstance(submission, ExecutionSubmission):
        return Failure(
            MarketTestSafetyValidationError(
                "market-test safety evaluation requires ExecutionSubmission"
            )
        )
    if not isinstance(environment_authorization, MarketTestEnvironmentAuthorization):
        return Failure(
            MarketTestSafetyValidationError(
                "market-test safety evaluation requires environment authorization"
            )
        )
    if not isinstance(policy, MarketTestSafetyPolicy):
        return Failure(
            MarketTestSafetyValidationError(
                "market-test safety evaluation requires MarketTestSafetyPolicy"
            )
        )
    if not isinstance(evaluated_at, datetime):
        return Failure(
            MarketTestSafetyValidationError("market-test evaluated_at must be datetime")
        )
    if evaluated_at.tzinfo is None or evaluated_at.utcoffset() is None:
        return Failure(
            MarketTestSafetyValidationError(
                "market-test evaluated_at must be timezone-aware"
            )
        )
    if evaluated_at < environment_authorization.authorized_at:
        return Failure(
            MarketTestSafetyBlockedError(
                "market-test safety evaluation must not predate environment authorization"
            )
        )
    if evaluated_at < submission.authorized_intent.authorized_at:
        return Failure(
            MarketTestSafetyBlockedError(
                "market-test safety evaluation must not predate order authorization"
            )
        )

    account = environment_authorization.account
    intent = submission.authorized_intent.intent
    if account not in policy.allowed_accounts:
        return Failure(
            MarketTestSafetyBlockedError("market-test account is not allowlisted")
        )
    if intent.instrument not in policy.allowed_instruments:
        return Failure(
            MarketTestSafetyBlockedError("market-test instrument is not allowlisted")
        )
    if intent.quantity.value > policy.max_order_quantity:
        return Failure(
            MarketTestSafetyBlockedError(
                "market-test order quantity exceeds configured maximum"
            )
        )

    try:
        permit = MarketTestSafetyPermit(
            policy_id=policy.policy_id,
            account=account,
            instrument=intent.instrument,
            quantity=intent.quantity.value,
            receipt_id=submission.receipt_id,
            evaluated_at=evaluated_at,
        )
    except MarketTestSafetyError as error:
        return Failure(error)
    return Success(permit)


class SafetyGuardedTestExecutionBoundary:
    """Guard TEST/DEMO execution before delegating to the external adapter."""

    __slots__ = ("_adapter", "_permits", "_policy")

    def __init__(
        self,
        *,
        adapter: AuthorizedTestExecutionAdapter,
        policy: MarketTestSafetyPolicy,
    ) -> None:
        if not isinstance(adapter, AuthorizedTestExecutionAdapter):
            raise MarketTestSafetyValidationError(
                "safety-guarded boundary requires AuthorizedTestExecutionAdapter"
            )
        if not isinstance(policy, MarketTestSafetyPolicy):
            raise MarketTestSafetyValidationError(
                "safety-guarded boundary requires MarketTestSafetyPolicy"
            )
        self._adapter = adapter
        self._policy = policy
        self._permits: dict[ExecutionReceiptId, MarketTestSafetyPermit] = {}

    @property
    def adapter(self) -> AuthorizedTestExecutionAdapter:
        return self._adapter

    @property
    def policy(self) -> MarketTestSafetyPolicy:
        return self._policy

    @property
    def permits(self) -> tuple[MarketTestSafetyPermit, ...]:
        return tuple(
            self._permits[key]
            for key in sorted(self._permits, key=lambda item: str(item.value))
        )

    def submit(
        self,
        submission: ExecutionSubmission,
    ) -> Result[ExecutionReceipt, ExecutionBoundaryError]:
        permit_result = evaluate_market_test_safety(
            submission,
            environment_authorization=self.adapter.environment_authorization,
            policy=self.policy,
            evaluated_at=submission.submitted_at,
        )
        if isinstance(permit_result, Failure):
            return Failure(permit_result.error)

        prior_permit = self._permits.get(submission.receipt_id)
        if prior_permit is not None and prior_permit != permit_result.value:
            return Failure(
                ExecutionBoundaryConflictError(
                    "market-test safety receipt reused with different permit"
                )
            )

        execution_result = self.adapter.submit(submission)
        if isinstance(execution_result, Failure):
            return Failure(execution_result.error)
        self._permits[execution_result.value.receipt_id] = permit_result.value
        return Success(execution_result.value)

    def status(
        self,
        receipt_id: ExecutionReceiptId,
    ) -> Result[ExecutionReceipt | None, ExecutionBoundaryError]:
        return self.adapter.status(receipt_id)

    def cancel(
        self,
        cancellation: ExecutionCancellation,
    ) -> Result[ExecutionReceipt, ExecutionBoundaryError]:
        return self.adapter.cancel(cancellation)
