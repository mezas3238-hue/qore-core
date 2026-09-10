from __future__ import annotations

from pathlib import Path


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"expected exactly one replacement in {path}, found {count}")
    path.write_text(text.replace(old, new), encoding="utf-8")


story_path = Path("src/qore/infrastructure/trader_lab/first_cohort_story_forensics.py")
old_markers = '''                "markers": [
                    _marker("signal", self.trade.signal_at, "SIG"),
                    _marker("entry", self.trade.filled_at, "ENTRY"),
                    _marker("mfe", self.mfe_at, f"MFE {format(self.mfe_r, 'f')}R"),
                    _marker("mae", self.mae_at, f"MAE {format(self.mae_r, 'f')}R"),
                    _marker("exit", self.trade.exited_at, self.trade.exit_reason.upper()),
                ],
'''
new_markers = '''                "markers": _sorted_markers(
                    [
                        _marker("signal", self.trade.signal_at, "SIG"),
                        _marker("entry", self.trade.filled_at, "ENTRY"),
                        _marker("mfe", self.mfe_at, f"MFE {format(self.mfe_r, 'f')}R"),
                        _marker("mae", self.mae_at, f"MAE {format(self.mae_r, 'f')}R"),
                        _marker("exit", self.trade.exited_at, self.trade.exit_reason.upper()),
                    ]
                ),
'''
replace_once(story_path, old_markers, new_markers)

old_frames = '''def _frame_sequence(episode: _Episode) -> list[dict[str, object]]:
    ordered = [
        ("context", episode.bars[0].closed_at),
        ("signal", episode.trade.signal_at),
        ("entry", episode.trade.filled_at),
        ("mfe", episode.mfe_at),
        ("mae", episode.mae_at),
        ("exit", episode.trade.exited_at),
        ("post_exit", episode.bars[-1].closed_at),
    ]
    frames: list[dict[str, object]] = []
    seen: set[tuple[str, datetime]] = set()
    for stage, at in ordered:
        key = (stage, at)
        if key in seen:
            continue
        seen.add(key)
        frames.append(
            {
                "stage": stage,
                "visible_through": at.isoformat(),
                "visible_through_unix": int(at.timestamp()),
            }
        )
    return frames
'''
new_frames = '''_FRAME_STAGE_ORDER = (
    "context",
    "signal",
    "entry",
    "mfe",
    "mae",
    "exit",
    "post_exit",
)
_MARKER_KIND_ORDER = ("signal", "entry", "mfe", "mae", "exit")


def _frame_sequence(episode: _Episode) -> list[dict[str, object]]:
    """Emit replay frames in evidence-time order with deterministic ties.

    MFE and MAE are both post-entry observations and either may occur first.
    Therefore the timestamp is authoritative; semantic stage order is only a
    deterministic tie-break when two observations share the same closed bar.
    """

    ordered = [
        ("context", episode.bars[0].closed_at),
        ("signal", episode.trade.signal_at),
        ("entry", episode.trade.filled_at),
        ("mfe", episode.mfe_at),
        ("mae", episode.mae_at),
        ("exit", episode.trade.exited_at),
        ("post_exit", episode.bars[-1].closed_at),
    ]
    unique: list[tuple[str, datetime]] = []
    seen: set[tuple[str, datetime]] = set()
    for stage, at in ordered:
        key = (stage, at)
        if key in seen:
            continue
        seen.add(key)
        unique.append((stage, at))
    stage_rank = {stage: index for index, stage in enumerate(_FRAME_STAGE_ORDER)}
    unique.sort(key=lambda item: (item[1], stage_rank[item[0]]))
    return [
        {
            "stage": stage,
            "visible_through": at.isoformat(),
            "visible_through_unix": int(at.timestamp()),
        }
        for stage, at in unique
    ]


def _sorted_markers(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    """Order chart markers by exact evidence timestamp with stable ties."""

    kind_rank = {kind: index for index, kind in enumerate(_MARKER_KIND_ORDER)}
    return sorted(
        rows,
        key=lambda row: (
            cast(str, row["at"]),
            kind_rank[cast(str, row["kind"])],
        ),
    )
'''
replace_once(story_path, old_frames, new_frames)


test_path = Path(
    "tests/infrastructure/trader_lab/test_architect_story_forensics_adjudication.py"
)
test_path.write_text(
    '''from __future__ import annotations

from datetime import UTC, datetime
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
''',
    encoding="utf-8",
)
