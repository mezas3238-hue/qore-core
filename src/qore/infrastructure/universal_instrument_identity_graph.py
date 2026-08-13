from __future__ import annotations

from dataclasses import dataclass

from qore.infrastructure.universal_instrument_identity import (
    CanonicalIdentityRef,
    EconomicIdentity,
    EconomicIdentityId,
    ExternalIdentifier,
    IdentityLifecycleEvent,
    IdentityMappingHistory,
    IdentityRelationship,
    ListingIdentity,
    ListingIdentityId,
    UniversalInstrumentIdentityValidationError,
)


def _identity_ref_exists(
    reference: CanonicalIdentityRef,
    *,
    economic_ids: frozenset[EconomicIdentityId],
    listing_ids: frozenset[ListingIdentityId],
) -> bool:
    value = reference.value
    if isinstance(value, EconomicIdentityId):
        return value in economic_ids
    return value in listing_ids


@dataclass(frozen=True, slots=True)
class UniversalInstrumentIdentityGraph:
    """Canonical identity graph with deterministic order and referential integrity."""

    economic_identities: tuple[EconomicIdentity, ...]
    listings: tuple[ListingIdentity, ...] = ()
    relationships: tuple[IdentityRelationship, ...] = ()
    lifecycle_events: tuple[IdentityLifecycleEvent, ...] = ()
    mapping_histories: tuple[IdentityMappingHistory, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.economic_identities, tuple) or not self.economic_identities:
            raise UniversalInstrumentIdentityValidationError(
                "identity graph economic_identities must be a non-empty immutable tuple"
            )
        if any(
            not isinstance(item, EconomicIdentity) for item in self.economic_identities
        ):
            raise UniversalInstrumentIdentityValidationError(
                "identity graph economic_identities must contain EconomicIdentity values"
            )
        if not isinstance(self.listings, tuple) or any(
            not isinstance(item, ListingIdentity) for item in self.listings
        ):
            raise UniversalInstrumentIdentityValidationError(
                "identity graph listings must be an immutable ListingIdentity tuple"
            )
        if not isinstance(self.relationships, tuple) or any(
            not isinstance(item, IdentityRelationship) for item in self.relationships
        ):
            raise UniversalInstrumentIdentityValidationError(
                "identity graph relationships must be an immutable IdentityRelationship tuple"
            )
        if not isinstance(self.lifecycle_events, tuple) or any(
            not isinstance(item, IdentityLifecycleEvent)
            for item in self.lifecycle_events
        ):
            raise UniversalInstrumentIdentityValidationError(
                "identity graph lifecycle_events must be an immutable IdentityLifecycleEvent tuple"
            )
        if not isinstance(self.mapping_histories, tuple) or any(
            not isinstance(item, IdentityMappingHistory)
            for item in self.mapping_histories
        ):
            raise UniversalInstrumentIdentityValidationError(
                "identity graph mapping_histories must be an immutable IdentityMappingHistory tuple"
            )

        economic_ids = tuple(item.identity_id for item in self.economic_identities)
        if len(set(economic_ids)) != len(economic_ids):
            raise UniversalInstrumentIdentityValidationError(
                "identity graph economic identity ids must be unique"
            )
        economic_id_set = frozenset(economic_ids)

        listing_ids = tuple(item.listing_id for item in self.listings)
        if len(set(listing_ids)) != len(listing_ids):
            raise UniversalInstrumentIdentityValidationError(
                "identity graph listing ids must be unique"
            )
        listing_id_set = frozenset(listing_ids)
        for listing in self.listings:
            if listing.economic_identity_id not in economic_id_set:
                raise UniversalInstrumentIdentityValidationError(
                    "identity graph listing must reference a retained economic identity"
                )

        relationship_ids = tuple(
            item.relationship_id for item in self.relationships
        )
        if len(set(relationship_ids)) != len(relationship_ids):
            raise UniversalInstrumentIdentityValidationError(
                "identity graph relationship ids must be unique"
            )
        ordered_component_keys: set[tuple[object, ...]] = set()
        for relationship in self.relationships:
            if (
                relationship.source_identity_id not in economic_id_set
                or relationship.target_identity_id not in economic_id_set
            ):
                raise UniversalInstrumentIdentityValidationError(
                    "identity graph relationship endpoints must be retained economic identities"
                )
            if relationship.ordinal is not None:
                component_key = (
                    relationship.source_identity_id,
                    relationship.relationship,
                    relationship.effective_from,
                    relationship.effective_until,
                    relationship.ordinal,
                )
                if component_key in ordered_component_keys:
                    raise UniversalInstrumentIdentityValidationError(
                        "identity graph ordered relationship ordinal must be unique within scope"
                    )
                ordered_component_keys.add(component_key)

        lifecycle_ids = tuple(item.event_id for item in self.lifecycle_events)
        if len(set(lifecycle_ids)) != len(lifecycle_ids):
            raise UniversalInstrumentIdentityValidationError(
                "identity graph lifecycle event ids must be unique"
            )
        for event in self.lifecycle_events:
            if not _identity_ref_exists(
                event.subject,
                economic_ids=economic_id_set,
                listing_ids=listing_id_set,
            ):
                raise UniversalInstrumentIdentityValidationError(
                    "identity graph lifecycle subject must reference a retained identity"
                )

        mapping_ids = tuple(
            item.revisions[0].mapping_id for item in self.mapping_histories
        )
        if len(set(mapping_ids)) != len(mapping_ids):
            raise UniversalInstrumentIdentityValidationError(
                "identity graph mapping ids must be unique"
            )
        external_identities: tuple[ExternalIdentifier, ...] = tuple(
            item.revisions[0].external_identity for item in self.mapping_histories
        )
        if len(set(external_identities)) != len(external_identities):
            raise UniversalInstrumentIdentityValidationError(
                "identity graph external identity may have only one retained mapping history"
            )
        for history in self.mapping_histories:
            previous_recorded_at = None
            for revision in history.revisions:
                if not _identity_ref_exists(
                    revision.target,
                    economic_ids=economic_id_set,
                    listing_ids=listing_id_set,
                ):
                    raise UniversalInstrumentIdentityValidationError(
                        "identity graph mapping target must reference a retained identity"
                    )
                if (
                    previous_recorded_at is not None
                    and revision.recorded_at <= previous_recorded_at
                ):
                    raise UniversalInstrumentIdentityValidationError(
                        "identity graph mapping revisions must have increasing recorded_at"
                    )
                previous_recorded_at = revision.recorded_at

        object.__setattr__(
            self,
            "economic_identities",
            tuple(
                sorted(
                    self.economic_identities,
                    key=lambda item: str(item.identity_id.value),
                )
            ),
        )
        object.__setattr__(
            self,
            "listings",
            tuple(sorted(self.listings, key=lambda item: str(item.listing_id.value))),
        )
        object.__setattr__(
            self,
            "relationships",
            tuple(
                sorted(
                    self.relationships,
                    key=lambda item: str(item.relationship_id.value),
                )
            ),
        )
        object.__setattr__(
            self,
            "lifecycle_events",
            tuple(
                sorted(
                    self.lifecycle_events,
                    key=lambda item: str(item.event_id.value),
                )
            ),
        )
        object.__setattr__(
            self,
            "mapping_histories",
            tuple(
                sorted(
                    self.mapping_histories,
                    key=lambda item: str(item.revisions[0].mapping_id.value),
                )
            ),
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            tuple(item.logical_values() for item in self.economic_identities),
            tuple(item.logical_values() for item in self.listings),
            tuple(item.logical_values() for item in self.relationships),
            tuple(item.logical_values() for item in self.lifecycle_events),
            tuple(item.logical_values() for item in self.mapping_histories),
        )
