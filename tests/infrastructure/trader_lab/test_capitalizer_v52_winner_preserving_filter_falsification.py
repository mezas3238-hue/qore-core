from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_v49_development_economics import (
    V49EconomicTrade,
)
from qore.infrastructure.trader_lab.capitalizer_v50_cognitive_feature_atlas import (
    V50CognitiveFeatureRow,
)
from qore.infrastructure.trader_lab.capitalizer_v52_winner_preserving_filter_falsification import (
    EXPECTANCY_MIN_EXCLUSIVE,
    PF_EXISTENCE_MIN_EXCLUSIVE,
    WINNER_COUNT_PRESERVATION_MIN,
    WINNER_R_PRESERVATION_MIN,
    _portfolio,
    _preservation,
)


def test_v52_thresholds_match_research_contract() -> None:
    assert WINNER_COUNT_PRESERVATION_MIN == Decimal("0.80")
    assert WINNER_R_PRESERVATION_MIN == Decimal("0.90")
    assert PF_EXISTENCE_MIN_EXCLUSIVE == Decimal("1")
    assert EXPECTANCY_MIN_EXCLUSIVE == Decimal("0")


def _trade(entry_at: str, realized_r: str) -> V49EconomicTrade:
    return V49EconomicTrade(
        symbol="EURUSD",
        session="LONDON",
        operating_date="2026-01-05",
        ordinal_candidate_at=entry_at,
        direction="LONG",
        entry_at=entry_at,
        exit_at=entry_at,
        entry_price="1.10",
        stop_price="1.09",
        target_price="1.12",
        planned_reward_r="2",
        realized_gross_r=realized_r,
        exit_reason="TARGET" if Decimal(realized_r) > 0 else "STOP",
        m1_bars_held=1,
        trigger_family="FVG_RETRACE_CISD",
        h1_state_basis="TEST",
    )


def _atlas(entry_at: str, *, stop_noise_state: str) -> V50CognitiveFeatureRow:
    return V50CognitiveFeatureRow(
        identity="QORE_CAPITALIZER_V50_COGNITIVE_FEATURE_ATLAS",
        symbol="EURUSD",
        session="LONDON",
        operating_date="2026-01-05",
        entry_at=entry_at,
        exit_at=entry_at,
        state_family_id="TEST_STATE",
        observation_tokens=(),
        structural_disposition="PASS_TO_COMPETITION",
        h1_freshness="FRESH",
        execution_freshness="FRESH",
        session_runway="AMPLE",
        stop_noise_state=stop_noise_state,
        stop_to_noise_ratio="2",
        destination_state="VALID",
        current_destination_room_r="2",
        target_candidate_count=1,
        target_has_one_r=True,
        target_has_two_r=True,
        execution_stop_available=True,
        execution_vs_thesis_ratio="0.5",
        trigger_family="FVG_RETRACE_CISD",
        h1_basis="TEST",
        candidate_ordinal_in_session_day=1,
        realized_gross_r="0",
        exit_reason="UNUSED_LABEL",
    )


def test_v52_recompetition_replaces_blocked_early_slot_causally() -> None:
    times = tuple(f"2026-01-05T10:0{i}:00+00:00" for i in range(4))
    trades = (
        _trade(times[0], "-1"),
        _trade(times[1], "2"),
        _trade(times[2], "1"),
        _trade(times[3], "3"),
    )
    atlas = {
        ("EURUSD", times[0]): _atlas(times[0], stop_noise_state="BLOCK"),
        ("EURUSD", times[1]): _atlas(times[1], stop_noise_state="KEEP"),
        ("EURUSD", times[2]): _atlas(times[2], stop_noise_state="KEEP"),
        ("EURUSD", times[3]): _atlas(times[3], stop_noise_state="KEEP"),
    }

    baseline = _portfolio(trades, atlas)
    candidate = _portfolio(
        trades,
        atlas,
        blocked_field="stop_noise_state",
        blocked_value="BLOCK",
    )

    assert tuple(item.entry_at for item in baseline) == times[:3]
    assert tuple(item.entry_at for item in candidate) == times[1:]
    preservation = _preservation(baseline, candidate)
    assert Decimal(preservation["winner_count_preservation"]) == Decimal("1")
    assert Decimal(preservation["winner_r_preservation"]) == Decimal("1")
    assert Decimal(preservation["loss_recall"]) == Decimal("1")
    assert preservation["new_recompetition_entries"] == 1
