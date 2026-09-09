"""CIBO five-Trader research laboratory.

This module closes the scientific seam between CIBO's existing capability/team
surfaces and the exact deterministic Trader evaluators.  It intentionally owns
no broker, order, Risk, promotion, DEMO or Production authority.

The decision-time boundary is strict: a versioned market state and a canonical
team are frozen before five isolated outputs are evaluated.  Future outcomes
are accepted only by the separate post-decision evaluator in
``trader_team_lab_research``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256
from re import fullmatch
from typing import Protocol
from uuid import UUID

from qore.infrastructure.cibo.contracts import CiboFunctionalEvidence
from qore.infrastructure.cibo.trader_suitability import (
    CiboSuitabilityAssessment,
    assess_market_trader_suitability,
)
from qore.infrastructure.cibo_trader_capability_profile import (
    CiboEvidenceFreshnessState,
    CiboRegimeKind,
    CiboTraderCapabilityProfile,
)
from qore.infrastructure.market_data import Instrument
from qore.infrastructure.traders.contracts import (
    DemoTradingDecision,
    DemoTradingEvidenceRef,
    DemoTradingMethodologyIdentity,
    DemoTradingOutput,
    DemoTradingTraderIdentity,
)
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success

_CODE_RE = r"[a-z][a-z0-9._-]*"
_FINGERPRINT_RE = r"[0-9a-f]{64}"
_FIRST_COHORT = ("vt-01", "vt-08", "vt-09", "vt-17", "vt-31")


class TraderTeamLabError(InfrastructureError):
    """Base error for the non-executing CIBO Trader-Team Lab."""

    __slots__ = ()


class TraderTeamLabValidationError(TraderTeamLabError):
    __slots__ = ()


class TraderTeamLabBlockedError(TraderTeamLabError):
    __slots__ = ()


def _aware(value: datetime, field: str) -> datetime:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise TraderTeamLabValidationError(f"{field} must be timezone-aware datetime")
    return value


def _code(value: str, field: str) -> str:
    if type(value) is not str or fullmatch(_CODE_RE, value) is None:
        raise TraderTeamLabValidationError(f"{field} must use canonical lowercase syntax")
    return value


def _codes(values: tuple[str, ...], field: str) -> tuple[str, ...]:
    if type(values) is not tuple or any(type(value) is not str for value in values):
        raise TraderTeamLabValidationError(f"{field} must be an immutable str tuple")
    normalized = tuple(_code(value, field) for value in values)
    if len(set(normalized)) != len(normalized):
        raise TraderTeamLabValidationError(f"{field} must not contain duplicates")
    return tuple(sorted(normalized))


def _decimal(value: Decimal, field: str) -> Decimal:
    if type(value) is not Decimal or not value.is_finite():
        raise TraderTeamLabValidationError(f"{field} must be finite Decimal")
    return value


def _utc(value: datetime) -> str:
    return _aware(value, "timestamp").astimezone(UTC).isoformat(timespec="microseconds")


def _canonical(value: object) -> bytes:
    def default(item: object) -> str:
        if type(item) is Decimal:
            normalized = Decimal(0) if item == 0 else item.normalize()
            return format(normalized, "f")
        if type(item) is datetime:
            return _utc(item)
        if type(item) is UUID:
            return str(item)
        raise TypeError(f"unsupported canonical value: {type(item).__qualname__}")

    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
        default=default,
    ).encode()


def _fingerprint(value: object) -> str:
    return sha256(_canonical(value)).hexdigest()


class MarketKnowledgeState(StrEnum):
    OBSERVED = "observed"
    UNKNOWN = "unknown"
    INSUFFICIENT_EVIDENCE = "insufficient-evidence"
    CONTRADICTORY = "contradictory"


@dataclass(frozen=True, slots=True)
class CiboMarketDimension:
    """One explicit market dimension; unknown is never represented as neutral."""

    name: str
    state: MarketKnowledgeState
    value: str | Decimal | None
    evidence_refs: tuple[DemoTradingEvidenceRef, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _code(self.name, "market dimension name"))
        if type(self.state) is not MarketKnowledgeState:
            raise TraderTeamLabValidationError("market dimension state must be exact")
        if self.state is MarketKnowledgeState.OBSERVED:
            if type(self.value) not in (str, Decimal):
                raise TraderTeamLabValidationError("observed market dimension requires a value")
            if type(self.value) is str and not self.value.strip():
                raise TraderTeamLabValidationError("observed market value must not be blank")
            if type(self.value) is Decimal:
                _decimal(self.value, "market dimension value")
            if not self.evidence_refs:
                raise TraderTeamLabValidationError("observed market dimension requires evidence")
        elif self.value is not None:
            raise TraderTeamLabValidationError("unobserved market dimension must not carry value")
        if type(self.evidence_refs) is not tuple or any(
            type(item) is not DemoTradingEvidenceRef for item in self.evidence_refs
        ):
            raise TraderTeamLabValidationError("dimension evidence must be exact refs")
        if len(set(self.evidence_refs)) != len(self.evidence_refs):
            raise TraderTeamLabValidationError("dimension evidence must not contain duplicates")
        object.__setattr__(
            self, "evidence_refs", tuple(sorted(self.evidence_refs, key=lambda item: item.value))
        )

    def logical_values(self) -> tuple[object, ...]:
        value = self.value
        if type(value) is Decimal:
            value = format(Decimal(0) if value == 0 else value.normalize(), "f")
        return self.name, self.state.value, value, tuple(ref.value for ref in self.evidence_refs)


@dataclass(frozen=True, slots=True)
class CiboMarketState:
    """Versioned, evidence-bound information available to every Trader at time t."""

    schema_version: str
    instrument: Instrument
    market_code: str
    observed_at: datetime
    information_cutoff: datetime
    timeframe_codes: tuple[str, ...]
    session_code: str
    dimensions: tuple[CiboMarketDimension, ...]
    regime_hypothesis: CiboRegimeKind
    regime_uncertainty: Decimal
    contradictory_evidence: tuple[DemoTradingEvidenceRef, ...]
    unsupported_dimensions: tuple[str, ...]
    provenance: tuple[DemoTradingEvidenceRef, ...]
    fingerprint: str

    def __post_init__(self) -> None:
        _code(self.schema_version, "market-state schema version")
        if type(self.instrument) is not Instrument:
            raise TraderTeamLabValidationError("market state requires canonical Instrument")
        self.instrument.__post_init__()
        _code(self.market_code, "market code")
        _aware(self.observed_at, "market observed_at")
        _aware(self.information_cutoff, "market information_cutoff")
        if self.information_cutoff > self.observed_at:
            raise TraderTeamLabValidationError("information cutoff cannot be in the future")
        object.__setattr__(self, "timeframe_codes", _codes(self.timeframe_codes, "timeframes"))
        _code(self.session_code, "session code")
        if type(self.dimensions) is not tuple or any(
            type(item) is not CiboMarketDimension for item in self.dimensions
        ):
            raise TraderTeamLabValidationError("dimensions must be exact market dimensions")
        for item in self.dimensions:
            item.__post_init__()
        names = tuple(item.name for item in self.dimensions)
        if len(set(names)) != len(names):
            raise TraderTeamLabValidationError("market dimensions must be unique")
        object.__setattr__(
            self, "dimensions", tuple(sorted(self.dimensions, key=lambda item: item.name))
        )
        if type(self.regime_hypothesis) is not CiboRegimeKind:
            raise TraderTeamLabValidationError("regime hypothesis must be exact")
        _decimal(self.regime_uncertainty, "regime uncertainty")
        if not Decimal(0) <= self.regime_uncertainty <= Decimal(1):
            raise TraderTeamLabValidationError("regime uncertainty must be in [0, 1]")
        for field, values in (
            ("contradictory evidence", self.contradictory_evidence),
            ("provenance", self.provenance),
        ):
            if type(values) is not tuple or any(
                type(item) is not DemoTradingEvidenceRef for item in values
            ):
                raise TraderTeamLabValidationError(f"{field} must be exact evidence refs")
            if len(set(values)) != len(values):
                raise TraderTeamLabValidationError(f"{field} must not contain duplicates")
        object.__setattr__(
            self,
            "contradictory_evidence",
            tuple(sorted(self.contradictory_evidence, key=lambda x: x.value)),
        )
        object.__setattr__(
            self, "provenance", tuple(sorted(self.provenance, key=lambda x: x.value))
        )
        if not self.provenance:
            raise TraderTeamLabValidationError("market state requires provenance")
        object.__setattr__(
            self,
            "unsupported_dimensions",
            _codes(self.unsupported_dimensions, "unsupported dimensions"),
        )
        if set(self.unsupported_dimensions) & set(names):
            raise TraderTeamLabValidationError("a dimension cannot be both present and unsupported")
        if fullmatch(_FINGERPRINT_RE, self.fingerprint) is None:
            raise TraderTeamLabValidationError("market-state fingerprint must be lowercase SHA-256")
        if self.fingerprint != self.compute_fingerprint():
            raise TraderTeamLabValidationError("market-state fingerprint mismatch")

    def material(self) -> tuple[object, ...]:
        return (
            self.schema_version,
            self.instrument.symbol,
            self.market_code,
            _utc(self.observed_at),
            _utc(self.information_cutoff),
            self.timeframe_codes,
            self.session_code,
            tuple(item.logical_values() for item in self.dimensions),
            self.regime_hypothesis.value,
            format(self.regime_uncertainty.normalize(), "f"),
            tuple(item.value for item in self.contradictory_evidence),
            self.unsupported_dimensions,
            tuple(item.value for item in self.provenance),
        )

    def compute_fingerprint(self) -> str:
        return _fingerprint(("qore.cibo.market-state.v1", self.material()))


def build_cibo_market_state(**values: object) -> CiboMarketState:
    """Build a market state and derive, never accept, its logical fingerprint."""

    values["fingerprint"] = "0" * 64
    provisional = CiboMarketState.__new__(CiboMarketState)
    for field, value in values.items():
        object.__setattr__(provisional, field, value)
    # Normalize everything before deriving the fingerprint.
    object.__setattr__(
        provisional,
        "fingerprint",
        _fingerprint(("qore.cibo.market-state.v1", _market_material(provisional))),
    )
    provisional.__post_init__()
    return provisional


def _market_material(state: CiboMarketState) -> tuple[object, ...]:
    # Construction-only projection independent of the fingerprint slot.
    return (
        state.schema_version,
        state.instrument.symbol,
        state.market_code,
        _utc(state.observed_at),
        _utc(state.information_cutoff),
        tuple(sorted(state.timeframe_codes)),
        state.session_code,
        tuple(
            sorted(
                (item.logical_values() for item in state.dimensions), key=lambda item: str(item[0])
            )
        ),
        state.regime_hypothesis.value,
        format(state.regime_uncertainty.normalize(), "f"),
        tuple(sorted(item.value for item in state.contradictory_evidence)),
        tuple(sorted(state.unsupported_dimensions)),
        tuple(sorted(item.value for item in state.provenance)),
    )


class OperatingEnvelopeDisposition(StrEnum):
    FAVORABLE = "favorable"
    ADVERSE = "adverse"
    UNCERTAIN = "uncertain"
    ABSTENTION = "abstention"
    INSUFFICIENT_EVIDENCE = "insufficient-evidence"


class HistoricalEvidenceState(StrEnum):
    CERTIFIED = "certified"
    STALE = "stale"
    CONTRADICTORY = "contradictory"
    INSUFFICIENT_SAMPLE = "insufficient-sample"


@dataclass(frozen=True, slots=True)
class TraderOperatingEnvelope:
    market_code: str
    regime_code: str
    disposition: OperatingEnvelopeDisposition
    expected_return: Decimal | None
    sample_size: int
    evidence_refs: tuple[DemoTradingEvidenceRef, ...]

    def __post_init__(self) -> None:
        _code(self.market_code, "envelope market")
        _code(self.regime_code, "envelope regime")
        if type(self.disposition) is not OperatingEnvelopeDisposition:
            raise TraderTeamLabValidationError("envelope disposition must be exact")
        if self.expected_return is not None:
            _decimal(self.expected_return, "envelope expected return")
        if type(self.sample_size) is not int or self.sample_size < 0:
            raise TraderTeamLabValidationError("envelope sample size must be non-negative int")
        if type(self.evidence_refs) is not tuple or any(
            type(item) is not DemoTradingEvidenceRef for item in self.evidence_refs
        ):
            raise TraderTeamLabValidationError("envelope evidence must be exact refs")
        if self.disposition is OperatingEnvelopeDisposition.INSUFFICIENT_EVIDENCE:
            if self.expected_return is not None:
                raise TraderTeamLabValidationError("insufficient envelope cannot estimate return")
        elif not self.evidence_refs:
            raise TraderTeamLabValidationError("evidenced envelope requires provenance")

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.market_code,
            self.regime_code,
            self.disposition.value,
            None if self.expected_return is None else format(self.expected_return.normalize(), "f"),
            self.sample_size,
            tuple(sorted(item.value for item in self.evidence_refs)),
        )


@dataclass(frozen=True, slots=True)
class TraderHistoricalIntelligenceProjection:
    """Consume-only projection expected from the external governed registry."""

    trader_identity: DemoTradingTraderIdentity
    methodology_identity: DemoTradingMethodologyIdentity
    state: HistoricalEvidenceState
    as_of: datetime
    sample_size: int
    envelopes: tuple[TraderOperatingEnvelope, ...]
    limitations: tuple[str, ...]
    provenance: tuple[DemoTradingEvidenceRef, ...]

    def __post_init__(self) -> None:
        if type(self.trader_identity) is not DemoTradingTraderIdentity:
            raise TraderTeamLabValidationError("history requires exact Trader identity")
        self.trader_identity.__post_init__()
        if type(self.methodology_identity) is not DemoTradingMethodologyIdentity:
            raise TraderTeamLabValidationError("history requires exact methodology identity")
        self.methodology_identity.__post_init__()
        if type(self.state) is not HistoricalEvidenceState:
            raise TraderTeamLabValidationError("history state must be exact")
        _aware(self.as_of, "history as_of")
        if type(self.sample_size) is not int or self.sample_size < 0:
            raise TraderTeamLabValidationError("history sample size must be non-negative int")
        if type(self.envelopes) is not tuple or any(
            type(item) is not TraderOperatingEnvelope for item in self.envelopes
        ):
            raise TraderTeamLabValidationError("history envelopes must be exact")
        for item in self.envelopes:
            item.__post_init__()
        keys = tuple((item.market_code, item.regime_code) for item in self.envelopes)
        if len(set(keys)) != len(keys):
            raise TraderTeamLabValidationError("history envelopes must be unique")
        object.__setattr__(
            self,
            "envelopes",
            tuple(sorted(self.envelopes, key=lambda x: (x.market_code, x.regime_code))),
        )
        object.__setattr__(self, "limitations", _codes(self.limitations, "history limitations"))
        if type(self.provenance) is not tuple or any(
            type(item) is not DemoTradingEvidenceRef for item in self.provenance
        ):
            raise TraderTeamLabValidationError("history provenance must be exact refs")
        if len(set(self.provenance)) != len(self.provenance):
            raise TraderTeamLabValidationError("history provenance must not contain duplicates")
        object.__setattr__(
            self, "provenance", tuple(sorted(self.provenance, key=lambda x: x.value))
        )
        if self.state is HistoricalEvidenceState.CERTIFIED and (
            not self.provenance or self.sample_size == 0
        ):
            raise TraderTeamLabValidationError("certified history requires samples and provenance")

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.trader_identity.logical_values(),
            self.methodology_identity.logical_values(),
            self.state.value,
            _utc(self.as_of),
            self.sample_size,
            tuple(item.logical_values() for item in self.envelopes),
            self.limitations,
            tuple(item.value for item in self.provenance),
        )


class TraderHistoricalIntelligencePort(Protocol):
    """Adapter seam for the not-yet-integrated authoritative registry."""

    def project(
        self,
        trader_identity: DemoTradingTraderIdentity,
        methodology_identity: DemoTradingMethodologyIdentity,
        *,
        as_of: datetime,
    ) -> Result[TraderHistoricalIntelligenceProjection, TraderTeamLabError]: ...


@dataclass(frozen=True, slots=True)
class CiboLabTraderMember:
    capability_profile: CiboTraderCapabilityProfile
    trader_identity: DemoTradingTraderIdentity
    methodology_identity: DemoTradingMethodologyIdentity
    historical_intelligence: TraderHistoricalIntelligenceProjection

    def __post_init__(self) -> None:
        if not isinstance(self.capability_profile, CiboTraderCapabilityProfile):
            raise TraderTeamLabValidationError("member requires capability profile")
        self.capability_profile.__post_init__()
        if type(self.trader_identity) is not DemoTradingTraderIdentity:
            raise TraderTeamLabValidationError("member requires exact Trader identity")
        self.trader_identity.__post_init__()
        if type(self.methodology_identity) is not DemoTradingMethodologyIdentity:
            raise TraderTeamLabValidationError("member requires exact methodology identity")
        self.methodology_identity.__post_init__()
        self.historical_intelligence.__post_init__()
        history = self.historical_intelligence
        if (
            history.trader_identity != self.trader_identity
            or history.methodology_identity != self.methodology_identity
        ):
            raise TraderTeamLabValidationError("historical intelligence identity laundering")
        if (
            self.capability_profile.config_fingerprint.value
            != self.trader_identity.config_fingerprint.value
        ):
            raise TraderTeamLabValidationError(
                "capability profile config does not match Trader config"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.capability_profile.logical_values(),
            self.trader_identity.logical_values(),
            self.methodology_identity.logical_values(),
            self.historical_intelligence.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class CiboLabTraderTeam:
    members: tuple[CiboLabTraderMember, ...]
    formed_at: datetime
    fingerprint: str
    research_only: bool = True

    def __post_init__(self) -> None:
        if (
            type(self.members) is not tuple
            or not self.members
            or any(type(item) is not CiboLabTraderMember for item in self.members)
        ):
            raise TraderTeamLabValidationError("team members must be exact and non-empty")
        for item in self.members:
            item.__post_init__()
        codes = tuple(item.trader_identity.trader_code.value for item in self.members)
        if len(set(codes)) != len(codes):
            raise TraderTeamLabValidationError("duplicate Trader identity")
        if tuple(sorted(codes)) != codes:
            raise TraderTeamLabValidationError("team must use canonical Trader ordering")
        _aware(self.formed_at, "team formed_at")
        if self.research_only is not True:
            raise TraderTeamLabValidationError("Trader-Team Lab is research-only")
        if (
            fullmatch(_FINGERPRINT_RE, self.fingerprint) is None
            or self.fingerprint != self.compute_fingerprint()
        ):
            raise TraderTeamLabValidationError("team fingerprint mismatch")

    def compute_fingerprint(self) -> str:
        return _fingerprint(
            (
                "qore.cibo.trader-team.v1",
                tuple(item.logical_values() for item in self.members),
                _utc(self.formed_at),
            )
        )


def build_cibo_lab_trader_team(
    profiles: tuple[CiboTraderCapabilityProfile, ...],
    identities: tuple[tuple[DemoTradingTraderIdentity, DemoTradingMethodologyIdentity], ...],
    *,
    history: TraderHistoricalIntelligencePort,
    formed_at: datetime,
    require_certified_history: bool = True,
) -> Result[CiboLabTraderTeam, TraderTeamLabError]:
    """Consume external history and form a canonical exact-version team."""

    try:
        if (
            type(profiles) is not tuple
            or type(identities) is not tuple
            or len(profiles) != len(identities)
        ):
            raise TraderTeamLabValidationError(
                "profiles and identities must have equal tuple length"
            )
        if len(profiles) != 5:
            raise TraderTeamLabValidationError("first CIBO cohort requires exactly five Traders")
        profile_by_config = {item.config_fingerprint.value: item for item in profiles}
        if len(profile_by_config) != len(profiles):
            raise TraderTeamLabValidationError("duplicate or same-config capability profiles")
        members: list[CiboLabTraderMember] = []
        for trader_identity, methodology_identity in sorted(
            identities, key=lambda pair: pair[0].trader_code.value
        ):
            profile = profile_by_config.get(trader_identity.config_fingerprint.value)
            if profile is None:
                raise TraderTeamLabValidationError("Trader config has no exact capability profile")
            projected = history.project(trader_identity, methodology_identity, as_of=formed_at)
            if isinstance(projected, Failure):
                return projected
            projection = projected.value
            if projection.as_of > formed_at:
                raise TraderTeamLabBlockedError("future historical intelligence is forbidden")
            if (
                require_certified_history
                and projection.state is not HistoricalEvidenceState.CERTIFIED
            ):
                raise TraderTeamLabBlockedError("certified historical intelligence is unavailable")
            if (
                require_certified_history
                and profile.freshness.state is not CiboEvidenceFreshnessState.CURRENT
            ):
                raise TraderTeamLabBlockedError("capability profile history is not current")
            members.append(
                CiboLabTraderMember(profile, trader_identity, methodology_identity, projection)
            )
        if tuple(member.trader_identity.trader_code.value for member in members) != _FIRST_COHORT:
            raise TraderTeamLabValidationError("team must contain exact VT-01/08/09/17/31 cohort")
        team = object.__new__(CiboLabTraderTeam)
        object.__setattr__(team, "members", tuple(members))
        object.__setattr__(team, "formed_at", formed_at)
        object.__setattr__(team, "research_only", True)
        object.__setattr__(team, "fingerprint", "0" * 64)
        object.__setattr__(team, "fingerprint", team.compute_fingerprint())
        team.__post_init__()
        return Success(team)
    except TraderTeamLabError as error:
        return Failure(error)


class ShadowTraderEvaluator(Protocol):
    """One isolated exact Trader evaluator; it cannot see peer outputs."""

    @property
    def trader_identity(self) -> DemoTradingTraderIdentity: ...

    @property
    def methodology_identity(self) -> DemoTradingMethodologyIdentity: ...

    def evaluate(
        self, market_state: CiboMarketState
    ) -> Result[DemoTradingOutput, TraderTeamLabError]: ...


class CiboMarketEvidenceAuthorityPort(Protocol):
    """External authority seam proving a market state is decision-time valid."""

    def verify(
        self,
        market_state: CiboMarketState,
        evidence: CiboFunctionalEvidence,
    ) -> Result[None, TraderTeamLabError]: ...


@dataclass(frozen=True, slots=True)
class CiboFiveTraderShadowEvaluation:
    market_state: CiboMarketState
    team: CiboLabTraderTeam
    outputs: tuple[DemoTradingOutput, ...]
    evaluated_at: datetime
    fingerprint: str
    research_only: bool = True

    def __post_init__(self) -> None:
        self.market_state.__post_init__()
        self.team.__post_init__()
        if (
            type(self.outputs) is not tuple
            or len(self.outputs) != 5
            or any(type(item) is not DemoTradingOutput for item in self.outputs)
        ):
            raise TraderTeamLabValidationError("shadow evaluation requires five exact outputs")
        for item in self.outputs:
            item.__post_init__()
        codes = tuple(item.trader_code.value for item in self.outputs)
        if codes != _FIRST_COHORT:
            raise TraderTeamLabValidationError("shadow outputs must retain canonical cohort order")
        member_by_code = {
            item.trader_identity.trader_code.value: item for item in self.team.members
        }
        allowed_refs = {item.value for item in self.market_state.provenance}
        for output in self.outputs:
            member = member_by_code[output.trader_code.value]
            if (
                output.version != member.trader_identity.version
                or output.config_fingerprint != member.trader_identity.config_fingerprint
                or output.methodology_id != member.methodology_identity.methodology_id
                or output.methodology_version != member.methodology_identity.version
                or output.methodology_fingerprint != member.methodology_identity.fingerprint
            ):
                raise TraderTeamLabValidationError("Trader output consumed under wrong identity")
            if output.evaluated_at != self.market_state.information_cutoff:
                raise TraderTeamLabValidationError("Trader output cutoff mismatch")
            if not {item.value for item in output.evidence_refs}.issubset(allowed_refs):
                raise TraderTeamLabValidationError("Trader output used unavailable information")
        _aware(self.evaluated_at, "shadow evaluated_at")
        if self.evaluated_at != self.market_state.information_cutoff:
            raise TraderTeamLabValidationError("shadow evaluation must occur at information cutoff")
        if self.research_only is not True:
            raise TraderTeamLabValidationError("shadow evaluation cannot carry execution authority")
        if (
            fullmatch(_FINGERPRINT_RE, self.fingerprint) is None
            or self.fingerprint != self.compute_fingerprint()
        ):
            raise TraderTeamLabValidationError("shadow fingerprint mismatch")

    def compute_fingerprint(self) -> str:
        return _fingerprint(
            (
                "qore.cibo.shadow.v1",
                self.market_state.fingerprint,
                self.team.fingerprint,
                tuple(item.logical_values() for item in self.outputs),
                _utc(self.evaluated_at),
            )
        )


def evaluate_five_trader_shadow(
    market_state: CiboMarketState,
    team: CiboLabTraderTeam,
    evaluators: tuple[ShadowTraderEvaluator, ...],
) -> Result[CiboFiveTraderShadowEvaluation, TraderTeamLabError]:
    """Evaluate exactly five isolated Traders against the same frozen state."""

    try:
        market_state.__post_init__()
        team.__post_init__()
        if type(evaluators) is not tuple or len(evaluators) != 5:
            raise TraderTeamLabValidationError("shadow evaluation requires five evaluators")
        evaluator_by_code = {item.trader_identity.trader_code.value: item for item in evaluators}
        if tuple(sorted(evaluator_by_code)) != _FIRST_COHORT or len(evaluator_by_code) != 5:
            raise TraderTeamLabValidationError("evaluators must cover exact first cohort once")
        outputs: list[DemoTradingOutput] = []
        for member in team.members:
            evaluator = evaluator_by_code[member.trader_identity.trader_code.value]
            if (
                evaluator.trader_identity != member.trader_identity
                or evaluator.methodology_identity != member.methodology_identity
            ):
                raise TraderTeamLabValidationError("evaluator identity does not match team member")
            result = evaluator.evaluate(market_state)
            if isinstance(result, Failure):
                return result
            outputs.append(result.value)
        shadow = object.__new__(CiboFiveTraderShadowEvaluation)
        object.__setattr__(shadow, "market_state", market_state)
        object.__setattr__(shadow, "team", team)
        object.__setattr__(shadow, "outputs", tuple(outputs))
        object.__setattr__(shadow, "evaluated_at", market_state.information_cutoff)
        object.__setattr__(shadow, "research_only", True)
        object.__setattr__(shadow, "fingerprint", "0" * 64)
        object.__setattr__(shadow, "fingerprint", shadow.compute_fingerprint())
        shadow.__post_init__()
        return Success(shadow)
    except TraderTeamLabError as error:
        return Failure(error)


@dataclass(frozen=True, slots=True)
class CiboMetaSelectionPolicy:
    version: str
    min_history_sample: int
    max_regime_uncertainty: Decimal
    require_setup: bool = True

    def __post_init__(self) -> None:
        _code(self.version, "policy version")
        if type(self.min_history_sample) is not int or self.min_history_sample <= 0:
            raise TraderTeamLabValidationError("minimum history sample must be positive int")
        _decimal(self.max_regime_uncertainty, "maximum regime uncertainty")
        if not Decimal(0) <= self.max_regime_uncertainty <= Decimal(1):
            raise TraderTeamLabValidationError("maximum uncertainty must be in [0, 1]")
        if type(self.require_setup) is not bool:
            raise TraderTeamLabValidationError("require_setup must be bool")

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.version,
            self.min_history_sample,
            format(self.max_regime_uncertainty.normalize(), "f"),
            self.require_setup,
        )


@dataclass(frozen=True, slots=True)
class CiboSelectionAlternative:
    trader_identity: DemoTradingTraderIdentity
    suitability: OperatingEnvelopeDisposition
    eligible: bool
    score: Decimal | None
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        self.trader_identity.__post_init__()
        if type(self.suitability) is not OperatingEnvelopeDisposition:
            raise TraderTeamLabValidationError("alternative suitability must be exact")
        if type(self.eligible) is not bool:
            raise TraderTeamLabValidationError("alternative eligible must be bool")
        if self.score is not None:
            _decimal(self.score, "alternative score")
        if (self.suitability is OperatingEnvelopeDisposition.FAVORABLE) != (self.score is not None):
            raise TraderTeamLabValidationError(
                "favorable alternative and evidence score must agree"
            )
        if self.eligible and self.score is None:
            raise TraderTeamLabValidationError("eligible alternative requires a score")
        object.__setattr__(self, "reasons", _codes(self.reasons, "alternative reasons"))

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.trader_identity.logical_values(),
            self.suitability.value,
            self.eligible,
            None if self.score is None else format(self.score.normalize(), "f"),
            self.reasons,
        )


@dataclass(frozen=True, slots=True)
class CiboMetaSelectionDecision:
    decision_id: UUID
    policy: CiboMetaSelectionPolicy
    market_state_fingerprint: str
    team_fingerprint: str
    shadow_fingerprint: str
    selected: DemoTradingTraderIdentity | None
    selected_output_fingerprint: str | None
    reasons: tuple[str, ...]
    evidence_refs: tuple[DemoTradingEvidenceRef, ...]
    suitability_assessments: tuple[CiboSuitabilityAssessment, ...]
    uncertainty: Decimal
    alternatives: tuple[CiboSelectionAlternative, ...]
    conflicting_evidence: tuple[DemoTradingEvidenceRef, ...]
    decided_at: datetime
    information_cutoff: datetime
    provenance: tuple[DemoTradingEvidenceRef, ...]
    fingerprint: str
    research_only: bool = True

    def __post_init__(self) -> None:
        if type(self.decision_id) is not UUID:
            raise TraderTeamLabValidationError("decision id must be UUID")
        self.policy.__post_init__()
        for field, value in (
            ("market state", self.market_state_fingerprint),
            ("team", self.team_fingerprint),
            ("shadow", self.shadow_fingerprint),
        ):
            if fullmatch(_FINGERPRINT_RE, value) is None:
                raise TraderTeamLabValidationError(f"{field} fingerprint must be SHA-256")
        if self.selected is not None:
            self.selected.__post_init__()
            if (
                self.selected_output_fingerprint is None
                or fullmatch(_FINGERPRINT_RE, self.selected_output_fingerprint) is None
            ):
                raise TraderTeamLabValidationError(
                    "selected Trader requires exact output fingerprint"
                )
        elif self.selected_output_fingerprint is not None:
            raise TraderTeamLabValidationError("NONE must not carry selected output")
        object.__setattr__(self, "reasons", _codes(self.reasons, "selection reasons"))
        for name, values in (
            ("evidence", self.evidence_refs),
            ("conflicting evidence", self.conflicting_evidence),
            ("provenance", self.provenance),
        ):
            if type(values) is not tuple or any(
                type(item) is not DemoTradingEvidenceRef for item in values
            ):
                raise TraderTeamLabValidationError(f"{name} must be exact evidence refs")
            if (
                len(set(values)) != len(values)
                or tuple(sorted(values, key=lambda item: item.value)) != values
            ):
                raise TraderTeamLabValidationError(f"{name} must be unique and canonically ordered")
        if (
            type(self.suitability_assessments) is not tuple
            or len(self.suitability_assessments) != 5
        ):
            raise TraderTeamLabValidationError("decision requires five suitability assessments")
        for assessment_item in self.suitability_assessments:
            assessment_item.__post_init__()
        if type(self.alternatives) is not tuple or len(self.alternatives) != 5:
            raise TraderTeamLabValidationError("decision requires five alternatives")
        for alternative_item in self.alternatives:
            alternative_item.__post_init__()
        alternative_codes = tuple(
            item.trader_identity.trader_code.value for item in self.alternatives
        )
        if alternative_codes != _FIRST_COHORT:
            raise TraderTeamLabValidationError(
                "decision alternatives must be exact canonical first cohort"
            )
        if tuple(item.config_fingerprint.value for item in self.suitability_assessments) != tuple(
            item.trader_identity.config_fingerprint.value for item in self.alternatives
        ):
            raise TraderTeamLabValidationError(
                "suitability assessments must match alternative configs"
            )
        ranked = [item for item in self.alternatives if item.eligible]
        ranked.sort(key=_alternative_rank_key)
        expected_selected = ranked[0].trader_identity if ranked else None
        if self.selected != expected_selected:
            raise TraderTeamLabValidationError(
                "selected Trader must be canonical best eligible alternative"
            )
        expected_reasons = (
            ("no-evidence-qualified-specialist",)
            if self.selected is None
            else ("highest-evidence-backed-suitability",)
        )
        if self.reasons != expected_reasons:
            raise TraderTeamLabValidationError("selection reasons must match decision")
        _decimal(self.uncertainty, "selection uncertainty")
        if not Decimal(0) <= self.uncertainty <= Decimal(1):
            raise TraderTeamLabValidationError("selection uncertainty must be in [0, 1]")
        _aware(self.decided_at, "decision time")
        _aware(self.information_cutoff, "decision information cutoff")
        if self.information_cutoff > self.decided_at:
            raise TraderTeamLabValidationError("decision cannot precede information cutoff")
        if self.research_only is not True:
            raise TraderTeamLabValidationError("selection is not execution authority")
        if (
            fullmatch(_FINGERPRINT_RE, self.fingerprint) is None
            or self.fingerprint != self.compute_fingerprint()
        ):
            raise TraderTeamLabValidationError("selection decision fingerprint mismatch")

    def compute_fingerprint(self) -> str:
        return _fingerprint(
            (
                "qore.cibo.meta-selection.v1",
                str(self.decision_id),
                self.policy.logical_values(),
                self.market_state_fingerprint,
                self.team_fingerprint,
                self.shadow_fingerprint,
                None if self.selected is None else self.selected.logical_values(),
                self.selected_output_fingerprint,
                self.reasons,
                tuple(item.value for item in self.evidence_refs),
                tuple(item.logical_values() for item in self.suitability_assessments),
                format(self.uncertainty.normalize(), "f"),
                tuple(item.logical_values() for item in self.alternatives),
                tuple(item.value for item in self.conflicting_evidence),
                _utc(self.decided_at),
                _utc(self.information_cutoff),
                tuple(item.value for item in self.provenance),
                self.research_only,
            )
        )


def _history_score(member: CiboLabTraderMember, state: CiboMarketState) -> Decimal | None:
    matches = [
        item
        for item in member.historical_intelligence.envelopes
        if item.market_code == state.market_code
        and item.regime_code == state.regime_hypothesis.value
    ]
    if len(matches) != 1:
        return None
    envelope = matches[0]
    if envelope.disposition is not OperatingEnvelopeDisposition.FAVORABLE:
        return None
    return envelope.expected_return


def _alternative_rank_key(item: CiboSelectionAlternative) -> tuple[Decimal, str]:
    if item.score is None:
        raise TraderTeamLabValidationError("ranked alternative requires a score")
    return -item.score, item.trader_identity.trader_code.value


def select_cibo_specialist(
    shadow: CiboFiveTraderShadowEvaluation,
    *,
    policy: CiboMetaSelectionPolicy,
    market_evidence: CiboFunctionalEvidence,
    market_authority: CiboMarketEvidenceAuthorityPort,
    decision_id: UUID,
    decided_at: datetime,
) -> Result[CiboMetaSelectionDecision, TraderTeamLabError]:
    """Select one exact specialist or NONE using decision-time evidence only."""

    try:
        shadow.__post_init__()
        policy.__post_init__()
        market_evidence.__post_init__()
        _aware(decided_at, "decided_at")
        state = shadow.market_state
        if (
            market_evidence.as_of > state.information_cutoff
            or decided_at < state.information_cutoff
        ):
            raise TraderTeamLabBlockedError("future evidence cannot enter CIBO selection")
        verified = market_authority.verify(state, market_evidence)
        if isinstance(verified, Failure):
            return verified
        output_by_code = {item.trader_code.value: item for item in shadow.outputs}
        assessments: list[CiboSuitabilityAssessment] = []
        alternatives: list[CiboSelectionAlternative] = []
        for member in shadow.team.members:
            assessed = assess_market_trader_suitability(
                member.capability_profile,
                current_regime=state.regime_hypothesis,
                market_evidence=market_evidence,
                assessed_at=state.information_cutoff,
                unsupported_dimensions=state.unsupported_dimensions,
                uncertainty_codes=("regime-uncertain",) if state.regime_uncertainty else (),
            )
            if isinstance(assessed, Failure):
                raise TraderTeamLabBlockedError(str(assessed.error))
            assessment = assessed.value
            assessments.append(assessment)
            output = output_by_code[member.trader_identity.trader_code.value]
            reasons: list[str] = []
            score = _history_score(member, state)
            if member.historical_intelligence.sample_size < policy.min_history_sample:
                reasons.append("history-sample-insufficient")
            if state.regime_uncertainty > policy.max_regime_uncertainty:
                reasons.append("regime-uncertainty-above-policy")
            if policy.require_setup and output.decision is not DemoTradingDecision.SETUP:
                reasons.append("trader-abstained")
            if score is None:
                reasons.append("no-favorable-operating-envelope")
            eligible = not reasons
            envelope_disposition = (
                OperatingEnvelopeDisposition.FAVORABLE
                if score is not None
                else OperatingEnvelopeDisposition.INSUFFICIENT_EVIDENCE
            )
            alternatives.append(
                CiboSelectionAlternative(
                    member.trader_identity,
                    envelope_disposition,
                    eligible,
                    score,
                    tuple(reasons),
                )
            )
        ranked = [item for item in alternatives if item.eligible and item.score is not None]
        ranked.sort(key=_alternative_rank_key)
        selected = ranked[0].trader_identity if ranked else None
        selected_output = None if selected is None else output_by_code[selected.trader_code.value]
        decision_reasons = (
            ("no-evidence-qualified-specialist",)
            if selected is None
            else ("highest-evidence-backed-suitability",)
        )
        decision = object.__new__(CiboMetaSelectionDecision)
        fields: dict[str, object] = {
            "decision_id": decision_id,
            "policy": policy,
            "market_state_fingerprint": state.fingerprint,
            "team_fingerprint": shadow.team.fingerprint,
            "shadow_fingerprint": shadow.fingerprint,
            "selected": selected,
            "selected_output_fingerprint": None
            if selected_output is None
            else selected_output.output_fingerprint.value,
            "reasons": decision_reasons,
            "evidence_refs": tuple(
                DemoTradingEvidenceRef(item.value)
                for item in sorted(
                    market_evidence.evidence_refs,
                    key=lambda item: item.value,
                )
            ),
            "suitability_assessments": tuple(assessments),
            "uncertainty": state.regime_uncertainty,
            "alternatives": tuple(alternatives),
            "conflicting_evidence": state.contradictory_evidence,
            "decided_at": decided_at,
            "information_cutoff": state.information_cutoff,
            "provenance": state.provenance,
            "research_only": True,
            "fingerprint": "0" * 64,
        }
        for name, value in fields.items():
            object.__setattr__(decision, name, value)
        object.__setattr__(decision, "fingerprint", decision.compute_fingerprint())
        decision.__post_init__()
        return Success(decision)
    except TraderTeamLabError as error:
        return Failure(error)


__all__ = [
    "CiboFiveTraderShadowEvaluation",
    "CiboLabTraderMember",
    "CiboLabTraderTeam",
    "CiboMarketDimension",
    "CiboMarketEvidenceAuthorityPort",
    "CiboMarketState",
    "CiboMetaSelectionDecision",
    "CiboMetaSelectionPolicy",
    "CiboSelectionAlternative",
    "HistoricalEvidenceState",
    "MarketKnowledgeState",
    "OperatingEnvelopeDisposition",
    "ShadowTraderEvaluator",
    "TraderHistoricalIntelligencePort",
    "TraderHistoricalIntelligenceProjection",
    "TraderOperatingEnvelope",
    "TraderTeamLabBlockedError",
    "TraderTeamLabError",
    "TraderTeamLabValidationError",
    "build_cibo_lab_trader_team",
    "build_cibo_market_state",
    "evaluate_five_trader_shadow",
    "select_cibo_specialist",
]
