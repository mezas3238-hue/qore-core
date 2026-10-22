"""VT08 R29: independent methodological adjudication preparation, not approval.

Transforms frozen R28 cases into explicit source-first decisions. Geometric
candidates never become TTrades-authorized POIs without original evidence.
"""
from __future__ import annotations

from collections import Counter

from qore.infrastructure.trader_lab.vt08_b_r23_signed_semantic_review_contract_v1 import (
    PINNED_R19_REPORT_DIGESTS,
)

QUESTIONS = (
    "reference_swing",
    "significant_poi",
    "protected_swing",
)


def audit_review_readiness(r28: dict) -> dict:
    if not isinstance(r28, dict) or r28.get("schema") != (
        "qore.vt08.r28.frozen_r19_methodology_queue.v1"
    ):
        raise ValueError("R29 requires an original R28 methodological queue")
    market = r28.get("market")
    if market not in PINNED_R19_REPORT_DIGESTS or (
        r28.get("original_r19_sha256") != PINNED_R19_REPORT_DIGESTS[market]
    ):
        raise ValueError("R29 unpinned R19 source lineage")
    cases = r28.get("methodology_cases")
    if not isinstance(cases, list) or len(cases) != r28.get("source_sample_count"):
        raise ValueError("R29 incomplete R28 denominator")
    if r28.get("source_complete_entries") != 0 or r28.get("cognitive_admissions") != 0:
        raise ValueError("R29 cannot promote an already asserted admission")
    if r28.get("verdict") != "VT08_METHOD_NOT_CERTIFIED":
        raise ValueError("R29 source certification state changed")
    seen = set()
    out = []
    counts = Counter()
    for case in cases:
        if not isinstance(case, dict):
            raise ValueError("R29 invalid methodological case")
        cid = case.get("case_id_sha256")
        if not isinstance(cid, str) or len(cid) != 64 or any(
            c not in "0123456789abcdef" for c in cid
        ) or cid in seen:
            raise ValueError("R29 invalid/duplicate source identity")
        seen.add(cid)
        if case.get("market") != r28.get("market"):
            raise ValueError("R29 cross-market case")
        gate = case.get("gate")
        if (not isinstance(gate, dict)
                or gate.get("methodology_gate") != "BLOCKED"
                or gate.get("trade_authorized") is not False
                or gate.get("cognitive_gate") not in (None, "NOT_EVALUATED")
                or gate.get("economic_gate") not in (None, "NOT_EVALUATED")
                or case.get("review_state") !=
                "WAIT_FOR_INDEPENDENT_METHOD_AUTHOR_ADJUDICATION"):
            raise ValueError("R29 unverified methodological authority")
        reasons = gate.get("blocked_reasons")
        if reasons is not None and (
            not isinstance(reasons, list)
            or "external_signature_verifier_not_connected" not in reasons
        ):
            raise ValueError("R29 source gate lacks independent signature block")
        questions = case.get("questions")
        if not isinstance(questions, dict) or set(questions) != set(QUESTIONS):
            raise ValueError("R29 missing source-first methodological questions")
        candidate = case.get("candidate_h1_fvg")
        status = (
            "GEOMETRIC_FVG_PRESENT_NOT_AUTHOR_SELECTED"
            if candidate is not None else "NO_GEOMETRIC_FVG_NOT_POI_REJECTION"
        )
        counts[status] += 1
        out.append({
            "case_id_sha256": cid,
            "market": r28["market"],
            "poi_screening": status,
            "swing_author_adjudication": "WAIT",
            "poi_author_adjudication": "WAIT",
            "protected_swing_author_adjudication": "WAIT",
            "source_reviewer_A": None,
            "source_reviewer_B": None,
            "methodological_admission": False,
        })
    return {
        "schema": "qore.vt08.r29.source_first_methodological_triage.v1",
        "market": r28["market"],
        "original_r19_sha256": r28["original_r19_sha256"],
        "original_case_count": len(out),
        "poi_screening_counts": dict(counts),
        "review_cases": out,
        "author_certified": 0,
        "cognitive_admissions": 0,
        "trade_authorized": False,
        "verdict": "WAIT_INDEPENDENT_AUTHOR_SOURCE_REVIEW",
    }
