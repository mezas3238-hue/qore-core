from __future__ import annotations

from dataclasses import fields, replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

import qore.infrastructure.futures_adapter_contracts as futures
import qore.infrastructure.futures_tradovate_candidate as tradovate
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
_ADAPTER_ID = AdapterId(UUID("68000000-0000-0000-0000-000000000001"))
_MARKET_SOURCE = ExternalSourceDescriptor(
    adapter_id=_ADAPTER_ID,
    source_id=SourceId(UUID("68000000-0000-0000-0000-000000000002")),
    port_name=PortName("market-data.tradovate-candidate"),
)
_EXECUTION_SOURCE = ExternalSourceDescriptor(
    adapter_id=_ADAPTER_ID,
    source_id=SourceId(UUID("68000000-0000-0000-0000-000000000003")),
    port_name=PortName("execution.tradovate-candidate"),
)
_ACCOUNT = TradingAccountId(UUID("68000000-0000-0000-0000-000000000004"))
_RUNTIME = ExecutionRuntimeReference(
    UUID("68000000-0000-0000-0000-000000000005")
)
_MAPPING = futures.FuturesContractMapping(
    provider=tradovate.TRADOVATE_PROVIDER,
    provider_contract_id=futures.FuturesProviderContractId("ESZ6"),
    instrument=Instrument("ESZ6"),
)


def _uuid(suffix: int) -> UUID:
    return UUID(f"68000000-0000-0000-0000-{suffix:012d}")


def _secret_ref() -> SecretRef:
    return SecretRef(
        ref_id=SecretRefId(_uuid(10)),
        name=AdapterSecretName("partner-auth"),
        external_reference=SecretExternalReference(
            "vault/futures/tradovate-candidate"
        ),
    )


def _profile() -> futures.FuturesAdapterProfile:
    return futures.FuturesAdapterProfile(
        adapter_id=_ADAPTER_ID,
        provider=tradovate.TRADOVATE_PROVIDER,
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
        quantity=2,
        order_type=futures.FuturesOrderType.MARKET,
        time_in_force=futures.FuturesTimeInForce.DAY,
        limit_price=None,
        stop_price=None,
        idempotency_key=futures.FuturesIdempotencyKey(_uuid(suffix + 200)),
        requested_at=_NOW + timedelta(seconds=1),
    )


def test_candidate_assessment_stays_offline_and_non_production() -> None:
    assessment = tradovate.evaluate_tradovate_candidate()

    assert assessment.provider == tradovate.TRADOVATE_PROVIDER
    assert assessment.status is (
        tradovate.TradovateCandidateStatus.OPERATIONAL_EVIDENCE_REQUIRED
    )
    assert assessment.demo_simulation_supported
    assert assessment.market_data_websocket_supported
    assert not assessment.authenticated_operational_evidence
    assert not assessment.network_io_performed
    assert not assessment.production_authorized


def test_profile_requires_candidate_capabilities_and_opaque_secret_refs() -> None:
    validated = tradovate.validate_tradovate_profile(_profile())
    assert isinstance(validated, result.Success)

    no_secret = replace(_profile(), secret_refs=())
    rejected = tradovate.validate_tradovate_profile(no_secret)
    assert isinstance(rejected, result.Failure)
    assert isinstance(rejected.error, tradovate.TradovateCandidateValidationError)

    names = {field.name for field in fields(futures.FuturesAdapterProfile)}
    assert names.isdisjoint(
        {"access_token", "password", "api_key", "secret_value", "bearer_token"}
    )


def test_quote_trade_and_bar_normalize_to_provider_neutral_contracts() -> None:
    quote = tradovate.TradovateQuotePayload(
        symbol=tradovate.TradovateSymbol("ESZ6"),
        provider_timestamp=_NOW,
        received_at=_NOW + timedelta(milliseconds=5),
        bid=5000.25,
        ask=5000.50,
    )
    normalized_quote = tradovate.normalize_tradovate_quote(
        quote,
        _MAPPING,
        _MARKET_SOURCE,
    )
    assert isinstance(normalized_quote, result.Success)
    assert normalized_quote.value.mapping.instrument == Instrument("ESZ6")
    assert normalized_quote.value.provider_timestamp == _NOW

    trade = tradovate.TradovateTradePayload(
        symbol=tradovate.TradovateSymbol("ESZ6"),
        provider_timestamp=_NOW,
        received_at=_NOW + timedelta(milliseconds=6),
        price=5000.50,
        quantity=3,
    )
    normalized_trade = tradovate.normalize_tradovate_trade(
        trade,
        _MAPPING,
        _MARKET_SOURCE,
    )
    assert isinstance(normalized_trade, result.Success)
    assert normalized_trade.value.price == 5000.50

    bar = tradovate.TradovateBarPayload(
        symbol=tradovate.TradovateSymbol("ESZ6"),
        opened_at=_NOW,
        closed_at=_NOW + timedelta(minutes=1),
        received_at=_NOW + timedelta(minutes=1, milliseconds=7),
        open=5000.0,
        high=5005.0,
        low=4995.0,
        close=5001.0,
    )
    normalized_bar = tradovate.normalize_tradovate_bar(
        bar,
        _MAPPING,
        _MARKET_SOURCE,
        timeframe=Timeframe(60),
    )
    assert isinstance(normalized_bar, result.Success)
    assert normalized_bar.value.closed_at == _NOW + timedelta(minutes=1)


def test_provider_symbol_mismatch_fails_closed() -> None:
    payload = tradovate.TradovateQuotePayload(
        symbol=tradovate.TradovateSymbol("NQZ6"),
        provider_timestamp=_NOW,
        received_at=_NOW + timedelta(milliseconds=5),
        bid=20000.0,
        ask=20000.25,
    )
    normalized = tradovate.normalize_tradovate_quote(
        payload,
        _MAPPING,
        _MARKET_SOURCE,
    )
    assert isinstance(normalized, result.Failure)
    assert isinstance(normalized.error, tradovate.TradovateCandidateValidationError)


def test_demo_translation_preserves_authorized_intent_and_automation_flag() -> None:
    request = _request()
    translated = tradovate.translate_tradovate_demo_order(
        request,
        account_ref=tradovate.TradovateDemoAccountReference(_uuid(40)),
    )

    assert isinstance(translated, result.Success)
    assert translated.value.request_id == request.request_id
    assert translated.value.symbol == tradovate.TradovateSymbol("ESZ6")
    assert translated.value.action is tradovate.TradovateOrderAction.BUY
    assert translated.value.order_type is tradovate.TradovateOrderType.MARKET
    assert translated.value.client_order_id == request.idempotency_key.value
    assert translated.value.is_automated is True
    assert request.decision_id == DecisionId(_uuid(130))


def test_paper_request_is_not_silently_routed_to_tradovate_demo() -> None:
    request = _request(
        suffix=50,
        environment=futures.FuturesExecutionEnvironment.PAPER,
    )
    translated = tradovate.translate_tradovate_demo_order(
        request,
        account_ref=tradovate.TradovateDemoAccountReference(_uuid(51)),
    )

    assert isinstance(translated, result.Failure)
    assert isinstance(translated.error, tradovate.TradovateCandidateValidationError)


def test_limit_and_stop_translation_never_invents_strategy() -> None:
    limit_request = replace(
        _request(suffix=60),
        order_type=futures.FuturesOrderType.LIMIT,
        limit_price=4999.50,
    )
    limit_intent = tradovate.translate_tradovate_demo_order(
        limit_request,
        account_ref=tradovate.TradovateDemoAccountReference(_uuid(61)),
    )
    assert isinstance(limit_intent, result.Success)
    assert limit_intent.value.order_type is tradovate.TradovateOrderType.LIMIT
    assert limit_intent.value.limit_price == 4999.50

    stop_request = replace(
        _request(suffix=62),
        order_type=futures.FuturesOrderType.STOP,
        stop_price=5006.0,
    )
    stop_intent = tradovate.translate_tradovate_demo_order(
        stop_request,
        account_ref=tradovate.TradovateDemoAccountReference(_uuid(63)),
    )
    assert isinstance(stop_intent, result.Success)
    assert stop_intent.value.order_type is tradovate.TradovateOrderType.STOP
    assert stop_intent.value.stop_price == 5006.0


def test_candidate_intent_exposes_no_network_or_live_execution_surface() -> None:
    intent_fields = {field.name for field in fields(tradovate.TradovateDemoOrderIntent)}
    prohibited = {
        "live",
        "production",
        "send_order",
        "submit_order",
        "retry_order",
        "redispatch",
        "http_client",
        "websocket_client",
        "access_token",
        "password",
        "api_key",
    }
    assert prohibited.isdisjoint(intent_fields)
    assert "LIVE" not in {item.name for item in futures.FuturesExecutionEnvironment}
    assert "PRODUCTION" not in {
        item.name for item in futures.FuturesExecutionEnvironment
    }
