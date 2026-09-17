from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab import cibo_market_atlas_target_destination_v2 as target
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import (
    Bar,
    Side,
    SourceCandle,
)


def _bar(
    opened_at: datetime,
    *,
    open_price: str,
    high: str,
    low: str,
    close: str,
) -> Bar:
    return Bar(
        opened_at=opened_at,
        closed_at=opened_at + timedelta(minutes=5),
        open=Decimal(open_price),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
    )


def _candle(
    opened_at: datetime,
    *,
    hours: int,
    high: str,
    low: str,
    close: str,
) -> SourceCandle:
    return SourceCandle(
        opened_at=opened_at,
        closed_at=opened_at + timedelta(hours=hours),
        open=Decimal(close),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        m5=(),
    )


def test_departure_anchor_requires_exact_completed_m5_bar() -> None:
    opened = datetime(2025, 1, 2, 10, 0, tzinfo=UTC)
    bars = (_bar(opened, open_price="99", high="101", low="98", close="100"),)
    opens = (opened,)

    assert target._departure_anchor(bars, opens, opened + timedelta(minutes=5)) == Decimal(
        "100"
    )
    assert target._departure_anchor(bars, opens, opened + timedelta(minutes=4)) is None


def test_supported_candidates_use_only_information_known_by_departure() -> None:
    departure = datetime(2025, 1, 2, 10, 30, tzinfo=UTC)
    prior = _candle(
        datetime(2025, 1, 2, 9, 0, tzinfo=UTC),
        hours=1,
        high="105",
        low="95",
        close="100",
    )
    current = _candle(
        datetime(2025, 1, 2, 10, 0, tzinfo=UTC),
        hours=1,
        high="150",
        low="98",
        close="101",
    )
    bars = tuple(
        _bar(
            datetime(2025, 1, 2, 10, minute, tzinfo=UTC),
            open_price="100",
            high="102",
            low="99",
            close="101",
        )
        for minute in (5, 10, 15, 20, 25)
    )
    row = {
        "liquidity_raid_at": datetime(2025, 1, 2, 10, 5, tzinfo=UTC).isoformat(),
        "opposite_boundary": "110",
        "source_timeframe": "H1",
        "source_boundary_created_at": datetime(
            2025, 1, 2, 9, 0, tzinfo=UTC
        ).isoformat(),
    }
    frames: dict[str, tuple[SourceCandle, ...]] = {"H1": (prior, current)}
    frame_opens = {"H1": tuple(item.opened_at for item in frames["H1"])}
    swings: dict[str, dict[Side, tuple[target.SwingCandidate, ...]]] = {
        "H1": {Side.LONG: (), Side.SHORT: ()}
    }
    swing_known: dict[str, dict[Side, tuple[datetime, ...]]] = {
        "H1": {Side.LONG: (), Side.SHORT: ()}
    }

    candidates = target._supported_candidates(
        row,
        departure=departure,
        anchor=Decimal("100"),
        side=Side.LONG,
        bars=bars,
        bar_opens=tuple(bar.opened_at for bar in bars),
        frames=frames,
        frame_opens=frame_opens,
        swings=swings,
        swing_known=swing_known,
    )

    assert {(item.kind, item.level) for item in candidates} == {
        ("SOURCE_OPPOSITE_BOUNDARY", Decimal("110")),
        ("PRIOR_CANDLE_DIRECTIONAL_BOUNDARY", Decimal("105")),
    }
    assert all(item.known_at <= departure for item in candidates)
    assert Decimal("150") not in {item.level for item in candidates}


def test_latest_active_swing_rejects_pre_departure_touch() -> None:
    departure = datetime(2025, 1, 2, 12, 0, tzinfo=UTC)
    stale = target.SwingCandidate(
        timeframe="H1",
        kind="ACTIVE_SWING_3_DIRECTIONAL_BOUNDARY",
        level=Decimal("105"),
        pivot_opened_at=datetime(2025, 1, 2, 8, 0, tzinfo=UTC),
        known_at=datetime(2025, 1, 2, 10, 0, tzinfo=UTC),
        touch_at=datetime(2025, 1, 2, 11, 0, tzinfo=UTC),
    )
    active = target.SwingCandidate(
        timeframe="H1",
        kind="ACTIVE_SWING_3_DIRECTIONAL_BOUNDARY",
        level=Decimal("110"),
        pivot_opened_at=datetime(2025, 1, 2, 9, 0, tzinfo=UTC),
        known_at=datetime(2025, 1, 2, 11, 0, tzinfo=UTC),
        touch_at=datetime(2025, 1, 2, 13, 0, tzinfo=UTC),
    )
    candidates = (stale, active)

    selected = target._latest_active_swing(
        candidates,
        tuple(item.known_at for item in candidates),
        departure=departure,
        anchor=Decimal("100"),
        side=Side.LONG,
    )

    assert selected is not None
    assert selected.level == Decimal("110")
    assert selected.known_at <= departure


def test_outcome_order_preserves_same_m5_ties() -> None:
    departure = datetime(2025, 1, 2, 11, 0, tzinfo=UTC)
    bars = (
        _bar(departure, open_price="100", high="106", low="99", close="105"),
        _bar(
            departure + timedelta(minutes=5),
            open_price="105",
            high="111",
            low="104",
            close="110",
        ),
    )
    known_at = departure - timedelta(hours=1)
    candidates = (
        target.Candidate(
            kind="TEST_A",
            timeframe="H1",
            level=Decimal("105"),
            structural_opened_at=known_at,
            known_at=known_at,
        ),
        target.Candidate(
            kind="TEST_B",
            timeframe="H1",
            level=Decimal("106"),
            structural_opened_at=known_at,
            known_at=known_at,
        ),
        target.Candidate(
            kind="TEST_C",
            timeframe="H1",
            level=Decimal("110"),
            structural_opened_at=known_at,
            known_at=known_at,
        ),
    )

    rows, episode = target._apply_outcomes(
        "episode-test",
        "XAUUSD",
        departure,
        Decimal("100"),
        Side.LONG,
        candidates,
        bars,
        tuple(bar.opened_at for bar in bars),
        Decimal("0.01"),
    )

    assert [row["touch_order_group"] for row in rows] == [1, 1, 2]
    assert rows[0]["touch_order_ambiguous_within_m5"] is True
    assert rows[1]["touch_order_ambiguous_within_m5"] is True
    assert rows[2]["touch_order_ambiguous_within_m5"] is False
    assert episode["first_touch_tied"] is True
    assert len(episode["first_touch_candidate_ids"]) == 2
    assert episode["complete_all_dol_claim"] is False
    assert episode["causal_candidate_selection"] is True


def test_candidate_universe_is_explicitly_bounded_and_research_only() -> None:
    assert target.IDENTITY == "CIBO_TARGET_DESTINATION_V2_SUPPORTED_REFERENCE_UNIVERSE"
    assert target.CANDIDATE_UNIVERSE == "SUPPORTED_REFERENCE_FAMILY_V2_BOUNDED"
    assert target.SOURCE_JOURNEY_RUN_ID == 35175979474
    assert target.SOURCE_M5_RUN_ID == 35166210458
