"""Integrator-2 intake reducer for B4 B-06/B-07 evidence.

This reducer repairs the A3<->B4 seam without inventing identity, calendar or
comparability. It consumes B4 terminal epistemic registries plus the exact B
identity frontier that carries explicit reference keys. A verified B-06 row is
promoted across the seam only when that explicit key is present upstream.

Current B-07 truth has zero canonical calendar bindings and zero comparable
relations, therefore every emitted fact remains NOT_COMPARABLE and relation
ineligible. This is an honest partial integration, not a completion claim.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import cast

from qore.infrastructure.core_stack_v2.shared_a3_b4_seam_contract import (
    SharedA3B4CalendarStatus,
    SharedA3B4IdentityStatus,
    SharedA3B4RelationEligibility,
    SharedA3B4TemporalStatus,
    SharedA3B4WorldFact,
)

B06_IDENTITY = "SHARED_B4_GLOBAL_IDENTITY_DISPOSITION_001"
B07_IDENTITY = "SHARED_B4_TEMPORAL_DISPOSITION_REGISTRY_001"
FRONTIER_IDENTITY = "SHARED_B_GLOBAL_IDENTITY_FRONTIER_V3_001"
EXPECTED_SENSOR_COUNT = 177


class SharedA3B4IntakeError(ValueError):
    """B4 intake evidence is inconsistent or widens authority."""


def _key(row: dict[str, object]) -> tuple[str, int]:
    provider = row.get("provider")
    symbol_id = row.get("provider_symbol_id")
    if not isinstance(provider, str) or not provider.strip():
        raise SharedA3B4IntakeError("provider identity missing")
    if type(symbol_id) is not int or symbol_id <= 0:
        raise SharedA3B4IntakeError("provider_symbol_id invalid")
    return provider, symbol_id


def _index(
    payload: dict[str, object],
    *,
    field: str = "records",
) -> dict[tuple[str, int], dict[str, object]]:
    raw_records = payload.get(field)
    if not isinstance(raw_records, list) or len(raw_records) != EXPECTED_SENSOR_COUNT:
        raise SharedA3B4IntakeError(f"{field} must contain exact 177 records")
    output: dict[tuple[str, int], dict[str, object]] = {}
    for raw in raw_records:
        if not isinstance(raw, dict):
            raise SharedA3B4IntakeError(f"{field} row invalid")
        row = cast(dict[str, object], raw)
        key = _key(row)
        if key in output:
            raise SharedA3B4IntakeError(f"duplicate provider identity in {field}")
        output[key] = row
    return output


def _explicit_identity(
    *,
    disposition: str,
    frontier: dict[str, object],
) -> tuple[SharedA3B4IdentityStatus, str | None]:
    if disposition == "CURRENT_REFERENCE_VERIFIED":
        candidates = tuple(
            value
            for value in (
                frontier.get("canonical_reference_identity"),
                frontier.get("observation_identity"),
            )
            if isinstance(value, str) and value.strip()
        )
        unique = tuple(dict.fromkeys(candidates))
        if len(unique) != 1:
            raise SharedA3B4IntakeError(
                "verified current reference lacks one explicit upstream identity"
            )
        return (
            SharedA3B4IdentityStatus.PROVIDER_NEUTRAL_REFERENCE_VERIFIED,
            unique[0],
        )
    if disposition == "VERSIONED_CONTRACT_VERIFIED":
        value = frontier.get("observation_identity")
        if not isinstance(value, str) or not value.strip():
            raise SharedA3B4IntakeError(
                "verified versioned contract lacks explicit upstream identity"
            )
        return SharedA3B4IdentityStatus.VERSIONED_CONTRACT_VERIFIED, value
    if disposition in {
        "LEGACY_LINEAGE_ONLY",
        "PROVIDER_BINDING_UNKNOWN",
        "PROVIDER_ATTESTED_ONLY",
    }:
        return SharedA3B4IdentityStatus.UNKNOWN, None
    raise SharedA3B4IntakeError(
        f"unsupported B-06 identity disposition: {disposition}"
    )


def _calendar_status(disposition: str) -> SharedA3B4CalendarStatus:
    if disposition == "DISTRIBUTED_OTC_CALENDAR_UNRESOLVED":
        return SharedA3B4CalendarStatus.DISTRIBUTED_OTC_UNRESOLVED
    if disposition == "R8_HISTORICAL_SESSION_PARTIAL":
        return SharedA3B4CalendarStatus.HISTORICAL_SESSION_PARTIAL
    if disposition in {
        "IDENTITY_BLOCKED",
        "IDENTITY_AND_MARKET_STRUCTURE_BLOCKED",
    }:
        return SharedA3B4CalendarStatus.UNKNOWN
    if disposition in {
        "CURRENT_INDEX_CALENDAR_UNRESOLVED",
        "LEGACY_HISTORICAL_VERSION_REQUIRED",
        "VERSIONED_SESSION_CALENDAR_REQUIRED",
        "REFERENCE_TEMPORAL_SEMANTICS_REQUIRED",
    }:
        return SharedA3B4CalendarStatus.UNRESOLVED
    raise SharedA3B4IntakeError(
        f"unsupported B-07 temporal disposition: {disposition}"
    )


@dataclass(frozen=True, slots=True)
class SharedA3B4IntakeBatch:
    facts: tuple[SharedA3B4WorldFact, ...]
    resolved_identity_count: int
    unknown_identity_count: int
    comparable_count: int
    relation_eligible_count: int
    b06_fingerprint: str
    b07_fingerprint: str
    frontier_fingerprint: str
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if len(self.facts) != EXPECTED_SENSOR_COUNT:
            raise SharedA3B4IntakeError("intake batch must contain exact 177 facts")
        identities = tuple(fact.instrument_key for fact in self.facts)
        if identities != tuple(sorted(set(identities))):
            raise SharedA3B4IntakeError(
                "intake facts must be unique and canonically ordered"
            )
        if self.resolved_identity_count != 90:
            raise SharedA3B4IntakeError("expected exact 90 resolved identities")
        if self.unknown_identity_count != 87:
            raise SharedA3B4IntakeError("expected exact 87 unknown identities")
        if self.comparable_count != 0 or self.relation_eligible_count != 0:
            raise SharedA3B4IntakeError(
                "current B-07 truth cannot authorize comparability or relations"
            )
        if self.productive_authority:
            raise SharedA3B4IntakeError(
                "A3/B4 intake cannot carry productive authority"
            )

    def fingerprint(self) -> str:
        payload = {
            "facts": [fact.fingerprint() for fact in self.facts],
            "resolved_identity_count": self.resolved_identity_count,
            "unknown_identity_count": self.unknown_identity_count,
            "comparable_count": self.comparable_count,
            "relation_eligible_count": self.relation_eligible_count,
            "b06_fingerprint": self.b06_fingerprint,
            "b07_fingerprint": self.b07_fingerprint,
            "frontier_fingerprint": self.frontier_fingerprint,
            "productive_authority": self.productive_authority,
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_b4_intake_batch(
    *,
    b06_registry: dict[str, object],
    b07_registry: dict[str, object],
    identity_frontier_v3: dict[str, object],
    fact_timestamp: datetime,
    decision_timestamp: datetime,
) -> SharedA3B4IntakeBatch:
    """Build exact 177-row A3 intake while preserving B4 uncertainty."""

    if b06_registry.get("identity") != B06_IDENTITY:
        raise SharedA3B4IntakeError("unexpected B-06 registry identity")
    if b07_registry.get("identity") != B07_IDENTITY:
        raise SharedA3B4IntakeError("unexpected B-07 registry identity")
    if identity_frontier_v3.get("identity") != FRONTIER_IDENTITY:
        raise SharedA3B4IntakeError("unexpected identity frontier V3")
    for payload, label in (
        (b06_registry, "B-06"),
        (b07_registry, "B-07"),
        (identity_frontier_v3, "frontier"),
    ):
        if payload.get("sensor_count") != EXPECTED_SENSOR_COUNT:
            raise SharedA3B4IntakeError(f"{label} sensor population drift")

    if b06_registry.get("b06_epistemic_closure_complete") is not True:
        raise SharedA3B4IntakeError("B-06 epistemic closure is not complete")
    if b06_registry.get("calendar_binding_authorized") is not False:
        raise SharedA3B4IntakeError("B-06 unexpectedly widened calendar authority")
    if b06_registry.get("relational_claims_authorized") is not False:
        raise SharedA3B4IntakeError("B-06 unexpectedly widened relation authority")
    if b06_registry.get("productive_authority") is not False:
        raise SharedA3B4IntakeError("B-06 unexpectedly widened productive authority")

    if b07_registry.get("b07_epistemic_closure_complete") is not True:
        raise SharedA3B4IntakeError("B-07 epistemic closure is not complete")
    if b07_registry.get("canonical_calendar_verified_count") != 0:
        raise SharedA3B4IntakeError("B-07 unexpectedly claims canonical calendars")
    if b07_registry.get("calendar_binding_verified_count") != 0:
        raise SharedA3B4IntakeError("B-07 unexpectedly claims calendar bindings")
    if b07_registry.get("comparability_eligible_count") != 0:
        raise SharedA3B4IntakeError("B-07 unexpectedly authorizes comparability")
    if b07_registry.get("relational_comparability_authorized") is not False:
        raise SharedA3B4IntakeError("B-07 unexpectedly widens relation authority")
    if b07_registry.get("productive_authority") is not False:
        raise SharedA3B4IntakeError("B-07 unexpectedly widens productive authority")

    b06 = _index(b06_registry)
    b07 = _index(b07_registry)
    frontier = _index(identity_frontier_v3)
    if set(b06) != set(b07) or set(b06) != set(frontier):
        raise SharedA3B4IntakeError("B-06/B-07/frontier populations differ")

    b06_fp = str(b06_registry.get("registry_fingerprint_sha256") or "")
    b07_fp = str(b07_registry.get("registry_fingerprint_sha256") or "")
    frontier_fp = str(
        identity_frontier_v3.get("frontier_v3_fingerprint_sha256") or ""
    )
    if any(len(value) != 64 for value in (b06_fp, b07_fp, frontier_fp)):
        raise SharedA3B4IntakeError("upstream fingerprint missing or invalid")

    facts: list[SharedA3B4WorldFact] = []
    for key in sorted(b06):
        b06_row = b06[key]
        b07_row = b07[key]
        frontier_row = frontier[key]
        if b06_row.get("provider_symbol") != b07_row.get("provider_symbol"):
            raise SharedA3B4IntakeError("B-06/B-07 provider symbol drift")
        if b06_row.get("provider_symbol") != frontier_row.get("provider_symbol"):
            raise SharedA3B4IntakeError("B-06/frontier provider symbol drift")

        disposition = b06_row.get("identity_disposition")
        temporal_disposition = b07_row.get("temporal_disposition")
        if not isinstance(disposition, str) or not disposition:
            raise SharedA3B4IntakeError("B-06 disposition missing")
        if not isinstance(temporal_disposition, str) or not temporal_disposition:
            raise SharedA3B4IntakeError("B-07 temporal disposition missing")
        if b07_row.get("relational_comparability_authorized") is not False:
            raise SharedA3B4IntakeError(
                "B-07 row unexpectedly authorizes relation comparability"
            )

        identity_status, explicit_identity = _explicit_identity(
            disposition=disposition,
            frontier=frontier_row,
        )
        facts.append(
            SharedA3B4WorldFact(
                source_workstream="B-06+B-07",
                instrument_key=f"{key[0]}:{key[1]:06d}",
                canonical_identity=explicit_identity,
                identity_status=identity_status,
                calendar_status=_calendar_status(temporal_disposition),
                data_health_state="NOT_ASSESSED_B09_PENDING",
                temporal_status=SharedA3B4TemporalStatus.NOT_COMPARABLE,
                relation_eligibility=SharedA3B4RelationEligibility.INELIGIBLE,
                fact_timestamp=fact_timestamp,
                decision_timestamp=decision_timestamp,
                provenance_refs=tuple(
                    sorted(
                        {
                            f"b06:{b06_fp}",
                            f"b07:{b07_fp}",
                            f"frontier-v3:{frontier_fp}",
                            f"provider-key:{key[0]}:{key[1]}",
                        }
                    )
                ),
                uncertainty_bps=10_000,
            )
        )

    resolved = sum(fact.identity_resolved for fact in facts)
    unknown = sum(
        fact.identity_status
        in {SharedA3B4IdentityStatus.UNKNOWN, SharedA3B4IdentityStatus.UNRESOLVED}
        for fact in facts
    )
    comparable = sum(
        fact.temporal_status is SharedA3B4TemporalStatus.COMPARABLE for fact in facts
    )
    eligible = sum(fact.relation_claim_allowed for fact in facts)
    return SharedA3B4IntakeBatch(
        facts=tuple(facts),
        resolved_identity_count=resolved,
        unknown_identity_count=unknown,
        comparable_count=comparable,
        relation_eligible_count=eligible,
        b06_fingerprint=b06_fp,
        b07_fingerprint=b07_fp,
        frontier_fingerprint=frontier_fp,
    )
