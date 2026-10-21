"""VT08 R28: convert frozen R19 POI review into methodological WAIT packets.

No POI is selected by geometric FVG existence. Original sample stays frozen.
"""
from __future__ import annotations

from qore.infrastructure.trader_lab.vt08_b_r19_blind_dual_rater_poi_queue_v1 import (
    MARKET_EXPECTED,
    SCHEMA as R19_SCHEMA,
    SEED as R19_SEED,
    digest,
)
from qore.infrastructure.trader_lab.vt08_b_r23_signed_semantic_review_contract_v1 import (
    PINNED_R19_REPORT_DIGESTS,
)
from qore.infrastructure.trader_lab.vt08_r27_methodology_gate import adjudicate


def build_methodology_queue(blind: dict, *, market: str) -> dict:
    if market not in MARKET_EXPECTED:
        raise ValueError("R28 unauthorized market")
    expected_count, expected_r18 = MARKET_EXPECTED[market]
    if (
        blind.get("schema") != R19_SCHEMA
        or blind.get("seed") != R19_SEED
        or blind.get("market") != market
        or digest(blind) != PINNED_R19_REPORT_DIGESTS[market]
        or blind.get("original_r18_sha256") != expected_r18
        or blind.get("original_r18_cases") != expected_count
        or blind.get("rater_A_signed") != 0
        or blind.get("rater_B_signed") != 0
        or blind.get("source_complete_entries") != 0
        or blind.get("cognitive_admissions") != 0
        or blind.get("broker_fills") != 0
        or blind.get("holdout_7y_accessed") is not False
        or blind.get("sizing_used") is not False
    ):
        raise ValueError("R28 R19 source review integrity drift")
    cases = blind.get("review_packets")
    if not isinstance(cases, list) or len(cases) != blind.get("selected_source_only_cases"):
        raise ValueError("R28 incomplete frozen review queue")
    output = []
    seen = set()
    categories = {}
    for case in cases:
        if not isinstance(case, dict):
            raise ValueError("R28 malformed source case")
        cid = case.get("case_id_sha256")
        if (not isinstance(cid, str) or len(cid) != 64
                or any(c not in "0123456789abcdef" for c in cid)
                or cid in seen or case.get("market") != market):
            raise ValueError("R28 duplicate or cross-market R19 case")
        seen.add(cid)
        if (case.get("source_complete") is not False
                or case.get("cognitive_ready") is not False
                or case.get("orders_authorized") is not False
                or case.get("human_rater_A_source_signoff") is not None
                or case.get("human_rater_B_independent_signoff") is not None):
            raise ValueError("R28 false original reviewer authority")
        category = case["category"]
        categories[category] = categories.get(category, 0) + 1
        packet = {
            "case_id_sha256": cid,
            "market": market,
            "decision_as_of_utc": case["c3_opened_at_utc"],
            "source_sha256": expected_r18,
            "rule_evidence": {},
            "independent_reviews": [],
            "unresolved_disagreements": [
                "reference_swing_selection",
                "significant_poi_selection",
                "protected_swing_causal_series",
            ],
        }
        verdict = adjudicate(packet)
        if verdict["methodology_gate"] != "BLOCKED":
            raise ValueError("R28 false methodological admission")
        output.append({
            "case_id_sha256": cid,
            "market": market,
            "original_r19_category": case["category"],
            "original_selection_rank_sha256": case["selection_rank_sha256"],
            "c3_opened_at_utc": case["c3_opened_at_utc"],
            "candidate_h1_fvg": case["candidate_h1_fvg"],
            "candidate_h1_prior_lows": case["candidate_h1_prior_lows"],
            "questions": {
                "reference_swing": "Which source-backed HTF swing is relevant as of C3?",
                "significant_poi": "Which pre-CISD level caused the reversal, and why?",
                "protected_swing": "Which exact opposing candles were closed through?",
            },
            "gate": verdict,
            "review_state": "WAIT_FOR_INDEPENDENT_METHOD_AUTHOR_ADJUDICATION",
        })
    if categories != blind.get("selected_category_counts"):
        raise ValueError("R28 source sample category census drift")
    return {
        "schema": "qore.vt08.r28.frozen_r19_methodology_queue.v1",
        "market": market,
        "original_r19_sha256": PINNED_R19_REPORT_DIGESTS[market],
        "source_sample_count": len(output),
        "source_complete_entries": 0,
        "cognitive_admissions": 0,
        "methodology_cases": output,
        "verdict": "VT08_METHOD_NOT_CERTIFIED",
    }
