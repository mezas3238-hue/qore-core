from decimal import Decimal

from qore.infrastructure.trader_lab.vt08_cognitive_adaptive_protection_v2 import (
    FRESH_BOUNDARY,
    LOW_RISK_REF_THRESHOLD,
    MARKETS,
)


def test_adaptive_protection_v2_freeze_constants() -> None:
    assert MARKETS == ("CADJPY", "NZDUSD")
    assert LOW_RISK_REF_THRESHOLD == Decimal("0.25")
    assert FRESH_BOUNDARY.isoformat() == "2023-09-24T23:45:00+00:00"
