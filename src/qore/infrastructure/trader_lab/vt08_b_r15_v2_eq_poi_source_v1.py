"""VT08 B R15 — source V2 correction: bullish C2 EQ and POI priority.

Independent physical original cTrader M3 evidence and source-only rule matrix.
DeepSeek V2 proposed (C2.close+C2.low)/2 for a bullish C2 sweep case,
but TTrades 2026-10-10 makes bullish C2 WITH bullish swing full-wick EQ.
No swing/POI is author-adjudicated here, so selected trade EQ is ALWAYS null.
POI priority applies only to continuations starting at a VERIFIED PS.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.trader_lab.vt08_5m_b_independent_raw_receipts_v1 import (
    _instant,
    _raw_bars,
    _verify_bar,
)
from qore.infrastructure.trader_lab.vt08_b_r11_cisd_after_htf_close_chronology_v1 import (
    STAGE,
    audit_cisd_htf_sequence,
)

SCHEMA = "qore.vt08.b.r15.v2_source_eq_poi_adjudication.v1"
EQ_SOURCE = "https://ttrades.com/how-to-use-equilibrium-eq-ttrades-fractal-model/"
POI_SOURCE = (
    "https://ttrades.com/the-only-points-of-interest-that-"
    "actually-matter-for-trading/"
)
M3 = timedelta(minutes=3)
M30 = timedelta(minutes=30)
POI_HIERARCHY = ("FVG", "SWING_HIGH_LOW", "CISD_RETEST")


def bullish_c2_eq_conditional(
    *, opened: Decimal, high: Decimal, low: Decimal, closed: Decimal,
) -> dict[str, object]:
    """Source-only EQ choices, not an authorized trade EQ."""
    if not (low <= min(opened, closed) <= max(opened, closed) <= high):
        raise ValueError("R15 OHLC physically impossible")
    if not low < high or not opened < closed:
        raise ValueError("R15 frozen C2 must have bullish body")
    full = (high + low) / 2
    close_to_low = (closed + low) / 2
    return {
        "c2_body": "BULLISH",
        "source_EQ_if_swing_is_bullish": str(full),
        "source_EQ_if_swing_is_bearish": str(close_to_low),
        "chosen_author_swing_identity": None,
        "chosen_trade_EQ": None,
        "candidate_branch_for_bullish_swing": "FULL_HIGH_LOW",
        "counterfactual_wrong_close_to_low_for_bullish_swing": (
            full != close_to_low
        ),
    }


def continuation_poi_priority(
    quantities: dict[str, int], *,
    protected_swing_author_validated: bool,
) -> dict[str, object]:
    """Only conditional category order; never invent a specific POI object."""
    if (
        type(protected_swing_author_validated) is not bool
        or set(quantities) != set(POI_HIERARCHY)
        or any(type(quantities[k]) is not int or quantities[k] < 0
               for k in POI_HIERARCHY)
    ):
        raise ValueError("R15 invalid source POI inventory")
    if not protected_swing_author_validated:
        return {
            "source_priority": list(POI_HIERARCHY),
            "status": "D_PROTECTED_SWING_UNVERIFIED",
            "chosen_poi": None,
        }
    for tier in POI_HIERARCHY:
        if quantities[tier]:
            return {
                "source_priority": list(POI_HIERARCHY),
                "highest_available_tier": tier,
                "status": (
                    "D_MULTIPLE_SAME_TIER_OBJECTS" if quantities[tier] > 1
                    else "CATEGORY_SELECTED_OBJECT_SOURCE_STILL_NEEDED"
                ),
                "chosen_poi": None,
            }
    return {
        "source_priority": list(POI_HIERARCHY),
        "status": "NO_SOURCE_POI_AVAILABLE",
        "chosen_poi": None,
    }


def audit_frozen_bullish_eq(
    frozen: dict[str, object], *,
    market: str, original_native_m3: Path,
) -> dict[str, object]:
    """Full pre-outcome native C2 receipts; never source-authorizes an entry."""
    r11 = audit_cisd_htf_sequence(
        frozen, expected_market=market, native_m3_file=original_native_m3,
    )
    sha, raw = _raw_bars(original_native_m3, "M3", market)
    stages = frozen.get("examples_by_stage")
    cases = stages.get(STAGE) if isinstance(stages, dict) else None
    if not isinstance(cases, list) or len(cases) != r11[
        "r3_unique_m3_proxy_source_cases"
    ]:
        raise ValueError("R15 frozen original denominator drift")
    counts: Counter[str] = Counter()
    output: list[dict[str, object]] = []
    seen: set[str] = set()
    for case in cases:
        if not isinstance(case, dict) or case.get("market") != market:
            raise ValueError("R15 foreign source event")
        c2 = _instant(case.get("c2_opened_at_utc"))
        entry = _instant(case.get("decision_at_utc"))
        if entry - c2 != M30:
            raise ValueError("R15 decision moved")
        identifier = hashlib.sha256(
            (market+"|"+c2.isoformat()+"|"+entry.isoformat()).encode()
        ).hexdigest()
        if identifier in seen:
            raise ValueError("R15 duplicate")
        seen.add(identifier)
        rec = case.get("c2_m3_raw_bar_receipts")
        if not isinstance(rec, list) or len(rec) != 10:
            raise ValueError("R15 requires all M3 source receipts")
        candle = [_verify_bar(
            v, expected_open=c2+i*M3, minutes=3, profile="M3",
            source_sha=sha, raw=raw,
        ) for i, v in enumerate(rec)]
        opened = candle[0][0]
        high = max(v[1] for v in candle)
        low = min(v[2] for v in candle)
        closed = candle[-1][3]
        eq = bullish_c2_eq_conditional(
            opened=opened, high=high, low=low, closed=closed,
        )
        counts["physical_bullish_c2"] += 1
        counts["conditional_full_vs_wick_eq_differs"] += int(
            eq["counterfactual_wrong_close_to_low_for_bullish_swing"]
        )
        counts["conditional_full_vs_wick_eq_equal"] += int(
            not eq["counterfactual_wrong_close_to_low_for_bullish_swing"]
        )
        output.append({
            "case_id_sha256": identifier,
            "market": market,
            "c2_opened_at_utc": c2.isoformat(),
            "c2_closed_at_utc": entry.isoformat(),
            "c2_raw_ohlc": list(map(str, (opened, high, low, closed))),
            **eq,
            "chosen_author_swing_proven": False,
            "chosen_bullish_poi_proven": False,
            "protected_swing_author_verified": False,
            "source_complete": False,
        })
    if len(output) != len(seen) or len(output) != len(cases):
        raise ValueError("R15 does not reconcile source population")
    return {
        "schema": SCHEMA, "market": market,
        "original_m3_sha256": sha, "frozen_cases": len(output),
        "counts": dict(counts), "all_case_source_eq_witnesses": output,
        "eq_primary_source": EQ_SOURCE,
        "conditional_poi_priority_primary_source": POI_SOURCE,
        "poi_hierarchy_when_protected_swing_is_verified": list(POI_HIERARCHY),
        "author_EQ_trade_authorized": False,
        "author_POI_trade_authorized": False,
        "author_complete_entries": 0, "real_cognitive_admissions": 0,
        "broker_fills": 0, "profit_factor": None,
        "sizing_used": False, "holdout_7y_accessed": False,
    }


def digest(result: dict[str, object]) -> str:
    return hashlib.sha256(json.dumps(
        result, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode()).hexdigest()
