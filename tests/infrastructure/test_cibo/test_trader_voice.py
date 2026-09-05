from __future__ import annotations

import dataclasses
from datetime import UTC, datetime, timedelta
from typing import cast

import pytest

from qore.infrastructure.cibo.contracts import (
    CiboFunctionalAuthority,
    CiboFunctionalBlockedError,
    CiboFunctionalValidationError,
)
from qore.infrastructure.cibo.trader_voice import (
    CiboCouncilDisposition,
    CiboCouncilResponse,
    CiboTraderCouncil,
    CiboTraderVoice,
)
from qore.infrastructure.cibo_trader_capability_profile import CiboEvidenceRef
from qore.infrastructure.research_evaluator_identity import (
    ResearchDecisionEvaluatorFamily,
    ResearchDecisionEvaluatorIdentity,
    ResearchDecisionEvaluatorSchemaVersion,
)
from qore.infrastructure.research_run import ResearchSoftwareRevision
from qore.kernel.result import Failure, Success

_NOW = datetime(2026, 8, 9, 0, 0, tzinfo=UTC)
_COUNCIL = CiboTraderCouncil()


def _identity(suffix: str = "vt01") -> ResearchDecisionEvaluatorIdentity:
    return ResearchDecisionEvaluatorIdentity(
        family=ResearchDecisionEvaluatorFamily(f"virtual.trader.{suffix}"),
        schema_version=ResearchDecisionEvaluatorSchemaVersion("v1"),
        software_revision=ResearchSoftwareRevision("rev-1"),
    )


def _voice(
    *,
    authority: CiboFunctionalAuthority = CiboFunctionalAuthority.OPINION,
) -> CiboTraderVoice:
    return CiboTraderVoice(
        trader_identity=_identity(),
        observation_codes=("obs-trend", "obs-volatility"),
        reasoning_code="reasoning-trend-strength",
        opinion_code="opinion-favorable",
        evidence_refs=(CiboEvidenceRef("evidence:voice"),),
        voiced_at=_NOW,
        authority=authority,
    )


# --- NORMAL ---


@pytest.mark.parametrize(
    "disposition,expected_authority",
    [
        (CiboCouncilDisposition.AGREE, CiboFunctionalAuthority.OPINION),
        (CiboCouncilDisposition.DISAGREE, CiboFunctionalAuthority.OPINION),
        (CiboCouncilDisposition.CHALLENGE, CiboFunctionalAuthority.OPINION),
        (CiboCouncilDisposition.REQUEST_EVIDENCE, CiboFunctionalAuthority.OPINION),
        (CiboCouncilDisposition.ROUTE_TO_RESEARCH, CiboFunctionalAuthority.REQUEST),
    ],
)
def test_council_dispositions_map_to_authority(
    disposition: CiboCouncilDisposition,
    expected_authority: CiboFunctionalAuthority,
) -> None:
    result = _COUNCIL.consider(
        _voice(),
        disposition=disposition,
        reason_codes=("council-review",),
        evidence_refs=(CiboEvidenceRef("evidence:council"),),
        responded_at=_NOW,
    )
    assert isinstance(result, Success)
    response: CiboCouncilResponse = result.value
    assert response.disposition is disposition
    assert response.authority is expected_authority


def test_voice_sorts_observation_codes_deterministically() -> None:
    voice = CiboTraderVoice(
        trader_identity=_identity(),
        observation_codes=("obs-b", "obs-a"),
        reasoning_code="reasoning-trend-strength",
        opinion_code="opinion-favorable",
        evidence_refs=(CiboEvidenceRef("evidence:voice"),),
        voiced_at=_NOW,
        authority=CiboFunctionalAuthority.OPINION,
    )
    assert voice.observation_codes == ("obs-a", "obs-b")


# --- ADVERSARIAL ---


@pytest.mark.parametrize(
    "authority",
    [
        CiboFunctionalAuthority.OBSERVATION,
        CiboFunctionalAuthority.RECOMMENDATION,
        CiboFunctionalAuthority.ABSTENTION,
        CiboFunctionalAuthority.ESCALATION,
        CiboFunctionalAuthority.REQUEST,
    ],
)
def test_voice_rejects_non_opinion_authority(
    authority: CiboFunctionalAuthority,
) -> None:
    with pytest.raises(CiboFunctionalValidationError):
        CiboTraderVoice(
            trader_identity=_identity(),
            observation_codes=("obs-trend",),
            reasoning_code="reasoning-trend-strength",
            opinion_code="opinion-favorable",
            evidence_refs=(CiboEvidenceRef("evidence:voice"),),
            voiced_at=_NOW,
            authority=authority,
        )


def test_consider_rejects_reflectively_corrupted_voice_authority() -> None:
    valid = _voice()
    corrupted = object.__new__(CiboTraderVoice)
    for field in dataclasses.fields(CiboTraderVoice):
        value = getattr(valid, field.name)
        if field.name == "authority":
            value = CiboFunctionalAuthority.RECOMMENDATION
        object.__setattr__(corrupted, field.name, value)
    result = _COUNCIL.consider(
        corrupted,
        disposition=CiboCouncilDisposition.AGREE,
        reason_codes=("council-review",),
        evidence_refs=(),
        responded_at=_NOW,
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboFunctionalBlockedError)


def test_consider_rejects_reflectively_corrupted_voice_fields() -> None:
    valid = _voice()
    corrupted = object.__new__(CiboTraderVoice)
    for field in dataclasses.fields(CiboTraderVoice):
        value = getattr(valid, field.name)
        if field.name == "observation_codes":
            value = ("BadCode!",)
        object.__setattr__(corrupted, field.name, value)
    result = _COUNCIL.consider(
        corrupted,
        disposition=CiboCouncilDisposition.AGREE,
        reason_codes=("council-review",),
        evidence_refs=(),
        responded_at=_NOW,
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboFunctionalValidationError)


def test_consider_rejects_wrong_type_voice() -> None:
    result = _COUNCIL.consider(
        cast(CiboTraderVoice, object()),
        disposition=CiboCouncilDisposition.AGREE,
        reason_codes=("council-review",),
        evidence_refs=(),
        responded_at=_NOW,
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboFunctionalValidationError)


def test_consider_rejects_response_before_voice() -> None:
    result = _COUNCIL.consider(
        _voice(),
        disposition=CiboCouncilDisposition.AGREE,
        reason_codes=("council-review",),
        evidence_refs=(),
        responded_at=_NOW - timedelta(seconds=1),
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboFunctionalValidationError)


def test_council_response_requires_request_authority_for_route() -> None:
    with pytest.raises(CiboFunctionalValidationError):
        CiboCouncilResponse(
            voice=_voice(),
            disposition=CiboCouncilDisposition.ROUTE_TO_RESEARCH,
            reason_codes=("council-review",),
            evidence_refs=(),
            responded_at=_NOW,
            authority=CiboFunctionalAuthority.OPINION,
        )


def test_council_response_rejects_escalation_for_route() -> None:
    with pytest.raises(CiboFunctionalValidationError):
        CiboCouncilResponse(
            voice=_voice(),
            disposition=CiboCouncilDisposition.ROUTE_TO_RESEARCH,
            reason_codes=("council-review",),
            evidence_refs=(),
            responded_at=_NOW,
            authority=CiboFunctionalAuthority.ESCALATION,
        )


# --- DETERMINISM / NO SIGNAL AUTHORITY ---


def test_repeated_identical_council_equal_logical_values() -> None:
    left = _COUNCIL.consider(
        _voice(),
        disposition=CiboCouncilDisposition.AGREE,
        reason_codes=("council-review",),
        evidence_refs=(CiboEvidenceRef("evidence:council"),),
        responded_at=_NOW,
    )
    right = _COUNCIL.consider(
        _voice(),
        disposition=CiboCouncilDisposition.AGREE,
        reason_codes=("council-review",),
        evidence_refs=(CiboEvidenceRef("evidence:council"),),
        responded_at=_NOW,
    )
    assert isinstance(left, Success)
    assert isinstance(right, Success)
    assert left.value == right.value
    assert left.value.logical_values() == right.value.logical_values()


def test_voice_and_council_are_not_signals() -> None:
    voice = _voice()
    assert not hasattr(voice, "order")
    assert not hasattr(voice, "signal")
    assert not hasattr(voice, "intent")
    assert not hasattr(voice, "quantity")
    assert not hasattr(_COUNCIL, "execute")
    assert not hasattr(_COUNCIL, "place_order")
