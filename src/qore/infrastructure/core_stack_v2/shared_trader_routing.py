"""Material Shared -> Trader routing without methodology ownership."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from qore.infrastructure.core_stack_v2.shared_trader_intelligence import (
    SharedIntelligenceClass,
    SharedTraderCapability,
    SharedTraderRelevantProjection,
)


@dataclass(frozen=True, slots=True)
class SharedRoutableFact:
    fact_ref: str
    snapshot_id: str
    intelligence_class: SharedIntelligenceClass
    markets: tuple[str, ...]
    horizons: tuple[str, ...]
    evidence_cutoff_at: datetime
    materiality_passed: bool
    data_health_passed: bool

    def __post_init__(self) -> None:
        if not self.fact_ref.strip() or not self.snapshot_id.strip():
            raise ValueError("routable fact identity must be explicit")
        if self.evidence_cutoff_at.tzinfo is None or self.evidence_cutoff_at.utcoffset() is None:
            raise ValueError("routable fact evidence_cutoff_at must be timezone-aware")
        for name in ("markets", "horizons"):
            values = getattr(self, name)
            if values != tuple(sorted(set(values))):
                raise ValueError(f"{name} must be unique and canonical")
            if any(not value.strip() for value in values):
                raise ValueError(f"{name} cannot contain empty values")


@dataclass(frozen=True, slots=True)
class SharedTraderRoutingResult:
    projection: SharedTraderRelevantProjection
    routed_fact_refs: tuple[str, ...]
    omitted_fact_refs: tuple[str, ...]
    omission_reasons: tuple[tuple[str, str], ...]
    methodology_inspected: bool = False
    methodology_mutated: bool = False
    execution_authority: bool = False
    capital_authority: bool = False
    risk_authority: bool = False

    def __post_init__(self) -> None:
        if self.routed_fact_refs != tuple(sorted(set(self.routed_fact_refs))):
            raise ValueError("routed facts must be unique and canonical")
        if self.omitted_fact_refs != tuple(sorted(set(self.omitted_fact_refs))):
            raise ValueError("omitted facts must be unique and canonical")
        if set(self.routed_fact_refs) & set(self.omitted_fact_refs):
            raise ValueError("fact cannot be both routed and omitted")
        if (
            self.methodology_inspected
            or self.methodology_mutated
            or self.execution_authority
            or self.capital_authority
            or self.risk_authority
        ):
            raise ValueError("Shared routing cannot own downstream authority")


def _fact_matches_capability(
    fact: SharedRoutableFact,
    capability: SharedTraderCapability,
) -> tuple[bool, str]:
    if not fact.data_health_passed:
        return False, "DATA_HEALTH_BLOCK"
    if not fact.materiality_passed:
        return False, "MATERIALITY_BLOCK"
    if fact.intelligence_class not in capability.supported_intelligence_classes:
        return False, "UNSUPPORTED_INTELLIGENCE_CLASS"
    if (
        fact.intelligence_class is SharedIntelligenceClass.POSITION_THREAT
        and not capability.open_position_monitoring_capability
    ):
        return False, "NO_OPEN_POSITION_MONITORING_CAPABILITY"
    if fact.markets and not set(fact.markets).intersection(capability.markets):
        return False, "MARKET_NOT_RELEVANT"
    if fact.horizons and not set(fact.horizons).intersection(capability.horizons):
        return False, "HORIZON_NOT_RELEVANT"
    return True, "ROUTED"


def route_shared_facts_to_trader(
    *,
    capability: SharedTraderCapability,
    facts: tuple[SharedRoutableFact, ...],
    projection_id: str,
    snapshot_id: str,
    projected_at: datetime,
    global_state_fingerprint: str,
) -> SharedTraderRoutingResult:
    """Filter material healthy global facts into one Trader-relevant projection."""

    if projected_at.tzinfo is None or projected_at.utcoffset() is None:
        raise ValueError("projected_at must be timezone-aware")
    if len(global_state_fingerprint) != 64:
        raise ValueError("global_state_fingerprint must be sha256 hex")
    try:
        int(global_state_fingerprint, 16)
    except ValueError as exc:
        raise ValueError("global_state_fingerprint must be sha256 hex") from exc

    refs = tuple(item.fact_ref for item in facts)
    if refs != tuple(sorted(set(refs))):
        raise ValueError("facts must be unique and canonical by fact_ref")
    if any(item.snapshot_id != snapshot_id for item in facts):
        raise ValueError("routing batch must bind one global snapshot")
    if any(item.evidence_cutoff_at > projected_at for item in facts):
        raise ValueError("routing cannot consume future evidence")

    routed: list[str] = []
    omitted: list[str] = []
    omissions: list[tuple[str, str]] = []
    classes: set[SharedIntelligenceClass] = set()
    evidence_cutoff = projected_at

    for fact in facts:
        evidence_cutoff = min(evidence_cutoff, fact.evidence_cutoff_at)
        matched, reason = _fact_matches_capability(fact, capability)
        if matched:
            routed.append(fact.fact_ref)
            classes.add(fact.intelligence_class)
        else:
            omitted.append(fact.fact_ref)
            omissions.append((fact.fact_ref, reason))

    projection = SharedTraderRelevantProjection(
        projection_id=projection_id,
        snapshot_id=snapshot_id,
        trader_id=capability.trader_id,
        projected_at=projected_at,
        evidence_cutoff_at=evidence_cutoff,
        intelligence_classes=tuple(sorted(classes, key=lambda item: item.value)),
        relevant_fact_refs=tuple(sorted(routed)),
        omitted_fact_refs=tuple(sorted(omitted)),
        global_state_fingerprint=global_state_fingerprint,
    )
    return SharedTraderRoutingResult(
        projection=projection,
        routed_fact_refs=tuple(sorted(routed)),
        omitted_fact_refs=tuple(sorted(omitted)),
        omission_reasons=tuple(sorted(omissions)),
    )
