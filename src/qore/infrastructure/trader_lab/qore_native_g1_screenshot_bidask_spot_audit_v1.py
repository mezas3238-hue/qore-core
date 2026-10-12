"""QORE Native 33 screenshots: strictly instantaneous Bid/Ask quality and cost proxy.

This tool NEVER validates 2016–2024 spreads, slippage, broker contract, fills,
NEWS PIT, trade economics, or G1. Prices are supplied by user screenshots
with unverified capture date and timestamp time zone; indices have alias risk.
"""
from __future__ import annotations

import argparse
import json
import re
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import qore_native_final33_three_m5_g0_v1 as universe
from qore.infrastructure.trader_lab import qore_native_market33_source_census_v1 as census

IDENTITY = "QORE_NATIVE_G1_USER_SCREENSHOT_BIDASK_SPOT_33_V1"
RESULT_IDENTITY = "QORE_NATIVE_33_ONE_SCREENSHOT_SPOT_SPREAD_AUDIT_V1"
SOURCE_SHA = "1291d5c2efb4e51c2698ea25ad420a01a213dc405b5070c37efbce4131606b85"
ALIASES = {"NAS100": "NDX100", "SP500": "SPX500"}
KNOWN_IMAGES = {
    "quote-screenshot-1": "7e261efa1364cdf8613c2996b04065d6f1a57ffa819eb9e9c9f640d020fb2897",
    "quote-screenshot-2": "ab1382d78ccebd3deed5aad3d61c27cf9352729f5c04b2e390951640fc15fbf0",
    "quote-screenshot-3": "c8794c6d6630d9f5fc0f5e5c30d2c87e139609222a20f6dbb595ac9e7d3132f3",
}
AMOUNTS = re.compile(r"^(?:0|[1-9][0-9]*)\.[0-9]{2,5}$")
TIME = re.compile(r"^16:13:(?:[0-5][0-9])$")

def spread_stats(doc: dict[str, Any]) -> dict[str, Any]:
    census.frozen_family_contract()
    if (
        doc.get("identity") != IDENTITY
        or doc.get("received_chat_date") != "2026-10-12"
        or doc.get("original_universe_G0_33_sha256") != SOURCE_SHA
        or doc.get("quote_calendar_date_verified") is not False
        or doc.get("quote_timezone_verified") is not False
        or doc.get("quote_broker_account_and_execution_contract_verified") is not False
        or doc.get("platform_app_identity_verified") is not False
        or doc.get("snapshot_device_clock_label") != "10:13"
        or doc.get("user_quote_rows_expected") != 33
    ):
        raise ValueError("screenshot provenance misrepresented")
    images = doc.get("screen_source_images")
    if (not isinstance(images, list) or len(images) != 3
            or {x.get("id"):x.get("sha256") for x in images} != KNOWN_IMAGES
            or any(x.get("raw_image_available_only_in_user_conversation") is not True
                   for x in images)):
        raise ValueError("missing or mismatched original 3 image SHA fingerprints")
    caveats = doc.get("scope_caveats", {})
    must_remain_uncertain = (
        "all_quotes_not_exactly_same_tick",
        "quote_date_and_timezones_unverified",
        "instruments_from_screenshot_may_differ_from_original_cTrader_G0_broker",
        "spread_instantaneous_not_historical",
        "commission_slippage_swap_latency_not_included",
        "fee_schedule_not_verified",
        "spread_around_trading_session_news_and_rollover_not_known",
        "execution_bidask_in_2016_to_2024_not_proven",
    )
    if (
        not isinstance(caveats, dict)
        or any(caveats.get(k) is not True for k in must_remain_uncertain)
        or caveats.get("net_certification_authorized") is not False
        or caveats.get("capital_or_live_authorized") is not False
    ):
        raise ValueError("screenshot cannot attest historic or executable broker costs")
    extra = doc.get("outside_frozen_universe_excluded")
    if (not isinstance(extra, list) or len(extra) != 1
            or extra[0].get("displayed_symbol") != "BTCUSD"):
        raise ValueError("BTCUSD is extra, not to be silently incorporated in 33")
    quotes = doc.get("rows")
    if not isinstance(quotes, list) or len(quotes) != 33:
        raise ValueError("must record exactly 33 owner-supplied market quotes")
    found: set[str] = set()
    result = []
    for row in quotes:
        symbol = row.get("canonical_symbol")
        displayed = row.get("displayed_symbol")
        if symbol not in universe.FROZEN_UNIVERSE_33 or symbol in found:
            raise ValueError("frozen QORE 33 missing/repeated or replaced")
        found.add(symbol)
        alias = symbol in ALIASES
        if displayed != ALIASES.get(symbol, symbol):
            raise ValueError("unverified alias cannot silently convert index quotes")
        if row.get("legacy_source_alias_equivalence_verified") is not (not alias):
            raise ValueError("symbol-mapping certainty drift")
        if (row.get("quote_bidask_operator_confirmed") is not True
                or row.get("not_historical_bidask") is not True):
            raise ValueError("bidask must be visibly provided but not historical")
        image_id = row.get("screenshot_id")
        if (image_id not in KNOWN_IMAGES
                or row.get("source_image_sha256") != KNOWN_IMAGES[image_id]):
            raise ValueError("per-quote original image SHA missing/mismatch")
        hhmmss = row.get("quote_hhmmss_displayed_unverified_timezone")
        if hhmmss is not None and (not isinstance(hhmmss, str) or not TIME.fullmatch(hhmmss)):
            raise ValueError("quote clock is not a verifiable timezone or dated timestamp")
        bid_s, ask_s = row.get("bid_transcribed"), row.get("ask_transcribed")
        if (not isinstance(bid_s, str) or not isinstance(ask_s, str)
                or not AMOUNTS.fullmatch(bid_s)
                or not AMOUNTS.fullmatch(ask_s)):
            raise ValueError("prices must be manually transcribed decimal strings")
        bid, ask = Decimal(bid_s), Decimal(ask_s)
        if bid <= 0 or ask < bid:
            raise ValueError("bid/ask inversion or invalid values")
        mid, spread = (bid + ask) / 2, ask - bid
        bps = spread / mid * Decimal(10000)
        unit = "USD_per_ounce_NOT_LOT_COST" if symbol in {"XAUUSD","XAGUSD"} else (
            "index_points_NOT_CONTRACT_COST" if symbol in {"NAS100","SP500","US30"}
            else "pips")
        pip_size = Decimal("0.01") if symbol.endswith("JPY") else Decimal("0.0001")
        pip = spread / pip_size if unit == "pips" else None
        quality = (
            "BLOCKED_ZERO_SPREAD_SNAPSHOT" if spread == 0 else
            "BLOCKED_INDEX_ALIAS_UNVERIFIED" if alias else
            "SPOT_ONLY_BROKER_HISTORICAL_VALIDATION_PENDING"
        )
        result.append({
            "canonical_symbol":symbol, "screenshot_symbol":displayed,
            "source_screenshot_id":image_id,
            "quote_local_clock_without_date_or_timezone":hhmmss,
            "bid":bid_s,"ask":ask_s,
            "spread_absolute":str(spread),
            "spread_unit":unit,
            "spread_pips_if_fx":str(pip) if pip is not None else None,
            "spread_bps_approx":round(float(bps),6),
            "family": next(k for k,v in census.FAMILIES.items() if symbol in v),
            "source_broker_historical_same_contract_verified":False,
            "commission_slippage_or_roll_over_included":False,
            "bidask_history_2016_2024_available":False,
            "usable_to_certify_net_edge":False,
            "quality_gate":quality,
        })
    if found != universe.FROZEN_UNIVERSE_33:
        raise ValueError("33 original market symbols not fully covered")
    known_anomalies = {x.get("symbol") for x in doc.get("known_anomalies", [])}
    if known_anomalies != {"GBPUSD","NAS100","SP500"}:
        raise ValueError("zero GBPUSD and mismatched index display alias flags required")
    by_q = {x["canonical_symbol"]:x for x in result}
    if by_q["GBPUSD"]["spread_absolute"] != "0.00000":
        raise ValueError("zero quote spread anomaly no longer matched source screenshot")
    if not by_q["GBPUSD"]["quality_gate"].startswith("BLOCKED"):
        raise ValueError("zero spread cannot be used as representative cost")
    return {
        "identity":RESULT_IDENTITY,
        "status":"G1_SPOT_TRANSCRIPTION_ONLY_NO_HISTORICAL_EXECUTION_CERTIFICATION",
        "source_g0_market_count":33,
        "visible_quote_coverage_33":33,
        "not_historically_time_aligned":True,
        "quote_calendar_date_verified":False,
        "platform_broker_account_verified":False,
        "historical_bidask_2016_2024_reconstructed":False,
        "bidask_commission_slippage_swap_live_fills_verified":False,
        "btc_extra_excluded":True,
        "zero_display_spread_anomaly":["GBPUSD"],
        "unverified_index_contract_aliases":["NAS100<->NDX100","SP500<->SPX500"],
        "eligible_for_spot_spread_descriptive_comparison":30,
        "traders_certified":0,
        "production_untouched":True,
        "spread_mid_bps_definition":"10000*(ask-bid)/((ask+bid)/2) SINGLE STATIC QUOTE, NOT COST MODEL",
        "rows":sorted(result,key=lambda x:x["canonical_symbol"]),
    }

def main() -> None:
    p=argparse.ArgumentParser()
    p.add_argument("quote_transcription",type=Path)
    p.add_argument("outdir",type=Path)
    args=p.parse_args()
    result=spread_stats(json.loads(args.quote_transcription.read_text(encoding="utf-8")))
    args.outdir.mkdir(parents=True, exist_ok=True)
    file=args.outdir/"qore-native-33-spot-bidask-spreads-audited.json"
    file.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    from qore.infrastructure.trader_lab import qore_native_existing12_m5_g0_v1 as g0
    file.with_name(file.name+".sha256").write_text(
        g0.sha256(file)+f"  {file.name}\n",encoding="utf-8",
    )
    print(json.dumps({
        "status":result["status"],"all_quotes":33,
        "broker_historical_quote_series_verified":False,
        "GBPUSD_zero_spread_blocked":True,
        "index_contract_aliases_blocked":2,
        "net_traders_certified":0,
        "examples":{x["canonical_symbol"]:x["spread_bps_approx"] for x in result["rows"]
                    if x["canonical_symbol"] in ("XAUUSD","XAGUSD","NAS100","SP500","US30","EURUSD","GBPUSD")},
    },sort_keys=True))

if __name__ == "__main__":
    main()
