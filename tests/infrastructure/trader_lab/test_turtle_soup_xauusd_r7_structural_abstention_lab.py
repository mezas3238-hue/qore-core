from decimal import Decimal

from qore.infrastructure.trader_lab import turtle_soup_xauusd_r7_structural_abstention_lab as r7


def test_frozen_invalid_state_exact() -> None:
    assert r7.FROZEN_INVALID == {
        "raid_depth_range_bucket": "q4:<=0.50",
        "cisd_progress_bucket": "q4:>0.75",
        "reclaim_latency_bucket": "<=5m",
        "protected_risk_range_bucket": "q3:<=1.0",
    }


def test_abstain_matches_only_frozen_state() -> None:
    row = dict(r7.FROZEN_INVALID)
    assert r7._is_abstain(row)
    row["cisd_progress_bucket"] = "q3:<=0.75"
    assert not r7._is_abstain(row)


def test_drawdown_and_losing_streak() -> None:
    vals = [Decimal("1"), Decimal("-1"), Decimal("-2"), Decimal("1")]
    assert r7._max_dd(vals) == Decimal("3")
    assert r7._max_losing_streak(vals) == 2
