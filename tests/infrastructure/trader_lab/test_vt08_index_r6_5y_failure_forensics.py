from decimal import Decimal

from qore.infrastructure.trader_lab import vt08_index_r6_5y_failure_forensics as mod


def test_forensics_identity_and_authority_boundaries() -> None:
    assert mod.IDENTITY == "VT08_INDEX_R6_5Y_FAILURE_FORENSICS_001"
    assert mod.PRIMARY_STRESS == Decimal("0.05")
    assert mod.SECONDARY_STRESS == Decimal("0.10")


def test_basic_metrics_delegate_is_stable() -> None:
    row = mod._metrics(
        (Decimal("2"), Decimal("-1"), Decimal("-1"), Decimal("2"))
    )
    assert row["sample"] == 4
    assert row["profit_factor"] == "2"
    assert row["max_drawdown_r"] == "2"


def test_density_attribution_separates_initial_and_rearm() -> None:
    class Signal:
        symbol = "NAS100"

    class Opportunity:
        def __init__(self, rearm: int, poi: str) -> None:
            self.rearm_index = rearm
            self.source_poi_kind = poi
            self.signal = Signal()

    rows = (
        mod.Admission(Opportunity(0, "fvg"), mod.datetime.now(mod.UTC)),
        mod.Admission(Opportunity(1, "fvg"), mod.datetime.now(mod.UTC)),
        mod.Admission(Opportunity(2, "cisd"), mod.datetime.now(mod.UTC)),
    )
    result = mod._density_attribution(rows)
    assert result["total"] == 3
    assert result["initial_trade_count"] == 1
    assert result["rearm_trade_count"] == 2
    assert result["rearm_share"] == str(Decimal(2) / Decimal(3))


def test_governor_trace_never_creates_zero_weight() -> None:
    assert mod.freeze.RISK_GOVERNOR["zero_weight_allowed"] is False
