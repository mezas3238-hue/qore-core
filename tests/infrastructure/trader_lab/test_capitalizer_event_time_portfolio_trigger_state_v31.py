from __future__ import annotations

from datetime import UTC, datetime

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_r_milestone_protection_2r_v1 as milestone,
)
from qore.infrastructure.trader_lab import (
    capitalizer_event_time_portfolio_trigger_state_v31 as v31,
)
from qore.infrastructure.trader_lab import (
    capitalizer_first_intervention_cross_trigger_optionality_v30 as v30,
)


def _trade(
    *,
    symbol: str,
    session: str = "LONDON",
    operating_date: str = "2026-01-05",
    side: str = "LONG",
    entry_at: str = "2026-01-05T08:00:00+00:00",
    exit_at: str = "2026-01-05T09:00:00+00:00",
    realized_r: str = "1",
) -> milestone.SimulatedTrade:
    return milestone.SimulatedTrade(
        symbol=symbol,
        session=session,
        operating_date=operating_date,
        side=side,
        entry_at=entry_at,
        exit_at=exit_at,
        entry_price="100",
        original_stop_price="99",
        final_stop_price="99",
        target_price="102",
        realized_gross_r=realized_r,
        exit_reason="TIME_EXIT",
        mode="ORIGINAL",
        protection_updates=0,
        first_protection_at=None,
        max_milestone_r_seen_before_exit="1",
        same_minute_stop_target_ambiguity=False,
    )


def test_same_timestamp_active_peer_outcome_is_invisible() -> None:
    current = _trade(symbol="EURUSD")
    observed = datetime(2026, 1, 5, 8, 30, tzinfo=UTC)
    peer_positive = _trade(
        symbol="GBPUSD",
        entry_at="2026-01-05T07:50:00+00:00",
        exit_at="2026-01-05T08:30:00+00:00",
        realized_r="10",
    )
    peer_negative = _trade(
        symbol="GBPUSD",
        entry_at="2026-01-05T07:50:00+00:00",
        exit_at="2026-01-05T08:30:00+00:00",
        realized_r="-10",
    )

    positive = v31._portfolio_vector(
        current_trade=current,
        observed_at=observed,
        projections=(peer_positive,),
    )
    negative = v31._portfolio_vector(
        current_trade=current,
        observed_at=observed,
        projections=(peer_negative,),
    )

    assert positive == negative
    assert positive[9] == 1.0
    assert positive[0] == 0.0


def test_strictly_prior_close_changes_realized_portfolio_state() -> None:
    current = _trade(symbol="EURUSD")
    observed = datetime(2026, 1, 5, 8, 30, tzinfo=UTC)
    prior_loss = _trade(
        symbol="GBPUSD",
        entry_at="2026-01-05T07:40:00+00:00",
        exit_at="2026-01-05T08:29:00+00:00",
        realized_r="-1.25",
    )

    vector = v31._portfolio_vector(
        current_trade=current,
        observed_at=observed,
        projections=(prior_loss,),
    )

    assert vector[0] == 1.25
    assert vector[1] == -1.25
    assert vector[2] == -1.25
    assert vector[3] == -1.25
    assert vector[4] == 1.0
    assert vector[5] == 1.0
    assert vector[6] == -1.25
    assert vector[7] == 1.0
    assert vector[9] == 0.0


def test_active_factor_features_do_not_read_realized_r() -> None:
    current = _trade(symbol="EURUSD", side="LONG")
    observed = datetime(2026, 1, 5, 8, 30, tzinfo=UTC)
    aligned_a = _trade(
        symbol="GBPUSD",
        side="LONG",
        entry_at="2026-01-05T08:10:00+00:00",
        exit_at="2026-01-05T09:00:00+00:00",
        realized_r="50",
    )
    aligned_b = _trade(
        symbol="GBPUSD",
        side="LONG",
        entry_at="2026-01-05T08:10:00+00:00",
        exit_at="2026-01-05T09:00:00+00:00",
        realized_r="-50",
    )

    first = v31._portfolio_vector(
        current_trade=current,
        observed_at=observed,
        projections=(aligned_a,),
    )
    second = v31._portfolio_vector(
        current_trade=current,
        observed_at=observed,
        projections=(aligned_b,),
    )

    assert first == second
    assert first[11] >= 1.0
    assert first[12] > 0.0


def test_next_event_time_orders_entry_and_trigger_chronologically() -> None:
    row = _trade(symbol="EURUSD")
    ordered = (row,)
    trigger_time = datetime(2026, 1, 5, 8, 5, tzinfo=UTC)

    assert v31._next_event_time(
        ordered=ordered,
        pointer=0,
        pending={("GBPUSD", "2026-01-05T07:00:00+00:00"): (
            trigger_time,
            "TRIGGER_050",
        )},
    ) == datetime(2026, 1, 5, 8, 0, tzinfo=UTC)

    assert v31._next_event_time(
        ordered=ordered,
        pointer=1,
        pending={("GBPUSD", "2026-01-05T07:00:00+00:00"): (
            trigger_time,
            "TRIGGER_050",
        )},
    ) == trigger_time


def test_v31_frozen_contract() -> None:
    assert v31.IDENTITY == (
        "QORE_CAPITALIZER_EVENT_TIME_PORTFOLIO_TRIGGER_STATE_V31"
    )
    assert v31.POLICY == (
        "FIRST_INTERVENTION_ROBUST_EVENT_TIME_PORTFOLIO_STATE"
    )
    assert v31.L2_PRIOR_STRENGTH == 12.0
    assert v31.SOURCE_TRIGGER_STATE_RUN_ID == 36283499014
    assert v31.EVENT_PORTFOLIO_FEATURE_DIMENSION == 20
    assert len(v31.EVENT_PORTFOLIO_FEATURES) == 20
    assert v31.EXPECTED_FEATURE_DIMENSION == 95
    assert len(v30._eligible_actions(v30.FAMILY_050)) == 9
    assert len(v30._eligible_actions(v30.FAMILY_075)) == 7
    assert len(v30._eligible_actions(v30.FAMILY_100)) == 4
