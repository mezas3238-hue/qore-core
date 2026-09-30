"""Phase-18 side-channel geometry instrumentation for immutable VT31 rearm rows.

The frozen VT31 V4 lineage already computes each rearm setup's entry, initial
stop and structural target before the terminal outcome is simulated. Historical
rearm rows omitted those three causal fields from serialization.

This patch captures that already-computed geometry in a module side channel
keyed by signal_at. It deliberately does not add fields to the historical row,
so every downstream historical transform sees the exact original row shape.
"""

from __future__ import annotations

from pathlib import Path

SOURCE_CODE_GIT_SHA = "cac38ed14f20e066536910145027426fd23f5939"
SOURCE_RELATIVE_PATH = (
    "scripts/vt31_nas100_r5_corrective_management_frontier_v1.py"
)

_INIT_OLD = """    policy = Vt31R22ExecutionPolicy()
    raw_rows: list[dict[str, object]] = []
"""
_INIT_NEW = """    policy = Vt31R22ExecutionPolicy()
    global _PHASE18_REARM_GEOMETRY
    _PHASE18_REARM_GEOMETRY = {}
    raw_rows: list[dict[str, object]] = []
"""

_CAPTURE_OLD = """                "used_for_runtime_decision": False,
            }
        )
        raw_rows.append(row)
"""
_CAPTURE_NEW = """                "used_for_runtime_decision": False,
            }
        )
        phase18_signal_key = str(row["signal_at"])
        if phase18_signal_key in _PHASE18_REARM_GEOMETRY:
            raise ValueError("duplicate VT31 Phase-18 rearm signal")
        _PHASE18_REARM_GEOMETRY[phase18_signal_key] = (
            format(setup.entry_price, "f"),
            format(setup.stop_price, "f"),
            format(setup.target_price, "f"),
        )
        raw_rows.append(row)
"""


def patch_source(source: str) -> str:
    init_count = source.count(_INIT_OLD)
    capture_count = source.count(_CAPTURE_OLD)
    if init_count != 1 or capture_count != 1:
        raise ValueError(
            "VT31 rearm source drift: expected one init/capture block, "
            f"got {init_count}/{capture_count}"
        )
    source = source.replace(_INIT_OLD, _INIT_NEW, 1)
    return source.replace(_CAPTURE_OLD, _CAPTURE_NEW, 1)


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
