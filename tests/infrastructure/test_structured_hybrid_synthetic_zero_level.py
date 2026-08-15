from decimal import Decimal
from uuid import UUID

from qore.infrastructure.structured_hybrid_synthetic_semantics import (
    StructuredContractLevel,
    StructuredContractLevelKind,
    StructuredLevelUnitCode,
)
from qore.infrastructure.universal_instrument_identity import EconomicIdentityId


def test_zero_structured_rate_level_is_valid_and_canonical() -> None:
    level = StructuredContractLevel(
        value=Decimal("0.000"),
        kind=StructuredContractLevelKind.RATE,
        reference_identity_id=EconomicIdentityId(UUID(int=1)),
        unit=StructuredLevelUnitCode("decimal-rate"),
    )

    assert level.logical_values()[0] == "0"
