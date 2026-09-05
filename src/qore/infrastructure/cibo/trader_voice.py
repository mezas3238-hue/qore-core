"""CF-16 Trader Voice: governed opinions and Council interaction.

A Trader Voice is an OPINION, never a formal signal or order. The Council
interaction only ever produces OPINION/REQUEST responses: it cannot emit a
signal, an order, a Risk decision, or a provider instruction.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from re import fullmatch

from qore.infrastructure.cibo.contracts import (
    CiboFunctionalAuthority,
    CiboFunctionalBlockedError,
    CiboFunctionalError,
    CiboFunctionalValidationError,
)
from qore.infrastructure.cibo_trader_capability_profile import CiboEvidenceRef
from qore.infrastructure.research_evaluator_identity import (
    ResearchDecisionEvaluatorIdentity,
)
from qore.kernel.result import Failure, Result, Success

_CODE_RE = r"[a-z][a-z0-9._-]*"

_SENSITIVE_PARTS = (
    "authorization:",
    "bearer ",
    "client_secret",
    "password=",
    "private_key",
    "secret=",
    "token=",
)


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if type(value) is not datetime:
        raise CiboFunctionalValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise CiboFunctionalValidationError(f"{field_name} must be timezone-aware")


def _validate_code(value: str, *, field_name: str) -> str:
    if not isinstance(value, str) or fullmatch(_CODE_RE, value) is None:
        raise CiboFunctionalValidationError(
            f"{field_name} must use canonical lowercase syntax"
        )
    normalized = value.lower()
    if any(part in normalized for part in _SENSITIVE_PARTS):
        raise CiboFunctionalValidationError(
            f"{field_name} must not contain sensitive material"
        )
    return value


def _validate_codes(values: tuple[str, ...], *, field_name: str) -> tuple[str, ...]:
    if not isinstance(values, tuple) or any(
        not isinstance(value, str) for value in values
    ):
        raise CiboFunctionalValidationError(
            f"{field_name} must be a tuple of strings"
        )
    normalized = tuple(_validate_code(value, field_name=field_name) for value in values)
    if len(set(normalized)) != len(normalized):
        raise CiboFunctionalValidationError(f"{field_name} must not contain duplicates")
    return tuple(sorted(normalized))


def _validate_evidence_refs(
    values: tuple[CiboEvidenceRef, ...],
    *,
    field_name: str,
) -> tuple[CiboEvidenceRef, ...]:
    if not isinstance(values, tuple) or any(
        not isinstance(item, CiboEvidenceRef) for item in values
    ):
        raise CiboFunctionalValidationError(
            f"{field_name} must be a tuple of CiboEvidenceRef"
        )
    if len(set(values)) != len(values):
        raise CiboFunctionalValidationError(f"{field_name} must not contain duplicates")
    return tuple(sorted(values, key=lambda item: item.value))


@dataclass(frozen=True, slots=True)
class CiboTraderVoice:
    """A governed Trader observation/opinion; never a signal or order.

    Authority is fixed to OPINION. The voice carries governed observations, a
    reasoning code, and an opinion code; it binds no order, intent, or execution
    semantics.
    """

    trader_identity: ResearchDecisionEvaluatorIdentity
    observation_codes: tuple[str, ...]
    reasoning_code: str
    opinion_code: str
    evidence_refs: tuple[CiboEvidenceRef, ...]
    voiced_at: datetime
    authority: CiboFunctionalAuthority

    def __post_init__(self) -> None:
        if not isinstance(self.trader_identity, ResearchDecisionEvaluatorIdentity):
            raise CiboFunctionalValidationError(
                "trader identity must be ResearchDecisionEvaluatorIdentity"
            )
        object.__setattr__(
            self,
            "observation_codes",
            _validate_codes(self.observation_codes, field_name="observation codes"),
        )
        object.__setattr__(
            self,
            "reasoning_code",
            _validate_code(self.reasoning_code, field_name="reasoning code"),
        )
        object.__setattr__(
            self,
            "opinion_code",
            _validate_code(self.opinion_code, field_name="opinion code"),
        )
        object.__setattr__(
            self,
            "evidence_refs",
            _validate_evidence_refs(self.evidence_refs, field_name="evidence refs"),
        )
        _validate_timestamp(self.voiced_at, field_name="voiced_at")
        if type(self.authority) is not CiboFunctionalAuthority:
            raise CiboFunctionalValidationError(
                "authority must be CiboFunctionalAuthority"
            )
        if self.authority is not CiboFunctionalAuthority.OPINION:
            raise CiboFunctionalValidationError(
                "trader voice authority must be OPINION; voice != signal"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.trader_identity.logical_values(),
            self.observation_codes,
            self.reasoning_code,
            self.opinion_code,
            tuple(item.logical_values() for item in self.evidence_refs),
            self.voiced_at.isoformat(),
            self.authority.value,
        )


class CiboCouncilDisposition(StrEnum):
    """Deterministic dispositions a Council may attach to a Trader Voice."""

    AGREE = "agree"
    DISAGREE = "disagree"
    CHALLENGE = "challenge"
    REQUEST_EVIDENCE = "request-evidence"
    ROUTE_TO_RESEARCH = "route-to-research"


@dataclass(frozen=True, slots=True)
class CiboCouncilResponse:
    """Immutable Council disposition on a voice; OPINION or REQUEST authority only."""

    voice: CiboTraderVoice
    disposition: CiboCouncilDisposition
    reason_codes: tuple[str, ...]
    evidence_refs: tuple[CiboEvidenceRef, ...]
    responded_at: datetime
    authority: CiboFunctionalAuthority

    def __post_init__(self) -> None:
        if not isinstance(self.voice, CiboTraderVoice):
            raise CiboFunctionalValidationError(
                "council response requires CiboTraderVoice"
            )
        CiboTraderVoice.__post_init__(self.voice)
        if type(self.disposition) is not CiboCouncilDisposition:
            raise CiboFunctionalValidationError(
                "disposition must be CiboCouncilDisposition"
            )
        object.__setattr__(
            self,
            "reason_codes",
            _validate_codes(self.reason_codes, field_name="reason codes"),
        )
        object.__setattr__(
            self,
            "evidence_refs",
            _validate_evidence_refs(self.evidence_refs, field_name="evidence refs"),
        )
        _validate_timestamp(self.responded_at, field_name="responded_at")
        if self.responded_at < self.voice.voiced_at:
            raise CiboFunctionalValidationError(
                "council response cannot predate the trader voice"
            )
        if type(self.authority) is not CiboFunctionalAuthority:
            raise CiboFunctionalValidationError(
                "authority must be CiboFunctionalAuthority"
            )
        expected = (
            CiboFunctionalAuthority.REQUEST
            if self.disposition is CiboCouncilDisposition.ROUTE_TO_RESEARCH
            else CiboFunctionalAuthority.OPINION
        )
        if self.authority is not expected:
            raise CiboFunctionalValidationError(
                "council authority must match the disposition"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.voice.logical_values(),
            self.disposition.value,
            self.reason_codes,
            tuple(item.logical_values() for item in self.evidence_refs),
            self.responded_at.isoformat(),
            self.authority.value,
        )


@dataclass(frozen=True, slots=True)
class CiboTraderCouncil:
    """Deterministic, stateless Council interaction over Trader Voices."""

    def consider(
        self,
        voice: CiboTraderVoice,
        *,
        disposition: CiboCouncilDisposition,
        reason_codes: tuple[str, ...],
        evidence_refs: tuple[CiboEvidenceRef, ...],
        responded_at: datetime,
    ) -> Result[CiboCouncilResponse, CiboFunctionalError]:
        """Produce an OPINION/REQUEST Council response; never a signal or order."""
        if not isinstance(voice, CiboTraderVoice):
            return Failure(
                CiboFunctionalValidationError("council requires CiboTraderVoice")
            )
        if type(disposition) is not CiboCouncilDisposition:
            return Failure(
                CiboFunctionalValidationError(
                    "disposition must be CiboCouncilDisposition"
                )
            )
        if voice.authority is not CiboFunctionalAuthority.OPINION:
            return Failure(
                CiboFunctionalBlockedError(
                    "council only considers OPINION trader voices; voice != signal"
                )
            )
        authority = (
            CiboFunctionalAuthority.REQUEST
            if disposition is CiboCouncilDisposition.ROUTE_TO_RESEARCH
            else CiboFunctionalAuthority.OPINION
        )
        try:
            return Success(
                CiboCouncilResponse(
                    voice=voice,
                    disposition=disposition,
                    reason_codes=reason_codes,
                    evidence_refs=evidence_refs,
                    responded_at=responded_at,
                    authority=authority,
                )
            )
        except CiboFunctionalError as error:
            return Failure(error)
