from __future__ import annotations

from types import SimpleNamespace

import pytest

from qore.infrastructure.ctrader_demo_lab_probe import CTraderDemoLabProbeError
from qore.infrastructure.trader_lab.turtle_soup_candidate_r5_classic_tick_runtime import (
    _decode_tick_page_with_signed_deltas,
)
from qore.infrastructure.trader_lab.turtle_soup_candidate_r5_classic_tick_targets import (
    frozen_tick_target_manifest,
)


def test_r5_tick_target_manifest_is_frozen_to_293_pre_oos_ambiguous_minutes() -> None:
    manifest = frozen_tick_target_manifest()
    assert manifest["manifest_digest_sha256"] == (
        "a960c0f34392b0fdd8e18963a275b8524e23c9ca4cd554e2c073d3826b428c7c"
    )
    assert manifest["target_count"] == 293
    assert manifest["m1_data_unavailable_count"] == 3
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


def test_tick_page_decodes_provider_timestamp_and_price_deltas_cumulatively() -> None:
    page = _decode_tick_page_with_signed_deltas(
        (
            SimpleNamespace(timestamp=1_700_000_000_500, tick=123456),
            SimpleNamespace(timestamp=-125, tick=-6),
            SimpleNamespace(timestamp=-375, tick=-10),
        ),
        digits=5,
    )
    assert [item.timestamp_ms for item in page] == [
        1_700_000_000_500,
        1_700_000_000_375,
        1_700_000_000_000,
    ]
    assert [item.price for item in page] == ["1.23456", "1.23450", "1.23440"]


def test_tick_page_preserves_equal_timestamp_and_signed_price_move() -> None:
    page = _decode_tick_page_with_signed_deltas(
        (
            SimpleNamespace(timestamp=1_700_000_000_500, tick=123456),
            SimpleNamespace(timestamp=0, tick=4),
        ),
        digits=5,
    )
    assert [item.timestamp_ms for item in page] == [
        1_700_000_000_500,
        1_700_000_000_500,
    ]
    assert [item.price for item in page] == ["1.23456", "1.23460"]


def test_tick_page_rejects_positive_timestamp_delta_in_newest_first_stream() -> None:
    with pytest.raises(CTraderDemoLabProbeError):
        _decode_tick_page_with_signed_deltas(
            (
                SimpleNamespace(timestamp=1_700_000_000_500, tick=123456),
                SimpleNamespace(timestamp=1, tick=-1),
            ),
            digits=5,
        )
