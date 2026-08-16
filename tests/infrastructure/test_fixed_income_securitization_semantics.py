from __future__ import annotations

from collections.abc import Callable
from dataclasses import FrozenInstanceError, fields, is_dataclass, replace
from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pytest

from qore.infrastructure import fixed_income_securitization_semantics as s
from qore.infrastructure.fixed_income_economics import (
    CompoundingConventionCode,
    CouponRate,
    DayCountConventionCode,
    FaceAmount,
    FinancialTenor,
    FinancialTenorUnit,
    FixedCouponTerms,
    FixedIncomeBenchmarkReference,
    FixedIncomeEvidenceRef,
    FixedIncomeReferenceRoleCode,
    FixedIncomeSpread,
)
from qore.infrastructure.universal_instrument_identity import EconomicIdentityId


def uid(value: int) -> UUID:
    return UUID(int=value)


def economic(value: int) -> EconomicIdentityId:
    return EconomicIdentityId(uid(value))


def evidence(value: int = 900) -> FixedIncomeEvidenceRef:
    return FixedIncomeEvidenceRef(uid(value))


def tenor() -> FinancialTenor:
    return FinancialTenor(1, FinancialTenorUnit.YEAR)


def coupon() -> FixedCouponTerms:
    return FixedCouponTerms(
        CouponRate(Decimal("0.05")),
        DayCountConventionCode("act-365"),
        tenor(),
    )


def benchmark(value: int = 800) -> FixedIncomeBenchmarkReference:
    return FixedIncomeBenchmarkReference(
        economic(value),
        FixedIncomeReferenceRoleCode("yield-maintenance"),
        tenor(),
    )


def metric(
    metric_id: int = 100,
) -> s.CumulativeRealizedLossRatioMetricDefinition:
    role = s.MetricRoleCode
    return s.CumulativeRealizedLossRatioMetricDefinition(
        s.MetricDefinitionId(uid(metric_id)),
        role.AGGREGATE_REALIZED_LOSSES_FROM_CUTOFF_THROUGH_MEASUREMENT_PERIOD,
        role.CUTOFF_DATE_POOL_BALANCE,
        role.CUMULATIVE_FROM_CUTOFF,
        role.NONE_AGGREGATION,
        evidence(metric_id + 1000),
    )


def delinquency(
    metric_id: int = 101,
) -> s.DelinquencyRatio60PlusMetricDefinition:
    role = s.MetricRoleCode
    return s.DelinquencyRatio60PlusMetricDefinition(
        s.MetricDefinitionId(uid(metric_id)),
        role.OUTSTANDING_PRINCIPAL_60_PLUS_DELINQUENT,
        role.INCLUDES_FORECLOSURE_BANKRUPTCY_REO,
        role.PERIOD_POOL_BALANCE,
        role.ROLLING_THREE_MONTHS,
        role.ARITHMETIC_MEAN_OF_PERIOD_RATIOS,
        evidence(metric_id + 1000),
    )


def enhancement(
    metric_id: int = 102,
) -> s.SeniorEnhancementPercentageMetricDefinition:
    role = s.MetricRoleCode
    return s.SeniorEnhancementPercentageMetricDefinition(
        s.MetricDefinitionId(uid(metric_id)),
        role.PRECEDING_DISTRIBUTION_DATE_MORTGAGE_LOAN_PRINCIPAL_BALANCE,
        role.MOST_SENIOR_CERTIFICATE_CLASS_PRINCIPAL_BALANCE,
        role.PRECEDING_MASTER_SERVICER_ADVANCE_DATE,
        role.PRECEDING_DISTRIBUTION_DATE_MORTGAGE_LOAN_PRINCIPAL_BALANCE,
        role.GROSS_BALANCE_MINUS_SENIOR_CERTIFICATE_BALANCE_OVER_GROSS_BALANCE,
        evidence(metric_id + 1000),
    )


def formula_a() -> s.YieldMaintenanceFormulaA:
    variant = s.YieldMaintenanceFormulaVariant
    stream = s.YieldMaintenancePaymentStreamBasis
    subtraction = s.YieldMaintenancePrincipalSubtractionBasis
    return s.YieldMaintenanceFormulaA(
        variant.PV_REMAINING_PRINCIPAL_AND_INTEREST_MINUS_PRINCIPAL,
        stream.REMAINING_CONTRACTUAL_PAYMENTS,
        subtraction.OUTSTANDING_PRINCIPAL_BALANCE,
        s.YieldMaintenanceHorizon.MATURITY,
        benchmark(),
        s.BenchmarkSelection.CLOSEST_MATURITY,
        CompoundingConventionCode("monthly"),
        CompoundingConventionCode("monthly"),
        tenor(),
        FixedIncomeSpread(Decimal("0.001")),
        s.PartialPrepaymentScaling.PREPAID_PRINCIPAL_OVER_OUTSTANDING_PRINCIPAL,
        evidence(700),
    )


def formula_b() -> s.YieldMaintenanceFormulaB:
    variant = s.YieldMaintenanceFormulaVariant
    principal = s.YieldMaintenancePrincipalBaseSemantic
    difference = s.YieldMaintenanceDifferentialSemantic
    return s.YieldMaintenanceFormulaB(
        variant.PV_INTEREST_DIFFERENTIAL,
        principal.PREPAID_PRINCIPAL,
        s.YieldMaintenanceLoanContractualRate(Decimal("0.06")),
        benchmark(801),
        difference.POSITIVE_PART_CONTRACTUAL_RATE_MINUS_REINVESTMENT_RATE,
        tenor(),
        s.YieldMaintenanceHorizon.OPEN_PREPAYMENT_DATE,
        s.DiscountRateBasis.REINVESTMENT_BENCHMARK_RATE,
        s.BenchmarkSelection.LINEAR_INTERPOLATION,
        CompoundingConventionCode("monthly"),
        evidence(701),
    )


def prepayment_terms() -> s.CollateralPrepaymentTerms:
    fixed = s.FixedPercentagePremium(
        s.PrepaymentFixedPremiumRate(Decimal("0.01")),
        s.FixedPercentagePremiumBasis.PREPAID_PRINCIPAL_AMOUNT,
    )
    phase1 = s.PrepaymentPhase(
        s.PrepaymentPhaseId(uid(501)),
        1,
        s.OriginationBoundary(),
        s.ProhibitedVoluntaryPrepayment(),
        None,
        evidence(1501),
    )
    charge = s.GreaterOfCharge(
        fixed,
        s.YieldMaintenanceCharge(formula_a()),
    )
    defeasance = s.DefeasanceTerms(
        s.SecuritizationCollateralTypeCode("government.securities"),
        s.DefeasanceQualificationOrNoticeRef(uid(503)),
        evidence(1502),
    )
    phase2 = s.PrepaymentPhase(
        s.PrepaymentPhaseId(uid(502)),
        2,
        s.AfterPaymentCountFromOriginationBoundary(12),
        s.PermittedVoluntaryPrepayment(charge),
        defeasance,
        evidence(1503),
    )
    phase3 = s.PrepaymentPhase(
        s.PrepaymentPhaseId(uid(504)),
        3,
        s.ExactDateBoundary(date(2030, 1, 1)),
        s.PermittedVoluntaryPrepayment(
            s.YieldMaintenanceCharge(formula_b())
        ),
        None,
        evidence(1504),
    )
    phase4 = s.PrepaymentPhase(
        s.PrepaymentPhaseId(uid(505)),
        4,
        s.PaymentCountBeforeMaturityBoundary(6),
        s.PermittedVoluntaryPrepayment(s.NoCharge()),
        None,
        evidence(1505),
    )
    return s.CollateralPrepaymentTerms(
        (phase4, phase2, phase1, phase3)
    )


def impac_schedule() -> s.ThresholdSchedule:
    ym = s.ContractualMeasurementYearMonth
    fraction = s.ExactFraction(1, 12)
    return s.ThresholdSchedule(
        (
            s.ConstantThresholdSegment(
                ym(2011, 12),
                None,
                s.ConstantThresholdRhs(Decimal("0.0225")),
            ),
            s.RampedThresholdSegment(
                ym(2009, 12),
                ym(2010, 11),
                s.ConstantThresholdRhs(Decimal("0.015")),
                s.ExactFractionOf(fraction, Decimal("0.005")),
            ),
            s.RampedThresholdSegment(
                ym(2007, 12),
                ym(2008, 11),
                s.ConstantThresholdRhs(Decimal("0.005")),
                s.ExactFractionOf(fraction, Decimal("0.005")),
            ),
            s.RampedThresholdSegment(
                ym(2010, 12),
                ym(2011, 11),
                s.ConstantThresholdRhs(Decimal("0.020")),
                s.ExactFractionOf(fraction, Decimal("0.0025")),
            ),
            s.RampedThresholdSegment(
                ym(2008, 12),
                ym(2009, 11),
                s.ConstantThresholdRhs(Decimal("0.010")),
                s.ExactFractionOf(fraction, Decimal("0.005")),
            ),
        )
    )


def condition_set(
    deal_id: s.SecuritizationDealId,
) -> s.ContractualConditionSet:
    event = s.EventCondition(
        s.ContractualConditionId(uid(201)),
        s.EventConditionKind.PAYMENT_DEFAULT,
        evidence(1201),
    )
    m1 = metric()
    m2 = delinquency()
    m3 = enhancement()
    test = s.PerformanceTestCondition(
        s.ContractualConditionId(uid(202)),
        m1.metric_definition_id,
        s.PerformanceTestComparator.GREATER_THAN_OR_EQUAL,
        s.ScheduledThresholdContract(impac_schedule()),
        s.ContractualMeasurementPeriod(
            s.ContractualMeasurementYearMonth(2007, 12),
            s.ContractualMeasurementYearMonth(2099, 12),
        ),
        evidence(1202),
    )
    composite = s.CompositeCondition(
        s.ContractualConditionId(uid(203)),
        s.CompositeConditionOperator.ALL_OF,
        (event.condition_id, test.condition_id),
        evidence(1203),
    )
    return s.ContractualConditionSet(
        deal_id,
        (event,),
        (m3, m1, m2),
        (test,),
        (composite,),
    )


def ranking(
    first: s.SecuritizationTrancheId,
    second: s.SecuritizationTrancheId,
) -> s.PriorityRanking:
    return s.PriorityRanking(
        (
            s.PariPassuGroup((first,)),
            s.PariPassuGroup((second,)),
        )
    )


def valid_deal(
    *,
    reverse_pools: bool = False,
    reverse_tranches: bool = False,
) -> s.SecuritizationDeal:
    deal_id = s.SecuritizationDealId(uid(1))
    pool1 = s.SecuritizationPoolId(uid(2))
    pool2 = s.SecuritizationPoolId(uid(3))
    t1 = s.SecuritizationTrancheId(uid(4))
    t2 = s.SecuritizationTrancheId(uid(5))
    prep = prepayment_terms()
    pools = (
        s.SecuritizationPool(
            pool1,
            deal_id,
            economic(20),
            s.ExplicitConstituentMembership(
                (economic(31), economic(30))
            ),
            s.SecuritizationPoolOriginalContractualBalance(
                Decimal("1000000")
            ),
            economic(99),
            s.SecuritizationCollateralTypeCode("cm.b-s"),
            prep,
            evidence(1301),
        ),
        s.SecuritizationPool(
            pool2,
            deal_id,
            economic(21),
            s.CombinedPoolMembership(
                economic(40),
                (economic(42), economic(41)),
            ),
            s.SecuritizationPoolOriginalContractualBalance(
                Decimal("500000")
            ),
            economic(99),
            s.SecuritizationCollateralTypeCode(
                "residential.mortgage"
            ),
            prep,
            evidence(1302),
        ),
    )
    tranches = (
        s.SecuritizationTranche(
            t1,
            deal_id,
            pool1,
            economic(50),
            FaceAmount(Decimal("700000")),
            economic(99),
            coupon(),
            evidence(1401),
        ),
        s.SecuritizationTranche(
            t2,
            deal_id,
            pool2,
            economic(51),
            FaceAmount(Decimal("300000")),
            economic(99),
            coupon(),
            evidence(1402),
        ),
    )
    conditions = condition_set(deal_id)
    priority = s.PriorityRegimeSet(
        deal_id,
        s.PriorityRegime(
            s.PriorityRegimeId(uid(301)),
            ranking(t1, t2),
            ranking(t1, t2),
            ranking(t2, t1),
        ),
        (
            s.ConditionedPriorityRegime(
                s.PriorityRegimeId(uid(302)),
                conditions.event_conditions[0].condition_id,
                1,
                ranking(t2, t1),
                ranking(t2, t1),
                ranking(t1, t2),
            ),
        ),
    )
    base = s.AllocationRegime(
        s.AllocationRegimeId(uid(401)),
        s.SequentialPrincipalAllocation((t1, t2)),
    )
    conditioned = s.ConditionedAllocationRegime(
        s.AllocationRegimeId(uid(402)),
        conditions.event_conditions[0].condition_id,
        1,
        s.ParallelProRataPrincipalAllocation(
            (t2, t1),
            s.ProRataPrincipalAllocationBasis.OUTSTANDING_PRINCIPAL_BALANCE,
        ),
    )
    scheduled = s.ScheduledPrincipalAllocationRegimeSet(
        deal_id,
        base,
        (conditioned,),
    )
    shares = s.ContractualShares(
        (
            s.ContractualShare(t2, Decimal("0.4")),
            s.ContractualShare(t1, Decimal("0.6")),
        )
    )
    unscheduled = s.UnscheduledPrincipalAllocationRegimeSet(
        deal_id,
        s.AllocationRegime(
            s.AllocationRegimeId(uid(403)),
            s.ParallelContractualSharesPrincipalAllocation(shares),
        ),
        (),
    )
    return s.SecuritizationDeal(
        deal_id,
        economic(10),
        tuple(reversed(pools)) if reverse_pools else pools,
        tuple(reversed(tranches)) if reverse_tranches else tranches,
        conditions,
        priority,
        scheduled,
        unscheduled,
        evidence(1600),
    )


def test_exact_fraction_gcd_and_no_float() -> None:
    assert (
        s.ExactFraction(2, 24).logical_values()
        == s.ExactFraction(1, 12).logical_values()
    )
    assert s.ExactFraction(3, 36).logical_values() == ("1", "12")
    with pytest.raises(s.FixedIncomeSecuritizationValidationError):
        s.ExactFraction(True, 12)  # type: ignore[arg-type]


@pytest.mark.parametrize("value", ["cm.bs", "cm-b.s", "a1"])
def test_collateral_code_accepts_canonical_lowercase(value: str) -> None:
    assert s.SecuritizationCollateralTypeCode(value).logical_values() == (
        value,
    )


@pytest.mark.parametrize("value", ["", "CMBS", "cm bs", "a" * 65])
def test_collateral_code_rejects_noncanonical(value: str) -> None:
    with pytest.raises(s.FixedIncomeSecuritizationValidationError):
        s.SecuritizationCollateralTypeCode(value)


def test_premium_rate_has_no_additional_sign_restriction() -> None:
    assert s.PrepaymentFixedPremiumRate(
        Decimal("-0.01")
    ).logical_values() == ("-0.01",)
    assert s.PrepaymentFixedPremiumRate(
        Decimal("0")
    ).logical_values() == ("0",)
    with pytest.raises(s.FixedIncomeSecuritizationValidationError):
        s.PrepaymentFixedPremiumRate(Decimal("NaN"))


MetricFactory = Callable[[], s.PerformanceMetricDefinition]


@pytest.mark.parametrize(
    "factory,field_name,wrong",
    [
        (
            metric,
            "numerator_role",
            s.MetricRoleCode.CUTOFF_DATE_POOL_BALANCE,
        ),
        (
            metric,
            "denominator_role",
            s.MetricRoleCode.CUMULATIVE_FROM_CUTOFF,
        ),
        (
            metric,
            "measurement_window_role",
            s.MetricRoleCode.NONE_AGGREGATION,
        ),
        (
            metric,
            "aggregation_role",
            s.MetricRoleCode.CUMULATIVE_FROM_CUTOFF,
        ),
        (
            delinquency,
            "numerator_population_role",
            s.MetricRoleCode.PERIOD_POOL_BALANCE,
        ),
        (
            delinquency,
            "qualification_role",
            s.MetricRoleCode.ROLLING_THREE_MONTHS,
        ),
        (
            delinquency,
            "denominator_role",
            s.MetricRoleCode.CUTOFF_DATE_POOL_BALANCE,
        ),
        (
            delinquency,
            "measurement_window_role",
            s.MetricRoleCode.CUMULATIVE_FROM_CUTOFF,
        ),
        (
            delinquency,
            "aggregation_role",
            s.MetricRoleCode.NONE_AGGREGATION,
        ),
        (
            enhancement,
            "gross_balance_role",
            s.MetricRoleCode.PERIOD_POOL_BALANCE,
        ),
        (
            enhancement,
            "subtracted_balance_role",
            s.MetricRoleCode.CUTOFF_DATE_POOL_BALANCE,
        ),
        (
            enhancement,
            "subtracted_balance_temporal_role",
            s.MetricRoleCode.CUMULATIVE_FROM_CUTOFF,
        ),
        (
            enhancement,
            "denominator_role",
            s.MetricRoleCode.PERIOD_POOL_BALANCE,
        ),
        (
            enhancement,
            "formula_operation_role",
            s.MetricRoleCode.NONE_AGGREGATION,
        ),
    ],
)
def test_every_wrong_fixed_metric_role_is_rejected(
    factory: MetricFactory,
    field_name: str,
    wrong: s.MetricRoleCode,
) -> None:
    definition = factory()
    with pytest.raises(s.FixedIncomeSecuritizationValidationError):
        replace(definition, **{field_name: wrong})


def test_valid_metric_logical_values_retain_formula_roles() -> None:
    values = (
        metric().logical_values()
        + delinquency().logical_values()
        + enhancement().logical_values()
    )
    role = s.MetricRoleCode
    expected = (
        role.AGGREGATE_REALIZED_LOSSES_FROM_CUTOFF_THROUGH_MEASUREMENT_PERIOD,
        role.CUTOFF_DATE_POOL_BALANCE,
        role.CUMULATIVE_FROM_CUTOFF,
        role.NONE_AGGREGATION,
        role.OUTSTANDING_PRINCIPAL_60_PLUS_DELINQUENT,
        role.INCLUDES_FORECLOSURE_BANKRUPTCY_REO,
        role.PERIOD_POOL_BALANCE,
        role.ROLLING_THREE_MONTHS,
        role.ARITHMETIC_MEAN_OF_PERIOD_RATIOS,
        role.PRECEDING_DISTRIBUTION_DATE_MORTGAGE_LOAN_PRINCIPAL_BALANCE,
        role.MOST_SENIOR_CERTIFICATE_CLASS_PRINCIPAL_BALANCE,
        role.PRECEDING_MASTER_SERVICER_ADVANCE_DATE,
        role.GROSS_BALANCE_MINUS_SENIOR_CERTIFICATE_BALANCE_OVER_GROSS_BALANCE,
    )
    for item in expected:
        assert item.value in values


def test_impac_schedule_is_exact_and_canonical() -> None:
    schedule = impac_schedule()
    starts = [
        item.start_year_month.logical_values()[0]
        for item in schedule.segments
    ]
    assert starts == [
        "2007-12",
        "2008-12",
        "2009-12",
        "2010-12",
        "2011-12",
    ]
    assert schedule.segments[-1].end_year_month is None
    assert s.ExactFraction(2, 24).logical_values() == ("1", "12")
    assert "0.0004166667" not in repr(schedule.logical_values())


def test_threshold_schedule_rejects_overlap_and_open_nonterminal() -> None:
    ym = s.ContractualMeasurementYearMonth
    constant = s.ConstantThresholdRhs(Decimal("1"))
    with pytest.raises(s.FixedIncomeSecuritizationValidationError):
        s.ThresholdSchedule(
            (
                s.ConstantThresholdSegment(ym(2020, 1), None, constant),
                s.ConstantThresholdSegment(
                    ym(2020, 2),
                    ym(2020, 3),
                    constant,
                ),
            )
        )
    with pytest.raises(s.FixedIncomeSecuritizationValidationError):
        s.ThresholdSchedule(
            (
                s.ConstantThresholdSegment(
                    ym(2020, 1),
                    ym(2020, 3),
                    constant,
                ),
                s.ConstantThresholdSegment(
                    ym(2020, 3),
                    ym(2020, 4),
                    constant,
                ),
            )
        )


def test_multiple_metric_threshold_is_nonnegative_and_typed() -> None:
    ref = s.MetricDefinitionId(uid(77))
    result = s.MultipleOfMetricThresholdRhs(Decimal("0"), ref)
    assert result.logical_values()[1] == "0"
    with pytest.raises(s.FixedIncomeSecuritizationValidationError):
        s.MultipleOfMetricThresholdRhs(Decimal("-1"), ref)


def test_pool_membership_is_canonical_and_distinct() -> None:
    left = s.ExplicitConstituentMembership(
        (economic(2), economic(1))
    )
    right = s.ExplicitConstituentMembership(
        (economic(1), economic(2))
    )
    assert left.logical_values() == right.logical_values()
    external = s.ExternalPoolReferenceMembership(economic(1))
    assert left.logical_values() != external.logical_values()
    combined = s.CombinedPoolMembership(
        economic(9),
        (economic(2), economic(1)),
    )
    assert combined.members == (economic(1), economic(2))


def test_priority_order_is_semantic_but_pari_passu_order_is_not() -> None:
    a = s.SecuritizationTrancheId(uid(1))
    b = s.SecuritizationTrancheId(uid(2))
    assert s.PariPassuGroup((b, a)).logical_values() == (
        s.PariPassuGroup((a, b)).logical_values()
    )
    assert ranking(a, b).logical_values() != ranking(b, a).logical_values()


def test_sequential_order_semantic_parallel_order_nonsemantic() -> None:
    a = s.SecuritizationTrancheId(uid(1))
    b = s.SecuritizationTrancheId(uid(2))
    left = s.SequentialPrincipalAllocation((a, b))
    right = s.SequentialPrincipalAllocation((b, a))
    assert left.logical_values() != right.logical_values()
    basis = s.ProRataPrincipalAllocationBasis.OUTSTANDING_PRINCIPAL_BALANCE
    pro_left = s.ParallelProRataPrincipalAllocation((a, b), basis)
    pro_right = s.ParallelProRataPrincipalAllocation((b, a), basis)
    assert pro_left.logical_values() == pro_right.logical_values()


def test_contractual_shares_are_exact_and_canonical() -> None:
    a = s.SecuritizationTrancheId(uid(1))
    b = s.SecuritizationTrancheId(uid(2))
    first = s.ContractualShares(
        (
            s.ContractualShare(b, Decimal("0.4")),
            s.ContractualShare(a, Decimal("0.6")),
        )
    )
    second = s.ContractualShares(
        (
            s.ContractualShare(a, Decimal("0.6")),
            s.ContractualShare(b, Decimal("0.4")),
        )
    )
    assert first.logical_values() == second.logical_values()
    with pytest.raises(s.FixedIncomeSecuritizationValidationError):
        s.ContractualShares(
            (
                s.ContractualShare(a, Decimal("0.7")),
                s.ContractualShare(b, Decimal("0.4")),
            )
        )


def test_pro_rata_fixed_discriminant_fails_closed() -> None:
    a = s.SecuritizationTrancheId(uid(1))
    with pytest.raises(s.FixedIncomeSecuritizationValidationError):
        s.ParallelProRataPrincipalAllocation(
            (a,),
            "other",  # type: ignore[arg-type]
        )


def test_formula_a_and_b_fixed_discriminants_fail_closed() -> None:
    a = formula_a()
    b = formula_b()
    variants = s.YieldMaintenanceFormulaVariant
    with pytest.raises(s.FixedIncomeSecuritizationValidationError):
        replace(
            a,
            formula_variant=variants.PV_INTEREST_DIFFERENTIAL,
        )
    with pytest.raises(s.FixedIncomeSecuritizationValidationError):
        replace(
            a,
            payment_stream_basis="other",  # type: ignore[arg-type]
        )
    with pytest.raises(s.FixedIncomeSecuritizationValidationError):
        replace(
            a,
            principal_subtraction_basis="other",  # type: ignore[arg-type]
        )
    with pytest.raises(s.FixedIncomeSecuritizationValidationError):
        replace(
            b,
            formula_variant=(
                variants.PV_REMAINING_PRINCIPAL_AND_INTEREST_MINUS_PRINCIPAL
            ),
        )
    with pytest.raises(s.FixedIncomeSecuritizationValidationError):
        replace(
            b,
            principal_base_semantic="other",  # type: ignore[arg-type]
        )
    with pytest.raises(s.FixedIncomeSecuritizationValidationError):
        replace(
            b,
            differential_semantic="other",  # type: ignore[arg-type]
        )
    with pytest.raises(s.FixedIncomeSecuritizationValidationError):
        replace(
            b,
            discount_rate_basis="other",  # type: ignore[arg-type]
        )


def test_formula_contractual_rate_is_not_coupon_rate() -> None:
    contractual_rate = formula_b().contractual_rate
    assert isinstance(
        contractual_rate,
        s.YieldMaintenanceLoanContractualRate,
    )
    assert not isinstance(contractual_rate, CouponRate)
    assert formula_a().logical_values() != formula_b().logical_values()


def test_prepayment_mixed_boundaries_follow_source_ordinal() -> None:
    terms = prepayment_terms()
    assert [item.ordinal for item in terms.phases] == [1, 2, 3, 4]
    assert isinstance(
        terms.phases[0].effective_from,
        s.OriginationBoundary,
    )
    assert isinstance(
        terms.phases[1].effective_from,
        s.AfterPaymentCountFromOriginationBoundary,
    )
    assert isinstance(
        terms.phases[2].effective_from,
        s.ExactDateBoundary,
    )
    assert isinstance(
        terms.phases[3].effective_from,
        s.PaymentCountBeforeMaturityBoundary,
    )


def test_prepayment_requires_origination_first() -> None:
    phase = s.PrepaymentPhase(
        s.PrepaymentPhaseId(uid(1)),
        1,
        s.ExactDateBoundary(date(2030, 1, 1)),
        s.ProhibitedVoluntaryPrepayment(),
        None,
        evidence(),
    )
    with pytest.raises(s.FixedIncomeSecuritizationValidationError):
        s.CollateralPrepaymentTerms((phase,))


def test_defeasance_notice_reference_is_not_evidence_reference() -> None:
    terms = prepayment_terms().phases[1].defeasance_terms
    assert terms is not None
    assert isinstance(
        terms.qualification_or_notice_ref,
        s.DefeasanceQualificationOrNoticeRef,
    )
    assert isinstance(terms.evidence_ref, FixedIncomeEvidenceRef)
    assert type(terms.qualification_or_notice_ref) is not type(
        terms.evidence_ref
    )


def test_condition_set_rejects_orphan_metric_and_composite_cycle() -> None:
    deal_id = s.SecuritizationDealId(uid(1))
    orphan_test = s.PerformanceTestCondition(
        s.ContractualConditionId(uid(2)),
        s.MetricDefinitionId(uid(999)),
        s.PerformanceTestComparator.GREATER_THAN,
        s.StaticThresholdContract(
            s.ConstantThresholdRhs(Decimal("1"))
        ),
        s.ContractualMeasurementPeriod(
            s.ContractualMeasurementYearMonth(2020, 1),
            s.ContractualMeasurementYearMonth(2020, 2),
        ),
        evidence(),
    )
    with pytest.raises(s.FixedIncomeSecuritizationValidationError):
        s.ContractualConditionSet(
            deal_id,
            (),
            (metric(),),
            (orphan_test,),
            (),
        )
    a = s.ContractualConditionId(uid(10))
    b = s.ContractualConditionId(uid(11))
    leaf1 = s.ContractualConditionId(uid(12))
    leaf2 = s.ContractualConditionId(uid(13))
    c1 = s.CompositeCondition(
        a,
        s.CompositeConditionOperator.ALL_OF,
        (b, leaf1),
        evidence(1),
    )
    c2 = s.CompositeCondition(
        b,
        s.CompositeConditionOperator.ANY_OF,
        (a, leaf2),
        evidence(2),
    )
    e1 = s.EventCondition(
        leaf1,
        s.EventConditionKind.PAYMENT_DEFAULT,
        evidence(3),
    )
    e2 = s.EventCondition(
        leaf2,
        s.EventConditionKind.ACCELERATION_EVENT,
        evidence(4),
    )
    with pytest.raises(s.FixedIncomeSecuritizationValidationError):
        s.ContractualConditionSet(
            deal_id,
            (e1, e2),
            (),
            (),
            (c1, c2),
        )


def test_event_kinds_are_exactly_frozen_set() -> None:
    assert {item.name for item in s.EventConditionKind} == {
        "PAYMENT_DEFAULT",
        "ISSUER_INSOLVENCY_DEFAULT",
        "COVENANT_REPRESENTATION_WARRANTY_BREACH",
        "ACCELERATION_EVENT",
    }


def test_deal_pool_and_tranche_permutations_are_nonsemantic() -> None:
    baseline = valid_deal()
    assert baseline.logical_values() == valid_deal(
        reverse_pools=True
    ).logical_values()
    assert baseline.logical_values() == valid_deal(
        reverse_tranches=True
    ).logical_values()


def test_deal_reuses_face_amount_coupon_and_evidence() -> None:
    deal = valid_deal()
    assert all(
        isinstance(item.original_face_amount, FaceAmount)
        for item in deal.tranches
    )
    assert all(
        isinstance(item.coupon, FixedCouponTerms)
        for item in deal.tranches
    )
    assert all(
        isinstance(item.evidence_ref, FixedIncomeEvidenceRef)
        for item in deal.tranches
    )


def test_shared_denomination_allowed_but_identity_conflation_rejected() -> None:
    deal = valid_deal()
    assert (
        deal.pools[0].denomination_currency_identity_id
        == deal.tranches[0].denomination_currency_identity_id
    )
    with pytest.raises(s.FixedIncomeSecuritizationValidationError):
        replace(
            deal,
            deal_identity_id=deal.pools[0].pool_identity_id,
        )


def test_deal_rejects_foreign_priority_tranche() -> None:
    deal = valid_deal()
    foreign = s.SecuritizationTrancheId(uid(999))
    bad_priority = replace(
        deal.priority_regime_set,
        base=replace(
            deal.priority_regime_set.base,
            interest_ranking=s.PriorityRanking(
                (s.PariPassuGroup((foreign,)),)
            ),
        ),
    )
    with pytest.raises(s.FixedIncomeSecuritizationValidationError):
        replace(deal, priority_regime_set=bad_priority)


def test_public_semantic_dataclasses_are_frozen_and_slotted() -> None:
    sample = s.SecuritizationCollateralTypeCode("cm.bs")
    assert is_dataclass(sample)
    assert hasattr(type(sample), "__slots__")
    with pytest.raises(FrozenInstanceError):
        sample.value = "other"  # type: ignore[misc]
    assert [field.name for field in fields(sample)] == ["value"]


def test_strict_uuid_int_date_and_decimal_validation() -> None:
    with pytest.raises(s.FixedIncomeSecuritizationValidationError):
        s.SecuritizationDealId("x")  # type: ignore[arg-type]
    with pytest.raises(s.FixedIncomeSecuritizationValidationError):
        s.ContractualMeasurementYearMonth(
            True,  # type: ignore[arg-type]
            1,
        )
    with pytest.raises(s.FixedIncomeSecuritizationValidationError):
        s.AfterPaymentCountFromOriginationBoundary(
            True  # type: ignore[arg-type]
        )
    with pytest.raises(s.FixedIncomeSecuritizationValidationError):
        s.ExactDateBoundary(
            "2030-01-01"  # type: ignore[arg-type]
        )
    with pytest.raises(s.FixedIncomeSecuritizationValidationError):
        s.SecuritizationPoolOriginalContractualBalance(Decimal("0"))


def test_source_has_no_forbidden_productive_imports_or_engines() -> None:
    assert s.__file__ is not None
    source = Path(s.__file__).read_text(encoding="utf-8")
    forbidden = (
        "requests",
        "httpx",
        "sqlalchemy",
        "sqlite3",
        "threading",
        "asyncio",
        "provider",
        "execution_runtime",
        "valuation_runtime",
        "uuid4",
    )
    assert all(token not in source for token in forbidden)
    assert "def calculate" not in source
    assert "def execute" not in source
    assert "def forecast" not in source
    assert "def present_value" not in source
