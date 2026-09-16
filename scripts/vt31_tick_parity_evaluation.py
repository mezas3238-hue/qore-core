"""Evaluate executable BID/ASK parity against 339 consumed resolved controls.

The control rows were previously treated as M1 fills with a path-clear fill bar.
This evaluator does not force historical M1 semantics to pass. It asks whether
the same frozen limit entry is actually executable on the correct quote side and
whether the executable exit side remains clear during that minute.

Any disagreement is evidence that the old M1 economics need correction; it is
not retuned away. Same-millisecond cross-stream ordering stays censored.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Any

from vt31_tick_execution_resolution import resolve_window

_EXPECTED_TOTAL = 339
_PASS_STATUS = "filled-clear-source-minute"


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text())
    if payload.get("research_only") is not True or payload.get("opens_new_holdout") is not False:
        raise ValueError(f"governance guard failed for {path}")
    return payload


def _closest_m1_side(source: dict[str, Any], evidence: dict[str, Any]) -> dict[str, str | None]:
    bid = evidence.get("bid")
    ask = evidence.get("ask")
    if not isinstance(bid, list) or not isinstance(ask, list) or not bid or not ask:
        return {"closest": None, "bid_error": None, "ask_error": None}
    m1_low = _d(source["m1_low"])
    m1_high = _d(source["m1_high"])
    bid_prices = [_d(row["price"]) for row in bid]
    ask_prices = [_d(row["price"]) for row in ask]
    bid_error = abs(m1_low - min(bid_prices)) + abs(m1_high - max(bid_prices))
    ask_error = abs(m1_low - min(ask_prices)) + abs(m1_high - max(ask_prices))
    if bid_error < ask_error:
        closest = "BID"
    elif ask_error < bid_error:
        closest = "ASK"
    else:
        closest = "TIE"
    return {
        "closest": closest,
        "bid_error": format(bid_error, "f"),
        "ask_error": format(ask_error, "f"),
    }


def evaluate(manifest_path: Path, acquisition_dir: Path, output_path: Path) -> dict[str, Any]:
    manifest = _load(manifest_path)
    windows = manifest.get("windows")
    if not isinstance(windows, list) or len(windows) != _EXPECTED_TOTAL:
        raise ValueError("parity manifest must contain exactly 339 controls")

    summary_path = acquisition_dir / "vt31-bounded-tick-acquisition-summary.json"
    acquisition = _load(summary_path)
    rows = acquisition.get("results")
    if not isinstance(rows, list) or len(rows) != _EXPECTED_TOTAL:
        raise ValueError("parity acquisition must contain exactly 339 rows")
    by_id = {
        row["window_id"]: row
        for row in rows
        if isinstance(row, dict) and isinstance(row.get("window_id"), str)
    }
    if len(by_id) != _EXPECTED_TOTAL:
        raise ValueError("parity acquisition identities changed")

    statuses: Counter[str] = Counter()
    closest_sides: Counter[str] = Counter()
    groups: dict[str, Counter[str]] = defaultdict(Counter)
    results: list[dict[str, Any]] = []
    for source in windows:
        if not isinstance(source, dict):
            raise ValueError("parity source row is malformed")
        window_id = source.get("window_id")
        if not isinstance(window_id, str) or window_id not in by_id:
            raise ValueError("parity source/acquisition identity mismatch")
        acquisition_row = by_id[window_id]
        if acquisition_row.get("status") != "available":
            status = "unresolved-acquisition-not-available"
            result: dict[str, Any] = {
                "window_id": window_id,
                "tick_status": status,
                "parity_pass": False,
                "acquisition_status": acquisition_row.get("status"),
            }
        else:
            evidence_file = acquisition_row.get("evidence_file")
            if not isinstance(evidence_file, str):
                raise ValueError("available parity row missing evidence file")
            evidence = json.loads((acquisition_dir / "windows" / evidence_file).read_text())
            tick = resolve_window(source, evidence)
            status = str(tick["status"])
            quote_match = _closest_m1_side(source, evidence)
            if quote_match["closest"] is not None:
                closest_sides[str(quote_match["closest"])] += 1
            result = {
                "window_id": window_id,
                "tick_status": status,
                "parity_pass": status == _PASS_STATUS,
                "fill_timestamp_ms": tick.get("fill_timestamp_ms"),
                "terminal_timestamp_ms": tick.get("terminal_timestamp_ms"),
                "terminal_r": tick.get("terminal_r"),
                "m1_quote_side_closest": quote_match["closest"],
                "m1_bid_endpoint_error": quote_match["bid_error"],
                "m1_ask_endpoint_error": quote_match["ask_error"],
            }
        statuses[status] += 1
        group_keys = (
            f"partition:{source['partition']}",
            f"market:{source['market']}",
            f"side:{source['side']}",
            f"partition_market:{source['partition']}:{source['market']}",
        )
        for key in group_keys:
            groups[key][status] += 1
        result.update(
            {
                "partition": source["partition"],
                "market": source["market"],
                "ny_date": source["ny_date"],
                "side": source["side"],
                "frozen_exit_reason": source["frozen_exit_reason"],
                "frozen_r_multiple": source["frozen_r_multiple"],
            }
        )
        results.append(result)

    parity_pass_count = statuses[_PASS_STATUS]
    payload: dict[str, Any] = {
        "schema": "qore.vt31.consumed_tick_execution_parity.v1",
        "research_only": True,
        "opens_new_holdout": False,
        "candidate_status": "NO_R9_NOT_CERTIFIED",
        "control_definition": "old M1 replay resolved fill with path-clear fill bar",
        "parity_definition": "executable quote-side fill and path-clear executable exit side within same source minute",
        "source_count": _EXPECTED_TOTAL,
        "parity_pass_count": parity_pass_count,
        "parity_fail_or_censored_count": _EXPECTED_TOTAL - parity_pass_count,
        "parity_pass_fraction": format(Decimal(parity_pass_count) / Decimal(_EXPECTED_TOTAL), ".12f"),
        "status_counts": dict(sorted(statuses.items())),
        "m1_quote_side_closest_counts": dict(sorted(closest_sides.items())),
        "group_status_counts": {key: dict(sorted(value.items())) for key, value in sorted(groups.items())},
        "results": results,
    }
    output_path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--acquisition-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = evaluate(args.manifest, args.acquisition_dir, args.output)
    print(json.dumps({
        "source_count": payload["source_count"],
        "parity_pass_count": payload["parity_pass_count"],
        "parity_fail_or_censored_count": payload["parity_fail_or_censored_count"],
        "status_counts": payload["status_counts"],
        "m1_quote_side_closest_counts": payload["m1_quote_side_closest_counts"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
