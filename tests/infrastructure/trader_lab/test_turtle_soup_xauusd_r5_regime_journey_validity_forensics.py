from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.trader_lab import turtle_soup_xauusd_r5_regime_journey_validity_forensics as mod


def _bar(day: int, close: str, high: str = "11", low: str = "9") -> mod.AggBar:
    return mod.AggBar(
        opened_at=datetime(2026, 1, day, tzinfo=UTC),
        open=Decimal("10"),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
    )


def test_fixed_ratio_and_efficiency_buckets() -> None:
    assert mod._bucket_ratio(Decimal("0.70")) == "compressed<=0.75"
    assert mod._bucket_ratio(Decimal("1.00")) == "normal_0.75_1.25"
    assert mod._bucket_ratio(Decimal("1.40")) == "expanded>1.25"
    assert mod._bucket_efficiency(Decimal("0.10")) == "choppy<0.25"
    assert mod._bucket_efficiency(Decimal("0.30")) == "directional_0.25_0.50"
    assert mod._bucket_efficiency(Decimal("0.70")) == "persistent>=0.50"


def test_reversal_edge_is_side_aware() -> None:
    loc = Decimal("0.15")
    assert mod._reversal_edge(loc, "long") == Decimal("0.15")
    assert mod._reversal_edge(loc, "short") == Decimal("0.85")
    assert mod._bucket_reversal_edge(Decimal("0.15")) == "near_reversal_edge<=0.20"


def test_trend_state_uses_pre_entry_completed_path() -> None:
    up = tuple(_bar(i, str(10 + i)) for i in range(1, 6))
    assert mod._trend_state(up, "long") == "persistent_with_trade"
    assert mod._trend_state(up, "short") == "persistent_against_trade"


def test_family_definition_is_structural_not_date_based() -> None:
    stable = {"raid_depth_range_bucket": "q2:<=0.10", "cisd_progress_bucket": "q4:>0.75"}
    failing = {"raid_depth_range_bucket": "q4:<=0.50", "cisd_progress_bucket": "q4:>0.75"}
    other = {"raid_depth_range_bucket": "q4:<=0.50", "cisd_progress_bucket": "q2:<=0.50"}
    assert mod._family(stable) == "STABLE_RAID_5_10"
    assert mod._family(failing) == "DEEP_RAID_25_50_LATE_CISD"
    assert mod._family(other) == "OTHER"
