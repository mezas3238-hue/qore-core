"""Adversarial closure for Correction 003 — Authority-Root Attestation.

Correction 003 removes the forgeable producer-record *attestation* claim entirely.
These tests prove, per canonical law:

- ``PUBLICLY CONSTRUCTIBLE RECORD != AUTHORITY-ROOTED ATTESTATION``
- ``TYPE VALIDITY != PROVENANCE AUTHENTICITY``
- ``CIBO FUNCTIONS != RISK / MARKET / ECONOMIC / LAB CERTIFICATION AUTHORITY``
- ``NO AUTHORITY ROOT -> EVIDENCE_DEPENDENT / FAIL CLOSED``

None of these tests weaken an existing assertion; they replace the Correction-002
"authenticated producer attestation" witnesses with authority-root witnesses.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

import pytest
from _governed_evidence_fixtures import (
    build_forged_economic_result,
    build_forged_market_observation,
    build_forged_risk_decision,
    dependent_evidence,
)

from qore.domain.events import CorrelationId
from qore.functional.decisions import (
    DecisionId,
    DecisionMetadata,
    DecisionOutcome,
    DecisionPriority,
    DecisionReason,
    DecisionReasonCode,
    DecisionStatus,
    DecisionType,
    FunctionalDecision,
)
from qore.infrastructure.cibo import contracts
from qore.infrastructure.cibo.contracts import (
    CiboEvidenceStatus,
    CiboFunctionalEvidence,
    CiboFunctionalValidationError,
    CiboGovernedEvidenceKind,
    synthesize_evidence,
)
from qore.infrastructure.cibo.executive_recommendation import (
    CiboRiskAwareComposer,
    CiboRiskContext,
)
from qore.infrastructure.cibo_trader_capability_profile import CiboEvidenceRef
from qore.kernel.result import Success

_NOW = datetime(2026, 8, 9, 0, 0, tzinfo=UTC)
_COMPOSER = CiboRiskAwareComposer()


# --- Correction 003 core: SUFFICIENT is not manufacturable by CIBO ---


def test_sufficient_evidence_cannot_be_manufactured() -> None:
    # CIBO is not a certification authority; SUFFICIENT requires an external
    # authority-rooted receipt that CIBO cannot manufacture.
    with pytest.raises(CiboFunctionalValidationError):
        CiboFunctionalEvidence(
            status=CiboEvidenceStatus.SUFFICIENT,
            evidence_refs=(CiboEvidenceRef("evidence:anything"),),
            as_of=_NOW,
        )


def test_no_forgeable_governed_material_type_remains() -> None:
    # The Correction-002 attestation-bound material is removed entirely, so there
    # is no route to wrap a public producer record into governed evidence.
    assert not hasattr(contracts, "CiboGovernedEvidenceMaterial")
    assert not hasattr(contracts, "CiboEvidenceAttestation")


def test_forged_risk_decision_is_public_value_record_not_authority_root() -> None:
    forged = build_forged_risk_decision()
    # It is trivially constructible by any caller...
    assert type(forged) is FunctionalDecision
    assert forged.status is DecisionStatus.RESOLVED
    assert forged.decision_type.value.startswith("risk.")
    # ...but a public value record confers no sufficiency.
    with pytest.raises(CiboFunctionalValidationError):
        CiboFunctionalEvidence(
            status=CiboEvidenceStatus.SUFFICIENT,
            evidence_refs=(CiboEvidenceRef("evidence:risk"),),
            as_of=_NOW,
        )


def test_forged_market_observation_is_public_value_record_not_authority_root() -> None:
    forged = build_forged_market_observation()
    assert forged.observation_id is not None
    with pytest.raises(CiboFunctionalValidationError):
        CiboFunctionalEvidence(
            status=CiboEvidenceStatus.SUFFICIENT,
            evidence_refs=(CiboEvidenceRef("evidence:market"),),
            as_of=_NOW,
        )


def test_forged_economic_result_is_public_value_record_not_authority_root() -> None:
    forged = build_forged_economic_result()
    assert forged.result_id is not None
    with pytest.raises(CiboFunctionalValidationError):
        CiboFunctionalEvidence(
            status=CiboEvidenceStatus.SUFFICIENT,
            evidence_refs=(CiboEvidenceRef("evidence:economic"),),
            as_of=_NOW,
        )


# --- Lane 3: Risk adversarial closure ---


def test_direct_risk_decision_cannot_become_risk_context() -> None:
    # CiboRiskContext requires an external-evidence-dependent RISK assessment;
    # a directly constructed FunctionalDecision (or any subclass) is rejected.
    forged = build_forged_risk_decision()
    with pytest.raises(CiboFunctionalValidationError):
        CiboRiskContext(
            risk_evidence=forged,  # type: ignore[arg-type]
            risk_assessment_code="risk.assessment.concentration",
            assessed_at=_NOW,
        )


def test_subclassed_risk_decision_cannot_launder_into_risk_evidence() -> None:
    class FakeRiskDecision(FunctionalDecision):
        pass

    forged = FakeRiskDecision(
        decision_id=DecisionId(UUID("00000000-0000-0000-0000-0000000000aa")),
        timestamp=_NOW,
        decision_type=DecisionType("risk.allocation-governance"),
        status=DecisionStatus.RESOLVED,
        priority=DecisionPriority.NORMAL,
        metadata=DecisionMetadata(correlation_id=CorrelationId(UUID(int=0x0AB))),
        reasons=(
            DecisionReason(
                code=DecisionReasonCode("risk.within-concentration-limits"),
                summary="forged",
            ),
        ),
        outcome=DecisionOutcome.APPROVED,
    )
    # A subclass of the public decision value record is still not authority-rooted
    # and cannot stand in for Risk authority.
    with pytest.raises(CiboFunctionalValidationError):
        CiboRiskContext(
            risk_evidence=forged,  # type: ignore[arg-type]
            risk_assessment_code="risk.assessment.concentration",
            assessed_at=_NOW,
        )


def test_risk_context_requires_risk_dependency_kind() -> None:
    with pytest.raises(CiboFunctionalValidationError):
        CiboRiskContext(
            risk_evidence=dependent_evidence(
                CiboGovernedEvidenceKind.MARKET,
                evidence_refs=(CiboEvidenceRef("evidence:market"),),
                as_of=_NOW,
            ),
            risk_assessment_code="risk.assessment.concentration",
            assessed_at=_NOW,
        )


def test_risk_context_requires_dependent_status() -> None:
    with pytest.raises(CiboFunctionalValidationError):
        CiboRiskContext(
            risk_evidence=CiboFunctionalEvidence(
                status=CiboEvidenceStatus.INSUFFICIENT,
                evidence_refs=(),
                as_of=_NOW,
                reasons=("insufficient",),
            ),
            risk_assessment_code="risk.assessment.concentration",
            assessed_at=_NOW,
        )


def test_future_risk_evidence_rejected() -> None:
    future = dependent_evidence(
        CiboGovernedEvidenceKind.RISK,
        evidence_refs=(CiboEvidenceRef("evidence:risk"),),
        as_of=datetime(2026, 8, 10, 0, 0, tzinfo=UTC),
    )
    with pytest.raises(CiboFunctionalValidationError):
        CiboRiskContext(
            risk_evidence=future,
            risk_assessment_code="risk.assessment.concentration",
            assessed_at=_NOW,
        )


def test_risk_dependent_evidence_fails_closed_at_composer() -> None:
    evidence = dependent_evidence(
        CiboGovernedEvidenceKind.MARKET,
        evidence_refs=(CiboEvidenceRef("evidence:functional"),),
        as_of=_NOW,
    )
    risk = CiboRiskContext(
        risk_evidence=dependent_evidence(
            CiboGovernedEvidenceKind.RISK,
            evidence_refs=(CiboEvidenceRef("evidence:risk"),),
            as_of=_NOW,
        ),
        risk_assessment_code="risk.assessment.concentration",
        assessed_at=_NOW,
    )
    result = _COMPOSER.compose(
        recommendation_code="recommend.allocate",
        functional_evidence=evidence,
        risk_context=risk,
        composed_at=_NOW,
    )
    assert isinstance(result, Success)
    # Correction 003: dependent evidence cannot produce RECOMMEND; it abstains.
    assert result.value.disposition.value == "abstain"


# --- Lane 4: Market / Economic / Lab adversarial closure ---


def test_market_forged_observation_cannot_certify_sufficiency() -> None:
    forged = build_forged_market_observation()
    assert forged.bid is not None and forged.ask is not None
    with pytest.raises(CiboFunctionalValidationError):
        CiboFunctionalEvidence(
            status=CiboEvidenceStatus.SUFFICIENT,
            evidence_refs=(CiboEvidenceRef("evidence:market"),),
            as_of=_NOW,
        )


def test_economic_forged_result_cannot_certify_sufficiency() -> None:
    forged = build_forged_economic_result()
    assert forged.result_id is not None
    with pytest.raises(CiboFunctionalValidationError):
        CiboFunctionalEvidence(
            status=CiboEvidenceStatus.SUFFICIENT,
            evidence_refs=(CiboEvidenceRef("evidence:economic"),),
            as_of=_NOW,
        )


def test_lab_kind_is_explicit_dependency_only() -> None:
    # LAB has no authority-rooted receipt; it can only be an explicit dependency
    # kind on an EVIDENCE_DEPENDENT assessment, never a manufactured SUFFICIENT.
    lab = dependent_evidence(
        CiboGovernedEvidenceKind.LAB,
        evidence_refs=(CiboEvidenceRef("evidence:lab"),),
        as_of=_NOW,
        reasons=("external.lab.authority",),
    )
    assert lab.status is CiboEvidenceStatus.EVIDENCE_DEPENDENT
    assert lab.dependency_kind is CiboGovernedEvidenceKind.LAB
    with pytest.raises(CiboFunctionalValidationError):
        CiboFunctionalEvidence(
            status=CiboEvidenceStatus.SUFFICIENT,
            evidence_refs=(CiboEvidenceRef("evidence:lab"),),
            as_of=_NOW,
        )


# --- Lane 5: recursive / exact-type / temporal regression ---


def test_evidence_status_value_equal_enum_laundering_rejected() -> None:
    class OtherStatus(StrEnum):
        EVIDENCE_DEPENDENT = "evidence-dependent"

    with pytest.raises(CiboFunctionalValidationError):
        CiboFunctionalEvidence(
            status=OtherStatus.EVIDENCE_DEPENDENT,  # type: ignore[arg-type]
            evidence_refs=(),
            as_of=_NOW,
            dependency_kind=CiboGovernedEvidenceKind.MARKET,
            reasons=("external.authority.required",),
        )


def test_dependency_kind_value_equal_enum_laundering_rejected() -> None:
    class OtherKind(StrEnum):
        MARKET = "market"

    with pytest.raises(CiboFunctionalValidationError):
        CiboFunctionalEvidence(
            status=CiboEvidenceStatus.EVIDENCE_DEPENDENT,
            evidence_refs=(),
            as_of=_NOW,
            dependency_kind=OtherKind.MARKET,  # type: ignore[arg-type]
            reasons=("external.authority.required",),
        )


def test_datetime_subclass_timestamp_laundering_rejected() -> None:
    class FakeDatetime(datetime):
        pass

    with pytest.raises(CiboFunctionalValidationError):
        CiboFunctionalEvidence(
            status=CiboEvidenceStatus.INSUFFICIENT,
            evidence_refs=(),
            as_of=FakeDatetime(2026, 8, 10, 0, 0, tzinfo=UTC),
            reasons=("insufficient",),
        )


def test_dependent_evidence_requires_dependency_kind() -> None:
    with pytest.raises(CiboFunctionalValidationError):
        CiboFunctionalEvidence(
            status=CiboEvidenceStatus.EVIDENCE_DEPENDENT,
            evidence_refs=(),
            as_of=_NOW,
            reasons=("external.authority.required",),
        )


def test_dependent_evidence_requires_explicit_reason() -> None:
    with pytest.raises(CiboFunctionalValidationError):
        CiboFunctionalEvidence(
            status=CiboEvidenceStatus.EVIDENCE_DEPENDENT,
            evidence_refs=(),
            as_of=_NOW,
            dependency_kind=CiboGovernedEvidenceKind.MARKET,
        )


def test_dependency_kind_forbidden_for_non_dependent() -> None:
    with pytest.raises(CiboFunctionalValidationError):
        CiboFunctionalEvidence(
            status=CiboEvidenceStatus.INSUFFICIENT,
            evidence_refs=(),
            as_of=_NOW,
            dependency_kind=CiboGovernedEvidenceKind.MARKET,
            reasons=("insufficient",),
        )


def test_synthesize_rejects_corrupted_nested_dependency_kind() -> None:
    corrupted = object.__new__(CiboFunctionalEvidence)
    object.__setattr__(corrupted, "status", CiboEvidenceStatus.EVIDENCE_DEPENDENT)
    object.__setattr__(corrupted, "evidence_refs", (CiboEvidenceRef("evidence:corrupt"),))
    object.__setattr__(corrupted, "as_of", _NOW)
    object.__setattr__(corrupted, "dependency_kind", "market")  # raw string
    object.__setattr__(corrupted, "reasons", ("external.authority.required",))
    with pytest.raises(CiboFunctionalValidationError):
        synthesize_evidence((corrupted,), as_of=_NOW)


def test_synthesize_rejects_heterogeneous_dependency_kinds() -> None:
    market = dependent_evidence(
        CiboGovernedEvidenceKind.MARKET,
        evidence_refs=(CiboEvidenceRef("evidence:market"),),
        as_of=_NOW,
    )
    economic = dependent_evidence(
        CiboGovernedEvidenceKind.ECONOMIC,
        evidence_refs=(CiboEvidenceRef("evidence:economic"),),
        as_of=_NOW,
    )
    with pytest.raises(CiboFunctionalValidationError):
        synthesize_evidence((market, economic), as_of=_NOW)


def test_synthesize_propagates_evidence_dependent_over_insufficient() -> None:
    dependent = dependent_evidence(
        CiboGovernedEvidenceKind.MARKET,
        evidence_refs=(CiboEvidenceRef("evidence:market"),),
        as_of=_NOW,
    )
    insufficient = CiboFunctionalEvidence(
        status=CiboEvidenceStatus.INSUFFICIENT,
        evidence_refs=(),
        as_of=_NOW,
        reasons=("insufficient",),
    )
    mixed = synthesize_evidence((dependent, insufficient), as_of=_NOW)
    assert mixed.status is CiboEvidenceStatus.EVIDENCE_DEPENDENT
    assert mixed.dependency_kind is CiboGovernedEvidenceKind.MARKET


def test_synthesize_deterministic_dependent_reduction() -> None:
    first = dependent_evidence(
        CiboGovernedEvidenceKind.MARKET,
        evidence_refs=(CiboEvidenceRef("evidence:a"),),
        as_of=_NOW,
    )
    second = dependent_evidence(
        CiboGovernedEvidenceKind.MARKET,
        evidence_refs=(CiboEvidenceRef("evidence:b"),),
        as_of=_NOW,
    )
    left = synthesize_evidence((first, second), as_of=_NOW)
    right = synthesize_evidence((second, first), as_of=_NOW)
    assert left == right
    assert left.logical_values() == right.logical_values()
    assert left.status is CiboEvidenceStatus.EVIDENCE_DEPENDENT


# --- no secret / no authority laundering ---


def test_dependent_evidence_logical_values_contain_no_secrets() -> None:
    evidence = dependent_evidence(
        CiboGovernedEvidenceKind.MARKET,
        evidence_refs=(CiboEvidenceRef("evidence:governed"),),
        as_of=_NOW,
    )
    rendered = repr(evidence.logical_values())
    for secret_part in ("private_key", "token=", "secret=", "password=", "authorization:"):
        assert secret_part not in rendered


def test_composer_grants_no_risk_or_execution_authority() -> None:
    for forbidden in ("decide", "execute", "approve", "authorize_risk"):
        assert not hasattr(_COMPOSER, forbidden)
