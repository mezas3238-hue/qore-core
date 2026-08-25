from decimal import Decimal

from qore.infrastructure.insurance_linked_risk_transfer_semantics import (
    InsuranceLinkedEffectMagnitude,
    InsuranceLinkedEffectUnitCode,
    InsuranceLinkedTriggerThreshold,
    InsuranceLinkedTriggerUnitCode,
)


def test_extreme_positive_exponent_uses_compact_representation() -> None:
    threshold = InsuranceLinkedTriggerThreshold(
        Decimal("1E+100000000"),
        InsuranceLinkedTriggerUnitCode("index-points"),
    )
    magnitude = InsuranceLinkedEffectMagnitude(
        Decimal("1E+100000000"),
        InsuranceLinkedEffectUnitCode("index-points"),
    )

    assert threshold.logical_values()[0] == "1e+100000000"
    assert magnitude.logical_values()[0] == "1e+100000000"


def test_extreme_negative_exponent_uses_compact_representation() -> None:
    threshold = InsuranceLinkedTriggerThreshold(
        Decimal("1E-100000000"),
        InsuranceLinkedTriggerUnitCode("index-points"),
    )
    magnitude = InsuranceLinkedEffectMagnitude(
        Decimal("1E-100000000"),
        InsuranceLinkedEffectUnitCode("index-points"),
    )

    assert threshold.logical_values()[0] == "1e-100000000"
    assert magnitude.logical_values()[0] == "1e-100000000"
