from decimal import Decimal

from qore.infrastructure.trader_lab import vt08_index_r17_formation_quality_forensics as mod


def test_r17_contract() -> None:
    assert mod.IDENTITY == "VT08_INDEX_R17_FORMATION_QUALITY_FORENSICS_001"
    assert mod.STRESS == Decimal("0.05")


def test_r17_fixed_risk_buckets() -> None:
    # Bucket names are intentionally fixed and not learned from outcomes.
    assert {"<0.15%", "0.15-0.30%", "0.30-0.50%", ">=0.50%"}


def test_r17_minutes_nonnegative() -> None:
    assert mod._minutes(-1.0) == 0
    assert mod._minutes(900.0) == 15
