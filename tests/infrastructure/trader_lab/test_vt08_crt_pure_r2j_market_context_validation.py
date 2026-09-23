from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.vt08_crt_pure_2y_replay import AggregatedCandle
from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import (
    BreachGroup,
    M15Bar,
    OldLevel,
    ParentCrt,
    ReferenceKind,
    ReferencePolicy,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2e_source_multiplicity_census import (
    ConfirmationState,
    SourceObservation,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2j_market_context_validation import (
    CANDIDATE_FAMILY,
    CandidateContext,
    CandidateId,
    _accept,
    _survives,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket
from qore.infrastructure.traders.crt_pure_methodology_candidate import (
    CrtPureCandidateDirection,
)


def _candle(opened_at: datetime) -> AggregatedCandle:
    return AggregatedCandle(
        opened_at=opened_at,
        closed_at=opened_at + timedelta(hours=4),
        open_price=100,
        high_price=120,
        low_price=80,
        close_price=100,
        m5_count=48,
    )


def _bar(
    opened_at: datetime,
    open_price: int,
    high_price: int,
    low_price: int,
    close_price: int,
) -> M15Bar:
    return M15Bar(
        opened_at=opened_at,
        open_price=open_price,
        high_price=high_price,
        low_price=low_price,
        close_price=close_price,
    )


def _context(
    *,
    market: CrtPureMarket,
    direction: CrtPureCandidateDirection,
    triplet: str,
    generation: int,
    reference_count: int,
    delay_bars: int,
    source_open: int = 100,
    source_high: int = 116,
    source_low: int = 84,
    source_close: int = 108,
) -> CandidateContext:
    t0 = datetime(2023, 1, 2, 20, 0, tzinfo=UTC)
    parent = ParentCrt(
        market=market,
        direction=direction,
        triplet=triplet,
        c3_opened_at=t0,
        c3_closed_at=t0 + timedelta(hours=4),
        c1=_candle(t0 - timedelta(hours=8)),
        c2=_candle(t0 - timedelta(hours=4)),
        c3_m5=(),
    )
    source = _bar(
        t0,
        source_open,
        source_high,
        source_low,
        source_close,
    )
    kind = (
        ReferenceKind.OLD_LOW
        if direction is CrtPureCandidateDirection.BULLISH
        else ReferenceKind.OLD_HIGH
    )
    refs = tuple(
        OldLevel(
            kind=kind,
            price=(source_low + 2 + index)
            if kind is ReferenceKind.OLD_LOW
            else (source_high - 2 - index),
            pivot_opened_at=t0 - timedelta(hours=2 + index),
            confirmed_at=t0 - timedelta(hours=1),
            policy=ReferencePolicy.UNTOUCHED_SWING_STRENGTH_1,
        )
        for index in range(reference_count)
    )
    observation = SourceObservation(
        group=BreachGroup(
            source_candle=source,
            kind=kind,
            policy=ReferencePolicy.UNTOUCHED_SWING_STRENGTH_1,
            references=refs,
        ),
        source_index=0,
        confirmation_state=ConfirmationState.EXECUTABLE_CONFIRMATION,
        confirmation_opened_at=t0 + timedelta(minutes=15 * delay_bars),
    )
    confirmation = _bar(
        t0 + timedelta(minutes=15 * delay_bars),
        102,
        118,
        98,
        110,
    )
    entry = _bar(
        confirmation.closed_at,
        110,
        112,
        106,
        111,
    )
    return CandidateContext(
        parent=parent,
        observation=observation,
        confirmation=confirmation,
        entry=entry,
        generation=generation,
    )


def test_candidate_family_is_frozen_by_market() -> None:
    assert CANDIDATE_FAMILY[CrtPureMarket.AUDUSD] == (
        CandidateId.CONTROL,
        CandidateId.AUD_G1,
        CandidateId.AUD_REF2_PLUS,
        CandidateId.AUD_SOURCE_RANGE_GE_030_C1,
        CandidateId.AUD_T1_BULLISH,
    )
    assert CANDIDATE_FAMILY[CrtPureMarket.USDJPY] == (
        CandidateId.CONTROL,
        CandidateId.USD_T1,
        CandidateId.USD_D2,
        CandidateId.USD_BODY_050_TO_075,
    )
    assert CANDIDATE_FAMILY[CrtPureMarket.BTCUSD] == (
        CandidateId.CONTROL,
        CandidateId.BTC_REF2_PLUS,
        CandidateId.BTC_BODY_GE_050,
        CandidateId.BTC_BEARISH,
        CandidateId.BTC_D2,
        CandidateId.BTC_T1_BEARISH,
    )


def test_aud_candidate_gates_are_simple_single_factors() -> None:
    context = _context(
        market=CrtPureMarket.AUDUSD,
        direction=CrtPureCandidateDirection.BULLISH,
        triplet="1",
        generation=1,
        reference_count=2,
        delay_bars=3,
    )
    assert _accept(CandidateId.CONTROL, context)
    assert _accept(CandidateId.AUD_G1, context)
    assert _accept(CandidateId.AUD_REF2_PLUS, context)
    assert _accept(CandidateId.AUD_SOURCE_RANGE_GE_030_C1, context)
    assert _accept(CandidateId.AUD_T1_BULLISH, context)


def test_usd_and_btc_candidate_gates_match_frozen_forensics() -> None:
    usd = _context(
        market=CrtPureMarket.USDJPY,
        direction=CrtPureCandidateDirection.BULLISH,
        triplet="1",
        generation=2,
        reference_count=1,
        delay_bars=2,
        source_open=100,
        source_high=112,
        source_low=88,
        source_close=114,
    )
    assert _accept(CandidateId.USD_T1, usd)
    assert _accept(CandidateId.USD_D2, usd)
    # Body/range = 14/24, inside 0.50-0.75.
    assert Decimal("0.50") <= usd.body_fraction < Decimal("0.75")
    assert _accept(CandidateId.USD_BODY_050_TO_075, usd)

    btc = _context(
        market=CrtPureMarket.BTCUSD,
        direction=CrtPureCandidateDirection.BEARISH,
        triplet="1",
        generation=3,
        reference_count=2,
        delay_bars=2,
    )
    assert _accept(CandidateId.BTC_REF2_PLUS, btc)
    assert _accept(CandidateId.BTC_BODY_GE_050, btc)
    assert _accept(CandidateId.BTC_BEARISH, btc)
    assert _accept(CandidateId.BTC_D2, btc)
    assert _accept(CandidateId.BTC_T1_BEARISH, btc)


def test_research_survival_gate_is_binary_not_ranked() -> None:
    full = {
        "trades": 30,
        "profit_factor": 1.20,
        "total_r": 4.0,
        "max_drawdown_r": 6.0,
    }
    y1 = {"total_r": 2.0}
    y2 = {"total_r": 2.0}
    survived, failures = _survives(full=full, year_1=y1, year_2=y2)
    assert survived is True
    assert failures == ()

    failed, reasons = _survives(
        full={**full, "profit_factor": 1.01},
        year_1=y1,
        year_2=y2,
    )
    assert failed is False
    assert reasons == ("MIN_PF",)
