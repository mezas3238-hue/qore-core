from __future__ import annotations

from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import (
    Model1LabTrade,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2j_market_context_validation import (
    CandidateId,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2m_survivor_robustness import (
    COST_STRESS_R,
    START_SUBWINDOWS,
    SURVIVORS,
    _stress_summary,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket


def _trade(r_multiple: float, opened_at: str) -> Model1LabTrade:
    return Model1LabTrade(
        schema="test",
        identity="test",
        market="AUDUSD",
        reference_policy="UNTOUCHED_SWING_STRENGTH_1",
        reference_count=1,
        reference_ids=("ref",),
        parent_direction="BULLISH",
        timing_triplet="1",
        c3_opened_at=opened_at,
        source_opened_at=opened_at,
        confirmation_opened_at=opened_at,
        entry_opened_at=opened_at,
        entry_price_relative=100,
        stop_price_relative=90,
        target_price_relative="110",
        exit_price_relative="110",
        exit_reason="TARGET_50",
        r_multiple=r_multiple,
    )


def test_r2m_survivor_family_is_frozen_from_r2j() -> None:
    assert SURVIVORS[CrtPureMarket.AUDUSD] == (CandidateId.AUD_G1,)
    assert SURVIVORS[CrtPureMarket.BTCUSD] == (
        CandidateId.CONTROL,
        CandidateId.BTC_BEARISH,
        CandidateId.BTC_BODY_GE_050,
        CandidateId.BTC_REF2_PLUS,
    )


def test_r2m_stress_family_is_frozen() -> None:
    assert COST_STRESS_R == (0.02, 0.05, 0.10)
    assert tuple(label for label, _, _ in START_SUBWINDOWS) == (
        "Y2022_23",
        "Y2023_24",
        "Y2024_25",
        "Y2025_26",
        "ROLL2_2022_24",
        "ROLL2_2023_25",
        "ROLL2_2024_26",
    )


def test_cost_perturbation_reduces_every_trade_deterministically() -> None:
    rows = (
        _trade(1.0, "2024-01-01T00:00:00+00:00"),
        _trade(-1.0, "2024-01-02T00:00:00+00:00"),
        _trade(0.5, "2024-01-03T00:00:00+00:00"),
    )

    base = _stress_summary(rows, 0.0)
    stressed = _stress_summary(rows, 0.10)

    assert base["total_r"] == 0.5
    assert stressed["total_r"] == 0.2
    assert stressed["mean_r"] < base["mean_r"]
    assert stressed["max_drawdown_r"] >= base["max_drawdown_r"]
