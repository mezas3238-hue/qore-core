"""Phase-18 geometry instrumentation for immutable VT31 rearm rows.

The frozen VT31 V4 lineage already computes each rearm setup's entry, initial
stop and structural target before the terminal outcome is simulated. Historical
rearm rows omitted those three causal fields from serialization. This patch
copies the already-computed setup geometry into the row; it does not change
authorization, selection, management, sizing, outcomes, or ordering.
"""

from __future__ import annotations

from pathlib import Path

SOURCE_CODE_GIT_SHA = "cac38ed14f20e066536910145027426fd23f5939"
SOURCE_RELATIVE_PATH = (
    "scripts/vt31_nas100_r5_corrective_management_frontier_v1.py"
)

_OLD = '''            {
                "local_date": local_day.isoformat(),
                "rearm_quality_score": score,
'''
_NEW = '''            {
                "local_date": local_day.isoformat(),
                "_phase18_rearm_geometry_instrumented": True,
                "entry": format(setup.entry_price, "f"),
                "initial_stop": format(setup.stop_price, "f"),
                "structural_target": format(setup.target_price, "f"),
                "rearm_quality_score": score,
'''


def patch_source(source: str) -> str:
    count = source.count(_OLD)
    if count != 1:
        raise ValueError(
            "VT31 rearm source drift: expected one rearm row-update block, "
            f"got {count}"
        )
    return source.replace(_OLD, _NEW, 1)


def patch_file(source_path: Path, output_path: Path) -> None:
    source = source_path.read_text(encoding="utf-8")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(patch_source(source), encoding="utf-8")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    patch_file(args.source, args.output)


if __name__ == "__main__":
    main()
