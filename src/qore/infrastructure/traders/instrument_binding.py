"""Canonical market-evidence/instrument binding for DEMO Trader evaluation.

The legacy deterministic Trader evaluators intentionally operate only on closed
OHLC primitives.  This boundary composes them with canonical market evidence so
an executable Trader output cannot acquire or replace its instrument after the
methodology has run.

The admitted chain is therefore:

``OhlcSnapshot(instrument) -> InstrumentBoundDemoTradingInput -> evaluator ->
InstrumentBoundDemoTradingOutput(instrument + instrument-bound fingerprint)``.

Only the instrument-bound output is admissible to the first-execution intent
bridge.  No order, Risk, provider, account, quantity, or Production authority is
created here.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256
from typing import Protocol

from qore.infrastructure.market_data import Instrument, OhlcSnapshot
from qore.infrastructure.market_observation import MarketTimeframeCode
from qore.infrastructure.traders.contracts import (
    DemoTradingConfigFingerprint,
    DemoTradingError,
    DemoTradingEvidenceRef,
    DemoTradingOutput,
    DemoTradingValidationError,
)
from qore.infrastructure.traders.evaluators import DemoTradingInput
from qore.infrastructure.traders.primitives import ClosedCandle
from qore.kernel.result import Failure, Result, Success

_TIMEFRAME_BY_SECONDS: dict[int, MarketTimeframeCode] = {
    60: MarketTimeframeCode.M1,
    300: MarketTimeframeCode.M5,
    900: MarketTimeframeCode.M15,
    14_400: MarketTimeframeCode.H4,
}


class InstrumentBoundDemoTradingError(DemoTradingError):
    """Base error for the canonical Trader instrument-binding boundary."""

    __slots__ = ()


class InstrumentBoundDemoTradingValidationError(InstrumentBoundDemoTradingError):
    """Market evidence cannot be bound to one exact Trader instrument."""

    __slots__ = ()


class DemoTradingEvaluatorBoundary(Protocol):
    """Structural boundary implemented by the deterministic cohort evaluators."""

    def evaluate(
        self,
        inputs: DemoTradingInput,
    ) -> Result[DemoTradingOutput, DemoTradingError]: ...


def _utc_iso(value: datetime) -> str:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise InstrumentBoundDemoTradingValidationError(
            "instrument-bound evaluation time must be timezone-aware"
        )
    return value.astimezone(UTC).isoformat(timespec="microseconds")


def _snapshot_payload(snapshot: OhlcSnapshot) -> dict[str, object]:
    snapshot.__post_init__()
    return {
        "snapshot_id": str(snapshot.snapshot_id.value),
        "instrument": snapshot.instrument.symbol,
        "source": repr(snapshot.source.logical_values()),
        "timeframe_seconds": snapshot.timeframe.seconds,
        "opened_at": _utc_iso(snapshot.opened_at),
        "closed_at": _utc_iso(snapshot.closed_at),
        # Float is the canonical market-data representation today.  hex() binds
        # its exact binary value without introducing display-rounding ambiguity.
        "open": snapshot.open.hex(),
        "high": snapshot.high.hex(),
        "low": snapshot.low.hex(),
        "close": snapshot.close.hex(),
    }


def _snapshot_digest(snapshot: OhlcSnapshot) -> str:
    payload = json.dumps(
        _snapshot_payload(snapshot),
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return sha256(payload).hexdigest()


def _evidence_ref(snapshot: OhlcSnapshot) -> DemoTradingEvidenceRef:
    return DemoTradingEvidenceRef(f"market:ohlc:{_snapshot_digest(snapshot)}")


def _market_evidence_digest(
    *,
    instrument: Instrument,
    snapshots: tuple[OhlcSnapshot, ...],
) -> str:
    material = {
        "schema": "qore.demo.trader.market-evidence.v1",
        "instrument": instrument.symbol,
        "snapshots": sorted(_snapshot_digest(item) for item in snapshots),
    }
    return sha256(
        json.dumps(
            material,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _closed_candle(snapshot: OhlcSnapshot) -> ClosedCandle:
    code = _TIMEFRAME_BY_SECONDS.get(snapshot.timeframe.seconds)
    if code is None:
        raise InstrumentBoundDemoTradingValidationError(
            "market evidence timeframe is not supported by the first DEMO Trader cohort"
        )
    try:
        return ClosedCandle(
            timeframe=code,
            opened_at=snapshot.opened_at,
            closed_at=snapshot.closed_at,
            open=Decimal(str(snapshot.open)),
            high=Decimal(str(snapshot.high)),
            low=Decimal(str(snapshot.low)),
            close=Decimal(str(snapshot.close)),
        )
    except DemoTradingError:
        raise
    except Exception as error:
        raise InstrumentBoundDemoTradingValidationError(
            "canonical market evidence cannot be converted to closed Trader evidence"
        ) from error


@dataclass(frozen=True, slots=True)
class InstrumentBoundDemoTradingInput:
    """Sealed Trader input derived from exact canonical market snapshots."""

    instrument: Instrument
    trader_input: DemoTradingInput
    market_evidence_digest: str
    _bound: bool = field(default=False, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._bound is not True:
            raise InstrumentBoundDemoTradingValidationError(
                "instrument-bound Trader input must be produced from canonical market evidence"
            )
        if type(self.instrument) is not Instrument:
            raise InstrumentBoundDemoTradingValidationError(
                "instrument must be canonical market-data Instrument"
            )
        self.instrument.__post_init__()
        if type(self.trader_input) is not DemoTradingInput:
            raise InstrumentBoundDemoTradingValidationError(
                "trader_input must be exact DemoTradingInput"
            )
        self.trader_input.__post_init__()
        if (
            type(self.market_evidence_digest) is not str
            or len(self.market_evidence_digest) != 64
            or any(ch not in "0123456789abcdef" for ch in self.market_evidence_digest)
        ):
            raise InstrumentBoundDemoTradingValidationError(
                "market_evidence_digest must be lowercase SHA-256"
            )


def build_instrument_bound_demo_trading_input(
    *,
    execution_evidence: tuple[OhlcSnapshot, ...],
    context_evidence: tuple[OhlcSnapshot, ...] = (),
    as_of: datetime,
) -> InstrumentBoundDemoTradingInput:
    """Derive exact Trader input and its instrument from retained market evidence."""

    _utc_iso(as_of)
    if type(execution_evidence) is not tuple or not execution_evidence:
        raise InstrumentBoundDemoTradingValidationError(
            "execution_evidence must be a non-empty OhlcSnapshot tuple"
        )
    if type(context_evidence) is not tuple:
        raise InstrumentBoundDemoTradingValidationError(
            "context_evidence must be an OhlcSnapshot tuple"
        )
    snapshots = (*execution_evidence, *context_evidence)
    if any(type(item) is not OhlcSnapshot for item in snapshots):
        raise InstrumentBoundDemoTradingValidationError(
            "all market evidence must be exact OhlcSnapshot values"
        )
    for snapshot in snapshots:
        snapshot.__post_init__()
        if snapshot.closed_at > as_of:
            raise InstrumentBoundDemoTradingValidationError(
                "future or still-open market evidence cannot enter Trader evaluation"
            )
    instrument = execution_evidence[0].instrument
    if any(item.instrument != instrument for item in snapshots):
        raise InstrumentBoundDemoTradingValidationError(
            "execution and context market evidence must bind one exact instrument"
        )
    refs = tuple(sorted((_evidence_ref(item) for item in snapshots), key=lambda item: item.value))
    if len(set(refs)) != len(refs):
        raise InstrumentBoundDemoTradingValidationError(
            "duplicate canonical market evidence is not admissible"
        )
    trader_input = DemoTradingInput(
        as_of=as_of,
        evidence_refs=refs,
        execution_candles=tuple(_closed_candle(item) for item in execution_evidence),
        context_candles=tuple(_closed_candle(item) for item in context_evidence),
    )
    digest = _market_evidence_digest(instrument=instrument, snapshots=snapshots)
    value = object.__new__(InstrumentBoundDemoTradingInput)
    object.__setattr__(value, "instrument", instrument)
    object.__setattr__(value, "trader_input", trader_input)
    object.__setattr__(value, "market_evidence_digest", digest)
    object.__setattr__(value, "_bound", True)
    value.__post_init__()
    return value


def compute_instrument_bound_output_fingerprint(
    *,
    instrument: Instrument,
    market_evidence_digest: str,
    trader_output: DemoTradingOutput,
) -> DemoTradingConfigFingerprint:
    """Bind Trader logical output identity to the exact evaluated instrument/evidence."""

    if type(instrument) is not Instrument:
        raise InstrumentBoundDemoTradingValidationError(
            "instrument-bound output requires canonical Instrument"
        )
    instrument.__post_init__()
    if type(trader_output) is not DemoTradingOutput:
        raise InstrumentBoundDemoTradingValidationError(
            "instrument-bound output requires exact DemoTradingOutput"
        )
    trader_output.__post_init__()
    if (
        type(market_evidence_digest) is not str
        or len(market_evidence_digest) != 64
        or any(ch not in "0123456789abcdef" for ch in market_evidence_digest)
    ):
        raise InstrumentBoundDemoTradingValidationError(
            "market_evidence_digest must be lowercase SHA-256"
        )
    canonical = {
        "schema": "qore.demo.trader.instrument-bound-output.v1",
        "instrument": instrument.symbol,
        "market_evidence_digest": market_evidence_digest,
        "trader_output_fingerprint": trader_output.output_fingerprint.value,
    }
    return DemoTradingConfigFingerprint(
        sha256(
            json.dumps(
                canonical,
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        ).hexdigest()
    )


@dataclass(frozen=True, slots=True)
class InstrumentBoundDemoTradingOutput:
    """Sealed executable Trader output with immutable instrument identity."""

    instrument: Instrument
    trader_output: DemoTradingOutput
    market_evidence_digest: str
    output_fingerprint: DemoTradingConfigFingerprint
    _evaluated: bool = field(default=False, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._evaluated is not True:
            raise InstrumentBoundDemoTradingValidationError(
                "instrument-bound output must be produced by canonical Trader evaluation"
            )
        expected = compute_instrument_bound_output_fingerprint(
            instrument=self.instrument,
            market_evidence_digest=self.market_evidence_digest,
            trader_output=self.trader_output,
        )
        if self.output_fingerprint != expected:
            raise InstrumentBoundDemoTradingValidationError(
                "instrument-bound output fingerprint must match instrument and evidence"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.instrument.symbol,
            self.market_evidence_digest,
            self.trader_output.logical_values(),
            self.output_fingerprint.logical_values(),
        )


def evaluate_instrument_bound_demo_trader(
    evaluator: DemoTradingEvaluatorBoundary,
    inputs: InstrumentBoundDemoTradingInput,
) -> Result[InstrumentBoundDemoTradingOutput, DemoTradingError]:
    """Run one deterministic Trader and seal its output to market instrument/evidence."""

    if type(inputs) is not InstrumentBoundDemoTradingInput:
        return Failure(
            InstrumentBoundDemoTradingValidationError(
                "Trader evaluation requires InstrumentBoundDemoTradingInput"
            )
        )
    try:
        inputs.__post_init__()
    except DemoTradingError as error:
        return Failure(error)
    result = evaluator.evaluate(inputs.trader_input)
    if isinstance(result, Failure):
        return result
    output = result.value
    try:
        output.__post_init__()
        if output.evidence_refs != inputs.trader_input.evidence_refs:
            raise InstrumentBoundDemoTradingValidationError(
                "Trader output must retain the exact market evidence references"
            )
        if output.evaluated_at != inputs.trader_input.as_of:
            raise InstrumentBoundDemoTradingValidationError(
                "Trader output evaluated_at must equal the bound input as_of"
            )
        fingerprint = compute_instrument_bound_output_fingerprint(
            instrument=inputs.instrument,
            market_evidence_digest=inputs.market_evidence_digest,
            trader_output=output,
        )
        bound = object.__new__(InstrumentBoundDemoTradingOutput)
        object.__setattr__(bound, "instrument", inputs.instrument)
        object.__setattr__(bound, "trader_output", output)
        object.__setattr__(bound, "market_evidence_digest", inputs.market_evidence_digest)
        object.__setattr__(bound, "output_fingerprint", fingerprint)
        object.__setattr__(bound, "_evaluated", True)
        bound.__post_init__()
        return Success(bound)
    except DemoTradingError as error:
        return Failure(error)