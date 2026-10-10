from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_stop_intelligence_p50_5y_replay_v1 import (
    _buffer_price,
    _candidate_stop,
    _ceil_to_increment,
    _pip_size,
)


def test_pip_size_is_market_specific() -> None:
    assert _pip_size("EURUSD") == Decimal("0.0001")
    assert _pip_size("USDJPY") == Decimal("0.01")
    assert _pip_size("NAS100") is None


def test_buffer_rounds_outward_to_provider_increment() -> None:
    assert _ceil_to_increment(Decimal("0.00121"), Decimal("0.0001")) == Decimal("0.0013")


def test_fx_buffer_uses_development_p50_absolute_pips() -> None:
    row = {"provider_quote_increment": "0.00001"}
    envelope = {
        "development_threshold_absolute": "2.3",
        "absolute_unit": "PIPS",
    }
    assert _buffer_price(
        symbol="EURUSD",
        row=row,
        envelope=envelope,
    ) == Decimal("0.00023")


def test_long_candidate_stop_is_beyond_ob_distal() -> None:
    row = {
        "provider_quote_increment": "0.00001",
        "entry_price": "1.10000",
        "target_price": "1.10200",
        "side": "LONG",
        "m1_order_block_low": "1.09950",
        "m1_order_block_high": "1.10010",
    }
    envelope = {
        "development_threshold_absolute": "2.0",
        "absolute_unit": "PIPS",
    }
    result = _candidate_stop(symbol="EURUSD", row=row, envelope=envelope)
    assert result is not None
    stop, buffer = result
    assert buffer == Decimal("0.00020")
    assert stop == Decimal("1.09930")


def test_short_candidate_stop_is_beyond_ob_distal() -> None:
    row = {
        "provider_quote_increment": "0.01",
        "entry_price": "100.00",
        "target_price": "95.00",
        "side": "SHORT",
        "m1_order_block_low": "99.00",
        "m1_order_block_high": "101.00",
    }
    envelope = {
        "development_threshold_absolute": "6.6",
        "absolute_unit": "PRICE_DISTANCE",
    }
    result = _candidate_stop(symbol="NAS100", row=row, envelope=envelope)
    assert result is not None
    stop, buffer = result
    assert buffer == Decimal("6.6")
    assert stop == Decimal("107.60")
