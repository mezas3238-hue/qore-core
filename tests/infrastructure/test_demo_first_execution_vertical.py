from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from typing import cast
from uuid import UUID

import pytest

from qore.domain.events import CorrelationId
from qore.infrastructure.account_policy import AccountPolicyVersion
from qore.infrastructure.client_accounts import TradingAccountId
from qore.infrastructure.connectivity import ProviderEndpoint
from qore.infrastructure.ctrader_demo_execution_configuration import (
    CTraderDemoCapability,
    CTraderDemoOperationalLimits,
    CTraderDemoRuntimeConfiguration,
    CTraderSymbolMapping,
    ctrader_demo_secret_requirements,
)
from qore.infrastructure.ctrader_demo_operational_runtime import (
    CTraderDemoSubmissionResult,
)
from qore.infrastructure.ctrader_demo_risk_operational_runtime import (
    CTraderDemoRiskOperationalRuntime,
    RiskCTraderDemoAccountBinding,
)
from qore.infrastructure.demo_first_execution_intent import (
    build_first_demo_execution_intent,
    minimum_broker_valid_quantity,
)
from qore.infrastructure.execution_boundary import (
    ExecutionReceipt,
    ExecutionReceiptId,
    ExecutionRequestId,
    ExecutionSubmission,
)
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
    MarketTestAccountIdentity,
)
from qore.infrastructure.order_intent import (
    ExecutionIdempotencyKey,
    ExecutionInstrument,
    OrderIntent,
    OrderIntentId,
    OrderSide,
    OrderType,
)
from qore.infrastructure.ports import ExternalRequestMetadata
from qore.infrastructure.risk_authority import (
    RiskAuthorization,
    RiskAuthorizationId,
    RiskDecision,
    RiskEnvironment,
    RiskFingerprint,
    RiskReservation,
    RiskReservationId,
    RiskScopeSnapshot,
)
from qore.infrastructure.risk_runtime import DemoRiskRuntime, RiskAuthorizedSubmission
from qore.infrastructure.trader_lab.cohort import (
    FirstCohortDemoSelection,
    FirstCohortTraderLabEntry,
)
from qore.infrastructure.traders.contracts import (
    DemoTradingAbstainReason,
    DemoTradingConfigFingerprint,
    DemoTradingDecision,
    DemoTradingEvidenceRef,
    DemoTradingMethodologyFingerprint,
    DemoTradingMethodologyId,
    DemoTradingMethodologyVersion,
    DemoTradingOutput,
    DemoTradingSetupSide,
    DemoTradingSetupSpec,
    DemoTradingTraderCode,
    DemoTradingTraderVersion,
    compute_trader_output_fingerprint,
)
from qore.kernel.result import Failure, Result, Success

_NOW = datetime(2026, 9, 7, 9, 30, tzinfo=UTC)
_ACCOUNT = MarketTestAccountIdentity(
    provider_key="ctrader-demo",
    account_ref="424242",
    environment=MarketRuntimeEnvironment.DEMO,
)
_RISK_ACCOUNT = TradingAccountId(UUID("61000000-0000-0000-0000-000000000001"))
_METADATA = ExternalRequestMetadata(
    correlation_id=CorrelationId(UUID("61000000-0000-0000-0000-000000000002"))
)
_CODE = DemoTradingTraderCode("vt-08")
_VERSION = DemoTradingTraderVersion("v1")
_CONFIG = DemoTradingConfigFingerprint("a" * 64)
_METHOD_ID = DemoTradingMethodologyId("crt-4h-amd")
_METHOD_VERSION = DemoTradingMethodologyVersion("v1")
_METHOD_FP = DemoTradingMethodologyFingerprint("b" * 64)


def _configuration(
    *,
    instrument: str = "EURUSD",
    digits: int = 5,
) -> CTraderDemoRuntimeConfiguration:
    return CTraderDemoRuntimeConfiguration(
        provider_key="ctrader-demo",
        environment=MarketRuntimeEnvironment.DEMO,
        endpoint=ProviderEndpoint(host="demo.ctraderapi.com", port=5035),
        account=_ACCOUNT,
        symbol_mappings=(
            CTraderSymbolMapping(
                instrument=ExecutionInstrument(instrument),
                symbol_id=1234,
                symbol_name=instrument,
                digits=digits,
                volume_step=Decimal("0.01"),
                min_volume_units=1000,
                max_volume_units=1_000_000,
                step_volume_units=1000,
            ),
        ),
        capabilities=(
            CTraderDemoCapability.ACCOUNT,
            CTraderDemoCapability.ORDERS,
        ),
        rest_timeout=__import__(
            "qore.infrastructure.transport", fromlist=["ExternalTransportTimeout"]
        ).ExternalTransportTimeout(milliseconds=3000),
        limits=CTraderDemoOperationalLimits(order_requests_per_second=1),
        secret_requirements=ctrader_demo_secret_requirements(),
    )


def _noop(value: object) -> None:
    del value


def _selection(monkeypatch: pytest.MonkeyPatch) -> FirstCohortDemoSelection:
    monkeypatch.setattr(FirstCohortDemoSelection, "__post_init__", _noop)
    monkeypatch.setattr(FirstCohortTraderLabEntry, "__post_init__", _noop)
    selected = object.__new__(FirstCohortTraderLabEntry)
    object.__setattr__(selected, "trader_code", _CODE)
    object.__setattr__(selected, "trader_version", _VERSION)
    object.__setattr__(selected, "config_fingerprint", _CONFIG)
    object.__setattr__(selected, "methodology_id", _METHOD_ID)
    object.__setattr__(selected, "methodology_version", _METHOD_VERSION)
    object.__setattr__(selected, "methodology_fingerprint", _METHOD_FP)
    selection = object.__new__(FirstCohortDemoSelection)
    object.__setattr__(selection, "selected", selected)
    return selection


def _output(
    *,
    decision: DemoTradingDecision = DemoTradingDecision.SETUP,
    trader_code: DemoTradingTraderCode = _CODE,
    entry: Decimal = Decimal("1.10000"),
) -> DemoTradingOutput:
    setup = None
    side = None
    abstain_reason = DemoTradingAbstainReason.NO_STRUCTURE
    if decision is DemoTradingDecision.SETUP:
        side = DemoTradingSetupSide.LONG
        setup = DemoTradingSetupSpec(
            side=side,
            entry_price=entry,
            invalidation_price=Decimal("1.09500"),
            take_profit_price=Decimal("1.11000"),
            entry_reason="governed first execution setup",
        )
        abstain_reason = None
    evidence_refs = (DemoTradingEvidenceRef("market:test:first-execution"),)
    fingerprint = compute_trader_output_fingerprint(
        trader_code=trader_code,
        version=_VERSION,
        config_fingerprint=_CONFIG,
        methodology_id=_METHOD_ID,
        methodology_version=_METHOD_VERSION,
        methodology_fingerprint=_METHOD_FP,
        evidence_refs=evidence_refs,
        timeframe="M5",
        session="h4-structural",
        decision=decision,
        side=side,
        setup=setup,
        abstain_reason=abstain_reason,
        evaluated_at=_NOW,
    )
    return DemoTradingOutput(
        trader_code=trader_code,
        version=_VERSION,
        config_fingerprint=_CONFIG,
        methodology_id=_METHOD_ID,
        methodology_version=_METHOD_VERSION,
        methodology_fingerprint=_METHOD_FP,
        evidence_refs=evidence_refs,
        timeframe="M5",
        session="h4-structural",
        decision=decision,
        side=side,
        setup=setup,
        abstain_reason=abstain_reason,
        evaluated_at=_NOW,
        output_fingerprint=fingerprint,
    )


def test_minimum_quantity_comes_only_from_provider_mapping() -> None:
    mapping = _configuration().symbol_mappings[0]

    quantity = minimum_broker_valid_quantity(mapping)

    assert quantity.value == Decimal("10.00")


def test_selected_setup_builds_minimum_size_protected_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    built = build_first_demo_execution_intent(
        _selection(monkeypatch),
        _output(),
        configuration=_configuration(),
        instrument=ExecutionInstrument("EURUSD"),
        intent_id=OrderIntentId(UUID("61000000-0000-0000-0000-000000000010")),
        idempotency_key=ExecutionIdempotencyKey(
            UUID("61000000-0000-0000-0000-000000000011")
        ),
        created_at=_NOW,
        metadata=_METADATA,
    )

    assert isinstance(built, Success)
    intent = built.value
    assert intent.order_type is OrderType.LIMIT
    assert intent.side is OrderSide.BUY
    assert intent.quantity.value == Decimal("10.00")
    assert intent.limit_price is not None
    assert intent.limit_price.value == Decimal("1.10000")
    assert intent.stop_loss is not None
    assert intent.stop_loss.value == Decimal("1.09500")
    assert intent.take_profit is not None
    assert intent.take_profit.value == Decimal("1.11000")


def test_abstain_and_non_selected_output_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selection = _selection(monkeypatch)
    common = dict(
        configuration=_configuration(),
        instrument=ExecutionInstrument("EURUSD"),
        intent_id=OrderIntentId(UUID("61000000-0000-0000-0000-000000000012")),
        idempotency_key=ExecutionIdempotencyKey(
            UUID("61000000-0000-0000-0000-000000000013")
        ),
        created_at=_NOW,
        metadata=_METADATA,
    )

    abstain = build_first_demo_execution_intent(
        selection,
        _output(decision=DemoTradingDecision.ABSTAIN),
        **common,
    )
    other = build_first_demo_execution_intent(
        selection,
        _output(trader_code=DemoTradingTraderCode("vt-01")),
        **common,
    )

    assert isinstance(abstain, Failure)
    assert isinstance(other, Failure)


def test_unmapped_symbol_and_non_exact_price_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selection = _selection(monkeypatch)
    common = dict(
        selection=selection,
        intent_id=OrderIntentId(UUID("61000000-0000-0000-0000-000000000014")),
        idempotency_key=ExecutionIdempotencyKey(
            UUID("61000000-0000-0000-0000-000000000015")
        ),
        created_at=_NOW,
        metadata=_METADATA,
    )

    unmapped = build_first_demo_execution_intent(
        output=_output(),
        configuration=_configuration(instrument="GBPUSD"),
        instrument=ExecutionInstrument("EURUSD"),
        **common,
    )
    inexact = build_first_demo_execution_intent(
        output=_output(entry=Decimal("1.100001")),
        configuration=_configuration(),
        instrument=ExecutionInstrument("EURUSD"),
        **common,
    )

    assert isinstance(unmapped, Failure)
    assert isinstance(inexact, Failure)


class _FakeCTrader:
    def __init__(self, *, fail_submit: bool = False) -> None:
        self._configuration = _configuration()
        self.fail_submit = fail_submit
        self.submissions: list[ExecutionSubmission] = []

    @property
    def configuration(self) -> CTraderDemoRuntimeConfiguration:
        return self._configuration

    def connect(
        self,
        *,
        checked_at: datetime,
        metadata: ExternalRequestMetadata,
    ) -> Result[object, object]:
        del checked_at, metadata
        return Success(SimpleNamespace())

    def submit_authorized(
        self,
        submission: ExecutionSubmission,
    ) -> Result[CTraderDemoSubmissionResult, object]:
        self.submissions.append(submission)
        if self.fail_submit:
            return Failure(RuntimeError("broker outcome unavailable"))
        receipt = cast(
            ExecutionReceipt,
            SimpleNamespace(receipt_id=submission.receipt_id),
        )
        return Success(
            CTraderDemoSubmissionResult(
                receipt=receipt,
                provider_order_ref="demo-order-1",
                fills=(),
            )
        )

    def poll_and_reconcile(
        self,
        submission: ExecutionSubmission,
        *,
        provider_order_ref: str,
        metadata: ExternalRequestMetadata,
    ) -> Result[object, object]:
        del submission, provider_order_ref, metadata
        return Failure(RuntimeError("not used in this focused test"))


def _risk_decision(
    *,
    account: TradingAccountId = _RISK_ACCOUNT,
    environment: RiskEnvironment = RiskEnvironment.DEMO,
) -> RiskDecision:
    authorization = object.__new__(RiskAuthorization)
    object.__setattr__(
        authorization,
        "authorization_id",
        RiskAuthorizationId(UUID("61000000-0000-0000-0000-000000000020")),
    )
    object.__setattr__(authorization, "account_id", account)
    object.__setattr__(authorization, "environment", environment)
    decision = object.__new__(RiskDecision)
    object.__setattr__(decision, "authorization", authorization)
    return decision


def _prepared_submission() -> RiskAuthorizedSubmission:
    receipt_id = ExecutionReceiptId(UUID("61000000-0000-0000-0000-000000000021"))
    submission = object.__new__(ExecutionSubmission)
    object.__setattr__(submission, "receipt_id", receipt_id)
    authorization = _risk_decision().authorization
    assert authorization is not None
    fingerprint = RiskFingerprint("c" * 64)
    reservation_id = RiskReservationId(
        UUID("61000000-0000-0000-0000-000000000022")
    )
    reservation = cast(
        RiskReservation,
        SimpleNamespace(reservation_id=reservation_id),
    )
    prepared = object.__new__(RiskAuthorizedSubmission)
    object.__setattr__(prepared, "submission", submission)
    object.__setattr__(prepared, "risk_authorization", authorization)
    object.__setattr__(prepared, "risk_authorization_fingerprint", fingerprint)
    object.__setattr__(prepared, "reservation", reservation)
    return prepared


def _patch_prepare(
    monkeypatch: pytest.MonkeyPatch,
    prepared: RiskAuthorizedSubmission,
    calls: list[OrderIntent],
) -> None:
    def _prepare(
        self: DemoRiskRuntime,
        decision: RiskDecision,
        intent: OrderIntent,
        **kwargs: object,
    ) -> Result[RiskAuthorizedSubmission, object]:
        del self, decision, kwargs
        calls.append(intent)
        return Success(prepared)

    monkeypatch.setattr(DemoRiskRuntime, "prepare_execution_submission", _prepare)


def _composition(
    ctrader: _FakeCTrader,
) -> CTraderDemoRiskOperationalRuntime:
    risk = object.__new__(DemoRiskRuntime)
    binding = RiskCTraderDemoAccountBinding(
        risk_account_id=_RISK_ACCOUNT,
        ctrader_account=_ACCOUNT,
    )
    return CTraderDemoRiskOperationalRuntime(
        risk=risk,
        ctrader=cast(object, ctrader),
        account_binding=binding,
    )


def _submit_kwargs() -> dict[str, object]:
    return {
        "scope": cast(RiskScopeSnapshot, object()),
        "account_policy_version": cast(AccountPolicyVersion, object()),
        "expected_authorization_fingerprint": RiskFingerprint("c" * 64),
        "request_id": ExecutionRequestId(
            UUID("61000000-0000-0000-0000-000000000023")
        ),
        "receipt_id": ExecutionReceiptId(
            UUID("61000000-0000-0000-0000-000000000021")
        ),
        "authorized_at": _NOW,
        "submitted_at": _NOW,
    }


def test_risk_account_mismatch_never_reaches_prepare_or_broker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[OrderIntent] = []
    ctrader = _FakeCTrader()
    _patch_prepare(monkeypatch, _prepared_submission(), calls)
    runtime = _composition(ctrader)
    other_account = TradingAccountId(
        UUID("61000000-0000-0000-0000-000000000099")
    )

    result = runtime.submit_risk_authorized(
        _risk_decision(account=other_account),
        cast(OrderIntent, object()),
        **_submit_kwargs(),
    )

    assert isinstance(result, Failure)
    assert calls == []
    assert ctrader.submissions == []


def test_exact_risk_prepared_submission_is_the_only_broker_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[OrderIntent] = []
    prepared = _prepared_submission()
    ctrader = _FakeCTrader()
    _patch_prepare(monkeypatch, prepared, calls)
    runtime = _composition(ctrader)
    intent = cast(OrderIntent, object())

    result = runtime.submit_risk_authorized(
        _risk_decision(),
        intent,
        **_submit_kwargs(),
    )

    assert isinstance(result, Success)
    assert calls == [intent]
    assert ctrader.submissions == [prepared.submission]
    assert result.value.broker.provider_order_ref == "demo-order-1"


def test_non_demo_risk_and_broker_failure_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[OrderIntent] = []
    prepared = _prepared_submission()
    ctrader = _FakeCTrader(fail_submit=True)
    _patch_prepare(monkeypatch, prepared, calls)
    runtime = _composition(ctrader)
    intent = cast(OrderIntent, object())

    non_demo = runtime.submit_risk_authorized(
        _risk_decision(environment=RiskEnvironment.PRODUCTION),
        intent,
        **_submit_kwargs(),
    )
    broker_failure = runtime.submit_risk_authorized(
        _risk_decision(),
        intent,
        **_submit_kwargs(),
    )

    assert isinstance(non_demo, Failure)
    assert isinstance(broker_failure, Failure)
    assert calls == [intent]
    assert ctrader.submissions == [prepared.submission]
