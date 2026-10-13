"""QORE-Alpha2 exact native M5 first-entry gross ONLY paired PATR reference.

No bid/ask, broker fills, commissions, macro-PIT or net trading claimed.
Never sends an order. All 11-year original RAW/QUALITY SHA verified before OHLC.
"""
from __future__ import annotations

import argparse
import json
import math
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from qore.research.alpha2_intermarket import (
    ENTRY_DELAY,
    H4,
    M5,
    MARKETS,
    MAX_HOLD,
    RESEARCH_CUTOFF,
    Bar,
    _check_bar,
    sha256_file,
)
from qore.research.alpha2_lab_h4_extract import (
    source33_manifest,
    source_rows_before_embargo,
    verify_source,
)
from qore.research.alpha2_signal_census import NAME, SOURCE_HEAD, SOURCE_SHA

IDENTITY = "QORE_ALPHA2_G1A_GROSS_NATIVE_M5_MATCHED_V1"
DEV_END = datetime(2022, 9, 17, tzinfo=UTC)
SOURCE_GROSS_ONLY = "RESEARCH_GROSS_NEWS_UNFILTERED_NOT_NET_NOT_LIVE"


def read_signed_signals(root: Path) -> list[dict[str, Any]]:
    ledger = root / NAME
    if (sha256_file(ledger) != SOURCE_SHA
            or (root / "exact-code-head-sha.txt").read_text(encoding="utf-8").strip()
            != SOURCE_HEAD):
        raise ValueError("immutable 33 signal-only original SHA/HEAD drift")
    raw = json.loads(ledger.read_text(encoding="utf-8"))
    if (raw.get("identity") != "QORE_ALPHA2_PATR_SHA33_ULTRAFAST_RESEARCH_LEDGER_V1"
            or raw.get("number_of_signals") != 224
            or raw.get("universe") != sorted(MARKETS)
            or raw.get("broker_orders") != 0
            or raw.get("gross_or_net_PnL_calculated") is not False):
        raise ValueError("original no-PnL source signal contract drift")
    signals = raw["signals"]
    if not isinstance(signals, list) or len(signals) != 224:
        raise ValueError("unrecognized source signal population")
    return signals


def _at(value: str) -> datetime:
    t = datetime.fromisoformat(value)
    if t.tzinfo is None or t.utcoffset() != timedelta(0):
        raise ValueError("exact UTC timestamp required")
    return t


def validate_one_signal(event: dict[str, Any]) -> tuple[datetime, datetime, float]:
    t = _at(event["bar_start_utc"])
    decision = _at(event["decision_utc"])
    entry = _at(event["earliest_entry_utc"])
    exit_latest = _at(event["latest_exit_utc"])
    d = event["stop_distance_price"]
    if (event["symbol"] not in MARKETS
            or decision != t + H4
            or entry != decision + ENTRY_DELAY
            or exit_latest != entry + MAX_HOLD
            or exit_latest > RESEARCH_CUTOFF
            or t.hour % 4 or t.minute or t.second or t.microsecond
            or not math.isfinite(d) or d <= 0
            or event["direction"] not in (-1, 1)
            or event["baseline_direction"] not in (-1, 1)
            or event["classification"] != "RESEARCH_SIGNAL_NOT_TRADE"
            or "BLOCKED" not in event["execution_status"]):
        raise ValueError("original signal decision/stop/entry/permissions drift")
    return entry, exit_latest, d


def arm(
    *,
    m5: Mapping[datetime, Bar],
    entry_at: datetime,
    expire_at: datetime,
    distance: float,
    direction: int,
) -> dict[str, Any]:
    """Strict native contiguous M5 path, adverse stop-first handling."""
    first = m5.get(entry_at)
    if first is None:
        return {"status": "NO_ENTRY_NATIVE_M5"}
    entry_price = first.open
    stop = entry_price - direction * distance
    target = entry_price + direction * (2.0 * distance)
    if entry_price <= 0 or min(stop, target) <= 0:
        return {"status": "UNSAFE_NONPOSITIVE_REFERENCE_GEOMETRY"}
    k = 0
    exit_price: float | None = None
    exit_at: datetime | None = None
    reason = ""
    both_touch = False
    while entry_at + M5 * k < expire_at:
        now = entry_at + M5 * k
        bar = m5.get(now)
        if bar is None:
            return {"status": "PATH_GAP_CENSORED", "first_gap_utc": now.isoformat()}
        _check_bar(bar)
        adverse_open = (bar.open <= stop if direction == 1 else bar.open >= stop)
        favorable_open = (bar.open >= target if direction == 1 else bar.open <= target)
        hits_stop = (bar.low <= stop if direction == 1 else bar.high >= stop)
        hits_target = (bar.high >= target if direction == 1 else bar.low <= target)
        if adverse_open:
            exit_price, reason = float(bar.open), "ADVERSE_GAP_STOP_AT_OPEN"
        elif favorable_open:
            exit_price, reason = float(target), "FAVORABLE_GAP_CAPPED_TARGET"
        elif hits_stop:
            exit_price = float(stop)
            both_touch = bool(hits_target)
            reason = "DOUBLE_TOUCH_STOP_FIRST" if both_touch else "STOP_REFERENCE"
        elif hits_target:
            exit_price, reason = float(target), "TARGET_REFERENCE"
        if exit_price is not None:
            exit_at = now + M5
            break
        k += 1
    if exit_price is None:
        expiry = m5.get(expire_at)
        if expiry is None:
            return {"status": "EXPIRY_OPEN_MISSING"}
        exit_price, exit_at, reason = float(expiry.open), expire_at, "EXPIRE_NATIVE_M5_OPEN"
    gross = direction * (exit_price - entry_price)
    return {
        "status": "COMPLETE_GROSS_PROXY",
        "entry_utc": entry_at.isoformat(), "exit_utc": exit_at.isoformat(),
        "entry_reference_price": float(entry_price),
        "exit_reference_price": float(exit_price),
        "stop_reference": float(stop), "target_reference": float(target),
        "planned_stop_distance_native_units": distance,
        "gross_R": float(gross / distance),
        "gross_bps": float(10000.0 * gross / entry_price),
        "reason": reason, "same_M5_stop_target_collision": both_touch,
        "bidask_or_broker_fill": False,
    }


def replay_symbol(
    symbol: str,
    native: Path,
    signed33: Path,
    signed_signal: Path,
    aggregate12: Path | None = None,
) -> dict[str, Any]:
    if symbol not in MARKETS:
        raise ValueError("frozen 33 market only")
    frozen = source33_manifest(signed33)
    proof = verify_source(symbol, native, frozen, aggregate12)
    ledger = read_signed_signals(signed_signal)
    source_subset = [x for x in ledger if x["symbol"] == symbol]
    by_event: dict[datetime, dict[str, Any]] = {}
    wanted: set[datetime] = set()
    for x in source_subset:
        entry, last, _ = validate_one_signal(x)
        if entry in by_event:
            raise ValueError("duplicate market entry events in signed ledger")
        by_event[entry] = x
        # Never access post-embargo economic values.
        for k in range(int(MAX_HOLD / M5) + 1):
            moment = entry + M5 * k
            if moment >= RESEARCH_CUTOFF:
                raise ValueError("embargo would be crossed")
            wanted.add(moment)

    # Original source validated before reading ANY OHLC values.
    available: dict[datetime, Bar] = {}
    for row in source_rows_before_embargo(native, symbol):
        if row.at in wanted:
            _check_bar(row)
            available[row.at] = row

    events: list[dict[str, Any]] = []
    for entry, signal in sorted(by_event.items()):
        expiry = _at(signal["latest_exit_utc"])
        d = float(signal["stop_distance_price"])
        era = "DEVELOPMENT" if _at(signal["decision_utc"]) < DEV_END else "DIAGNOSTIC"
        if era == "DEVELOPMENT" and expiry >= DEV_END:
            strategy = control = {"status": "ERA_BOUNDARY_CENSORED"}
        else:
            strategy = arm(m5=available, entry_at=entry, expire_at=expiry,
                           distance=d, direction=signal["direction"])
            control = arm(m5=available, entry_at=entry, expire_at=expiry,
                          distance=d, direction=signal["baseline_direction"])
        paired = (strategy["status"] == control["status"] == "COMPLETE_GROSS_PROXY")
        decision = _at(signal["decision_utc"])
        iso = decision.isocalendar()
        events.append({
            "market": symbol, "era": era, "decision_utc": decision.isoformat(),
            "iso_week": f"{iso.year}-W{iso.week:02d}",
            "entry_requested_utc": entry.isoformat(),
            "strategy_direction": signal["direction"],
            "baseline_direction": signal["baseline_direction"],
            "strategy": strategy, "baseline": control,
            "paired_observed": paired,
            "paired_delta_gross_R": (
                strategy["gross_R"] - control["gross_R"] if paired else None
            ),
            "paired_delta_gross_bps": (
                strategy["gross_bps"] - control["gross_bps"] if paired else None
            ),
            "source_is_original_provider_M5": True,
            "news_PIT_filtered": False, "bidask_executable": False,
        })
    return {
        "identity": IDENTITY,
        "scope": SOURCE_GROSS_ONLY,
        "symbol": symbol, "original33_source_sha256":
        "1291d5c2efb4e51c2698ea25ad420a01a213dc405b5070c37efbce4131606b85",
        "signals_exact_immutable_sha256": SOURCE_SHA,
        "source_audit": proof, "total_original_signals": len(source_subset),
        "paired_gross_observable": sum(x["paired_observed"] for x in events),
        "events": events, "missing_events_not_suppressed": True,
        "net_certified": False, "macro_PIT_verified": False,
        "broker_costs_verified": False, "production_untouched": True,
        "2024_09_17_plus_prices_not_read": True,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("symbol", choices=MARKETS)
    p.add_argument("native", type=Path)
    p.add_argument("signed33", type=Path)
    p.add_argument("signed_signals", type=Path)
    p.add_argument("dest", type=Path)
    p.add_argument("--aggregate12", type=Path)
    x = p.parse_args()
    result = replay_symbol(x.symbol, x.native, x.signed33,
                           x.signed_signals, x.aggregate12)
    x.dest.mkdir(parents=True, exist_ok=True)
    dest = x.dest / f"alpha2-g1a-gross-{x.symbol}.json"
    dest.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    (dest.parent / (dest.name + ".sha256")).write_text(
        sha256_file(dest) + "  " + dest.name + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "symbol": x.symbol, "signals": result["total_original_signals"],
        "paired": result["paired_gross_observable"], "status": SOURCE_GROSS_ONLY,
        "net_certified": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
