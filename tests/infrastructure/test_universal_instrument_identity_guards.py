from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from typing import Any, Callable, cast
from uuid import UUID

import pytest

from qore.infrastructure.universal_instrument_identity import (
    CanonicalIdentityRef,
    EconomicIdentity,
    EconomicIdentityId,
    EconomicIdentityKind,
    ExternalIdentifier,
    ExternalIdentifierKind,
    ExternalIdentifierNamespace,
    ExternalIdentifierValue,
    ExternalIdentityMappingRevision,
    IdentityConstructionKind,
    IdentityEvidenceRef,
    IdentityFamilyCode,
    IdentityLifecycleEvent,
    IdentityLifecycleEventId,
    IdentityMappingHistory,
    IdentityMappingId,
    IdentityMappingRevision,
    IdentityRelationship,
    IdentityRelationshipCode,
    IdentityRelationshipId,
    LifecycleEventCode,
    ListingIdentity,
    ListingIdentityId,
    MarketVenueCode,
    UniversalInstrumentIdentityValidationError,
)
from qore.infrastructure.universal_instrument_identity_graph import (
    UniversalInstrumentIdentityGraph,
)

_T0 = datetime(2026, 1, 1, tzinfo=UTC)
_T1 = datetime(2026, 2, 1, tzinfo=UTC)


def _uuid(value: int) -> UUID:
    return UUID(int=value)


def _evidence(value: int) -> IdentityEvidenceRef:
    return IdentityEvidenceRef(_uuid(10_000 + value))


def _identity(value: int) -> EconomicIdentity:
    return EconomicIdentity(
        identity_id=EconomicIdentityId(_uuid(value)),
        kind=EconomicIdentityKind.TRADABLE_INSTRUMENT,
        family=IdentityFamilyCode("equity"),
        construction=IdentityConstructionKind.NATIVE,
        evidence_ref=_evidence(value),
    )


def _listing(value: int, parent: EconomicIdentity) -> ListingIdentity:
    return ListingIdentity(
        listing_id=ListingIdentityId(_uuid(1_000 + value)),
        economic_identity_id=parent.identity_id,
        venue=MarketVenueCode("xnas"),
        display_symbol=f"SYM{value}",
        valid_from=_T0,
        valid_until=None,
        evidence_ref=_evidence(1_000 + value),
    )


def _relationship(
    value: int,
    source: EconomicIdentity,
    target: EconomicIdentity,
) -> IdentityRelationship:
    return IdentityRelationship(
        relationship_id=IdentityRelationshipId(_uuid(2_000 + value)),
        source_identity_id=source.identity_id,
        target_identity_id=target.identity_id,
        relationship=IdentityRelationshipCode("underlying"),
        effective_from=_T0,
        effective_until=None,
        evidence_ref=_evidence(2_000 + value),
    )


def _event(value: int, subject: CanonicalIdentityRef) -> IdentityLifecycleEvent:
    return IdentityLifecycleEvent(
        event_id=IdentityLifecycleEventId(_uuid(3_000 + value)),
        subject=subject,
        event_type=LifecycleEventCode("listing.start"),
        effective_at=_T0,
        recorded_at=_T0,
        evidence_ref=_evidence(3_000 + value),
    )


def _external(symbol: str = "AAPL") -> ExternalIdentifier:
    return ExternalIdentifier(
        kind=ExternalIdentifierKind.LEGACY_QORE,
        namespace=ExternalIdentifierNamespace("market-data.instrument"),
        value=ExternalIdentifierValue(symbol),
    )


def _mapping(
    value: int,
    target: CanonicalIdentityRef,
    *,
    external: ExternalIdentifier | None = None,
) -> ExternalIdentityMappingRevision:
    return ExternalIdentityMappingRevision(
        mapping_id=IdentityMappingId(_uuid(4_000 + value)),
        revision=IdentityMappingRevision(1),
        parent_revision=None,
        external_identity=external or _external(),
        target=target,
        effective_from=_T0,
        effective_until=None,
        recorded_at=_T0,
        evidence_ref=_evidence(4_000 + value),
    )


@pytest.mark.parametrize(
    "factory",
    (
        EconomicIdentityId,
        ListingIdentityId,
        IdentityRelationshipId,
        IdentityLifecycleEventId,
        IdentityMappingId,
        IdentityEvidenceRef,
    ),
)
def test_uuid_wrappers_reject_non_uuid_and_emit_logical_value(
    factory: Callable[[UUID], Any],
) -> None:
    value = _uuid(1)
    assert factory(value).logical_values() == (str(value),)
    with pytest.raises(
        UniversalInstrumentIdentityValidationError,
        match="must be UUID",
    ):
        factory(cast(UUID, "not-uuid"))


@pytest.mark.parametrize(
    "factory",
    (
        IdentityFamilyCode,
        MarketVenueCode,
        ExternalIdentifierNamespace,
        IdentityRelationshipCode,
        LifecycleEventCode,
    ),
)
def test_code_wrappers_reject_noncanonical_text(
    factory: Callable[[str], Any],
) -> None:
    assert factory("valid.code-1").logical_values() == ("valid.code-1",)
    with pytest.raises(
        UniversalInstrumentIdentityValidationError,
        match="canonical lowercase code syntax",
    ):
        factory("INVALID CODE")


def test_external_identifier_value_rejects_bad_public_text() -> None:
    for invalid in ("", " padded ", "A\nB", "X" * 257):
        with pytest.raises(
            UniversalInstrumentIdentityValidationError,
            match="non-empty trimmed text",
        ):
            ExternalIdentifierValue(invalid)


def test_listing_runtime_type_and_time_guards() -> None:
    listing = _listing(1, _identity(1))
    for field, bad in (
        ("listing_id", "bad"),
        ("economic_identity_id", "bad"),
        ("venue", "bad"),
        ("evidence_ref", "bad"),
    ):
        with pytest.raises(UniversalInstrumentIdentityValidationError):
            replace(listing, **{field: cast(Any, bad)})

    with pytest.raises(
        UniversalInstrumentIdentityValidationError,
        match="must be datetime",
    ):
        replace(listing, valid_from=cast(datetime, "bad"))
    with pytest.raises(
        UniversalInstrumentIdentityValidationError,
        match="timezone-aware",
    ):
        replace(listing, valid_until=datetime(2026, 1, 2))


def test_relationship_runtime_type_time_and_interval_guards() -> None:
    relation = _relationship(1, _identity(10), _identity(11))
    for field, bad in (
        ("relationship_id", "bad"),
        ("source_identity_id", "bad"),
        ("target_identity_id", "bad"),
        ("relationship", "bad"),
        ("evidence_ref", "bad"),
    ):
        with pytest.raises(UniversalInstrumentIdentityValidationError):
            replace(relation, **{field: cast(Any, bad)})

    with pytest.raises(UniversalInstrumentIdentityValidationError):
        replace(relation, effective_from=cast(datetime, "bad"))
    with pytest.raises(UniversalInstrumentIdentityValidationError):
        replace(relation, effective_until=datetime(2026, 1, 2))
    with pytest.raises(
        UniversalInstrumentIdentityValidationError,
        match="after effective_from",
    ):
        replace(relation, effective_until=_T0)


def test_lifecycle_runtime_type_and_timestamp_guards() -> None:
    event = _event(1, CanonicalIdentityRef(_identity(20).identity_id))
    for field, bad in (
        ("event_id", "bad"),
        ("subject", "bad"),
        ("event_type", "bad"),
        ("evidence_ref", "bad"),
    ):
        with pytest.raises(UniversalInstrumentIdentityValidationError):
            replace(event, **{field: cast(Any, bad)})

    with pytest.raises(UniversalInstrumentIdentityValidationError):
        replace(event, effective_at=cast(datetime, "bad"))
    with pytest.raises(UniversalInstrumentIdentityValidationError):
        replace(event, recorded_at=datetime(2026, 1, 2))


def test_mapping_revision_runtime_type_parent_and_time_guards() -> None:
    mapping = _mapping(1, CanonicalIdentityRef(_identity(30).identity_id))
    for field, bad in (
        ("mapping_id", "bad"),
        ("revision", "bad"),
        ("parent_revision", "bad"),
        ("external_identity", "bad"),
        ("target", "bad"),
        ("evidence_ref", "bad"),
    ):
        with pytest.raises(UniversalInstrumentIdentityValidationError):
            replace(mapping, **{field: cast(Any, bad)})

    with pytest.raises(
        UniversalInstrumentIdentityValidationError,
        match="first mapping revision",
    ):
        replace(mapping, parent_revision=IdentityMappingRevision(1))
    with pytest.raises(UniversalInstrumentIdentityValidationError):
        replace(mapping, effective_from=cast(datetime, "bad"))
    with pytest.raises(UniversalInstrumentIdentityValidationError):
        replace(mapping, effective_until=datetime(2026, 1, 2))
    with pytest.raises(
        UniversalInstrumentIdentityValidationError,
        match="after effective_from",
    ):
        replace(mapping, effective_until=_T0)
    with pytest.raises(UniversalInstrumentIdentityValidationError):
        replace(mapping, recorded_at=datetime(2026, 1, 2))

    later = replace(
        mapping,
        revision=IdentityMappingRevision(2),
        parent_revision=IdentityMappingRevision(1),
        recorded_at=_T1,
    )
    with pytest.raises(
        UniversalInstrumentIdentityValidationError,
        match="later mapping revision",
    ):
        replace(later, parent_revision=None)
    with pytest.raises(
        UniversalInstrumentIdentityValidationError,
        match="earlier parent_revision",
    ):
        replace(later, parent_revision=IdentityMappingRevision(2))


def test_mapping_history_rejects_container_mapping_and_parent_defects() -> None:
    target = CanonicalIdentityRef(_identity(40).identity_id)
    first = _mapping(10, target)

    with pytest.raises(
        UniversalInstrumentIdentityValidationError,
        match="non-empty immutable tuple",
    ):
        IdentityMappingHistory(cast(tuple[ExternalIdentityMappingRevision, ...], ()))
    with pytest.raises(
        UniversalInstrumentIdentityValidationError,
        match="non-empty immutable tuple",
    ):
        IdentityMappingHistory((cast(ExternalIdentityMappingRevision, "bad"),))

    second = replace(
        first,
        revision=IdentityMappingRevision(2),
        parent_revision=IdentityMappingRevision(1),
        recorded_at=_T1,
    )
    wrong_mapping = replace(
        second,
        mapping_id=IdentityMappingId(_uuid(9_999)),
    )
    with pytest.raises(
        UniversalInstrumentIdentityValidationError,
        match="one mapping_id",
    ):
        IdentityMappingHistory((first, wrong_mapping))

    wrong_parent = replace(
        second,
        parent_revision=IdentityMappingRevision(1),
    )
    assert IdentityMappingHistory((first, wrong_parent)).latest_revision == wrong_parent


def test_graph_rejects_collection_shapes_and_duplicate_economic_identity() -> None:
    identity = _identity(50)
    with pytest.raises(UniversalInstrumentIdentityValidationError):
        UniversalInstrumentIdentityGraph(
            economic_identities=cast(tuple[EconomicIdentity, ...], ()),
        )
    with pytest.raises(UniversalInstrumentIdentityValidationError):
        UniversalInstrumentIdentityGraph(
            economic_identities=(cast(EconomicIdentity, "bad"),),
        )
    with pytest.raises(UniversalInstrumentIdentityValidationError):
        UniversalInstrumentIdentityGraph(
            economic_identities=(identity,),
            listings=(cast(ListingIdentity, "bad"),),
        )
    with pytest.raises(UniversalInstrumentIdentityValidationError):
        UniversalInstrumentIdentityGraph(
            economic_identities=(identity,),
            relationships=(cast(IdentityRelationship, "bad"),),
        )
    with pytest.raises(UniversalInstrumentIdentityValidationError):
        UniversalInstrumentIdentityGraph(
            economic_identities=(identity,),
            lifecycle_events=(cast(IdentityLifecycleEvent, "bad"),),
        )
    with pytest.raises(UniversalInstrumentIdentityValidationError):
        UniversalInstrumentIdentityGraph(
            economic_identities=(identity,),
            mapping_histories=(cast(IdentityMappingHistory, "bad"),),
        )
    with pytest.raises(
        UniversalInstrumentIdentityValidationError,
        match="economic identity ids must be unique",
    ):
        UniversalInstrumentIdentityGraph(economic_identities=(identity, identity))


def test_graph_rejects_duplicate_and_dangling_listing_relationship_lifecycle() -> None:
    first = _identity(60)
    second = _identity(61)
    listing = _listing(2, first)

    with pytest.raises(
        UniversalInstrumentIdentityValidationError,
        match="listing ids must be unique",
    ):
        UniversalInstrumentIdentityGraph(
            economic_identities=(first,),
            listings=(listing, listing),
        )

    dangling_listing = replace(
        listing,
        economic_identity_id=EconomicIdentityId(_uuid(90_001)),
    )
    with pytest.raises(
        UniversalInstrumentIdentityValidationError,
        match="listing must reference",
    ):
        UniversalInstrumentIdentityGraph(
            economic_identities=(first,),
            listings=(dangling_listing,),
        )

    relation = _relationship(2, first, second)
    duplicate_relation = replace(relation, target_identity_id=first.identity_id)
    with pytest.raises(
        UniversalInstrumentIdentityValidationError,
        match="relationship ids must be unique",
    ):
        UniversalInstrumentIdentityGraph(
            economic_identities=(first, second),
            relationships=(relation, duplicate_relation),
        )

    event = _event(2, CanonicalIdentityRef(first.identity_id))
    with pytest.raises(
        UniversalInstrumentIdentityValidationError,
        match="lifecycle event ids must be unique",
    ):
        UniversalInstrumentIdentityGraph(
            economic_identities=(first,),
            lifecycle_events=(event, event),
        )

    dangling_event = replace(
        event,
        subject=CanonicalIdentityRef(ListingIdentityId(_uuid(90_002))),
    )
    with pytest.raises(
        UniversalInstrumentIdentityValidationError,
        match="lifecycle subject",
    ):
        UniversalInstrumentIdentityGraph(
            economic_identities=(first,),
            lifecycle_events=(dangling_event,),
        )


def test_graph_accepts_listing_mapping_target_and_rejects_mapping_conflicts() -> None:
    identity = _identity(70)
    listing = _listing(3, identity)
    target = CanonicalIdentityRef(listing.listing_id)
    first = IdentityMappingHistory((_mapping(20, target),))

    graph = UniversalInstrumentIdentityGraph(
        economic_identities=(identity,),
        listings=(listing,),
        mapping_histories=(first,),
    )
    assert graph.mapping_histories == (first,)

    same_mapping_id = IdentityMappingHistory(
        (
            replace(
                _mapping(21, target, external=_external("MSFT")),
                mapping_id=first.revisions[0].mapping_id,
            ),
        )
    )
    with pytest.raises(
        UniversalInstrumentIdentityValidationError,
        match="mapping ids must be unique",
    ):
        UniversalInstrumentIdentityGraph(
            economic_identities=(identity,),
            listings=(listing,),
            mapping_histories=(first, same_mapping_id),
        )

    dangling = IdentityMappingHistory(
        (
            _mapping(
                22,
                CanonicalIdentityRef(ListingIdentityId(_uuid(90_003))),
                external=_external("TSLA"),
            ),
        )
    )
    with pytest.raises(
        UniversalInstrumentIdentityValidationError,
        match="mapping target",
    ):
        UniversalInstrumentIdentityGraph(
            economic_identities=(identity,),
            mapping_histories=(dangling,),
        )
