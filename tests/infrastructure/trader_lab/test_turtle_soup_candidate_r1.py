from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from itertools import count
from uuid import UUID

import pytest

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
    CANONICAL_TRADER_CODE,
    RESEARCH_IDENTITY,
    TurtleSoupR1Config,
    TurtleSoupR1Decision,
    TurtleSoupR1ManagementFamily,
    TurtleSoupR1Reason,
    TurtleSoupR1ValidationError,
    TurtleSoupR1Variant,
    evaluate_classic,
    evaluate_plus_one,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide

_IDS = count(1000)
_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID(int=1)),
    source_id=SourceId(UUID(int=2)),
    port_name=PortName("market-data.turtle-soup-test"),
)
_INSTRUMENT = Instrument("ES")
_BASE = datetime(2026, 1, 1, tzinfo=UTC)


def _field(value: str | Decimal) -> MarketOhlcField:
    price = value if type(value) is Decimal else Decimal(value)
    return MarketOhlcField(
        validity=MarketOhlcFieldValidity.VALID,
        price=MarketPrice(price),
    )


def _bar(
    *,
    code: MarketTimeframeCode,
    opened_at: datetime,
    o: str,
    h: str,
    lo: str,
    c: str,
) -> QualifiedOhlcBarObservation:
    if code is MarketTimeframeCode.D1:
        closed_at = opened_at + timedelta(days=1)
    elif code is MarketTimeframeCode.M1:
        closed_at = opened_at + timedelta(minutes=1)
    else:  # pragma: no cover - test helper guard
        raise AssertionError("unsupported test timeframe")
    return QualifiedOhlcBarObservation(
        observation_id=MarketObservationId(UUID(int=next(_IDS))),
        instrument=_INSTRUMENT,
        source=_SOURCE,
        timeframe=MarketTimeframe(code),
        price_side=MarketPriceSide.BID,
        origin=MarketBarOrigin.NATIVE,
        opened_at=opened_at,
        closed_at=closed_at,
        open=_field(o),
        high=_field(h),
        low=_field(lo),
        close=_field(c),
        evidence_ref=MarketObservationEvidenceReference(UUID(int=next(_IDS))),
    )


def _long_history(*, reference_index: int = 16, tie_index: int | None = None) -> tuple[QualifiedOhlcBarObservation, ...]:
    bars: list[QualifiedOhlcBarObservation] = []
    for index in range(20):
        low = "90.00" if index == reference_index or index == tie_index else f"{95 + index / 100:.2f}"
        bars.append(
            _bar(
                code=MarketTimeframeCode.D1,
                opened_at=_BASE + timedelta(days=index),
                o="100.00",
                h="110.00",
                lo=low,
                c="100.00",
            )
        )
    return tuple(bars)


def _short_history(*, reference_index: int = 16, tie_index: int | None = None) -> tuple[QualifiedOhlcBarObservation, ...]:
    bars: list[QualifiedOhlcBarObservation] = []
    for index in range(20):
        high = "120.00" if index == reference_index or index == tie_index else f"{110 + index / 100:.2f}"
        bars.append(
            _bar(
                code=MarketTimeframeCode.D1,
                opened_at=_BASE + timedelta(days=index),
                o="100.00",
                h=high,
                lo="90.00",
                c="100.00",
            )
        )
    return tuple(bars)


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
    return TurtleSoupR1Config(tick_size=Decimal("0.01"), classic_entry_offset_ticks=5)


def test_candidate_has_no_recycled_vt09_identity() -> None:
    assert RESEARCH_IDENTITY == "turtle-soup-candidate-r1"
    assert CANONICAL_TRADER_CODE == "CODE_UNASSIGNED"


def test_source_constants_cannot_be_mutated_into_deepseek_3_vs_4_blend() -> None:
    with pytest.raises(TurtleSoupR1ValidationError):
        TurtleSoupR1Config(
            tick_size=Decimal("0.01"),
            classic_min_reference_age=3,
        )
    with pytest.raises(TurtleSoupR1ValidationError):
        TurtleSoupR1Config(
            tick_size=Decimal("0.01"),
            plus_one_min_reference_age=4,
        )
    with pytest.raises(TurtleSoupR1ValidationError):
        TurtleSoupR1Config(
            tick_size=Decimal("0.01"),
            classic_entry_offset_ticks=4,
        )


def test_config_fingerprint_is_deterministic_and_binds_tick_choice() -> None:
    first = _config().fingerprint()
    second = _config().fingerprint()
    other = TurtleSoupR1Config(
        tick_size=Decimal("0.01"), classic_entry_offset_ticks=10
    ).fingerprint()
    assert first == second
    assert first != other
    assert len(first) == 64


def test_classic_long_requires_four_bar_old_reference_and_enters_same_session() -> None:
    history = _long_history(reference_index=16)  # age == 4
    start = history[-1].closed_at
    path = _m1(
        start,
        (
            ("89.95", "90.00", "89.80", "89.90"),
            ("89.90", "90.06", "89.85", "90.05"),
        ),
    )
    result = evaluate_classic(
        history=history,
        current_session_path=path,
        side=DemoTradingSetupSide.LONG,
        config=_config(),
    )
    assert result.decision is TurtleSoupR1Decision.SETUP
    assert result.reason is None
    assert result.setup is not None
    assert result.setup.variant is TurtleSoupR1Variant.CLASSIC
    assert result.setup.reference_age == 4
    assert result.setup.reference_price == Decimal("90.00")
    assert result.setup.entry_trigger_price == Decimal("90.05")
    assert result.setup.executable_entry_price == Decimal("90.05")
    assert result.setup.initial_stop_price == Decimal("89.79")
    assert result.setup.fill_at == path[1].opened_at
    assert (
        result.setup.management_family
        is TurtleSoupR1ManagementFamily.CLASSIC_TRAILING_STOP_UNRESOLVED
    )


def test_classic_three_bar_old_reference_abstains() -> None:
    history = _long_history(reference_index=17)  # age == 3
    path = _m1(
        history[-1].closed_at,
        (
            ("89.95", "90.00", "89.80", "89.90"),
            ("89.90", "90.06", "89.85", "90.05"),
        ),
    )
    result = evaluate_classic(
        history=history,
        current_session_path=path,
        side=DemoTradingSetupSide.LONG,
        config=_config(),
    )
    assert result.decision is TurtleSoupR1Decision.ABSTAIN
    assert result.reason is TurtleSoupR1Reason.REFERENCE_TOO_RECENT


def test_classic_same_lower_bar_sweep_and_recovery_is_censored() -> None:
    history = _long_history(reference_index=16)
    path = _m1(
        history[-1].closed_at,
        (("90.10", "90.10", "89.80", "90.05"),),
    )
    result = evaluate_classic(
        history=history,
        current_session_path=path,
        side=DemoTradingSetupSide.LONG,
        config=_config(),
    )
    assert result.decision is TurtleSoupR1Decision.AMBIGUOUS
    assert result.reason is TurtleSoupR1Reason.INTRABAR_PATH_AMBIGUOUS


def test_classic_unique_reference_is_required() -> None:
    history = _long_history(reference_index=15, tie_index=16)
    path = _m1(
        history[-1].closed_at,
        (("89.95", "90.00", "89.80", "89.90"),),
    )
    result = evaluate_classic(
        history=history,
        current_session_path=path,
        side=DemoTradingSetupSide.LONG,
        config=_config(),
    )
    assert result.decision is TurtleSoupR1Decision.AMBIGUOUS
    assert result.reason is TurtleSoupR1Reason.REFERENCE_TIE


def test_classic_order_does_not_leak_into_a_later_unprovided_session() -> None:
    history = _long_history(reference_index=16)
    path = _m1(
        history[-1].closed_at,
        (
            ("89.95", "90.00", "89.80", "89.90"),
            ("89.90", "90.04", "89.85", "90.00"),
        ),
    )
    result = evaluate_classic(
        history=history,
        current_session_path=path,
        side=DemoTradingSetupSide.LONG,
        config=_config(),
    )
    assert result.decision is TurtleSoupR1Decision.ABSTAIN
    assert result.reason is TurtleSoupR1Reason.NO_ENTRY


def test_classic_short_is_symmetric_and_uses_five_tick_offset() -> None:
    history = _short_history(reference_index=16)
    path = _m1(
        history[-1].closed_at,
        (
            ("120.05", "120.20", "120.00", "120.10"),
            ("120.10", "120.15", "119.94", "119.96"),
        ),
    )
    result = evaluate_classic(
        history=history,
        current_session_path=path,
        side=DemoTradingSetupSide.SHORT,
        config=_config(),
    )
    assert result.decision is TurtleSoupR1Decision.SETUP
    assert result.setup is not None
    assert result.setup.entry_trigger_price == Decimal("119.95")
    assert result.setup.executable_entry_price == Decimal("119.95")
    assert result.setup.initial_stop_price == Decimal("120.21")


def test_plus_one_long_uses_three_bar_age_next_bar_reference_entry_and_two_bar_stop() -> None:
    history = _long_history(reference_index=17)  # age == 3
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
        (
            ("89.80", "89.90", "89.60", "89.85"),
            ("89.85", "90.10", "89.70", "90.05"),
        ),
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
    assert result.setup.variant is TurtleSoupR1Variant.PLUS_ONE
    assert result.setup.reference_age == 3
    assert result.setup.entry_trigger_price == Decimal("90.00")
    assert result.setup.executable_entry_price == Decimal("90.00")
    assert result.setup.initial_stop_price == Decimal("89.49")
    assert (
        result.setup.management_family
        is TurtleSoupR1ManagementFamily.PLUS_ONE_PARTIAL_2_TO_6_BARS_PLUS_TRAIL_UNRESOLVED
    )


def test_plus_one_reference_two_bars_old_is_too_recent() -> None:
    history = _long_history(reference_index=18)  # age == 2
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
    assert result.reason is TurtleSoupR1Reason.REFERENCE_TOO_RECENT


def test_plus_one_requires_breakout_bar_close_at_or_beyond_reference() -> None:
    history = _long_history(reference_index=17)
    breakout = _bar(
        code=MarketTimeframeCode.D1,
        opened_at=history[-1].closed_at,
        o="91.00",
        h="92.00",
        lo="89.50",
        c="90.20",
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
    assert result.reason is TurtleSoupR1Reason.NO_CLOSE_CONFIRMATION


def test_plus_one_gap_through_stop_entry_fills_at_observed_open() -> None:
    history = _long_history(reference_index=17)
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
        (("90.20", "90.40", "90.10", "90.30"),),
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
    assert result.setup.entry_trigger_price == Decimal("90.00")
    assert result.setup.executable_entry_price == Decimal("90.20")
    assert result.setup.initial_stop_price == Decimal("89.49")


def test_plus_one_fill_bar_new_extreme_is_censored_as_unknown_path() -> None:
    history = _long_history(reference_index=17)
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
        (("89.80", "90.10", "89.40", "90.05"),),
    )
    result = evaluate_plus_one(
        history=history,
        breakout_bar=breakout,
        next_bar_path=path,
        side=DemoTradingSetupSide.LONG,
        config=_config(),
    )
    assert result.decision is TurtleSoupR1Decision.AMBIGUOUS
    assert result.reason is TurtleSoupR1Reason.INTRABAR_PATH_AMBIGUOUS


def test_plus_one_no_fill_on_next_bar_path_expires_fail_closed() -> None:
    history = _long_history(reference_index=17)
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
        (
            ("89.80", "89.90", "89.60", "89.70"),
            ("89.70", "89.95", "89.65", "89.90"),
        ),
    )
    result = evaluate_plus_one(
        history=history,
        breakout_bar=breakout,
        next_bar_path=path,
        side=DemoTradingSetupSide.LONG,
        config=_config(),
    )
    assert result.decision is TurtleSoupR1Decision.ABSTAIN
    assert result.reason is TurtleSoupR1Reason.NO_ENTRY


def test_plus_one_short_is_symmetric() -> None:
    history = _short_history(reference_index=17)
    breakout = _bar(
        code=MarketTimeframeCode.D1,
        opened_at=history[-1].closed_at,
        o="119.00",
        h="120.50",
        lo="118.00",
        c="120.20",
    )
    path = _m1(
        breakout.closed_at,
        (
            ("120.20", "120.40", "120.10", "120.20"),
            ("120.20", "120.30", "119.90", "119.95"),
        ),
    )
    result = evaluate_plus_one(
        history=history,
        breakout_bar=breakout,
        next_bar_path=path,
        side=DemoTradingSetupSide.SHORT,
        config=_config(),
    )
    assert result.decision is TurtleSoupR1Decision.SETUP
    assert result.setup is not None
    assert result.setup.entry_trigger_price == Decimal("120.00")
    assert result.setup.executable_entry_price == Decimal("120.00")
    assert result.setup.initial_stop_price == Decimal("120.51")
