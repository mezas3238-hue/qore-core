"""Synthetic fixtures: target R arithmetic and identity are not target optimization."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    V49Opportunity,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_h1_target_asymmetry_audit_v1 import (
    _source_matches,
    report_source_target_geometry,
)
from qore.infrastructure.trader_lab.capitalizer_v49_development_economics import (
    V49EconomicTrade,
)

START = datetime(2026, 3, 12, 10, tzinfo=UTC)


def _source(symbol: str, ordinal: int, target: str) -> V49Opportunity:
    now = START + timedelta(minutes=ordinal * 3)
    return V49Opportunity(
        symbol=symbol, session="LONDON", operating_date="2026-03-12",
        h1_state_direction="BULLISH",
        h1_state_from=(START - timedelta(hours=1)).isoformat(),
        h1_state_until=(START + timedelta(hours=2)).isoformat(),
        h1_state_basis="H1_C2",
        m15_setup_confirmed_at=(START - timedelta(minutes=10)).isoformat(),
        m15_protected_swing_price="99",
        m1_trigger_confirmed_at=now.isoformat(),
        m1_trigger_family=(
            "FVG_RETRACE_CISD" if ordinal % 2 else "LIQUIDITY_SWEEP_CISD"
        ),
        decision_reference_price="100",
        structural_target_witness_price=target,
    )


def _trade(source: V49Opportunity, exit_reason: str, realized: str) -> V49EconomicTrade:
    start = datetime.fromisoformat(source.m1_trigger_confirmed_at)
    rr = (Decimal(source.structural_target_witness_price) - Decimal("100"))
    return V49EconomicTrade(
        symbol=source.symbol, session=source.session,
        operating_date=source.operating_date,
        ordinal_candidate_at=start.isoformat(), direction="LONG",
        entry_at=start.isoformat(),
        exit_at=(start + timedelta(minutes=2)).isoformat(),
        entry_price=source.decision_reference_price,
        stop_price=source.m15_protected_swing_price,
        target_price=source.structural_target_witness_price,
        planned_reward_r=str(rr),
        realized_gross_r=realized,
        exit_reason=exit_reason, m1_bars_held=2,
        trigger_family=source.m1_trigger_family,
        h1_state_basis=source.h1_state_basis,
    )


def test_actual_target_exit_is_full_witness_reward_not_partial() -> None:
    s = _source("EURUSD", 0, "100.4")
    row = _source_matches(s, _trade(s, "TARGET", "0.4"))
    assert row.full_target_exit_no_partials is True
    assert Decimal(row.planned_target_r) == Decimal("0.4")
    assert Decimal(row.m15_stop_risk_price) == 1
    assert Decimal(row.h1_destination_distance_price) == Decimal("0.4")


def test_planned_r_thresholds_show_low_payoff_even_on_target() -> None:
    sources = (
        _source("EURUSD", 0, "100.25"),
        _source("EURUSD", 1, "100.4"),
        _source("GBPUSD", 2, "102"),
        _source("GBPUSD", 3, "101"),
    )
    outcomes = (
        _trade(sources[0], "TARGET", "0.25"),
        _trade(sources[1], "TARGET", "0.4"),
        _trade(sources[2], "STOP", "-1"),
        _trade(sources[3], "SESSION_EXIT", "-0.15"),
    )
    report, rows = report_source_target_geometry(
        sources, outcomes, expected_markets=2
    )
    assert report["source_opportunities"] == 4
    assert report["selected_after_max3"] == 3
    assert report["selected"]["target_exits"] == 2
    assert report["selected"]["target_exits_mean_realized_r"] == "0.325"
    assert report["selected"]["planned_target_r_below"]["1"] == 2
    assert report["selected"]["target_exits_planned_r_below_one"] == 2
    assert report["h1_target_witness_independently_replayed_with_m1"] is False
    assert not report["live_authorized"]
    assert len(rows) == 4


@pytest.mark.parametrize(
    ("changes", "pattern"),
    [
        ({"stop_price": "98"}, "stop/target identity mismatch"),
        ({"target_price": "100.9"}, "stop/target identity mismatch"),
        ({"planned_reward_r": "2"}, "planned reward R"),
        ({"realized_gross_r": "0.1"}, "full target exit"),
        ({"direction": "SHORT"}, "direction disagree"),
        ({"trigger_family": "UNKNOWN"}, "stop/target identity mismatch"),
    ],
)
def test_economic_replay_cannot_silently_relabel_source(
    changes: dict[str, str], pattern: str
) -> None:
    s = _source("EURUSD", 0, "100.4")
    with pytest.raises(ValueError, match=pattern):
        _source_matches(s, replace(_trade(s, "TARGET", "0.4"), **changes))


def test_audit_rejects_missing_and_duplicate_trades() -> None:
    s = _source("EURUSD", 0, "100.4")
    t = _trade(s, "TARGET", "0.4")
    with pytest.raises(ValueError, match="same source twice|multiple times"):
        report_source_target_geometry((s,), (t, t), expected_markets=1)
    with pytest.raises(ValueError, match="not complete"):
        report_source_target_geometry((s,), (), expected_markets=1)


def test_legacy_source_target_is_not_conflated_with_h1_pivot() -> None:
    s = _source("EURUSD", 0, "100.4")
    report, _ = report_source_target_geometry(
        (s,), (_trade(s, "TARGET", "0.4"),), expected_markets=1
    )
    assert report["target_source"] == "V49_CAUSAL_H1_CANDLE_HIGH_LOW_WITNESS"
    assert report["cannot_claim_h1_swing_pivot_confirmation"] is True
