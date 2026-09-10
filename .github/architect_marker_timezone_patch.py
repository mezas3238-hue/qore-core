from __future__ import annotations

from pathlib import Path


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"expected exactly one replacement in {path}, found {count}")
    path.write_text(text.replace(old, new), encoding="utf-8")


story_path = Path("src/qore/infrastructure/trader_lab/first_cohort_story_forensics.py")
old_helper = '''def _sorted_markers(rows: list[dict[str, object]]) -> list[dict[str, object]]:
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
new_helper = '''def _sorted_markers(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    """Order chart markers by absolute evidence instant with stable ties."""

    kind_rank = {kind: index for index, kind in enumerate(_MARKER_KIND_ORDER)}

    def marker_key(row: dict[str, object]) -> tuple[datetime, int]:
        raw_at = cast(str, row["at"])
        parsed_at = datetime.fromisoformat(raw_at)
        if parsed_at.tzinfo is None or parsed_at.utcoffset() is None:
            raise FirstCohortStoryForensicsError("chart marker timestamp must be timezone-aware")
        return parsed_at.astimezone(UTC), kind_rank[cast(str, row["kind"])]

    return sorted(rows, key=marker_key)
'''
replace_once(story_path, old_helper, new_helper)


test_path = Path("tests/infrastructure/trader_lab/test_architect_story_forensics_adjudication.py")
old_import = "from datetime import UTC, datetime\n"
new_import = "from datetime import UTC, datetime, timedelta, timezone\n"
replace_once(test_path, old_import, new_import)

append = '''\n\ndef test_markers_sort_by_absolute_instant_across_timezone_offsets() -> None:\n    earlier_same_day = datetime(\n        2026, 1, 5, 13, 0, tzinfo=timezone(timedelta(hours=1))\n    )  # 12:00 UTC\n    later_utc = datetime(2026, 1, 5, 12, 30, tzinfo=UTC)\n    rows = _sorted_markers(\n        [\n            _marker("mae", later_utc, "MAE"),\n            _marker("mfe", earlier_same_day, "MFE"),\n        ]\n    )\n    assert [cast(str, row["kind"]) for row in rows] == ["mfe", "mae"]\n'''
text = test_path.read_text(encoding="utf-8")
if "test_markers_sort_by_absolute_instant_across_timezone_offsets" in text:
    raise SystemExit("timezone regression already present")
test_path.write_text(text + append, encoding="utf-8")
