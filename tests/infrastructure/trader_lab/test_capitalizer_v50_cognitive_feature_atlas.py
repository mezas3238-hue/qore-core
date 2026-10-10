import json
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path

from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    V49Opportunity,
)
from qore.infrastructure.trader_lab.capitalizer_v49_development_economics import (
    V49EconomicTrade,
)
from qore.infrastructure.trader_lab.capitalizer_v50_cognitive_feature_atlas import (
    _load_opportunities,
    _load_outcomes,
)


def test_atlas_loaders_keep_outcome_separate_from_candidate(tmp_path: Path) -> None:
    entry = datetime(2026, 1, 5, 10, 5, tzinfo=UTC)
    opportunity = V49Opportunity(
        symbol="EURUSD",
        session="LONDON",
        operating_date="2026-01-05",
        h1_state_direction="BULLISH",
        h1_state_from=(entry - timedelta(minutes=30)).isoformat(),
        h1_state_until=(entry + timedelta(hours=2)).isoformat(),
        h1_state_basis="CANDLE2_REVERSAL:BULLISH_FVG",
        m15_setup_confirmed_at=(entry - timedelta(minutes=5)).isoformat(),
        m15_protected_swing_price="99",
        m1_trigger_confirmed_at=entry.isoformat(),
        m1_trigger_family="FVG_RETRACE_CISD",
        decision_reference_price="100",
        structural_target_witness_price="101",
    )
    capacity = tmp_path / "capitalizer-eurusd-v49-hf-capacity-opportunities.jsonl"
    capacity.write_text(json.dumps(asdict(opportunity)) + "\n", encoding="utf-8")

    outcome = V49EconomicTrade(
        symbol="EURUSD",
        session="LONDON",
        operating_date="2026-01-05",
        ordinal_candidate_at=entry.isoformat(),
        direction="LONG",
        entry_at=entry.isoformat(),
        exit_at=(entry + timedelta(minutes=10)).isoformat(),
        entry_price="100",
        stop_price="99",
        target_price="101",
        planned_reward_r="1",
        realized_gross_r="-1",
        exit_reason="STOP",
        m1_bars_held=10,
        trigger_family="FVG_RETRACE_CISD",
        h1_state_basis="CANDLE2_REVERSAL:BULLISH_FVG",
    )
    economic = tmp_path / "capitalizer-eurusd-v49-development-economics-trades.jsonl"
    economic.write_text(json.dumps(asdict(outcome)) + "\n", encoding="utf-8")

    opportunities = _load_opportunities(tmp_path)
    outcomes = _load_outcomes(tmp_path)
    assert opportunities == (opportunity,)
    assert outcomes[("EURUSD", entry.isoformat())].realized_gross_r == "-1"
    assert opportunity.outcome_used is False
