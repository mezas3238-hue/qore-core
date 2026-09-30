from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_target_context import (
    load_target_contexts,
    target_context_at,
)


def _row(
    *,
    candidate_id: str,
    touch: bool,
    touch_minutes: int | None,
) -> dict[str, object]:
    departure = datetime(2026, 9, 19, 12, 0, tzinfo=UTC)
    return {
        "schema": "qore.cibo_market_atlas.target_destination.v2",
        "identity": "CIBO_TARGET_DESTINATION_V2_SUPPORTED_REFERENCE_UNIVERSE",
        "episode_id": "USDJPY:EP",
        "candidate_id": candidate_id,
        "symbol": "USDJPY",
        "side": "long",
        "departure_at": departure.isoformat(),
        "departure_anchor_price": "147.000",
        "candidate_type": "PRIOR_CANDLE_DIRECTIONAL_BOUNDARY",
        "source_timeframe": "H1",
        "candidate_price": "147.100",
        "candidate_distance_ticks": "100",
        "candidate_known_at": (departure - timedelta(minutes=30)).isoformat(),
        "candidate_structural_opened_at": (
            departure - timedelta(hours=1)
        ).isoformat(),
        "active_untouched_at_departure": True,
        "causal_feature": True,
        "outcome_only": False,
        "result_fields_outcome_only": True,
        "touch_within_24h": touch,
        "time_to_touch_minutes": touch_minutes,
        "touch_m5_opened_at": (
            None
            if touch_minutes is None
            else (departure + timedelta(minutes=touch_minutes)).isoformat()
        ),
        "touch_m5_closed_at": None,
        "touch_order_ambiguous_within_m5": False,
        "touch_order_group": None,
    }


def _write(root: Path, rows: tuple[dict[str, object], ...]) -> None:
    root.mkdir(parents=True)
    path = root / "TARGET_DESTINATION_LEDGER_V2.jsonl"
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def test_target_context_ignores_post_departure_touch_results(tmp_path: Path) -> None:
    left = tmp_path / "left"
    right = tmp_path / "right"
    _write(left, (_row(candidate_id="A", touch=True, touch_minutes=15),))
    _write(right, (_row(candidate_id="A", touch=False, touch_minutes=None),))

    left_contexts = load_target_contexts(left)
    right_contexts = load_target_contexts(right)
    assert left_contexts == right_contexts
    context = left_contexts[0]
    assert context.post_departure_outcomes_used is False
    assert context.active_candidate_count == 1
    assert context.nearest_distance_ticks is not None
    assert context.families == ("PRIOR_CANDLE_DIRECTIONAL_BOUNDARY",)
    assert context.timeframes == ("H1",)


def test_target_context_requires_candidate_known_by_departure(tmp_path: Path) -> None:
    root = tmp_path / "future"
    row = _row(candidate_id="FUTURE", touch=False, touch_minutes=None)
    departure = datetime.fromisoformat(str(row["departure_at"]))
    row["candidate_known_at"] = (departure + timedelta(minutes=5)).isoformat()
    _write(root, (row,))

    try:
        load_target_contexts(root)
    except ValueError as exc:
        assert "known after departure" in str(exc)
    else:
        raise AssertionError("future candidate must fail closed")


def test_target_context_lookup_is_exact_time_and_direction(tmp_path: Path) -> None:
    root = tmp_path / "lookup"
    _write(root, (_row(candidate_id="A", touch=False, touch_minutes=None),))
    contexts = load_target_contexts(root)
    departure = datetime(2026, 9, 19, 12, 0, tzinfo=UTC)

    assert (
        target_context_at(
            contexts,
            symbol="USDJPY",
            side=CapitalizerSide.LONG,
            departure_at=departure,
        )
        is not None
    )
    assert (
        target_context_at(
            contexts,
            symbol="USDJPY",
            side=CapitalizerSide.SHORT,
            departure_at=departure,
        )
        is None
    )
