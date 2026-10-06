from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

from qore.infrastructure.cibo_position_release_readiness_sensor import (
    measure_position_release_readiness,
)
from tests.infrastructure.test_cibo_full_economic_digital_twin import (
    T0,
    _position_competition_twin,
)


def test_release_readiness_blocks_without_causal_mark() -> None:
    twin = _position_competition_twin(
        continuation_value=Decimal("0.5"),
        headroom_risk=Decimal("1"),
        headroom_margin=Decimal("10"),
    )
    position = replace(
        twin.positions[0],
        entry_price=Decimal("100"),
        structural_stop=Decimal("99"),
        technical_target=Decimal("102"),
        continuation_value_identified=True,
        releasable=True,
        current_mark_price=None,
        market_state_observed_at=None,
        mark_to_market_identified=False,
    )
    twin = replace(twin, positions=(position,))

    report = measure_position_release_readiness(twin)

    assert report.continuation_identified_count == 1
    assert report.price_geometry_identified_count == 1
    assert report.mark_to_market_identified_count == 0
    assert report.executable_release_count == 0
    assert report.executable_release_rate == Decimal("0")
    assert report.primary_blocker == "MARK_TO_MARKET_UNIDENTIFIED"


def test_release_readiness_requires_complete_causal_market_state() -> None:
    twin = _position_competition_twin(
        continuation_value=Decimal("0.5"),
        headroom_risk=Decimal("1"),
        headroom_margin=Decimal("10"),
    )
    position = replace(
        twin.positions[0],
        entry_price=Decimal("100"),
        structural_stop=Decimal("99"),
        technical_target=Decimal("102"),
        current_mark_price=Decimal("100.7"),
        market_state_observed_at=T0 - timedelta(minutes=1),
        mark_to_market_identified=True,
        continuation_value_identified=True,
        releasable=True,
    )
    twin = replace(twin, positions=(position,))

    report = measure_position_release_readiness(twin)

    assert report.executable_release_count == 1
    assert report.executable_release_rate == Decimal("1")
    assert report.primary_blocker == "NONE"
