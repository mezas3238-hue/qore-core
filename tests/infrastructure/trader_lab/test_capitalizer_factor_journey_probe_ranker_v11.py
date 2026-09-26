from __future__ import annotations

from qore.infrastructure.trader_lab import (
    capitalizer_causal_probe_ranker_v10 as v10,
)
from qore.infrastructure.trader_lab import (
    capitalizer_factor_journey_probe_ranker_v11 as lab,
)


def test_exposure_graph_preserves_fx_leg_direction() -> None:
    long_eurusd = lab._factor_map(symbol="EURUSD", side="LONG")
    long_gbpusd = lab._factor_map(symbol="GBPUSD", side="LONG")
    assert long_eurusd["USD"].net_r < 0
    assert long_gbpusd["USD"].net_r < 0


def test_v11_reuses_v10_pretrade_as_base() -> None:
    assert lab._BASE_PRETRADE is v10._pretrade


def test_strict_oos_contract_is_unchanged() -> None:
    assert v10.STRICT_OOS_PERIODS == (
        "CONSUMED_VALIDATION_2022_2024",
        "CONSUMED_RESERVED_2020_2022",
    )


def test_session_order_is_causal() -> None:
    assert lab.SESSION_ORDER == {
        "ASIA": 0,
        "LONDON": 1,
        "NEW_YORK": 2,
    }
