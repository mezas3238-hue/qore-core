from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

import pytest

from qore.infrastructure.commodity_contract_delivery_semantics import (
    CommodityContractValidationError,
    CommodityDeliveryAlternative,
    CommodityDeliveryMethodCode,
    CommodityDeliveryWindow,
    CommodityEvidenceRef,
    CommodityFamilyCode,
    CommodityFuturesContractTerms,
    CommodityGradeCode,
    CommodityPhysicalDeliveryTerms,
    CommodityReferenceTerms,
    CommodityTermsId,
)
from qore.infrastructure.derivative_contract_semantics import (
    DerivativeContractMonth,
    DerivativeContractMultiplier,
    DerivativeEvidenceRef,
    DerivativeSettlementStyle,
    DerivativeTermsId,
    FuturesContractTerms,
)
from qore.infrastructure.universal_instrument_identity import EconomicIdentityId


def _economic_id(seed: int) -> EconomicIdentityId:
    return EconomicIdentityId(UUID(int=seed))


def _terms_id(seed: int = 100) -> CommodityTermsId:
    return CommodityTermsId(UUID(int=seed))


def _evidence(seed: int = 200) -> CommodityEvidenceRef:
    return CommodityEvidenceRef(UUID(int=seed))


def _derivative_terms_id(seed: int = 300) -> DerivativeTermsId:
    return DerivativeTermsId(UUID(int=seed))


def _derivative_evidence(seed: int = 400) -> DerivativeEvidenceRef:
    return DerivativeEvidenceRef(UUID(int=seed))


def _commodity_reference(
    *,
    reference_seed: int = 10,
    unit_seed: int = 11,
    family: str = "energy",
) -> CommodityReferenceTerms:
    return CommodityReferenceTerms(
        terms_id=_terms_id(101),
        reference_identity_id=_economic_id(reference_seed),
        family=CommodityFamilyCode(family),
        measurement_unit_identity_id=_economic_id(unit_seed),
        evidence_ref=_evidence(201),
    )


def _futures(
    *,
    reference_seed: int = 10,
    unit_seed: int = 11,
    settlement_style: DerivativeSettlementStyle = DerivativeSettlementStyle.PHYSICAL,
) -> FuturesContractTerms:
    return FuturesContractTerms(
        terms_id=_derivative_terms_id(),
        instrument_identity_id=_economic_id(1),
        reference_identity_id=_economic_id(reference_seed),
        settlement_identity_id=_economic_id(12),
        contract_month=DerivativeContractMonth(2026, 9),
        expiry_date=date(2026, 8, 20),
        multiplier=DerivativeContractMultiplier(
            value=Decimal("1000"),
            unit_identity_id=_economic_id(unit_seed),
        ),
        settlement_style=settlement_style,
        evidence_ref=_derivative_evidence(),
        first_notice_date=(
            date(2026, 8, 17)
            if settlement_style is DerivativeSettlementStyle.PHYSICAL
            else None
        ),
        last_trade_date=date(2026, 8, 19),
    )


def _alternative(
    *,
    grade: str = "grade-a",
    location_seed: int = 20,
    method: str = "warehouse-receipt",
    start_date: date = date(2026, 8, 21),
    end_date: date = date(2026, 8, 31),
) -> CommodityDeliveryAlternative:
    return CommodityDeliveryAlternative(
        grade=CommodityGradeCode(grade),
        location_identity_id=_economic_id(location_seed),
        method=CommodityDeliveryMethodCode(method),
        window=CommodityDeliveryWindow(start_date, end_date),
    )


def _physical_delivery(
    *alternatives: CommodityDeliveryAlternative,
) -> CommodityPhysicalDeliveryTerms:
    retained = alternatives or (_alternative(),)
    return CommodityPhysicalDeliveryTerms(tuple(retained))


def _commodity_futures(
    *,
    futures: FuturesContractTerms | None = None,
    reference: CommodityReferenceTerms | None = None,
    physical_delivery: CommodityPhysicalDeliveryTerms | None = None,
) -> CommodityFuturesContractTerms:
    actual_futures = futures or _futures()
    actual_reference = reference or _commodity_reference()
    if physical_delivery is None and (
        actual_futures.settlement_style is DerivativeSettlementStyle.PHYSICAL
    ):
        physical_delivery = _physical_delivery()
    return CommodityFuturesContractTerms(
        terms_id=_terms_id(),
        futures=actual_futures,
        commodity_reference=actual_reference,
        evidence_ref=_evidence(),
        physical_delivery=physical_delivery,
    )


def test_local_ids_are_uuid_backed_and_not_economic_identity() -> None:
    terms_id = _terms_id()
    evidence = _evidence()

    assert terms_id.logical_values() == (str(UUID(int=100)),)
    assert evidence.logical_values() == (str(UUID(int=200)),)
    assert not isinstance(terms_id, EconomicIdentityId)
    assert not isinstance(evidence, EconomicIdentityId)


@pytest.mark.parametrize(
    ("factory", "bad_value"),
    [
        (CommodityTermsId, "not-a-uuid"),
        (CommodityEvidenceRef, "not-a-uuid"),
    ],
)
def test_local_uuid_wrappers_reject_raw_text(
    factory: type[Any],
    bad_value: str,
) -> None:
    with pytest.raises(CommodityContractValidationError):
        factory(cast(Any, bad_value))


def test_commodity_reference_retains_family_identity_and_measurement_unit() -> None:
    terms = _commodity_reference(family="energy")

    assert terms.logical_values()[0] == "commodity-reference"
    assert terms.logical_values()[2] == _economic_id(10).logical_values()
    assert terms.logical_values()[3] == ("energy",)
    assert terms.logical_values()[4] == _economic_id(11).logical_values()


def test_commodity_reference_rejects_raw_identity_and_self_unit() -> None:
    with pytest.raises(CommodityContractValidationError, match="reference identity"):
        CommodityReferenceTerms(
            terms_id=_terms_id(),
            reference_identity_id=cast(Any, UUID(int=10)),
            family=CommodityFamilyCode("energy"),
            measurement_unit_identity_id=_economic_id(11),
            evidence_ref=_evidence(),
        )

    with pytest.raises(CommodityContractValidationError, match="must differ"):
        CommodityReferenceTerms(
            terms_id=_terms_id(),
            reference_identity_id=_economic_id(10),
            family=CommodityFamilyCode("energy"),
            measurement_unit_identity_id=_economic_id(10),
            evidence_ref=_evidence(),
        )


def test_family_grade_and_delivery_method_are_distinct_typed_semantics() -> None:
    family = CommodityFamilyCode("energy")
    grade = CommodityGradeCode("wti-spec")
    method = CommodityDeliveryMethodCode("pipeline-transfer")

    assert family.logical_values() == ("energy",)
    assert grade.logical_values() == ("wti-spec",)
    assert method.logical_values() == ("pipeline-transfer",)
    assert type(family) is not type(grade)
    assert type(grade) is not type(method)


def test_typed_code_fields_reject_raw_string_laundering() -> None:
    with pytest.raises(CommodityContractValidationError):
        CommodityReferenceTerms(
            terms_id=_terms_id(),
            reference_identity_id=_economic_id(10),
            family=cast(Any, "energy"),
            measurement_unit_identity_id=_economic_id(11),
            evidence_ref=_evidence(),
        )

    with pytest.raises(CommodityContractValidationError):
        CommodityDeliveryAlternative(
            grade=cast(Any, "grade-a"),
            location_identity_id=_economic_id(20),
            method=CommodityDeliveryMethodCode("warehouse-receipt"),
            window=CommodityDeliveryWindow(date(2026, 8, 21), date(2026, 8, 31)),
        )


def test_codes_reject_credential_like_or_noncanonical_material() -> None:
    for value in ("token=abc", "Bearer-token", "UPPER", " leading", "a/b"):
        with pytest.raises(CommodityContractValidationError):
            CommodityGradeCode(value)


def test_delivery_window_retains_roles_and_rejects_reverse_chronology() -> None:
    window = CommodityDeliveryWindow(date(2026, 8, 21), date(2026, 8, 31))

    assert window.logical_values() == ("2026-08-21", "2026-08-31")

    with pytest.raises(CommodityContractValidationError, match="end_date"):
        CommodityDeliveryWindow(date(2026, 9, 1), date(2026, 8, 31))


def test_delivery_window_rejects_datetime_laundering() -> None:
    with pytest.raises(CommodityContractValidationError, match="start_date must be date"):
        CommodityDeliveryWindow(
            cast(date, datetime(2026, 8, 21, tzinfo=UTC)),
            date(2026, 8, 31),
        )

    with pytest.raises(CommodityContractValidationError, match="end_date must be date"):
        CommodityDeliveryWindow(
            date(2026, 8, 21),
            cast(date, datetime(2026, 8, 31, tzinfo=UTC)),
        )


def test_delivery_alternative_retains_grade_location_method_and_window() -> None:
    alternative = _alternative(
        grade="grade-b",
        location_seed=22,
        method="pipeline-transfer",
    )

    assert alternative.logical_values() == (
        ("grade-b",),
        _economic_id(22).logical_values(),
        ("pipeline-transfer",),
        ("2026-08-21", "2026-08-31"),
    )


def test_delivery_location_requires_economic_identity() -> None:
    with pytest.raises(CommodityContractValidationError, match="location identity"):
        CommodityDeliveryAlternative(
            grade=CommodityGradeCode("grade-a"),
            location_identity_id=cast(Any, UUID(int=20)),
            method=CommodityDeliveryMethodCode("warehouse-receipt"),
            window=CommodityDeliveryWindow(date(2026, 8, 21), date(2026, 8, 31)),
        )


def test_physical_delivery_requires_nonempty_immutable_tuple() -> None:
    with pytest.raises(CommodityContractValidationError, match="non-empty tuple"):
        CommodityPhysicalDeliveryTerms(())

    with pytest.raises(CommodityContractValidationError, match="non-empty tuple"):
        CommodityPhysicalDeliveryTerms(cast(Any, [_alternative()]))


def test_physical_delivery_rejects_duplicate_alternatives() -> None:
    alternative = _alternative()

    with pytest.raises(CommodityContractValidationError, match="must be unique"):
        CommodityPhysicalDeliveryTerms((alternative, alternative))


def test_physical_delivery_canonicalizes_caller_order() -> None:
    first = _alternative(grade="grade-a", location_seed=21)
    second = _alternative(grade="grade-b", location_seed=20)

    left = CommodityPhysicalDeliveryTerms((second, first))
    right = CommodityPhysicalDeliveryTerms((first, second))

    assert left.alternatives == right.alternatives
    assert left.logical_values() == right.logical_values()


def test_commodity_futures_reuses_umi05_futures_terms_without_flattening() -> None:
    futures = _futures()
    terms = _commodity_futures(futures=futures)

    assert terms.futures is futures
    assert terms.logical_values()[2] == futures.logical_values()
    assert terms.futures.contract_month == DerivativeContractMonth(2026, 9)
    assert terms.futures.expiry_date == date(2026, 8, 20)
    assert terms.futures.first_notice_date == date(2026, 8, 17)
    assert terms.futures.last_trade_date == date(2026, 8, 19)


def test_commodity_futures_rejects_reference_identity_mismatch() -> None:
    with pytest.raises(CommodityContractValidationError, match="reference identity"):
        _commodity_futures(reference=_commodity_reference(reference_seed=99))


def test_commodity_futures_rejects_measurement_unit_mismatch() -> None:
    with pytest.raises(CommodityContractValidationError, match="multiplier unit"):
        _commodity_futures(reference=_commodity_reference(unit_seed=99))


def test_physical_futures_require_explicit_physical_delivery_terms() -> None:
    futures = _futures(settlement_style=DerivativeSettlementStyle.PHYSICAL)

    with pytest.raises(
        CommodityContractValidationError,
        match="require explicit physical delivery",
    ):
        CommodityFuturesContractTerms(
            terms_id=_terms_id(),
            futures=futures,
            commodity_reference=_commodity_reference(),
            evidence_ref=_evidence(),
            physical_delivery=None,
        )


def test_cash_futures_reject_physical_delivery_terms() -> None:
    futures = _futures(settlement_style=DerivativeSettlementStyle.CASH)

    with pytest.raises(
        CommodityContractValidationError,
        match="must not carry physical delivery",
    ):
        CommodityFuturesContractTerms(
            terms_id=_terms_id(),
            futures=futures,
            commodity_reference=_commodity_reference(),
            evidence_ref=_evidence(),
            physical_delivery=_physical_delivery(),
        )


def test_cash_futures_are_representable_without_physical_delivery() -> None:
    futures = _futures(settlement_style=DerivativeSettlementStyle.CASH)
    terms = _commodity_futures(futures=futures, physical_delivery=None)

    assert terms.futures.settlement_style is DerivativeSettlementStyle.CASH
    assert terms.physical_delivery is None
    assert terms.logical_values()[4] is None


def test_delivery_location_cannot_launder_contract_commodity_or_unit_identity() -> None:
    for seed in (1, 10, 11):
        with pytest.raises(CommodityContractValidationError, match="location identity"):
            _commodity_futures(
                physical_delivery=_physical_delivery(_alternative(location_seed=seed))
            )


def test_delivery_window_does_not_invent_expiry_or_notice_chronology() -> None:
    futures = _futures()
    alternative = _alternative(
        start_date=date(2026, 8, 1),
        end_date=date(2026, 8, 10),
    )
    terms = _commodity_futures(
        futures=futures,
        physical_delivery=_physical_delivery(alternative),
    )

    assert terms.physical_delivery is not None
    assert terms.physical_delivery.alternatives[0].window.end_date < futures.expiry_date


def test_terms_are_frozen() -> None:
    reference = _commodity_reference()
    terms = _commodity_futures(reference=reference)

    with pytest.raises(FrozenInstanceError):
        setattr(reference, "family", CommodityFamilyCode("metals"))
    with pytest.raises(FrozenInstanceError):
        setattr(terms, "physical_delivery", None)


def test_no_candidate_type_exposes_lifecycle_logistics_settlement_or_execution_engine() -> None:
    reference = _commodity_reference()
    physical = _physical_delivery()
    terms = _commodity_futures(reference=reference, physical_delivery=physical)

    forbidden = (
        "record_lifecycle",
        "resolve_calendar",
        "select_delivery",
        "calculate_storage",
        "calculate_basis",
        "ship",
        "transfer_title",
        "warehouse",
        "settle",
        "execute",
        "apply",
        "adjust_position",
        "adjust_inventory",
        "reserve_risk",
        "provider",
    )
    for obj in (reference, physical, terms):
        for name in forbidden:
            assert not hasattr(obj, name)


def test_logical_values_are_repeatable_and_secret_free() -> None:
    terms = _commodity_futures(
        physical_delivery=_physical_delivery(
            _alternative(grade="grade-a", location_seed=20),
            _alternative(grade="grade-b", location_seed=21),
        )
    )

    first = repr(terms.logical_values())
    second = repr(terms.logical_values())

    assert first == second
    lowered = first.lower()
    for marker in ("token=", "secret=", "password=", "bearer "):
        assert marker not in lowered
