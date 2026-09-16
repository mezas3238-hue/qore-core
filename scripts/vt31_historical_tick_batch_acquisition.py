"""Acquire BID/ASK ticks for the immutable 437-window VT-31 consumed manifest.

This module is research-only. It never opens a fresh holdout, changes trader rules,
or authorizes execution. Every requested window must already exist in the immutable
R5/R6/R8 consumed manifest. Provider/account binding is exact and failures remain
explicitly unresolved rather than being imputed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from qore.infrastructure.ctrader_demo_lab_long_horizon_probe import _required_env
from qore.infrastructure.ctrader_demo_lab_probe import CTraderDemoLabProbeError
from qore.infrastructure.ctrader_demo_lab_vt31_v2_probe import (
    _RESEARCH_MARKETS,
    _connect_and_resolve_market,
)
from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiCredentials,
    SpotwareCTraderOpenApiClient,
)

from vt31_historical_tick_probe import (
    _MIN_REQUEST_INTERVAL_SECONDS,
    _collect_side,
    _enable_research_tick_messages,
    _projection,
)

_EXPECTED_COUNTS = {"r5": 157, "r6": 159, "r8_fresh": 121}
_EXPECTED_TOTAL = sum(_EXPECTED_COUNTS.values())
_MAX_ATTEMPTS = 3
_RETRY_BACKOFF_SECONDS = (0.50, 1.00)
_INTER_REQUEST_SECONDS = max(0.25, _MIN_REQUEST_INTERVAL_SECONDS)


def _credentials() -> CTraderOpenApiCredentials:
    return CTraderOpenApiCredentials(
        client_id=_required_env("QORE_CTRADER_CLIENT_ID", "QORE_CTRADER_DEMO_CLIENT_ID"),
        client_secret=_required_env(
            "QORE_CTRADER_CLIENT_SECRET", "QORE_CTRADER_DEMO_CLIENT_SECRET"
        ),
        access_token=_required_env(
            "QORE_CTRADER_ACCESS_TOKEN", "QORE_CTRADER_DEMO_ACCESS_TOKEN"
        ),
        refresh_token=_required_env(
            "QORE_CTRADER_REFRESH_TOKEN", "QORE_CTRADER_DEMO_REFRESH_TOKEN"
        ),
        ctid_trader_account_id=int(
            _required_env("QORE_CTRADER_DEMO_ACCOUNT_ID", "QORE_CTRADER_ACCOUNT_ID")
        ),
    )


def _load_manifest(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text())
    if payload.get("research_only") is not True:
        raise CTraderDemoLabProbeError("tick manifest must be research-only")
    if payload.get("opens_new_holdout") is not False:
        raise CTraderDemoLabProbeError("tick manifest must not open a new holdout")
    windows = payload.get("windows")
    if not isinstance(windows, list) or len(windows) != _EXPECTED_TOTAL:
        raise CTraderDemoLabProbeError("tick manifest must contain exactly 437 windows")
    observed: dict[str, int] = defaultdict(int)
    identities: set[str] = set()
    for row in windows:
        if not isinstance(row, dict):
            raise CTraderDemoLabProbeError("tick manifest row is malformed")
        partition = row.get("partition")
        market = row.get("market")
        window_id = row.get("window_id")
        opened_ms = row.get("tick_window_open_ms")
        closed_ms = row.get("tick_window_close_ms")
        if partition not in _EXPECTED_COUNTS:
            raise CTraderDemoLabProbeError("tick manifest partition is unexpected")
        if market not in _RESEARCH_MARKETS:
            raise CTraderDemoLabProbeError("tick manifest market is unexpected")
        if not isinstance(window_id, str) or not window_id:
            raise CTraderDemoLabProbeError("tick manifest window id is malformed")
        if window_id in identities:
            raise CTraderDemoLabProbeError("tick manifest window ids must be unique")
        identities.add(window_id)
        if type(opened_ms) is not int or type(closed_ms) is not int:
            raise CTraderDemoLabProbeError("tick manifest boundaries are malformed")
        if closed_ms <= opened_ms or closed_ms - opened_ms != 59_999:
            raise CTraderDemoLabProbeError("tick manifest must contain exact M1 windows")
        observed[partition] += 1
    if dict(observed) != _EXPECTED_COUNTS:
        raise CTraderDemoLabProbeError("tick manifest partition counts changed")
    return payload


def _canonical_sha(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def _collect_with_retry(
    client: SpotwareCTraderOpenApiClient,
    *,
    account_id: int,
    symbol_id: int,
    quote_type: str,
    opened_ms: int,
    closed_ms: int,
) -> tuple[object, ...]:
    last_error: Exception | None = None
    for attempt in range(_MAX_ATTEMPTS):
        time.sleep(_INTER_REQUEST_SECONDS)
        try:
            return _collect_side(
                client,
                account_id=account_id,
                symbol_id=symbol_id,
                quote_type=quote_type,
                opened_ms=opened_ms,
                closed_ms=closed_ms,
                timeout_seconds=12.0,
            )
        except CTraderDemoLabProbeError as error:
            last_error = error
            if attempt + 1 >= _MAX_ATTEMPTS:
                break
            time.sleep(_RETRY_BACKOFF_SECONDS[attempt])
    if last_error is None:
        raise AssertionError("historical tick retry loop exited without result")
    raise last_error


def _group_counts(results: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    groups: dict[str, dict[str, int]] = {}
    for result in results:
        key = f"{result['partition']}:{result['market']}"
        group = groups.setdefault(
            key,
            {
                "available": 0,
                "partial": 0,
                "empty": 0,
                "probe_failure": 0,
                "binding_mismatch": 0,
            },
        )
        group[result["status"]] += 1
    return groups


def acquire(manifest_path: Path, output_dir: Path) -> dict[str, Any]:
    manifest = _load_manifest(manifest_path)
    windows = sorted(
        manifest["windows"],
        key=lambda row: (
            row["market"],
            row["tick_window_open_ms"],
            row["window_id"],
        ),
    )
    evidence_dir = output_dir / "windows"
    evidence_dir.mkdir(parents=True, exist_ok=True)

    client = SpotwareCTraderOpenApiClient(credentials=_credentials())
    results: list[dict[str, Any]] = []
    try:
        _enable_research_tick_messages(client)
        bindings: dict[str, tuple[int, str, object, str]] = {}
        for market in sorted(_RESEARCH_MARKETS):
            bindings[market] = _connect_and_resolve_market(
                client,
                market=market,
                timeout_seconds=12.0,
            )
        account_ids = {binding[0] for binding in bindings.values()}
        fingerprints = {binding[1] for binding in bindings.values()}
        if len(account_ids) != 1 or len(fingerprints) != 1:
            raise CTraderDemoLabProbeError(
                "historical tick markets must share one exact account binding"
            )

        for index, row in enumerate(windows, start=1):
            market = row["market"]
            account_id, fingerprint, symbol, provider_symbol = bindings[market]
            base_result: dict[str, Any] = {
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
                base_result.update(
                    {
                        "status": "binding_mismatch",
                        "bid_count": 0,
                        "ask_count": 0,
                        "resolved_provider_symbol": provider_symbol,
                    }
                )
                results.append(base_result)
                print(
                    index,
                    market,
                    row["ny_date"],
                    "binding_mismatch",
                    provider_symbol,
                )
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
                base_result.update(
                    {
                        "status": "probe_failure",
                        "bid_count": 0,
                        "ask_count": 0,
                        "error_type": type(error).__name__,
                        "error_message": str(error),
                    }
                )
                results.append(base_result)
                print(index, market, row["ny_date"], "probe_failure")
                continue

            bid_projection = _projection(bid, symbol.digits)
            ask_projection = _projection(ask, symbol.digits)
            bid_count = len(bid_projection)
            ask_count = len(ask_projection)
            if bid_count and ask_count:
                status = "available"
            elif bid_count or ask_count:
                status = "partial"
            else:
                status = "empty"
            evidence: dict[str, Any] = {
                "schema": "qore.vt31.consumed_historical_tick_window.v2",
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
            evidence_path.write_text(
                json.dumps(evidence, sort_keys=True, separators=(",", ":")) + "\n"
            )
            base_result.update(
                {
                    "status": status,
                    "bid_count": bid_count,
                    "ask_count": ask_count,
                    "bid_first_ms": bid_projection[0]["timestamp_ms"]
                    if bid_projection
                    else None,
                    "bid_last_ms": bid_projection[-1]["timestamp_ms"]
                    if bid_projection
                    else None,
                    "ask_first_ms": ask_projection[0]["timestamp_ms"]
                    if ask_projection
                    else None,
                    "ask_last_ms": ask_projection[-1]["timestamp_ms"]
                    if ask_projection
                    else None,
                    "provider_symbol": provider_symbol,
                    "symbol_id": symbol.symbol_id,
                    "digits": symbol.digits,
                    "account_fingerprint": fingerprint,
                    "evidence_sha256": evidence_sha,
                    "evidence_file": evidence_path.name,
                }
            )
            results.append(base_result)
            if index % 25 == 0 or status != "available" or index == len(windows):
                print(index, market, row["ny_date"], status, bid_count, ask_count)
    finally:
        client.close()

    summary: dict[str, Any] = {
        "schema": "qore.vt31.consumed_historical_tick_acquisition.v1",
        "research_only": True,
        "opens_new_holdout": False,
        "candidate_status": "NO_R9_NOT_CERTIFIED",
        "source_manifest": manifest_path.name,
        "source_window_count": _EXPECTED_TOTAL,
        "request_policy": {
            "quote_sides": ["BID", "ASK"],
            "max_attempts": _MAX_ATTEMPTS,
            "retry_backoff_seconds": list(_RETRY_BACKOFF_SECONDS),
            "minimum_inter_request_seconds": _INTER_REQUEST_SECONDS,
            "unavailable_or_failed_windows": "remain_censored_no_imputation",
        },
        "available": sum(result["status"] == "available" for result in results),
        "partial": sum(result["status"] == "partial" for result in results),
        "empty": sum(result["status"] == "empty" for result in results),
        "probe_failure": sum(
            result["status"] == "probe_failure" for result in results
        ),
        "binding_mismatch": sum(
            result["status"] == "binding_mismatch" for result in results
        ),
        "groups": _group_counts(results),
        "results": results,
    }
    if len(results) != _EXPECTED_TOTAL:
        raise AssertionError("historical tick acquisition lost manifest rows")
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "vt31-historical-tick-acquisition-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    summary = acquire(args.manifest, args.output_dir)
    print(
        json.dumps(
            {
                key: summary[key]
                for key in (
                    "source_window_count",
                    "available",
                    "partial",
                    "empty",
                    "probe_failure",
                    "binding_mismatch",
                )
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
