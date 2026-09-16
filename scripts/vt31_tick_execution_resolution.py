"""Fail-closed execution resolution for consumed VT-31 same-M1 ambiguity.

The resolver is intentionally narrow. It consumes only already-acquired BID/ASK
historical ticks for already-consumed R5/R6/R8 windows. It does not discover new
setups, alter R8 quality rules, open a new holdout, authorize live trading, or
impute missing quote history.

Execution semantics frozen here:
- long pending entry is a BUY LIMIT and requires ASK <= entry;
- short pending entry is a SELL LIMIT and requires BID >= entry;
- after a long fill, stop/target protection is evaluated on BID;
- after a short fill, stop/target protection is evaluated on ASK;
- events on opposite quote streams sharing the same millisecond are unordered and
  therefore censored rather than guessed;
- limit entry economics use the frozen limit price, never optimistic price
  improvement from a historical quote crossing through the limit.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable


class TickResolutionError(RuntimeError):
    """Raised when immutable consumed tick evidence is malformed."""


def _price(tick: dict[str, object]) -> Decimal:
    value = tick.get("price")
    if not isinstance(value, str):
        raise TickResolutionError("tick price must be a decimal string")
    parsed = Decimal(value)
    if parsed <= 0:
        raise TickResolutionError("tick price must be positive")
    return parsed


def _timestamp(tick: dict[str, object]) -> int:
    value = tick.get("timestamp_ms")
    if type(value) is not int or value <= 0:
        raise TickResolutionError("tick timestamp_ms must be a positive integer")
    return value


def _validated_stream(
    evidence: dict[str, object], name: str, opened_ms: int, closed_ms: int
) -> tuple[dict[str, object], ...]:
    raw = evidence.get(name)
    if not isinstance(raw, list):
        raise TickResolutionError(f"{name} stream is missing")
    result: list[dict[str, object]] = []
    previous: int | None = None
    for item in raw:
        if not isinstance(item, dict):
            raise TickResolutionError(f"{name} tick is malformed")
        timestamp = _timestamp(item)
        _price(item)
        if not opened_ms <= timestamp <= closed_ms:
            raise TickResolutionError(f"{name} tick escaped source window")
        if previous is not None and timestamp < previous:
            raise TickResolutionError(f"{name} stream must be chronological")
        previous = timestamp
        result.append(item)
    return tuple(result)


def _first_matching(
    stream: tuple[dict[str, object], ...], predicate: Callable[[Decimal], bool]
) -> dict[str, object] | None:
    for tick in stream:
        if predicate(_price(tick)):
            return tick
    return None


def _first_matching_at_or_after(
    stream: tuple[dict[str, object], ...],
    timestamp_ms: int,
    predicate: Callable[[Decimal], bool],
) -> dict[str, object] | None:
    for tick in stream:
        if _timestamp(tick) < timestamp_ms:
            continue
        if predicate(_price(tick)):
            return tick
    return None


def resolve_window(
    source_window: dict[str, object], evidence: dict[str, object]
) -> dict[str, object]:
    """Resolve one consumed fill-bar ambiguity without optimistic path inference."""
    window_id = source_window.get("window_id")
    if not isinstance(window_id, str) or not window_id:
        raise TickResolutionError("source window id is malformed")
    evidence_source = evidence.get("source_window")
    if not isinstance(evidence_source, dict) or evidence_source.get("window_id") != window_id:
        raise TickResolutionError("evidence/source window identity mismatch")

    side = source_window.get("side")
    if side not in {"long", "short"}:
        raise TickResolutionError("source side must be long or short")
    opened_ms = source_window.get("tick_window_open_ms")
    closed_ms = source_window.get("tick_window_close_ms")
    if type(opened_ms) is not int or type(closed_ms) is not int or closed_ms <= opened_ms:
        raise TickResolutionError("source tick boundaries are malformed")

    try:
        entry = Decimal(str(source_window["entry"]))
        stop = Decimal(str(source_window["initial_stop"]))
        target = Decimal(str(source_window["fixed_2r_target"]))
    except (KeyError, ArithmeticError, ValueError) as error:
        raise TickResolutionError("source prices are malformed") from error
    if min(entry, stop, target) <= 0:
        raise TickResolutionError("source prices must be positive")
    if side == "long" and not stop < entry < target:
        raise TickResolutionError("long stop/entry/target ordering is invalid")
    if side == "short" and not target < entry < stop:
        raise TickResolutionError("short target/entry/stop ordering is invalid")

    bid = _validated_stream(evidence, "bid", opened_ms, closed_ms)
    ask = _validated_stream(evidence, "ask", opened_ms, closed_ms)
    if not bid or not ask:
        return {
            "window_id": window_id,
            "status": "unresolved-missing-quote-side",
            "side": side,
            "fill_timestamp_ms": None,
            "terminal_timestamp_ms": None,
            "terminal_r": None,
        }

    if side == "long":
        fill_stream = ask
        fill_tick = _first_matching(fill_stream, lambda price: price <= entry)
        exit_stream = bid
        stop_predicate = lambda price: price <= stop
        target_predicate = lambda price: price >= target
        fill_quote_side = "ASK"
        exit_quote_side = "BID"
    else:
        fill_stream = bid
        fill_tick = _first_matching(fill_stream, lambda price: price >= entry)
        exit_stream = ask
        stop_predicate = lambda price: price >= stop
        target_predicate = lambda price: price <= target
        fill_quote_side = "BID"
        exit_quote_side = "ASK"

    if fill_tick is None:
        return {
            "window_id": window_id,
            "status": "no-executable-fill-in-source-minute",
            "side": side,
            "fill_quote_side": fill_quote_side,
            "exit_quote_side": exit_quote_side,
            "fill_timestamp_ms": None,
            "terminal_timestamp_ms": None,
            "terminal_r": None,
        }

    fill_ms = _timestamp(fill_tick)
    first_stop = _first_matching_at_or_after(exit_stream, fill_ms, stop_predicate)
    first_target = _first_matching_at_or_after(exit_stream, fill_ms, target_predicate)
    stop_ms = _timestamp(first_stop) if first_stop is not None else None
    target_ms = _timestamp(first_target) if first_target is not None else None

    # BID and ASK are separate cTrader streams. Equal millisecond timestamps do
    # not provide a cross-stream sequence, so do not guess whether fill or exit
    # happened first when protection is already touched in that same millisecond.
    same_ms_terminal = (
        (stop_ms is not None and stop_ms == fill_ms)
        or (target_ms is not None and target_ms == fill_ms)
    )
    if same_ms_terminal:
        return {
            "window_id": window_id,
            "status": "unresolved-same-ms-cross-stream-order",
            "side": side,
            "fill_quote_side": fill_quote_side,
            "exit_quote_side": exit_quote_side,
            "fill_timestamp_ms": fill_ms,
            "terminal_timestamp_ms": fill_ms,
            "terminal_r": None,
        }

    candidates = [
        (timestamp, label, terminal_r)
        for timestamp, label, terminal_r in (
            (stop_ms, "initial-stop-after-fill", "-1"),
            (target_ms, "fixed-2r-target-after-fill", "2"),
        )
        if timestamp is not None and timestamp > fill_ms
    ]
    if not candidates:
        return {
            "window_id": window_id,
            "status": "filled-clear-source-minute",
            "side": side,
            "fill_quote_side": fill_quote_side,
            "exit_quote_side": exit_quote_side,
            "fill_timestamp_ms": fill_ms,
            "terminal_timestamp_ms": None,
            "terminal_r": None,
        }

    candidates.sort(key=lambda item: (item[0], item[1]))
    earliest_ms = candidates[0][0]
    earliest = [item for item in candidates if item[0] == earliest_ms]
    if len(earliest) != 1:
        return {
            "window_id": window_id,
            "status": "unresolved-same-ms-stop-target-order",
            "side": side,
            "fill_quote_side": fill_quote_side,
            "exit_quote_side": exit_quote_side,
            "fill_timestamp_ms": fill_ms,
            "terminal_timestamp_ms": earliest_ms,
            "terminal_r": None,
        }

    _, status, terminal_r = earliest[0]
    return {
        "window_id": window_id,
        "status": status,
        "side": side,
        "fill_quote_side": fill_quote_side,
        "exit_quote_side": exit_quote_side,
        "fill_timestamp_ms": fill_ms,
        "terminal_timestamp_ms": earliest_ms,
        "terminal_r": terminal_r,
    }


def resolve_acquisition(
    manifest_path: Path, acquisition_dir: Path, output_path: Path
) -> dict[str, object]:
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("research_only") is not True or manifest.get("opens_new_holdout") is not False:
        raise TickResolutionError("manifest governance guard failed")
    windows = manifest.get("windows")
    if not isinstance(windows, list):
        raise TickResolutionError("manifest windows are malformed")

    acquisition_summary_path = acquisition_dir / "vt31-historical-tick-acquisition-summary.json"
    acquisition_summary = json.loads(acquisition_summary_path.read_text())
    acquisition_rows = acquisition_summary.get("results")
    if not isinstance(acquisition_rows, list):
        raise TickResolutionError("acquisition summary results are malformed")
    by_id = {
        row["window_id"]: row
        for row in acquisition_rows
        if isinstance(row, dict) and isinstance(row.get("window_id"), str)
    }
    if len(by_id) != len(windows):
        raise TickResolutionError("acquisition/manifest identity cardinality mismatch")

    results: list[dict[str, object]] = []
    for source in windows:
        if not isinstance(source, dict):
            raise TickResolutionError("manifest row is malformed")
        window_id = source.get("window_id")
        if not isinstance(window_id, str) or window_id not in by_id:
            raise TickResolutionError("manifest window missing from acquisition summary")
        acquisition = by_id[window_id]
        if acquisition.get("status") != "available":
            results.append(
                {
                    "window_id": window_id,
                    "partition": source.get("partition"),
                    "market": source.get("market"),
                    "ny_date": source.get("ny_date"),
                    "side": source.get("side"),
                    "status": "unresolved-acquisition-not-available",
                    "acquisition_status": acquisition.get("status"),
                    "fill_timestamp_ms": None,
                    "terminal_timestamp_ms": None,
                    "terminal_r": None,
                }
            )
            continue
        evidence_file = acquisition.get("evidence_file")
        if not isinstance(evidence_file, str) or not evidence_file:
            raise TickResolutionError("available acquisition is missing evidence_file")
        evidence = json.loads((acquisition_dir / "windows" / evidence_file).read_text())
        resolved = resolve_window(source, evidence)
        resolved.update(
            {
                "partition": source.get("partition"),
                "market": source.get("market"),
                "ny_date": source.get("ny_date"),
            }
        )
        results.append(resolved)

    counts = Counter(str(item["status"]) for item in results)
    payload: dict[str, object] = {
        "schema": "qore.vt31.consumed_tick_execution_resolution.v1",
        "research_only": True,
        "opens_new_holdout": False,
        "candidate_status": "NO_R9_NOT_CERTIFIED",
        "execution_semantics": {
            "long_limit_entry": "ASK<=entry",
            "short_limit_entry": "BID>=entry",
            "long_protection": "BID",
            "short_protection": "ASK",
            "same_millisecond_cross_stream_order": "censor",
            "limit_price_improvement": "not_credited_use_frozen_entry_price",
            "missing_or_partial_quote_data": "censor_no_imputation",
        },
        "source_window_count": len(windows),
        "counts": dict(sorted(counts.items())),
        "results": results,
    }
    output_path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    return payload


def _tick(timestamp_ms: int, price: str) -> dict[str, object]:
    return {"timestamp_ms": timestamp_ms, "price": price}


def _source(side: str) -> dict[str, object]:
    if side == "long":
        stop, entry, target = "99", "100", "102"
    else:
        target, entry, stop = "98", "100", "101"
    return {
        "window_id": f"self-test-{side}",
        "side": side,
        "tick_window_open_ms": 1000,
        "tick_window_close_ms": 1999,
        "entry": entry,
        "initial_stop": stop,
        "fixed_2r_target": target,
    }


def _evidence(source: dict[str, object], bid: list[dict[str, object]], ask: list[dict[str, object]]) -> dict[str, object]:
    return {"source_window": dict(source), "bid": bid, "ask": ask}


def self_test() -> None:
    long = _source("long")
    # Stop excursion before entry must not kill a position that does not yet exist.
    result = resolve_window(
        long,
        _evidence(
            long,
            [_tick(1100, "98.5"), _tick(1500, "100.2")],
            [_tick(1400, "99.9")],
        ),
    )
    assert result["status"] == "filled-clear-source-minute"
    assert result["fill_timestamp_ms"] == 1400

    result = resolve_window(
        long,
        _evidence(
            long,
            [_tick(1300, "100.1"), _tick(1600, "98.9")],
            [_tick(1400, "99.9")],
        ),
    )
    assert result["status"] == "initial-stop-after-fill"
    assert result["terminal_r"] == "-1"

    result = resolve_window(
        long,
        _evidence(
            long,
            [_tick(1300, "100.1"), _tick(1600, "102.1")],
            [_tick(1400, "99.9")],
        ),
    )
    assert result["status"] == "fixed-2r-target-after-fill"
    assert result["terminal_r"] == "2"

    short = _source("short")
    result = resolve_window(
        short,
        _evidence(
            short,
            [_tick(1300, "100.1")],
            [_tick(1400, "100.0"), _tick(1600, "97.9")],
        ),
    )
    assert result["status"] == "fixed-2r-target-after-fill"

    result = resolve_window(
        long,
        _evidence(
            long,
            [_tick(1400, "98.9")],
            [_tick(1400, "99.9")],
        ),
    )
    assert result["status"] == "unresolved-same-ms-cross-stream-order"

    result = resolve_window(
        long,
        _evidence(
            long,
            [_tick(1500, "100.0")],
            [_tick(1500, "100.1")],
        ),
    )
    assert result["status"] == "no-executable-fill-in-source-minute"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--acquisition-dir", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        print("vt31 tick execution resolver self-test: PASS")
        return
    if args.manifest is None or args.acquisition_dir is None or args.output is None:
        parser.error("--manifest, --acquisition-dir and --output are required unless --self-test")
    payload = resolve_acquisition(args.manifest, args.acquisition_dir, args.output)
    print(json.dumps(payload["counts"], sort_keys=True))


if __name__ == "__main__":
    main()
