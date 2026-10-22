"""VT08 B R23: genuine semantic adjudication ledger, source-only and fail-closed.

Join two independent frozen reviews (R20 raw FVG/opposing M3 series and
R22 competing swing/POI/NY context). Output 107 case-specific missing
author evidence dossiers. NEVER grant an A/B signature, setup, cognitive
admission, broker fill, or economic gate from physical coincidence.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter

from qore.infrastructure.trader_lab.vt08_b_r20_poi_opposing_run_causal_join_v1 import (
    SCHEMA as R20_SCHEMA,
)
from qore.infrastructure.trader_lab.vt08_b_r20_poi_opposing_run_causal_join_v1 import (
    digest as r20_digest,
)
from qore.infrastructure.trader_lab.vt08_b_r22_multi_poi_contradiction_join_v1 import (
    SCHEMA as R22_SCHEMA,
)

SCHEMA = "qore.vt08.b.r23.semantic_review_evidence_firstfail.v1"
OWNER = "VT08_CURRENT_ONLY_NO_QORE_ALPHA"
EXPECTED = {
    "EURJPY": (538, 21, "4408333b40703a383119e83b04cbaa1164dc21948ba3673b92ceafdc5e82f706"),
    "USDCHF": (518, 21, "74fc303ed9269014131f163bf8d44e44f4ae2285af78c3695935d1fd6ac7ae16"),
    "NZDUSD": (550, 21, "b8956e81ab20429284f359cd2af99bb71afda8bb27fe2523c990ab9005377114"),
    "CADJPY": (516, 21, "f001dd4263a02c8a8c72cbc5295319955800c94608f47bcc0ca27b9d2d418440"),
    "USDCAD": (535, 23, "17381f63e6a0bdb78a7b55bdf122052411a1aeca1417c778cd312680d36f61e3"),
}
# The evidence requirements are assertions about audit completeness,
# NOT invented thresholds, nor new rules attributed to the author.
REQUIRED = {
    "relevant_swing": (
        "https://ttrades.com/relevant-swings-which-swing-highs-and-lows-matter-in-trading/",
        "separation and candidate swing selection: source IDs, TF, as-of, alternatives",
    ),
    "important_poi": (
        "https://ttrades.com/how-change-in-the-state-of-delivery-cisd-confirms-swing-points/",
        "pre-CISD important level: type, source ID, last untouched status and reason chosen",
    ),
    "protected_swing": (
        "https://ttrades.com/positional-entries-enter-before-the-expansion/",
        "authenticated PS relation to POI + original opposing-series IDs, as-of C3.open",
    ),
    "equilibrium": (
        "https://ttrades.com/how-to-use-equilibrium-eq-ttrades-fractal-model/",
        "author-selected reference swing and chosen C2 conditional EQ formula",
    ),
    "breaker": (
        "https://ttrades.com/breaker-blocks-simplified/",
        "source sequence low→high→lower-low→higher-high, TF, breaker candle IDs and low",
    ),
    "stop_loss": (
        "https://ttrades.com/timeframe-alignment-how-to-align-higher-and-lower-time-frames-for-precision-entries/",
        "stop below EQ AND breaker low in specific M30→M3 Example 1; PS level, FVG room",
    ),
    "target": (
        "https://ttrades.com/how-to-set-price-targets-using-the-fractal-model/",
        "unbroken HTF target as-of entry, all competing candidates and selection provenance",
    ),
    "cognitive": (
        "VT08_COGNITION_27_CAUSAL_FIELDS",
        "27 genuine per-SITUATION fields and independent B review after methodology authority",
    ),
}


def build_semantic_wait_ledger(
    r20: dict[str, object], r22: dict[str, object], *, market: str,
) -> dict[str, object]:
    """Single frozen source-only queue, not an authorized review signature."""
    if market not in EXPECTED:
        raise ValueError("R23 unknown VT08-only market")
    n, sample_n, pinned20 = EXPECTED[market]
    if (
        r20.get("schema") != R20_SCHEMA
        or r20.get("market") != market
        or r20.get("owner_scope") != OWNER
        or r20_digest(r20) != pinned20
        or r20.get("original_cases") != n
        or r20.get("blind_review_cases") != sample_n
        or r20.get("source_authorized_entries") != 0
        or r20.get("genuine_human_A_signoffs") != 0
        or r20.get("genuine_human_B_signoffs") != 0
        or r20.get("cognitive_admissions") != 0
        or r20.get("broker_fills") != 0
        or r20.get("profit_factor") is not None
        or r20.get("holdout_7y_accessed") is not False
        or r20.get("sizing_used") is not False
    ):
        raise ValueError("R23 R20 original owner/census or source SHA mismatch")
    if (
        r22.get("schema") != R22_SCHEMA
        or r22.get("market") != market
        or r22.get("all_original_case_count") != n
        or r22.get("r19_blind_packets_enriched") != sample_n
        or r22.get("source_author_complete") != 0
        or r22.get("dual_source_human_reviews_completed") != 0
        or r22.get("cognitive_admissions") != 0
        or r22.get("broker_fills") != 0
        or r22.get("economic_gates_evaluated") is not False
        or r22.get("holdout_7y_accessed") is not False
        or r22.get("sizing_used") is not False
        or r22.get("frozen_original_r18_digest") != r20.get("r18_pinned_sha256")
        or r22.get("frozen_original_r19_digest") != r20.get("r19_pinned_sha256")
        or r22.get("original_r21_m3_source_sha") != r20.get("original_native_m3_sha256")
    ):
        raise ValueError("R23 R22 cross-feed/scope, custody or authority mismatch")
    a = r20.get("enriched_blind_review_packets")
    b = r22.get("blind_rater_dossiers")
    if not isinstance(a, list) or not isinstance(b, list):
        raise ValueError("R23 missing source review packets")
    if len(a) != sample_n or len(b) != sample_n:
        raise ValueError("R23 altered preregistered R19 case count")
    index_a: dict[str, dict[str, object]] = {}
    index_b: dict[str, dict[str, object]] = {}
    for bucket, rows in ((index_a, a), (index_b, b)):
        for item in rows:
            if not isinstance(item, dict) or item.get("market") != market:
                raise ValueError("R23 foreign review packet")
            cid = item.get("case_id_sha256")
            if not isinstance(cid, str) or len(cid) != 64 or cid in bucket:
                raise ValueError("R23 duplicated/invalid source case ID")
            if (
                item.get("human_rater_A_source_signoff") is not None
                or item.get("human_rater_B_independent_signoff") is not None
                or item.get("source_complete") is not False
                or item.get("cognitive_ready") is not False
                or item.get("orders_authorized") is not False
            ):
                raise ValueError("R23 forged human signature or cognitive/trade admission")
            bucket[cid] = item
    if set(index_a) != set(index_b):
        raise ValueError("R23 R20/R22 blind review identities differ")
    all20 = r20.get("all_physical_causal_opposing_run_witnesses")
    all22 = r22.get("entire_original_census")
    if not isinstance(all20, list) or not isinstance(all22, list):
        raise ValueError("R23 missing full original case census")
    if (
        len(all20) != n or len(all22) != n
        or len({x["case_id_sha256"] for x in all20}) != n
        or {x["case_id_sha256"] for x in all20}
        != {x["case_id_sha256"] for x in all22}
    ):
        raise ValueError("R23 full frozen 2657 denominator/case IDs changed")
    full20 = {x["case_id_sha256"]: x for x in all20}
    full22 = {x["case_id_sha256"]: x for x in all22}
    counts: Counter[str] = Counter()
    dossiers = []
    for cid in sorted(index_a):
        x, y = index_a[cid], index_b[cid]
        if (
            x.get("category") != y.get("category")
            or x.get("selection_rank_sha256") != y.get("selection_rank_sha256")
            or x.get("c2_opened_at_utc") != y.get("c2_opened_at_utc")
            or x.get("cisd_closed_at_utc") != y.get("cisd_closed_at_utc")
            or x.get("c3_opened_at_utc") != y.get("c3_opened_at_utc")
        ):
            raise ValueError("R23 preregistered R19 event/category/rank mutated")
        phys = x.get("independent_bearish_run_causal_witness")
        context = y.get("R22_independent_physical_context")
        if phys != full20[cid] or context != full22[cid]:
            raise ValueError("R23 embedded case-level M3 vs HTF witness drift")
        if (
            phys.get("source_complete") is not False
            or phys.get("author_protected_swing") is not False
            or context.get("relevance_and_poi_selection_adjudicated") is not False
            or context.get("two_independent_raters_signed") is not False
            or y.get("primary_source_important_poi_ref") is not None
            or y.get("primary_source_relevant_swing_ref") is not None
            or y.get("rater_A_verified") is not False
            or y.get("rater_B_verified") is not False
            or y.get("eligible_for_pnl") is not False
        ):
            raise ValueError("R23 false source or reviewer semantic authority")
        phase = phys.get("physical_first_touch_relative_to_run")
        if not isinstance(phase, str):
            raise ValueError("R23 original POI phase not accounted for")
        counts["sample_"+str(x["category"])] += 1
        counts["physical_"+phase] += 1
        counts["unreviewed"] += 1
        dossiers.append({
            "case_id_sha256": cid, "market": market,
            "frozen_r19_category": x["category"],
            "frozen_r19_rank": x["selection_rank_sha256"],
            "C3_decision_at_utc": x["c3_opened_at_utc"],
            "physical_candidate_evidence": {
                "r20_bearish_series_causal_witness": phys,
                "r22_competing_poi_context": context,
            },
            "source_fidelity_questions": {
                k: {
                    "primary_source": url,
                    "what_reviewer_must_prove": requirement,
                    "A_provenance_and_author_selection": None,
                    "B_independent_evidence": None,
                    "status": "AWAITING_REAL_REVIEW",
                }
                for k, (url, requirement) in REQUIRED.items()
            },
            "methodology": "VT08_TTRADES_CURRENT",
            "owner_scope": OWNER,
            "human_A_real_review": None,
            "human_B_real_review": None,
            "source_authenticity_accepted": False,
            "cognitive_admission_authorized": False,
            "economic_evaluation_authorized": False,
            "decision": "WAIT_FOR_AUTHENTIC_SWING_POI_PS_ADJUDICATION",
        })
    if len(dossiers) != sample_n:
        raise ValueError("R23 missing adversarial sample")
    return {
        "schema": SCHEMA, "market": market,
        "original_source_cases_unchanged": n,
        "original_r20_sha256": pinned20,
        "original_r18_sha256": r20["r18_pinned_sha256"],
        "original_r19_sha256": r20["r19_pinned_sha256"],
        "sample_cases_for_genuine_review": len(dossiers),
        "sample_context_counts": dict(sorted(counts.items())),
        "critical_source_questions": list(REQUIRED),
        "review_dossiers": dossiers,
        "human_A_genuinely_reviewed": 0,
        "human_B_genuinely_reviewed": 0,
        "source_author_complete": 0,
        "cognitive_admissions": 0,
        "broker_fills": 0,
        "profit_factor": None, "holdout_7y_accessed": False,
        "sizing_used": False, "QORE_alpha_excluded": True,
        "economic_gates_evaluated": False,
    }


def digest(result: dict[str, object]) -> str:
    return hashlib.sha256(json.dumps(
        result, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode()).hexdigest()
