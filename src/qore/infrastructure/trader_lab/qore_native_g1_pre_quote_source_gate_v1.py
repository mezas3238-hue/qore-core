"""QORE Native G1-PRE: strictly fail-closed provenance/causality audit for quote pilots.

Audits ONLY the representation of paired as-of quotes. It does not attest that a
broker sent the bytes, that a join was causally reconstructed from native side
ticks, that the execution account matches G0, or that any strategy is NET viable.
Never wire this module into a trader or production execution.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.qore_native_market33_source_census_v1 import (
    frozen_family_contract,
)
from qore.infrastructure.trader_lab.qore_native_final33_three_m5_g0_v1 import (
    FROZEN_UNIVERSE_33,
)

IDENTITY = "QORE_NATIVE_G1_PRE_ASOF_QUOTE_PILOT_INPUT_V1"
G0_SOURCE_SHA = "1291d5c2efb4e51c2698ea25ad420a01a213dc405b5070c37efbce4131606b85"
SHA_RE = re.compile(r"^[a-f0-9]{64}$")
PRICE_RE = re.compile(r"^(?:0|[1-9]\d*)(?:\.\d+)?$")
UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$")
MAX_ASOF_AGE_SECONDS = Decimal("5")
MAX_PILOT_ROWS = 100_000


def _sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or not SHA_RE.fullmatch(value):
        raise ValueError(f"{label}: missing SHA256 witness")
    return value


def _utc(value: Any, label: str) -> datetime:
    if not isinstance(value, str) or not UTC_RE.fullmatch(value):
        raise ValueError(f"{label}: require explicit ISO8601 UTC Z timestamp")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError as exc:
        raise ValueError(f"{label}: invalid timestamp") from exc


def _price(value: Any, label: str) -> Decimal:
    if not isinstance(value, str) or not PRICE_RE.fullmatch(value):
        raise ValueError(f"{label}: decimal string required")
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"{label}: invalid decimal") from exc
    if not parsed.is_finite() or parsed <= 0:
        raise ValueError(f"{label}: positive finite decimal required")
    return parsed


def audit(manifest: dict[str, Any], raw_quotes_jsonl: bytes) -> dict[str, Any]:
    frozen_family_contract()
    if (
        manifest.get("identity") != IDENTITY
        or manifest.get("g0_source_sha256") != G0_SOURCE_SHA
        or manifest.get("provider") != "CTRADER_OPEN_API"
        or manifest.get("environment") != "DEMO"
        or manifest.get("source_kind") != "NATIVE_SIDE_TICKS_PAIRED_ASOF"
        or manifest.get("timestamp_timezone") != "UTC"
        or manifest.get("historical_NET_economics_claimed") is not False
        or manifest.get("production_enabled") is not False
        or manifest.get("capture_mode") not in {"HISTORICAL_BACKFILL", "FORWARD_PAPER_CAPTURE"}
    ):
        raise ValueError("G1-PRE pilot source/provenance contract not satisfied")
    for field in ("broker_name", "broker_server"):
        if not isinstance(manifest.get(field), str) or not manifest[field].strip():
            raise ValueError(f"{field}: explicit broker identity claim required")
    _sha(manifest.get("account_fingerprint_sha256"), "account fingerprint")
    if not isinstance(raw_quotes_jsonl, bytes):
        raise ValueError("quotes must be exact source bytes")
    if hashlib.sha256(raw_quotes_jsonl).hexdigest() != _sha(
        manifest.get("quotes_jsonl_sha256"), "quote content"
    ):
        raise ValueError("quote source bytes do not match manifest SHA256")
    contracts = manifest.get("instruments")
    if not isinstance(contracts, list) or not 1 <= len(contracts) <= 33:
        raise ValueError("pilot must declare 1..33 contracts explicitly")
    book: dict[str, dict[str, Any]] = {}
    for contract in contracts:
        if not isinstance(contract, dict):
            raise ValueError("invalid instrument contract")
        symbol = contract.get("canonical_symbol")
        if symbol not in FROZEN_UNIVERSE_33 or symbol in book:
            raise ValueError("instrument not in frozen 33 or duplicated")
        if not isinstance(contract.get("provider_symbol"), str) or not contract["provider_symbol"]:
            raise ValueError("provider symbol required; no implicit aliases")
        if isinstance(contract.get("provider_symbol_id"), bool) or not isinstance(
            contract.get("provider_symbol_id"), int
        ) or contract["provider_symbol_id"] <= 0:
            raise ValueError("positive provider symbol ID required")
        _sha(contract.get("broker_contract_document_sha256"), "contract document")
        size = _price(contract.get("tick_size"), "tick size")
        book[symbol] = {"contract": contract, "tick": size}
    # Source claims are unverified even if manifest has a contract document digest.
    counts: dict[str, dict[str, Any]] = {
        sym: {"total": 0, "valid_format": 0, "zero_spread_quarantined": 0,
              "crossed_quarantined": 0, "stale_asof_quarantined": 0}
        for sym in book
    }
    last_seq: dict[str, int] = {}
    last_time: dict[str, datetime] = {}
    seen = 0
    try:
        body = raw_quotes_jsonl.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("quote file must be UTF-8 JSONL") from exc
    for line in body.splitlines():
        if not line.strip():
            raise ValueError("blank JSONL record is invalid")
        seen += 1
        if seen > MAX_PILOT_ROWS:
            raise ValueError("pilot cap exceeded; split into separately hashed shards")
        try:
            rec = json.loads(line)
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid JSONL quote") from exc
        if not isinstance(rec, dict):
            raise ValueError("quote record must be an object")
        sym = rec.get("canonical_symbol")
        if sym not in book:
            raise ValueError("quote absent from declared frozen symbol/contract list")
        contract = book[sym]["contract"]
        if (
            rec.get("provider_symbol") != contract["provider_symbol"]
            or rec.get("provider_symbol_id") != contract["provider_symbol_id"]
        ):
            raise ValueError("provider symbol ID/alias mismatch against manifest")
        seq = rec.get("source_sequence")
        if isinstance(seq, bool) or not isinstance(seq, int) or seq < 0:
            raise ValueError("source sequence must be nonnegative integer")
        if sym in last_seq and seq <= last_seq[sym]:
            raise ValueError("repeated/out-of-order source sequence")
        now = _utc(rec.get("decision_time_utc"), "decision")
        bid_time = _utc(rec.get("bid_market_time_utc"), "bid market")
        ask_time = _utc(rec.get("ask_market_time_utc"), "ask market")
        if sym in last_time and now < last_time[sym]:
            raise ValueError("out-of-order decision clock")
        if bid_time > now or ask_time > now:
            raise ValueError("future quote used in as-of decision (lookahead)")
        observed = rec.get("both_sides_received_at_utc")
        if manifest["capture_mode"] == "FORWARD_PAPER_CAPTURE":
            when = _utc(observed, "forward receive")
            if when < max(bid_time, ask_time) or when > now:
                raise ValueError("forward quote receipt causality violated")
        elif observed is not None:
            raise ValueError("backfill has no historical decision-time receipt witness")
        bid, ask = _price(rec.get("bid"), "bid"), _price(rec.get("ask"), "ask")
        tick = book[sym]["tick"]
        if bid % tick or ask % tick:
            raise ValueError("bid/ask inconsistent with declared contract tick size")
        age_bid = Decimal(str((now - bid_time).total_seconds()))
        age_ask = Decimal(str((now - ask_time).total_seconds()))
        row = counts[sym]
        row["total"] += 1
        if ask < bid:
            row["crossed_quarantined"] += 1
        elif ask == bid:
            row["zero_spread_quarantined"] += 1
        elif max(age_bid, age_ask) > MAX_ASOF_AGE_SECONDS:
            row["stale_asof_quarantined"] += 1
        else:
            row["valid_format"] += 1
        last_seq[sym], last_time[sym] = seq, now
    if seen == 0:
        raise ValueError("empty quote pilot is not evidence")
    valid = sum(c["valid_format"] for c in counts.values())
    return {
        "identity": "QORE_NATIVE_G1_PRE_QUOTE_SOURCE_FORMAT_AUDIT_V1",
        "status": "SOURCE_FORMAT_TRIAGED_EXTERNAL_ATTESTATION_PENDING",
        "source_g0_sha256": G0_SOURCE_SHA,
        "quotes_input_sha256": hashlib.sha256(raw_quotes_jsonl).hexdigest(),
        "capture_mode": manifest["capture_mode"],
        "pilot_market_count": len(book),
        "frozen_market_count": 33,
        "total_quote_rows": seen,
        "asof_format_valid_rows_not_fills": valid,
        "per_symbol": counts,
        "unseen_markets": sorted(FROZEN_UNIVERSE_33 - set(book)),
        "index_alias_homologation_external_pending": sorted(
            set(book).intersection({"NAS100", "SP500"})
        ),
        "source_native_tick_origin_independently_verified": False,
        "broker_account_contract_equivalence_with_G0_verified": False,
        "native_bid_ask_join_independently_reproduced": False,
        "historical_price_entry_exit_coverage_verified": False,
        "commission_slippage_swap_news_PIT_verified": False,
        "historical_NET_authorized": False,
        "paper_order_submission_authorized": False,
        "live_order_submission_authorized": False,
        "certified_traders": 0,
        "operational_next_step": "REVIEW_NATIVE_SIDE_TICKS_AND_BROKER_CONTRACT_BEFORE_NET",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest_json", type=Path)
    parser.add_argument("quotes_jsonl", type=Path)
    parser.add_argument("output_json", type=Path)
    args = parser.parse_args()
    result = audit(
        json.loads(args.manifest_json.read_text(encoding="utf-8")),
        args.quotes_jsonl.read_bytes(),
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": result["status"],
        "markets": result["pilot_market_count"],
        "quotes": result["total_quote_rows"],
        "format_valid_not_fills": result["asof_format_valid_rows_not_fills"],
        "historical_NET_authorized": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
