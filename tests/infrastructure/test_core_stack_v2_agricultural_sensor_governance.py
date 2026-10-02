from __future__ import annotations

from datetime import UTC, datetime

import pytest

from qore.infrastructure.core_stack_v2.agricultural_sensor_governance import (
    AGRICULTURAL_QUALIFICATION_PIPELINE,
    AgriculturalCapabilityEvidenceState,
    AgriculturalDiscoveryTarget,
    AgriculturalProviderCapabilityRow,
    AgriculturalProviderDiscoveryState,
    AgriculturalQualificationStage,
    AgriculturalScientificMaturity,
    AgriculturalWorldFamily,
    GlobalAgriculturalSensorMatrix,
    ProviderAgriculturalCandidate,
    build_agricultural_provider_capability_matrix,
)

NOW = datetime(2026, 9, 29, 19, 0, tzinfo=UTC)
SHA = "1" * 64
UNIVERSE_SHA = "2" * 64


def _target(
    key: str,
    term: str,
    *,
    family: AgriculturalWorldFamily = AgriculturalWorldFamily.AGRICULTURE,
) -> AgriculturalDiscoveryTarget:
    return AgriculturalDiscoveryTarget(
        conceptual_market_key=key,
        display_name=key.replace("_", " ").title(),
        world_family=family,
        complex_memberships=(family.value,),
        discovery_terms=(term,),
    )


def _candidate(
    symbol: str,
    symbol_id: int,
    description: str,
    *,
    provider: str = "CTRADER_DEMO",
) -> ProviderAgriculturalCandidate:
    return ProviderAgriculturalCandidate(
        provider=provider,
        provider_symbol_id=symbol_id,
        provider_symbol=symbol,
        provider_native_symbol_name=symbol,
        provider_description=description,
        provenance_ref=f"provider-catalog:{SHA}",
    )


def test_agricultural_qualification_pipeline_is_owner_ordered() -> None:
    assert AGRICULTURAL_QUALIFICATION_PIPELINE == (
        AgriculturalQualificationStage.DISCOVERED,
        AgriculturalQualificationStage.IDENTITY_VERIFIED,
        AgriculturalQualificationStage.CONTRACT_MAPPED,
        AgriculturalQualificationStage.CALENDAR_MAPPED,
        AgriculturalQualificationStage.HISTORICAL_AVAILABILITY_VERIFIED,
        AgriculturalQualificationStage.TIMESTAMP_VERIFIED,
        AgriculturalQualificationStage.DATA_QUALITY_VERIFIED,
        AgriculturalQualificationStage.ROLL_POLICY_VERIFIED,
        AgriculturalQualificationStage.TEMPORALLY_OBSERVABLE,
        AgriculturalQualificationStage.RELATIONALLY_COMPARABLE,
        AgriculturalQualificationStage.INFORMATION_GAIN_TESTED,
        AgriculturalQualificationStage.CAUSALLY_RESEARCHED,
        AgriculturalQualificationStage.TEMPORALLY_REPLICATED,
        AgriculturalQualificationStage.SCIENTIFICALLY_ADMITTED,
    )


def test_empty_provider_agricultural_catalog_is_explicit_absence() -> None:
    targets = tuple(
        sorted(
            (
                _target("CORN", "corn"),
                _target(
                    "COFFEE",
                    "coffee",
                    family=AgriculturalWorldFamily.SOFTS,
                ),
                _target(
                    "LIVE_CATTLE",
                    "live cattle",
                    family=AgriculturalWorldFamily.LIVESTOCK,
                ),
            ),
            key=lambda item: item.conceptual_market_key,
        )
    )

    matrix = build_agricultural_provider_capability_matrix(
        provider="CTRADER_DEMO",
        as_of=NOW,
        source_catalog_fingerprint=SHA,
        conceptual_universe_identity=(
            "QORE_SHARED_AGRICULTURAL_CONCEPTUAL_UNIVERSE_001"
        ),
        conceptual_universe_fingerprint=UNIVERSE_SHA,
        targets=targets,
        provider_catalog=(),
    )

    assert len(matrix.rows) == 3
    assert all(
        row.discovery_state
        is AgriculturalProviderDiscoveryState.ABSENT_FROM_CURRENT_CATALOG_EVIDENCE
        for row in matrix.rows
    )
    assert all(not row.candidates for row in matrix.rows)
    assert all(
        row.scientific_maturity is AgriculturalScientificMaturity.ABSENT
        for row in matrix.rows
    )
    assert matrix.automatic_sensor_admission is False
    assert matrix.relational_claims_authorized is False
    assert matrix.protected_holdout_opened is False
    assert len(matrix.fingerprint()) == 64


def test_provider_text_match_creates_candidate_not_identity() -> None:
    target = _target("CORN", "corn")
    provider_row = _candidate(
        "CORN_DEC",
        501,
        "Corn futures candidate - December",
    )

    matrix = build_agricultural_provider_capability_matrix(
        provider="CTRADER_DEMO",
        as_of=NOW,
        source_catalog_fingerprint=SHA,
        conceptual_universe_identity=(
            "QORE_SHARED_AGRICULTURAL_CONCEPTUAL_UNIVERSE_001"
        ),
        conceptual_universe_fingerprint=UNIVERSE_SHA,
        targets=(target,),
        provider_catalog=(provider_row,),
    )
    row = matrix.rows[0]

    assert row.discovery_state is (
        AgriculturalProviderDiscoveryState.DISCOVERED_CANDIDATE
    )
    assert row.candidates == (provider_row,)
    assert row.scientific_maturity is AgriculturalScientificMaturity.DISCOVERED
    assert row.contract_type == "UNKNOWN"
    assert row.identity_verified is False
    assert row.contract_mapped is False
    assert row.calendar_mapped is False
    assert row.roll_policy_verified is False
    assert row.relational_ready is False
    assert row.final_global_admission_authority is False
    assert row.historical_availability is AgriculturalCapabilityEvidenceState.UNKNOWN
    assert row.realtime_availability is AgriculturalCapabilityEvidenceState.UNKNOWN
    assert row.bid_ask_availability is AgriculturalCapabilityEvidenceState.UNKNOWN
    assert row.tick_availability is AgriculturalCapabilityEvidenceState.UNKNOWN
    assert row.ohlc_availability is AgriculturalCapabilityEvidenceState.UNKNOWN
    assert row.contract_metadata_availability is (
        AgriculturalCapabilityEvidenceState.UNKNOWN
    )


def test_cryptic_provider_symbol_is_not_guessed_into_agriculture() -> None:
    target = _target("CORN", "corn")
    provider_row = _candidate(
        "ZC",
        502,
        "Undocumented provider product",
    )

    matrix = build_agricultural_provider_capability_matrix(
        provider="CTRADER_DEMO",
        as_of=NOW,
        source_catalog_fingerprint=SHA,
        conceptual_universe_identity=(
            "QORE_SHARED_AGRICULTURAL_CONCEPTUAL_UNIVERSE_001"
        ),
        conceptual_universe_fingerprint=UNIVERSE_SHA,
        targets=(target,),
        provider_catalog=(provider_row,),
    )

    assert matrix.rows[0].discovery_state is (
        AgriculturalProviderDiscoveryState.ABSENT_FROM_CURRENT_CATALOG_EVIDENCE
    )
    assert matrix.rows[0].candidates == ()


def test_provider_filter_prevents_cross_provider_candidate_leakage() -> None:
    target = _target("CORN", "corn")
    other = _candidate(
        "CORN_DEC",
        900,
        "Corn futures candidate - December",
        provider="OTHER_PROVIDER",
    )

    matrix = build_agricultural_provider_capability_matrix(
        provider="CTRADER_DEMO",
        as_of=NOW,
        source_catalog_fingerprint=SHA,
        conceptual_universe_identity=(
            "QORE_SHARED_AGRICULTURAL_CONCEPTUAL_UNIVERSE_001"
        ),
        conceptual_universe_fingerprint=UNIVERSE_SHA,
        targets=(target,),
        provider_catalog=(other,),
    )

    assert matrix.rows[0].candidates == ()
    assert matrix.rows[0].discovery_state is (
        AgriculturalProviderDiscoveryState.ABSENT_FROM_CURRENT_CATALOG_EVIDENCE
    )


def test_agri1_row_cannot_grant_identity_or_sovereign_authority() -> None:
    target = _target("CORN", "corn")

    with pytest.raises(
        ValueError,
        match="cannot grant qualification or authority",
    ):
        AgriculturalProviderCapabilityRow(
            target=target,
            provider="CTRADER_DEMO",
            discovery_state=(
                AgriculturalProviderDiscoveryState.ABSENT_FROM_CURRENT_CATALOG_EVIDENCE
            ),
            candidates=(),
            identity_verified=True,
        )


def test_candidate_and_matrix_fingerprints_are_deterministic() -> None:
    target = _target("CORN", "corn")
    provider_row = _candidate(
        "CORN_DEC",
        501,
        "Corn futures candidate - December",
    )

    first = build_agricultural_provider_capability_matrix(
        provider="CTRADER_DEMO",
        as_of=NOW,
        source_catalog_fingerprint=SHA,
        conceptual_universe_identity=(
            "QORE_SHARED_AGRICULTURAL_CONCEPTUAL_UNIVERSE_001"
        ),
        conceptual_universe_fingerprint=UNIVERSE_SHA,
        targets=(target,),
        provider_catalog=(provider_row,),
    )
    second = build_agricultural_provider_capability_matrix(
        provider="CTRADER_DEMO",
        as_of=NOW,
        source_catalog_fingerprint=SHA,
        conceptual_universe_identity=(
            "QORE_SHARED_AGRICULTURAL_CONCEPTUAL_UNIVERSE_001"
        ),
        conceptual_universe_fingerprint=UNIVERSE_SHA,
        targets=(target,),
        provider_catalog=(provider_row,),
    )

    assert first.fingerprint() == second.fingerprint()
    assert first.rows[0].fingerprint() == second.rows[0].fingerprint()


def test_matrix_rejects_authority_expansion() -> None:
    with pytest.raises(
        ValueError,
        match="cannot expand authority",
    ):
        GlobalAgriculturalSensorMatrix(
            as_of=NOW,
            source_catalog_fingerprint=SHA,
            rows=(),
            conceptual_universe_identity=(
                "QORE_SHARED_AGRICULTURAL_CONCEPTUAL_UNIVERSE_001"
            ),
            conceptual_universe_fingerprint=UNIVERSE_SHA,
            automatic_sensor_admission=True,
        )
