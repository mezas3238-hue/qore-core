#!/usr/bin/env python3
"""Ultrafast multi-fold scientific replay runner for VT31 GitHub Trader Lab.

The runner executes immutable consumed folds in parallel and deliberately
defers per-fold Monte Carlo when the target replay exposes the canonical
specialist module. The stitched adjudicator owns the final 10,000-path Monte
Carlo, so repeating it for every fold/variant would add compute without adding
information.

Fresh Holdout is never opened by this utility.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import sys
import time
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from pathlib import Path
from typing import Any


def _parse_fold(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("fold must be NAME=PATH")
    name, raw = value.split("=", 1)
    if not name:
        raise argparse.ArgumentTypeError("fold name cannot be empty")
    return name, Path(raw)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _cache_key(
    target_script: Path,
    evidence: Path,
) -> str:
    digest = hashlib.sha256()
    digest.update(target_script.read_bytes())
    digest.update(b"\0")
    digest.update(_sha256_file(evidence).encode())
    digest.update(b"\0")
    digest.update(os.environ.get("GITHUB_SHA", "local").encode())
    return digest.hexdigest()


def _deferred_monte_carlo(
    _: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "algorithm": "deferred-to-stitched-adjudicator",
        "paths": 0,
        "block_length": 5,
        "positive_terminal_probability": "0",
        "p05_terminal_r": "0",
        "p50_terminal_r": "0",
        "p95_max_drawdown_r": "0",
    }


def _load_target(path: Path) -> Any:
    module_name = (
        "_qore_vt31_ultrafast_target_"
        + str(os.getpid())
        + "_"
        + hashlib.sha256(str(path).encode()).hexdigest()[:12]
    )
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load target script: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _run_fold(
    *,
    fold: str,
    evidence: str,
    target_script: str,
    output_dir: str,
    cache_dir: str,
) -> dict[str, object]:
    started = time.monotonic()
    evidence_path = Path(evidence).resolve()
    target_path = Path(target_script).resolve()
    fold_root = Path(output_dir).resolve() / "folds" / fold
    fold_root.mkdir(parents=True, exist_ok=True)
    result_path = fold_root / "result.json"

    key = _cache_key(target_path, evidence_path)
    cache_path = Path(cache_dir).resolve() / f"{fold}-{key}.json"
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    if cache_path.is_file():
        shutil.copy2(cache_path, result_path)
        return {
            "fold": fold,
            "status": "CACHE_HIT",
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "cache_key": key,
        }

    target = _load_target(target_path)
    specialist = getattr(target, "specialist", None)
    original_mc = None
    if specialist is not None and hasattr(specialist, "_monte_carlo"):
        original_mc = specialist._monte_carlo
        specialist._monte_carlo = _deferred_monte_carlo

    try:
        payload = target.replay(evidence_path)
    finally:
        if original_mc is not None:
            specialist._monte_carlo = original_mc

    if not isinstance(payload, dict):
        raise RuntimeError(f"{fold}: target replay did not return an object")
    governance = payload.get("governance", {})
    if governance.get("fresh_holdout_opened") is not False:
        raise RuntimeError(f"{fold}: Fresh Holdout governance is not sealed")
    if governance.get("position_sizing_used") is not False:
        raise RuntimeError(f"{fold}: sizing governance violated")

    encoded = json.dumps(payload, sort_keys=True, indent=2) + "\n"
    result_path.write_text(encoded, encoding="utf-8")
    cache_path.write_text(encoded, encoding="utf-8")
    return {
        "fold": fold,
        "status": "COMPUTED",
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "cache_key": key,
        "variant_count": len(payload.get("variants", {})),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-script", required=True, type=Path)
    parser.add_argument(
        "--fold",
        action="append",
        type=_parse_fold,
        required=True,
    )
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--cache-dir", required=True, type=Path)
    parser.add_argument("--heartbeat-seconds", type=float, default=1.0)
    args = parser.parse_args()

    folds = dict(args.fold)
    if len(folds) != len(args.fold):
        raise SystemExit("duplicate fold names are forbidden")
    if args.heartbeat_seconds <= 0:
        raise SystemExit("heartbeat must be positive")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.cache_dir.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    print(
        "QORE_TRADER_LAB_EVENT "
        + json.dumps(
            {
                "kind": "run.started",
                "folds": sorted(folds),
                "max_parallel_lanes": len(folds),
                "fresh_holdout_opened": False,
            },
            sort_keys=True,
        ),
        flush=True,
    )

    results: dict[str, dict[str, object]] = {}
    with ProcessPoolExecutor(max_workers=len(folds)) as pool:
        future_to_fold = {
            pool.submit(
                _run_fold,
                fold=fold,
                evidence=str(path),
                target_script=str(args.target_script),
                output_dir=str(args.output_dir),
                cache_dir=str(args.cache_dir),
            ): fold
            for fold, path in folds.items()
        }
        pending = set(future_to_fold)
        while pending:
            done, pending = wait(
                pending,
                timeout=args.heartbeat_seconds,
                return_when=FIRST_COMPLETED,
            )
            if not done:
                print(
                    "QORE_TRADER_LAB_EVENT "
                    + json.dumps(
                        {
                            "kind": "heartbeat",
                            "elapsed_seconds": round(
                                time.monotonic() - started,
                                3,
                            ),
                            "pending": sorted(
                                future_to_fold[item]
                                for item in pending
                            ),
                        },
                        sort_keys=True,
                    ),
                    flush=True,
                )
                continue
            for future in done:
                fold = future_to_fold[future]
                result = future.result()
                results[fold] = result
                print(
                    "QORE_TRADER_LAB_EVENT "
                    + json.dumps(
                        {
                            "kind": "fold.completed",
                            **result,
                        },
                        sort_keys=True,
                    ),
                    flush=True,
                )

    elapsed = time.monotonic() - started
    manifest = {
        "schema": "qore.vt31.ultrafast-scientific-replay-lab.v1",
        "target_script": str(args.target_script),
        "folds": {
            fold: results[fold]
            for fold in sorted(results)
        },
        "parallel_fold_count": len(folds),
        "elapsed_seconds": round(elapsed, 3),
        "monte_carlo": "deferred-to-stitched-adjudicator",
        "fresh_holdout_opened": False,
        "certification_claimed": False,
    }
    (args.output_dir / "manifest.json").write_text(
        json.dumps(manifest, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        "QORE_TRADER_LAB_FAST_HEADLINE "
        + json.dumps(manifest, sort_keys=True),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
