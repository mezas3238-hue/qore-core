"""VT08 B R10: independent, as-of three-H1 context INCLUDING current H1.

Original TTrades Relevant Swings proposes 3 HTF candles including current.
A R7 instead examines three completely closed pre-C2 H1. This B evidence
compares those PHYSICAL observation windows, never infers author relevance.
A provisional current H1 is NOT a completed candle or a tradable signal.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.trader_lab.vt08_5m_b_independent_raw_receipts_v1 import (
    _instant,
    _prices,
    _raw_bars,
)

SCHEMA = "qore.vt08.b.r10.three_h1_including_current_causal_source.v1"
JOIN_SCHEMA = "qore.vt08.a.blind_three_source_review_join.v1"
SOURCE = "https://ttrades.com/relevant-swings-which-swing-highs-and-lows-matter-in-trading/"
M15 = timedelta(minutes=15)
HOUR = timedelta(hours=1)
PINNED_M15 = {
    "EURJPY": "565c1f93f31ee100f07ec4aa5b058c4a2b6f1600bc7980989720589c198d5047",
    "USDCHF": "1b8541c1dc8358200a1a0d77d6a6f3df97c86b9a2b3400e7425a59c6bb12f464",
    "NZDUSD": "77a9c599f6f22c7353ded3a76ce18ced2bd2e3e5c8badfac6dfa4c3b228a99cb",
    "CADJPY": "e598cab241aa183cd9661d6939978322b1f8a9959a82c6bb409d5e2c374d44f4",
    "USDCAD": "6a47a292f4eb3c7b35c5510602d37763edbf90b122e276a298379b2b4e53ea93",
}


def _bar_sha(row: Mapping[str, object], sha: str) -> str:
    opened = _instant(row.get("opened_at"))
    closed = _instant(row.get("closed_at"))
    if closed != opened + M15:
        raise ValueError("VT08 R10 M15 duration mismatch")
    ohlc = tuple(str(row.get(k)) for k in ("open", "high", "low", "close"))
    _prices(ohlc)
    payload = {
        "profile": "M15", "source_raw_sha256": sha,
        "opened_at_utc": opened.isoformat(),
        "closed_at_utc": closed.isoformat(), "ohlc": ohlc,
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _window(
    raw: Mapping[datetime, Mapping[str, object]],
    sha: str,
    start: datetime,
    end: datetime,
) -> dict[str, object] | None:
    if end < start or (end - start) % M15 != timedelta(0):
        raise ValueError("VT08 R10 invalid observation cutoff")
    receipts: list[str] = []
    prices: list[tuple[Decimal, Decimal, Decimal, Decimal]] = []
    count = int((end - start) / M15)
    for i in range(count):
        clock = start + i * M15
        candle = raw.get(clock)
        if candle is None or _instant(candle.get("closed_at")) != clock + M15:
            return None  # Quarantine gaps; never fill with assumptions.
        prices.append(_prices(tuple(str(candle.get(k)) for k in (
            "open", "high", "low", "close",
        ))))
        receipts.append(_bar_sha(candle, sha))
    if count == 0:
        return {"bars_closed": 0, "bar_ids": [], "ohlc": None}
    return {
        "bars_closed": count, "bar_ids": receipts,
        "ohlc": [
            str(prices[0][0]), str(max(p[1] for p in prices)),
            str(min(p[2] for p in prices)), str(prices[-1][3]),
        ],
    }


def _pivot(
    older: Mapping[str, object] | None,
    previous: Mapping[str, object] | None,
    current: Mapping[str, object] | None,
) -> bool | None:
    if not older or not previous or not current or not current.get("bars_closed"):
        return None
    a, b, c = (x.get("ohlc") for x in (older, previous, current))
    if not isinstance(a, list) or not isinstance(b, list) or not isinstance(c, list):
        return None
    return Decimal(str(b[2])) < min(Decimal(str(a[2])), Decimal(str(c[2])))


def reconstruct_current_h1_context(
    joined: Mapping[str, object], *, market: str, m15_file: Path,
) -> dict[str, object]:
    """Inspect the complete frozen R7 source universe, outcomes strictly absent."""
    if joined.get("schema") != JOIN_SCHEMA or joined.get("market") != market:
        raise ValueError("VT08 R10 foreign R7 identity")
    if (
        joined.get("source_complete_entries") != 0
        or joined.get("broker_fills") != 0
        or joined.get("profit_factor") is not None
        or joined.get("signed_A_B_manifest") is not None
        or joined.get("certified") is not False
    ):
        raise ValueError("VT08 R10 false certified/PnL R7 input")
    sha, raw = _raw_bars(m15_file, "M15", market)
    if sha != PINNED_M15.get(market):
        raise ValueError("VT08 R10 original market M15 SHA not pinned")
    cases = joined.get("all_source_only_cases")
    if (
        not isinstance(cases, list) or not cases
        or len(cases) != joined.get("frozen_event_count")
    ):
        raise ValueError("VT08 R10 incomplete frozen R7 candidate inventory")
    seen: set[tuple[datetime, datetime]] = set()
    totals: Counter[str] = Counter()
    receipts: list[dict[str, object]] = []
    for case in cases:
        if not isinstance(case, dict) or case.get("market") != market:
            raise ValueError("VT08 R10 cross-market event")
        c2 = _instant(case.get("c2_opened_at_utc"))
        c3 = _instant(case.get("decision_at_utc"))
        key = (c2, c3)
        if key in seen or c3 != c2 + timedelta(minutes=30):
            raise ValueError("VT08 R10 repeated/future decision identity")
        seen.add(key)
        if c2.minute not in (0, 30) or c2.second or c2.microsecond:
            raise ValueError("VT08 R10 unapproved C2 clock")
        source_id = hashlib.sha256(
            (market + "|" + c2.isoformat() + "|" + c3.isoformat()).encode()
        ).hexdigest()
        if case.get("case_id_sha256") != source_id:
            raise ValueError("VT08 R10 R7 source identity checksum drift")
        h = c2.replace(minute=0, second=0, microsecond=0)
        closed_prior_three = _window(raw, sha, h - 3 * HOUR, h)
        older = _window(raw, sha, h - 2 * HOUR, h - HOUR)
        previous = _window(raw, sha, h - HOUR, h)
        current_asof_c2 = _window(raw, sha, h, c2)
        current_asof_c3 = _window(raw, sha, h, c3)
        # Old R7 rule checks three completely closed H1, while TTrades text
        # describes 3 HTF INCLUDING current. Both are physical diagnostics.
        r7_complete = case.get("pre_c2_three_h1_physically_complete")
        if not isinstance(r7_complete, bool) or (
            (closed_prior_three is not None) != r7_complete
        ):
            raise ValueError("VT08 R10 prior-three-H1 native vs R7 mismatch")
        if (older is None) != (previous is None):
            totals["partially_missing_previous_two"] += 1
        prior_two_complete = older is not None and previous is not None
        c2_count = current_asof_c2["bars_closed"] if current_asof_c2 else None
        c3_count = current_asof_c3["bars_closed"] if current_asof_c3 else None
        if c2_count not in (0, 2, None) or c3_count not in (2, 4, None):
            raise ValueError("VT08 R10 invalid partial H1 observability")
        totals["events"] += 1
        totals["r7_closed_three_available"] += int(r7_complete)
        totals["prior_two_h1_available"] += int(prior_two_complete)
        totals["current_h1_empty_at_c2"] += int(c2_count == 0)
        totals["current_h1_partial_at_c2"] += int(c2_count == 2)
        totals["current_h1_partial_at_c3"] += int(c3_count == 2)
        totals["current_h1_fully_closed_at_c3"] += int(c3_count == 4)
        totals["current_h1_missing_at_c3"] += int(c3_count is None)
        p2 = _pivot(older, previous, current_asof_c2)
        p3 = _pivot(older, previous, current_asof_c3)
        totals["basic_low_pivot_observable_at_c2"] += int(p2 is True)
        totals["basic_low_pivot_observable_at_c3"] += int(p3 is True)
        totals["basic_low_pivot_at_c3_still_provisional"] += int(
            p3 is True and c3_count == 2
        )
        totals["basic_low_pivot_at_c3_current_h1_complete"] += int(
            p3 is True and c3_count == 4
        )
        receipts.append({
            "market": market, "c2_opened_at_utc": c2.isoformat(),
            "decision_at_utc": c3.isoformat(), "case_id_sha256": source_id,
            "old_r7_basic_low_pivot": case.get("basic_bullish_h1_pivot") is True,
            "old_r7_three_h1_closed": r7_complete,
            "previous_two_h1_complete": prior_two_complete,
            "older_h1": older, "previous_h1": previous,
            "current_h1_asof_c2": current_asof_c2,
            "current_h1_asof_c3": current_asof_c3,
            "pivot_three_including_current_asof_c2": p2,
            "pivot_three_including_current_asof_c3": p3,
            "source_relevant_swing_selected": False,
            "valid_separation_adjudicated": False,
            "author_target_or_entry_selected": False,
        })
    if len(receipts) != len(seen) or totals["events"] != len(cases):
        raise ValueError("VT08 R10 source conservation failed")
    return {
        "schema": SCHEMA, "market": market,
        "source_article": SOURCE,
        "native_m15_sha256": sha,
        "frozen_source_events": len(receipts),
        "counts": dict(totals),
        "all_source_only_witnesses": receipts,
        "interpretation": "PHYSICAL_PARTIAL_CURRENT_H1_NOT_SOURCE_RELEVANCE",
        "author_relevant_swing_certified": False,
        "source_complete_entries": 0,
        "cognitive_admission_authorized": False,
        "broker_fills": 0, "profit_factor": None,
        "holdout_7y_accessed": False, "sizing_used": False,
    }
