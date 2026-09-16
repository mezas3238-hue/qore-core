"""Causal driver for consumed VT-31 pending LIMIT tick resolution.

This wrapper exists to validate the resolver with execution-causal self tests:
quotes before an executable LIMIT fill cannot stop a non-existent position, while
an exit-side quote tied to the fill millisecond is censored because BID/ASK
cross-stream order is unknowable. Consumed evidence only; no fresh access.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from vt31_pending_limit_tick_resolution import resolve_manifest, resolve_pending_window


def _tick(timestamp_ms: int, price: str) -> dict[str, object]:
    return {"timestamp_ms": timestamp_ms, "price": price}


def self_test() -> None:
    source = {
        "window_id": "follow-long",
        "parent_window_id": "parent-long",
        "side": "long",
        "entry": "100",
        "initial_stop": "99",
        "fixed_2r_target": "102",
        "tick_window_open_ms": 60_000,
        "tick_window_close_ms": 179_999,
    }
    seed = {
        "source_window": {
            "window_id": "parent-long",
            "tick_window_open_ms": 1,
            "tick_window_close_ms": 59_999,
        },
        "bid": [_tick(59_900, "100.2")],
        "ask": [_tick(59_900, "100.4")],
    }

    stopped_after_fill = {
        "source_window": dict(source),
        "bid": [_tick(70_000, "100.1"), _tick(121_000, "98.9")],
        "ask": [_tick(65_000, "100.2"), _tick(120_500, "99.9")],
    }
    result = resolve_pending_window(source, stopped_after_fill, seed)
    assert result["status"] == "initial-stop-in-fill-minute"
    assert result["fill_timestamp_ms"] == 120_500
    assert result["terminal_timestamp_ms"] == 121_000

    clear = {
        "source_window": dict(source),
        "bid": [_tick(70_000, "100.1"), _tick(121_000, "100.0"), _tick(130_000, "100.5")],
        "ask": [_tick(120_500, "99.9")],
    }
    result = resolve_pending_window(source, clear, seed)
    assert result["status"] == "executable-fill-minute-clear"

    # A stop-side quote below the stop before the later LIMIT fill is irrelevant:
    # there is no open position yet. The latest exit-side quote before fill wins.
    seed_pre_fill_below_stop = {
        "source_window": {
            "window_id": "parent-long",
            "tick_window_open_ms": 1,
            "tick_window_close_ms": 59_999,
        },
        "bid": [_tick(59_900, "98.8")],
        "ask": [_tick(59_900, "99.2")],
    }
    result = resolve_pending_window(source, clear, seed_pre_fill_below_stop)
    assert result["status"] == "executable-fill-minute-clear"

    # Opposite quote streams at the exact same millisecond cannot be causally
    # ordered, so a fill tied with a stop is censored rather than forced to -1.
    same_ms = {
        "source_window": dict(source),
        "bid": [_tick(70_000, "100.1"), _tick(120_500, "98.8")],
        "ask": [_tick(120_500, "99.9")],
    }
    result = resolve_pending_window(source, same_ms, seed)
    assert result["status"] == "unresolved-same-ms-cross-stream-order"
    assert result["terminal_r"] is None

    no_fill = {
        "source_window": dict(source),
        "bid": [_tick(80_000, "100.1")],
        "ask": [_tick(80_000, "100.2")],
    }
    result = resolve_pending_window(source, no_fill, seed)
    assert result["status"] == "no-executable-fill-through-pending-cutoff"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--acquisition-dir", type=Path)
    parser.add_argument("--seed-acquisition-dir", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        print("vt31 pending-limit causal driver self-test: PASS")
        return
    if args.manifest is None or args.acquisition_dir is None or args.seed_acquisition_dir is None or args.output is None:
        parser.error("manifest/acquisition/seed-acquisition/output are required unless --self-test")
    payload = resolve_manifest(args.manifest, args.acquisition_dir, args.seed_acquisition_dir, args.output)
    print(json.dumps(payload["counts"], sort_keys=True))


if __name__ == "__main__":
    main()
