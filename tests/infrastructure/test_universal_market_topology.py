from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta, timezone
from uuid import UUID

import pytest

from qore.infrastructure.universal_instrument_identity import (
    EconomicIdentityId,
    IdentityEvidenceRef,
    ListingIdentity,
    ListingIdentityId,
    MarketVenueCode,
)
from qore.infrastructure.universal_market_topology import (
    EconomicMarketTopologyScope,
    EconomicVenueMarketTopologyScope,
    FragmentedMarketTopology,
    ListingMarketTopologyScope,
    MarketFragmentationId,
    MarketInfrastructureContext,
    MarketInteractionMechanism,
    MarketStage,
    MarketTopologyEffectiveInterval,
    MarketTopologyEvidenceRef,
    MarketTopologyProfile,
    MarketTopologyProfileId,
    MarketTransparency,
    UniversalMarketTopologyValidationError,
    VenueMarketTopologyScope,
)


def _economic(value: int) -> EconomicIdentityId:
    return EconomicIdentityId(UUID(int=value))


def _venue(value: str) -> MarketVenueCode:
    return MarketVenueCode(value)


def _identity_evidence(value: int) -> IdentityEvidenceRef:
    return IdentityEvidenceRef(UUID(int=value))


def _topology_evidence(value: int) -> MarketTopologyEvidenceRef:
    return MarketTopologyEvidenceRef(UUID(int=value))


def _interval(
    start_day: int = 1,
    end_day: int | None = 20,
) -> MarketTopologyEffectiveInterval:
    return MarketTopologyEffectiveInterval(
        effective_from=datetime(2026, 1, start_day, tzinfo=UTC),
        effective_until=(
            datetime(2026, 1, end_day, tzinfo=UTC)
            if end_day is not None
            else None
        ),
    )


def _listing(
    *,
    listing_value: int = 100,
    economic_value: int = 1,
    venue: str = "venue-a",
    valid_from_day: int = 1,
    valid_until_day: int | None = 31,
) -> ListingIdentity:
    return ListingIdentity(
        listing_id=ListingIdentityId(UUID(int=listing_value)),
        economic_identity_id=_economic(economic_value),
        venue=_venue(venue),
        display_symbol="TEST",
        valid_from=datetime(2026, 1, valid_from_day, tzinfo=UTC),
        valid_until=(
            datetime(2026, 1, valid_until_day, tzinfo=UTC)
            if valid_until_day is not None
            else None
        ),
        evidence_ref=_identity_evidence(listing_value + 1000),
    )


def _profile(
    *,
    profile_value: int,
    subject: object,
    mechanisms: tuple[MarketInteractionMechanism, ...] = (
        MarketInteractionMechanism.CENTRAL_LIMIT_ORDER_BOOK,
    ),
    interval: MarketTopologyEffectiveInterval | None = None,
    stages: tuple[MarketStage, ...] = (),
    transparency: MarketTransparency | None = None,
    context: MarketInfrastructureContext | None = None,
) -> MarketTopologyProfile:
    return MarketTopologyProfile(
        profile_id=MarketTopologyProfileId(UUID(int=profile_value)),
        subject=subject,  # type: ignore[arg-type]
        mechanisms=mechanisms,
        effective_interval=interval or _interval(),
        evidence_ref=_topology_evidence(profile_value + 2000),
        stages=stages,
        transparency=transparency,
        infrastructure_context=context,
    )


def test_four_scope_shapes_preserve_owner_semantics_without_fake_listing() -> None:
    economic = _economic(1)
    venue = _venue("otc-a")
    listing = _listing(economic_value=1, venue="listed-a")

    economic_scope = EconomicMarketTopologyScope(economic)
    listing_scope = ListingMarketTopologyScope(listing)
    venue_scope = VenueMarketTopologyScope(venue)
    economic_venue_scope = EconomicVenueMarketTopologyScope(economic, venue)

    assert economic_scope.logical_values()[0] == "economic"
    assert listing_scope.economic_identity_id == economic
    assert listing_scope.venue == _venue("listed-a")
    assert venue_scope.logical_values() == ("venue", venue.logical_values())
    assert economic_venue_scope.logical_values() == (
        "economic-venue",
        economic.logical_values(),
        venue.logical_values(),
    )
    assert not hasattr(economic_venue_scope, "listing")
    assert not hasattr(economic_venue_scope, "listing_id")
    assert not hasattr(economic_venue_scope, "display_symbol")


def test_profile_canonicalizes_hybrid_mechanisms_and_stages() -> None:
    profile_a = _profile(
        profile_value=1,
        subject=VenueMarketTopologyScope(_venue("venue-a")),
        mechanisms=(
            MarketInteractionMechanism.AUCTION,
            MarketInteractionMechanism.CENTRAL_LIMIT_ORDER_BOOK,
        ),
        stages=(MarketStage.SECONDARY, MarketStage.PRIMARY),
        transparency=MarketTransparency.MIXED,
        context=MarketInfrastructureContext.CENTRALIZED,
    )
    profile_b = _profile(
        profile_value=1,
        subject=VenueMarketTopologyScope(_venue("venue-a")),
        mechanisms=(
            MarketInteractionMechanism.CENTRAL_LIMIT_ORDER_BOOK,
            MarketInteractionMechanism.AUCTION,
        ),
        stages=(MarketStage.PRIMARY, MarketStage.SECONDARY),
        transparency=MarketTransparency.MIXED,
        context=MarketInfrastructureContext.CENTRALIZED,
    )

    assert profile_a.mechanisms == (
        MarketInteractionMechanism.AUCTION,
        MarketInteractionMechanism.CENTRAL_LIMIT_ORDER_BOOK,
    )
    assert profile_a.stages == (MarketStage.PRIMARY, MarketStage.SECONDARY)
    assert profile_a.logical_values() == profile_b.logical_values()


def test_infrastructure_context_does_not_imply_interaction_mechanism() -> None:
    centralized_amm = _profile(
        profile_value=2,
        subject=VenueMarketTopologyScope(_venue("venue-a")),
        mechanisms=(MarketInteractionMechanism.AUTOMATED_MARKET_MAKER,),
        context=MarketInfrastructureContext.CENTRALIZED,
    )
    on_chain_clob = _profile(
        profile_value=3,
        subject=VenueMarketTopologyScope(_venue("venue-b")),
        mechanisms=(MarketInteractionMechanism.CENTRAL_LIMIT_ORDER_BOOK,),
        context=MarketInfrastructureContext.ON_CHAIN,
    )

    assert centralized_amm.mechanisms == (
        MarketInteractionMechanism.AUTOMATED_MARKET_MAKER,
    )
    assert on_chain_clob.mechanisms == (
        MarketInteractionMechanism.CENTRAL_LIMIT_ORDER_BOOK,
    )


def test_otc_economic_venue_scope_supports_rfq_without_listing() -> None:
    profile = _profile(
        profile_value=4,
        subject=EconomicVenueMarketTopologyScope(
            _economic(1),
            _venue("dealer-network-a"),
        ),
        mechanisms=(
            MarketInteractionMechanism.DEALER_RFQ,
            MarketInteractionMechanism.BILATERAL,
        ),
        context=None,
    )

    assert profile.economic_identity_id == _economic(1)
    assert profile.venue == _venue("dealer-network-a")
    assert isinstance(profile.subject, EconomicVenueMarketTopologyScope)


def test_economic_scope_supports_bilateral_without_any_venue_claim() -> None:
    profile = _profile(
        profile_value=5,
        subject=EconomicMarketTopologyScope(_economic(1)),
        mechanisms=(MarketInteractionMechanism.BILATERAL,),
    )

    assert profile.economic_identity_id == _economic(1)
    assert profile.venue is None


def test_listing_scope_derives_economic_and_venue_from_exact_listing() -> None:
    listing = _listing(economic_value=9, venue="venue-x")
    profile = _profile(
        profile_value=6,
        subject=ListingMarketTopologyScope(listing),
        interval=_interval(2, 20),
        mechanisms=(MarketInteractionMechanism.QUOTE_DRIVEN,),
    )

    assert profile.economic_identity_id == _economic(9)
    assert profile.venue == _venue("venue-x")
    assert profile.subject.logical_values() == ("listing", listing.logical_values())


def test_listing_scope_rejects_profile_before_listing_validity() -> None:
    listing = _listing(valid_from_day=5)

    with pytest.raises(
        UniversalMarketTopologyValidationError,
        match="within listing validity",
    ):
        _profile(
            profile_value=7,
            subject=ListingMarketTopologyScope(listing),
            interval=_interval(4, 20),
        )


def test_listing_scope_rejects_open_ended_profile_when_listing_has_end() -> None:
    listing = _listing(valid_until_day=20)

    with pytest.raises(
        UniversalMarketTopologyValidationError,
        match="within listing validity",
    ):
        _profile(
            profile_value=8,
            subject=ListingMarketTopologyScope(listing),
            interval=_interval(2, None),
        )


def test_open_ended_listing_can_support_open_ended_topology() -> None:
    listing = _listing(valid_until_day=None)
    profile = _profile(
        profile_value=9,
        subject=ListingMarketTopologyScope(listing),
        interval=_interval(2, None),
    )

    assert profile.effective_interval.effective_until is None


def test_effective_interval_canonicalizes_equivalent_instants() -> None:
    plus_530 = timezone(timedelta(hours=5, minutes=30))
    utc_interval = MarketTopologyEffectiveInterval(
        datetime(2026, 1, 1, 0, 0, 0, 123456, tzinfo=UTC),
        datetime(2026, 1, 2, 0, 0, 0, 123456, tzinfo=UTC),
    )
    offset_interval = MarketTopologyEffectiveInterval(
        datetime(2026, 1, 1, 5, 30, 0, 123456, tzinfo=plus_530),
        datetime(2026, 1, 2, 5, 30, 0, 123456, tzinfo=plus_530),
    )

    assert utc_interval.logical_values() == offset_interval.logical_values()
    assert utc_interval.logical_values() == (
        "2026-01-01T00:00:00.123456+00:00",
        "2026-01-02T00:00:00.123456+00:00",
    )


def test_fragmentation_retains_same_economic_identity_across_distinct_venues() -> None:
    economic = _economic(42)
    listing = _listing(
        listing_value=420,
        economic_value=42,
        venue="venue-b",
        valid_until_day=31,
    )
    profile_b = _profile(
        profile_value=20,
        subject=ListingMarketTopologyScope(listing),
        interval=_interval(1, 25),
        mechanisms=(MarketInteractionMechanism.CENTRAL_LIMIT_ORDER_BOOK,),
    )
    profile_a = _profile(
        profile_value=10,
        subject=EconomicVenueMarketTopologyScope(economic, _venue("venue-a")),
        interval=_interval(1, 25),
        mechanisms=(MarketInteractionMechanism.DEALER_RFQ,),
    )

    fragmented = FragmentedMarketTopology(
        fragmentation_id=MarketFragmentationId(UUID(int=1)),
        economic_identity_id=economic,
        profiles=(profile_b, profile_a),
        effective_interval=_interval(5, 20),
        evidence_ref=_topology_evidence(999),
    )

    assert fragmented.profiles == (profile_a, profile_b)
    assert fragmented.venues == (_venue("venue-a"), _venue("venue-b"))
    assert fragmented.logical_values()[2] == (
        profile_a.logical_values(),
        profile_b.logical_values(),
    )


def test_fragmentation_canonicalizes_component_order() -> None:
    economic = _economic(50)
    profile_a = _profile(
        profile_value=1,
        subject=EconomicVenueMarketTopologyScope(economic, _venue("venue-a")),
    )
    profile_b = _profile(
        profile_value=2,
        subject=EconomicVenueMarketTopologyScope(economic, _venue("venue-b")),
    )
    left = FragmentedMarketTopology(
        MarketFragmentationId(UUID(int=50)),
        economic,
        (profile_b, profile_a),
        _interval(2, 15),
        _topology_evidence(50),
    )
    right = FragmentedMarketTopology(
        MarketFragmentationId(UUID(int=50)),
        economic,
        (profile_a, profile_b),
        _interval(2, 15),
        _topology_evidence(50),
    )

    assert left.logical_values() == right.logical_values()


def test_fragmentation_rejects_wrong_economic_identity() -> None:
    profile_a = _profile(
        profile_value=1,
        subject=EconomicVenueMarketTopologyScope(_economic(1), _venue("venue-a")),
    )
    profile_b = _profile(
        profile_value=2,
        subject=EconomicVenueMarketTopologyScope(_economic(2), _venue("venue-b")),
    )

    with pytest.raises(
        UniversalMarketTopologyValidationError,
        match="exact economic identity",
    ):
        FragmentedMarketTopology(
            MarketFragmentationId(UUID(int=1)),
            _economic(1),
            (profile_a, profile_b),
            _interval(2, 15),
            _topology_evidence(1),
        )


def test_fragmentation_rejects_non_venue_qualified_profile() -> None:
    economic = _economic(1)
    profile_a = _profile(
        profile_value=1,
        subject=EconomicMarketTopologyScope(economic),
    )
    profile_b = _profile(
        profile_value=2,
        subject=EconomicVenueMarketTopologyScope(economic, _venue("venue-b")),
    )

    with pytest.raises(
        UniversalMarketTopologyValidationError,
        match="venue-qualified",
    ):
        FragmentedMarketTopology(
            MarketFragmentationId(UUID(int=2)),
            economic,
            (profile_a, profile_b),
            _interval(2, 15),
            _topology_evidence(2),
        )


def test_fragmentation_rejects_one_distinct_venue() -> None:
    economic = _economic(1)
    profile_a = _profile(
        profile_value=1,
        subject=EconomicVenueMarketTopologyScope(economic, _venue("venue-a")),
    )
    profile_b = _profile(
        profile_value=2,
        subject=EconomicVenueMarketTopologyScope(economic, _venue("venue-a")),
        mechanisms=(MarketInteractionMechanism.AUCTION,),
    )

    with pytest.raises(
        UniversalMarketTopologyValidationError,
        match="two distinct venues",
    ):
        FragmentedMarketTopology(
            MarketFragmentationId(UUID(int=3)),
            economic,
            (profile_a, profile_b),
            _interval(2, 15),
            _topology_evidence(3),
        )


def test_fragmentation_rejects_interval_not_covered_by_every_profile() -> None:
    economic = _economic(1)
    profile_a = _profile(
        profile_value=1,
        subject=EconomicVenueMarketTopologyScope(economic, _venue("venue-a")),
        interval=_interval(1, 10),
    )
    profile_b = _profile(
        profile_value=2,
        subject=EconomicVenueMarketTopologyScope(economic, _venue("venue-b")),
        interval=_interval(1, 20),
    )

    with pytest.raises(
        UniversalMarketTopologyValidationError,
        match="covered by every component",
    ):
        FragmentedMarketTopology(
            MarketFragmentationId(UUID(int=4)),
            economic,
            (profile_a, profile_b),
            _interval(5, 15),
            _topology_evidence(4),
        )


def test_profiles_and_fragmentation_are_frozen() -> None:
    profile = _profile(
        profile_value=1,
        subject=VenueMarketTopologyScope(_venue("venue-a")),
    )

    with pytest.raises(FrozenInstanceError):
        profile.transparency = MarketTransparency.DARK  # type: ignore[misc]
