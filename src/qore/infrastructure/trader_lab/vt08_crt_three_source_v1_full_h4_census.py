"""No-PnL, no-sizing census of all complete UTC H4 C1/C2 windows.

See the preregistered Owner tri-source research protocol dated 2026-10-15.
No legacy two-triplets-per-day or casebook stratum selection is applied.
C3 future bars are NOT used for eligibility; only first 30 min can be read.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.vt08_crt_pure_2y_replay import ReplayBar
from qore.infrastructure.trader_lab.vt08_crt_pure_original_atlas_reader import (
    load_atlas_vt08_m5,
)
from qore.infrastructure.trader_lab.vt08_crt_three_source_candidate_v1 import (
    _direction,
    evaluate_three_source_case,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket

H4 = timedelta(hours=4)
M5 = timedelta(minutes=5)
SCHEMA = "qore.vt08.crt_three_source_v1.full_utc_h4_development_census.v1"


def _bar_payload(bar: ReplayBar) -> dict[str, Any]:
    return {
        "opened_at_utc": bar.opened_at.astimezone(UTC).isoformat(),
        "open_relative": bar.open_price,
        "high_relative": bar.high_price,
        "low_relative": bar.low_price,
        "close_relative": bar.close_price,
    }


def _aggregate(rows: tuple[ReplayBar, ...]) -> dict[str, Any]:
    if not rows:
        raise ValueError("empty OHLC")
    first = _bar_payload(rows[0])
    first["high_relative"] = max(b.high_price for b in rows)
    first["low_relative"] = min(b.low_price for b in rows)
    first["close_relative"] = rows[-1].close_price
    return first


def _h4_floor(t: datetime) -> datetime:
    utc = t.astimezone(UTC)
    return utc.replace(hour=utc.hour - utc.hour % 4, minute=0, second=0, microsecond=0)


def full_utc_h4_census(
    market: CrtPureMarket,
    bars: tuple[ReplayBar, ...],
) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    if market not in (CrtPureMarket.AUDUSD, CrtPureMarket.USDJPY):
        raise ValueError("BTCUSD frozen / unexpected market")
    if not bars:
        raise ValueError("missing original Atlas M5")
    m5: dict[datetime, ReplayBar] = {}
    h4_starts: set[datetime] = set()
    for bar in bars:
        if bar.opened_at.tzinfo is None:
            raise ValueError("M5 clock requires timezone")
        opened = bar.opened_at.astimezone(UTC)
        if opened in m5:
            raise ValueError("duplicate source M5 timestamp")
        m5[opened] = bar
        h4_starts.add(_h4_floor(opened))
    h4: dict[datetime, dict[str, Any]] = {}
    for start in sorted(h4_starts):
        samples = tuple(m5.get(start + i * M5) for i in range(48))
        if any(sample is None for sample in samples):
            continue
        h4[start] = _aggregate(tuple(s for s in samples if s is not None))
    rows: list[dict[str, Any]] = []
    status = Counter[str]()
    per_year: dict[str, Counter[str]] = defaultdict(Counter)
    for h4_c2_started in sorted(h4):
        c1_started = h4_c2_started - H4
        if c1_started not in h4:
            continue
        c3_started = h4_c2_started + H4
        c1, c2 = h4[c1_started], h4[h4_c2_started]
        source_direction = _direction(c1, c2)
        year = str(c3_started.year)
        row: dict[str, Any] = {
            "market": market.value,
            "parent_H4_c3_opened_at_utc": c3_started.isoformat(),
            "year_utc": year,
            "source_direction": source_direction,
            "first30_clock_utc": (c3_started + timedelta(minutes=30)).isoformat(),
            "conceptual_state": "ABSTAIN",
            "why": "H4_NO_ONE_SIDE_PURGE_RECLAIM",
            "research_only": True,
            "not_fresh_holdout": True,
            "not_a_trade": True,
        }
        if source_direction is not None:
            first_six = tuple(m5.get(c3_started + i * M5) for i in range(6))
            if any(item is None for item in first_six):
                row["conceptual_state"] = "WAIT"
                row["why"] = "M15_PREFIX_MISSING_FIRST30"
            else:
                six = tuple(item for item in first_six if item is not None)
                m15_c1 = _aggregate(six[:3])
                m15_c2 = _aggregate(six[3:])
                token = f"{market.value}|{c3_started.isoformat()}|V1"
                case = {
                    "schema": "qore.vt08.crt_pure.gm2_real_blinded_casebook.v1",
                    "case_id": hashlib.sha256(token.encode()).hexdigest()[:20],
                    "market": market.value,
                    "parent_H4_direction_context": source_direction,
                    "parent_H4_c3_opened_at_utc": c3_started.isoformat(),
                    "parent_H4_C1_ohlc": c1,
                    "parent_H4_C2_ohlc": c2,
                    "M15_observed_prefix_through_C2": [m15_c1, m15_c2],
                    "decision_clock_utc": (c3_started + timedelta(minutes=30)).isoformat(),
                    "reference_level_selection": "UNRESOLVED_BY_PRIMARY_SOURCE",
                    "author_model1_equivalence": "NOT_ADJUDICATED",
                    "is_execution_authorized": False,
                    "not_new_holdout": True,
                    "future_C3_withheld_from_blind_file": True,
                }
                outcome = evaluate_three_source_case(case)
                row["conceptual_state"] = outcome["conceptual_state"]
                row["why"] = outcome["why"]
                row["case_id"] = outcome["case_id"]
                row["not_trading_signal"] = outcome["not_trading_signal"]
        status[row["conceptual_state"]] += 1
        per_year[year][row["conceptual_state"]] += 1
        rows.append(row)
    if not rows:
        raise ValueError("no complete previous H4 parent pairs for census")
    if len({r["parent_H4_c3_opened_at_utc"] for r in rows}) != len(rows):
        raise ValueError("multiple claims to one H4 C3 event")
    summary = {
        "schema": SCHEMA,
        "market": market.value,
        "original_m5": len(bars),
        "complete_utc_h4": len(h4),
        "complete_h4_c1_c2_contexts": len(rows),
        "conceptual_states": dict(sorted(status.items())),
        "by_year": {
            year: dict(sorted(counts.items()))
            for year, counts in sorted(per_year.items())
        },
        "time_policy": "UTC_00_04_08_12_16_20_QORE_PREREG",
        "historical_data_used_before": True,
        "not_fresh_holdout": True,
        "sampled_by_future_C3": False,
        "PnL_computed": False,
        "sizing_used": False,
        "trading_orders": False,
        "economics_certified": False,
        "methodology_certified": False,
        "global_certified": False,
    }
    return summary, tuple(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("market", choices=("AUDUSD", "USDJPY"))
    ap.add_argument("atlas_root", type=Path)
    ap.add_argument("output", type=Path)
    args = ap.parse_args()
    market = CrtPureMarket(args.market)
    bars, provenance = load_atlas_vt08_m5(market, args.atlas_root)
    manifest, rows = full_utc_h4_census(market, bars)
    manifest["atlas_provenance"] = provenance
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "three-source-v1-h4-full-summary.json").write_text(
        json.dumps(manifest, sort_keys=True, indent=2) + "\n"
    )
    with (args.output / "three-source-v1-h4-full-ledger.jsonl").open("w") as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=True) + "\n")
    print(json.dumps({
        k: v for k, v in manifest.items() if k != "atlas_provenance"
    }, sort_keys=True))


if __name__ == "__main__":
    main()
