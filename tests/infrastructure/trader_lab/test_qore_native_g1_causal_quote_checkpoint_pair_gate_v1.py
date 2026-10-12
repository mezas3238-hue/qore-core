"""G1 source-only paired quote test. No trade PnL or real-order execution."""
from __future__ import annotations

from pathlib import Path

import pytest
from qore.infrastructure.trader_lab import qore_native_g1_causal_quote_checkpoint_pair_gate_v1 as g


def test_exact_time_only_backward_source_no_future_quote():
    bids=[(100,100000),(300,100010)]
    asks=[(120,100005),(320,100020)]
    assert g.decision_quality(99,bids,asks)=="MISSING_SIDE"
    assert g.decision_quality(115,bids,asks)=="MISSING_SIDE"
    assert g.decision_quality(121,bids,asks)=="OK_POSITIVE_BIDASK"
    assert g.decision_quality(305,bids,asks)=="CROSSED_SPREAD"
    assert g.decision_quality(320,bids,asks)=="OK_POSITIVE_BIDASK"


def test_zero_spread_cannot_be_treated_as_cost_free_eligible():
    bids=[(0,100000),(1000,100010)]
    asks=[(0,100000),(1000,100020)]
    assert g.decision_quality(0,bids,asks)=="ZERO_SPREAD"
    assert g.decision_quality(1000,bids,asks)=="OK_POSITIVE_BIDASK"
    outcome=g.check_pair(0,1000,bids,asks)
    assert not outcome["source_pair_eligible"]
    assert outcome["economic_PnL_or_execution_authorized"] is False


def test_stale_side_vs_fresh_source_is_not_backward_filled_forever():
    bids=[(0,100000)]
    asks=[(0,100010),(10000,100020)]
    assert g.decision_quality(5000,bids,asks)=="OK_POSITIVE_BIDASK"
    assert g.decision_quality(5001,bids,asks)=="STALE_SIDE"
    assert g.decision_quality(10000,bids,asks)=="STALE_SIDE"


def test_conflicting_same_ms_or_unordered_events_are_never_accepted():
    with pytest.raises(ValueError,match="CONFLICTING_SAME_MILLISECOND"):
        g.decision_quality(100,[(10,100000),(10,100001)],[(10,100010)])
    with pytest.raises(ValueError,match="NONMONOTONE"):
        g.decision_quality(100,[(90,100000),(50,100000)],[(10,100010)])


def test_valid_pair_requires_both_source_checkpoints_positive():
    bid=[(100,100000),(300,100001)]
    ask=[(100,100010),(300,100021)]
    good=g.check_pair(100,300,bid,ask)
    assert good["source_pair_eligible"] is True
    assert good["entry_source_quality"] == good["exit_source_quality"] == "OK_POSITIVE_BIDASK"
    assert good["economic_PnL_or_execution_authorized"] is False
    with pytest.raises(ValueError,match="PAIR_TIMES_INVALID"):
        g.check_pair(300,100,bid,ask)


def test_input_clock_types_and_threshold_fail_closed():
    with pytest.raises(ValueError,match="TIMESTAMP_OR_MAX_AGE_INVALID"):
        g.decision_quality(True,[(0,1)],[(0,2)])
    with pytest.raises(ValueError,match="TIMESTAMP_OR_MAX_AGE_INVALID"):
        g.decision_quality(10,[(0,1)],[(0,2)],max_age_ms=0)


def test_frozen_calendar_sample_no_optimization():
    assert g.CHECKPOINT_MINUTES == ((5,15),(10,25))
    assert len(g.verified.TARGETS)==5
    assert len(g.verified.WINDOWS)==2
    assert g.SOURCE_RUN == 38288411671
    assert g.SOURCE_ARTIFACT==11764163362


def test_original_proto_sha_second_decoder_required(tmp_path: Path):
    with pytest.raises(ValueError,match="SOURCE_SHA_REGISTER_MISSING"):
        g.actual_source_checkpoints(tmp_path)
