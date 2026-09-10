from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from types import SimpleNamespace
from typing import cast

from qore.infrastructure.trader_lab.first_cohort_story_forensics import (
    _Episode,
    _frame_sequence,
    _marker,
    _sorted_markers,
)


def _at(minute: int) -> datetime:
    return datetime(2026, 1, 5, 12, minute, tzinfo=UTC)


def _episode(*, mfe_at: datetime, mae_at: datetime) -> _Episode:
    return cast(
        _Episode,
        SimpleNamespace(
            bars=(
                SimpleNamespace(closed_at=_at(0)),
                SimpleNamespace(closed_at=_at(6)),
            ),
            trade=SimpleNamespace(
                signal_at=_at(1),
                filled_at=_at(2),
                exited_at=_at(5),
            ),
            mfe_at=mfe_at,
            mae_at=mae_at,
        ),
    )


def _frame_stages(episode: _Episode) -> list[str]:
    frames = _frame_sequence(episode)
    times = [cast(int, row["visible_through_unix"]) for row in frames]
    assert times == sorted(times)
    return [cast(str, row["stage"]) for row in frames]


def test_frames_allow_mae_before_mfe_without_rewriting_evidence_order() -> None:
    stages = _frame_stages(_episode(mfe_at=_at(4), mae_at=_at(3)))
    assert stages == ["context", "signal", "entry", "mae", "mfe", "exit", "post_exit"]


def test_frames_allow_mfe_before_mae_without_rewriting_evidence_order() -> None:
    stages = _frame_stages(_episode(mfe_at=_at(3), mae_at=_at(4)))
    assert stages == ["context", "signal", "entry", "mfe", "mae", "exit", "post_exit"]


def test_frames_use_semantic_order_only_as_same_bar_tie_break() -> None:
    stages = _frame_stages(_episode(mfe_at=_at(3), mae_at=_at(3)))
    assert stages == ["context", "signal", "entry", "mfe", "mae", "exit", "post_exit"]


def test_markers_are_time_monotonic_when_mae_precedes_mfe() -> None:
    rows = _sorted_markers(
        [
            _marker("signal", _at(1), "SIG"),
            _marker("entry", _at(2), "ENTRY"),
            _marker("mfe", _at(4), "MFE"),
            _marker("mae", _at(3), "MAE"),
            _marker("exit", _at(5), "EXIT"),
        ]
    )
    assert [cast(str, row["kind"]) for row in rows] == [
        "signal",
        "entry",
        "mae",
        "mfe",
        "exit",
    ]
    assert [cast(str, row["at"]) for row in rows] == sorted(
        cast(str, row["at"]) for row in rows
    )


def test_markers_use_semantic_order_only_as_same_bar_tie_break() -> None:
    rows = _sorted_markers(
        [
            _marker("mae", _at(3), "MAE"),
            _marker("mfe", _at(3), "MFE"),
        ]
    )
    assert [cast(str, row["kind"]) for row in rows] == ["mfe", "mae"]


def test_markers_sort_by_absolute_instant_across_timezone_offsets() -> None:
    earlier_same_day = datetime(
        2026, 1, 5, 13, 0, tzinfo=timezone(timedelta(hours=1))
    )  # 12:00 UTC
    later_utc = datetime(2026, 1, 5, 12, 30, tzinfo=UTC)
    rows = _sorted_markers(
        [
            _marker("mae", later_utc, "MAE"),
            _marker("mfe", earlier_same_day, "MFE"),
        ]
    )
    assert [cast(str, row["kind"]) for row in rows] == ["mfe", "mae"]
