from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

from qore.infrastructure.universal_instrument_identity import (
    EconomicIdentityId,
    ListingIdentity,
    MarketVenueCode,
)
from qore.kernel.errors import InfrastructureError


class UniversalMarketTopologyError(InfrastructureError):
    """Base error for provider-neutral market-topology semantics."""

    __slots__ = ()


class UniversalMarketTopologyValidationError(UniversalMarketTopologyError):
    """Violation of a universal market-topology invariant."""

    __slots__ = ()


def _validate_uuid(value: UUID, *, field_name: str) -> None:
    if type(value) is not UUID:
        raise UniversalMarketTopologyValidationError(f"{field_name} must be UUID")


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise UniversalMarketTopologyValidationError(f"{field_name} must be datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise UniversalMarketTopologyValidationError(
            f"{field_name} must be timezone-aware"
        )


def _canonical_timestamp(value: datetime, *, field_name: str) -> str:
    _validate_timestamp(value, field_name=field_name)
    return value.astimezone(UTC).isoformat(timespec="microseconds")


@dataclass(frozen=True, slots=True)
class MarketTopologyProfileId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="market topology profile id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class MarketFragmentationId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="market fragmentation id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class MarketTopologyEvidenceRef:
    """Opaque reference to retained topology evidence; never evidence content."""

    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="market topology evidence ref")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


class MarketInteractionMechanism(StrEnum):
    """Structural interaction mechanism; never live market state or execution policy."""

    CENTRAL_LIMIT_ORDER_BOOK = "central-limit-order-book"
    DEALER_RFQ = "dealer-rfq"
    QUOTE_DRIVEN = "quote-driven"
    AUCTION = "auction"
    BILATERAL = "bilateral"
    AUTOMATED_MARKET_MAKER = "automated-market-maker"


class MarketStage(StrEnum):
    """Structural issuance/trading stage; not listing identity or current session state."""

    PRIMARY = "primary"
    SECONDARY = "secondary"


class MarketTransparency(StrEnum):
    """Structural transparency qualification; not current liquidity visibility."""

    LIT = "lit"
    DARK = "dark"
    MIXED = "mixed"


class MarketInfrastructureContext(StrEnum):
    """Structural infrastructure context independent of interaction mechanism."""

    CENTRALIZED = "centralized"
    ON_CHAIN = "on-chain"
    HYBRID = "hybrid"


@dataclass(frozen=True, slots=True)
class MarketTopologyEffectiveInterval:
    effective_from: datetime
    effective_until: datetime | None = None

    def __post_init__(self) -> None:
        _validate_timestamp(self.effective_from, field_name="topology effective_from")
        if self.effective_until is not None:
            _validate_timestamp(
                self.effective_until,
                field_name="topology effective_until",
            )
            if self.effective_until <= self.effective_from:
                raise UniversalMarketTopologyValidationError(
                    "topology effective_until must be after effective_from"
                )

    def logical_values(self) -> tuple[str, str | None]:
        return (
            _canonical_timestamp(
                self.effective_from,
                field_name="topology effective_from",
            ),
            (
                _canonical_timestamp(
                    self.effective_until,
                    field_name="topology effective_until",
                )
                if self.effective_until is not None
                else None
            ),
        )


@dataclass(frozen=True, slots=True)
class EconomicMarketTopologyScope:
    """Economic-wide topology without asserting a listing or venue."""

    economic_identity_id: EconomicIdentityId

    def __post_init__(self) -> None:
        if not isinstance(self.economic_identity_id, EconomicIdentityId):
            raise UniversalMarketTopologyValidationError(
                "economic topology scope requires EconomicIdentityId"
            )

    def logical_values(self) -> tuple[object, ...]:
        return ("economic", self.economic_identity_id.logical_values())


@dataclass(frozen=True, slots=True)
class ListingMarketTopologyScope:
    """Topology of one exact retained UMI-02 listing identity."""

    listing: ListingIdentity

    def __post_init__(self) -> None:
        if not isinstance(self.listing, ListingIdentity):
            raise UniversalMarketTopologyValidationError(
                "listing topology scope requires exact ListingIdentity"
            )

    @property
    def economic_identity_id(self) -> EconomicIdentityId:
        return self.listing.economic_identity_id

    @property
    def venue(self) -> MarketVenueCode:
        return self.listing.venue

    def logical_values(self) -> tuple[object, ...]:
        return ("listing", self.listing.logical_values())


@dataclass(frozen=True, slots=True)
class VenueMarketTopologyScope:
    """Venue-wide topology without asserting one economic instrument."""

    venue: MarketVenueCode

    def __post_init__(self) -> None:
        if not isinstance(self.venue, MarketVenueCode):
            raise UniversalMarketTopologyValidationError(
                "venue topology scope requires MarketVenueCode"
            )

    def logical_values(self) -> tuple[object, ...]:
        return ("venue", self.venue.logical_values())


@dataclass(frozen=True, slots=True)
class EconomicVenueMarketTopologyScope:
    """Economic-at-venue topology without fabricating a ListingIdentity."""

    economic_identity_id: EconomicIdentityId
    venue: MarketVenueCode

    def __post_init__(self) -> None:
        if not isinstance(self.economic_identity_id, EconomicIdentityId):
            raise UniversalMarketTopologyValidationError(
                "economic-venue topology scope requires EconomicIdentityId"
            )
        if not isinstance(self.venue, MarketVenueCode):
            raise UniversalMarketTopologyValidationError(
                "economic-venue topology scope requires MarketVenueCode"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "economic-venue",
            self.economic_identity_id.logical_values(),
            self.venue.logical_values(),
        )


MarketTopologySubject = (
    EconomicMarketTopologyScope
    | ListingMarketTopologyScope
    | VenueMarketTopologyScope
    | EconomicVenueMarketTopologyScope
)

_MARKET_TOPOLOGY_SUBJECT_TYPES = (
    EconomicMarketTopologyScope,
    ListingMarketTopologyScope,
    VenueMarketTopologyScope,
    EconomicVenueMarketTopologyScope,
)


def _subject_economic_identity(
    subject: MarketTopologySubject,
) -> EconomicIdentityId | None:
    if isinstance(subject, EconomicMarketTopologyScope):
        return subject.economic_identity_id
    if isinstance(subject, ListingMarketTopologyScope):
        return subject.economic_identity_id
    if isinstance(subject, EconomicVenueMarketTopologyScope):
        return subject.economic_identity_id
    return None


def _subject_venue(subject: MarketTopologySubject) -> MarketVenueCode | None:
    if isinstance(subject, ListingMarketTopologyScope):
        return subject.venue
    if isinstance(subject, VenueMarketTopologyScope):
        return subject.venue
    if isinstance(subject, EconomicVenueMarketTopologyScope):
        return subject.venue
    return None


def _interval_contains(
    outer: MarketTopologyEffectiveInterval,
    inner: MarketTopologyEffectiveInterval,
) -> bool:
    if inner.effective_from < outer.effective_from:
        return False
    if outer.effective_until is None:
        return True
    if inner.effective_until is None:
        return False
    return inner.effective_until <= outer.effective_until


def _listing_interval(listing: ListingIdentity) -> MarketTopologyEffectiveInterval:
    return MarketTopologyEffectiveInterval(
        effective_from=listing.valid_from,
        effective_until=listing.valid_until,
    )


@dataclass(frozen=True, slots=True)
class MarketTopologyProfile:
    """Immutable static market-structure qualification; never live state or routing."""

    profile_id: MarketTopologyProfileId
    subject: MarketTopologySubject
    mechanisms: tuple[MarketInteractionMechanism, ...]
    effective_interval: MarketTopologyEffectiveInterval
    evidence_ref: MarketTopologyEvidenceRef
    stages: tuple[MarketStage, ...] = ()
    transparency: MarketTransparency | None = None
    infrastructure_context: MarketInfrastructureContext | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.profile_id, MarketTopologyProfileId):
            raise UniversalMarketTopologyValidationError(
                "topology profile_id must be MarketTopologyProfileId"
            )
        if not isinstance(self.subject, _MARKET_TOPOLOGY_SUBJECT_TYPES):
            raise UniversalMarketTopologyValidationError(
                "topology subject must be a supported typed topology scope"
            )
        if type(self.mechanisms) is not tuple or not self.mechanisms:
            raise UniversalMarketTopologyValidationError(
                "topology mechanisms must be a non-empty immutable tuple"
            )
        if any(
            not isinstance(item, MarketInteractionMechanism)
            for item in self.mechanisms
        ):
            raise UniversalMarketTopologyValidationError(
                "topology mechanisms must contain MarketInteractionMechanism"
            )
        if len(set(self.mechanisms)) != len(self.mechanisms):
            raise UniversalMarketTopologyValidationError(
                "topology mechanisms must be unique"
            )
        object.__setattr__(
            self,
            "mechanisms",
            tuple(sorted(self.mechanisms, key=lambda item: item.value)),
        )

        if not isinstance(self.effective_interval, MarketTopologyEffectiveInterval):
            raise UniversalMarketTopologyValidationError(
                "topology effective_interval must be MarketTopologyEffectiveInterval"
            )
        if not isinstance(self.evidence_ref, MarketTopologyEvidenceRef):
            raise UniversalMarketTopologyValidationError(
                "topology evidence_ref must be MarketTopologyEvidenceRef"
            )

        if type(self.stages) is not tuple:
            raise UniversalMarketTopologyValidationError(
                "topology stages must be an immutable tuple"
            )
        if any(not isinstance(item, MarketStage) for item in self.stages):
            raise UniversalMarketTopologyValidationError(
                "topology stages must contain MarketStage"
            )
        if len(set(self.stages)) != len(self.stages):
            raise UniversalMarketTopologyValidationError(
                "topology stages must be unique"
            )
        object.__setattr__(
            self,
            "stages",
            tuple(sorted(self.stages, key=lambda item: item.value)),
        )

        if self.transparency is not None and not isinstance(
            self.transparency,
            MarketTransparency,
        ):
            raise UniversalMarketTopologyValidationError(
                "topology transparency must be MarketTransparency or None"
            )
        if self.infrastructure_context is not None and not isinstance(
            self.infrastructure_context,
            MarketInfrastructureContext,
        ):
            raise UniversalMarketTopologyValidationError(
                "topology infrastructure_context must be "
                "MarketInfrastructureContext or None"
            )

        if isinstance(self.subject, ListingMarketTopologyScope):
            if not _interval_contains(
                _listing_interval(self.subject.listing),
                self.effective_interval,
            ):
                raise UniversalMarketTopologyValidationError(
                    "listing-scoped topology interval must stay within listing validity"
                )

    @property
    def economic_identity_id(self) -> EconomicIdentityId | None:
        return _subject_economic_identity(self.subject)

    @property
    def venue(self) -> MarketVenueCode | None:
        return _subject_venue(self.subject)

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.profile_id.logical_values(),
            self.subject.logical_values(),
            tuple(item.value for item in self.mechanisms),
            self.effective_interval.logical_values(),
            self.evidence_ref.logical_values(),
            tuple(item.value for item in self.stages),
            self.transparency.value if self.transparency is not None else None,
            (
                self.infrastructure_context.value
                if self.infrastructure_context is not None
                else None
            ),
        )


@dataclass(frozen=True, slots=True)
class FragmentedMarketTopology:
    """Multi-venue economic topology; deliberately contains no route-selection policy."""

    fragmentation_id: MarketFragmentationId
    economic_identity_id: EconomicIdentityId
    profiles: tuple[MarketTopologyProfile, ...]
    effective_interval: MarketTopologyEffectiveInterval
    evidence_ref: MarketTopologyEvidenceRef

    def __post_init__(self) -> None:
        if not isinstance(self.fragmentation_id, MarketFragmentationId):
            raise UniversalMarketTopologyValidationError(
                "fragmentation_id must be MarketFragmentationId"
            )
        if not isinstance(self.economic_identity_id, EconomicIdentityId):
            raise UniversalMarketTopologyValidationError(
                "fragmentation economic_identity_id must be EconomicIdentityId"
            )
        if type(self.profiles) is not tuple or len(self.profiles) < 2:
            raise UniversalMarketTopologyValidationError(
                "fragmented topology requires at least two topology profiles"
            )
        if any(not isinstance(item, MarketTopologyProfile) for item in self.profiles):
            raise UniversalMarketTopologyValidationError(
                "fragmented topology profiles must contain MarketTopologyProfile"
            )
        if not isinstance(self.effective_interval, MarketTopologyEffectiveInterval):
            raise UniversalMarketTopologyValidationError(
                "fragmentation effective_interval must be "
                "MarketTopologyEffectiveInterval"
            )
        if not isinstance(self.evidence_ref, MarketTopologyEvidenceRef):
            raise UniversalMarketTopologyValidationError(
                "fragmentation evidence_ref must be MarketTopologyEvidenceRef"
            )

        profile_ids = tuple(item.profile_id for item in self.profiles)
        if len(set(profile_ids)) != len(profile_ids):
            raise UniversalMarketTopologyValidationError(
                "fragmented topology profile identities must be unique"
            )

        venues: list[MarketVenueCode] = []
        for profile in self.profiles:
            if profile.economic_identity_id != self.economic_identity_id:
                raise UniversalMarketTopologyValidationError(
                    "fragmented topology profile must bind exact economic identity"
                )
            if profile.venue is None:
                raise UniversalMarketTopologyValidationError(
                    "fragmented topology requires venue-qualified component profiles"
                )
            if not _interval_contains(
                profile.effective_interval,
                self.effective_interval,
            ):
                raise UniversalMarketTopologyValidationError(
                    "fragmentation interval must be covered by every component profile"
                )
            venues.append(profile.venue)

        if len(set(venues)) < 2:
            raise UniversalMarketTopologyValidationError(
                "fragmented topology requires at least two distinct venues"
            )

        object.__setattr__(
            self,
            "profiles",
            tuple(
                sorted(
                    self.profiles,
                    key=lambda item: (
                        item.venue.value if item.venue is not None else "",
                        str(item.profile_id.value),
                    ),
                )
            ),
        )

    @property
    def venues(self) -> tuple[MarketVenueCode, ...]:
        unique = {item.venue for item in self.profiles if item.venue is not None}
        return tuple(sorted(unique, key=lambda item: item.value))

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.fragmentation_id.logical_values(),
            self.economic_identity_id.logical_values(),
            tuple(item.logical_values() for item in self.profiles),
            self.effective_interval.logical_values(),
            self.evidence_ref.logical_values(),
        )
