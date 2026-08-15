from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from qore.infrastructure.universal_instrument_identity import MarketVenueCode
from qore.infrastructure.universal_market_topology import (
    MarketInteractionMechanism,
    MarketTopologyEffectiveInterval,
    MarketTopologyEvidenceRef,
    MarketTopologyProfile,
    MarketTopologyProfileId,
    VenueMarketTopologyScope,
)


def test_venue_scoped_profile_projects_exact_venue_without_economic_claim() -> None:
    venue = MarketVenueCode("venue-only")
    profile = MarketTopologyProfile(
        profile_id=MarketTopologyProfileId(UUID(int=1)),
        subject=VenueMarketTopologyScope(venue),
        mechanisms=(MarketInteractionMechanism.AUCTION,),
        effective_interval=MarketTopologyEffectiveInterval(
            effective_from=datetime(2026, 1, 1, tzinfo=UTC),
            effective_until=datetime(2026, 2, 1, tzinfo=UTC),
        ),
        evidence_ref=MarketTopologyEvidenceRef(UUID(int=2)),
    )

    assert profile.venue == venue
    assert profile.economic_identity_id is None
