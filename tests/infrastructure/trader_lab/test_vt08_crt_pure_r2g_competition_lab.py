from __future__ import annotations

from datetime import UTC, datetime, timedelta

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
from qore.infrastructure.trader_lab.vt08_crt_pure_r2g_competition_lab import (
    POLICY_FAMILY,
    CompetitionPolicy,
    select_competing_hypothesis,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket
from qore.infrastructure.traders.crt_pure_methodology_candidate import (
    CrtPureCandidateDirection,
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


def _candle(opened_at: datetime) -> AggregatedCandle:
    return AggregatedCandle(
        opened_at=opened_at,
        closed_at=opened_at + timedelta(hours=4),
        open_price=100,
        high_price=110,
        low_price=90,
        close_price=100,
        m5_count=48,
    )


def _parent(opened_at: datetime) -> ParentCrt:
    return ParentCrt(
        market=CrtPureMarket.AUDUSD,
        direction=CrtPureCandidateDirection.BULLISH,
        triplet="1",
        c3_opened_at=opened_at,
        c3_closed_at=opened_at + timedelta(hours=4),
        c1=_candle(opened_at - timedelta(hours=8)),
        c2=_candle(opened_at - timedelta(hours=4)),
        c3_m5=(),
    )


def _observation(
    *,
    bar: M15Bar,
    source_index: int,
    price: int,
) -> SourceObservation:
    level = OldLevel(
        kind=ReferenceKind.OLD_LOW,
        price=price,
        pivot_opened_at=bar.opened_at - timedelta(hours=1),
        confirmed_at=bar.opened_at - timedelta(minutes=30),
        policy=ReferencePolicy.UNTOUCHED_SWING_STRENGTH_1,
    )
    return SourceObservation(
        group=BreachGroup(
            source_candle=bar,
            kind=ReferenceKind.OLD_LOW,
            policy=ReferencePolicy.UNTOUCHED_SWING_STRENGTH_1,
            references=(level,),
        ),
        source_index=source_index,
        confirmation_state=ConfirmationState.NO_BODY_CONFIRMATION,
        confirmation_opened_at=None,
    )


def test_policy_family_is_frozen_and_contains_control() -> None:
    assert POLICY_FAMILY == (
        CompetitionPolicy.FIRST_SOURCE_ONLY_CONTROL,
        CompetitionPolicy.FIRST_CONFIRMATION_WINS,
        CompetitionPolicy.NEWEST_SUPERSEDES_CONFIRMATION_FIRST,
        CompetitionPolicy.NEWEST_SUPERSEDES_SOURCE_FIRST,
    )


def test_first_source_control_does_not_fall_through_to_later_source() -> None:
    t0 = datetime(2026, 1, 1, 20, 0, tzinfo=UTC)
    source_1 = _bar(t0, 106, 108, 95, 98)
    no_confirm = _bar(t0 + timedelta(minutes=15), 98, 100, 97, 99)
    source_2 = _bar(t0 + timedelta(minutes=30), 104, 105, 96, 99)
    confirm_2 = _bar(t0 + timedelta(minutes=45), 99, 106, 99, 105)
    entry_2 = _bar(t0 + timedelta(minutes=60), 105, 107, 104, 106)
    c3 = (source_1, no_confirm, source_2, confirm_2, entry_2)
    observations = (
        _observation(bar=source_1, source_index=0, price=96),
        _observation(bar=source_2, source_index=2, price=97),
    )

    selected = select_competing_hypothesis(
        policy=CompetitionPolicy.FIRST_SOURCE_ONLY_CONTROL,
        parent=_parent(t0),
        observations=observations,
        c3_m15=c3,
    )

    assert selected is None


def test_first_confirmation_wins_can_select_later_independent_source() -> None:
    t0 = datetime(2026, 1, 1, 20, 0, tzinfo=UTC)
    source_1 = _bar(t0, 105, 107, 95, 98)
    source_2 = _bar(t0 + timedelta(minutes=15), 101, 103, 96, 99)
    confirm_2 = _bar(t0 + timedelta(minutes=30), 99, 103, 99, 102)
    entry = _bar(t0 + timedelta(minutes=45), 102, 104, 101, 103)
    late_confirm_1 = _bar(t0 + timedelta(minutes=60), 103, 107, 102, 106)
    final_entry = _bar(t0 + timedelta(minutes=75), 106, 108, 105, 107)
    c3 = (source_1, source_2, confirm_2, entry, late_confirm_1, final_entry)
    observations = (
        _observation(bar=source_1, source_index=0, price=96),
        _observation(bar=source_2, source_index=1, price=97),
    )

    selected = select_competing_hypothesis(
        policy=CompetitionPolicy.FIRST_CONFIRMATION_WINS,
        parent=_parent(t0),
        observations=observations,
        c3_m15=c3,
    )

    assert selected is not None
    assert selected[0] == observations[1]
    assert selected[1] == confirm_2
    assert selected[2] == entry


def test_same_close_tie_is_explicit_between_supersession_policies() -> None:
    t0 = datetime(2026, 1, 1, 20, 0, tzinfo=UTC)
    source_1 = _bar(t0, 100, 102, 95, 98)
    neutral = _bar(t0 + timedelta(minutes=15), 98, 100, 97, 99)
    # This candle both confirms source_1 and becomes a new bullish Model #1 source
    # candidate at its close: down-close, but still closes above source_1 open.
    source_2 = _bar(t0 + timedelta(minutes=30), 105, 106, 96, 102)
    confirm_2 = _bar(t0 + timedelta(minutes=45), 102, 107, 101, 106)
    entry_2 = _bar(t0 + timedelta(minutes=60), 106, 108, 105, 107)
    c3 = (source_1, neutral, source_2, confirm_2, entry_2)
    observations = (
        _observation(bar=source_1, source_index=0, price=96),
        _observation(bar=source_2, source_index=2, price=97),
    )
    parent = _parent(t0)

    confirmation_first = select_competing_hypothesis(
        policy=CompetitionPolicy.NEWEST_SUPERSEDES_CONFIRMATION_FIRST,
        parent=parent,
        observations=observations,
        c3_m15=c3,
    )
    source_first = select_competing_hypothesis(
        policy=CompetitionPolicy.NEWEST_SUPERSEDES_SOURCE_FIRST,
        parent=parent,
        observations=observations,
        c3_m15=c3,
    )

    assert confirmation_first is not None
    assert confirmation_first[0] == observations[0]
    assert source_first is not None
    assert source_first[0] == observations[1]
