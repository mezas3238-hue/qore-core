"""FX carry H4 historical-source preflight: genuine PIT 1M forwards required.

This module generates no economic returns or Sharpe. It rejects spot-only or
made-up forward premiums. No broker access, order execution, file downloads,
retrospective market outcomes, current swaps as history, or OOS holdout.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path

IDENTITY = "QORE_NATIVE_FX_CARRY_28_ONE_MONTH_PIT_GATE_V1"
EMBARGO = date(2024, 9, 17)
EARLIEST = date(2016, 9, 17)
DECISION_MARGIN = timedelta(minutes=5)
MAX_QUOTE_AGE = timedelta(days=7)
LEGS = 6
WEIGHT = Decimal(1) / Decimal(12)
CURRENCIES = frozenset(("AUD", "CAD", "CHF", "EUR", "GBP", "JPY", "NZD", "USD"))
FX28 = (
    "AUDUSD", "EURUSD", "GBPUSD", "NZDUSD", "USDCAD", "USDCHF", "USDJPY",
    "AUDJPY", "AUDCAD", "AUDCHF", "AUDNZD", "CADCHF", "CADJPY", "CHFJPY",
    "EURAUD", "EURCAD", "EURCHF", "EURGBP", "EURJPY", "EURNZD",
    "GBPAUD", "GBPCAD", "GBPCHF", "GBPJPY", "GBPNZD",
    "NZDCAD", "NZDCHF", "NZDJPY",
)
SCHEMA = "QORE_FX_CARRY_ONE_MONTH_SIGNED_SPOT_FORWARD_PIT_SNAPSHOT_V1"
REQUIRED_ROW = frozenset((
    "symbol", "observed_at_utc", "received_at_utc", "decision_at_utc",
    "spot_bid", "spot_ask", "forward_bid", "forward_ask",
    "maturity_utc", "tenor", "quote_basis", "provider_id",
    "source_evidence_sha256", "license_read_authorized",
))


def validate_universe() -> None:
    if len(FX28) != 28 or len(set(FX28)) != 28:
        raise ValueError("FX_CARRY_FROZEN_ROSTER_BAD")
    unordered = {frozenset((s[:3], s[3:])) for s in FX28}
    if (len(unordered) != 28 or
        {c for s in FX28 for c in (s[:3], s[3:])} != CURRENCIES):
        raise ValueError("FX_CARRY_EIGHT_CURRENCY_NETWORK_BAD")


def utc(value: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError("FX_CARRY_TIME_NOT_STRING")
    t = datetime.fromisoformat(value)
    if t.tzinfo is None or t.utcoffset() != timedelta():
        raise ValueError("FX_CARRY_TIMESTAMP_MUST_BE_UTC")
    return t.astimezone(UTC)


def price(row: dict, field: str) -> Decimal:
    try:
        value = Decimal(str(row[field]))
    except (KeyError, InvalidOperation, ValueError):
        raise ValueError("FX_CARRY_REQUIRED_PRICE_MISSING_OR_MALFORMED_" + field)
    if not value.is_finite() or value <= 0:
        raise ValueError("FX_CARRY_NONPOSITIVE_OR_NONFINITE_PRICE_" + field)
    return value


def quote(row: dict) -> tuple[str, Decimal, datetime]:
    if not isinstance(row, dict) or set(row) != REQUIRED_ROW:
        raise ValueError("FX_CARRY_PIT_ROW_SCHEMA_EXACT_REQUIRED")
    symbol = row["symbol"]
    if symbol not in FX28:
        raise ValueError("FX_CARRY_UNKNOWN_PAIR")
    if row["quote_basis"] != "QUOTE_PER_ONE_BASE" or row["tenor"] != "1M":
        raise ValueError("FX_CARRY_BAD_ORIENTATION_OR_TENOR")
    if row["license_read_authorized"] is not True:
        raise ValueError("FX_CARRY_LICENSE_NOT_VERIFIED")
    provider = row["provider_id"]
    if not isinstance(provider, str) or not provider.strip():
        raise ValueError("FX_CARRY_PROVIDER_ID_UNKNOWN")
    digest = row["source_evidence_sha256"]
    if (not isinstance(digest, str) or len(digest) != 64 or
        any(c not in "0123456789abcdef" for c in digest)
        or digest == "0"*64):
        raise ValueError("FX_CARRY_SOURCE_EVIDENCE_SHA_MISSING")
    observed = utc(row["observed_at_utc"])
    received = utc(row["received_at_utc"])
    decision = utc(row["decision_at_utc"])
    maturity = utc(row["maturity_utc"])
    if (not EARLIEST <= decision.date() < EMBARGO or
        not observed <= received <= decision - DECISION_MARGIN or
        decision - observed > MAX_QUOTE_AGE):
        raise ValueError("FX_CARRY_LOOKAHEAD_OR_INVALID_HOLDOUT_OR_STALE_QUOTE")
    days_to_maturity = (maturity - decision).total_seconds() / 86400
    if not 25 <= days_to_maturity <= 40:
        raise ValueError("FX_CARRY_FORWARD_MATURITY_NOT_1M")
    sb, sa, fb, fa = (price(row, x) for x in
                       ("spot_bid", "spot_ask", "forward_bid", "forward_ask"))
    if sb > sa or fb > fa:
        raise ValueError("FX_CARRY_NEGATIVE_QUOTED_SPREAD")
    spot_mid = (sb+sa)/2
    forward_mid = (fb+fa)/2
    # Quote/base S: high-yield BASE => spot exceeds BASE-discounted
    # forward, hence positive log(S/F). This is a ranking ONLY.
    score = Decimal(str(math.log(float(spot_mid / forward_mid))))
    if not score.is_finite():
        raise ValueError("FX_CARRY_NONFINITE_FORWARD_DISCOUNT")
    return symbol, score, decision


def rank_one_month(payload: dict) -> dict:
    """Predecision rank only; NEVER evaluate returns or certify broker carry."""
    validate_universe()
    if (not isinstance(payload, dict) or
        set(payload) != {"schema", "quotes", "source_license_scope"} or
        payload["schema"] != SCHEMA or
        payload["source_license_scope"] != "PRIVATE_RESEARCH_READ_ONLY" or
        not isinstance(payload["quotes"], list)):
        raise ValueError("FX_CARRY_MISSING_SIGNED_PIT_SNAPSHOT_ENVELOPE")
    quotes = payload["quotes"]
    if len(quotes) != 28:
        raise ValueError("FX_CARRY_MISSING_SOME_OF_28_HISTORICAL_FORWARD_QUOTES")
    scored = [quote(item) for item in quotes]
    if ({x[0] for x in scored} != set(FX28) or
        len({x[0] for x in scored}) != 28):
        raise ValueError("FX_CARRY_DUPLICATE_OR_MISSING_SYMBOL")
    times = {x[2] for x in scored}
    if len(times) != 1:
        raise ValueError("FX_CARRY_DIFFERENT_DECISION_TIME_WITHIN_CROSS_SECTION")
    ranked = sorted(scored, key=lambda q: (-q[1], q[0]))
    longs = [symbol for symbol,score,t in ranked[:LEGS]]
    shorts = [symbol for symbol,score,t in ranked[-LEGS:]]
    if len(set(longs+shorts)) != 12:
        raise ValueError("FX_CARRY_BASKET_NOT_DISJOINT")
    pos = {s: Decimal(0) for s in FX28}
    for s in longs:pos[s] = WEIGHT
    for s in shorts:pos[s] = -WEIGHT
    exposures = {c: Decimal(0) for c in CURRENCIES}
    for s,p in pos.items():
        exposures[s[:3]] += p
        exposures[s[3:]] -= p
    # 1/12 has an infinite decimal representation: Decimal precision can
    # leave <=1e-28 cancellation noise even for algebraically flat baskets.
    tolerance = Decimal("1e-20")
    if (abs(sum(exposures.values())) > tolerance or
        abs(sum(pos.values())) > tolerance):
        raise ValueError("FX_CARRY_CURRENCY_EXPOSURE_NOT_SELF_FINANCING")
    if abs(sum(abs(p) for p in pos.values()) - Decimal(1)) > tolerance:
        raise ValueError("FX_CARRY_GROSS_EXPOSURE_NOT_ONE")
    return {
        "identity": IDENTITY,
        "status": "ONE_MONTH_PIT_FORWARD_QUOTE_STRUCTURE_PASS_NOT_ECONOMIC_EDGE",
        "decision_at_utc": next(iter(times)).isoformat(),
        "input_quotes_seen": 28,
        "independent_currencies": 8,
        "pairs_are_NOT_28_independent_return_factors": True,
        "long_6_pairs": longs,
        "short_6_pairs": shorts,
        "gross_exposure_nominal": 1.0,
        "nominal_base_quote_currency_exposure": {
            c: float(exposures[c]) for c in sorted(exposures)},
        "source_origin_authenticated_by_external_license_holder": False,
        "source_pit_revision_history_independently_authenticated": False,
        "FX_carry_economic_backtest_performed": False,
        "forward_excess_return_and_broker_swaps_verified": False,
        "broker_net_authorized": False,
        "holdout_2024_09_17_onward_opened": False,
        "certified_traders": 0,
    }


def preflight() -> dict:
    """Evidence actually observed so far: only original spot M5 and snapshots."""
    validate_universe()
    return {
        "identity": IDENTITY,
        "status": "BLOCKED_NO_AUTHENTIC_PIT_CARRY_SOURCE",
        "fx_pairs_in_original_G0": 28,
        "underlying_currencies": sorted(CURRENCIES),
        "independent_currency_dimensions_at_most": 7,
        "verified_original_spot_M5_sources": 33,
        "verified_historical_one_month_forward_quote_sets_28_of_28": 0,
        "verified_historical_PIT_eight_currency_interest_rate_curves": 0,
        "read_only_current_12_broker_spec_snapshot_PR": 870,
        "current_swapLong_swapShort_explicitly_present_in_that_snapshot": False,
        "current_broker_snapshot_proves_historical_2016_2024_swaps": False,
        "monthly_portfolio_backtest_executed": False,
        "source_only_M5_sufficient_for_FX_carry": False,
        "holdout_opened": False,
        "claimed_sharpe": None,
        "certified_traders": 0,
        "production_untouched": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--one-month-private-PIT-snapshot", type=Path)
    args = parser.parse_args()
    if args.one_month_private_PIT_snapshot:
        raw = args.one_month_private_PIT_snapshot.read_bytes()
        parsed = json.loads(raw)
        result = rank_one_month(parsed)
        # SHA provenance of the received snapshot bytes, no export raw quotes
        result["local_input_bytes_sha256_not_provider_authentication"] = (
            hashlib.sha256(raw).hexdigest()
        )
    else:
        result = preflight()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps({
        "identity": result["identity"], "status": result["status"],
        "economic_PNL_or_SHARPE_calculated": False,
        "holdout_opened": False, "certified": 0
    }, sort_keys=True))


if __name__ == "__main__":
    main()
