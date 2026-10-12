"""Single non-economic source expansion: 26 verified markets + AUDNZD M5.

The 27 market union is a manifest only. All original raw ledgers stay immutable.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import qore_native_cohort23_m5_source_union_v1 as base

IDENTITY = "QORE_NATIVE_COHORT27_WITH_AUDNZD_G0_SOURCE_V1"
ADDED = ("AUDNZD",)
SOURCE_PARENT26_SHA = "da2b33c7be9e4bd56f561acd725b6777e68aa6ef9deee00b20c7a38cfb9ef862"
PARENT26_CODE_SHA = "2391063da42abdb733783ea9fb1781314419a946"
PARENT26_COUNT = 19160586


def new_source(source: Path) -> dict[str, Any]:
    a = base.audit_new_symbol("AUDNZD", source, allowed_symbols=ADDED)
    if a.get("g1_net_authorized") is not False:
        raise ValueError("no net authorization")
    return a


def old26(parent: Path) -> dict[str, Any]:
    name = "qore-native-cohort26-unified.json"
    ledger = base._hash_scope(parent / "OUTPUT_SHA256SUMS.txt", {name, "code-head-sha.txt"})
    if ledger[name] != SOURCE_PARENT26_SHA:
        raise ValueError("frozen parent26 SHA does not match")
    base.g0.verified_file(parent, ledger, name)
    code = base.g0.verified_file(parent, ledger, "code-head-sha.txt")
    if code.read_text(encoding="utf-8").strip() != PARENT26_CODE_SHA:
        raise ValueError("parent26 exact code HEAD mismatch")
    sidecar = base._hash_scope(parent / (name + ".sha256"), {name})
    if sidecar[name] != SOURCE_PARENT26_SHA:
        raise ValueError("parent26 sidecar SHA discrepancy")
    a = json.loads((parent / name).read_text(encoding="utf-8"))
    if (a.get("identity") != "QORE_NATIVE_COHORT26_23_PLUS_3_M5_SOURCE_G0_V1"
            or a.get("status") != "G0_26_OF_26_SOURCE_SHA_PASS_NO_ECONOMICS"
            or a.get("market_count") != 26
            or a.get("total_26_m5_bars") != PARENT26_COUNT
            or a.get("g1_net_authorized") is not False
            or a.get("production_untouched") is not True
            or len(a.get("markets", [])) != 26
            or len({r["symbol"] for r in a["markets"]}) != 26
            or sum(r["m5_bars"] for r in a["markets"]) != PARENT26_COUNT):
        raise ValueError("parent26 G0 exact content invalid")
    return a


def combine(parent: Path, additional: Path) -> dict[str, Any]:
    p = old26(parent)
    name = "qore-native-cohort27-new-AUDNZD.json"
    witness = base._hash_scope(additional / (name + ".sha256"), {name})
    base.g0.verified_file(additional, witness, name)
    new = json.loads((additional / name).read_text(encoding="utf-8"))
    if (new.get("status") != "G0_NEW_PROVIDER_M5_SHA_PASS"
            or new.get("symbol") != "AUDNZD"
            or new.get("capture_run") != base.NEW_SOURCE_RUN
            or new.get("capture_head_sha") != base.NEW_SOURCE_SHA
            or new.get("source_integrity_checked") is not True
            or new.get("ohlc_prices_returns_or_pnl_analyzed") is not False
            or new.get("g1_net_authorized") is not False
            or len(new.get("years", [])) != 11
            or new.get("m5_bars", 0) <= 0):
        raise ValueError("AUDNZD new M5 source witness not validated")
    if "AUDNZD" in {x["symbol"] for x in p["markets"]}:
        raise ValueError("double-counted AUDNZD")
    row = {
        "symbol": "AUDNZD", "provider_symbol": "AUDNZD",
        "provider_symbol_id": new["provider_symbol_id"],
        "source_cohort": "ADDED1_ICMARKETS_CTRADER_DEMO",
        "original_source_run": new["capture_run"],
        "original_source_head_sha": new["capture_head_sha"],
        "m5_bars": new["m5_bars"],
        "first_utc": new["first_utc"], "last_utc": new["last_utc"],
        "source_manifest_sha256": new["manifest_sha256"],
        "raw_sha256_by_year": {str(x["year"]): x["raw_sha256"] for x in new["years"]},
    }
    rows = sorted([*p["markets"], row], key=lambda x:x["symbol"])
    if len(rows) != 27 or len({x["symbol"] for x in rows}) != 27:
        raise ValueError("must be 27 unique symbols")
    return {
        "identity": IDENTITY,
        "status": "G0_27_OF_27_M5_SHA_VERIFIED_NO_ECONOMICS",
        "parent_26_sha256": SOURCE_PARENT26_SHA,
        "parent_26_count": PARENT26_COUNT,
        "added_audnzd_bars": new["m5_bars"],
        "total_m5_bars": sum(x["m5_bars"] for x in rows),
        "market_count": 27, "markets": rows,
        "source_broker_boundaries_preserved": True,
        "ohlc_or_pnl_not_examined": True,
        "historical_bidask_available": False,
        "economic_net_authorized": False,
        "traders_certified": 0,
        "production_untouched": True,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    commands = p.add_subparsers(dest="action", required=True)
    a = commands.add_parser("audit")
    a.add_argument("original", type=Path)
    a.add_argument("output", type=Path)
    b = commands.add_parser("combine")
    b.add_argument("parent", type=Path)
    b.add_argument("additional", type=Path)
    b.add_argument("output", type=Path)
    x = p.parse_args()
    if x.action == "audit":
        data = new_source(x.original)
        target = x.output / "qore-native-cohort27-new-AUDNZD.json"
    else:
        data = combine(x.parent, x.additional)
        target = x.output / "qore-native-cohort27-unified.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    target.with_name(target.name + ".sha256").write_text(
        base.g0.sha256(target) + f"  {target.name}\n", encoding="utf-8"
    )
    print(json.dumps({
        "status": data["status"],
        "nmarkets": data.get("market_count"),
        "bars": data.get("m5_bars", data.get("total_m5_bars")),
        "no_pnl": True,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
