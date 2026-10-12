"""QORE Native G0 additive source audit: immutable cohort23 + next three M5.

No trading, no OHLC economics, no copy/splice of prices, no PnL.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import qore_native_cohort23_m5_source_union_v1 as first

IDENTITY = "QORE_NATIVE_COHORT26_23_PLUS_3_M5_SOURCE_G0_V1"
MORE = ("GBPNZD", "AUDCAD", "AUDCHF")
EXACT_PARENT_SHA = "cb9a21f77131b07db2da964ba123bd8c282ded23"
EXPECTED_PARENT_COUNT = 16924567
EXPECTED_PARENT_MANIFEST_SHA256 = "ca467b1d952420440b38d4e600606e43896e14230ac8438c7ceb4225a478770c"


def audit_additional(symbol: str, source: Path) -> dict[str, Any]:
    if symbol not in MORE or symbol in first.ALL:
        raise ValueError("new source outside 3 frozen additional markets")
    data = first.audit_new_symbol(symbol, source, allowed_symbols=MORE)
    if (data.get("status") != "G0_NEW_PROVIDER_M5_SHA_PASS"
            or data.get("g1_net_authorized") is not False
            or data.get("capture_run") != first.NEW_SOURCE_RUN):
        raise ValueError("extra M5 source integrity not certified")
    data["cohort_extension"] = IDENTITY
    return data


def read_verified_parent(source: Path) -> dict[str, Any]:
    expected_files = {
        "qore-native-cohort23-unified-manifest.json", "code-head-sha.txt"
    }
    witness = first._hash_scope(source / "OUTPUT_SHA256SUMS.txt", expected_files)
    parent_name = "qore-native-cohort23-unified-manifest.json"
    manifest = first.g0.verified_file(source, witness, parent_name)
    head = first.g0.verified_file(source, witness, "code-head-sha.txt")
    if (witness[parent_name] != EXPECTED_PARENT_MANIFEST_SHA256
            or head.read_text(encoding="utf-8").strip() != EXACT_PARENT_SHA):
        raise ValueError("frozen 23-manifest/witness SHA drift")
    sidecar = first._hash_scope(
        source / (parent_name + ".sha256"), {parent_name}
    )
    if sidecar[parent_name] != EXPECTED_PARENT_MANIFEST_SHA256:
        raise ValueError("parent 23 sidecar digest drift")
    data = json.loads(manifest.read_text(encoding="utf-8"))
    parents = data.get("markets")
    if (data.get("identity") != first.IDENTITY
            or data.get("status") != first.FINAL_STATUS
            or data.get("cohort_count") != 23
            or data.get("new_sha_verified_count") != 11
            or data.get("original_count") != 12
            or data.get("combined_m5_bars") != EXPECTED_PARENT_COUNT
            or data.get("g1_net_authorized") is not False
            or data.get("production_untouched") is not True
            or data.get("cross_broker_raw_prices_not_concatenated") is not True
            or not isinstance(parents, list) or len(parents) != 23
            or {row["symbol"] for row in parents} != set(first.ALL)
            or sum(x["m5_bars"] for x in parents) != EXPECTED_PARENT_COUNT):
        raise ValueError("parent 23 provenance or total incorrect")
    return data


def combine(parent: Path, extra: Path) -> dict[str, Any]:
    a = read_verified_parent(parent)
    paths = list(extra.rglob("qore-native-cohort26-new-*.json"))
    if len(paths) != 3:
        raise ValueError("expected exactly three new annual SHA verified witnesses")
    rows = []
    for path in paths:
        sidecar = first._hash_scope(path.with_name(path.name + ".sha256"), {path.name})
        first.g0.verified_file(path.parent, sidecar, path.name)
        data = json.loads(path.read_text(encoding="utf-8"))
        if (data.get("status") != "G0_NEW_PROVIDER_M5_SHA_PASS"
                or data.get("cohort_extension") != IDENTITY
                or data.get("ohlc_prices_returns_or_pnl_analyzed") is not False
                or data.get("source_integrity_checked") is not True
                or data.get("g1_net_authorized") is not False
                or data.get("capture_run") != first.NEW_SOURCE_RUN
                or data.get("capture_head_sha") != first.NEW_SOURCE_SHA
                or len(data.get("years", [])) != 11
                or data.get("m5_bars", 0) <= 0):
            raise ValueError("new additional symbol witness invalid")
        rows.append({
            "symbol": data["symbol"],
            "provider_symbol": data["provider_symbol"],
            "source_cohort": "ADDED3_ICMARKETS_CTRADER_DEMO",
            "provider_symbol_id": data["provider_symbol_id"],
            "original_source_run": data["capture_run"],
            "original_source_head_sha": data["capture_head_sha"],
            "source_manifest_sha256": data["manifest_sha256"],
            "m5_bars": data["m5_bars"],
            "first_utc": data["first_utc"],
            "last_utc": data["last_utc"],
            "raw_sha256_by_year": {str(x["year"]): x["raw_sha256"] for x in data["years"]},
        })
    if {x["symbol"] for x in rows} != set(MORE):
        raise ValueError("additional 3 source names collide or missing")
    together = sorted([*a["markets"], *rows], key=lambda x: x["symbol"])
    if len(together) != 26 or len({x["symbol"] for x in together}) != 26:
        raise ValueError("not exactly 26 nonoverlapping markets")
    return {
        "identity": IDENTITY,
        "status": "G0_26_OF_26_SOURCE_SHA_PASS_NO_ECONOMICS",
        "parent_23_head_sha": EXACT_PARENT_SHA,
        "parent_23_manifest_sha256": EXPECTED_PARENT_MANIFEST_SHA256,
        "parent_23_original_m5_bars": EXPECTED_PARENT_COUNT,
        "extension_3_m5_bars": sum(x["m5_bars"] for x in rows),
        "total_26_m5_bars": sum(x["m5_bars"] for x in together),
        "market_count": len(together),
        "new_three_count": 3,
        "markets": together,
        "source_provenance_separated": True,
        "prices_not_stitched": True,
        "no_bidask_historical": True,
        "gross_research_only_if_preregistered": True,
        "g1_net_authorized": False,
        "no_market_outcomes_opened": True,
        "traders_certified": 0,
        "production_untouched": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="mode", required=True)
    verify = commands.add_parser("verify")
    verify.add_argument("symbol", choices=MORE)
    verify.add_argument("source", type=Path)
    verify.add_argument("output", type=Path)
    merge = commands.add_parser("combine")
    merge.add_argument("previous23", type=Path)
    merge.add_argument("three", type=Path)
    merge.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.mode == "verify":
        data = audit_additional(args.symbol, args.source)
        path = args.output / f"qore-native-cohort26-new-{args.symbol}.json"
    else:
        data = combine(args.previous23, args.three)
        path = args.output / "qore-native-cohort26-unified.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    path.with_name(path.name + ".sha256").write_text(
        first.g0.sha256(path) + f"  {path.name}\n", encoding="utf-8"
    )
    print(json.dumps({
        "status": data["status"],
        "symbol": data.get("symbol"),
        "bars": data.get("m5_bars", data.get("total_26_m5_bars")),
        "market_count": data.get("market_count"),
        "no_economics": True, "no_live": True,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
