from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from itertools import count
from uuid import UUID

from qore.infrastructure.market_data import Instrument
from qore.infrastructure.market_observation import (
    MarketBarOrigin,
    MarketObservationEvidenceReference,
    MarketObservationId,
    MarketOhlcField,
    MarketOhlcFieldValidity,
    MarketPrice,
    MarketPriceSide,
    MarketTimeframe,
    MarketTimeframeCode,
    QualifiedOhlcBarObservation,
)
from qore.infrastructure.ports import AdapterId, ExternalSourceDescriptor, PortName, SourceId
from qore.infrastructure.trader_lab.turtle_soup_candidate_r1 import (
    TurtleSoupR1Config,
    TurtleSoupR1Decision,
    TurtleSoupR1Reason,
    evaluate_classic,
    evaluate_plus_one,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide

_IDS = count(9000)
_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID(int=91)),
    source_id=SourceId(UUID(int=92)),
    port_name=PortName("market-data.turtle-soup-path-test"),
)
_INSTRUMENT = Instrument("ES")
_BASE = datetime(2026, 1, 1, tzinfo=UTC)


def _field(value: str) -> MarketOhlcField:
    return MarketOhlcField(
        validity=MarketOhlcFieldValidity.VALID,
        price=MarketPrice(Decimal(value)),
    )


def _duration(code: MarketTimeframeCode) -> timedelta:
    if code is MarketTimeframeCode.D1:
        return timedelta(days=1)
    if code is MarketTimeframeCode.M10:
        return timedelta(minutes=10)
    if code is MarketTimeframeCode.M1:
        return timedelta(minutes=1)
    raise AssertionError("unsupported test timeframe")


def _bar(
    *,
    code: MarketTimeframeCode,
    opened_at: datetime,
    o: str,
    h: str,
    lo: str,
    c: str,
) -> QualifiedOhlcBarObservation:
    return QualifiedOhlcBarObservation(
        observation_id=MarketObservationId(UUID(int=next(_IDS))),
        instrument=_INSTRUMENT,
        source=_SOURCE,
        timeframe=MarketTimeframe(code),
        price_side=MarketPriceSide.BID,
        origin=MarketBarOrigin.NATIVE,
        opened_at=opened_at,
        closed_at=opened_at + _duration(code),
        open=_field(o),
        high=_field(h),
        low=_field(lo),
        close=_field(c),
        evidence_ref=MarketObservationEvidenceReference(UUID(int=next(_IDS))),
    )


def _history(
    *,
    code: MarketTimeframeCode,
    reference_index: int,
    side: DemoTradingSetupSide,
) -> tuple[QualifiedOhlcBarObservation, ...]:
    interval = _duration(code)
    rows: list[QualifiedOhlcBarObservation] = []
    for index in range(20):
        if side is DemoTradingSetupSide.LONG:
            low = "90.00" if index == reference_index else f"{95 + index / 100:.2f}"
            high = "110.00"
        else:
            low = "90.00"
            high = "120.00" if index == reference_index else f"{110 + index / 100:.2f}"
        rows.append(
            _bar(
                code=code,
                opened_at=_BASE + interval * index,
                o="100.00",
                h=high,
                lo=low,
                c="100.00",
            )
        )
    return tuple(rows)


def _m1(
    start: datetime,
    rows: tuple[tuple[str, str, str, str], ...],
) -> tuple[QualifiedOhlcBarObservation, ...]:
    return tuple(
        _bar(
            code=MarketTimeframeCode.M1,
            opened_at=start + timedelta(minutes=index),
            o=o,
            h=h,
            lo=lo,
            c=c,
        )
        for index, (o, h, lo, c) in enumerate(rows)
    )


def _config() -> TurtleSoupR1Config:
    return TurtleSoupR1Config(
        tick_size=Decimal("0.01"),
        classic_entry_offset_ticks=5,
    )


def test_intraday_classic_fails_closed_until_age_mapping_is_adjudicated() -> None:
    history = _history(
        code=MarketTimeframeCode.M10,
        reference_index=16,
        side=DemoTradingSetupSide.LONG,
    )
    path = _m1(
        history[-1].closed_at,
        (
            ("89.95", "90.00", "89.80", "89.90"),
            ("89.90", "90.02", "89.85", "90.01"),
        ),
    )
    result = evaluate_classic(
        history=history,
        current_session_path=path,
        side=DemoTradingSetupSide.LONG,
        config=_config(),
    )
    assert result.decision is TurtleSoupR1Decision.ABSTAIN
    assert result.reason is TurtleSoupR1Reason.INTRADAY_AGE_UNRESOLVED


def test_intraday_plus_one_fails_closed_until_age_mapping_is_adjudicated() -> None:
    history = _history(
        code=MarketTimeframeCode.M10,
        reference_index=17,
        side=DemoTradingSetupSide.LONG,
    )
    breakout = _bar(
        code=MarketTimeframeCode.M10,
        opened_at=history[-1].closed_at,
        o="91.00",
        h="92.00",
        lo="89.50",
        c="89.80",
    )
    path = _m1(
        breakout.closed_at,
        (("89.80", "90.10", "89.60", "90.05"),),
    )
    result = evaluate_plus_one(
        history=history,
        breakout_bar=breakout,
        next_bar_path=path,
        side=DemoTradingSetupSide.LONG,
        config=_config(),
    )
    assert result.decision is TurtleSoupR1Decision.ABSTAIN
    assert result.reason is TurtleSoupR1Reason.INTRADAY_AGE_UNRESOLVED


def test_classic_gap_recovery_fills_at_open_before_same_bar_new_low() -> None:
    history = _history(
        code=MarketTimeframeCode.D1,
        reference_index=16,
        side=DemoTradingSetupSide.LONG,
    )
    path = _m1(
        history[-1].closed_at,
        (
            ("89.95", "90.00", "89.80", "89.90"),
            ("90.20", "90.30", "89.70", "90.10"),
        ),
    )
    result = evaluate_classic(
        history=history,
        current_session_path=path,
        side=DemoTradingSetupSide.LONG,
        config=_config(),
    )
    assert result.decision is TurtleSoupR1Decision.SETUP
    assert result.setup is not None
    assert result.setup.executable_entry_price == Decimal("90.20")
    assert result.setup.initial_stop_price == Decimal("89.79")


def test_classic_non_gap_entry_with_new_low_same_bar_is_ambiguous() -> None:
    history = _history(
        code=MarketTimeframeCode.D1,
        reference_index=16,
        side=DemoTradingSetupSide.LONG,
    )
    path = _m1(
        history[-1].closed_at,
        (
            ("89.95", "90.00", "89.80", "89.90"),
            ("89.90", "90.10", "89.70", "90.05"),
        ),
    )
    result = evaluate_classic(
        history=history,
        current_session_path=path,
        side=DemoTradingSetupSide.LONG,
        config=_config(),
    )
    assert result.decision is TurtleSoupR1Decision.AMBIGUOUS
    assert result.reason is TurtleSoupR1Reason.INTRABAR_PATH_AMBIGUOUS


def test_plus_one_gap_fill_precedes_same_bar_new_low() -> None:
    history = _history(
        code=MarketTimeframeCode.D1,
        reference_index=17,
        side=DemoTradingSetupSide.LONG,
    )
    breakout = _bar(
        code=MarketTimeframeCode.D1,
        opened_at=history[-1].closed_at,
        o="91.00",
        h="92.00",
        lo="89.50",
        c="89.80",
    )
    path = _m1(
        breakout.closed_at,
        (("90.20", "90.40", "89.40", "90.30"),),
    )
    result = evaluate_plus_one(
        history=history,
        breakout_bar=breakout,
        next_bar_path=path,
        side=DemoTradingSetupSide.LONG,
        config=_config(),
    )
    assert result.decision is TurtleSoupR1Decision.SETUP
    assert result.setup is not None
    assert result.setup.executable_entry_price == Decimal("90.20")
    assert result.setup.initial_stop_price == Decimal("89.49")


def test_execution_path_cannot_begin_before_source_bar_closes() -> None:
    history = _history(
        code=MarketTimeframeCode.D1,
        reference_index=16,
        side=DemoTradingSetupSide.LONG,
    )
    path = _m1(
        history[-1].closed_at - timedelta(minutes=1),
        (("89.95", "90.10", "89.80", "90.05"),),
    )
    result = evaluate_classic(
        history=history,
        current_session_path=path,
        side=DemoTradingSetupSide.LONG,
        config=_config(),
    )
    assert result.decision is TurtleSoupR1Decision.ABSTAIN
    assert result.reason is TurtleSoupR1Reason.INVALID_EVIDENCE
