"""Causal predecision projection for Phase22 Turtle target ledgers.

Target Destination V2 intentionally records post-departure touch outcomes for
research. Frozen Turtle replay code needs only the candidate identity plus the
knowledge of whether a candidate had already been touched *before* entry.
This adapter masks every outcome at or after the decision timestamp so fresh
Phase22 decisions cannot observe their own future.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal
from typing import Any, cast

_OUTCOME_FIELDS = (
    "touch_within_24h",
    "touch_m5_opened_at",
    "touch_m5_closed_at",
    "time_to_touch_minutes",
    "touch_order_group",
    "touch_order_ambiguous_within_m5",
)


def _aware(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Phase22 Turtle decision timestamp must be aware")


def _timestamp(value: object) -> datetime | None:
    if value is None:
        return None
    parsed = datetime.fromisoformat(str(value))
    _aware(parsed)
    return parsed


def project_target_rows_predecision(
    rows: Sequence[dict[str, Any]],
    *,
    at: datetime,
) -> tuple[dict[str, Any], ...]:
    """Retain prior-touch evidence, mask simultaneous/future outcomes."""

    _aware(at)
    projected: list[dict[str, Any]] = []
    for raw in rows:
        row = dict(raw)
        touch_at = _timestamp(row.get("touch_m5_opened_at"))
        if touch_at is None or touch_at < at:
            projected.append(row)
            continue

        row["touch_within_24h"] = False
        row["touch_m5_opened_at"] = None
        row["touch_m5_closed_at"] = None
        row["time_to_touch_minutes"] = None
        row["touch_order_group"] = None
        row["touch_order_ambiguous_within_m5"] = False
        projected.append(row)
    return tuple(projected)


def assert_no_future_outcome_surface(
    rows: Sequence[dict[str, Any]],
    *,
    at: datetime,
) -> None:
    """Fail closed if a projected row still exposes future touch evidence."""

    _aware(at)
    for row in rows:
        touch_at = _timestamp(row.get("touch_m5_opened_at"))
        if touch_at is not None and touch_at >= at:
            raise ValueError("Phase22 Turtle future touch leaked into decision")
        if touch_at is None:
            for field in _OUTCOME_FIELDS:
                value = row.get(field)
                if field == "touch_within_24h" and value not in {None, False}:
                    raise ValueError(
                        "Phase22 Turtle masked touch flag remains outcome-aware"
                    )
                if (
                    field == "touch_order_ambiguous_within_m5"
                    and value not in {None, False}
                ):
                    raise ValueError(
                        "Phase22 Turtle masked ambiguity remains outcome-aware"
                    )
                if field not in {
                    "touch_within_24h",
                    "touch_order_ambiguous_within_m5",
                } and value is not None:
                    raise ValueError(
                        "Phase22 Turtle masked outcome field remains populated"
                    )


ActiveLadder = Callable[..., list[Any]]


@contextmanager
def fresh_causal_active_ladder(module: Any) -> Iterator[None]:
    """Patch only one loaded frozen replay module for its FRESH invocation."""

    v1 = getattr(module, "v1", None)
    original = getattr(v1, "_active_ladder", None)
    if v1 is None or not callable(original):
        raise ValueError(
            "Phase22 fresh Turtle replay lacks _active_ladder causal seam"
        )

    def causal_active_ladder(
        rows: Sequence[dict[str, Any]],
        *,
        at: datetime,
        side: Any,
        entry: Decimal,
        tick: Decimal,
    ) -> list[Any]:
        projected = project_target_rows_predecision(rows, at=at)
        assert_no_future_outcome_surface(projected, at=at)
        return cast(
            list[Any],
            original(
                projected,
                at=at,
                side=side,
                entry=entry,
                tick=tick,
            ),
        )

    v1._active_ladder = causal_active_ladder
    try:
        yield
    finally:
        v1._active_ladder = original
