"""Phase22 window adapter for frozen Turtle-Soup Trader replays.

The adapter changes only the evaluation window exposed by an already-frozen
geometry replay module. It does not alter entry logic, memories, target
selection, stop logic, risk overlays, market inputs or provider economics.

PARITY mode must regenerate the exact Phase18 population before FRESH mode may
be used by the one-shot Phase22 V2 examination.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from typing import Any

from qore.infrastructure.cibo_ce2i_holdout_registry import (
    ACTIVE_USD60_HOLDOUT_CANDIDATE,
)

PARITY_OPEN = datetime(2021, 9, 17, tzinfo=UTC)
PARITY_CLOSE = datetime(2026, 9, 17, tzinfo=UTC)
FRESH_CANDIDATE_ID = ACTIVE_USD60_HOLDOUT_CANDIDATE.candidate_id
FRESH_OPEN = ACTIVE_USD60_HOLDOUT_CANDIDATE.start_at
FRESH_CLOSE = ACTIVE_USD60_HOLDOUT_CANDIDATE.end_exclusive_at


@dataclass(frozen=True, slots=True)
class TurtleReplayConfig:
    trader_id: str
    expected_parity_rows: int
    geometry_filename: str
    symbol: str


CONFIGS = {
    "GBPJPY_R38": TurtleReplayConfig(
        trader_id="R38_GBPJPY",
        expected_parity_rows=897,
        geometry_filename="phase18-gbpjpy-r37-geometry-trades.jsonl",
        symbol="GBPJPY",
    ),
    "GBPUSD_R43": TurtleReplayConfig(
        trader_id="R43_GBPUSD",
        expected_parity_rows=907,
        geometry_filename="phase18-gbpusd-r39-geometry-trades.jsonl",
        symbol="GBPUSD",
    ),
    "AUDJPY_R42": TurtleReplayConfig(
        trader_id="R42_AUDJPY",
        expected_parity_rows=1039,
        geometry_filename="phase18-audjpy-r40-geometry-trades.jsonl",
        symbol="AUDJPY",
    ),
    "XAUUSD_R34": TurtleReplayConfig(
        trader_id="R34_XAUUSD",
        expected_parity_rows=921,
        geometry_filename="phase18-xauusd-r34-geometry-trades.jsonl",
        symbol="XAUUSD",
    ),
}


def _load_module(path: Path) -> ModuleType:
    if not path.is_file():
        raise ValueError(f"frozen replay module not found: {path}")
    module_name = (
        "qore_phase22_window_"
        + hashlib.sha256(str(path.resolve()).encode()).hexdigest()[:16]
    )
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ValueError("cannot load frozen replay module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    return module


def _read_jsonl(path: Path) -> tuple[dict[str, Any], ...]:
    return tuple(
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    )


def _window(mode: str) -> tuple[datetime, datetime]:
    if mode == "PARITY":
        return PARITY_OPEN, PARITY_CLOSE
    if mode == "FRESH":
        return FRESH_OPEN, FRESH_CLOSE
    raise ValueError("mode must be PARITY or FRESH")


def _timestamp(row: dict[str, Any], key: str) -> datetime:
    value = datetime.fromisoformat(str(row[key]))
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{key} must be timezone-aware")
    return value.astimezone(UTC)


def validate_window_rows(
    *,
    rows: tuple[dict[str, Any], ...],
    config: TurtleReplayConfig,
    mode: str,
) -> None:
    start, end = _window(mode)
    if mode == "PARITY" and len(rows) != config.expected_parity_rows:
        raise ValueError(
            f"{config.trader_id} parity population drift: "
            f"{len(rows)} != {config.expected_parity_rows}"
        )
    prior_identity: tuple[datetime, str] | None = None
    for index, row in enumerate(rows):
        signal_at = _timestamp(row, "signal_at")
        entry_at = _timestamp(row, "entry_at")
        exit_at = _timestamp(row, "exit_at")
        if not start <= signal_at < end:
            raise ValueError(
                f"{config.trader_id} signal outside {mode} window at row {index}"
            )
        if entry_at < signal_at:
            raise ValueError(
                f"{config.trader_id} entry precedes signal at row {index}"
            )
        if exit_at <= entry_at:
            raise ValueError(
                f"{config.trader_id} exit must follow entry at row {index}"
            )
        side = str(row.get("side", ""))
        if side not in {"long", "short"}:
            raise ValueError(
                f"{config.trader_id} invalid side at row {index}"
            )
        identity = (signal_at, side)
        if (
            mode == "FRESH"
            and prior_identity is not None
            and identity < prior_identity
        ):
            raise ValueError(
                f"{config.trader_id} geometry rows are not chronological"
            )
        prior_identity = identity


def run_window_replay(
    *,
    trader: str,
    mode: str,
    module_path: Path,
    raw_root: Path,
    target_root: Path,
    cognitive_root: Path,
    freeze_root: Path,
    output: Path,
) -> dict[str, Any]:
    config = CONFIGS[trader]
    start, end = _window(mode)
    module = _load_module(module_path)
    run = getattr(module, "run", None)
    if not callable(run):
        raise ValueError("frozen replay module does not expose run(...)")
    if not hasattr(module, "EVAL_OPEN") or not hasattr(module, "EVAL_CLOSE"):
        raise ValueError("frozen replay module has no evaluation window")

    original_open = module.EVAL_OPEN
    original_close = module.EVAL_CLOSE
    output.mkdir(parents=True, exist_ok=True)
    try:
        module.EVAL_OPEN = start
        module.EVAL_CLOSE = end
        report = run(
            raw_root,
            target_root,
            cognitive_root,
            freeze_root,
            output,
        )
    finally:
        module.EVAL_OPEN = original_open
        module.EVAL_CLOSE = original_close

    geometry_path = output / config.geometry_filename
    if not geometry_path.is_file():
        raise ValueError(
            f"{config.trader_id} geometry serialization missing: "
            f"{config.geometry_filename}"
        )
    rows = _read_jsonl(geometry_path)
    validate_window_rows(rows=rows, config=config, mode=mode)
    module_sha = hashlib.sha256(module_path.read_bytes()).hexdigest()
    geometry_sha = hashlib.sha256(geometry_path.read_bytes()).hexdigest()

    payload: dict[str, Any] = {
        "schema": "qore.cibo.phase22.turtle_window_replay.v1",
        "trader_id": config.trader_id,
        "symbol": config.symbol,
        "mode": mode,
        "window": {
            "start": start.isoformat(),
            "end_exclusive": end.isoformat(),
        },
        "row_count": len(rows),
        "expected_parity_rows": config.expected_parity_rows,
        "source_module_sha256": f"sha256:{module_sha}",
        "geometry_sha256": f"sha256:{geometry_sha}",
        "source_report_identity": (
            report.get("identity") if isinstance(report, dict) else None
        ),
        "methodology_parameters_changed": False,
        "legacy_trader_sizing_used_for_cibo": False,
        "provider_economics_claimed": False,
        "fresh_holdout_outcomes_executed": mode == "FRESH",
        "research_only": True,
        "live_authorized": False,
        "real_capital_authorized": False,
    }
    receipt = output / "phase22-window-replay-receipt.json"
    receipt.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trader", choices=tuple(CONFIGS), required=True)
    parser.add_argument("--mode", choices=("PARITY", "FRESH"), required=True)
    parser.add_argument("--module-path", type=Path, required=True)
    parser.add_argument("--raw-root", type=Path, required=True)
    parser.add_argument("--target-root", type=Path, required=True)
    parser.add_argument("--cognitive-root", type=Path, required=True)
    parser.add_argument("--freeze-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = run_window_replay(
        trader=args.trader,
        mode=args.mode,
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
