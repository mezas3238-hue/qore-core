from qore.infrastructure.trader_lab import (
    capitalizer_v3_source_first_fvg_maturation_census_2y_v1 as census,
)


def test_fvg_maturation_census_contract_is_frozen() -> None:
    assert census.IDENTITY == (
        "QORE_CAPITALIZER_V3_SOURCE_FIRST_FVG_MATURATION_CENSUS_2Y_V1"
    )
    assert census.EXPECTED_ROWS == 322
    assert census.EXPECTED_SAME_SIDE_BEFORE_DEADLINE == 289
    assert census.EXPECTED_OPPOSED_BEFORE_DEADLINE == 246


def test_fvg_maturation_order_is_causal() -> None:
    from datetime import UTC, datetime

    same = datetime(2026, 1, 1, 10, 1, tzinfo=UTC)
    opposed = datetime(2026, 1, 1, 10, 2, tzinfo=UTC)
    assert census._order(same, opposed) == "SAME_SIDE_FIRST"
    assert census._order(opposed, same) == "OPPOSED_FIRST"
    assert census._order(same, same) == "SIMULTANEOUS"
    assert census._order(same, None) == "SAME_SIDE_ONLY"
    assert census._order(None, opposed) == "NO_SAME_SIDE_FVG"
