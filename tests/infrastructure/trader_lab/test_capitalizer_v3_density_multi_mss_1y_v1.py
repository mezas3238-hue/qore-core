from datetime import UTC, datetime

from qore.infrastructure.trader_lab.capitalizer_v3_density_multi_mss_1y_v1 import (
    IDENTITY,
    MATRIX_IDENTITY,
    STOP_IDENTITY,
    TARGET_IDENTITY,
    _find_all_m3_mss,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide


def test_density_multi_mss_keeps_v3_economic_contract() -> None:
    assert IDENTITY == "QORE_CAPITALIZER_V3_DENSITY_MULTI_MSS_1Y_V1"
    assert MATRIX_IDENTITY == "QORE_CAPITALIZER_NINE_MARKET_V3_DENSITY_MULTI_MSS_1Y_V1"
    assert STOP_IDENTITY == "M3_BROKEN_SWING_PLUS_5_PIP_BUFFER"
    assert TARGET_IDENTITY == "FIXED_2R_OR_NEXT_H1_OPEN"


def test_multi_mss_empty_window_is_empty() -> None:
    now = datetime(2026, 9, 22, tzinfo=UTC)
    assert _find_all_m3_mss(
        (),
        (),
        (),
        after=now,
        before=now,
        side=CapitalizerSide.LONG,
    ) == ()
