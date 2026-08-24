from __future__ import annotations

from dataclasses import fields
from datetime import date
from decimal import Decimal
from uuid import UUID

import pytest

from qore.infrastructure.derivative_contract_semantics import (
    DerivativeContractMultiplier,
    DerivativeEvidenceRef,
    DerivativeNotional,
    DerivativePriceQuoteBasisCode,
    DerivativeSettlementStyle,
    DerivativeStrike,
    DerivativeStrikeBasis,
    DerivativeTermsId,
    OptionContractTerms,
    OptionExerciseStyle,
    OptionExerciseTerms,
    OptionRight,
)
from qore.infrastructure.option_exotic_semantics import (
    BarrierRebateTerms,
    ChooserOptionTerms,
    CliquetOptionFeature,
    CliquetStrikeConventionCode,
    CompoundOptionRelationship,
    LookbackExtremumRole,
    LookbackKind,
    LookbackOptionTerms,
    OptionExoticValidationError,
    ShoutOptionFeature,
)
from qore.infrastructure.universal_instrument_identity import EconomicIdentityId


def _uuid(value: int) -> UUID:
    return UUID(f"00000000-0000-0000-0000-{value:012d}")


def _identity(value: int) -> EconomicIdentityId:
    return EconomicIdentityId(_uuid(value))


def _evidence(value: int) -> DerivativeEvidenceRef:
    return DerivativeEvidenceRef(_uuid(value))


def _strike(value: str = "100") -> DerivativeStrike:
    return DerivativeStrike(
        value=Decimal(value),
        basis=DerivativeStrikeBasis.PRICE,
        quote_identity_id=_identity(900),
        price_quote_basis=DerivativePriceQuoteBasisCode("currency-per-unit"),
    )


def _exercise() -> OptionExerciseTerms:
    return OptionExerciseTerms(style=OptionExerciseStyle.EUROPEAN)


def _notional(value: str = "1000") -> DerivativeNotional:
    return DerivativeNotional(Decimal(value), _identity(102))


def _multiplier(value: str = "5") -> DerivativeContractMultiplier:
    return DerivativeContractMultiplier(Decimal(value), _identity(102))


def _option(*, expiry: date = date(2027, 12, 18)) -> OptionContractTerms:
    return OptionContractTerms(
        terms_id=DerivativeTermsId(_uuid(100)),
        instrument_identity_id=_identity(101),
        underlying_identity_id=_identity(200),
        settlement_identity_id=_identity(102),
        right=OptionRight.CALL,
        strike=_strike(),
        expiry_date=expiry,
        exercise=_exercise(),
        settlement_style=DerivativeSettlementStyle.CASH,
        evidence_ref=_evidence(103),
        notional=_notional(),
    )


def _lookback(
    kind: LookbackKind,
    right: OptionRight,
    extremum: LookbackExtremumRole,
) -> LookbackOptionTerms:
    return LookbackOptionTerms(
        terms_id=DerivativeTermsId(_uuid(500)),
        instrument_identity_id=_identity(501),
        underlying_identity_id=_identity(502),
        settlement_identity_id=_identity(102),
        right=right,
        kind=kind,
        fixed_strike=_strike("95") if kind is LookbackKind.FIXED_STRIKE else None,
        observation_window_start=date(2027, 1, 2),
        observation_window_end=date(2027, 11, 30),
        extremum_role=extremum,
        observation_schedule=None,
        expiry_date=date(2027, 12, 18),
        exercise=_exercise(),
        settlement_style=DerivativeSettlementStyle.CASH,
        evidence_ref=_evidence(503),
        notional=_notional(),
    )


@pytest.mark.parametrize(
    ("kind", "right", "extremum", "expected_kind", "expected_right", "expected_extremum"),
    [
        (
            LookbackKind.FIXED_STRIKE,
            OptionRight.CALL,
            LookbackExtremumRole.MAX,
            "fixed-strike",
            "call",
            "max",
        ),
        (
            LookbackKind.FIXED_STRIKE,
            OptionRight.PUT,
            LookbackExtremumRole.MIN,
            "fixed-strike",
            "put",
            "min",
        ),
        (
            LookbackKind.FLOATING_STRIKE,
            OptionRight.CALL,
            LookbackExtremumRole.MIN,
            "floating-strike",
            "call",
            "min",
        ),
        (
            LookbackKind.FLOATING_STRIKE,
            OptionRight.PUT,
            LookbackExtremumRole.MAX,
            "floating-strike",
            "put",
            "max",
        ),
    ],
)
def test_gatec_lookback_projection_preserves_kind_right_and_extremum(
    kind: LookbackKind,
    right: OptionRight,
    extremum: LookbackExtremumRole,
    expected_kind: str,
    expected_right: str,
    expected_extremum: str,
) -> None:
    projection = _lookback(kind, right, extremum).logical_values()
    assert projection[5] == expected_right
    assert projection[6] == expected_kind
    assert projection[10] == expected_extremum


@pytest.mark.parametrize(
    "reset_dates",
    [
        (date(2027, 6, 1), date(2027, 11, 2)),
        (date(2026, 12, 31), date(2027, 6, 1)),
        (date(2027, 3, 1), date(2027, 6, 1), date(2027, 11, 2)),
    ],
)
def test_gatec_cliquet_window_checks_every_reset(
    reset_dates: tuple[date, ...],
) -> None:
    with pytest.raises(OptionExoticValidationError):
        CliquetOptionFeature(
            option=_option(),
            reset_dates=reset_dates,
            local_strike_convention=CliquetStrikeConventionCode("previous-reset"),
            local_reset_observation_window=(date(2027, 1, 1), date(2027, 11, 1)),
            evidence_ref=_evidence(801),
        )


def test_gatec_chooser_multiplier_only_is_valid_and_material() -> None:
    value = ChooserOptionTerms(
        terms_id=DerivativeTermsId(_uuid(600)),
        instrument_identity_id=_identity(601),
        underlying_identity_id=_identity(602),
        settlement_identity_id=_identity(102),
        allowed_rights=(OptionRight.PUT, OptionRight.CALL),
        common_strike=_strike("105"),
        decision_date=date(2027, 6, 1),
        expiry_date=date(2027, 12, 18),
        exercise=_exercise(),
        settlement_style=DerivativeSettlementStyle.CASH,
        evidence_ref=_evidence(603),
        multiplier=_multiplier("5"),
        notional=None,
    )
    projection = value.logical_values()
    assert projection[-2] == ("5", (str(_uuid(102)),))
    assert projection[-1] is None


def test_gatec_new_aggregate_field_sets_are_exact() -> None:
    expected = {
        LookbackOptionTerms: (
            "terms_id",
            "instrument_identity_id",
            "underlying_identity_id",
            "settlement_identity_id",
            "right",
            "kind",
            "observation_window_start",
            "observation_window_end",
            "extremum_role",
            "expiry_date",
            "exercise",
            "settlement_style",
            "evidence_ref",
            "fixed_strike",
            "observation_schedule",
            "multiplier",
            "notional",
        ),
        ChooserOptionTerms: (
            "terms_id",
            "instrument_identity_id",
            "underlying_identity_id",
            "settlement_identity_id",
            "allowed_rights",
            "common_strike",
            "decision_date",
            "expiry_date",
            "exercise",
            "settlement_style",
            "evidence_ref",
            "multiplier",
            "notional",
        ),
        CompoundOptionRelationship: (
            "outer_option",
            "underlying_option",
            "evidence_ref",
        ),
        CliquetOptionFeature: (
            "option",
            "reset_dates",
            "local_strike_convention",
            "evidence_ref",
            "local_cap",
            "local_floor",
            "local_reset_observation_window",
        ),
        ShoutOptionFeature: (
            "option",
            "shout_right_count",
            "shout_window_start",
            "shout_window_end",
            "locked_in_reference_rule",
            "evidence_ref",
        ),
        BarrierRebateTerms: (
            "barrier_option",
            "barrier_feature_id",
            "trigger_condition",
            "payout",
            "evidence_ref",
        ),
    }
    for aggregate, field_names in expected.items():
        assert tuple(field.name for field in fields(aggregate)) == field_names
