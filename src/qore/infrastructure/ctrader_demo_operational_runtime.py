from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from qore.infrastructure.ctrader_demo_execution_configuration import (
    CTraderDemoRuntimeConfiguration,
)
from qore.infrastructure.ctrader_demo_execution_contracts import (
    CTraderDemoFillObservation,
    CTraderDemoFillReconciliation,
)
from qore.infrastructure.ctrader_demo_execution_gateway import (
    CTraderDemoExecutionGateway,
)
from qore.infrastructure.ctrader_demo_market_data import (
    CTraderDemoMarketDataFlow,
    CTraderDemoMarketDataPayloadAdapter,
)
from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiCredentials,
    CTraderOpenApiMessageClientBoundary,
    SpotwareCTraderOpenApiClient,
)
from qore.infrastructure.ctrader_open_api_market_data_client import (
    CTraderOpenApiMarketDataClient,
)
from qore.infrastructure.ctrader_open_api_transport import (
    CTraderOpenApiExecutionTransport,
)
from qore.infrastructure.execution_boundary import (
    ExecutionBoundaryError,
    ExecutionReceipt,
    ExecutionSubmission,
)
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
    MarketTestEnvironmentAuthorization,
)
from qore.infrastructure.ports import (
    ExternalHealth,
    ExternalPortError,
    ExternalRequestMetadata,
    ExternalSourceDescriptor,
    PortAvailability,
)
from qore.infrastructure.test_execution_adapter import AuthorizedTestExecutionAdapter
from qore.kernel.result import Failure, Result, Success


class CTraderDemoOperationalRuntimeError(ExecutionBoundaryError):
    """Sanitized base error for the composed cTrader DEMO runtime."""

    __slots__ = ()


class CTraderDemoOperationalRuntimeValidationError(CTraderDemoOperationalRuntimeError):
    """The runtime composition is not demonstrably DEMO-only."""

    __slots__ = ()


@dataclass(frozen=True, slots=True)
class CTraderDemoSubmissionResult:
    """Canonical receipt plus provider and fill evidence for one authorized mutation."""

    receipt: ExecutionReceipt
    provider_order_ref: str
    fills: tuple[CTraderDemoFillObservation, ...]


class CTraderDemoOperationalRuntime:
    """One authenticated DEMO session shared by market data and authorized execution.

    This composition cannot create trading authority. It accepts only a canonical
    ``ExecutionSubmission`` that already contains the upstream pre-trade approval,
    and it additionally enforces the explicit TEST/DEMO environment authorization.
    """

    __slots__ = (
        "_client",
        "_clock",
        "_configuration",
        "_environment_authorization",
        "_execution",
        "_gateway",
        "_market_data",
        "_market_client",
        "_transport",
    )

    def __init__(
        self,
        *,
        configuration: CTraderDemoRuntimeConfiguration,
        credentials: CTraderOpenApiCredentials,
        environment_authorization: MarketTestEnvironmentAuthorization,
        market_data_descriptor: ExternalSourceDescriptor,
        client: CTraderOpenApiMessageClientBoundary | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if not isinstance(configuration, CTraderDemoRuntimeConfiguration):
            raise CTraderDemoOperationalRuntimeValidationError(
                "configuration must be CTraderDemoRuntimeConfiguration"
            )
        if configuration.environment is not MarketRuntimeEnvironment.DEMO:
            raise CTraderDemoOperationalRuntimeValidationError(
                "operational runtime is restricted to cTrader DEMO"
            )
        if not isinstance(environment_authorization, MarketTestEnvironmentAuthorization):
            raise CTraderDemoOperationalRuntimeValidationError(
                "environment authorization must be explicit"
            )
        if environment_authorization.account != configuration.account:
            raise CTraderDemoOperationalRuntimeValidationError(
                "environment authorization must match the configured DEMO account"
            )
        if not isinstance(credentials, CTraderOpenApiCredentials):
            raise CTraderDemoOperationalRuntimeValidationError(
                "credentials must be CTraderOpenApiCredentials"
            )
        if str(credentials.ctid_trader_account_id) != configuration.account.account_ref:
            raise CTraderDemoOperationalRuntimeValidationError(
                "credential account must match the configured DEMO account"
            )
        runtime_client = client or SpotwareCTraderOpenApiClient(credentials=credentials)
        if runtime_client.account_id != credentials.ctid_trader_account_id:
            raise CTraderDemoOperationalRuntimeValidationError(
                "injected client account must match the supplied credentials"
            )
        runtime_clock = clock or (lambda: datetime.now(UTC))
        transport = CTraderOpenApiExecutionTransport(
            configuration=configuration,
            client=runtime_client,
            clock=runtime_clock,
        )
        gateway = CTraderDemoExecutionGateway(
            configuration=configuration,
            transport=transport,
        )
        market_client = CTraderOpenApiMarketDataClient(
            descriptor=market_data_descriptor,
            configuration=configuration,
            client=runtime_client,
            clock=runtime_clock,
        )
        self._configuration = configuration
        self._environment_authorization = environment_authorization
        self._client = runtime_client
        self._clock = runtime_clock
        self._transport = transport
        self._gateway = gateway
        self._execution = AuthorizedTestExecutionAdapter(
            environment_authorization=environment_authorization,
            gateway=gateway,
        )
        self._market_data = CTraderDemoMarketDataFlow(
            CTraderDemoMarketDataPayloadAdapter(client=market_client)
        )
        self._market_client = market_client

    @property
    def configuration(self) -> CTraderDemoRuntimeConfiguration:
        return self._configuration

    @property
    def market_data(self) -> CTraderDemoMarketDataFlow:
        return self._market_data

    @property
    def execution(self) -> AuthorizedTestExecutionAdapter:
        return self._execution

    def connect(
        self,
        *,
        checked_at: datetime,
        metadata: ExternalRequestMetadata,
    ) -> Result[ExternalHealth, ExternalPortError]:
        """Authenticate app/account and return sanitized provider health."""
        health = self._market_data.payload_adapter.health(
            checked_at=checked_at,
            metadata=metadata,
        )
        if isinstance(health, Failure):
            return health
        if health.value.availability is not PortAvailability.AVAILABLE:
            return health
        validated = self._market_client.validate_symbol_mappings()
        if isinstance(validated, Failure):
            return validated
        return health

    def submit_authorized(
        self,
        submission: ExecutionSubmission,
    ) -> Result[CTraderDemoSubmissionResult, ExecutionBoundaryError]:
        """Perform one DEMO mutation only for an already-authorized submission."""
        if not isinstance(submission, ExecutionSubmission):
            return Failure(
                CTraderDemoOperationalRuntimeValidationError(
                    "submit_authorized requires ExecutionSubmission"
                )
            )
        validated = self._market_client.validate_symbol_mappings()
        if isinstance(validated, Failure):
            return Failure(
                CTraderDemoOperationalRuntimeError(
                    "cTrader DEMO symbol preflight failed before mutation"
                )
            )
        receipt_result = self._execution.submit(submission)
        if isinstance(receipt_result, Failure):
            return Failure(receipt_result.error)
        attempt = next(
            (item for item in self._gateway.attempts if item.receipt_id == submission.receipt_id),
            None,
        )
        if attempt is None or attempt.provider_order_ref is None:
            return Failure(
                CTraderDemoOperationalRuntimeValidationError(
                    "accepted cTrader execution is missing its provider reference"
                )
            )
        fills_result = self._ingest_pending_fills(
            submission,
            provider_order_ref=attempt.provider_order_ref,
        )
        if isinstance(fills_result, Failure):
            return fills_result
        return Success(
            CTraderDemoSubmissionResult(
                receipt=receipt_result.value,
                provider_order_ref=attempt.provider_order_ref,
                fills=fills_result.value,
            )
        )

    def poll_and_reconcile(
        self,
        submission: ExecutionSubmission,
        *,
        provider_order_ref: str,
        metadata: ExternalRequestMetadata,
    ) -> Result[CTraderDemoFillReconciliation, ExecutionBoundaryError]:
        """Query provider state, ingest native deals, then reconcile cumulative fills."""
        queried = self._transport.query_order(provider_order_ref, metadata=metadata)
        if isinstance(queried, Failure):
            return queried
        fills = self._ingest_pending_fills(
            submission,
            provider_order_ref=provider_order_ref,
        )
        if isinstance(fills, Failure):
            return fills
        return self._gateway.reconcile_fills(
            submission.receipt_id,
            reconciled_at=self._clock(),
        )

    def _ingest_pending_fills(
        self,
        submission: ExecutionSubmission,
        *,
        provider_order_ref: str,
    ) -> Result[tuple[CTraderDemoFillObservation, ...], ExecutionBoundaryError]:
        observations: list[CTraderDemoFillObservation] = []
        for payload in self._transport.drain_fill_payloads(provider_order_ref):
            observed = self._gateway.observe_fill(
                submission,
                payload,
                received_at=self._clock(),
            )
            if isinstance(observed, Failure):
                return Failure(observed.error)
            observations.append(observed.value)
        return Success(tuple(observations))

    def close(self) -> None:
        self._client.close()
