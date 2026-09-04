"""CIBO Cognitive World Model substrate (CA-04).

A typed, immutable *cognitive representation/projection layer* over financial
and Core state. It represents references and projections for market/regime,
Trader, portfolio/economic, operational/Core health, and research state, plus
temporal snapshot identity, source evidence/provenance identity, and explicit
contradiction/staleness/missing-evidence state.

This is **not** an authoritative market/Trader/portfolio/research contract and
**not** a market-monitoring behaviour. It never fabricates current state: every
snapshot ``as_of`` and every reference ``as_of`` is supplied explicitly by the
caller, timestamps must be timezone-aware, and stale/contradictory state remains
explicit instead of being collapsed into a single asserted truth.

Architecture laws honoured: immutable snapshots (1, 15, 16), explicit
caller-supplied time (14, 18), provenance references (2, 7), deterministic
canonical ordering (19), secret-bearing evidence fails closed (20), no global
mutable state (21), and no hindsight rewriting (22).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from re import compile
from uuid import UUID

from qore.infrastructure.cibo_cognitive_common import (
    CiboCognitiveError,
    CiboCognitiveFingerprint,
    CiboCognitiveValidationError,
    TraderSubject,
    contains_secret_material,
    fingerprint_material,
    require_aware_datetime,
    require_exact_str,
    utc_instant,
)
from qore.kernel.result import Failure, Result, Success
from qore.kernel.temporal import canonical_instant

_TOKEN = compile(r"[^\s\x00-\x1f\x7f]{1,256}")


class WorldModelError(CiboCognitiveError):
    """Base error for the CIBO cognitive world model."""

    __slots__ = ()


class WorldModelValidationError(WorldModelError, CiboCognitiveValidationError):
    """Violation of a cognitive world model invariant."""

    __slots__ = ()


class WorldModelDomain(StrEnum):
    """Cognitive representation categories (not authoritative contracts)."""

    MARKET = "market"
    TRADER = "trader"
    PORTFOLIO = "portfolio"
    OPERATIONAL = "operational"
    RESEARCH = "research"


class WorldModelReferenceStatus(StrEnum):
    """Explicit availability status of a single source reference."""

    CURRENT = "current"
    STALE = "stale"
    MISSING = "missing"


@dataclass(frozen=True, slots=True)
class WorldModelSourceId:
    """Explicit identity of the external source backing a reference."""

    value: str

    def __post_init__(self) -> None:
        self.revalidate()

    def revalidate(self) -> None:
        require_exact_str(self.value, field="world model source id")
        if _TOKEN.fullmatch(self.value) is None:
            raise WorldModelValidationError(
                "world model source id must be a non-blank token without whitespace"
            )
        if contains_secret_material(self.value):
            raise WorldModelValidationError(
                "world model source id must not carry secret-bearing material"
            )

    def logical_values(self) -> tuple[str]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class WorldModelSourceVersion:
    """Explicit version of the external source backing a reference."""

    value: str

    def __post_init__(self) -> None:
        self.revalidate()

    def revalidate(self) -> None:
        require_exact_str(self.value, field="world model source version")
        if _TOKEN.fullmatch(self.value) is None:
            raise WorldModelValidationError(
                "world model source version must be a non-blank token without whitespace"
            )
        if contains_secret_material(self.value):
            raise WorldModelValidationError(
                "world model source version must not carry secret-bearing material"
            )

    def logical_values(self) -> tuple[str]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class WorldModelReference:
    """Immutable, provenance-bound projection of one external source state."""

    domain: WorldModelDomain
    source_id: WorldModelSourceId
    source_version: WorldModelSourceVersion
    as_of: datetime
    status: WorldModelReferenceStatus
    evidence_fingerprint: CiboCognitiveFingerprint | None = None
    evidence_label: str | None = None

    def __post_init__(self) -> None:
        self.revalidate()

    def revalidate(self) -> None:
        if type(self.domain) is not WorldModelDomain:
            raise WorldModelValidationError("reference domain must be a WorldModelDomain")
        if type(self.source_id) is not WorldModelSourceId:
            raise WorldModelValidationError("reference source id must be a WorldModelSourceId")
        self.source_id.revalidate()
        if type(self.source_version) is not WorldModelSourceVersion:
            raise WorldModelValidationError(
                "reference source version must be a WorldModelSourceVersion"
            )
        self.source_version.revalidate()
        require_aware_datetime(self.as_of, field="reference as_of")
        if type(self.status) is not WorldModelReferenceStatus:
            raise WorldModelValidationError(
                "reference status must be a WorldModelReferenceStatus"
            )
        if self.evidence_fingerprint is not None:
            if type(self.evidence_fingerprint) is not CiboCognitiveFingerprint:
                raise WorldModelValidationError(
                    "reference evidence fingerprint must be a CiboCognitiveFingerprint"
                )
            self.evidence_fingerprint.revalidate()
        if self.status is WorldModelReferenceStatus.MISSING:
            if self.evidence_fingerprint is not None:
                raise WorldModelValidationError(
                    "a missing reference must not carry an evidence fingerprint"
                )
        elif self.evidence_fingerprint is None:
            raise WorldModelValidationError(
                "a current or stale reference must carry an evidence fingerprint"
            )
        if self.evidence_label is not None:
            require_exact_str(self.evidence_label, field="reference evidence label")
            if contains_secret_material(self.evidence_label):
                raise WorldModelValidationError(
                    "reference evidence label must not carry secret-bearing material"
                )
            if len(self.evidence_label) > 512:
                raise WorldModelValidationError("reference evidence label exceeds 512 chars")

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.domain.value,
            self.source_id.value,
            self.source_version.value,
            canonical_instant(self.as_of),
            self.status.value,
            self.evidence_fingerprint.value if self.evidence_fingerprint is not None else None,
            self.evidence_label,
        )

    def sort_key(self) -> tuple[str, ...]:
        return (
            self.domain.value,
            self.source_id.value,
            self.source_version.value,
            canonical_instant(self.as_of),
            self.status.value,
            self.evidence_fingerprint.value if self.evidence_fingerprint is not None else "",
            self.evidence_label or "",
        )


@dataclass(frozen=True, slots=True)
class WorldModelContradiction:
    """Explicit disagreement between two same-domain references."""

    left: WorldModelReference
    right: WorldModelReference
    reason: str

    def __post_init__(self) -> None:
        self.revalidate()

    def revalidate(self) -> None:
        if type(self.left) is not WorldModelReference:
            raise WorldModelValidationError("contradiction left must be a WorldModelReference")
        self.left.revalidate()
        if type(self.right) is not WorldModelReference:
            raise WorldModelValidationError("contradiction right must be a WorldModelReference")
        self.right.revalidate()
        if self.left == self.right:
            raise WorldModelValidationError("a contradiction requires two distinct references")
        if self.left.domain is not self.right.domain:
            raise WorldModelValidationError(
                "a contradiction requires same-domain references"
            )
        require_exact_str(self.reason, field="contradiction reason")
        if not self.reason.strip():
            raise WorldModelValidationError("contradiction reason must not be blank")
        if contains_secret_material(self.reason):
            raise WorldModelValidationError(
                "contradiction reason must not carry secret-bearing material"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (self.left.logical_values(), self.right.logical_values(), self.reason)

    def sort_key(self) -> tuple[tuple[str, ...], tuple[str, ...], str]:
        return (self.left.sort_key(), self.right.sort_key(), self.reason)


def _canonical_timedelta(value: timedelta) -> str:
    return f"{value.days}:{value.seconds}:{value.microseconds}"


@dataclass(frozen=True, slots=True)
class WorldModelSnapshot:
    """Immutable cognitive projection of the world as of an explicit instant."""

    snapshot_id: UUID
    as_of: datetime
    staleness_threshold: timedelta
    references: tuple[WorldModelReference, ...]
    contradictions: tuple[WorldModelContradiction, ...]
    fingerprint: CiboCognitiveFingerprint

    def __post_init__(self) -> None:
        self.revalidate()

    def revalidate(self) -> None:
        canonical = _canonicalize_snapshot(
            self.snapshot_id,
            self.as_of,
            self.staleness_threshold,
            self.references,
            self.contradictions,
        )
        if self.snapshot_id != canonical.snapshot_id:
            raise WorldModelValidationError("snapshot id does not match canonical content")
        if self.as_of != canonical.as_of:
            raise WorldModelValidationError("snapshot as_of does not match canonical content")
        if self.staleness_threshold != canonical.staleness_threshold:
            raise WorldModelValidationError(
                "snapshot staleness threshold does not match canonical content"
            )
        if self.references != canonical.references:
            raise WorldModelValidationError("snapshot references are not canonically ordered")
        if self.contradictions != canonical.contradictions:
            raise WorldModelValidationError(
                "snapshot contradictions are not canonically ordered"
            )
        if self.fingerprint != canonical.fingerprint:
            raise WorldModelValidationError(
                "snapshot fingerprint does not match its canonical content"
            )

    def references_for(self, domain: WorldModelDomain) -> tuple[WorldModelReference, ...]:
        """Return the non-missing references for ``domain`` in canonical order."""
        if type(domain) is not WorldModelDomain:
            raise WorldModelValidationError("domain must be a WorldModelDomain")
        self.revalidate()
        return tuple(
            r
            for r in self.references
            if r.domain is domain and r.status is not WorldModelReferenceStatus.MISSING
        )

    def resolved_reference(
        self, domain: WorldModelDomain
    ) -> Result[WorldModelReference, WorldModelError]:
        """Return a single asserted truth only when no collapse is required.

        Two or more non-missing references in a domain, or any open
        contradiction in that domain, yield ``Failure``: contradictory source
        states are never collapsed into one asserted truth.
        """
        if type(domain) is not WorldModelDomain:
            return Failure(WorldModelValidationError("domain must be a WorldModelDomain"))
        self.revalidate()
        open_contradictions = [c for c in self.contradictions if c.left.domain is domain]
        if open_contradictions:
            return Failure(
                WorldModelValidationError(
                    "domain carries open contradictions; cannot assert a single truth"
                )
            )
        matches = self.references_for(domain)
        if len(matches) == 1:
            return Success(matches[0])
        if not matches:
            return Failure(WorldModelValidationError("domain has no non-missing reference"))
        return Failure(
            WorldModelValidationError(
                "domain has multiple references; cannot collapse into one asserted truth"
            )
        )

    def stale_references(self) -> tuple[WorldModelReference, ...]:
        self.revalidate()
        return tuple(
            r for r in self.references if r.status is WorldModelReferenceStatus.STALE
        )

    def missing_domains(self) -> tuple[WorldModelDomain, ...]:
        self.revalidate()
        present = {
            r.domain
            for r in self.references
            if r.status is not WorldModelReferenceStatus.MISSING
        }
        return tuple(
            sorted((d for d in WorldModelDomain if d not in present), key=lambda d: d.value)
        )


def _rebuild_references(
    references: object,
) -> tuple[WorldModelReference, ...]:
    if type(references) is not tuple:
        raise WorldModelValidationError("references must be a tuple")
    rebuilt = []
    for ref in references:
        if type(ref) is not WorldModelReference:
            raise WorldModelValidationError(
                "references must contain only WorldModelReference values"
            )
        rebuilt.append(
            WorldModelReference(
                domain=ref.domain,
                source_id=ref.source_id,
                source_version=ref.source_version,
                as_of=ref.as_of,
                status=ref.status,
                evidence_fingerprint=ref.evidence_fingerprint,
                evidence_label=ref.evidence_label,
            )
        )
    return tuple(sorted(rebuilt, key=lambda r: r.sort_key()))


def _rebuild_contradictions(
    contradictions: object,
    references: tuple[WorldModelReference, ...],
) -> tuple[WorldModelContradiction, ...]:
    if type(contradictions) is not tuple:
        raise WorldModelValidationError("contradictions must be a tuple")
    rebuilt = []
    for contradiction in contradictions:
        if type(contradiction) is not WorldModelContradiction:
            raise WorldModelValidationError(
                "contradictions must contain only WorldModelContradiction values"
            )
        rebuilt.append(
            WorldModelContradiction(
                left=contradiction.left,
                right=contradiction.right,
                reason=contradiction.reason,
            )
        )
    ordered = tuple(sorted(rebuilt, key=lambda c: c.sort_key()))
    reference_keys = {r.sort_key() for r in references}
    for contradiction in ordered:
        if (
            contradiction.left.sort_key() not in reference_keys
            or contradiction.right.sort_key() not in reference_keys
        ):
            raise WorldModelValidationError(
                "contradiction references must be present in the snapshot"
            )
    return ordered


@dataclass(frozen=True, slots=True)
class _CanonicalSnapshot:
    snapshot_id: UUID
    as_of: datetime
    staleness_threshold: timedelta
    references: tuple[WorldModelReference, ...]
    contradictions: tuple[WorldModelContradiction, ...]
    fingerprint: CiboCognitiveFingerprint


def _snapshot_material(
    snapshot_id: UUID,
    as_of: datetime,
    staleness_threshold: timedelta,
    references: tuple[WorldModelReference, ...],
    contradictions: tuple[WorldModelContradiction, ...],
) -> tuple[object, ...]:
    return (
        str(snapshot_id),
        canonical_instant(as_of),
        _canonical_timedelta(staleness_threshold),
        tuple(r.logical_values() for r in references),
        tuple(c.logical_values() for c in contradictions),
    )


def _canonicalize_snapshot(
    snapshot_id: object,
    as_of: object,
    staleness_threshold: object,
    references: object,
    contradictions: object,
) -> _CanonicalSnapshot:
    if type(snapshot_id) is not UUID:
        raise WorldModelValidationError("snapshot id must be a UUID")
    aware_as_of = require_aware_datetime(as_of, field="snapshot as_of")
    if type(staleness_threshold) is not timedelta:
        raise WorldModelValidationError("staleness threshold must be a timedelta")
    if staleness_threshold < timedelta(0):
        raise WorldModelValidationError("staleness threshold must be non-negative")

    rebuilt_refs = _rebuild_references(references)
    for ref in rebuilt_refs:
        if utc_instant(ref.as_of, field="reference as_of") > utc_instant(
            aware_as_of, field="snapshot as_of"
        ):
            raise WorldModelValidationError(
                "reference as_of must not postdate the snapshot as_of"
            )
        if (
            ref.status is WorldModelReferenceStatus.CURRENT
            and (
                utc_instant(aware_as_of, field="snapshot as_of")
                - utc_instant(ref.as_of, field="reference as_of")
            )
            > staleness_threshold
        ):
            raise WorldModelValidationError(
                "a current reference is stale relative to the snapshot as_of"
            )

    rebuilt_contradictions = _rebuild_contradictions(contradictions, rebuilt_refs)
    fingerprint = fingerprint_material(
        _snapshot_material(
            snapshot_id,
            aware_as_of,
            staleness_threshold,
            rebuilt_refs,
            rebuilt_contradictions,
        )
    )
    return _CanonicalSnapshot(
        snapshot_id,
        aware_as_of,
        staleness_threshold,
        rebuilt_refs,
        rebuilt_contradictions,
        fingerprint,
    )


def build_world_model_snapshot(
    *,
    snapshot_id: UUID,
    as_of: datetime,
    references: Sequence[WorldModelReference],
    contradictions: Sequence[WorldModelContradiction] = (),
    staleness_threshold: timedelta = timedelta(0),
) -> WorldModelSnapshot:
    """Build a validated, canonically ordered, fingerprinted world snapshot."""
    if type(snapshot_id) is not UUID:
        raise WorldModelValidationError("snapshot id must be a UUID")
    if not isinstance(references, Sequence):
        raise WorldModelValidationError("references must be a sequence")
    if not isinstance(contradictions, Sequence):
        raise WorldModelValidationError("contradictions must be a sequence")
    canonical = _canonicalize_snapshot(
        snapshot_id,
        as_of,
        staleness_threshold,
        tuple(references),
        tuple(contradictions),
    )
    return WorldModelSnapshot(
        snapshot_id=canonical.snapshot_id,
        as_of=canonical.as_of,
        staleness_threshold=canonical.staleness_threshold,
        references=canonical.references,
        contradictions=canonical.contradictions,
        fingerprint=canonical.fingerprint,
    )


def project_world_state(
    snapshot: WorldModelSnapshot, domain: WorldModelDomain
) -> Result[tuple[WorldModelReference, ...], WorldModelError]:
    """Project the non-missing references of ``domain`` without asserting truth."""
    if type(snapshot) is not WorldModelSnapshot:
        return Failure(WorldModelValidationError("snapshot must be a WorldModelSnapshot"))
    if type(domain) is not WorldModelDomain:
        return Failure(WorldModelValidationError("domain must be a WorldModelDomain"))
    return Success(snapshot.references_for(domain))


class MarketTraderSuitabilityDisposition(StrEnum):
    """Typed, authority-free suitability disposition for one exact Trader context.

    FAVORABLE is the only positive assertion; it is only admissible when every
    market/instrument/regime reference is CURRENT, evidence lineage is non-empty,
    no contradiction is present, and explicit limitations are retained.
    """

    FAVORABLE = "favorable"
    DEGRADED = "degraded"
    UNSUITABLE = "unsuitable"
    UNCERTAIN = "uncertain"
    INSUFFICIENT_EVIDENCE = "insufficient-evidence"
    CONTRADICTORY_EVIDENCE = "contradictory-evidence"


class MarketContextKind(StrEnum):
    """The three exact market-context axes bound by a suitability assertion."""

    MARKET = "market"
    INSTRUMENT = "instrument"
    REGIME = "regime"


@dataclass(frozen=True, slots=True)
class MarketContextReference:
    """Exact, evidence-bound, time-bound context reference for one market axis."""

    kind: MarketContextKind
    reference: str
    as_of: datetime
    status: WorldModelReferenceStatus
    evidence_fingerprint: CiboCognitiveFingerprint | None = None
    evidence_label: str | None = None

    def __post_init__(self) -> None:
        self.revalidate()

    def revalidate(self) -> None:
        if type(self.kind) is not MarketContextKind:
            raise WorldModelValidationError(
                "market context kind must be a MarketContextKind"
            )
        require_exact_str(self.reference, field="market context reference")
        if _TOKEN.fullmatch(self.reference) is None:
            raise WorldModelValidationError(
                "market context reference must be a non-blank token without whitespace"
            )
        if contains_secret_material(self.reference):
            raise WorldModelValidationError(
                "market context reference must not carry secret-bearing material"
            )
        require_aware_datetime(self.as_of, field="market context as_of")
        if type(self.status) is not WorldModelReferenceStatus:
            raise WorldModelValidationError(
                "market context status must be a WorldModelReferenceStatus"
            )
        if self.status is WorldModelReferenceStatus.MISSING:
            if self.evidence_fingerprint is not None:
                raise WorldModelValidationError(
                    "a missing market context reference must not carry an evidence fingerprint"
                )
        elif self.evidence_fingerprint is None:
            raise WorldModelValidationError(
                "a current or stale market context reference must carry an evidence fingerprint"
            )
        if self.evidence_fingerprint is not None:
            if type(self.evidence_fingerprint) is not CiboCognitiveFingerprint:
                raise WorldModelValidationError(
                    "market context evidence fingerprint must be a CiboCognitiveFingerprint"
                )
            self.evidence_fingerprint.revalidate()
        if self.evidence_label is not None:
            require_exact_str(self.evidence_label, field="market context evidence label")
            if contains_secret_material(self.evidence_label):
                raise WorldModelValidationError(
                    "market context evidence label must not carry secret-bearing material"
                )
            if len(self.evidence_label) > 512:
                raise WorldModelValidationError(
                    "market context evidence label exceeds 512 chars"
                )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.kind.value,
            self.reference,
            canonical_instant(self.as_of),
            self.status.value,
            self.evidence_fingerprint.value if self.evidence_fingerprint is not None else None,
            self.evidence_label,
        )

    def sort_key(self) -> tuple[str, ...]:
        return (
            self.kind.value,
            self.reference,
            canonical_instant(self.as_of),
            self.status.value,
            self.evidence_fingerprint.value if self.evidence_fingerprint is not None else "",
            self.evidence_label or "",
        )


@dataclass(frozen=True, slots=True)
class MarketTraderContext:
    """Exact market/instrument/regime context set for one suitability assertion."""

    market: MarketContextReference
    instrument: MarketContextReference
    regime: MarketContextReference

    def __post_init__(self) -> None:
        self.revalidate()

    def revalidate(self) -> None:
        for slot, expected in (
            (self.market, MarketContextKind.MARKET),
            (self.instrument, MarketContextKind.INSTRUMENT),
            (self.regime, MarketContextKind.REGIME),
        ):
            if type(slot) is not MarketContextReference:
                raise WorldModelValidationError(
                    "market context slot must be a MarketContextReference"
                )
            slot.revalidate()
            if slot.kind is not expected:
                raise WorldModelValidationError(
                    f"market context slot must use the {expected.value} axis"
                )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.market.logical_values(),
            self.instrument.logical_values(),
            self.regime.logical_values(),
        )

    def sort_key(self) -> tuple[tuple[str, ...], ...]:
        return (self.market.sort_key(), self.instrument.sort_key(), self.regime.sort_key())


def _canonical_codes(
    values: tuple[str, ...],
    *,
    field_name: str,
) -> tuple[str, ...]:
    """Validate and canonically order a tuple of non-blank, secret-free codes."""
    if type(values) is not tuple or any(type(value) is not str for value in values):
        raise WorldModelValidationError(
            f"{field_name} must be an immutable tuple of exact strings"
        )
    normalized = []
    for value in values:
        if not value.strip():
            raise WorldModelValidationError(f"{field_name} must not contain blank codes")
        if contains_secret_material(value):
            raise WorldModelValidationError(
                f"{field_name} must not carry secret-bearing material"
            )
        normalized.append(value)
    if len(set(normalized)) != len(normalized):
        raise WorldModelValidationError(f"{field_name} must not contain duplicates")
    return tuple(sorted(normalized))


def _canonical_lineage(
    values: tuple[CiboCognitiveFingerprint, ...],
    *,
    field_name: str,
) -> tuple[CiboCognitiveFingerprint, ...]:
    """Validate, deduplicate, and canonically order an evidence lineage."""
    if type(values) is not tuple or any(
        type(item) is not CiboCognitiveFingerprint for item in values
    ):
        raise WorldModelValidationError(
            f"{field_name} must be an immutable tuple of CiboCognitiveFingerprint"
        )
    for item in values:
        item.revalidate()
    by_value = {item.value: item for item in values}
    if len(by_value) != len(values):
        raise WorldModelValidationError(f"{field_name} must not contain duplicates")
    return tuple(sorted(values, key=lambda item: item.value))


@dataclass(frozen=True, slots=True)
class MarketTraderSuitability:
    """Typed suitability disposition for one exact Trader in one exact context.

    The disposition is fail-closed: stale, missing, or contradictory evidence
    forbids FAVORABLE (the only positive assertion) and forces the corresponding
    non-positive disposition. A FAVORABLE assertion must retain explicit
    limitations so ``MARKET KNOWLEDGE != CLAIM OF PERFECT CERTAINTY``. The object
    exposes no execution, Risk, promotion, DEMO, Production, or profitability
    authority.
    """

    suitability_id: UUID
    trader: TraderSubject
    context: MarketTraderContext
    disposition: MarketTraderSuitabilityDisposition
    uncertainty_codes: tuple[str, ...]
    limitations: tuple[str, ...]
    contradictions: tuple[str, ...]
    evidence_lineage: tuple[CiboCognitiveFingerprint, ...]
    fingerprint: CiboCognitiveFingerprint

    def __post_init__(self) -> None:
        self.revalidate()

    def revalidate(self) -> None:
        if type(self.suitability_id) is not UUID:
            raise WorldModelValidationError("suitability id must be a UUID")
        if type(self.trader) is not TraderSubject:
            raise WorldModelValidationError("suitability trader must be a TraderSubject")
        self.trader.revalidate()
        if type(self.context) is not MarketTraderContext:
            raise WorldModelValidationError(
                "suitability context must be a MarketTraderContext"
            )
        self.context.revalidate()
        if type(self.disposition) is not MarketTraderSuitabilityDisposition:
            raise WorldModelValidationError(
                "suitability disposition must be a MarketTraderSuitabilityDisposition"
            )
        if self.uncertainty_codes != _canonical_codes(
            self.uncertainty_codes, field_name="suitability uncertainty codes"
        ):
            raise WorldModelValidationError(
                "suitability uncertainty codes failed canonical revalidation"
            )
        if self.limitations != _canonical_codes(
            self.limitations, field_name="suitability limitations"
        ):
            raise WorldModelValidationError(
                "suitability limitations failed canonical revalidation"
            )
        if self.contradictions != _canonical_codes(
            self.contradictions, field_name="suitability contradictions"
        ):
            raise WorldModelValidationError(
                "suitability contradictions failed canonical revalidation"
            )
        if self.evidence_lineage != _canonical_lineage(
            self.evidence_lineage, field_name="suitability evidence lineage"
        ):
            raise WorldModelValidationError(
                "suitability evidence lineage failed canonical revalidation"
            )
        if type(self.fingerprint) is not CiboCognitiveFingerprint:
            raise WorldModelValidationError(
                "suitability fingerprint must be a CiboCognitiveFingerprint"
            )
        self.fingerprint.revalidate()
        self._validate_disposition()
        if self.fingerprint != fingerprint_material(self.logical_values()):
            raise WorldModelValidationError(
                "suitability fingerprint does not match its canonical content"
            )

    def _validate_disposition(self) -> None:
        refs = (self.context.market, self.context.instrument, self.context.regime)
        contradictory = bool(self.contradictions)
        missing = any(r.status is WorldModelReferenceStatus.MISSING for r in refs)
        stale = any(r.status is WorldModelReferenceStatus.STALE for r in refs)
        has_lineage = bool(self.evidence_lineage)
        if contradictory:
            allowed = {MarketTraderSuitabilityDisposition.CONTRADICTORY_EVIDENCE}
        elif missing or not has_lineage:
            allowed = {MarketTraderSuitabilityDisposition.INSUFFICIENT_EVIDENCE}
        elif stale:
            allowed = {MarketTraderSuitabilityDisposition.UNCERTAIN}
        else:
            allowed = {
                MarketTraderSuitabilityDisposition.FAVORABLE,
                MarketTraderSuitabilityDisposition.DEGRADED,
                MarketTraderSuitabilityDisposition.UNSUITABLE,
                MarketTraderSuitabilityDisposition.UNCERTAIN,
            }
        if self.disposition not in allowed:
            raise WorldModelValidationError(
                "suitability disposition is not admissible for its evidence state"
            )
        if (
            self.disposition is MarketTraderSuitabilityDisposition.FAVORABLE
            and not self.limitations
        ):
            raise WorldModelValidationError(
                "a favorable suitability assertion must retain explicit limitations"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            str(self.suitability_id),
            self.trader.logical_values(),
            self.context.logical_values(),
            self.disposition.value,
            self.uncertainty_codes,
            self.limitations,
            self.contradictions,
            tuple(item.value for item in self.evidence_lineage),
        )


def build_market_trader_suitability(
    *,
    suitability_id: UUID,
    trader: TraderSubject,
    context: MarketTraderContext,
    disposition: MarketTraderSuitabilityDisposition,
    uncertainty_codes: Sequence[str] = (),
    limitations: Sequence[str] = (),
    contradictions: Sequence[str] = (),
    evidence_lineage: Sequence[CiboCognitiveFingerprint] = (),
) -> MarketTraderSuitability:
    """Build a validated, canonically ordered, fingerprinted suitability assertion."""
    if type(suitability_id) is not UUID:
        raise WorldModelValidationError("suitability id must be a UUID")
    if type(trader) is not TraderSubject:
        raise WorldModelValidationError("suitability trader must be a TraderSubject")
    trader.revalidate()
    if type(context) is not MarketTraderContext:
        raise WorldModelValidationError(
            "suitability context must be a MarketTraderContext"
        )
    context.revalidate()
    if type(disposition) is not MarketTraderSuitabilityDisposition:
        raise WorldModelValidationError(
            "suitability disposition must be a MarketTraderSuitabilityDisposition"
        )
    if not isinstance(uncertainty_codes, Sequence):
        raise WorldModelValidationError("uncertainty codes must be a sequence")
    if not isinstance(limitations, Sequence):
        raise WorldModelValidationError("limitations must be a sequence")
    if not isinstance(contradictions, Sequence):
        raise WorldModelValidationError("contradictions must be a sequence")
    if not isinstance(evidence_lineage, Sequence):
        raise WorldModelValidationError("evidence lineage must be a sequence")
    uncertainty = _canonical_codes(
        tuple(uncertainty_codes), field_name="suitability uncertainty codes"
    )
    limitation_codes = _canonical_codes(
        tuple(limitations), field_name="suitability limitations"
    )
    contradiction_codes = _canonical_codes(
        tuple(contradictions), field_name="suitability contradictions"
    )
    lineage = _canonical_lineage(
        tuple(evidence_lineage), field_name="suitability evidence lineage"
    )
    logical = (
        str(suitability_id),
        trader.logical_values(),
        context.logical_values(),
        disposition.value,
        uncertainty,
        limitation_codes,
        contradiction_codes,
        tuple(item.value for item in lineage),
    )
    return MarketTraderSuitability(
        suitability_id=suitability_id,
        trader=trader,
        context=context,
        disposition=disposition,
        uncertainty_codes=uncertainty,
        limitations=limitation_codes,
        contradictions=contradiction_codes,
        evidence_lineage=lineage,
        fingerprint=fingerprint_material(logical),
    )


__all__ = [
    "MarketContextKind",
    "MarketContextReference",
    "MarketTraderContext",
    "MarketTraderSuitability",
    "MarketTraderSuitabilityDisposition",
    "WorldModelContradiction",
    "WorldModelDomain",
    "WorldModelError",
    "WorldModelReference",
    "WorldModelReferenceStatus",
    "WorldModelSnapshot",
    "WorldModelSourceId",
    "WorldModelSourceVersion",
    "WorldModelValidationError",
    "build_market_trader_suitability",
    "build_world_model_snapshot",
    "project_world_state",
]
