from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from re import fullmatch
from uuid import UUID

from qore.infrastructure.ports import ExternalSourceDescriptor
from qore.kernel.errors import InfrastructureError


class UniversalInstrumentIdentityError(InfrastructureError):
    """Base error for universal instrument identity/lifecycle contracts."""

    __slots__ = ()


class UniversalInstrumentIdentityValidationError(UniversalInstrumentIdentityError):
    """Violation of a universal instrument identity/lifecycle invariant."""

    __slots__ = ()


def _validate_uuid(value: UUID, *, field_name: str) -> None:
    if not isinstance(value, UUID):
        raise UniversalInstrumentIdentityValidationError(f"{field_name} must be UUID")


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise UniversalInstrumentIdentityValidationError(
            f"{field_name} must be datetime"
        )
    if value.tzinfo is None or value.utcoffset() is None:
        raise UniversalInstrumentIdentityValidationError(
            f"{field_name} must be timezone-aware"
        )


def _validate_code(value: str, *, field_name: str) -> None:
    if not isinstance(value, str) or fullmatch(
        r"[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*", value
    ) is None:
        raise UniversalInstrumentIdentityValidationError(
            f"{field_name} must use canonical lowercase code syntax"
        )


def _validate_text(value: str, *, field_name: str, max_length: int) -> None:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value) > max_length
        or any(ord(character) < 32 or ord(character) == 127 for character in value)
    ):
        raise UniversalInstrumentIdentityValidationError(
            f"{field_name} must be non-empty trimmed text without control characters"
        )


@dataclass(frozen=True, slots=True)
class EconomicIdentityId:
    """Stable QORE identity for one economic instrument or reference object."""

    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="economic identity id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ListingIdentityId:
    """Stable QORE identity for one venue/listing representation."""

    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="listing identity id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class IdentityRelationshipId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="identity relationship id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class IdentityLifecycleEventId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="identity lifecycle event id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class IdentityMappingId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="identity mapping id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class IdentityEvidenceRef:
    """Reference to retained identity evidence; never the evidence itself."""

    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="identity evidence ref")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


class EconomicIdentityKind(StrEnum):
    TRADABLE_INSTRUMENT = "tradable-instrument"
    REFERENCE_OBJECT = "reference-object"


class IdentityConstructionKind(StrEnum):
    NATIVE = "native"
    SYNTHETIC = "synthetic"
    COMPOSITE = "composite"
    CONTINUOUS_REFERENCE = "continuous-reference"


class ExternalIdentifierKind(StrEnum):
    LEGACY_QORE = "legacy-qore"
    PROVIDER_NATIVE = "provider-native"
    VENUE_NATIVE = "venue-native"
    STANDARD = "standard"
    NETWORK_NATIVE = "network-native"


@dataclass(frozen=True, slots=True)
class IdentityFamilyCode:
    """Extensible classification code; classification is never identity."""

    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="identity family code")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class MarketVenueCode:
    """Provider-neutral venue/listing scope code."""

    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="market venue code")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class ExternalIdentifierNamespace:
    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="external identifier namespace")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class ExternalIdentifierValue:
    value: str

    def __post_init__(self) -> None:
        _validate_text(
            self.value,
            field_name="external identifier value",
            max_length=256,
        )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class IdentityRelationshipCode:
    """Extensible relationship role without one global family enum."""

    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="identity relationship code")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class LifecycleEventCode:
    """Extensible lifecycle event code; not every family shares one lifecycle."""

    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="lifecycle event code")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class IdentityMappingRevision:
    value: int

    def __post_init__(self) -> None:
        if type(self.value) is not int or self.value <= 0:
            raise UniversalInstrumentIdentityValidationError(
                "identity mapping revision must be a positive int"
            )

    def logical_values(self) -> tuple[int, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class EconomicIdentity:
    """Stable canonical identity, independent of provider symbol/listing text."""

    identity_id: EconomicIdentityId
    kind: EconomicIdentityKind
    family: IdentityFamilyCode
    construction: IdentityConstructionKind
    evidence_ref: IdentityEvidenceRef

    def __post_init__(self) -> None:
        if not isinstance(self.identity_id, EconomicIdentityId):
            raise UniversalInstrumentIdentityValidationError(
                "economic identity identity_id must be EconomicIdentityId"
            )
        if not isinstance(self.kind, EconomicIdentityKind):
            raise UniversalInstrumentIdentityValidationError(
                "economic identity kind must be EconomicIdentityKind"
            )
        if not isinstance(self.family, IdentityFamilyCode):
            raise UniversalInstrumentIdentityValidationError(
                "economic identity family must be IdentityFamilyCode"
            )
        if not isinstance(self.construction, IdentityConstructionKind):
            raise UniversalInstrumentIdentityValidationError(
                "economic identity construction must be IdentityConstructionKind"
            )
        if not isinstance(self.evidence_ref, IdentityEvidenceRef):
            raise UniversalInstrumentIdentityValidationError(
                "economic identity evidence_ref must be IdentityEvidenceRef"
            )
        if (
            self.construction is IdentityConstructionKind.CONTINUOUS_REFERENCE
            and self.kind is not EconomicIdentityKind.REFERENCE_OBJECT
        ):
            raise UniversalInstrumentIdentityValidationError(
                "continuous-reference identity must be a reference object"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.identity_id.logical_values(),
            self.kind.value,
            self.family.logical_values(),
            self.construction.value,
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class ListingIdentity:
    """One venue/listing representation of an economic identity."""

    listing_id: ListingIdentityId
    economic_identity_id: EconomicIdentityId
    venue: MarketVenueCode
    display_symbol: str
    valid_from: datetime
    valid_until: datetime | None
    evidence_ref: IdentityEvidenceRef

    def __post_init__(self) -> None:
        if not isinstance(self.listing_id, ListingIdentityId):
            raise UniversalInstrumentIdentityValidationError(
                "listing listing_id must be ListingIdentityId"
            )
        if not isinstance(self.economic_identity_id, EconomicIdentityId):
            raise UniversalInstrumentIdentityValidationError(
                "listing economic_identity_id must be EconomicIdentityId"
            )
        if not isinstance(self.venue, MarketVenueCode):
            raise UniversalInstrumentIdentityValidationError(
                "listing venue must be MarketVenueCode"
            )
        _validate_text(
            self.display_symbol,
            field_name="listing display_symbol",
            max_length=128,
        )
        _validate_timestamp(self.valid_from, field_name="listing valid_from")
        if self.valid_until is not None:
            _validate_timestamp(self.valid_until, field_name="listing valid_until")
            if self.valid_until <= self.valid_from:
                raise UniversalInstrumentIdentityValidationError(
                    "listing valid_until must be after valid_from"
                )
        if not isinstance(self.evidence_ref, IdentityEvidenceRef):
            raise UniversalInstrumentIdentityValidationError(
                "listing evidence_ref must be IdentityEvidenceRef"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.listing_id.logical_values(),
            self.economic_identity_id.logical_values(),
            self.venue.logical_values(),
            self.display_symbol,
            self.valid_from.isoformat(),
            self.valid_until.isoformat() if self.valid_until is not None else None,
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class CanonicalIdentityRef:
    """Typed reference to either economic identity or one listing identity."""

    value: EconomicIdentityId | ListingIdentityId

    def __post_init__(self) -> None:
        if not isinstance(self.value, (EconomicIdentityId, ListingIdentityId)):
            raise UniversalInstrumentIdentityValidationError(
                "canonical identity ref must reference economic or listing identity"
            )

    def logical_values(self) -> tuple[object, ...]:
        if isinstance(self.value, EconomicIdentityId):
            return ("economic", self.value.logical_values())
        return ("listing", self.value.logical_values())


@dataclass(frozen=True, slots=True)
class ExternalIdentifier:
    """External/legacy identifier with explicit semantic class and scope."""

    kind: ExternalIdentifierKind
    namespace: ExternalIdentifierNamespace
    value: ExternalIdentifierValue
    source: ExternalSourceDescriptor | None = None
    venue: MarketVenueCode | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, ExternalIdentifierKind):
            raise UniversalInstrumentIdentityValidationError(
                "external identifier kind must be ExternalIdentifierKind"
            )
        if not isinstance(self.namespace, ExternalIdentifierNamespace):
            raise UniversalInstrumentIdentityValidationError(
                "external identifier namespace must be ExternalIdentifierNamespace"
            )
        if not isinstance(self.value, ExternalIdentifierValue):
            raise UniversalInstrumentIdentityValidationError(
                "external identifier value must be ExternalIdentifierValue"
            )
        if self.source is not None and not isinstance(
            self.source, ExternalSourceDescriptor
        ):
            raise UniversalInstrumentIdentityValidationError(
                "external identifier source must be ExternalSourceDescriptor or None"
            )
        if self.venue is not None and not isinstance(self.venue, MarketVenueCode):
            raise UniversalInstrumentIdentityValidationError(
                "external identifier venue must be MarketVenueCode or None"
            )
        if self.kind is ExternalIdentifierKind.PROVIDER_NATIVE and self.source is None:
            raise UniversalInstrumentIdentityValidationError(
                "provider-native identifier requires explicit source provenance"
            )
        if self.kind is ExternalIdentifierKind.VENUE_NATIVE and self.venue is None:
            raise UniversalInstrumentIdentityValidationError(
                "venue-native identifier requires explicit venue scope"
            )
        if self.kind is ExternalIdentifierKind.LEGACY_QORE and (
            self.source is not None or self.venue is not None
        ):
            raise UniversalInstrumentIdentityValidationError(
                "legacy QORE identifier must not masquerade as external scope"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.kind.value,
            self.namespace.logical_values(),
            self.value.logical_values(),
            self.source.logical_values() if self.source is not None else None,
            self.venue.logical_values() if self.venue is not None else None,
        )


@dataclass(frozen=True, slots=True)
class IdentityRelationship:
    """Effective-dated relationship in the canonical economic identity graph."""

    relationship_id: IdentityRelationshipId
    source_identity_id: EconomicIdentityId
    target_identity_id: EconomicIdentityId
    relationship: IdentityRelationshipCode
    effective_from: datetime
    effective_until: datetime | None
    evidence_ref: IdentityEvidenceRef
    ordinal: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.relationship_id, IdentityRelationshipId):
            raise UniversalInstrumentIdentityValidationError(
                "relationship_id must be IdentityRelationshipId"
            )
        if not isinstance(self.source_identity_id, EconomicIdentityId):
            raise UniversalInstrumentIdentityValidationError(
                "source_identity_id must be EconomicIdentityId"
            )
        if not isinstance(self.target_identity_id, EconomicIdentityId):
            raise UniversalInstrumentIdentityValidationError(
                "target_identity_id must be EconomicIdentityId"
            )
        if self.source_identity_id == self.target_identity_id:
            raise UniversalInstrumentIdentityValidationError(
                "identity relationship source and target must differ"
            )
        if not isinstance(self.relationship, IdentityRelationshipCode):
            raise UniversalInstrumentIdentityValidationError(
                "relationship must be IdentityRelationshipCode"
            )
        _validate_timestamp(self.effective_from, field_name="relationship effective_from")
        if self.effective_until is not None:
            _validate_timestamp(
                self.effective_until,
                field_name="relationship effective_until",
            )
            if self.effective_until <= self.effective_from:
                raise UniversalInstrumentIdentityValidationError(
                    "relationship effective_until must be after effective_from"
                )
        if not isinstance(self.evidence_ref, IdentityEvidenceRef):
            raise UniversalInstrumentIdentityValidationError(
                "relationship evidence_ref must be IdentityEvidenceRef"
            )
        if self.ordinal is not None and (
            type(self.ordinal) is not int or self.ordinal <= 0
        ):
            raise UniversalInstrumentIdentityValidationError(
                "relationship ordinal must be a positive int or None"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.relationship_id.logical_values(),
            self.source_identity_id.logical_values(),
            self.target_identity_id.logical_values(),
            self.relationship.logical_values(),
            self.effective_from.isoformat(),
            self.effective_until.isoformat()
            if self.effective_until is not None
            else None,
            self.evidence_ref.logical_values(),
            self.ordinal,
        )


@dataclass(frozen=True, slots=True)
class IdentityLifecycleEvent:
    """Evidence-bearing lifecycle event without one global lifecycle enum."""

    event_id: IdentityLifecycleEventId
    subject: CanonicalIdentityRef
    event_type: LifecycleEventCode
    effective_at: datetime
    recorded_at: datetime
    evidence_ref: IdentityEvidenceRef

    def __post_init__(self) -> None:
        if not isinstance(self.event_id, IdentityLifecycleEventId):
            raise UniversalInstrumentIdentityValidationError(
                "lifecycle event_id must be IdentityLifecycleEventId"
            )
        if not isinstance(self.subject, CanonicalIdentityRef):
            raise UniversalInstrumentIdentityValidationError(
                "lifecycle subject must be CanonicalIdentityRef"
            )
        if not isinstance(self.event_type, LifecycleEventCode):
            raise UniversalInstrumentIdentityValidationError(
                "lifecycle event_type must be LifecycleEventCode"
            )
        _validate_timestamp(self.effective_at, field_name="lifecycle effective_at")
        _validate_timestamp(self.recorded_at, field_name="lifecycle recorded_at")
        if not isinstance(self.evidence_ref, IdentityEvidenceRef):
            raise UniversalInstrumentIdentityValidationError(
                "lifecycle evidence_ref must be IdentityEvidenceRef"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.event_id.logical_values(),
            self.subject.logical_values(),
            self.event_type.logical_values(),
            self.effective_at.isoformat(),
            self.recorded_at.isoformat(),
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class ExternalIdentityMappingRevision:
    """One immutable revision of legacy/external-to-canonical identity mapping."""

    mapping_id: IdentityMappingId
    revision: IdentityMappingRevision
    parent_revision: IdentityMappingRevision | None
    external_identity: ExternalIdentifier
    target: CanonicalIdentityRef
    effective_from: datetime
    effective_until: datetime | None
    recorded_at: datetime
    evidence_ref: IdentityEvidenceRef

    def __post_init__(self) -> None:
        if not isinstance(self.mapping_id, IdentityMappingId):
            raise UniversalInstrumentIdentityValidationError(
                "mapping mapping_id must be IdentityMappingId"
            )
        if not isinstance(self.revision, IdentityMappingRevision):
            raise UniversalInstrumentIdentityValidationError(
                "mapping revision must be IdentityMappingRevision"
            )
        if self.parent_revision is not None and not isinstance(
            self.parent_revision, IdentityMappingRevision
        ):
            raise UniversalInstrumentIdentityValidationError(
                "mapping parent_revision must be IdentityMappingRevision or None"
            )
        if self.revision.value == 1 and self.parent_revision is not None:
            raise UniversalInstrumentIdentityValidationError(
                "first mapping revision must not have parent_revision"
            )
        if self.revision.value > 1 and (
            self.parent_revision is None
            or self.parent_revision.value >= self.revision.value
        ):
            raise UniversalInstrumentIdentityValidationError(
                "later mapping revision requires an earlier parent_revision"
            )
        if not isinstance(self.external_identity, ExternalIdentifier):
            raise UniversalInstrumentIdentityValidationError(
                "mapping external_identity must be ExternalIdentifier"
            )
        if not isinstance(self.target, CanonicalIdentityRef):
            raise UniversalInstrumentIdentityValidationError(
                "mapping target must be CanonicalIdentityRef"
            )
        _validate_timestamp(self.effective_from, field_name="mapping effective_from")
        if self.effective_until is not None:
            _validate_timestamp(
                self.effective_until,
                field_name="mapping effective_until",
            )
            if self.effective_until <= self.effective_from:
                raise UniversalInstrumentIdentityValidationError(
                    "mapping effective_until must be after effective_from"
                )
        _validate_timestamp(self.recorded_at, field_name="mapping recorded_at")
        if not isinstance(self.evidence_ref, IdentityEvidenceRef):
            raise UniversalInstrumentIdentityValidationError(
                "mapping evidence_ref must be IdentityEvidenceRef"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.mapping_id.logical_values(),
            self.revision.logical_values(),
            self.parent_revision.logical_values()
            if self.parent_revision is not None
            else None,
            self.external_identity.logical_values(),
            self.target.logical_values(),
            self.effective_from.isoformat(),
            self.effective_until.isoformat()
            if self.effective_until is not None
            else None,
            self.recorded_at.isoformat(),
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class IdentityMappingHistory:
    """Complete retained revision chain for one external identity mapping."""

    revisions: tuple[ExternalIdentityMappingRevision, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.revisions, tuple) or not self.revisions or any(
            not isinstance(item, ExternalIdentityMappingRevision)
            for item in self.revisions
        ):
            raise UniversalInstrumentIdentityValidationError(
                "mapping history revisions must be a non-empty immutable tuple"
            )
        first = self.revisions[0]
        expected_mapping_id = first.mapping_id
        expected_external_identity = first.external_identity
        for index, revision in enumerate(self.revisions, start=1):
            if revision.mapping_id != expected_mapping_id:
                raise UniversalInstrumentIdentityValidationError(
                    "mapping history must retain one mapping_id"
                )
            if revision.external_identity != expected_external_identity:
                raise UniversalInstrumentIdentityValidationError(
                    "mapping history must retain one external identity"
                )
            if revision.revision.value != index:
                raise UniversalInstrumentIdentityValidationError(
                    "mapping history revisions must be contiguous from 1"
                )
            if index == 1:
                if revision.parent_revision is not None:
                    raise UniversalInstrumentIdentityValidationError(
                        "first mapping history revision must not have parent"
                    )
            elif (
                revision.parent_revision is None
                or revision.parent_revision.value != index - 1
            ):
                raise UniversalInstrumentIdentityValidationError(
                    "mapping history parent_revision must reference prior revision"
                )

    @property
    def latest_revision(self) -> ExternalIdentityMappingRevision:
        return self.revisions[-1]

    def logical_values(self) -> tuple[object, ...]:
        return (tuple(item.logical_values() for item in self.revisions),)
