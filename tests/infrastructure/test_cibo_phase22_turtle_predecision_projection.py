from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from qore.infrastructure.cibo_phase22_turtle_predecision_projection import (
    fresh_causal_active_ladder,
    project_target_rows_predecision,
)

_AT = datetime(2016, 1, 4, 10, tzinfo=UTC)


def _row(touch: str | None) -> dict[str, object]:
    return {
        "candidate_type": "ACTIVE_SWING_3_DIRECTIONAL_BOUNDARY",
        "source_timeframe": "H1",
        "candidate_price": "1.2500",
        "candidate_known_at": "2016-01-04T09:00:00+00:00",
        "touch_within_24h": touch is not None,
        "touch_m5_opened_at": touch,
        "touch_m5_closed_at": (
            None if touch is None else "2016-01-04T10:10:00+00:00"
        ),
        "time_to_touch_minutes": 10 if touch is not None else None,
        "touch_order_group": 1 if touch is not None else None,
        "touch_order_ambiguous_within_m5": touch is not None,
    }


def test_future_touch_outcomes_are_fully_masked() -> None:
    rows = project_target_rows_predecision(
        (_row("2016-01-04T10:05:00+00:00"),),
        at=_AT,
    )

    row = rows[0]
    assert row["touch_within_24h"] is False
    assert row["touch_m5_opened_at"] is None
    assert row["touch_m5_closed_at"] is None
    assert row["time_to_touch_minutes"] is None
    assert row["touch_order_group"] is None
    assert row["touch_order_ambiguous_within_m5"] is False


def test_prior_touch_is_retained_for_causal_invalidation() -> None:
    touch = "2016-01-04T09:55:00+00:00"
    rows = project_target_rows_predecision((_row(touch),), at=_AT)

    assert rows[0]["touch_m5_opened_at"] == touch


def test_future_outcome_changes_cannot_change_wrapped_input() -> None:
    captured: list[tuple[dict[str, object], ...]] = []

    def original(rows: object, **_kwargs: object) -> list[object]:
        captured.append(tuple(dict(item) for item in rows))  # type: ignore[arg-type]
        return []

    module = SimpleNamespace(
        v1=SimpleNamespace(_active_ladder=original),
    )
    first = _row("2016-01-04T10:05:00+00:00")
    second = _row("2016-01-04T18:00:00+00:00")
    second["time_to_touch_minutes"] = 480
    second["touch_order_group"] = 9

    with fresh_causal_active_ladder(module):
        module.v1._active_ladder(
            (first,),
            at=_AT,
            side="long",
            entry=object(),
            tick=object(),
        )
        module.v1._active_ladder(
            (second,),
            at=_AT,
            side="long",
            entry=object(),
            tick=object(),
        )

    assert captured[0] == captured[1]
    assert module.v1._active_ladder is original
