from decimal import Decimal

from qore.infrastructure.trader_lab import vt08_index_r19_poi_target_dual as mod


def test_r19_contract() -> None:
    assert mod.FIVE_YEAR_MIN_TRADES == 1500
    assert mod.FIVE_YEAR_MAX_TRADES == 1600
    assert mod.TWO_YEAR_MIN_TRADES == 600
    assert mod.TWO_YEAR_MAX_TRADES == 700
    assert mod.PF_MIN == Decimal("1.50")
    assert mod.DD_MAX == Decimal("6")


def test_r19_target_map_space_is_bounded() -> None:
    maps = mod._maps()
    assert len(maps) == 96
    assert {row.cisd for row in maps} == {
        Decimal("0.75"),
        Decimal("1.00"),
        Decimal("1.25"),
        Decimal("1.50"),
        Decimal("1.75"),
        Decimal("2.00"),
    }


def test_r19_no_risk_governor_contract() -> None:
    p = mod._policy(Decimal("1.25"))
    assert p.target_r == Decimal("1.25")
    assert p.trail_name == "OFF"
    assert p.deadline_bars is None
