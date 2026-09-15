"""DEMO Risk/Policy cognitive plane (L5): advisory analysis only.

This module owns no risk authority. It produces advisory
:class:`CognitiveAnalysis` values and their provenance receipts, never a
``RiskDecision`` or ``RiskAuthorization``. It deliberately imports only
``RiskError`` / ``RiskValidationError`` / ``RiskFingerprint`` /
``compute_fingerprint`` from ``risk_authority`` and defines no way to construct
an authority-issuing symbol. The cognitive opinion is never risk authority.

Deterministic and fail-closed:

* no ambient clock (``completed_at`` is caller-supplied and timezone-aware);
* no ambient UUID generation (every identity is caller-supplied);
* exact runtime types (``type(x) is ...`` rejects ``bool``/``int``/subclass
  laundering);
* routing is a pure function of the typed situation (no sticky high/max state);
* the transport is an injected Protocol; a real provider probe is not part of
  this unit and no live API key is required.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum, auto
from re import fullmatch
from typing import Protocol, runtime_checkable
from uuid import UUID

from qore.infrastructure.risk_authority import (
    RiskError,
    RiskFingerprint,
    RiskValidationError,
    compute_fingerprint,
)
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success
from qore.modules.cibo.cognitive_contracts import contains_secret_material

__all__ = [
    "CognitiveAnalysis",
    "CognitiveLedger",
    "CognitiveReceipt",
    "CognitiveRequest",
    "CognitiveTransportResult",
    "RiskCognitiveEffort",
    "RiskCognitiveError",
    "RiskCognitiveModel",
    "RiskCognitiveRoute",
    "RiskCognitiveRuntime",
    "RiskCognitiveTransport",
    "RiskCognitiveValidationError",
    "RiskSituationKind",
    "replay_analysis",
    "route_for_situation",
    "validate_no_secret_material",
]


class RiskCognitiveModel(StrEnum):
    """Concrete model a cognitive transport may be routed to (never authority)."""

    TERRA = "gpt-5.6-terra"
    SOL = "gpt-5.6-sol"


class RiskCognitiveEffort(StrEnum):
    """Bounded reasoning effort tiers (never an execution/authority lever)."""

    MEDIUM = "medium"
    HIGH = "high"
    MAX = "max"


class RiskSituationKind(StrEnum):
    """Typed situational signal that drives deterministic routing."""

    ORDINARY_MONITORING = auto()
    MATERIAL_AMBIGUITY = auto()
    CONTRADICTORY_SOURCES = auto()
    EXCEPTIONAL_BREACH_RISK = auto()


class RiskCognitiveError(RiskError):
    """Base error for the advisory cognitive plane."""

    __slots__ = ()


class RiskCognitiveValidationError(RiskCognitiveError):
    """A cognitive value or call violates a deterministic invariant."""

    __slots__ = ()


_CANONICAL_REF_RE = r"[a-z][a-z0-9._:/-]*"


def _validate_uuid(value: object, *, field_name: str) -> None:
    if type(value) is not UUID:
        raise RiskCognitiveValidationError(f"{field_name} must be a UUID")


def _validate_timestamp(value: object, *, field_name: str) -> None:
    if type(value) is not datetime:
        raise RiskCognitiveValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise RiskCognitiveValidationError(f"{field_name} must be timezone-aware")


def _validate_fingerprint(value: object, *, field_name: str) -> None:
    if type(value) is not RiskFingerprint:
        raise RiskCognitiveValidationError(f"{field_name} must be a RiskFingerprint")


def _has_control_chars(text: str) -> bool:
    return any(ord(ch) < 32 or ord(ch) == 127 for ch in text)


def validate_no_secret_material(text: str, *, field_name: str) -> None:
    """Raise :class:`RiskCognitiveValidationError` when ``text`` carries secret material."""

    if type(text) is not str:
        raise RiskCognitiveValidationError(f"{field_name} must be an exact str")
    if contains_secret_material(text):
        raise RiskCognitiveValidationError(
            f"{field_name} must not contain secret material"
        )


def _validate_prompt(value: object, *, field_name: str) -> None:
    if type(value) is not str or not value.strip():
        raise RiskCognitiveValidationError(f"{field_name} must be a non-empty string")
    if _has_control_chars(value):
        raise RiskCognitiveValidationError(
            f"{field_name} must not contain control characters"
        )
    if contains_secret_material(value):
        raise RiskCognitiveValidationError(
            f"{field_name} must not contain secret material"
        )


def _validate_provider_name(value: object, *, field_name: str) -> None:
    if type(value) is not str or not value.strip():
        raise RiskCognitiveValidationError(f"{field_name} must be a non-empty string")
    if _has_control_chars(value):
        raise RiskCognitiveValidationError(
            f"{field_name} must not contain control characters"
        )


def _validate_response_text(value: object, *, field_name: str) -> None:
    if type(value) is not str or not value.strip():
        raise RiskCognitiveValidationError(f"{field_name} must be a non-empty string")
    if contains_secret_material(value):
        raise RiskCognitiveValidationError(
            f"{field_name} must not contain secret material"
        )


def _validate_optional_ref(value: object, *, field_name: str) -> None:
    if value is None:
        return
    if type(value) is not str or not value.strip():
        raise RiskCognitiveValidationError(
            f"{field_name} must be a non-empty string or None"
        )
    if contains_secret_material(value):
        raise RiskCognitiveValidationError(
            f"{field_name} must not contain secret material"
        )


def _canonical_source_refs(value: object, *, field_name: str) -> tuple[str, ...]:
    if type(value) is not tuple or any(type(item) is not str for item in value):
        raise RiskCognitiveValidationError(f"{field_name} must be a tuple of strings")
    for ref in value:
        if fullmatch(_CANONICAL_REF_RE, ref) is None:
            raise RiskCognitiveValidationError(
                f"{field_name} must use canonical reference syntax"
            )
        if contains_secret_material(ref):
            raise RiskCognitiveValidationError(
                f"{field_name} must not contain secret material"
            )
    if len(set(value)) != len(value):
        raise RiskCognitiveValidationError(f"{field_name} must not contain duplicates")
    return tuple(sorted(value))


@dataclass(frozen=True, slots=True)
class RiskCognitiveRoute:
    """Deterministic (model, effort) routing decision for one situation."""

    model: RiskCognitiveModel = RiskCognitiveModel.TERRA
    effort: RiskCognitiveEffort = RiskCognitiveEffort.MEDIUM

    def __post_init__(self) -> None:
        if type(self.model) is not RiskCognitiveModel:
            raise RiskCognitiveValidationError("route model must be RiskCognitiveModel")
        if type(self.effort) is not RiskCognitiveEffort:
            raise RiskCognitiveValidationError("route effort must be RiskCognitiveEffort")


_SITUATION_ROUTES: dict[RiskSituationKind, RiskCognitiveRoute] = {
    RiskSituationKind.ORDINARY_MONITORING: RiskCognitiveRoute(
        RiskCognitiveModel.TERRA, RiskCognitiveEffort.MEDIUM
    ),
    RiskSituationKind.MATERIAL_AMBIGUITY: RiskCognitiveRoute(
        RiskCognitiveModel.TERRA, RiskCognitiveEffort.HIGH
    ),
    RiskSituationKind.CONTRADICTORY_SOURCES: RiskCognitiveRoute(
        RiskCognitiveModel.SOL, RiskCognitiveEffort.HIGH
    ),
    RiskSituationKind.EXCEPTIONAL_BREACH_RISK: RiskCognitiveRoute(
        RiskCognitiveModel.SOL, RiskCognitiveEffort.MAX
    ),
}


def route_for_situation(kind: RiskSituationKind) -> RiskCognitiveRoute:
    """Return the deterministic route for ``kind`` (a pure function of the situation).

    There is no sticky high/max state: routing is a direct typed lookup, so the
    original (lower) situation always maps back to its lower route.
    """

    if type(kind) is not RiskSituationKind:
        raise RiskCognitiveValidationError("kind must be RiskSituationKind")
    return _SITUATION_ROUTES[kind]


@dataclass(frozen=True, slots=True)
class CognitiveRequest:
    """Immutable, secret-free request for one advisory cognitive opinion."""

    request_id: UUID
    situation: RiskSituationKind
    evidence_digest: RiskFingerprint
    source_refs: tuple[str, ...]
    prompt: str

    def __post_init__(self) -> None:
        try:
            _validate_uuid(self.request_id, field_name="request_id")
            if type(self.situation) is not RiskSituationKind:
                raise RiskCognitiveValidationError("situation must be RiskSituationKind")
            _validate_fingerprint(self.evidence_digest, field_name="evidence_digest")
            _validate_prompt(self.prompt, field_name="prompt")
        except RiskCognitiveValidationError as exc:
            raise RiskValidationError(str(exc)) from exc
        try:
            canonical = _canonical_source_refs(self.source_refs, field_name="source_refs")
        except RiskCognitiveValidationError as exc:
            raise RiskValidationError(str(exc)) from exc
        object.__setattr__(self, "source_refs", canonical)

    def logical_values(self) -> tuple[object, ...]:
        return (
            str(self.request_id),
            self.situation.value,
            self.evidence_digest.value,
            self.source_refs,
            self.prompt,
        )


@dataclass(frozen=True, slots=True)
class CognitiveTransportResult:
    """Secret-free result returned by an injected cognitive transport."""

    provider: str
    model: RiskCognitiveModel
    effort: RiskCognitiveEffort
    response_text: str
    provider_response_ref: str | None

    def __post_init__(self) -> None:
        _validate_provider_name(self.provider, field_name="provider")
        if type(self.model) is not RiskCognitiveModel:
            raise RiskCognitiveValidationError(
                "transport result model must be RiskCognitiveModel"
            )
        if type(self.effort) is not RiskCognitiveEffort:
            raise RiskCognitiveValidationError(
                "transport result effort must be RiskCognitiveEffort"
            )
        _validate_response_text(self.response_text, field_name="response_text")
        _validate_optional_ref(
            self.provider_response_ref, field_name="provider_response_ref"
        )


@dataclass(frozen=True, slots=True)
class CognitiveReceipt:
    """Provenance of one admitted advisory output (no hidden chain-of-thought)."""

    receipt_id: UUID
    provider: str
    model: RiskCognitiveModel
    effort: RiskCognitiveEffort
    request_digest: RiskFingerprint
    source_refs: tuple[str, ...]
    routing_fingerprint: RiskFingerprint
    config_fingerprint: RiskFingerprint
    provider_response_ref: str | None
    admitted_output_digest: RiskFingerprint
    completed_at: datetime

    def __post_init__(self) -> None:
        _validate_uuid(self.receipt_id, field_name="receipt_id")
        _validate_provider_name(self.provider, field_name="provider")
        if type(self.model) is not RiskCognitiveModel:
            raise RiskCognitiveValidationError("receipt model must be RiskCognitiveModel")
        if type(self.effort) is not RiskCognitiveEffort:
            raise RiskCognitiveValidationError(
                "receipt effort must be RiskCognitiveEffort"
            )
        for name in (
            "request_digest",
            "routing_fingerprint",
            "config_fingerprint",
            "admitted_output_digest",
        ):
            _validate_fingerprint(getattr(self, name), field_name=name)
        object.__setattr__(
            self,
            "source_refs",
            _canonical_source_refs(self.source_refs, field_name="source_refs"),
        )
        _validate_optional_ref(
            self.provider_response_ref, field_name="provider_response_ref"
        )
        _validate_timestamp(self.completed_at, field_name="completed_at")


@dataclass(frozen=True, slots=True)
class CognitiveAnalysis:
    """Immutable advisory analysis (never a risk decision or authorization)."""

    analysis_id: UUID
    route: RiskCognitiveRoute
    situation: RiskSituationKind
    evidence_digest: RiskFingerprint
    source_refs: tuple[str, ...]
    conclusion: str
    limitations: tuple[str, ...]
    receipt: CognitiveReceipt
    completed_at: datetime

    def __post_init__(self) -> None:
        _validate_uuid(self.analysis_id, field_name="analysis_id")
        if type(self.route) is not RiskCognitiveRoute:
            raise RiskCognitiveValidationError("analysis route must be RiskCognitiveRoute")
        if type(self.situation) is not RiskSituationKind:
            raise RiskCognitiveValidationError("analysis situation must be RiskSituationKind")
        _validate_fingerprint(self.evidence_digest, field_name="evidence_digest")
        object.__setattr__(
            self,
            "source_refs",
            _canonical_source_refs(self.source_refs, field_name="source_refs"),
        )
        _validate_response_text(self.conclusion, field_name="conclusion")
        if type(self.limitations) is not tuple or any(
            type(item) is not str for item in self.limitations
        ):
            raise RiskCognitiveValidationError(
                "limitations must be a tuple of strings"
            )
        for limitation in self.limitations:
            _validate_response_text(limitation, field_name="limitation")
        if type(self.receipt) is not CognitiveReceipt:
            raise RiskCognitiveValidationError("receipt must be CognitiveReceipt")
        _validate_timestamp(self.completed_at, field_name="completed_at")


@runtime_checkable
class RiskCognitiveTransport(Protocol):
    """Injected transport seam producing one secret-free advisory result."""

    def respond(
        self, request: CognitiveRequest
    ) -> Result[CognitiveTransportResult, RiskCognitiveError]:
        """Return an advisory result without lateral authority."""
        ...


class RiskCognitiveRuntime:
    """Deterministic runtime turning a request into an advisory analysis."""

    def __init__(
        self,
        transport: RiskCognitiveTransport,
        *,
        config_fingerprint: RiskFingerprint,
    ) -> None:
        if not callable(getattr(transport, "respond", None)):
            raise RiskCognitiveValidationError(
                "transport must provide a respond method"
            )
        _validate_fingerprint(config_fingerprint, field_name="config_fingerprint")
        self._transport = transport
        self._config_fingerprint = config_fingerprint

    def analyze(
        self,
        request: CognitiveRequest,
        *,
        analysis_id: UUID,
        receipt_id: UUID,
        completed_at: datetime,
    ) -> Result[CognitiveAnalysis, RiskCognitiveError]:
        # 1. Defensive re-validation of the retained request and call inputs.
        try:
            if type(request) is not CognitiveRequest:
                raise RiskCognitiveValidationError("request must be CognitiveRequest")
            request.__post_init__()
            _validate_uuid(analysis_id, field_name="analysis_id")
            _validate_uuid(receipt_id, field_name="receipt_id")
            _validate_timestamp(completed_at, field_name="completed_at")
        except RiskCognitiveValidationError as exc:
            return Failure(exc)
        except RiskValidationError as exc:
            return Failure(RiskCognitiveValidationError(str(exc)))

        # 2. Route deterministically from the situation (pure, no sticky state).
        route = route_for_situation(request.situation)

        # 3. Invoke the injected transport; fail closed on any non-result.
        try:
            response = self._transport.respond(request)
        except RiskCognitiveError as exc:
            return Failure(exc)
        except InfrastructureError as exc:
            return Failure(RiskCognitiveError(f"transport infrastructure failure: {exc}"))
        except Exception as exc:
            return Failure(
                RiskCognitiveError(f"transport raised {type(exc).__name__}: {exc}")
            )

        if isinstance(response, Failure):
            return response
        if not isinstance(response, Success):
            return Failure(
                RiskCognitiveValidationError("transport must return a Result")
            )
        result = response.value
        if type(result) is not CognitiveTransportResult:
            return Failure(
                RiskCognitiveValidationError(
                    "transport success must carry CognitiveTransportResult"
                )
            )

        # 4. The transport must not silently downgrade/upgrade the routed route.
        if result.model is not route.model:
            return Failure(
                RiskCognitiveValidationError("transport model must match routed model")
            )
        if result.effort is not route.effort:
            return Failure(
                RiskCognitiveValidationError("transport effort must match routed effort")
            )

        # 5. Secret-safety re-check on the admitted output.
        try:
            validate_no_secret_material(
                result.response_text, field_name="response_text"
            )
        except RiskCognitiveValidationError as exc:
            return Failure(exc)

        # 6. Build the provenance receipt and the advisory analysis.
        request_digest = compute_fingerprint(request.logical_values())
        admitted_output_digest = compute_fingerprint(result.response_text)
        routing_fingerprint = compute_fingerprint(route.model.value, route.effort.value)

        try:
            receipt = CognitiveReceipt(
                receipt_id=receipt_id,
                provider=result.provider,
                model=result.model,
                effort=result.effort,
                request_digest=request_digest,
                source_refs=request.source_refs,
                routing_fingerprint=routing_fingerprint,
                config_fingerprint=self._config_fingerprint,
                provider_response_ref=result.provider_response_ref,
                admitted_output_digest=admitted_output_digest,
                completed_at=completed_at,
            )
            analysis = CognitiveAnalysis(
                analysis_id=analysis_id,
                route=route,
                situation=request.situation,
                evidence_digest=request.evidence_digest,
                source_refs=request.source_refs,
                conclusion=result.response_text,
                limitations=(),
                receipt=receipt,
                completed_at=completed_at,
            )
        except RiskCognitiveValidationError as exc:
            return Failure(exc)
        return Success(analysis)


@dataclass(frozen=True, slots=True)
class CognitiveLedger:
    """Immutable append-only ledger of retained advisory analyses."""

    records: tuple[CognitiveAnalysis, ...]

    def __post_init__(self) -> None:
        if type(self.records) is not tuple or any(
            type(item) is not CognitiveAnalysis for item in self.records
        ):
            raise RiskCognitiveValidationError(
                "ledger records must contain only CognitiveAnalysis values"
            )
        identities = [item.analysis_id for item in self.records]
        if len(set(identities)) != len(identities):
            raise RiskCognitiveValidationError(
                "ledger analysis identities must be unique"
            )
        object.__setattr__(
            self,
            "records",
            tuple(sorted(self.records, key=lambda item: item.analysis_id.int)),
        )

    def append(self, analysis: CognitiveAnalysis) -> CognitiveLedger:
        """Return a new ledger with one retained analysis appended (never mutates)."""

        if type(analysis) is not CognitiveAnalysis:
            raise RiskCognitiveValidationError("analysis must be CognitiveAnalysis")
        return CognitiveLedger(self.records + (analysis,))

    def replay(self, analysis_id: UUID) -> CognitiveAnalysis | None:
        """Return the retained admitted analysis directly; never calls a transport."""

        _validate_uuid(analysis_id, field_name="analysis_id")
        for analysis in self.records:
            if analysis.analysis_id == analysis_id:
                return analysis
        return None


def replay_analysis(
    ledger: CognitiveLedger, analysis_id: UUID
) -> CognitiveAnalysis | None:
    """Read a retained analysis from ``ledger`` without any provider call."""

    if type(ledger) is not CognitiveLedger:
        raise RiskCognitiveValidationError("ledger must be CognitiveLedger")
    return ledger.replay(analysis_id)
