"""Synthetic original protobuf-gated dual-sided source updates and zero episodes."""
from __future__ import annotations

from pathlib import Path

import pytest

from qore.infrastructure.trader_lab import qore_native_g1_original_proto_zero_episodes_v1 as f


def test_same_millisecond_updates_can_be_zero_or_positive():
    bid=[(0,100000),(100,100000),(200,100005),(300,100010)]
    ask=[(0,100000),(100,100000),(200,100010),(300,100010)]
    result=f.investigate(bid,ask)
    assert result["source_quality_counts"]["zero_spread"]==3
    assert result["source_quality_counts"]["positive_spread"]==1
    assert result["source_quality_counts"]["zero_same_millisecond"]==3
    assert result["simultaneous_native_bid_ask_updated_instants"]==4
    assert result["simultaneous_native_equal_price"]==3
    assert result["simultaneous_native_positive_price_gap"]==1
    assert result["zero_episode_count_consecutive_source_instants"]==2
    assert result["zero_episode_max_consecutive_source_instants"]==2
    assert result["is_original_historical_fill_execution_verified"] is False


def test_one_side_lag_causes_zero_from_either_direction_not_from_future():
    bid=[(0,100000),(200,100005)]
    ask=[(100,100000),(300,100005)]
    out=f.investigate(bid,ask)
    assert out["source_quality_counts"]["missing_side"]==1
    assert out["source_quality_counts"]["zero_spread"]==2
    assert out["zero_last_known_bid_older"]==1
    assert out["zero_last_known_ask_older"]==1
    assert out["zero_last_known_max_side_lag_ms_buckets"]["1_100"]==2
    assert out["source_quality_counts"]["zero_same_millisecond"]==0


def test_stale_source_not_claimed_zero():
    out=f.investigate([(0,100000)],[(1,100000),(6000,100000)])
    assert out["source_quality_counts"]["zero_spread"]==1
    assert out["source_quality_counts"]["stale_side"]==1
    assert out["source_quality_counts"]["missing_side"]==1


def test_same_ms_ambiguous_price_fails_closed():
    with pytest.raises(ValueError,match="SAME_MS_CAUSAL_AMBIGUITY"):
        f.investigate([(0,100000),(0,100005)],[(0,100010)])
    with pytest.raises(ValueError,match="CLOCK_INVERTED"):
        f.investigate([(1,100000),(0,100000)],[(0,100010)])


def test_market_source_must_have_both_sides():
    with pytest.raises(ValueError,match="BOTH_SIDES_REQUIRED"):
        f.investigate([],[(0,100000)])


def test_real_original_artifact_sha_precondition_not_optional(tmp_path: Path):
    with pytest.raises(ValueError,match="SOURCE_SHA_REGISTER_MISSING"):
        f.analyze_original(tmp_path)


def test_scope_not_net_or_unbiased_study():
    assert f.ORIGINAL_RUN==38288411671
    assert f.ORIGINAL_ARTIFACT==11764163362
    assert f.IDENTITY.endswith("_V1")
    assert f.CLOCK_LIMIT_MS==5000
