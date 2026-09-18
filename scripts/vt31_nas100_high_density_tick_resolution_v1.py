"""Resolve high-density OCO ambiguity with historical BID/ASK ticks.

This resolver is deliberately fail-closed. It consumes only tick evidence
acquired for already-consumed M1 windows and never discovers a setup.

Execution semantics:
- long LIMIT fill uses ASK <= entry;
- short LIMIT fill uses BID >= entry;
- long stop/target protection uses BID;
- short stop/target protection uses ASK;
- activation time is respected per OCO order;
- multiple orders first executable at the same millisecond remain unresolved;
- cross-stream same-millisecond fill/terminal ordering remains unresolved.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from collections.abc import Callable
from decimal import Decimal
from pathlib import Path
from typing import Any

from vt31_tick_execution_resolution import (
    TickResolutionError,
    _price,
    _timestamp,
    _validated_stream,
)

SCHEMA = "qore.vt31.nas100.high_density_tick_resolution.v1"


def _summary_path(root: Path) -> Path:
    candidates = (
        root / "high-density-tick-acquisition-summary.json",
        root / "vt31-historical-tick-acquisition-summary.json",
    )
    existing = [path for path in candidates if path.is_file()]
    if len(existing) != 1:
        raise TickResolutionError(
            f"expected one acquisition summary in {root}, got {existing}"
        )
    return existing[0]


def _acquisition_index(
    roots: list[Path],
) -> dict[tuple[str, str, int, int], tuple[Path, dict[str, Any]]]:
    result: dict[
        tuple[str, str, int, int],
        tuple[Path, dict[str, Any]],
    ] = {}
    for root in roots:
        summary = json.loads(_summary_path(root).read_text())
        if (
            summary.get("research_only") is not True
            or summary.get("opens_new_holdout") is not False
        ):
            raise TickResolutionError("acquisition governance guard failed")
        rows = summary.get("results")
        if not isinstance(rows, list):
            raise TickResolutionError("acquisition rows are malformed")
        for row in rows:
            if not isinstance(row, dict):
                continue
            opened = row.get("tick_window_open_ms")
            closed = row.get("tick_window_close_ms")
            market = row.get("market")
            provider = row.get("provider")
            if (
                not isinstance(market, str)
                or not isinstance(provider, str)
                or type(opened) is not int
                or type(closed) is not int
            ):
                continue
            key = (market, provider, opened, closed)
            current = result.get(key)
            if current is None or row.get("status") == "available":
                result[key] = (root, cast_row(row))
    return result


def cast_row(row: dict[str, object]) -> dict[str, Any]:
    return {str(key): value for key, value in row.items()}


def _evidence(
    root: Path,
    row: dict[str, Any],
    source: dict[str, Any],
) -> dict[str, Any] | None:
    if row.get("status") != "available":
        return None
    filename = row.get("evidence_file")
    if not isinstance(filename, str) or not filename:
        raise TickResolutionError("available row has no evidence file")
    path = root / "windows" / filename
    if not path.is_file():
        raise TickResolutionError(f"tick evidence is missing: {path}")
    payload = json.loads(path.read_text())
    if (
        payload.get("research_only") is not True
        or payload.get("opens_new_holdout") is not False
    ):
        raise TickResolutionError("tick evidence governance guard failed")
    if payload.get("market") != source["market"]:
        raise TickResolutionError("tick evidence market mismatch")
    if payload.get("provider_symbol") != source["provider"]:
        raise TickResolutionError("tick evidence provider mismatch")
    if payload.get("opened_ms") != source["tick_window_open_ms"]:
        raise TickResolutionError("tick evidence open mismatch")
    if payload.get("closed_ms") != source["tick_window_close_ms"]:
        raise TickResolutionError("tick evidence close mismatch")
    return payload


def _threshold_predicate(
    mode: str,
    threshold: Decimal,
) -> Callable[[Decimal], bool]:
    if mode == "le":
        def at_or_below(price: Decimal) -> bool:
            return price <= threshold

        return at_or_below
    if mode == "ge":
        def at_or_above(price: Decimal) -> bool:
            return price >= threshold

        return at_or_above
    raise ValueError(mode)


def _first_at_or_after(
    stream: tuple[dict[str, object], ...],
    *,
    activation_ms: int,
    predicate: Callable[[Decimal], bool],
) -> dict[str, object] | None:
    for tick in stream:
        if _timestamp(tick) < activation_ms:
            continue
        if predicate(_price(tick)):
            return tick
    return None


def _terminal_after_fill(
    *,
    source: dict[str, Any],
    evidence: dict[str, Any],
    side: str,
    entry: Decimal,
    stop: Decimal,
    target: Decimal,
    activation_ms: int,
) -> dict[str, object]:
    opened_ms = int(source["tick_window_open_ms"])
    closed_ms = int(source["tick_window_close_ms"])
    bid = _validated_stream(evidence, "bid", opened_ms, closed_ms)
    ask = _validated_stream(evidence, "ask", opened_ms, closed_ms)
    if not bid or not ask:
        return {
            "status": "unresolved-missing-quote-side",
            "fill_timestamp_ms": None,
            "terminal_timestamp_ms": None,
            "terminal_r": None,
        }

    if side == "long":
        fill_stream = ask
        exit_stream = bid
        fill_predicate = _threshold_predicate("le", entry)
        stop_predicate = _threshold_predicate("le", stop)
        target_predicate = _threshold_predicate("ge", target)
        fill_quote_side = "ASK"
        exit_quote_side = "BID"
    else:
        fill_stream = bid
        exit_stream = ask
        fill_predicate = _threshold_predicate("ge", entry)
        stop_predicate = _threshold_predicate("ge", stop)
        target_predicate = _threshold_predicate("le", target)
        fill_quote_side = "BID"
        exit_quote_side = "ASK"

    fill = _first_at_or_after(
        fill_stream,
        activation_ms=activation_ms,
        predicate=fill_predicate,
    )
    if fill is None:
        return {
            "status": "no-executable-fill-in-source-minute",
            "fill_quote_side": fill_quote_side,
            "exit_quote_side": exit_quote_side,
            "fill_timestamp_ms": None,
            "terminal_timestamp_ms": None,
            "terminal_r": None,
        }
    fill_ms = _timestamp(fill)

    stop_hit = _first_at_or_after(
        exit_stream,
        activation_ms=fill_ms,
        predicate=stop_predicate,
    )
    target_hit = _first_at_or_after(
        exit_stream,
        activation_ms=fill_ms,
        predicate=target_predicate,
    )
    stop_ms = _timestamp(stop_hit) if stop_hit is not None else None
    target_ms = _timestamp(target_hit) if target_hit is not None else None

    if (
        (stop_ms is not None and stop_ms == fill_ms)
        or (target_ms is not None and target_ms == fill_ms)
    ):
        return {
            "status": "unresolved-same-ms-cross-stream-order",
            "fill_quote_side": fill_quote_side,
            "exit_quote_side": exit_quote_side,
            "fill_timestamp_ms": fill_ms,
            "terminal_timestamp_ms": fill_ms,
            "terminal_r": None,
        }

    candidates = [
        item
        for item in (
            (stop_ms, "initial-stop-after-fill", "-1"),
            (target_ms, "target-after-fill", None),
        )
        if item[0] is not None and cast_int(item[0]) > fill_ms
    ]
    if not candidates:
        return {
            "status": "filled-clear-source-minute",
            "fill_quote_side": fill_quote_side,
            "exit_quote_side": exit_quote_side,
            "fill_timestamp_ms": fill_ms,
            "terminal_timestamp_ms": None,
            "terminal_r": None,
        }

    normalized = sorted(
        (
            cast_int(timestamp),
            status,
            terminal_r,
        )
        for timestamp, status, terminal_r in candidates
    )
    earliest_ms = normalized[0][0]
    earliest = [item for item in normalized if item[0] == earliest_ms]
    if len(earliest) != 1:
        return {
            "status": "unresolved-same-ms-stop-target-order",
            "fill_quote_side": fill_quote_side,
            "exit_quote_side": exit_quote_side,
            "fill_timestamp_ms": fill_ms,
            "terminal_timestamp_ms": earliest_ms,
            "terminal_r": None,
        }

    terminal_ms, status, terminal_r = earliest[0]
    if status == "target-after-fill":
        risk = abs(entry - stop)
        reward = abs(target - entry)
        if risk <= 0:
            raise TickResolutionError("risk must be positive")
        terminal_r = format(reward / risk, "f")
    return {
        "status": status,
        "fill_quote_side": fill_quote_side,
        "exit_quote_side": exit_quote_side,
        "fill_timestamp_ms": fill_ms,
        "terminal_timestamp_ms": terminal_ms,
        "terminal_r": terminal_r,
    }


def cast_int(value: object) -> int:
    if type(value) is not int:
        raise TickResolutionError("timestamp must be integer")
    return value


def _order_result(
    source: dict[str, Any],
    evidence: dict[str, Any],
    order: dict[str, Any],
) -> dict[str, object]:
    side = str(order.get("side", source.get("side")))
    if side not in {"long", "short"}:
        raise TickResolutionError("order side is invalid")
    entry = Decimal(str(order["entry"]))
    stop = Decimal(str(order["initial_stop"]))
    target = Decimal(str(order["target"]))
    activation_ms = cast_int(order["activation_ms"])
    if side == "long" and not stop < entry < target:
        raise TickResolutionError("long order geometry is invalid")
    if side == "short" and not target < entry < stop:
        raise TickResolutionError("short order geometry is invalid")
    result = _terminal_after_fill(
        source=source,
        evidence=evidence,
        side=side,
        entry=entry,
        stop=stop,
        target=target,
        activation_ms=activation_ms,
    )
    return {
        **result,
        "side": side,
        "family": order.get("family"),
        "entry": format(entry, "f"),
        "initial_stop": format(stop, "f"),
        "target": format(target, "f"),
        "activation_ms": activation_ms,
    }


def resolve_window(
    source: dict[str, Any],
    evidence: dict[str, Any],
) -> dict[str, object]:
    classification = source.get("classification")
    if classification == "OCO_FILL_BAR_PATH":
        order = {
            "side": source["side"],
            "family": source["family"],
            "entry": source["entry"],
            "initial_stop": source["initial_stop"],
            "target": source["target"],
            "activation_ms": source["activation_ms"],
        }
        return {
            "window_id": source["window_id"],
            "classification": classification,
            **_order_result(source, evidence, order),
        }

    if classification != "OCO_MULTI_PRICE_FIRST_FILL":
        raise TickResolutionError(
            f"unsupported classification: {classification}"
        )
    orders = source.get("orders")
    if not isinstance(orders, list) or len(orders) < 2:
        raise TickResolutionError("multi-price OCO orders are malformed")

    attempted = [
        _order_result(source, evidence, cast_row(order))
        for order in orders
        if isinstance(order, dict)
    ]
    filled = [
        item
        for item in attempted
        if item.get("fill_timestamp_ms") is not None
    ]
    if not filled:
        return {
            "window_id": source["window_id"],
            "classification": classification,
            "status": "no-executable-oco-fill-in-source-minute",
            "selected_order": None,
            "attempted_orders": attempted,
        }

    earliest_ms = min(cast_int(item["fill_timestamp_ms"]) for item in filled)
    earliest = [
        item
        for item in filled
        if cast_int(item["fill_timestamp_ms"]) == earliest_ms
    ]
    if len(earliest) != 1:
        return {
            "window_id": source["window_id"],
            "classification": classification,
            "status": "unresolved-same-ms-multi-order-fill",
            "selected_order": None,
            "fill_timestamp_ms": earliest_ms,
            "attempted_orders": attempted,
        }

    selected = earliest[0]
    return {
        "window_id": source["window_id"],
        "classification": classification,
        "status": selected["status"],
        "selected_order": selected,
        "fill_timestamp_ms": selected["fill_timestamp_ms"],
        "terminal_timestamp_ms": selected["terminal_timestamp_ms"],
        "terminal_r": selected["terminal_r"],
        "attempted_orders": attempted,
    }


def resolve(
    manifest_path: Path,
    acquisition_roots: list[Path],
    output_path: Path,
) -> dict[str, object]:
    manifest = json.loads(manifest_path.read_text())
    if (
        manifest.get("research_only") is not True
        or manifest.get("opens_new_holdout") is not False
    ):
        raise TickResolutionError("manifest governance guard failed")
    windows = manifest.get("windows")
    if not isinstance(windows, list):
        raise TickResolutionError("manifest windows are malformed")

    index = _acquisition_index(acquisition_roots)
    results: list[dict[str, object]] = []
    counts: Counter[str] = Counter()
    evidence_available = 0

    for raw in windows:
        if not isinstance(raw, dict):
            raise TickResolutionError("manifest window is malformed")
        source = cast_row(raw)
        key = (
            str(source["market"]),
            str(source["provider"]),
            cast_int(source["tick_window_open_ms"]),
            cast_int(source["tick_window_close_ms"]),
        )
        located = index.get(key)
        if located is None:
            row = {
                "window_id": source["window_id"],
                "classification": source["classification"],
                "status": "unresolved-no-tick-evidence",
            }
        else:
            root, acquisition_row = located
            evidence = _evidence(root, acquisition_row, source)
            if evidence is None:
                row = {
                    "window_id": source["window_id"],
                    "classification": source["classification"],
                    "status": (
                        "unresolved-acquisition-"
                        + str(acquisition_row.get("status"))
                    ),
                }
            else:
                evidence_available += 1
                row = resolve_window(source, evidence)
        counts[str(row["status"])] += 1
        results.append(row)

    payload = {
        "schema": SCHEMA,
        "research_only": True,
        "opens_new_holdout": False,
        "candidate_status": "RESEARCH_NOT_CERTIFIED",
        "source_manifest": manifest_path.name,
        "source_window_count": len(windows),
        "tick_evidence_available_count": evidence_available,
        "counts": dict(sorted(counts.items())),
        "results": results,
        "governance": {
            "missing_ticks_imputed": False,
            "same_ms_cross_stream_order_guessed": False,
            "same_ms_multi_order_fill_guessed": False,
            "policy_promoted": False,
            "live_authorized": False,
            "production_authorized": False,
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n"
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument(
        "--acquisition-dir",
        action="append",
        required=True,
        type=Path,
    )
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = resolve(
        args.manifest,
        args.acquisition_dir,
        args.output,
    )
    print(
        json.dumps(
            {
                "source_window_count": payload["source_window_count"],
                "tick_evidence_available_count": payload[
                    "tick_evidence_available_count"
                ],
                "counts": payload["counts"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
