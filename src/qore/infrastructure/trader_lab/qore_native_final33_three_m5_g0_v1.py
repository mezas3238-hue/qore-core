"""QORE Native final 33 M5 source gate (30 frozen + 3 unverified original archives).

Research-only. This module cannot admit 33 until all NZDJPY/NZDCAD/NZDCHF
original provider RAW+QUALITY SHA, annual counts and identities pass. No OHLC
outcomes, no claims of net tradability or same broker account among cohorts.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import qore_native_cohort23_m5_source_union_v1 as g0
from qore.infrastructure.trader_lab import qore_native_cohort30_chfjpy_m5_g0_v1 as p30

IDENTITY = "QORE_NATIVE_33_SOURCE_M5_IMMUTABLE_G0_V1"
SOURCE_TAIL = ("NZDJPY", "NZDCAD", "NZDCHF")
PARENT_30_CODE_SHA = "7c41bc4d0b135efb0885c17bafe9869342a5c377"
PARENT_30_JSON_SHA = "96b6709022905215d582abdc20edb452c7766dd42fd945e76144de8a29d29283"
PARENT_30_RUN = 38205741712
PARENT_30_M5_BARS = 22141699
EXPECTED_PARENT_30 = p30.EXPECTED_PARENT_SYMBOLS | {p30.NEW_SYMBOL}
SOURCE_CAP_RUN = g0.NEW_SOURCE_RUN
SOURCE_CAP_SHA = g0.NEW_SOURCE_SHA
FROZEN_UNIVERSE_33 = EXPECTED_PARENT_30 | set(SOURCE_TAIL)


def roster_contract() -> None:
    if (
        len(EXPECTED_PARENT_30) != 30
        or len(SOURCE_TAIL) != 3
        or len(FROZEN_UNIVERSE_33) != 33
        or set(SOURCE_TAIL) & EXPECTED_PARENT_30
    ):
        raise ValueError("owner frozen universe exactly 33 non-overlapping symbols violated")


def audit_tail(symbol: str, path: Path) -> dict[str, Any]:
    roster_contract()
    if symbol not in SOURCE_TAIL:
        raise ValueError("market outside frozen last-three research source roster")
    d = g0.audit_new_symbol(symbol, path, allowed_symbols=SOURCE_TAIL)
    if (
        d.get("symbol") != symbol
        or d.get("status") != "G0_NEW_PROVIDER_M5_SHA_PASS"
        or d.get("source_integrity_checked") is not True
        or d.get("ohlc_prices_returns_or_pnl_analyzed") is not False
        or d.get("g1_net_authorized") is not False
        or d.get("capture_run") != SOURCE_CAP_RUN
        or d.get("capture_head_sha") != SOURCE_CAP_SHA
        or len(d.get("years", [])) != 11
        or d.get("m5_bars", 0) <= 0
    ):
        raise ValueError("unverified final original source")
    return d


def verified_parent30(original: Path) -> dict[str, Any]:
    name = "qore-native-unified-30-m5.json"
    hashes = g0._hash_scope(
        original / "OUTPUT_SHA256SUMS.txt", {name, "code-head-sha.txt"}
    )
    p = g0.g0.verified_file(original, hashes, name)
    head = g0.g0.verified_file(original, hashes, "code-head-sha.txt")
    sides = g0._hash_scope(original / (name + ".sha256"), {name})
    if (
        hashes[name] != PARENT_30_JSON_SHA
        or sides[name] != PARENT_30_JSON_SHA
        or head.read_text(encoding="utf-8").strip() != PARENT_30_CODE_SHA
    ):
        raise ValueError("parent 30 SHA manifest or code drift")
    d = json.loads(p.read_text(encoding="utf-8"))
    markets = d.get("market_roster")
    if (
        d.get("identity") != p30.IDENTITY
        or d.get("status") != "G0_30_OF_30_M5_SOURCE_SHA_VERIFIED_NO_ECONOMICS"
        or d.get("market_count") != 30
        or d.get("total_original_m5_bars") != PARENT_30_M5_BARS
        or d.get("traders_certified") != 0
        or d.get("net_certification_authorized") is not False
        or d.get("ohlc_outcomes_not_read") is not True
        or d.get("production_untouched") is not True
        or not isinstance(markets, list)
        or len(markets) != 30
        or {row["symbol"] for row in markets} != EXPECTED_PARENT_30
        or sum(row["m5_bars"] for row in markets) != PARENT_30_M5_BARS
    ):
        raise ValueError("parent G0 30 roster/flags/counts not original")
    return d


def build33(parent: Path, signed_three: Path) -> dict[str, Any]:
    roster_contract()
    p = verified_parent30(parent)
    witnesses = sorted(signed_three.rglob("qore-native-tail33-new-*.json"))
    if len(witnesses) != 3:
        raise ValueError("three distinct final SHA verified years witnesses required")
    extra = []
    for path in witnesses:
        digest = g0._hash_scope(path.with_name(path.name + ".sha256"), {path.name})
        g0.g0.verified_file(path.parent, digest, path.name)
        data = json.loads(path.read_text(encoding="utf-8"))
        if (
            data.get("status") != "G0_NEW_PROVIDER_M5_SHA_PASS"
            or data.get("source_integrity_checked") is not True
            or data.get("ohlc_prices_returns_or_pnl_analyzed") is not False
            or data.get("g1_net_authorized") is not False
            or data.get("capture_run") != SOURCE_CAP_RUN
            or data.get("capture_head_sha") != SOURCE_CAP_SHA
            or len(data.get("years", [])) != 11
            or data.get("m5_bars", 0) <= 0
        ):
            raise ValueError("final new M5 archive or SHA evidence not validated")
        extra.append({
            "symbol": data["symbol"],
            "source_cohort": "FINAL3_ICMARKETS_CTRADER_DEMO",
            "provider_symbol": data["provider_symbol"],
            "provider_symbol_id": data["provider_symbol_id"],
            "m5_bars": data["m5_bars"],
            "first_utc": data["first_utc"],
            "last_utc": data["last_utc"],
            "original_source_run": data["capture_run"],
            "original_source_code_sha": data["capture_head_sha"],
            "source_manifest_sha256": data["manifest_sha256"],
            "raw_sha256_by_year": {
                str(a["year"]): a["raw_sha256"] for a in data["years"]
            },
            "quality_sha256_by_year": {
                str(a["year"]): a["quality_sha256"] for a in data["years"]
            },
        })
    if {row["symbol"] for row in extra} != set(SOURCE_TAIL):
        raise ValueError("wrong final three market source witnesses")
    markets = sorted([*p["market_roster"], *extra], key=lambda x:x["symbol"])
    if len(markets) != 33 or {x["symbol"] for x in markets} != FROZEN_UNIVERSE_33:
        raise ValueError("owner 33 universe incomplete or overlapping")
    return {
        "identity": IDENTITY,
        "status": "G0_33_OF_33_PROVIDER_M5_SHA_VERIFIED_NO_ECONOMICS",
        "market_count": 33,
        "parent30_bars": PARENT_30_M5_BARS,
        "parent30_manifest_sha256": PARENT_30_JSON_SHA,
        "parent30_producer_head_sha": PARENT_30_CODE_SHA,
        "added_tail_three_bars": sum(r["m5_bars"] for r in extra),
        "all_33_original_m5_bars": sum(r["m5_bars"] for r in markets),
        "market_roster": markets,
        "original12_vs_new21_same_ICMarkets_account_verified": False,
        "broker_session_H4_D1_reconstruction_certified": False,
        "historical_bidask_spread_verified": False,
        "news_macro_asof_exclusion_verified": False,
        "net_execution_economics_authorized": False,
        "market_outcomes_unexamined": True,
        "all_original_M5_sources_retained_as_individual_artifacts": True,
        "traders_certified": 0,
        "production_untouched": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    subs = parser.add_subparsers(dest="mode", required=True)
    p = subs.add_parser("audit")
    p.add_argument("symbol", choices=SOURCE_TAIL)
    p.add_argument("original_source", type=Path)
    p.add_argument("output", type=Path)
    q = subs.add_parser("combine")
    q.add_argument("parent30_artifact", type=Path)
    q.add_argument("three_original_sha_witnesses", type=Path)
    q.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.mode == "audit":
        result = audit_tail(args.symbol, args.original_source)
        dest = args.output / f"qore-native-tail33-new-{args.symbol}.json"
    else:
        result = build33(args.parent30_artifact, args.three_original_sha_witnesses)
        dest = args.output / "qore-native-complete33-source-m5.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    dest.with_name(dest.name + ".sha256").write_text(
        g0.g0.sha256(dest) + f"  {dest.name}\n", encoding="utf-8"
    )
    print(json.dumps({
        "status": result["status"],
        "symbol": result.get("symbol"),
        "markets": result.get("market_count"),
        "m5_bars": result.get("m5_bars", result.get("all_33_original_m5_bars")),
        "OHLC_or_PNL_not_read": True,
        "no_LIVE": True,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
