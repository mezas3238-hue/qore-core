from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

import pytest
from _governed_evidence_fixtures import dependent_evidence

from qore.infrastructure.cibo.contracts import (
    CiboFunctionalAuthority,
    CiboFunctionalEvidence,
    CiboFunctionalValidationError,
    CiboGovernedEvidenceKind,
)
from qore.infrastructure.cibo.specialist_mesh import (
    CiboSpecialistFaculty,
    CiboSpecialistMesh,
    CiboSpecialistOpinion,
)
from qore.infrastructure.cibo_trader_capability_profile import CiboEvidenceRef
from qore.kernel.result import Failure, Success

_NOW = datetime(2026, 8, 9, 0, 0, tzinfo=UTC)
_MESH = CiboSpecialistMesh()


def _ref(code: str) -> CiboEvidenceRef:
    return CiboEvidenceRef(f"evidence:{code}")


def _evidence() -> CiboFunctionalEvidence:
    # A specialist opinion carries evidence-dependent (not self-certified) backing.
    return dependent_evidence(
        CiboGovernedEvidenceKind.MARKET,
        evidence_refs=(_ref("mesh"),),
        as_of=_NOW,
        reasons=("external.authority.required",),
    )


def _opinion(
    faculty: CiboSpecialistFaculty,
    opinion_code: str,
    *,
    authored_at: datetime = _NOW,
) -> CiboSpecialistOpinion:
    return CiboSpecialistOpinion(
        faculty=faculty,
        opinion_code=opinion_code,
        evidence=_evidence(),
        authored_at=authored_at,
        authority=CiboFunctionalAuthority.OPINION,
    )


def test_two_opinions_produce_opinion_summary() -> None:
    first = _opinion(CiboSpecialistFaculty.EQUITY, "momentum-breakout")
    second = _opinion(CiboSpecialistFaculty.FX, "carry-bias")
    result = _MESH.collect((second, first), concluded_at=_NOW)
    assert isinstance(result, Success)
    summary = result.value
    assert summary.authority is CiboFunctionalAuthority.OPINION
    assert summary.faculty_count == 2
    assert summary.opinions == (first, second)


def test_deduplicates_identical_opinions() -> None:
    opinion = _opinion(CiboSpecialistFaculty.EQUITY, "momentum-breakout")
    result = _MESH.collect((opinion, opinion), concluded_at=_NOW)
    assert isinstance(result, Success)
    summary = result.value
    assert summary.faculty_count == 1
    assert summary.opinions == (opinion,)


def test_empty_opinions_rejected() -> None:
    result = _MESH.collect((), concluded_at=_NOW)
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboFunctionalValidationError)


def test_recommendation_authority_opinion_rejected() -> None:
    with pytest.raises(CiboFunctionalValidationError):
        CiboSpecialistOpinion(
            faculty=CiboSpecialistFaculty.EQUITY,
            opinion_code="momentum-breakout",
            evidence=_evidence(),
            authored_at=_NOW,
            authority=CiboFunctionalAuthority.RECOMMENDATION,
        )


def test_observation_authority_opinion_rejected() -> None:
    with pytest.raises(CiboFunctionalValidationError):
        CiboSpecialistOpinion(
            faculty=CiboSpecialistFaculty.EQUITY,
            opinion_code="momentum-breakout",
            evidence=_evidence(),
            authored_at=_NOW,
            authority=CiboFunctionalAuthority.OBSERVATION,
        )


def test_summary_authority_never_escalates() -> None:
    result = _MESH.collect(
        (
            _opinion(CiboSpecialistFaculty.EQUITY, "momentum-breakout"),
            _opinion(CiboSpecialistFaculty.FX, "carry-bias"),
        ),
        concluded_at=_NOW,
    )
    assert isinstance(result, Success)
    assert result.value.authority is CiboFunctionalAuthority.OPINION


def test_wrong_type_opinions_return_typed_failure() -> None:
    bad = cast(tuple[CiboSpecialistOpinion, ...], ("not-opinion",))
    result = _MESH.collect(bad, concluded_at=_NOW)
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboFunctionalValidationError)


def test_repeated_identical_input_equal_logical_values() -> None:
    opinions = (
        _opinion(CiboSpecialistFaculty.EQUITY, "momentum-breakout"),
        _opinion(CiboSpecialistFaculty.FX, "carry-bias"),
    )
    left = _MESH.collect(opinions, concluded_at=_NOW)
    right = _MESH.collect(opinions, concluded_at=_NOW)
    assert isinstance(left, Success)
    assert isinstance(right, Success)
    assert left.value == right.value
    assert left.value.logical_values() == right.value.logical_values()
