from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

import pytest
from _governed_evidence_fixtures import dependent_evidence

from qore.infrastructure.cibo.contracts import (
    CiboEvidenceStatus,
    CiboFunctionalBlockedError,
    CiboFunctionalEvidence,
    CiboFunctionalValidationError,
    CiboGovernedEvidenceKind,
)
from qore.infrastructure.cibo.market_monitoring import (
    CiboMonitoringSignal,
    CiboWorldMonitor,
    CiboWorldObservation,
)
from qore.infrastructure.cibo_trader_capability_profile import CiboEvidenceRef
from qore.kernel.result import Failure, Success

_NOW = datetime(2026, 8, 9, 0, 0, tzinfo=UTC)
_MONITOR = CiboWorldMonitor()


def _ref(code: str) -> CiboEvidenceRef:
    return CiboEvidenceRef(f"evidence:{code}")


def _evidence(
    status: CiboEvidenceStatus,
    *,
    refs: tuple[CiboEvidenceRef, ...] = (),
    reasons: tuple[str, ...] = ("assessment",),
) -> CiboFunctionalEvidence:
    if status is CiboEvidenceStatus.EVIDENCE_DEPENDENT:
        return dependent_evidence(
            CiboGovernedEvidenceKind.MARKET,
            evidence_refs=refs,
            as_of=_NOW,
            reasons=reasons or ("external.authority.required",),
        )
    return CiboFunctionalEvidence(
        status=status,
        evidence_refs=refs,
        as_of=_NOW,
        reasons=reasons,
    )


def test_dependent_evidence_fails_closed_instead_of_no_material_change() -> None:
    # Correction 003: CIBO is not a market certification authority, so an
    # evidence-dependent market assessment can never reduce to NO_MATERIAL_CHANGE.
    # The monitor fails closed rather than certifying an unauthenticated fact.
    ref = _ref("eur-usd")
    result = _MONITOR.observe(
        (_evidence(CiboEvidenceStatus.EVIDENCE_DEPENDENT, refs=(ref,)),),
        observed_at=_NOW,
        subject_refs=(ref,),
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboFunctionalBlockedError)


def test_stale_evidence_is_stale_signal_not_material_change() -> None:
    ref = _ref("eur-usd")
    result = _MONITOR.observe(
        (_evidence(CiboEvidenceStatus.STALE, refs=(ref,)),),
        observed_at=_NOW,
        subject_refs=(ref,),
    )
    assert isinstance(result, Success)
    assert result.value.signal is CiboMonitoringSignal.STALE_EVIDENCE


def test_contradictory_evidence_is_contradiction() -> None:
    ref = _ref("eur-usd")
    result = _MONITOR.observe(
        (_evidence(CiboEvidenceStatus.CONTRADICTORY, refs=(ref,)),),
        observed_at=_NOW,
        subject_refs=(ref,),
    )
    assert isinstance(result, Success)
    assert result.value.signal is CiboMonitoringSignal.CONTRADICTION


def test_contradiction_without_subjects_fails_closed() -> None:
    ref = _ref("eur-usd")
    result = _MONITOR.observe(
        (_evidence(CiboEvidenceStatus.CONTRADICTORY, refs=(ref,)),),
        observed_at=_NOW,
        subject_refs=(),
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboFunctionalValidationError)


def test_missing_evidence_is_evidence_gap() -> None:
    result = _MONITOR.observe(
        (_evidence(CiboEvidenceStatus.MISSING, refs=(), reasons=("gap",)),),
        observed_at=_NOW,
        subject_refs=(),
    )
    assert isinstance(result, Success)
    assert result.value.signal is CiboMonitoringSignal.EVIDENCE_GAP


def test_insufficient_evidence_fails_closed() -> None:
    ref = _ref("eur-usd")
    result = _MONITOR.observe(
        (_evidence(CiboEvidenceStatus.INSUFFICIENT, refs=(ref,), reasons=("thin",)),),
        observed_at=_NOW,
        subject_refs=(ref,),
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboFunctionalBlockedError)


def test_monitor_never_invents_material_change() -> None:
    ref = _ref("eur-usd")
    result = _MONITOR.observe(
        (_evidence(CiboEvidenceStatus.EVIDENCE_DEPENDENT, refs=(ref,)),),
        observed_at=_NOW,
        subject_refs=(ref,),
    )
    # Evidence-dependent market input never resolves to a material-fact signal.
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboFunctionalBlockedError)


def test_wrong_type_assessments_return_typed_failure() -> None:
    bad = cast(tuple[CiboFunctionalEvidence, ...], ("not-evidence",))
    result = _MONITOR.observe(bad, observed_at=_NOW, subject_refs=())
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboFunctionalValidationError)


def test_explicit_material_change_requires_sufficient_evidence() -> None:
    # A material-change signal demands SUFFICIENT (authority-rooted) evidence.
    # Since CIBO cannot manufacture SUFFICIENT, an evidence-dependent assessment
    # can never back a material change and fails closed.
    ref = _ref("eur-usd")
    evidence = _evidence(CiboEvidenceStatus.EVIDENCE_DEPENDENT, refs=(ref,))
    with pytest.raises(CiboFunctionalValidationError):
        CiboWorldObservation(
            signal=CiboMonitoringSignal.MATERIAL_CHANGE,
            evidence=evidence,
            observed_at=_NOW,
            subject_refs=(ref,),
            reasons=(),
        )


def test_no_material_change_requires_sufficient_evidence() -> None:
    # Constructor/deriver parity: NO_MATERIAL_CHANGE is the all-clear conclusion
    # the reducer only emits from SUFFICIENT evidence; it must not be admitted on
    # insufficient evidence by direct construction.
    ref = _ref("eur-usd")
    evidence = _evidence(
        CiboEvidenceStatus.INSUFFICIENT,
        refs=(ref,),
        reasons=("thin",),
    )
    with pytest.raises(CiboFunctionalValidationError):
        CiboWorldObservation(
            signal=CiboMonitoringSignal.NO_MATERIAL_CHANGE,
            evidence=evidence,
            observed_at=_NOW,
            subject_refs=(),
            reasons=("thin",),
        )


def test_repeated_identical_input_equal_logical_values() -> None:
    ref = _ref("eur-usd")
    assessments = (_evidence(CiboEvidenceStatus.STALE, refs=(ref,)),)
    left = _MONITOR.observe(assessments, observed_at=_NOW, subject_refs=(ref,))
    right = _MONITOR.observe(assessments, observed_at=_NOW, subject_refs=(ref,))
    assert isinstance(left, Success)
    assert isinstance(right, Success)
    assert left.value == right.value
    assert left.value.logical_values() == right.value.logical_values()
