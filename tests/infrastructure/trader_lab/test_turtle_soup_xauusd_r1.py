from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab import turtle_soup_xauusd_r1 as r1
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import (
    Bar,
    Side,
    SourceCandle,
)


def _source(
    opened: datetime,
    *,
    open_: str,
    high: str,
    low: str,
    close: str,
) -> SourceCandle:
    return SourceCandle(
        opened_at=opened,
        closed_at=opened + timedelta(hours=1),
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        m5=(),
    )


def _trade(index: int, primary: str, stress: str) -> r1.Trade:
    quarter_month = (index % 4) * 3 + 1
    entry_at = datetime(2015, quarter_month, 2, tzinfo=UTC) + timedelta(days=index // 4)
    gross = Decimal(primary) + r1.PRIMARY_FRICTION_R
    return r1.Trade(
        timeframe="H4" if index % 2 == 0 else "H1",
        side=Side.LONG if index % 2 == 0 else Side.SHORT,
        c1_opened_at=entry_at - timedelta(hours=8),
        c2_opened_at=entry_at - timedelta(hours=4),
        raid_at=entry_at - timedelta(hours=3),
        cisd_at=entry_at - timedelta(minutes=30),
        entry_at=entry_at,
        exit_at=entry_at + timedelta(hours=1),
        entry=Decimal("1200"),
        stop=Decimal("1190"),
        target=Decimal("1220"),
        exit_price=Decimal("1210"),
        projected_r=Decimal("2"),
        gross_r=gross,
        primary_net_r=Decimal(primary),
        stress_net_r=Decimal(stress),
        exit_reason="target",
        session_bucket="london",
        prior_body_alignment="opposed",
    )


def test_frozen_identity_and_holdout_window() -> None:
    assert r1.IDENTITY == "TURTLE_SOUP_XAUUSD_R1"
    assert r1.HOLDOUT_ID == "TURTLE_SOUP_XAUUSD_R1_FRESH_2015_2016"
    assert r1.SYMBOL == "XAUUSD"
    assert r1.EVIDENCE_TIER == "E4_FROZEN_CANDIDATE_RULE"
    assert r1.ACQUISITION_OPEN == datetime(2015, 1, 1, tzinfo=UTC)
    assert r1.EVAL_OPEN == datetime(2015, 3, 1, tzinfo=UTC)
    assert r1.EVAL_CLOSE == datetime(2016, 3, 1, tzinfo=UTC)
    assert r1.MAX_LIFETIME == timedelta(hours=24)


def test_exact_c2_closure_is_frozen() -> None:
    opened = datetime(2026, 1, 1, tzinfo=UTC)
    c1 = _source(opened, open_="100", high="110", low="90", close="100")
    bullish = _source(
        opened + timedelta(hours=1),
        open_="95",
        high="108",
        low="89",
        close="91",
    )
    bearish = _source(
        opened + timedelta(hours=1),
        open_="105",
        high="111",
        low="92",
        close="109",
    )
    neither = _source(
        opened + timedelta(hours=1),
        open_="100",
        high="109",
        low="91",
        close="101",
    )
    assert r1.exact_c2_side(c1, bullish) is Side.LONG
    assert r1.exact_c2_side(c1, bearish) is Side.SHORT
    assert r1.exact_c2_side(c1, neither) is None


def test_target_must_remain_untouched_before_entry() -> None:
    opened = datetime(2026, 1, 1, tzinfo=UTC)
    bar = Bar(
        opened_at=opened,
        closed_at=opened + timedelta(minutes=5),
        open=Decimal("100"),
        high=Decimal("105"),
        low=Decimal("95"),
        close=Decimal("101"),
    )
    candle = SourceCandle(
        opened_at=opened,
        closed_at=opened + timedelta(hours=1),
        open=Decimal("100"),
        high=Decimal("105"),
        low=Decimal("95"),
        close=Decimal("101"),
        m5=(bar,),
    )
    assert r1._target_untouched(candle, Side.LONG, Decimal("106")) is True
    assert r1._target_untouched(candle, Side.LONG, Decimal("105")) is False
    assert r1._target_untouched(candle, Side.SHORT, Decimal("94")) is True
    assert r1._target_untouched(candle, Side.SHORT, Decimal("95")) is False


def test_preregistered_gate_can_survive_but_never_certifies() -> None:
    trades = [
        _trade(index, "0.60", "0.55") if index % 5 else _trade(index, "-0.40", "-0.45")
        for index in range(40)
    ]
    outcome, checks = r1._research_outcome(trades)
    assert outcome == "OOS_SURVIVED_RESEARCH_GATE_NOT_CERTIFIED"
    assert all(checks.values())


def test_small_sample_is_rejected() -> None:
    trades = [_trade(index, "0.50", "0.45") for index in range(20)]
    outcome, checks = r1._research_outcome(trades)
    assert outcome == "R1_REJECTED_FOR_PROMOTION"
    assert checks["sample_at_least_30"] is False
