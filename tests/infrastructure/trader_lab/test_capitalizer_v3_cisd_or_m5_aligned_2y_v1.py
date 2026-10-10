from datetime import UTC, datetime

from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_v3_cisd_or_m5_aligned_2y_v1 import (
    BASELINE_MAX3_TRADES,
    CLEAN_SAME_BAR_CISD_ONLY,
    CLEAN_SAME_BAR_CISD_ONLY_ALIGNED,
    IDENTITY,
    MATRIX_IDENTITY,
    _confirmation_route_key,
)


def test_cisd_or_m5_contract_is_frozen() -> None:
    assert IDENTITY == "QORE_CAPITALIZER_V3_CISD_OR_M5_ALIGNED_2Y_V1"
    assert MATRIX_IDENTITY == (
        "QORE_CAPITALIZER_NINE_MARKET_V3_CISD_OR_M5_ALIGNED_2Y_V1"
    )
    assert BASELINE_MAX3_TRADES == 474
    assert CLEAN_SAME_BAR_CISD_ONLY == 1298
    assert CLEAN_SAME_BAR_CISD_ONLY_ALIGNED == 925


def test_confirmation_route_key_is_deterministic() -> None:
    closeback = datetime(2026, 9, 22, 10, 5, tzinfo=UTC)
    confirmed = datetime(2026, 9, 22, 10, 18, tzinfo=UTC)

    assert _confirmation_route_key(
        closeback_at=closeback,
        side=CapitalizerSide.LONG,
        confirmed_at=confirmed,
    ) == (
        "2026-09-22T10:05:00+00:00|LONG|"
        "2026-09-22T10:18:00+00:00"
    )
