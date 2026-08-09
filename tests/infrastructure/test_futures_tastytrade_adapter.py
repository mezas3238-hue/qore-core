from __future__ import annotations

from dataclasses import fields, replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

import qore.infrastructure.futures_adapter_contracts as futures
import qore.infrastructure.futures_tastytrade_adapter as tastytrade
import qore.kernel.result as result
from qore.functional.decisions import DecisionId
from qore.infrastructure.adapter_configuration import AdapterSecretName
from qore.infrastructure.client_accounts import (
    ExecutionRuntimeReference,
    TradingAccountId,
)
from qore.infrastructure.hosting_execution_lease import (
    HostingExecutionAuthorityAttestation,
    HostingExecutionLeaseId,
    HostingFencingGeneration,
    HostingLeaseEvidenceReference,
)
from qore.infrastructure.market_data import Instrument, Timeframe
from qore.infrastructure.ports import (
    AdapterId,
    ExternalSourceDescriptor,
    PortName,
    SourceId,
)
from qore.infrastructure.secrets import (
    SecretExternalReference,
    SecretRef,
    SecretRefId,
)

_NOW = datetime(2026, 8, 10, 12, 0, tzinfo=UTC)
_ADAPTER_ID = AdapterId(UUID("64000000-0000-0000-0000-000000000001"))
_MARKET_SOURCE = ExternalSourceDescriptor(
    adapter_id=_ADAPTER_ID,
    source_id=SourceId(UUID("64000000-0000-0000-0000-000000000002")),
    port_name=PortName("market-data.tastytrade-certification"),
)
_EXECUTION_SOURCE = ExternalSourceDescriptor(
    adapter_id=_ADAPTER_ID,
    source_id=SourceId(UUID("64000000-0000-0000-0000-000000000003")),
    port_name=PortName("execution.tastytrade-certification"),
)
_ACCOUNT = TradingAccountId(UUID("64000000-0000-0000-0000-000000000004"))
_RUNTIME = ExecutionRuntimeReference(
    UUID("64000000-0000-0000-0000-000000000005")
)
_SYMBOL = tastytrade.TastytradeFuturesSymbol("/ESZ6")
_MAPPING = futures.FuturesContractMapping(
    provider=tastytrade.TASTYTRADE_PROVIDER,
    provider_contract_id=futures.FuturesProviderContractId(_SYMBOL.value),
    instrument=Instrument("ESZ6"),
)


def _uuid(suffix: int) -> UUID:
    return UUID(f"64000000-0000-0000-0000-{suffix:012d}")


def _secret_ref() -> SecretRef:
    return SecretRef(
        ref_id=SecretRefId(_uuid(10)),
        name=AdapterSecretName("sandbox-session"),
        external_reference=SecretExternalReference(
            "vault/futures/tastytrade-certification"
        ),
    )


def _profile() -> futures.FuturesAdapterProfile:
    return futures.FuturesAdapterProfile(
        adapter_id=_ADAPTER_ID,
        provider=tastytrade.TASTYTRADE_PROVIDER,
        market_data_source=_MARKET_SOURCE,
        execution_source=_EXECUTION_SOURCE,
        capabilities=(
            futures.FuturesAdapterCapability.MARKET_DATA,
            futures.FuturesAdapterCapability.EXECUTION,
        ),
        secret_refs=(_secret_ref(),),
    )


def _authority() -> HostingExecutionAuthorityAttestation:
    return HostingExecutionAuthorityAttestation(
        account_id=_ACCOUNT,
        runtime_ref=_RUNTIME,
        lease_id=HostingExecutionLeaseId(_uuid(20)),
        generation=HostingFencingGeneration(11),
        evaluated_at=_NOW,
        evidence_ref=HostingLeaseEvidenceReference(_uuid(21)),
    )


def _request(
    *,
    suffix: int = 30,
    quantity: int = 2,
    environment: futures.FuturesExecutionEnvironment = (
        futures.FuturesExecutionEnvironment.SIMULATION
    ),
) -> futures.FuturesExecutionRequest:
    return futures.FuturesExecutionRequest(
        request_id=futures.FuturesExecutionRequestId(_uuid(suffix)),
        account_id=_ACCOUNT,
        runtime_ref=_RUNTIME,
        decision_id=DecisionId(_uuid(suffix + 100)),
        authority=_authority(),
        environment=environment,
        mapping=_MAPPING,
        side=futures.FuturesOrderSide.BUY,
        quantity=quantity,
        order_type=futures.FuturesOrderType.MARKET,
        time_in_force=futures.FuturesTimeInForce.DAY,
        limit_price=None,
        stop_price=None,
        idempotency_key=futures.FuturesIdempotencyKey(_uuid(suffix + 200)),
        requested_at=_NOW + timedelta(seconds=1),
    )


def test_tastytrade_profile_requires_capabilities_and_secret_refs() -> None:
    validated = tastytrade.validate_tastytrade_profile(_profile())
    assert isinstance(validated, result.Success)

    rejected = tastytrade.validate_tastytrade_profile(
        replace(_profile(), secret_refs=())
    )
    assert isinstance(rejected, result.Failure)
    assert isinstance(rejected.error, tastytrade.TastytradeFuturesValidationError)

    names = {field.name for field in fields(futures.FuturesAdapterProfile)}
    assert names.isdisjoint(
        {"login", "password", "account_number", "access_token", "authorization_header"}
    )


def test_sandbox_market_data_is_never_claimed_realtime_certifiable() -> None:
    quote = tastytrade.TastytradeQuotePayload(
        symbol=_SYMBOL,
        data_mode=tastytrade.TastytradeSandboxMarketDataMode.DELAYED_15_MINUTES,
        provider_timestamp=_NOW,
        received_at=_NOW + timedelta(milliseconds=5),
        bid=5000.25,
        ask=5000.50,
    )
    normalized = tastytrade.normalize_tastytrade_quote(
        quote,
        _MAPPING,
        _MARKET_SOURCE,
    )

    assert isinstance(normalized, result.Success)
    assert normalized.value.data_mode is (
        tastytrade.TastytradeSandboxMarketDataMode.DELAYED_15_MINUTES
    )
    assert normalized.value.is_realtime_certifiable is False
    assert tastytrade.TASTYTRADE_SANDBOX_QUOTE_DELAY_MINUTES == 15


def test_unknown_sandbox_data_mode_also_fails_realtime_certification() -> None:
    quote = tastytrade.TastytradeQuotePayload(
        symbol=_SYMBOL,
        data_mode=tastytrade.TastytradeSandboxMarketDataMode.UNKNOWN,
        provider_timestamp=_NOW,
        received_at=_NOW + timedelta(milliseconds=5),
        bid=5000.25,
        ask=5000.50,
    )
    normalized = tastytrade.normalize_tastytrade_quote(
        quote,
        _MAPPING,
        _MARKET_SOURCE,
    )
    assert isinstance(normalized, result.Success)
    assert normalized.value.is_realtime_certifiable is False


def test_trade_and_bar_normalization_preserve_delayed_sandbox_mode() -> None:
    trade = tastytrade.TastytradeTradePayload(
        symbol=_SYMBOL,
        data_mode=tastytrade.TastytradeSandboxMarketDataMode.DELAYED_15_MINUTES,
        provider_timestamp=_NOW,
        received_at=_NOW + timedelta(milliseconds=6),
        price=5000.50,
        quantity=3,
    )
    normalized_trade = tastytrade.normalize_tastytrade_trade(
        trade,
        _MAPPING,
        _MARKET_SOURCE,
    )
    assert isinstance(normalized_trade, result.Success)
    assert normalized_trade.value.is_realtime_certifiable is False

    bar = tastytrade.TastytradeBarPayload(
        symbol=_SYMBOL,
        data_mode=tastytrade.TastytradeSandboxMarketDataMode.DELAYED_15_MINUTES,
        opened_at=_NOW,
        closed_at=_NOW + timedelta(minutes=1),
        received_at=_NOW + timedelta(minutes=1, milliseconds=7),
        open=5000.0,
        high=5005.0,
        low=4995.0,
        close=5001.0,
    )
    normalized_bar = tastytrade.normalize_tastytrade_bar(
        bar,
        _MAPPING,
        _MARKET_SOURCE,
        timeframe=Timeframe(60),
    )
    assert isinstance(normalized_bar, result.Success)
    assert normalized_bar.value.is_realtime_certifiable is False
    assert normalized_bar.value.observation.mapping.instrument == Instrument("ESZ6")


def test_symbol_mismatch_fails_closed() -> None:
    payload = tastytrade.TastytradeQuotePayload(
        symbol=tastytrade.TastytradeFuturesSymbol("/NQZ6"),
        data_mode=tastytrade.TastytradeSandboxMarketDataMode.DELAYED_15_MINUTES,
        provider_timestamp=_NOW,
        received_at=_NOW + timedelta(milliseconds=5),
        bid=20000.0,
        ask=20000.25,
    )
    normalized = tastytrade.normalize_tastytrade_quote(
        payload,
        _MAPPING,
        _MARKET_SOURCE,
    )
    assert isinstance(normalized, result.Failure)


def test_sandbox_reset_requires_reconciliation_not_order_redispatch() -> None:
    assert tastytrade.classify_tastytrade_sandbox_continuity(
        tastytrade.TastytradeSandboxLifecycleState.CURRENT
    ) is tastytrade.TastytradeSandboxContinuityDisposition.CONTINUE
    assert tastytrade.classify_tastytrade_sandbox_continuity(
        tastytrade.TastytradeSandboxLifecycleState.RESET_DETECTED
    ) is tastytrade.TastytradeSandboxContinuityDisposition.RECONCILE_SANDBOX_STATE
    assert tastytrade.classify_tastytrade_sandbox_continuity(
        tastytrade.TastytradeSandboxLifecycleState.UNKNOWN
    ) is tastytrade.TastytradeSandboxContinuityDisposition.BLOCK

    dispositions = {
        item.value for item in tastytrade.TastytradeSandboxContinuityDisposition
    }
    assert dispositions.isdisjoint({"retry_order", "redispatch", "resend_order"})


def test_sandbox_order_translation_preserves_authority_and_idempotency() -> None:
    request = _request()
    translated = tastytrade.translate_tastytrade_sandbox_order(
        request,
        account_ref=tastytrade.TastytradeSandboxAccountReference(_uuid(40)),
    )

    assert isinstance(translated, result.Success)
    assert translated.value.request_id == request.request_id
    assert translated.value.symbol == _SYMBOL
    assert translated.value.action is tastytrade.TastytradeOrderAction.BUY
    assert translated.value.order_type is tastytrade.TastytradeOrderType.MARKET
    assert translated.value.client_order_id == request.idempotency_key.value
    assert request.decision_id == DecisionId(_uuid(130))


def test_paper_request_is_not_silently_routed_to_tastytrade_sandbox() -> None:
    request = _request(
        suffix=50,
        environment=futures.FuturesExecutionEnvironment.PAPER,
    )
    translated = tastytrade.translate_tastytrade_sandbox_order(
        request,
        account_ref=tastytrade.TastytradeSandboxAccountReference(_uuid(51)),
    )
    assert isinstance(translated, result.Failure)
    assert isinstance(translated.error, tastytrade.TastytradeFuturesValidationError)


def test_limit_and_stop_translation_do_not_mutate_upstream_strategy() -> None:
    limit_request = replace(
        _request(suffix=60),
        order_type=futures.FuturesOrderType.LIMIT,
        limit_price=4999.50,
    )
    limit_intent = tastytrade.translate_tastytrade_sandbox_order(
        limit_request,
        account_ref=tastytrade.TastytradeSandboxAccountReference(_uuid(61)),
    )
    assert isinstance(limit_intent, result.Success)
    assert limit_intent.value.order_type is tastytrade.TastytradeOrderType.LIMIT
    assert limit_intent.value.limit_price == 4999.50

    stop_request = replace(
        _request(suffix=62),
        order_type=futures.FuturesOrderType.STOP,
        stop_price=5006.0,
    )
    stop_intent = tastytrade.translate_tastytrade_sandbox_order(
        stop_request,
        account_ref=tastytrade.TastytradeSandboxAccountReference(_uuid(63)),
    )
    assert isinstance(stop_intent, result.Success)
    assert stop_intent.value.order_type is tastytrade.TastytradeOrderType.STOP
    assert stop_intent.value.stop_price == 5006.0


def test_unknown_execution_event_becomes_ambiguous_without_retry() -> None:
    request = _request(suffix=70)
    payload = tastytrade.TastytradeExecutionEventPayload(
        request_id=request.request_id,
        event_type=tastytrade.TastytradeExecutionEventType.UNKNOWN,
        provider_order_id=None,
        cumulative_filled_quantity=0,
        observed_at=request.requested_at + timedelta(milliseconds=20),
        evidence_ref=futures.FuturesExecutionEvidenceReference(_uuid(71)),
    )
    normalized = tastytrade.normalize_tastytrade_execution_event(
        request,
        payload,
        observation_id=futures.FuturesExecutionObservationId(_uuid(72)),
    )
    assert isinstance(normalized, result.Success)
    assert normalized.value.state is futures.FuturesExecutionState.AMBIGUOUS
    assert not hasattr(normalized.value, "retry")
    assert not hasattr(normalized.value, "redispatch")


def test_accepted_partial_fill_and_fill_use_delivery8_fill_bounds() -> None:
    request = _request(suffix=80, quantity=2)
    for event_type, filled, suffix in (
        (tastytrade.TastytradeExecutionEventType.ACCEPTED, 0, 81),
        (tastytrade.TastytradeExecutionEventType.PARTIAL_FILL, 1, 82),
        (tastytrade.TastytradeExecutionEventType.FILL, 2, 83),
    ):
        payload = tastytrade.TastytradeExecutionEventPayload(
            request_id=request.request_id,
            event_type=event_type,
            provider_order_id="sandbox-order-1",
            cumulative_filled_quantity=filled,
            observed_at=request.requested_at + timedelta(milliseconds=suffix),
            evidence_ref=futures.FuturesExecutionEvidenceReference(_uuid(suffix + 100)),
        )
        normalized = tastytrade.normalize_tastytrade_execution_event(
            request,
            payload,
            observation_id=futures.FuturesExecutionObservationId(_uuid(suffix + 200)),
        )
        assert isinstance(normalized, result.Success)


def test_unknown_reconciliation_maps_to_canonical_ambiguity() -> None:
    request = _request(suffix=90)
    payload = tastytrade.TastytradeReconciliationPayload(
        request_id=request.request_id,
        status=tastytrade.TastytradeReconciliationStatus.UNKNOWN,
        reconciled_at=request.requested_at + timedelta(seconds=1),
        evidence_refs=(futures.FuturesExecutionEvidenceReference(_uuid(91)),),
    )
    normalized = tastytrade.normalize_tastytrade_reconciliation(payload)
    assert isinstance(normalized, result.Success)
    assert normalized.value.status is futures.FuturesExecutionReconciliationStatus.AMBIGUOUS


def test_adapter_has_no_production_client_or_order_retry_surface() -> None:
    prohibited = {
        "production",
        "submit_order",
        "send_order",
        "retry_order",
        "redispatch",
        "http_client",
        "dxlink_client",
        "session_token",
    }
    for surface in (
        tastytrade.TastytradeSandboxOrderIntent,
        tastytrade.TastytradeExecutionEventPayload,
        tastytrade.TastytradeNormalizedQuote,
        tastytrade.TastytradeNormalizedBar,
    ):
        assert prohibited.isdisjoint(set(dir(surface)))
