from collections import Counter
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import CapitalizerM1Bar
from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerSession
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_full_ict_density_scanner_1y_v1 import (
    DailyObjective,
    HTFBiasEvent,
    _fvg_fill_price_local,
    _latest_bias_before,
    _portfolio_max3,
    _scan_session,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceDirection,
)


def _bar(
    minute: int,
    *,
    open_: str,
    high: str,
    low: str,
    close: str,
) -> CapitalizerM1Bar:
    opened = datetime(2026, 1, 5, 13, 30, tzinfo=UTC) + timedelta(minutes=minute)
    return CapitalizerM1Bar(
        symbol="NAS100",
        opened_at=opened,
        closed_at=opened + timedelta(minutes=1),
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=None,
        digits=2,
    )


def _synthetic_long_chain() -> tuple[CapitalizerM1Bar, ...]:
    return (
        _bar(0, open_="100", high="101", low="99", close="100"),
        _bar(1, open_="100", high="102", low="100", close="101"),
        _bar(2, open_="101", high="101.5", low="99.5", close="100"),
        _bar(3, open_="100", high="101", low="100", close="100.5"),
        _bar(4, open_="100", high="100.2", low="99", close="99.8"),
        _bar(5, open_="99.8", high="103.5", low="99.7", close="103"),
        _bar(6, open_="103", high="103.2", low="101", close="102"),
        _bar(7, open_="102", high="102.2", low="100.8", close="101.2"),
        _bar(8, open_="101.2", high="105.2", low="101", close="104.8"),
        _bar(9, open_="104.8", high="105", low="104", close="104.5"),
    )


def test_fvg_fill_uses_first_causal_gap_touch() -> None:
    bar = _bar(0, open_="102", high="102.2", low="100.8", close="101.2")
    assert _fvg_fill_price_local(
        bar,
        fvg_low=Decimal("100.2"),
        fvg_high=Decimal("101"),
        side=CapitalizerSide.LONG,
    ) == Decimal("101")


def test_bias_confirmed_at_session_start_is_not_used_early() -> None:
    start = datetime(2026, 1, 5, 13, 30, tzinfo=UTC)
    previous = HTFBiasEvent(
        confirmed_at=start - timedelta(hours=1),
        direction=CapitalizerSourceDirection.BULLISH,
        closure_kind="CANDLE2_REVERSAL",
        poi_kind="SWING_LOW",
    )
    current = HTFBiasEvent(
        confirmed_at=start,
        direction=CapitalizerSourceDirection.BEARISH,
        closure_kind="CANDLE2_REVERSAL",
        poi_kind="SWING_HIGH",
    )
    events = (previous, current)
    assert _latest_bias_before(
        events,
        tuple(item.confirmed_at for item in events),
        start,
    ) == previous


def test_full_chain_produces_target_trade_without_old_candidate_ledger() -> None:
    bars = _synthetic_long_chain()
    bias = HTFBiasEvent(
        confirmed_at=bars[0].opened_at - timedelta(hours=2),
        direction=CapitalizerSourceDirection.BULLISH,
        closure_kind="CANDLE2_REVERSAL",
        poi_kind="SWING_LOW",
    )
    objective = DailyObjective(
        ny_date="2026-01-04",
        high=Decimal("105"),
        low=Decimal("95"),
    )
    stages: Counter[str] = Counter()
    trades = _scan_session(
        symbol="NAS100",
        session=CapitalizerSession.NEW_YORK,
        operating_date="2026-01-05",
        bars=bars,
        bias=bias,
        objective_source=objective,
        stages=stages,
    )
    assert len(trades) == 1
    trade = trades[0]
    assert trade.entry_price == "101"
    assert trade.stop_price == "99"
    assert trade.target_price == "105"
    assert trade.exit_reason == "TARGET"
    assert Decimal(trade.realized_gross_r) == Decimal("2")
    assert stages["M1_RAID"] >= 1
    assert stages["M1_DISPLACEMENT_AFTER_RAID"] >= 1
    assert stages["M1_MSS_AFTER_RAID"] >= 1
    assert stages["M1_FVG_AFTER_MSS"] >= 1
    assert stages["M1_RETRACE_ENTRY"] == 1


def test_portfolio_max3_keeps_first_three_entries_in_session() -> None:
    bars = _synthetic_long_chain()
    bias = HTFBiasEvent(
        confirmed_at=bars[0].opened_at - timedelta(hours=2),
        direction=CapitalizerSourceDirection.BULLISH,
        closure_kind="CANDLE2_REVERSAL",
        poi_kind="SWING_LOW",
    )
    objective = DailyObjective("2026-01-04", Decimal("105"), Decimal("95"))
    base = _scan_session(
        symbol="NAS100",
        session=CapitalizerSession.NEW_YORK,
        operating_date="2026-01-05",
        bars=bars,
        bias=bias,
        objective_source=objective,
        stages=Counter(),
    )[0]
    trades = tuple(
        replace(
            base,
            symbol=f"MKT{index}",
            entry_at=(
                datetime.fromisoformat(base.entry_at) + timedelta(seconds=index)
            ).isoformat(),
        )
        for index in range(4)
    )
    selected = _portfolio_max3(trades)
    assert len(selected) == 3
    assert [item.symbol for item in selected] == ["MKT0", "MKT1", "MKT2"]
