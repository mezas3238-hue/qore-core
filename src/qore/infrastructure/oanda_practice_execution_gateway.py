from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from re import fullmatch
from typing import Protocol

from qore.infrastructure.execution_boundary import (
    ExecutionBoundaryConflictError,
    ExecutionBoundaryError,
    ExecutionBoundaryNotFoundError,
    ExecutionSubmission,
)
from qore.infrastructure.market_test_environment import MarketTestAccountIdentity
from qore.infrastructure.oanda_practice_configuration import (
    OandaPracticeCapability,
    OandaPracticeRuntimeConfiguration,
)
from qore.infrastructure.oanda_practice_execution_codec import (
    OandaPracticeExecutionOutcome,
    OandaPracticeOrderCreatePlan,
    build_oanda_practice_order_create_plan,
    build_oanda_practice_submit_gateway_receipt,
    decode_oanda_practice_order_cancel_response,
    decode_oanda_practice_order_create_response,
)
from qore.infrastructure.ports import ExternalRequestMetadata
from qore.infrastructure.test_execution_adapter import TestExecutionGatewayReceipt
from qore.infrastructure.transport import (
    ExternalTransportResponse,
    ExternalTransportTimeout,
)
from qore.kernel.result import Failure, Result, Success


class OandaPracticeExecutionGatewayError(ExecutionBoundaryError):
    """Base error for the offline-composable OANDA Practice execution gateway."""

    __slots__ = ()


class OandaPracticeExecutionGatewayValidationError(OandaPracticeExecutionGatewayError):
    """A Practice gateway value violates configuration or chronology invariants."""

    __slots__ = ()


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise OandaPracticeExecutionGatewayValidationError(
            f"{field_name} must be a datetime"
        )
    if value.tzinfo is None or value.utcoffset() is None:
        raise OandaPracticeExecutionGatewayValidationError(
            f"{field_name} must be timezone-aware"
        )


def _validate_provider_ref(value: str) -> str:
    if not isinstance(value, str) or fullmatch(r"[0-9]+", value) is None:
        raise OandaPracticeExecutionGatewayValidationError(
            "OANDA provider execution ref must be a numeric string"
        )
    return value


def _account_fingerprint(account_ref: str) -> str:
    digest = hashlib.sha256(account_ref.encode("utf-8")).hexdigest()
    return f"sha256:{digest[:24]}"


@dataclass(frozen=True, slots=True)
class OandaPracticeOrderCancelPlan:
    """Secret-free deterministic plan for one future Practice order cancellation."""

    account: MarketTestAccountIdentity
    endpoint_origin: str
    path: str
    timeout: ExternalTransportTimeout
    provider_execution_ref: str
    requested_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.account, MarketTestAccountIdentity):
            raise OandaPracticeExecutionGatewayValidationError(
                "cancel plan requires MarketTestAccountIdentity"
            )
        if self.account.provider_key != "oanda-v20":
            raise OandaPracticeExecutionGatewayValidationError(
                "cancel plan provider must be oanda-v20"
            )
        if self.account.environment.value != "demo":
            raise OandaPracticeExecutionGatewayValidationError(
                "cancel plan environment must be demo"
            )
        if self.endpoint_origin != "https://api-fxpractice.oanda.com":
            raise OandaPracticeExecutionGatewayValidationError(
                "cancel plan endpoint must be OANDA Practice"
            )
        provider_ref = _validate_provider_ref(self.provider_execution_ref)
        expected_path = (
            f"/v3/accounts/{self.account.account_ref}/orders/{provider_ref}/cancel"
        )
        if self.path != expected_path:
            raise OandaPracticeExecutionGatewayValidationError(
                "cancel plan path must bind the configured account and provider ref"
            )
        if not isinstance(self.timeout, ExternalTransportTimeout):
            raise OandaPracticeExecutionGatewayValidationError(
                "cancel plan requires ExternalTransportTimeout"
            )
        _validate_timestamp(self.requested_at, field_name="cancel requested_at")

    @property
    def account_fingerprint(self) -> str:
        return _account_fingerprint(self.account.account_ref)

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.account.logical_values(),
            self.endpoint_origin,
            self.path,
            self.timeout.logical_values(),
            self.provider_execution_ref,
            self.requested_at.isoformat(),
        )

    def sanitized_values(self) -> tuple[object, ...]:
        return (
            self.account.provider_key,
            self.account.environment.value,
            self.account_fingerprint,
            self.endpoint_origin,
            self.timeout.logical_values(),
            self.provider_execution_ref,
            self.requested_at.isoformat(),
        )


def build_oanda_practice_order_cancel_plan(
    configuration: OandaPracticeRuntimeConfiguration,
    *,
    provider_execution_ref: str,
    requested_at: datetime,
) -> Result[OandaPracticeOrderCancelPlan, ExecutionBoundaryError]:
    """Build one exact secret-free Practice cancellation plan."""

    if not isinstance(configuration, OandaPracticeRuntimeConfiguration):
        return Failure(
            OandaPracticeExecutionGatewayValidationError(
                "cancel planning requires OandaPracticeRuntimeConfiguration"
            )
        )
    if OandaPracticeCapability.ORDERS not in configuration.capabilities:
        return Failure(
            OandaPracticeExecutionGatewayValidationError(
                "OANDA Practice configuration must authorize orders capability"
            )
        )
    try:
        provider_ref = _validate_provider_ref(provider_execution_ref)
        _validate_timestamp(requested_at, field_name="cancel requested_at")
        plan = OandaPracticeOrderCancelPlan(
            account=configuration.account,
            endpoint_origin=configuration.rest_endpoint.origin,
            path=(
                f"/v3/accounts/{configuration.account.account_ref}/orders/"
                f"{provider_ref}/cancel"
            ),
            timeout=configuration.rest_timeout,
            provider_execution_ref=provider_ref,
            requested_at=requested_at,
        )
    except OandaPracticeExecutionGatewayError as error:
        return Failure(error)
    return Success(plan)


class OandaPracticeExecutionTransportBoundary(Protocol):
    """Already-authenticated Practice-only write transport used behind the gateway."""

    @property
    def configuration(self) -> OandaPracticeRuntimeConfiguration:
        """Return the exact Practice configuration bound to this transport."""
        ...

    def create_order(
        self,
        plan: OandaPracticeOrderCreatePlan,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[ExternalTransportResponse, ExecutionBoundaryError]:
        """Perform at most one provider create request for the supplied plan."""
        ...

    def cancel_order(
        self,
        plan: OandaPracticeOrderCancelPlan,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[ExternalTransportResponse, ExecutionBoundaryError]:
        """Perform at most one provider cancellation request for the supplied plan."""
        ...


class OandaPracticeExecutionGateway:
    """Compose canonical TEST/DEMO execution with an injected Practice transport."""

    __slots__ = (
        "_configuration",
        "_metadata_by_provider_ref",
        "_outcomes_by_provider_ref",
        "_transport",
    )

    def __init__(
        self,
        *,
        configuration: OandaPracticeRuntimeConfiguration,
        transport: OandaPracticeExecutionTransportBoundary,
    ) -> None:
        if not isinstance(configuration, OandaPracticeRuntimeConfiguration):
            raise OandaPracticeExecutionGatewayValidationError(
                "Practice execution gateway requires OandaPracticeRuntimeConfiguration"
            )
        if OandaPracticeCapability.ORDERS not in configuration.capabilities:
            raise OandaPracticeExecutionGatewayValidationError(
                "Practice execution gateway requires orders capability"
            )
        transport_configuration = getattr(transport, "configuration", None)
        if transport_configuration != configuration:
            raise OandaPracticeExecutionGatewayValidationError(
                "Practice execution transport configuration must match gateway"
            )
        if not callable(getattr(transport, "create_order", None)):
            raise OandaPracticeExecutionGatewayValidationError(
                "Practice execution transport requires create_order"
            )
        if not callable(getattr(transport, "cancel_order", None)):
            raise OandaPracticeExecutionGatewayValidationError(
                "Practice execution transport requires cancel_order"
            )
        self._configuration = configuration
        self._transport = transport
        self._metadata_by_provider_ref: dict[str, ExternalRequestMetadata] = {}
        self._outcomes_by_provider_ref: dict[str, OandaPracticeExecutionOutcome] = {}

    @property
    def configuration(self) -> OandaPracticeRuntimeConfiguration:
        return self._configuration

    @property
    def outcomes(self) -> tuple[OandaPracticeExecutionOutcome, ...]:
        return tuple(
            self._outcomes_by_provider_ref[key]
            for key in sorted(self._outcomes_by_provider_ref, key=int)
        )

    def submit(
        self,
        *,
        account: MarketTestAccountIdentity,
        submission: ExecutionSubmission,
    ) -> Result[TestExecutionGatewayReceipt, ExecutionBoundaryError]:
        if account != self.configuration.account:
            return Failure(
                OandaPracticeExecutionGatewayValidationError(
                    "gateway submit account must match Practice configuration"
                )
            )
        if not isinstance(submission, ExecutionSubmission):
            return Failure(
                OandaPracticeExecutionGatewayValidationError(
                    "gateway submit requires ExecutionSubmission"
                )
            )
        plan_result = build_oanda_practice_order_create_plan(
            self.configuration,
            submission,
        )
        if isinstance(plan_result, Failure):
            return Failure(plan_result.error)
        plan = plan_result.value
        metadata = submission.authorized_intent.intent.metadata
        response_result = self._transport.create_order(
            plan,
            metadata=metadata,
        )
        if isinstance(response_result, Failure):
            return Failure(response_result.error)
        outcome_result = decode_oanda_practice_order_create_response(
            self.configuration,
            submission,
            plan,
            response_result.value,
        )
        if isinstance(outcome_result, Failure):
            return Failure(outcome_result.error)
        outcome = outcome_result.value
        receipt_result = build_oanda_practice_submit_gateway_receipt(outcome)
        if isinstance(receipt_result, Failure):
            return Failure(receipt_result.error)
        prior = self._metadata_by_provider_ref.get(outcome.provider_execution_ref)
        if prior is not None:
            return Failure(
                ExecutionBoundaryConflictError(
                    "OANDA provider execution reference already observed by gateway"
                )
            )
        self._metadata_by_provider_ref[outcome.provider_execution_ref] = metadata
        self._outcomes_by_provider_ref[outcome.provider_execution_ref] = outcome
        return Success(receipt_result.value)

    def cancel(
        self,
        *,
        account: MarketTestAccountIdentity,
        provider_execution_ref: str,
        cancelled_at: datetime,
    ) -> Result[TestExecutionGatewayReceipt, ExecutionBoundaryError]:
        if account != self.configuration.account:
            return Failure(
                OandaPracticeExecutionGatewayValidationError(
                    "gateway cancel account must match Practice configuration"
                )
            )
        try:
            provider_ref = _validate_provider_ref(provider_execution_ref)
            _validate_timestamp(cancelled_at, field_name="cancelled_at")
        except OandaPracticeExecutionGatewayError as error:
            return Failure(error)
        metadata = self._metadata_by_provider_ref.get(provider_ref)
        if metadata is None:
            return Failure(
                ExecutionBoundaryNotFoundError(
                    "gateway cannot cancel an unknown provider execution reference"
                )
            )
        plan_result = build_oanda_practice_order_cancel_plan(
            self.configuration,
            provider_execution_ref=provider_ref,
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
        receipt_result = decode_oanda_practice_order_cancel_response(
            self.configuration,
            provider_execution_ref=provider_ref,
            response=response_result.value,
        )
        if isinstance(receipt_result, Failure):
            return Failure(receipt_result.error)
        receipt = receipt_result.value
        if receipt.recorded_at < cancelled_at:
            return Failure(
                OandaPracticeExecutionGatewayValidationError(
                    "provider cancellation receipt must not predate cancel request"
                )
            )
        return Success(receipt)
