"""Acquire BID/ASK ticks for a bounded VT-31 *consumed* manifest.

Unlike the original fixed 437-window acquisition, this helper accepts a frozen
research-only manifest with an arbitrary non-zero number of already-consumed
windows. It exists for control parity and narrowly declared follow-up windows.
It cannot open a fresh holdout, discover setups, retune trader rules, or impute
missing quote evidence.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from qore.infrastructure.ctrader_demo_lab_probe import CTraderDemoLabProbeError
from qore.infrastructure.ctrader_open_api_client import SpotwareCTraderOpenApiClient

from vt31_historical_tick_batch_acquisition import (
    _canonical_sha,
    _collect_with_retry,
    _connect_and_resolve_market,
    _credentials,
    _enable_research_tick_messages,
    _projection,
    _RESEARCH_MARKETS,
)

_MAX_WINDOW_MS = 3_600_000
_MAX_WINDOWS = 1_000
_ALLOWED_PARTITIONS = {"r5", "r6", "r8_fresh"}


def _load_manifest(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text())
    if payload.get("research_only") is not True:
        raise CTraderDemoLabProbeError("manifest must be research-only")
    if payload.get("opens_new_holdout") is not False:
        raise CTraderDemoLabProbeError("manifest must not open a new holdout")
    windows = payload.get("windows")
    if not isinstance(windows, list) or not 1 <= len(windows) <= _MAX_WINDOWS:
        raise CTraderDemoLabProbeError("manifest window cardinality is out of bounds")
    identities: set[str] = set()
    for row in windows:
        if not isinstance(row, dict):
            raise CTraderDemoLabProbeError("manifest row is malformed")
        if row.get("partition") not in _ALLOWED_PARTITIONS:
            raise CTraderDemoLabProbeError("manifest partition is unexpected")
        if row.get("market") not in _RESEARCH_MARKETS:
            raise CTraderDemoLabProbeError("manifest market is unexpected")
        window_id = row.get("window_id")
        if not isinstance(window_id, str) or not window_id or window_id in identities:
            raise CTraderDemoLabProbeError("manifest window id is malformed or duplicated")
        identities.add(window_id)
        provider = row.get("provider")
        if not isinstance(provider, str) or not provider:
            raise CTraderDemoLabProbeError("manifest provider binding is missing")
        opened_ms = row.get("tick_window_open_ms")
        closed_ms = row.get("tick_window_close_ms")
        if type(opened_ms) is not int or type(closed_ms) is not int:
            raise CTraderDemoLabProbeError("manifest boundaries are malformed")
        duration = closed_ms - opened_ms + 1
        if not 1 <= duration <= _MAX_WINDOW_MS:
            raise CTraderDemoLabProbeError("manifest window duration is out of bounds")
    return payload


def _group_counts(results: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    groups: dict[str, dict[str, int]] = {}
    for result in results:
        key = f"{result['partition']}:{result['market']}"
        group = groups.setdefault(
            key,
            {"available": 0, "partial": 0, "empty": 0, "probe_failure": 0, "binding_mismatch": 0},
        )
        group[result["status"]] += 1
    return groups


def acquire(manifest_path: Path, output_dir: Path) -> dict[str, Any]:
    manifest = _load_manifest(manifest_path)
    windows = sorted(
        manifest["windows"],
        key=lambda row: (row["market"], row["tick_window_open_ms"], row["window_id"]),
    )
    evidence_dir = output_dir / "windows"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    client = SpotwareCTraderOpenApiClient(credentials=_credentials())
    results: list[dict[str, Any]] = []
    try:
        _enable_research_tick_messages(client)
        bindings: dict[str, tuple[int, str, object, str]] = {}
        for market in sorted(_RESEARCH_MARKETS):
            bindings[market] = _connect_and_resolve_market(client, market=market, timeout_seconds=12.0)
        account_ids = {binding[0] for binding in bindings.values()}
        fingerprints = {binding[1] for binding in bindings.values()}
        if len(account_ids) != 1 or len(fingerprints) != 1:
            raise CTraderDemoLabProbeError("consumed tick markets must share one exact account binding")

        for index, row in enumerate(windows, start=1):
            market = row["market"]
            account_id, fingerprint, symbol, provider_symbol = bindings[market]
            base: dict[str, Any] = {
                "partition": row["partition"],
                "market": market,
                "provider": row["provider"],
                "ny_date": row["ny_date"],
                "side": row["side"],
                "window_id": row["window_id"],
                "tick_window_open_ms": row["tick_window_open_ms"],
                "tick_window_close_ms": row["tick_window_close_ms"],
            }
            if provider_symbol != row["provider"]:
                base.update({"status": "binding_mismatch", "bid_count": 0, "ask_count": 0, "resolved_provider_symbol": provider_symbol})
                results.append(base)
                continue
            try:
                bid = _collect_with_retry(
                    client,
                    account_id=account_id,
                    symbol_id=symbol.symbol_id,
                    quote_type="BID",
                    opened_ms=row["tick_window_open_ms"],
                    closed_ms=row["tick_window_close_ms"],
                )
                ask = _collect_with_retry(
                    client,
                    account_id=account_id,
                    symbol_id=symbol.symbol_id,
                    quote_type="ASK",
                    opened_ms=row["tick_window_open_ms"],
                    closed_ms=row["tick_window_close_ms"],
                )
            except CTraderDemoLabProbeError as error:
                base.update({"status": "probe_failure", "bid_count": 0, "ask_count": 0, "error_type": type(error).__name__, "error_message": str(error)})
                results.append(base)
                continue

            bid_projection = _projection(bid, symbol.digits)
            ask_projection = _projection(ask, symbol.digits)
            if bid_projection and ask_projection:
                status = "available"
            elif bid_projection or ask_projection:
                status = "partial"
            else:
                status = "empty"
            evidence: dict[str, Any] = {
                "schema": "qore.vt31.consumed_historical_tick_window.v3",
                "research_only": True,
                "opens_new_holdout": False,
                "source_window": row,
                "market": market,
                "provider_symbol": provider_symbol,
                "symbol_id": symbol.symbol_id,
                "digits": symbol.digits,
                "account_fingerprint": fingerprint,
                "opened_ms": row["tick_window_open_ms"],
                "closed_ms": row["tick_window_close_ms"],
                "bid": bid_projection,
                "ask": ask_projection,
            }
            evidence_sha = _canonical_sha(evidence)
            evidence["sha256"] = evidence_sha
            evidence_path = evidence_dir / f"{row['window_id']}.json"
            evidence_path.write_text(json.dumps(evidence, sort_keys=True, separators=(",", ":")) + "\n")
            base.update(
                {
                    "status": status,
                    "bid_count": len(bid_projection),
                    "ask_count": len(ask_projection),
                    "bid_first_ms": bid_projection[0]["timestamp_ms"] if bid_projection else None,
                    "bid_last_ms": bid_projection[-1]["timestamp_ms"] if bid_projection else None,
                    "ask_first_ms": ask_projection[0]["timestamp_ms"] if ask_projection else None,
                    "ask_last_ms": ask_projection[-1]["timestamp_ms"] if ask_projection else None,
                    "provider_symbol": provider_symbol,
                    "symbol_id": symbol.symbol_id,
                    "digits": symbol.digits,
                    "account_fingerprint": fingerprint,
                    "evidence_sha256": evidence_sha,
                    "evidence_file": evidence_path.name,
                }
            )
            results.append(base)
            if index % 25 == 0 or status != "available" or index == len(windows):
                print(index, len(windows), market, row["ny_date"], status, len(bid_projection), len(ask_projection))
    finally:
        client.close()

    total = len(windows)
    summary: dict[str, Any] = {
        "schema": "qore.vt31.bounded_consumed_historical_tick_acquisition.v1",
        "research_only": True,
        "opens_new_holdout": False,
        "candidate_status": "NO_R9_NOT_CERTIFIED",
        "source_manifest": manifest_path.name,
        "source_window_count": total,
        "available": sum(row["status"] == "available" for row in results),
        "partial": sum(row["status"] == "partial" for row in results),
        "empty": sum(row["status"] == "empty" for row in results),
        "probe_failure": sum(row["status"] == "probe_failure" for row in results),
        "binding_mismatch": sum(row["status"] == "binding_mismatch" for row in results),
        "groups": _group_counts(results),
        "results": results,
    }
    if len(results) != total:
        raise AssertionError("bounded acquisition lost manifest rows")
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "vt31-bounded-tick-acquisition-summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    summary = acquire(args.manifest, args.output_dir)
    print(json.dumps({key: summary[key] for key in ("source_window_count", "available", "partial", "empty", "probe_failure", "binding_mismatch")}, sort_keys=True))


if __name__ == "__main__":
    main()
