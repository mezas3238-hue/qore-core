"""Winner and realized-R preservation is matched by source, not by PF alone."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    V49Opportunity,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_v49_v50_g_waterfall_v1 import (
    source_id,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_winner_retention_v1 import (
    _origin,
    _source_table,
    compare_winner_mass,
)
from qore.infrastructure.trader_lab.capitalizer_v49_development_economics import (
    V49EconomicTrade,
)


def _opportunity() -> V49Opportunity:
    decision = datetime(2026, 5, 4, 9, 20, tzinfo=UTC)
    return V49Opportunity(
        symbol="EURUSD", session="LONDON", operating_date="2026-05-04",
        h1_state_direction="BULLISH",
        h1_state_from=(decision - timedelta(hours=1)).isoformat(),
        h1_state_until=(decision + timedelta(hours=3)).isoformat(),
        h1_state_basis="BULLISH_FVG",
        m15_setup_confirmed_at=(decision - timedelta(minutes=5)).isoformat(),
        m15_protected_swing_price="1.101",
        m1_trigger_confirmed_at=decision.isoformat(),
        m1_trigger_family="FVG_RETRACE_CISD",
        decision_reference_price="1.102",
        structural_target_witness_price="1.105",
    )


def _trade(op: V49Opportunity) -> V49EconomicTrade:
    at = datetime.fromisoformat(op.m1_trigger_confirmed_at)
    return V49EconomicTrade(
        symbol=op.symbol,
        session=op.session,
        operating_date=op.operating_date,
        ordinal_candidate_at=at.isoformat(),
        direction="LONG",
        entry_at=at.isoformat(),
        exit_at=(at + timedelta(minutes=3)).isoformat(),
        entry_price=op.decision_reference_price,
        stop_price="1.101",
        target_price="1.105",
        planned_reward_r="3",
        realized_gross_r="3",
        exit_reason="TARGET",
        m1_bars_held=3,
        trigger_family=op.m1_trigger_family,
        h1_state_basis=op.h1_state_basis,
    )


def test_winner_preservation_is_not_unmatched_candidate_win_rate() -> None:
    baseline = {
        "win-a": Decimal("2"),
        "win-b": Decimal("1"),
        "loss": Decimal("-1"),
    }
    candidate = {
        "win-a": Decimal("1.5"),
        "win-b": Decimal("-1"),
        "loss": Decimal("4"),
        "new-win": Decimal("3"),
    }
    result = compare_winner_mass(baseline, candidate)
    assert result["baseline_positive_winners"] == 2
    assert result["candidate_positive_winners"] == 3
    assert result["retained_baseline_winning_source_ids"] == 1
    assert result["winner_count_preservation_ratio"] == "0.5"
    assert result["original_winner_mass_preservation_ratio"] == str(Decimal(2) / 3)
    assert result["candidate_realized_winner_mass_ratio"] == "0.5"
    assert result["new_candidate_winner_ids_not_in_baseline_selected"] == 1
    assert result["passes_80pct_winner_count"] is False
    assert result["passes_90pct_winner_mass"] is False


def test_full_baseline_winner_preservation_does_not_require_equal_profit() -> None:
    result = compare_winner_mass(
        {"a": Decimal(2), "b": Decimal("0.5")},
        {"a": Decimal("0.2"), "b": Decimal(4)},
    )
    assert result["passes_80pct_winner_count"] is True
    assert result["passes_90pct_winner_mass"] is True
    assert result["candidate_realized_winner_mass_ratio"] == "1.68"


def test_zero_baseline_winners_cannot_pass_a_percent_threshold() -> None:
    result = compare_winner_mass(
        {"loss": Decimal("-2")}, {"new-win": Decimal(5)}
    )
    assert result["baseline_positive_winners"] == 0
    assert result["winner_count_preservation_ratio"] is None
    assert result["passes_80pct_winner_count"] is False
    assert result["passes_90pct_winner_mass"] is False


def test_trade_provenance_identifies_source_and_refuses_foreign_or_ambiguous() -> None:
    source = _opportunity()
    trade = _trade(source)
    assert _origin(trade, _source_table((source,))) == source_id(source)
    with pytest.raises(ValueError, match="missing or ambiguous"):
        _origin(replace(trade, entry_price="1.000"), _source_table((source,)))
    # The actual trade fields do not carry the M15 parent identity; if two
    # different parents share a key, the analysis must not select one.
    other = replace(source, m15_protected_swing_price="1.100")
    with pytest.raises(ValueError, match="missing or ambiguous"):
        _origin(trade, _source_table((source, other)))
