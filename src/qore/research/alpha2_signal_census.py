"""QORE Alpha2 signal-density census from signed research ledger: NO PnL."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from qore.research.alpha2_intermarket import MARKETS, sha256_file

SOURCE_RUN = 38268654596
SOURCE_HEAD = "a0841226934f1140817a52db72c47141623a8aa4"
SOURCE_SHA = "604702839117423c08057e9348a97b0899c2db92f1e1d6daf92d9480e6217f22"
NAME = "alpha2-patr-33-signal-ledger-research-only.json"


def census(root: Path) -> dict:
    path = root / NAME
    if sha256_file(path) != SOURCE_SHA:
        raise ValueError("first full33 ultra-fast signal ledger SHA mismatch")
    if (root / "exact-code-head-sha.txt").read_text(encoding="utf-8").strip() != SOURCE_HEAD:
        raise ValueError("source exact head mismatch")
    record = json.loads(path.read_text(encoding="utf-8"))
    if (record.get("identity") != "QORE_ALPHA2_PATR_SHA33_ULTRAFAST_RESEARCH_LEDGER_V1"
            or record.get("universe") != sorted(MARKETS)
            or record.get("number_of_signals") != 224
            or record.get("source33_sha256") !=
            "1291d5c2efb4e51c2698ea25ad420a01a213dc405b5070c37efbce4131606b85"
            or record.get("broker_orders") != 0
            or record.get("gross_or_net_PnL_calculated") is not False
            or record.get("utc001_certified") is not False):
        raise ValueError("original signed PATR 33-ledger flags/identity invalid")
    rows = record["signals"]
    if not isinstance(rows, list) or len(rows) != 224:
        raise ValueError("source ledger count inconsistent")
    counts = {symbol: 0 for symbol in sorted(MARKETS)}
    annual: Counter[str] = Counter()
    weekly: Counter[str] = Counter()
    by_era: Counter[str] = Counter()
    donor_count: Counter[str] = Counter()
    clashes: Counter[str] = Counter()
    seen: set[tuple[str, str]] = set()
    years_by_symbol: dict[str, Counter[str]] = {s: Counter() for s in sorted(MARKETS)}
    for r in rows:
        symbol = r["symbol"]
        t = datetime.fromisoformat(r["decision_utc"])
        if symbol not in counts or t.tzinfo is None or t.utcoffset() != UTC.utcoffset(None):
            raise ValueError("invalid symbol/UTC")
        if not datetime(2016, 9, 17, tzinfo=UTC) <= t < datetime(2024, 9, 17, tzinfo=UTC):
            raise ValueError("signal outside consumed dev and diagnostic years")
        key = (symbol, r["bar_start_utc"])
        if key in seen:
            raise ValueError("duplicate event")
        seen.add(key)
        era = "DEVELOPMENT" if t < datetime(2022, 9, 17, tzinfo=UTC) else "DIAGNOSTIC"
        week = t.isocalendar()
        counts[symbol] += 1
        years_by_symbol[symbol][str(t.year)] += 1
        annual[str(t.year)] += 1
        weekly[f"{week.year}-W{week.week:02d}"] += 1
        by_era[era] += 1
        donors = r["donors"]
        if len(donors) < 5 or symbol in donors or len(set(donors)) != len(donors):
            raise ValueError("unacceptable donor set")
        for donor in donors:
            donor_count[donor] += 1
        clashes[r["decision_utc"]] += 1
    return {
        "identity": "QORE_ALPHA2_33_SIGNAL_DENSITY_NO_PNL_V1",
        "source_run": SOURCE_RUN,
        "source_head": SOURCE_HEAD,
        "source_ledger_sha256": SOURCE_SHA,
        "signals_total": len(rows), "markets": len(MARKETS),
        "symbols_all_reported_including_zero": counts,
        "calendar_year": dict(sorted(annual.items())),
        "eras": dict(sorted(by_era.items())),
        "calendar_weeks_with_signals": len(weekly),
        "calendar_weeks_with_multiple_signals": sum(v > 1 for v in weekly.values()),
        "max_signals_same_week": max(weekly.values(), default=0),
        "max_simultaneous_decisions_same_timestamp": max(clashes.values(), default=0),
        "donor_usage_counts": dict(sorted(donor_count.items())),
        "per_symbol_by_year": {s:dict(sorted(y.items())) for s,y in years_by_symbol.items()},
        "utc001_sample_sufficiency": "NOT_EVALUATED_NO_DEFENSIBLE_POWER_YET",
        "gross_net_PnL": "NOT_COMPUTED",
        "market_year_zero_signal_cells": sum(
            years_by_symbol[s].get(str(y),0)==0 for s in MARKETS for y in range(2017,2024)
        ),
        "original_holdout_untouched": True,
        "costs_and_news_PIT_unverified": True,
        "trader_certified": False,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("source_artifact", type=Path)
    p.add_argument("destination", type=Path)
    x = p.parse_args()
    result = census(x.source_artifact)
    x.destination.mkdir(parents=True, exist_ok=True)
    target = x.destination / "alpha2-33-signal-density-source-only.json"
    target.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["identity"], "signals": result["signals_total"],
                      "by_era": result["eras"], "years": result["calendar_year"],
                      "weekly_clusters": result["calendar_weeks_with_signals"],
                      "zero_market_year_cells": result["market_year_zero_signal_cells"]},
                     sort_keys=True))


if __name__ == "__main__":
    main()
