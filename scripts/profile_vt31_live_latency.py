# ruff: noqa: E402, I001, N813, UP035
from __future__ import annotations

import argparse
import gzip
import json
import sys
import time
from collections import defaultdict
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Callable

import MetaTrader5 as mt5  # type: ignore

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import vt31_nas100_live_policy as policy  # noqa: E402
from qore.infrastructure.vt31_nas100_live import (  # noqa: E402
    Vt31Nas100M1Cache,
    _evidence_fingerprint,
    _evidence_prefix_hasher,
    _finish_evidence_fingerprint,
)
from qore.infrastructure.vt31_nas100_state import Vt31Nas100LiveState  # noqa: E402
from qore.infrastructure.traders.vt31_nas100_cibo_market_memory import (  # noqa: E402
    cibo_market_memory_fingerprint,
)


def _timed(
    owner: Any,
    name: str,
    totals: dict[str, int],
    calls: dict[str, int],
) -> Callable[..., Any]:
    original: Callable[..., Any] = getattr(owner, name)

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        started = time.perf_counter_ns()
        try:
            return original(*args, **kwargs)
        finally:
            totals[name] += time.perf_counter_ns() - started
            calls[name] += 1

    setattr(owner, name, wrapper)
    return original


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--anchors",
        nargs="+",
        default=[
            "2026-09-22T14:20:00+00:00",
            "2026-09-22T14:21:00+00:00",
            "2026-09-22T14:22:00+00:00",
            "2026-09-22T14:23:00+00:00",
            "2026-09-22T14:24:00+00:00",
            "2026-09-22T14:25:00+00:00",
            "2026-09-22T14:26:00+00:00",
        ],
    )
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--export-fixture", type=Path)
    args = parser.parse_args()

    if not mt5.initialize():
        raise SystemExit(f"MT5 initialize failed: {mt5.last_error()}")
    try:
        now = datetime.now(UTC)
        cache = Vt31Nas100M1Cache()
        preload_started = time.perf_counter_ns()
        cache.preload(mt5, now=now)
        preload_ns = time.perf_counter_ns() - preload_started

        if args.export_fixture is not None:
            anchor = datetime.fromisoformat(args.anchors[-1]).astimezone(UTC)
            fixture_bars = cache.closed_m1(through=anchor)[-5001:]
            payload = {
                "schema": "qore.vt31.live_replay.v1",
                "anchor": anchor.isoformat(),
                "bars": [
                    {
                        "opened_at": bar.opened_at.isoformat(),
                        "open": bar.open,
                        "high": bar.high,
                        "low": bar.low,
                        "close": bar.close,
                    }
                    for bar in fixture_bars
                ],
            }
            args.export_fixture.parent.mkdir(parents=True, exist_ok=True)
            with gzip.open(args.export_fixture, "wt", encoding="utf-8") as handle:
                json.dump(payload, handle, separators=(",", ":"))

        warm_started = time.perf_counter_ns()
        cibo_market_memory_fingerprint()
        warm_ns = time.perf_counter_ns() - warm_started
        output: dict[str, Any] = {
            "probe": "vt31-live-latency-read-only",
            "startup_memory_warm_ms": warm_ns / 1_000_000,
            "preload_ms": preload_ns / 1_000_000,
            "anchors": [],
        }
        for value in args.anchors:
            anchor = datetime.fromisoformat(value).astimezone(UTC)
            prefix = cache.closed_m1(
                through=anchor - timedelta(minutes=1)
            )
            if args.limit:
                prefix = prefix[-args.limit:]
            prepare_started = time.perf_counter_ns()
            prefix_hasher = _evidence_prefix_hasher(prefix)
            prefix_digest = prefix_hasher.copy()
            prefix_digest.update(b"]")
            prepared_context = policy.prepare_live_context(
                prefix,
                evidence_fingerprint=prefix_digest.hexdigest(),
            )
            prepare_ns = time.perf_counter_ns() - prepare_started

            totals: dict[str, int] = defaultdict(int)
            calls: dict[str, int] = defaultdict(int)

            policy.evaluate_vt31_r2_2_source = (
                __import__(
                    "qore.infrastructure.traders.vt31_silver_bullet_r2_2",
                    fromlist=["evaluate_vt31_r2_2_source"],
                ).evaluate_vt31_r2_2_source
            )
            patches = [
                (
                    policy,
                    "evaluate_vt31_r2_2_source",
                    _timed(policy, "evaluate_vt31_r2_2_source", totals, calls),
                ),
                (
                    policy.specialist,
                    "_context_map",
                    _timed(policy.specialist, "_context_map", totals, calls),
                ),
                (
                    policy.specialist,
                    "_state_snapshot",
                    _timed(policy.specialist, "_state_snapshot", totals, calls),
                ),
                (
                    policy.oco,
                    "_candidate_order",
                    _timed(policy.oco, "_candidate_order", totals, calls),
                ),
                (
                    policy.hybrid,
                    "_activation_setup",
                    _timed(policy.hybrid, "_activation_setup", totals, calls),
                ),
            ]

            closed_started = time.perf_counter_ns()
            closed = cache.closed_m1(through=anchor)
            if args.limit:
                closed = closed[-(args.limit + 1):]
            closed_ns = time.perf_counter_ns() - closed_started

            fingerprint_started = time.perf_counter_ns()
            if closed[:-1] != prefix:
                raise RuntimeError("prepared evidence prefix drift")
            fingerprint = _finish_evidence_fingerprint(
                prefix_hasher,
                closed[-1],
                has_prefix=bool(prefix),
            )
            fingerprint_ns = time.perf_counter_ns() - fingerprint_started
            if fingerprint != _evidence_fingerprint(closed):
                raise RuntimeError("incremental evidence fingerprint mismatch")

            evaluate_started = time.perf_counter_ns()
            basket, reason = policy.evaluate_live_basket(
                closed_m1=closed,
                evidence_fingerprint=fingerprint,
                live_state=Vt31Nas100LiveState(),
                prepared_context=prepared_context,
            )
            evaluate_ns = time.perf_counter_ns() - evaluate_started
            output["anchors"].append(
                {
                    "anchor": anchor.isoformat(),
                    "closed_bars": len(closed),
                    "prearm_prepare_ms": prepare_ns / 1_000_000,
                    "closed_m1_ms": closed_ns / 1_000_000,
                    "fingerprint_ms": fingerprint_ns / 1_000_000,
                    "strategy_ms": evaluate_ns / 1_000_000,
                    "reason": reason,
                    "basket": None if basket is None else asdict(basket),
                    "calls": dict(calls),
                    "component_ms": {
                        key: value_ns / 1_000_000 for key, value_ns in totals.items()
                    },
                }
            )
            for owner, name, original in patches:
                setattr(owner, name, original)
        print(json.dumps(output, sort_keys=True, default=str))
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
