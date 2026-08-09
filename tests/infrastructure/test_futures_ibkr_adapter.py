from __future__ import annotations

from dataclasses import fields, replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

import qore.infrastructure.futures_adapter_contracts as futures
import qore.infrastructure.futures_ibkr_adapter as ibkr
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

_NOW = datetime(2026, 8, 10, 11, 0, tzinfo=UTC)
_ADAPTER_ID = AdapterId(UUID("63000000-0000-0000-0000-000000000001"))
_MARKET_SOURCE = ExternalSourceDescriptor(
    adapter_id=_ADAPTER_ID,
    source_id=SourceId(UUID("63000000-0000-0000-0000-000000000002")),
    port_name=PortName("market-data.ibkr-certification"),
)
_EXECUTION_SOURCE = ExternalSourceDescriptor(
    adapter_id=_ADAPTER_ID,
    source_id=SourceId(UUID("63000000-0000-0000-0000-000000000003")),
    port_name=PortName("execution.ibkr-certification"),
)
_ACCOUNT = TradingAccountId(UUID("63000000-0000-0000-0000-000000000004"))
_RUNTIME = ExecutionRuntimeReference(
    UUID("63000000-0000-0000-0000-000000000005")
)
_CONTRACT_ID = ibkr.IBKRContractId(123456789)
_MAPPING = futures.FuturesContractMapping(
    provider=ibkr.IBKR_PROVIDER,
    provider_contract_id=futures.FuturesProviderContractId(str(_CONTRACT_ID.value)),
    instrument=Instrument("ESZ6"),
)


def _uuid(suffix: int) -> UUID:
    return UUID(f"63000000-0000-0000-0000-{suffix:012d}")


def _secret_ref() -> SecretRef:
    return SecretRef(
        ref_id=SecretRefId(_uuid(10)),
        name=AdapterSecretName("session"),
        external_reference=SecretExternalReference("vault/futures/ibkr-certification"),
    )


def _profile() -> futures.FuturesAdapterProfile:
    return futures.FuturesAdapterProfile(
        adapter_id=_ADAPTER_ID,
        provider=ibkr.IBKR_PROVIDER,
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
        generation=HostingFencingGeneration(10),
        evaluated_at=_NOW,
        evidence_ref=HostingLeaseEvidenceReference(_uuid(21)),
    )


def _request(
    *,
    suffix: int = 30,
    quantity: int = 2,
    environment: futures.FuturesExecutionEnvironment = futures.FuturesExecutionEnvironment.PAPER,
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


def test_ibkr_profile_requires_capabilities_and_opaque_secret_refs() -> None:
    validated = ibkr.validate_ibkr_profile(_profile())
    assert isinstance(validated, result.Success)

    rejected = ibkr.validate_ibkr_profile(replace(_profile(), secret_refs=()))
    assert isinstance(rejected, result.Failure)
    assert isinstance(rejected.error, ibkr.IBKRFuturesValidationError)

    names = {field.name for field in fields(futures.FuturesAdapterProfile)}
    assert names.isdisjoint(
        {"username", "account_code", "password", "token", "authorization_header"}
    )


def test_contract_id_is_provider_specific_and_must_match_mapping() -> None:
    quote = ibkr.IBKRQuotePayload(
        contract_id=_CONTRACT_ID,
        data_mode=ibkr.IBKRMarketDataMode.REALTIME,
        provider_timestamp=_NOW,
        received_at=_NOW + timedelta(milliseconds=4),
        bid=5000.25,
        ask=5000.50,
    )
    normalized = ibkr.normalize_ibkr_quote(quote, _MAPPING, _MARKET_SOURCE)
    assert isinstance(normalized, result.Success)
    assert normalized.value.observation.mapping.instrument == Instrument("ESZ6")

    wrong = replace(quote, contract_id=ibkr.IBKRContractId(987654321))
    rejected = ibkr.normalize_ibkr_quote(wrong, _MAPPING, _MARKET_SOURCE)
    assert isinstance(rejected, result.Failure)


def test_realtime_delayed_and_unknown_market_data_modes_are_preserved() -> None:
    for mode, expected in (
        (ibkr.IBKRMarketDataMode.REALTIME, True),
        (ibkr.IBKRMarketDataMode.DELAYED, False),
        (ibkr.IBKRMarketDataMode.UNKNOWN, False),
    ):
        payload = ibkr.IBKRQuotePayload(
            contract_id=_CONTRACT_ID,
            data_mode=mode,
            provider_timestamp=_NOW,
            received_at=_NOW + timedelta(milliseconds=4),
            bid=5000.25,
            ask=5000.50,
        )
        normalized = ibkr.normalize_ibkr_quote(payload, _MAPPING, _MARKET_SOURCE)
        assert isinstance(normalized, result.Success)
        assert normalized.value.data_mode is mode
        assert normalized.value.is_realtime_certifiable is expected


def test_trade_and_bar_normalization_preserve_data_mode_and_provider_timing() -> None:
    trade = ibkr.IBKRTradePayload(
        contract_id=_CONTRACT_ID,
        data_mode=ibkr.IBKRMarketDataMode.DELAYED,
        provider_timestamp=_NOW,
        received_at=_NOW + timedelta(milliseconds=6),
        price=5000.50,
        quantity=3,
    )
    normalized_trade = ibkr.normalize_ibkr_trade(trade, _MAPPING, _MARKET_SOURCE)
    assert isinstance(normalized_trade, result.Success)
    assert normalized_trade.value.data_mode is ibkr.IBKRMarketDataMode.DELAYED
    assert normalized_trade.value.is_realtime_certifiable is False

    bar = ibkr.IBKRBarPayload(
        contract_id=_CONTRACT_ID,
        data_mode=ibkr.IBKRMarketDataMode.REALTIME,
        opened_at=_NOW,
        closed_at=_NOW + timedelta(minutes=1),
        received_at=_NOW + timedelta(minutes=1, milliseconds=7),
        open=5000.0,
        high=5005.0,
        low=4995.0,
        close=5001.0,
    )
    normalized_bar = ibkr.normalize_ibkr_bar(
        bar,
        _MAPPING,
        _MARKET_SOURCE,
        timeframe=Timeframe(60),
    )
    assert isinstance(normalized_bar, result.Success)
    assert normalized_bar.value.is_realtime_certifiable is True
    assert normalized_bar.value.observation.closed_at == _NOW + timedelta(minutes=1)


def test_provider_stream_end_requires_market_data_resubscription_only() -> None:
    assert ibkr.classify_ibkr_market_data_continuity(
        ibkr.IBKRMarketDataSessionObservation.ACTIVE
    ) is ibkr.IBKRMarketDataContinuityState.ACTIVE
    assert ibkr.classify_ibkr_market_data_continuity(
        ibkr.IBKRMarketDataSessionObservation.PROVIDER_STREAM_ENDED
    ) is ibkr.IBKRMarketDataContinuityState.RESUBSCRIPTION_REQUIRED
    assert ibkr.classify_ibkr_market_data_continuity(
        ibkr.IBKRMarketDataSessionObservation.SESSION_UNAUTHORIZED
    ) is ibkr.IBKRMarketDataContinuityState.BLOCKED
    assert ibkr.classify_ibkr_market_data_continuity(
        ibkr.IBKRMarketDataSessionObservation.UNKNOWN
    ) is ibkr.IBKRMarketDataContinuityState.BLOCKED

    states = {item.value for item in ibkr.IBKRMarketDataContinuityState}
    assert states.isdisjoint({"retry_order", "redispatch", "resend_order"})


def test_paper_order_translation_preserves_upstream_authority_and_idempotency() -> None:
    request = _request()
    translated = ibkr.translate_ibkr_paper_order(
        request,
        account_ref=ibkr.IBKRPaperAccountReference(_uuid(40)),
    )

    assert isinstance(translated, result.Success)
    assert translated.value.request_id == request.request_id
    assert translated.value.contract_id == _CONTRACT_ID
    assert translated.value.action is ibkr.IBKROrderAction.BUY
    assert translated.value.order_type is ibkr.IBKROrderType.MARKET
    assert translated.value.order_ref == request.idempotency_key.value
    assert request.decision_id == DecisionId(_uuid(130))


def test_simulation_request_is_not_silently_routed_to_ibkr_paper() -> None:
    request = _request(
        suffix=50,
        environment=futures.FuturesExecutionEnvironment.SIMULATION,
    )
    translated = ibkr.translate_ibkr_paper_order(
        request,
        account_ref=ibkr.IBKRPaperAccountReference(_uuid(51)),
    )
    assert isinstance(translated, result.Failure)
    assert isinstance(translated.error, ibkr.IBKRFuturesValidationError)


def test_limit_and_stop_translation_do_not_mutate_strategy() -> None:
    limit_request = replace(
        _request(suffix=60),
        order_type=futures.FuturesOrderType.LIMIT,
        limit_price=4999.50,
    )
    limit_intent = ibkr.translate_ibkr_paper_order(
        limit_request,
        account_ref=ibkr.IBKRPaperAccountReference(_uuid(61)),
    )
    assert isinstance(limit_intent, result.Success)
    assert limit_intent.value.order_type is ibkr.IBKROrderType.LIMIT
    assert limit_intent.value.limit_price == 4999.50

    stop_request = replace(
        _request(suffix=62),
        order_type=futures.FuturesOrderType.STOP,
        stop_price=5006.0,
    )
    stop_intent = ibkr.translate_ibkr_paper_order(
        stop_request,
        account_ref=ibkr.IBKRPaperAccountReference(_uuid(63)),
    )
    assert isinstance(stop_intent, result.Success)
    assert stop_intent.value.order_type is ibkr.IBKROrderType.STOP
    assert stop_intent.value.stop_price == 5006.0


def test_unknown_execution_event_becomes_ambiguous_without_retry() -> None:
    request = _request(suffix=70)
    payload = ibkr.IBKRExecutionEventPayload(
        request_id=request.request_id,
        event_type=ibkr.IBKRExecutionEventType.UNKNOWN,
        provider_order_id=None,
        cumulative_filled_quantity=0,
        observed_at=request.requested_at + timedelta(milliseconds=20),
        evidence_ref=futures.FuturesExecutionEvidenceReference(_uuid(71)),
    )
    normalized = ibkr.normalize_ibkr_execution_event(
        request,
        payload,
        observation_id=futures.FuturesExecutionObservationId(_uuid(72)),
    )
    assert isinstance(normalized, result.Success)
    assert normalized.value.state is futures.FuturesExecutionState.AMBIGUOUS
    assert not hasattr(normalized.value, "retry")
    assert not hasattr(normalized.value, "redispatch")


def test_ack_partial_fill_and_fill_use_delivery8_fill_bounds() -> None:
    request = _request(suffix=80, quantity=2)
    for event_type, filled, suffix in (
        (ibkr.IBKRExecutionEventType.ACKNOWLEDGED, 0, 81),
        (ibkr.IBKRExecutionEventType.PARTIAL_FILL, 1, 82),
        (ibkr.IBKRExecutionEventType.FILL, 2, 83),
    ):
        payload = ibkr.IBKRExecutionEventPayload(
            request_id=request.request_id,
            event_type=event_type,
            provider_order_id="paper-order-1",
            cumulative_filled_quantity=filled,
            observed_at=request.requested_at + timedelta(milliseconds=suffix),
            evidence_ref=futures.FuturesExecutionEvidenceReference(_uuid(suffix + 100)),
        )
        normalized = ibkr.normalize_ibkr_execution_event(
            request,
            payload,
            observation_id=futures.FuturesExecutionObservationId(_uuid(suffix + 200)),
        )
        assert isinstance(normalized, result.Success)


def test_unknown_reconciliation_maps_to_canonical_ambiguity() -> None:
    request = _request(suffix=90)
    payload = ibkr.IBKRReconciliationPayload(
        request_id=request.request_id,
        status=ibkr.IBKRReconciliationStatus.UNKNOWN,
        reconciled_at=request.requested_at + timedelta(seconds=1),
        evidence_refs=(futures.FuturesExecutionEvidenceReference(_uuid(91)),),
    )
    normalized = ibkr.normalize_ibkr_reconciliation(payload)
    assert isinstance(normalized, result.Success)
    assert normalized.value.status is futures.FuturesExecutionReconciliationStatus.AMBIGUOUS


def test_ibkr_adapter_has_no_network_client_production_or_order_retry_surface() -> None:
    prohibited = {
        "production",
        "live",
        "submit_order",
        "send_order",
        "retry_order",
        "redispatch",
        "tws_client",
        "web_api_client",
        "gateway_client",
    }
    for surface in (
        ibkr.IBKRPaperOrderIntent,
        ibkr.IBKRExecutionEventPayload,
        ibkr.IBKRNormalizedQuote,
        ibkr.IBKRNormalizedBar,
    ):
        assert prohibited.isdisjoint(set(dir(surface)))
