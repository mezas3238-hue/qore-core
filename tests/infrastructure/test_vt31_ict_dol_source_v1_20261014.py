"""Source-only ICT contextual DOL provenance, adversarial M1 fixtures; no PnL."""
from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    NEW_YORK,
    CognitiveDecision,
    M1Bar,
    SessionId,
    Side,
)
from scripts.vt31_ict_dol_source_v1_20261014 import attest_ict_dol_source


def instant(year: int, month: int, day: int, hour: int, minute: int = 0):
    return datetime(
        year, month, day, hour, minute, tzinfo=NEW_YORK,
    ).astimezone(UTC)


def bar(start: datetime, high: str = "102", low: str = "98") -> M1Bar:
    return M1Bar(
        start, start + timedelta(minutes=1),
        Decimal("100"), Decimal(high), Decimal(low), Decimal("100"),
    )


def strip(start: datetime, end: datetime) -> tuple[M1Bar, ...]:
    n = int((end - start).total_seconds() // 60)
    return tuple(bar(start + timedelta(minutes=i)) for i in range(n))


def upgrade(
    bars: tuple[M1Bar, ...], start: datetime, end: datetime,
    high: str, low: str,
) -> tuple[M1Bar, ...]:
    rows = list(bars)
    indices = [i for i, b in enumerate(rows) if start <= b.opened_at < end]
    assert indices
    rows[indices[4]] = bar(rows[indices[4]].opened_at, high=high)
    rows[indices[5]] = bar(rows[indices[5]].opened_at, low=low)
    return tuple(rows)


def scenario(
    session: SessionId = SessionId.NY_AM,
    source: str = "ASIA_NY_CLOCK",
    side: Side = Side.LONG,
    month: int = 7,
) -> tuple[tuple[M1Bar, ...], CognitiveDecision]:
    day = 1 if month == 7 else 15
    begin = instant(2025, month, day, 0)
    hour = {SessionId.LONDON: 3, SessionId.NY_AM: 10, SessionId.NY_PM: 14}[session]
    at = instant(2025, month, day, hour, 6)
    history = strip(begin, at)
    asia_end = instant(2025, month, day, 3)
    london_end = instant(2025, month, day, 5)
    history = upgrade(history, begin, asia_end, "110", "90")
    # Use non-consumptive London range for Asia tests.
    london_high, london_low = (
        ("104", "96") if source == "ASIA_NY_CLOCK" else ("120", "80")
    )
    history = upgrade(
        history, asia_end, london_end, london_high, london_low,
    ) if session != SessionId.LONDON else history
    src_end = asia_end if source == "ASIA_NY_CLOCK" else london_end
    hi, lo = ("110", "90") if source == "ASIA_NY_CLOCK" else ("120", "80")
    cognition = CognitiveDecision(
        session=session, side=side, observed_at=at,
        draw_target=Decimal(hi if side == Side.LONG else lo),
        draw_family=source + ("_HIGH" if side == Side.LONG else "_LOW"),
        draw_level_observed_at=src_end,
        structure_level=Decimal("100"),
        structure_level_confirmed_at=begin,
        structure_break_confirmed_at=at,
        source_provenance="SYNTHETIC_FIXTURE_NOT_SOURCE_AUTHOR",
        cognitive_version="TEST_ONLY_EXISTING_COG_DTO",
    )
    return history, cognition


@pytest.mark.parametrize("session,source", [
    (SessionId.LONDON, "ASIA_NY_CLOCK"),
    (SessionId.NY_AM, "ASIA_NY_CLOCK"),
    (SessionId.NY_AM, "LONDON_NY_CLOCK"),
    (SessionId.NY_PM, "ASIA_NY_CLOCK"),
    (SessionId.NY_PM, "LONDON_NY_CLOCK"),
])
@pytest.mark.parametrize("side", [Side.LONG, Side.SHORT])
@pytest.mark.parametrize("month,utc_offset", [(7, -4), (1, -5)])
def test_five_session_source_combinations_both_sides_and_dst(
    session, source, side, month, utc_offset,
):
    history, cognition = scenario(session, source, side, month)
    out = attest_ict_dol_source(
        as_of=cognition.observed_at, session=session,
        history=history, cognition=cognition,
    )
    assert out.state == "CONFIRMED", out.record()
    assert out.pools and len(out.pools) == 6
    matched = next(p for p in out.pools if p.family == cognition.draw_family)
    assert matched.level == cognition.draw_target
    assert matched.state == "UNCONSUMED"
    hours = cognition.observed_at.astimezone(NEW_YORK).utcoffset()
    assert int(hours.total_seconds() / 3600) == utc_offset
    assert not out.method_certified and not out.cognition_certified
    assert not out.execution_authorized
    assert out.record()["pools"][0]["source_end"]


def test_source_only_does_not_mint_a_cognitive_decision():
    history, cog = scenario()
    out = attest_ict_dol_source(
        as_of=cog.observed_at, session=cog.session, history=history,
    )
    assert out.state == "UNKNOWN"
    assert "NO_PREEXISTING_COG_DECISION" in out.reasons
    assert len(out.pools) == 6


def test_original_london_session_cannot_use_five_am_london_pool():
    history, cog = scenario(SessionId.LONDON)
    bad = replace(
        cog, draw_family="LONDON_NY_CLOCK_HIGH",
        draw_target=Decimal("120"),
        draw_level_observed_at=instant(2025, 7, 1, 3),
    )
    out = attest_ict_dol_source(
        as_of=cog.observed_at, session=cog.session, history=history,
        cognition=bad,
    )
    assert out.state == "REJECTED"
    assert "COG_DOL_ANNOUNCED_BEFORE_SOURCE_CLOSE" in out.reasons
    assert all(
        p.state == "UNKNOWN"
        for p in out.pools if p.family.startswith("LONDON_NY_CLOCK")
    )


def test_wrong_price_is_rejected_not_silently_rounded():
    history, cog = scenario()
    false = replace(cog, draw_target=cog.draw_target + Decimal("0.01"))
    out = attest_ict_dol_source(
        as_of=cog.observed_at, session=cog.session,
        history=history, cognition=false,
    )
    assert out.state == "REJECTED"
    assert "COG_DOL_PRICE_DISAGREES_WITH_SOURCE_M1" in out.reasons


def test_unrecognized_family_and_wrong_side_are_rejected():
    history, cog = scenario()
    args = dict(as_of=cog.observed_at, session=cog.session, history=history)
    assert attest_ict_dol_source(
        **args, cognition=replace(cog, draw_family="PRIOR_WEEK_HIGH"),
    ).state == "REJECTED"
    assert "COG_DOL_SIDE_CONTRADICTS_DIRECTION" in attest_ict_dol_source(
        **args, cognition=replace(cog, side=Side.SHORT),
    ).reasons


def test_consumed_pool_cannot_be_revived_after_price_retreat():
    history, cog = scenario(SessionId.NY_AM, "ASIA_NY_CLOCK")
    index = next(
        i for i, b in enumerate(history)
        if b.opened_at == instant(2025, 7, 1, 5, 30)
    )
    modified = list(history)
    modified[index] = bar(history[index].opened_at, high="111")
    out = attest_ict_dol_source(
        as_of=cog.observed_at, session=cog.session,
        history=tuple(modified), cognition=cog,
    )
    assert out.state == "REJECTED"
    assert "COG_DOL_ALREADY_CONSUMED" in out.reasons
    source = next(p for p in out.pools if p.family == cog.draw_family)
    assert source.first_touch_at == modified[index].closed_at


def test_missing_source_candle_causes_unknown_without_level_from_cog():
    history, cog = scenario()
    missing = tuple(
        b for b in history
        if b.opened_at != instant(2025, 7, 1, 1, 3)
    )
    out = attest_ict_dol_source(
        as_of=cog.observed_at, session=cog.session,
        history=missing, cognition=cog,
    )
    assert out.state == "UNKNOWN"
    source = next(p for p in out.pools if p.family == cog.draw_family)
    assert source.level is None and source.state == "UNKNOWN"


def test_missing_post_source_candle_means_unknown_not_free_liquidity():
    history, cog = scenario()
    missing = tuple(
        b for b in history
        if b.opened_at != instant(2025, 7, 1, 3, 22)
    )
    out = attest_ict_dol_source(
        as_of=cog.observed_at, session=cog.session,
        history=missing, cognition=cog,
    )
    assert out.state == "UNKNOWN"
    assert "POOL_AVAILABILITY_UNVERIFIABLE" in out.reasons


@pytest.mark.parametrize("input_name", ["duplicate", "unsorted", "future"])
def test_duplicate_unsorted_and_future_m1_rejected(input_name):
    history, cog = scenario()
    if input_name == "duplicate":
        corrupted = history[:8] + (history[7],) + history[8:]
    elif input_name == "unsorted":
        corrupted = (history[1], history[0]) + history[2:]
    else:
        corrupted = history + (bar(cog.observed_at),)
    out = attest_ict_dol_source(
        as_of=cog.observed_at, session=cog.session,
        history=corrupted, cognition=cog,
    )
    assert out.state == "REJECTED"


def test_stale_asof_or_wrong_session_cannot_authorize():
    history, cog = scenario()
    args = dict(as_of=cog.observed_at, session=cog.session, history=history)
    assert "COG_SESSION_OR_ASOF_MISMATCH" in attest_ict_dol_source(
        **args, cognition=replace(
            cog, observed_at=cog.observed_at + timedelta(minutes=1)
        ),
    ).reasons
    assert attest_ict_dol_source(
        **dict(args, session=SessionId.LONDON), cognition=cog,
    ).state == "REJECTED"


def test_previous_cash_prior_weekday_complete_and_source_clock():
    prev_start = instant(2025, 6, 30, 9, 30)
    current_at = instant(2025, 7, 1, 10, 6)
    history = strip(prev_start, current_at)
    history = upgrade(
        history, prev_start, instant(2025, 6, 30, 16),
        "150", "50",
    )
    cog = CognitiveDecision(
        session=SessionId.NY_AM, side=Side.LONG,
        observed_at=current_at, draw_target=Decimal("150"),
        draw_family="PRIOR_NY_CASH_SESSION_HIGH",
        draw_level_observed_at=instant(2025, 6, 30, 16),
        structure_level=Decimal("100"),
        structure_level_confirmed_at=prev_start,
        structure_break_confirmed_at=current_at,
        source_provenance="TEST_ONLY", cognitive_version="SYNTHETIC",
    )
    out = attest_ict_dol_source(
        as_of=current_at, session=cog.session,
        history=history, cognition=cog,
    )
    assert out.state == "CONFIRMED", out.record()
    source = next(p for p in out.pools if p.family == cog.draw_family)
    assert source.source_end == instant(2025, 6, 30, 16)


def test_monday_previous_friday_without_weekend_market_calendar_unknown():
    friday_start = instant(2025, 7, 4, 9, 30)
    monday_start = instant(2025, 7, 7, 0)
    monday_at = instant(2025, 7, 7, 3, 6)
    # Synthetic Friday cash fixture, NOT asserting July 4 real market was open.
    friday = upgrade(
        strip(friday_start, instant(2025, 7, 4, 16)),
        friday_start, instant(2025, 7, 4, 16), "150", "50",
    )
    history = friday + strip(monday_start, monday_at)
    cog = CognitiveDecision(
        session=SessionId.LONDON, side=Side.LONG,
        observed_at=monday_at, draw_target=Decimal("150"),
        draw_family="PRIOR_NY_CASH_SESSION_HIGH",
        draw_level_observed_at=instant(2025, 7, 4, 16),
        structure_level=Decimal("100"),
        structure_level_confirmed_at=friday_start,
        structure_break_confirmed_at=monday_at,
        source_provenance="TEST_ONLY", cognitive_version="SYNTHETIC",
    )
    out = attest_ict_dol_source(
        as_of=monday_at, session=SessionId.LONDON,
        history=history, cognition=cog,
    )
    assert out.state == "UNKNOWN"
    assert "POOL_AVAILABILITY_UNVERIFIABLE" in out.reasons


def test_weekday_holiday_or_early_close_does_not_fallback_to_older_cash():
    history, cog = scenario()
    older_friday = strip(
        instant(2025, 6, 27, 9, 30), instant(2025, 6, 27, 16),
    )
    history = older_friday + history
    candidate = replace(
        cog, draw_family="PRIOR_NY_CASH_SESSION_HIGH",
        draw_level_observed_at=instant(2025, 6, 30, 16),
    )
    out = attest_ict_dol_source(
        as_of=cog.observed_at, session=cog.session,
        history=history, cognition=candidate,
    )
    assert out.state == "UNKNOWN"
    assert "SOURCE_POOL_NOT_CAUSALLY_ATTESTABLE" in out.reasons


def test_neither_method_nor_economic_gate_is_authorized():
    history, cog = scenario(SessionId.NY_PM, "LONDON_NY_CLOCK")
    attestation = attest_ict_dol_source(
        as_of=cog.observed_at, session=cog.session,
        history=history, cognition=cog,
    )
    public = attestation.record()
    assert public["method_certified"] is False
    assert public["cognition_certified"] is False
    assert public["execution_authorized"] is False
    assert "profit_factor" not in public
    assert "lot_size" not in public


def test_genuine_cleanroom_cog_pool_price_rebuilt_independently():
    """Actual original engine emits cash=150; we verify source without its DTO.

    The gap from prior cash close to current 09:00 means UNCONSUMED is not
    attested. Source identity and level are verified, but availability UNKNOWN.
    """
    from qore.infrastructure.traders.vt31_ict_cleanroom.cognition import (
        VT31CleanroomCognition,
    )
    from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
        G3_MSS_FRAMEWORK_POLICY,
    )
    from scripts.vt31_cog_evidence_v2_20261014 import (
        ICT_GENERAL,
        inspect_cog_evidence,
    )

    day9 = instant(2025, 7, 1, 9)
    day10 = instant(2025, 7, 1, 10)
    prev = instant(2025, 6, 30, 9, 30)

    def native(
        start: datetime, o: str, hi: str, lo: str, c: str,
    ) -> M1Bar:
        return M1Bar(
            start, start + timedelta(minutes=1),
            Decimal(o), Decimal(hi), Decimal(lo), Decimal(c),
        )

    prior_cash = tuple(
        native(
            prev + timedelta(minutes=i), "110",
            "150" if i == 33 else "114",
            "80" if i == 45 else "108", "111",
        )
        for i in range(390)
    )
    nine = [
        native(day9 + timedelta(minutes=i), "100", "102", "98", "101")
        for i in range(60)
    ]
    nine[10] = native(day9 + timedelta(minutes=10), "100", "110", "98", "101")
    nine[20] = native(day9 + timedelta(minutes=20), "100", "102", "90", "101")
    nine[57] = native(day9 + timedelta(minutes=57), "100", "104", "98", "101")
    ten = (
        native(day10, "100", "102", "98", "100"),
        native(day10 + timedelta(minutes=1), "96", "99", "89", "95"),
        native(day10 + timedelta(minutes=2), "94", "106", "93", "105"),
    )
    engine = VT31CleanroomCognition(
        framework_policy=G3_MSS_FRAMEWORK_POLICY,
    )
    emitted = None
    for row in prior_cash + tuple(nine) + ten:
        engine.observe_closed_m1(row)
        if row.closed_at == ten[-1].closed_at:
            emitted = engine.assess(
                session=SessionId.NY_AM, as_of=row.closed_at,
            ).decision
    assert emitted is not None
    assert emitted.draw_family == "PRIOR_NY_CASH_SESSION_HIGH"
    assert emitted.draw_target == Decimal("150")

    raw_history = prior_cash + tuple(nine) + ten
    m2 = attest_ict_dol_source(
        as_of=ten[-1].closed_at, session=SessionId.NY_AM,
        history=raw_history, cognition=emitted,
    )
    pool = next(p for p in m2.pools if p.family == emitted.draw_family)
    assert pool.level == Decimal("150")  # source independent of DTO
    assert pool.source_end == instant(2025, 6, 30, 16)
    assert pool.state == "UNKNOWN"  # cannot infer no overnight touches
    assert m2.state == "UNKNOWN"
    assert "POOL_AVAILABILITY_UNVERIFIABLE" in m2.reasons
    v2 = inspect_cog_evidence(
        profile=ICT_GENERAL, session=SessionId.NY_AM,
        as_of=ten[-1].closed_at, history=raw_history, cognition=emitted,
    )
    assert v2.state == "UNKNOWN"  # original V2 still not globally certified
    assert not m2.method_certified and not m2.execution_authorized
