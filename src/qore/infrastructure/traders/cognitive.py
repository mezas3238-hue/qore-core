"""Governed Trader-local cognitive wrapper (adaptive cognition contract #492).

The cognitive layer is a CHANNEL, never a reasoning tier and never a source of
authority. Its deterministic flow is:

``DETERMINISTIC TRADER STATE + EXACT EVIDENCE -> COGNITIVE INTERPRETATION ->
OPINION / EXPLANATION / QUESTION / DOUBT``

Provider-neutral routing is decided ONLY from a typed ``TraderCognitiveSituation``
(never from prompt text), so voice, text, and UI share the exact same routing and
words such as ``urgent``, ``MAX``, or ``controversy`` cannot self-escalate.

Routing law (from #492):

- routine explanation/voice/context            -> ``gpt-5.6-terra`` / medium;
- ambiguous evidence within specialty          -> ``gpt-5.6-terra`` / high;
- serious internal contradiction               -> governed escalation request
  (the trader may NOT self-grant Sol/MAX or authority);
- material conflict between Traders            -> CIBO adjudication (Sol / high);
- unresolved material multi-Trader conflict    -> CIBO ``COUNCIL_ADVERSARIAL`` (Sol / max).

Every opinion binds the exact deterministic setup/state reference, the evidence
subset actually used, the provider/model/effort receipt, and provenance. No
opinion carries an order, account, quantity, Risk approval, or Production/
real-capital authority.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from hashlib import sha256

from qore.infrastructure.traders.contracts import (
    DemoTradingConfigFingerprint,
    DemoTradingEvidenceRef,
    DemoTradingMethodologyFingerprint,
    DemoTradingMethodologyId,
    DemoTradingMethodologyVersion,
    DemoTradingTraderCode,
    DemoTradingTraderVersion,
)
from qore.kernel.errors import InfrastructureError

TERRA_MODEL = "gpt-5.6-terra"
SOL_MODEL = "gpt-5.6-sol"


class TraderCognitiveError(InfrastructureError):
    """Base error for governed Trader-local cognition."""

    __slots__ = ()


class TraderCognitiveValidationError(TraderCognitiveError):
    """A Trader cognitive value violated a governed #492 invariant."""

    __slots__ = ()


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if type(value) is not datetime:
        raise TraderCognitiveValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise TraderCognitiveValidationError(f"{field_name} must be timezone-aware")


def _utc_iso(value: datetime, *, field_name: str) -> str:
    _validate_timestamp(value, field_name=field_name)
    return value.astimezone(UTC).isoformat(timespec="microseconds")


def _validate_text(value: str, *, field_name: str, max_length: int = 4000) -> str:
    if type(value) is not str or not value.strip():
        raise TraderCognitiveValidationError(f"{field_name} must be non-empty text")
    if any(ch in value for ch in "\x00\n\r\t"):
        raise TraderCognitiveValidationError(f"{field_name} must not contain control chars")
    if len(value) > max_length:
        raise TraderCognitiveValidationError(f"{field_name} exceeds maximum length")
    return value


def _canonical_evidence_refs(
    values: tuple[DemoTradingEvidenceRef, ...],
    *,
    field_name: str,
) -> tuple[DemoTradingEvidenceRef, ...]:
    """Validate and deterministically order (deduped) evidence refs."""

    if type(values) is not tuple or any(
        type(item) is not DemoTradingEvidenceRef for item in values
    ):
        raise TraderCognitiveValidationError(
            f"{field_name} must be an immutable DemoTradingEvidenceRef tuple"
        )
    if len(set(values)) != len(values):
        raise TraderCognitiveValidationError(f"{field_name} must not contain duplicates")
    return tuple(sorted(values, key=lambda item: item.value))


class TraderCognitiveMode(StrEnum):
    """Typed situational signal that decides routing (never prompt text)."""

    ROUTINE = "routine"
    AMBIGUOUS = "ambiguous"
    CONTRADICTION = "contradiction"
    CONFLICT = "conflict"
    COUNCIL_ADVERSARIAL = "council-adversarial"


class TraderCognitiveRouting(StrEnum):
    """Governed routing outcome (provider-neutral)."""

    TERRA_MEDIUM = "terra-medium"
    TERRA_HIGH = "terra-high"
    ESCALATION_REQUEST = "escalation-request"
    CIBO_HIGH = "cibo-high"
    CIBO_MAX = "cibo-max"


class TraderCognitiveDestination(StrEnum):
    """Where a routed cognition is directed."""

    TRADER_LOCAL = "trader-local"
    GOVERNED_ESCALATION = "governed-escalation"
    CIBO_ADJUDICATION = "cibo-adjudication"


@dataclass(frozen=True, slots=True)
class TraderCognitiveSituation:
    """Explicit typed signals used to route Trader cognition.

    There is intentionally no text/prompt field: routing can never be influenced
    by prompt wording such as ``urgent``, ``MAX``, or ``controversy``.
    """

    mode: TraderCognitiveMode = TraderCognitiveMode.ROUTINE

    def __post_init__(self) -> None:
        if type(self.mode) is not TraderCognitiveMode:
            raise TraderCognitiveValidationError(
                "cognitive situation mode must be TraderCognitiveMode"
            )


@dataclass(frozen=True, slots=True)
class TraderCognitiveRoute:
    """Exact governed routing: semantic mode + provider model/effort + destination."""

    routing: TraderCognitiveRouting
    model: str | None
    effort: str | None
    destination: TraderCognitiveDestination

    def __post_init__(self) -> None:
        if type(self.routing) is not TraderCognitiveRouting:
            raise TraderCognitiveValidationError(
                "route routing must be TraderCognitiveRouting"
            )
        if type(self.destination) is not TraderCognitiveDestination:
            raise TraderCognitiveValidationError(
                "route destination must be TraderCognitiveDestination"
            )
        if self.routing in (
            TraderCognitiveRouting.ESCALATION_REQUEST,
        ):
            if self.model is not None or self.effort is not None:
                raise TraderCognitiveValidationError(
                    "escalation request must not self-grant model or effort"
                )
            if self.destination is not TraderCognitiveDestination.GOVERNED_ESCALATION:
                raise TraderCognitiveValidationError(
                    "escalation request must target governed escalation"
                )
        else:
            if type(self.model) is not str or not self.model:
                raise TraderCognitiveValidationError("route model must be a non-empty str")
            if type(self.effort) is not str or not self.effort:
                raise TraderCognitiveValidationError("route effort must be a non-empty str")

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.routing.value,
            self.model,
            self.effort,
            self.destination.value,
        )


_ROUTING_TABLE: dict[TraderCognitiveMode, tuple[str, str | None, str | None, str]] = {
    TraderCognitiveMode.ROUTINE: (
        TraderCognitiveRouting.TERRA_MEDIUM.value,
        TERRA_MODEL,
        "medium",
        TraderCognitiveDestination.TRADER_LOCAL.value,
    ),
    TraderCognitiveMode.AMBIGUOUS: (
        TraderCognitiveRouting.TERRA_HIGH.value,
        TERRA_MODEL,
        "high",
        TraderCognitiveDestination.TRADER_LOCAL.value,
    ),
    TraderCognitiveMode.CONTRADICTION: (
        TraderCognitiveRouting.ESCALATION_REQUEST.value,
        None,
        None,
        TraderCognitiveDestination.GOVERNED_ESCALATION.value,
    ),
    TraderCognitiveMode.CONFLICT: (
        TraderCognitiveRouting.CIBO_HIGH.value,
        SOL_MODEL,
        "high",
        TraderCognitiveDestination.CIBO_ADJUDICATION.value,
    ),
    TraderCognitiveMode.COUNCIL_ADVERSARIAL: (
        TraderCognitiveRouting.CIBO_MAX.value,
        SOL_MODEL,
        "max",
        TraderCognitiveDestination.CIBO_ADJUDICATION.value,
    ),
}


def route_trader_cognition(
    situation: TraderCognitiveSituation,
) -> TraderCognitiveRoute:
    """Route Trader cognition from the typed situation (channel-independent).

    Voice, text, and UI must all call this same function with the same typed
    situation; no channel may force a higher model/effort.
    """

    if type(situation) is not TraderCognitiveSituation:
        raise TraderCognitiveValidationError(
            "cognitive routing requires TraderCognitiveSituation"
        )
    # Re-enter the situation invariant at the trust boundary. A reflectively
    # corrupted ``mode`` (a plain string that hash/equality-collides with a
    # StrEnum member) must fail closed here instead of silently self-escalating
    # routing (e.g. a raw "council-adversarial" must never reach CIBO_MAX).
    situation.__post_init__()
    routing, model, effort, destination = _ROUTING_TABLE[situation.mode]
    return TraderCognitiveRoute(
        routing=TraderCognitiveRouting(routing),
        model=model,
        effort=effort,
        destination=TraderCognitiveDestination(destination),
    )


class TraderCognitiveProvenance(StrEnum):
    """Dialogue provenance of an opinion."""

    INDEPENDENT = "independent"
    REPLY_TO_CIBO = "reply-to-cibo"
    REPLY_TO_CEO = "reply-to-ceo"
    REPLY_TO_TRADER = "reply-to-trader"


@dataclass(frozen=True, slots=True)
class TraderCognitiveReceipt:
    """Immutable, replay-safe provider/model/effort receipt for one opinion."""

    routing: TraderCognitiveRouting
    model: str | None
    effort: str | None
    fingerprint: DemoTradingConfigFingerprint

    def __post_init__(self) -> None:
        if type(self.routing) is not TraderCognitiveRouting:
            raise TraderCognitiveValidationError(
                "receipt routing must be TraderCognitiveRouting"
            )
        if type(self.fingerprint) is not DemoTradingConfigFingerprint:
            raise TraderCognitiveValidationError(
                "receipt fingerprint must be DemoTradingConfigFingerprint"
            )
        if self.routing is TraderCognitiveRouting.ESCALATION_REQUEST:
            if self.model is not None or self.effort is not None:
                raise TraderCognitiveValidationError(
                    "escalation receipt must not carry model or effort"
                )
        else:
            if type(self.model) is not str or not self.model:
                raise TraderCognitiveValidationError("receipt model must be a non-empty str")
            if type(self.effort) is not str or not self.effort:
                raise TraderCognitiveValidationError("receipt effort must be a non-empty str")

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.routing.value,
            self.model,
            self.effort,
            self.fingerprint.logical_values(),
        )


def compute_trader_cognitive_receipt_fingerprint(
    *,
    routing: TraderCognitiveRouting,
    model: str | None,
    effort: str | None,
    issued_at: datetime,
) -> DemoTradingConfigFingerprint:
    """Derive a replay-safe receipt fingerprint from retained provider material."""

    if type(routing) is not TraderCognitiveRouting:
        raise TraderCognitiveValidationError("receipt fingerprint requires a routing")
    _validate_timestamp(issued_at, field_name="receipt issued_at")
    canonical = {
        "schema": "qore.trader.cognitive.receipt.v1",
        "routing": routing.value,
        "model": model,
        "effort": effort,
        "issued_at": _utc_iso(issued_at, field_name="receipt issued_at"),
    }
    return DemoTradingConfigFingerprint(
        sha256(
            json.dumps(
                canonical,
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        ).hexdigest()
    )


def build_trader_cognitive_receipt(
    *,
    route: TraderCognitiveRoute,
    issued_at: datetime,
) -> TraderCognitiveReceipt:
    """Build a receipt whose model/effort exactly matches the governed route."""

    if type(route) is not TraderCognitiveRoute:
        raise TraderCognitiveValidationError("receipt requires TraderCognitiveRoute")
    _validate_timestamp(issued_at, field_name="receipt issued_at")
    fingerprint = compute_trader_cognitive_receipt_fingerprint(
        routing=route.routing,
        model=route.model,
        effort=route.effort,
        issued_at=issued_at,
    )
    return TraderCognitiveReceipt(
        routing=route.routing,
        model=route.model,
        effort=route.effort,
        fingerprint=fingerprint,
    )


@dataclass(frozen=True, slots=True)
class TraderCognitiveOpinion:
    """An admitted Trader cognitive opinion bound to exact deterministic state.

    The opinion references the deterministic output (by its replay-safe
    fingerprint) and the exact evidence subset it uses. It carries no setup of
    its own, no order/account/quantity/Risk/Production authority, and no hidden
    chain-of-thought. Its receipt is immutable and replay-safe: replay must reuse
    the retained receipt rather than re-call a changed external model.
    """

    trader_code: DemoTradingTraderCode
    version: DemoTradingTraderVersion
    config_fingerprint: DemoTradingConfigFingerprint
    methodology_id: DemoTradingMethodologyId
    methodology_version: DemoTradingMethodologyVersion
    methodology_fingerprint: DemoTradingMethodologyFingerprint
    deterministic_output_fingerprint: DemoTradingConfigFingerprint
    supplied_evidence_refs: tuple[DemoTradingEvidenceRef, ...]
    evidence_refs: tuple[DemoTradingEvidenceRef, ...]
    situation: TraderCognitiveSituation
    receipt: TraderCognitiveReceipt
    provenance: TraderCognitiveProvenance
    thesis: str
    invalidation: str
    limitations: tuple[str, ...]
    voiced_at: datetime
    opinion_fingerprint: DemoTradingConfigFingerprint

    def __post_init__(self) -> None:
        if type(self.trader_code) is not DemoTradingTraderCode:
            raise TraderCognitiveValidationError(
                "opinion requires DemoTradingTraderCode"
            )
        if type(self.version) is not DemoTradingTraderVersion:
            raise TraderCognitiveValidationError(
                "opinion requires DemoTradingTraderVersion"
            )
        if type(self.config_fingerprint) is not DemoTradingConfigFingerprint:
            raise TraderCognitiveValidationError(
                "opinion requires DemoTradingConfigFingerprint"
            )
        if type(self.methodology_id) is not DemoTradingMethodologyId:
            raise TraderCognitiveValidationError(
                "opinion requires DemoTradingMethodologyId"
            )
        if type(self.methodology_version) is not DemoTradingMethodologyVersion:
            raise TraderCognitiveValidationError(
                "opinion requires DemoTradingMethodologyVersion"
            )
        if type(self.methodology_fingerprint) is not DemoTradingMethodologyFingerprint:
            raise TraderCognitiveValidationError(
                "opinion requires DemoTradingMethodologyFingerprint"
            )
        if type(self.deterministic_output_fingerprint) is not DemoTradingConfigFingerprint:
            raise TraderCognitiveValidationError(
                "opinion requires the deterministic output fingerprint"
            )
        object.__setattr__(
            self,
            "supplied_evidence_refs",
            _canonical_evidence_refs(
                self.supplied_evidence_refs, field_name="opinion supplied evidence"
            ),
        )
        object.__setattr__(
            self,
            "evidence_refs",
            _canonical_evidence_refs(self.evidence_refs, field_name="opinion evidence"),
        )
        supplied = set(self.supplied_evidence_refs)
        if any(ref not in supplied for ref in self.evidence_refs):
            raise TraderCognitiveValidationError(
                "opinion may only use evidence present in the deterministic state"
            )
        if type(self.situation) is not TraderCognitiveSituation:
            raise TraderCognitiveValidationError(
                "opinion requires TraderCognitiveSituation"
            )
        if type(self.receipt) is not TraderCognitiveReceipt:
            raise TraderCognitiveValidationError(
                "opinion requires TraderCognitiveReceipt"
            )
        if type(self.provenance) is not TraderCognitiveProvenance:
            raise TraderCognitiveValidationError(
                "opinion provenance must be TraderCognitiveProvenance"
            )
        # Provider model/effort must match the governed route for the situation.
        expected_route = route_trader_cognition(self.situation)
        if self.receipt.routing is not expected_route.routing:
            raise TraderCognitiveValidationError(
                "receipt routing must match the governed route"
            )
        if self.receipt.model != expected_route.model:
            raise TraderCognitiveValidationError(
                "receipt model must match the governed route"
            )
        if self.receipt.effort != expected_route.effort:
            raise TraderCognitiveValidationError(
                "receipt effort must match the governed route"
            )
        object.__setattr__(
            self,
            "thesis",
            _validate_text(self.thesis, field_name="opinion thesis", max_length=4000),
        )
        object.__setattr__(
            self,
            "invalidation",
            _validate_text(
                self.invalidation,
                field_name="opinion invalidation",
                max_length=4000,
            ),
        )
        if type(self.limitations) is not tuple or any(
            type(item) is not str or not item.strip() for item in self.limitations
        ):
            raise TraderCognitiveValidationError(
                "opinion limitations must be a non-empty string tuple"
            )
        _validate_timestamp(self.voiced_at, field_name="opinion voiced_at")
        expected_receipt = compute_trader_cognitive_receipt_fingerprint(
            routing=self.receipt.routing,
            model=self.receipt.model,
            effort=self.receipt.effort,
            issued_at=self.voiced_at,
        )
        if self.receipt.fingerprint != expected_receipt:
            raise TraderCognitiveValidationError(
                "receipt fingerprint must bind routing, model, effort, and voiced_at"
            )
        if type(self.opinion_fingerprint) is not DemoTradingConfigFingerprint:
            raise TraderCognitiveValidationError(
                "opinion requires a replay-safe fingerprint"
            )
        expected = compute_trader_cognitive_opinion_fingerprint(
            trader_code=self.trader_code,
            version=self.version,
            config_fingerprint=self.config_fingerprint,
            methodology_id=self.methodology_id,
            methodology_version=self.methodology_version,
            methodology_fingerprint=self.methodology_fingerprint,
            deterministic_output_fingerprint=self.deterministic_output_fingerprint,
            supplied_evidence_refs=self.supplied_evidence_refs,
            evidence_refs=self.evidence_refs,
            situation=self.situation,
            receipt=self.receipt,
            provenance=self.provenance,
            thesis=self.thesis,
            invalidation=self.invalidation,
            limitations=self.limitations,
            voiced_at=self.voiced_at,
        )
        if self.opinion_fingerprint != expected:
            raise TraderCognitiveValidationError(
                "opinion fingerprint must match the exact retained opinion"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.trader_code.logical_values(),
            self.version.logical_values(),
            self.config_fingerprint.logical_values(),
            self.methodology_id.logical_values(),
            self.methodology_version.logical_values(),
            self.methodology_fingerprint.logical_values(),
            self.deterministic_output_fingerprint.logical_values(),
            tuple(item.logical_values() for item in self.supplied_evidence_refs),
            tuple(item.logical_values() for item in self.evidence_refs),
            self.situation.mode.value,
            self.receipt.logical_values(),
            self.provenance.value,
            self.thesis,
            self.invalidation,
            self.limitations,
            _utc_iso(self.voiced_at, field_name="opinion voiced_at"),
            self.opinion_fingerprint.logical_values(),
        )


def compute_trader_cognitive_opinion_fingerprint(
    *,
    trader_code: DemoTradingTraderCode,
    version: DemoTradingTraderVersion,
    config_fingerprint: DemoTradingConfigFingerprint,
    methodology_id: DemoTradingMethodologyId,
    methodology_version: DemoTradingMethodologyVersion,
    methodology_fingerprint: DemoTradingMethodologyFingerprint,
    deterministic_output_fingerprint: DemoTradingConfigFingerprint,
    supplied_evidence_refs: tuple[DemoTradingEvidenceRef, ...],
    evidence_refs: tuple[DemoTradingEvidenceRef, ...],
    situation: TraderCognitiveSituation,
    receipt: TraderCognitiveReceipt,
    provenance: TraderCognitiveProvenance,
    thesis: str,
    invalidation: str,
    limitations: tuple[str, ...],
    voiced_at: datetime,
) -> DemoTradingConfigFingerprint:
    """Derive the replay-safe logical identity of one admitted opinion."""

    if type(trader_code) is not DemoTradingTraderCode:
        raise TraderCognitiveValidationError("opinion fingerprint requires trader code")
    if type(version) is not DemoTradingTraderVersion:
        raise TraderCognitiveValidationError("opinion fingerprint requires version")
    if type(config_fingerprint) is not DemoTradingConfigFingerprint:
        raise TraderCognitiveValidationError("opinion fingerprint requires config")
    if type(methodology_id) is not DemoTradingMethodologyId:
        raise TraderCognitiveValidationError("opinion fingerprint requires methodology")
    if type(methodology_version) is not DemoTradingMethodologyVersion:
        raise TraderCognitiveValidationError("opinion fingerprint requires methodology version")
    if type(methodology_fingerprint) is not DemoTradingMethodologyFingerprint:
        raise TraderCognitiveValidationError("opinion fingerprint requires methodology fp")
    if type(deterministic_output_fingerprint) is not DemoTradingConfigFingerprint:
        raise TraderCognitiveValidationError(
            "opinion fingerprint requires deterministic output fp"
        )
    if type(evidence_refs) is not tuple or any(
        type(item) is not DemoTradingEvidenceRef for item in evidence_refs
    ):
        raise TraderCognitiveValidationError("opinion fingerprint evidence must be typed")
    if type(supplied_evidence_refs) is not tuple or any(
        type(item) is not DemoTradingEvidenceRef for item in supplied_evidence_refs
    ):
        raise TraderCognitiveValidationError(
            "opinion fingerprint supplied evidence must be typed"
        )
    if type(situation) is not TraderCognitiveSituation:
        raise TraderCognitiveValidationError("opinion fingerprint requires situation")
    if type(receipt) is not TraderCognitiveReceipt:
        raise TraderCognitiveValidationError("opinion fingerprint requires receipt")
    if type(provenance) is not TraderCognitiveProvenance:
        raise TraderCognitiveValidationError("opinion fingerprint requires provenance")
    # Re-enter nested invariants: a reflectively corrupted situation mode or
    # receipt routing must produce a typed validation error rather than leaking
    # an AttributeError from ``.value`` / ``logical_values()`` below.
    situation.__post_init__()
    receipt.__post_init__()
    _validate_timestamp(voiced_at, field_name="opinion fingerprint voiced_at")
    canonical = {
        "schema": "qore.trader.cognitive.opinion.v1",
        "trader_code": trader_code.value,
        "version": version.value,
        "config_fingerprint": config_fingerprint.value,
        "methodology_id": methodology_id.value,
        "methodology_version": methodology_version.value,
        "methodology_fingerprint": methodology_fingerprint.value,
        "deterministic_output_fingerprint": deterministic_output_fingerprint.value,
        "supplied_evidence_refs": tuple(sorted(item.value for item in supplied_evidence_refs)),
        "evidence_refs": tuple(sorted(item.value for item in evidence_refs)),
        "situation": situation.mode.value,
        "receipt": list(receipt.logical_values()),
        "provenance": provenance.value,
        "thesis": thesis,
        "invalidation": invalidation,
        "limitations": list(limitations),
        "voiced_at": _utc_iso(voiced_at, field_name="opinion voiced_at"),
    }
    return DemoTradingConfigFingerprint(
        sha256(
            json.dumps(
                canonical,
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        ).hexdigest()
    )


@dataclass(frozen=True, slots=True)
class TraderVoiceChannel:
    """A voice channel. It is a CHANNEL, never a reasoning tier.

    Voice, text, and UI must produce the same routing class for the same typed
    situation; speaking must not force HIGH/MAX.
    """

    channel: str

    def __post_init__(self) -> None:
        if type(self.channel) is not str or not self.channel.strip():
            raise TraderCognitiveValidationError("voice channel must be non-empty")

    def route(self, situation: TraderCognitiveSituation) -> TraderCognitiveRoute:
        """Route identically to every other channel for the same situation."""

        return route_trader_cognition(situation)


def build_trader_cognitive_opinion(
    *,
    trader_code: DemoTradingTraderCode,
    version: DemoTradingTraderVersion,
    config_fingerprint: DemoTradingConfigFingerprint,
    methodology_id: DemoTradingMethodologyId,
    methodology_version: DemoTradingMethodologyVersion,
    methodology_fingerprint: DemoTradingMethodologyFingerprint,
    deterministic_output_fingerprint: DemoTradingConfigFingerprint,
    supplied_evidence_refs: tuple[DemoTradingEvidenceRef, ...],
    evidence_refs: tuple[DemoTradingEvidenceRef, ...],
    situation: TraderCognitiveSituation,
    provenance: TraderCognitiveProvenance,
    thesis: str,
    invalidation: str,
    limitations: tuple[str, ...],
    voiced_at: datetime,
) -> TraderCognitiveOpinion:
    """Build an admitted opinion whose receipt matches the governed route.

    The receipt is derived from ``route_trader_cognition(situation)`` at
    ``voiced_at``, so provider model/effort can never diverge from the governed
    route, and the evidence subset is validated against the deterministic state.
    """

    route = route_trader_cognition(situation)
    receipt = build_trader_cognitive_receipt(route=route, issued_at=voiced_at)
    fingerprint = compute_trader_cognitive_opinion_fingerprint(
        trader_code=trader_code,
        version=version,
        config_fingerprint=config_fingerprint,
        methodology_id=methodology_id,
        methodology_version=methodology_version,
        methodology_fingerprint=methodology_fingerprint,
        deterministic_output_fingerprint=deterministic_output_fingerprint,
        supplied_evidence_refs=supplied_evidence_refs,
        evidence_refs=evidence_refs,
        situation=situation,
        receipt=receipt,
        provenance=provenance,
        thesis=thesis,
        invalidation=invalidation,
        limitations=limitations,
        voiced_at=voiced_at,
    )
    return TraderCognitiveOpinion(
        trader_code=trader_code,
        version=version,
        config_fingerprint=config_fingerprint,
        methodology_id=methodology_id,
        methodology_version=methodology_version,
        methodology_fingerprint=methodology_fingerprint,
        deterministic_output_fingerprint=deterministic_output_fingerprint,
        supplied_evidence_refs=supplied_evidence_refs,
        evidence_refs=evidence_refs,
        situation=situation,
        receipt=receipt,
        provenance=provenance,
        thesis=thesis,
        invalidation=invalidation,
        limitations=limitations,
        voiced_at=voiced_at,
        opinion_fingerprint=fingerprint,
    )
