from decimal import Decimal

from qore.infrastructure.trader_lab import turtle_soup_xauusd_r3_forensics as f


def test_stat_and_risk_geometry_are_deterministic() -> None:
    stat = f._stat([Decimal("2"), Decimal("-1"), Decimal("3"), Decimal("-2")])
    assert stat["count"] == 4
    assert stat["total_r"] == "2"
    assert stat["profit_factor"] == str(Decimal("5") / Decimal("3"))
    assert stat["max_drawdown_r"] == "2"

    geometry = f._risk_geometry({"entry": "100", "stop": "99.9", "target": "102"})
    assert geometry["absolute_risk_price"] == "0.1"
    assert geometry["risk_bps_of_entry"] == "10.000"
    assert geometry["structural_reward_r"] == "2E+1"


def test_cap_is_diagnostic_only_mechanic() -> None:
    values = [Decimal("-1"), Decimal("4"), Decimal("12")]
    assert f._cap(values, Decimal("5")) == [Decimal("-1"), Decimal("4"), Decimal("5")]
