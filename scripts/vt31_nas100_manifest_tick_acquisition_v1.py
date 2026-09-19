"""Acquire exact BID/ASK ticks from a governed missing-window manifest.

Research-only utility for already-consumed VT31 NAS100 evidence. The manifest
fully determines the queried minutes; this script cannot discover additional
dates or open a fresh holdout.
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

SCHEMA="qore.vt31.nas100.manifest_tick_acquisition.v1"
MARKET="NAS100"
PROVIDER="USTEC"


def _load_manifest(
    path: Path,
    *,
    partition: str,
    expected_count: int,
) -> dict[str, Any]:
    payload=json.loads(path.read_text())
    if payload.get("research_only") is not True:
        raise CTraderDemoLabProbeError("manifest must be research-only")
    if payload.get("opens_new_holdout") is not False:
        raise CTraderDemoLabProbeError("manifest must not open a holdout")
    windows=payload.get("windows")
    if not isinstance(windows,list) or len(windows)!=expected_count:
        raise CTraderDemoLabProbeError(
            f"expected {expected_count} exact windows"
        )
    if payload.get("window_count")!=expected_count:
        raise CTraderDemoLabProbeError("manifest count binding failed")

    seen: set[str]=set()
    for row in windows:
        if not isinstance(row,dict):
            raise CTraderDemoLabProbeError("window row is malformed")
        if row.get("partition")!=partition:
            raise CTraderDemoLabProbeError("partition binding changed")
        if row.get("market")!=MARKET:
            raise CTraderDemoLabProbeError("market binding changed")
        if row.get("provider")!=PROVIDER:
            raise CTraderDemoLabProbeError("provider binding changed")
        window_id=row.get("window_id")
        opened=row.get("tick_window_open_ms")
        closed=row.get("tick_window_close_ms")
        if not isinstance(window_id,str) or not window_id:
            raise CTraderDemoLabProbeError("window id is malformed")
        if window_id in seen:
            raise CTraderDemoLabProbeError("window ids must be unique")
        seen.add(window_id)
        if type(opened) is not int or type(closed) is not int:
            raise CTraderDemoLabProbeError("window boundaries malformed")
        if closed<=opened or closed-opened!=59_999:
            raise CTraderDemoLabProbeError("window must be exact M1")
    return payload


def acquire(
    manifest_path: Path,
    *,
    partition: str,
    expected_count: int,
    output_dir: Path,
) -> dict[str,Any]:
    manifest=_load_manifest(
        manifest_path,
        partition=partition,
        expected_count=expected_count,
    )
    windows=sorted(
        manifest["windows"],
        key=lambda row:(row["tick_window_open_ms"],row["window_id"]),
    )
    evidence_dir=output_dir/"windows"
    evidence_dir.mkdir(parents=True,exist_ok=True)

    client=SpotwareCTraderOpenApiClient(credentials=_credentials())
    results: list[dict[str,Any]]=[]
    try:
        _enable_research_tick_messages(client)
        account_id,fingerprint,symbol,provider_symbol=(
            _connect_and_resolve_market(
                client,
                market=MARKET,
                timeout_seconds=12.0,
            )
        )
        if provider_symbol!=PROVIDER:
            raise CTraderDemoLabProbeError(
                "NAS100 provider does not resolve to USTEC"
            )

        for index,row in enumerate(windows,start=1):
            base: dict[str,Any]={
                "partition":partition,
                "market":MARKET,
                "provider":PROVIDER,
                "ny_date":row.get("ny_date"),
                "classification":row.get("classification"),
                "variant":row.get("variant"),
                "window_id":row["window_id"],
                "tick_window_open_ms":row["tick_window_open_ms"],
                "tick_window_close_ms":row["tick_window_close_ms"],
            }
            try:
                bid=_collect_with_retry(
                    client,
                    account_id=account_id,
                    symbol_id=symbol.symbol_id,
                    quote_type="BID",
                    opened_ms=row["tick_window_open_ms"],
                    closed_ms=row["tick_window_close_ms"],
                )
                ask=_collect_with_retry(
                    client,
                    account_id=account_id,
                    symbol_id=symbol.symbol_id,
                    quote_type="ASK",
                    opened_ms=row["tick_window_open_ms"],
                    closed_ms=row["tick_window_close_ms"],
                )
            except CTraderDemoLabProbeError as error:
                base.update({
                    "status":"probe_failure",
                    "bid_count":0,
                    "ask_count":0,
                    "error_type":type(error).__name__,
                    "error_message":str(error),
                })
                results.append(base)
                print(index,row["ny_date"],"probe_failure")
                continue

            bid_projection=_projection(bid,symbol.digits)
            ask_projection=_projection(ask,symbol.digits)
            bid_count=len(bid_projection)
            ask_count=len(ask_projection)
            if bid_count and ask_count:
                status="available"
            elif bid_count or ask_count:
                status="partial"
            else:
                status="empty"

            evidence: dict[str,Any]={
                "schema":"qore.vt31.nas100.manifest_tick_window.v1",
                "research_only":True,
                "opens_new_holdout":False,
                "source_window":row,
                "market":MARKET,
                "provider_symbol":provider_symbol,
                "symbol_id":symbol.symbol_id,
                "digits":symbol.digits,
                "account_fingerprint":fingerprint,
                "opened_ms":row["tick_window_open_ms"],
                "closed_ms":row["tick_window_close_ms"],
                "bid":bid_projection,
                "ask":ask_projection,
            }
            evidence_sha=_canonical_sha(evidence)
            evidence["sha256"]=evidence_sha
            evidence_path=evidence_dir/f"{row['window_id']}.json"
            evidence_path.write_text(
                json.dumps(
                    evidence,
                    sort_keys=True,
                    separators=(",",":"),
                )+"\n"
            )
            base.update({
                "status":status,
                "bid_count":bid_count,
                "ask_count":ask_count,
                "provider_symbol":provider_symbol,
                "symbol_id":symbol.symbol_id,
                "digits":symbol.digits,
                "account_fingerprint":fingerprint,
                "evidence_sha256":evidence_sha,
                "evidence_file":evidence_path.name,
            })
            results.append(base)
            print(index,row["ny_date"],status,bid_count,ask_count)
    finally:
        client.close()

    summary={
        "schema":SCHEMA,
        "research_only":True,
        "opens_new_holdout":False,
        "candidate_status":"RESEARCH_NOT_CERTIFIED",
        "partition":partition,
        "variant":manifest.get("variant"),
        "source_manifest":manifest_path.name,
        "source_manifest_sha256":manifest.get("source_manifest_sha256"),
        "source_window_count":expected_count,
        "available":sum(r["status"]=="available" for r in results),
        "partial":sum(r["status"]=="partial" for r in results),
        "empty":sum(r["status"]=="empty" for r in results),
        "probe_failure":sum(
            r["status"]=="probe_failure" for r in results
        ),
        "results":results,
    }
    if len(results)!=expected_count:
        raise AssertionError("acquisition lost manifest rows")
    output_dir.mkdir(parents=True,exist_ok=True)
    (output_dir/"manifest-tick-acquisition-summary.json").write_text(
        json.dumps(summary,sort_keys=True,indent=2)+"\n"
    )
    return summary


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--manifest",required=True,type=Path)
    parser.add_argument("--partition",required=True)
    parser.add_argument("--expected-count",required=True,type=int)
    parser.add_argument("--output-dir",required=True,type=Path)
    args=parser.parse_args()
    payload=acquire(
        args.manifest,
        partition=args.partition,
        expected_count=args.expected_count,
        output_dir=args.output_dir,
    )
    print(json.dumps({
        key:payload[key]
        for key in (
            "partition",
            "source_window_count",
            "available",
            "partial",
            "empty",
            "probe_failure",
        )
    },sort_keys=True))


if __name__=="__main__":
    main()
