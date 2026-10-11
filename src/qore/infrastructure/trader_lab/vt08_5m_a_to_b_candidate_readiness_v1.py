"""Fail-closed, research-only independent check of Architect A -> B envelope.

Readiness is NOT a trading signal or a proof that source-derived feature values
are correct. It checks shape, clocks and missing provenance BEFORE any
Cognitive V1 Situation Model can be constructed. A retains source authority.
"""
from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Final

from qore.infrastructure.traders.vt08_cognitive_5m_research_scope import (
    CAUSAL_FIELDS,
    RESEARCH_MARKETS,
)

SCHEMA: Final = "VT08_5M_CANDIDATE_EVENT_V1"
SOURCE_ID: Final = re.compile(r"vt08-5m-source:[0-9a-f]{64}\Z")
HEX: Final = re.compile(r"[0-9a-f]{64}\Z")
CAUSAL_SOURCE_KEYS: Final = ("source_h4", "cisd", "protected_swing")
# NO jointly signed A/B source-situation manifest exists. A caller-supplied
# boolean is never acceptable evidence of an approved integration contract.
APPROVED_A_B_MANIFEST_SHA256: Final[str | None] = None


class Vt08CandidateBoundaryError(ValueError):
    """Invalid/unsafe A-originated envelope: never pass to cognitive replay."""


@dataclass(frozen=True, slots=True)
class Vt08CandidateReadiness:
    source_event_id: str
    snapshot_event_id: str
    market: str
    decision_at: datetime
    blockers: tuple[str, ...]
    cognitive_ready: bool
    research_only: bool = True
    order_authorized: bool = False


def _timestamp(raw: object, name: str) -> datetime:
    if not isinstance(raw, str):
        raise Vt08CandidateBoundaryError(f"{name} must be ISO-8601 text")
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise Vt08CandidateBoundaryError(f"{name} has invalid timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise Vt08CandidateBoundaryError(f"{name} must be timezone-aware")
    return parsed.astimezone(UTC)


def inspect_architect_a_candidate(
    envelope: Mapping[str, object],
    *,
    joint_contract_manifest_sha256: str | None = None,
) -> Vt08CandidateReadiness:
    """Never turn incomplete source into a cognition EXECUTE decision.

    Current A V1 B01 has bias_feature_cutoff UNATTESTED and does not supply all
    Cognitive V1 situation field timestamps. The truthful answer is blocked,
    not an invented set of confirmations.
    """
    if envelope.get("schema") != SCHEMA:
        raise Vt08CandidateBoundaryError("A->B candidate schema mismatch")
    source_id = envelope.get("source_event_id")
    fingerprint = envelope.get("event_fingerprint")
    event_id = envelope.get("event_id")
    if not isinstance(source_id, str) or SOURCE_ID.fullmatch(source_id) is None:
        raise Vt08CandidateBoundaryError("invalid stable source_event_id")
    if not isinstance(fingerprint, str) or HEX.fullmatch(fingerprint) is None:
        raise Vt08CandidateBoundaryError("invalid event_fingerprint")
    if event_id != f"vt08-5m:{fingerprint}":
        raise Vt08CandidateBoundaryError("event_id must match snapshot fingerprint")
    market = envelope.get("market")
    if not isinstance(market, str) or market not in RESEARCH_MARKETS:
        raise Vt08CandidateBoundaryError("candidate market outside research 5M")
    if envelope.get("research_only") is not True:
        raise Vt08CandidateBoundaryError("candidate lacks research-only authority")
    if (
        envelope.get("execution_authorized") is not False
        or envelope.get("live_authorized") is not False
    ):
        raise Vt08CandidateBoundaryError("A candidate cannot grant execution")
    if envelope.get("source_family") != "positional-entry":
        raise Vt08CandidateBoundaryError("unfrozen A source family")
    if envelope.get("ltf_profile") != "M15_STANDARD":
        raise Vt08CandidateBoundaryError("unfrozen A LTF profile")
    if envelope.get("methodology_status") != "SOURCE_COMPLETE_EXECUTABLE":
        raise Vt08CandidateBoundaryError("source bundle not executable")
    anchor = envelope.get("anchor_ny_hour")
    if type(anchor) is not int or anchor not in (1, 5, 9):
        raise Vt08CandidateBoundaryError("anchor outside Owner 01/05/09")

    decision = _timestamp(envelope.get("decision_at"), "decision_at")
    observed = _timestamp(envelope.get("evidence_as_of"), "evidence_as_of")
    expiry = _timestamp(envelope.get("pending_expiry_at"), "pending_expiry_at")
    if observed > decision or expiry <= decision:
        raise Vt08CandidateBoundaryError("A source event has invalid causal window")
    feature_times = envelope.get("feature_close_cutoffs")
    if not isinstance(feature_times, dict) or set(feature_times) != set(
        CAUSAL_SOURCE_KEYS
    ):
        raise Vt08CandidateBoundaryError("missing source confirmation cutoffs")
    for name in CAUSAL_SOURCE_KEYS:
        if _timestamp(feature_times[name], name) > decision:
            raise Vt08CandidateBoundaryError("future source confirmation forbidden")

    blockers: list[str] = []
    raw_bias = envelope.get("bias_feature_cutoff")
    if raw_bias == "UNATTESTED_IN_LEGACY_B01_CANDIDATE":
        blockers.append("A_B:DAILY_BIAS_SOURCE_TIME_UNATTESTED")
    elif _timestamp(raw_bias, "bias_feature_cutoff") > decision:
        raise Vt08CandidateBoundaryError("future bias evidence forbidden")
    features = envelope.get("cognitive_feature_cutoffs")
    if not isinstance(features, dict) or set(features) != set(CAUSAL_FIELDS):
        blockers.append("A_B:COGNITIVE_FEATURE_PROVENANCE_INCOMPLETE")
    else:
        for name in CAUSAL_FIELDS:
            if _timestamp(features[name], name) > decision:
                raise Vt08CandidateBoundaryError("future cognitive feature forbidden")

    if (
        APPROVED_A_B_MANIFEST_SHA256 is None
        or joint_contract_manifest_sha256 != APPROVED_A_B_MANIFEST_SHA256
    ):
        blockers.append("A_B:CONTRACT_NOT_JOINTLY_FROZEN")
    return Vt08CandidateReadiness(
        source_event_id=source_id,
        snapshot_event_id=event_id,
        market=market,
        decision_at=decision,
        blockers=tuple(blockers),
        cognitive_ready=not blockers,
    )
