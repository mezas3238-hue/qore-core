from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

import pytest

from qore.infrastructure.commodity_contract_delivery_semantics import (
    CommodityEvidenceRef,
    CommodityTermsId,
)
from qore.infrastructure.specialized_commodity_semantics import (
    FreightTerms,
    FreightTransactionKind,
    FreightWorldscalePoints,
    SpecializedCommodityValidationError,
)
from qore.infrastructure.universal_instrument_identity import EconomicIdentityId


def test_freight_instrument_and_route_identities_must_differ() -> None:
    shared_identity = EconomicIdentityId(UUID("00000000-0000-0000-0000-000000000041"))

    with pytest.raises(SpecializedCommodityValidationError, match="must differ"):
        FreightTerms(
            terms_id=CommodityTermsId(
                UUID("00000000-0000-0000-0000-000000000040")
            ),
            instrument_identity_id=shared_identity,
            route_identity_id=shared_identity,
            kind=FreightTransactionKind.WET_VOYAGE_CHARTER,
            calculation_start_date=date(2027, 2, 1),
            calculation_end_date=date(2027, 2, 28),
            evidence_ref=CommodityEvidenceRef(
                UUID("00000000-0000-0000-0000-000000000043")
            ),
            worldscale_points=FreightWorldscalePoints(Decimal("100")),
        )
