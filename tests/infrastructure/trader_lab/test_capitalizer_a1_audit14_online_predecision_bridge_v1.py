"""Audit14 -> A1 outcome isolation and causal source identity regression tests.

Fixture-only; never claim a nine-market historical test or physical fills.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from qore.infrastructure.trader_lab.capitalizer_a1_audit14_online_predecision_bridge_v1 import (
    AUDIT14_FIELDS,
    reconcile_audit14_online_witnesses,
    safe_witness_dict,
    sanitize_audit14_row,
)
from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    V49Opportunity,
)
from qore.infrastructure.trader_lab.capitalizer_v50_g_causal_decision_trace import (
    source_opportunity_id,
)

AT = datetime(2026, 1, 5, 10, tzinfo=UTC)


def _src() -> V49Opportunity:
    return V49Opportunity(
        symbol="AUDJPY", session="ASIA", operating_date="2026-01-05",
        h1_state_direction="BULLISH", h1_state_from=(AT-timedelta(hours=2)).isoformat(),
        h1_state_until=(AT+timedelta(hours=1)).isoformat(),
        h1_state_basis="CANDLE2_REVERSAL",
        m15_setup_confirmed_at=(AT-timedelta(minutes=30)).isoformat(),
        m15_protected_swing_price="98",
        m1_trigger_confirmed_at=AT.isoformat(),
        m1_trigger_family="LIQUIDITY_SWEEP_CISD",
        decision_reference_price="100.2",
        structural_target_witness_price="101",
    )


def _row(source: V49Opportunity) -> dict[str, Any]:
    return {
        "source_opportunity_id": source_opportunity_id(source),
        "symbol": source.symbol, "session": source.session,
        "operating_date": source.operating_date,
        "v49_entry_at": source.m1_trigger_confirmed_at,
        "online_entry_at": (AT-timedelta(minutes=15)).isoformat(),
        "online_family": "FVG_RETRACE_CISD",
        "source_family": source.m1_trigger_family,
        "frozen_381": True,
        "first_online_differs": True,
        "status": "ELIGIBLE",
        "rejection_is_diagnostic_not_a_hard_veto": False,
        "original_gross_r": "-1",
        "candidate_gross_r": "0.5",
        "candidate_entry_price": "100",
        "candidate_stop_price": source.m15_protected_swing_price,
        "candidate_target_price": "101",
        "candidate_exit_reason": "TARGET",
        "session_at_online": source.session,
        "source_anchored_H1_M15_not_regenerated": True,
        "source_author_POI_not_independently_certified": True,
        "physical_bid_ask_available": False,
    }


def test_whitelist_and_future_results_cannot_reach_master_frame() -> None:
    source = _src()
    original = _row(source)
    assert set(original) == AUDIT14_FIELDS
    witness = sanitize_audit14_row(original=source, raw=original)
    output = safe_witness_dict(witness)
    assert witness.source_opportunity_id == source_opportunity_id(source)
    assert witness.online_family == "FVG_RETRACE_CISD"
    assert witness.online_decision_at < witness.original_decision_at
    assert "gross" not in str(output).lower()
    assert "exit_reason" not in str(output).lower()
    assert "h1_state_until" not in output
    assert not witness.full_master_frame_invoked
    assert not witness.source_h1_m15_regenerated
    assert not witness.broker_bid_ask_verified
    changed = {**original, "original_gross_r": "123456789R",
               "candidate_gross_r": "-99999R",
               "candidate_exit_reason": "MAGIC_WINNER"}
    assert sanitize_audit14_row(original=source, raw=changed) == witness


def test_full_universe_census_is_not_claimed_by_three_fixtures() -> None:
    source = _src()
    witnesses, report = reconcile_audit14_online_witnesses(
        originals=(source,), rows=(_row(source),), full_nine_market=False,
    )
    assert len(witnesses) == 1
    assert report["source_ids_reconciled"] == 1
    assert report["paper_trades_executed"] == 0
    assert report["master_frame_invoked"] is False
    assert report["ex_post_outcomes_forwarded"] is False
    with pytest.raises(ValueError, match="2876-source"):
        reconcile_audit14_online_witnesses(originals=(source,), rows=(_row(source),))


def test_future_or_pre_m15_decisions_fail_closed() -> None:
    source = _src()
    row = _row(source)
    with pytest.raises(ValueError, match="future M1"):
        sanitize_audit14_row(
            original=source, raw={
                **row, "online_entry_at": (AT+timedelta(minutes=1)).isoformat(),
            },
        )
    with pytest.raises(ValueError, match="future M1"):
        sanitize_audit14_row(
            original=source, raw={
                **row, "online_entry_at":
                    source.m15_setup_confirmed_at,
            },
        )


def test_nonenforced_status_is_diagnostic_and_never_forwarded_as_target() -> None:
    source = _src()
    row = _row(source)
    status = {
        **row, "status": "NO_UNTOUCHED_H1_OBJECTIVE_AT_ONLINE_CLOSE",
        "candidate_target_price": None,
        "candidate_gross_r": None,
        "candidate_exit_reason": None,
        "rejection_is_diagnostic_not_a_hard_veto": True,
    }
    witness = sanitize_audit14_row(original=source, raw=status)
    assert witness.status != "ELIGIBLE"
    assert witness.target_price is None
    assert not witness.alters_trade_admission
    with pytest.raises(ValueError, match="hard veto"):
        sanitize_audit14_row(
            original=source,
            raw={**status, "rejection_is_diagnostic_not_a_hard_veto": False},
        )


def test_extra_unreviewed_field_or_mutated_source_is_rejected() -> None:
    source = _src()
    row = _row(source)
    with pytest.raises(ValueError, match="schema changed"):
        sanitize_audit14_row(original=source, raw={
            **row, "future_60_min_winner": True,
        })
    with pytest.raises(ValueError, match="frozen V49 source"):
        sanitize_audit14_row(original=replace(source, symbol="EURUSD"), raw=row)
    with pytest.raises(ValueError, match="discrepancy flag"):
        sanitize_audit14_row(
            original=source, raw={**row, "first_online_differs": False},
        )


def test_ineligible_target_and_wrong_route_geometry_fail_closed() -> None:
    source = _src()
    row = _row(source)
    with pytest.raises(ValueError, match="stop/target geometry"):
        sanitize_audit14_row(
            original=source, raw={**row, "candidate_target_price": "99"},
        )
    with pytest.raises(ValueError, match="ineligible"):
        sanitize_audit14_row(
            original=source,
            raw={**row, "status": "INVALID_M15_STOP_AT_ONLINE_CLOSE",
                 "rejection_is_diagnostic_not_a_hard_veto": True},
        )
