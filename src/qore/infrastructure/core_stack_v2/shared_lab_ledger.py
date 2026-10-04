"""Canonical capability evidence ledger for QORE Shared Lab.

The ledger prevents pooled rescue: every mandatory capability is assessed
individually before any organism-level aggregate can pass.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.core_stack_v2.shared_lab import CapabilityLabRecord


class CapabilityProofTier(StrEnum):
    ENGINEERING_GREEN = "ENGINEERING_GREEN"
    FUNCTIONALLY_PROVEN = "FUNCTIONALLY_PROVEN"
    CAUSALLY_PROVEN = "CAUSALLY_PROVEN"
    SCIENTIFICALLY_PROVEN = "SCIENTIFICALLY_PROVEN"
    INTEGRATION_PROVEN = "INTEGRATION_PROVEN"
    PHASE_PROVEN = "PHASE_PROVEN"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class CapabilityLedgerEntry:
    capability_id: str
    mandatory: bool
    record_fingerprint: str
    native_engine_pass: bool
    cable_reality_pass: bool
    leakage_free: bool
    latency_pass: bool
    cognitively_live: bool
    required_levels_pass: bool
    mutation_pass: bool
    metamorphic_pass: bool
    ablation_pass: bool
    phase_proven: bool
    proof_tier: CapabilityProofTier


@dataclass(frozen=True, slots=True)
class CapabilityLedgerAssessment:
    entries: tuple[CapabilityLedgerEntry, ...]
    mandatory_count: int
    mandatory_proven_count: int
    blocker_ids: tuple[str, ...]
    no_pooled_rescue_pass: bool


def _tier(record: CapabilityLabRecord) -> CapabilityProofTier:
    if not record.engineering_green:
        return CapabilityProofTier.FAILED
    if not record.native_engine.passed or not record.cable_reality_pass:
        return CapabilityProofTier.FAILED
    if not record.leakage_free or not record.efficiency.deadline_pass:
        return CapabilityProofTier.FAILED
    if not record.required_levels_pass or not record.efficiency.cognitively_live:
        return CapabilityProofTier.FUNCTIONALLY_PROVEN
    if not record.mutation_pass or not record.metamorphic_pass:
        return CapabilityProofTier.CAUSALLY_PROVEN
    if not record.ablation_pass:
        return CapabilityProofTier.SCIENTIFICALLY_PROVEN
    if record.phase_proven:
        return CapabilityProofTier.PHASE_PROVEN
    return CapabilityProofTier.INTEGRATION_PROVEN


def build_capability_ledger(
    records: tuple[CapabilityLabRecord, ...],
    *,
    mandatory_ids: frozenset[str],
) -> CapabilityLedgerAssessment:
    ids = tuple(record.capability_id for record in records)
    if len(ids) != len(set(ids)):
        raise ValueError("capability ledger identities must be unique")
    missing = mandatory_ids.difference(ids)
    if missing:
        raise ValueError(f"mandatory capabilities missing records: {sorted(missing)}")

    entries = tuple(
        CapabilityLedgerEntry(
            capability_id=record.capability_id,
            mandatory=record.capability_id in mandatory_ids,
            record_fingerprint=record.fingerprint(),
            native_engine_pass=record.native_engine.passed,
            cable_reality_pass=record.cable_reality_pass,
            leakage_free=record.leakage_free,
            latency_pass=record.efficiency.deadline_pass,
            cognitively_live=record.efficiency.cognitively_live,
            required_levels_pass=record.required_levels_pass,
            mutation_pass=record.mutation_pass,
            metamorphic_pass=record.metamorphic_pass,
            ablation_pass=record.ablation_pass,
            phase_proven=record.phase_proven,
            proof_tier=_tier(record),
        )
        for record in sorted(records, key=lambda item: item.capability_id)
    )
    blockers = tuple(
        entry.capability_id
        for entry in entries
        if entry.mandatory and not entry.phase_proven
    )
    mandatory_count = sum(entry.mandatory for entry in entries)
    proven_count = sum(entry.mandatory and entry.phase_proven for entry in entries)
    return CapabilityLedgerAssessment(
        entries=entries,
        mandatory_count=mandatory_count,
        mandatory_proven_count=proven_count,
        blocker_ids=blockers,
        no_pooled_rescue_pass=mandatory_count > 0 and not blockers,
    )
