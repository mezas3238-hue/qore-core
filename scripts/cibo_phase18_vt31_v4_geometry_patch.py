"""Phase-18 serialization instrumentation for immutable VT31 V4 binding.

The source program is the exact historical Execution Binding V4 five-year
validator. The patch exposes selected trade rows while preserving the exact
authoritative metrics/Monte Carlo input shape. Geometry added only for Phase 18
is stripped from the rows used by certified V4 calculations.
"""

from __future__ import annotations

from pathlib import Path

SOURCE_CODE_GIT_SHA = "cac38ed14f20e066536910145027426fd23f5939"
SOURCE_RELATIVE_PATH = (
    "scripts/vt31_nas100_structural_target_execution_binding_5y_v4.py"
)

_SELECTED_OLD = '''    selected = [
        row for row in adjusted
        if START_DATE
        <= date.fromisoformat(cast(str, row["local_date"]))
        < END_EXCLUSIVE_DATE
    ]
    metrics = _metrics(selected)
'''

_SELECTED_NEW = '''    selected = [
        row for row in adjusted
        if START_DATE
        <= date.fromisoformat(cast(str, row["local_date"]))
        < END_EXCLUSIVE_DATE
    ]
    phase18_trade_rows = selected
    selected = []
    for phase18_row in phase18_trade_rows:
        authoritative_row = dict(phase18_row)
        if authoritative_row.pop(
            "_phase18_rearm_geometry_instrumented",
            False,
        ):
            authoritative_row.pop("entry", None)
            authoritative_row.pop("initial_stop", None)
            authoritative_row.pop("structural_target", None)
        selected.append(authoritative_row)
    metrics = _metrics(selected)
'''

_RESULT_OLD = '''        "five_year_result": {
            "trade_count": len(selected),
            "metrics": metrics,
'''

_RESULT_NEW = '''        "five_year_result": {
            "trade_count": len(selected),
            "trade_rows": phase18_trade_rows,
            "metrics": metrics,
'''


def patch_source(source: str) -> str:
    selected_count = source.count(_SELECTED_OLD)
    result_count = source.count(_RESULT_OLD)
    if selected_count != 1 or result_count != 1:
        raise ValueError(
            "VT31 V4 source drift: expected one selected block and one "
            f"five_year_result block, got {selected_count}/{result_count}"
        )
    source = source.replace(_SELECTED_OLD, _SELECTED_NEW, 1)
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
