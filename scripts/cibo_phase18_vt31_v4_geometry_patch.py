"""Phase-18 serialization instrumentation for immutable VT31 V4 binding.

The source program is the exact historical Execution Binding V4 five-year
validator. This patch only exposes its already-computed selected trade rows in
the JSON payload. It does not alter signal selection, geometry, lifecycle,
risk arithmetic, path ordering, execution binding, or outcomes.
"""

from __future__ import annotations

from pathlib import Path

SOURCE_CODE_GIT_SHA = "cac38ed14f20e066536910145027426fd23f5939"
SOURCE_RELATIVE_PATH = (
    "scripts/vt31_nas100_structural_target_execution_binding_5y_v4.py"
)

_OLD = '''        "five_year_result": {
            "trade_count": len(selected),
            "metrics": metrics,
'''
_NEW = '''        "five_year_result": {
            "trade_count": len(selected),
            "trade_rows": selected,
            "metrics": metrics,
'''


def patch_source(source: str) -> str:
    count = source.count(_OLD)
    if count != 1:
        raise ValueError(
            "VT31 V4 source drift: expected one five_year_result block, "
            f"got {count}"
        )
    return source.replace(_OLD, _NEW, 1)


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
