from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

import pytest
from _governed_evidence_fixtures import dependent_evidence

from qore.infrastructure.cibo.contracts import (
    CiboEvidenceStatus,
    CiboFunctionalAuthority,
    CiboFunctionalEvidence,
    CiboFunctionalValidationError,
    CiboGovernedEvidenceKind,
)
from qore.infrastructure.cibo.core_health import (
    CiboCapabilityHealth,
    CiboCoreHealth,
    CiboHealthSnapshot,
    CiboHealthState,
)
from qore.infrastructure.cibo_trader_capability_profile import CiboEvidenceRef
from qore.kernel.result import Failure, Success

_NOW = datetime(2026, 8, 9, 0, 0, tzinfo=UTC)
_CORE = CiboCoreHealth()


def _capability(
    *,
    code: str = "core.ingestion",
    availability: CiboHealthState = CiboHealthState.HEALTHY,
    stale: tuple[CiboEvidenceRef, ...] = (),
    missing: tuple[CiboEvidenceRef, ...] = (),
    gaps: tuple[CiboEvidenceRef, ...] = (),
) -> CiboCapabilityHealth:
    return CiboCapabilityHealth(
        capability_code=code,
        availability=availability,
        stale_inputs=stale,
        missing_inputs=missing,
        reconciliation_gaps=gaps,
        evidence_pipeline_code=f"{code}.pipeline",
    )


def _evidence(
    status: CiboEvidenceStatus = CiboEvidenceStatus.EVIDENCE_DEPENDENT,
) -> CiboFunctionalEvidence:
    if status is CiboEvidenceStatus.EVIDENCE_DEPENDENT:
        return dependent_evidence(
            CiboGovernedEvidenceKind.ECONOMIC,
            evidence_refs=(CiboEvidenceRef("evidence:core.health"),),
            as_of=_NOW,
            reasons=("external.authority.required",),
        )
    return CiboFunctionalEvidence(
        status=status,
        evidence_refs=(),
        as_of=_NOW,
        reasons=("evidence.insufficient",),
    )


def test_dependent_evidence_degrades_instead_of_healthy() -> None:
    # Correction 003: without an authority-rooted receipt CIBO cannot certify
    # HEALTHY; evidence-dependent inputs fail closed to DEGRADED escalation.
    result = _CORE.assess(
        (_capability(),),
        evidence=_evidence(),
        blockers=(),
        assessed_at=_NOW,
    )
    assert isinstance(result, Success)
    snapshot = result.value
    assert snapshot.overall is CiboHealthState.DEGRADED
    assert snapshot.authority is CiboFunctionalAuthority.ESCALATION


def test_degraded_when_a_capability_is_degraded() -> None:
    result = _CORE.assess(
        (_capability(availability=CiboHealthState.DEGRADED),),
        evidence=_evidence(),
        blockers=(),
        assessed_at=_NOW,
    )
    assert isinstance(result, Success)
    assert result.value.overall is CiboHealthState.DEGRADED
    assert result.value.authority is CiboFunctionalAuthority.ESCALATION


def test_blocked_escalates_with_nonempty_blockers() -> None:
    result = _CORE.assess(
        (_capability(availability=CiboHealthState.BLOCKED),),
        evidence=_evidence(),
        blockers=("core.pipeline.blocked",),
        assessed_at=_NOW,
    )
    assert isinstance(result, Success)
    snapshot = result.value
    assert snapshot.overall is CiboHealthState.BLOCKED
    assert snapshot.authority is CiboFunctionalAuthority.ESCALATION
    assert snapshot.blockers == ("core.pipeline.blocked",)


def test_blocked_without_blockers_fails_closed() -> None:
    result = _CORE.assess(
        (_capability(availability=CiboHealthState.BLOCKED),),
        evidence=_evidence(),
        blockers=(),
        assessed_at=_NOW,
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboFunctionalValidationError)


def test_insufficient_evidence_degrades_without_repair() -> None:
    result = _CORE.assess(
        (_capability(),),
        evidence=_evidence(status=CiboEvidenceStatus.INSUFFICIENT),
        blockers=(),
        assessed_at=_NOW,
    )
    assert isinstance(result, Success)
    snapshot = result.value
    assert snapshot.overall is CiboHealthState.DEGRADED
    assert snapshot.authority is CiboFunctionalAuthority.ESCALATION
    for name in ("repair", "trading", "order", "corrective", "mutation"):
        assert not hasattr(snapshot, name)


@pytest.mark.parametrize(
    "capability",
    [
        CiboCapabilityHealth(
            capability_code="core.stale",
            availability=CiboHealthState.HEALTHY,
            stale_inputs=(CiboEvidenceRef("evidence:stale"),),
            missing_inputs=(),
            reconciliation_gaps=(),
            evidence_pipeline_code="core.stale.pipeline",
        ),
        CiboCapabilityHealth(
            capability_code="core.missing",
            availability=CiboHealthState.HEALTHY,
            stale_inputs=(),
            missing_inputs=(CiboEvidenceRef("evidence:missing"),),
            reconciliation_gaps=(),
            evidence_pipeline_code="core.missing.pipeline",
        ),
        CiboCapabilityHealth(
            capability_code="core.gap",
            availability=CiboHealthState.HEALTHY,
            stale_inputs=(),
            missing_inputs=(),
            reconciliation_gaps=(CiboEvidenceRef("evidence:gap"),),
            evidence_pipeline_code="core.gap.pipeline",
        ),
    ],
)
def test_stale_missing_or_gap_inputs_degrade(capability: CiboCapabilityHealth) -> None:
    result = _CORE.assess(
        (capability,),
        evidence=_evidence(),
        blockers=(),
        assessed_at=_NOW,
    )
    assert isinstance(result, Success)
    assert result.value.overall is CiboHealthState.DEGRADED
    assert result.value.authority is CiboFunctionalAuthority.ESCALATION


def test_repeated_identical_input_equal_logical_values() -> None:
    capabilities = (_capability(code="core.a"), _capability(code="core.b"))
    left = _CORE.assess(
        capabilities,
        evidence=_evidence(),
        blockers=(),
        assessed_at=_NOW,
    )
    right = _CORE.assess(
        capabilities,
        evidence=_evidence(),
        blockers=(),
        assessed_at=_NOW,
    )
    assert isinstance(left, Success)
    assert isinstance(right, Success)
    assert left.value == right.value
    assert left.value.logical_values() == right.value.logical_values()


def test_malformed_nested_type_returns_failure() -> None:
    result = _CORE.assess(
        cast(tuple[CiboCapabilityHealth, ...], (object(),)),
        evidence=_evidence(),
        blockers=(),
        assessed_at=_NOW,
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboFunctionalValidationError)


def test_reflectively_corrupted_capability_returns_failure() -> None:
    corrupted = object.__new__(CiboCapabilityHealth)
    object.__setattr__(corrupted, "capability_code", "core.bad")
    object.__setattr__(corrupted, "availability", "not-a-state")
    object.__setattr__(corrupted, "stale_inputs", ())
    object.__setattr__(corrupted, "missing_inputs", ())
    object.__setattr__(corrupted, "reconciliation_gaps", ())
    object.__setattr__(corrupted, "evidence_pipeline_code", "core.bad.pipeline")
    result = _CORE.assess(
        (corrupted,),
        evidence=_evidence(),
        blockers=(),
        assessed_at=_NOW,
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboFunctionalValidationError)


def test_reflectively_corrupted_evidence_returns_failure() -> None:
    corrupted = object.__new__(CiboFunctionalEvidence)
    object.__setattr__(corrupted, "status", "not-a-status")
    object.__setattr__(corrupted, "evidence_refs", ())
    object.__setattr__(corrupted, "as_of", _NOW)
    object.__setattr__(corrupted, "dependency_kind", None)
    object.__setattr__(corrupted, "reasons", ("evidence.insufficient",))
    result = _CORE.assess(
        (_capability(),),
        evidence=corrupted,
        blockers=(),
        assessed_at=_NOW,
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboFunctionalValidationError)


def test_health_snapshot_cannot_overstate_health_with_blocked_capability() -> None:
    # Constructor/deriver parity: a BLOCKED capability must never coexist with a
    # HEALTHY overall state via direct construction.
    blocked = _capability(code="core.blocked", availability=CiboHealthState.BLOCKED)
    with pytest.raises(CiboFunctionalValidationError):
        CiboHealthSnapshot(
            capabilities=(blocked,),
            overall=CiboHealthState.HEALTHY,
            evidence=_evidence(),
            blockers=(),
            assessed_at=_NOW,
            authority=CiboFunctionalAuthority.OBSERVATION,
        )


def test_health_snapshot_cannot_overstate_health_with_degraded_capability() -> None:
    # A DEGRADED capability also forbids a HEALTHY overall state.
    degraded = _capability(code="core.degraded", availability=CiboHealthState.DEGRADED)
    with pytest.raises(CiboFunctionalValidationError):
        CiboHealthSnapshot(
            capabilities=(degraded,),
            overall=CiboHealthState.HEALTHY,
            evidence=_evidence(),
            blockers=(),
            assessed_at=_NOW,
            authority=CiboFunctionalAuthority.OBSERVATION,
        )
