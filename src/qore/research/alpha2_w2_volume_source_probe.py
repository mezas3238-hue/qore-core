"""QORE Alpha2 W2 native tick-activity source coverage, pre-price feasibility.

No OHLC access, returns, labels, PnL or orders. Four frozen symbols only.
Verify original 11-part RAW+quality source SHA before opening annual rows.
"""
from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from statistics import median
from typing import Any

from qore.research.alpha2_lab_h4_extract import source33_manifest, verify_source

PILOT = ("NAS100", "XAUUSD", "EURUSD", "EURCHF")
CUTOFF = datetime(2024, 9, 17, tzinfo=UTC)
SCHEMA = "QORE_ALPHA2_W2_PILOT_NATIVE_VOLUME_SOURCE_ONLY_V1"


def classify_activity(value: object) -> str:
    if value is None:
        return "NULL"
    if type(value) is not int:
        return "NON_INTEGER"
    if value < 0:
        return "NEGATIVE"
    if value == 0:
        return "ZERO"
    return "POSITIVE"


def pilot(
    symbol: str, original_root: Path, signed33: Path,
    aggregate12: Path | None,
) -> dict[str, Any]:
    if symbol not in PILOT:
        raise ValueError("outside owner-frozen W2 SOURCE four-market pilot")
    frozen = source33_manifest(signed33)
    proof = verify_source(symbol, original_root, frozen, aggregate12)
    per_year: dict[str, dict[str, Any]] = {}
    total_categories: Counter[str] = Counter()
    source_bars = 0
    previous: datetime | None = None
    for year in range(2016, 2025):
        ledger = original_root / "RAW_M5_LEDGER" / f"{year}.jsonl"
        category_counts: Counter[str] = Counter()
        positives: list[int] = []
        n = 0
        with ledger.open(encoding="utf-8") as handle:
            for line in handle:
                # Parse metadata fields only. NEVER reference open/high/low/close.
                row = json.loads(line)
                t = datetime.fromisoformat(row["opened_at"])
                if t.tzinfo is None or t.utcoffset() is None:
                    raise ValueError("original provider timestamp must be aware")
                t = t.astimezone(UTC)
                if t >= CUTOFF:
                    continue
                if (previous is not None and t <= previous) or t.minute % 5:
                    raise ValueError("original native M5 ordering invalid")
                previous = t
                n += 1
                cls = classify_activity(row.get("volume"))
                category_counts[cls] += 1
                total_categories[cls] += 1
                if cls == "POSITIVE":
                    positives.append(row["volume"])
        source_bars += n
        per_year[str(year)] = {
            "m5_rows_pre_embargo": n,
            "category_counts": {
                label: category_counts[label]
                for label in ("NULL", "ZERO", "POSITIVE", "NEGATIVE", "NON_INTEGER")
            },
            "positive_volume_median": float(median(positives)) if positives else None,
            "max_positive_volume": max(positives, default=None),
        }
    if source_bars <= 0 or sum(total_categories.values()) != source_bars:
        raise ValueError("W2 source volume census rows did not reconcile")
    return {
        "identity": SCHEMA,
        "market": symbol,
        "source": proof,
        "original_m5_count_all_years": proof["m5_bars_verified"],
        "m5_rows_pre_embargo": source_bars,
        "categories": dict(sorted(total_categories.items())),
        "per_year": per_year,
        "sample_rule": "FOUR_PRESELECTED_SOURCES_BEFORE_W2_PRICE_OR_PNL",
        "broker_volume_semantics": "PROVIDER_VOLUME_SEMANTICS_UNVERIFIED",
        "ohlc_fields_accessed": False,
        "price_returns_or_PnL_read": False,
        "after_2024_09_17_OHLC_unread": True,
        "profitability_claim": False,
        "broker_bidask_costs_verified": False,
        "certified": False,
        "production_untouched": True,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("symbol", choices=PILOT)
    p.add_argument("original_provider", type=Path)
    p.add_argument("signed33", type=Path)
    p.add_argument("destination", type=Path)
    p.add_argument("--aggregate12", type=Path)
    opts = p.parse_args()
    result = pilot(opts.symbol, opts.original_provider, opts.signed33, opts.aggregate12)
    opts.destination.mkdir(parents=True, exist_ok=True)
    dest = opts.destination / f"alpha2-w2-volume-source-{opts.symbol}.json"
    dest.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "market": result["market"], "source_rows": result["m5_rows_pre_embargo"],
        "categories": result["categories"],
        "provider_volume_semantics": result["broker_volume_semantics"],
        "ohlc_or_PnL_read": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
