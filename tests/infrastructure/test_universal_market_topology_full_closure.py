from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast
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


class _ForgedUUID(UUID):
    """Adversarial UUID subclass rejected by UMI11 exact-type wrappers."""


def _uuid_tuple(value: int) -> tuple[str, ...]:
    return (str(UUID(int=value)),)


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
        effective_from=datetime(2026, 4, start_day, tzinfo=UTC),
        effective_until=(
            datetime(2026, 4, end_day, tzinfo=UTC)
            if end_day is not None
            else None
        ),
    )


def _listing(
    *,
    listing_value: int = 100,
    economic_value: int = 10,
    venue: str = "venue-listed",
) -> ListingIdentity:
    return ListingIdentity(
        listing_id=ListingIdentityId(UUID(int=listing_value)),
        economic_identity_id=_economic(economic_value),
        venue=_venue(venue),
        display_symbol="UMI11",
        valid_from=datetime(2026, 4, 1, tzinfo=UTC),
        valid_until=datetime(2026, 4, 30, tzinfo=UTC),
        evidence_ref=_identity_evidence(listing_value + 1000),
    )


def _venue_profile(
    *,
    profile_value: int,
    economic_value: int,
    venue: str,
    mechanism: MarketInteractionMechanism,
) -> MarketTopologyProfile:
    return MarketTopologyProfile(
        profile_id=MarketTopologyProfileId(UUID(int=profile_value)),
        subject=EconomicVenueMarketTopologyScope(
            _economic(economic_value),
            _venue(venue),
        ),
        mechanisms=(mechanism,),
        effective_interval=_interval(1, 25),
        evidence_ref=_topology_evidence(profile_value + 2000),
    )


def _expected_economic_venue_profile(
    *,
    profile_value: int,
    economic_value: int,
    venue: str,
    mechanism: str,
) -> tuple[object, ...]:
    return (
        _uuid_tuple(profile_value),
        ("economic-venue", _uuid_tuple(economic_value), (venue,)),
        (mechanism,),
        (
            "2026-04-01T00:00:00.000000+00:00",
            "2026-04-25T00:00:00.000000+00:00",
        ),
        _uuid_tuple(profile_value + 2000),
        (),
        None,
        None,
    )


def test_uuid_wrappers_require_exact_uuid_type_and_preserve_exact_material() -> None:
    profile_id = MarketTopologyProfileId(UUID(int=1))
    fragmentation_id = MarketFragmentationId(UUID(int=2))
    evidence_ref = MarketTopologyEvidenceRef(UUID(int=3))

    assert profile_id.logical_values() == _uuid_tuple(1)
    assert fragmentation_id.logical_values() == _uuid_tuple(2)
    assert evidence_ref.logical_values() == _uuid_tuple(3)

    with pytest.raises(
        UniversalMarketTopologyValidationError,
        match="market topology profile id must be UUID",
    ):
        MarketTopologyProfileId(cast(Any, _ForgedUUID(int=1)))

    with pytest.raises(
        UniversalMarketTopologyValidationError,
        match="market fragmentation id must be UUID",
    ):
        MarketFragmentationId(cast(Any, _ForgedUUID(int=2)))

    with pytest.raises(
        UniversalMarketTopologyValidationError,
        match="market topology evidence ref must be UUID",
    ):
        MarketTopologyEvidenceRef(cast(Any, _ForgedUUID(int=3)))


def test_effective_interval_rejects_non_datetime_before_timezone_validation() -> None:
    with pytest.raises(
        UniversalMarketTopologyValidationError,
        match="topology effective_from must be datetime",
    ):
        MarketTopologyEffectiveInterval(
            effective_from=cast(Any, "2026-04-01T00:00:00Z"),
            effective_until=datetime(2026, 4, 2, tzinfo=UTC),
        )


def test_all_four_subject_scopes_have_independent_complete_projection_oracles() -> None:
    economic = _economic(10)
    venue = _venue("venue-otc")
    listing = _listing(
        listing_value=100,
        economic_value=10,
        venue="venue-listed",
    )

    economic_scope = EconomicMarketTopologyScope(economic)
    listing_scope = ListingMarketTopologyScope(listing)
    venue_scope = VenueMarketTopologyScope(venue)
    economic_venue_scope = EconomicVenueMarketTopologyScope(economic, venue)

    assert economic_scope.logical_values() == (
        "economic",
        _uuid_tuple(10),
    )
    assert listing_scope.logical_values() == (
        "listing",
        (
            _uuid_tuple(100),
            _uuid_tuple(10),
            ("venue-listed",),
            "UMI11",
            "2026-04-01T00:00:00.000000+00:00",
            "2026-04-30T00:00:00.000000+00:00",
            _uuid_tuple(1100),
        ),
    )
    assert venue_scope.logical_values() == (
        "venue",
        ("venue-otc",),
    )
    assert economic_venue_scope.logical_values() == (
        "economic-venue",
        _uuid_tuple(10),
        ("venue-otc",),
    )


def test_profile_complete_projection_is_independent_and_canonical() -> None:
    profile = MarketTopologyProfile(
        profile_id=MarketTopologyProfileId(UUID(int=200)),
        subject=EconomicVenueMarketTopologyScope(
            _economic(10),
            _venue("venue-b"),
        ),
        mechanisms=(
            MarketInteractionMechanism.QUOTE_DRIVEN,
            MarketInteractionMechanism.AUCTION,
            MarketInteractionMechanism.DEALER_RFQ,
        ),
        effective_interval=MarketTopologyEffectiveInterval(
            effective_from=datetime(2026, 4, 2, 3, 4, 5, 123456, tzinfo=UTC),
            effective_until=datetime(2026, 4, 20, 6, 7, 8, 654321, tzinfo=UTC),
        ),
        evidence_ref=_topology_evidence(300),
        stages=(MarketStage.SECONDARY, MarketStage.PRIMARY),
        transparency=MarketTransparency.MIXED,
        infrastructure_context=MarketInfrastructureContext.HYBRID,
    )

    expected = (
        _uuid_tuple(200),
        (
            "economic-venue",
            _uuid_tuple(10),
            ("venue-b",),
        ),
        (
            "auction",
            "dealer-rfq",
            "quote-driven",
        ),
        (
            "2026-04-02T03:04:05.123456+00:00",
            "2026-04-20T06:07:08.654321+00:00",
        ),
        _uuid_tuple(300),
        ("primary", "secondary"),
        "mixed",
        "hybrid",
    )

    assert profile.logical_values() == expected


def test_profile_none_optional_branches_are_material() -> None:
    profile = MarketTopologyProfile(
        profile_id=MarketTopologyProfileId(UUID(int=201)),
        subject=EconomicMarketTopologyScope(_economic(11)),
        mechanisms=(MarketInteractionMechanism.BILATERAL,),
        effective_interval=_interval(2, None),
        evidence_ref=_topology_evidence(301),
        transparency=None,
        infrastructure_context=None,
    )

    assert profile.logical_values() == (
        _uuid_tuple(201),
        ("economic", _uuid_tuple(11)),
        ("bilateral",),
        ("2026-04-02T00:00:00.000000+00:00", None),
        _uuid_tuple(301),
        (),
        None,
        None,
    )


def test_fragmentation_complete_projection_is_independent_and_canonical() -> None:
    profile_b = _venue_profile(
        profile_value=302,
        economic_value=42,
        venue="venue-b",
        mechanism=MarketInteractionMechanism.CENTRAL_LIMIT_ORDER_BOOK,
    )
    profile_a = _venue_profile(
        profile_value=301,
        economic_value=42,
        venue="venue-a",
        mechanism=MarketInteractionMechanism.DEALER_RFQ,
    )

    fragmented = FragmentedMarketTopology(
        fragmentation_id=MarketFragmentationId(UUID(int=400)),
        economic_identity_id=_economic(42),
        profiles=(profile_b, profile_a),
        effective_interval=_interval(5, 20),
        evidence_ref=_topology_evidence(500),
    )

    expected_profile_a = _expected_economic_venue_profile(
        profile_value=301,
        economic_value=42,
        venue="venue-a",
        mechanism="dealer-rfq",
    )
    expected_profile_b = _expected_economic_venue_profile(
        profile_value=302,
        economic_value=42,
        venue="venue-b",
        mechanism="central-limit-order-book",
    )
    expected = (
        _uuid_tuple(400),
        _uuid_tuple(42),
        (expected_profile_a, expected_profile_b),
        (
            "2026-04-05T00:00:00.000000+00:00",
            "2026-04-20T00:00:00.000000+00:00",
        ),
        _uuid_tuple(500),
    )

    assert fragmented.logical_values() == expected
    assert fragmented.venues == (
        _venue("venue-a"),
        _venue("venue-b"),
    )


def test_profile_rejects_wrong_profile_id_type_directly() -> None:
    with pytest.raises(
        UniversalMarketTopologyValidationError,
        match="topology profile_id must be MarketTopologyProfileId",
    ):
        MarketTopologyProfile(
            profile_id=cast(Any, UUID(int=1)),
            subject=EconomicMarketTopologyScope(_economic(1)),
            mechanisms=(MarketInteractionMechanism.BILATERAL,),
            effective_interval=_interval(),
            evidence_ref=_topology_evidence(1),
        )


def test_profile_rejects_wrong_effective_interval_type_directly() -> None:
    with pytest.raises(
        UniversalMarketTopologyValidationError,
        match="topology effective_interval must be MarketTopologyEffectiveInterval",
    ):
        MarketTopologyProfile(
            profile_id=MarketTopologyProfileId(UUID(int=1)),
            subject=EconomicMarketTopologyScope(_economic(1)),
            mechanisms=(MarketInteractionMechanism.BILATERAL,),
            effective_interval=cast(Any, datetime(2026, 4, 1, tzinfo=UTC)),
            evidence_ref=_topology_evidence(1),
        )


def test_profile_rejects_wrong_evidence_ref_type_directly() -> None:
    with pytest.raises(
        UniversalMarketTopologyValidationError,
        match="topology evidence_ref must be MarketTopologyEvidenceRef",
    ):
        MarketTopologyProfile(
            profile_id=MarketTopologyProfileId(UUID(int=1)),
            subject=EconomicMarketTopologyScope(_economic(1)),
            mechanisms=(MarketInteractionMechanism.BILATERAL,),
            effective_interval=_interval(),
            evidence_ref=cast(Any, _identity_evidence(1)),
        )


def test_profile_rejects_mutable_stage_collection_directly() -> None:
    with pytest.raises(
        UniversalMarketTopologyValidationError,
        match="topology stages must be an immutable tuple",
    ):
        MarketTopologyProfile(
            profile_id=MarketTopologyProfileId(UUID(int=1)),
            subject=EconomicMarketTopologyScope(_economic(1)),
            mechanisms=(MarketInteractionMechanism.BILATERAL,),
            effective_interval=_interval(),
            evidence_ref=_topology_evidence(1),
            stages=cast(Any, [MarketStage.PRIMARY]),
        )


def _fragmentation_profiles() -> tuple[MarketTopologyProfile, MarketTopologyProfile]:
    return (
        _venue_profile(
            profile_value=601,
            economic_value=60,
            venue="venue-a",
            mechanism=MarketInteractionMechanism.DEALER_RFQ,
        ),
        _venue_profile(
            profile_value=602,
            economic_value=60,
            venue="venue-b",
            mechanism=MarketInteractionMechanism.CENTRAL_LIMIT_ORDER_BOOK,
        ),
    )


def test_fragmentation_rejects_wrong_fragmentation_id_type_directly() -> None:
    profiles = _fragmentation_profiles()

    with pytest.raises(
        UniversalMarketTopologyValidationError,
        match="fragmentation_id must be MarketFragmentationId",
    ):
        FragmentedMarketTopology(
            fragmentation_id=cast(Any, UUID(int=1)),
            economic_identity_id=_economic(60),
            profiles=profiles,
            effective_interval=_interval(5, 20),
            evidence_ref=_topology_evidence(700),
        )


def test_fragmentation_rejects_wrong_economic_identity_type_directly() -> None:
    profiles = _fragmentation_profiles()

    with pytest.raises(
        UniversalMarketTopologyValidationError,
        match="fragmentation economic_identity_id must be EconomicIdentityId",
    ):
        FragmentedMarketTopology(
            fragmentation_id=MarketFragmentationId(UUID(int=600)),
            economic_identity_id=cast(Any, UUID(int=60)),
            profiles=profiles,
            effective_interval=_interval(5, 20),
            evidence_ref=_topology_evidence(700),
        )


def test_fragmentation_rejects_wrong_profile_element_type_directly() -> None:
    profile_a, _ = _fragmentation_profiles()

    with pytest.raises(
        UniversalMarketTopologyValidationError,
        match="fragmented topology profiles must contain MarketTopologyProfile",
    ):
        FragmentedMarketTopology(
            fragmentation_id=MarketFragmentationId(UUID(int=600)),
            economic_identity_id=_economic(60),
            profiles=cast(Any, (profile_a, "not-a-profile")),
            effective_interval=_interval(5, 20),
            evidence_ref=_topology_evidence(700),
        )


def test_fragmentation_rejects_wrong_effective_interval_type_directly() -> None:
    profiles = _fragmentation_profiles()

    with pytest.raises(
        UniversalMarketTopologyValidationError,
        match="fragmentation effective_interval must be MarketTopologyEffectiveInterval",
    ):
        FragmentedMarketTopology(
            fragmentation_id=MarketFragmentationId(UUID(int=600)),
            economic_identity_id=_economic(60),
            profiles=profiles,
            effective_interval=cast(Any, datetime(2026, 4, 5, tzinfo=UTC)),
            evidence_ref=_topology_evidence(700),
        )


def test_fragmentation_rejects_wrong_evidence_ref_type_directly() -> None:
    profiles = _fragmentation_profiles()

    with pytest.raises(
        UniversalMarketTopologyValidationError,
        match="fragmentation evidence_ref must be MarketTopologyEvidenceRef",
    ):
        FragmentedMarketTopology(
            fragmentation_id=MarketFragmentationId(UUID(int=600)),
            economic_identity_id=_economic(60),
            profiles=profiles,
            effective_interval=_interval(5, 20),
            evidence_ref=cast(Any, _identity_evidence(700)),
        )
