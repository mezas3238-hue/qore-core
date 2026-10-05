from dataclasses import replace
from decimal import Decimal

from qore.infrastructure.cibo_position_continuation_coverage_sensor import (
    measure_position_continuation_coverage,
)
from tests.infrastructure.test_cibo_full_economic_digital_twin import (
    _position_competition_twin,
)


def test_continuation_sensor_separates_entry_expectation_from_current_value() -> None:
    twin = _position_competition_twin(
        continuation_value=Decimal("0"),
        headroom_risk=Decimal("1"),
        headroom_margin=Decimal("10"),
    )
    position = replace(
        twin.positions[0],
        continuation_value_identified=False,
        remaining_reward_identified=False,
    )
    twin = replace(twin, positions=(position,))

    report = measure_position_continuation_coverage(twin)

    assert report.open_position_count == 1
    assert report.entry_expectation_identified_count == 1
    assert report.continuation_value_identified_count == 0
    assert report.continuation_coverage == Decimal("0")
    assert report.portfolio_actionable_coverage == Decimal("0")
    assert report.primary_blocker == "CONTINUATION_VALUE_UNIDENTIFIED"


def test_continuation_sensor_marks_position_actionable_only_when_identified() -> None:
    twin = _position_competition_twin(
        continuation_value=Decimal("0.5"),
        headroom_risk=Decimal("1"),
        headroom_margin=Decimal("10"),
    )
    position = replace(
        twin.positions[0],
        continuation_value_identified=True,
        remaining_reward_identified=True,
    )
    twin = replace(twin, positions=(position,))

    report = measure_position_continuation_coverage(twin)

    assert report.continuation_coverage == Decimal("1")
    assert report.portfolio_actionable_coverage == Decimal("1")
    assert report.primary_blocker == "NONE"
