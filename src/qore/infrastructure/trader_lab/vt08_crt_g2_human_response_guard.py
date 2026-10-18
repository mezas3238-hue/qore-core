"""R10 structural guardian for R9 blinded G2 human response submissions.

This validator consumes ONLY reviewer-visible casebooks and submitted responses.
Never accesses sealed engine labels, outcomes, reviewer credentials or capital.
Even fully populated fake responses NEVER authorize methodology/certification.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from typing import Any

from qore.infrastructure.trader_lab.vt08_crt_g2_independent_blind_review import (
    ALLOWED_CHOICES,
    SCHEMA as R9_SCHEMA,
)

SCHEMA = "qore.vt08.crt.g2_human_response_guard.r10.research_only.v1"
MARKET_COUNTS = {"AUDUSD": 16, "USDJPY": 20}
RESPONSE_FIELDS = frozenset({
    "schema", "case_id", "reviewer_payload_sha256", "human_choice",
    "source_quote_locator", "causal_reason_for_choice", "counterexample_if_any",
    "independent_reviewer_github_review_verified", "owner_github_approval_verified",
    "methodology_gate_passed", "must_verify_external_github_identity",
})
AUTHORITY_FIELDS = (
    "independent_reviewer_github_review_verified",
    "owner_github_approval_verified", "methodology_gate_passed",
)


def _digest(value: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":")
    ).encode()).hexdigest()


def _distinct_by_id(rows: tuple[dict[str, Any], ...]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        cid = row.get("case_id")
        if not isinstance(cid, str) or len(cid) != 28:
            raise ValueError("G2 response case identity invalid")
        if cid in result:
            raise ValueError("duplicate G2 case identity")
        result[cid] = row
    return result


def audit_g2_human_responses_structural_only(
    market: str,
    reviewer_only: tuple[dict[str, Any], ...],
    submissions: tuple[dict[str, Any], ...],
) -> dict[str, Any]:
    """Check response completeness only; no G-M1 PASS under ANY input."""
    if market not in MARKET_COUNTS:
        raise ValueError("unknown/frozen G2 review market")
    expected = MARKET_COUNTS[market]
    if len(reviewer_only) != expected or len(submissions) != expected:
        raise ValueError("G2 independent sample count not the frozen R9 source")
    cases = _distinct_by_id(reviewer_only)
    replies = _distinct_by_id(submissions)
    if set(cases) != set(replies):
        raise ValueError("G2 response cases not exactly the blinded source cases")
    if list(cases) != list(replies):
        raise ValueError("G2 case submission order differs from fixed review")
    blocker_counts: Counter[str] = Counter()
    answer_counts: Counter[str] = Counter()
    for cid, payload in cases.items():
        if (
            payload.get("schema") != R9_SCHEMA
            or payload.get("market") != market
            or payload.get("reviewer_result") is not None
            or payload.get("independent_methodology_review_complete") is not False
            or payload.get("not_a_trade") is not True
            or payload.get("no_sizing") is not True
        ):
            raise ValueError("G2 reviewer-only case was rewritten or promoted")
        response = replies[cid]
        if set(response) != RESPONSE_FIELDS or response.get("schema") != R9_SCHEMA:
            raise ValueError("G2 response schema has extra/forged fields")
        if (
            response.get("reviewer_payload_sha256") != _digest(payload)
            or type(response.get("must_verify_external_github_identity")) is not bool
            or not response["must_verify_external_github_identity"]
        ):
            raise ValueError("G2 response SHA or reviewer independence root tampered")
        if any(response.get(field) is not False for field in AUTHORITY_FIELDS):
            raise ValueError("G2 JSON cannot self-assert external GitHub approvals")
        choice = response["human_choice"]
        if choice is None:
            blocker_counts["UNANSWERED_BLIND_CASE"] += 1
            continue
        if not isinstance(choice, str) or choice not in ALLOWED_CHOICES:
            raise ValueError("G2 reviewer submission choice outside fixed policy")
        answer_counts[choice] += 1
        reason = response["causal_reason_for_choice"]
        if not isinstance(reason, str) or len(reason.strip()) < 32:
            blocker_counts["MISSING_INDEPENDENT_CAUSAL_REASON"] += 1
        locator = response["source_quote_locator"]
        if not isinstance(locator, str) or len(locator.strip()) < 10:
            blocker_counts["MISSING_SOURCE_OR_QORE_PROPOSAL_LOCATOR"] += 1
        elif not (
            locator.startswith((
                "RomeoTPT:", "SpeculatorFL:", "TraderFlameseN:",
                "QORE_ENGINEERING:", "SOURCE_GAP:",
            ))
        ):
            blocker_counts["SOURCE_PROVENANCE_KIND_UNLABELED"] += 1
        if choice == "INSUFFICIENT_SOURCE":
            if not isinstance(locator, str) or not locator.startswith("SOURCE_GAP:"):
                blocker_counts["INSUFFICIENT_SOURCE_REQUIRES_EXPLICIT_GAP"] += 1
        elif isinstance(locator, str) and locator.startswith("SOURCE_GAP:"):
            blocker_counts["POSITIVE_SELECTION_CANNOT_CITE_ONLY_SOURCE_GAP"] += 1
        challenge = response["counterexample_if_any"]
        if not isinstance(challenge, str) or len(challenge.strip()) < 20:
            blocker_counts["MISSING_COUNTEREXAMPLE_OR_EXPLICIT_NONE_RATIONALE"] += 1
    completed = not blocker_counts and len(answer_counts) == expected
    return {
        "schema": SCHEMA,
        "market": market,
        "frozen_R9_review_cases": expected,
        "structurally_answered": sum(answer_counts.values()),
        "unanswered": blocker_counts.get("UNANSWERED_BLIND_CASE", 0),
        "answer_distribution_NOT_TRUTH": dict(sorted(answer_counts.items())),
        "blocker_counts": dict(sorted(blocker_counts.items())),
        "responses_sha256": hashlib.sha256(
            b"\n".join(
                json.dumps(x, sort_keys=True, separators=(",", ":")).encode()
                for x in submissions
            )
        ).hexdigest(),
        "structurally_complete_NOT_APPROVED": completed,
        "independent_GitHub_identity_authenticated": False,
        "owner_approval_authenticated": False,
        "source_citations_independently_verified": False,
        "G_M1_PASS": False,
        "G_M2_PASS": False,
        "G_M5_ISSUED": False,
        "GLOBAL_CERTIFIED": False,
        "not_a_trade": True,
        "no_sizing": True,
    }
