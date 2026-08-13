from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID

import pytest

from qore.infrastructure.ports import (
    AdapterId,
    ExternalSourceDescriptor,
    PortName,
    SourceId,
)
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
_T1 = datetime(2026, 3, 1, tzinfo=UTC)
_T2 = datetime(2026, 6, 1, tzinfo=UTC)
_T3 = datetime(2026, 9, 1, tzinfo=UTC)


def _uuid(value: int) -> UUID:
    return UUID(int=value)


def _economic_id(value: int) -> EconomicIdentityId:
    return EconomicIdentityId(_uuid(value))


def _evidence(value: int) -> IdentityEvidenceRef:
    return IdentityEvidenceRef(_uuid(10_000 + value))


def _identity(
    value: int,
    *,
    family: str,
    kind: EconomicIdentityKind = EconomicIdentityKind.TRADABLE_INSTRUMENT,
    construction: IdentityConstructionKind = IdentityConstructionKind.NATIVE,
) -> EconomicIdentity:
    return EconomicIdentity(
        identity_id=_economic_id(value),
        kind=kind,
        family=IdentityFamilyCode(family),
        construction=construction,
        evidence_ref=_evidence(value),
    )


def _source(value: int = 1) -> ExternalSourceDescriptor:
    return ExternalSourceDescriptor(
        adapter_id=AdapterId(_uuid(20_000 + value)),
        source_id=SourceId(_uuid(30_000 + value)),
        port_name=PortName("instrument-catalog.reference"),
    )


def _legacy_symbol(symbol: str) -> ExternalIdentifier:
    return ExternalIdentifier(
        kind=ExternalIdentifierKind.LEGACY_QORE,
        namespace=ExternalIdentifierNamespace("market-data.instrument"),
        value=ExternalIdentifierValue(symbol),
    )


def test_economic_identity_separates_tradable_and_reference_objects() -> None:
    equity = _identity(1, family="equity")
    benchmark = _identity(
        2,
        family="benchmark-index",
        kind=EconomicIdentityKind.REFERENCE_OBJECT,
    )
    continuous = _identity(
        3,
        family="future-series",
        kind=EconomicIdentityKind.REFERENCE_OBJECT,
        construction=IdentityConstructionKind.CONTINUOUS_REFERENCE,
    )

    assert equity.kind is EconomicIdentityKind.TRADABLE_INSTRUMENT
    assert benchmark.kind is EconomicIdentityKind.REFERENCE_OBJECT
    assert continuous.construction is IdentityConstructionKind.CONTINUOUS_REFERENCE

    with pytest.raises(
        UniversalInstrumentIdentityValidationError,
        match="continuous-reference identity must be a reference object",
    ):
        _identity(
            4,
            family="future",
            construction=IdentityConstructionKind.CONTINUOUS_REFERENCE,
        )


def test_one_economic_identity_can_have_multiple_independent_listings() -> None:
    equity = _identity(10, family="equity")
    primary = ListingIdentity(
        listing_id=ListingIdentityId(_uuid(101)),
        economic_identity_id=equity.identity_id,
        venue=MarketVenueCode("xnas"),
        display_symbol="AAPL",
        valid_from=_T0,
        valid_until=None,
        evidence_ref=_evidence(101),
    )
    alternate = ListingIdentity(
        listing_id=ListingIdentityId(_uuid(102)),
        economic_identity_id=equity.identity_id,
        venue=MarketVenueCode("bats"),
        display_symbol="AAPL",
        valid_from=_T0,
        valid_until=None,
        evidence_ref=_evidence(102),
    )

    graph = UniversalInstrumentIdentityGraph(
        economic_identities=(equity,),
        listings=(alternate, primary),
    )

    assert graph.listings[0].listing_id == primary.listing_id
    assert primary.economic_identity_id == alternate.economic_identity_id
    assert primary.listing_id != alternate.listing_id


def test_external_identifier_kinds_preserve_scope_without_becoming_identity() -> None:
    provider_native = ExternalIdentifier(
        kind=ExternalIdentifierKind.PROVIDER_NATIVE,
        namespace=ExternalIdentifierNamespace("ctrader.symbol-id"),
        value=ExternalIdentifierValue("12345"),
        source=_source(),
    )
    venue_native = ExternalIdentifier(
        kind=ExternalIdentifierKind.VENUE_NATIVE,
        namespace=ExternalIdentifierNamespace("exchange.product-id"),
        value=ExternalIdentifierValue("ESU6"),
        venue=MarketVenueCode("xcme"),
    )
    isin = ExternalIdentifier(
        kind=ExternalIdentifierKind.STANDARD,
        namespace=ExternalIdentifierNamespace("isin"),
        value=ExternalIdentifierValue("US0378331005"),
    )

    assert provider_native.kind is ExternalIdentifierKind.PROVIDER_NATIVE
    assert venue_native.kind is ExternalIdentifierKind.VENUE_NATIVE
    assert isin.kind is ExternalIdentifierKind.STANDARD
    assert provider_native.logical_values() != isin.logical_values()

    with pytest.raises(
        UniversalInstrumentIdentityValidationError,
        match="provider-native identifier requires explicit source provenance",
    ):
        ExternalIdentifier(
            kind=ExternalIdentifierKind.PROVIDER_NATIVE,
            namespace=ExternalIdentifierNamespace("ctrader.symbol-id"),
            value=ExternalIdentifierValue("12345"),
        )

    with pytest.raises(
        UniversalInstrumentIdentityValidationError,
        match="venue-native identifier requires explicit venue scope",
    ):
        ExternalIdentifier(
            kind=ExternalIdentifierKind.VENUE_NATIVE,
            namespace=ExternalIdentifierNamespace("exchange.product-id"),
            value=ExternalIdentifierValue("ESU6"),
        )

    with pytest.raises(
        UniversalInstrumentIdentityValidationError,
        match="legacy QORE identifier must not masquerade as external scope",
    ):
        ExternalIdentifier(
            kind=ExternalIdentifierKind.LEGACY_QORE,
            namespace=ExternalIdentifierNamespace("market-data.instrument"),
            value=ExternalIdentifierValue("EURUSD"),
            venue=MarketVenueCode("otc"),
        )


def test_relationship_graph_represents_underlying_currency_series_and_components() -> None:
    option = _identity(200, family="option")
    equity = _identity(201, family="equity")
    fx_pair = _identity(202, family="fx")
    eur = _identity(
        203,
        family="currency",
        kind=EconomicIdentityKind.REFERENCE_OBJECT,
    )
    usd = _identity(
        204,
        family="currency",
        kind=EconomicIdentityKind.REFERENCE_OBJECT,
    )
    future = _identity(205, family="future")
    future_series = _identity(
        206,
        family="future-series",
        kind=EconomicIdentityKind.REFERENCE_OBJECT,
    )
    spread = _identity(
        207,
        family="multi-leg",
        construction=IdentityConstructionKind.COMPOSITE,
    )
    second_future = _identity(208, family="future")

    relationships = (
        IdentityRelationship(
            relationship_id=IdentityRelationshipId(_uuid(300)),
            source_identity_id=option.identity_id,
            target_identity_id=equity.identity_id,
            relationship=IdentityRelationshipCode("underlying"),
            effective_from=_T0,
            effective_until=None,
            evidence_ref=_evidence(300),
        ),
        IdentityRelationship(
            relationship_id=IdentityRelationshipId(_uuid(301)),
            source_identity_id=fx_pair.identity_id,
            target_identity_id=eur.identity_id,
            relationship=IdentityRelationshipCode("currency.base"),
            effective_from=_T0,
            effective_until=None,
            evidence_ref=_evidence(301),
        ),
        IdentityRelationship(
            relationship_id=IdentityRelationshipId(_uuid(302)),
            source_identity_id=fx_pair.identity_id,
            target_identity_id=usd.identity_id,
            relationship=IdentityRelationshipCode("currency.quote"),
            effective_from=_T0,
            effective_until=None,
            evidence_ref=_evidence(302),
        ),
        IdentityRelationship(
            relationship_id=IdentityRelationshipId(_uuid(303)),
            source_identity_id=future.identity_id,
            target_identity_id=future_series.identity_id,
            relationship=IdentityRelationshipCode("series.member"),
            effective_from=_T0,
            effective_until=None,
            evidence_ref=_evidence(303),
        ),
        IdentityRelationship(
            relationship_id=IdentityRelationshipId(_uuid(304)),
            source_identity_id=spread.identity_id,
            target_identity_id=future.identity_id,
            relationship=IdentityRelationshipCode("component"),
            effective_from=_T0,
            effective_until=None,
            evidence_ref=_evidence(304),
            ordinal=1,
        ),
        IdentityRelationship(
            relationship_id=IdentityRelationshipId(_uuid(305)),
            source_identity_id=spread.identity_id,
            target_identity_id=second_future.identity_id,
            relationship=IdentityRelationshipCode("component"),
            effective_from=_T0,
            effective_until=None,
            evidence_ref=_evidence(305),
            ordinal=2,
        ),
    )

    graph = UniversalInstrumentIdentityGraph(
        economic_identities=(
            option,
            equity,
            fx_pair,
            eur,
            usd,
            future,
            future_series,
            spread,
            second_future,
        ),
        relationships=relationships,
    )

    assert len(graph.relationships) == 6
    assert {item.relationship.value for item in graph.relationships} == {
        "underlying",
        "currency.base",
        "currency.quote",
        "series.member",
        "component",
    }


def test_graph_rejects_duplicate_component_ordinal_within_same_scope() -> None:
    spread = _identity(
        400,
        family="multi-leg",
        construction=IdentityConstructionKind.COMPOSITE,
    )
    first = _identity(401, family="future")
    second = _identity(402, family="future")
    relation_one = IdentityRelationship(
        relationship_id=IdentityRelationshipId(_uuid(410)),
        source_identity_id=spread.identity_id,
        target_identity_id=first.identity_id,
        relationship=IdentityRelationshipCode("component"),
        effective_from=_T0,
        effective_until=None,
        evidence_ref=_evidence(410),
        ordinal=1,
    )
    relation_two = IdentityRelationship(
        relationship_id=IdentityRelationshipId(_uuid(411)),
        source_identity_id=spread.identity_id,
        target_identity_id=second.identity_id,
        relationship=IdentityRelationshipCode("component"),
        effective_from=_T0,
        effective_until=None,
        evidence_ref=_evidence(411),
        ordinal=1,
    )

    with pytest.raises(
        UniversalInstrumentIdentityValidationError,
        match="ordered relationship ordinal must be unique",
    ):
        UniversalInstrumentIdentityGraph(
            economic_identities=(spread, first, second),
            relationships=(relation_one, relation_two),
        )


def test_lifecycle_is_event_based_and_does_not_force_global_expiry() -> None:
    equity = _identity(500, family="equity")
    future = _identity(501, family="future")
    bond = _identity(502, family="bond")
    swap = _identity(503, family="swap")
    perpetual = _identity(504, family="crypto-perpetual")

    events = (
        IdentityLifecycleEvent(
            event_id=IdentityLifecycleEventId(_uuid(510)),
            subject=CanonicalIdentityRef(equity.identity_id),
            event_type=LifecycleEventCode("listing.start"),
            effective_at=_T0,
            recorded_at=_T0,
            evidence_ref=_evidence(510),
        ),
        IdentityLifecycleEvent(
            event_id=IdentityLifecycleEventId(_uuid(511)),
            subject=CanonicalIdentityRef(future.identity_id),
            event_type=LifecycleEventCode("expiry"),
            effective_at=_T3,
            recorded_at=_T1,
            evidence_ref=_evidence(511),
        ),
        IdentityLifecycleEvent(
            event_id=IdentityLifecycleEventId(_uuid(512)),
            subject=CanonicalIdentityRef(bond.identity_id),
            event_type=LifecycleEventCode("maturity"),
            effective_at=_T3,
            recorded_at=_T1,
            evidence_ref=_evidence(512),
        ),
        IdentityLifecycleEvent(
            event_id=IdentityLifecycleEventId(_uuid(513)),
            subject=CanonicalIdentityRef(swap.identity_id),
            event_type=LifecycleEventCode("termination"),
            effective_at=_T3,
            recorded_at=_T2,
            evidence_ref=_evidence(513),
        ),
    )

    graph = UniversalInstrumentIdentityGraph(
        economic_identities=(equity, future, bond, swap, perpetual),
        lifecycle_events=events,
    )

    perpetual_events = tuple(
        event
        for event in graph.lifecycle_events
        if event.subject == CanonicalIdentityRef(perpetual.identity_id)
    )
    assert perpetual_events == ()
    assert {event.event_type.value for event in graph.lifecycle_events} == {
        "listing.start",
        "expiry",
        "maturity",
        "termination",
    }


def test_mapping_history_retains_versioned_effective_identity_interpretation() -> None:
    old_identity = _identity(600, family="fx")
    replacement_identity = _identity(601, family="fx")
    external = _legacy_symbol("EURUSD")
    mapping_id = IdentityMappingId(_uuid(610))

    first = ExternalIdentityMappingRevision(
        mapping_id=mapping_id,
        revision=IdentityMappingRevision(1),
        parent_revision=None,
        external_identity=external,
        target=CanonicalIdentityRef(old_identity.identity_id),
        effective_from=_T0,
        effective_until=_T2,
        recorded_at=_T0,
        evidence_ref=_evidence(610),
    )
    second = ExternalIdentityMappingRevision(
        mapping_id=mapping_id,
        revision=IdentityMappingRevision(2),
        parent_revision=IdentityMappingRevision(1),
        external_identity=external,
        target=CanonicalIdentityRef(replacement_identity.identity_id),
        effective_from=_T2,
        effective_until=None,
        recorded_at=_T3,
        evidence_ref=_evidence(611),
    )
    history = IdentityMappingHistory((first, second))

    graph = UniversalInstrumentIdentityGraph(
        economic_identities=(replacement_identity, old_identity),
        mapping_histories=(history,),
    )

    assert graph.mapping_histories[0].revisions == (first, second)
    assert history.latest_revision == second
    assert first.target != second.target
    assert first.logical_values() != second.logical_values()


def test_mapping_history_rejects_revision_gaps_and_external_identity_changes() -> None:
    target = _identity(700, family="equity")
    mapping_id = IdentityMappingId(_uuid(710))
    first_external = _legacy_symbol("AAPL")
    second_external = _legacy_symbol("MSFT")
    first = ExternalIdentityMappingRevision(
        mapping_id=mapping_id,
        revision=IdentityMappingRevision(1),
        parent_revision=None,
        external_identity=first_external,
        target=CanonicalIdentityRef(target.identity_id),
        effective_from=_T0,
        effective_until=None,
        recorded_at=_T0,
        evidence_ref=_evidence(710),
    )
    third = ExternalIdentityMappingRevision(
        mapping_id=mapping_id,
        revision=IdentityMappingRevision(3),
        parent_revision=IdentityMappingRevision(1),
        external_identity=first_external,
        target=CanonicalIdentityRef(target.identity_id),
        effective_from=_T1,
        effective_until=None,
        recorded_at=_T1,
        evidence_ref=_evidence(711),
    )

    with pytest.raises(
        UniversalInstrumentIdentityValidationError,
        match="revisions must be contiguous from 1",
    ):
        IdentityMappingHistory((first, third))

    second_changed = ExternalIdentityMappingRevision(
        mapping_id=mapping_id,
        revision=IdentityMappingRevision(2),
        parent_revision=IdentityMappingRevision(1),
        external_identity=second_external,
        target=CanonicalIdentityRef(target.identity_id),
        effective_from=_T1,
        effective_until=None,
        recorded_at=_T1,
        evidence_ref=_evidence(712),
    )
    with pytest.raises(
        UniversalInstrumentIdentityValidationError,
        match="retain one external identity",
    ):
        IdentityMappingHistory((first, second_changed))


def test_graph_rejects_parallel_mapping_histories_for_same_external_identity() -> None:
    first_target = _identity(800, family="equity")
    second_target = _identity(801, family="equity")
    external = _legacy_symbol("AAPL")
    first_history = IdentityMappingHistory(
        (
            ExternalIdentityMappingRevision(
                mapping_id=IdentityMappingId(_uuid(810)),
                revision=IdentityMappingRevision(1),
                parent_revision=None,
                external_identity=external,
                target=CanonicalIdentityRef(first_target.identity_id),
                effective_from=_T0,
                effective_until=None,
                recorded_at=_T0,
                evidence_ref=_evidence(810),
            ),
        )
    )
    second_history = IdentityMappingHistory(
        (
            ExternalIdentityMappingRevision(
                mapping_id=IdentityMappingId(_uuid(811)),
                revision=IdentityMappingRevision(1),
                parent_revision=None,
                external_identity=external,
                target=CanonicalIdentityRef(second_target.identity_id),
                effective_from=_T0,
                effective_until=None,
                recorded_at=_T0,
                evidence_ref=_evidence(811),
            ),
        )
    )

    with pytest.raises(
        UniversalInstrumentIdentityValidationError,
        match="only one retained mapping history",
    ):
        UniversalInstrumentIdentityGraph(
            economic_identities=(first_target, second_target),
            mapping_histories=(first_history, second_history),
        )


def test_graph_rejects_dangling_references_and_nonmonotonic_mapping_recording() -> None:
    retained = _identity(900, family="equity")
    missing = _identity(901, family="equity")
    dangling = IdentityRelationship(
        relationship_id=IdentityRelationshipId(_uuid(910)),
        source_identity_id=retained.identity_id,
        target_identity_id=missing.identity_id,
        relationship=IdentityRelationshipCode("underlying"),
        effective_from=_T0,
        effective_until=None,
        evidence_ref=_evidence(910),
    )
    with pytest.raises(
        UniversalInstrumentIdentityValidationError,
        match="relationship endpoints must be retained economic identities",
    ):
        UniversalInstrumentIdentityGraph(
            economic_identities=(retained,),
            relationships=(dangling,),
        )

    external = _legacy_symbol("AAPL")
    mapping_id = IdentityMappingId(_uuid(911))
    first = ExternalIdentityMappingRevision(
        mapping_id=mapping_id,
        revision=IdentityMappingRevision(1),
        parent_revision=None,
        external_identity=external,
        target=CanonicalIdentityRef(retained.identity_id),
        effective_from=_T0,
        effective_until=None,
        recorded_at=_T2,
        evidence_ref=_evidence(911),
    )
    second = ExternalIdentityMappingRevision(
        mapping_id=mapping_id,
        revision=IdentityMappingRevision(2),
        parent_revision=IdentityMappingRevision(1),
        external_identity=external,
        target=CanonicalIdentityRef(retained.identity_id),
        effective_from=_T1,
        effective_until=None,
        recorded_at=_T1,
        evidence_ref=_evidence(912),
    )
    with pytest.raises(
        UniversalInstrumentIdentityValidationError,
        match="mapping revisions must have increasing recorded_at",
    ):
        UniversalInstrumentIdentityGraph(
            economic_identities=(retained,),
            mapping_histories=(IdentityMappingHistory((first, second)),),
        )


def test_identity_contracts_reject_bool_as_int_and_naive_timestamps() -> None:
    with pytest.raises(
        UniversalInstrumentIdentityValidationError,
        match="mapping revision must be a positive int",
    ):
        IdentityMappingRevision(cast(int, True))

    first = _identity(1_000, family="future")
    second = _identity(1_001, family="future")
    with pytest.raises(
        UniversalInstrumentIdentityValidationError,
        match="relationship ordinal must be a positive int",
    ):
        IdentityRelationship(
            relationship_id=IdentityRelationshipId(_uuid(1_010)),
            source_identity_id=first.identity_id,
            target_identity_id=second.identity_id,
            relationship=IdentityRelationshipCode("component"),
            effective_from=_T0,
            effective_until=None,
            evidence_ref=_evidence(1_010),
            ordinal=cast(int, True),
        )

    with pytest.raises(
        UniversalInstrumentIdentityValidationError,
        match="listing valid_from must be timezone-aware",
    ):
        ListingIdentity(
            listing_id=ListingIdentityId(_uuid(1_011)),
            economic_identity_id=first.identity_id,
            venue=MarketVenueCode("xcme"),
            display_symbol="ESU6",
            valid_from=datetime(2026, 1, 1),
            valid_until=None,
            evidence_ref=_evidence(1_011),
        )


def test_graph_logical_values_are_deterministic_independent_of_input_order() -> None:
    first = _identity(1_100, family="equity")
    second = _identity(1_101, family="benchmark-index")
    graph_one = UniversalInstrumentIdentityGraph(
        economic_identities=(second, first),
    )
    graph_two = UniversalInstrumentIdentityGraph(
        economic_identities=(first, second),
    )

    assert graph_one.economic_identities == graph_two.economic_identities
    assert graph_one.logical_values() == graph_two.logical_values()
    assert graph_one.economic_identities[0].identity_id == first.identity_id


def test_effective_intervals_reject_nonpositive_duration() -> None:
    identity = _identity(1_200, family="equity")
    with pytest.raises(
        UniversalInstrumentIdentityValidationError,
        match="listing valid_until must be after valid_from",
    ):
        ListingIdentity(
            listing_id=ListingIdentityId(_uuid(1_210)),
            economic_identity_id=identity.identity_id,
            venue=MarketVenueCode("xnas"),
            display_symbol="AAPL",
            valid_from=_T1,
            valid_until=_T1,
            evidence_ref=_evidence(1_210),
        )

    target = _identity(1_201, family="benchmark-index")
    with pytest.raises(
        UniversalInstrumentIdentityValidationError,
        match="relationship effective_until must be after effective_from",
    ):
        IdentityRelationship(
            relationship_id=IdentityRelationshipId(_uuid(1_211)),
            source_identity_id=identity.identity_id,
            target_identity_id=target.identity_id,
            relationship=IdentityRelationshipCode("benchmark"),
            effective_from=_T2,
            effective_until=_T2 - timedelta(seconds=1),
            evidence_ref=_evidence(1_211),
        )
