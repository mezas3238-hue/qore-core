"""MC-28 explicit identity/mapping error diagnostic.

Known mappings can be checked for provider-field drift. Records without enough
identity evidence remain UNKNOWN rather than being mislabeled as mismatches.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class MappingDiagnosticState(StrEnum):
    MATCH = "MATCH"
    MISMATCH = "MISMATCH"
    UNKNOWN = "UNKNOWN"


KNOWN_MAPPING_STAGES = frozenset(
    {
        "CURRENT_REFERENCE_OBJECT_MAPPED",
        "CURRENT_OFFICIAL_REFERENCE_MAPPED",
        "DATED_CONTRACT_DESCRIPTOR_VERIFIED",
    }
)


@dataclass(frozen=True, slots=True)
class MappingExpectation:
    provider: str
    provider_symbol_id: int
    provider_symbol: str
    provider_description: str
    resolution_stage: str
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.provider.strip() or not self.provider_symbol.strip():
            raise ValueError("mapping expectation requires provider identity")
        if type(self.provider_symbol_id) is not int or self.provider_symbol_id <= 0:
            raise ValueError("provider_symbol_id must be positive int")
        if not self.provider_description.strip():
            raise ValueError("mapping expectation requires provider description")
        if (
            not self.evidence_refs
            or self.evidence_refs != tuple(sorted(set(self.evidence_refs)))
        ):
            raise ValueError("mapping expectation evidence must be canonical")


@dataclass(frozen=True, slots=True)
class MappingObservation:
    provider: str
    provider_symbol_id: int
    provider_symbol: str
    provider_description: str


@dataclass(frozen=True, slots=True)
class MappingDiagnostic:
    state: MappingDiagnosticState
    reason_codes: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    broker_mutation_authority: bool = False
    execution_authority: bool = False
    risk_authority: bool = False
    sizing_authority: bool = False

    def __post_init__(self) -> None:
        if not self.reason_codes:
            raise ValueError("mapping diagnostic requires reason codes")
        if (
            self.broker_mutation_authority
            or self.execution_authority
            or self.risk_authority
            or self.sizing_authority
        ):
            raise ValueError("mapping diagnostic is observational only")


def diagnose_mapping(
    expectation: MappingExpectation,
    observation: MappingObservation,
) -> MappingDiagnostic:
    if expectation.resolution_stage not in KNOWN_MAPPING_STAGES:
        return MappingDiagnostic(
            state=MappingDiagnosticState.UNKNOWN,
            reason_codes=("IDENTITY_NOT_RESOLVED_ENOUGH_FOR_MISMATCH_CLAIM",),
            evidence_refs=expectation.evidence_refs,
        )

    reasons: list[str] = []
    if observation.provider != expectation.provider:
        reasons.append("PROVIDER_MISMATCH")
    if observation.provider_symbol_id != expectation.provider_symbol_id:
        reasons.append("PROVIDER_SYMBOL_ID_MISMATCH")
    if observation.provider_symbol != expectation.provider_symbol:
        reasons.append("PROVIDER_SYMBOL_MISMATCH")
    if observation.provider_description != expectation.provider_description:
        reasons.append("PROVIDER_DESCRIPTION_MISMATCH")

    if reasons:
        return MappingDiagnostic(
            state=MappingDiagnosticState.MISMATCH,
            reason_codes=tuple(sorted(reasons)),
            evidence_refs=expectation.evidence_refs,
        )
    return MappingDiagnostic(
        state=MappingDiagnosticState.MATCH,
        reason_codes=("KNOWN_MAPPING_FIELDS_MATCH",),
        evidence_refs=expectation.evidence_refs,
    )
