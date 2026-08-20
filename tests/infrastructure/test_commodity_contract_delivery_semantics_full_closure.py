from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

import pytest

import qore.infrastructure.commodity_contract_delivery_semantics as commodity
import qore.infrastructure.derivative_contract_semantics as derivative
import qore.infrastructure.universal_instrument_identity as identity

_VALID_PARENT_STATE_CASES: tuple[
    tuple[derivative.DerivativeSettlementStyle, bool, bool, str], ...
] = (
    (derivative.DerivativeSettlementStyle.CASH, False, False, "cash"),
    (derivative.DerivativeSettlementStyle.PHYSICAL, True, False, "physical"),
    (derivative.DerivativeSettlementStyle.PHYSICAL, True, True, "physical"),
)


def _economic_id(seed: int) -> identity.EconomicIdentityId:
    return identity.EconomicIdentityId(UUID(int=seed))


def test_full_closure_parent_guard_basis_is_exactly_the_three_valid_states() -> None:
    assert _VALID_PARENT_STATE_CASES == (
        (derivative.DerivativeSettlementStyle.CASH, False, False, "cash"),
        (derivative.DerivativeSettlementStyle.PHYSICAL, True, False, "physical"),
        (derivative.DerivativeSettlementStyle.PHYSICAL, True, True, "physical"),
    )


@pytest.mark.parametrize(
    (
        "settlement_style",
        "include_physical_delivery",
        "include_first_notice",
        "expected_settlement_style",
    ),
    _VALID_PARENT_STATE_CASES,
)
def test_full_closure_commodity_futures_projection_breaks_parent_guard_correlation(
    settlement_style: derivative.DerivativeSettlementStyle,
    include_physical_delivery: bool,
    include_first_notice: bool,
    expected_settlement_style: str,
) -> None:
    first_notice_date = date(2026, 8, 17) if include_first_notice else None
    futures = derivative.FuturesContractTerms(
        terms_id=derivative.DerivativeTermsId(UUID(int=300)),
        instrument_identity_id=_economic_id(1),
        reference_identity_id=_economic_id(10),
        settlement_identity_id=_economic_id(12),
        contract_month=derivative.DerivativeContractMonth(2026, 9),
        expiry_date=date(2026, 8, 20),
        multiplier=derivative.DerivativeContractMultiplier(
            value=Decimal("1000"),
            unit_identity_id=_economic_id(11),
        ),
        settlement_style=settlement_style,
        evidence_ref=derivative.DerivativeEvidenceRef(UUID(int=400)),
        first_notice_date=first_notice_date,
        last_trade_date=date(2026, 8, 19),
    )
    reference = commodity.CommodityReferenceTerms(
        terms_id=commodity.CommodityTermsId(UUID(int=101)),
        reference_identity_id=_economic_id(10),
        commodity_class=commodity.CommodityClassCode("energy"),
        measurement_unit_identity_id=_economic_id(11),
        evidence_ref=commodity.CommodityEvidenceRef(UUID(int=201)),
    )
    physical_delivery = (
        commodity.CommodityPhysicalDeliveryTerms(
            (
                commodity.CommodityDeliveryAlternative(
                    grade=commodity.CommodityGradeCode("grade-a"),
                    location_identity_id=_economic_id(20),
                    method=commodity.CommodityDeliveryMethodCode(
                        "warehouse-receipt"
                    ),
                    window=commodity.CommodityDeliveryWindow(
                        date(2026, 8, 21),
                        date(2026, 8, 31),
                    ),
                ),
            )
        )
        if include_physical_delivery
        else None
    )
    terms = commodity.CommodityFuturesContractTerms(
        terms_id=commodity.CommodityTermsId(UUID(int=100)),
        futures=futures,
        commodity_reference=reference,
        evidence_ref=commodity.CommodityEvidenceRef(UUID(int=200)),
        physical_delivery=physical_delivery,
    )

    expected_first_notice = "2026-08-17" if include_first_notice else None
    expected_physical_delivery: tuple[object, ...] | None = (
        (
            (
                (
                    ("grade-a",),
                    (str(UUID(int=20)),),
                    ("warehouse-receipt",),
                    ("2026-08-21", "2026-08-31"),
                ),
            ),
        )
        if include_physical_delivery
        else None
    )

    assert terms.logical_values() == (
        "commodity-futures",
        (str(UUID(int=100)),),
        (
            "futures",
            (str(UUID(int=300)),),
            (str(UUID(int=1)),),
            (str(UUID(int=10)),),
            (str(UUID(int=12)),),
            (2026, 9),
            "2026-08-20",
            (
                "1000",
                (str(UUID(int=11)),),
            ),
            expected_settlement_style,
            (str(UUID(int=400)),),
            None,
            expected_first_notice,
            "2026-08-19",
        ),
        (
            "commodity-reference",
            (str(UUID(int=101)),),
            (str(UUID(int=10)),),
            ("energy",),
            (str(UUID(int=11)),),
            (str(UUID(int=201)),),
        ),
        expected_physical_delivery,
        (str(UUID(int=200)),),
    )
