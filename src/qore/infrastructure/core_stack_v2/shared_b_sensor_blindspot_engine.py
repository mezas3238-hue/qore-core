"""Architect-B sensor-side Blindspot Engine.

Detects declared gaps in observability without inventing the missing evidence.
Second-order blindspots are represented explicitly when the coverage inventory
itself is incomplete.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class SharedBBlindspotKind(StrEnum):
    SENSOR_FAMILY_ABSENT = "SENSOR_FAMILY_ABSENT"
    TIME_HORIZON_ABSENT = "TIME_HORIZON_ABSENT"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    IDENTITY_UNRESOLVED = "IDENTITY_UNRESOLVED"
    MARKET_HOURS_UNRESOLVED = "MARKET_HOURS_UNRESOLVED"
    DATA_HEALTH_NOT_OBSERVED = "DATA_HEALTH_NOT_OBSERVED"
    RELATION_COMPARABILITY_UNKNOWN = "RELATION_COMPARABILITY_UNKNOWN"
    COVERAGE_INVENTORY_INCOMPLETE = "COVERAGE_INVENTORY_INCOMPLETE"


@dataclass(frozen=True, slots=True)
class SharedBObservationRequirement:
    requirement_id: str
    sensor_family: str
    horizon: str
    identity_required: bool
    market_hours_required: bool
    data_health_required: bool
    relation_comparability_required: bool
    provenance_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in ("requirement_id","sensor_family","horizon"):
            value=getattr(self,name)
            if not isinstance(value,str) or not value.strip():
                raise ValueError(f"{name} must be non-empty")
        for name in (
            "identity_required","market_hours_required",
            "data_health_required","relation_comparability_required",
        ):
            if type(getattr(self,name)) is not bool:
                raise ValueError(f"{name} must be bool")
        if (
            not self.provenance_refs
            or self.provenance_refs != tuple(sorted(set(self.provenance_refs)))
        ):
            raise ValueError(
                "requirement provenance must be non-empty and canonical"
            )


@dataclass(frozen=True, slots=True)
class SharedBSensorCoverageFact:
    sensor_family: str
    horizon: str
    observed_at: datetime
    evidence_cutoff_at: datetime
    sensor_ids: tuple[str, ...]
    provider_available: bool
    identity_resolved: bool
    market_hours_resolved: bool
    data_health_observed: bool
    relation_comparability_known: bool
    provenance_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.sensor_family.strip() or not self.horizon.strip():
            raise ValueError("coverage family/horizon must be non-empty")
        for name in ("observed_at","evidence_cutoff_at"):
            value=getattr(self,name)
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(f"{name} must be timezone-aware")
        if self.evidence_cutoff_at > self.observed_at:
            raise ValueError("future blindspot evidence is forbidden")
        if self.sensor_ids != tuple(sorted(set(self.sensor_ids))):
            raise ValueError("sensor_ids must be unique and canonical")
        for name in (
            "provider_available","identity_resolved","market_hours_resolved",
            "data_health_observed","relation_comparability_known",
        ):
            if type(getattr(self,name)) is not bool:
                raise ValueError(f"{name} must be bool")
        if (
            not self.provenance_refs
            or self.provenance_refs != tuple(sorted(set(self.provenance_refs)))
        ):
            raise ValueError(
                "coverage provenance must be non-empty and canonical"
            )


@dataclass(frozen=True, slots=True)
class SharedBBlindspot:
    requirement_id: str
    sensor_family: str
    horizon: str
    kind: SharedBBlindspotKind
    reason_code: str
    known_missing: bool
    second_order_possible: bool
    provenance_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SharedBBlindspotReport:
    as_of: datetime
    blindspots: tuple[SharedBBlindspot, ...]
    coverage_inventory_complete: bool
    second_order_blindspot_possible: bool
    productive_authority: bool = False
    sensor_admission_authority: bool = False
    relation_authority: bool = False

    def __post_init__(self) -> None:
        if self.as_of.tzinfo is None or self.as_of.utcoffset() is None:
            raise ValueError("blindspot report as_of must be timezone-aware")
        keys=tuple(
            (
                item.requirement_id,
                item.sensor_family,
                item.horizon,
                item.kind.value,
            )
            for item in self.blindspots
        )
        if keys != tuple(sorted(keys)) or len(keys) != len(set(keys)):
            raise ValueError("blindspots must be unique and canonical")
        if (
            self.productive_authority
            or self.sensor_admission_authority
            or self.relation_authority
        ):
            raise ValueError("blindspot engine carries no downstream authority")


def detect_sensor_blindspots(
    *,
    requirements: tuple[SharedBObservationRequirement, ...],
    coverage: tuple[SharedBSensorCoverageFact, ...],
    as_of: datetime,
    coverage_inventory_complete: bool,
) -> SharedBBlindspotReport:
    """Detect only evidence-supported gaps; never synthesize missing sensors."""

    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValueError("as_of must be timezone-aware")
    requirement_ids=tuple(item.requirement_id for item in requirements)
    if (
        requirement_ids != tuple(sorted(requirement_ids))
        or len(requirement_ids) != len(set(requirement_ids))
    ):
        raise ValueError("requirements must be unique and canonical")

    by_key:dict[tuple[str,str],SharedBSensorCoverageFact]={}
    family_horizons:dict[str,set[str]]={}
    for coverage_fact in coverage:
        if (
            coverage_fact.observed_at > as_of
            or coverage_fact.evidence_cutoff_at > as_of
        ):
            raise ValueError("future coverage fact is forbidden")
        key=(coverage_fact.sensor_family,coverage_fact.horizon)
        if key in by_key:
            raise ValueError("duplicate coverage fact")
        by_key[key]=coverage_fact
        family_horizons.setdefault(
            coverage_fact.sensor_family,
            set(),
        ).add(coverage_fact.horizon)

    blindspots:list[SharedBBlindspot]=[]
    for requirement in requirements:
        key=(requirement.sensor_family,requirement.horizon)
        fact=by_key.get(key)
        base_provenance=requirement.provenance_refs

        if fact is None:
            kind=(
                SharedBBlindspotKind.SENSOR_FAMILY_ABSENT
                if requirement.sensor_family not in family_horizons
                else SharedBBlindspotKind.TIME_HORIZON_ABSENT
            )
            blindspots.append(
                SharedBBlindspot(
                    requirement_id=requirement.requirement_id,
                    sensor_family=requirement.sensor_family,
                    horizon=requirement.horizon,
                    kind=kind,
                    reason_code=kind.value,
                    known_missing=coverage_inventory_complete,
                    second_order_possible=not coverage_inventory_complete,
                    provenance_refs=base_provenance,
                )
            )
            continue

        provenance=tuple(
            sorted(set(base_provenance + fact.provenance_refs))
        )
        checks=(
            (
                not fact.provider_available,
                SharedBBlindspotKind.PROVIDER_UNAVAILABLE,
            ),
            (
                requirement.identity_required and not fact.identity_resolved,
                SharedBBlindspotKind.IDENTITY_UNRESOLVED,
            ),
            (
                requirement.market_hours_required
                and not fact.market_hours_resolved,
                SharedBBlindspotKind.MARKET_HOURS_UNRESOLVED,
            ),
            (
                requirement.data_health_required
                and not fact.data_health_observed,
                SharedBBlindspotKind.DATA_HEALTH_NOT_OBSERVED,
            ),
            (
                requirement.relation_comparability_required
                and not fact.relation_comparability_known,
                SharedBBlindspotKind.RELATION_COMPARABILITY_UNKNOWN,
            ),
        )
        for triggered,kind in checks:
            if triggered:
                blindspots.append(
                    SharedBBlindspot(
                        requirement_id=requirement.requirement_id,
                        sensor_family=requirement.sensor_family,
                        horizon=requirement.horizon,
                        kind=kind,
                        reason_code=kind.value,
                        known_missing=True,
                        second_order_possible=not coverage_inventory_complete,
                        provenance_refs=provenance,
                    )
                )

    if not coverage_inventory_complete:
        blindspots.append(
            SharedBBlindspot(
                requirement_id="__COVERAGE_INVENTORY__",
                sensor_family="__UNKNOWN__",
                horizon="__UNKNOWN__",
                kind=SharedBBlindspotKind.COVERAGE_INVENTORY_INCOMPLETE,
                reason_code="SECOND_ORDER_BLINDSPOT_CANNOT_BE_EXCLUDED",
                known_missing=False,
                second_order_possible=True,
                provenance_refs=("blindspot:inventory-completeness",),
            )
        )

    return SharedBBlindspotReport(
        as_of=as_of,
        blindspots=tuple(
            sorted(
                blindspots,
                key=lambda item:(
                    item.requirement_id,
                    item.sensor_family,
                    item.horizon,
                    item.kind.value,
                ),
            )
        ),
        coverage_inventory_complete=coverage_inventory_complete,
        second_order_blindspot_possible=not coverage_inventory_complete,
    )
