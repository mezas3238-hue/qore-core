"""QORE Alpha2 G2 admits original 29 cTrader DEMO quote source artifact.

Only frozen 2020+2023 historical window bytes; do NOT inspect 2026 quotes,
no historical as-of availability assertion, no trader PnL, NET, or orders.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from qore.research.alpha2_intermarket import MARKETS

ORIGINAL_RUN = 38283737706
ORIGINAL_HEAD = "f8262bd7cdea1fbfb2287c3c1fe0dae3be2b0efc"
SOURCE_IDENTITY = "QORE_NATIVE_G1_PRE_REMAINING29_CTRADER_BIDASK_SOURCE_V1"
G0_SHA = "1291d5c2efb4e51c2698ea25ad420a01a213dc405b5070c37efbce4131606b85"
OMITTED = {"NZDUSD", "XAGUSD", "SP500", "NAS100"}
SOURCE_29 = set(MARKETS) - OMITTED
WINDOWS = (
    ("2020-09-15T13:00:00+00:00", "2020-09-15T13:10:00+00:00"),
    ("2023-09-19T13:00:00+00:00", "2023-09-19T13:10:00+00:00"),
    ("2026-09-15T13:00:00+00:00", "2026-09-15T13:10:00+00:00"),
)
SCALE = Decimal(100000)
ID = "QORE_ALPHA2_G2_29_BIDASK_PAST_SOURCE_TWO_WINDOWS_INDEPENDENT_SHA_V1"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as input_file:
        for buf in iter(lambda: input_file.read(1024*1024), b""):
            h.update(buf)
    return h.hexdigest()


def manifest_sha(root: Path, name: str, ledger: str) -> Path:
    text = (root / ledger).read_text(encoding="utf-8").strip().splitlines()
    found = {}
    for line in text:
        parts = line.split()
        if len(parts)!=2 or parts[1] in found:
            raise ValueError("SOURCE_SHA_MANIFEST_INVALID")
        found[parts[1]]=parts[0]
    if name not in found:
        raise ValueError("SOURCE_WITNESS_MISSING")
    path=root / name
    if not path.is_file() or digest(path)!=found[name]:
        raise ValueError("SOURCE_MANIFEST_ORIGINAL_SHA_INVALID")
    return path


def audit_two_sides(
    folder: Path, symbol: str, window_index: int,
    window: tuple[str,str], side: str, source_meta: dict,
    witnesses: dict[str,str],
) -> dict:
    if side not in ("BID", "ASK") or window_index not in (1,2):
        raise ValueError("HOLDOUT_OR_SIDE_OUT_OF_SCOPE")
    left, right=(int(datetime.fromisoformat(t).timestamp()*1000) for t in window)
    native_name=f"{symbol}-{window_index}-{side}-integer.jsonl"
    decoded_name=f"{symbol}-{window_index}-{side}-decoded.jsonl"
    if (source_meta.get("native_int_file") != native_name
            or source_meta.get("decoded_file") != decoded_name):
        raise ValueError("SOURCED_NATIVE_DECIMAL_FILE_SCOPE_DRIFT")
    files = [folder/native_name, folder/decoded_name]
    for path,declared in zip(
        files,
        (source_meta.get("native_int_sha256"),source_meta.get("decoded_sha256")),
        strict=True,
    ):
        if not path.is_file() or path.name not in witnesses:
            raise ValueError("BIDASK_RAW_FILE_OR_WITNESS_MISSING")
        h=digest(path)
        if h!=witnesses[path.name] or h!=declared:
            raise ValueError("BIDASK_NATIVE_OR_DECIMAL_SHA_MISMATCH")
    count=0
    prev=None
    min_at=None
    max_at=None
    with files[0].open(encoding="utf-8") as raw, files[1].open(encoding="utf-8") as decoded:
        for raw_line, dec_line in zip(raw,decoded,strict=True):
            orig=json.loads(raw_line)
            readable=json.loads(dec_line)
            at=orig.get("epoch_ms")
            integer=orig.get("integer_price_1e5")
            if (type(at) is not int or type(integer) is not int or integer<=0
                    or not left<=at<right
                    or prev is not None and at<prev
                    or readable.get("native_sequence")!=count):
                raise ValueError("ORIGINAL_BIDASK_TICK_TIME_OR_SOURCE_INVALID")
            expected_time=(datetime.fromtimestamp(at/1000,tz=UTC)
                           .isoformat(timespec="milliseconds").replace("+00:00","Z"))
            if (readable.get("event_time_utc")!=expected_time
                    or Decimal(str(readable.get("price"))) != Decimal(integer)/SCALE):
                raise ValueError("NATIVE_INTEGER_VS_DECIMAL_OR_TIME_DIFFERENT")
            count+=1
            prev=at
            min_at=at if min_at is None else min_at
            max_at=at
    if count == 0 or count!=source_meta.get("native_tick_count"):
        raise ValueError("ORIGINAL_NONEMPTY_NATIVE_TICK_COUNT_MISMATCH")
    return {
        "tick_count":count,"earliest_ms":min_at,"latest_ms":max_at,
        "native_int_sha256":witnesses[native_name],
        "decoded_sha256":witnesses[decoded_name],
        "broker_side":side, "trade_fills_proven":False,
    }


def audit(original: Path) -> dict:
    summary_name="G1-29-SOURCE-CENSUS-NOT-NET.json"
    path=manifest_sha(original,summary_name,"G1_CENSUS_SHA256SUMS.txt")
    source=json.loads(path.read_text(encoding="utf-8"))
    if (len(SOURCE_29)!=29
            or source.get("identity")!=SOURCE_IDENTITY
            or source.get("g0_source_sha256")!=G0_SHA
            or source.get("status")!="G1_ALL_29_THREE_WINDOWS_SOURCE_PASS_NOT_NET"
            or source.get("attempted")!=29 or source.get("complete")!=29
            or set(source.get("source_markets_requested",[]))!=SOURCE_29
            or source.get("historical_NET_authorized") is not False
            or source.get("trade_orders_sent")!=0
            or source.get("token_refresh_attempts")!=0):
        raise ValueError("29_SOURCE_ROOT_PROVENANCE_OR_ROSTER_INVALID")
    result={}
    for symbol in sorted(SOURCE_29):
        folder=original/symbol
        rootmanifest=manifest_sha(
            folder,"SOURCE-MANIFEST-NOT-NET.json","SOURCE_SHA256SUMS.txt"
        )
        evidence=json.loads(rootmanifest.read_text(encoding="utf-8"))
        if (evidence.get("identity") != SOURCE_IDENTITY
                or evidence.get("canonical_symbol") != symbol
                or evidence.get("provider_symbol") != symbol
                or evidence.get("provider")!="ICMARKETS_CTRADER_DEMO"
                or evidence.get("account_type")!="DEMO"
                or evidence.get("source_g0_sha256")!=G0_SHA
                or evidence.get("state")!="THREE_WINDOWS_NATIVE_BID_ASK_PRESENT_NOT_NET"
                or evidence.get("complete_windows")!=3
                or evidence.get("source_captured_both_sides") is not True
                or tuple(tuple(x) for x in evidence.get("frozen_windows",[]))!=WINDOWS
                or evidence.get("historical_NET_authorized") is not False
                or evidence.get("trade_orders_sent")!=0
                or evidence.get("token_refresh_attempts")!=0):
            raise ValueError("29_SOURCE_SYMBOL_ACCOUNT_OR_WINDOW_SCOPE_INVALID")
        witnesses={}
        for line in (folder/"SOURCE_SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
            v=line.split()
            if len(v)!=2 or v[1] in witnesses or "/" in v[1] or ".." in v[1]:
                raise ValueError("SIDE_SHA256_WITNESS_INVALID")
            witnesses[v[1]]=v[0]
        if len(witnesses)!=13:
            raise ValueError("29_SOURCE_SIDE_WITNESS_EXPECTED_13")
        bywindow={}
        for idx in (1,2):
            row=evidence["windows"][idx-1]
            if (tuple(row.get("utc_range",[]))!=WINDOWS[idx-1]
                    or row.get("both_sides_nonempty") is not True):
                raise ValueError("29_SOURCE_ORIGINAL_CLOCK_DRIFT")
            bywindow[str(idx)]={
                side:audit_two_sides(
                    folder,symbol,idx,WINDOWS[idx-1],
                    side,row["by_side"][side],witnesses
                )
                for side in ("BID","ASK")
            }
        result[symbol]={
            "provider":"ICMARKETS_CTRADER_DEMO",
            "provider_symbol_id":evidence["provider_symbol_id"],
            "original_manifest_sha256":digest(rootmanifest),
            "consumed_past_windows_only":bywindow,
            "2026_window_price_bytes_not_accessed":True,
            "historical_asof_availability_verified":False,
            "contract_identical_to_original_12_verified":False,
        }
    return {
        "identity":ID,"status":"SOURCE29_TWO_PAST_WINDOWS_SHA_VERIFIED_NOT_NET",
        "source_original_actions_run":ORIGINAL_RUN,
        "source_original_code_head":ORIGINAL_HEAD,
        "source_root_sha256":digest(path),
        "market_count":29,"all_29":result,
        "total_two_eras_bid_ticks":sum(
            w["BID"]["tick_count"] for m in result.values()
            for w in m["consumed_past_windows_only"].values()
        ),
        "total_two_eras_ask_ticks":sum(
            w["ASK"]["tick_count"] for m in result.values()
            for w in m["consumed_past_windows_only"].values()
        ),
        "market_universe_certified":False,
        "net_costs_history_complete":False,
        "market_execution_asof_verified":False,
        "holdout_2026_quote_values_unread":True,
        "gross_methods_W1_W2_W3_still_no_support":True,
        "traders_certified":0,"live_order_authorized":False,
    }


def main() -> None:
    p=argparse.ArgumentParser()
    p.add_argument("original_artifact",type=Path)
    p.add_argument("output",type=Path)
    args=p.parse_args()
    result=audit(args.original_artifact)
    args.output.mkdir(parents=True,exist_ok=True)
    path=args.output/"alpha2-g2-real29-two-past-windows-source-index.json"
    path.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({
        "status":result["status"],"markets":result["market_count"],
        "bid_ticks_consumed_windows":result["total_two_eras_bid_ticks"],
        "ask_ticks_consumed_windows":result["total_two_eras_ask_ticks"],
        "holdout_tick_prices_unread":True,"NET":"BLOCKED",
    },sort_keys=True))


if __name__=="__main__":
    main()
