from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Protocol
from uuid import UUID

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
from qore.infrastructure.ctrader_demo_mutation_ledger import (
    CTraderDemoMutationLedger,
    CTraderDemoMutationLedgerError,
    CTraderDemoMutationLedgerRecord,
    ctrader_submission_digest,
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


def _stable_fill_identity(observation: CTraderDemoFillObservation) -> tuple[object, ...]:
    """Return immutable deal identity, excluding projection and receive-time fields."""
    return (
        observation.receipt_id.logical_values(),
        observation.idempotency_key.logical_values(),
        observation.account.logical_values(),
        observation.instrument.value,
        observation.side.value,
        observation.provider_order_ref,
        observation.fill_ref,
        format(observation.fill_quantity, "f"),
        format(observation.fill_price, "f"),
    )


def _stable_fill_digest(observation: CTraderDemoFillObservation) -> str:
    canonical = json.dumps(
        _stable_fill_identity(observation),
        default=str,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(canonical).hexdigest()}"


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

    def discover_order(
        self,
        plan: CTraderOrderCreatePlan,
        *,
        from_timestamp: datetime,
        to_timestamp: datetime,
        metadata: ExternalRequestMetadata,
    ) -> Result[ExternalTransportResponse, ExecutionBoundaryError]:
        """Search one complete provider-history window by exact clientOrderId."""
        ...


class CTraderDemoExecutionGateway:
    """Compose canonical TEST/DEMO execution with an injected cTrader DEMO transport."""

    __slots__ = (
        "_attempts",
        "_authoritative_filled",
        "_configuration",
        "_fill_complete",
        "_fill_identity_digests",
        "_fills_by_receipt",
        "_metadata_by_provider_ref",
        "_mutation_ledger",
        "_durable_records",
        "_outcomes_by_receipt",
        "_outcomes_by_provider_ref",
        "_receipt_ids",
        "_receipts",
        "_reject_errors",
        "_submissions",
        "_submission_digests",
        "_staged_here",
        "_transport",
    )

    def __init__(
        self,
        *,
        configuration: CTraderDemoRuntimeConfiguration,
        transport: CTraderDemoExecutionTransportBoundary,
        mutation_ledger: CTraderDemoMutationLedger,
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
        if not callable(getattr(transport, "discover_order", None)):
            raise CTraderDemoExecutionGatewayValidationError(
                "cTrader transport requires discover_order"
            )
        if not callable(getattr(mutation_ledger, "records", None)) or not callable(
            getattr(mutation_ledger, "upsert", None)
        ):
            raise CTraderDemoExecutionGatewayValidationError(
                "cTrader execution gateway requires a mutation ledger"
            )
        self._configuration = configuration
        self._transport = transport
        self._mutation_ledger = mutation_ledger
        self._attempts: dict[ExecutionIdempotencyKey, CTraderDemoMutationAttempt] = {}
        self._receipt_ids: set[ExecutionReceiptId] = set()
        self._receipts: dict[ExecutionReceiptId, TestExecutionGatewayReceipt] = {}
        self._reject_errors: dict[ExecutionReceiptId, CTraderDemoExecutionNotAcceptedError] = {}
        self._submissions: dict[ExecutionReceiptId, ExecutionSubmission] = {}
        self._submission_digests: dict[ExecutionIdempotencyKey, str] = {}
        self._staged_here: set[ExecutionIdempotencyKey] = set()
        self._durable_records: dict[
            ExecutionIdempotencyKey, CTraderDemoMutationLedgerRecord
        ] = {}
        self._outcomes_by_receipt: dict[ExecutionReceiptId, CTraderDemoExecutionOutcome] = {}
        self._outcomes_by_provider_ref: dict[str, CTraderDemoExecutionOutcome] = {}
        self._metadata_by_provider_ref: dict[str, ExternalRequestMetadata] = {}
        self._fills_by_receipt: dict[ExecutionReceiptId, dict[str, CTraderDemoFillObservation]] = {}
        self._authoritative_filled: dict[ExecutionReceiptId, Decimal] = {}
        self._fill_complete: dict[ExecutionReceiptId, bool] = {}
        self._fill_identity_digests: dict[ExecutionReceiptId, dict[str, str]] = {}
        self._restore_durable_records()

    def _restore_durable_records(self) -> None:
        try:
            records = self._mutation_ledger.records()
            for record in records:
                key = ExecutionIdempotencyKey(UUID(record.idempotency_key))
                receipt_id = ExecutionReceiptId(UUID(record.receipt_id))
                if key in self._durable_records or receipt_id in self._receipt_ids:
                    raise CTraderDemoExecutionGatewayValidationError(
                        "durable mutation ledger contains duplicate identity"
                    )
                restored_record = record
                if record.state is CTraderDemoAttemptState.ATTEMPT_STARTED:
                    restored_record = replace(
                        record,
                        state=CTraderDemoAttemptState.OUTCOME_UNKNOWN,
                        reason="process restarted after durable mutation fence",
                    )
                    self._mutation_ledger.upsert(restored_record)
                self._durable_records[key] = restored_record
                self._submission_digests[key] = restored_record.submission_digest
                self._receipt_ids.add(receipt_id)
                self._attempts[key] = CTraderDemoMutationAttempt(
                    idempotency_key=key,
                    receipt_id=receipt_id,
                    submission_logical=(restored_record.submission_digest,),
                    state=restored_record.state,
                    transitioned_at=restored_record.transitioned_at,
                    provider_order_ref=restored_record.provider_order_ref,
                    reason=restored_record.reason,
                )
                self._authoritative_filled[receipt_id] = Decimal(
                    restored_record.cumulative_quantity
                )
                self._fill_complete[receipt_id] = restored_record.is_complete
                self._fill_identity_digests[receipt_id] = dict(
                    restored_record.fill_identities
                )
        except (ValueError, CTraderDemoMutationLedgerError) as error:
            raise CTraderDemoExecutionGatewayValidationError(
                "durable mutation ledger could not be restored safely"
            ) from error

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

    @property
    def has_unresolved_mutations(self) -> bool:
        return any(
            attempt.state
            not in {
                CTraderDemoAttemptState.DEFINITIVE_OUTCOME,
                CTraderDemoAttemptState.RESOLVED,
            }
            for attempt in self._attempts.values()
        )

    def stage_risk_fence(
        self,
        submission: ExecutionSubmission,
        *,
        risk_authorization_id: str,
        risk_authorization_fingerprint: str,
        risk_reservation_id: str,
    ) -> Result[None, ExecutionBoundaryError]:
        """Persist Risk provenance before the create-attempt critical section."""
        if not isinstance(submission, ExecutionSubmission):
            return Failure(
                CTraderDemoExecutionGatewayValidationError(
                    "risk fence requires ExecutionSubmission"
                )
            )
        for value, field_name in (
            (risk_authorization_id, "risk_authorization_id"),
            (risk_authorization_fingerprint, "risk_authorization_fingerprint"),
            (risk_reservation_id, "risk_reservation_id"),
        ):
            if not isinstance(value, str) or not value:
                return Failure(
                    CTraderDemoExecutionGatewayValidationError(
                        f"{field_name} must be non-empty"
                    )
                )
        plan_result = build_ctrader_demo_order_create_plan(self._configuration, submission)
        if isinstance(plan_result, Failure):
            return Failure(plan_result.error)
        key = submission.idempotency_key
        digest = ctrader_submission_digest(submission)
        known = self._durable_records.get(key)
        if known is not None:
            if known.submission_digest != digest:
                return Failure(
                    CTraderDemoExecutionConflictError(
                        "durable idempotency key conflicts with Risk submission"
                    )
                )
            return Success(None)
        record = CTraderDemoMutationLedgerRecord(
            idempotency_key=str(key.value),
            receipt_id=str(submission.receipt_id.value),
            submission_digest=digest,
            client_order_id=plan_result.value.client_msg_id,
            state=CTraderDemoAttemptState.ATTEMPT_STARTED,
            transitioned_at=submission.submitted_at,
            risk_authorization_id=risk_authorization_id,
            risk_authorization_fingerprint=risk_authorization_fingerprint,
            risk_reservation_id=risk_reservation_id,
        )
        persisted = self._persist_record(key, record)
        if isinstance(persisted, Failure):
            return persisted
        self._submission_digests[key] = digest
        self._staged_here.add(key)
        return Success(None)

    def restore_submission(
        self, submission: ExecutionSubmission
    ) -> Result[None, ExecutionBoundaryError]:
        """Rehydrate an original submission for discovery, never for resubmission."""
        if not isinstance(submission, ExecutionSubmission):
            return Failure(
                CTraderDemoExecutionGatewayValidationError(
                    "restore_submission requires ExecutionSubmission"
                )
            )
        key = submission.idempotency_key
        record = self._durable_records.get(key)
        if record is None or record.receipt_id != str(submission.receipt_id.value):
            return Failure(
                ExecutionBoundaryNotFoundError(
                    "no durable mutation matches the supplied submission"
                )
            )
        if record.submission_digest != ctrader_submission_digest(submission):
            return Failure(
                CTraderDemoExecutionConflictError(
                    "restored submission does not match its durable digest"
                )
            )
        self._submissions[submission.receipt_id] = submission
        return Success(None)

    def _persist_record(
        self,
        key: ExecutionIdempotencyKey,
        record: CTraderDemoMutationLedgerRecord,
    ) -> Result[None, ExecutionBoundaryError]:
        try:
            self._mutation_ledger.upsert(record)
        except CTraderDemoMutationLedgerError as error:
            return Failure(error)
        self._durable_records[key] = record
        return Success(None)

    def _persist_attempt(
        self,
        submission: ExecutionSubmission,
        attempt: CTraderDemoMutationAttempt,
        *,
        client_order_id: str,
        outcome: str | None = None,
    ) -> Result[None, ExecutionBoundaryError]:
        key = submission.idempotency_key
        prior = self._durable_records.get(key)
        record = CTraderDemoMutationLedgerRecord(
            idempotency_key=str(key.value),
            receipt_id=str(submission.receipt_id.value),
            submission_digest=ctrader_submission_digest(submission),
            client_order_id=client_order_id,
            state=attempt.state,
            transitioned_at=attempt.transitioned_at,
            provider_order_ref=attempt.provider_order_ref,
            reason=attempt.reason,
            outcome=outcome if outcome is not None else (prior.outcome if prior else None),
            fill_refs=prior.fill_refs if prior else (),
            fill_identities=prior.fill_identities if prior else (),
            cumulative_quantity=prior.cumulative_quantity if prior else "0",
            is_complete=prior.is_complete if prior else False,
            risk_authorization_id=prior.risk_authorization_id if prior else None,
            risk_authorization_fingerprint=(
                prior.risk_authorization_fingerprint if prior else None
            ),
            risk_reservation_id=prior.risk_reservation_id if prior else None,
        )
        return self._persist_record(key, record)

    def _persist_transition(
        self,
        submission: ExecutionSubmission,
        attempt: CTraderDemoMutationAttempt,
        *,
        outcome: str | None = None,
    ) -> Result[None, ExecutionBoundaryError]:
        record = self._durable_records.get(submission.idempotency_key)
        if record is None:
            return Failure(
                CTraderDemoExecutionGatewayValidationError(
                    "attempt transition is missing its durable mutation fence"
                )
            )
        return self._persist_attempt(
            submission,
            attempt,
            client_order_id=record.client_order_id,
            outcome=outcome,
        )

    def _record_unknown(
        self,
        key: ExecutionIdempotencyKey,
        submission: ExecutionSubmission,
        *,
        reason: str,
        client_order_id: str,
    ) -> Result[None, ExecutionBoundaryError]:
        attempt = CTraderDemoMutationAttempt(
            idempotency_key=key,
            receipt_id=submission.receipt_id,
            submission_logical=submission.logical_values(),
            state=CTraderDemoAttemptState.OUTCOME_UNKNOWN,
            transitioned_at=submission.submitted_at,
            reason=reason,
        )
        self._attempts[key] = attempt
        return self._persist_attempt(
            submission,
            attempt,
            client_order_id=client_order_id,
        )

    def _persist_fill_state(
        self,
        submission: ExecutionSubmission,
    ) -> Result[None, ExecutionBoundaryError]:
        key = submission.idempotency_key
        prior = self._durable_records.get(key)
        if prior is None:
            return Failure(
                CTraderDemoExecutionGatewayValidationError(
                    "fill evidence is missing its durable mutation fence"
                )
            )
        receipt_id = submission.receipt_id
        identities = self._fill_identity_digests.get(receipt_id, {})
        record = replace(
            prior,
            fill_refs=tuple(sorted(identities)),
            fill_identities=tuple(sorted(identities.items())),
            cumulative_quantity=format(
                self._authoritative_filled.get(receipt_id, Decimal("0")), "f"
            ),
            is_complete=self._fill_complete.get(receipt_id, False),
        )
        return self._persist_record(key, record)

    def _finish_fill(
        self,
        submission: ExecutionSubmission,
        observation: CTraderDemoFillObservation,
    ) -> Result[CTraderDemoFillObservation, ExecutionBoundaryError]:
        persisted = self._persist_fill_state(submission)
        if isinstance(persisted, Failure):
            return Failure(persisted.error)
        return Success(observation)

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
            if self._submission_digests.get(key) != ctrader_submission_digest(submission):
                return Failure(
                    CTraderDemoExecutionConflictError(
                        "cTrader idempotency key reused with different submission"
                    )
                )
            if prior.state is CTraderDemoAttemptState.NOT_ATTEMPTED or (
                prior.state is CTraderDemoAttemptState.ATTEMPT_STARTED
                and key in self._staged_here
            ):
                pass
            elif prior.state is CTraderDemoAttemptState.DEFINITIVE_OUTCOME:
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
            elif prior.state is CTraderDemoAttemptState.RESOLVED:
                receipt = self._receipts.get(prior.receipt_id)
                if receipt is not None:
                    return Success(receipt)
                return Failure(
                    CTraderDemoExecutionConflictError(
                        "cTrader execution already resolved; resubmission prohibited"
                    )
                )
            else:
                return Failure(
                    CTraderDemoExecutionUnknownOutcomeError(
                        "cTrader execution has an unresolved mutating attempt; "
                        "reconciliation is required before any resubmission"
                    )
                )
        if submission.receipt_id in self._receipt_ids and prior is None:
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
        self._submission_digests[key] = ctrader_submission_digest(submission)

        started = CTraderDemoMutationAttempt(
            idempotency_key=key,
            receipt_id=submission.receipt_id,
            submission_logical=submission.logical_values(),
            state=CTraderDemoAttemptState.ATTEMPT_STARTED,
            transitioned_at=submission.submitted_at,
            reason="durable fence committed before provider mutation",
        )
        persisted_started = self._persist_attempt(
            submission,
            started,
            client_order_id=plan.client_msg_id,
        )
        if isinstance(persisted_started, Failure):
            return Failure(persisted_started.error)
        self._attempts[key] = started
        self._staged_here.discard(key)

        metadata = submission.authorized_intent.intent.metadata
        response_result = self._transport.submit_order(plan, metadata=metadata)
        if isinstance(response_result, Failure):
            persisted_unknown = self._record_unknown(
                key,
                submission,
                reason="provider transport failure after mutating attempt",
                client_order_id=plan.client_msg_id,
            )
            if isinstance(persisted_unknown, Failure):
                return Failure(persisted_unknown.error)
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
            persisted_unknown = self._record_unknown(
                key,
                submission,
                reason="malformed provider response after possible effect",
                client_order_id=plan.client_msg_id,
            )
            if isinstance(persisted_unknown, Failure):
                return Failure(persisted_unknown.error)
            return Failure(
                CTraderDemoExecutionUnknownOutcomeError(
                    "cTrader provider response could not be definitively decoded; "
                    "reconciliation is required"
                )
            )

        outcome = outcome_result.value
        if outcome.provider_order_ref in self._outcomes_by_provider_ref:
            persisted_unknown = self._record_unknown(
                key,
                submission,
                reason="provider order reference already observed",
                client_order_id=plan.client_msg_id,
            )
            if isinstance(persisted_unknown, Failure):
                return Failure(persisted_unknown.error)
            return Failure(
                CTraderDemoExecutionUnknownOutcomeError(
                    "cTrader provider order reference was already observed; "
                    "reconciliation is required"
                )
            )

        definitive = CTraderDemoMutationAttempt(
            idempotency_key=key,
            receipt_id=submission.receipt_id,
            submission_logical=submission.logical_values(),
            state=CTraderDemoAttemptState.DEFINITIVE_OUTCOME,
            transitioned_at=outcome.recorded_at,
            provider_order_ref=outcome.provider_order_ref,
            reason=outcome.disposition.value,
        )
        persisted_definitive = self._persist_attempt(
            submission,
            definitive,
            client_order_id=plan.client_msg_id,
            outcome=outcome.disposition.value,
        )
        if isinstance(persisted_definitive, Failure):
            return Failure(
                CTraderDemoExecutionUnknownOutcomeError(
                    "provider outcome was received but durable commit failed; "
                    "reconciliation required"
                )
            )
        self._attempts[key] = definitive
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

        requested = submission.authorized_intent.intent.quantity.value
        if observation.cumulative_quantity > requested:
            return Failure(
                CTraderDemoExecutionConflictError(
                    "cTrader cumulative fill exceeds requested quantity"
                )
            )

        ledger = self._fills_by_receipt.setdefault(receipt_id, {})
        existing = ledger.get(observation.fill_ref)
        persisted_identity = self._fill_identity_digests.setdefault(receipt_id, {}).get(
            observation.fill_ref
        )
        observation_digest = _stable_fill_digest(observation)
        if existing is None and persisted_identity is not None:
            if persisted_identity != observation_digest:
                return Failure(
                    CTraderDemoExecutionConflictError(
                        "durable cTrader fill reference has different deal identity"
                    )
                )
            if observation.cumulative_quantity > self._authoritative_filled.get(
                receipt_id, Decimal("0")
            ):
                self._authoritative_filled[receipt_id] = observation.cumulative_quantity
            if observation.is_complete:
                self._fill_complete[receipt_id] = True
            ledger[observation.fill_ref] = observation
            return self._finish_fill(submission, observation)
        if existing is not None:
            if _stable_fill_identity(existing) != _stable_fill_identity(observation):
                return Failure(
                    CTraderDemoExecutionConflictError(
                        "duplicate cTrader fill reference with different deal identity"
                    )
                )
            duplicate_authoritative = self._authoritative_filled.get(
                receipt_id, Decimal("0")
            )
            if observation.cumulative_quantity > duplicate_authoritative:
                self._authoritative_filled[receipt_id] = observation.cumulative_quantity
            if observation.is_complete:
                self._fill_complete[receipt_id] = True
            if (
                observation.cumulative_quantity > existing.cumulative_quantity
                or (observation.is_complete and not existing.is_complete)
            ):
                ledger[observation.fill_ref] = observation
                self._fill_identity_digests[receipt_id][observation.fill_ref] = observation_digest
                return self._finish_fill(submission, observation)
            return self._finish_fill(submission, existing)

        if observation.is_complete:
            self._fill_complete[receipt_id] = True

        authoritative = self._authoritative_filled.get(receipt_id)
        if authoritative is not None and observation.cumulative_quantity < authoritative:
            # Late/out-of-order fill event: retain evidence but do not regress.
            ledger[observation.fill_ref] = observation
            self._fill_identity_digests[receipt_id][observation.fill_ref] = observation_digest
            return self._finish_fill(submission, observation)
        self._authoritative_filled[receipt_id] = observation.cumulative_quantity
        ledger[observation.fill_ref] = observation
        self._fill_identity_digests[receipt_id][observation.fill_ref] = observation_digest
        return self._finish_fill(submission, observation)

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
            persisted = self._persist_transition(submission, current)
            if isinstance(persisted, Failure):
                return persisted
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
            persisted = self._persist_transition(submission, resolved.value)
            if isinstance(persisted, Failure):
                return persisted
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
        persisted = self._persist_transition(
            submission,
            resolved.value,
            outcome=outcome.disposition.value,
        )
        if isinstance(persisted, Failure):
            return persisted
        self._attempts[key] = resolved.value
        return Success(resolved.value)

    def discover_unknown_outcome(
        self,
        *,
        receipt_id: ExecutionReceiptId,
        from_timestamp: datetime,
        to_timestamp: datetime,
        searched_at: datetime,
    ) -> Result[CTraderDemoMutationAttempt, ExecutionBoundaryError]:
        """Recover an unknown create by its persisted clientOrderId, never by retrying it."""
        if not isinstance(receipt_id, ExecutionReceiptId):
            return Failure(
                CTraderDemoExecutionGatewayValidationError(
                    "discover_unknown_outcome requires ExecutionReceiptId"
                )
            )
        for value, field_name in (
            (from_timestamp, "from_timestamp"),
            (to_timestamp, "to_timestamp"),
            (searched_at, "searched_at"),
        ):
            if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
                return Failure(
                    CTraderDemoExecutionGatewayValidationError(
                        f"{field_name} must be a timezone-aware datetime"
                    )
                )
        if from_timestamp >= to_timestamp:
            return Failure(
                CTraderDemoExecutionGatewayValidationError(
                    "from_timestamp must predate to_timestamp"
                )
            )
        submission = self._submissions.get(receipt_id)
        if submission is None:
            return Failure(
                ExecutionBoundaryNotFoundError(
                    "gateway cannot discover an unknown execution receipt"
                )
            )
        key = submission.idempotency_key
        prior = self._attempts.get(key)
        if prior is None or prior.state not in {
            CTraderDemoAttemptState.OUTCOME_UNKNOWN,
            CTraderDemoAttemptState.RECONCILIATION_REQUIRED,
        }:
            return Failure(
                CTraderDemoExecutionConflictError(
                    "attempt is not in a discoverable indeterminate state"
                )
            )
        current = prior
        if prior.state is CTraderDemoAttemptState.OUTCOME_UNKNOWN:
            transitioned = transition_ctrader_demo_attempt(
                prior,
                CTraderDemoAttemptState.RECONCILIATION_REQUIRED,
                transitioned_at=searched_at,
                reason="clientOrderId discovery required",
            )
            if isinstance(transitioned, Failure):
                return Failure(transitioned.error)
            current = transitioned.value
            persisted = self._persist_transition(submission, current)
            if isinstance(persisted, Failure):
                return persisted
            self._attempts[key] = current

        plan_result = build_ctrader_demo_order_create_plan(self._configuration, submission)
        if isinstance(plan_result, Failure):
            return Failure(plan_result.error)
        metadata = submission.authorized_intent.intent.metadata
        discovered = self._transport.discover_order(
            plan_result.value,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
            metadata=metadata,
        )
        if isinstance(discovered, Failure):
            return self._contain_discovery(
                key,
                current,
                transitioned_at=to_timestamp,
                reason="clientOrderId discovery failed or was incomplete",
            )
        response = discovered.value
        if response.status_code == 404:
            resolved = transition_ctrader_demo_attempt(
                current,
                CTraderDemoAttemptState.RESOLVED,
                transitioned_at=response.received_at,
                reason="complete clientOrderId search proved no external effect",
            )
            if isinstance(resolved, Failure):
                return Failure(resolved.error)
            persisted = self._persist_transition(submission, resolved.value)
            if isinstance(persisted, Failure):
                return persisted
            self._attempts[key] = resolved.value
            return Success(resolved.value)
        if response.status_code != 200:
            return self._contain_discovery(
                key,
                current,
                transitioned_at=response.received_at,
                reason="clientOrderId discovery was ambiguous or contradictory",
            )
        try:
            payload = json.loads(response.payload.decode("utf-8"))
            provider_order_ref = payload["orderId"]
        except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError):
            return self._contain_discovery(
                key,
                current,
                transitioned_at=response.received_at,
                reason="clientOrderId discovery returned malformed identity evidence",
            )
        if not isinstance(provider_order_ref, str) or not provider_order_ref:
            return self._contain_discovery(
                key,
                current,
                transitioned_at=response.received_at,
                reason="clientOrderId discovery returned invalid order identity",
            )
        reconciled = self.resolve_unknown_outcome(
            receipt_id=receipt_id,
            provider_order_ref=provider_order_ref,
            queried_at=response.received_at,
        )
        if isinstance(reconciled, Failure):
            latest = self._attempts[key]
            return self._contain_discovery(
                key,
                latest,
                transitioned_at=response.received_at + timedelta(microseconds=1),
                reason="discovered order could not be reconciled definitively",
            )
        return reconciled

    def _contain_discovery(
        self,
        key: ExecutionIdempotencyKey,
        current: CTraderDemoMutationAttempt,
        *,
        transitioned_at: datetime,
        reason: str,
    ) -> Result[CTraderDemoMutationAttempt, ExecutionBoundaryError]:
        contained = transition_ctrader_demo_attempt(
            current,
            CTraderDemoAttemptState.CONTAINED,
            transitioned_at=transitioned_at,
            reason=reason,
        )
        if isinstance(contained, Failure):
            return Failure(contained.error)
        submission = self._submissions.get(current.receipt_id)
        if submission is None:
            return Failure(
                CTraderDemoExecutionGatewayValidationError(
                    "contained discovery is missing its restored submission"
                )
            )
        persisted = self._persist_transition(submission, contained.value)
        if isinstance(persisted, Failure):
            return persisted
        self._attempts[key] = contained.value
        return Success(contained.value)
