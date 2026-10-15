"""Blind physical-only join of VT08 pre-C2 H1 pivot, EQ, untouched H1 highs.

All 2,657 frozen source events are retained, keyed to the same market and
C2/C3 UTC clocks. No prospective trades are authorized. The shortlist is
for INDEPENDENT qualitative B review, never for PnL selection, automatic
relevance, target election, or economic-gate denominators.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Final

SCHEMA: Final = "qore.vt08.a.blind_three_source_review_join.v1"
EQ_SCHEMA: Final = "qore.vt08.a.author_eq_conditional_review.v1"
TARGET_SCHEMA: Final = "qore.vt08.a.observed_h1_untouched_high_witness.v1"
SWING_SCHEMA: Final = "qore.vt08.a.pre_c2_h1_basic_swing_physical_witness.v1"
CATEGORIES: Final = (
    "MISSING_PRE_C2_H1_SOURCE",
    "NO_CLOSED_THREE_H1_BULLISH_BASIC_PIVOT_SHAPE",
    "NO_UNTOUCHED_H1_HIGH_IN_OBSERVED_SEGMENT",
    "MULTIPLE_UNTOUCHED_H1_HIGHS_D",
    "UNIQUE_OBSERVED_H1_HIGH_AND_BASIC_PIVOT_FOR_BLIND_REVIEW_ONLY",
)


def _key(item: dict[str, object], market: str) -> tuple[str, str]:
    if item.get("market") != market:
        raise ValueError("cross-market semantic review row")
    a = item.get("c2_opened_at_utc")
    b = item.get("decision_at_utc")
    if not isinstance(a, str) or not isinstance(b, str):
        raise ValueError("C2/C3 clocks must be strings")
    try:
        c2 = datetime.fromisoformat(a)
        c3 = datetime.fromisoformat(b)
    except ValueError as exc:
        raise ValueError("bad C2/C3 clock") from exc
    if c2.utcoffset() is None or c3.utcoffset() is None:
        raise ValueError("naive source clock")
    if c3.astimezone(UTC) - c2.astimezone(UTC) != timedelta(minutes=30):
        raise ValueError("C3 source clock must equal C2.close")
    return c2.astimezone(UTC).isoformat(), c3.astimezone(UTC).isoformat()


def _indexed(
    rows: object, market: str,
) -> dict[tuple[str, str], dict[str, object]]:
    if not isinstance(rows, list):
        raise ValueError("source witness rows missing")
    output: dict[tuple[str, str], dict[str, object]] = {}
    for item in rows:
        if not isinstance(item, dict):
            raise ValueError("physical witness is not record")
        key = _key(item, market)
        if key in output:
            raise ValueError("duplicate physical C2/C3 source identity")
        output[key] = item
    return output


def join_blind_source_reviews(
    eq: dict[str, object],
    target: dict[str, object],
    swing: dict[str, object],
) -> dict[str, object]:
    """Fail closed if any provenance layer does not cover exact same events."""
    if (
        eq.get("schema") != EQ_SCHEMA
        or target.get("schema") != TARGET_SCHEMA
        or swing.get("schema") != SWING_SCHEMA
    ):
        raise ValueError("unfrozen physical source schema")
    market = eq.get("market")
    if not isinstance(market, str) or target.get("market") != market or swing.get("market") != market:
        raise ValueError("cross-market reports never merge")
    eq_raw = eq.get("source_raw_market_map")
    if (
        not isinstance(eq_raw, dict)
        or target.get("input_m15_source_sha256") not in eq_raw
        or any(value != market for value in eq_raw.values())
    ):
        raise ValueError("physical raw market SHA mismatch")
    if (
        eq.get("source_complete_entries") != 0
        or eq.get("verified_fills") != 0
        or eq.get("profit_factor") is not None
        or target.get("source_complete_entries") != 0
        or target.get("broker_fills") != 0
        or target.get("profit_factor") is not None
        or swing.get("source_complete") is not False
        or swing.get("broker_fills") != 0
        or swing.get("profit_factor") is not None
    ):
        raise ValueError("source-only report carries false trading authority")
    e = _indexed(eq.get("all_conditional_eq_witnesses"), market)
    t = _indexed(target.get("witnesses"), market)
    s = _indexed(swing.get("review_witnesses"), market)
    n = len(e)
    if (
        not n or n != eq.get("source_case_count")
        or n != target.get("frozen_source_events")
        or n != swing.get("input_contexts")
        or set(e) != set(t) or set(e) != set(s)
    ):
        raise ValueError("nonidentical frozen source case universes")
    results: list[dict[str, object]] = []
    groups: Counter[str] = Counter()
    for key in sorted(e):
        eqr, tr, sr = e[key], t[key], s[key]
        available = sr.get("pre_c2_h1_complete") is True
        low = sr.get("basic_swing_bullish_low") is True
        high_count = tr.get("witness_count")
        levels = tr.get("untouched_h1_high_candidates")
        if not isinstance(high_count, int) or not isinstance(levels, list):
            raise ValueError("H1 physical target list missing")
        if high_count != len(levels) or high_count < 0:
            raise ValueError("H1 target cardinality mismatch")
        if eqr.get("eq_selection_authorized") is not False:
            raise ValueError("A cannot auto-select EQ without relevant swing")
        if eqr.get("eq_swing_identity_author_adjudicated") is not False:
            raise ValueError("A pretends source swing adjudicated")
        if sr.get("author_relevant_swing_verified") is True:
            raise ValueError("basic pivot mistakenly promoted to relevant swing")
        if tr.get("author_target_selected") is not False:
            raise ValueError("H1 level incorrectly called author-selected target")
        if available != (eqr.get("prior_h1_context_available") is True):
            raise ValueError("H1 completeness differs between source producers")
        if not available:
            code = CATEGORIES[0]
        elif not low:
            code = CATEGORIES[1]
        elif high_count == 0:
            code = CATEGORIES[2]
        elif high_count > 1:
            code = CATEGORIES[3]
        else:
            code = CATEGORIES[4]
        groups[code] += 1
        review = {
            "market": market,
            "c2_opened_at_utc": key[0],
            "decision_at_utc": key[1],
            "case_id_sha256": hashlib.sha256(
                (market + "|" + key[0] + "|" + key[1]).encode()
            ).hexdigest(),
            "pre_c2_three_h1_physically_complete": available,
            "basic_bullish_h1_pivot": low,
            "basic_bearish_h1_pivot": sr.get("basic_swing_bearish_high") is True,
            "h1_swing_source_ids": sr.get("h1_source_bar_id_groups", []),
            "c2_eq_full_conditional": eqr.get(
                "eq_if_prior_bullish_swing_source_valid_with_close"
            ),
            "c2_eq_close_to_low_conditional": eqr.get(
                "eq_if_prior_bullish_swing_valid_but_close_against"
            ),
            "source_unconsumed_h1_highs": levels,
            "target_cardinality": high_count,
            "diagnostic_review_class": code,
            "source_author_relevant_swing_verified": False,
            "source_author_target_selected": False,
            "source_author_breaker_verified": False,
            "source_author_ps_cisd_verified": False,
            "source_author_poi_verified": False,
            "methodology_source_complete": False,
            "cognitive_verified": False,
            "broker_fill_verified": False,
            "rater_A": None,
            "rater_B_independent": None,
            "author_adjudication": "NOT_STARTED_D",
        }
        results.append(review)
    if sum(groups.values()) != n:
        raise ValueError("blind source funnel lost candidates")
    return {
        "schema": SCHEMA,
        "market": market,
        "frozen_event_count": n,
        "category_counts": {key: groups[key] for key in CATEGORIES},
        "all_source_only_cases": results,
        "selection_basis": "CHRONOLOGY_AND_PHYSICAL_SOURCE_ONLY_NO_PNL",
        "B_independent_semantic_review_complete": False,
        "signed_A_B_manifest": None,
        "source_complete_entries": 0,
        "broker_fills": 0,
        "profit_factor": None,
        "sortino": None,
        "max_drawdown": None,
        "holdout_7y_accessed": False,
        "sizing_used": False,
        "certified": False,
    }


def report_sha256(report: dict[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(report, sort_keys=True, separators=(",", ":"), allow_nan=False)
        .encode("utf-8")
    ).hexdigest()
