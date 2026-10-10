from typing import cast

from qore.infrastructure.trader_lab import (
    capitalizer_v3_source_first_wait5_fvg_lag2_fresh_holdout_2y_v1 as holdout,
)
from qore.infrastructure.trader_lab.capitalizer_owner_h1_m3_m1_causal_reversal_1y_v3 import (
    V3Trade,
)


def test_fvg_lag2_holdout_contract_is_frozen() -> None:
    assert holdout.IDENTITY == (
        "QORE_CAPITALIZER_V3_SOURCE_FIRST_WAIT5_FVG_LAG2_"
        "FRESH_HOLDOUT_2Y_V1"
    )
    assert holdout.HOLDOUT_START.isoformat() == "2022-09-17T00:00:00+00:00"
    assert holdout.HOLDOUT_END.isoformat() == "2024-09-17T00:00:00+00:00"
    assert holdout.DEVELOPMENT_START.isoformat() == "2024-09-17T00:00:00+00:00"
    assert holdout.HOLDOUT_END <= holdout.DEVELOPMENT_START


def test_holdout_trade_key_is_deterministic() -> None:
    class Trade:
        symbol = "NAS100"
        session = "NEW_YORK"
        operating_date = "2023-01-03"
        side = "LONG"
        entry_at = "2023-01-03T15:31:00+00:00"

    assert holdout._trade_key(cast(V3Trade, Trade())) == (
        "NAS100",
        "NEW_YORK",
        "2023-01-03",
        "LONG",
        "2023-01-03T15:31:00+00:00",
    )
