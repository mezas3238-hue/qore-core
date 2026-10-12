"""Frozen 33-market economic-research inventory from signed G0 metadata ONLY.

No OHLC, outcomes or invented brokerage cost, market-hour assumptions. Market
families are an exhaustive 33-symbol prior classification, not a PnL ranking.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import qore_native_cohort23_m5_source_union_v1 as source
from qore.infrastructure.trader_lab import qore_native_final33_three_m5_g0_v1 as final33

IDENTITY = "QORE_NATIVE_FULL_33_FROZEN_MARKET_CENSUS_G0_ONLY_V1"
INDICES = frozenset(("NAS100", "SP500", "US30"))
METALS = frozenset(("XAUUSD", "XAGUSD"))
FX_MAJORS = frozenset(("AUDUSD", "EURUSD", "GBPUSD", "NZDUSD", "USDCAD", "USDCHF", "USDJPY"))
FX_CROSSES = frozenset((
    "AUDJPY", "AUDCAD", "AUDCHF", "AUDNZD", "CADCHF", "CADJPY",
    "CHFJPY", "EURAUD", "EURCAD", "EURCHF", "EURGBP", "EURJPY", "EURNZD",
    "GBPAUD", "GBPCAD", "GBPCHF", "GBPJPY", "GBPNZD",
    "NZDCAD", "NZDCHF", "NZDJPY",
))
FAMILIES = {
    "equity_indices": INDICES,
    "metals": METALS,
    "fx_majors": FX_MAJORS,
    "fx_crosses": FX_CROSSES,
}
KNOWN_SOURCE_COHORTS = {
    "EXISTING12_CTRADER_DEMO_ORIGINAL",
    "NEW11_ICMARKETS_CTRADER_DEMO",
    "ADDED3_ICMARKETS_CTRADER_DEMO",
    "ADDED1_ICMARKETS_CTRADER_DEMO",
    "NEW_M5_ICMARKETS_DEMO_NEXT_TWO",
    "ICMARKETS_CTRADER_DEMO_18_OF_21",
    "FINAL3_ICMARKETS_CTRADER_DEMO",
}
ORIGINAL_COHORT = "EXISTING12_CTRADER_DEMO_ORIGINAL"
YEAR_LABELS = {str(y) for y in range(2016, 2027)}


def frozen_family_contract() -> None:
    joined = [s for values in FAMILIES.values() for s in values]
    if (
        len(joined) != 33 or len(set(joined)) != 33
        or set(joined) != final33.FROZEN_UNIVERSE_33
        or tuple(map(len, (INDICES, METALS, FX_MAJORS, FX_CROSSES))) != (3, 2, 7, 21)
    ):
        raise ValueError("33-market classification incomplete/overlapping/unfrozen")


def census(manifest: dict[str, Any]) -> dict[str, Any]:
    frozen_family_contract()
    if (
        manifest.get("identity") != final33.IDENTITY
        or manifest.get("status") != "G0_33_OF_33_PROVIDER_M5_SHA_VERIFIED_NO_ECONOMICS"
        or manifest.get("market_count") != 33
        or manifest.get("parent30_bars") != final33.PARENT_30_M5_BARS
        or manifest.get("parent30_manifest_sha256") != final33.PARENT_30_JSON_SHA
        or manifest.get("parent30_producer_head_sha") != final33.PARENT_30_CODE_SHA
        or manifest.get("market_outcomes_unexamined") is not True
        or manifest.get("historical_bidask_spread_verified") is not False
        or manifest.get("net_execution_economics_authorized") is not False
        or manifest.get("production_untouched") is not True
        or manifest.get("traders_certified") != 0
        or manifest.get("original12_vs_new21_same_ICMarkets_account_verified") is not False
    ):
        raise ValueError("33 G0 source manifest not attested or economic claims drift")
    records = manifest.get("market_roster")
    if (
        not isinstance(records, list) or len(records) != 33
        or len({s.get("symbol") for s in records}) != 33
        or {s["symbol"] for s in records} != final33.FROZEN_UNIVERSE_33
    ):
        raise ValueError("input is not unique frozen 33 universe")
    family_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    origin_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    all_rows: list[dict[str, Any]] = []
    for row in sorted(records, key=lambda r: r["symbol"]):
        sym = row["symbol"]
        grp = next(f for f, symbols in FAMILIES.items() if sym in symbols)
        origin = row.get("source_cohort")
        if origin not in KNOWN_SOURCE_COHORTS:
            raise ValueError("33 source lost broker provenance")
        n = row.get("m5_bars")
        if type(n) is not int or n <= 0:
            raise ValueError("M5 row count missing/invalid")
        is_original = origin == ORIGINAL_COHORT
        if is_original != (sym in source.EXISTING):
            raise ValueError("original 12 vs new 21 source origin drift")
        if not is_original:
            raw = row.get("raw_sha256_by_year")
            if raw is None:
                raw = row.get("original_raw_sha256_by_year")
            if (not isinstance(raw, dict) or set(raw) != YEAR_LABELS
                    or any(not isinstance(v, str) or len(v) != 64 for v in raw.values())):
                raise ValueError("one of 21 new original 11-year SHA ledgers missing")
        sample = {
            "symbol": sym, "family": grp,
            "source_cohort": origin, "native_m5_bars": n,
            "signed_existing12_source_provenance": is_original,
            "signed_new21_yearly_source_hashes": not is_original,
            "broker_session_calendar_verified": False,
            "bidask_cost_verified": False,
            "OHLC_outcomes_analyzed_here": False,
        }
        all_rows.append(sample)
        family_rows[grp].append(sample)
        origin_rows["original12_demo" if is_original else "new21_icmarkets_demo"].append(sample)
    summed = sum(r["native_m5_bars"] for r in all_rows)
    expected_extra = sum(r["native_m5_bars"] for r in all_rows if r["symbol"] in final33.SOURCE_TAIL)
    if (
        manifest.get("added_tail_three_bars") != expected_extra
        or summed - expected_extra != final33.PARENT_30_M5_BARS
        or 
        summed != manifest.get("all_33_original_m5_bars")
        or sum(r["native_m5_bars"] for r in origin_rows["original12_demo"]) != 8726985
        or len(origin_rows["original12_demo"]) != 12
        or len(origin_rows["new21_icmarkets_demo"]) != 21
    ):
        raise ValueError("original G0 12/21 bar source sum does not reconcile")
    by_family = {
        family: {
            "assets": len(family_rows[family]),
            "symbols": sorted(row["symbol"] for row in family_rows[family]),
            "verified_original_m5_bars": sum(row["native_m5_bars"] for row in family_rows[family]),
        }
        for family in FAMILIES
    }
    by_origin = {
        label: {
            "assets": len(rows),
            "native_m5_bars": sum(row["native_m5_bars"] for row in rows),
        }
        for label, rows in sorted(origin_rows.items())
    }
    return {
        "identity": IDENTITY,
        "status": "G0_FULL33_FAMILIES_ALL_COVERED_NO_MARKET_OUTCOMES",
        "source_run_original_12": source.g0.SOURCE_RUN,
        "source_run_new_21": source.NEW_SOURCE_RUN,
        "markets_count": 33,
        "native_m5_bars": summed,
        "families": by_family,
        "provenance": by_origin,
        "symbols": all_rows,
        "all_markets_included_no_economic_selection": True,
        "multi_source_broker_equivalence_not_proven": True,
        "no_H4_D1_broker_candle_certification": True,
        "no_broker_historical_bidask": True,
        "no_executable_net_results": True,
        "no_live_or_paper_trading": True,
        "no_returns_or_PnL_read": True,
        "traders_certified": 0,
        "next_gate": "SEPARATE_CAUSAL_PREREG_PLUS_REALISTIC_COST_MODEL",
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("verified_33_source_manifest", type=Path)
    ap.add_argument("output", type=Path)
    args = ap.parse_args()
    source_file = args.verified_33_source_manifest
    parent = source_file.parent
    hashes = source._hash_scope(
        parent / "OUTPUT_SHA256SUMS.txt",
        {source_file.name, "exact-code-head-sha.txt"},
    )
    source.g0.verified_file(parent, hashes, source_file.name)
    check = source._hash_scope(
        source_file.with_name(source_file.name + ".sha256"), {source_file.name}
    )
    source.g0.verified_file(parent, check, source_file.name)
    if check[source_file.name] != hashes[source_file.name]:
        raise ValueError("33 manifest SHA witnesses disagree")
    manifest = json.loads(source_file.read_text(encoding="utf-8"))
    output = census(manifest)
    args.output.mkdir(parents=True, exist_ok=True)
    file = args.output / "qore-native-33-market-families-source-only.json"
    file.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    file.with_name(file.name + ".sha256").write_text(
        source.g0.sha256(file) + f"  {file.name}\n", encoding="utf-8"
    )
    print(json.dumps({
        "status": output["status"],
        "families": {k: v["assets"] for k, v in output["families"].items()},
        "all_market_bars": output["native_m5_bars"],
        "net_authorized": False, "PnL_read": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
