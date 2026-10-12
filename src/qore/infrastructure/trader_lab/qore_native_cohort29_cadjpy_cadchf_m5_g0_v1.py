"""QORE Native G0: add CADJPY and CADCHF to frozen 27-source M5 universe.

Source SHA and chronology only. Never access OHLC prices, outcomes, PnL,
broker executions or VPS. The combined manifest is an index, not concatenated
bars from different brokers/transport identities.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import qore_native_cohort23_m5_source_union_v1 as source
from qore.infrastructure.trader_lab import qore_native_cohort27_audnzd_g0_v1 as p27

IDENTITY = "QORE_NATIVE_29_27_PLUS_CADJPY_CADCHF_M5_G0_V1"
FROZEN_PARENT_IDENTITY = p27.IDENTITY
FROZEN_PARENT_MANIFEST_SHA = "499219430212dd50ffcefe681e6372ac3d66a54c420d03c3924d1ec2dc9680d0"
FROZEN_PARENT_CODE_SHA = "56b07172bdded93f9fafadedf614c770a2a2dc40"
FROZEN_PARENT_RUN = 38204152494
FROZEN_PARENT_BARS = 19905871
NEW_TWO = ("CADJPY", "CADCHF")
EXPECTED_27 = set(source.ALL) | {"GBPNZD", "AUDCAD", "AUDCHF", "AUDNZD"}


def audit_new(symbol: str, root: Path) -> dict[str, Any]:
    """SHA-check original source annual RAW and QUALITY without reading OHLC."""
    if symbol not in NEW_TWO or symbol in EXPECTED_27:
        raise ValueError("unexpected/overlapping extra market")
    result = source.audit_new_symbol(symbol, root, allowed_symbols=NEW_TWO)
    if (
        result["status"] != "G0_NEW_PROVIDER_M5_SHA_PASS"
        or result.get("source_integrity_checked") is not True
        or result.get("g1_net_authorized") is not False
        or result.get("ohlc_prices_returns_or_pnl_analyzed") is not False
        or result.get("capture_run") != source.NEW_SOURCE_RUN
        or result.get("capture_head_sha") != source.NEW_SOURCE_SHA
        or len(result.get("years", [])) != 11
    ):
        raise ValueError("new source G0 audit evidence not sufficient")
    return result


def verify_parent(original_27_artifact: Path) -> dict[str, Any]:
    """Re-open the frozen verified 27 manifest, exact digest and code SHA."""
    name = "qore-native-cohort27-unified.json"
    files = source._hash_scope(
        original_27_artifact / "OUTPUT_SHA256SUMS.txt",
        {name, "code-head-sha.txt"},
    )
    parent_path = source.g0.verified_file(original_27_artifact, files, name)
    head_path = source.g0.verified_file(original_27_artifact, files, "code-head-sha.txt")
    if (
        source.g0.sha256(parent_path) != FROZEN_PARENT_MANIFEST_SHA
        or head_path.read_text(encoding="utf-8").strip() != FROZEN_PARENT_CODE_SHA
    ):
        raise ValueError("parent 27 digest or executed code SHA drift")
    sidecar = source._hash_scope(
        original_27_artifact / (name + ".sha256"), {name},
    )
    if sidecar[name] != FROZEN_PARENT_MANIFEST_SHA:
        raise ValueError("parent 27 sidecar SHA mismatch")
    data = json.loads(parent_path.read_text(encoding="utf-8"))
    entries = data.get("markets")
    if (
        data.get("identity") != FROZEN_PARENT_IDENTITY
        or data.get("status") != "G0_27_OF_27_M5_SHA_VERIFIED_NO_ECONOMICS"
        or data.get("market_count") != 27
        or data.get("total_m5_bars") != FROZEN_PARENT_BARS
        or data.get("economic_net_authorized") is not False
        or data.get("ohlc_or_pnl_not_examined") is not True
        or data.get("production_untouched") is not True
        or data.get("traders_certified") != 0
        or not isinstance(entries, list)
        or len(entries) != 27
        or {row["symbol"] for row in entries} != EXPECTED_27
        or sum(row["m5_bars"] for row in entries) != FROZEN_PARENT_BARS
    ):
        raise ValueError("parent 27 source cohort flags, counts or roster drift")
    return data


def combine(parent: Path, audits_root: Path) -> dict[str, Any]:
    previous = verify_parent(parent)
    paths = sorted(audits_root.rglob("native-29-added-*.json"))
    if len(paths) != 2:
        raise ValueError("exactly two independent new SHA-audit JSON witnesses required")
    added = []
    for path in paths:
        original_name = path.name
        signed = source._hash_scope(
            path.with_name(original_name + ".sha256"), {original_name}
        )
        source.g0.verified_file(path.parent, signed, original_name)
        data = json.loads(path.read_text(encoding="utf-8"))
        if (
            data.get("status") != "G0_NEW_PROVIDER_M5_SHA_PASS"
            or data.get("source_integrity_checked") is not True
            or data.get("ohlc_prices_returns_or_pnl_analyzed") is not False
            or data.get("g1_net_authorized") is not False
            or data.get("capture_run") != source.NEW_SOURCE_RUN
            or data.get("capture_head_sha") != source.NEW_SOURCE_SHA
            or len(data.get("years", [])) != 11
            or data.get("m5_bars", 0) <= 0
        ):
            raise ValueError("new symbol witness not SHA-validated")
        added.append({
            "symbol": data["symbol"],
            "source_cohort": "NEW_M5_ICMARKETS_DEMO_NEXT_TWO",
            "provider_symbol": data["provider_symbol"],
            "provider_symbol_id": data["provider_symbol_id"],
            "m5_bars": data["m5_bars"],
            "first_utc": data["first_utc"],
            "last_utc": data["last_utc"],
            "original_run": data["capture_run"],
            "original_code_sha": data["capture_head_sha"],
            "manifest_sha256": data["manifest_sha256"],
            "original_raw_sha256_by_year": {
                str(y["year"]): y["raw_sha256"] for y in data["years"]
            },
        })
    if {row["symbol"] for row in added} != set(NEW_TWO):
        raise ValueError("new cohort not exact CADJPY/CADCHF")
    all_rows = sorted([*previous["markets"], *added], key=lambda r: r["symbol"])
    if (
        len(all_rows) != 29
        or len({x["symbol"] for x in all_rows}) != 29
        or sum(x["m5_bars"] for x in previous["markets"]) != FROZEN_PARENT_BARS
    ):
        raise ValueError("29-market union dedup or parent-count mismatch")
    return {
        "identity": IDENTITY,
        "status": "G0_29_OF_29_M5_SOURCE_SHA_PASS_NO_ECONOMICS",
        "source_count": 29,
        "parent_27_manifest_sha256": FROZEN_PARENT_MANIFEST_SHA,
        "parent_27_code_sha": FROZEN_PARENT_CODE_SHA,
        "parent_27_original_bars": FROZEN_PARENT_BARS,
        "additional_two_bars": sum(x["m5_bars"] for x in added),
        "combined_m5_bars": sum(x["m5_bars"] for x in all_rows),
        "source_original_capture_run": source.NEW_SOURCE_RUN,
        "markets": all_rows,
        "source_broker_boundaries_preserved": True,
        "cross_source_prices_not_concatenated": True,
        "ohlc_outcomes_not_examined": True,
        "historical_bid_ask_verified": False,
        "net_economics_authorized": False,
        "h4_broker_candles_certified": False,
        "traders_certified": 0,
        "production_untouched": True,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="mode", required=True)
    first = sub.add_parser("audit")
    first.add_argument("symbol", choices=NEW_TWO)
    first.add_argument("original_source", type=Path)
    first.add_argument("destination", type=Path)
    last = sub.add_parser("combine")
    last.add_argument("original_parent_27", type=Path)
    last.add_argument("new_sha_witnesses", type=Path)
    last.add_argument("destination", type=Path)
    args = ap.parse_args()
    if args.mode == "audit":
        record = audit_new(args.symbol, args.original_source)
        final = args.destination / f"native-29-added-{args.symbol}.json"
    else:
        record = combine(args.original_parent_27, args.new_sha_witnesses)
        final = args.destination / "qore-native-unified-29-m5.json"
    final.parent.mkdir(parents=True, exist_ok=True)
    final.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    final.with_name(final.name + ".sha256").write_text(
        source.g0.sha256(final) + f"  {final.name}\n", encoding="utf-8"
    )
    print(json.dumps({
        "status": record["status"],
        "symbol": record.get("symbol"),
        "source_count": record.get("source_count"),
        "bars": record.get("m5_bars", record.get("combined_m5_bars")),
        "market_returns_not_examined": True,
        "trading_enabled": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
