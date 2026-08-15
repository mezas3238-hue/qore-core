from __future__ import annotations

from dataclasses import fields
from datetime import UTC, datetime
from inspect import getsource
from typing import Any, cast
from uuid import UUID

import pytest

import qore.infrastructure.universal_market_topology as topology_module
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


def _economic(value: int = 1) -> EconomicIdentityId:
    return EconomicIdentityId(UUID(int=value))


def _venue(value: str = "venue-a") -> MarketVenueCode:
    return MarketVenueCode(value)


def _interval(
    start: int = 1,
    end: int | None = 20,
) -> MarketTopologyEffectiveInterval:
    return MarketTopologyEffectiveInterval(
        datetime(2026, 2, start, tzinfo=UTC),
        datetime(2026, 2, end, tzinfo=UTC) if end is not None else None,
    )


def _listing() -> ListingIdentity:
    return ListingIdentity(
        listing_id=ListingIdentityId(UUID(int=100)),
        economic_identity_id=_economic(),
        venue=_venue(),
        display_symbol="TEST",
        valid_from=datetime(2026, 2, 1, tzinfo=UTC),
        valid_until=datetime(2026, 2, 28, tzinfo=UTC),
        evidence_ref=IdentityEvidenceRef(UUID(int=200)),
    )


def _profile(
    value: int = 1,
    *,
    subject: object | None = None,
    mechanisms: tuple[MarketInteractionMechanism, ...] = (
        MarketInteractionMechanism.CENTRAL_LIMIT_ORDER_BOOK,
    ),
) -> MarketTopologyProfile:
    subject_value = (
        subject
        if subject is not None
        else EconomicVenueMarketTopologyScope(_economic(), _venue())
    )
    return MarketTopologyProfile(
        profile_id=MarketTopologyProfileId(UUID(int=value)),
        subject=cast(Any, subject_value),
        mechanisms=mechanisms,
        effective_interval=_interval(),
        evidence_ref=MarketTopologyEvidenceRef(UUID(int=value + 1000)),
    )


@pytest.mark.parametrize(
    ("factory", "message"),
    [
        (
            lambda: EconomicMarketTopologyScope(cast(Any, UUID(int=1))),
            "EconomicIdentityId",
        ),
        (
            lambda: ListingMarketTopologyScope(cast(Any, _economic())),
            "ListingIdentity",
        ),
        (
            lambda: VenueMarketTopologyScope(cast(Any, "venue-a")),
            "MarketVenueCode",
        ),
        (
            lambda: EconomicVenueMarketTopologyScope(
                cast(Any, UUID(int=1)),
                _venue(),
            ),
            "EconomicIdentityId",
        ),
        (
            lambda: EconomicVenueMarketTopologyScope(
                _economic(),
                cast(Any, "venue-a"),
            ),
            "MarketVenueCode",
        ),
    ],
)
def test_topology_scopes_fail_closed_on_owner_type_laundering(
    factory: object,
    message: str,
) -> None:
    with pytest.raises(UniversalMarketTopologyValidationError, match=message):
        cast(Any, factory)()


def test_effective_interval_rejects_naive_timestamp() -> None:
    with pytest.raises(
        UniversalMarketTopologyValidationError,
        match="timezone-aware",
    ):
        MarketTopologyEffectiveInterval(
            cast(Any, datetime(2026, 1, 1)),
            datetime(2026, 1, 2, tzinfo=UTC),
        )


def test_effective_interval_rejects_non_positive_span() -> None:
    instant = datetime(2026, 1, 1, tzinfo=UTC)
    with pytest.raises(
        UniversalMarketTopologyValidationError,
        match="must be after effective_from",
    ):
        MarketTopologyEffectiveInterval(instant, instant)


def test_profile_requires_non_empty_mechanisms() -> None:
    with pytest.raises(
        UniversalMarketTopologyValidationError,
        match="non-empty immutable tuple",
    ):
        _profile(mechanisms=())


def test_profile_rejects_duplicate_mechanisms() -> None:
    with pytest.raises(
        UniversalMarketTopologyValidationError,
        match="mechanisms must be unique",
    ):
        _profile(
            mechanisms=(
                MarketInteractionMechanism.AUCTION,
                MarketInteractionMechanism.AUCTION,
            )
        )


def test_profile_rejects_wrong_mechanism_type() -> None:
    with pytest.raises(
        UniversalMarketTopologyValidationError,
        match="MarketInteractionMechanism",
    ):
        _profile(mechanisms=(cast(Any, "auction"),))


def test_profile_rejects_arbitrary_subject() -> None:
    with pytest.raises(
        UniversalMarketTopologyValidationError,
        match="supported typed topology scope",
    ):
        _profile(subject=cast(Any, _economic()))


def test_profile_rejects_mutable_mechanism_collection() -> None:
    with pytest.raises(
        UniversalMarketTopologyValidationError,
        match="immutable tuple",
    ):
        MarketTopologyProfile(
            profile_id=MarketTopologyProfileId(UUID(int=1)),
            subject=EconomicMarketTopologyScope(_economic()),
            mechanisms=cast(Any, [MarketInteractionMechanism.BILATERAL]),
            effective_interval=_interval(),
            evidence_ref=MarketTopologyEvidenceRef(UUID(int=2)),
        )


def test_profile_rejects_duplicate_stage_qualification() -> None:
    with pytest.raises(
        UniversalMarketTopologyValidationError,
        match="stages must be unique",
    ):
        MarketTopologyProfile(
            profile_id=MarketTopologyProfileId(UUID(int=1)),
            subject=EconomicMarketTopologyScope(_economic()),
            mechanisms=(MarketInteractionMechanism.BILATERAL,),
            effective_interval=_interval(),
            evidence_ref=MarketTopologyEvidenceRef(UUID(int=2)),
            stages=(MarketStage.PRIMARY, MarketStage.PRIMARY),
        )


def test_profile_rejects_wrong_stage_type() -> None:
    with pytest.raises(
        UniversalMarketTopologyValidationError,
        match="MarketStage",
    ):
        MarketTopologyProfile(
            profile_id=MarketTopologyProfileId(UUID(int=1)),
            subject=EconomicMarketTopologyScope(_economic()),
            mechanisms=(MarketInteractionMechanism.BILATERAL,),
            effective_interval=_interval(),
            evidence_ref=MarketTopologyEvidenceRef(UUID(int=2)),
            stages=(cast(Any, "primary"),),
        )


def test_profile_rejects_wrong_transparency_type() -> None:
    with pytest.raises(
        UniversalMarketTopologyValidationError,
        match="MarketTransparency",
    ):
        MarketTopologyProfile(
            profile_id=MarketTopologyProfileId(UUID(int=1)),
            subject=VenueMarketTopologyScope(_venue()),
            mechanisms=(MarketInteractionMechanism.QUOTE_DRIVEN,),
            effective_interval=_interval(),
            evidence_ref=MarketTopologyEvidenceRef(UUID(int=2)),
            transparency=cast(Any, "dark"),
        )


def test_profile_rejects_wrong_infrastructure_context_type() -> None:
    with pytest.raises(
        UniversalMarketTopologyValidationError,
        match="MarketInfrastructureContext",
    ):
        MarketTopologyProfile(
            profile_id=MarketTopologyProfileId(UUID(int=1)),
            subject=VenueMarketTopologyScope(_venue()),
            mechanisms=(MarketInteractionMechanism.QUOTE_DRIVEN,),
            effective_interval=_interval(),
            evidence_ref=MarketTopologyEvidenceRef(UUID(int=2)),
            infrastructure_context=cast(Any, "on-chain"),
        )


def test_listing_profile_cannot_extend_beyond_listing_end() -> None:
    with pytest.raises(
        UniversalMarketTopologyValidationError,
        match="within listing validity",
    ):
        MarketTopologyProfile(
            profile_id=MarketTopologyProfileId(UUID(int=1)),
            subject=ListingMarketTopologyScope(_listing()),
            mechanisms=(MarketInteractionMechanism.CENTRAL_LIMIT_ORDER_BOOK,),
            effective_interval=MarketTopologyEffectiveInterval(
                datetime(2026, 2, 1, tzinfo=UTC),
                datetime(2026, 3, 1, tzinfo=UTC),
            ),
            evidence_ref=MarketTopologyEvidenceRef(UUID(int=2)),
        )


def test_fragmentation_requires_two_profiles() -> None:
    profile = _profile()
    with pytest.raises(
        UniversalMarketTopologyValidationError,
        match="at least two topology profiles",
    ):
        FragmentedMarketTopology(
            MarketFragmentationId(UUID(int=1)),
            _economic(),
            (profile,),
            _interval(2, 10),
            MarketTopologyEvidenceRef(UUID(int=3)),
        )


def test_fragmentation_rejects_duplicate_profile_identity() -> None:
    profile_a = _profile(
        1,
        subject=EconomicVenueMarketTopologyScope(_economic(), _venue("venue-a")),
    )
    profile_b = _profile(
        1,
        subject=EconomicVenueMarketTopologyScope(_economic(), _venue("venue-b")),
    )
    with pytest.raises(
        UniversalMarketTopologyValidationError,
        match="profile identities must be unique",
    ):
        FragmentedMarketTopology(
            MarketFragmentationId(UUID(int=1)),
            _economic(),
            (profile_a, profile_b),
            _interval(2, 10),
            MarketTopologyEvidenceRef(UUID(int=3)),
        )


def test_fragmentation_rejects_venue_wide_profile_as_instrument_component() -> None:
    profile_a = _profile(
        1,
        subject=VenueMarketTopologyScope(_venue("venue-a")),
    )
    profile_b = _profile(
        2,
        subject=EconomicVenueMarketTopologyScope(_economic(), _venue("venue-b")),
    )
    with pytest.raises(
        UniversalMarketTopologyValidationError,
        match="exact economic identity",
    ):
        FragmentedMarketTopology(
            MarketFragmentationId(UUID(int=1)),
            _economic(),
            (profile_a, profile_b),
            _interval(2, 10),
            MarketTopologyEvidenceRef(UUID(int=3)),
        )


def test_fragmentation_rejects_mutable_profile_collection() -> None:
    profile_a = _profile(
        1,
        subject=EconomicVenueMarketTopologyScope(_economic(), _venue("venue-a")),
    )
    profile_b = _profile(
        2,
        subject=EconomicVenueMarketTopologyScope(_economic(), _venue("venue-b")),
    )
    with pytest.raises(
        UniversalMarketTopologyValidationError,
        match="at least two topology profiles",
    ):
        FragmentedMarketTopology(
            MarketFragmentationId(UUID(int=1)),
            _economic(),
            cast(Any, [profile_a, profile_b]),
            _interval(2, 10),
            MarketTopologyEvidenceRef(UUID(int=3)),
        )


def test_topology_contracts_have_no_routing_matching_or_live_state_methods() -> None:
    forbidden = {
        "route",
        "best_venue",
        "match",
        "submit",
        "execute",
        "request_rfq",
        "swap",
        "observe",
        "order_book",
        "pool_reserves",
        "current_phase",
    }
    for type_ in (MarketTopologyProfile, FragmentedMarketTopology):
        assert forbidden.isdisjoint(dir(type_))


def test_topology_dataclasses_expose_no_arbitrary_dict_or_any_fields() -> None:
    for type_ in (
        MarketTopologyProfileId,
        MarketFragmentationId,
        MarketTopologyEvidenceRef,
        MarketTopologyEffectiveInterval,
        EconomicMarketTopologyScope,
        ListingMarketTopologyScope,
        VenueMarketTopologyScope,
        EconomicVenueMarketTopologyScope,
        MarketTopologyProfile,
        FragmentedMarketTopology,
    ):
        annotations = type_.__annotations__
        for field in fields(type_):
            annotation = str(annotations[field.name])
            assert "dict" not in annotation.lower()
            assert "Any" not in annotation
            assert "Callable" not in annotation


def test_source_has_no_provider_io_scheduler_or_nondeterminism() -> None:
    source = getsource(topology_module)
    forbidden_fragments = (
        "import requests",
        "import httpx",
        "urllib",
        "socket",
        "asyncio",
        "threading",
        "time.sleep",
        "datetime.now",
        "date.today",
        "uuid4",
        "random.",
        "eval(",
        "exec(",
    )
    for fragment in forbidden_fragments:
        assert fragment not in source


def test_orthogonal_enums_do_not_alias_one_another() -> None:
    mechanism_values = {item.value for item in MarketInteractionMechanism}
    stage_values = {item.value for item in MarketStage}
    transparency_values = {item.value for item in MarketTransparency}
    context_values = {item.value for item in MarketInfrastructureContext}

    assert mechanism_values.isdisjoint(stage_values)
    assert mechanism_values.isdisjoint(transparency_values)
    assert mechanism_values.isdisjoint(context_values)
    assert stage_values.isdisjoint(transparency_values)
    assert stage_values.isdisjoint(context_values)
    assert transparency_values.isdisjoint(context_values)
