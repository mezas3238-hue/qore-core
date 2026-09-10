"""Independent eleven-market thesis review for one frozen Trader dossier.

This layer sits above per-market and per-episode Story Forensics. It forces every
reviewer to explain one Trader across the same eleven-market evidence universe
without seeing peer conclusions during the machine first pass.
"""

from __future__ import annotations

import json
from copy import deepcopy
from enum import StrEnum
from hashlib import sha256
from typing import cast

from qore.infrastructure.trader_lab.story_forensics_review_panel import ReviewRole

_DOSSIER_SCHEMA = "qore.trader_lab.eleven_market_trader_research_dossier.v1"
_PANEL_SCHEMA = "qore.trader_lab.eleven_market_trader_thesis_panel.v1"
_REQUIRED_MARKETS = (
    "EURUSD",
    "GBPUSD",
    "USDJPY",
    "AUDUSD",
    "USDCAD",
    "XAUUSD",
    "NAS100",
    "SP500",
    "GBPJPY",
    "AUDJPY",
    "US30",
)
_MACHINE_ROLES = (
    ReviewRole.HARNESS,
    ReviewRole.EXPERT,
    ReviewRole.WORK,
    ReviewRole.ARCHITECT,
)
_REQUIRED_ROLES = (*_MACHINE_ROLES, ReviewRole.HUMAN_OWNER)


class ElevenMarketThesisError(ValueError):
    """Raised when a Trader thesis weakens the eleven-market review contract."""

    __slots__ = ()


class VerdictFamily(StrEnum):
    """High-level research families for a cross-market Trader conclusion."""

    ROBUST_CROSS_MARKET = "ROBUST_CROSS_MARKET"
    SPECIALIST = "SPECIALIST"
    MARKET_DEPENDENT = "MARKET_DEPENDENT"
    SESSION_DEPENDENT = "SESSION_DEPENDENT"
    DIRECTION_DEPENDENT = "DIRECTION_DEPENDENT"
    REGIME_DEPENDENT = "REGIME_DEPENDENT"
    STRUCTURAL_WEAKNESS = "STRUCTURAL_WEAKNESS"
    MIXED_UNRESOLVED = "MIXED_UNRESOLVED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


def _object(value: object, *, field_name: str) -> dict[str, object]:
    if type(value) is not dict or any(type(key) is not str for key in value):
        raise ElevenMarketThesisError(f"{field_name} must be a JSON object")
    return cast(dict[str, object], value)


def _array(value: object, *, field_name: str) -> list[object]:
    if type(value) is not list:
        raise ElevenMarketThesisError(f"{field_name} must be a JSON array")
    return cast(list[object], value)


def _text(value: object, *, field_name: str) -> str:
    if type(value) is not str or not value:
        raise ElevenMarketThesisError(f"{field_name} must be non-empty text")
    return value


def _strict_bool(value: object, *, field_name: str) -> bool:
    if type(value) is not bool:
        raise ElevenMarketThesisError(f"{field_name} must be bool")
    return value


def _string_list(
    value: object,
    *,
    field_name: str,
    allow_empty: bool = False,
) -> list[str]:
    rows = _array(value, field_name=field_name)
    if not rows and not allow_empty:
        raise ElevenMarketThesisError(f"{field_name} cannot be empty")
    result = [_text(item, field_name=field_name) for item in rows]
    if len(set(result)) != len(result):
        raise ElevenMarketThesisError(f"{field_name} cannot contain duplicates")
    return result


def _canonical(value: object) -> str:
    try:
        return json.dumps(
            value,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as error:
        raise ElevenMarketThesisError("thesis payload must be canonical JSON") from error


def _digest(value: object) -> str:
    return sha256(_canonical(value).encode("utf-8")).hexdigest()


def _validate_dossier(
    dossier: dict[str, object],
) -> tuple[str, list[dict[str, object]]]:
    if _text(dossier.get("schema"), field_name="dossier schema") != _DOSSIER_SCHEMA:
        raise ElevenMarketThesisError("eleven-market thesis requires research dossier v1")
    if not _strict_bool(dossier.get("research_only"), field_name="research_only"):
        raise ElevenMarketThesisError("dossier must be research-only")
    if _strict_bool(dossier.get("execution_authority"), field_name="execution_authority"):
        raise ElevenMarketThesisError("dossier cannot carry execution authority")
    trader_code = _text(dossier.get("trader_code"), field_name="trader_code")
    markets = [
        _object(item, field_name="market evidence")
        for item in _array(dossier.get("markets"), field_name="markets")
    ]
    if len(markets) != len(_REQUIRED_MARKETS):
        raise ElevenMarketThesisError("dossier must contain exactly eleven markets")
    symbols = [_text(row.get("symbol"), field_name="market symbol") for row in markets]
    if len(set(symbols)) != len(symbols):
        raise ElevenMarketThesisError("dossier cannot contain duplicate markets")
    if set(symbols) != set(_REQUIRED_MARKETS):
        raise ElevenMarketThesisError("dossier market universe does not match QORE eleven")
    for row in markets:
        if not _strict_bool(row.get("evidence_ready"), field_name="evidence_ready"):
            raise ElevenMarketThesisError("all eleven markets must be evidence-ready")
        _text(row.get("evidence_digest"), field_name="evidence_digest")
        summary = _object(row.get("summary"), field_name="market summary")
        _object(summary.get("story_forensics"), field_name="story_forensics")
        characterization = _object(
            summary.get("characterization"),
            field_name="characterization",
        )
        walk_forward = _object(
            characterization.get("walk_forward_assessment"),
            field_name="walk_forward_assessment",
        )
        _strict_bool(walk_forward.get("oos_pass"), field_name="oos_pass")
        _strict_bool(walk_forward.get("stress_pass"), field_name="stress_pass")
        _object(summary.get("provenance"), field_name="market provenance")
    observed_fingerprint = _text(
        dossier.get("dossier_fingerprint"),
        field_name="dossier_fingerprint",
    )
    fingerprint_material = deepcopy(dossier)
    fingerprint_material.pop("dossier_fingerprint", None)
    if _digest(fingerprint_material) != observed_fingerprint:
        raise ElevenMarketThesisError("research dossier fingerprint mismatch")
    return trader_code, markets


def _empty_lanes() -> dict[str, object]:
    return {
        role.value: {
            "status": "PENDING",
            "assessment": None,
            "assessment_digest": None,
        }
        for role in _REQUIRED_ROLES
    }


def build_eleven_market_thesis_panel(
    dossier: dict[str, object],
) -> dict[str, object]:
    """Create one sealed-review ledger for a Trader across all eleven markets."""
    trader_code, markets = _validate_dossier(dossier)
    evidence_index = {
        _text(row.get("symbol"), field_name="market symbol"): _text(
            row.get("evidence_digest"),
            field_name="evidence_digest",
        )
        for row in markets
    }
    return {
        "schema": _PANEL_SCHEMA,
        "research_only": True,
        "execution_authority": False,
        "trader_code": trader_code,
        "dossier_digest": _digest(dossier),
        "required_markets": list(_REQUIRED_MARKETS),
        "market_evidence_index": dict(sorted(evidence_index.items())),
        "review_protocol": {
            "machine_first_pass_independent": True,
            "human_after_machine_first_pass": True,
            "majority_vote_is_truth": False,
            "disagreement_retained": True,
            "exceptions_must_be_explained": True,
            "market_omission_allowed": False,
            "market_evidence_digest_binding_required": True,
            "direct_methodology_mutation_allowed": False,
            "fresh_holdout_required_after_change": True,
        },
        "frozen_dossier": deepcopy(dossier),
        "review_lanes": _empty_lanes(),
        "synthesis_status": "BLOCKED_PENDING_REVIEWS",
    }


def _role(value: object) -> ReviewRole:
    raw = _text(value, field_name="role")
    try:
        return ReviewRole(raw)
    except ValueError as error:
        raise ElevenMarketThesisError("unknown review role") from error


def _verdict(value: object) -> VerdictFamily:
    raw = _text(value, field_name="verdict_family")
    try:
        return VerdictFamily(raw)
    except ValueError as error:
        raise ElevenMarketThesisError("unknown verdict family") from error


def _market_evidence_index(value: object) -> dict[str, str]:
    rows = _object(value, field_name="market_evidence_index")
    if set(rows) != set(_REQUIRED_MARKETS):
        raise ElevenMarketThesisError("market evidence index must cover all eleven markets")
    return {
        symbol: _text(rows.get(symbol), field_name=f"{symbol} evidence digest")
        for symbol in _REQUIRED_MARKETS
    }


def _required_output_contract(
    evidence_index: dict[str, str],
) -> dict[str, object]:
    return {
        "verdict_family": [item.value for item in VerdictFamily],
        "central_conclusion": "plain-language thesis across all eleven markets",
        "rationale": "one or more evidence-grounded reasons",
        "common_patterns": "repeated behavior across multiple markets",
        "material_exceptions": "contradictory markets or explicit NONE",
        "strengths_to_preserve": "one or more protected characteristics",
        "degradation_risks": "one or more behaviors/changes that may weaken the Trader",
        "evidence_by_market": {
            symbol: {
                "evidence_digest": evidence_index[symbol],
                "findings": "one or more findings grounded in this exact market evidence",
            }
            for symbol in _REQUIRED_MARKETS
        },
        "causal_hypothesis": "provisional mechanism explaining the thesis",
        "counterexample_or_falsifier": "what evidence would overturn the conclusion",
        "confidence": ["low", "medium", "high"],
        "fresh_holdout_required_for_changes": True,
    }


def reviewer_packet(
    panel: dict[str, object],
    *,
    role: ReviewRole,
) -> dict[str, object]:
    """Return a first-pass packet without peer conclusions for machine reviewers."""
    if _text(panel.get("schema"), field_name="panel schema") != _PANEL_SCHEMA:
        raise ElevenMarketThesisError("unexpected thesis panel schema")
    lanes = _object(panel.get("review_lanes"), field_name="review_lanes")
    evidence_index = _market_evidence_index(panel.get("market_evidence_index"))
    packet = {
        "trader_code": _text(panel.get("trader_code"), field_name="trader_code"),
        "dossier_digest": _text(panel.get("dossier_digest"), field_name="dossier_digest"),
        "market_evidence_index": deepcopy(evidence_index),
        "frozen_dossier": deepcopy(panel.get("frozen_dossier")),
        "role": role.value,
        "required_output": _required_output_contract(evidence_index),
    }
    if role is ReviewRole.HUMAN_OWNER:
        sealed: dict[str, object] = {}
        for machine_role in _MACHINE_ROLES:
            lane = _object(lanes.get(machine_role.value), field_name="review lane")
            if lane.get("status") != "SEALED":
                raise ElevenMarketThesisError(
                    "human review is blocked until machine first passes are sealed"
                )
            sealed[machine_role.value] = deepcopy(lane.get("assessment"))
        packet["mode"] = "human_adjudication"
        packet["sealed_machine_reviews"] = sealed
        return packet
    packet["mode"] = "independent_first_pass"
    return packet


def _validate_evidence_by_market(
    value: object,
    *,
    evidence_index: dict[str, str],
) -> dict[str, dict[str, object]]:
    rows = _object(value, field_name="evidence_by_market")
    if set(rows) != set(_REQUIRED_MARKETS):
        raise ElevenMarketThesisError("assessment must address all eleven markets")
    result: dict[str, dict[str, object]] = {}
    for symbol in _REQUIRED_MARKETS:
        row = _object(rows.get(symbol), field_name=f"{symbol} evidence")
        evidence_digest = _text(
            row.get("evidence_digest"),
            field_name=f"{symbol} evidence_digest",
        )
        if evidence_digest != evidence_index[symbol]:
            raise ElevenMarketThesisError(f"{symbol} evidence digest mismatch")
        findings = _string_list(
            row.get("findings"),
            field_name=f"{symbol} findings",
        )
        if set(row) != {"evidence_digest", "findings"}:
            raise ElevenMarketThesisError(
                f"{symbol} evidence must contain only evidence_digest and findings"
            )
        result[symbol] = {
            "evidence_digest": evidence_digest,
            "findings": findings,
        }
    return result


def _validate_assessment(
    assessment: dict[str, object],
    *,
    dossier_digest: str,
    evidence_index: dict[str, str],
) -> ReviewRole:
    if _text(assessment.get("dossier_digest"), field_name="dossier_digest") != dossier_digest:
        raise ElevenMarketThesisError("assessment dossier digest mismatch")
    role = _role(assessment.get("role"))
    _verdict(assessment.get("verdict_family"))
    _text(assessment.get("central_conclusion"), field_name="central_conclusion")
    _string_list(assessment.get("rationale"), field_name="rationale")
    _string_list(assessment.get("common_patterns"), field_name="common_patterns")
    _string_list(
        assessment.get("material_exceptions"),
        field_name="material_exceptions",
    )
    _string_list(
        assessment.get("strengths_to_preserve"),
        field_name="strengths_to_preserve",
    )
    _string_list(assessment.get("degradation_risks"), field_name="degradation_risks")
    _validate_evidence_by_market(
        assessment.get("evidence_by_market"),
        evidence_index=evidence_index,
    )
    _text(assessment.get("causal_hypothesis"), field_name="causal_hypothesis")
    _text(
        assessment.get("counterexample_or_falsifier"),
        field_name="counterexample_or_falsifier",
    )
    confidence = _text(assessment.get("confidence"), field_name="confidence")
    if confidence not in {"low", "medium", "high"}:
        raise ElevenMarketThesisError("confidence must be low, medium or high")
    if not _strict_bool(
        assessment.get("fresh_holdout_required_for_changes"),
        field_name="fresh_holdout_required_for_changes",
    ):
        raise ElevenMarketThesisError("methodology-changing conclusions require fresh holdout")
    return role


def seal_assessment(
    panel: dict[str, object],
    *,
    assessment: dict[str, object],
) -> dict[str, object]:
    """Seal one role exactly once while preserving first-pass independence."""
    result = deepcopy(panel)
    dossier_digest = _text(result.get("dossier_digest"), field_name="dossier_digest")
    evidence_index = _market_evidence_index(result.get("market_evidence_index"))
    role = _validate_assessment(
        assessment,
        dossier_digest=dossier_digest,
        evidence_index=evidence_index,
    )
    lanes = _object(result.get("review_lanes"), field_name="review_lanes")
    lane = _object(lanes.get(role.value), field_name="review lane")
    if lane.get("status") != "PENDING":
        raise ElevenMarketThesisError("review lane is already sealed")
    if role is ReviewRole.HUMAN_OWNER:
        for machine_role in _MACHINE_ROLES:
            machine_lane = _object(lanes.get(machine_role.value), field_name="review lane")
            if machine_lane.get("status") != "SEALED":
                raise ElevenMarketThesisError(
                    "human review cannot seal before all machine first passes"
                )
    else:
        human_lane = _object(lanes.get(ReviewRole.HUMAN_OWNER.value), field_name="human lane")
        if human_lane.get("status") == "SEALED":
            raise ElevenMarketThesisError("machine review cannot follow human adjudication")
    lane["status"] = "SEALED"
    lane["assessment"] = deepcopy(assessment)
    lane["assessment_digest"] = _digest(assessment)
    if all(
        _object(lanes.get(item.value), field_name="review lane").get("status") == "SEALED"
        for item in _REQUIRED_ROLES
    ):
        result["synthesis_status"] = "READY_FOR_SYNTHESIS"
    return result


def synthesize_eleven_market_thesis(panel: dict[str, object]) -> dict[str, object]:
    """Expose all sealed verdicts without converting majority opinion into truth."""
    lanes = _object(panel.get("review_lanes"), field_name="review_lanes")
    reviews: dict[str, object] = {}
    verdict_counts: dict[str, int] = {}
    for role in _REQUIRED_ROLES:
        lane = _object(lanes.get(role.value), field_name="review lane")
        if lane.get("status") != "SEALED":
            raise ElevenMarketThesisError("thesis synthesis requires all five reviews")
        assessment = _object(lane.get("assessment"), field_name="assessment")
        reviews[role.value] = deepcopy(assessment)
        verdict = _verdict(assessment.get("verdict_family")).value
        verdict_counts[verdict] = verdict_counts.get(verdict, 0) + 1
    return {
        "schema": "qore.trader_lab.eleven_market_trader_thesis_synthesis.v1",
        "state": "RESEARCH_SYNTHESIS_ONLY",
        "research_only": True,
        "execution_authority": False,
        "trader_code": _text(panel.get("trader_code"), field_name="trader_code"),
        "dossier_digest": _text(panel.get("dossier_digest"), field_name="dossier_digest"),
        "reviews": reviews,
        "verdict_counts": dict(sorted(verdict_counts.items())),
        "majority_vote_is_truth": False,
        "disagreement_retained": True,
        "human_adjudication_required": True,
        "fresh_holdout_required_for_changes": True,
    }
