from __future__ import annotations

from types import SimpleNamespace

import pytest

from qore.infrastructure.ctrader_demo_lab_probe import CTraderDemoLabProbeError
from qore.infrastructure.trader_lab.turtle_soup_candidate_r5_classic_tick_probe import (
    _decode_tick_page,
)
from qore.infrastructure.trader_lab.turtle_soup_candidate_r5_classic_tick_targets import (
    frozen_tick_target_manifest,
)


def test_r5_tick_target_manifest_is_frozen_to_293_pre_oos_minutes() -> None:
    manifest = frozen_tick_target_manifest()
    assert manifest["manifest_digest_sha256"] == (
        "4923fe9eb2d85416e69d03a4514ebe92bda4a2e277c73ca1e70df5f1cd6bc27f"
    )
    assert manifest["target_count"] == 293
    targets = manifest["targets"]
    assert isinstance(targets, dict)
    assert {symbol: len(rows) for symbol, rows in targets.items()} == {
        "EURUSD": 40,
        "GBPUSD": 47,
        "USDJPY": 35,
        "AUDUSD": 43,
        "USDCAD": 43,
        "GBPJPY": 44,
        "AUDJPY": 41,
    }
    assert all(
        row["side"] in {"long", "short"}
        for rows in targets.values()
        for row in rows
    )


def test_tick_page_decodes_newest_first_absolute_then_delta_timestamps() -> None:
    page = _decode_tick_page(
        (
            SimpleNamespace(timestamp=1_700_000_000_500, tick=123456),
            SimpleNamespace(timestamp=125, tick=123450),
            SimpleNamespace(timestamp=375, tick=123440),
        ),
        digits=5,
    )
    assert [item.timestamp_ms for item in page] == [
        1_700_000_000_500,
        1_700_000_000_375,
        1_700_000_000_000,
    ]
    assert [item.price for item in page] == ["1.23456", "1.23450", "1.23440"]


def test_tick_page_rejects_negative_delta() -> None:
    with pytest.raises(CTraderDemoLabProbeError):
        _decode_tick_page(
            (
                SimpleNamespace(timestamp=1_700_000_000_500, tick=123456),
                SimpleNamespace(timestamp=-1, tick=123450),
            ),
            digits=5,
        )
