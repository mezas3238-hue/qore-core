#!/usr/bin/env python3
"""CIBO research sweep: preload immutable M5 evidence once, fork bounded workers.

Research-only runner. The underlying sovereign CIBO replay engine is unchanged.
Each variant is passed to cibo_trader_lab_three_mode_ceiling.main() with exactly
the same CLI arguments as the prior standalone Python process. Linux fork
inherits the verified in-memory M5 corpus (copy on write). Fail closed on any
missing/invalid input or child failure. No persistent untrusted pickle cache.
"""
from __future__ import annotations

import argparse
import functools
import json
import multiprocessing
import multiprocessing.connection
import os
import sys
import time
from collections import deque
from pathlib import Path

from qore.infrastructure.trader_lab import (
    cibo_market_atlas_journey_extractor_v1 as atlas,
)
import cibo_trader_lab_three_mode_ceiling as replay


def _roots(args: list[str]) -> dict[str, Path]:
    roots: dict[str, Path] = {}
    for index, token in enumerate(args):
        if token != "--lifecycle-source-root":
            continue
        if index + 1 >= len(args):
            raise ValueError("missing lifecycle source root")
        key, sep, value = args[index + 1].partition("=")
        if not sep or not key or not value or key in roots:
            raise ValueError("invalid or duplicate lifecycle source root")
        roots[key] = Path(value).resolve(strict=True)
    return roots


def _child(name: str, args: list[str]) -> None:
    # fork inherits the immutable, already verified M5 evidence and cached
    # load_raw_m5() results; each child builds its own isolated decision state.
    sys.argv = ["cibo_trader_lab_three_mode_ceiling.py", *args]
    started = time.monotonic()
    print("QORE_CIBO_BATCH_CASE_START " + json.dumps({"name": name}), flush=True)
    outcome = replay.main()
    if outcome not in (None, 0):
        raise RuntimeError(f"CIBO case {name!r} returned {outcome!r}")
    print(
        "QORE_CIBO_BATCH_CASE_DONE " + json.dumps(
            {"name": name, "elapsed_seconds": round(time.monotonic() - started, 3)}
        ),
        flush=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", required=True, type=Path)
    parser.add_argument("--workers", type=int, default=2)
    parsed = parser.parse_args()
    if not sys.platform.startswith("linux"):
        raise RuntimeError("CIBO preload sharing requires Linux fork")
    if parsed.workers < 1 or parsed.workers > 4:
        raise ValueError("workers must be in [1, 4] (prevent runner oversubscription)")
    cases = []
    names: set[str] = set()
    outputs: set[Path] = set()
    root_signature = None
    with parsed.cases.open(encoding="utf-8") as stream:
        for row in stream:
            if not row.strip():
                continue
            args = json.loads(row)
            if not isinstance(args, list) or not all(
                isinstance(value, str) for value in args
            ):
                raise ValueError("batch cases must contain JSON argument arrays")
            if "--output" not in args:
                raise ValueError("case requires explicit --output")
            output_idx = args.index("--output") + 1
            if output_idx >= len(args):
                raise ValueError("missing output path")
            output = Path(args[output_idx]).resolve()
            if output in outputs:
                raise ValueError("duplicate output path")
            outputs.add(output)
            case_name = output.stem
            if case_name in names:
                raise ValueError("duplicate case name")
            names.add(case_name)
            roots = _roots(args)
            signature = tuple(sorted((k, str(v)) for k, v in roots.items()))
            if root_signature is None:
                root_signature = signature
            elif signature != root_signature:
                raise ValueError("case source roots differ; cannot share verified M5")
            cases.append((case_name, args))
    if not cases:
        raise ValueError("empty research batch")

    started = time.monotonic()
    if root_signature:
        if set(dict(root_signature)) != replay._LIFECYCLE_SYMBOLS:
            raise ValueError("expected exactly six sovereign M5 symbol roots")
        # Every case receives the SAME read-only bytes as the original workflow.
        # Keep the source artifact SHA256 and custody validation in the YAML.
        shared_loader = functools.lru_cache(maxsize=8)(atlas.load_raw_m5)
        replay.load_raw_m5 = shared_loader
        for symbol, location in root_signature:
            evidence, _provenance = shared_loader(Path(location))
            if evidence.symbol != symbol:
                raise ValueError(f"Market Atlas symbol mismatch: {symbol}")
    preload = time.monotonic() - started
    print("QORE_CIBO_BATCH_PRELOAD " + json.dumps({
        "cases": len(cases),
        "workers": parsed.workers,
        "symbols": len(root_signature or ()),
        "elapsed_seconds": round(preload, 3),
        "architecture": "read-only-m5-copy-on-write-fork",
    }), flush=True)

    ctx = multiprocessing.get_context("fork")
    pending = deque(cases)
    running: dict[int, tuple[multiprocessing.Process, str]] = {}
    failures: list[str] = []
    try:
        while pending or running:
            while pending and len(running) < parsed.workers and not failures:
                name, argv = pending.popleft()
                process = ctx.Process(target=_child, args=(name, argv), name=name)
                process.start()
                if process.pid is None:
                    raise RuntimeError(f"failed to start case {name}")
                running[process.pid] = (process, name)
            if not running:
                break
            multiprocessing.connection.wait(
                [process.sentinel for process, _name in running.values()]
            )
            for pid, (process, name) in list(running.items()):
                if not process.sentinel or not process.exitcode is None:
                    process.join()
                    if process.exitcode:
                        failures.append(f"{name}: exit {process.exitcode}")
                    del running[pid]
            if failures:
                for process, _name in running.values():
                    process.terminate()
                for process, _name in running.values():
                    process.join()
                break
    finally:
        for process, _name in running.values():
            if process.is_alive():
                process.terminate()
            process.join()

    print("QORE_CIBO_BATCH_DONE " + json.dumps({
        "status": "FAIL" if failures else "PASS",
        "completed": len(cases) - len(pending) - len(failures),
        "failures": failures,
        "elapsed_seconds": round(time.monotonic() - started, 3),
    }), flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
