from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum
from math import gcd
from re import fullmatch
from typing import ClassVar
from uuid import UUID

from qore.infrastructure.fixed_income_economics import (
    CompoundingConventionCode,
    FaceAmount,
    FinancialTenor,
    FixedCouponTerms,
    FixedIncomeBenchmarkReference,
    FixedIncomeCouponTerms,
    FixedIncomeEvidenceRef,
    FixedIncomeSpread,
    FloatingCouponTerms,
    ZeroCouponTerms,
)
from qore.infrastructure.universal_instrument_identity import EconomicIdentityId
from qore.kernel.errors import InfrastructureError


class FixedIncomeSecuritizationSemanticsError(InfrastructureError):
    __slots__ = ()


class FixedIncomeSecuritizationValidationError(
    FixedIncomeSecuritizationSemanticsError
):
    __slots__ = ()


def _fail(message: str) -> None:
    raise FixedIncomeSecuritizationValidationError(message)


def _require(value: object, expected: type[object], name: str) -> None:
    if not isinstance(value, expected):
        _fail(f"{name} must be {expected.__name__}")


def _identity(value: EconomicIdentityId, name: str) -> None:
    if not isinstance(value, EconomicIdentityId):
        _fail(f"{name} must be EconomicIdentityId")


def _evidence(value: FixedIncomeEvidenceRef, name: str) -> None:
    if not isinstance(value, FixedIncomeEvidenceRef):
        _fail(f"{name} must be FixedIncomeEvidenceRef")


def _positive_int(value: int, name: str) -> None:
    if type(value) is not int or value <= 0:
        _fail(f"{name} must be a positive int")


def _decimal(
    value: Decimal,
    name: str,
    *,
    positive: bool = False,
) -> None:
    if type(value) is not Decimal or not value.is_finite():
        _fail(f"{name} must be a finite Decimal")
    if positive and value <= 0:
        _fail(f"{name} must be positive")


def _canonical_decimal(value: Decimal) -> str:
    normalized = value.normalize()
    return "0" if normalized == 0 else format(normalized, "f")


def _coupon(value: object) -> bool:
    return isinstance(
        value,
        (FixedCouponTerms, FloatingCouponTerms, ZeroCouponTerms),
    )


@dataclass(frozen=True, slots=True)
class _UuidValue:
    value: UUID

    def __post_init__(self) -> None:
        if type(self.value) is not UUID:
            _fail(f"{type(self).__name__}.value must be UUID")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class SecuritizationDealId(_UuidValue):
    pass


@dataclass(frozen=True, slots=True)
class SecuritizationPoolId(_UuidValue):
    pass


@dataclass(frozen=True, slots=True)
class SecuritizationTrancheId(_UuidValue):
    pass


@dataclass(frozen=True, slots=True)
class PriorityRegimeId(_UuidValue):
    pass


@dataclass(frozen=True, slots=True)
class AllocationRegimeId(_UuidValue):
    pass


@dataclass(frozen=True, slots=True)
class ContractualConditionId(_UuidValue):
    pass


@dataclass(frozen=True, slots=True)
class MetricDefinitionId(_UuidValue):
    pass


@dataclass(frozen=True, slots=True)
class PrepaymentPhaseId(_UuidValue):
    pass


@dataclass(frozen=True, slots=True)
class DefeasanceQualificationOrNoticeRef(_UuidValue):
    pass


@dataclass(frozen=True, slots=True)
class _DecimalValue:
    value: Decimal
    _positive: ClassVar[bool] = False

    def __post_init__(self) -> None:
        _decimal(
            self.value,
            type(self).__name__,
            positive=self._positive,
        )

    def logical_values(self) -> tuple[str, ...]:
        return (_canonical_decimal(self.value),)


@dataclass(frozen=True, slots=True)
class SecuritizationPoolOriginalContractualBalance(_DecimalValue):
    _positive: ClassVar[bool] = True


@dataclass(frozen=True, slots=True)
class PrepaymentFixedPremiumRate(_DecimalValue):
    pass


@dataclass(frozen=True, slots=True)
class YieldMaintenanceLoanContractualRate(_DecimalValue):
    pass


@dataclass(frozen=True, slots=True)
class SecuritizationCollateralTypeCode:
    value: str

    def __post_init__(self) -> None:
        valid = (
            type(self.value) is str
            and bool(self.value)
            and len(self.value) <= 64
            and fullmatch(
                r"[a-z0-9]+(?:[._-][a-z0-9]+)*",
                self.value,
            )
            is not None
        )
        if not valid:
            _fail("collateral type must use canonical lowercase code syntax")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True, order=True)
class ContractualMeasurementYearMonth:
    year: int
    month: int

    def __post_init__(self) -> None:
        _positive_int(self.year, "contractual measurement year")
        if type(self.month) is not int or not 1 <= self.month <= 12:
            _fail(
                "contractual measurement month must be int from 1 through 12"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (f"{self.year:04d}-{self.month:02d}",)


@dataclass(frozen=True, slots=True)
class ContractualMeasurementPeriod:
    start_year_month: ContractualMeasurementYearMonth
    end_year_month: ContractualMeasurementYearMonth

    def __post_init__(self) -> None:
        _require(
            self.start_year_month,
            ContractualMeasurementYearMonth,
            "period start",
        )
        _require(
            self.end_year_month,
            ContractualMeasurementYearMonth,
            "period end",
        )
        if self.end_year_month < self.start_year_month:
            _fail("measurement period end must not precede start")

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.start_year_month.logical_values(),
            self.end_year_month.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class ExactFraction:
    numerator: int
    denominator: int

    def __post_init__(self) -> None:
        _positive_int(self.numerator, "exact fraction numerator")
        _positive_int(self.denominator, "exact fraction denominator")
        divisor = gcd(self.numerator, self.denominator)
        object.__setattr__(
            self,
            "numerator",
            self.numerator // divisor,
        )
        object.__setattr__(
            self,
            "denominator",
            self.denominator // divisor,
        )

    def logical_values(self) -> tuple[str, ...]:
        return (
            str(self.numerator),
            str(self.denominator),
        )


@dataclass(frozen=True, slots=True)
class ExactFractionOf:
    fraction: ExactFraction
    base_rate: Decimal

    def __post_init__(self) -> None:
        _require(self.fraction, ExactFraction, "fraction")
        _decimal(self.base_rate, "fraction base rate")

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.fraction.logical_values(),
            _canonical_decimal(self.base_rate),
        )


class MetricRoleCode(StrEnum):
    AGGREGATE_REALIZED_LOSSES_FROM_CUTOFF_THROUGH_MEASUREMENT_PERIOD = (
        "aggregate-realized-losses-from-cutoff-through-measurement-period"
    )
    CUTOFF_DATE_POOL_BALANCE = "cutoff-date-pool-balance"
    CUMULATIVE_FROM_CUTOFF = "cumulative-from-cutoff"
    NONE_AGGREGATION = "none-aggregation"
    OUTSTANDING_PRINCIPAL_60_PLUS_DELINQUENT = (
        "outstanding-principal-60-plus-delinquent"
    )
    INCLUDES_FORECLOSURE_BANKRUPTCY_REO = (
        "includes-foreclosure-bankruptcy-reo"
    )
    PERIOD_POOL_BALANCE = "period-pool-balance"
    ROLLING_THREE_MONTHS = "rolling-three-months"
    ARITHMETIC_MEAN_OF_PERIOD_RATIOS = (
        "arithmetic-mean-of-period-ratios"
    )
    PRECEDING_DISTRIBUTION_DATE_MORTGAGE_LOAN_PRINCIPAL_BALANCE = (
        "preceding-distribution-date-mortgage-loan-principal-balance"
    )
    MOST_SENIOR_CERTIFICATE_CLASS_PRINCIPAL_BALANCE = (
        "most-senior-certificate-class-principal-balance"
    )
    PRECEDING_MASTER_SERVICER_ADVANCE_DATE = (
        "preceding-master-servicer-advance-date"
    )
    GROSS_BALANCE_MINUS_SENIOR_CERTIFICATE_BALANCE_OVER_GROSS_BALANCE = (
        "gross-balance-minus-senior-certificate-balance-over-gross-balance"
    )


def _fixed_roles(
    actual: tuple[MetricRoleCode, ...],
    expected: tuple[MetricRoleCode, ...],
) -> None:
    mismatch = len(actual) != len(expected) or any(
        left is not right
        for left, right in zip(
            actual,
            expected,
            strict=True,
        )
    )
    if mismatch:
        _fail("metric definition contains a non-canonical fixed role")


@dataclass(frozen=True, slots=True)
class CumulativeRealizedLossRatioMetricDefinition:
    metric_definition_id: MetricDefinitionId
    numerator_role: MetricRoleCode
    denominator_role: MetricRoleCode
    measurement_window_role: MetricRoleCode
    aggregation_role: MetricRoleCode
    evidence_ref: FixedIncomeEvidenceRef

    def __post_init__(self) -> None:
        _require(
            self.metric_definition_id,
            MetricDefinitionId,
            "metric_definition_id",
        )
        role = MetricRoleCode
        _fixed_roles(
            (
                self.numerator_role,
                self.denominator_role,
                self.measurement_window_role,
                self.aggregation_role,
            ),
            (
                role.AGGREGATE_REALIZED_LOSSES_FROM_CUTOFF_THROUGH_MEASUREMENT_PERIOD,
                role.CUTOFF_DATE_POOL_BALANCE,
                role.CUMULATIVE_FROM_CUTOFF,
                role.NONE_AGGREGATION,
            ),
        )
        _evidence(self.evidence_ref, "metric evidence")

    def logical_values(self) -> tuple[object, ...]:
        return (
            "cumulative-realized-loss-ratio",
            self.metric_definition_id.logical_values(),
            self.numerator_role.value,
            self.denominator_role.value,
            self.measurement_window_role.value,
            self.aggregation_role.value,
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class DelinquencyRatio60PlusMetricDefinition:
    metric_definition_id: MetricDefinitionId
    numerator_population_role: MetricRoleCode
    qualification_role: MetricRoleCode
    denominator_role: MetricRoleCode
    measurement_window_role: MetricRoleCode
    aggregation_role: MetricRoleCode
    evidence_ref: FixedIncomeEvidenceRef

    def __post_init__(self) -> None:
        _require(
            self.metric_definition_id,
            MetricDefinitionId,
            "metric_definition_id",
        )
        role = MetricRoleCode
        _fixed_roles(
            (
                self.numerator_population_role,
                self.qualification_role,
                self.denominator_role,
                self.measurement_window_role,
                self.aggregation_role,
            ),
            (
                role.OUTSTANDING_PRINCIPAL_60_PLUS_DELINQUENT,
                role.INCLUDES_FORECLOSURE_BANKRUPTCY_REO,
                role.PERIOD_POOL_BALANCE,
                role.ROLLING_THREE_MONTHS,
                role.ARITHMETIC_MEAN_OF_PERIOD_RATIOS,
            ),
        )
        _evidence(self.evidence_ref, "metric evidence")

    def logical_values(self) -> tuple[object, ...]:
        return (
            "delinquency-ratio-60-plus",
            self.metric_definition_id.logical_values(),
            self.numerator_population_role.value,
            self.qualification_role.value,
            self.denominator_role.value,
            self.measurement_window_role.value,
            self.aggregation_role.value,
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class SeniorEnhancementPercentageMetricDefinition:
    metric_definition_id: MetricDefinitionId
    gross_balance_role: MetricRoleCode
    subtracted_balance_role: MetricRoleCode
    subtracted_balance_temporal_role: MetricRoleCode
    denominator_role: MetricRoleCode
    formula_operation_role: MetricRoleCode
    evidence_ref: FixedIncomeEvidenceRef

    def __post_init__(self) -> None:
        _require(
            self.metric_definition_id,
            MetricDefinitionId,
            "metric_definition_id",
        )
        role = MetricRoleCode
        _fixed_roles(
            (
                self.gross_balance_role,
                self.subtracted_balance_role,
                self.subtracted_balance_temporal_role,
                self.denominator_role,
                self.formula_operation_role,
            ),
            (
                role.PRECEDING_DISTRIBUTION_DATE_MORTGAGE_LOAN_PRINCIPAL_BALANCE,
                role.MOST_SENIOR_CERTIFICATE_CLASS_PRINCIPAL_BALANCE,
                role.PRECEDING_MASTER_SERVICER_ADVANCE_DATE,
                role.PRECEDING_DISTRIBUTION_DATE_MORTGAGE_LOAN_PRINCIPAL_BALANCE,
                role.GROSS_BALANCE_MINUS_SENIOR_CERTIFICATE_BALANCE_OVER_GROSS_BALANCE,
            ),
        )
        _evidence(self.evidence_ref, "metric evidence")

    def logical_values(self) -> tuple[object, ...]:
        return (
            "senior-enhancement-percentage",
            self.metric_definition_id.logical_values(),
            self.gross_balance_role.value,
            self.subtracted_balance_role.value,
            self.subtracted_balance_temporal_role.value,
            self.denominator_role.value,
            self.formula_operation_role.value,
            self.evidence_ref.logical_values(),
        )


type PerformanceMetricDefinition = (
    CumulativeRealizedLossRatioMetricDefinition
    | DelinquencyRatio60PlusMetricDefinition
    | SeniorEnhancementPercentageMetricDefinition
)


class EventConditionKind(StrEnum):
    PAYMENT_DEFAULT = "payment-default"
    ISSUER_INSOLVENCY_DEFAULT = "issuer-insolvency-default"
    COVENANT_REPRESENTATION_WARRANTY_BREACH = (
        "covenant-representation-warranty-breach"
    )
    ACCELERATION_EVENT = "acceleration-event"


@dataclass(frozen=True, slots=True)
class EventCondition:
    condition_id: ContractualConditionId
    kind: EventConditionKind
    evidence_ref: FixedIncomeEvidenceRef

    def __post_init__(self) -> None:
        _require(
            self.condition_id,
            ContractualConditionId,
            "condition_id",
        )
        _require(self.kind, EventConditionKind, "event kind")
        _evidence(self.evidence_ref, "event evidence")

    def logical_values(self) -> tuple[object, ...]:
        return (
            "event",
            self.condition_id.logical_values(),
            self.kind.value,
            self.evidence_ref.logical_values(),
        )


class PerformanceTestComparator(StrEnum):
    LESS_THAN = "less-than"
    LESS_THAN_OR_EQUAL = "less-than-or-equal"
    GREATER_THAN = "greater-than"
    GREATER_THAN_OR_EQUAL = "greater-than-or-equal"


@dataclass(frozen=True, slots=True)
class ConstantThresholdRhs:
    value: Decimal

    def __post_init__(self) -> None:
        _decimal(self.value, "constant threshold")

    def logical_values(self) -> tuple[object, ...]:
        return (
            "constant",
            _canonical_decimal(self.value),
        )


@dataclass(frozen=True, slots=True)
class MultipleOfMetricThresholdRhs:
    multiplier: Decimal
    metric_definition_id: MetricDefinitionId

    def __post_init__(self) -> None:
        _decimal(self.multiplier, "metric threshold multiplier")
        if self.multiplier < 0:
            _fail("metric threshold multiplier must be non-negative")
        _require(
            self.metric_definition_id,
            MetricDefinitionId,
            "threshold metric_definition_id",
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "multiple-of-metric",
            _canonical_decimal(self.multiplier),
            self.metric_definition_id.logical_values(),
        )


type ThresholdRhs = ConstantThresholdRhs | MultipleOfMetricThresholdRhs


def _threshold(value: object) -> bool:
    return isinstance(
        value,
        (ConstantThresholdRhs, MultipleOfMetricThresholdRhs),
    )


@dataclass(frozen=True, slots=True)
class ConstantThresholdSegment:
    start_year_month: ContractualMeasurementYearMonth
    end_year_month: ContractualMeasurementYearMonth | None
    threshold_rhs: ThresholdRhs

    def __post_init__(self) -> None:
        _require(
            self.start_year_month,
            ContractualMeasurementYearMonth,
            "segment start",
        )
        if self.end_year_month is not None:
            _require(
                self.end_year_month,
                ContractualMeasurementYearMonth,
                "segment end",
            )
            if self.end_year_month < self.start_year_month:
                _fail("segment end must not precede start")
        if not _threshold(self.threshold_rhs):
            _fail("segment threshold_rhs must be ThresholdRhs")

    def logical_values(self) -> tuple[object, ...]:
        end = (
            None
            if self.end_year_month is None
            else self.end_year_month.logical_values()
        )
        return (
            "constant-segment",
            self.start_year_month.logical_values(),
            end,
            self.threshold_rhs.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class RampedThresholdSegment:
    start_year_month: ContractualMeasurementYearMonth
    end_year_month: ContractualMeasurementYearMonth
    base_threshold_rhs: ThresholdRhs
    increment: ExactFractionOf

    def __post_init__(self) -> None:
        _require(
            self.start_year_month,
            ContractualMeasurementYearMonth,
            "ramp start",
        )
        _require(
            self.end_year_month,
            ContractualMeasurementYearMonth,
            "ramp end",
        )
        if self.end_year_month < self.start_year_month:
            _fail("ramp end must not precede start")
        if not _threshold(self.base_threshold_rhs):
            _fail("ramp base_threshold_rhs must be ThresholdRhs")
        _require(self.increment, ExactFractionOf, "ramp increment")

    def logical_values(self) -> tuple[object, ...]:
        return (
            "ramped-segment",
            self.start_year_month.logical_values(),
            self.end_year_month.logical_values(),
            self.base_threshold_rhs.logical_values(),
            self.increment.logical_values(),
        )


type ThresholdScheduleSegment = (
    ConstantThresholdSegment | RampedThresholdSegment
)


@dataclass(frozen=True, slots=True)
class ThresholdSchedule:
    segments: tuple[ThresholdScheduleSegment, ...]

    def __post_init__(self) -> None:
        if type(self.segments) is not tuple or not self.segments:
            _fail("threshold schedule requires a non-empty tuple")
        segment_types = (
            ConstantThresholdSegment,
            RampedThresholdSegment,
        )
        if not all(
            isinstance(item, segment_types)
            for item in self.segments
        ):
            _fail("threshold schedule contains invalid segment")
        ordered = tuple(
            sorted(
                self.segments,
                key=lambda item: item.start_year_month,
            )
        )
        for index, segment in enumerate(ordered):
            if (
                segment.end_year_month is None
                and index != len(ordered) - 1
            ):
                _fail("open-ended threshold segment must be terminal")
            if index:
                prior = ordered[index - 1]
                overlaps = (
                    prior.end_year_month is None
                    or segment.start_year_month <= prior.end_year_month
                )
                if overlaps:
                    _fail("threshold schedule segments must not overlap")
        object.__setattr__(self, "segments", ordered)

    def logical_values(self) -> tuple[object, ...]:
        return tuple(
            segment.logical_values()
            for segment in self.segments
        )


@dataclass(frozen=True, slots=True)
class StaticThresholdContract:
    rhs: ThresholdRhs

    def __post_init__(self) -> None:
        if not _threshold(self.rhs):
            _fail("static threshold rhs must be ThresholdRhs")

    def logical_values(self) -> tuple[object, ...]:
        return (
            "static",
            self.rhs.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class ScheduledThresholdContract:
    schedule: ThresholdSchedule

    def __post_init__(self) -> None:
        _require(
            self.schedule,
            ThresholdSchedule,
            "threshold schedule",
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "scheduled",
            self.schedule.logical_values(),
        )


type ThresholdContract = StaticThresholdContract | ScheduledThresholdContract


@dataclass(frozen=True, slots=True)
class PerformanceTestCondition:
    condition_id: ContractualConditionId
    metric_definition_id: MetricDefinitionId
    comparator: PerformanceTestComparator
    threshold_contract: ThresholdContract
    contractual_effective_period: ContractualMeasurementPeriod
    evidence_ref: FixedIncomeEvidenceRef

    def __post_init__(self) -> None:
        _require(
            self.condition_id,
            ContractualConditionId,
            "condition_id",
        )
        _require(
            self.metric_definition_id,
            MetricDefinitionId,
            "metric_definition_id",
        )
        _require(
            self.comparator,
            PerformanceTestComparator,
            "comparator",
        )
        threshold_types = (
            StaticThresholdContract,
            ScheduledThresholdContract,
        )
        if not isinstance(self.threshold_contract, threshold_types):
            _fail("threshold_contract must be ThresholdContract")
        _require(
            self.contractual_effective_period,
            ContractualMeasurementPeriod,
            "effective period",
        )
        _evidence(
            self.evidence_ref,
            "performance-test evidence",
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "performance-test",
            self.condition_id.logical_values(),
            self.metric_definition_id.logical_values(),
            self.comparator.value,
            self.threshold_contract.logical_values(),
            self.contractual_effective_period.logical_values(),
            self.evidence_ref.logical_values(),
        )


class CompositeConditionOperator(StrEnum):
    ALL_OF = "all-of"
    ANY_OF = "any-of"


@dataclass(frozen=True, slots=True)
class CompositeCondition:
    condition_id: ContractualConditionId
    operator: CompositeConditionOperator
    children: tuple[ContractualConditionId, ...]
    evidence_ref: FixedIncomeEvidenceRef

    def __post_init__(self) -> None:
        _require(
            self.condition_id,
            ContractualConditionId,
            "condition_id",
        )
        _require(
            self.operator,
            CompositeConditionOperator,
            "operator",
        )
        if type(self.children) is not tuple or len(self.children) < 2:
            _fail("composite condition requires at least two children")
        if not all(
            isinstance(item, ContractualConditionId)
            for item in self.children
        ):
            _fail("composite children must be ContractualConditionId")
        if (
            self.condition_id in self.children
            or len(set(self.children)) != len(self.children)
        ):
            _fail("composite children must be unique and exclude self")
        object.__setattr__(
            self,
            "children",
            tuple(
                sorted(
                    self.children,
                    key=lambda item: item.logical_values(),
                )
            ),
        )
        _evidence(self.evidence_ref, "composite evidence")

    def logical_values(self) -> tuple[object, ...]:
        return (
            "composite",
            self.condition_id.logical_values(),
            self.operator.value,
            tuple(
                item.logical_values()
                for item in self.children
            ),
            self.evidence_ref.logical_values(),
        )


def _metric_id(
    value: PerformanceMetricDefinition,
) -> MetricDefinitionId:
    return value.metric_definition_id


def _threshold_metric_ids(
    value: ThresholdContract,
) -> set[MetricDefinitionId]:
    result: set[MetricDefinitionId] = set()

    def add(rhs: ThresholdRhs) -> None:
        if isinstance(rhs, MultipleOfMetricThresholdRhs):
            result.add(rhs.metric_definition_id)

    if isinstance(value, StaticThresholdContract):
        add(value.rhs)
    else:
        for segment in value.schedule.segments:
            if isinstance(segment, ConstantThresholdSegment):
                add(segment.threshold_rhs)
            else:
                add(segment.base_threshold_rhs)
    return result


@dataclass(frozen=True, slots=True)
class ContractualConditionSet:
    deal_id: SecuritizationDealId
    event_conditions: tuple[EventCondition, ...]
    performance_metric_definitions: tuple[
        PerformanceMetricDefinition,
        ...,
    ]
    performance_test_conditions: tuple[PerformanceTestCondition, ...]
    composite_conditions: tuple[CompositeCondition, ...]

    def __post_init__(self) -> None:
        _require(
            self.deal_id,
            SecuritizationDealId,
            "condition-set deal_id",
        )
        groups = (
            (
                self.event_conditions,
                EventCondition,
                "event_conditions",
            ),
            (
                self.performance_test_conditions,
                PerformanceTestCondition,
                "performance_test_conditions",
            ),
            (
                self.composite_conditions,
                CompositeCondition,
                "composite_conditions",
            ),
        )
        for values, expected, name in groups:
            if type(values) is not tuple or not all(
                isinstance(item, expected)
                for item in values
            ):
                _fail(f"condition-set {name} must be a typed tuple")
        metric_types = (
            CumulativeRealizedLossRatioMetricDefinition,
            DelinquencyRatio60PlusMetricDefinition,
            SeniorEnhancementPercentageMetricDefinition,
        )
        if (
            type(self.performance_metric_definitions) is not tuple
            or not all(
                isinstance(item, metric_types)
                for item in self.performance_metric_definitions
            )
        ):
            _fail(
                "condition-set performance_metric_definitions "
                "must be a typed tuple"
            )
        events = tuple(
            sorted(
                self.event_conditions,
                key=lambda item: item.condition_id.logical_values(),
            )
        )
        metrics = tuple(
            sorted(
                self.performance_metric_definitions,
                key=lambda item: item.metric_definition_id.logical_values(),
            )
        )
        tests = tuple(
            sorted(
                self.performance_test_conditions,
                key=lambda item: item.condition_id.logical_values(),
            )
        )
        composites = tuple(
            sorted(
                self.composite_conditions,
                key=lambda item: item.condition_id.logical_values(),
            )
        )
        object.__setattr__(self, "event_conditions", events)
        object.__setattr__(
            self,
            "performance_metric_definitions",
            metrics,
        )
        object.__setattr__(
            self,
            "performance_test_conditions",
            tests,
        )
        object.__setattr__(
            self,
            "composite_conditions",
            composites,
        )
        condition_ids = [item.condition_id for item in events]
        condition_ids.extend(item.condition_id for item in tests)
        condition_ids.extend(item.condition_id for item in composites)
        metric_ids = [_metric_id(item) for item in metrics]
        if (
            len(set(condition_ids)) != len(condition_ids)
            or len(set(metric_ids)) != len(metric_ids)
        ):
            _fail("condition and metric ids must be unique")
        known_conditions = set(condition_ids)
        known_metrics = set(metric_ids)
        for test in tests:
            if test.metric_definition_id not in known_metrics:
                _fail("performance test references orphan metric")
            referenced = _threshold_metric_ids(test.threshold_contract)
            if not referenced.issubset(known_metrics):
                _fail("threshold references orphan metric")
        by_id = {
            item.condition_id: item
            for item in composites
        }
        for composite in composites:
            if not set(composite.children).issubset(known_conditions):
                _fail("composite references orphan condition")
        visiting: set[ContractualConditionId] = set()
        visited: set[ContractualConditionId] = set()

        def visit(item: ContractualConditionId) -> None:
            if item in visiting:
                _fail("composite condition graph must be acyclic")
            if item in visited or item not in by_id:
                return
            visiting.add(item)
            for child in by_id[item].children:
                visit(child)
            visiting.remove(item)
            visited.add(item)

        for item in by_id:
            visit(item)

    def logical_values(self) -> tuple[object, ...]:
        return (
            "condition-set",
            self.deal_id.logical_values(),
            tuple(
                item.logical_values()
                for item in self.event_conditions
            ),
            tuple(
                item.logical_values()
                for item in self.performance_metric_definitions
            ),
            tuple(
                item.logical_values()
                for item in self.performance_test_conditions
            ),
            tuple(
                item.logical_values()
                for item in self.composite_conditions
            ),
        )


@dataclass(frozen=True, slots=True)
class ExplicitConstituentMembership:
    members: tuple[EconomicIdentityId, ...]

    def __post_init__(self) -> None:
        if type(self.members) is not tuple or not self.members:
            _fail("explicit membership requires non-empty tuple")
        for item in self.members:
            _identity(item, "explicit member")
        if len(set(self.members)) != len(self.members):
            _fail("explicit members must be unique")
        object.__setattr__(
            self,
            "members",
            tuple(
                sorted(
                    self.members,
                    key=lambda item: item.logical_values(),
                )
            ),
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "explicit-membership",
            tuple(
                item.logical_values()
                for item in self.members
            ),
        )


@dataclass(frozen=True, slots=True)
class ExternalPoolReferenceMembership:
    external_pool_reference_identity_id: EconomicIdentityId

    def __post_init__(self) -> None:
        _identity(
            self.external_pool_reference_identity_id,
            "external pool reference",
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "external-pool-reference",
            self.external_pool_reference_identity_id.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class CombinedPoolMembership:
    external_pool_reference_identity_id: EconomicIdentityId
    members: tuple[EconomicIdentityId, ...]

    def __post_init__(self) -> None:
        _identity(
            self.external_pool_reference_identity_id,
            "external pool reference",
        )
        normalized = ExplicitConstituentMembership(self.members)
        object.__setattr__(
            self,
            "members",
            normalized.members,
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "combined-membership",
            self.external_pool_reference_identity_id.logical_values(),
            tuple(
                item.logical_values()
                for item in self.members
            ),
        )


type SecuritizationPoolMembership = (
    ExplicitConstituentMembership
    | ExternalPoolReferenceMembership
    | CombinedPoolMembership
)


@dataclass(frozen=True, slots=True)
class PariPassuGroup:
    tranche_ids: tuple[SecuritizationTrancheId, ...]

    def __post_init__(self) -> None:
        if type(self.tranche_ids) is not tuple or not self.tranche_ids:
            _fail("pari-passu group requires non-empty tuple")
        if not all(
            isinstance(item, SecuritizationTrancheId)
            for item in self.tranche_ids
        ):
            _fail("pari-passu entries must be SecuritizationTrancheId")
        if len(set(self.tranche_ids)) != len(self.tranche_ids):
            _fail("pari-passu tranche ids must be unique")
        object.__setattr__(
            self,
            "tranche_ids",
            tuple(
                sorted(
                    self.tranche_ids,
                    key=lambda item: item.logical_values(),
                )
            ),
        )

    def logical_values(self) -> tuple[object, ...]:
        return tuple(
            item.logical_values()
            for item in self.tranche_ids
        )


@dataclass(frozen=True, slots=True)
class PriorityRanking:
    groups: tuple[PariPassuGroup, ...]

    def __post_init__(self) -> None:
        valid = (
            type(self.groups) is tuple
            and bool(self.groups)
            and all(
                isinstance(item, PariPassuGroup)
                for item in self.groups
            )
        )
        if not valid:
            _fail(
                "priority ranking requires non-empty tuple "
                "of PariPassuGroup"
            )
        flattened = [
            item
            for group in self.groups
            for item in group.tranche_ids
        ]
        if len(set(flattened)) != len(flattened):
            _fail("tranche may appear only once in a priority ranking")

    def logical_values(self) -> tuple[object, ...]:
        return tuple(
            group.logical_values()
            for group in self.groups
        )


@dataclass(frozen=True, slots=True)
class PriorityRegime:
    regime_id: PriorityRegimeId
    interest_ranking: PriorityRanking
    principal_ranking: PriorityRanking
    loss_ranking: PriorityRanking

    def __post_init__(self) -> None:
        _require(
            self.regime_id,
            PriorityRegimeId,
            "priority regime_id",
        )
        for value in (
            self.interest_ranking,
            self.principal_ranking,
            self.loss_ranking,
        ):
            _require(value, PriorityRanking, "priority ranking")

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.regime_id.logical_values(),
            self.interest_ranking.logical_values(),
            self.principal_ranking.logical_values(),
            self.loss_ranking.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class ConditionedPriorityRegime:
    regime_id: PriorityRegimeId
    condition_id: ContractualConditionId
    precedence_ordinal: int
    interest_ranking: PriorityRanking
    principal_ranking: PriorityRanking
    loss_ranking: PriorityRanking

    def __post_init__(self) -> None:
        _require(
            self.regime_id,
            PriorityRegimeId,
            "priority regime_id",
        )
        _require(
            self.condition_id,
            ContractualConditionId,
            "priority condition_id",
        )
        _positive_int(
            self.precedence_ordinal,
            "priority precedence ordinal",
        )
        for value in (
            self.interest_ranking,
            self.principal_ranking,
            self.loss_ranking,
        ):
            _require(value, PriorityRanking, "priority ranking")

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.regime_id.logical_values(),
            self.condition_id.logical_values(),
            self.precedence_ordinal,
            self.interest_ranking.logical_values(),
            self.principal_ranking.logical_values(),
            self.loss_ranking.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class PriorityRegimeSet:
    deal_id: SecuritizationDealId
    base: PriorityRegime
    conditioned: tuple[ConditionedPriorityRegime, ...]

    def __post_init__(self) -> None:
        _require(
            self.deal_id,
            SecuritizationDealId,
            "priority-set deal_id",
        )
        _require(self.base, PriorityRegime, "priority base")
        if (
            type(self.conditioned) is not tuple
            or not all(
                isinstance(item, ConditionedPriorityRegime)
                for item in self.conditioned
            )
        ):
            _fail("conditioned priority regimes must be typed tuple")
        ordered = tuple(
            sorted(
                self.conditioned,
                key=lambda item: item.precedence_ordinal,
            )
        )
        ids = [
            self.base.regime_id,
            *(item.regime_id for item in ordered),
        ]
        ordinals = [item.precedence_ordinal for item in ordered]
        if (
            len(set(ids)) != len(ids)
            or len(set(ordinals)) != len(ordinals)
        ):
            _fail(
                "priority regime ids and precedence ordinals "
                "must be unique"
            )
        object.__setattr__(self, "conditioned", ordered)

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.deal_id.logical_values(),
            self.base.logical_values(),
            tuple(
                item.logical_values()
                for item in self.conditioned
            ),
        )


class ProRataPrincipalAllocationBasis(StrEnum):
    OUTSTANDING_PRINCIPAL_BALANCE = "outstanding-principal-balance"


@dataclass(frozen=True, slots=True)
class SequentialPrincipalAllocation:
    ordered_tranche_ids: tuple[SecuritizationTrancheId, ...]

    def __post_init__(self) -> None:
        if (
            type(self.ordered_tranche_ids) is not tuple
            or not self.ordered_tranche_ids
        ):
            _fail("sequential allocation requires non-empty tuple")
        if not all(
            isinstance(item, SecuritizationTrancheId)
            for item in self.ordered_tranche_ids
        ):
            _fail("sequential allocation requires tranche ids")
        if len(set(self.ordered_tranche_ids)) != len(
            self.ordered_tranche_ids
        ):
            _fail("sequential allocation tranche ids must be unique")

    def logical_values(self) -> tuple[object, ...]:
        return (
            "sequential",
            tuple(
                item.logical_values()
                for item in self.ordered_tranche_ids
            ),
        )


@dataclass(frozen=True, slots=True)
class ParallelProRataPrincipalAllocation:
    participating_tranche_ids: tuple[SecuritizationTrancheId, ...]
    pro_rata_basis: ProRataPrincipalAllocationBasis

    def __post_init__(self) -> None:
        required_basis = (
            ProRataPrincipalAllocationBasis.OUTSTANDING_PRINCIPAL_BALANCE
        )
        if self.pro_rata_basis is not required_basis:
            _fail(
                "pro-rata basis must be "
                "OUTSTANDING_PRINCIPAL_BALANCE"
            )
        if (
            type(self.participating_tranche_ids) is not tuple
            or not self.participating_tranche_ids
        ):
            _fail("pro-rata allocation requires non-empty tuple")
        if not all(
            isinstance(item, SecuritizationTrancheId)
            for item in self.participating_tranche_ids
        ):
            _fail("pro-rata allocation requires tranche ids")
        if len(set(self.participating_tranche_ids)) != len(
            self.participating_tranche_ids
        ):
            _fail("pro-rata tranche ids must be unique")
        object.__setattr__(
            self,
            "participating_tranche_ids",
            tuple(
                sorted(
                    self.participating_tranche_ids,
                    key=lambda item: item.logical_values(),
                )
            ),
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "parallel-pro-rata",
            self.pro_rata_basis.value,
            tuple(
                item.logical_values()
                for item in self.participating_tranche_ids
            ),
        )


@dataclass(frozen=True, slots=True)
class ContractualShare:
    tranche_id: SecuritizationTrancheId
    share: Decimal

    def __post_init__(self) -> None:
        _require(
            self.tranche_id,
            SecuritizationTrancheId,
            "share tranche_id",
        )
        _decimal(self.share, "contractual share")
        if self.share < 0:
            _fail("contractual share must be non-negative")

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.tranche_id.logical_values(),
            _canonical_decimal(self.share),
        )


@dataclass(frozen=True, slots=True)
class ContractualShares:
    shares: tuple[ContractualShare, ...]

    def __post_init__(self) -> None:
        valid = (
            type(self.shares) is tuple
            and bool(self.shares)
            and all(
                isinstance(item, ContractualShare)
                for item in self.shares
            )
        )
        if not valid:
            _fail("contractual shares must be non-empty typed tuple")
        ordered = tuple(
            sorted(
                self.shares,
                key=lambda item: item.tranche_id.logical_values(),
            )
        )
        if len({item.tranche_id for item in ordered}) != len(ordered):
            _fail("contractual shares require unique tranche ids")
        total = sum(
            (item.share for item in ordered),
            Decimal("0"),
        )
        if total != Decimal("1"):
            _fail("contractual shares must sum exactly to one")
        object.__setattr__(self, "shares", ordered)

    def logical_values(self) -> tuple[object, ...]:
        return tuple(
            item.logical_values()
            for item in self.shares
        )


@dataclass(frozen=True, slots=True)
class ParallelContractualSharesPrincipalAllocation:
    contractual_shares: ContractualShares

    def __post_init__(self) -> None:
        _require(
            self.contractual_shares,
            ContractualShares,
            "contractual_shares",
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "parallel-contractual-shares",
            self.contractual_shares.logical_values(),
        )


type PrincipalAllocationContract = (
    SequentialPrincipalAllocation
    | ParallelProRataPrincipalAllocation
    | ParallelContractualSharesPrincipalAllocation
)


def _allocation(value: object) -> bool:
    return isinstance(
        value,
        (
            SequentialPrincipalAllocation,
            ParallelProRataPrincipalAllocation,
            ParallelContractualSharesPrincipalAllocation,
        ),
    )


@dataclass(frozen=True, slots=True)
class AllocationRegime:
    regime_id: AllocationRegimeId
    allocation_contract: PrincipalAllocationContract

    def __post_init__(self) -> None:
        _require(
            self.regime_id,
            AllocationRegimeId,
            "allocation regime_id",
        )
        if not _allocation(self.allocation_contract):
            _fail("allocation_contract must be PrincipalAllocationContract")

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.regime_id.logical_values(),
            self.allocation_contract.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class ConditionedAllocationRegime:
    regime_id: AllocationRegimeId
    condition_id: ContractualConditionId
    precedence_ordinal: int
    allocation_contract: PrincipalAllocationContract

    def __post_init__(self) -> None:
        _require(
            self.regime_id,
            AllocationRegimeId,
            "allocation regime_id",
        )
        _require(
            self.condition_id,
            ContractualConditionId,
            "allocation condition_id",
        )
        _positive_int(
            self.precedence_ordinal,
            "allocation precedence ordinal",
        )
        if not _allocation(self.allocation_contract):
            _fail("allocation_contract must be PrincipalAllocationContract")

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.regime_id.logical_values(),
            self.condition_id.logical_values(),
            self.precedence_ordinal,
            self.allocation_contract.logical_values(),
        )


def _allocation_set_validate(
    deal_id: SecuritizationDealId,
    base: AllocationRegime,
    conditioned: tuple[ConditionedAllocationRegime, ...],
) -> tuple[ConditionedAllocationRegime, ...]:
    _require(
        deal_id,
        SecuritizationDealId,
        "allocation-set deal_id",
    )
    _require(base, AllocationRegime, "allocation base")
    if (
        type(conditioned) is not tuple
        or not all(
            isinstance(item, ConditionedAllocationRegime)
            for item in conditioned
        )
    ):
        _fail("conditioned allocation regimes must be typed tuple")
    ordered = tuple(
        sorted(
            conditioned,
            key=lambda item: item.precedence_ordinal,
        )
    )
    ids = [
        base.regime_id,
        *(item.regime_id for item in ordered),
    ]
    ordinals = [item.precedence_ordinal for item in ordered]
    if (
        len(set(ids)) != len(ids)
        or len(set(ordinals)) != len(ordinals)
    ):
        _fail(
            "allocation regime ids and precedence ordinals "
            "must be unique"
        )
    return ordered


@dataclass(frozen=True, slots=True)
class ScheduledPrincipalAllocationRegimeSet:
    deal_id: SecuritizationDealId
    base: AllocationRegime
    conditioned: tuple[ConditionedAllocationRegime, ...]

    def __post_init__(self) -> None:
        normalized = _allocation_set_validate(
            self.deal_id,
            self.base,
            self.conditioned,
        )
        object.__setattr__(self, "conditioned", normalized)

    def logical_values(self) -> tuple[object, ...]:
        return (
            "scheduled",
            self.deal_id.logical_values(),
            self.base.logical_values(),
            tuple(
                item.logical_values()
                for item in self.conditioned
            ),
        )


@dataclass(frozen=True, slots=True)
class UnscheduledPrincipalAllocationRegimeSet:
    deal_id: SecuritizationDealId
    base: AllocationRegime
    conditioned: tuple[ConditionedAllocationRegime, ...]

    def __post_init__(self) -> None:
        normalized = _allocation_set_validate(
            self.deal_id,
            self.base,
            self.conditioned,
        )
        object.__setattr__(self, "conditioned", normalized)

    def logical_values(self) -> tuple[object, ...]:
        return (
            "unscheduled",
            self.deal_id.logical_values(),
            self.base.logical_values(),
            tuple(
                item.logical_values()
                for item in self.conditioned
            ),
        )


@dataclass(frozen=True, slots=True)
class OriginationBoundary:
    def logical_values(self) -> tuple[str, ...]:
        return ("origination",)


@dataclass(frozen=True, slots=True)
class ExactDateBoundary:
    date_value: date

    def __post_init__(self) -> None:
        if type(self.date_value) is not date:
            _fail("exact prepayment boundary must be date")

    def logical_values(self) -> tuple[str, ...]:
        return (
            "exact-date",
            self.date_value.isoformat(),
        )


@dataclass(frozen=True, slots=True)
class AfterPaymentCountFromOriginationBoundary:
    payment_count: int

    def __post_init__(self) -> None:
        _positive_int(
            self.payment_count,
            "payment count from origination",
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "after-payment-count-from-origination",
            self.payment_count,
        )


@dataclass(frozen=True, slots=True)
class PaymentCountBeforeMaturityBoundary:
    payment_count: int

    def __post_init__(self) -> None:
        _positive_int(
            self.payment_count,
            "payment count before maturity",
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "payment-count-before-maturity",
            self.payment_count,
        )


type ContractualPrepaymentBoundary = (
    OriginationBoundary
    | ExactDateBoundary
    | AfterPaymentCountFromOriginationBoundary
    | PaymentCountBeforeMaturityBoundary
)


class FixedPercentagePremiumBasis(StrEnum):
    PREPAID_PRINCIPAL_AMOUNT = "prepaid-principal-amount"
    OUTSTANDING_PRINCIPAL_AMOUNT = "outstanding-principal-amount"


class BenchmarkSelection(StrEnum):
    CLOSEST_MATURITY = "closest-maturity"
    LINEAR_INTERPOLATION = "linear-interpolation"


class YieldMaintenanceHorizon(StrEnum):
    MATURITY = "maturity"
    OPEN_PREPAYMENT_DATE = "open-prepayment-date"


class PartialPrepaymentScaling(StrEnum):
    NONE = "none"
    PREPAID_PRINCIPAL_OVER_OUTSTANDING_PRINCIPAL = (
        "prepaid-principal-over-outstanding-principal"
    )


class YieldMaintenanceFormulaVariant(StrEnum):
    PV_REMAINING_PRINCIPAL_AND_INTEREST_MINUS_PRINCIPAL = (
        "pv-remaining-principal-and-interest-minus-principal"
    )
    PV_INTEREST_DIFFERENTIAL = "pv-interest-differential"


class DiscountRateBasis(StrEnum):
    REINVESTMENT_BENCHMARK_RATE = "reinvestment-benchmark-rate"


class YieldMaintenancePaymentStreamBasis(StrEnum):
    REMAINING_CONTRACTUAL_PAYMENTS = "remaining-contractual-payments"


class YieldMaintenancePrincipalSubtractionBasis(StrEnum):
    OUTSTANDING_PRINCIPAL_BALANCE = "outstanding-principal-balance"


class YieldMaintenancePrincipalBaseSemantic(StrEnum):
    PREPAID_PRINCIPAL = "prepaid-principal"


class YieldMaintenanceDifferentialSemantic(StrEnum):
    POSITIVE_PART_CONTRACTUAL_RATE_MINUS_REINVESTMENT_RATE = (
        "positive-part-contractual-rate-minus-reinvestment-rate"
    )


@dataclass(frozen=True, slots=True)
class YieldMaintenanceFormulaA:
    formula_variant: YieldMaintenanceFormulaVariant
    payment_stream_basis: YieldMaintenancePaymentStreamBasis
    principal_subtraction_basis: YieldMaintenancePrincipalSubtractionBasis
    horizon: YieldMaintenanceHorizon
    benchmark_reference: FixedIncomeBenchmarkReference
    benchmark_selection: BenchmarkSelection
    discount_rate_conversion: CompoundingConventionCode
    compounding: CompoundingConventionCode
    payment_frequency: FinancialTenor
    spread: FixedIncomeSpread | None
    partial_prepayment_scaling: PartialPrepaymentScaling
    evidence_ref: FixedIncomeEvidenceRef

    def __post_init__(self) -> None:
        variant = YieldMaintenanceFormulaVariant
        expected_variant = (
            variant.PV_REMAINING_PRINCIPAL_AND_INTEREST_MINUS_PRINCIPAL
        )
        if self.formula_variant is not expected_variant:
            _fail("Formula A requires its fixed formula_variant")
        stream = YieldMaintenancePaymentStreamBasis
        expected_stream = stream.REMAINING_CONTRACTUAL_PAYMENTS
        if self.payment_stream_basis is not expected_stream:
            _fail("Formula A requires remaining contractual payments")
        subtraction = YieldMaintenancePrincipalSubtractionBasis
        expected_subtraction = subtraction.OUTSTANDING_PRINCIPAL_BALANCE
        if self.principal_subtraction_basis is not expected_subtraction:
            _fail("Formula A requires outstanding-principal subtraction")
        _require(
            self.horizon,
            YieldMaintenanceHorizon,
            "Formula A horizon",
        )
        _require(
            self.benchmark_reference,
            FixedIncomeBenchmarkReference,
            "Formula A benchmark",
        )
        _require(
            self.benchmark_selection,
            BenchmarkSelection,
            "Formula A benchmark selection",
        )
        _require(
            self.discount_rate_conversion,
            CompoundingConventionCode,
            "Formula A discount conversion",
        )
        _require(
            self.compounding,
            CompoundingConventionCode,
            "Formula A compounding",
        )
        _require(
            self.payment_frequency,
            FinancialTenor,
            "Formula A frequency",
        )
        if self.spread is not None:
            _require(
                self.spread,
                FixedIncomeSpread,
                "Formula A spread",
            )
        _require(
            self.partial_prepayment_scaling,
            PartialPrepaymentScaling,
            "Formula A scaling",
        )
        _evidence(self.evidence_ref, "Formula A evidence")

    def logical_values(self) -> tuple[object, ...]:
        spread = (
            None
            if self.spread is None
            else self.spread.logical_values()
        )
        return (
            "yield-maintenance-a",
            self.formula_variant.value,
            self.payment_stream_basis.value,
            self.principal_subtraction_basis.value,
            self.horizon.value,
            self.benchmark_reference.logical_values(),
            self.benchmark_selection.value,
            self.discount_rate_conversion.logical_values(),
            self.compounding.logical_values(),
            self.payment_frequency.logical_values(),
            spread,
            self.partial_prepayment_scaling.value,
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class YieldMaintenanceFormulaB:
    formula_variant: YieldMaintenanceFormulaVariant
    principal_base_semantic: YieldMaintenancePrincipalBaseSemantic
    contractual_rate: YieldMaintenanceLoanContractualRate
    reinvestment_benchmark: FixedIncomeBenchmarkReference
    differential_semantic: YieldMaintenanceDifferentialSemantic
    frequency: FinancialTenor
    horizon: YieldMaintenanceHorizon
    discount_rate_basis: DiscountRateBasis
    benchmark_selection: BenchmarkSelection
    compounding_conversion: CompoundingConventionCode
    evidence_ref: FixedIncomeEvidenceRef

    def __post_init__(self) -> None:
        variant = YieldMaintenanceFormulaVariant
        expected_variant = variant.PV_INTEREST_DIFFERENTIAL
        if self.formula_variant is not expected_variant:
            _fail("Formula B requires its fixed formula_variant")
        principal = YieldMaintenancePrincipalBaseSemantic
        expected_principal = principal.PREPAID_PRINCIPAL
        if self.principal_base_semantic is not expected_principal:
            _fail("Formula B requires PREPAID_PRINCIPAL")
        difference = YieldMaintenanceDifferentialSemantic
        expected_difference = (
            difference.POSITIVE_PART_CONTRACTUAL_RATE_MINUS_REINVESTMENT_RATE
        )
        if self.differential_semantic is not expected_difference:
            _fail("Formula B requires positive-part interest differential")
        expected_discount = DiscountRateBasis.REINVESTMENT_BENCHMARK_RATE
        if self.discount_rate_basis is not expected_discount:
            _fail("Formula B requires REINVESTMENT_BENCHMARK_RATE")
        _require(
            self.contractual_rate,
            YieldMaintenanceLoanContractualRate,
            "Formula B contractual rate",
        )
        _require(
            self.reinvestment_benchmark,
            FixedIncomeBenchmarkReference,
            "Formula B benchmark",
        )
        _require(
            self.frequency,
            FinancialTenor,
            "Formula B frequency",
        )
        _require(
            self.horizon,
            YieldMaintenanceHorizon,
            "Formula B horizon",
        )
        _require(
            self.benchmark_selection,
            BenchmarkSelection,
            "Formula B benchmark selection",
        )
        _require(
            self.compounding_conversion,
            CompoundingConventionCode,
            "Formula B compounding conversion",
        )
        _evidence(self.evidence_ref, "Formula B evidence")

    def logical_values(self) -> tuple[object, ...]:
        return (
            "yield-maintenance-b",
            self.formula_variant.value,
            self.principal_base_semantic.value,
            self.contractual_rate.logical_values(),
            self.reinvestment_benchmark.logical_values(),
            self.differential_semantic.value,
            self.frequency.logical_values(),
            self.horizon.value,
            self.discount_rate_basis.value,
            self.benchmark_selection.value,
            self.compounding_conversion.logical_values(),
            self.evidence_ref.logical_values(),
        )


type YieldMaintenanceFormula = (
    YieldMaintenanceFormulaA | YieldMaintenanceFormulaB
)


@dataclass(frozen=True, slots=True)
class NoCharge:
    def logical_values(self) -> tuple[str, ...]:
        return ("no-charge",)


@dataclass(frozen=True, slots=True)
class FixedPercentagePremium:
    percentage: PrepaymentFixedPremiumRate
    basis: FixedPercentagePremiumBasis

    def __post_init__(self) -> None:
        _require(
            self.percentage,
            PrepaymentFixedPremiumRate,
            "fixed premium percentage",
        )
        _require(
            self.basis,
            FixedPercentagePremiumBasis,
            "fixed premium basis",
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "fixed-percentage-premium",
            self.percentage.logical_values(),
            self.basis.value,
        )


@dataclass(frozen=True, slots=True)
class YieldMaintenanceCharge:
    formula: YieldMaintenanceFormula

    def __post_init__(self) -> None:
        formula_types = (
            YieldMaintenanceFormulaA,
            YieldMaintenanceFormulaB,
        )
        if not isinstance(self.formula, formula_types):
            _fail(
                "yield-maintenance charge requires YieldMaintenanceFormula"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "yield-maintenance",
            self.formula.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class GreaterOfCharge:
    fixed_premium: FixedPercentagePremium
    yield_maintenance: YieldMaintenanceCharge

    def __post_init__(self) -> None:
        _require(
            self.fixed_premium,
            FixedPercentagePremium,
            "greater-of fixed premium",
        )
        _require(
            self.yield_maintenance,
            YieldMaintenanceCharge,
            "greater-of yield maintenance",
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "greater-of",
            self.fixed_premium.logical_values(),
            self.yield_maintenance.logical_values(),
        )


type PrepaymentCharge = (
    NoCharge
    | FixedPercentagePremium
    | YieldMaintenanceCharge
    | GreaterOfCharge
)


@dataclass(frozen=True, slots=True)
class ProhibitedVoluntaryPrepayment:
    def logical_values(self) -> tuple[str, ...]:
        return ("prohibited",)


@dataclass(frozen=True, slots=True)
class PermittedVoluntaryPrepayment:
    charge: PrepaymentCharge

    def __post_init__(self) -> None:
        charge_types = (
            NoCharge,
            FixedPercentagePremium,
            YieldMaintenanceCharge,
            GreaterOfCharge,
        )
        if not isinstance(self.charge, charge_types):
            _fail("permitted prepayment requires PrepaymentCharge")

    def logical_values(self) -> tuple[object, ...]:
        return (
            "permitted",
            self.charge.logical_values(),
        )


type VoluntaryPrepaymentState = (
    ProhibitedVoluntaryPrepayment | PermittedVoluntaryPrepayment
)


@dataclass(frozen=True, slots=True)
class DefeasanceTerms:
    substitution_collateral_type: SecuritizationCollateralTypeCode
    qualification_or_notice_ref: DefeasanceQualificationOrNoticeRef | None
    evidence_ref: FixedIncomeEvidenceRef

    def __post_init__(self) -> None:
        _require(
            self.substitution_collateral_type,
            SecuritizationCollateralTypeCode,
            "defeasance collateral",
        )
        if self.qualification_or_notice_ref is not None:
            _require(
                self.qualification_or_notice_ref,
                DefeasanceQualificationOrNoticeRef,
                "defeasance notice ref",
            )
        _evidence(self.evidence_ref, "defeasance evidence")

    def logical_values(self) -> tuple[object, ...]:
        notice = (
            None
            if self.qualification_or_notice_ref is None
            else self.qualification_or_notice_ref.logical_values()
        )
        return (
            self.substitution_collateral_type.logical_values(),
            notice,
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class PrepaymentPhase:
    phase_id: PrepaymentPhaseId
    ordinal: int
    effective_from: ContractualPrepaymentBoundary
    voluntary_prepayment_state: VoluntaryPrepaymentState
    defeasance_terms: DefeasanceTerms | None
    evidence_ref: FixedIncomeEvidenceRef

    def __post_init__(self) -> None:
        _require(
            self.phase_id,
            PrepaymentPhaseId,
            "phase_id",
        )
        _positive_int(
            self.ordinal,
            "prepayment phase ordinal",
        )
        boundary_types = (
            OriginationBoundary,
            ExactDateBoundary,
            AfterPaymentCountFromOriginationBoundary,
            PaymentCountBeforeMaturityBoundary,
        )
        if not isinstance(self.effective_from, boundary_types):
            _fail("effective_from must be ContractualPrepaymentBoundary")
        state_types = (
            ProhibitedVoluntaryPrepayment,
            PermittedVoluntaryPrepayment,
        )
        if not isinstance(self.voluntary_prepayment_state, state_types):
            _fail(
                "voluntary_prepayment_state must be "
                "VoluntaryPrepaymentState"
            )
        if self.defeasance_terms is not None:
            _require(
                self.defeasance_terms,
                DefeasanceTerms,
                "defeasance_terms",
            )
        _evidence(
            self.evidence_ref,
            "prepayment phase evidence",
        )

    def logical_values(self) -> tuple[object, ...]:
        defeasance = (
            None
            if self.defeasance_terms is None
            else self.defeasance_terms.logical_values()
        )
        return (
            self.phase_id.logical_values(),
            self.ordinal,
            self.effective_from.logical_values(),
            self.voluntary_prepayment_state.logical_values(),
            defeasance,
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class CollateralPrepaymentTerms:
    phases: tuple[PrepaymentPhase, ...]

    def __post_init__(self) -> None:
        valid = (
            type(self.phases) is tuple
            and bool(self.phases)
            and all(
                isinstance(item, PrepaymentPhase)
                for item in self.phases
            )
        )
        if not valid:
            _fail(
                "collateral prepayment phases must be "
                "non-empty typed tuple"
            )
        ordered = tuple(
            sorted(
                self.phases,
                key=lambda item: item.ordinal,
            )
        )
        if not isinstance(
            ordered[0].effective_from,
            OriginationBoundary,
        ):
            _fail("first prepayment phase must begin at origination")
        ids_unique = len({item.phase_id for item in ordered}) == len(
            ordered
        )
        ordinals_unique = len({item.ordinal for item in ordered}) == len(
            ordered
        )
        if not ids_unique or not ordinals_unique:
            _fail("prepayment phase ids and ordinals must be unique")
        boundaries = [
            item.effective_from.logical_values()
            for item in ordered
        ]
        if len(set(boundaries)) != len(boundaries):
            _fail("prepayment phase boundaries must be unique")
        object.__setattr__(self, "phases", ordered)

    def logical_values(self) -> tuple[object, ...]:
        return tuple(
            item.logical_values()
            for item in self.phases
        )


@dataclass(frozen=True, slots=True)
class SecuritizationPool:
    pool_id: SecuritizationPoolId
    deal_id: SecuritizationDealId
    pool_identity_id: EconomicIdentityId
    membership: SecuritizationPoolMembership
    original_contractual_balance: SecuritizationPoolOriginalContractualBalance
    denomination_currency_identity_id: EconomicIdentityId
    collateral_type: SecuritizationCollateralTypeCode
    collateral_prepayment_terms: CollateralPrepaymentTerms
    evidence_ref: FixedIncomeEvidenceRef

    def __post_init__(self) -> None:
        _require(
            self.pool_id,
            SecuritizationPoolId,
            "pool_id",
        )
        _require(
            self.deal_id,
            SecuritizationDealId,
            "pool deal_id",
        )
        _identity(self.pool_identity_id, "pool identity")
        membership_types = (
            ExplicitConstituentMembership,
            ExternalPoolReferenceMembership,
            CombinedPoolMembership,
        )
        if not isinstance(self.membership, membership_types):
            _fail("membership must be SecuritizationPoolMembership")
        _require(
            self.original_contractual_balance,
            SecuritizationPoolOriginalContractualBalance,
            "pool balance",
        )
        _identity(
            self.denomination_currency_identity_id,
            "pool denomination",
        )
        if (
            self.pool_identity_id
            == self.denomination_currency_identity_id
        ):
            _fail("pool identity must differ from denomination")
        _require(
            self.collateral_type,
            SecuritizationCollateralTypeCode,
            "collateral_type",
        )
        _require(
            self.collateral_prepayment_terms,
            CollateralPrepaymentTerms,
            "prepayment terms",
        )
        _evidence(self.evidence_ref, "pool evidence")

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.pool_id.logical_values(),
            self.deal_id.logical_values(),
            self.pool_identity_id.logical_values(),
            self.membership.logical_values(),
            self.original_contractual_balance.logical_values(),
            self.denomination_currency_identity_id.logical_values(),
            self.collateral_type.logical_values(),
            self.collateral_prepayment_terms.logical_values(),
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class SecuritizationTranche:
    tranche_id: SecuritizationTrancheId
    deal_id: SecuritizationDealId
    pool_id: SecuritizationPoolId
    tranche_identity_id: EconomicIdentityId
    original_face_amount: FaceAmount
    denomination_currency_identity_id: EconomicIdentityId
    coupon: FixedIncomeCouponTerms
    evidence_ref: FixedIncomeEvidenceRef

    def __post_init__(self) -> None:
        _require(
            self.tranche_id,
            SecuritizationTrancheId,
            "tranche_id",
        )
        _require(
            self.deal_id,
            SecuritizationDealId,
            "tranche deal_id",
        )
        _require(
            self.pool_id,
            SecuritizationPoolId,
            "tranche pool_id",
        )
        _identity(
            self.tranche_identity_id,
            "tranche identity",
        )
        _require(
            self.original_face_amount,
            FaceAmount,
            "original_face_amount",
        )
        _identity(
            self.denomination_currency_identity_id,
            "tranche denomination",
        )
        if (
            self.tranche_identity_id
            == self.denomination_currency_identity_id
        ):
            _fail("tranche identity must differ from denomination")
        if not _coupon(self.coupon):
            _fail("coupon must be FixedIncomeCouponTerms")
        _evidence(self.evidence_ref, "tranche evidence")

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.tranche_id.logical_values(),
            self.deal_id.logical_values(),
            self.pool_id.logical_values(),
            self.tranche_identity_id.logical_values(),
            self.original_face_amount.logical_values(),
            self.denomination_currency_identity_id.logical_values(),
            self.coupon.logical_values(),
            self.evidence_ref.logical_values(),
        )


def _priority_ids(
    value: PriorityRegimeSet,
) -> set[SecuritizationTrancheId]:
    result: set[SecuritizationTrancheId] = set()
    base_rankings = (
        value.base.interest_ranking,
        value.base.principal_ranking,
        value.base.loss_ranking,
    )
    for ranking in base_rankings:
        for group in ranking.groups:
            result.update(group.tranche_ids)
    for regime in value.conditioned:
        conditioned_rankings = (
            regime.interest_ranking,
            regime.principal_ranking,
            regime.loss_ranking,
        )
        for ranking in conditioned_rankings:
            for group in ranking.groups:
                result.update(group.tranche_ids)
    return result


def _allocation_ids(
    value: PrincipalAllocationContract,
) -> set[SecuritizationTrancheId]:
    if isinstance(value, SequentialPrincipalAllocation):
        return set(value.ordered_tranche_ids)
    if isinstance(value, ParallelProRataPrincipalAllocation):
        return set(value.participating_tranche_ids)
    return {
        item.tranche_id
        for item in value.contractual_shares.shares
    }


def _allocation_set_ids(
    value: (
        ScheduledPrincipalAllocationRegimeSet
        | UnscheduledPrincipalAllocationRegimeSet
    ),
) -> set[SecuritizationTrancheId]:
    result = _allocation_ids(value.base.allocation_contract)
    for regime in value.conditioned:
        result.update(_allocation_ids(regime.allocation_contract))
    return result


@dataclass(frozen=True, slots=True)
class SecuritizationDeal:
    deal_id: SecuritizationDealId
    deal_identity_id: EconomicIdentityId
    pools: tuple[SecuritizationPool, ...]
    tranches: tuple[SecuritizationTranche, ...]
    condition_set: ContractualConditionSet
    priority_regime_set: PriorityRegimeSet
    scheduled_allocation_regime_set: ScheduledPrincipalAllocationRegimeSet
    unscheduled_allocation_regime_set: UnscheduledPrincipalAllocationRegimeSet
    evidence_ref: FixedIncomeEvidenceRef

    def __post_init__(self) -> None:
        _require(
            self.deal_id,
            SecuritizationDealId,
            "deal_id",
        )
        _identity(self.deal_identity_id, "deal identity")
        pools_valid = (
            type(self.pools) is tuple
            and bool(self.pools)
            and all(
                isinstance(item, SecuritizationPool)
                for item in self.pools
            )
        )
        if not pools_valid:
            _fail("deal pools must be non-empty typed tuple")
        tranches_valid = (
            type(self.tranches) is tuple
            and bool(self.tranches)
            and all(
                isinstance(item, SecuritizationTranche)
                for item in self.tranches
            )
        )
        if not tranches_valid:
            _fail("deal tranches must be non-empty typed tuple")
        pools = tuple(
            sorted(
                self.pools,
                key=lambda item: item.pool_id.logical_values(),
            )
        )
        tranches = tuple(
            sorted(
                self.tranches,
                key=lambda item: item.tranche_id.logical_values(),
            )
        )
        object.__setattr__(self, "pools", pools)
        object.__setattr__(self, "tranches", tranches)
        pool_ids = [item.pool_id for item in pools]
        tranche_ids = [item.tranche_id for item in tranches]
        if (
            len(set(pool_ids)) != len(pool_ids)
            or len(set(tranche_ids)) != len(tranche_ids)
        ):
            _fail("deal pool/tranche ids must be unique")
        if any(
            item.deal_id != self.deal_id
            for item in pools
        ):
            _fail("all pools must bind parent deal")
        if any(
            item.deal_id != self.deal_id
            for item in tranches
        ):
            _fail("all tranches must bind parent deal")
        pool_id_set = set(pool_ids)
        if any(
            item.pool_id not in pool_id_set
            for item in tranches
        ):
            _fail("every tranche pool_id must resolve inside deal")
        pool_economic = [
            item.pool_identity_id
            for item in pools
        ]
        tranche_economic = [
            item.tranche_identity_id
            for item in tranches
        ]
        if self.deal_identity_id in {
            *pool_economic,
            *tranche_economic,
        }:
            _fail("deal identity must differ from pool/tranche identities")
        if (
            len(set(pool_economic)) != len(pool_economic)
            or len(set(tranche_economic)) != len(tranche_economic)
        ):
            _fail("pool/tranche economic identities must be unique")
        if set(pool_economic).intersection(tranche_economic):
            _fail("pool and tranche economic identities must differ")
        _require(
            self.condition_set,
            ContractualConditionSet,
            "condition_set",
        )
        _require(
            self.priority_regime_set,
            PriorityRegimeSet,
            "priority_regime_set",
        )
        _require(
            self.scheduled_allocation_regime_set,
            ScheduledPrincipalAllocationRegimeSet,
            "scheduled allocation set",
        )
        _require(
            self.unscheduled_allocation_regime_set,
            UnscheduledPrincipalAllocationRegimeSet,
            "unscheduled allocation set",
        )
        owned_deal_ids = (
            self.condition_set.deal_id,
            self.priority_regime_set.deal_id,
            self.scheduled_allocation_regime_set.deal_id,
            self.unscheduled_allocation_regime_set.deal_id,
        )
        if any(
            value != self.deal_id
            for value in owned_deal_ids
        ):
            _fail("all deal-owned sets must bind parent deal")
        tranche_set = set(tranche_ids)
        if not _priority_ids(
            self.priority_regime_set
        ).issubset(tranche_set):
            _fail("priority regime references foreign tranche")
        if not _allocation_set_ids(
            self.scheduled_allocation_regime_set
        ).issubset(tranche_set):
            _fail("scheduled allocation references foreign tranche")
        if not _allocation_set_ids(
            self.unscheduled_allocation_regime_set
        ).issubset(tranche_set):
            _fail("unscheduled allocation references foreign tranche")
        known_conditions = {
            item.condition_id
            for item in self.condition_set.event_conditions
        }
        known_conditions.update(
            item.condition_id
            for item in self.condition_set.performance_test_conditions
        )
        known_conditions.update(
            item.condition_id
            for item in self.condition_set.composite_conditions
        )
        if any(
            item.condition_id not in known_conditions
            for item in self.priority_regime_set.conditioned
        ):
            _fail(
                "conditioned priority regime references orphan condition"
            )
        if any(
            item.condition_id not in known_conditions
            for item in self.scheduled_allocation_regime_set.conditioned
        ):
            _fail(
                "conditioned scheduled allocation references orphan condition"
            )
        if any(
            item.condition_id not in known_conditions
            for item in self.unscheduled_allocation_regime_set.conditioned
        ):
            _fail(
                "conditioned unscheduled allocation references orphan condition"
            )
        _evidence(self.evidence_ref, "deal evidence")

    def logical_values(self) -> tuple[object, ...]:
        return (
            "securitization-deal",
            self.deal_id.logical_values(),
            self.deal_identity_id.logical_values(),
            tuple(
                item.logical_values()
                for item in self.pools
            ),
            tuple(
                item.logical_values()
                for item in self.tranches
            ),
            self.condition_set.logical_values(),
            self.priority_regime_set.logical_values(),
            self.scheduled_allocation_regime_set.logical_values(),
            self.unscheduled_allocation_regime_set.logical_values(),
            self.evidence_ref.logical_values(),
        )
