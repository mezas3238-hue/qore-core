"""Independent SHA + first-received side quote QA of one DEMO NZDUSD pilot.

Source-only, no order, no PnL and NO original quote prices duplicated in output.
Do not equate the app-dequeue timestamp with the dealer's matching engine clock.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

HEAD = "ca32ad2311c5c6b4a9312073ca0b4c7b53109a75"
SOURCE_IDENTITY = "QORE_ALPHA2_G2_ICMARKETS_DEMO_NZDUSD_FORWARD_RECEIPT_V1"
SUCCESS = "FORWARD_RECEIVED_NZDUSD_DEMO_SPOT_SOURCE_PRESENT"
AUDIT_IDENTITY = "QORE_ALPHA2_G2_NZDUSD_INDEPENDENT_DEMO_FIRST_RECEIPT_QA_V1"
STATUS = "FORWARD_DEMO_SOURCE_RECEIPT_SHA_AND_INDEPENDENT_QA_PASS_NOT_EXECUTABLE"
RAW = "nzdusd-demo-forward-first-seen-spot-events.jsonl"
MANIFEST = "alpha2-g2-nzdusd-prospective-demo-source-manifest.json"
SHA_SOURCE = "SOURCE_SHA256SUMS.txt"
SHA_COMPLETE = "COMPLETE_SHA256SUMS.txt"
CODE_HEAD = "exact-code-head-sha.txt"
SCHEMA = {
    "sequence", "source_symbol", "first_observed_by_runner_utc",
    "provider_event_at_ms", "native_bid_1e5", "native_ask_1e5",
    "event_is_NOT_fill", "current_side_freshness_class",
}
VALID_CLASS = {
    "MISSING_OR_STALE_BIDASK",
    "CROSSED_QUOTE_QUARANTINED",
    "ZERO_QUOTE_QUARANTINED",
    "POSITIVE_SPREAD_OBSERVATION_NO_FILL",
}
MAX_SIDE_AGE = timedelta(seconds=5)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _ledger(path: Path, *, filenames: set[str]) -> dict[str, str]:
    entries = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.strip().split()
        if len(parts) != 2 or parts[1] in entries:
            raise ValueError("SOURCE_PROOF_LEDGER_INVALID")
        if parts[1].startswith("/") or ".." in parts[1] or "/" in parts[1]:
            raise ValueError("SOURCE_PROOF_PATH_TRAVERSAL")
        entries[parts[1]] = parts[0]
    if set(entries) != filenames:
        raise ValueError("SOURCE_PROOF_FILE_SET_DIFFERENT")
    return entries


def _utc(value: Any) -> datetime:
    if type(value) is not str:
        raise ValueError("COLLECTOR_TIMESTAMP_MISSING")
    try:
        dt = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValueError("COLLECTOR_TIMESTAMP_INVALID") from None
    if dt.tzinfo is None or dt.utcoffset() != timedelta(0):
        raise ValueError("COLLECTOR_TIMESTAMP_NOT_UTC")
    return dt


def _valid_integer_price(value: Any, label: str) -> None:
    if value is not None and (type(value) is not int or value <= 0):
        raise ValueError(f"{label}_SOURCE_PRICE_TYPE_INVALID")


def qa_events(records: list[dict[str, Any]]) -> dict:
    if not records:
        raise ValueError("SOURCE_NO_RECEIVED_SPOT_EVENTS")
    counts: Counter[str] = Counter()
    last_bid: int | None = None
    last_ask: int | None = None
    bid_seen: datetime | None = None
    ask_seen: datetime | None = None
    prev: datetime | None = None
    first: datetime | None = None
    for i, record in enumerate(records):
        if not isinstance(record, dict) or set(record) != SCHEMA:
            raise ValueError("SOURCE_SPOT_SCHEMA_UNEXPECTED")
        if (record["sequence"] != i or type(record["sequence"]) is not int
                or record["source_symbol"] != "NZDUSD"
                or record["event_is_NOT_fill"] is not True):
            raise ValueError("SOURCE_SPOT_ID_OR_SEQUENCE_DIFFERENT")
        now = _utc(record["first_observed_by_runner_utc"])
        if prev is not None and now < prev:
            raise ValueError("SOURCE_COLLECTOR_CLOCK_REVERSED")
        first = now if first is None else first
        prev = now
        event_timestamp = record["provider_event_at_ms"]
        if event_timestamp is not None:
            if type(event_timestamp) is not int or event_timestamp <= 0:
                raise ValueError("SOURCE_SPOT_PROVIDER_TIME_INVALID")
            try:
                event_at = datetime.fromtimestamp(event_timestamp / 1000, tz=UTC)
            except (ValueError, OverflowError, OSError):
                raise ValueError("SOURCE_SPOT_PROVIDER_TIME_INVALID") from None
            if event_at > now:
                raise ValueError("SOURCE_PROVIDER_EVENT_LATER_THAN_RECEIPT")
            counts["events_with_provider_timestamp"] += 1
        bid = record["native_bid_1e5"]
        ask = record["native_ask_1e5"]
        _valid_integer_price(bid, "BID")
        _valid_integer_price(ask, "ASK")
        if bid is None and ask is None:
            raise ValueError("SOURCE_BOTH_SIDES_MISSING_IN_EVENT")
        if bid is not None:
            counts["bid_updates"] += 1
            last_bid,bid_seen = bid,now
        if ask is not None:
            counts["ask_updates"] += 1
            last_ask,ask_seen = ask,now
        if (last_bid is None or last_ask is None
                or bid_seen is None or ask_seen is None
                or now-bid_seen > MAX_SIDE_AGE
                or now-ask_seen > MAX_SIDE_AGE):
            classification = "MISSING_OR_STALE_BIDASK"
        elif last_ask < last_bid:
            classification = "CROSSED_QUOTE_QUARANTINED"
        elif last_ask == last_bid:
            classification = "ZERO_QUOTE_QUARANTINED"
        else:
            classification = "POSITIVE_SPREAD_OBSERVATION_NO_FILL"
        if (record["current_side_freshness_class"] not in VALID_CLASS
                or classification != record["current_side_freshness_class"]):
            raise ValueError("SOURCE_BIDASK_FIRST_SEEN_CLASSIFICATION_DIFFERENT")
        counts[classification] += 1
    if counts["bid_updates"] == 0 or counts["ask_updates"] == 0:
        raise ValueError("SOURCE_NOT_TWO_SIDED")
    if prev is None or first is None or prev-first > timedelta(seconds=50):
        raise ValueError("SOURCE_OUTSIDE_45S_COLLECTOR_SCOPE")
    counts["all_received"] = len(records)
    return {
        "counts":dict(counts),
        "first_received":first.isoformat(),
        "last_received":prev.isoformat(),
        "duration_observed_seconds":(prev-first).total_seconds(),
        "bid_and_ask_received":True,
        "origin_event_time_is_not_delivery_clock":True,
        "collector_timestamp_is_after_queue_dequeue":True,
        "provider_clock_latency_calibrated":False,
        "real_executable_quoted_costs_verified":False,
    }


def audit(root: Path) -> dict:
    if set(p.name for p in root.iterdir() if p.is_file()) != {
        RAW, MANIFEST, SHA_SOURCE, SHA_COMPLETE, CODE_HEAD,
    }:
        raise ValueError("SOURCE_ARTIFACT_SCOPE_CHANGED")
    first = _ledger(root/SHA_SOURCE,filenames={RAW,MANIFEST})
    final = _ledger(root/SHA_COMPLETE,filenames={RAW,MANIFEST,CODE_HEAD})
    for name in (RAW,MANIFEST):
        if first[name] != final[name]:
            raise ValueError("SOURCE_2_LEDGER_CONTRADICTION")
    for filename,expected in final.items():
        if sha256(root/filename) != expected:
            raise ValueError("SOURCE_ORIGINAL_SHA256_TAMPERED")
    if (root/CODE_HEAD).read_text(encoding="utf-8").strip() != HEAD:
        raise ValueError("SOURCE_ORIGINAL_RECEIVER_HEAD_DRIFT")
    metadata=json.loads((root/MANIFEST).read_text(encoding="utf-8"))
    if (metadata.get("identity") != SOURCE_IDENTITY
            or metadata.get("status") != SUCCESS
            or metadata.get("source_observation_state") != SUCCESS
            or metadata.get("symbol") != "NZDUSD"
            or metadata.get("broker") != "ICMARKETS_CTRADER"
            or metadata.get("account_type") != "DEMO"
            or metadata.get("duration_seconds_fixed") != 45
            or metadata.get("broker_account_or_token_persisted") is not False
            or metadata.get("orders_sent") != 0
            or metadata.get("token_refresh_attempts") != 0
            or metadata.get("both_sides_seen_nonzero") is not True
            or metadata.get("historical_available_at_proven") is not False
            or metadata.get("actual_execution_fill_proven") is not False
            or metadata.get("NET_certified") is not False
            or type(metadata.get("native_provider_symbol_id")) is not int
            or metadata.get("native_provider_symbol_id") <= 0):
        raise ValueError("SOURCE_DEMO_BROKER_SCOPE_OR_BLOCKER_WRONG")
    records=[]
    for line in (root/RAW).read_text(encoding="utf-8").splitlines():
        records.append(json.loads(line))
    summary=qa_events(records)
    if (len(records) != metadata.get("received_events")
            or first[RAW] != metadata.get("original_spot_events_sha256")
            or summary["first_received"] != metadata.get("first_collector_utc")
            or summary["last_received"] != metadata.get("last_collector_utc")
            or summary["counts"]["all_received"] != sum(
                metadata.get("observed_classifications",{}).values()
            )):
        raise ValueError("SOURCE_MANIFEST_RECEIPT_COUNT_OR_CLOCK_DIFFERENT")
    for label, count in metadata["observed_classifications"].items():
        if label not in VALID_CLASS or summary["counts"].get(label,0)!=count:
            raise ValueError("SOURCE_CLASSIFICATION_RECONCILIATION_FAILED")
    return {
        "identity": AUDIT_IDENTITY, "status":STATUS,
        "original_forward_run":38296610948,"original_exact_code_head":HEAD,
        "original_events_sha256":first[RAW],
        "original_manifest_sha256":first[MANIFEST],
        "quote_source": "ICMARKETS_CTRADER_DEMO_NZDUSD",
        "observed_quote_event_quality":summary,
        "native_bidask_values_not_republished":True,
        "source_original_broker_credentials_not_accessed":True,
        "new_quote_downloads":0,"orders":0,
        "source_attestation_is_not_broker_fill":True,
        "source_attestation_is_not_PIT_macro":True,
        "coverage_of_all_33_verified":False,
        "NET_PF_Sharpe_Sortino_DD_computed":False,
        "UTC001_certified":False,
    }


def main() -> None:
    p=argparse.ArgumentParser()
    p.add_argument("original_forward_source",type=Path)
    p.add_argument("out",type=Path)
    args=p.parse_args()
    obj=audit(args.original_forward_source)
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/"alpha2-g2-nzdusd-independent-firstreceipt-QA.json").write_text(
        json.dumps(obj,indent=2,sort_keys=True)+"\n",encoding="utf-8",
    )
    print(json.dumps({
        "status":obj["status"],
        "events":obj["observed_quote_event_quality"]["counts"]["all_received"],
        "classes":obj["observed_quote_event_quality"]["counts"],
        "gross_or_NET_economics":False,
    },sort_keys=True))


if __name__=="__main__":
    main()
