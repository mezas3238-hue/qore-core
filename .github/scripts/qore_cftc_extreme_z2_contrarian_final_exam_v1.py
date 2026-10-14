"""FINAL preregistered CFTC Z>=2 extreme contrarian reference-price experiment.

This is a single one-shot exploratory family, NOT trading evidence. All CFTC
archives are pinned by SHA-256 in the predecessor runner. EIA sources are
pinned and clipped to 2012-2021 by the original EIA parser. No 2022+ values,
execution, net PnL, trader promotion, source-license assertion or real risk.
"""
from __future__ import annotations

import bisect
import hashlib
import json
import math
import statistics
import urllib.request
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from qore_futures_a_cftc_managed_money_one_shot_screen_v1 import (
    CFTC_URL,
    CONTRACT_CODES,
    DIGESTS,
    EIA_KEYS,
    CftcPosition,
    _read_cftc_archive,
)
from qore.infrastructure.trader_lab.qore_futures_a_eia_f1f2_predictive_screen_v1 import (
    read_frozen_eia_xls,
)

PREREG_SHA = "1cca3399514125ba11ae446a059e09382c605d40"
PREREG_PATH = (
    "docs/research/"
    "QORE_CFTC_EXTREME_POSITION_Z2_CONTRARIAN_SINGLE_FINAL_PREREG_2026-10-13.md"
)
Z_LOOKBACK = 104
Z_THRESHOLD = 2.0
ENTRY_LAG_CALENDAR_DAYS = 21
EXIT_HORIZON_CALENDAR_DAYS = 42
COOLDOWN_REPORTS = 8
ALPHA_PER_MARKET = 0.025
MIN_EVENTS_EACH_WINDOW = 8
MIN_EVENTS_EACH_EXTREME_SIGN = 2
MIN_REVERSAL_ACCURACY = 0.65
WINDOWS = {"dev": (date(2014, 1, 1), date(2018, 12, 31)),
           "diag": (date(2019, 1, 1), date(2021, 12, 31))}
BLACKOUTS = ((date(2013, 9, 1), date(2013, 11, 30)),
             (date(2018, 12, 1), date(2019, 4, 30)))


@dataclass(frozen=True)
class Extreme:
    report_date: date
    z: float
    sign: int  # +1 extreme net-long => expect DOWN; -1 net-short => UP
    entry_date: date
    exit_date: date
    correct_reversal: bool | None


def _z(series: list[CftcPosition], i: int) -> float | None:
    """ONLY 104 prior report values; never include observation i in baseline."""
    if i < Z_LOOKBACK:
        return None
    trailing = [entry.net_oi for entry in series[i - Z_LOOKBACK:i]]
    sigma = statistics.stdev(trailing)
    if sigma <= 0.0 or not math.isfinite(sigma):
        return None
    return (series[i].net_oi - statistics.mean(trailing)) / sigma


def _window(day: date) -> str | None:
    for name, (start, end) in WINDOWS.items():
        if start <= day <= end:
            return name
    return None


def select_events(
    positions: list[CftcPosition], prices: dict[date, float],
) -> tuple[list[Extreme], dict[str, int]]:
    """Deterministic crossed-extreme episodes, no lookahead in selection.

    Event is locked BEFORE scoring the F1 sign; even a tied outcome occupies
    the cooldown/overlap slot. Does not cherry-pick subsequent opportunities.
    """
    ordered = sorted(positions, key=lambda x: x.report_date)
    if len(set(v.report_date for v in ordered)) != len(ordered):
        raise ValueError("DUPLICATE_CFTC_REPORT")
    dates = sorted(prices)
    zvals = [_z(ordered, i) for i in range(len(ordered))]
    found: list[Extreme] = []
    counters = {
        "crossing_candidates": 0,
        "blackout_rejections": 0,
        "cooldown_rejections": 0,
        "outside_windows_or_no_reference_prices": 0,
        "zero_reference_change_excluded": 0,
        "accepted_scored_events": 0,
    }
    last_idx = -COOLDOWN_REPORTS
    last_exit: date | None = None
    for i in range(Z_LOOKBACK + 1, len(ordered)):
        value = zvals[i]
        previous = zvals[i - 1]
        if value is None or previous is None:
            continue
        sign = 0
        if value >= Z_THRESHOLD and previous < Z_THRESHOLD:
            sign = 1
        elif value <= -Z_THRESHOLD and previous > -Z_THRESHOLD:
            sign = -1
        if sign == 0:
            continue
        counters["crossing_candidates"] += 1
        day = ordered[i].report_date
        if any(a <= day <= b for a, b in BLACKOUTS):
            counters["blackout_rejections"] += 1
            continue
        if i - last_idx < COOLDOWN_REPORTS:
            counters["cooldown_rejections"] += 1
            continue
        j = bisect.bisect_left(
            dates, day + timedelta(days=ENTRY_LAG_CALENDAR_DAYS)
        )
        if j >= len(dates):
            counters["outside_windows_or_no_reference_prices"] += 1
            continue
        start = dates[j]
        k = bisect.bisect_left(
            dates, start + timedelta(days=EXIT_HORIZON_CALENDAR_DAYS)
        )
        if k >= len(dates):
            counters["outside_windows_or_no_reference_prices"] += 1
            continue
        end = dates[k]
        window = _window(day)
        if (
            window is None or _window(start) != window or _window(end) != window
        ):
            counters["outside_windows_or_no_reference_prices"] += 1
            continue
        if last_exit is not None and start <= last_exit:
            counters["cooldown_rejections"] += 1
            continue
        # LOCK episode before looking at outcome / ties.
        last_idx = i
        last_exit = end
        diff = prices[end] - prices[start]
        if diff == 0:
            counters["zero_reference_change_excluded"] += 1
            found.append(Extreme(day, value, sign, start, end, None))
            continue
        correct = diff < 0 if sign == 1 else diff > 0
        found.append(Extreme(day, value, sign, start, end, correct))
        counters["accepted_scored_events"] += 1
    return found, counters


def _one_sided_sign_p(n: int, correct: int) -> float:
    if n <= 0 or not 0 <= correct <= n:
        raise ValueError("INVALID_SIGN_TEST_COUNTS")
    return sum(math.comb(n, j) for j in range(correct, n + 1)) / (2 ** n)


def adjudicate(events: list[Extreme], window: str) -> dict[str, Any]:
    if window not in WINDOWS:
        raise ValueError("INVALID_WINDOW")
    sample = [
        x for x in events
        if _window(x.report_date) == window and x.correct_reversal is not None
    ]
    positive = sum(x.sign == 1 for x in sample)
    negative = sum(x.sign == -1 for x in sample)
    correct = sum(x.correct_reversal is True for x in sample)
    n = len(sample)
    eligible = (
        n >= MIN_EVENTS_EACH_WINDOW
        and min(positive, negative) >= MIN_EVENTS_EACH_EXTREME_SIGN
    )
    result: dict[str, Any] = {
        "n_independent_events": n,
        "long_extreme_events": positive,
        "short_extreme_events": negative,
        "correct_reversals": correct,
        "minimum_events": MIN_EVENTS_EACH_WINDOW,
        "minimum_each_extreme_sign": MIN_EVENTS_EACH_EXTREME_SIGN,
    }
    if not eligible:
        result.update({
            "accuracy": None,
            "exact_one_sided_p": None,
            "decision": "INCONCLUSIVE_INSUFFICIENT_INDEPENDENT_EXTREMES",
        })
    else:
        accuracy = correct / n
        p = _one_sided_sign_p(n, correct)
        good = accuracy >= MIN_REVERSAL_ACCURACY and p <= ALPHA_PER_MARKET
        result.update({
            "accuracy": accuracy,
            "exact_one_sided_p": p,
            "decision": "PRELIMINARY_SUPPORT" if good else "NO_SUPPORT",
        })
    return result


def run_final_examination() -> dict[str, Any]:
    weekly: dict[str, list[CftcPosition]] = {
        name: [] for name in CONTRACT_CODES
    }
    for year in sorted(DIGESTS):
        request = urllib.request.Request(
            CFTC_URL.format(year=year),
            headers={"User-Agent": "QORE-CFTC-EXTREME-FINAL-PRECOMMIT/1.0"},
        )
        with urllib.request.urlopen(request, timeout=70) as response:
            binary = response.read(30_000_001)
        parsed = _read_cftc_archive(binary, year)
        for root in weekly:
            weekly[root].extend(parsed[root])
    result: dict[str, Any] = {
        "schema": "qore.futures-a.cftc-z2-contrarian-final-exam.v1",
        "prereg_commit": PREREG_SHA,
        "historical_eia_backfill_first_published_at_verified": False,
        "native_futures_execution_data_available": False,
        "holdout_2022_2024_opened": False,
        "fx_holdout_consumed": False,
        "profit_factor_or_net_pnl_calculated": False,
        "trader_certified": False,
        "live_or_demo_enabled": False,
        "new_data_purchase_usd": 0,
        "roots": {},
    }
    results: dict[str, Any] = {}
    for root in ("NG", "WTI"):
        prices = read_frozen_eia_xls(EIA_KEYS[root])
        observed, audit = select_events(weekly[root], prices)
        dev = adjudicate(observed, "dev")
        diag = adjudicate(observed, "diag")
        results[root] = {
            "weeks_total": len(weekly[root]),
            "audit_counts": audit,
            "dev": dev,
            "diag": diag,
        }
    checks = [
        results[root][window]["decision"]
        for root in ("NG", "WTI")
        for window in ("dev", "diag")
    ]
    if all(c == "PRELIMINARY_SUPPORT" for c in checks):
        result["final_scientific_verdict"] = (
            "PRELIMINARY_REFERENCE_ASSOCIATION_NOT_TRADABLE"
        )
        result["cftc_family_qore_next_action"] = (
            "SEPARATE_ECONOMIC_AND_ASOF_SOURCE_VALIDATION_BEFORE_ANY_PROMOTION"
        )
    elif any(c.startswith("INCONCLUSIVE") for c in checks):
        result["final_scientific_verdict"] = "CLOSED_INCONCLUSIVE_LOW_POWER"
        result["cftc_family_qore_next_action"] = (
            "STOP_THIS_FAMILY_WITHOUT_UNIVERSAL_NO_EDGE_CLAIM"
        )
    else:
        result["final_scientific_verdict"] = (
            "NO_SUPPORT_FINAL_CFTC_FAMILY_FOR_QORE"
        )
        result["cftc_family_qore_next_action"] = (
            "STOP_THIS_FAMILY_NO_4_MARKET_EXTENSION_OR_RETUNING"
        )
    result["roots"] = results
    canonical = json.dumps(
        result, sort_keys=True, separators=(",", ":"), allow_nan=False
    )
    result["receipt_sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
    return result


def main() -> None:
    result = run_final_examination()
    output = Path("artifacts/research/cftc_extreme_z2_final_exam.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    for root, item in result["roots"].items():
        print("CFTC_Z2", root, "AUDIT", json.dumps(item["audit_counts"], sort_keys=True))
        for window in ("dev", "diag"):
            print("CFTC_Z2", root, window, json.dumps(item[window], sort_keys=True))
    print("CFTC_Z2_FINAL_VERDICT", result["final_scientific_verdict"])
    print("CFTC_Z2_CLOSURE", result["cftc_family_qore_next_action"])
    print("CFTC_Z2_RECEIPT_SHA256", result["receipt_sha256"])
    print("NO_ECONOMIC_EDGE_CLAIM_NO_HOLDOUT_NO_LIVE")


if __name__ == "__main__":
    main()
