"""Architect-B secondary observational provider intake contract.

Defines the fail-closed technical boundary for future agricultural/soft/
livestock observation sources. Technical qualification never grants Owner
authorization, scientific admission, trading authority or broker mutation.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class SecondaryProviderIntakeState(StrEnum):
    TECHNICALLY_INCOMPLETE = "TECHNICALLY_INCOMPLETE"
    READY_FOR_OWNER_AUTHORIZATION = "READY_FOR_OWNER_AUTHORIZATION"


@dataclass(frozen=True, slots=True)
class SecondaryObservationProviderCandidate:
    provider_id: str
    provider_identity_verified: bool
    legal_or_license_evidence_ref: str | None
    data_terms_evidence_ref: str | None
    read_only_access_verified: bool
    instrument_identity_evidence_available: bool
    provider_event_timestamp_available: bool
    retrieval_timestamp_available: bool
    historical_provenance_hashing_supported: bool
    deterministic_replay_supported: bool
    bid_ask_or_native_observation_semantics_documented: bool
    mutation_capability_present: bool
    credentials_separated_from_repository: bool
    owner_authorized: bool = False

    def __post_init__(self) -> None:
        if not self.provider_id.strip():
            raise ValueError("provider_id must be non-empty")


@dataclass(frozen=True, slots=True)
class SecondaryProviderIntakeAssessment:
    provider_id: str
    state: SecondaryProviderIntakeState
    technical_requirements_pass: bool
    owner_authorized: bool
    scientific_admission_authorized: bool
    productive_authority: bool
    broker_mutation_authority: bool
    reason_codes: tuple[str, ...]


def assess_secondary_observation_provider(
    candidate: SecondaryObservationProviderCandidate,
) -> SecondaryProviderIntakeAssessment:
    reasons: list[str] = []

    if not candidate.provider_identity_verified:
        reasons.append("PROVIDER_IDENTITY_UNVERIFIED")
    if not candidate.legal_or_license_evidence_ref:
        reasons.append("LEGAL_OR_LICENSE_EVIDENCE_MISSING")
    if not candidate.data_terms_evidence_ref:
        reasons.append("DATA_TERMS_EVIDENCE_MISSING")
    if not candidate.read_only_access_verified:
        reasons.append("READ_ONLY_ACCESS_UNVERIFIED")
    if not candidate.instrument_identity_evidence_available:
        reasons.append("INSTRUMENT_IDENTITY_EVIDENCE_UNAVAILABLE")
    if not candidate.provider_event_timestamp_available:
        reasons.append("PROVIDER_EVENT_TIMESTAMP_UNAVAILABLE")
    if not candidate.retrieval_timestamp_available:
        reasons.append("RETRIEVAL_TIMESTAMP_UNAVAILABLE")
    if not candidate.historical_provenance_hashing_supported:
        reasons.append("PROVENANCE_HASHING_UNSUPPORTED")
    if not candidate.deterministic_replay_supported:
        reasons.append("DETERMINISTIC_REPLAY_UNSUPPORTED")
    if not candidate.bid_ask_or_native_observation_semantics_documented:
        reasons.append("OBSERVATION_SEMANTICS_UNDOCUMENTED")
    if candidate.mutation_capability_present:
        reasons.append("MUTATION_CAPABILITY_PRESENT")
    if not candidate.credentials_separated_from_repository:
        reasons.append("CREDENTIAL_ISOLATION_UNVERIFIED")

    technical_pass = not reasons
    state = (
        SecondaryProviderIntakeState.READY_FOR_OWNER_AUTHORIZATION
        if technical_pass
        else SecondaryProviderIntakeState.TECHNICALLY_INCOMPLETE
    )
    return SecondaryProviderIntakeAssessment(
        provider_id=candidate.provider_id,
        state=state,
        technical_requirements_pass=technical_pass,
        owner_authorized=candidate.owner_authorized,
        scientific_admission_authorized=False,
        productive_authority=False,
        broker_mutation_authority=False,
        reason_codes=tuple(sorted(set(reasons))),
    )
