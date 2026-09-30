from __future__ import annotations

from qore.infrastructure.core_stack_v2.shared_b_secondary_provider_intake import (
    SecondaryObservationProviderCandidate,
    SecondaryProviderIntakeState,
    assess_secondary_observation_provider,
)


def _candidate(**overrides: object) -> SecondaryObservationProviderCandidate:
    values: dict[str, object] = {
        "provider_id": "HYPOTHETICAL_OBSERVATION_PROVIDER",
        "provider_identity_verified": True,
        "legal_or_license_evidence_ref": "legal:sealed",
        "data_terms_evidence_ref": "terms:sealed",
        "read_only_access_verified": True,
        "instrument_identity_evidence_available": True,
        "provider_event_timestamp_available": True,
        "retrieval_timestamp_available": True,
        "historical_provenance_hashing_supported": True,
        "deterministic_replay_supported": True,
        "bid_ask_or_native_observation_semantics_documented": True,
        "mutation_capability_present": False,
        "credentials_separated_from_repository": True,
        "owner_authorized": False,
    }
    values.update(overrides)
    return SecondaryObservationProviderCandidate(**values)  # type: ignore[arg-type]


def test_technical_pass_still_requires_owner_and_scientific_admission() -> None:
    result = assess_secondary_observation_provider(_candidate())
    assert result.state is SecondaryProviderIntakeState.READY_FOR_OWNER_AUTHORIZATION
    assert result.technical_requirements_pass is True
    assert result.owner_authorized is False
    assert result.scientific_admission_authorized is False
    assert result.productive_authority is False
    assert result.broker_mutation_authority is False
    assert result.reason_codes == ()


def test_mutation_capability_fails_technical_boundary() -> None:
    result = assess_secondary_observation_provider(
        _candidate(mutation_capability_present=True)
    )
    assert result.state is SecondaryProviderIntakeState.TECHNICALLY_INCOMPLETE
    assert result.technical_requirements_pass is False
    assert "MUTATION_CAPABILITY_PRESENT" in result.reason_codes


def test_missing_time_or_provenance_fails_closed() -> None:
    result = assess_secondary_observation_provider(
        _candidate(
            provider_event_timestamp_available=False,
            historical_provenance_hashing_supported=False,
        )
    )
    assert result.state is SecondaryProviderIntakeState.TECHNICALLY_INCOMPLETE
    assert "PROVIDER_EVENT_TIMESTAMP_UNAVAILABLE" in result.reason_codes
    assert "PROVENANCE_HASHING_UNSUPPORTED" in result.reason_codes


def test_owner_authorization_never_equals_scientific_admission() -> None:
    result = assess_secondary_observation_provider(
        _candidate(owner_authorized=True)
    )
    assert result.technical_requirements_pass is True
    assert result.owner_authorized is True
    assert result.scientific_admission_authorized is False
    assert result.productive_authority is False
