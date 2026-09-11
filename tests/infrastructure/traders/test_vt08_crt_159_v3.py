from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.traders.contracts import DemoTradingDecision, DemoTradingSetupSide
from qore.infrastructure.traders.vt08_crt_159_v3 import (
    SUPPORTED_MARKETS,
    Vt08Crt159V3Candle,
    Vt08Crt159V3Input,
    crt_direction,
    evaluate_vt08_crt_159_v3,
)


def _candle(
    opened: datetime,
    hours: int,
    open_price: str,
    high: str,
    low: str,
    close: str,
) -> Vt08Crt159V3Candle:
    return Vt08Crt159V3Candle(
        opened_at=opened,
        closed_at=opened + timedelta(hours=hours),
        open=Decimal(open_price),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
    )


def test_v3_exactly_supports_core_11_market_set() -> None:
    assert set(SUPPORTED_MARKETS) == {
        "AUDJPY",
        "AUDUSD",
        "EURUSD",
        "GBPJPY",
        "GBPUSD",
        "NAS100",
        "SP500",
        "US30",
        "USDCAD",
        "USDJPY",
        "XAUUSD",
    }


def test_crt_direction_requires_one_sided_sweep_and_close_back_inside() -> None:
    opened = datetime(2026, 1, 5, tzinfo=UTC)
    reference = _candle(opened, 4, "100", "110", "90", "105")
    bullish_manip = _candle(reference.closed_at, 4, "105", "108", "85", "95")
    bearish_manip = _candle(reference.closed_at, 4, "105", "115", "92", "100")
    assert crt_direction(reference, bullish_manip) is DemoTradingSetupSide.LONG
    assert crt_direction(reference, bearish_manip) is DemoTradingSetupSide.SHORT


def test_nested_daily_h4_h1_m15_alignment_yields_v3_long_setup() -> None:
    day0 = datetime(2026, 1, 2, tzinfo=UTC)
    daily_ref = _candle(day0, 24, "100", "120", "80", "110")
    daily_man = _candle(daily_ref.closed_at, 24, "110", "115", "75", "100")
    h4_ref = _candle(datetime(2026, 1, 5, 6, tzinfo=UTC), 4, "100", "110", "90", "105")
    h4_man = _candle(h4_ref.closed_at, 4, "105", "108", "88", "100")
    h1_ref = _candle(h4_man.closed_at, 1, "100", "104", "96", "102")
    h1_man = _candle(h1_ref.closed_at, 1, "102", "103", "94", "100")
    m15_ref = _candle(h1_man.closed_at, 1, "100", "102", "98", "101")
    m15_man = _candle(m15_ref.closed_at, 1, "101", "102", "97", "100")
    entry = _candle(m15_man.closed_at, 1, "100", "103", "99", "102")
    result = evaluate_vt08_crt_159_v3(
        Vt08Crt159V3Input(
            symbol="EURUSD",
            as_of=entry.opened_at,
            daily_reference=daily_ref,
            daily_manipulation=daily_man,
            h4_reference_01=h4_ref,
            h4_manipulation_05=h4_man,
            h1_reference_09=h1_ref,
            h1_manipulation_10=h1_man,
            m15_reference_1100=m15_ref,
            m15_manipulation_1115=m15_man,
            entry_bar_1130=entry,
            h4_distribution_closes_at=entry.opened_at + timedelta(hours=2),
        )
    )
    assert result.decision is DemoTradingDecision.SETUP
    assert result.setup is not None
    assert result.setup.side is DemoTradingSetupSide.LONG
    assert result.setup.entry_price == Decimal("100")
    assert result.setup.stop_loss == Decimal("97")
    assert result.setup.take_profit == Decimal("110")


def test_nested_direction_disagreement_abstains() -> None:
    opened = datetime(2026, 1, 2, tzinfo=UTC)
    daily_ref = _candle(opened, 24, "100", "120", "80", "110")
    daily_man = _candle(daily_ref.closed_at, 24, "110", "115", "75", "100")
    h4_ref = _candle(datetime(2026, 1, 5, 6, tzinfo=UTC), 4, "100", "110", "90", "105")
    h4_man = _candle(h4_ref.closed_at, 4, "105", "115", "95", "100")
    h1_ref = _candle(h4_man.closed_at, 1, "100", "104", "96", "102")
    h1_man = _candle(h1_ref.closed_at, 1, "102", "103", "94", "100")
    m15_ref = _candle(h1_man.closed_at, 1, "100", "102", "98", "101")
    m15_man = _candle(m15_ref.closed_at, 1, "101", "102", "97", "100")
    entry = _candle(m15_man.closed_at, 1, "100", "103", "99", "102")
    result = evaluate_vt08_crt_159_v3(
        Vt08Crt159V3Input(
            symbol="EURUSD",
            as_of=entry.opened_at,
            daily_reference=daily_ref,
            daily_manipulation=daily_man,
            h4_reference_01=h4_ref,
            h4_manipulation_05=h4_man,
            h1_reference_09=h1_ref,
            h1_manipulation_10=h1_man,
            m15_reference_1100=m15_ref,
            m15_manipulation_1115=m15_man,
            entry_bar_1130=entry,
            h4_distribution_closes_at=entry.opened_at + timedelta(hours=2),
        )
    )
    assert result.decision is DemoTradingDecision.ABSTAIN
