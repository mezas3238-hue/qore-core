"""Final user-pre-registered volatility-scaled daily 252d momentum, research only.

Frozen prereg f9248d42; no broker orders, no historical OOS claim, no NET.
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import date
from pathlib import Path
from statistics import stdev

from qore.research.alpha2_intermarket import MARKETS, sha256_file
from qore.research.alpha2_lab_h4_extract import (
    source33_manifest,
    source_rows_before_embargo,
    verify_source,
)
from qore.research.alpha2_tsmom_daily_weekly import (
    DEV_END,
    EMBARGO,
    Day,
    daily_from_native,
)

IDENTITY = "QORE_ALPHA2_FINAL_TSMOM_252_RISK20_TARGET10_CAP3_V1"
PREREG = "f9248d42a6cbced3d6e962b24e47c709cb91161c"
WARMUP = 254
LOOKBACK = 252
VOL_WINDOW = 20
ANNUAL_TARGET_VOL = 0.10
EXPOSURE_CAP = 3.0
HOLD = 5
COST_PER_SIDE_BPS = 1.0


def _risk_weight(days: list[Day], i: int) -> tuple[float, float, bool]:
    """Past 252 eligible closes for sign and last twenty *prior* daily returns."""
    if i < WARMUP:
        raise ValueError("TSMOM_FINAL_RISK_WARMUP_INCOMPLETE")
    old = days[i-LOOKBACK-1].close
    recent = days[i-1].close
    direction = int(recent > old) - int(recent < old)
    if direction == 0:
        return 0.0, 0.0, False
    log_r = [
        math.log(days[j].close / days[j-1].close)
        for j in range(i-VOL_WINDOW, i)
    ]
    if len(log_r) != VOL_WINDOW or not all(math.isfinite(x) for x in log_r):
        return 0.0, 0.0, False
    daily_sigma = stdev(log_r)
    annual = daily_sigma * math.sqrt(252)
    if annual <= 0 or not math.isfinite(annual):
        return 0.0, 0.0, False
    unconstrained = ANNUAL_TARGET_VOL / annual
    capped = unconstrained > EXPOSURE_CAP
    magnitude = min(EXPOSURE_CAP, unconstrained)
    return direction * magnitude, annual, capped


def replay(symbol: str, days: list[Day]) -> dict:
    if symbol not in MARKETS or any(
        days[j-1].utc_day >= days[j].utc_day for j in range(1, len(days))
    ):
        raise ValueError("TSMOM_FINAL_SYMBOL_OR_DAILY_ORDER_INVALID")
    original = []
    denied: dict[str, int] = {}
    attempted_weeks: set[str] = set()
    last_exit: date | None = None
    capped = 0
    for i in range(WARMUP, len(days)):
        item = days[i]
        y, w, _ = item.utc_day.isocalendar()
        week = f"{y}-W{w:02d}"
        if week in attempted_weeks or (
            last_exit is not None and item.utc_day <= last_exit
        ):
            continue
        attempted_weeks.add(week)
        signed, realized, hit_cap = _risk_weight(days, i)
        if signed == 0.0:
            denied["ZERO_SIGN_OR_REALIZED_VOL"] = (
                denied.get("ZERO_SIGN_OR_REALIZED_VOL", 0) + 1
            )
            continue
        if i + HOLD > len(days):
            denied["INSUFFICIENT_FIVE_SESSIONS"] = (
                denied.get("INSUFFICIENT_FIVE_SESSIONS", 0) + 1
            )
            continue
        final = days[i+HOLD-1]
        if item.utc_day < DEV_END <= final.utc_day or final.utc_day >= EMBARGO:
            denied["ERA_BOUNDARY_OR_EMBARGO"] = (
                denied.get("ERA_BOUNDARY_OR_EMBARGO", 0) + 1
            )
            continue
        # Risk has to be known from pre-entry closes only; no M5 return in signal.
        gross = signed * 10000 * (final.close/item.open - 1)
        assume = COST_PER_SIDE_BPS * 2 * abs(signed)
        if not math.isfinite(gross) or assume <= 0:
            raise ValueError("TSMOM_FINAL_NONFINITE_PRICE_OR_COST")
        capped += int(hit_cap)
        original.append({
            "symbol": symbol,
            "era": "DEVELOPMENT" if item.utc_day < DEV_END else "DIAGNOSTIC",
            "iso_week": week,
            "decision_reference_utc_day": item.utc_day.isoformat(),
            "last_native_reference_exit_day": final.utc_day.isoformat(),
            "signed_risk_scaled_exposure": signed,
            "realized_20d_vol_annual": realized,
            "vol_target_cap_applied": hit_cap,
            "gross_risk_scaled_reference_bps": gross,
            "assumed_1bp_each_side_cost_bps": assume,
            "gross_minus_assumed_cost_proxy_bps": gross-assume,
            "broker_NET_NOT_VERIFIED": True,
        })
        last_exit = final.utc_day
    return {
        "symbol": symbol,
        "count_events": len(original),
        "cap_hit_events": capped,
        "censored_or_abstained": denied,
        "events": original,
    }


def replay_original(symbol: str, native: Path, signed33: Path, aggregate12: Path | None) -> dict:
    if symbol not in MARKETS:
        raise ValueError("TSMOM_FINAL_NOT_IN_ORIGINAL33")
    manifest = source33_manifest(signed33)
    proof = verify_source(symbol, native, manifest, aggregate12)
    days, original_census = daily_from_native(source_rows_before_embargo(native, symbol))
    x = replay(symbol, days)
    return {
        "identity": IDENTITY,
        "prereg_ancestor": PREREG,
        "original_source_manifest_sha256": (
            "1291d5c2efb4e51c2698ea25ad420a01a213dc405b5070c37efbce4131606b85"
        ),
        "source_proof": proof,
        "original_census": original_census,
        "original_11year_RAW_QUALITY_sha_verified": True,
        "embargoed_2024_plus_OHLC_not_read": True,
        "prior_panel_previously_exposed_exploratory": True,
        "actual_BIDASK_not_proven": True,
        "broker_execution_NOT_proven": True,
        "broker_NET_not_computed": True,
        "UTC001_certified": False,
        "orders": 0,
        **x,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("symbol", choices=MARKETS)
    p.add_argument("native", type=Path)
    p.add_argument("signed33", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--aggregate12", type=Path)
    args = p.parse_args()
    data = replay_original(args.symbol, args.native, args.signed33, args.aggregate12)
    args.output.mkdir(parents=True, exist_ok=True)
    path = args.output / f"alpha2-tsmom-final-risk-{args.symbol}.json"
    path.write_text(json.dumps(data, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    path.with_name(path.name+".sha256").write_text(
        sha256_file(path)+"  "+path.name+"\n", encoding="utf-8"
    )
    print(json.dumps({
        "symbol": args.symbol, "n": data["count_events"],
        "cap": data["cap_hit_events"], "NET": "BLOCKED", "orders": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
