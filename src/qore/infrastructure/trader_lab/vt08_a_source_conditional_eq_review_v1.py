"""VT08 TTrades C2 EQ source-conditioned *arithmetic witnesses* for B review.

Physical OHLC parity from A/B raw catalog, NOT relevant-swing selection,
not source-authorized EQ regime, breaker, stop, target, fills or PnL.
All 2,657 frozen C2 structural precursor cases are processed without
sampling by outcomes. The author uses full candle EQ when C2 closes
WITH an authenticated bullish swing, and close-to-low EQ when against.
No prior swing identity is inferred from a generic three-H1 geometry.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Final

EQ_SOURCE: Final = (
    "https://ttrades.com/how-to-use-equilibrium-eq-ttrades-fractal-model/"
)
SWING_SOURCE: Final = (
    "https://ttrades.com/relevant-swings-which-swing-highs-and-lows-matter-in-trading/"
)
SOURCE_SCHEMA: Final = "qore.vt08.a_b.market_raw_custody_catalog.v1"
SCHEMA: Final = "qore.vt08.a.author_eq_conditional_review.v1"


def _utc(s: object) -> datetime:
    if not isinstance(s, str):
        raise ValueError("missing physical bar timestamp")
    try:
        t = datetime.fromisoformat(s)
    except ValueError as exc:
        raise ValueError("invalid physical bar timestamp") from exc
    if t.utcoffset() is None:
        raise ValueError("naive physical bar timestamp")
    return t.astimezone(UTC)


def _ohlc(raw: Mapping[str, object]) -> tuple[Decimal, ...]:
    values = raw.get("ohlc")
    if not isinstance(values, (tuple, list)) or len(values) != 4:
        raise ValueError("physical OHLC tuple invalid")
    try:
        v = tuple(Decimal(str(x)) for x in values)
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("physical OHLC numeric conversion invalid") from exc
    if any(not n.is_finite() or n <= 0 for n in v):
        raise ValueError("non-finite source OHLC")
    if v[2] > min(v[0], v[3]) or v[1] < max(v[0], v[3]):
        raise ValueError("impossible OHLC")
    return v


def _m30(
    catalog: Mapping[str, object],
    ids: list[str],
    *,
    profile: str,
    start: datetime,
    n: int,
    step: int,
) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    if len(ids) != n or len(set(ids)) != n:
        raise ValueError("missing/duplicate M30 constituent bars")
    bars: list[tuple[Decimal, ...]] = []
    for i, key in enumerate(ids):
        raw = catalog.get(key)
        if not isinstance(raw, dict) or raw.get("profile") != profile:
            raise ValueError("missing authenticated expected-profile bar")
        at = _utc(raw.get("opened_at_utc"))
        closed = _utc(raw.get("closed_at_utc"))
        if at != start + timedelta(minutes=step * i):
            raise ValueError("noncontiguous source bars")
        if closed != at + timedelta(minutes=step):
            raise ValueError("wrong physical source duration")
        bars.append(_ohlc(raw))
    return (
        bars[0][0],
        max(candle[1] for candle in bars),
        min(candle[2] for candle in bars),
        bars[-1][3],
    )


def conditional_eq_witnesses(
    source_catalog: Mapping[str, object],
) -> dict[str, object]:
    """All source-only events: authenticated C2 OHLC, no semantic promotion.

    Caller must furnish A's physical-custody artifact. B must independently
    rehash its underlying M3/M15 source and judge swing/POI before acting.
    """
    if source_catalog.get("schema") != SOURCE_SCHEMA:
        raise ValueError("expected frozen source-catalog schema")
    if any(source_catalog.get(x) is not False for x in (
        "author_fidelity_certified",
        "cognitive_certified",
        "economic_gates_certified",
        "pnl_evaluated",
    )):
        raise ValueError("source-only catalog cannot claim certified evidence")
    if source_catalog.get("orders") != 0 or source_catalog.get("fills") != 0:
        raise ValueError("source-only catalog cannot contain orders or fills")
    market = source_catalog.get("market")
    raw_market = source_catalog.get("source_raw_market_map")
    pinned = source_catalog.get("pinned_raw_shas")
    if (
        not isinstance(market, str)
        or not isinstance(raw_market, dict)
        or not isinstance(pinned, list)
        or set(raw_market) != set(pinned)
        or len(pinned) != 2
        or any(x != market for x in raw_market.values())
    ):
        raise ValueError("physical market to SHA custody mismatch")
    bars = source_catalog.get("bar_catalog")
    events = source_catalog.get("source_only_events")
    if not isinstance(bars, dict) or not isinstance(events, list):
        raise ValueError("missing physical source BAR/CASE catalog")
    if source_catalog.get("source_only_event_count") != len(events):
        raise ValueError("frozen source case inventory incomplete")
    observed: list[dict[str, object]] = []
    seen_decisions: set[str] = set()
    h1_incomplete = 0
    for event in events:
        if not isinstance(event, dict) or event.get("market") != market:
            raise ValueError("cross-market source event")
        if event.get("source_complete") is not False:
            raise ValueError("false claim of author completeness")
        decision = _utc(event.get("decision_at_utc"))
        c2_open = _utc(event.get("c2_opened_at_utc"))
        if decision != c2_open + timedelta(minutes=30):
            raise ValueError("C2 complete future was consumed too early")
        if decision.isoformat() in seen_decisions:
            raise ValueError("duplicate source decision")
        seen_decisions.add(decision.isoformat())
        sources = event.get("source_bar_groups")
        if not isinstance(sources, dict):
            raise ValueError("source groups missing")
        m3_ids = sources.get("c2_m3_raw_bar_receipts")
        m15_ids = sources.get("c2_m15_raw_bar_receipts")
        if not isinstance(m3_ids, list) or not isinstance(m15_ids, list):
            raise ValueError("M3/M15 source ids required")
        m3 = _m30(bars, m3_ids, profile="M3", start=c2_open, n=10, step=3)
        m15 = _m30(bars, m15_ids, profile="M15", start=c2_open, n=2, step=15)
        if m3 != m15:
            raise ValueError("native M3/M15 C2 physical OHLC mismatch")
        op, high, low, close = m3
        if not (low < op < high and low < close < high and close > op):
            raise ValueError("not the frozen bullish C2 reversal family")
        prior_h1 = sources.get("pre_c2_h1_m15_raw_bar_receipts")
        if not isinstance(prior_h1, list):
            raise ValueError("missing H1 provenance group")
        if prior_h1:
            if len(prior_h1) != 12:
                raise ValueError("incomplete prior H1 provenance group")
            h1_end = c2_open.replace(minute=0, second=0, microsecond=0)
            h1_start = h1_end - timedelta(hours=3)
            # Re-attest source clocks but never treat three H1 as the
            # author-selected valid swing.
            for i, key in enumerate(prior_h1):
                raw = bars.get(key)
                if not isinstance(raw, dict) or raw.get("profile") != "M15":
                    raise ValueError("H1 context is not original M15 physical source")
                if _utc(raw.get("opened_at_utc")) != h1_start + timedelta(minutes=15 * i):
                    raise ValueError("H1 bar future/noncontiguous")
                if _utc(raw.get("closed_at_utc")) > c2_open:
                    raise ValueError("H1 context reads from C2 future")
        else:
            h1_incomplete += 1
        observed.append({
            "market": market,
            "c2_opened_at_utc": c2_open.isoformat(),
            "decision_at_utc": decision.isoformat(),
            "c2_source_m3_bar_ids": m3_ids,
            "c2_source_m15_bar_ids": m15_ids,
            "prior_h1_context_source_ids": prior_h1,
            "prior_h1_context_available": len(prior_h1) == 12,
            "c2_open": str(op),
            "c2_high": str(high),
            "c2_low": str(low),
            "c2_close": str(close),
            "eq_if_prior_bullish_swing_source_valid_with_close": str(
                (high + low) / Decimal(2)
            ),
            "eq_if_prior_bullish_swing_valid_but_close_against": str(
                (close + low) / Decimal(2)
            ),
            "actual_frozen_c2_body_direction": "BULLISH",
            "eq_swing_identity_author_adjudicated": False,
            "eq_selection_authorized": False,
            "poi_significance_author_adjudicated": False,
            "breaker_low_author_adjudicated": False,
            "stop_price_authorized": False,
            "htf_untouched_target_author_adjudicated": False,
            "source_complete": False,
            "cognitive_admitted": False,
            "fills": 0,
        })
    return {
        "schema": SCHEMA,
        "market": market,
        "source_case_count": len(observed),
        "prior_h1_incomplete_cases": h1_incomplete,
        "source_raw_market_map": raw_market,
        "rule_sources": {
            "conditional_eq": EQ_SOURCE,
            "pre_c2_relevant_swing": SWING_SOURCE,
        },
        "all_conditional_eq_witnesses": observed,
        "source_complete_entries": 0,
        "cognitive_admissions": 0,
        "verified_fills": 0,
        "profit_factor": None,
        "sortino": None,
        "sharpe": None,
        "max_drawdown": None,
        "holdout_7y_accessed": False,
        "sizing_used": False,
        "certified": False,
    }


def canonical_report_sha256(payload: Mapping[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
        .encode("utf-8")
    ).hexdigest()
