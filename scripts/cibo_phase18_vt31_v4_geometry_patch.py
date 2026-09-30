"""Phase-18 serialization instrumentation for immutable VT31 V4 binding.

The historical V4 validator must remain byte-for-byte equivalent in economic
behavior. Rearm geometry needed by Phase 18 is captured out-of-band while the
frozen rearm setup already exists, then merged only into a separate serialized
copy after the original physical execution binding has completed.

Historical rows are never enriched before any historical transform.
"""

from __future__ import annotations

from pathlib import Path

SOURCE_CODE_GIT_SHA = "cac38ed14f20e066536910145027426fd23f5939"
SOURCE_RELATIVE_PATH = (
    "scripts/vt31_nas100_structural_target_execution_binding_5y_v4.py"
)

_PHYSICALIZE_OLD = """    adjusted, binding_diag = physical._physicalize(rows, by_day=by_day)
    selected = [
        row for row in adjusted
        if START_DATE
        <= date.fromisoformat(cast(str, row["local_date"]))
        < END_EXCLUSIVE_DATE
    ]
    metrics = _metrics(selected)
"""

_PHYSICALIZE_NEW = """    phase18_rearm_geometry = dict(
        getattr(residual.corrective, "_PHASE18_REARM_GEOMETRY", {})
    )
    adjusted, binding_diag = physical._physicalize(rows, by_day=by_day)
    phase18_adjusted = []
    for authoritative_row in adjusted:
        phase18_row = dict(authoritative_row)
        geometry = phase18_rearm_geometry.get(str(authoritative_row["signal_at"]))
        if geometry is not None:
            (
                phase18_row["entry"],
                phase18_row["initial_stop"],
                phase18_row["structural_target"],
            ) = geometry
        phase18_adjusted.append(phase18_row)

    selected = [
        row for row in adjusted
        if START_DATE
        <= date.fromisoformat(cast(str, row["local_date"]))
        < END_EXCLUSIVE_DATE
    ]
    phase18_trade_rows = [
        row for row in phase18_adjusted
        if START_DATE
        <= date.fromisoformat(cast(str, row["local_date"]))
        < END_EXCLUSIVE_DATE
    ]
    if len(phase18_trade_rows) != len(selected):
        raise ValueError("VT31 Phase-18 row population drift")
    metrics = _metrics(selected)
"""

_RESULT_OLD = """        "five_year_result": {
            "trade_count": len(selected),
            "metrics": metrics,
"""

_RESULT_NEW = """        "five_year_result": {
            "trade_count": len(selected),
            "trade_rows": phase18_trade_rows,
            "metrics": metrics,
"""


def patch_source(source: str) -> str:
    physicalize_count = source.count(_PHYSICALIZE_OLD)
    result_count = source.count(_RESULT_OLD)
    if physicalize_count != 1 or result_count != 1:
        raise ValueError(
            "VT31 V4 source drift: expected one physicalize/selected block "
            f"and one five_year_result block, got "
            f"{physicalize_count}/{result_count}"
        )
    source = source.replace(_PHYSICALIZE_OLD, _PHYSICALIZE_NEW, 1)
    return source.replace(_RESULT_OLD, _RESULT_NEW, 1)


def patch_file(source_path: Path, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        patch_source(source_path.read_text(encoding="utf-8")),
        encoding="utf-8",
    )


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    patch_file(args.source, args.output)


if __name__ == "__main__":
    main()
