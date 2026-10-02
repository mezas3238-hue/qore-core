from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from qore.infrastructure.core_stack_v2.shared_trader_intelligence import (
    SharedTraderIntelligenceValidationError,
)
from qore.infrastructure.core_stack_v2.shared_trader_intelligence_preregistration import (
    SharedSTIHistoricalStudyPreregistration,
    SharedSTIResearchQuestion,
)

T0 = datetime(2026, 9, 29, 22, 15, tzinfo=UTC)
SHA_A = "a" * 64
SHA_B = "b" * 64
SHA_C = "c" * 64
SHA_D = "d" * 64
SHA_E = "e" * 64
SHA_F = "f" * 64


def _prereg() -> SharedSTIHistoricalStudyPreregistration:
    return SharedSTIHistoricalStudyPreregistration(
        preregistration_id="sti-historical-replay-001",
        version="001",
        frozen_at=T0,
        trader_id="QORE_GLOBAL_MACRO_SWING_RESEARCH_INTERFACE",
        trader_version="research-v1",
        trader_config_fingerprint=SHA_A,
        dataset_fingerprint=SHA_B,
        opportunity_universe_fingerprint=SHA_C,
        materiality_policy_fingerprint=SHA_D,
        control_policy_fingerprint=SHA_E,
        treatment_policy_fingerprint=SHA_F,
        split_identity="consumed-development-validation-001",
        research_questions=(
            SharedSTIResearchQuestion.CONTINUATION_POSITIVE_TAIL,
            SharedSTIResearchQuestion.OPPORTUNITY_DISCOVERY,
            SharedSTIResearchQuestion.POSITION_THREAT,
            SharedSTIResearchQuestion.REGIME_TRANSITION,
        ),
        markets=("EURUSD", "XAUUSD"),
        horizons=("D1", "H4", "W1"),
        selection_rule_ref="prereg:selection-rules-001",
        threshold_spec_ref="prereg:thresholds-001",
        metric_definition_refs=(
            "metric:false-alert",
            "metric:missed-alert",
            "metric:winner-preservation",
        ),
        stress_protocol_ref="stress:sti-001",
        temporal_replication_protocol_ref="replication:sti-001",
        source_evidence_refs=(
            "owner-directive-007",
            "sti-causal-replay-contract-001",
            "sti-control-treatment-attribution-001",
        ),
    )


def test_preregistration_freezes_causal_research_without_runtime_authority() -> None:
    prereg = _prereg()

    assert prereg.selection_rules_frozen is True
    assert prereg.thresholds_frozen is True
    assert prereg.development_evidence_only is True
    assert prereg.protected_certification_holdout_opened is False
    assert prereg.protected_certification_holdout_fingerprint is None
    assert prereg.outcome_aware_policy_mutation_authorized is False
    assert prereg.productive_behavior_authority is False
    assert len(prereg.fingerprint()) == 64


def test_preregistration_cannot_open_or_name_protected_holdout() -> None:
    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="cannot open or identify protected certification holdout",
    ):
        replace(_prereg(), protected_certification_holdout_opened=True)

    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="cannot open or identify protected certification holdout",
    ):
        replace(
            _prereg(),
            protected_certification_holdout_fingerprint="1" * 64,
        )


def test_control_and_treatment_policies_must_differ() -> None:
    prereg = _prereg()
    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="policy fingerprints must differ",
    ):
        replace(
            prereg,
            treatment_policy_fingerprint=prereg.control_policy_fingerprint,
        )


def test_preregistration_requires_frozen_selection_and_thresholds() -> None:
    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="must freeze selection rules and thresholds",
    ):
        replace(_prereg(), selection_rules_frozen=False)

    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="must freeze selection rules and thresholds",
    ):
        replace(_prereg(), thresholds_frozen=False)


def test_preregistration_is_development_validation_only() -> None:
    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="development/validation only",
    ):
        replace(_prereg(), development_evidence_only=False)


def test_preregistration_rejects_outcome_aware_mutation_and_productive_authority() -> None:
    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="cannot authorize outcome-aware mutation",
    ):
        replace(_prereg(), outcome_aware_policy_mutation_authorized=True)

    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="cannot authorize productive behavior",
    ):
        replace(_prereg(), productive_behavior_authority=True)


def test_research_questions_and_domains_must_be_canonical() -> None:
    prereg = _prereg()

    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="research questions must be non-empty, unique and canonical",
    ):
        replace(
            prereg,
            research_questions=(
                SharedSTIResearchQuestion.REGIME_TRANSITION,
                SharedSTIResearchQuestion.OPPORTUNITY_DISCOVERY,
            ),
        )

    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="markets must be non-empty, unique and canonical",
    ):
        replace(prereg, markets=("XAUUSD", "EURUSD"))

    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="horizons must be non-empty, unique and canonical",
    ):
        replace(prereg, horizons=("W1", "H4"))


def test_preregistration_requires_sha256_fingerprints() -> None:
    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="dataset_fingerprint must be sha256 hex",
    ):
        replace(_prereg(), dataset_fingerprint="not-a-sha")
