"""Architect B5 exact handoff/disposition ledger for B-11..B-15."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from enum import StrEnum

from qore.infrastructure.core_stack_v2.shared_b5_asset_world_disposition import (
    assess_agricultural_world,
    assess_commodity_world,
)


class B5WorkDisposition(StrEnum):
    DEPENDENCY_BLOCKED = "DEPENDENCY_BLOCKED"
    READY_FOR_EMPIRICAL_POPULATION = "READY_FOR_EMPIRICAL_POPULATION"
    KNOWN_BLINDSPOT = "KNOWN_BLINDSPOT"
    GOVERNED_UNKNOWN = "GOVERNED_UNKNOWN"
    COMPLETE_AND_PROVEN = "COMPLETE_AND_PROVEN"


def _fingerprint(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            default=str,
        ).encode("utf-8")
    ).hexdigest()


def _validate_empirical_flag(name: str, value: bool) -> None:
    if type(value) is not bool:
        raise ValueError(f"{name} must be bool")


def _relational_disposition(
    *,
    population_ready: bool,
    empirical_complete: bool,
    blocked_codes: tuple[str, ...],
    empirical_requirement_code: str,
) -> tuple[str, list[str]]:
    if empirical_complete:
        if not population_ready:
            raise ValueError(
                "empirical relational completion requires B4 comparability authority"
            )
        return B5WorkDisposition.COMPLETE_AND_PROVEN.value, []
    if population_ready:
        return (
            B5WorkDisposition.READY_FOR_EMPIRICAL_POPULATION.value,
            [empirical_requirement_code],
        )
    return B5WorkDisposition.DEPENDENCY_BLOCKED.value, list(blocked_codes)


def build_b5_handoff(
    *,
    b4_comparability_eligible_count: int,
    b4_relational_comparability_authorized: bool,
    b11_empirical_population_complete: bool = False,
    b12_empirical_population_complete: bool = False,
    b13_empirical_population_complete: bool = False,
) -> dict[str, object]:
    """Build B5 truth without upgrading authorization into scientific proof."""

    if (
        type(b4_comparability_eligible_count) is not int
        or b4_comparability_eligible_count < 0
    ):
        raise ValueError("B4 comparability eligible count invalid")
    if type(b4_relational_comparability_authorized) is not bool:
        raise ValueError("B4 relational comparability authority must be bool")

    _validate_empirical_flag(
        "b11_empirical_population_complete",
        b11_empirical_population_complete,
    )
    _validate_empirical_flag(
        "b12_empirical_population_complete",
        b12_empirical_population_complete,
    )
    _validate_empirical_flag(
        "b13_empirical_population_complete",
        b13_empirical_population_complete,
    )

    relational_population_ready = (
        b4_relational_comparability_authorized
        and b4_comparability_eligible_count > 0
    )
    blocked_codes: list[str] = []
    if not b4_relational_comparability_authorized:
        blocked_codes.append("B08_RELATIONAL_COMPARABILITY_NOT_AUTHORIZED")
    if b4_comparability_eligible_count == 0:
        blocked_codes.append("ZERO_COMPARABILITY_ELIGIBLE_SENSORS")
    relational_blockers = tuple(blocked_codes)

    b11_disposition, b11_blockers = _relational_disposition(
        population_ready=relational_population_ready,
        empirical_complete=b11_empirical_population_complete,
        blocked_codes=relational_blockers,
        empirical_requirement_code="B11_EMPIRICAL_POPULATION_NOT_EXECUTED",
    )
    b12_disposition, b12_blockers = _relational_disposition(
        population_ready=relational_population_ready,
        empirical_complete=b12_empirical_population_complete,
        blocked_codes=relational_blockers,
        empirical_requirement_code="B12_EMPIRICAL_POPULATION_NOT_EXECUTED",
    )
    b13_disposition, b13_blockers = _relational_disposition(
        population_ready=relational_population_ready,
        empirical_complete=b13_empirical_population_complete,
        blocked_codes=relational_blockers,
        empirical_requirement_code="B13_EMPIRICAL_POPULATION_NOT_EXECUTED",
    )

    agriculture = assess_agricultural_world(
        authorized_provider_count=1,
        agricultural_candidate_count=0,
        soft_candidate_count=0,
        livestock_candidate_count=0,
        secondary_provider_owner_authorized=False,
        secondary_provider_scientifically_admitted=False,
        proxy_agriculture_used=False,
        evidence_refs=(
            "artifact:11059457712",
            "artifact:11126270432",
            "artifact:11128508597",
            "run:36623645085",
            "run:36777269692",
            "run:36783743044",
        ),
    )
    commodity = assess_commodity_world(
        metal_reference_object_count=11,
        metal_provider_neutral_identity_count=0,
        energy_reference_object_count=3,
        energy_provider_neutral_identity_count=0,
        dated_gc_contract_count=5,
        expired_gc_contract_count=5,
        current_front_contract_verified_count=0,
        roll_semantics_verified=False,
        continuous_series_verified=False,
        venue_identity_verified=False,
        evidence_refs=(
            "artifact:11115769948",
            "artifact:11128416668",
            "artifact:11128739693",
            "artifact:11129012317",
            "run:36755839843",
            "run:36782329462",
            "run:36784542345",
            "run:36784810864",
        ),
    )

    items = [
        {
            "work_id": "B-11",
            "title": "Relationship Lifecycle",
            "functional_engine_implemented": True,
            "required_states": ["BIRTH", "ACTIVE", "DEGRADED", "STALE", "DEAD"],
            "empirical_population_complete": b11_empirical_population_complete,
            "disposition": b11_disposition,
            "blockers": b11_blockers,
            "outcome_used": False,
            "productive_authority": False,
        },
        {
            "work_id": "B-12",
            "title": "Lead-Lag Observability",
            "functional_engine_implemented": True,
            "temporal_precedence_is_causation": False,
            "empirical_population_complete": b12_empirical_population_complete,
            "disposition": b12_disposition,
            "blockers": b12_blockers,
            "outcome_used": False,
            "productive_authority": False,
        },
        {
            "work_id": "B-13",
            "title": "Structural Divergence",
            "functional_engine_implemented": True,
            "fully_comparable_window_required": True,
            "empirical_population_complete": b13_empirical_population_complete,
            "disposition": b13_disposition,
            "blockers": b13_blockers,
            "outcome_used": False,
            "productive_authority": False,
        },
        {
            "work_id": "B-14",
            "title": "Agricultural World",
            "functional_engine_implemented": True,
            "disposition": B5WorkDisposition.KNOWN_BLINDSPOT.value,
            "asset_world_receipt": asdict(agriculture),
            "blockers": list(agriculture.blocker_codes),
            "proxy_used": False,
            "productive_authority": False,
        },
        {
            "work_id": "B-15",
            "title": "Commodity World",
            "functional_engine_implemented": True,
            "disposition": B5WorkDisposition.GOVERNED_UNKNOWN.value,
            "asset_world_receipt": asdict(commodity),
            "blockers": list(commodity.blocker_codes),
            "inference_used": False,
            "productive_authority": False,
        },
    ]
    empirical_relational_population_complete = (
        relational_population_ready
        and b11_empirical_population_complete
        and b12_empirical_population_complete
        and b13_empirical_population_complete
    )
    payload: dict[str, object] = {
        "identity": "SHARED_ARCHITECT_B5_RELATIONAL_ASSET_WORLD_HANDOFF_001",
        "owned_work_ids": ["B-11", "B-12", "B-13", "B-14", "B-15"],
        "b4_comparability_eligible_count": b4_comparability_eligible_count,
        "b4_relational_comparability_authorized": (
            b4_relational_comparability_authorized
        ),
        "items": items,
        "functional_engine_count": 5,
        "functional_engine_implemented_count": 5,
        "complete_and_proven_count": sum(
            item["disposition"] == B5WorkDisposition.COMPLETE_AND_PROVEN.value
            for item in items
        ),
        "dependency_blocked_count": sum(
            item["disposition"] == B5WorkDisposition.DEPENDENCY_BLOCKED.value
            for item in items
        ),
        "known_blindspot_count": 1,
        "governed_unknown_count": 1,
        "engineering_open_count": 0,
        "empirical_relational_population_complete": (
            empirical_relational_population_complete
        ),
        "b5_scientific_closure_complete": all(
            item["disposition"] == B5WorkDisposition.COMPLETE_AND_PROVEN.value
            for item in items
        ),
        "handoff_to_integrator_3_ready": True,
        "fresh_holdout_opened": False,
        "target_or_outcome_read": False,
        "broker_mutation": False,
        "live": False,
        "production": False,
        "real_capital": False,
        "execution_authority": False,
        "risk_authority": False,
        "sizing_authority": False,
    }
    payload["handoff_fingerprint_sha256"] = _fingerprint(payload)
    return payload
