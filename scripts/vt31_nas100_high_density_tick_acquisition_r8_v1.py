"""Acquire BID/ASK ticks for the 49 unresolved R8 high-density minutes.

Research-only consumed-evidence acquisition.

The source manifest is produced by VT31_NAS100 R5 High Density Tick Manifest V1.
Only the exact missing R8 windows are queried. No new dates are discovered and no
fresh holdout is opened. Unavailable data remains explicit and censored.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from vt31_historical_tick_batch_acquisition import (
    _canonical_sha,
    _collect_with_retry,
    _credentials,
)
from vt31_historical_tick_probe import (
    _enable_research_tick_messages,
    _projection,
)

from qore.infrastructure.ctrader_demo_lab_probe import CTraderDemoLabProbeError
from qore.infrastructure.ctrader_demo_lab_vt31_v2_probe import (
    _connect_and_resolve_market,
)
from qore.infrastructure.ctrader_open_api_client import SpotwareCTraderOpenApiClient

SCHEMA = "qore.vt31.nas100.high_density_tick_acquisition.r8.v1"
MARKET = "NAS100"
PROVIDER = "USTEC"
EXPECTED_WINDOWS = 49
EXPECTED_SOURCE_MANIFEST_SHA256 = (
    "8014f420cc518e4897f1e5e3917cb93ca51b0beff41e8009331f22227137509a"
)


def _load_manifest(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text())
    if payload.get("research_only") is not True:
        raise CTraderDemoLabProbeError("manifest must be research-only")
    if payload.get("opens_new_holdout") is not False:
        raise CTraderDemoLabProbeError("manifest must not open a holdout")
    if payload.get("source_manifest_sha256") != EXPECTED_SOURCE_MANIFEST_SHA256:
        raise CTraderDemoLabProbeError("source manifest fingerprint changed")
    windows = payload.get("windows")
    if not isinstance(windows, list) or len(windows) != EXPECTED_WINDOWS:
        raise CTraderDemoLabProbeError(
            "manifest must contain exactly 50 unresolved windows"
        )

    identities: set[str] = set()
    for row in windows:
        if not isinstance(row, dict):
            raise CTraderDemoLabProbeError("window row is malformed")
        if row.get("partition") != "r8_fresh":
            raise CTraderDemoLabProbeError("only R8 is authorized")
        if row.get("market") != MARKET:
            raise CTraderDemoLabProbeError("only NAS100 is authorized")
        if row.get("provider") != PROVIDER:
            raise CTraderDemoLabProbeError("provider binding changed")
        window_id = row.get("window_id")
        opened_ms = row.get("tick_window_open_ms")
        closed_ms = row.get("tick_window_close_ms")
        if not isinstance(window_id, str) or not window_id:
            raise CTraderDemoLabProbeError("window id is malformed")
        if window_id in identities:
            raise CTraderDemoLabProbeError("window ids must be unique")
        identities.add(window_id)
        if type(opened_ms) is not int or type(closed_ms) is not int:
            raise CTraderDemoLabProbeError("window boundaries are malformed")
        if closed_ms <= opened_ms or closed_ms - opened_ms != 59_999:
            raise CTraderDemoLabProbeError("window must be exact M1")
    return payload


def acquire(manifest_path: Path, output_dir: Path) -> dict[str, Any]:
    manifest = _load_manifest(manifest_path)
    windows = sorted(
        manifest["windows"],
        key=lambda row: (row["tick_window_open_ms"], row["window_id"]),
    )
    evidence_dir = output_dir / "windows"
    evidence_dir.mkdir(parents=True, exist_ok=True)

    client = SpotwareCTraderOpenApiClient(credentials=_credentials())
    results: list[dict[str, Any]] = []
    try:
        _enable_research_tick_messages(client)
        account_id, fingerprint, symbol, provider_symbol = (
            _connect_and_resolve_market(
                client,
                market=MARKET,
                timeout_seconds=12.0,
            )
        )
        if provider_symbol != PROVIDER:
            raise CTraderDemoLabProbeError(
                "NAS100 provider does not resolve to USTEC"
            )

        for index, row in enumerate(windows, start=1):
            base: dict[str, Any] = {
                "partition": "r8_fresh",
                "market": MARKET,
                "provider": PROVIDER,
                "ny_date": row["ny_date"],
                "classification": row["classification"],
                "side": row["side"],
                "window_id": row["window_id"],
                "tick_window_open_ms": row["tick_window_open_ms"],
                "tick_window_close_ms": row["tick_window_close_ms"],
            }
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
                base.update(
                    {
                        "status": "probe_failure",
                        "bid_count": 0,
                        "ask_count": 0,
                        "error_type": type(error).__name__,
                        "error_message": str(error),
                    }
                )
                results.append(base)
                print(index, row["ny_date"], "probe_failure")
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
                "schema": "qore.vt31.nas100.high_density_tick_window.v1",
                "research_only": True,
                "opens_new_holdout": False,
                "source_window": row,
                "market": MARKET,
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
                json.dumps(evidence, sort_keys=True, separators=(",", ":"))
                + "\n"
            )
            base.update(
                {
                    "status": status,
                    "bid_count": bid_count,
                    "ask_count": ask_count,
                    "bid_first_ms": (
                        bid_projection[0]["timestamp_ms"]
                        if bid_projection
                        else None
                    ),
                    "bid_last_ms": (
                        bid_projection[-1]["timestamp_ms"]
                        if bid_projection
                        else None
                    ),
                    "ask_first_ms": (
                        ask_projection[0]["timestamp_ms"]
                        if ask_projection
                        else None
                    ),
                    "ask_last_ms": (
                        ask_projection[-1]["timestamp_ms"]
                        if ask_projection
                        else None
                    ),
                    "provider_symbol": provider_symbol,
                    "symbol_id": symbol.symbol_id,
                    "digits": symbol.digits,
                    "account_fingerprint": fingerprint,
                    "evidence_sha256": evidence_sha,
                    "evidence_file": evidence_path.name,
                }
            )
            results.append(base)
            print(
                index,
                row["ny_date"],
                status,
                bid_count,
                ask_count,
            )
    finally:
        client.close()

    summary = {
        "schema": SCHEMA,
        "research_only": True,
        "opens_new_holdout": False,
        "candidate_status": "NO_FINAL_CANDIDATE_NOT_CERTIFIED",
        "source_manifest": manifest_path.name,
        "source_manifest_sha256": EXPECTED_SOURCE_MANIFEST_SHA256,
        "source_window_count": EXPECTED_WINDOWS,
        "available": sum(row["status"] == "available" for row in results),
        "partial": sum(row["status"] == "partial" for row in results),
        "empty": sum(row["status"] == "empty" for row in results),
        "probe_failure": sum(
            row["status"] == "probe_failure" for row in results
        ),
        "results": results,
    }
    if len(results) != EXPECTED_WINDOWS:
        raise AssertionError("tick acquisition lost manifest rows")
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "high-density-tick-acquisition-summary.json").write_text(
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
                )
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
