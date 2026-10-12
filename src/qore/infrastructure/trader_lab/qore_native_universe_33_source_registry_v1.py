"""Owner-requested cross-asset universe, observed GitHub provenance, NOT broker verification.

For classification we use QORE Issue #574's 33 market cohort. QORE's original
CIBO 10Y M5 Atlas run #35166210458 has 12 immutable per-symbol artifacts;
9 of those also have native M1 10Y in run #35548099334.
EURJPY and USDCHF have shorter 7Y M5 archives in run #36079229139.
All other entries are *not in these verified archives*, not a proof that
no other QORE file, cTrader account or provider has these instruments.
No download or trading executed by this module.
"""
from __future__ import annotations

import json
from pathlib import Path

REGISTRY_ID = "QORE_NATIVE_UNIVERSE_33_INVENTORY_20261011_SOURCE_ONLY"
GROUPS = {
    "indices": ("NAS100", "SP500", "US30"),
    "metals": ("XAUUSD", "XAGUSD"),
    "fx_majors": ("EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD", "NZDUSD"),
    "fx_crosses_minors": (
        "EURGBP", "EURJPY", "EURCHF", "EURCAD", "EURAUD", "EURNZD",
        "GBPJPY", "GBPCHF", "GBPCAD", "GBPAUD", "GBPNZD",
        "AUDJPY", "AUDCAD", "AUDCHF", "AUDNZD",
        "CADJPY", "CADCHF", "CHFJPY",
        "NZDJPY", "NZDCAD", "NZDCHF",
    ),
}

M5_10Y = frozenset({
    "AUDJPY", "AUDUSD", "EURUSD", "GBPJPY", "GBPUSD", "USDCAD",
    "USDJPY", "NAS100", "SP500", "US30", "XAUUSD", "XAGUSD",
})
M1_10Y = frozenset({
    "AUDJPY", "AUDUSD", "EURUSD", "GBPJPY", "GBPUSD", "USDCAD",
    "USDJPY", "NAS100", "XAUUSD",
})
M5_7Y = frozenset({"EURJPY", "USDCHF"})
CANONICAL_ALIAS_HINTS = {"NAS100": "USTEC"}  # historical CIBO alias, NOT current broker proof
M5_10Y_SOURCE = {
    "run_id": 35166210458,
    "head_sha": "ab782b8e9f890f86a2b6500070f0556b4b685e3d",
    "start_utc": "2016-09-17T00:00:00+00:00",
    "end_exclusive_utc": "2026-09-17T00:00:00+00:00",
    "source": "CIBO cTrader DEMO windowed M5 artifacts",
}
M1_10Y_SOURCE = {
    "run_id": 35548099334,
    "head_sha": "18c338aedd5013ce65a6cb6408ffbc2e904a6217",
    "start_utc": "2016-09-17T00:00:00+00:00",
    "end_exclusive_utc": "2026-09-17T00:00:00+00:00",
    "source": "Capitalizer cTrader DEMO native M1 artifacts",
}
M5_7Y_SOURCE = {
    "run_id": 36079229139,
    "head_sha": "6958ea0c4f183020b5248b413af998065c6662da",
    "approx_first_m5_utc": "2019-09-27T00:50:00+00:00",
    "approx_end_m5_utc": "2026-09-25T00:45:00+00:00",
    "source": "QORE VT08 cTrader DEMO 7Y archive (reserved-window restrictions)",
}


def universe() -> tuple[str, ...]:
    flat = tuple(x for group in GROUPS.values() for x in group)
    if len(flat) != len(set(flat)) or len(flat) != 33:
        raise ValueError("CANONICAL_UNIVERSE_DUPLICATE_OR_WRONG_COUNT")
    if M5_10Y & M5_7Y or not (M1_10Y <= M5_10Y):
        raise ValueError("PROVENANCE_COHORT_INCONSISTENT")
    return flat


def inventory() -> dict[str, object]:
    flat = universe()
    rows = []
    for group, symbols in GROUPS.items():
        for symbol in symbols:
            coverage = (
                "EXISTING_M5_10Y" if symbol in M5_10Y else
                "EXISTING_M5_7Y_PARTIAL" if symbol in M5_7Y else
                "NOT_IN_VERIFIED_GITHUB_M5_ARCHIVES"
            )
            rows.append({
                "symbol": symbol,
                "group": group,
                "m5_status": coverage,
                "m1_status": ("EXISTING_M1_10Y" if symbol in M1_10Y
                              else "NO_VERIFIED_M1_10Y_ARTIFACT"),
                "provider_symbol_id_confirmed_current_account": False,
                "ic_markets_account_proven": False,
                "cTrader_download_completed_in_this_program": False,
                "historical_alias_hint_not_broker_proof": CANONICAL_ALIAS_HINTS.get(symbol),
                "requires_m5_capture_or_extension": symbol not in M5_10Y,
                "requires_m1_capture": symbol not in M1_10Y,
            })
    return {
        "identity": REGISTRY_ID,
        "definition_source_issue": "https://github.com/mezas3238-hue/qore-core/issues/574",
        "source_archives": {
            "m5_10y": M5_10Y_SOURCE,
            "m1_10y": M1_10Y_SOURCE,
            "m5_7y": M5_7Y_SOURCE,
        },
        "groups": {k: list(v) for k, v in GROUPS.items()},
        "counts": {
            "universe_total": len(flat),
            "indices": 3, "metals": 2,
            "fx_majors": 7, "fx_crosses_minors": 21,
            "verified_m5_10y": len(M5_10Y),
            "verified_m5_7y_partial": len(M5_7Y),
            "m5_absent_from_selected_archives": len(flat) - len(M5_10Y) - len(M5_7Y),
            "m5_needed_to_reach_10y_target": len(flat) - len(M5_10Y),
            "verified_m1_10y": len(M1_10Y),
            "m1_needed_to_reach_10y_target": len(flat) - len(M1_10Y),
        },
        "m5_pending": [s for s in flat if s not in M5_10Y],
        "m1_pending": [s for s in flat if s not in M1_10Y],
        "rows": rows,
        "actual_ICMarkets_broker_identity": "UNVERIFIED",
        "broker_catalog_fetched": False,
        "account_authorized": False,
        "new_captures_confirmed": 0,
        "data_integrity_certified_for_all_33": False,
        "fresh_oos_claimed": False,
        "production_authorized": False,
        "live_authorized": False,
    }


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result = inventory()
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print("QORE_33_INVENTORY_NO_NEW_CAPTURE",
          json.dumps(result["counts"], sort_keys=True))


if __name__ == "__main__":
    main()
