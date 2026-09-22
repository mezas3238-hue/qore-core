"""Canonical FundedNext Stellar Instant MT5 provider gateway.

This module reuses QORE's provider-neutral execution contracts.  It never creates
strategy or capital authority: callers must provide a canonical
``ExecutionSubmission`` that already contains pre-trade authorization and the
global execution switch.  ``AuthorizedTestExecutionAdapter`` owns canonical
idempotency; this gateway owns broker-specific preflight, durable mutation
fencing and unknown-outcome recovery.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from typing import Protocol

from qore.infrastructure.execution_boundary import (
    ExecutionBoundaryConflictError,
    ExecutionBoundaryError,
    ExecutionBoundaryNotFoundError,
    ExecutionStatus,
    ExecutionSubmission,
)
from qore.infrastructure.fundednext_execution_bridge import extract_risk_provenance
from qore.infrastructure.fundednext_mt5_mutation_ledger import (
    FundedNextMt5MutationLedger,
    FundedNextMt5MutationLedgerError,
    FundedNextMt5MutationRecord,
    FundedNextMt5MutationState,
    fundednext_submission_digest,
)
from qore.infrastructure.fundednext_stellar_instant import (
    StellarInstantRuleVerification,
    resolve_pilot_symbol,
)
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
    MarketTestAccountIdentity,
)
from qore.infrastructure.order_intent import OrderSide, OrderType
from qore.infrastructure.test_execution_adapter import TestExecutionGatewayReceipt
from qore.kernel.result import Failure, Result, Success

_PROVIDER_KEY = "fundednext-stellar-instant-mt5"


class Mt5ExecutionError(ExecutionBoundaryError):
    """FundedNext MT5 execution failed closed."""

    __slots__ = ()


class Mt5ExecutionValidationError(Mt5ExecutionError):
    """Provider/account/order/specification invariant is invalid."""

    __slots__ = ()


class Mt5ExecutionBlockedError(Mt5ExecutionError):
    """Provider mutation is not currently authorized or safe."""

    __slots__ = ()


class Mt5ExecutionOutcomeUnknownError(Mt5ExecutionError):
    """Provider mutation outcome is ambiguous and requires reconciliation."""

    __slots__ = ()


class Mt5ExecutionRejectedError(Mt5ExecutionError):
    """Provider definitively rejected the requested mutation."""

    __slots__ = ()


class Mt5ProviderOutcome(StrEnum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class Mt5AccountState:
    balance: Decimal
    equity: Decimal
    margin: Decimal
    free_margin: Decimal
    observed_at: datetime

    def __post_init__(self) -> None:
        for name, value in (
            ("balance", self.balance),
            ("equity", self.equity),
            ("margin", self.margin),
            ("free_margin", self.free_margin),
        ):
            _nonnegative(value, name)
        _aware(self.observed_at, "observed_at")


@dataclass(frozen=True, slots=True)
class Mt5SymbolSpecification:
    provider_symbol: str
    bid: Decimal
    ask: Decimal
    spread_points: Decimal
    digits: int
    point: Decimal
    contract_size: Decimal
    tick_size: Decimal
    tick_value: Decimal
    minimum_volume: Decimal
    maximum_volume: Decimal
    volume_step: Decimal
    minimum_stop_distance_points: Decimal
    freeze_level_points: Decimal
    margin_per_volume: Decimal
    trade_enabled: bool
    session_open: bool
    observed_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.provider_symbol, str) or not self.provider_symbol:
            raise Mt5ExecutionValidationError("provider_symbol must be non-empty")
        for name, value in (
            ("bid", self.bid),
            ("ask", self.ask),
            ("point", self.point),
            ("contract_size", self.contract_size),
            ("tick_size", self.tick_size),
            ("tick_value", self.tick_value),
            ("minimum_volume", self.minimum_volume),
            ("maximum_volume", self.maximum_volume),
            ("volume_step", self.volume_step),
            ("margin_per_volume", self.margin_per_volume),
        ):
            _positive(value, name)
        for name, value in (
            ("spread_points", self.spread_points),
            ("minimum_stop_distance_points", self.minimum_stop_distance_points),
            ("freeze_level_points", self.freeze_level_points),
        ):
            _nonnegative(value, name)
        if self.ask < self.bid:
            raise Mt5ExecutionValidationError("ask cannot be below bid")
        if type(self.digits) is not int or self.digits < 0:
            raise Mt5ExecutionValidationError("digits must be non-negative int")
        if self.maximum_volume < self.minimum_volume:
            raise Mt5ExecutionValidationError(
                "maximum_volume cannot be below minimum_volume"
            )
        _aware(self.observed_at, "observed_at")


@dataclass(frozen=True, slots=True)
class FundedNextMt5OrderPlan:
    client_order_id: str
    qore_symbol: str
    provider_symbol: str
    side: OrderSide
    order_type: OrderType
    volume: Decimal
    effective_entry: Decimal
    limit_price: Decimal | None
    stop_loss: Decimal
    take_profit: Decimal
    margin_required: Decimal
    planned_at: datetime

    def __post_init__(self) -> None:
        if not self.client_order_id.startswith("qore-"):
            raise Mt5ExecutionValidationError(
                "client_order_id must use deterministic QORE namespace"
            )
        if type(self.side) is not OrderSide or type(self.order_type) is not OrderType:
            raise Mt5ExecutionValidationError("plan side/type must be canonical")
        for name, value in (
            ("volume", self.volume),
            ("effective_entry", self.effective_entry),
            ("stop_loss", self.stop_loss),
            ("take_profit", self.take_profit),
            ("margin_required", self.margin_required),
        ):
            _positive(value, name)
        if self.limit_price is not None:
            _positive(self.limit_price, "limit_price")
        _aware(self.planned_at, "planned_at")


@dataclass(frozen=True, slots=True)
class FundedNextMt5TransportReceipt:
    client_order_id: str
    outcome: Mt5ProviderOutcome
    recorded_at: datetime
    provider_order_ref: str | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.client_order_id, str) or not self.client_order_id:
            raise Mt5ExecutionValidationError("transport client_order_id is required")
        if type(self.outcome) is not Mt5ProviderOutcome:
            raise Mt5ExecutionValidationError("transport outcome must be canonical")
        _aware(self.recorded_at, "recorded_at")
        if self.outcome in {Mt5ProviderOutcome.ACCEPTED, Mt5ProviderOutcome.CANCELLED}:
            if not self.provider_order_ref:
                raise Mt5ExecutionValidationError(
                    "accepted/cancelled transport result requires provider order ref"
                )
        if self.reason is not None and not self.reason:
            raise Mt5ExecutionValidationError("transport reason must be non-empty or None")


class FundedNextMt5TransportBoundary(Protocol):
    """Secret-bearing MT5 client injected outside repository configuration."""

    def connected(self) -> bool: ...

    def account_state(self, account_ref: str) -> Mt5AccountState | None: ...

    def symbol_info(self, provider_symbol: str) -> Mt5SymbolSpecification | None: ...

    def submit_order(
        self,
        plan: FundedNextMt5OrderPlan,
    ) -> FundedNextMt5TransportReceipt: ...

    def cancel_order(
        self,
        provider_order_ref: str,
        *,
        client_order_id: str,
        cancelled_at: datetime,
    ) -> FundedNextMt5TransportReceipt: ...

    def discover_order(
        self,
        client_order_id: str,
    ) -> FundedNextMt5TransportReceipt | None: ...


class FundedNextMt5ExecutionGateway:
    """Broker-specific gateway behind QORE's AuthorizedTestExecutionAdapter."""

    def __init__(
        self,
        *,
        account: MarketTestAccountIdentity,
        transport: FundedNextMt5TransportBoundary,
        mutation_ledger: FundedNextMt5MutationLedger,
        rule_verification: StellarInstantRuleVerification,
        owner_submission_enabled: bool = False,
        max_spec_age: timedelta = timedelta(seconds=10),
        max_spread_points: Decimal | None = None,
    ) -> None:
        _validate_account(account)
        if not isinstance(rule_verification, StellarInstantRuleVerification):
            raise Mt5ExecutionValidationError(
                "Stellar Instant rule verification must be explicit"
            )
        if max_spec_age <= timedelta(0):
            raise Mt5ExecutionValidationError("max_spec_age must be positive")
        if max_spread_points is not None:
            _nonnegative(max_spread_points, "max_spread_points")
        for method in (
            "connected",
            "account_state",
            "symbol_info",
            "submit_order",
            "cancel_order",
            "discover_order",
        ):
            if not callable(getattr(transport, method, None)):
                raise Mt5ExecutionValidationError(
                    f"FundedNext MT5 transport requires {method}"
                )
        if not callable(getattr(mutation_ledger, "records", None)) or not callable(
            getattr(mutation_ledger, "upsert", None)
        ):
            raise Mt5ExecutionValidationError(
                "FundedNext MT5 gateway requires a durable mutation ledger port"
            )
        self._account = account
        self._transport = transport
        self._ledger = mutation_ledger
        self._rules = rule_verification
        self._owner_submission_enabled = owner_submission_enabled
        self._max_spec_age = max_spec_age
        self._max_spread_points = max_spread_points
        self._records: dict[str, FundedNextMt5MutationRecord] = {}
        self._restore_records()

    @property
    def account(self) -> MarketTestAccountIdentity:
        return self._account

    @property
    def has_unresolved_mutations(self) -> bool:
        return any(
            record.state
            in {
                FundedNextMt5MutationState.ATTEMPT_STARTED,
                FundedNextMt5MutationState.OUTCOME_UNKNOWN,
            }
            for record in self._records.values()
        )

    def read_account(self, *, now: datetime) -> Mt5AccountState:
        _aware(now, "now")
        if not self._transport.connected():
            raise Mt5ExecutionBlockedError("mt5-disconnected")
        state = self._transport.account_state(self._account.account_ref)
        if state is None:
            raise Mt5ExecutionBlockedError("mt5-account-state-unavailable")
        _fresh(state.observed_at, now, self._max_spec_age, "account-state")
        return state

    def read_symbol(self, qore_symbol: str, *, now: datetime) -> Mt5SymbolSpecification:
        _aware(now, "now")
        if not self._transport.connected():
            raise Mt5ExecutionBlockedError("mt5-disconnected")
        provider_symbol = resolve_pilot_symbol(qore_symbol)
        spec = self._transport.symbol_info(provider_symbol)
        if spec is None:
            raise Mt5ExecutionBlockedError("mt5-symbol-info-missing")
        if spec.provider_symbol != provider_symbol:
            raise Mt5ExecutionValidationError("mt5-symbol-alias-mismatch")
        _fresh(spec.observed_at, now, self._max_spec_age, "symbol-info")
        if not spec.trade_enabled or not spec.session_open:
            raise Mt5ExecutionBlockedError("mt5-symbol-not-tradable")
        if self._max_spread_points is not None and spec.spread_points > self._max_spread_points:
            raise Mt5ExecutionBlockedError("spread-outside-operational-containment")
        return spec

    def plan_submission(
        self,
        submission: ExecutionSubmission,
        *,
        now: datetime,
    ) -> FundedNextMt5OrderPlan:
        """Construct exact broker plan for READ_ONLY/SHADOW without mutation."""

        if not isinstance(submission, ExecutionSubmission):
            raise Mt5ExecutionValidationError(
                "MT5 plan requires canonical ExecutionSubmission"
            )
        _aware(now, "now")
        if now < submission.submitted_at:
            raise Mt5ExecutionValidationError("plan time cannot predate submission")
        if now > submission.authorized_intent.authorization.expires_at:
            raise Mt5ExecutionBlockedError("canonical pre-trade authorization expired")
        intent = submission.authorized_intent.intent
        spec = self.read_symbol(intent.instrument.value, now=now)
        self._validate_volume(intent.quantity.value, spec)
        if intent.stop_loss is None or intent.take_profit is None:
            raise Mt5ExecutionValidationError("FundedNext order requires SL and TP")
        if intent.order_type is OrderType.LIMIT:
            if intent.limit_price is None:
                raise Mt5ExecutionValidationError("limit order requires limit price")
            effective_entry = intent.limit_price.value
            limit_price = intent.limit_price.value
        else:
            effective_entry = spec.ask if intent.side is OrderSide.BUY else spec.bid
            limit_price = None
        stop_loss = intent.stop_loss.value
        take_profit = intent.take_profit.value
        self._validate_geometry(
            side=intent.side,
            entry=effective_entry,
            stop=stop_loss,
            target=take_profit,
            spec=spec,
        )
        margin_required = intent.quantity.value * spec.margin_per_volume
        account = self.read_account(now=now)
        if margin_required > account.free_margin:
            raise Mt5ExecutionBlockedError("insufficient-mt5-free-margin")
        return FundedNextMt5OrderPlan(
            client_order_id=_client_order_id(submission),
            qore_symbol=intent.instrument.value,
            provider_symbol=spec.provider_symbol,
            side=intent.side,
            order_type=intent.order_type,
            volume=intent.quantity.value,
            effective_entry=effective_entry,
            limit_price=limit_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            margin_required=margin_required,
            planned_at=now,
        )

    def submit(
        self,
        *,
        account: MarketTestAccountIdentity,
        submission: ExecutionSubmission,
    ) -> Result[TestExecutionGatewayReceipt, ExecutionBoundaryError]:
        """Perform at most one provider create attempt for one canonical submission."""

        if account != self._account:
            return Failure(Mt5ExecutionValidationError("MT5 account binding mismatch"))
        if not isinstance(submission, ExecutionSubmission):
            return Failure(
                Mt5ExecutionValidationError(
                    "MT5 submit requires canonical ExecutionSubmission"
                )
            )
        now = submission.submitted_at
        if not self._owner_submission_enabled:
            return Failure(
                Mt5ExecutionBlockedError(
                    "owner-order-submission-authorization-disabled"
                )
            )
        if self.has_unresolved_mutations:
            return Failure(
                Mt5ExecutionOutcomeUnknownError(
                    "unresolved-provider-state-suspends-new-orders"
                )
            )
        try:
            plan = self.plan_submission(submission, now=now)
            key = str(submission.idempotency_key.value)
            digest = fundednext_submission_digest(submission)
            prior = self._records.get(key)
            if prior is not None:
                return self._replay_prior_submission(prior, digest)
            risk_id, risk_fingerprint, reservation_id = extract_risk_provenance(
                submission
            )
            record = FundedNextMt5MutationRecord(
                idempotency_key=key,
                receipt_id=str(submission.receipt_id.value),
                submission_digest=digest,
                client_order_id=plan.client_order_id,
                state=FundedNextMt5MutationState.ATTEMPT_STARTED,
                transitioned_at=now,
                risk_authorization_id=risk_id,
                risk_authorization_fingerprint=risk_fingerprint,
                risk_reservation_id=reservation_id,
            )
            if not self._rules.automated_mt5_allowed(now):
                return Failure(
                    Mt5ExecutionBlockedError(
                        "fundednext-automation-rules-not-current-and-verified"
                    )
                )
            self._persist(record)
            outcome = self._transport.submit_order(plan)
            if outcome.client_order_id != plan.client_order_id:
                unknown = record.transition(
                    state=FundedNextMt5MutationState.OUTCOME_UNKNOWN,
                    transitioned_at=outcome.recorded_at,
                    reason="provider-client-order-id-mismatch",
                )
                self._persist(unknown)
                return Failure(
                    Mt5ExecutionOutcomeUnknownError(
                        "provider acknowledgement identity mismatch; reconcile first"
                    )
                )
            return self._apply_submit_outcome(record, outcome)
        except (Mt5ExecutionError, FundedNextMt5MutationLedgerError) as error:
            return Failure(error)

    def cancel(
        self,
        *,
        account: MarketTestAccountIdentity,
        provider_execution_ref: str,
        cancelled_at: datetime,
    ) -> Result[TestExecutionGatewayReceipt, ExecutionBoundaryError]:
        if account != self._account:
            return Failure(Mt5ExecutionValidationError("MT5 account binding mismatch"))
        _aware(cancelled_at, "cancelled_at")
        if not self._owner_submission_enabled:
            return Failure(
                Mt5ExecutionBlockedError(
                    "owner-order-submission-authorization-disabled"
                )
            )
        record = next(
            (
                item
                for item in self._records.values()
                if item.provider_order_ref == provider_execution_ref
            ),
            None,
        )
        if record is None:
            return Failure(ExecutionBoundaryNotFoundError("MT5 order not found"))
        if record.state is FundedNextMt5MutationState.CANCELLED:
            return Success(
                TestExecutionGatewayReceipt(
                    provider_execution_ref=provider_execution_ref,
                    status=ExecutionStatus.CANCELLED,
                    recorded_at=record.transitioned_at,
                )
            )
        if record.state is not FundedNextMt5MutationState.ACCEPTED:
            return Failure(
                Mt5ExecutionOutcomeUnknownError(
                    "MT5 order cannot cancel before accepted state is reconciled"
                )
            )
        try:
            outcome = self._transport.cancel_order(
                provider_execution_ref,
                client_order_id=record.client_order_id,
                cancelled_at=cancelled_at,
            )
            if outcome.outcome is Mt5ProviderOutcome.CANCELLED:
                if outcome.provider_order_ref != provider_execution_ref:
                    unknown = record.transition(
                        state=FundedNextMt5MutationState.OUTCOME_UNKNOWN,
                        transitioned_at=outcome.recorded_at,
                        reason="cancel-provider-reference-mismatch",
                    )
                    self._persist(unknown)
                    return Failure(
                        Mt5ExecutionOutcomeUnknownError(
                            "cancellation acknowledgement mismatch; reconcile first"
                        )
                    )
                cancelled = record.transition(
                    state=FundedNextMt5MutationState.CANCELLED,
                    transitioned_at=outcome.recorded_at,
                    provider_order_ref=provider_execution_ref,
                )
                self._persist(cancelled)
                return Success(
                    TestExecutionGatewayReceipt(
                        provider_execution_ref=provider_execution_ref,
                        status=ExecutionStatus.CANCELLED,
                        recorded_at=outcome.recorded_at,
                    )
                )
            unknown = record.transition(
                state=FundedNextMt5MutationState.OUTCOME_UNKNOWN,
                transitioned_at=outcome.recorded_at,
                provider_order_ref=provider_execution_ref,
                reason=outcome.reason or "cancel-outcome-unknown",
            )
            self._persist(unknown)
            return Failure(
                Mt5ExecutionOutcomeUnknownError(
                    "cancellation outcome is not definitive; reconcile first"
                )
            )
        except FundedNextMt5MutationLedgerError as error:
            return Failure(error)

    def discover_unknown_outcome(
        self,
        submission: ExecutionSubmission,
    ) -> Result[TestExecutionGatewayReceipt, ExecutionBoundaryError]:
        """Discover original order by deterministic client id; never resubmit it."""

        if not isinstance(submission, ExecutionSubmission):
            return Failure(
                Mt5ExecutionValidationError(
                    "unknown-outcome recovery requires canonical submission"
                )
            )
        key = str(submission.idempotency_key.value)
        record = self._records.get(key)
        if record is None:
            return Failure(ExecutionBoundaryNotFoundError("mutation record not found"))
        if record.submission_digest != fundednext_submission_digest(submission):
            return Failure(
                ExecutionBoundaryConflictError(
                    "recovery submission conflicts with durable digest"
                )
            )
        if record.state is FundedNextMt5MutationState.ACCEPTED:
            assert record.provider_order_ref is not None
            return Success(
                TestExecutionGatewayReceipt(
                    provider_execution_ref=record.provider_order_ref,
                    status=ExecutionStatus.ACCEPTED,
                    recorded_at=record.transitioned_at,
                )
            )
        if record.state is FundedNextMt5MutationState.CANCELLED:
            assert record.provider_order_ref is not None
            return Success(
                TestExecutionGatewayReceipt(
                    provider_execution_ref=record.provider_order_ref,
                    status=ExecutionStatus.CANCELLED,
                    recorded_at=record.transitioned_at,
                )
            )
        if record.state is FundedNextMt5MutationState.REJECTED:
            return Failure(Mt5ExecutionRejectedError("provider definitively rejected order"))
        outcome = self._transport.discover_order(record.client_order_id)
        if outcome is None or outcome.outcome is Mt5ProviderOutcome.UNKNOWN:
            return Failure(
                Mt5ExecutionOutcomeUnknownError(
                    "provider order remains unresolved; new orders stay suspended"
                )
            )
        if outcome.client_order_id != record.client_order_id:
            return Failure(
                Mt5ExecutionOutcomeUnknownError(
                    "discovered provider identity does not match durable client order id"
                )
            )
        try:
            if outcome.outcome is Mt5ProviderOutcome.ACCEPTED:
                if outcome.provider_order_ref is None:
                    return Failure(
                        Mt5ExecutionOutcomeUnknownError(
                            "accepted discovery is missing provider order reference"
                        )
                    )
                accepted = record.transition(
                    state=FundedNextMt5MutationState.ACCEPTED,
                    transitioned_at=outcome.recorded_at,
                    provider_order_ref=outcome.provider_order_ref,
                )
                self._persist(accepted)
                return Success(
                    TestExecutionGatewayReceipt(
                        provider_execution_ref=outcome.provider_order_ref,
                        status=ExecutionStatus.ACCEPTED,
                        recorded_at=outcome.recorded_at,
                    )
                )
            if outcome.outcome is Mt5ProviderOutcome.CANCELLED:
                if outcome.provider_order_ref is None:
                    return Failure(
                        Mt5ExecutionOutcomeUnknownError(
                            "cancelled discovery is missing provider order reference"
                        )
                    )
                cancelled = record.transition(
                    state=FundedNextMt5MutationState.CANCELLED,
                    transitioned_at=outcome.recorded_at,
                    provider_order_ref=outcome.provider_order_ref,
                )
                self._persist(cancelled)
                return Success(
                    TestExecutionGatewayReceipt(
                        provider_execution_ref=outcome.provider_order_ref,
                        status=ExecutionStatus.CANCELLED,
                        recorded_at=outcome.recorded_at,
                    )
                )
            rejected = record.transition(
                state=FundedNextMt5MutationState.REJECTED,
                transitioned_at=outcome.recorded_at,
                reason=outcome.reason or "provider-rejected",
            )
            self._persist(rejected)
            return Failure(Mt5ExecutionRejectedError("provider definitively rejected order"))
        except FundedNextMt5MutationLedgerError as error:
            return Failure(error)

    def _restore_records(self) -> None:
        try:
            for record in self._ledger.records():
                if record.idempotency_key in self._records:
                    raise Mt5ExecutionValidationError(
                        "durable MT5 ledger contains duplicate idempotency key"
                    )
                restored = record
                if record.state is FundedNextMt5MutationState.ATTEMPT_STARTED:
                    restored = record.transition(
                        state=FundedNextMt5MutationState.OUTCOME_UNKNOWN,
                        transitioned_at=record.transitioned_at,
                        reason="process-restarted-after-durable-mutation-fence",
                    )
                    self._ledger.upsert(restored)
                self._records[restored.idempotency_key] = restored
        except FundedNextMt5MutationLedgerError as error:
            raise Mt5ExecutionValidationError(
                "durable FundedNext MT5 mutation ledger could not be restored"
            ) from error

    def _persist(self, record: FundedNextMt5MutationRecord) -> None:
        self._ledger.upsert(record)
        self._records[record.idempotency_key] = record

    def _replay_prior_submission(
        self,
        prior: FundedNextMt5MutationRecord,
        digest: str,
    ) -> Result[TestExecutionGatewayReceipt, ExecutionBoundaryError]:
        if prior.submission_digest != digest:
            return Failure(
                ExecutionBoundaryConflictError(
                    "MT5 idempotency key reused with different canonical submission"
                )
            )
        if prior.state is FundedNextMt5MutationState.ACCEPTED:
            assert prior.provider_order_ref is not None
            return Success(
                TestExecutionGatewayReceipt(
                    provider_execution_ref=prior.provider_order_ref,
                    status=ExecutionStatus.ACCEPTED,
                    recorded_at=prior.transitioned_at,
                )
            )
        if prior.state is FundedNextMt5MutationState.REJECTED:
            return Failure(Mt5ExecutionRejectedError("provider definitively rejected order"))
        if prior.state is FundedNextMt5MutationState.CANCELLED:
            return Failure(
                ExecutionBoundaryConflictError(
                    "cancelled MT5 order cannot be submitted again"
                )
            )
        return Failure(
            Mt5ExecutionOutcomeUnknownError(
                "durable provider mutation is unresolved; reconcile first"
            )
        )

    def _apply_submit_outcome(
        self,
        record: FundedNextMt5MutationRecord,
        outcome: FundedNextMt5TransportReceipt,
    ) -> Result[TestExecutionGatewayReceipt, ExecutionBoundaryError]:
        try:
            if outcome.outcome is Mt5ProviderOutcome.ACCEPTED:
                if outcome.provider_order_ref is None:
                    unknown = record.transition(
                        state=FundedNextMt5MutationState.OUTCOME_UNKNOWN,
                        transitioned_at=outcome.recorded_at,
                        reason="accepted-outcome-missing-provider-reference",
                    )
                    self._persist(unknown)
                    return Failure(
                        Mt5ExecutionOutcomeUnknownError(
                            "accepted provider outcome missing order reference"
                        )
                    )
                accepted = record.transition(
                    state=FundedNextMt5MutationState.ACCEPTED,
                    transitioned_at=outcome.recorded_at,
                    provider_order_ref=outcome.provider_order_ref,
                )
                self._persist(accepted)
                return Success(
                    TestExecutionGatewayReceipt(
                        provider_execution_ref=outcome.provider_order_ref,
                        status=ExecutionStatus.ACCEPTED,
                        recorded_at=outcome.recorded_at,
                    )
                )
            if outcome.outcome is Mt5ProviderOutcome.REJECTED:
                rejected = record.transition(
                    state=FundedNextMt5MutationState.REJECTED,
                    transitioned_at=outcome.recorded_at,
                    reason=outcome.reason or "provider-rejected",
                )
                self._persist(rejected)
                return Failure(
                    Mt5ExecutionRejectedError("provider definitively rejected order")
                )
            unknown = record.transition(
                state=FundedNextMt5MutationState.OUTCOME_UNKNOWN,
                transitioned_at=outcome.recorded_at,
                provider_order_ref=outcome.provider_order_ref,
                reason=outcome.reason or "provider-outcome-unknown",
            )
            self._persist(unknown)
            return Failure(
                Mt5ExecutionOutcomeUnknownError(
                    "provider outcome is ambiguous; reconcile before any new order"
                )
            )
        except FundedNextMt5MutationLedgerError as error:
            return Failure(error)

    @staticmethod
    def _validate_volume(volume: Decimal, spec: Mt5SymbolSpecification) -> None:
        _positive(volume, "authorized_volume")
        if not spec.minimum_volume <= volume <= spec.maximum_volume:
            raise Mt5ExecutionBlockedError("authorized-volume-outside-broker-range")
        units = volume / spec.volume_step
        if units != units.to_integral_value():
            raise Mt5ExecutionBlockedError("authorized-volume-not-on-broker-step")

    @staticmethod
    def _validate_geometry(
        *,
        side: OrderSide,
        entry: Decimal,
        stop: Decimal,
        target: Decimal,
        spec: Mt5SymbolSpecification,
    ) -> None:
        if side is OrderSide.BUY:
            if not stop < entry < target:
                raise Mt5ExecutionBlockedError("invalid-long-order-geometry")
        elif side is OrderSide.SELL:
            if not target < entry < stop:
                raise Mt5ExecutionBlockedError("invalid-short-order-geometry")
        else:
            raise Mt5ExecutionValidationError("unsupported canonical order side")
        minimum_distance = spec.minimum_stop_distance_points * spec.point
        if abs(entry - stop) < minimum_distance:
            raise Mt5ExecutionBlockedError("stop-inside-broker-minimum-distance")
        if abs(target - entry) < minimum_distance:
            raise Mt5ExecutionBlockedError("target-inside-broker-minimum-distance")


def _client_order_id(submission: ExecutionSubmission) -> str:
    return f"qore-{submission.idempotency_key.value.hex[:24]}"


def _validate_account(account: MarketTestAccountIdentity) -> None:
    if not isinstance(account, MarketTestAccountIdentity):
        raise Mt5ExecutionValidationError("MT5 account identity must be explicit")
    if account.provider_key != _PROVIDER_KEY:
        raise Mt5ExecutionValidationError(
            "MT5 account must use fundednext-stellar-instant-mt5 provider key"
        )
    if account.environment not in {
        MarketRuntimeEnvironment.DEMO,
        MarketRuntimeEnvironment.TEST,
    }:
        raise Mt5ExecutionValidationError(
            "FundedNext simulated proprietary account must remain TEST/DEMO in QORE"
        )


def _fresh(observed_at: datetime, now: datetime, max_age: timedelta, name: str) -> None:
    _aware(observed_at, f"{name}.observed_at")
    if observed_at > now:
        raise Mt5ExecutionValidationError(f"{name}-timestamp-from-future")
    if now - observed_at > max_age:
        raise Mt5ExecutionBlockedError(f"{name}-stale")


def _aware(value: datetime, name: str) -> None:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise Mt5ExecutionValidationError(f"{name} must be timezone-aware")


def _positive(value: Decimal, name: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite() or value <= 0:
        raise Mt5ExecutionValidationError(f"{name} must be positive finite Decimal")


def _nonnegative(value: Decimal, name: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
        raise Mt5ExecutionValidationError(
            f"{name} must be non-negative finite Decimal"
        )
