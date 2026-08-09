from __future__ import annotations

from dataclasses import fields, replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

import qore.infrastructure.futures_adapter_contracts as futures
import qore.infrastructure.futures_tradestation_adapter as tradestation
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

_NOW = datetime(2026, 8, 10, 10, 0, tzinfo=UTC)
_ADAPTER_ID = AdapterId(UUID("62000000-0000-0000-0000-000000000001"))
_MARKET_SOURCE = ExternalSourceDescriptor(
    adapter_id=_ADAPTER_ID,
    source_id=SourceId(UUID("62000000-0000-0000-0000-000000000002")),
    port_name=PortName("market-data.tradestation-certification"),
)
_EXECUTION_SOURCE = ExternalSourceDescriptor(
    adapter_id=_ADAPTER_ID,
    source_id=SourceId(UUID("62000000-0000-0000-0000-000000000003")),
    port_name=PortName("execution.tradestation-certification"),
)
_ACCOUNT = TradingAccountId(UUID("62000000-0000-0000-0000-000000000004"))
_RUNTIME = ExecutionRuntimeReference(
    UUID("62000000-0000-0000-0000-000000000005")
)
_MAPPING = futures.FuturesContractMapping(
    provider=tradestation.TRADESTATION_PROVIDER,
    provider_contract_id=futures.FuturesProviderContractId("@ESZ26"),
    instrument=Instrument("ESZ6"),
)


def _uuid(suffix: int) -> UUID:
    return UUID(f"62000000-0000-0000-0000-{suffix:012d}")


def _secret_ref() -> SecretRef:
    return SecretRef(
        ref_id=SecretRefId(_uuid(10)),
        name=AdapterSecretName("oauth"),
        external_reference=SecretExternalReference(
            "vault/futures/tradestation-certification"
        ),
    )


def _profile() -> futures.FuturesAdapterProfile:
    return futures.FuturesAdapterProfile(
        adapter_id=_ADAPTER_ID,
        provider=tradestation.TRADESTATION_PROVIDER,
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
        generation=HostingFencingGeneration(9),
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


def test_tradestation_profile_requires_both_capabilities_and_secret_refs() -> None:
    validated = tradestation.validate_tradestation_profile(_profile())
    assert isinstance(validated, result.Success)

    no_secret = replace(_profile(), secret_refs=())
    rejected = tradestation.validate_tradestation_profile(no_secret)
    assert isinstance(rejected, result.Failure)
    assert isinstance(rejected.error, tradestation.TradeStationFuturesValidationError)


def test_profile_contains_only_secret_references_not_secret_values() -> None:
    profile = _profile()
    assert profile.secret_refs == (_secret_ref(),)
    names = {field.name for field in fields(futures.FuturesAdapterProfile)}
    assert names.isdisjoint(
        {"access_token", "refresh_token", "password", "secret_value", "bearer_token"}
    )


def test_quote_trade_and_bar_payloads_normalize_to_delivery8_contracts() -> None:
    quote = tradestation.TradeStationQuotePayload(
        symbol=tradestation.TradeStationSymbol("@ESZ26"),
        provider_timestamp=_NOW,
        received_at=_NOW + timedelta(milliseconds=5),
        bid=5000.25,
        ask=5000.50,
    )
    normalized_quote = tradestation.normalize_tradestation_quote(
        quote,
        _MAPPING,
        _MARKET_SOURCE,
    )
    assert isinstance(normalized_quote, result.Success)
    assert normalized_quote.value.mapping.instrument == Instrument("ESZ6")
    assert normalized_quote.value.provider_timestamp == _NOW

    trade = tradestation.TradeStationTradePayload(
        symbol=tradestation.TradeStationSymbol("@ESZ26"),
        provider_timestamp=_NOW,
        received_at=_NOW + timedelta(milliseconds=6),
        price=5000.50,
        quantity=3,
    )
    normalized_trade = tradestation.normalize_tradestation_trade(
        trade,
        _MAPPING,
        _MARKET_SOURCE,
    )
    assert isinstance(normalized_trade, result.Success)
    assert normalized_trade.value.price == 5000.50
    assert normalized_trade.value.quantity == 3

    bar = tradestation.TradeStationBarPayload(
        symbol=tradestation.TradeStationSymbol("@ESZ26"),
        opened_at=_NOW,
        closed_at=_NOW + timedelta(minutes=1),
        received_at=_NOW + timedelta(minutes=1, milliseconds=7),
        open=5000.0,
        high=5005.0,
        low=4995.0,
        close=5001.0,
    )
    normalized_bar = tradestation.normalize_tradestation_bar(
        bar,
        _MAPPING,
        _MARKET_SOURCE,
        timeframe=Timeframe(60),
    )
    assert isinstance(normalized_bar, result.Success)
    assert normalized_bar.value.mapping.instrument == Instrument("ESZ6")
    assert normalized_bar.value.closed_at == _NOW + timedelta(minutes=1)


def test_provider_symbol_mismatch_fails_closed() -> None:
    payload = tradestation.TradeStationQuotePayload(
        symbol=tradestation.TradeStationSymbol("@NQZ26"),
        provider_timestamp=_NOW,
        received_at=_NOW + timedelta(milliseconds=5),
        bid=20000.0,
        ask=20000.25,
    )
    normalized = tradestation.normalize_tradestation_quote(
        payload,
        _MAPPING,
        _MARKET_SOURCE,
    )
    assert isinstance(normalized, result.Failure)
    assert isinstance(normalized.error, tradestation.TradeStationFuturesValidationError)


def test_sim_order_translation_preserves_upstream_decision_and_idempotency_shape() -> None:
    request = _request()
    translated = tradestation.translate_tradestation_sim_order(
        request,
        account_ref=tradestation.TradeStationSimAccountReference(_uuid(40)),
    )

    assert isinstance(translated, result.Success)
    assert translated.value.request_id == request.request_id
    assert translated.value.symbol == tradestation.TradeStationSymbol("@ESZ26")
    assert translated.value.action is tradestation.TradeStationOrderAction.BUY
    assert translated.value.order_type is tradestation.TradeStationOrderType.MARKET
    assert translated.value.client_order_id == request.idempotency_key.value
    assert request.decision_id == DecisionId(_uuid(130))


def test_paper_request_is_not_silently_routed_to_tradestation_sim() -> None:
    request = _request(
        suffix=50,
        environment=futures.FuturesExecutionEnvironment.PAPER,
    )
    translated = tradestation.translate_tradestation_sim_order(
        request,
        account_ref=tradestation.TradeStationSimAccountReference(_uuid(51)),
    )

    assert isinstance(translated, result.Failure)
    assert isinstance(translated.error, tradestation.TradeStationFuturesValidationError)


def test_limit_and_stop_orders_translate_without_strategy_mutation() -> None:
    limit_request = replace(
        _request(suffix=60),
        order_type=futures.FuturesOrderType.LIMIT,
        limit_price=4999.50,
    )
    limit_intent = tradestation.translate_tradestation_sim_order(
        limit_request,
        account_ref=tradestation.TradeStationSimAccountReference(_uuid(61)),
    )
    assert isinstance(limit_intent, result.Success)
    assert limit_intent.value.order_type is tradestation.TradeStationOrderType.LIMIT
    assert limit_intent.value.limit_price == 4999.50

    stop_request = replace(
        _request(suffix=62),
        order_type=futures.FuturesOrderType.STOP,
        stop_price=5006.0,
    )
    stop_intent = tradestation.translate_tradestation_sim_order(
        stop_request,
        account_ref=tradestation.TradeStationSimAccountReference(_uuid(63)),
    )
    assert isinstance(stop_intent, result.Success)
    assert stop_intent.value.order_type is (
        tradestation.TradeStationOrderType.STOP_MARKET
    )
    assert stop_intent.value.stop_price == 5006.0


def test_unknown_provider_event_becomes_ambiguous_and_never_redispatches() -> None:
    request = _request(suffix=70)
    payload = tradestation.TradeStationExecutionEventPayload(
        request_id=request.request_id,
        event_type=tradestation.TradeStationExecutionEventType.UNKNOWN,
        provider_order_id=None,
        cumulative_filled_quantity=0,
        observed_at=request.requested_at + timedelta(milliseconds=20),
        evidence_ref=futures.FuturesExecutionEvidenceReference(_uuid(71)),
    )
    normalized = tradestation.normalize_tradestation_execution_event(
        request,
        payload,
        observation_id=futures.FuturesExecutionObservationId(_uuid(72)),
    )

    assert isinstance(normalized, result.Success)
    assert normalized.value.state is futures.FuturesExecutionState.AMBIGUOUS
    assert not hasattr(normalized.value, "retry")
    assert not hasattr(normalized.value, "redispatch")


def test_ack_partial_and_fill_normalize_with_exact_fill_bounds() -> None:
    request = _request(suffix=80, quantity=2)
    for event_type, filled, suffix in (
        (tradestation.TradeStationExecutionEventType.ACKNOWLEDGED, 0, 81),
        (tradestation.TradeStationExecutionEventType.PARTIAL_FILL, 1, 82),
        (tradestation.TradeStationExecutionEventType.FILL, 2, 83),
    ):
        payload = tradestation.TradeStationExecutionEventPayload(
            request_id=request.request_id,
            event_type=event_type,
            provider_order_id="sim-order-1",
            cumulative_filled_quantity=filled,
            observed_at=request.requested_at + timedelta(milliseconds=suffix),
            evidence_ref=futures.FuturesExecutionEvidenceReference(_uuid(suffix + 100)),
        )
        normalized = tradestation.normalize_tradestation_execution_event(
            request,
            payload,
            observation_id=futures.FuturesExecutionObservationId(_uuid(suffix + 200)),
        )
        assert isinstance(normalized, result.Success)


def test_unknown_reconciliation_maps_to_canonical_ambiguity() -> None:
    request = _request(suffix=90)
    payload = tradestation.TradeStationReconciliationPayload(
        request_id=request.request_id,
        status=tradestation.TradeStationReconciliationStatus.UNKNOWN,
        reconciled_at=request.requested_at + timedelta(seconds=1),
        evidence_refs=(futures.FuturesExecutionEvidenceReference(_uuid(91)),),
    )
    normalized = tradestation.normalize_tradestation_reconciliation(payload)

    assert isinstance(normalized, result.Success)
    assert normalized.value.status is (
        futures.FuturesExecutionReconciliationStatus.AMBIGUOUS
    )


def test_tradestation_adapter_has_no_live_environment_or_network_execution_method() -> None:
    prohibited = {
        "live",
        "production",
        "send_order",
        "submit_order",
        "retry_order",
        "redispatch",
        "http_client",
        "oauth_client",
    }
    assert prohibited.isdisjoint(set(dir(tradestation.TradeStationSimOrderIntent)))
    assert prohibited.isdisjoint(set(dir(tradestation.TradeStationExecutionEventPayload)))
    assert "LIVE" not in {item.name for item in futures.FuturesExecutionEnvironment}
    assert "PRODUCTION" not in {
        item.name for item in futures.FuturesExecutionEnvironment
    }
