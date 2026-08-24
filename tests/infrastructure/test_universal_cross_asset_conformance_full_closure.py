from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

import qore.infrastructure.fixed_income_securitization_semantics as securitization
import qore.infrastructure.fx_semantics as fx
import qore.infrastructure.option_exotic_semantics as exotic
from qore.infrastructure.derivative_contract_semantics import (
    DerivativeEvidenceRef,
    DerivativeNotional,
    DerivativeSettlementStyle,
    DerivativeTermsId,
    OptionExerciseStyle,
    OptionExerciseTerms,
    OptionRight,
)
from qore.infrastructure.fixed_income_economics import FixedIncomeEvidenceRef
from qore.infrastructure.universal_instrument_identity import EconomicIdentityId


def _uuid(value: int) -> UUID:
    return UUID(int=value)


def _identity(value: int) -> EconomicIdentityId:
    return EconomicIdentityId(_uuid(value))


def test_fx_carry_forward_retains_pair_direction_and_currency_roles() -> None:
    pair = fx.FxQuotedCurrencyPair(
        pair_identity_id=_identity(100),
        currency1_identity_id=_identity(101),
        currency2_identity_id=_identity(102),
        quote_basis=fx.FxQuoteBasis.CURRENCY1_PER_CURRENCY2,
        evidence_ref=fx.FxEvidenceRef(_uuid(103)),
    )
    spot = fx.FxSpotTerms(
        terms_id=fx.FxTermsId(_uuid(104)),
        instrument_identity_id=_identity(105),
        quoted_pair=pair,
        flows=(
            fx.FxCurrencyFlow(
                fx.FxFlowDirection.PAY,
                fx.FxCurrencyAmount(Decimal("100"), _identity(101)),
            ),
            fx.FxCurrencyFlow(
                fx.FxFlowDirection.RECEIVE,
                fx.FxCurrencyAmount(Decimal("110"), _identity(102)),
            ),
        ),
        value_dates=fx.FxValueDates(date(2026, 8, 24), date(2026, 8, 24)),
        agreed_exchange_rate=fx.FxExchangeRate(
            Decimal("1.1"),
            pair.pair_identity_id,
            pair.quote_basis,
        ),
        evidence_ref=fx.FxEvidenceRef(_uuid(106)),
    )

    material = (
        str(spot.terms_id.value),
        str(spot.instrument_identity_id.value),
        str(spot.quoted_pair.pair_identity_id.value),
        str(spot.quoted_pair.currency1_identity_id.value),
        str(spot.quoted_pair.currency2_identity_id.value),
        spot.quoted_pair.quote_basis.value,
        tuple(
            (
                flow.direction.value,
                str(flow.amount.value),
                str(flow.amount.currency_identity_id.value),
            )
            for flow in spot.flows
        ),
        spot.value_dates.currency1_value_date.isoformat(),
        spot.value_dates.currency2_value_date.isoformat(),
        str(spot.agreed_exchange_rate.value),
        spot.agreed_exchange_rate.quote_basis.value,
        str(spot.evidence_ref.value),
    )

    assert material == (
        "00000000-0000-0000-0000-000000000068",
        "00000000-0000-0000-0000-000000000069",
        "00000000-0000-0000-0000-000000000064",
        "00000000-0000-0000-0000-000000000065",
        "00000000-0000-0000-0000-000000000066",
        "currency1-per-currency2",
        (
            (
                "pay",
                "100",
                "00000000-0000-0000-0000-000000000065",
            ),
            (
                "receive",
                "110",
                "00000000-0000-0000-0000-000000000066",
            ),
        ),
        "2026-08-24",
        "2026-08-24",
        "1.1",
        "currency1-per-currency2",
        "00000000-0000-0000-0000-00000000006a",
    )
    assert spot.logical_values() == (
        "fx-spot-terms",
        ("00000000-0000-0000-0000-000000000068",),
        ("00000000-0000-0000-0000-000000000069",),
        (
            "fx-quoted-currency-pair",
            ("00000000-0000-0000-0000-000000000064",),
            ("00000000-0000-0000-0000-000000000065",),
            ("00000000-0000-0000-0000-000000000066",),
            "currency1-per-currency2",
            ("00000000-0000-0000-0000-000000000067",),
        ),
        (
            (
                "pay",
                (
                    "100",
                    ("00000000-0000-0000-0000-000000000065",),
                ),
            ),
            (
                "receive",
                (
                    "110",
                    ("00000000-0000-0000-0000-000000000066",),
                ),
            ),
        ),
        ("2026-08-24", "2026-08-24"),
        (
            "fx-exchange-rate",
            "1.1",
            ("00000000-0000-0000-0000-000000000064",),
            "currency1-per-currency2",
        ),
        ("00000000-0000-0000-0000-00000000006a",),
    )


def test_exotic_carry_forward_retains_digital_and_asian_semantics() -> None:
    payout = exotic.DigitalOptionPayout(
        kind=exotic.DigitalPayoutKind.CASH,
        amount=exotic.DigitalPayoutAmount(
            Decimal("10"),
            _identity(200),
        ),
        timing=exotic.DigitalPayoutTiming.DEFERRED,
        evidence_ref=DerivativeEvidenceRef(_uuid(201)),
    )
    averaging_period = exotic.AsianAveragingPeriod(
        explicit_observations=(
            exotic.AsianAveragingObservation(
                exotic.AsianAveragingLiteralDate(date(2026, 10, 1))
            ),
            exotic.AsianAveragingObservation(
                exotic.AsianAveragingLiteralDate(date(2026, 10, 2))
            ),
        ),
        observation_kind=exotic.AsianAveragingObservationKind.UNWEIGHTED,
    )
    asian = exotic.AsianOptionTerms(
        terms_id=DerivativeTermsId(_uuid(202)),
        instrument_identity_id=_identity(203),
        underlying_identity_id=_identity(204),
        settlement_identity_id=_identity(205),
        right=OptionRight.CALL,
        expiry_date=date(2026, 12, 18),
        exercise=OptionExerciseTerms(style=OptionExerciseStyle.EUROPEAN),
        settlement_style=DerivativeSettlementStyle.CASH,
        evidence_ref=DerivativeEvidenceRef(_uuid(206)),
        averaging_role=exotic.AsianAveragingRole.IN,
        averaging_method=exotic.AsianAveragingMethodCode("arithmetic"),
        averaging_period_in=averaging_period,
        averaging_period_out=None,
        fixed_strike=None,
        strike_factor=Decimal("1.1"),
        notional=DerivativeNotional(Decimal("1000"), _identity(205)),
    )

    assert asian.averaging_period_in is not None
    observation_dates: list[str] = []
    for observation in asian.averaging_period_in.explicit_observations:
        assert isinstance(observation.locator, exotic.AsianAveragingLiteralDate)
        observation_dates.append(observation.locator.value.isoformat())

    payout_material = (
        payout.kind.value,
        str(payout.amount.value),
        str(payout.amount.unit_identity_id.value),
        payout.timing.value,
        str(payout.evidence_ref.value),
    )
    asian_material = (
        asian.averaging_role.value,
        asian.averaging_method.value,
        tuple(observation_dates),
        asian.averaging_period_out,
        asian.fixed_strike,
        str(asian.strike_factor),
    )

    assert payout_material == (
        "cash",
        "10",
        "00000000-0000-0000-0000-0000000000c8",
        "deferred",
        "00000000-0000-0000-0000-0000000000c9",
    )
    assert asian_material == (
        "in",
        "arithmetic",
        ("2026-10-01", "2026-10-02"),
        None,
        None,
        "1.1",
    )
    assert payout.logical_values() == (
        "cash",
        (
            "10",
            ("00000000-0000-0000-0000-0000000000c8",),
        ),
        "deferred",
        ("00000000-0000-0000-0000-0000000000c9",),
    )
    assert asian.logical_values() == (
        "asian-option",
        ("00000000-0000-0000-0000-0000000000ca",),
        ("00000000-0000-0000-0000-0000000000cb",),
        ("00000000-0000-0000-0000-0000000000cc",),
        ("00000000-0000-0000-0000-0000000000cd",),
        "call",
        "2026-12-18",
        ("european", None, ()),
        "cash",
        ("00000000-0000-0000-0000-0000000000ce",),
        "in",
        ("arithmetic",),
        (
            (
                (("literal-date", "2026-10-01"), None),
                (("literal-date", "2026-10-02"), None),
            ),
            (),
            "unweighted",
        ),
        None,
        None,
        "1.1",
        None,
        (
            "1000",
            ("00000000-0000-0000-0000-0000000000cd",),
        ),
    )


def test_securitization_carry_forward_retains_fixed_contract_roles() -> None:
    role = securitization.MetricRoleCode
    metric = securitization.CumulativeRealizedLossRatioMetricDefinition(
        metric_definition_id=securitization.MetricDefinitionId(_uuid(300)),
        numerator_role=(
            role.AGGREGATE_REALIZED_LOSSES_FROM_CUTOFF_THROUGH_MEASUREMENT_PERIOD
        ),
        denominator_role=role.CUTOFF_DATE_POOL_BALANCE,
        measurement_window_role=role.CUMULATIVE_FROM_CUTOFF,
        aggregation_role=role.NONE_AGGREGATION,
        evidence_ref=FixedIncomeEvidenceRef(_uuid(301)),
    )
    fraction = securitization.ExactFraction(2, 24)
    balance = securitization.SecuritizationPoolOriginalContractualBalance(
        Decimal("1000000")
    )

    material = (
        str(metric.metric_definition_id.value),
        metric.numerator_role.value,
        metric.denominator_role.value,
        metric.measurement_window_role.value,
        metric.aggregation_role.value,
        str(metric.evidence_ref.value),
        fraction.numerator,
        fraction.denominator,
        str(balance.value),
    )

    assert material == (
        "00000000-0000-0000-0000-00000000012c",
        "aggregate-realized-losses-from-cutoff-through-measurement-period",
        "cutoff-date-pool-balance",
        "cumulative-from-cutoff",
        "none-aggregation",
        "00000000-0000-0000-0000-00000000012d",
        1,
        12,
        "1000000",
    )
    assert metric.logical_values() == (
        "cumulative-realized-loss-ratio",
        ("00000000-0000-0000-0000-00000000012c",),
        "aggregate-realized-losses-from-cutoff-through-measurement-period",
        "cutoff-date-pool-balance",
        "cumulative-from-cutoff",
        "none-aggregation",
        ("00000000-0000-0000-0000-00000000012d",),
    )
    assert fraction.logical_values() == ("1", "12")
    assert balance.logical_values() == ("1000000",)


def test_equal_decimal_does_not_flatten_new_owner_semantics() -> None:
    amount = Decimal("0.05")
    fx_rate = fx.FxExchangeRate(
        amount,
        _identity(400),
        fx.FxQuoteBasis.CURRENCY2_PER_CURRENCY1,
    )
    digital_amount = exotic.DigitalPayoutAmount(amount, _identity(401))
    premium_rate = securitization.PrepaymentFixedPremiumRate(amount)

    assert fx_rate.value == digital_amount.value == premium_rate.value
    assert type(fx_rate) is fx.FxExchangeRate
    assert type(digital_amount) is exotic.DigitalPayoutAmount
    assert type(premium_rate) is securitization.PrepaymentFixedPremiumRate
    assert fx_rate.quote_basis is fx.FxQuoteBasis.CURRENCY2_PER_CURRENCY1
    assert digital_amount.unit_identity_id == _identity(401)
