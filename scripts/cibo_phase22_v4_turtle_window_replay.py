"""Exact V4 window adapter for the five frozen Turtle replay lanes."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from typing import Any

from cibo_phase22_turtle_window_replay import (
    bind_replay_evaluation_window,
    validate_source_report_window,
)

from qore.infrastructure.cibo_phase22_turtle_predecision_projection import (
    fresh_causal_active_ladder,
)
from qore.infrastructure.cibo_phase22_v4_governance import (
    PHASE22_V4_CANDIDATE,
    V4_CANDIDATE_ID,
)

_CONFIGS = {
    "R34_XAUUSD": ("XAUUSD", "phase18-xauusd-r34-geometry-trades.jsonl"),
    "R38_EURUSD": ("EURUSD", "phase18-eurusd-r38-geometry-trades.jsonl"),
    "R43_GBPUSD": ("GBPUSD", "phase18-gbpusd-r39-geometry-trades.jsonl"),
    "R38_GBPJPY": ("GBPJPY", "phase18-gbpjpy-r37-geometry-trades.jsonl"),
    "R42_AUDJPY": ("AUDJPY", "phase18-audjpy-r40-geometry-trades.jsonl"),
}
_START = PHASE22_V4_CANDIDATE.start_at
_END = PHASE22_V4_CANDIDATE.end_exclusive_at


def _load(path: Path) -> ModuleType:
    if not path.is_file():
        raise ValueError("V4 Turtle frozen module missing")
    name = "qore_phase22_v4_" + hashlib.sha256(
        str(path.resolve()).encode()
    ).hexdigest()[:16]
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ValueError("V4 Turtle module cannot load")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(name, None)
        raise
    return module


def _aware(raw: object, field: str) -> datetime:
    value = datetime.fromisoformat(str(raw)).astimezone(UTC)
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"V4 Turtle {field} must be timezone-aware")
    return value


def _rows(path: Path) -> tuple[dict[str, Any], ...]:
    if not path.is_file():
        raise ValueError("V4 Turtle geometry serialization missing")
    result: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError("V4 Turtle geometry row must be object")
        result.append(row)
    return tuple(result)


def _validate(rows: tuple[dict[str, Any], ...], trader_id: str) -> None:
    prior: tuple[datetime, str] | None = None
    for index, row in enumerate(rows):
        signal = _aware(row["signal_at"], "signal_at")
        entry = _aware(row["entry_at"], "entry_at")
        exit_at = _aware(row["exit_at"], "exit_at")
        if not _START <= signal < _END:
            raise ValueError(
                f"{trader_id} V4 signal outside frozen window row={index}"
            )
        if entry < signal or exit_at <= entry:
            raise ValueError(f"{trader_id} V4 chronology invalid row={index}")
        side = str(row.get("side", "")).lower()
        if side not in {"long", "short"}:
            raise ValueError(f"{trader_id} V4 side invalid row={index}")
        identity = (signal, side)
        if prior is not None and identity < prior:
            raise ValueError(f"{trader_id} V4 geometry not chronological")
        prior = identity


def run_v4(
    *,
    trader_id: str,
    module_path: Path,
    raw_root: Path,
    target_root: Path,
    cognitive_root: Path,
    freeze_root: Path,
    output: Path,
) -> dict[str, object]:
    symbol, geometry_name = _CONFIGS[trader_id]
    module = _load(module_path)
    run = getattr(module, "run", None)
    if not callable(run):
        raise ValueError("V4 Turtle module has no run")
    if not hasattr(module, "EVAL_OPEN") or not hasattr(module, "EVAL_CLOSE"):
        raise ValueError("V4 Turtle module lacks evaluation window")

    output.mkdir(parents=True, exist_ok=True)
    with bind_replay_evaluation_window(
        module,
        start=_START,
        end=_END,
    ) as bound_surfaces:
        with fresh_causal_active_ladder(module):
            report = run(
                raw_root,
                target_root,
                cognitive_root,
                freeze_root,
                output,
            )
    validate_source_report_window(report=report, start=_START, end=_END)
    geometry_path = output / geometry_name
    rows = _rows(geometry_path)
    _validate(rows, trader_id)

    payload = {
        "schema": "qore.cibo.phase22.v4-turtle-window-replay.v1",
        "candidate_id": V4_CANDIDATE_ID,
        "trader_id": trader_id,
        "symbol": symbol,
        "window": {
            "start": _START.isoformat(),
            "end_exclusive": _END.isoformat(),
        },
        "row_count": len(rows),
        "geometry_filename": geometry_name,
        "geometry_sha256": (
            "sha256:" + hashlib.sha256(geometry_path.read_bytes()).hexdigest()
        ),
        "source_module_sha256": (
            "sha256:" + hashlib.sha256(module_path.read_bytes()).hexdigest()
        ),
        "bound_eval_surfaces": list(bound_surfaces),
        "subordinate_setup_window_bound": "r3" in bound_surfaces,
        "future_outcomes_masked_predecision": True,
        "methodology_parameters_changed": False,
        "legacy_trader_sizing_used_for_cibo": False,
        "broker_mutation_performed": False,
        "fresh_outcomes_executed": True,
        "productive_authority": False,
    }
    (output / "phase22-v4-turtle-replay-receipt.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trader-id", choices=tuple(_CONFIGS), required=True)
    parser.add_argument("--module-path", type=Path, required=True)
    parser.add_argument("--raw-root", type=Path, required=True)
    parser.add_argument("--target-root", type=Path, required=True)
    parser.add_argument("--cognitive-root", type=Path, required=True)
    parser.add_argument("--freeze-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = run_v4(
        trader_id=args.trader_id,
        module_path=args.module_path,
        raw_root=args.raw_root,
        target_root=args.target_root,
        cognitive_root=args.cognitive_root,
        freeze_root=args.freeze_root,
        output=args.output,
    )
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
