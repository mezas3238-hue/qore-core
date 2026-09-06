from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Protocol

from qore.infrastructure.ctrader_demo_execution_codec import (
    CTraderOrderCancelPlan,
    CTraderOrderCreatePlan,
    build_ctrader_demo_order_cancel_plan,
    build_ctrader_demo_order_create_plan,
    build_ctrader_demo_submit_gateway_receipt,
    decode_ctrader_demo_fill_observation,
    decode_ctrader_demo_order_cancel_response,
    decode_ctrader_demo_order_create_response,
    decode_ctrader_demo_order_query_response,
)
from qore.infrastructure.ctrader_demo_execution_configuration import (
    CTraderDemoCapability,
    CTraderDemoRuntimeConfiguration,
)
from qore.infrastructure.ctrader_demo_execution_contracts import (
    CTraderDemoAttemptState,
    CTraderDemoExecutionConflictError,
    CTraderDemoExecutionNotAcceptedError,
    CTraderDemoExecutionOutcome,
    CTraderDemoExecutionUnknownOutcomeError,
    CTraderDemoFillObservation,
    CTraderDemoFillReconciliation,
    CTraderDemoMutationAttempt,
    CTraderDemoOrderDisposition,
    reconcile_ctrader_demo_fills,
    transition_ctrader_demo_attempt,
)
from qore.infrastructure.execution_boundary import (
    ExecutionBoundaryError,
    ExecutionBoundaryNotFoundError,
    ExecutionReceiptId,
    ExecutionStatus,
    ExecutionSubmission,
)
from qore.infrastructure.execution_reconciliation import (
    ExecutionObservation,
    ExecutionReconciliationError,
)
from qore.infrastructure.market_test_environment import MarketTestAccountIdentity
from qore.infrastructure.order_intent import ExecutionIdempotencyKey
from qore.infrastructure.ports import ExternalRequestMetadata
from qore.infrastructure.test_execution_adapter import TestExecutionGatewayReceipt
from qore.infrastructure.transport import ExternalTransportResponse
from qore.kernel.result import Failure, Result, Success

_ACCEPTED_DISPOSITIONS = frozenset(
    {
        CTraderDemoOrderDisposition.ACCEPTED,
        CTraderDemoOrderDisposition.PARTIALLY_FILLED,
        CTraderDemoOrderDisposition.FILLED,
    }
)


class CTraderDemoExecutionGatewayError(ExecutionBoundaryError):
    """Base error for the cTrader DEMO execution gateway."""

    __slots__ = ()


class CTraderDemoExecutionGatewayValidationError(CTraderDemoExecutionGatewayError):
    """Violation of a cTrader DEMO execution gateway invariant."""

    __slots__ = ()


class CTraderDemoExecutionTransportBoundary(Protocol):
    """Injected cTrader DEMO write transport that owns connection/auth lifecycle."""

    @property
    def configuration(self) -> CTraderDemoRuntimeConfiguration: ...

    def submit_order(
        self,
        plan: CTraderOrderCreatePlan,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[ExternalTransportResponse, ExecutionBoundaryError]:
        """Perform at most one provider create request for the supplied plan."""
        ...

    def cancel_order(
        self,
        plan: CTraderOrderCancelPlan,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[ExternalTransportResponse, ExecutionBoundaryError]:
        """Perform at most one provider cancellation request for the supplied plan."""
        ...

    def query_order(
        self,
        provider_order_ref: str,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[ExternalTransportResponse, ExecutionBoundaryError]:
        """Perform at most one provider order-state query for reconciliation."""
        ...


class CTraderDemoExecutionGateway:
    """Compose canonical TEST/DEMO execution with an injected cTrader DEMO transport."""

    __slots__ = (
        "_attempts",
        "_authoritative_filled",
        "_configuration",
        "_fill_complete",
        "_fills_by_receipt",
        "_metadata_by_provider_ref",
        "_outcomes_by_receipt",
        "_outcomes_by_provider_ref",
        "_receipt_ids",
        "_receipts",
        "_reject_errors",
        "_submissions",
        "_transport",
    )

    def __init__(
        self,
        *,
        configuration: CTraderDemoRuntimeConfiguration,
        transport: CTraderDemoExecutionTransportBoundary,
    ) -> None:
        if not isinstance(configuration, CTraderDemoRuntimeConfiguration):
            raise CTraderDemoExecutionGatewayValidationError(
                "cTrader execution gateway requires CTraderDemoRuntimeConfiguration"
            )
        if CTraderDemoCapability.ORDERS not in configuration.capabilities:
            raise CTraderDemoExecutionGatewayValidationError(
                "cTrader execution gateway requires orders capability"
            )
        transport_configuration = getattr(transport, "configuration", None)
        if transport_configuration != configuration:
            raise CTraderDemoExecutionGatewayValidationError(
                "cTrader transport configuration must match gateway"
            )
        if not callable(getattr(transport, "submit_order", None)):
            raise CTraderDemoExecutionGatewayValidationError(
                "cTrader transport requires submit_order"
            )
        if not callable(getattr(transport, "cancel_order", None)):
            raise CTraderDemoExecutionGatewayValidationError(
                "cTrader transport requires cancel_order"
            )
        if not callable(getattr(transport, "query_order", None)):
            raise CTraderDemoExecutionGatewayValidationError(
                "cTrader transport requires query_order"
            )
        self._configuration = configuration
        self._transport = transport
        self._attempts: dict[ExecutionIdempotencyKey, CTraderDemoMutationAttempt] = {}
        self._receipt_ids: set[ExecutionReceiptId] = set()
        self._receipts: dict[ExecutionReceiptId, TestExecutionGatewayReceipt] = {}
        self._reject_errors: dict[ExecutionReceiptId, CTraderDemoExecutionNotAcceptedError] = {}
        self._submissions: dict[ExecutionReceiptId, ExecutionSubmission] = {}
        self._outcomes_by_receipt: dict[ExecutionReceiptId, CTraderDemoExecutionOutcome] = {}
        self._outcomes_by_provider_ref: dict[str, CTraderDemoExecutionOutcome] = {}
        self._metadata_by_provider_ref: dict[str, ExternalRequestMetadata] = {}
        self._fills_by_receipt: dict[ExecutionReceiptId, dict[str, CTraderDemoFillObservation]] = {}
        self._authoritative_filled: dict[ExecutionReceiptId, Decimal] = {}
        self._fill_complete: dict[ExecutionReceiptId, bool] = {}

    @property
    def configuration(self) -> CTraderDemoRuntimeConfiguration:
        return self._configuration

    @property
    def attempts(self) -> tuple[CTraderDemoMutationAttempt, ...]:
        return tuple(
            self._attempts[key] for key in sorted(self._attempts, key=lambda item: str(item.value))
        )

    @property
    def outcomes(self) -> tuple[CTraderDemoExecutionOutcome, ...]:
        return tuple(
            self._outcomes_by_provider_ref[key] for key in sorted(self._outcomes_by_provider_ref)
        )

    def _record_unknown(
        self,
        key: ExecutionIdempotencyKey,
        submission: ExecutionSubmission,
        *,
        reason: str,
    ) -> None:
        self._attempts[key] = CTraderDemoMutationAttempt(
            idempotency_key=key,
            receipt_id=submission.receipt_id,
            submission_logical=submission.logical_values(),
            state=CTraderDemoAttemptState.OUTCOME_UNKNOWN,
            transitioned_at=submission.submitted_at,
            reason=reason,
        )

    def submit(
        self,
        *,
        account: MarketTestAccountIdentity,
        submission: ExecutionSubmission,
    ) -> Result[TestExecutionGatewayReceipt, ExecutionBoundaryError]:
        if account != self._configuration.account:
            return Failure(
                CTraderDemoExecutionGatewayValidationError(
                    "gateway submit account must match cTrader DEMO configuration"
                )
            )
        if not isinstance(submission, ExecutionSubmission):
            return Failure(
                CTraderDemoExecutionGatewayValidationError(
                    "gateway submit requires ExecutionSubmission"
                )
            )
        key = submission.idempotency_key
        prior = self._attempts.get(key)
        if prior is not None:
            if prior.submission_logical != submission.logical_values():
                return Failure(
                    CTraderDemoExecutionConflictError(
                        "cTrader idempotency key reused with different submission"
                    )
                )
            if prior.state is CTraderDemoAttemptState.DEFINITIVE_OUTCOME:
                receipt = self._receipts.get(prior.receipt_id)
                if receipt is not None:
                    return Success(receipt)
                reject = self._reject_errors.get(prior.receipt_id)
                if reject is not None:
                    return Failure(reject)
                return Failure(
                    CTraderDemoExecutionGatewayValidationError(
                        "definitive attempt missing its gateway receipt"
                    )
                )
            if prior.state is CTraderDemoAttemptState.RESOLVED:
                receipt = self._receipts.get(prior.receipt_id)
                if receipt is not None:
                    return Success(receipt)
                return Failure(
                    CTraderDemoExecutionConflictError(
                        "cTrader execution already resolved; resubmission prohibited"
                    )
                )
            return Failure(
                CTraderDemoExecutionUnknownOutcomeError(
                    "cTrader execution has an unresolved mutating attempt; "
                    "reconciliation is required before any resubmission"
                )
            )
        if submission.receipt_id in self._receipt_ids:
            return Failure(
                CTraderDemoExecutionConflictError("cTrader execution receipt id already exists")
            )

        plan_result = build_ctrader_demo_order_create_plan(
            self._configuration,
            submission,
        )
        if isinstance(plan_result, Failure):
            return Failure(plan_result.error)
        plan = plan_result.value

        self._receipt_ids.add(submission.receipt_id)
        self._submissions[submission.receipt_id] = submission

        metadata = submission.authorized_intent.intent.metadata
        response_result = self._transport.submit_order(plan, metadata=metadata)
        if isinstance(response_result, Failure):
            self._record_unknown(
                key,
                submission,
                reason="provider transport failure after mutating attempt",
            )
            return Failure(
                CTraderDemoExecutionUnknownOutcomeError(
                    "cTrader mutating attempt reached an indeterminate outcome; "
                    "reconciliation is required"
                )
            )

        outcome_result = decode_ctrader_demo_order_create_response(
            self._configuration,
            submission,
            plan,
            response_result.value,
        )
        if isinstance(outcome_result, Failure):
            self._record_unknown(
                key,
                submission,
                reason="malformed provider response after possible effect",
            )
            return Failure(
                CTraderDemoExecutionUnknownOutcomeError(
                    "cTrader provider response could not be definitively decoded; "
                    "reconciliation is required"
                )
            )

        outcome = outcome_result.value
        if outcome.provider_order_ref in self._outcomes_by_provider_ref:
            self._record_unknown(
                key,
                submission,
                reason="provider order reference already observed",
            )
            return Failure(
                CTraderDemoExecutionUnknownOutcomeError(
                    "cTrader provider order reference was already observed; "
                    "reconciliation is required"
                )
            )

        self._attempts[key] = CTraderDemoMutationAttempt(
            idempotency_key=key,
            receipt_id=submission.receipt_id,
            submission_logical=submission.logical_values(),
            state=CTraderDemoAttemptState.DEFINITIVE_OUTCOME,
            transitioned_at=outcome.recorded_at,
            provider_order_ref=outcome.provider_order_ref,
            reason=outcome.disposition.value,
        )
        self._outcomes_by_receipt[submission.receipt_id] = outcome
        self._outcomes_by_provider_ref[outcome.provider_order_ref] = outcome
        self._metadata_by_provider_ref[outcome.provider_order_ref] = metadata

        if outcome.disposition not in _ACCEPTED_DISPOSITIONS:
            reject = CTraderDemoExecutionNotAcceptedError(
                f"cTrader order was not accepted: {outcome.disposition.value}"
            )
            self._reject_errors[submission.receipt_id] = reject
            return Failure(reject)
        receipt_result = build_ctrader_demo_submit_gateway_receipt(outcome)
        if isinstance(receipt_result, Failure):
            return Failure(receipt_result.error)
        receipt = receipt_result.value
        self._receipts[submission.receipt_id] = receipt
        return Success(receipt)

    def cancel(
        self,
        *,
        account: MarketTestAccountIdentity,
        provider_execution_ref: str,
        cancelled_at: datetime,
    ) -> Result[TestExecutionGatewayReceipt, ExecutionBoundaryError]:
        if account != self._configuration.account:
            return Failure(
                CTraderDemoExecutionGatewayValidationError(
                    "gateway cancel account must match cTrader DEMO configuration"
                )
            )
        if not isinstance(provider_execution_ref, str) or not provider_execution_ref:
            return Failure(
                CTraderDemoExecutionGatewayValidationError(
                    "provider_execution_ref must be a non-empty string"
                )
            )
        if not isinstance(cancelled_at, datetime):
            return Failure(
                CTraderDemoExecutionGatewayValidationError("cancelled_at must be a datetime")
            )
        if cancelled_at.tzinfo is None or cancelled_at.utcoffset() is None:
            return Failure(
                CTraderDemoExecutionGatewayValidationError("cancelled_at must be timezone-aware")
            )
        metadata = self._metadata_by_provider_ref.get(provider_execution_ref)
        if metadata is None:
            return Failure(
                ExecutionBoundaryNotFoundError(
                    "gateway cannot cancel an unknown provider execution reference"
                )
            )
        plan_result = build_ctrader_demo_order_cancel_plan(
            self._configuration,
            provider_order_ref=provider_execution_ref,
            requested_at=cancelled_at,
        )
        if isinstance(plan_result, Failure):
            return Failure(plan_result.error)
        response_result = self._transport.cancel_order(
            plan_result.value,
            metadata=metadata,
        )
        if isinstance(response_result, Failure):
            return Failure(response_result.error)
        receipt_result = decode_ctrader_demo_order_cancel_response(
            self._configuration,
            provider_order_ref=provider_execution_ref,
            response=response_result.value,
        )
        if isinstance(receipt_result, Failure):
            return Failure(receipt_result.error)
        receipt = receipt_result.value
        if receipt.recorded_at < cancelled_at:
            return Failure(
                CTraderDemoExecutionGatewayValidationError(
                    "provider cancellation receipt must not predate cancel request"
                )
            )
        return Success(receipt)

    def observe_fill(
        self,
        submission: ExecutionSubmission,
        payload: bytes,
        *,
        received_at: datetime,
    ) -> Result[CTraderDemoFillObservation, ExecutionBoundaryError]:
        """Ingest one provider fill event idempotently, without corrective trading."""
        if not isinstance(submission, ExecutionSubmission):
            return Failure(
                CTraderDemoExecutionGatewayValidationError(
                    "observe_fill requires ExecutionSubmission"
                )
            )
        if submission.receipt_id not in self._receipt_ids:
            return Failure(
                ExecutionBoundaryNotFoundError(
                    "gateway cannot observe fills for an unknown execution receipt"
                )
            )
        observation_result = decode_ctrader_demo_fill_observation(
            self._configuration,
            submission,
            payload,
            received_at=received_at,
        )
        if isinstance(observation_result, Failure):
            return Failure(observation_result.error)
        observation = observation_result.value

        receipt_id = submission.receipt_id
        known_outcome = self._outcomes_by_receipt.get(receipt_id)
        if (
            known_outcome is not None
            and known_outcome.provider_order_ref != observation.provider_order_ref
        ):
            return Failure(
                CTraderDemoExecutionConflictError(
                    "cTrader fill order reference does not match the submitted order"
                )
            )

        ledger = self._fills_by_receipt.setdefault(receipt_id, {})
        existing = ledger.get(observation.fill_ref)
        if existing is not None:
            if existing.provider_identity() != observation.provider_identity():
                return Failure(
                    CTraderDemoExecutionConflictError(
                        "duplicate cTrader fill reference with different evidence"
                    )
                )
            return Success(existing)

        requested = submission.authorized_intent.intent.quantity.value
        if observation.cumulative_quantity > requested:
            return Failure(
                CTraderDemoExecutionConflictError(
                    "cTrader cumulative fill exceeds requested quantity"
                )
            )

        if observation.is_complete:
            self._fill_complete[receipt_id] = True

        authoritative = self._authoritative_filled.get(receipt_id)
        if authoritative is not None and observation.cumulative_quantity < authoritative:
            # Late/out-of-order fill event: retain evidence but do not regress.
            ledger[observation.fill_ref] = observation
            return Success(observation)
        self._authoritative_filled[receipt_id] = observation.cumulative_quantity
        ledger[observation.fill_ref] = observation
        return Success(observation)

    def reconcile_fills(
        self,
        receipt_id: ExecutionReceiptId,
        *,
        reconciled_at: datetime,
    ) -> Result[CTraderDemoFillReconciliation, ExecutionBoundaryError]:
        """Reconcile cumulative fill evidence against the exact requested quantity."""
        if not isinstance(receipt_id, ExecutionReceiptId):
            return Failure(
                CTraderDemoExecutionGatewayValidationError(
                    "reconcile_fills requires ExecutionReceiptId"
                )
            )
        submission = self._submissions.get(receipt_id)
        if submission is None:
            return Failure(
                ExecutionBoundaryNotFoundError(
                    "gateway cannot reconcile fills for an unknown execution receipt"
                )
            )
        authoritative = self._authoritative_filled.get(receipt_id)
        filled = authoritative if authoritative is not None else Decimal("0")
        outcome = self._outcomes_by_receipt.get(receipt_id)
        is_complete = (
            outcome is not None and outcome.disposition is CTraderDemoOrderDisposition.FILLED
        ) or self._fill_complete.get(receipt_id, False)
        result = reconcile_ctrader_demo_fills(
            submission.authorized_intent.intent.quantity.value,
            filled,
            is_complete=is_complete,
            reconciled_at=reconciled_at,
        )
        if isinstance(result, Failure):
            return Failure(result.error)
        return Success(result.value)

    def project_execution_observation(
        self,
        receipt_id: ExecutionReceiptId,
        *,
        observed_at: datetime,
    ) -> Result[ExecutionObservation, ExecutionBoundaryError]:
        """Project the definitive provider outcome into canonical observation form."""
        if not isinstance(receipt_id, ExecutionReceiptId):
            return Failure(
                CTraderDemoExecutionGatewayValidationError(
                    "project_execution_observation requires ExecutionReceiptId"
                )
            )
        submission = self._submissions.get(receipt_id)
        if submission is None:
            return Failure(
                ExecutionBoundaryNotFoundError(
                    "gateway cannot project an unknown execution receipt"
                )
            )
        outcome = self._outcomes_by_receipt.get(receipt_id)
        if outcome is None:
            return Failure(
                ExecutionBoundaryNotFoundError("gateway has no definitive outcome to project")
            )
        status: ExecutionStatus
        if outcome.disposition in _ACCEPTED_DISPOSITIONS:
            status = ExecutionStatus.ACCEPTED
        elif outcome.disposition is CTraderDemoOrderDisposition.CANCELLED:
            status = ExecutionStatus.CANCELLED
        else:
            return Failure(
                CTraderDemoExecutionGatewayValidationError(
                    "cTrader outcome cannot be projected to canonical execution status"
                )
            )
        try:
            observation = ExecutionObservation(
                receipt_id=receipt_id,
                request_id=submission.request_id,
                idempotency_key=submission.idempotency_key,
                status=status,
                observed_at=observed_at,
            )
        except ExecutionReconciliationError as error:
            return Failure(
                CTraderDemoExecutionGatewayValidationError(
                    f"execution observation projection failed: {error}"
                )
            )
        return Success(observation)

    def resolve_unknown_outcome(
        self,
        *,
        receipt_id: ExecutionReceiptId,
        provider_order_ref: str,
        queried_at: datetime,
        scope_complete: bool = False,
    ) -> Result[CTraderDemoMutationAttempt, ExecutionBoundaryError]:
        """Resolve an indeterminate mutation via provider search, never resubmitting."""
        if not isinstance(receipt_id, ExecutionReceiptId):
            return Failure(
                CTraderDemoExecutionGatewayValidationError(
                    "resolve_unknown_outcome requires ExecutionReceiptId"
                )
            )
        if not isinstance(provider_order_ref, str) or not provider_order_ref:
            return Failure(
                CTraderDemoExecutionGatewayValidationError(
                    "provider_order_ref must be a non-empty string"
                )
            )
        submission = self._submissions.get(receipt_id)
        if submission is None:
            return Failure(
                ExecutionBoundaryNotFoundError(
                    "gateway cannot resolve an unknown execution receipt"
                )
            )
        key = submission.idempotency_key
        prior = self._attempts.get(key)
        if prior is None:
            return Failure(
                CTraderDemoExecutionGatewayValidationError(
                    "no mutating attempt recorded for this receipt"
                )
            )
        if not isinstance(queried_at, datetime):
            return Failure(
                CTraderDemoExecutionGatewayValidationError("queried_at must be a datetime")
            )
        if queried_at.tzinfo is None or queried_at.utcoffset() is None:
            return Failure(
                CTraderDemoExecutionGatewayValidationError("queried_at must be timezone-aware")
            )
        if type(scope_complete) is not bool:
            return Failure(
                CTraderDemoExecutionGatewayValidationError("scope_complete must be a strict bool")
            )
        if prior.state not in {
            CTraderDemoAttemptState.OUTCOME_UNKNOWN,
            CTraderDemoAttemptState.RECONCILIATION_REQUIRED,
        }:
            return Failure(
                CTraderDemoExecutionConflictError(
                    "attempt is not in a reconcilable indeterminate state"
                )
            )

        current = prior
        if prior.state is CTraderDemoAttemptState.OUTCOME_UNKNOWN:
            reconciled = transition_ctrader_demo_attempt(
                prior,
                CTraderDemoAttemptState.RECONCILIATION_REQUIRED,
                transitioned_at=queried_at,
                reason="provider-state reconciliation search required",
            )
            if isinstance(reconciled, Failure):
                return Failure(reconciled.error)
            current = reconciled.value
            self._attempts[key] = current

        metadata = submission.authorized_intent.intent.metadata
        query_result = self._transport.query_order(
            provider_order_ref,
            metadata=metadata,
        )
        if isinstance(query_result, Failure):
            return Failure(
                CTraderDemoExecutionUnknownOutcomeError(
                    "provider-state search failed; reconciliation remains required"
                )
            )
        response = query_result.value

        if response.status_code == 404:
            target = (
                CTraderDemoAttemptState.RESOLVED
                if scope_complete
                else CTraderDemoAttemptState.CONTAINED
            )
            reason = (
                "provider search complete with no external effect evidenced"
                if scope_complete
                else "provider order not found but query scope is not complete"
            )
            resolved = transition_ctrader_demo_attempt(
                current,
                target,
                transitioned_at=response.received_at,
                provider_order_ref=provider_order_ref,
                reason=reason,
            )
            if isinstance(resolved, Failure):
                return Failure(resolved.error)
            self._attempts[key] = resolved.value
            return Success(resolved.value)

        outcome_result = decode_ctrader_demo_order_query_response(
            self._configuration,
            provider_order_ref=provider_order_ref,
            response=response,
        )
        if isinstance(outcome_result, Failure):
            return Failure(
                CTraderDemoExecutionUnknownOutcomeError(
                    "provider-state search returned ambiguous evidence"
                )
            )
        outcome = outcome_result.value
        self._outcomes_by_receipt[receipt_id] = outcome
        self._outcomes_by_provider_ref[outcome.provider_order_ref] = outcome
        self._metadata_by_provider_ref[outcome.provider_order_ref] = metadata
        resolved = transition_ctrader_demo_attempt(
            current,
            CTraderDemoAttemptState.RESOLVED,
            transitioned_at=response.received_at,
            provider_order_ref=outcome.provider_order_ref,
            reason=f"resolved definitive {outcome.disposition.value}",
        )
        if isinstance(resolved, Failure):
            return Failure(resolved.error)
        self._attempts[key] = resolved.value
        return Success(resolved.value)
