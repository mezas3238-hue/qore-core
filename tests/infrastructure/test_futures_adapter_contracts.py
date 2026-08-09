from __future__ import annotations

from dataclasses import fields, replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

import qore.infrastructure.futures_adapter_contracts as futures
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
from qore.infrastructure.market_data import Instrument, MarketDataSnapshotId, Timeframe
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

_NOW = datetime(2026, 8, 10, 9, 0, tzinfo=UTC)
_ADAPTER_ID = AdapterId(UUID("61000000-0000-0000-0000-000000000001"))
_MARKET_SOURCE = ExternalSourceDescriptor(
    adapter_id=_ADAPTER_ID,
    source_id=SourceId(UUID("61000000-0000-0000-0000-000000000002")),
    port_name=PortName("market-data.futures-certification"),
)
_EXECUTION_SOURCE = ExternalSourceDescriptor(
    adapter_id=_ADAPTER_ID,
    source_id=SourceId(UUID("61000000-0000-0000-0000-000000000003")),
    port_name=PortName("execution.futures-certification"),
)
_ACCOUNT = TradingAccountId(UUID("61000000-0000-0000-0000-000000000004"))
_RUNTIME = ExecutionRuntimeReference(
    UUID("61000000-0000-0000-0000-000000000005")
)
_INSTRUMENT = Instrument("ESZ6")
_PROVIDER = futures.FuturesProviderName("certification-provider")
_MAPPING = futures.FuturesContractMapping(
    provider=_PROVIDER,
    provider_contract_id=futures.FuturesProviderContractId("ES-2026-12"),
    instrument=_INSTRUMENT,
)


def _uuid(suffix: int) -> UUID:
    return UUID(f"61000000-0000-0000-0000-{suffix:012d}")


def _authority() -> HostingExecutionAuthorityAttestation:
    return HostingExecutionAuthorityAttestation(
        account_id=_ACCOUNT,
        runtime_ref=_RUNTIME,
        lease_id=HostingExecutionLeaseId(_uuid(10)),
        generation=HostingFencingGeneration(8),
        evaluated_at=_NOW,
        evidence_ref=HostingLeaseEvidenceReference(_uuid(11)),
    )


def _request(
    *,
    suffix: int = 20,
    idempotency_suffix: int = 21,
    quantity: int = 2,
) -> futures.FuturesExecutionRequest:
    return futures.FuturesExecutionRequest(
        request_id=futures.FuturesExecutionRequestId(_uuid(suffix)),
        account_id=_ACCOUNT,
        runtime_ref=_RUNTIME,
        decision_id=DecisionId(_uuid(suffix + 100)),
        authority=_authority(),
        environment=futures.FuturesExecutionEnvironment.SIMULATION,
        mapping=_MAPPING,
        side=futures.FuturesOrderSide.BUY,
        quantity=quantity,
        order_type=futures.FuturesOrderType.MARKET,
        time_in_force=futures.FuturesTimeInForce.DAY,
        limit_price=None,
        stop_price=None,
        idempotency_key=futures.FuturesIdempotencyKey(_uuid(idempotency_suffix)),
        requested_at=_NOW + timedelta(seconds=1),
    )


def test_adapter_profile_uses_canonical_sources_and_secret_refs_only() -> None:
    secret_ref = SecretRef(
        ref_id=SecretRefId(_uuid(30)),
        name=AdapterSecretName("oauth"),
        external_reference=SecretExternalReference(
            "vault/futures/certification-provider"
        ),
    )
    profile = futures.FuturesAdapterProfile(
        adapter_id=_ADAPTER_ID,
        provider=_PROVIDER,
        market_data_source=_MARKET_SOURCE,
        execution_source=_EXECUTION_SOURCE,
        capabilities=(
            futures.FuturesAdapterCapability.MARKET_DATA,
            futures.FuturesAdapterCapability.EXECUTION,
        ),
        secret_refs=(secret_ref,),
    )

    assert profile.secret_refs == (secret_ref,)
    field_names = {field.name for field in fields(futures.FuturesAdapterProfile)}
    assert field_names.isdisjoint(
        {"password", "secret", "secret_value", "token", "authorization_header"}
    )


def test_contract_mapping_keeps_provider_identity_outside_canonical_instrument() -> None:
    assert _MAPPING.instrument == Instrument("ESZ6")
    assert _MAPPING.provider_contract_id == futures.FuturesProviderContractId(
        "ES-2026-12"
    )
    assert _MAPPING.provider == _PROVIDER


def test_quote_and_bar_normalization_preserve_provider_timestamp_and_source() -> None:
    quote = futures.FuturesQuoteObservation(
        mapping=_MAPPING,
        source=_MARKET_SOURCE,
        provider_timestamp=_NOW,
        received_at=_NOW + timedelta(milliseconds=5),
        bid=5000.25,
        ask=5000.50,
    )
    normalized_quote = futures.normalize_futures_quote(
        quote,
        snapshot_id=MarketDataSnapshotId(_uuid(40)),
    )
    assert isinstance(normalized_quote, result.Success)
    assert normalized_quote.value.instrument == _INSTRUMENT
    assert normalized_quote.value.source == _MARKET_SOURCE
    assert normalized_quote.value.observed_at == _NOW

    bar = futures.FuturesBarObservation(
        mapping=_MAPPING,
        source=_MARKET_SOURCE,
        timeframe=Timeframe(60),
        opened_at=_NOW,
        closed_at=_NOW + timedelta(minutes=1),
        received_at=_NOW + timedelta(minutes=1, milliseconds=7),
        open=5000.0,
        high=5005.0,
        low=4995.0,
        close=5001.0,
    )
    normalized_bar = futures.normalize_futures_bar(
        bar,
        snapshot_id=MarketDataSnapshotId(_uuid(41)),
    )
    assert isinstance(normalized_bar, result.Success)
    assert normalized_bar.value.instrument == _INSTRUMENT
    assert normalized_bar.value.opened_at == _NOW
    assert normalized_bar.value.closed_at == _NOW + timedelta(minutes=1)
    assert normalized_bar.value.source == _MARKET_SOURCE


def test_trade_observation_preserves_source_timestamp_price_and_contract_quantity() -> None:
    trade = futures.FuturesTradeObservation(
        mapping=_MAPPING,
        source=_MARKET_SOURCE,
        provider_timestamp=_NOW,
        received_at=_NOW + timedelta(milliseconds=4),
        price=5001.25,
        quantity=3,
    )

    assert trade.mapping.instrument == _INSTRUMENT
    assert trade.provider_timestamp == _NOW
    assert trade.price == 5001.25
    assert trade.quantity == 3


def test_execution_environment_is_strictly_non_production() -> None:
    assert {item.value for item in futures.FuturesExecutionEnvironment} == {
        "paper",
        "simulation",
    }
    assert "production" not in {
        item.value for item in futures.FuturesExecutionEnvironment
    }


def test_execution_request_requires_core_decision_and_exact_writer_attestation_scope() -> None:
    request = _request()

    assert isinstance(request.decision_id, DecisionId)
    assert request.authority.account_id == request.account_id
    assert request.authority.runtime_ref == request.runtime_ref
    request_fields = {field.name: field.type for field in fields(request)}
    assert request_fields["decision_id"] == "DecisionId"
    assert request_fields["authority"] == "HostingExecutionAuthorityAttestation"

    other_account = TradingAccountId(_uuid(50))
    with pytest.raises(futures.FuturesAdapterValidationError):
        futures.FuturesExecutionRequest(
            request_id=futures.FuturesExecutionRequestId(_uuid(51)),
            account_id=other_account,
            runtime_ref=_RUNTIME,
            decision_id=DecisionId(_uuid(52)),
            authority=_authority(),
            environment=futures.FuturesExecutionEnvironment.PAPER,
            mapping=_MAPPING,
            side=futures.FuturesOrderSide.SELL,
            quantity=1,
            order_type=futures.FuturesOrderType.MARKET,
            time_in_force=futures.FuturesTimeInForce.DAY,
            limit_price=None,
            stop_price=None,
            idempotency_key=futures.FuturesIdempotencyKey(_uuid(53)),
            requested_at=_NOW + timedelta(seconds=1),
        )


def test_order_type_price_invariants_are_closed_and_deterministic() -> None:
    limit_request = replace(
        _request(),
        order_type=futures.FuturesOrderType.LIMIT,
        limit_price=4999.50,
    )
    assert limit_request.limit_price == 4999.50

    stop_request = replace(
        _request(suffix=60, idempotency_suffix=61),
        order_type=futures.FuturesOrderType.STOP,
        stop_price=5006.0,
    )
    assert stop_request.stop_price == 5006.0

    with pytest.raises(futures.FuturesAdapterValidationError):
        replace(_request(), limit_price=4999.0)


def test_replay_classification_never_means_retry_or_redispatch() -> None:
    known = _request(suffix=70, idempotency_suffix=71)
    duplicate = replace(
        known,
        request_id=futures.FuturesExecutionRequestId(_uuid(72)),
        requested_at=known.requested_at + timedelta(seconds=1),
    )
    conflict = replace(duplicate, quantity=3)
    unrelated = _request(suffix=73, idempotency_suffix=74)

    assert futures.classify_futures_request_replay(known, None) is (
        futures.FuturesReplayDisposition.NEW_REQUEST_UNSEEN
    )
    assert futures.classify_futures_request_replay(duplicate, known) is (
        futures.FuturesReplayDisposition.DUPLICATE_ALREADY_KNOWN
    )
    assert futures.classify_futures_request_replay(conflict, known) is (
        futures.FuturesReplayDisposition.IDEMPOTENCY_CONFLICT
    )
    assert futures.classify_futures_request_replay(unrelated, known) is (
        futures.FuturesReplayDisposition.NEW_REQUEST_UNSEEN
    )
    assert {item.value for item in futures.FuturesReplayDisposition}.isdisjoint(
        {"retry", "redispatch", "resend"}
    )


def test_ack_partial_fill_fill_and_ambiguous_are_observations_only() -> None:
    request = _request(suffix=80, idempotency_suffix=81, quantity=2)
    provider_ref = futures.FuturesProviderOrderReference("paper-order-1")

    ack = futures.FuturesExecutionObservation(
        observation_id=futures.FuturesExecutionObservationId(_uuid(82)),
        request_id=request.request_id,
        state=futures.FuturesExecutionState.ACKNOWLEDGED,
        provider_order_ref=provider_ref,
        cumulative_filled_quantity=0,
        observed_at=request.requested_at + timedelta(milliseconds=5),
        evidence_ref=futures.FuturesExecutionEvidenceReference(_uuid(83)),
    )
    partial = futures.FuturesExecutionObservation(
        observation_id=futures.FuturesExecutionObservationId(_uuid(84)),
        request_id=request.request_id,
        state=futures.FuturesExecutionState.PARTIALLY_FILLED,
        provider_order_ref=provider_ref,
        cumulative_filled_quantity=1,
        observed_at=request.requested_at + timedelta(milliseconds=8),
        evidence_ref=futures.FuturesExecutionEvidenceReference(_uuid(85)),
    )
    filled = futures.FuturesExecutionObservation(
        observation_id=futures.FuturesExecutionObservationId(_uuid(86)),
        request_id=request.request_id,
        state=futures.FuturesExecutionState.FILLED,
        provider_order_ref=provider_ref,
        cumulative_filled_quantity=2,
        observed_at=request.requested_at + timedelta(milliseconds=12),
        evidence_ref=futures.FuturesExecutionEvidenceReference(_uuid(87)),
    )
    ambiguous = futures.FuturesExecutionObservation(
        observation_id=futures.FuturesExecutionObservationId(_uuid(88)),
        request_id=request.request_id,
        state=futures.FuturesExecutionState.AMBIGUOUS,
        provider_order_ref=None,
        cumulative_filled_quantity=0,
        observed_at=request.requested_at + timedelta(milliseconds=20),
        evidence_ref=futures.FuturesExecutionEvidenceReference(_uuid(89)),
    )

    for observation in (ack, partial, filled, ambiguous):
        validated = futures.validate_futures_execution_observation(
            request,
            observation,
        )
        assert isinstance(validated, result.Success)

    assert ambiguous.state is futures.FuturesExecutionState.AMBIGUOUS
    assert not hasattr(ambiguous, "retry")
    assert not hasattr(ambiguous, "redispatch")


def test_execution_observation_cannot_overfill_or_fake_final_fill() -> None:
    request = _request(suffix=90, idempotency_suffix=91, quantity=2)
    provider_ref = futures.FuturesProviderOrderReference("paper-order-2")
    bad_fill = futures.FuturesExecutionObservation(
        observation_id=futures.FuturesExecutionObservationId(_uuid(92)),
        request_id=request.request_id,
        state=futures.FuturesExecutionState.FILLED,
        provider_order_ref=provider_ref,
        cumulative_filled_quantity=1,
        observed_at=request.requested_at + timedelta(milliseconds=10),
        evidence_ref=futures.FuturesExecutionEvidenceReference(_uuid(93)),
    )

    validated = futures.validate_futures_execution_observation(request, bad_fill)
    assert isinstance(validated, result.Failure)
    assert isinstance(validated.error, futures.FuturesAdapterValidationError)


def test_ambiguous_execution_requires_reconciliation_not_automatic_redispatch() -> None:
    request = _request(suffix=100, idempotency_suffix=101)
    reconciliation = futures.FuturesExecutionReconciliation(
        request_id=request.request_id,
        status=futures.FuturesExecutionReconciliationStatus.AMBIGUOUS,
        reconciled_at=request.requested_at + timedelta(seconds=1),
        evidence_refs=(
            futures.FuturesExecutionEvidenceReference(_uuid(102)),
            futures.FuturesExecutionEvidenceReference(_uuid(103)),
        ),
    )

    assert reconciliation.status is (
        futures.FuturesExecutionReconciliationStatus.AMBIGUOUS
    )
    assert {item.value for item in futures.FuturesExecutionReconciliationStatus} == {
        "matched",
        "diverged",
        "ambiguous",
    }


def test_provider_neutral_surfaces_expose_no_strategy_or_provider_io_methods() -> None:
    prohibited = {
        "core_decision",
        "create_decision",
        "provider_sdk",
        "redispatch",
        "retry",
        "retry_order",
        "submit_order",
        "switch_server",
    }
    for surface in (
        futures.FuturesAdapterProfile,
        futures.FuturesContractMapping,
        futures.FuturesExecutionRequest,
        futures.FuturesExecutionObservation,
        futures.FuturesExecutionReconciliation,
    ):
        assert prohibited.isdisjoint(set(dir(surface)))
