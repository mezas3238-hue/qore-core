from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any, cast
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


def _u(value: int) -> UUID:
    return UUID(int=value)


def _ev(value: int) -> IdentityEvidenceRef:
    return IdentityEvidenceRef(_u(10_000 + value))


def _identity(value: int) -> EconomicIdentity:
    return EconomicIdentity(
        EconomicIdentityId(_u(value)),
        EconomicIdentityKind.TRADABLE_INSTRUMENT,
        IdentityFamilyCode("equity"),
        IdentityConstructionKind.NATIVE,
        _ev(value),
    )


def _listing(value: int, parent: EconomicIdentity) -> ListingIdentity:
    return ListingIdentity(
        ListingIdentityId(_u(1_000 + value)),
        parent.identity_id,
        MarketVenueCode("xnas"),
        f"SYM{value}",
        _T0,
        None,
        _ev(1_000 + value),
    )


def _external(symbol: str = "AAPL") -> ExternalIdentifier:
    return ExternalIdentifier(
        ExternalIdentifierKind.LEGACY_QORE,
        ExternalIdentifierNamespace("legacy.symbol"),
        ExternalIdentifierValue(symbol),
    )


def _relation(
    value: int,
    source: EconomicIdentity,
    target: EconomicIdentity,
) -> IdentityRelationship:
    return IdentityRelationship(
        IdentityRelationshipId(_u(2_000 + value)),
        source.identity_id,
        target.identity_id,
        IdentityRelationshipCode("underlying"),
        _T0,
        None,
        _ev(2_000 + value),
    )


def _event(value: int, subject: CanonicalIdentityRef) -> IdentityLifecycleEvent:
    return IdentityLifecycleEvent(
        IdentityLifecycleEventId(_u(3_000 + value)),
        subject,
        LifecycleEventCode("listing.start"),
        _T0,
        _T0,
        _ev(3_000 + value),
    )


def _mapping(
    value: int,
    target: CanonicalIdentityRef,
    *,
    external: ExternalIdentifier | None = None,
) -> ExternalIdentityMappingRevision:
    return ExternalIdentityMappingRevision(
        IdentityMappingId(_u(4_000 + value)),
        IdentityMappingRevision(1),
        None,
        external or _external(),
        target,
        _T0,
        None,
        _T0,
        _ev(4_000 + value),
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
def test_id_wrappers_are_strict(factory: Callable[[UUID], Any]) -> None:
    assert factory(_u(1)).logical_values() == (str(_u(1)),)
    with pytest.raises(UniversalInstrumentIdentityValidationError):
        factory(cast(UUID, "bad"))


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
def test_code_wrappers_are_strict(factory: Callable[[str], Any]) -> None:
    assert factory("valid.code").logical_values() == ("valid.code",)
    with pytest.raises(UniversalInstrumentIdentityValidationError):
        factory("INVALID CODE")


def test_public_identifier_text_guards() -> None:
    for invalid in ("", " padded ", "A\nB", "X" * 257):
        with pytest.raises(UniversalInstrumentIdentityValidationError):
            ExternalIdentifierValue(invalid)


def test_listing_fail_closed_guards() -> None:
    listing = _listing(1, _identity(1))
    for field in ("listing_id", "economic_identity_id", "venue", "evidence_ref"):
        with pytest.raises(UniversalInstrumentIdentityValidationError):
            replace(listing, **{field: cast(Any, "bad")})
    with pytest.raises(UniversalInstrumentIdentityValidationError):
        replace(listing, valid_from=cast(datetime, "bad"))
    with pytest.raises(UniversalInstrumentIdentityValidationError):
        replace(listing, valid_until=datetime(2026, 1, 2))


def test_external_identifier_runtime_guards() -> None:
    base = _external()
    for field in ("kind", "namespace", "value", "source", "venue"):
        with pytest.raises(UniversalInstrumentIdentityValidationError):
            replace(base, **{field: cast(Any, "bad")})


def test_relationship_fail_closed_guards() -> None:
    relation = _relation(1, _identity(10), _identity(11))
    for field in (
        "relationship_id",
        "source_identity_id",
        "target_identity_id",
        "relationship",
        "evidence_ref",
    ):
        with pytest.raises(UniversalInstrumentIdentityValidationError):
            replace(relation, **{field: cast(Any, "bad")})
    with pytest.raises(UniversalInstrumentIdentityValidationError):
        replace(relation, effective_from=cast(datetime, "bad"))
    with pytest.raises(UniversalInstrumentIdentityValidationError):
        replace(relation, effective_until=datetime(2026, 1, 2))
    with pytest.raises(UniversalInstrumentIdentityValidationError):
        replace(relation, effective_until=_T0)


def test_lifecycle_fail_closed_guards() -> None:
    event = _event(1, CanonicalIdentityRef(_identity(20).identity_id))
    for field in ("event_id", "subject", "event_type", "evidence_ref"):
        with pytest.raises(UniversalInstrumentIdentityValidationError):
            replace(event, **{field: cast(Any, "bad")})
    with pytest.raises(UniversalInstrumentIdentityValidationError):
        replace(event, effective_at=cast(datetime, "bad"))
    with pytest.raises(UniversalInstrumentIdentityValidationError):
        replace(event, recorded_at=datetime(2026, 1, 2))


def test_mapping_revision_fail_closed_guards() -> None:
    mapping = _mapping(1, CanonicalIdentityRef(_identity(30).identity_id))
    for field in (
        "mapping_id",
        "revision",
        "parent_revision",
        "external_identity",
        "target",
        "evidence_ref",
    ):
        with pytest.raises(UniversalInstrumentIdentityValidationError):
            replace(mapping, **{field: cast(Any, "bad")})
    with pytest.raises(UniversalInstrumentIdentityValidationError):
        replace(mapping, parent_revision=IdentityMappingRevision(1))
    with pytest.raises(UniversalInstrumentIdentityValidationError):
        replace(mapping, effective_from=cast(datetime, "bad"))
    with pytest.raises(UniversalInstrumentIdentityValidationError):
        replace(mapping, effective_until=datetime(2026, 1, 2))
    with pytest.raises(UniversalInstrumentIdentityValidationError):
        replace(mapping, effective_until=_T0)
    with pytest.raises(UniversalInstrumentIdentityValidationError):
        replace(mapping, recorded_at=datetime(2026, 1, 2))

    later = replace(
        mapping,
        revision=IdentityMappingRevision(2),
        parent_revision=IdentityMappingRevision(1),
        recorded_at=_T1,
    )
    with pytest.raises(UniversalInstrumentIdentityValidationError):
        replace(later, parent_revision=None)
    with pytest.raises(UniversalInstrumentIdentityValidationError):
        replace(later, parent_revision=IdentityMappingRevision(2))


def test_mapping_history_container_and_mapping_id_guards() -> None:
    first = _mapping(10, CanonicalIdentityRef(_identity(40).identity_id))
    with pytest.raises(UniversalInstrumentIdentityValidationError):
        IdentityMappingHistory(())
    with pytest.raises(UniversalInstrumentIdentityValidationError):
        IdentityMappingHistory((cast(ExternalIdentityMappingRevision, "bad"),))

    second = replace(
        first,
        revision=IdentityMappingRevision(2),
        parent_revision=IdentityMappingRevision(1),
        recorded_at=_T1,
    )
    with pytest.raises(UniversalInstrumentIdentityValidationError):
        IdentityMappingHistory(
            (first, replace(second, mapping_id=IdentityMappingId(_u(9_999))))
        )


def test_graph_collection_and_duplicate_guards() -> None:
    identity = _identity(50)
    with pytest.raises(UniversalInstrumentIdentityValidationError):
        UniversalInstrumentIdentityGraph(())
    with pytest.raises(UniversalInstrumentIdentityValidationError):
        UniversalInstrumentIdentityGraph((cast(EconomicIdentity, "bad"),))
    with pytest.raises(UniversalInstrumentIdentityValidationError):
        UniversalInstrumentIdentityGraph((identity,), (cast(ListingIdentity, "bad"),))
    with pytest.raises(UniversalInstrumentIdentityValidationError):
        UniversalInstrumentIdentityGraph(
            (identity,), relationships=(cast(IdentityRelationship, "bad"),)
        )
    with pytest.raises(UniversalInstrumentIdentityValidationError):
        UniversalInstrumentIdentityGraph(
            (identity,), lifecycle_events=(cast(IdentityLifecycleEvent, "bad"),)
        )
    with pytest.raises(UniversalInstrumentIdentityValidationError):
        UniversalInstrumentIdentityGraph(
            (identity,), mapping_histories=(cast(IdentityMappingHistory, "bad"),)
        )
    with pytest.raises(UniversalInstrumentIdentityValidationError):
        UniversalInstrumentIdentityGraph((identity, identity))


def test_graph_rejects_dangling_and_duplicate_facts() -> None:
    first = _identity(60)
    second = _identity(61)
    listing = _listing(2, first)
    with pytest.raises(UniversalInstrumentIdentityValidationError):
        UniversalInstrumentIdentityGraph((first,), (listing, listing))
    with pytest.raises(UniversalInstrumentIdentityValidationError):
        UniversalInstrumentIdentityGraph(
            (first,),
            (replace(listing, economic_identity_id=EconomicIdentityId(_u(90_001))),),
        )

    relation = _relation(2, first, second)
    with pytest.raises(UniversalInstrumentIdentityValidationError):
        UniversalInstrumentIdentityGraph(
            (first, second),
            relationships=(relation, replace(relation, target_identity_id=first.identity_id)),
        )

    event = _event(2, CanonicalIdentityRef(first.identity_id))
    with pytest.raises(UniversalInstrumentIdentityValidationError):
        UniversalInstrumentIdentityGraph((first,), lifecycle_events=(event, event))
    with pytest.raises(UniversalInstrumentIdentityValidationError):
        UniversalInstrumentIdentityGraph(
            (first,),
            lifecycle_events=(
                replace(event, subject=CanonicalIdentityRef(ListingIdentityId(_u(90_002)))),
            ),
        )


def test_graph_listing_mapping_target_and_mapping_conflicts() -> None:
    identity = _identity(70)
    listing = _listing(3, identity)
    target = CanonicalIdentityRef(listing.listing_id)
    first = IdentityMappingHistory((_mapping(20, target),))
    graph = UniversalInstrumentIdentityGraph(
        (identity,), (listing,), mapping_histories=(first,)
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
    with pytest.raises(UniversalInstrumentIdentityValidationError):
        UniversalInstrumentIdentityGraph(
            (identity,), (listing,), mapping_histories=(first, same_mapping_id)
        )

    dangling = IdentityMappingHistory(
        (
            _mapping(
                22,
                CanonicalIdentityRef(ListingIdentityId(_u(90_003))),
                external=_external("TSLA"),
            ),
        )
    )
    with pytest.raises(UniversalInstrumentIdentityValidationError):
        UniversalInstrumentIdentityGraph((identity,), mapping_histories=(dangling,))
