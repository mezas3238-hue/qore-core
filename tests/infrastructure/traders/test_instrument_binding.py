from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from qore.infrastructure.market_data import (
    Instrument,
    MarketDataSnapshotId,
    OhlcSnapshot,
    Timeframe,
)
from qore.infrastructure.ports import (
    AdapterId,
    ExternalSourceDescriptor,
    PortName,
    SourceId,
)
from qore.infrastructure.traders.contracts import (
    DemoTradingAbstainReason,
    DemoTradingConfigFingerprint,
    DemoTradingDecision,
    DemoTradingMethodologyFingerprint,
    DemoTradingMethodologyId,
    DemoTradingMethodologyVersion,
    DemoTradingOutput,
    DemoTradingTraderCode,
    DemoTradingTraderVersion,
    compute_trader_output_fingerprint,
)
from qore.infrastructure.traders.evaluators import DemoTradingInput
from qore.infrastructure.traders.instrument_binding import (
    InstrumentBoundDemoTradingValidationError,
    build_instrument_bound_demo_trading_input,
    evaluate_instrument_bound_demo_trader,
)
from qore.kernel.result import Success

_NOW = datetime(2026, 9, 7, 12, 0, tzinfo=UTC)
_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("62000000-0000-0000-0000-000000000001")),
    source_id=SourceId(UUID("62000000-0000-0000-0000-000000000002")),
    port_name=PortName("market-data.instrument-binding-test"),
)
_CODE = DemoTradingTraderCode("vt-31")
_VERSION = DemoTradingTraderVersion("v1")
_CONFIG = DemoTradingConfigFingerprint("a" * 64)
_METHOD_ID = DemoTradingMethodologyId("silver-bullet")
_METHOD_VERSION = DemoTradingMethodologyVersion("v1")
_METHOD_FP = DemoTradingMethodologyFingerprint("b" * 64)


def _snapshot(
    *,
    suffix: int,
    instrument: str,
    seconds: int,
    closed_at: datetime,
) -> OhlcSnapshot:
    return OhlcSnapshot(
        snapshot_id=MarketDataSnapshotId(
            UUID(f"62000000-0000-0000-0000-{suffix:012d}")
        ),
        instrument=Instrument(instrument),
        source=_SOURCE,
        timeframe=Timeframe(seconds),
        opened_at=closed_at - timedelta(seconds=seconds),
        closed_at=closed_at,
        open=1.1000,
        high=1.1020,
        low=1.0990,
        close=1.1010,
    )


class _AbstainingEvaluator:
    def evaluate(self, inputs: DemoTradingInput):  # type: ignore[no-untyped-def]
        fingerprint = compute_trader_output_fingerprint(
            trader_code=_CODE,
            version=_VERSION,
            config_fingerprint=_CONFIG,
            methodology_id=_METHOD_ID,
            methodology_version=_METHOD_VERSION,
            methodology_fingerprint=_METHOD_FP,
            evidence_refs=inputs.evidence_refs,
            timeframe="M5",
            session="instrument-binding-test",
            decision=DemoTradingDecision.ABSTAIN,
            side=None,
            setup=None,
            abstain_reason=DemoTradingAbstainReason.NO_STRUCTURE,
            evaluated_at=inputs.as_of,
        )
        return Success(
            DemoTradingOutput(
                trader_code=_CODE,
                version=_VERSION,
                config_fingerprint=_CONFIG,
                methodology_id=_METHOD_ID,
                methodology_version=_METHOD_VERSION,
                methodology_fingerprint=_METHOD_FP,
                evidence_refs=inputs.evidence_refs,
                timeframe="M5",
                session="instrument-binding-test",
                decision=DemoTradingDecision.ABSTAIN,
                side=None,
                setup=None,
                abstain_reason=DemoTradingAbstainReason.NO_STRUCTURE,
                evaluated_at=inputs.as_of,
                output_fingerprint=fingerprint,
            )
        )


def test_market_snapshots_mint_exact_instrument_bound_trader_output() -> None:
    bound_input = build_instrument_bound_demo_trading_input(
        execution_evidence=(
            _snapshot(
                suffix=10,
                instrument="EURUSD",
                seconds=300,
                closed_at=_NOW,
            ),
        ),
        as_of=_NOW,
    )

    result = evaluate_instrument_bound_demo_trader(_AbstainingEvaluator(), bound_input)

    assert isinstance(result, Success)
    assert result.value.instrument == Instrument("EURUSD")
    assert result.value.trader_output.evidence_refs == bound_input.trader_input.evidence_refs
    assert result.value.output_fingerprint.value != result.value.trader_output.output_fingerprint.value


def test_mixed_instrument_execution_and_context_evidence_fails_closed() -> None:
    with pytest.raises(
        InstrumentBoundDemoTradingValidationError,
        match="one exact instrument",
    ):
        build_instrument_bound_demo_trading_input(
            execution_evidence=(
                _snapshot(
                    suffix=11,
                    instrument="EURUSD",
                    seconds=300,
                    closed_at=_NOW,
                ),
            ),
            context_evidence=(
                _snapshot(
                    suffix=12,
                    instrument="GBPUSD",
                    seconds=14_400,
                    closed_at=_NOW,
                ),
            ),
            as_of=_NOW,
        )


def test_future_market_evidence_fails_closed_before_trader_evaluation() -> None:
    with pytest.raises(
        InstrumentBoundDemoTradingValidationError,
        match="future or still-open",
    ):
        build_instrument_bound_demo_trading_input(
            execution_evidence=(
                _snapshot(
                    suffix=13,
                    instrument="EURUSD",
                    seconds=300,
                    closed_at=_NOW + timedelta(minutes=5),
                ),
            ),
            as_of=_NOW,
        )