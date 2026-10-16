"""VT08 B R19 — preregistered blinded dual-rater POI review queue.

Input ONLY the five already source-verified R18 research files. Select by
fixed SHA-based ranking *without outcomes/PnL*. No approval flag is ever
manufactured: two genuine independent raters are required downstream.
No alternate strategies or QORE-alpha, no trading authority.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter

from qore.infrastructure.trader_lab.vt08_b_r18_pre_cisd_h1_poi_native_timing_v1 import (
    SCHEMA as R18_SCHEMA,
)
from qore.infrastructure.trader_lab.vt08_b_r18_pre_cisd_h1_poi_native_timing_v1 import (
    digest as r18_digest,
)

SCHEMA = "qore.vt08.b.r19.preregistered_blind_poi_review_queue.v1"
SEED = "VT08-OWNER-R19-POI-BLIND-PRE-PNL-2026-10-16"
MARKET_EXPECTED = {
    "EURJPY": (538, "aa4e64613aad028548f1d07cf4ed8f4c4ae5a8aa3ebbd5454943e7e2ee2fd5b9"),
    "USDCHF": (518, "f306859c13b3925b42f6c1b49f5eb62497d3c72235a4a49fbdb5979872f043f6"),
    "NZDUSD": (550, "1bb8871d28fe2217b1d1e9187fd99e1b9260090258ab4f5995959cdcebb103f3"),
    "CADJPY": (516, "f0e3d2dd7fb1cc73e4cb4d2a07c25fb93b76137e09ff0f1fdc607eba288a0dbc"),
    "USDCAD": (535, "bec27d9651a65d85502dd62c319f258d540a56784c0b141efccdf973946332a6"),
}
BULL = "BULLISH_H1_3BAR_FVG_GEOMETRY"
BEAR = "BEARISH_H1_3BAR_FVG_GEOMETRY"
PRE = "TOUCHED_BEFORE_CISD_BAR"
SAME = "TOUCHED_IN_CISD_BAR_SEQUENCE_UNKNOWN"


def deterministic_rank(market: str, candidate_id: str) -> str:
    return hashlib.sha256(
        (SEED+"|"+market+"|"+candidate_id).encode()
    ).hexdigest()


def _category(case: dict[str, object]) -> str:
    zone = case.get("pre_existing_h1_fvg_candidate")
    if zone is None:
        return "CONTROL_NO_THREE_H1_FVG"
    if not isinstance(zone, dict):
        raise ValueError("R19 forged POI witness")
    direction = zone.get("type")
    phase = zone.get("first_touch_phase")
    if direction == BULL and phase == PRE:
        return "BULLISH_FVG_TOUCHED_PRE_CISD"
    if direction == BULL and phase == SAME:
        return "SAME_CISD_M3_BAR_INTRABAR_UNKNOWN"
    if direction == BEAR and phase == PRE:
        return "BEARISH_FVG_TOUCHED_PRE_CISD_NEGATIVE_CONTROL"
    return "OTHER_SOURCE_POI_PHYSICAL_STATE"


def build_blind_review_queue(r18: dict[str, object], *, market: str) -> dict[str, object]:
    """Choose 10+10 and ALL rare temporal adversaries per market.

    This is an AUDIT SAMPLE, not a trading universe selector.
    """
    if market not in MARKET_EXPECTED:
        raise ValueError("R19 unapproved VT08 market")
    expected_count, fixed_sha = MARKET_EXPECTED[market]
    if (
        r18.get("schema") != R18_SCHEMA or r18.get("market") != market
        or r18.get("owner_scope") != "VT08_CURRENT_ONLY_NO_QORE_ALPHA"
        or r18_digest(r18) != fixed_sha
        or r18.get("original_source_cases") != expected_count
        or r18.get("source_complete_entries") != 0
        or r18.get("cognitive_admissions") != 0
        or r18.get("broker_fills") != 0
        or r18.get("profit_factor") is not None
    ):
        raise ValueError("R19 R18 original evidence/owner scope digest mismatch")
    original = r18.get("all_pre_cisd_h1_poi_source_witnesses")
    if not isinstance(original, list) or len(original) != expected_count:
        raise ValueError("R19 incomplete original POI source denominator")
    by_category: dict[str, list[dict[str, object]]] = {}
    identifiers: set[str] = set()
    for item in original:
        if (
            not isinstance(item, dict) or item.get("market") != market
            or item.get("author_source_complete") is not False
            or item.get("author_relevant_swing_selected") is not False
            or item.get("author_poi_significant_and_selected") is not False
            or item.get("author_protected_swing_adjudicated") is not False
            or item.get("cognitive_admission") is not False
            or item.get("broker_fill") is not False
        ):
            raise ValueError("R19 input attempts false source/cognitive authority")
        cid = item.get("case_id_sha256")
        if not isinstance(cid, str) or len(cid) != 64 or cid in identifiers:
            raise ValueError("R19 duplicate/corrupt frozen source identity")
        identifiers.add(cid)
        zone = item.get("pre_existing_h1_fvg_candidate")
        if isinstance(zone, dict) and zone.get("first_touch_bar_opened_at_utc") is not None:
            if not isinstance(zone.get("first_touch_m3_source_bar_id"), str):
                raise ValueError("R19 first touch has no source M3 bar ID")
        by_category.setdefault(_category(item), []).append(item)
    controls = (
        ("BULLISH_FVG_TOUCHED_PRE_CISD", 10),
        ("CONTROL_NO_THREE_H1_FVG", 10),
        ("SAME_CISD_M3_BAR_INTRABAR_UNKNOWN", None),
        ("BEARISH_FVG_TOUCHED_PRE_CISD_NEGATIVE_CONTROL", None),
    )
    packets = []
    totals: Counter[str] = Counter()
    for category, count in controls:
        ordered = sorted(by_category.get(category, []), key=lambda item: (
            deterministic_rank(market, item["case_id_sha256"]),
            item["case_id_sha256"],
        ))
        if count is not None and len(ordered) < count:
            raise ValueError("R19 not enough frozen, unbiased strata: "+category)
        selected = ordered if count is None else ordered[:count]
        for item in selected:
            cid = item["case_id_sha256"]
            packets.append({
                "case_id_sha256": cid, "market": market,
                "category": category,
                "selection_seed": SEED,
                "selection_rank_sha256": deterministic_rank(market, cid),
                "c2_opened_at_utc": item["c2_opened_at_utc"],
                "cisd_closed_at_utc": item["cisd_closed_at_utc"],
                "c3_opened_at_utc": item["c3_opened_at_utc"],
                "upstream_h1_status": item["upstream_h1_status"],
                "candidate_h1_fvg": item["pre_existing_h1_fvg_candidate"],
                "candidate_h1_prior_lows": item["pre_existing_h1_low_candidates"],
                "human_rater_A_source_signoff": None,
                "human_rater_B_independent_signoff": None,
                "human_rater_disagreement": None,
                "author_POI_relevance_selected": False,
                "source_complete": False,
                "cognitive_ready": False,
                "orders_authorized": False,
            })
            totals[category] += 1
    if len({row["case_id_sha256"] for row in packets}) != len(packets):
        raise ValueError("R19 strata overlap invalid")
    return {
        "schema": SCHEMA, "market": market, "seed": SEED,
        "original_r18_sha256": fixed_sha, "original_r18_cases": expected_count,
        "review_sample_not_a_trading_cohort": True,
        "selection_without_pnl": True,
        "selected_category_counts": dict(totals),
        "selected_source_only_cases": len(packets), "review_packets": packets,
        "rater_A_signed": 0, "rater_B_signed": 0, "disagreements_resolved": 0,
        "source_complete_entries": 0, "cognitive_admissions": 0,
        "broker_fills": 0, "holdout_7y_accessed": False,
        "sizing_used": False, "alpha_programs_authorized": 0,
    }


def digest(data: dict[str, object]) -> str:
    return hashlib.sha256(json.dumps(
        data, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode()).hexdigest()
