from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID

import pytest

from qore.infrastructure.ports import AdapterId, ExternalSourceDescriptor, PortName, SourceId
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
from qore.infrastructure.universal_instrument_identity_graph import UniversalInstrumentIdentityGraph

_T0 = datetime(2026, 1, 1, tzinfo=UTC)
_T1 = datetime(2026, 3, 1, tzinfo=UTC)
_T2 = datetime(2026, 6, 1, tzinfo=UTC)
_T3 = datetime(2026, 9, 1, tzinfo=UTC)


def _uuid(value: int) -> UUID:
    return UUID(int=value)


def _evidence(value: int) -> IdentityEvidenceRef:
    return IdentityEvidenceRef(_uuid(10_000 + value))


def _identity(
    value: int,
    *,
    family: str = "equity",
    kind: EconomicIdentityKind = EconomicIdentityKind.TRADABLE_INSTRUMENT,
    construction: IdentityConstructionKind = IdentityConstructionKind.NATIVE,
) -> EconomicIdentity:
    return EconomicIdentity(
        identity_id=EconomicIdentityId(_uuid(value)),
        kind=kind,
        family=IdentityFamilyCode(family),
        construction=construction,
        evidence_ref=_evidence(value),
    )


def _source() -> ExternalSourceDescriptor:
    return ExternalSourceDescriptor(
        adapter_id=AdapterId(_uuid(20_001)),
        source_id=SourceId(_uuid(30_001)),
        port_name=PortName("instrument-catalog.reference"),
    )


def _external(symbol: str) -> ExternalIdentifier:
    return ExternalIdentifier(
        kind=ExternalIdentifierKind.LEGACY_QORE,
        namespace=ExternalIdentifierNamespace("market-data.instrument"),
        value=ExternalIdentifierValue(symbol),
    )


def _revision(
    *,
    mapping_id: IdentityMappingId,
    revision: int,
    parent: int | None,
    external: ExternalIdentifier,
    target: CanonicalIdentityRef,
    recorded_at: datetime,
    effective_from: datetime = _T0,
    effective_until: datetime | None = None,
) -> ExternalIdentityMappingRevision:
    return ExternalIdentityMappingRevision(
        mapping_id=mapping_id,
        revision=IdentityMappingRevision(revision),
        parent_revision=IdentityMappingRevision(parent) if parent is not None else None,
        external_identity=external,
        target=target,
        effective_from=effective_from,
        effective_until=effective_until,
        recorded_at=recorded_at,
        evidence_ref=_evidence(5_000 + revision),
    )


def test_identity_kind_listing_and_deterministic_projection() -> None:
    equity = _identity(1)
    benchmark = _identity(2, family="benchmark-index", kind=EconomicIdentityKind.REFERENCE_OBJECT)
    continuous = _identity(
        3,
        family="future-series",
        kind=EconomicIdentityKind.REFERENCE_OBJECT,
        construction=IdentityConstructionKind.CONTINUOUS_REFERENCE,
    )
    assert equity.kind is EconomicIdentityKind.TRADABLE_INSTRUMENT
    assert benchmark.kind is EconomicIdentityKind.REFERENCE_OBJECT
    assert continuous.logical_values()[3] == IdentityConstructionKind.CONTINUOUS_REFERENCE.value
    with pytest.raises(UniversalInstrumentIdentityValidationError, match="reference object"):
        _identity(4, family="future", construction=IdentityConstructionKind.CONTINUOUS_REFERENCE)

    first = ListingIdentity(
        listing_id=ListingIdentityId(_uuid(101)),
        economic_identity_id=equity.identity_id,
        venue=MarketVenueCode("xnas"),
        display_symbol="AAPL",
        valid_from=_T0,
        valid_until=None,
        evidence_ref=_evidence(101),
    )
    second = replace(
        first,
        listing_id=ListingIdentityId(_uuid(102)),
        venue=MarketVenueCode("bats"),
    )
    graph = UniversalInstrumentIdentityGraph(
        economic_identities=(benchmark, equity),
        listings=(second, first),
    )
    assert first.economic_identity_id == second.economic_identity_id
    assert CanonicalIdentityRef(first.listing_id).logical_values()[0] == "listing"
    assert graph.economic_identities[0].identity_id == equity.identity_id


def test_external_identifiers_keep_semantic_scope_and_public_values() -> None:
    provider = ExternalIdentifier(
        kind=ExternalIdentifierKind.PROVIDER_NATIVE,
        namespace=ExternalIdentifierNamespace("ctrader.symbol-id"),
        value=ExternalIdentifierValue("12345"),
        source=_source(),
    )
    venue = ExternalIdentifier(
        kind=ExternalIdentifierKind.VENUE_NATIVE,
        namespace=ExternalIdentifierNamespace("exchange.product-id"),
        value=ExternalIdentifierValue("ESU6"),
        venue=MarketVenueCode("xcme"),
    )
    standard = ExternalIdentifier(
        kind=ExternalIdentifierKind.STANDARD,
        namespace=ExternalIdentifierNamespace("isin"),
        value=ExternalIdentifierValue("US0378331005"),
    )
    assert provider.logical_values() != standard.logical_values()
    assert venue.venue == MarketVenueCode("xcme")
    with pytest.raises(
        UniversalInstrumentIdentityValidationError,
        match="requires explicit source",
    ):
        replace(provider, source=None)
    with pytest.raises(UniversalInstrumentIdentityValidationError, match="requires explicit venue"):
        replace(venue, venue=None)
    with pytest.raises(UniversalInstrumentIdentityValidationError, match="must not masquerade"):
        replace(_external("EURUSD"), venue=MarketVenueCode("otc"))
    public_name = ExternalIdentifierValue("TOKEN")
    assert public_name.logical_values() == ("TOKEN",)
    guarded = "".join(chr(value) for value in (116, 111, 107, 101, 110, 61, 120))
    with pytest.raises(UniversalInstrumentIdentityValidationError):
        ExternalIdentifierValue(guarded)


def test_relationships_cover_underlying_currency_series_and_ordered_components() -> None:
    option = _identity(20, family="option")
    equity = _identity(21)
    fx = _identity(22, family="fx")
    eur = _identity(23, family="currency", kind=EconomicIdentityKind.REFERENCE_OBJECT)
    usd = _identity(24, family="currency", kind=EconomicIdentityKind.REFERENCE_OBJECT)
    future = _identity(25, family="future")
    series = _identity(26, family="future-series", kind=EconomicIdentityKind.REFERENCE_OBJECT)
    spread = _identity(27, family="multi-leg", construction=IdentityConstructionKind.COMPOSITE)
    second_future = _identity(28, family="future")

    def relation(
        value: int,
        source: EconomicIdentity,
        target: EconomicIdentity,
        code: str,
        ordinal: int | None = None,
    ) -> IdentityRelationship:
        return IdentityRelationship(
            relationship_id=IdentityRelationshipId(_uuid(200 + value)),
            source_identity_id=source.identity_id,
            target_identity_id=target.identity_id,
            relationship=IdentityRelationshipCode(code),
            effective_from=_T0,
            effective_until=None,
            evidence_ref=_evidence(200 + value),
            ordinal=ordinal,
        )

    relationships = (
        relation(1, option, equity, "underlying"),
        relation(2, fx, eur, "currency.base"),
        relation(3, fx, usd, "currency.quote"),
        relation(4, future, series, "series.member"),
        relation(5, spread, future, "component", 1),
        relation(6, spread, second_future, "component", 2),
    )
    graph = UniversalInstrumentIdentityGraph(
        economic_identities=(option, equity, fx, eur, usd, future, series, spread, second_future),
        relationships=relationships,
    )
    assert len(graph.relationships) == 6
    duplicate = replace(relationships[-1], ordinal=1)
    with pytest.raises(UniversalInstrumentIdentityValidationError, match="ordinal"):
        UniversalInstrumentIdentityGraph(
            economic_identities=graph.economic_identities,
            relationships=relationships[:-1] + (duplicate,),
        )
    with pytest.raises(UniversalInstrumentIdentityValidationError, match="source and target"):
        replace(relationships[0], target_identity_id=option.identity_id)


def test_lifecycle_does_not_force_expiry() -> None:
    equity = _identity(30)
    future = _identity(31, family="future")
    bond = _identity(32, family="bond")
    perpetual = _identity(33, family="crypto-perpetual")
    events = (
        IdentityLifecycleEvent(
            event_id=IdentityLifecycleEventId(_uuid(301)),
            subject=CanonicalIdentityRef(equity.identity_id),
            event_type=LifecycleEventCode("listing.start"),
            effective_at=_T0,
            recorded_at=_T0,
            evidence_ref=_evidence(301),
        ),
        IdentityLifecycleEvent(
            event_id=IdentityLifecycleEventId(_uuid(302)),
            subject=CanonicalIdentityRef(future.identity_id),
            event_type=LifecycleEventCode("expiry"),
            effective_at=_T3,
            recorded_at=_T1,
            evidence_ref=_evidence(302),
        ),
        IdentityLifecycleEvent(
            event_id=IdentityLifecycleEventId(_uuid(303)),
            subject=CanonicalIdentityRef(bond.identity_id),
            event_type=LifecycleEventCode("maturity"),
            effective_at=_T3,
            recorded_at=_T1,
            evidence_ref=_evidence(303),
        ),
    )
    graph = UniversalInstrumentIdentityGraph(
        economic_identities=(equity, future, bond, perpetual),
        lifecycle_events=events,
    )
    assert not any(
        item.subject == CanonicalIdentityRef(perpetual.identity_id)
        for item in graph.lifecycle_events
    )


def test_mapping_history_preserves_versioned_historical_interpretation() -> None:
    old = _identity(40, family="fx")
    new = _identity(41, family="fx")
    mapping_id = IdentityMappingId(_uuid(401))
    external = _external("EURUSD")
    first = _revision(
        mapping_id=mapping_id,
        revision=1,
        parent=None,
        external=external,
        target=CanonicalIdentityRef(old.identity_id),
        recorded_at=_T0,
        effective_until=_T2,
    )
    second = _revision(
        mapping_id=mapping_id,
        revision=2,
        parent=1,
        external=external,
        target=CanonicalIdentityRef(new.identity_id),
        recorded_at=_T3,
        effective_from=_T2,
    )
    history = IdentityMappingHistory((first, second))
    graph = UniversalInstrumentIdentityGraph(
        economic_identities=(new, old),
        mapping_histories=(history,),
    )
    assert history.latest_revision == second
    assert first.target != second.target
    assert graph.mapping_histories[0].logical_values() == history.logical_values()


def test_mapping_history_rejects_gap_external_change_and_nonmonotonic_recording() -> None:
    target = _identity(50)
    mapping_id = IdentityMappingId(_uuid(501))
    external = _external("AAPL")
    first = _revision(
        mapping_id=mapping_id,
        revision=1,
        parent=None,
        external=external,
        target=CanonicalIdentityRef(target.identity_id),
        recorded_at=_T1,
    )
    gap = _revision(
        mapping_id=mapping_id,
        revision=3,
        parent=1,
        external=external,
        target=CanonicalIdentityRef(target.identity_id),
        recorded_at=_T2,
    )
    with pytest.raises(UniversalInstrumentIdentityValidationError, match="contiguous"):
        IdentityMappingHistory((first, gap))
    changed = _revision(
        mapping_id=mapping_id,
        revision=2,
        parent=1,
        external=_external("MSFT"),
        target=CanonicalIdentityRef(target.identity_id),
        recorded_at=_T2,
    )
    with pytest.raises(UniversalInstrumentIdentityValidationError, match="external identity"):
        IdentityMappingHistory((first, changed))
    nonmonotonic = _revision(
        mapping_id=mapping_id,
        revision=2,
        parent=1,
        external=external,
        target=CanonicalIdentityRef(target.identity_id),
        recorded_at=_T0,
    )
    with pytest.raises(UniversalInstrumentIdentityValidationError, match="increasing recorded_at"):
        IdentityMappingHistory((first, nonmonotonic))


def test_graph_rejects_parallel_mapping_and_dangling_reference() -> None:
    first = _identity(60)
    second = _identity(61)
    external = _external("AAPL")
    history_one = IdentityMappingHistory(
        (_revision(
            mapping_id=IdentityMappingId(_uuid(601)),
            revision=1,
            parent=None,
            external=external,
            target=CanonicalIdentityRef(first.identity_id),
            recorded_at=_T0,
        ),)
    )
    history_two = IdentityMappingHistory(
        (_revision(
            mapping_id=IdentityMappingId(_uuid(602)),
            revision=1,
            parent=None,
            external=external,
            target=CanonicalIdentityRef(second.identity_id),
            recorded_at=_T0,
        ),)
    )
    with pytest.raises(
        UniversalInstrumentIdentityValidationError,
        match="only one retained mapping history",
    ):
        UniversalInstrumentIdentityGraph(
            economic_identities=(first, second),
            mapping_histories=(history_one, history_two),
        )
    relation = IdentityRelationship(
        relationship_id=IdentityRelationshipId(_uuid(603)),
        source_identity_id=first.identity_id,
        target_identity_id=EconomicIdentityId(_uuid(99_999)),
        relationship=IdentityRelationshipCode("underlying"),
        effective_from=_T0,
        effective_until=None,
        evidence_ref=_evidence(603),
    )
    with pytest.raises(UniversalInstrumentIdentityValidationError, match="relationship endpoints"):
        UniversalInstrumentIdentityGraph(economic_identities=(first,), relationships=(relation,))


def test_strict_time_interval_type_guards_and_deterministic_order() -> None:
    with pytest.raises(UniversalInstrumentIdentityValidationError, match="positive int"):
        IdentityMappingRevision(cast(int, True))
    identity = _identity(70)
    with pytest.raises(UniversalInstrumentIdentityValidationError, match="timezone-aware"):
        ListingIdentity(
            listing_id=ListingIdentityId(_uuid(701)),
            economic_identity_id=identity.identity_id,
            venue=MarketVenueCode("xnas"),
            display_symbol="AAPL",
            valid_from=datetime(2026, 1, 1),
            valid_until=None,
            evidence_ref=_evidence(701),
        )
    listing = ListingIdentity(
        listing_id=ListingIdentityId(_uuid(702)),
        economic_identity_id=identity.identity_id,
        venue=MarketVenueCode("xnas"),
        display_symbol="AAPL",
        valid_from=_T1,
        valid_until=None,
        evidence_ref=_evidence(702),
    )
    with pytest.raises(UniversalInstrumentIdentityValidationError, match="after valid_from"):
        replace(listing, valid_until=_T1 - timedelta(seconds=1))
    other = _identity(71, family="benchmark-index", kind=EconomicIdentityKind.REFERENCE_OBJECT)
    graph_one = UniversalInstrumentIdentityGraph(economic_identities=(other, identity))
    graph_two = UniversalInstrumentIdentityGraph(economic_identities=(identity, other))
    assert graph_one.logical_values() == graph_two.logical_values()


def test_runtime_type_guards_reject_invalid_public_shapes() -> None:
    base = _identity(80)
    for field in ("identity_id", "kind", "family", "construction", "evidence_ref"):
        with pytest.raises(UniversalInstrumentIdentityValidationError):
            replace(base, **{field: cast(Any, "bad")})
    with pytest.raises(UniversalInstrumentIdentityValidationError):
        CanonicalIdentityRef(cast(Any, "bad"))
    with pytest.raises(UniversalInstrumentIdentityValidationError):
        UniversalInstrumentIdentityGraph(economic_identities=cast(Any, []))
    with pytest.raises(UniversalInstrumentIdentityValidationError):
        UniversalInstrumentIdentityGraph(economic_identities=(cast(Any, "bad"),))
