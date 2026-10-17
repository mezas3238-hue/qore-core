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
from qore.infrastructure.trader_lab.vt08_crt_pure_r2i_context_forensics import (
    BASE_POLICY,
    CompetitionPolicy,
    _bucket_delay,
    _bucket_fraction,
    _bucket_generation,
    _bucket_range_ratio,
    _bucket_references,
    _bucket_rr,
    _delay_bars,
    _penetration_fraction,
    _source_body_fraction,
    _source_range_to_c1,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket
from qore.infrastructure.traders.crt_pure_methodology_candidate import (
    CrtPureCandidateDirection,
)


def _candle(opened_at: datetime, *, high: int = 120, low: int = 80) -> AggregatedCandle:
    return AggregatedCandle(
        opened_at=opened_at,
        closed_at=opened_at + timedelta(hours=4),
        open_price=100,
        high_price=high,
        low_price=low,
        close_price=100,
        m5_count=48,
    )


def _parent(direction: CrtPureCandidateDirection) -> ParentCrt:
    opened_at = datetime(2026, 1, 1, 20, 0, tzinfo=UTC)
    return ParentCrt(
        market=CrtPureMarket.AUDUSD,
        direction=direction,
        triplet="1",
        c3_opened_at=opened_at,
        c3_closed_at=opened_at + timedelta(hours=4),
        c1=_candle(opened_at - timedelta(hours=8)),
        c2=_candle(opened_at - timedelta(hours=4)),
        c3_m5=(),
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


def _observation(
    *,
    source: M15Bar,
    reference_price: int,
    kind: ReferenceKind,
) -> SourceObservation:
    level = OldLevel(
        kind=kind,
        price=reference_price,
        pivot_opened_at=source.opened_at - timedelta(hours=1),
        confirmed_at=source.opened_at - timedelta(minutes=30),
        policy=ReferencePolicy.UNTOUCHED_SWING_STRENGTH_1,
    )
    return SourceObservation(
        group=BreachGroup(
            source_candle=source,
            kind=kind,
            policy=ReferencePolicy.UNTOUCHED_SWING_STRENGTH_1,
            references=(level,),
        ),
        source_index=0,
        confirmation_state=ConfirmationState.NO_BODY_CONFIRMATION,
        confirmation_opened_at=None,
    )


def test_forensics_keeps_newest_competition_base_policy() -> None:
    assert BASE_POLICY is CompetitionPolicy.NEWEST_SUPERSEDES_CONFIRMATION_FIRST


def test_bucket_boundaries_are_deterministic() -> None:
    assert _bucket_generation(1) == "G1"
    assert _bucket_generation(2) == "G2"
    assert _bucket_generation(3) == "G3_PLUS"

    assert _bucket_references(1) == "REF1"
    assert _bucket_references(2) == "REF2_PLUS"

    assert _bucket_delay(1) == "D1"
    assert _bucket_delay(2) == "D2"
    assert _bucket_delay(3) == "D3_PLUS"

    assert _bucket_rr(Decimal("0.49")) == "RR_LT_0_50"
    assert _bucket_rr(Decimal("0.50")) == "RR_0_50_TO_0_75"
    assert _bucket_rr(Decimal("0.75")) == "RR_0_75_TO_1_00"
    assert _bucket_rr(Decimal("1.00")) == "RR_1_00_TO_1_25"
    assert _bucket_rr(Decimal("1.25")) == "RR_1_25_TO_1_50"
    assert _bucket_rr(Decimal("1.50")) == "RR_1_50_TO_2_00"
    assert _bucket_rr(Decimal("2.00")) == "RR_GE_2_00"

    assert _bucket_fraction(Decimal("0.24"), "BODY") == "BODY_LT_0_25"
    assert _bucket_fraction(Decimal("0.25"), "BODY") == "BODY_0_25_TO_0_50"
    assert _bucket_fraction(Decimal("0.50"), "BODY") == "BODY_0_50_TO_0_75"
    assert _bucket_fraction(Decimal("0.75"), "BODY") == "BODY_GE_0_75"

    assert _bucket_range_ratio(Decimal("0.09")) == "SRC_RANGE_LT_0_10_C1"
    assert _bucket_range_ratio(Decimal("0.10")) == "SRC_RANGE_0_10_TO_0_20_C1"
    assert _bucket_range_ratio(Decimal("0.20")) == "SRC_RANGE_0_20_TO_0_30_C1"
    assert _bucket_range_ratio(Decimal("0.30")) == "SRC_RANGE_GE_0_30_C1"


def test_source_body_and_range_are_pre_entry_features() -> None:
    t0 = datetime(2026, 1, 1, 20, 0, tzinfo=UTC)
    source = _bar(t0, 100, 110, 90, 105)

    assert _source_body_fraction(source) == Decimal("0.25")
    assert _source_range_to_c1(_parent(CrtPureCandidateDirection.BULLISH), source) == Decimal("0.5")


def test_penetration_fraction_bullish_uses_depth_below_old_low() -> None:
    t0 = datetime(2026, 1, 1, 20, 0, tzinfo=UTC)
    source = _bar(t0, 100, 108, 90, 95)
    observation = _observation(
        source=source,
        reference_price=96,
        kind=ReferenceKind.OLD_LOW,
    )

    assert _penetration_fraction(
        parent=_parent(CrtPureCandidateDirection.BULLISH),
        observation=observation,
    ) == Decimal(6) / Decimal(18)


def test_penetration_fraction_bearish_uses_depth_above_old_high() -> None:
    t0 = datetime(2026, 1, 1, 20, 0, tzinfo=UTC)
    source = _bar(t0, 100, 112, 94, 106)
    observation = _observation(
        source=source,
        reference_price=106,
        kind=ReferenceKind.OLD_HIGH,
    )

    assert _penetration_fraction(
        parent=_parent(CrtPureCandidateDirection.BEARISH),
        observation=observation,
    ) == Decimal(6) / Decimal(18)


def test_confirmation_delay_counts_whole_m15_bars_after_source_close() -> None:
    t0 = datetime(2026, 1, 1, 20, 0, tzinfo=UTC)
    source = _bar(t0, 100, 104, 95, 98)
    confirmation = _bar(t0 + timedelta(minutes=30), 99, 106, 98, 105)

    assert _delay_bars(source, confirmation) == 2
