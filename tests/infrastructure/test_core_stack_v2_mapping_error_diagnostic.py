from qore.infrastructure.core_stack_v2.mapping_error_diagnostic import (
    MappingDiagnosticState,
    MappingExpectation,
    MappingObservation,
    diagnose_mapping,
)


def _expectation(stage: str) -> MappingExpectation:
    return MappingExpectation(
        provider="CTRADER_DEMO",
        provider_symbol_id=42,
        provider_symbol="US500",
        provider_description="US 500 index",
        resolution_stage=stage,
        evidence_refs=("artifact:b06",),
    )


def test_known_mapping_matches_exact_observation() -> None:
    result = diagnose_mapping(
        _expectation("CURRENT_OFFICIAL_REFERENCE_MAPPED"),
        MappingObservation(
            "CTRADER_DEMO",
            42,
            "US500",
            "US 500 index",
        ),
    )
    assert result.state is MappingDiagnosticState.MATCH


def test_known_mapping_detects_provider_field_drift() -> None:
    result = diagnose_mapping(
        _expectation("CURRENT_OFFICIAL_REFERENCE_MAPPED"),
        MappingObservation(
            "CTRADER_DEMO",
            42,
            "US500_DRIFT",
            "US 500 index",
        ),
    )
    assert result.state is MappingDiagnosticState.MISMATCH
    assert "PROVIDER_SYMBOL_MISMATCH" in result.reason_codes


def test_unresolved_identity_is_unknown_not_false_mismatch() -> None:
    result = diagnose_mapping(
        _expectation("PROVIDER_BINDING_UNRESOLVED"),
        MappingObservation(
            "CTRADER_DEMO",
            42,
            "DRIFTED",
            "changed",
        ),
    )
    assert result.state is MappingDiagnosticState.UNKNOWN


def test_mapping_diagnostic_never_acquires_authority() -> None:
    result = diagnose_mapping(
        _expectation("DATED_CONTRACT_DESCRIPTOR_VERIFIED"),
        MappingObservation(
            "CTRADER_DEMO",
            42,
            "US500",
            "US 500 index",
        ),
    )
    assert result.broker_mutation_authority is False
    assert result.execution_authority is False
    assert result.risk_authority is False
    assert result.sizing_authority is False
