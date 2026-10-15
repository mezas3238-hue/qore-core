"""VT08 B R10: census-backed, outcome-blind cognitive readiness inventory.

An A R7 physical witness is NOT an author-approved CandidateEvent or a
27-field Situation. Build a complete review queue without converting source
geometry into cognitive EXECUTE or inventing per-field semantic receipts.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Final

from qore.infrastructure.traders.vt08_cognitive_5m_research_scope import CAUSAL_FIELDS

SCHEMA: Final = "qore.vt08.a.blind_three_source_review_join.v1"
OUT_SCHEMA: Final = "qore.vt08.b.r10.blind_cognitive_admission_inventory.v1"
MARKETS: Final = frozenset(("EURJPY", "USDCHF", "NZDUSD", "CADJPY", "USDCAD"))
MISSING: Final = "MISSING_PRE_C2_H1_SOURCE"
NO_PIVOT: Final = "NO_CLOSED_THREE_H1_BULLISH_BASIC_PIVOT_SHAPE"
NO_HIGH: Final = "NO_UNTOUCHED_H1_HIGH_IN_OBSERVED_SEGMENT"
MULTI: Final = "MULTIPLE_UNTOUCHED_H1_HIGHS_D"
SINGLE: Final = "UNIQUE_OBSERVED_H1_HIGH_AND_BASIC_PIVOT_FOR_BLIND_REVIEW_ONLY"
CLASSES: Final = (MISSING, NO_PIVOT, NO_HIGH, MULTI, SINGLE)
SOURCE_FLAGS: Final = (
    "source_author_relevant_swing_verified",
    "source_author_target_selected",
    "source_author_breaker_verified",
    "source_author_ps_cisd_verified",
    "source_author_poi_verified",
    "methodology_source_complete",
    "cognitive_verified",
    "broker_fill_verified",
)
UNPROVEN_FIELDS: Final = (
    "relevant_swing", "valid_separation", "poi", "cisd_ps",
    "breaker_origin", "eq_regime", "stop", "htf_target", "target_tiebreak",
)


def _utc(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("VT08 R10 source decision time required")
    try:
        d = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("VT08 R10 invalid source clock") from exc
    if d.tzinfo is None or d.utcoffset() is None:
        raise ValueError("VT08 R10 offset-aware UTC event required")
    return d.astimezone(UTC)


def _sha(obj: object) -> str:
    return hashlib.sha256(json.dumps(
        obj, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")).hexdigest()


def _classify(case: dict[str, object]) -> str:
    available = case.get("pre_c2_three_h1_physically_complete")
    pivot = case.get("basic_bullish_h1_pivot")
    count = case.get("target_cardinality")
    if type(available) is not bool or type(pivot) is not bool:
        raise ValueError("VT08 R10 missing explicit H1 and pivot flags")
    if type(count) is not int or count < 0:
        raise ValueError("VT08 R10 missing authentic H1 count")
    if not available:
        return MISSING
    if not pivot:
        return NO_PIVOT
    if count == 0:
        return NO_HIGH
    if count > 1:
        return MULTI
    return SINGLE


def audit_blind_cognitive_admission(
    report: dict[str, object], *, expected_market: str,
) -> dict[str, object]:
    """Never treat full physical provenance as authentic 27-field cognition.

    Each frozen C2 belongs to exactly one chronological blind-review bucket.
    Actual A/B semantic adjudication and field receipts MUST come from a
    separate signed contract; their absence is a BLOCK, not an empty PASS.
    """
    if expected_market not in MARKETS or report.get("market") != expected_market:
        raise ValueError("VT08 R10 wrong market")
    if report.get("schema") != SCHEMA:
        raise ValueError("VT08 R10 noncanonical A R7 source-only report")
    if (
        report.get("selection_basis") != "CHRONOLOGY_AND_PHYSICAL_SOURCE_ONLY_NO_PNL"
        or report.get("B_independent_semantic_review_complete") is not False
        or report.get("signed_A_B_manifest") is not None
        or report.get("source_complete_entries") != 0
        or report.get("broker_fills") != 0
        or report.get("profit_factor") is not None
        or report.get("sortino") is not None
        or report.get("max_drawdown") is not None
        or report.get("holdout_7y_accessed") is not False
        or report.get("sizing_used") is not False
        or report.get("certified") is not False
    ):
        raise ValueError("VT08 R10 false semantic/economic authority in source report")
    rows = report.get("all_source_only_cases")
    if not isinstance(rows, list) or not rows or any(not isinstance(x, dict) for x in rows):
        raise ValueError("VT08 R10 source-only case rows absent")
    if type(report.get("frozen_event_count")) is not int or len(rows) != report[
        "frozen_event_count"
    ]:
        raise ValueError("VT08 R10 full frozen universe cardinality drift")
    if len(CAUSAL_FIELDS) != 27:
        raise ValueError("VT08 R10 cognition field contract changed without version")
    seen: set[tuple[str, str]] = set()
    queue: list[dict[str, object]] = []
    classes: Counter[str] = Counter()
    for case in rows:
        if case.get("market") != expected_market:
            raise ValueError("VT08 R10 mixed source markets")
        c2, c3 = _utc(case.get("c2_opened_at_utc")), _utc(case.get("decision_at_utc"))
        if c3 - c2 != timedelta(minutes=30):
            raise ValueError("VT08 R10 future or non-frozen C3 clock")
        key = (c2.isoformat(), c3.isoformat())
        if key in seen:
            raise ValueError("VT08 R10 duplicate C2 source identity")
        seen.add(key)
        identity = _sha(f"{expected_market}|{key[0]}|{key[1]}")
        # A R7 hashes the bytes of the text itself, not a JSON string.
        identity = hashlib.sha256(
            f"{expected_market}|{key[0]}|{key[1]}".encode()
        ).hexdigest()
        if case.get("case_id_sha256") != identity:
            raise ValueError("VT08 R10 changed case source identity")
        levels = case.get("source_unconsumed_h1_highs")
        if not isinstance(levels, list) or case.get("target_cardinality") != len(levels):
            raise ValueError("VT08 R10 R7 high source cardinality drift")
        assigned = _classify(case)
        if case.get("diagnostic_review_class") != assigned:
            raise ValueError("VT08 R10 A category does not match source flags")
        if (
            case.get("rater_A") is not None
            or case.get("rater_B_independent") is not None
            or case.get("author_adjudication") != "NOT_STARTED_D"
            or any(case.get(name) is not False for name in SOURCE_FLAGS)
        ):
            raise ValueError("VT08 R10 forged author review or cognitive permission")
        # These keys are absent in R7; their presence cannot create a true
        # signed 27-field Situation, even if hashes happen to be well formed.
        if any(key in case for key in (
            "situation_27_field_receipts", "cognitive_feature_proofs",
            "source_author_signed", "terminal_pnl", "net_pnl",
            "broker_fill", "candidate_event_v1",
        )):
            raise ValueError("VT08 R10 outcome/false Situation injected in review")
        classes[assigned] += 1
        queue.append({
            "case_id_sha256": identity,
            "market": expected_market,
            "c2_opened_at_utc": key[0],
            "decision_at_utc": key[1],
            "diagnostic_review_class": assigned,
            "requested_method_evidence": UNPROVEN_FIELDS,
            "semantic_review_state": "D_NOT_ADJUDICATED",
            "cognitive_27_source_receipts_verified": 0,
            "cognitive_missing_fields": CAUSAL_FIELDS,
            "source_method_author_validated": False,
            "cognitive_execute_authorized": False,
            "broker_order_authorized": False,
        })
    if report.get("category_counts") != {name: classes[name] for name in CLASSES}:
        raise ValueError("VT08 R10 physical bucket coverage drift")
    queue.sort(key=lambda x: (str(x["decision_at_utc"]), str(x["case_id_sha256"])))
    return {
        "schema": OUT_SCHEMA,
        "market": expected_market,
        "frozen_source_report_sha256": _sha(report),
        "cases_review_queued": len(queue),
        "physical_categories": {name: classes[name] for name in CLASSES},
        "cognitive_causal_fields_required": len(CAUSAL_FIELDS),
        "genuine_cognitive_field_receipts_verified": 0,
        "unverified_cognitive_field_instances": len(queue) * len(CAUSAL_FIELDS),
        "source_author_complete": 0,
        "cognitive_admissions": 0,
        "verified_fills": 0,
        "approved_a_b_manifest_sha256": None,
        "research_only": True,
        "holdout_7y_accessed": False,
        "sizing_used": False,
        "economic_gates_evaluated": False,
        "review_queue": queue,
        "verdict": "NO_COGNITIVE_ADMISSION_WITHOUT_AUTHOR_SEMANTIC_RECEIPTS",
    }
