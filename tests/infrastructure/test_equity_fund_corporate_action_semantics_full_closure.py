from __future__ import annotations

from uuid import UUID

import pytest

from qore.infrastructure.equity_fund_corporate_action_semantics import (
    EquityFundEvidenceRef,
    EquityFundTermsId,
    EquityShareClassCode,
    FundNavBasis,
    FundNavBasisCode,
    FundVehicleKind,
    FundVehicleTerms,
)
from qore.infrastructure.universal_instrument_identity import EconomicIdentityId


_FUND_VEHICLE_KIND_CASES: tuple[tuple[FundVehicleKind, str], ...] = (
    (FundVehicleKind.ETF, "etf"),
    (FundVehicleKind.MUTUAL_FUND, "mutual-fund"),
    (FundVehicleKind.CLOSED_END_FUND, "closed-end-fund"),
    (FundVehicleKind.MONEY_MARKET_FUND, "money-market-fund"),
    (FundVehicleKind.LISTED_TRUST, "listed-trust"),
    (FundVehicleKind.REIT, "reit"),
)

_OPTIONAL_STATE_CASES: tuple[tuple[bool, bool], ...] = (
    (False, False),
    (True, False),
    (False, True),
    (True, True),
)


def test_full_closure_fund_vehicle_kind_matrix_matches_current_bounded_enum() -> None:
    assert {kind for kind, _ in _FUND_VEHICLE_KIND_CASES} == set(FundVehicleKind)
    assert {expected for _, expected in _FUND_VEHICLE_KIND_CASES} == {
        "etf",
        "mutual-fund",
        "closed-end-fund",
        "money-market-fund",
        "listed-trust",
        "reit",
    }


@pytest.mark.parametrize(
    ("vehicle_kind", "expected_kind"),
    _FUND_VEHICLE_KIND_CASES,
)
@pytest.mark.parametrize(
    ("include_share_class", "include_nav_basis"),
    _OPTIONAL_STATE_CASES,
)
def test_full_closure_fund_vehicle_projection_breaks_kind_and_optional_guard_correlation(
    vehicle_kind: FundVehicleKind,
    expected_kind: str,
    include_share_class: bool,
    include_nav_basis: bool,
) -> None:
    share_class = EquityShareClassCode("retail") if include_share_class else None
    nav_basis = (
        FundNavBasis(
            currency_identity_id=EconomicIdentityId(UUID(int=504)),
            unit_identity_id=EconomicIdentityId(UUID(int=505)),
            basis=FundNavBasisCode("per-share"),
            evidence_ref=EquityFundEvidenceRef(UUID(int=506)),
        )
        if include_nav_basis
        else None
    )
    terms = FundVehicleTerms(
        terms_id=EquityFundTermsId(UUID(int=501)),
        instrument_identity_id=EconomicIdentityId(UUID(int=502)),
        vehicle_kind=vehicle_kind,
        evidence_ref=EquityFundEvidenceRef(UUID(int=503)),
        share_class=share_class,
        nav_basis=nav_basis,
    )

    expected_share_class: tuple[str, ...] | None = (
        ("retail",) if include_share_class else None
    )
    expected_nav_basis: tuple[object, ...] | None = (
        (
            (str(UUID(int=504)),),
            (str(UUID(int=505)),),
            ("per-share",),
            (str(UUID(int=506)),),
        )
        if include_nav_basis
        else None
    )

    assert terms.logical_values() == (
        "fund-vehicle",
        (str(UUID(int=501)),),
        (str(UUID(int=502)),),
        expected_kind,
        expected_share_class,
        expected_nav_basis,
        (str(UUID(int=503)),),
    )
