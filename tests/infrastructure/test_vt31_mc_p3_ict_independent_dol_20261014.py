"""Independent price-lineage verification for ICT GENERAL, never author certification."""
from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from qore.infrastructure.traders.vt31_ict_cleanroom.cognition import (
    VT31CleanroomCognition,
)
from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    G3_MSS_FRAMEWORK_POLICY,
    M1Bar,
    SessionId,
    Side,
)
from scripts.vt31_mc_p3_ict_independent_dol_20261014 import (
    compare_general_cog_v2_with_dol,
    verify_ict_dol_from_m1,
)

NY = ZoneInfo("America/New_York")
HOURS = {SessionId.LONDON: 3, SessionId.NY_AM: 10, SessionId.NY_PM: 14}


def bar(
    t: datetime, o="100", high="102", lo="98", close="100.5",
) -> M1Bar:
    return M1Bar(
        t, t+timedelta(minutes=1),
        Decimal(o), Decimal(high), Decimal(lo), Decimal(close),
    )


def source_and_actual_cog(
    *, side: Side = Side.LONG,
    session: SessionId = SessionId.NY_AM,
    day: tuple[int, int, int] = (2025, 7, 1),
) -> tuple[tuple[M1Bar, ...], object]:
    h = HOURS[session]
    start = datetime(*day, 0, tzinfo=NY).astimezone(UTC)
    engine = VT31CleanroomCognition(
        framework_policy=G3_MSS_FRAMEWORK_POLICY,
    )
    rows: list[M1Bar] = []
    patterns = (
        [
            ("100", "103", "99", "101"),
            ("101", "103", "100", "100.5"),
            ("101", "105", "100", "102"),
            ("101", "104", "100", "101"),
            ("101", "104", "100", "104"),
            ("101", "109", "101", "107"),
        ] if side is Side.LONG else [
            ("100", "101", "97", "99"),
            ("99", "100", "97", "99.5"),
            ("99", "100", "95", "98"),
            ("99", "100", "96", "99"),
            ("99", "100", "96", "97"),
            ("99", "100", "91", "93"),
        ]
    )
    for minute in range(h*60+6):
        t = start+timedelta(minutes=minute)
        if minute == 45:
            row = bar(t, high="120")
        elif minute == 55:
            row = bar(t, lo="80")
        elif minute >= h*60:
            o, hi, lo, c = patterns[minute-h*60]
            row = bar(t, o=o, high=hi, lo=lo, close=c)
        else:
            row = bar(t)
        engine.observe_closed_m1(row)
        rows.append(row)
    at = rows[-1].closed_at
    actual = engine.assess(session=session, as_of=at)
    assert actual.decision is not None, actual.missing
    assert actual.decision.side is side
    assert actual.decision.draw_family == (
        "ASIA_NY_CLOCK_HIGH" if side is Side.LONG else "ASIA_NY_CLOCK_LOW"
    )
    assert actual.decision.draw_target == Decimal(
        "120" if side is Side.LONG else "80"
    )
    return tuple(rows), actual.decision


@pytest.mark.parametrize("session", [
    SessionId.LONDON, SessionId.NY_AM, SessionId.NY_PM,
])
@pytest.mark.parametrize("side", [Side.LONG, Side.SHORT])
@pytest.mark.parametrize("day", [(2025, 7, 1), (2025, 1, 15)])
def test_actual_cog_asia_pool_price_lineage_confirmed_all_ict_windows(
    session, side, day,
):
    rows, cog = source_and_actual_cog(
        session=session, side=side, day=day,
    )
    t = rows[-1].closed_at
    evidence = verify_ict_dol_from_m1(
        as_of=t, session=session, cognition=cog, history=rows,
    )
    assert evidence.state == "VERIFIED_QORE_DOL_PRICE_LINEAGE", evidence
    assert evidence.source_family == cog.draw_family
    assert evidence.observed_level == cog.draw_target
    assert evidence.source_confirmed_at == rows[179].closed_at
    assert evidence.reviewed_monitor_bars == len(rows)-180
    assert evidence.record()["method_certified"] is False
    assert evidence.execution_authorized is False
    combined = compare_general_cog_v2_with_dol(
        as_of=t, session=session, cognition=cog, history=rows,
    )
    assert combined.state == (
        "QORE_MSS_AND_DOL_SOURCE_SUPPORTED_NOT_ICT_CERTIFIED"
    ), combined
    assert combined.source_state == "VERIFIED_QORE_DOL_PRICE_LINEAGE"
    assert combined.v2_state == "UNKNOWN"
    assert not combined.method_certified and not combined.cognition_certified
    assert not combined.execution_authorized


def test_mutated_target_cannot_pass_independent_pool_source():
    rows, cog = source_and_actual_cog()
    false = replace(cog, draw_target=Decimal("121"))
    r = verify_ict_dol_from_m1(
        as_of=rows[-1].closed_at, session=SessionId.NY_AM,
        cognition=false, history=rows,
    )
    assert r.state == "REJECTED"
    assert "COG_DOL_PRICE_DIFFERS_FROM_INDEPENDENT_M1_SOURCE" in r.reasons
    assert r.observed_level == Decimal("120")


def test_tampered_pool_confirmation_timestamp_is_rejected():
    rows, cog = source_and_actual_cog()
    false = replace(
        cog, draw_level_observed_at=cog.draw_level_observed_at+timedelta(minutes=1),
    )
    out = verify_ict_dol_from_m1(
        as_of=rows[-1].closed_at, session=SessionId.NY_AM,
        cognition=false, history=rows,
    )
    assert out.state == "REJECTED"
    assert "COG_DOL_CONFIRMATION_TIMESTAMP_MISMATCH" in out.reasons


def test_independently_observed_consumption_invalidates_old_dol():
    rows, cog = source_and_actual_cog()
    altered = list(rows)
    altered[190] = bar(rows[190].opened_at, high="121")
    out = verify_ict_dol_from_m1(
        as_of=rows[-1].closed_at, session=SessionId.NY_AM,
        cognition=cog, history=tuple(altered),
    )
    assert out.state == "REJECTED"
    assert "DOL_ALREADY_CONSUMED_AFTER_CONFIRMATION" in out.reasons


def test_missing_asia_source_is_unknown_never_zero_imputed():
    rows, cog = source_and_actual_cog()
    missing = rows[:35]+rows[36:]
    out = verify_ict_dol_from_m1(
        as_of=rows[-1].closed_at, session=SessionId.NY_AM,
        cognition=cog, history=missing,
    )
    assert out.state == "UNKNOWN"
    assert "SOURCE_RANGE_INCOMPLETE_OR_M1_GAPPED" in out.reasons


def test_missing_post_confirmation_minute_is_unknown_path():
    rows, cog = source_and_actual_cog()
    missing = rows[:210]+rows[211:]
    out = verify_ict_dol_from_m1(
        as_of=rows[-1].closed_at, session=SessionId.NY_AM,
        cognition=cog, history=missing,
    )
    assert out.state == "UNKNOWN"
    assert "POST_CONFIRMATION_M1_MONITORING_GAP" in out.reasons


def test_duplicate_or_future_or_stale_source_never_verified():
    rows, cog = source_and_actual_cog()
    future = bar(rows[-1].closed_at)
    assert verify_ict_dol_from_m1(
        as_of=rows[-1].closed_at, session=SessionId.NY_AM,
        cognition=cog, history=rows+(future,),
    ).state == "REJECTED"
    assert verify_ict_dol_from_m1(
        as_of=rows[-1].closed_at, session=SessionId.NY_AM,
        cognition=cog, history=rows+(rows[-1],),
    ).state == "REJECTED"
    assert verify_ict_dol_from_m1(
        as_of=rows[-1].closed_at+timedelta(minutes=1),
        session=SessionId.NY_AM, cognition=cog, history=rows,
    ).state == "REJECTED"


def test_false_session_and_side_or_unknown_family_rejected():
    rows, cog = source_and_actual_cog()
    t = rows[-1].closed_at
    assert verify_ict_dol_from_m1(
        as_of=t, session=SessionId.LONDON, cognition=cog,
        history=rows,
    ).state == "REJECTED"
    side = replace(cog, side=Side.SHORT)
    assert "DOL_SOURCE_SIDE_CONTRADICTS_COG" in verify_ict_dol_from_m1(
        as_of=t, session=SessionId.NY_AM, cognition=side, history=rows,
    ).reasons
    unrecognized = replace(cog, draw_family="NAS100_MYSTERY_POOL_HIGH")
    assert verify_ict_dol_from_m1(
        as_of=t, session=SessionId.NY_AM, cognition=unrecognized,
        history=rows,
    ).state == "REJECTED"


def test_no_previous_complete_cash_source_returns_unknown_not_target_guess():
    rows, cog = source_and_actual_cog()
    false = replace(cog, draw_family="PRIOR_NY_CASH_SESSION_HIGH")
    r = verify_ict_dol_from_m1(
        as_of=rows[-1].closed_at, session=SessionId.NY_AM,
        cognition=false, history=rows,
    )
    assert r.state == "UNKNOWN"
    assert "PRIOR_NY_CASH_SESSION_COMPLETE_M1_UNKNOWN" in r.reasons


def test_london_pool_is_not_available_in_london_session():
    rows, cog = source_and_actual_cog(session=SessionId.LONDON)
    false = replace(cog, draw_family="LONDON_NY_CLOCK_HIGH")
    r = verify_ict_dol_from_m1(
        as_of=rows[-1].closed_at, session=SessionId.LONDON,
        cognition=false, history=rows,
    )
    assert r.state == "REJECTED"
    assert "LONDON_POOL_NOT_AVAILABLE_IN_LONDON_SESSION" in r.reasons


def test_no_cog_returns_unknown_never_owns_trader_direction():
    rows, _ = source_and_actual_cog()
    result = verify_ict_dol_from_m1(
        as_of=rows[-1].closed_at, session=SessionId.NY_AM,
        cognition=None, history=rows,
    )
    assert result.state == "UNKNOWN"
    assert "NO_COG_DECISION_AT_ASOF" in result.reasons


def test_composition_never_hides_bad_mss_price_as_ict_certified():
    rows, cog = source_and_actual_cog()
    wrong = replace(cog, mss_anchor_close=Decimal("109"))
    outcome = compare_general_cog_v2_with_dol(
        as_of=rows[-1].closed_at, session=SessionId.NY_AM,
        cognition=wrong, history=rows,
    )
    assert outcome.state == "REJECTED"
    assert not outcome.method_certified and not outcome.execution_authorized
