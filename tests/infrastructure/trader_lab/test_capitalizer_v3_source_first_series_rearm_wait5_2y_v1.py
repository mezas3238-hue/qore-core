from typing import cast

from qore.infrastructure.trader_lab import (
    capitalizer_v3_source_first_series_rearm_wait5_2y_v1 as candidate,
)
from qore.infrastructure.trader_lab.capitalizer_owner_h1_m3_m1_causal_reversal_1y_v3 import (
    V3Trade,
)


def test_series_rearm_wait5_contract_is_frozen() -> None:
    assert candidate.IDENTITY == (
        "QORE_CAPITALIZER_V3_SOURCE_FIRST_SERIES_REARM_WAIT5_2Y_V1"
    )
    assert candidate.MATRIX_IDENTITY == (
        "QORE_CAPITALIZER_NINE_MARKET_V3_SOURCE_FIRST_SERIES_REARM_WAIT5_2Y_V1"
    )
    assert candidate.WAIT5_BASELINE_RAW == 1003
    assert candidate.WAIT5_BASELINE_MAX3 == 983
    assert vars(candidate)["BOUNDARY_SEMANTICS"] == (
        "FIRST_OPPOSING_OPEN_PER_DISTINCT_POST_SWEEP_SERIES"
    )


def test_trade_key_is_deterministic() -> None:
    class Trade:
        symbol = "NAS100"
        session = "NEW_YORK"
        operating_date = "2026-01-03"
        side = "LONG"
        entry_at = "2026-01-03T15:31:00+00:00"

    assert candidate._trade_key(cast(V3Trade, Trade())) == (
        "NAS100",
        "NEW_YORK",
        "2026-01-03",
        "LONG",
        "2026-01-03T15:31:00+00:00",
    )
