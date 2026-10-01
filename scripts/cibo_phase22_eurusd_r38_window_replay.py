"""Frozen-window adapter for the exact R38 EURUSD replay engine.

Only two windows are legal:
- PARITY: the already-consumed Phase18 five-year population;
- FRESH: the preregistered 2017H1 CIBO-policy holdout.

The adapter never changes R38 methodology parameters. FRESH execution is kept
out of the parity workflow and must be invoked only by the final governed
Phase22 runner after every Trader lane has parity evidence.
"""

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

SOURCE_CODE_GIT_SHA = "324fb91d44a6fa328e66de2e22ace7386630c7aa"
PARITY_OPEN = datetime(2021, 9, 17, tzinfo=UTC)
PARITY_CLOSE = datetime(2026, 9, 17, tzinfo=UTC)
FRESH_OPEN = datetime(2017, 1, 1, tzinfo=UTC)
FRESH_CLOSE = datetime(2017, 7, 1, tzinfo=UTC)
_ALLOWED = {
    "PARITY": (PARITY_OPEN, PARITY_CLOSE),
    "FRESH": (FRESH_OPEN, FRESH_CLOSE),
}


def replay_window(mode: str) -> tuple[datetime, datetime]:
    try:
        return _ALLOWED[mode]
    except KeyError as error:
        raise ValueError("EURUSD Phase22 mode must be PARITY or FRESH") from error


def _load_module(path: Path) -> ModuleType:
    if not path.is_file():
        raise ValueError("EURUSD Phase22 replay module path is missing")
    spec = importlib.util.spec_from_file_location(
        "cibo_phase22_eurusd_r38_exact_source",
        path,
    )
    if spec is None or spec.loader is None:
        raise ValueError("unable to load exact EURUSD R38 replay module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def run_window(
    *,
    mode: str,
    module_path: Path,
    raw_root: Path,
    target_root: Path,
    cognitive_root: Path,
    freeze_root: Path,
    output_dir: Path,
) -> dict[str, Any]:
    opened_at, closed_at = replay_window(mode)
    module = _load_module(module_path)
    for name in ("EVAL_OPEN", "EVAL_CLOSE", "run"):
        if not hasattr(module, name):
            raise ValueError(f"EURUSD exact replay module missing {name}")

    module.EVAL_OPEN = opened_at
    module.EVAL_CLOSE = closed_at
    result = module.run(
        raw_root,
        target_root,
        cognitive_root,
        freeze_root,
        output_dir,
    )
    if not isinstance(result, dict):
        raise ValueError("EURUSD exact replay returned non-object report")

    trades_path = output_dir / "phase18-eurusd-r38-geometry-trades.jsonl"
    report_path = output_dir / "phase18-eurusd-r38-geometry-report.json"
    if not trades_path.is_file() or not report_path.is_file():
        raise ValueError("EURUSD exact replay did not emit canonical geometry files")

    rows: list[dict[str, Any]] = []
    for raw in trades_path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        row = json.loads(raw)
        if not isinstance(row, dict):
            raise ValueError("EURUSD geometry row must be object")
        entry_at = datetime.fromisoformat(str(row["entry_at"]))
        if not (opened_at <= entry_at < closed_at):
            raise ValueError("EURUSD replay emitted trade outside frozen window")
        rows.append(row)

    if mode == "PARITY" and len(rows) != 863:
        raise ValueError("EURUSD Phase18 parity population drift")

    receipt = {
        "schema": "qore.cibo.phase22.eurusd-r38-window-replay.v1",
        "trader_id": "R38_EURUSD",
        "mode": mode,
        "source_code_git_sha": SOURCE_CODE_GIT_SHA,
        "window": {
            "open": opened_at.isoformat(),
            "close": closed_at.isoformat(),
        },
        "rows": len(rows),
        "geometry_sha256": _sha256(trades_path),
        "engine_report_sha256": _sha256(report_path),
        "methodology_parameters_modified": False,
        "window_is_preregistered": True,
        "fresh_holdout_accessed": mode == "FRESH",
        "fresh_outcomes_executed": mode == "FRESH",
        "productive_authority": False,
    }
    (output_dir / "phase22-eurusd-r38-window-replay-receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=tuple(_ALLOWED), required=True)
    parser.add_argument("--module-path", type=Path, required=True)
    parser.add_argument("--raw-root", type=Path, required=True)
    parser.add_argument("--target-root", type=Path, required=True)
    parser.add_argument("--cognitive-root", type=Path, required=True)
    parser.add_argument("--freeze-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    receipt = run_window(
        mode=args.mode,
        module_path=args.module_path,
        raw_root=args.raw_root,
        target_root=args.target_root,
        cognitive_root=args.cognitive_root,
        freeze_root=args.freeze_root,
        output_dir=args.output_dir,
    )
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
