"""Resolve consumed VT-31 pending LIMIT entries through a bounded eligibility window.

This resolver is used only after a first M1 touch was proven non-executable on the
correct quote side. It finds the first later executable fill, resolves only that
fill minute with BID/ASK, and then hands a path-clear fill back to the frozen M1
protected-swing lifecycle. It never applies the initial stop statically across the
whole pending-entry window.

Governance:
- consumed evidence only;
- no setup discovery or retuning;
- no fresh holdout access;
- no imputation of missing quote state;
- opposite quote streams tied at the fill millisecond remain censored.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable

from vt31_tick_execution_resolution import TickResolutionError, _price, _timestamp, _validated_stream


def _summary_path(root: Path) -> Path:
    candidates = (
        root / "vt31-bounded-tick-acquisition-summary.json",
        root / "vt31-historical-tick-acquisition-summary.json",
    )
    existing = [path for path in candidates if path.is_file()]
    if len(existing) != 1:
        raise TickResolutionError(f"expected exactly one acquisition summary in {root}")
    return existing[0]


def _load_acquisition(root: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    payload = json.loads(_summary_path(root).read_text())
    if payload.get("research_only") is not True or payload.get("opens_new_holdout") is not False:
        raise TickResolutionError("acquisition governance guard failed")
    rows = payload.get("results")
    if not isinstance(rows, list):
        raise TickResolutionError("acquisition results are malformed")
    by_id = {
        row["window_id"]: row
        for row in rows
        if isinstance(row, dict) and isinstance(row.get("window_id"), str)
    }
    if len(by_id) != len(rows):
        raise TickResolutionError("acquisition identities are malformed or duplicated")
    return payload, by_id


def _evidence(root: Path, row: dict[str, Any]) -> dict[str, Any]:
    if row.get("status") != "available":
        raise TickResolutionError("requested acquisition row is not available")
    filename = row.get("evidence_file")
    if not isinstance(filename, str) or not filename:
        raise TickResolutionError("available acquisition row has no evidence file")
    path = root / "windows" / filename
    if not path.is_file():
        raise TickResolutionError("acquisition evidence file is missing")
    payload = json.loads(path.read_text())
    if payload.get("research_only") is not True or payload.get("opens_new_holdout") is not False:
        raise TickResolutionError("evidence governance guard failed")
    return payload


def _predicate(side: str, kind: str, threshold: Decimal) -> Callable[[Decimal], bool]:
    if kind == "fill":
        return (lambda price: price <= threshold) if side == "long" else (lambda price: price >= threshold)
    if kind == "stop":
        return (lambda price: price <= threshold) if side == "long" else (lambda price: price >= threshold)
    if kind == "target":
        return (lambda price: price >= threshold) if side == "long" else (lambda price: price <= threshold)
    raise AssertionError(kind)


def _last_at_or_before(stream: tuple[dict[str, object], ...], timestamp_ms: int) -> dict[str, object] | None:
    result = None
    for tick in stream:
        if _timestamp(tick) > timestamp_ms:
            break
        result = tick
    return result


def _first_after(
    stream: tuple[dict[str, object], ...],
    timestamp_ms: int,
    closed_ms: int,
    predicate: Callable[[Decimal], bool],
) -> dict[str, object] | None:
    for tick in stream:
        tick_ms = _timestamp(tick)
        if tick_ms <= timestamp_ms:
            continue
        if tick_ms > closed_ms:
            break
        if predicate(_price(tick)):
            return tick
    return None


def resolve_pending_window(
    source: dict[str, Any],
    evidence: dict[str, Any],
    seed_evidence: dict[str, Any] | None,
) -> dict[str, Any]:
    window_id = source.get("window_id")
    parent_id = source.get("parent_window_id")
    if not isinstance(window_id, str) or not window_id:
        raise TickResolutionError("pending source id is malformed")
    if not isinstance(parent_id, str) or not parent_id:
        raise TickResolutionError("pending parent id is malformed")
    evidence_source = evidence.get("source_window")
    if not isinstance(evidence_source, dict) or evidence_source.get("window_id") != window_id:
        raise TickResolutionError("pending evidence/source identity mismatch")

    side = source.get("side")
    if side not in {"long", "short"}:
        raise TickResolutionError("pending side is malformed")
    opened_ms = source.get("tick_window_open_ms")
    closed_ms = source.get("tick_window_close_ms")
    if type(opened_ms) is not int or type(closed_ms) is not int or closed_ms < opened_ms:
        raise TickResolutionError("pending boundaries are malformed")
    entry = Decimal(str(source["entry"]))
    stop = Decimal(str(source["initial_stop"]))
    target = Decimal(str(source["fixed_2r_target"]))
    if min(entry, stop, target) <= 0:
        raise TickResolutionError("pending prices must be positive")
    if side == "long" and not stop < entry < target:
        raise TickResolutionError("long pending price ordering is invalid")
    if side == "short" and not target < entry < stop:
        raise TickResolutionError("short pending price ordering is invalid")

    bid = _validated_stream(evidence, "bid", opened_ms, closed_ms)
    ask = _validated_stream(evidence, "ask", opened_ms, closed_ms)
    if not bid or not ask:
        return {
            "window_id": window_id,
            "parent_window_id": parent_id,
            "status": "unresolved-missing-followup-quote-side",
            "side": side,
            "fill_timestamp_ms": None,
            "fill_minute_close_ms": None,
            "terminal_timestamp_ms": None,
            "terminal_r": None,
        }

    if side == "long":
        fill_stream, exit_stream = ask, bid
        fill_quote_side, exit_quote_side = "ASK", "BID"
    else:
        fill_stream, exit_stream = bid, ask
        fill_quote_side, exit_quote_side = "BID", "ASK"
    fill_predicate = _predicate(side, "fill", entry)
    stop_predicate = _predicate(side, "stop", stop)
    target_predicate = _predicate(side, "target", target)
    fill_tick = next((tick for tick in fill_stream if fill_predicate(_price(tick))), None)
    if fill_tick is None:
        return {
            "window_id": window_id,
            "parent_window_id": parent_id,
            "status": "no-executable-fill-through-pending-cutoff",
            "side": side,
            "fill_quote_side": fill_quote_side,
            "exit_quote_side": exit_quote_side,
            "fill_timestamp_ms": None,
            "fill_minute_close_ms": None,
            "terminal_timestamp_ms": None,
            "terminal_r": None,
        }

    fill_ms = _timestamp(fill_tick)
    fill_minute_close_ms = min(((fill_ms // 60_000) + 1) * 60_000 - 1, closed_ms)

    seed_exit: tuple[dict[str, object], ...] = ()
    if seed_evidence is not None:
        seed_source = seed_evidence.get("source_window")
        if not isinstance(seed_source, dict) or seed_source.get("window_id") != parent_id:
            raise TickResolutionError("seed evidence/parent identity mismatch")
        seed_open = seed_source.get("tick_window_open_ms")
        seed_close = seed_source.get("tick_window_close_ms")
        if type(seed_open) is not int or type(seed_close) is not int:
            raise TickResolutionError("seed evidence boundaries are malformed")
        seed_exit = _validated_stream(
            seed_evidence,
            "bid" if side == "long" else "ask",
            seed_open,
            seed_close,
        )

    current = _last_at_or_before(seed_exit, fill_ms)
    follow_current = _last_at_or_before(exit_stream, fill_ms)
    if follow_current is not None and (current is None or _timestamp(follow_current) >= _timestamp(current)):
        current = follow_current
    if current is None:
        return {
            "window_id": window_id,
            "parent_window_id": parent_id,
            "status": "unresolved-missing-exit-quote-state-at-fill",
            "side": side,
            "fill_quote_side": fill_quote_side,
            "exit_quote_side": exit_quote_side,
            "fill_timestamp_ms": fill_ms,
            "fill_minute_close_ms": fill_minute_close_ms,
            "terminal_timestamp_ms": None,
            "terminal_r": None,
        }

    current_ms = _timestamp(current)
    current_price = _price(current)
    current_stop = stop_predicate(current_price)
    current_target = target_predicate(current_price)
    if current_stop and current_target:
        raise TickResolutionError("stop and target predicates cannot overlap")
    if current_ms == fill_ms and (current_stop or current_target):
        return {
            "window_id": window_id,
            "parent_window_id": parent_id,
            "status": "unresolved-same-ms-cross-stream-order",
            "side": side,
            "fill_quote_side": fill_quote_side,
            "exit_quote_side": exit_quote_side,
            "fill_timestamp_ms": fill_ms,
            "fill_minute_close_ms": fill_minute_close_ms,
            "terminal_timestamp_ms": fill_ms,
            "terminal_r": None,
        }
    if current_stop:
        return {
            "window_id": window_id,
            "parent_window_id": parent_id,
            "status": "initial-stop-at-executable-fill",
            "side": side,
            "fill_quote_side": fill_quote_side,
            "exit_quote_side": exit_quote_side,
            "fill_timestamp_ms": fill_ms,
            "fill_minute_close_ms": fill_minute_close_ms,
            "terminal_timestamp_ms": fill_ms,
            "terminal_r": "-1",
        }
    if current_target:
        return {
            "window_id": window_id,
            "parent_window_id": parent_id,
            "status": "fixed-2r-target-at-executable-fill",
            "side": side,
            "fill_quote_side": fill_quote_side,
            "exit_quote_side": exit_quote_side,
            "fill_timestamp_ms": fill_ms,
            "fill_minute_close_ms": fill_minute_close_ms,
            "terminal_timestamp_ms": fill_ms,
            "terminal_r": "2",
        }

    first_stop = _first_after(exit_stream, fill_ms, fill_minute_close_ms, stop_predicate)
    first_target = _first_after(exit_stream, fill_ms, fill_minute_close_ms, target_predicate)
    candidates = []
    if first_stop is not None:
        candidates.append((_timestamp(first_stop), "initial-stop-in-fill-minute", "-1"))
    if first_target is not None:
        candidates.append((_timestamp(first_target), "fixed-2r-target-in-fill-minute", "2"))
    candidates.sort(key=lambda item: item[0])
    if candidates:
        earliest_ms = candidates[0][0]
        earliest = [item for item in candidates if item[0] == earliest_ms]
        if len(earliest) != 1:
            return {
                "window_id": window_id,
                "parent_window_id": parent_id,
                "status": "unresolved-same-ms-stop-target-order",
                "side": side,
                "fill_quote_side": fill_quote_side,
                "exit_quote_side": exit_quote_side,
                "fill_timestamp_ms": fill_ms,
                "fill_minute_close_ms": fill_minute_close_ms,
                "terminal_timestamp_ms": earliest_ms,
                "terminal_r": None,
            }
        terminal_ms, status, terminal_r = earliest[0]
        return {
            "window_id": window_id,
            "parent_window_id": parent_id,
            "status": status,
            "side": side,
            "fill_quote_side": fill_quote_side,
            "exit_quote_side": exit_quote_side,
            "fill_timestamp_ms": fill_ms,
            "fill_minute_close_ms": fill_minute_close_ms,
            "terminal_timestamp_ms": terminal_ms,
            "terminal_r": terminal_r,
        }

    return {
        "window_id": window_id,
        "parent_window_id": parent_id,
        "status": "executable-fill-minute-clear",
        "side": side,
        "fill_quote_side": fill_quote_side,
        "exit_quote_side": exit_quote_side,
        "fill_timestamp_ms": fill_ms,
        "fill_minute_close_ms": fill_minute_close_ms,
        "terminal_timestamp_ms": None,
        "terminal_r": None,
    }


def resolve_manifest(
    manifest_path: Path,
    acquisition_dir: Path,
    seed_acquisition_dir: Path,
    output_path: Path,
) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("research_only") is not True or manifest.get("opens_new_holdout") is not False:
        raise TickResolutionError("pending manifest governance guard failed")
    windows = manifest.get("windows")
    if not isinstance(windows, list) or not windows:
        raise TickResolutionError("pending manifest windows are malformed")
    acquisition, acquisition_by_id = _load_acquisition(acquisition_dir)
    seed_acquisition, seed_by_id = _load_acquisition(seed_acquisition_dir)
    if acquisition.get("source_window_count") != len(windows):
        raise TickResolutionError("pending acquisition cardinality mismatch")

    results: list[dict[str, Any]] = []
    for source in windows:
        if not isinstance(source, dict):
            raise TickResolutionError("pending source row is malformed")
        window_id = source.get("window_id")
        parent_id = source.get("parent_window_id")
        if not isinstance(window_id, str) or window_id not in acquisition_by_id:
            raise TickResolutionError("pending acquisition identity mismatch")
        if not isinstance(parent_id, str) or parent_id not in seed_by_id:
            raise TickResolutionError("pending seed identity mismatch")
        acquisition_row = acquisition_by_id[window_id]
        seed_row = seed_by_id[parent_id]
        if acquisition_row.get("status") != "available":
            result = {
                "window_id": window_id,
                "parent_window_id": parent_id,
                "status": "unresolved-followup-acquisition-not-available",
                "side": source.get("side"),
                "fill_timestamp_ms": None,
                "fill_minute_close_ms": None,
                "terminal_timestamp_ms": None,
                "terminal_r": None,
            }
        elif seed_row.get("status") != "available":
            result = {
                "window_id": window_id,
                "parent_window_id": parent_id,
                "status": "unresolved-seed-acquisition-not-available",
                "side": source.get("side"),
                "fill_timestamp_ms": None,
                "fill_minute_close_ms": None,
                "terminal_timestamp_ms": None,
                "terminal_r": None,
            }
        else:
            result = resolve_pending_window(
                source,
                _evidence(acquisition_dir, acquisition_row),
                _evidence(seed_acquisition_dir, seed_row),
            )
        result.update(
            {
                "partition": source.get("partition"),
                "market": source.get("market"),
                "ny_date": source.get("ny_date"),
            }
        )
        results.append(result)

    counts = Counter(str(row["status"]) for row in results)
    payload: dict[str, Any] = {
        "schema": "qore.vt31.consumed_pending_limit_tick_resolution.v1",
        "research_only": True,
        "opens_new_holdout": False,
        "candidate_status": "NO_R9_NOT_CERTIFIED",
        "source_window_count": len(windows),
        "semantics": {
            "pending_limit_cutoff": manifest.get("pending_entry_cutoff"),
            "first_executable_fill_only": True,
            "fill_bar_resolution": "correct quote side through exact fill M1 only",
            "post_clear_fill_handoff": "frozen M1 protected-swing lifecycle",
            "cross_stream_same_millisecond": "censor",
            "missing_quote_state": "censor-no-imputation",
        },
        "counts": dict(sorted(counts.items())),
        "results": results,
    }
    output_path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    return payload


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
        "source_window": {"window_id": "parent-long", "tick_window_open_ms": 1, "tick_window_close_ms": 59_999},
        "bid": [_tick(59_900, "100.2")],
        "ask": [_tick(59_900, "100.4")],
    }
    evidence = {
        "source_window": dict(source),
        "bid": [_tick(70_000, "100.1"), _tick(121_000, "98.9")],
        "ask": [_tick(65_000, "100.2"), _tick(120_500, "99.9")],
    }
    result = resolve_pending_window(source, evidence, seed)
    assert result["status"] == "initial-stop-in-fill-minute"
    assert result["fill_timestamp_ms"] == 120_500
    assert result["terminal_timestamp_ms"] == 121_000

    evidence_clear = {
        "source_window": dict(source),
        "bid": [_tick(70_000, "100.1"), _tick(121_000, "100.0"), _tick(130_000, "100.5")],
        "ask": [_tick(120_500, "99.9")],
    }
    result = resolve_pending_window(source, evidence_clear, seed)
    assert result["status"] == "executable-fill-minute-clear"
    assert result["fill_minute_close_ms"] == 179_999

    no_fill = {
        "source_window": dict(source),
        "bid": [_tick(80_000, "100.1")],
        "ask": [_tick(80_000, "100.2")],
    }
    result = resolve_pending_window(source, no_fill, seed)
    assert result["status"] == "no-executable-fill-through-pending-cutoff"

    seed_stopped = {
        "source_window": {"window_id": "parent-long", "tick_window_open_ms": 1, "tick_window_close_ms": 59_999},
        "bid": [_tick(59_900, "98.8")],
        "ask": [_tick(59_900, "99.2")],
    }
    result = resolve_pending_window(source, evidence_clear, seed_stopped)
    assert result["status"] == "initial-stop-at-executable-fill"
    assert result["terminal_r"] == "-1"


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
        print("vt31 pending-limit tick resolver self-test: PASS")
        return
    if args.manifest is None or args.acquisition_dir is None or args.seed_acquisition_dir is None or args.output is None:
        parser.error("manifest/acquisition/seed-acquisition/output are required unless --self-test")
    payload = resolve_manifest(args.manifest, args.acquisition_dir, args.seed_acquisition_dir, args.output)
    print(json.dumps(payload["counts"], sort_keys=True))


if __name__ == "__main__":
    main()
