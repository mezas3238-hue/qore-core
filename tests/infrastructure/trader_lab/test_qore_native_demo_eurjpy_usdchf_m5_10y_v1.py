"""A read-only, exact-two-symbol isolation gate for the cTrader DEMO capture."""
from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from qore.infrastructure.trader_lab import cibo_market_atlas_10y_m5_consumer_v1 as base
from qore.infrastructure.trader_lab import (
    qore_native_demo_eurjpy_usdchf_m5_10y_v1 as capture,
)


def test_frozen_exact_two_fx_symbols_and_source_range() -> None:
    assert capture.SYMBOLS == ("EURJPY", "USDCHF")
    assert capture.SOURCE_SYMBOLS == {"EURJPY": "EURJPY", "USDCHF": "USDCHF"}
    assert capture.EXPECTED_START == "2016-09-17T00:00:00+00:00"
    assert capture.EXPECTED_END_EXCLUSIVE == "2026-09-17T00:00:00+00:00"
    assert "DEMO" in capture.IDENTITY
    assert "M5" in capture.IDENTITY


def test_activated_isolated_identity_uses_no_count_transport(monkeypatch: pytest.MonkeyPatch) -> None:
    mutable = ("PROVIDER_SYMBOL_MAP", "TARGET_SYMBOLS", "IDENTITY",
               "PARENT_IDENTITY", "SCHEMA", "RAW_SCHEMA",
               "QUALITY_SCHEMA", "_read_chunk")
    for attr in mutable:
        monkeypatch.setattr(base, attr, getattr(base, attr))
    original_source = dict(base.PROVIDER_SYMBOL_MAP)
    capture.activate_research_only()
    assert base.PROVIDER_SYMBOL_MAP == capture.SOURCE_SYMBOLS
    assert base.TARGET_SYMBOLS == capture.SYMBOLS
    assert base.IDENTITY == capture.IDENTITY
    assert base.PARENT_IDENTITY == capture.PARENT_IDENTITY
    assert base._read_chunk.__name__ == "read_windowed_chunk"
    assert all(s in original_source for s in ("EURUSD", "GBPUSD"))
    assert ("EURJPY" not in original_source) and ("USDCHF" not in original_source)


def test_fail_closed_if_window_or_period_drift(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(base, "TARGET_START", datetime(2020, 1, 1, tzinfo=UTC))
    with pytest.raises(ValueError, match="source window start"):
        capture.activate_research_only()


def test_no_order_messages_in_source() -> None:
    import inspect

    source = inspect.getsource(capture)
    for prohibited in ("ProtoOANewOrderReq", "ProtoOAClosePositionReq",
                       "ProtoOACancelOrderReq", "ProtoOAModifyOrderReq"):
        assert prohibited not in source
    with patch.object(base, "main") as mocked:
        with patch.object(capture, "activate_research_only"):
            capture.main()
        mocked.assert_called_once()
