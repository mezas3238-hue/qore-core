"""G0 source-only extension 29→30: IC Markets CHFJPY original M5 with 11 RAW SHAs.

No OHLC returns, fills or trading. Preserve parent sources as immutable manifest.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import qore_native_cohort23_m5_source_union_v1 as base
from qore.infrastructure.trader_lab import qore_native_cohort29_cadjpy_cadchf_m5_g0_v1 as parent29

IDENTITY = "QORE_NATIVE_30_MARKET_CHFJPY_ORIGINAL_M5_G0_V1"
NEW_SYMBOL = "CHFJPY"
PARENT_29_CODE_SHA = "c550e2f12195a018494a1c580c371dca21941a99"
PARENT_29_JSON_SHA = "8ec07974e2276ab35f871064e03a6a0dedc87b987289b21cdcc737d599c447cb"
PARENT_29_RUN = 38205083910
PARENT_BARS = 21396360
EXPECTED_PARENT_SYMBOLS = parent29.EXPECTED_27 | set(parent29.NEW_TWO)


def original_chfjpy_audit(root: Path) -> dict[str, Any]:
    result = base.audit_new_symbol(NEW_SYMBOL, root, allowed_symbols=(NEW_SYMBOL,))
    if (
        result.get("status") != "G0_NEW_PROVIDER_M5_SHA_PASS"
        or result.get("source_integrity_checked") is not True
        or result.get("ohlc_prices_returns_or_pnl_analyzed") is not False
        or result.get("g1_net_authorized") is not False
        or result.get("capture_run") != base.NEW_SOURCE_RUN
        or result.get("capture_head_sha") != base.NEW_SOURCE_SHA
        or result.get("m5_bars", 0) <= 0
        or len(result.get("years", [])) != 11
    ):
        raise ValueError("CHFJPY source witness not admissible")
    return result


def parent_29_source(path: Path) -> dict[str, Any]:
    file = "qore-native-unified-29-m5.json"
    hashes = base._hash_scope(path / "OUTPUT_SHA256SUMS.txt", {file, "code-head-sha.txt"})
    original = base.g0.verified_file(path, hashes, file)
    head = base.g0.verified_file(path, hashes, "code-head-sha.txt")
    digest = base._hash_scope(path / (file + ".sha256"), {file})
    if (digest[file] != PARENT_29_JSON_SHA or hashes[file] != PARENT_29_JSON_SHA
            or head.read_text(encoding="utf-8").strip() != PARENT_29_CODE_SHA):
        raise ValueError("parent 29 original signed hash or code HEAD drift")
    j = json.loads(original.read_text(encoding="utf-8"))
    markets = j.get("markets")
    if (
        j.get("identity") != parent29.IDENTITY
        or j.get("status") != "G0_29_OF_29_M5_SOURCE_SHA_PASS_NO_ECONOMICS"
        or j.get("source_count") != 29
        or j.get("combined_m5_bars") != PARENT_BARS
        or j.get("traders_certified") != 0
        or j.get("ohlc_outcomes_not_examined") is not True
        or j.get("net_economics_authorized") is not False
        or j.get("production_untouched") is not True
        or not isinstance(markets, list)
        or len(markets) != 29
        or {x["symbol"] for x in markets} != EXPECTED_PARENT_SYMBOLS
        or sum(x["m5_bars"] for x in markets) != PARENT_BARS
    ):
        raise ValueError("29 parent roster source identity/flags/counts drift")
    return j


def combine(parent: Path, new: Path) -> dict[str, Any]:
    data = parent_29_source(parent)
    name = "qore-native-added-CHFJPY-30.json"
    sha = base._hash_scope(new / (name + ".sha256"), {name})
    original = base.g0.verified_file(new, sha, name)
    child = json.loads(original.read_text(encoding="utf-8"))
    if (
        child.get("symbol") != NEW_SYMBOL
        or child.get("status") != "G0_NEW_PROVIDER_M5_SHA_PASS"
        or child.get("source_integrity_checked") is not True
        or child.get("ohlc_prices_returns_or_pnl_analyzed") is not False
        or child.get("g1_net_authorized") is not False
        or child.get("capture_run") != base.NEW_SOURCE_RUN
        or child.get("capture_head_sha") != base.NEW_SOURCE_SHA
        or len(child.get("years", [])) != 11
        or child.get("m5_bars", 0) <= 0
    ):
        raise ValueError("CHFJPY audit SHA witness invalid")
    if NEW_SYMBOL in EXPECTED_PARENT_SYMBOLS:
        raise ValueError("CHFJPY duplicate in parent 29")
    row = {
        "symbol": NEW_SYMBOL,
        "source_cohort": "ICMARKETS_CTRADER_DEMO_18_OF_21",
        "provider_symbol": child["provider_symbol"],
        "provider_symbol_id": child["provider_symbol_id"],
        "m5_bars": child["m5_bars"],
        "first_utc": child["first_utc"], "last_utc": child["last_utc"],
        "original_source_run": child["capture_run"],
        "original_source_code_sha": child["capture_head_sha"],
        "source_manifest_sha256": child["manifest_sha256"],
        "raw_sha256_by_year": {
            str(x["year"]): x["raw_sha256"] for x in child["years"]
        },
    }
    records = sorted([*data["markets"], row], key=lambda v:v["symbol"])
    if len(records) != 30 or len({r["symbol"] for r in records}) != 30:
        raise ValueError("30 markets not unique")
    return {
        "identity": IDENTITY,
        "status": "G0_30_OF_30_M5_SOURCE_SHA_VERIFIED_NO_ECONOMICS",
        "market_count": 30,
        "parent_29_manifest_sha256": PARENT_29_JSON_SHA,
        "parent_29_bars": PARENT_BARS,
        "added_chfjpy_m5": child["m5_bars"],
        "total_original_m5_bars": sum(v["m5_bars"] for v in records),
        "market_roster": records,
        "last_three_pending_original_sha": ["NZDJPY", "NZDCAD", "NZDCHF"],
        "broker_identity_12_vs_18_identical_not_proven": True,
        "prices_not_joined_or_reconstructed": True,
        "ohlc_outcomes_not_read": True,
        "bidask_historical_verified": False,
        "net_certification_authorized": False,
        "no_news_pit_calendar_certified": False,
        "traders_certified": 0,
        "production_untouched": True,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="mode", required=True)
    a = sub.add_parser("audit")
    a.add_argument("original", type=Path)
    a.add_argument("destination", type=Path)
    b = sub.add_parser("combine")
    b.add_argument("previous29", type=Path)
    b.add_argument("new_audit", type=Path)
    b.add_argument("destination", type=Path)
    x = ap.parse_args()
    if x.mode == "audit":
        result = original_chfjpy_audit(x.original)
        final = x.destination / "qore-native-added-CHFJPY-30.json"
    else:
        result = combine(x.previous29, x.new_audit)
        final = x.destination / "qore-native-unified-30-m5.json"
    final.parent.mkdir(parents=True, exist_ok=True)
    final.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    final.with_name(final.name + ".sha256").write_text(
        base.g0.sha256(final) + f"  {final.name}\n", encoding="utf-8"
    )
    print(json.dumps({
        "status": result["status"], "symbol": result.get("symbol"),
        "market_count": result.get("market_count"),
        "m5": result.get("m5_bars", result.get("total_original_m5_bars")),
        "profit_examined": False, "orders_placed": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
