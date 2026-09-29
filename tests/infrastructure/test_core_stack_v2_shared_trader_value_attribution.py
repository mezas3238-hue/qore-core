from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.core_stack_v2.shared_trader_intelligence import (
    SharedTraderIntelligenceValidationError,
)
from qore.infrastructure.core_stack_v2.shared_trader_value_attribution import (
    SharedAttributionDisposition,
    SharedTraderAttributionDesign,
    SharedTraderDecisionCode,
    SharedTraderDecisionRecord,
    SharedTraderStudyArm,
    SharedTraderValueDimension,
    compare_paired_trader_decisions,
)

T0 = datetime(2026, 9, 29, 21, 0, tzinfo=UTC)
SHA_A = "a" * 64
SHA_B = "b" * 64
SHA_C = "c" * 64
SHA_D = "d" * 64
SHA_E = "e" * 64


def _design() -> SharedTraderAttributionDesign:
    return SharedTraderAttributionDesign(
        study_id="sti-attribution-001",
        trader_id="QORE_GLOBAL_MACRO_SWING_RESEARCH",
        trader_version="research-v1",
        trader_config_fingerprint=SHA_A,
        dataset_fingerprint=SHA_B,
        opportunity_universe_fingerprint=SHA_C,
        control_policy_fingerprint=SHA_D,
        treatment_policy_fingerprint=SHA_E,
        preregistration_ref="prereg:sti-attribution-001",
        split_identity="development-validation-001",
        evidence_cutoff_at=T0,
        value_dimensions=(
            SharedTraderValueDimension.ENTRY_DECISION,
            SharedTraderValueDimension.OPPORTUNITY_DISCOVERY,
            SharedTraderValueDimension.POSITION_MANAGEMENT,
        ),
    )


def _control(
    code: SharedTraderDecisionCode = SharedTraderDecisionCode.WAIT,
) -> SharedTraderDecisionRecord:
    return SharedTraderDecisionRecord(
        study_id="sti-attribution-001",
        arm=SharedTraderStudyArm.CONTROL_WITHOUT_PROACTIVE_SHARED,
        opportunity_id="opportunity-001",
        decision_id="control-decision-001",
        decision_time=T0,
        decision_code=code,
        shared_intelligence_ref=None,
        decision_evidence_refs=("trader:control-evidence",),
    )


def _treatment(
    code: SharedTraderDecisionCode = SharedTraderDecisionCode.WAIT,
) -> SharedTraderDecisionRecord:
    return SharedTraderDecisionRecord(
        study_id="sti-attribution-001",
        arm=SharedTraderStudyArm.TREATMENT_WITH_PROACTIVE_SHARED,
        opportunity_id="opportunity-001",
        decision_id="treatment-decision-001",
        decision_time=T0,
        decision_code=code,
        shared_intelligence_ref="shared:snapshot-001",
        decision_evidence_refs=(
            "shared:snapshot-001",
            "trader:treatment-evidence",
        ),
    )


def test_design_requires_same_opportunity_universe() -> None:
    design = _design()

    assert design.same_opportunity_universe_required is True
    assert design.protected_holdout is False
    assert design.productive_behavior_authority is False
    assert len(design.fingerprint()) == 64

    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="requires the same opportunity universe",
    ):
        replace(design, same_opportunity_universe_required=False)


def test_design_rejects_identical_control_and_treatment_policy() -> None:
    design = _design()

    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="policy fingerprints must differ",
    ):
        replace(
            design,
            treatment_policy_fingerprint=design.control_policy_fingerprint,
        )


def test_attribution_design_cannot_open_protected_holdout() -> None:
    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="cannot be opened by attribution design",
    ):
        replace(_design(), protected_holdout=True)


def test_control_arm_cannot_consume_proactive_shared_intelligence() -> None:
    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="control arm cannot consume",
    ):
        replace(
            _control(),
            shared_intelligence_ref="shared:leakage",
        )


def test_treatment_arm_requires_shared_intelligence_reference() -> None:
    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="treatment arm requires",
    ):
        replace(
            _treatment(),
            shared_intelligence_ref=None,
        )


def test_decision_record_cannot_contain_future_outcome() -> None:
    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="cannot contain outcome information",
    ):
        replace(
            _treatment(),
            future_outcome_used=True,
        )

    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="cannot contain outcome information",
    ):
        replace(
            _treatment(),
            outcome_value="+3R",
        )


def test_identical_behavior_yields_no_shared_causal_value_claim() -> None:
    attribution = compare_paired_trader_decisions(
        design=_design(),
        control=_control(SharedTraderDecisionCode.WAIT),
        treatment=_treatment(SharedTraderDecisionCode.WAIT),
    )

    assert attribution.disposition is (
        SharedAttributionDisposition.NO_BEHAVIORAL_DIFFERENCE
    )
    assert attribution.behavioral_difference is False
    assert attribution.causal_economic_value_claim_authorized is False


def test_behavioral_difference_still_does_not_prove_economic_value() -> None:
    attribution = compare_paired_trader_decisions(
        design=_design(),
        control=_control(SharedTraderDecisionCode.WAIT),
        treatment=_treatment(SharedTraderDecisionCode.VALID_TRADE),
    )

    assert attribution.disposition is (
        SharedAttributionDisposition.BEHAVIORAL_DIFFERENCE_OBSERVED
    )
    assert attribution.behavioral_difference is True
    assert attribution.causal_economic_value_claim_authorized is False


def test_paired_attribution_requires_same_opportunity_identity() -> None:
    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="identical opportunity identity",
    ):
        compare_paired_trader_decisions(
            design=_design(),
            control=_control(),
            treatment=replace(
                _treatment(),
                opportunity_id="opportunity-OTHER",
            ),
        )


def test_paired_attribution_requires_same_decision_time() -> None:
    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="identical decision time",
    ):
        compare_paired_trader_decisions(
            design=_design(),
            control=_control(),
            treatment=replace(
                _treatment(),
                decision_time=T0 + timedelta(seconds=1),
            ),
        )


def test_arm_identity_cannot_be_swapped() -> None:
    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="control decision must use control arm",
    ):
        compare_paired_trader_decisions(
            design=_design(),
            control=replace(
                _control(),
                arm=SharedTraderStudyArm.TREATMENT_WITH_PROACTIVE_SHARED,
                shared_intelligence_ref="shared:snapshot-001",
            ),
            treatment=_treatment(),
        )
