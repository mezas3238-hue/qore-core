"""Historical ORIGINAL E1 research opportunity clocks vs genuine G1 native quote windows.

Not an execution replay. The signed original E1 archives include gross outcomes,
but this bridge DOES NOT ACCESS or EXPORT any future-return field or E1 sign.
Research decisions and theoretical bar-horizon closes are not actual fills.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab import (
    qore_native_g1_causal_quote_checkpoint_pair_gate_v1 as quote_gate,
    qore_native_g1_proto_wire_second_decoder_qa_v1 as proto,
)

IDENTITY = "QORE_NATIVE_G1_ORIGINAL_E1_EVENT_CLOCK_SOURCE_COVERAGE_V1"
E1_SOURCE_RUN = 38257207836
E1_CODE_SHA = "dfe78f115957a40f4188c30e78bd7f88c2ce6c42"
E1_PREREG = "67022daf7e2c3335eda991fd217df83fc1a34bc4"
G0_SOURCE_SHA = "1291d5c2efb4e51c2698ea25ad420a01a213dc405b5070c37efbce4131606b85"
E1_IDENTITY = "QORE_NATIVE_33X7_E1_FROZEN_GROSS_ONLY_V1"
E1_STATUS = "E1_SEVEN_METHOD_GROSS_ONLY_PREVIOUSLY_EXPOSED_PERIODS"
SOURCE_RUN = 38288411671
SOURCE_ARTIFACT = 11764163362
HISTORICAL_EMBARGO = datetime(2024, 9, 17, tzinfo=UTC)
START = datetime(2016, 9, 17, tzinfo=UTC)
TARGETS = ("EURUSD", "GBPUSD", "USDJPY", "XAGUSD", "SP500")
SAMPLE_DATES = frozenset({"2021-03-16", "2023-03-21"})
ARTIFACTS = {
    "EURUSD": (11750423859, "7778ff7b91375dbb2795b892aa8e7a11d69c08a11cd9c19269c67c8c0a044b42"),
    "GBPUSD": (11749804668, "b714aa0f47ba00ddb017e4e9e1865a9f4df46c3da477328b140cef8606fd06a8"),
    "USDJPY": (11750653329, "53197e51d9b6c19f463e5a2487ab58d3bf454c0b63a6c372a6f381eb0446a0a9"),
    "XAGUSD": (11750733271, "9ccad45b0ca2fca7e8483b420bf4f340fab3476af93e85986b6449d4ad262ed8"),
    "SP500": (11750917832, "c1a31a57a4385ad1609346e1d7e7ab8c460f5639004df1966bc53e2e2f419bef"),
}
METHODS = {
    "REVERSAL_12H": 240,
    "POST_OPEN_CONT": 120,
    "PERSISTENCE_12H": 240,
    "OPEN_INITIAL_REACTION": 15,
    "SWEEP_RECLAIM": 120,
    "TREND_MULTI_DAY": 240,
    "RANGE_BREAK_CONT": 120,
}
NO_PNL_EXPORTED = True


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _expected_research_clock(canonical: str, method: str, day: date) -> datetime:
    """Independent frozen E1 target-start clock reconstruction, including DST."""
    if canonical not in TARGETS or method not in METHODS:
        raise ValueError("E1_CLOCK_UNREGISTERED_METHOD_OR_SYMBOL")
    if method in ("REVERSAL_12H", "PERSISTENCE_12H", "TREND_MULTI_DAY"):
        return datetime(day.year, day.month, day.day, 16, tzinfo=UTC)
    if method in ("SWEEP_RECLAIM", "RANGE_BREAK_CONT"):
        return datetime(day.year, day.month, day.day, 13, tzinfo=UTC)
    if canonical == "SP500":
        tz, hour, minute = "America/New_York", 9, 30
    elif canonical == "XAGUSD":
        tz, hour, minute = "America/New_York", 8, 0
    else:
        tz, hour, minute = "Europe/London", 8, 0
    ref = datetime(day.year, day.month, day.day, hour, minute, tzinfo=ZoneInfo(tz))
    delta = 15 if method == "OPEN_INITIAL_REACTION" else 30
    return (ref + timedelta(minutes=delta)).astimezone(UTC)


def _verify_signed_e1(folder: Path, symbol: str) -> tuple[list[dict[str, Any]], str]:
    """Read all EVENT clocks; future gross values in file are never accessed."""
    if symbol not in TARGETS or not folder.is_dir():
        raise ValueError("E1_SOURCE_SYMBOL_OR_FOLDER_MISSING")
    name = f"qore-native-e1-seven-{symbol}.json"
    path = folder / name
    sha_path = folder / (name + ".sha256")
    head_path = folder / "exact-code-head-sha.txt"
    if {p.name for p in folder.iterdir() if p.is_file()} != {name, name+".sha256", head_path.name}:
        raise ValueError("E1_SOURCE_ARTIFACT_FILE_SET_INVALID")
    registered = sha_path.read_text(encoding="utf-8").splitlines()
    if len(registered) != 1 or registered[0] != sha(path.read_bytes())+"  "+name:
        raise ValueError("E1_ORIGINAL_JSON_SHA_MISMATCH")
    if head_path.read_text(encoding="utf-8").strip() != E1_CODE_SHA:
        raise ValueError("E1_CODE_HEAD_NOT_FROZEN")
    doc = json.loads(path.read_bytes())
    if (doc.get("identity") != E1_IDENTITY
            or doc.get("status") != E1_STATUS
            or doc.get("source33_sha") != G0_SOURCE_SHA
            or doc.get("frozen_prereg_commit") != E1_PREREG
            or doc.get("original_symbol") != symbol
            or doc.get("future_ohlc_not_read") is not True
            or doc.get("net_certified") is not False
            or doc.get("traders_certified") != 0
            or doc.get("production_untouched") is not True
            or doc.get("source_audit", {}).get("original_raw_11_year_sha_checked") is not True):
        raise ValueError("E1_G0_OR_PREREG_OR_PRODUCTION_STATE_DRIFT")
    sections = doc.get("seven_methods")
    if (not isinstance(sections, list) or len(sections) != 7
            or {x.get("method_id") for x in sections} != set(METHODS)):
        raise ValueError("E1_SEVEN_METHOD_ROSTER_INVALID")
    selected: list[dict[str, Any]] = []
    for block in sections:
        method = block["method_id"]
        if (block.get("cell_id") != f"{method}__{symbol}"
                or block.get("net_economics_authorized") is not False
                or block.get("bidask_measured") is not False
                or block.get("news_asof_filtered") is not False):
            raise ValueError("E1_HISTORIC_NO_NET_NO_NEWS_CONTRACT_CHANGED")
        previous_dates: set[str] = set()
        events = block.get("paired_events")
        if not isinstance(events, list):
            raise ValueError("E1_HISTORIC_EVENT_LIST_INVALID")
        for row in events:
            original_date = row.get("utc_date")
            if not isinstance(original_date, str) or original_date in previous_dates:
                raise ValueError("E1_DUPLICATE_OR_INVALID_RESEARCH_DATE")
            parsed_date = date.fromisoformat(original_date)
            week = parsed_date.isocalendar()
            if (row.get("iso_week") != f"{week.year}-W{week.week:02d}"
                    or row.get("method_id") != method
                    or row.get("broker_executable_fill") is not False
                    or row.get("macro_news_asof_filtered") is not False
                    or row.get("strategy_signal") not in (-1, 1)
                    or row.get("baseline_signal") not in (-1, 1)):
                raise ValueError("E1_RESEARCH_DECISION_PROVENANCE_INVALID")
            clock = datetime.fromisoformat(row["reference_entry_utc"])
            if (clock.tzinfo is None or clock.utcoffset() is None
                    or not START <= clock.astimezone(UTC) < HISTORICAL_EMBARGO
                    or clock.astimezone(UTC).date() != parsed_date
                    or clock.astimezone(UTC) != _expected_research_clock(symbol, method, parsed_date)):
                raise ValueError("E1_RESEARCH_CLOCK_LOOKAHEAD_OR_DST_DRIFT")
            previous_dates.add(original_date)
            if original_date in SAMPLE_DATES:
                start = clock.astimezone(UTC)
                # Frozen E1 target M5 count, NOT broker exit execution.
                theoretical_close = start + timedelta(minutes=METHODS[method])
                event_id = sha(f"{E1_CODE_SHA}|{method}|{symbol}|{start.isoformat()}".encode())
                selected.append({
                    "opportunity_sha256": event_id,
                    "canonical_symbol": symbol,
                    "method_id": method,
                    "research_entry_clock_utc": start.isoformat(),
                    "theoretical_m5_target_close_clock_utc": theoretical_close.isoformat(),
                    "theoretical_target_minutes": METHODS[method],
                    "source_g0_account_vs_G1_broker_contract_homologated": False,
                    "broker_order_open_close_proven": False,
                    "future_outcome_fields_exported": False,
                })
    return selected, sha(path.read_bytes())


def _source_quote_windows(root: Path, parent: dict) -> dict[tuple[str, str], tuple[list[tuple[int, int]], list[tuple[int, int]]]]:
    """Protobuf original was already SHA independently audited by parent."""
    if parent["source_markets"] != 5 or parent["source_windows_per_market"] != 2:
        raise ValueError("G1_PARENT_SOURCE_5X2_REQUIRED")
    result = {}
    for symbol in TARGETS:
        market_dir = root / symbol
        row = json.loads((market_dir / "SOURCE_MARKET_MANIFEST_NOT_NET.json").read_bytes())
        for window_no, frozen in enumerate(proto.WINDOWS, 1):
            w = row["windows"][window_no-1]
            first = int(datetime.fromisoformat(frozen[0]).timestamp()*1000)
            stop = int(datetime.fromisoformat(frozen[1]).timestamp()*1000)
            b = proto.verify_side(market_dir,symbol,window_no,"BID",w["by_side"]["BID"],first,stop)
            a = proto.verify_side(market_dir,symbol,window_no,"ASK",w["by_side"]["ASK"],first,stop)
            result[(symbol,frozen[0][:10])] = b,a
    return result


def evaluate(original_e1_root: Path, original_proto: Path) -> dict[str, Any]:
    verified_source = proto.audit(original_proto)
    if (verified_source.get("status")
            != "SOURCE_WIRE_INDEPENDENT_CUMULATIVE_DELTA_PARITY_PASS_NO_NET"
            or verified_source.get("NET_authorized") is not False):
        raise ValueError("G1_PROTO_SECOND_DECODER_SOURCE_QA_BLOCKED")
    quotes = _source_quote_windows(original_proto, verified_source)
    outcomes = []
    provenance = {}
    for symbol in TARGETS:
        originals, evidence_sha = _verify_signed_e1(original_e1_root / symbol, symbol)
        provenance[symbol] = {
            "original_E1_artifact_id": ARTIFACTS[symbol][0],
            "github_artifact_original_zip_sha256_expected": ARTIFACTS[symbol][1],
            "E1_original_json_sha256_verified": evidence_sha,
        }
        for event in originals:
            at = datetime.fromisoformat(event["research_entry_clock_utc"]).astimezone(UTC)
            exit_at = datetime.fromisoformat(event["theoretical_m5_target_close_clock_utc"]).astimezone(UTC)
            key = (symbol,at.date().isoformat())
            if key not in quotes:
                raise ValueError("G1_EXACT_SOURCE_WINDOW_DATE_MISSING")
            window_start = datetime(at.year,at.month,at.day,13,tzinfo=UTC)
            window_end = window_start + timedelta(minutes=30)
            entry_in = window_start <= at < window_end
            exit_in = window_start <= exit_at < window_end
            b, a = quotes[key]
            entry_quality = (quote_gate.decision_quality(int(at.timestamp()*1000),b,a)
                             if entry_in else "ENTRY_OUTSIDE_SOURCE_WINDOW")
            exit_quality = (quote_gate.decision_quality(int(exit_at.timestamp()*1000),b,a)
                            if exit_in else "EXIT_OUTSIDE_SOURCE_WINDOW")
            both = entry_quality == exit_quality == "OK_POSITIVE_BIDASK"
            outcomes.append({
                **event,
                "current_market_provider_symbol": proto.TARGETS[symbol],
                "sample_entry_clock_in_quote_window": entry_in,
                "theoretical_close_clock_in_quote_window": exit_in,
                "entry_quote_source_state": entry_quality,
                "theoretical_close_quote_source_state": exit_quality,
                "both_quotes_available_source_only_not_NET": both,
            })
    outcomes.sort(key=lambda x:(x["research_entry_clock_utc"],x["canonical_symbol"],x["method_id"]))
    if len(outcomes) != len({x["opportunity_sha256"] for x in outcomes}):
        raise ValueError("E1_DUPLICATE_OPPORTUNITY_IDENTITY")
    if not outcomes:
        raise ValueError("E1_ORIGINAL_SOURCE_NO_RESEARCH_EVENTS_SELECTED")
    counters = Counter()
    per_symbol = {}
    per_method = {}
    for row in outcomes:
        counters["real_e1_research_events"] += 1
        counters["entry_in_source_quote_window"] += int(row["sample_entry_clock_in_quote_window"])
        counters["theoretical_close_in_source_quote_window"] += int(row["theoretical_close_clock_in_quote_window"])
        counters["both_clocks_inside_source_window"] += int(row["sample_entry_clock_in_quote_window"] and row["theoretical_close_clock_in_quote_window"])
        counters["both_quotes_ok_not_NET"] += int(row["both_quotes_available_source_only_not_NET"])
        counters["entry_state_"+row["entry_quote_source_state"]] += 1
        counters["exit_state_"+row["theoretical_close_quote_source_state"]] += 1
        per_symbol[row["canonical_symbol"]] = per_symbol.get(row["canonical_symbol"], 0)+1
        per_method[row["method_id"]] = per_method.get(row["method_id"],0)+1
    return {
        "identity": IDENTITY,
        "status": "ORIGINAL_E1_HISTORICAL_RESEARCH_CLOCKS_VS_G1_SOURCE_GAPS_AUDITED_NO_NET",
        "source_G0_sha": G0_SOURCE_SHA, "original_E1_code_sha": E1_CODE_SHA,
        "original_E1_source_run": E1_SOURCE_RUN,
        "original_proto_source_run": SOURCE_RUN,
        "original_proto_source_artifact": SOURCE_ARTIFACT,
        "original_E1_sha_provenance": provenance,
        "source_field_protobuf_independently_redecoded": True,
        "original_research_outcomes_prior_exposed_no_virgin_holdout": True,
        "signed_E1_strategy_gross_bps_never_accessed_or_exported": True,
        "research_opportunities_not_broker_executions": True,
        "theoretical_M5_target_close_not_real_exit_execution": True,
        "source_G0_vs_G1_contracts_not_homologated": True,
        "market_cohort": list(TARGETS),
        "historical_source_quote_windows_utc": [list(w) for w in proto.WINDOWS],
        "source_gate_side_age_maximum_ms": quote_gate.AGE_LIMIT_MS,
        "counts": dict(sorted(counters.items())),
        "per_symbol": dict(sorted(per_symbol.items())),
        "per_method": dict(sorted(per_method.items())),
        "historical_NET_authorized": False, "certified_traders": 0,
        "event_source_clocks_only": outcomes,
    }


def main() -> None:
    cli = argparse.ArgumentParser()
    cli.add_argument("signed_original_e1_dir", type=Path)
    cli.add_argument("original_proto_quotes_dir", type=Path)
    cli.add_argument("output", type=Path)
    args = cli.parse_args()
    report = evaluate(args.signed_original_e1_dir,args.original_proto_quotes_dir)
    args.output.mkdir(parents=True,exist_ok=True)
    path = args.output / "G1_ORIGINAL_E1_OPPORTUNITY_CLOCK_SOURCE_GAPS_NOT_NET.json"
    path.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    (args.output/"SHA256SUMS.txt").write_text(sha(path.read_bytes())+"  "+path.name+"\n")
    print(json.dumps({
        "status":report["status"], "counts":report["counts"],
        "per_symbol":report["per_symbol"],
        "historical_NET_authorized":False,"certified_traders":0,
    },sort_keys=True))


if __name__ == "__main__":
    main()
