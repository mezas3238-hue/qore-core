from decimal import Decimal

from qore.infrastructure.trader_lab import turtle_soup_xauusd_r2_cibo_full as r2


def test_r2_temporal_split_and_governance_contract() -> None:
    assert r2.EVAL_OPEN.isoformat() == "2016-09-17T00:00:00+00:00"
    assert r2.TRAIN_CLOSE.isoformat() == "2022-09-17T00:00:00+00:00"
    assert r2.EVAL_CLOSE.isoformat() == "2026-09-17T00:00:00+00:00"
    assert r2.TRAIN_CLOSE < r2.EVAL_CLOSE
    assert "mfe" not in r2.FEATURES
    assert "mae" not in r2.FEATURES
    assert "exit_reason" not in r2.FEATURES
    assert "target_time" not in r2.FEATURES


def test_bucket_boundaries_are_predeclared() -> None:
    cuts = (Decimal("0.25"), Decimal("0.50"), Decimal("0.75"))
    assert r2._bucket(None, cuts) == "missing"
    assert r2._bucket(Decimal("0.10"), cuts).startswith("q1")
    assert r2._bucket(Decimal("0.50"), cuts).startswith("q2")
    assert r2._bucket(Decimal("0.90"), cuts).startswith("q4")


def test_latency_bucket_is_deterministic() -> None:
    assert r2._latency_bucket(None) == "missing"
    assert r2._latency_bucket(5) == "<=5m"
    assert r2._latency_bucket(15) == "6-15m"
    assert r2._latency_bucket(30) == "16-30m"
    assert r2._latency_bucket(60) == "31-60m"
    assert r2._latency_bucket(120) == "61-120m"
    assert r2._latency_bucket(121) == ">120m"


def test_all_features_are_pre_entry_context() -> None:
    expected = {
        "timeframe", "side", "session", "weekday", "prior_body_alignment",
        "fvg_before_entry", "exact_equal_liquidity", "raid_depth_range_bucket",
        "reclaim_latency_bucket", "cisd_progress_bucket",
        "protected_risk_range_bucket", "source_range_state_bucket",
        "body_fraction_bucket", "rejection_wick_bucket", "close_location_bucket",
        "projected_r_bucket", "target_distance_range_bucket",
    }
    assert set(r2.FEATURES) == expected
