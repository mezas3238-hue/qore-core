from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_r_milestone_protection_2r_v1 as milestone,
)
from qore.infrastructure.trader_lab import capitalizer_exposure_graph as exposure

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


def _trade(
    symbol: str,
    side: str,
    *,
    entry_at: str = "2026-01-01T15:00:00+00:00",
    exit_at: str = "2026-01-01T16:00:00+00:00",
) -> milestone.SimulatedTrade:
    return milestone.SimulatedTrade(
        symbol=symbol,
        session="NEW_YORK",
        operating_date="2026-01-01",
        side=side,
        entry_at=entry_at,
        exit_at=exit_at,
        entry_price="100",
        original_stop_price="99",
        final_stop_price="99",
        target_price="102",
        realized_gross_r="2",
        exit_reason="TARGET",
        mode="ORIGINAL",
        protection_updates=0,
        first_protection_at=None,
        max_milestone_r_seen_before_exit="2",
        same_minute_stop_target_ambiguity=False,
    )


def test_same_timestamp_peer_is_not_prior_active_exposure() -> None:
    current = _trade("GBPUSD", "LONG")
    peer = _trade("EURUSD", "LONG")
    assert lab._active_trades((peer,), entry_at=current.entry_at) == ()


def test_exact_timestamp_competition_sees_factor_alignment_and_conflict() -> None:
    current = _trade("GBPUSD", "LONG")
    aligned = _trade("EURUSD", "LONG")
    opposed = _trade("USDCAD", "LONG")
    key = ("P", current.session, current.entry_at)
    before = dict(lab._SIMULTANEOUS)
    try:
        lab._SIMULTANEOUS.clear()
        lab._SIMULTANEOUS[key] = (current, aligned, opposed)
        features = lab._competition_features(period="P", trade=current)
    finally:
        lab._SIMULTANEOUS.clear()
        lab._SIMULTANEOUS.update(before)

    peer_count, same_factor, aligned_count, opposed_count, shared = features
    assert peer_count > 0
    assert same_factor > 0
    assert aligned_count > 0
    assert opposed_count > 0
    assert shared > 0


def test_open_factor_exposure_does_not_read_active_trade_outcome() -> None:
    current = _trade("GBPUSD", "LONG", entry_at="2026-01-01T15:30:00+00:00")
    active = _trade(
        "EURUSD",
        "LONG",
        entry_at="2026-01-01T15:00:00+00:00",
        exit_at="2026-01-01T16:00:00+00:00",
    )
    altered = replace(active, realized_gross_r="-999")
    assert lab._factor_features((active,), trade=current) == lab._factor_features(
        (altered,),
        trade=current,
    )


def test_unit_exposure_is_explicitly_structural_not_capital_sizing() -> None:
    position = exposure.CapitalizerExposurePosition(
        symbol="EURUSD",
        side=exposure.CapitalizerSide.LONG,
        risk_r=Decimal("1"),
    )
    assert position.risk_r == Decimal("1")
