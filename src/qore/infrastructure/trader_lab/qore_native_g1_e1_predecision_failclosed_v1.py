"""QORE Native G1: fail-closed bridge from E1 research clocks to causal evidence.

Input is ONLY the already published source-only JSONL.gz from G1 audit.py.
No gross outcomes, signals, prices, account details, fills, or economics are read.
No path in this module can authorize orders or net backtests.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

E1_SHA = "dfe78f115957a40f4188c30e78bd7f88c2ce6c42"
EMBARGO = datetime(2024, 9, 17, tzinfo=UTC)
LOWER = datetime(2016, 9, 17, tzinfo=UTC)
METHODS = {
    "REVERSAL_12H": 240, "POST_OPEN_CONT": 120, "PERSISTENCE_12H": 240,
    "OPEN_INITIAL_REACTION": 15, "SWEEP_RECLAIM": 120,
    "TREND_MULTI_DAY": 240, "RANGE_BREAK_CONT": 120,
}
MARKETS = frozenset((
    "NAS100", "SP500", "US30", "XAUUSD", "XAGUSD",
    "AUDUSD", "EURUSD", "GBPUSD", "NZDUSD", "USDCAD", "USDCHF", "USDJPY",
    "AUDJPY", "AUDCAD", "AUDCHF", "AUDNZD", "CADCHF", "CADJPY", "CHFJPY",
    "EURAUD", "EURCAD", "EURCHF", "EURGBP", "EURJPY", "EURNZD",
    "GBPAUD", "GBPCAD", "GBPCHF", "GBPJPY", "GBPNZD",
    "NZDCAD", "NZDCHF", "NZDJPY",
))
SOURCE_COLUMNS = frozenset((
    "opportunity_sha256", "method_id", "symbol", "entry_research_utc",
    "theoretical_M5_target_close_utc", "duration_minutes",
    "broker_provenance", "news_asof_filtered", "real_broker_fill",
    "outcome_exported",
))
BLOCK_REASON = "E1_RESEARCH_CLOCK_NOT_A_CAUSAL_TRADE_DECISION"
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def unique_keys(pairs):
    value = {}
    for k, v in pairs:
        if k in value:
            raise ValueError("DUPLICATE_JSON_KEY")
        value[k] = v
    return value


def utc(value: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError("CLOCK_NOT_A_STRING")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("CLOCK_INVALID_ISO") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise ValueError("CLOCK_NOT_EXPLICIT_UTC")
    return parsed.astimezone(UTC)


def read_research_event(record: dict) -> tuple[datetime, datetime]:
    if type(record) is not dict or set(record) != SOURCE_COLUMNS:
        raise ValueError("RESEARCH_SOURCE_SCHEMA_DRIFT_OR_OUTCOME_LEAK")
    symbol = record["symbol"]
    method = record["method_id"]
    if symbol not in MARKETS or method not in METHODS:
        raise ValueError("FROZEN_RESEARCH_UNIVERSE_DRIFT")
    if (type(record["duration_minutes"]) is not int
            or record["duration_minutes"] != METHODS[method]):
        raise ValueError("FROZEN_HORIZON_DRIFT")
    if any(record[key] is not False for key in (
            "news_asof_filtered", "real_broker_fill", "outcome_exported")):
        raise ValueError("RESEARCH_NO_EXECUTION_CONTRACT_DRIFT")
    expected_cohort = ("ORIGINAL12_G0_CONTRACT_UNHOMOLOGATED"
                       if symbol in {"AUDJPY", "AUDUSD", "EURUSD", "GBPJPY",
                                     "GBPUSD", "USDCAD", "USDJPY", "NAS100",
                                     "SP500", "US30", "XAUUSD", "XAGUSD"}
                       else "NEW21_ICMARKETS_G0_CONTRACT_NOT_G1_PROVEN")
    if record["broker_provenance"] != expected_cohort:
        raise ValueError("SOURCE_PROVENANCE_OR_CONTRACT_DRIFT")
    start = utc(record["entry_research_utc"])
    target = utc(record["theoretical_M5_target_close_utc"])
    if not (LOWER <= start < EMBARGO and start < target <= EMBARGO):
        raise ValueError("DATE_OUTSIDE_EXPOSED_DEV_DIAG_OR_EMBARGO")
    if target != start + timedelta(minutes=METHODS[method]):
        raise ValueError("THEORETICAL_CLOSE_DRIFT")
    expected = digest(f"{E1_SHA}|{method}|{symbol}|{start.isoformat()}".encode())
    if record["opportunity_sha256"] != expected:
        raise ValueError("E1_OPPORTUNITY_IDENTITY_DRIFT")
    return start, target


def assess_predecision_shape(record: dict, witness: dict | None) -> dict:
    """Check a *synthetic/unsigned* witness shape; never assert authenticity.

    No synthetic attestation, however structurally valid, can become a fill or
    certified edge. An independent witness-byte SHA verifier is still missing.
    """
    start, _ = read_research_event(record)
    if witness is None:
        return {"status": "NO_PREDECISION_WITNESS", "reason": BLOCK_REASON,
                "causal_structure_pass": False, "witness_verified": False,
                "order_authorized": False, "historical_NET_authorized": False}
    required = {
        "opportunity_sha256", "symbol", "method_id", "closed_bar_available_at_utc",
        "all_features_observed_at_utc", "decision_emitted_at_utc",
        "entry_order_eligible_at_utc", "order_expiration_at_utc",
        "independent_witness_sha256", "signal_side",
    }
    if type(witness) is not dict or set(witness) != required:
        raise ValueError("WITNESS_SCHEMA_MISSING_OR_UNEXPECTED")
    if (witness["opportunity_sha256"] != record["opportunity_sha256"]
            or witness["symbol"] != record["symbol"]
            or witness["method_id"] != record["method_id"]):
        raise ValueError("WITNESS_EVENT_PROVENANCE_MISMATCH")
    if witness["signal_side"] not in ("LONG", "SHORT"):
        raise ValueError("WITNESS_SIDE_INVALID")
    if not isinstance(witness["independent_witness_sha256"], str) or not HEX64.fullmatch(
            witness["independent_witness_sha256"]):
        raise ValueError("WITNESS_DIGEST_INVALID")
    close, feature, decision, eligible, expiry = (
        utc(witness[k]) for k in (
            "closed_bar_available_at_utc", "all_features_observed_at_utc",
            "decision_emitted_at_utc", "entry_order_eligible_at_utc",
            "order_expiration_at_utc",
        )
    )
    if (close > decision or feature > decision or decision > eligible
            or eligible >= expiry or not LOWER <= close
            or expiry > EMBARGO):
        raise ValueError("WITNESS_CAUSAL_CLOCK_OR_EMBARGO_VIOLATION")
    # The E1 reference clock is not an entry-order time; do not require equal
    # clocks or overwrite the research clock with a reconstructed trade.
    return {
        "status": "STRUCTURE_ONLY_PASS_AUTHENTICITY_AND_ECONOMICS_BLOCKED",
        "research_clock_utc": start.isoformat(),
        "causal_structure_pass": True, "witness_verified": False,
        "source_quotes_verified": False, "contract_verified": False,
        "orders_or_fills_measured": False, "order_authorized": False,
        "historical_NET_authorized": False,
    }


def audit_legacy_clock_ledger(source: Path, destination: Path,
                              expected_rows: int = 373611) -> dict:
    """Full 33x7 old-E1 audit; emits strictly BLOCKED clock-only rows.

    Requires an independently SHA-verified upstream archive ledger. The input
    checksum here is for reproducibility, not independent source authentication.
    """
    if type(expected_rows) is not int or expected_rows <= 0:
        raise ValueError("EXPECTED_COUNT_MUST_BE_POSITIVE")
    destination.mkdir(parents=True, exist_ok=True)
    output = destination / "E1_PREDECISION_REJECTED_CLOCKS_ONLY.jsonl.gz"
    tmp = destination / ".E1_PREDECISION_REJECTED_CLOCKS_ONLY.tmp.gz"
    seen_ids = set()
    seen_symbols = set()
    seen_cells = set()
    count = 0
    sha_input = hashlib.sha256()
    try:
        with gzip.open(source, "rb") as reader, tmp.open("wb") as raw:
            with gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as zipped:
                for line in reader:
                    sha_input.update(line)
                    record = json.loads(line, object_pairs_hook=unique_keys)
                    read_research_event(record)
                    identity = record["opportunity_sha256"]
                    if identity in seen_ids:
                        raise ValueError("DUPLICATE_RESEARCH_OPPORTUNITY")
                    seen_ids.add(identity)
                    seen_symbols.add(record["symbol"])
                    seen_cells.add((record["symbol"], record["method_id"]))
                    result = {
                        "opportunity_sha256": identity,
                        "symbol": record["symbol"], "method_id": record["method_id"],
                        "research_entry_clock_utc": record["entry_research_utc"],
                        "theoretical_m5_close_utc": record["theoretical_M5_target_close_utc"],
                        "predecision_evidence": "MISSING",
                        "rejection_reason": BLOCK_REASON,
                        "entry_order_eligible_at_utc": None,
                        "exit_decision_time_utc": None,
                        "broker_fill": False, "orders_authorized": False,
                        "NET_authorized": False,
                    }
                    zipped.write((json.dumps(result, sort_keys=True,
                                             separators=(",", ":")) + "\n").encode())
                    count += 1
        if count != expected_rows or (expected_rows == 373611 and (
                seen_symbols != MARKETS or len(seen_cells) != 231)):
            raise ValueError("SIGNED_E1_EXPECTED_UNIVERSE_OR_COUNT_DRIFT")
        tmp.replace(output)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
    summary = {
        "identity": "QORE_NATIVE_E1_PREDECISION_FAIL_CLOSED_V1",
        "source_kind": "PREVIOUSLY_EXPOSED_SIGNED_E1_RESEARCH_CLOCKS_ONLY",
        "research_opportunities_checked": count,
        "distinct_markets": len(seen_symbols),
        "distinct_market_method_cells": len(seen_cells),
        "predecision_witnesses_verified": 0,
        "research_clocks_rejected_as_orders": count,
        "executable_trades_proven": 0,
        "raw_legacy_lines_sha256": sha_input.hexdigest(),
        "blocked_ledger_gzip_sha256": digest(output.read_bytes()),
        "historical_NET_authorized": False, "certified_traders": 0,
        "holdout_from_2024_09_17_not_read": True,
        "source_authentication": "REQUIRES_UPSTREAM_SIGNED_E1_ARCHIVE_CHECK",
        "required_next": ["#837", "#857", "#856", "#863"],
    }
    (destination / "E1_PREDECISION_FAIL_CLOSED_SUMMARY.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_only_research_clock_jsonl_gz", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--expected-rows", type=int, default=373611)
    args = parser.parse_args()
    result = audit_legacy_clock_ledger(
        args.source_only_research_clock_jsonl_gz, args.output_dir,
        expected_rows=args.expected_rows)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
