#!/usr/bin/env python3
"""Frozen NAS100 M1 census of TTrades native COG's first source opportunity.

No future OHLC passes to the COG: each call receives only 09h and the 10h
CLOSED prefix. No outcomes, PnL, fills or parameter fitting are evaluated.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from collections.abc import Iterable
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import M1Bar
from scripts.vt31_ttrades_am_native_cog_v1_20261014 import (
    propose_ttrades_am_cognition,
)

NY = ZoneInfo("America/New_York")
MARKET_SHA = "0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa"
M1_TOTAL = 1059784
PREREG = "41b97b356de031bd19b7fa0ef9144841d7683254"
MODEL = "VT31_TTRADES_AM_NATIVE_COG_V1_20261014_M1_SOURCE_CENSUS"


def hash_file(path: Path) -> str:
    checksum = hashlib.sha256()
    with path.open("rb") as src:
        while chunk := src.read(2**20):
            checksum.update(chunk)
    return checksum.hexdigest()


def market_rows(path: Path) -> Iterable[dict[str, Any]]:
    import ijson

    expected = {
        "base_id": "VT31_NAS100_OWNER_3Y_BASE_001",
        "market": "NAS100",
        "base_start_at": "2023-10-01T00:00:00+00:00",
        "base_end_exclusive": "2026-10-01T00:00:00+00:00",
    }
    with path.open("rb") as inp:
        for field, value in expected.items():
            inp.seek(0)
            if next(ijson.items(inp, field), None) != value:
                raise ValueError("SOURCE_HEADER_IDENTITY_MISMATCH: " + field)
        inp.seek(0)
        yield from ijson.items(inp, "periods.M1.item")


def parse_time(raw: object) -> datetime:
    value = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("SOURCE_NAIVE_M1")
    return value.astimezone(UTC)


def collect_hours(
    rows: Iterable[dict[str, Any]], *, expected_m1: int = M1_TOTAL,
) -> tuple[dict[str, dict[int, tuple[M1Bar, ...]]], int]:
    hours: dict[str, dict[int, list[M1Bar]]] = defaultdict(
        lambda: {9: [], 10: []}
    )
    total = 0
    previous: datetime | None = None
    for row in rows:
        opened = parse_time(row["opened_at"])
        closed = parse_time(row["closed_at"])
        if closed - opened != timedelta(minutes=1):
            raise ValueError("SOURCE_NOT_EXACT_M1")
        if previous is not None and opened <= previous:
            raise ValueError("SOURCE_M1_DUPLICATE_OR_OUT_OF_ORDER")
        previous = opened
        total += 1
        ny = opened.astimezone(NY)
        if ny.hour not in (9, 10):
            continue
        bar = M1Bar(
            opened, closed,
            Decimal(str(row["open"])),
            Decimal(str(row["high"])),
            Decimal(str(row["low"])),
            Decimal(str(row["close"])),
        )
        hours[ny.date().isoformat()][ny.hour].append(bar)
    if total != expected_m1:
        raise ValueError(f"M1_EXPECTED_{expected_m1}_OBSERVED_{total}")
    return {
        day: {hour: tuple(rows) for hour, rows in blocks.items()}
        for day, blocks in hours.items()
    }, total


def complete_hour(day: str, hour: int, bars: tuple[M1Bar, ...]) -> bool:
    if len(bars) != 60:
        return False
    date = datetime.fromisoformat(day).date()
    start = datetime.combine(date, time(hour), tzinfo=NY).astimezone(UTC)
    return all(
        b.opened_at == start + timedelta(minutes=i)
        and b.closed_at == start + timedelta(minutes=i + 1)
        for i, b in enumerate(bars)
    )


def adjudicate_day(
    nine: tuple[M1Bar, ...], ten: tuple[M1Bar, ...],
) -> dict[str, Any]:
    """One day, first source return wins/blocks; no later cherry-pick."""
    latest: Any = None
    for minute in range(1, 61):
        prefix = ten[:minute]
        latest = propose_ttrades_am_cognition(
            as_of=prefix[-1].closed_at, history=nine + prefix,
        )
        # Source first-return is terminal even when QORE MSS is absent.
        if (
            latest.state in ("REJECTED", "CONTEXT_ATTESTED_NOT_CERTIFIED")
            or latest.native_state == "RETURN_INSIDE_OBSERVED"
            or "BOTH_H1_SIDES_SWEPT_UNKNOWN_INTRABAR_ORDER" in latest.reasons
        ):
            break
    assert latest is not None
    key = (
        "MSS_ATTESTED_CONTEXT_ONLY"
        if latest.state == "CONTEXT_ATTESTED_NOT_CERTIFIED"
        else "FIRST_RETURN_NO_QORE_MSS"
        if "QORE_MSS_PROXY_NOT_CONFIRMED_ON_FIRST_RETURN" in latest.reasons
        else "AMBIGUOUS_DOUBLE_SWEEP"
        if "BOTH_H1_SIDES_SWEPT_UNKNOWN_INTRABAR_ORDER" in latest.reasons
        else "REJECTED_SOURCE"
        if latest.state == "REJECTED"
        else "NO_SWEEP"
        if latest.native_state == "AWAIT_SWEEP"
        else "SWEEP_NO_RETURN"
        if latest.native_state == "AWAIT_RETURN"
        else "UNKNOWN_SOURCE"
    )
    return {
        "classification": key,
        "as_of": latest.as_of.isoformat(),
        "native_state": latest.native_state,
        "reasons": list(latest.reasons),
        "has_source_cognitive_proposal": latest.decision is not None,
        "side": (
            latest.decision.side.value if latest.decision is not None else None
        ),
        "dol_family": (
            latest.decision.draw_family if latest.decision is not None else None
        ),
        "method_certified": False,
        "execution_authorized": False,
    }


def run_census(
    groups: dict[str, dict[int, tuple[M1Bar, ...]]],
) -> dict[str, Any]:
    counts: Counter[str] = Counter()
    rows: list[dict[str, Any]] = []
    for day, hours in sorted(groups.items()):
        nine, ten = hours.get(9, ()), hours.get(10, ())
        if not complete_hour(day, 9, nine) or not complete_hour(day, 10, ten):
            result = {
                "classification": "INCOMPLETE_M1_HOURS",
                "has_source_cognitive_proposal": False,
                "method_certified": False,
                "execution_authorized": False,
            }
        else:
            result = adjudicate_day(nine, ten)
        counts[result["classification"]] += 1
        rows.append({"ny_day": day, **result})
    assert sum(counts.values()) == len(groups)
    candidates = counts["MSS_ATTESTED_CONTEXT_ONLY"]
    assert sum(int(x["has_source_cognitive_proposal"]) for x in rows) == candidates
    return {
        "model": MODEL,
        "data_identity": "NAS100_CFD_3Y_DEVELOPMENT_NOT_FRESH_HOLDOUT",
        "market_sha256": MARKET_SHA,
        "preregistered_document_commit": PREREG,
        "observed_days_total": len(rows),
        "state_counts": dict(sorted(counts.items())),
        "M2_M3_context_only_candidates_not_trades": candidates,
        "source_classifications": rows,
        "historical_development_not_independent_holdout": True,
        "economic_PF_drawdown_sharpe": None,
        "quotes_bid_ask_order_ACK_count": 0,
        "trader_certified": False,
        "live_authorized": False,
        "no_sizing_and_no_future_outcomes": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--market", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if hash_file(args.market) != MARKET_SHA:
        raise ValueError("FROZEN_M1_SHA256_MISMATCH")
    groups, total = collect_hours(market_rows(args.market))
    report = run_census(groups)
    report["market_m1_count"] = total
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        k: report[k] for k in (
            "model", "market_m1_count", "observed_days_total",
            "state_counts", "M2_M3_context_only_candidates_not_trades",
        )
    }, sort_keys=True))


if __name__ == "__main__":
    main()
