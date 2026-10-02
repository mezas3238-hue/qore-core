from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

import pytest

from qore.infrastructure.commodity_contract_delivery_semantics import (
    CommodityClassCode,
    CommodityEvidenceRef,
    CommodityFuturesContractTerms,
    CommodityReferenceTerms,
    CommodityTermsId,
)
from qore.infrastructure.core_stack_v2.agricultural_instrument_identity import (
    AgriculturalCommodityClass,
    AgriculturalCommodityReferenceQualification,
    AgriculturalCropYearCode,
    AgriculturalCropYearReference,
    AgriculturalFuturesContractQualification,
    AgriculturalIdentityQualificationError,
    assert_agricultural_native_execution_identity,
)
from qore.infrastructure.derivative_contract_semantics import (
    DerivativeContractMonth,
    DerivativeContractMultiplier,
    DerivativeEvidenceRef,
    DerivativeSettlementStyle,
    DerivativeTermsId,
    FuturesContractTerms,
)
from qore.infrastructure.universal_instrument_identity import (
    EconomicIdentity,
    EconomicIdentityId,
    EconomicIdentityKind,
    IdentityConstructionKind,
    IdentityEvidenceRef,
    IdentityFamilyCode,
    ListingIdentity,
    ListingIdentityId,
    MarketVenueCode,
)

REF_ID = EconomicIdentityId(UUID("00000000-0000-4000-8000-000000000001"))
CONTRACT_ID = EconomicIdentityId(
    UUID("00000000-0000-4000-8000-000000000002")
)
UNIT_ID = EconomicIdentityId(UUID("00000000-0000-4000-8000-000000000003"))
USD_ID = EconomicIdentityId(UUID("00000000-0000-4000-8000-000000000004"))
REGION_ID = EconomicIdentityId(UUID("00000000-0000-4000-8000-000000000005"))
IDENTITY_EVIDENCE = IdentityEvidenceRef(
    UUID("00000000-0000-4000-8000-000000000011")
)
LISTING_EVIDENCE = IdentityEvidenceRef(
    UUID("00000000-0000-4000-8000-000000000012")
)
CROP_EVIDENCE = IdentityEvidenceRef(
    UUID("00000000-0000-4000-8000-000000000013")
)
COMMODITY_EVIDENCE = CommodityEvidenceRef(
    UUID("00000000-0000-4000-8000-000000000021")
)
DERIVATIVE_EVIDENCE = DerivativeEvidenceRef(
    UUID("00000000-0000-4000-8000-000000000031")
)


def _reference_identity(
    *,
    construction: IdentityConstructionKind = IdentityConstructionKind.NATIVE,
) -> EconomicIdentity:
    return EconomicIdentity(
        identity_id=REF_ID,
        kind=EconomicIdentityKind.REFERENCE_OBJECT,
        family=IdentityFamilyCode("commodities"),
        construction=construction,
        evidence_ref=IDENTITY_EVIDENCE,
    )


def _contract_identity(
    *,
    construction: IdentityConstructionKind = IdentityConstructionKind.NATIVE,
) -> EconomicIdentity:
    return EconomicIdentity(
        identity_id=CONTRACT_ID,
        kind=EconomicIdentityKind.TRADABLE_INSTRUMENT,
        family=IdentityFamilyCode("futures"),
        construction=construction,
        evidence_ref=IDENTITY_EVIDENCE,
    )


def _commodity_reference(
    *,
    commodity_class: str = "agriculture",
) -> CommodityReferenceTerms:
    return CommodityReferenceTerms(
        terms_id=CommodityTermsId(
            UUID("00000000-0000-4000-8000-000000000041")
        ),
        reference_identity_id=REF_ID,
        commodity_class=CommodityClassCode(commodity_class),
        measurement_unit_identity_id=UNIT_ID,
        evidence_ref=COMMODITY_EVIDENCE,
    )


def _agricultural_reference(
    *,
    commodity_class: str = "agriculture",
    agricultural_class: AgriculturalCommodityClass = (
        AgriculturalCommodityClass.AGRICULTURE
    ),
    crop_year: AgriculturalCropYearReference | None = None,
) -> AgriculturalCommodityReferenceQualification:
    return AgriculturalCommodityReferenceQualification(
        economic_identity=_reference_identity(),
        commodity_reference=_commodity_reference(
            commodity_class=commodity_class
        ),
        agricultural_class=agricultural_class,
        crop_year=crop_year,
    )


def _futures_terms(
    *,
    instrument_id: EconomicIdentityId = CONTRACT_ID,
    reference_id: EconomicIdentityId = REF_ID,
) -> FuturesContractTerms:
    return FuturesContractTerms(
        terms_id=DerivativeTermsId(
            UUID("00000000-0000-4000-8000-000000000051")
        ),
        instrument_identity_id=instrument_id,
        reference_identity_id=reference_id,
        settlement_identity_id=USD_ID,
        contract_month=DerivativeContractMonth(year=2027, month=7),
        expiry_date=date(2027, 7, 14),
        multiplier=DerivativeContractMultiplier(
            value=Decimal("5000"),
            unit_identity_id=UNIT_ID,
        ),
        settlement_style=DerivativeSettlementStyle.CASH,
        evidence_ref=DERIVATIVE_EVIDENCE,
        tick_value=None,
        first_notice_date=None,
        last_trade_date=date(2027, 7, 14),
    )


def _commodity_contract(
    *,
    futures: FuturesContractTerms | None = None,
    reference: CommodityReferenceTerms | None = None,
) -> CommodityFuturesContractTerms:
    return CommodityFuturesContractTerms(
        terms_id=CommodityTermsId(
            UUID("00000000-0000-4000-8000-000000000061")
        ),
        futures=futures or _futures_terms(),
        commodity_reference=reference or _commodity_reference(),
        evidence_ref=COMMODITY_EVIDENCE,
        physical_delivery=None,
    )


def _listing(
    *,
    economic_identity_id: EconomicIdentityId = CONTRACT_ID,
) -> ListingIdentity:
    return ListingIdentity(
        listing_id=ListingIdentityId(
            UUID("00000000-0000-4000-8000-000000000071")
        ),
        economic_identity_id=economic_identity_id,
        venue=MarketVenueCode("xcme"),
        display_symbol="TEST-CORN-JUL27",
        valid_from=datetime(2026, 1, 1, tzinfo=UTC),
        valid_until=None,
        evidence_ref=LISTING_EVIDENCE,
    )


def test_agricultural_reference_composes_umi02_and_umi07() -> None:
    qualification = _agricultural_reference()

    assert qualification.economic_identity.identity_id == REF_ID
    assert qualification.commodity_reference.reference_identity_id == REF_ID
    assert qualification.agricultural_class is (
        AgriculturalCommodityClass.AGRICULTURE
    )
    assert qualification.economic_identity.family.value == "commodities"
    assert len(qualification.logical_values()) == 5


@pytest.mark.parametrize(
    ("commodity_class", "agricultural_class"),
    (
        ("agriculture", AgriculturalCommodityClass.AGRICULTURE),
        ("softs", AgriculturalCommodityClass.SOFTS),
        ("livestock", AgriculturalCommodityClass.LIVESTOCK),
    ),
)
def test_owner_agricultural_classes_compose_without_new_identity_authority(
    commodity_class: str,
    agricultural_class: AgriculturalCommodityClass,
) -> None:
    qualification = _agricultural_reference(
        commodity_class=commodity_class,
        agricultural_class=agricultural_class,
    )

    assert qualification.commodity_reference.commodity_class.value == (
        commodity_class
    )


def test_crop_year_is_region_scoped_optional_context() -> None:
    crop_year = AgriculturalCropYearReference(
        code=AgriculturalCropYearCode("2026/27"),
        region_identity_id=REGION_ID,
        evidence_ref=CROP_EVIDENCE,
    )
    qualification = _agricultural_reference(crop_year=crop_year)

    assert qualification.crop_year == crop_year
    assert qualification.crop_year.region_identity_id == REGION_ID


def test_crop_year_code_rejects_free_form_or_empty_text() -> None:
    for value in ("", "2026 27", "2026?27"):
        with pytest.raises(
            AgriculturalIdentityQualificationError,
            match="crop-year code",
        ):
            AgriculturalCropYearCode(value)


def test_agricultural_reference_rejects_commodity_class_drift() -> None:
    with pytest.raises(
        AgriculturalIdentityQualificationError,
        match="agricultural class must match",
    ):
        _agricultural_reference(
            commodity_class="softs",
            agricultural_class=AgriculturalCommodityClass.AGRICULTURE,
        )


def test_agricultural_reference_rejects_noncommodity_umi_family() -> None:
    identity = EconomicIdentity(
        identity_id=REF_ID,
        kind=EconomicIdentityKind.REFERENCE_OBJECT,
        family=IdentityFamilyCode("futures"),
        construction=IdentityConstructionKind.NATIVE,
        evidence_ref=IDENTITY_EVIDENCE,
    )

    with pytest.raises(
        AgriculturalIdentityQualificationError,
        match="UMI commodities family",
    ):
        AgriculturalCommodityReferenceQualification(
            economic_identity=identity,
            commodity_reference=_commodity_reference(),
            agricultural_class=AgriculturalCommodityClass.AGRICULTURE,
        )


def test_dated_agricultural_futures_composes_umi_identity_listing_and_contract() -> None:
    reference = _agricultural_reference()
    qualification = AgriculturalFuturesContractQualification(
        economic_identity=_contract_identity(),
        listing=_listing(),
        agricultural_reference=reference,
        commodity_contract=_commodity_contract(
            reference=reference.commodity_reference
        ),
    )

    assert qualification.contract_year == 2027
    assert qualification.contract_month == 7
    assert qualification.listing.venue.value == "xcme"
    assert (
        qualification.commodity_contract.futures.instrument_identity_id
        == CONTRACT_ID
    )


def test_futures_listing_identity_mismatch_fails_closed() -> None:
    reference = _agricultural_reference()
    wrong_id = EconomicIdentityId(
        UUID("00000000-0000-4000-8000-000000000099")
    )

    with pytest.raises(
        AgriculturalIdentityQualificationError,
        match="listing must reference",
    ):
        AgriculturalFuturesContractQualification(
            economic_identity=_contract_identity(),
            listing=_listing(economic_identity_id=wrong_id),
            agricultural_reference=reference,
            commodity_contract=_commodity_contract(
                reference=reference.commodity_reference
            ),
        )


def test_futures_underlying_reference_mismatch_fails_closed() -> None:
    reference = _agricultural_reference()
    wrong_ref = EconomicIdentityId(
        UUID("00000000-0000-4000-8000-000000000098")
    )
    futures = _futures_terms(reference_id=wrong_ref)

    with pytest.raises(
        AgriculturalIdentityQualificationError,
        match="UMI-05 futures reference identity mismatch",
    ):
        AgriculturalFuturesContractQualification(
            economic_identity=_contract_identity(),
            listing=_listing(),
            agricultural_reference=reference,
            commodity_contract=CommodityFuturesContractTerms(
                terms_id=CommodityTermsId(
                    UUID("00000000-0000-4000-8000-000000000061")
                ),
                futures=futures,
                commodity_reference=CommodityReferenceTerms(
                    terms_id=CommodityTermsId(
                        UUID("00000000-0000-4000-8000-000000000062")
                    ),
                    reference_identity_id=wrong_ref,
                    commodity_class=CommodityClassCode("agriculture"),
                    measurement_unit_identity_id=UNIT_ID,
                    evidence_ref=COMMODITY_EVIDENCE,
                ),
                evidence_ref=COMMODITY_EVIDENCE,
                physical_delivery=None,
            ),
        )


def test_continuous_reference_cannot_be_execution_identity() -> None:
    continuous = EconomicIdentity(
        identity_id=EconomicIdentityId(
            UUID("00000000-0000-4000-8000-000000000090")
        ),
        kind=EconomicIdentityKind.REFERENCE_OBJECT,
        family=IdentityFamilyCode("futures"),
        construction=IdentityConstructionKind.CONTINUOUS_REFERENCE,
        evidence_ref=IDENTITY_EVIDENCE,
    )

    with pytest.raises(
        AgriculturalIdentityQualificationError,
        match="must be tradable instrument",
    ):
        assert_agricultural_native_execution_identity(continuous)


def test_native_futures_identity_is_eligible_for_execution_identity_layer() -> None:
    assert_agricultural_native_execution_identity(_contract_identity())


def test_synthetic_or_composite_contract_cannot_masquerade_as_dated_future() -> None:
    synthetic = EconomicIdentity(
        identity_id=CONTRACT_ID,
        kind=EconomicIdentityKind.TRADABLE_INSTRUMENT,
        family=IdentityFamilyCode("futures"),
        construction=IdentityConstructionKind.SYNTHETIC,
        evidence_ref=IDENTITY_EVIDENCE,
    )

    with pytest.raises(
        AgriculturalIdentityQualificationError,
        match="dated agricultural futures must be native identity",
    ):
        AgriculturalFuturesContractQualification(
            economic_identity=synthetic,
            listing=_listing(),
            agricultural_reference=_agricultural_reference(),
            commodity_contract=_commodity_contract(),
        )
