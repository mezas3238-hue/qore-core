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
import gzip
import hashlib
import json
import multiprocessing
import multiprocessing.connection
import os
import sys
import time
from bisect import bisect_left, bisect_right
from collections import deque
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.trader_lab import (
    cibo_market_atlas_journey_extractor_v1 as atlas,
)
from qore.infrastructure.cibo_single_account_manifest_settlement import (
    manifest_row_to_shadow_outcome_observation,
)
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import (
    Bar, Evidence,
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
        roots[key] = Path(value).resolve()
    return roots


def _arg_value(args: list[str], flag: str) -> str:
    if flag not in args:
        raise ValueError(f"missing required batch flag {flag}")
    index = args.index(flag) + 1
    if index >= len(args):
        raise ValueError(f"missing value for {flag}")
    return args[index]


def _fingerprint(cases: list[tuple[str, list[str]]]) -> tuple[str, dict]:
    """Bind cache to exact manifest bytes, source artifact digests and code."""
    manifests = {Path(_arg_value(args, "--manifest")).resolve()
                 for _, args in cases}
    if len(manifests) != 1:
        raise ValueError("all batch cases must share a sovereign manifest")
    manifest_path = next(iter(manifests))
    raw = manifest_path.read_bytes()
    manifest = json.loads(raw)
    if not isinstance(manifest.get("opportunities"), list):
        raise ValueError("M5 preparation requires manifest opportunities")
    artifacts = {}
    for symbol in sorted(replay._LIFECYCLE_SYMBOLS):
        digest = os.environ.get(f"ATLAS_{symbol}_DIGEST")
        if not digest or not digest.startswith("sha256:") or len(digest) != 71:
            raise ValueError(f"missing verified artifact digest: {symbol}")
        artifacts[symbol] = digest
    code_modules = [
        Path(__file__), Path(replay.__file__), Path(atlas.__file__),
        Path(sys.modules["qore.infrastructure.cibo_position_lifecycle"].__file__),
        Path(sys.modules["qore.infrastructure.cibo_single_account_manifest_settlement"].__file__),
        Path(sys.modules["qore.infrastructure.cibo_single_account_manifest_economics"].__file__),
    ]
    source = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
              for p in code_modules}
    identity = {
        "schema": "qore.cibo.ultrafast.m5-trade-window.v1",
        "manifest_sha256": hashlib.sha256(raw).hexdigest(),
        "atlas_artifact_sha256": artifacts,
        "source_sha256": source,
    }
    digest = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    return digest, manifest


def _prune_per_trade(evidence: Evidence, rows: list[dict]) -> Evidence:
    """Lossless for every manifest trade: union of its exact original M5 slices."""
    if not evidence.bars:
        raise ValueError("empty sovereign M5 bars")
    opened = tuple(bar.opened_at for bar in evidence.bars)
    closed = tuple(bar.closed_at for bar in evidence.bars)
    selected = bytearray(len(evidence.bars))
    for row in rows:
        outcome = manifest_row_to_shadow_outcome_observation(row)
        start = bisect_left(opened, outcome.entry_at)
        end = bisect_right(closed, outcome.exit_at)
        if start < end:
            selected[start:end] = bytes([1]) * (end - start)
    slim = tuple(bar for i, bar in enumerate(evidence.bars) if selected[i])
    if not slim:
        slim = evidence.bars[:1]
    return Evidence(symbol=evidence.symbol, digits=evidence.digits, bars=slim)


def _encode(prepared: dict[str, Evidence], fingerprint: str) -> dict:
    return {
        "schema": "qore.cibo.ultrafast.pruned-m5.v1",
        "fingerprint": fingerprint,
        "symbols": {
            key: {
                "digits": evidence.digits,
                "bars": [[bar.opened_at.isoformat(), bar.closed_at.isoformat(),
                          str(bar.open), str(bar.high), str(bar.low), str(bar.close)]
                         for bar in evidence.bars],
            }
            for key, evidence in sorted(prepared.items())
        },
    }


def _decode(payload: dict, fingerprint: str) -> dict[str, Evidence]:
    if (payload.get("schema") != "qore.cibo.ultrafast.pruned-m5.v1"
            or payload.get("fingerprint") != fingerprint):
        raise ValueError("stale or tampered prepared M5 source cache")
    source = payload.get("symbols")
    if not isinstance(source, dict) or set(source) != replay._LIFECYCLE_SYMBOLS:
        raise ValueError("incorrect prepared M5 symbol set")
    result = {}
    for symbol, item in sorted(source.items()):
        bars = tuple(Bar(
            opened_at=datetime.fromisoformat(row[0]),
            closed_at=datetime.fromisoformat(row[1]),
            open=Decimal(row[2]), high=Decimal(row[3]),
            low=Decimal(row[4]), close=Decimal(row[5]),
        ) for row in item["bars"])
        if not bars or any(
            bar.opened_at.tzinfo is None or bar.closed_at.tzinfo is None
            or bar.closed_at <= bar.opened_at
            for bar in bars
        ) or any(a.opened_at >= b.opened_at for a, b in zip(bars, bars[1:])):
            raise ValueError("invalid prepared M5 chronology")
        result[symbol] = Evidence(
            symbol=symbol, digits=int(item["digits"]), bars=bars
        )
    return result


def _load_or_prepare(
    cases: list[tuple[str, list[str]]],
    roots: tuple[tuple[str, str], ...],
    cache_dir: Path,
) -> None:
    start = time.monotonic()
    fingerprint, manifest = _fingerprint(cases)
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / ("m5-" + fingerprint + ".json.gz")
    if cache_file.is_file():
        with gzip.open(cache_file, "rt", encoding="utf-8") as reader:
            cached = _decode(json.load(reader), fingerprint)
        cache_status = "hit"
    else:
        by_symbol = {}
        for row in manifest["opportunities"]:
            symbol = str(row["qore_symbol"])
            if symbol not in replay._LIFECYCLE_SYMBOLS:
                raise ValueError(f"unexpected manifest symbol: {symbol}")
            by_symbol.setdefault(symbol, []).append(row)
        cached = {}
        original_loader = atlas.load_raw_m5
        retained = {}
        for symbol, location in roots:
            evidence, _provenance = original_loader(Path(location))
            if evidence.symbol != symbol:
                raise ValueError(f"Market Atlas symbol mismatch: {symbol}")
            cached[symbol] = _prune_per_trade(evidence, by_symbol.get(symbol, []))
            retained[symbol] = {
                "full": len(evidence.bars),
                "pruned": len(cached[symbol].bars),
            }
        data = _encode(cached, fingerprint)
        temporary = cache_file.with_suffix(".tmp")
        with gzip.open(temporary, "wt", encoding="utf-8", compresslevel=3) as stream:
            json.dump(data, stream, separators=(",", ":"))
        os.replace(temporary, cache_file)
        cache_status = "built"
        print("QORE_CIBO_ULTRA_WINDOW_RETENTION " + json.dumps(retained), flush=True)
    lookup = {
        Path(location).resolve(): (cached[symbol], {"ultrafast": cache_status})
        for symbol, location in roots
    }

    def cached_loader(root: Path):
        target = Path(root).resolve()
        if target not in lookup:
            raise ValueError(f"prepared M5 requested outside fingerprinted roots: {target}")
        return lookup[target]

    replay.load_raw_m5 = functools.lru_cache(maxsize=8)(cached_loader)
    print("QORE_CIBO_ULTRA_M5 " + json.dumps({
        "status": cache_status,
        "fingerprint": fingerprint,
        "bars": {symbol: len(e.bars) for symbol, e in cached.items()},
        "elapsed_seconds": round(time.monotonic() - start, 3),
    }), flush=True)


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
    parser.add_argument("--m5-cache-dir", type=Path)
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
        if parsed.m5_cache_dir is not None:
            _load_or_prepare(cases, root_signature, parsed.m5_cache_dir)
        else:
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
