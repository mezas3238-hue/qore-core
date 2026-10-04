"""Scope-level admission gate for Architect-3 consumption of B4 world facts.

Integrator 2 uses explicit required instrument keys. No global claim may be
inferred from unrelated healthy facts or from partial coverage elsewhere.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.core_stack_v2.shared_a3_b4_seam_contract import (
    SharedA3B4CalendarStatus,
    SharedA3B4TemporalStatus,
    SharedA3B4WorldFact,
)


class SharedA3B4ScopeGateError(ValueError):
    """Scope gate input is invalid."""


class SharedA3B4ScopeBlocker(StrEnum):
    MISSING_FACT = "MISSING_FACT"
    IDENTITY_UNRESOLVED = "IDENTITY_UNRESOLVED"
    MARKET_TIME_UNRESOLVED = "MARKET_TIME_UNRESOLVED"
    TEMPORAL_NOT_COMPARABLE = "TEMPORAL_NOT_COMPARABLE"
    DATA_HEALTH_NOT_READY = "DATA_HEALTH_NOT_READY"
    RELATION_INELIGIBLE = "RELATION_INELIGIBLE"


@dataclass(frozen=True, slots=True)
class SharedA3B4ScopeResult:
    required_instrument_keys: tuple[str, ...]
    ready_instrument_keys: tuple[str, ...]
    blocked: tuple[tuple[str, tuple[SharedA3B4ScopeBlocker, ...]], ...]
    require_relation_claims: bool
    a3_scope_consumption_allowed: bool
    a3_scope_relation_claim_allowed: bool
    global_inference_from_unrequested_facts_allowed: bool = False

    def __post_init__(self) -> None:
        if not self.required_instrument_keys:
            raise SharedA3B4ScopeGateError("required scope cannot be empty")
        if self.required_instrument_keys != tuple(
            sorted(set(self.required_instrument_keys))
        ):
            raise SharedA3B4ScopeGateError(
                "required instrument keys must be unique and canonical"
            )
        if self.ready_instrument_keys != tuple(sorted(set(self.ready_instrument_keys))):
            raise SharedA3B4ScopeGateError(
                "ready instrument keys must be unique and canonical"
            )
        if self.global_inference_from_unrequested_facts_allowed:
            raise SharedA3B4ScopeGateError(
                "scope gate cannot infer global readiness from unrelated facts"
            )


def assess_a3_b4_scope(
    *,
    facts: Iterable[SharedA3B4WorldFact],
    required_instrument_keys: tuple[str, ...],
    require_relation_claims: bool = False,
) -> SharedA3B4ScopeResult:
    """Assess only the explicitly requested A3 world scope."""

    if not required_instrument_keys:
        raise SharedA3B4ScopeGateError("required scope cannot be empty")
    required = tuple(sorted(set(required_instrument_keys)))
    if required != required_instrument_keys:
        raise SharedA3B4ScopeGateError(
            "required instrument keys must be unique and canonical"
        )

    by_key: dict[str, SharedA3B4WorldFact] = {}
    for fact in facts:
        if fact.instrument_key in by_key:
            raise SharedA3B4ScopeGateError(
                f"duplicate world fact: {fact.instrument_key}"
            )
        by_key[fact.instrument_key] = fact

    ready: list[str] = []
    blocked: list[tuple[str, tuple[SharedA3B4ScopeBlocker, ...]]] = []
    for key in required:
        scope_fact = by_key.get(key)
        reasons: list[SharedA3B4ScopeBlocker] = []
        if scope_fact is None:
            reasons.append(SharedA3B4ScopeBlocker.MISSING_FACT)
        else:
            if not scope_fact.identity_resolved:
                reasons.append(SharedA3B4ScopeBlocker.IDENTITY_UNRESOLVED)
            if (
                scope_fact.calendar_status
                is not SharedA3B4CalendarStatus.VERIFIED_CANONICAL
            ):
                reasons.append(SharedA3B4ScopeBlocker.MARKET_TIME_UNRESOLVED)
            if scope_fact.temporal_status is not SharedA3B4TemporalStatus.COMPARABLE:
                reasons.append(SharedA3B4ScopeBlocker.TEMPORAL_NOT_COMPARABLE)
            if scope_fact.data_health_state != "HEALTHY":
                reasons.append(SharedA3B4ScopeBlocker.DATA_HEALTH_NOT_READY)
            if require_relation_claims and not scope_fact.relation_claim_allowed:
                reasons.append(SharedA3B4ScopeBlocker.RELATION_INELIGIBLE)
        if reasons:
            blocked.append((key, tuple(reasons)))
        else:
            ready.append(key)

    consumption_allowed = not blocked and len(ready) == len(required)
    relation_allowed = consumption_allowed and (
        not require_relation_claims
        or all(by_key[key].relation_claim_allowed for key in required)
    )
    return SharedA3B4ScopeResult(
        required_instrument_keys=required,
        ready_instrument_keys=tuple(ready),
        blocked=tuple(blocked),
        require_relation_claims=require_relation_claims,
        a3_scope_consumption_allowed=consumption_allowed,
        a3_scope_relation_claim_allowed=relation_allowed,
    )
