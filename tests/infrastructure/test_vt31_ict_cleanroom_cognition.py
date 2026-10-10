"""One clean-room VT31 cognitive producer: provenance, native DOL, MSS and no future."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from qore.infrastructure.traders.vt31_ict_cleanroom.cognition import (
    VERSION,
    VT31CleanroomCognition,
    _confirmed_break,
    _verified_pools,
)
from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    M1Bar,
    SessionId,
    Side,
)

NY = ZoneInfo("America/New_York")


def _bar(
    opened: datetime,
    *,
    o: str = "100",
    h: str = "101",
    lo: str = "99",
    c: str = "100.5",
) -> M1Bar:
    return M1Bar(
        opened_at=opened,
        closed_at=opened + timedelta(minutes=1),
        open=Decimal(o),
        high=Decimal(h),
        low=Decimal(lo),
        close=Decimal(c),
    )


def _fixtures() -> tuple[tuple[M1Bar, ...], datetime]:
    previous = datetime(2026, 1, 2, 14, 30, tzinfo=UTC)
    today = datetime(2026, 1, 5, 5, tzinfo=UTC)
    # FULL prior NY cash session 09:30-16:00: explicit high 150, low 80.
    prev_bars = tuple(
        _bar(
            previous + timedelta(minutes=i),
            o="110", h="150" if i == 33 else "114",
            lo="80" if i == 45 else "108", c="111",
        )
        for i in range(390)
    )
    # Completed Asian range 00:00-03:00 NY: 180 closed M1.
    asia = tuple(
        _bar(today + timedelta(minutes=i))
        for i in range(180)
    )
    start = today + timedelta(minutes=180)  # 03:00 EST
    events = (
        _bar(start, o="100", h="103", lo="99", c="101"),
        _bar(start + timedelta(minutes=1), o="101", h="103", lo="100", c="100.5"),
        _bar(start + timedelta(minutes=2), o="101", h="105", lo="100", c="102"),
        _bar(start + timedelta(minutes=3), o="101", h="104", lo="100", c="101"),
        _bar(start + timedelta(minutes=4), o="101", h="104", lo="100", c="104"),
        _bar(start + timedelta(minutes=5), o="101", h="109", lo="101", c="107"),
    )
    return prev_bars + asia + events, events[-1].closed_at


def test_one_cleanroom_cognition_produces_timestamped_dol_and_shift() -> None:
    bars, at = _fixtures()
    engine = VT31CleanroomCognition()
    for bar in bars:
        engine.observe_closed_m1(bar)
    result = engine.assess(session=SessionId.LONDON, as_of=at)
    assert result.decision is not None, result.missing
    assert result.decision.session is SessionId.LONDON
    assert result.decision.side is Side.LONG
    assert result.decision.draw_family == "PRIOR_NY_CASH_SESSION_HIGH"
    assert result.decision.draw_target == Decimal("150")
    assert result.decision.structure_level == Decimal("105")
    assert result.decision.structure_level_confirmed_at < (
        result.decision.structure_break_confirmed_at
    )
    assert result.decision.draw_level_observed_at <= at
    assert "H1" in result.verified_htf
    assert "M15" in result.verified_htf
    assert "MSS_PIVOT_CONFIRMED" in result.decision.source_provenance
    assert result.trade_authorized is False
    assert VERSION == result.decision.cognitive_version


def test_market_cognition_cannot_consume_future_bar_then_fake_past_time() -> None:
    bars, at = _fixtures()
    engine = VT31CleanroomCognition()
    for bar in bars:
        engine.observe_closed_m1(bar)
    with pytest.raises(ValueError, match="exactly latest closed"):
        engine.assess(
            session=SessionId.LONDON,
            as_of=at - timedelta(minutes=1),
        )
    previous = engine.assess(session=SessionId.LONDON, as_of=at)
    future_bar = _bar(at, o="107", h="140", lo="103", c="139")
    engine.observe_closed_m1(future_bar)
    with pytest.raises(ValueError, match="exactly latest closed"):
        engine.assess(session=SessionId.LONDON, as_of=at)
    assert previous.decision is not None
    assert previous.decision.draw_target == Decimal("150")


def test_missing_real_pools_or_unconfirmed_mss_fails_closed() -> None:
    bars, at = _fixtures()
    no_prior = tuple(
        bar for bar in bars if bar.opened_at.date() == at.date()
    )
    unavailable = VT31CleanroomCognition()
    for bar in no_prior:
        unavailable.observe_closed_m1(bar)
    output = unavailable.assess(session=SessionId.LONDON, as_of=at)
    assert output.decision is None
    assert "LIQUIDITY_POOL" in output.missing
    assert not output.trade_authorized
    truncated = bars[:-1]
    assert _confirmed_break(truncated) is None


def test_timestamped_liquidity_has_no_future_source() -> None:
    bars, at = _fixtures()
    now = _verified_pools(
        bars, at, SessionId.LONDON,
    )
    assert any(p.family == "PRIOR_NY_CASH_SESSION_HIGH" for p in now)
    assert not any(p.family == "ASIA_NY_CLOCK_HIGH" for p in now)
    # The completed Asia high of 101 was swept by the later 03:02 high
    # of 105. It cannot be re-offered as unswept draw-on-liquidity.
    assert all(p.confirmed_at <= at for p in now)
    after = _verified_pools(
        bars,
        at - timedelta(hours=1),
        SessionId.LONDON,
    )
    # Pure producer expects a causally filtered series. All returned
    # producers must still carry their original timestamp.
    assert all(p.confirmed_at <= at for p in after)


def test_market_cognition_rejects_duplicate_and_misordered_m1() -> None:
    bars, _ = _fixtures()
    e = VT31CleanroomCognition()
    e.observe_closed_m1(bars[-1])
    with pytest.raises(ValueError, match="duplicate/overlapping"):
        e.observe_closed_m1(bars[-1])
    with pytest.raises(ValueError, match="duplicate/overlapping"):
        e.observe_closed_m1(bars[0])


def test_no_legacy_research_or_dynamic_risk_in_cleanroom() -> None:
    import ast
    from pathlib import Path

    p = (
        Path(__file__).resolve().parents[2]
        / "src/qore/infrastructure/traders/vt31_ict_cleanroom/cognition.py"
    )
    syntax = ast.parse(p.read_text(encoding="utf-8"))
    banned = (
        "vt31_nas100_", "vt31_silver_bullet", "ttrades",
        "comp008", "comp009", "legacy",
    )
    for node in ast.walk(syntax):
        if isinstance(node, ast.ImportFrom):
            module = (node.module or "").lower()
            assert not any(name in module for name in banned)
    assert set(VT31CleanroomCognition.assess.__annotations__) >= {
        "session", "as_of",
    }


def test_old_closed_htf_does_not_masquerade_as_current_session_context() -> None:
    bars, at = _fixtures()
    # Preserve the prior Friday DOL and current 03:00 MSS, but delete the
    # completed current-day H1/M15 evidence. COG MUST NOT carry Friday H1.
    stale = tuple(
        b for b in bars
        if b.opened_at.date() != at.date()
        or b.opened_at.hour >= 8
    )
    engine = VT31CleanroomCognition()
    for bar in stale:
        engine.observe_closed_m1(bar)
    result = engine.assess(session=SessionId.LONDON, as_of=at)
    assert result.decision is None
    assert "H1_CLOSED_CONTEXT" in result.missing
    assert "M15_CLOSED_CONTEXT" in result.missing
    assert result.verified_htf == ()


def test_real_cognitive_decision_is_consumed_by_ops_same_session_fvg() -> None:
    from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
        MethodologyDecision,
    )
    from qore.infrastructure.traders.vt31_ict_cleanroom.trader import (
        VT31Trader,
    )

    bars, _ = _fixtures()
    last = bars[-1]
    # Actual strictly directional FVG: the third 03:05 candle has low 105,
    # above the 03:03 candle high 104. It also breaks the confirmed 105 MSS.
    final = _bar(
        last.opened_at, o="105", h="109", lo="105", c="108",
    )
    trader = VT31Trader()
    last_out = None
    for item in (*bars[:-1], final):
        last_out = trader.on_closed_m1(item)
    assert last_out is not None
    assert last_out.cognition is not None
    assert last_out.cognition.decision is not None
    assert last_out.cognition.decision.draw_target == Decimal("150")
    assert last_out.operational_phase is MethodologyDecision.RESEARCH_PENDING_CE
    state = trader.snapshot()
    assert state["registered_trader_count"] == 1
    assert state["session_windows"][-1]["model"] == "LONDON"
    assert state["live_authorized"] is False


def test_partial_previous_day_is_not_false_confirmed_pdh_or_cash_pool() -> None:
    bars, at = _fixtures()
    prior = tuple(b for b in bars if b.opened_at.date() != at.date())
    current = tuple(b for b in bars if b.opened_at.date() == at.date())
    incomplete = prior[:180] + current
    pools = _verified_pools(incomplete, at, SessionId.LONDON)
    assert not any(p.family.startswith("PRIOR_NY_CASH_SESSION") for p in pools)
    full = _verified_pools(bars, at, SessionId.LONDON)
    assert any(p.family == "PRIOR_NY_CASH_SESSION_HIGH" for p in full)
    assert all(p.confirmed_at <= at for p in full)
