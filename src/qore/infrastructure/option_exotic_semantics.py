from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from re import fullmatch

from qore.infrastructure.derivative_contract_semantics import (
    DerivativeContractMultiplier,
    DerivativeEvidenceRef,
    DerivativeNotional,
    DerivativeSettlementStyle,
    DerivativeStrike,
    DerivativeTermsId,
    OptionContractTerms,
    OptionExerciseTerms,
    OptionRight,
)
from qore.infrastructure.structured_hybrid_synthetic_semantics import (
    StructuredBarrierFeature,
    StructuredFeatureId,
    StructuredObservationMode,
    StructuredObservationScheduleCode,
)
from qore.infrastructure.universal_instrument_identity import EconomicIdentityId
from qore.kernel.errors import InfrastructureError
from qore.kernel.temporal import is_timezone_aware_datetime


class OptionExoticSemanticsError(InfrastructureError):
    __slots__ = ()


class OptionExoticValidationError(OptionExoticSemanticsError):
    __slots__ = ()


def _identity(value: EconomicIdentityId, name: str) -> None:
    if not isinstance(value, EconomicIdentityId):
        raise OptionExoticValidationError(f"{name} must be EconomicIdentityId")


def _date(value: date, name: str) -> None:
    if type(value) is not date:
        raise OptionExoticValidationError(f"{name} must be date")


def _positive(value: Decimal, name: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite() or value <= 0:
        raise OptionExoticValidationError(f"{name} must be a positive finite Decimal")


def _nonnegative(value: Decimal, name: str) -> None:
    if type(value) is not Decimal or not value.is_finite() or value < 0:
        raise OptionExoticValidationError(f"{name} must be a non-negative finite Decimal")


def _finite(value: Decimal, name: str) -> None:
    if type(value) is not Decimal or not value.is_finite():
        raise OptionExoticValidationError(f"{name} must be a finite Decimal")


def _exercise_chronology(
    exercise: OptionExerciseTerms,
    expiry_date: date,
    name: str,
) -> None:
    if not isinstance(exercise, OptionExerciseTerms):
        raise OptionExoticValidationError(f"{name} exercise has invalid type")
    if (
        exercise.american_start_date is not None
        and exercise.american_start_date > expiry_date
    ):
        raise OptionExoticValidationError(f"{name} American start must not follow expiry")
    if any(value > expiry_date for value in exercise.bermudan_dates):
        raise OptionExoticValidationError(f"{name} Bermudan date must not follow expiry")


def _aware_datetime(value: datetime, name: str) -> None:
    if type(value) is not datetime or not is_timezone_aware_datetime(value):
        raise OptionExoticValidationError(f"{name} must be an aware datetime")


def _code(value: str, name: str) -> None:
    if (
        not isinstance(value, str)
        or len(value) > 64
        or fullmatch(r"[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*", value) is None
    ):
        raise OptionExoticValidationError(f"{name} must use canonical lowercase code syntax")


def _decimal(value: Decimal) -> str:
    normalized = value.normalize()
    return "0" if normalized == 0 else format(normalized, "f")


class DigitalTriggerStyle(StrEnum):
    EXPIRY = "expiry"
    TOUCH = "touch"


class DigitalTouchCondition(StrEnum):
    TOUCH = "touch"
    NO_TOUCH = "no-touch"


class DigitalPayoutKind(StrEnum):
    CASH = "cash"
    ASSET = "asset"


class DigitalPayoutTiming(StrEnum):
    IMMEDIATE = "immediate"
    DEFERRED = "deferred"


class AsianAveragingRole(StrEnum):
    IN = "in"
    OUT = "out"
    BOTH = "both"


class AsianAveragingObservationKind(StrEnum):
    UNWEIGHTED = "unweighted"
    WEIGHTED = "weighted"


@dataclass(frozen=True, slots=True)
class AsianAveragingMethodCode:
    value: str

    def __post_init__(self) -> None:
        _code(self.value, "asian averaging method code")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class AsianAveragingScheduleCode:
    value: str

    def __post_init__(self) -> None:
        _code(self.value, "asian averaging schedule code")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class AsianAveragingLiteralDate:
    value: date

    def __post_init__(self) -> None:
        _date(self.value, "asian observation literal date")

    def logical_values(self) -> tuple[str, ...]:
        return ("literal-date", self.value.isoformat())


@dataclass(frozen=True, slots=True)
class AsianAveragingLiteralDateTime:
    value: datetime

    def __post_init__(self) -> None:
        _aware_datetime(self.value, "asian observation literal datetime")

    def logical_values(self) -> tuple[str, ...]:
        return ("literal-datetime", self.value.isoformat())


@dataclass(frozen=True, slots=True)
class AsianAveragingScheduleObservation:
    schedule_code: AsianAveragingScheduleCode
    observation_number: int

    def __post_init__(self) -> None:
        if type(self.schedule_code) is not AsianAveragingScheduleCode:
            raise OptionExoticValidationError("schedule observation code has invalid type")
        if type(self.observation_number) is not int or self.observation_number <= 0:
            raise OptionExoticValidationError(
                "schedule observation number must be a positive int"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "schedule-observation",
            self.schedule_code.logical_values(),
            str(self.observation_number),
        )


@dataclass(frozen=True, slots=True)
class DigitalPayoutAmount:
    value: Decimal
    unit_identity_id: EconomicIdentityId

    def __post_init__(self) -> None:
        _positive(self.value, "digital payout amount")
        _identity(self.unit_identity_id, "digital payout unit identity")

    def logical_values(self) -> tuple[object, ...]:
        return (_decimal(self.value), self.unit_identity_id.logical_values())


@dataclass(frozen=True, slots=True)
class DigitalOptionPayout:
    kind: DigitalPayoutKind
    amount: DigitalPayoutAmount
    timing: DigitalPayoutTiming
    evidence_ref: DerivativeEvidenceRef

    def __post_init__(self) -> None:
        if not isinstance(self.kind, DigitalPayoutKind):
            raise OptionExoticValidationError("digital payout kind must be DigitalPayoutKind")
        if not isinstance(self.amount, DigitalPayoutAmount):
            raise OptionExoticValidationError("digital payout amount must be DigitalPayoutAmount")
        if not isinstance(self.timing, DigitalPayoutTiming):
            raise OptionExoticValidationError("digital payout timing must be DigitalPayoutTiming")
        if not isinstance(self.evidence_ref, DerivativeEvidenceRef):
            raise OptionExoticValidationError(
                "digital payout evidence must be DerivativeEvidenceRef"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.kind.value,
            self.amount.logical_values(),
            self.timing.value,
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class DigitalOptionTrigger:
    barrier: StructuredBarrierFeature
    style: DigitalTriggerStyle
    touch_condition: DigitalTouchCondition | None
    evidence_ref: DerivativeEvidenceRef

    def __post_init__(self) -> None:
        if not isinstance(self.barrier, StructuredBarrierFeature):
            raise OptionExoticValidationError("digital trigger must reuse StructuredBarrierFeature")
        if not isinstance(self.style, DigitalTriggerStyle):
            raise OptionExoticValidationError("digital trigger style must be DigitalTriggerStyle")
        if self.touch_condition is not None and not isinstance(
            self.touch_condition, DigitalTouchCondition
        ):
            raise OptionExoticValidationError("digital touch condition has invalid type")
        if not isinstance(self.evidence_ref, DerivativeEvidenceRef):
            raise OptionExoticValidationError("digital trigger evidence has invalid type")
        if self.style is DigitalTriggerStyle.EXPIRY and self.touch_condition is not None:
            raise OptionExoticValidationError("expiry trigger must not carry touch condition")
        if self.style is DigitalTriggerStyle.TOUCH and self.touch_condition is None:
            raise OptionExoticValidationError("touch trigger requires touch/no-touch condition")

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.barrier.logical_values(),
            self.style.value,
            self.touch_condition.value if self.touch_condition is not None else None,
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class BarrierOptionTerms:
    option: OptionContractTerms
    barriers: tuple[StructuredBarrierFeature, ...]
    evidence_ref: DerivativeEvidenceRef

    def __post_init__(self) -> None:
        if not isinstance(self.option, OptionContractTerms):
            raise OptionExoticValidationError("barrier option must compose OptionContractTerms")
        if type(self.barriers) is not tuple or not self.barriers:
            raise OptionExoticValidationError(
                "barrier option requires immutable non-empty barriers"
            )
        for barrier in self.barriers:
            if not isinstance(barrier, StructuredBarrierFeature):
                raise OptionExoticValidationError(
                    "barrier option must reuse StructuredBarrierFeature"
                )
            if barrier.reference_identity_id != self.option.underlying_identity_id:
                raise OptionExoticValidationError("barrier reference must equal option underlying")
            if any(d > self.option.expiry_date for d in barrier.observation.explicit_dates):
                raise OptionExoticValidationError("barrier observation must not follow expiry")
        ids = tuple(barrier.feature_id for barrier in self.barriers)
        if len(set(ids)) != len(ids):
            raise OptionExoticValidationError("barrier feature ids must be unique")
        object.__setattr__(
            self,
            "barriers",
            tuple(sorted(self.barriers, key=lambda barrier: str(barrier.feature_id.value))),
        )
        if not isinstance(self.evidence_ref, DerivativeEvidenceRef):
            raise OptionExoticValidationError("barrier option evidence has invalid type")

    def logical_values(self) -> tuple[object, ...]:
        return (
            "barrier-option",
            self.option.logical_values(),
            tuple(barrier.logical_values() for barrier in self.barriers),
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class DigitalOptionTerms:
    terms_id: DerivativeTermsId
    instrument_identity_id: EconomicIdentityId
    underlying_identity_id: EconomicIdentityId
    settlement_identity_id: EconomicIdentityId
    expiry_date: date
    triggers: tuple[DigitalOptionTrigger, ...]
    payout: DigitalOptionPayout
    evidence_ref: DerivativeEvidenceRef

    def __post_init__(self) -> None:
        if not isinstance(self.terms_id, DerivativeTermsId):
            raise OptionExoticValidationError("digital terms_id must be DerivativeTermsId")
        _identity(self.instrument_identity_id, "digital instrument identity")
        _identity(self.underlying_identity_id, "digital underlying identity")
        _identity(self.settlement_identity_id, "digital settlement identity")
        if self.instrument_identity_id == self.underlying_identity_id:
            raise OptionExoticValidationError("digital instrument and underlying must differ")
        if self.instrument_identity_id == self.settlement_identity_id:
            raise OptionExoticValidationError("digital instrument and settlement must differ")
        _date(self.expiry_date, "digital expiry")
        if type(self.triggers) is not tuple or len(self.triggers) != 1:
            raise OptionExoticValidationError("bounded digital option requires exactly one trigger")
        trigger = self.triggers[0]
        if not isinstance(trigger, DigitalOptionTrigger):
            raise OptionExoticValidationError("digital trigger has invalid type")
        if trigger.barrier.reference_identity_id != self.underlying_identity_id:
            raise OptionExoticValidationError("digital trigger reference must equal underlying")
        if any(d > self.expiry_date for d in trigger.barrier.observation.explicit_dates):
            raise OptionExoticValidationError("digital observation must not follow expiry")
        if (
            trigger.style is DigitalTriggerStyle.EXPIRY
            and trigger.barrier.observation.mode is StructuredObservationMode.CONTINUOUS
        ):
            raise OptionExoticValidationError("expiry trigger must not use continuous observation")
        if (
            trigger.style is DigitalTriggerStyle.EXPIRY
            and trigger.barrier.observation.explicit_dates
            and trigger.barrier.observation.explicit_dates != (self.expiry_date,)
        ):
            raise OptionExoticValidationError("expiry observation must equal option expiry")
        if not isinstance(self.payout, DigitalOptionPayout):
            raise OptionExoticValidationError("digital payout has invalid type")
        if not isinstance(self.evidence_ref, DerivativeEvidenceRef):
            raise OptionExoticValidationError("digital option evidence has invalid type")

    def logical_values(self) -> tuple[object, ...]:
        return (
            "digital-option",
            self.terms_id.logical_values(),
            self.instrument_identity_id.logical_values(),
            self.underlying_identity_id.logical_values(),
            self.settlement_identity_id.logical_values(),
            self.expiry_date.isoformat(),
            tuple(trigger.logical_values() for trigger in self.triggers),
            self.payout.logical_values(),
            self.evidence_ref.logical_values(),
        )


def _asian_locator_kind(locator: object) -> int:
    if type(locator) is AsianAveragingLiteralDate:
        return 0
    if type(locator) is AsianAveragingLiteralDateTime:
        return 1
    if type(locator) is AsianAveragingScheduleObservation:
        return 2
    raise OptionExoticValidationError("invalid asian observation locator type")


def _asian_locator_key(locator: object) -> tuple[object, ...]:
    if type(locator) is AsianAveragingLiteralDate:
        return (0, locator.value.toordinal())
    if type(locator) is AsianAveragingLiteralDateTime:
        return (
            1,
            locator.value,
            locator.value.isoformat(),
        )
    if type(locator) is AsianAveragingScheduleObservation:
        return (2, locator.schedule_code.value, locator.observation_number)
    raise OptionExoticValidationError("invalid asian observation locator type")


def _asian_observation_sort_key(
    observation: AsianAveragingObservation,
) -> tuple[object, ...]:
    return _asian_locator_key(observation.locator)


@dataclass(frozen=True, slots=True)
class AsianAveragingObservation:
    locator: (
        AsianAveragingLiteralDate
        | AsianAveragingLiteralDateTime
        | AsianAveragingScheduleObservation
    )
    weight: Decimal | None = None

    def __post_init__(self) -> None:
        if type(self.locator) not in (
            AsianAveragingLiteralDate,
            AsianAveragingLiteralDateTime,
            AsianAveragingScheduleObservation,
        ):
            raise OptionExoticValidationError("asian observation locator has invalid type")
        if self.weight is not None:
            _nonnegative(self.weight, "asian observation weight")

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.locator.logical_values(),
            _decimal(self.weight) if self.weight is not None else None,
        )


@dataclass(frozen=True, slots=True)
class AsianAveragingPeriod:
    explicit_observations: tuple[AsianAveragingObservation, ...] = ()
    schedule_codes: tuple[AsianAveragingScheduleCode, ...] = ()
    observation_kind: AsianAveragingObservationKind | None = None

    def __post_init__(self) -> None:
        if type(self.explicit_observations) is not tuple:
            raise OptionExoticValidationError("asian observations must be immutable tuple")
        if any(
            type(item) is not AsianAveragingObservation
            for item in self.explicit_observations
        ):
            raise OptionExoticValidationError("asian observation has invalid type")

        if type(self.schedule_codes) is not tuple:
            raise OptionExoticValidationError("asian schedule codes must be immutable tuple")
        if any(
            type(item) is not AsianAveragingScheduleCode
            for item in self.schedule_codes
        ):
            raise OptionExoticValidationError("asian schedule code has invalid type")

        if not self.explicit_observations and not self.schedule_codes:
            raise OptionExoticValidationError("asian period requires observations and/or schedules")

        if self.explicit_observations and self.observation_kind is None:
            raise OptionExoticValidationError(
                "explicit asian observations require observation kind"
            )
        if not self.explicit_observations and self.observation_kind is not None:
            raise OptionExoticValidationError("observation kind requires explicit observations")
        if self.observation_kind is not None and not isinstance(
            self.observation_kind, AsianAveragingObservationKind
        ):
            raise OptionExoticValidationError("asian observation kind has invalid type")

        if len(set(code.value for code in self.schedule_codes)) != len(self.schedule_codes):
            raise OptionExoticValidationError("asian schedule codes must be unique")
        object.__setattr__(
            self,
            "schedule_codes",
            tuple(sorted(self.schedule_codes, key=lambda code: code.value)),
        )

        if self.observation_kind is AsianAveragingObservationKind.UNWEIGHTED:
            for observation in self.explicit_observations:
                if type(observation.locator) is AsianAveragingScheduleObservation:
                    raise OptionExoticValidationError(
                        "unweighted observations cannot use schedule locator"
                    )
                if observation.weight is not None:
                    raise OptionExoticValidationError(
                        "unweighted observations cannot carry explicit weight"
                    )

        for observation in self.explicit_observations:
            locator = observation.locator
            if type(locator) is AsianAveragingScheduleObservation:
                if locator.schedule_code not in self.schedule_codes:
                    raise OptionExoticValidationError(
                        "schedule observation code must appear in period schedules"
                    )

        if len(
            {_asian_locator_key(item.locator) for item in self.explicit_observations}
        ) != len(self.explicit_observations):
            raise OptionExoticValidationError("asian observation locators must be unique")

        object.__setattr__(
            self,
            "explicit_observations",
            tuple(
                sorted(
                    self.explicit_observations,
                    key=_asian_observation_sort_key,
                )
            ),
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            tuple(item.logical_values() for item in self.explicit_observations),
            tuple(code.logical_values() for code in self.schedule_codes),
            self.observation_kind.value if self.observation_kind is not None else None,
        )


@dataclass(frozen=True, slots=True)
class AsianOptionTerms:
    terms_id: DerivativeTermsId
    instrument_identity_id: EconomicIdentityId
    underlying_identity_id: EconomicIdentityId
    settlement_identity_id: EconomicIdentityId
    right: OptionRight
    expiry_date: date
    exercise: OptionExerciseTerms
    settlement_style: DerivativeSettlementStyle
    evidence_ref: DerivativeEvidenceRef
    averaging_role: AsianAveragingRole
    averaging_method: AsianAveragingMethodCode
    averaging_period_in: AsianAveragingPeriod | None = None
    averaging_period_out: AsianAveragingPeriod | None = None
    fixed_strike: DerivativeStrike | None = None
    strike_factor: Decimal | None = None
    multiplier: DerivativeContractMultiplier | None = None
    notional: DerivativeNotional | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.terms_id, DerivativeTermsId):
            raise OptionExoticValidationError("asian terms_id has invalid type")
        _identity(self.instrument_identity_id, "asian instrument identity")
        _identity(self.underlying_identity_id, "asian underlying identity")
        _identity(self.settlement_identity_id, "asian settlement identity")
        if self.instrument_identity_id == self.underlying_identity_id:
            raise OptionExoticValidationError("asian instrument and underlying must differ")
        if self.instrument_identity_id == self.settlement_identity_id:
            raise OptionExoticValidationError("asian instrument and settlement must differ")
        if not isinstance(self.right, OptionRight):
            raise OptionExoticValidationError("asian right has invalid type")
        _date(self.expiry_date, "asian expiry")
        if not isinstance(self.exercise, OptionExerciseTerms):
            raise OptionExoticValidationError("asian exercise has invalid type")
        if (
            self.exercise.american_start_date is not None
            and self.exercise.american_start_date > self.expiry_date
        ):
            raise OptionExoticValidationError("asian American start must not follow expiry")
        if any(d > self.expiry_date for d in self.exercise.bermudan_dates):
            raise OptionExoticValidationError("asian Bermudan date must not follow expiry")
        if not isinstance(self.settlement_style, DerivativeSettlementStyle):
            raise OptionExoticValidationError("asian settlement style has invalid type")
        if not isinstance(self.evidence_ref, DerivativeEvidenceRef):
            raise OptionExoticValidationError("asian evidence has invalid type")
        if not isinstance(self.averaging_role, AsianAveragingRole):
            raise OptionExoticValidationError("asian averaging role has invalid type")
        if not isinstance(self.averaging_method, AsianAveragingMethodCode):
            raise OptionExoticValidationError("asian averaging method has invalid type")
        if self.averaging_period_in is not None and not isinstance(
            self.averaging_period_in, AsianAveragingPeriod
        ):
            raise OptionExoticValidationError("asian averaging-in period has invalid type")
        if self.averaging_period_out is not None and not isinstance(
            self.averaging_period_out, AsianAveragingPeriod
        ):
            raise OptionExoticValidationError("asian averaging-out period has invalid type")
        if self.fixed_strike is not None and not isinstance(self.fixed_strike, DerivativeStrike):
            raise OptionExoticValidationError("asian fixed strike has invalid type")
        if self.strike_factor is not None:
            if type(self.strike_factor) is not Decimal or not self.strike_factor.is_finite():
                raise OptionExoticValidationError("asian strike factor must be finite Decimal")
        if self.multiplier is not None and not isinstance(
            self.multiplier, DerivativeContractMultiplier
        ):
            raise OptionExoticValidationError("asian multiplier has invalid type")
        if self.notional is not None and not isinstance(self.notional, DerivativeNotional):
            raise OptionExoticValidationError("asian notional has invalid type")
        if self.multiplier is None and self.notional is None:
            raise OptionExoticValidationError("asian option requires multiplier and/or notional")

        if self.averaging_role is AsianAveragingRole.IN:
            if self.averaging_period_in is None or self.averaging_period_out is not None:
                raise OptionExoticValidationError("averaging-in requires only in period")
            if self.fixed_strike is not None:
                raise OptionExoticValidationError("averaging-in must not carry fixed strike")
        elif self.averaging_role is AsianAveragingRole.OUT:
            if self.averaging_period_out is None or self.averaging_period_in is not None:
                raise OptionExoticValidationError("averaging-out requires only out period")
            if self.fixed_strike is None:
                raise OptionExoticValidationError("averaging-out requires fixed strike")
        else:
            if self.averaging_period_in is None or self.averaging_period_out is None:
                raise OptionExoticValidationError("averaging-both requires both periods")
            if self.fixed_strike is not None:
                raise OptionExoticValidationError("averaging-both must not carry fixed strike")

        for period in (self.averaging_period_in, self.averaging_period_out):
            if period is None:
                continue
            for observation in period.explicit_observations:
                locator = observation.locator
                if type(locator) is AsianAveragingLiteralDate:
                    if locator.value > self.expiry_date:
                        raise OptionExoticValidationError(
                            "asian observation must not follow expiry"
                        )
                elif type(locator) is AsianAveragingLiteralDateTime:
                    if locator.value.date() > self.expiry_date:
                        raise OptionExoticValidationError(
                            "asian observation must not follow expiry"
                        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "asian-option",
            self.terms_id.logical_values(),
            self.instrument_identity_id.logical_values(),
            self.underlying_identity_id.logical_values(),
            self.settlement_identity_id.logical_values(),
            self.right.value,
            self.expiry_date.isoformat(),
            self.exercise.logical_values(),
            self.settlement_style.value,
            self.evidence_ref.logical_values(),
            self.averaging_role.value,
            self.averaging_method.logical_values(),
            self.averaging_period_in.logical_values()
            if self.averaging_period_in is not None
            else None,
            self.averaging_period_out.logical_values()
            if self.averaging_period_out is not None
            else None,
            self.fixed_strike.logical_values() if self.fixed_strike is not None else None,
            _decimal(self.strike_factor) if self.strike_factor is not None else None,
            self.multiplier.logical_values() if self.multiplier is not None else None,
            self.notional.logical_values() if self.notional is not None else None,
        )


class LookbackKind(StrEnum):
    FIXED_STRIKE = "fixed-strike"
    FLOATING_STRIKE = "floating-strike"


class LookbackExtremumRole(StrEnum):
    MIN = "min"
    MAX = "max"


@dataclass(frozen=True, slots=True)
class LookbackOptionTerms:
    terms_id: DerivativeTermsId
    instrument_identity_id: EconomicIdentityId
    underlying_identity_id: EconomicIdentityId
    settlement_identity_id: EconomicIdentityId
    right: OptionRight
    kind: LookbackKind
    observation_window_start: date
    observation_window_end: date
    extremum_role: LookbackExtremumRole
    expiry_date: date
    exercise: OptionExerciseTerms
    settlement_style: DerivativeSettlementStyle
    evidence_ref: DerivativeEvidenceRef
    fixed_strike: DerivativeStrike | None = None
    observation_schedule: StructuredObservationScheduleCode | None = None
    multiplier: DerivativeContractMultiplier | None = None
    notional: DerivativeNotional | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.terms_id, DerivativeTermsId):
            raise OptionExoticValidationError("lookback terms_id has invalid type")
        _identity(self.instrument_identity_id, "lookback instrument identity")
        _identity(self.underlying_identity_id, "lookback underlying identity")
        _identity(self.settlement_identity_id, "lookback settlement identity")
        if self.instrument_identity_id == self.underlying_identity_id:
            raise OptionExoticValidationError("lookback instrument and underlying must differ")
        if self.instrument_identity_id == self.settlement_identity_id:
            raise OptionExoticValidationError("lookback instrument and settlement must differ")
        if not isinstance(self.right, OptionRight):
            raise OptionExoticValidationError("lookback right has invalid type")
        if not isinstance(self.kind, LookbackKind):
            raise OptionExoticValidationError("lookback kind has invalid type")
        if self.fixed_strike is not None and not isinstance(self.fixed_strike, DerivativeStrike):
            raise OptionExoticValidationError("lookback fixed strike has invalid type")
        if self.kind is LookbackKind.FIXED_STRIKE and self.fixed_strike is None:
            raise OptionExoticValidationError("fixed-strike lookback requires fixed strike")
        if self.kind is LookbackKind.FLOATING_STRIKE and self.fixed_strike is not None:
            raise OptionExoticValidationError("floating-strike lookback forbids fixed strike")
        _date(self.observation_window_start, "lookback observation window start")
        _date(self.observation_window_end, "lookback observation window end")
        _date(self.expiry_date, "lookback expiry")
        if not self.observation_window_start < self.observation_window_end:
            raise OptionExoticValidationError("lookback observation window must be increasing")
        if self.observation_window_end > self.expiry_date:
            raise OptionExoticValidationError("lookback observation window must not follow expiry")
        if not isinstance(self.extremum_role, LookbackExtremumRole):
            raise OptionExoticValidationError("lookback extremum role has invalid type")
        if self.observation_schedule is not None and not isinstance(
            self.observation_schedule, StructuredObservationScheduleCode
        ):
            raise OptionExoticValidationError("lookback observation schedule has invalid type")
        _exercise_chronology(self.exercise, self.expiry_date, "lookback")
        if not isinstance(self.settlement_style, DerivativeSettlementStyle):
            raise OptionExoticValidationError("lookback settlement style has invalid type")
        if not isinstance(self.evidence_ref, DerivativeEvidenceRef):
            raise OptionExoticValidationError("lookback evidence has invalid type")
        if self.multiplier is not None and not isinstance(
            self.multiplier, DerivativeContractMultiplier
        ):
            raise OptionExoticValidationError("lookback multiplier has invalid type")
        if self.notional is not None and not isinstance(self.notional, DerivativeNotional):
            raise OptionExoticValidationError("lookback notional has invalid type")
        if self.multiplier is None and self.notional is None:
            raise OptionExoticValidationError("lookback requires multiplier and/or notional")

    def logical_values(self) -> tuple[object, ...]:
        return (
            "lookback-option",
            self.terms_id.logical_values(),
            self.instrument_identity_id.logical_values(),
            self.underlying_identity_id.logical_values(),
            self.settlement_identity_id.logical_values(),
            self.right.value,
            self.kind.value,
            self.fixed_strike.logical_values() if self.fixed_strike is not None else None,
            self.observation_window_start.isoformat(),
            self.observation_window_end.isoformat(),
            self.extremum_role.value,
            self.observation_schedule.logical_values()
            if self.observation_schedule is not None
            else None,
            self.expiry_date.isoformat(),
            self.exercise.logical_values(),
            self.settlement_style.value,
            self.evidence_ref.logical_values(),
            self.multiplier.logical_values() if self.multiplier is not None else None,
            self.notional.logical_values() if self.notional is not None else None,
        )


@dataclass(frozen=True, slots=True)
class ChooserOptionTerms:
    terms_id: DerivativeTermsId
    instrument_identity_id: EconomicIdentityId
    underlying_identity_id: EconomicIdentityId
    settlement_identity_id: EconomicIdentityId
    allowed_rights: tuple[OptionRight, ...]
    common_strike: DerivativeStrike
    decision_date: date
    expiry_date: date
    exercise: OptionExerciseTerms
    settlement_style: DerivativeSettlementStyle
    evidence_ref: DerivativeEvidenceRef
    multiplier: DerivativeContractMultiplier | None = None
    notional: DerivativeNotional | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.terms_id, DerivativeTermsId):
            raise OptionExoticValidationError("chooser terms_id has invalid type")
        _identity(self.instrument_identity_id, "chooser instrument identity")
        _identity(self.underlying_identity_id, "chooser underlying identity")
        _identity(self.settlement_identity_id, "chooser settlement identity")
        if self.instrument_identity_id == self.underlying_identity_id:
            raise OptionExoticValidationError("chooser instrument and underlying must differ")
        if self.instrument_identity_id == self.settlement_identity_id:
            raise OptionExoticValidationError("chooser instrument and settlement must differ")
        if type(self.allowed_rights) is not tuple:
            raise OptionExoticValidationError("chooser allowed rights must be immutable tuple")
        if any(not isinstance(value, OptionRight) for value in self.allowed_rights):
            raise OptionExoticValidationError("chooser allowed right has invalid type")
        if len(set(self.allowed_rights)) != len(self.allowed_rights):
            raise OptionExoticValidationError("chooser allowed rights must be unique")
        if set(self.allowed_rights) != {OptionRight.CALL, OptionRight.PUT}:
            raise OptionExoticValidationError("chooser requires exactly CALL and PUT rights")
        object.__setattr__(
            self,
            "allowed_rights",
            tuple(sorted(self.allowed_rights, key=lambda value: value.value)),
        )
        if not isinstance(self.common_strike, DerivativeStrike):
            raise OptionExoticValidationError("chooser common strike has invalid type")
        _date(self.decision_date, "chooser decision date")
        _date(self.expiry_date, "chooser expiry")
        if not self.decision_date < self.expiry_date:
            raise OptionExoticValidationError("chooser decision date must precede expiry")
        _exercise_chronology(self.exercise, self.expiry_date, "chooser")
        if not isinstance(self.settlement_style, DerivativeSettlementStyle):
            raise OptionExoticValidationError("chooser settlement style has invalid type")
        if not isinstance(self.evidence_ref, DerivativeEvidenceRef):
            raise OptionExoticValidationError("chooser evidence has invalid type")
        if self.multiplier is not None and not isinstance(
            self.multiplier, DerivativeContractMultiplier
        ):
            raise OptionExoticValidationError("chooser multiplier has invalid type")
        if self.notional is not None and not isinstance(self.notional, DerivativeNotional):
            raise OptionExoticValidationError("chooser notional has invalid type")
        if self.multiplier is None and self.notional is None:
            raise OptionExoticValidationError("chooser requires multiplier and/or notional")

    def logical_values(self) -> tuple[object, ...]:
        return (
            "chooser-option",
            self.terms_id.logical_values(),
            self.instrument_identity_id.logical_values(),
            self.underlying_identity_id.logical_values(),
            self.settlement_identity_id.logical_values(),
            tuple(value.value for value in self.allowed_rights),
            self.common_strike.logical_values(),
            self.decision_date.isoformat(),
            self.expiry_date.isoformat(),
            self.exercise.logical_values(),
            self.settlement_style.value,
            self.evidence_ref.logical_values(),
            self.multiplier.logical_values() if self.multiplier is not None else None,
            self.notional.logical_values() if self.notional is not None else None,
        )


@dataclass(frozen=True, slots=True)
class CompoundOptionRelationship:
    outer_option: OptionContractTerms
    underlying_option: OptionContractTerms
    evidence_ref: DerivativeEvidenceRef

    def __post_init__(self) -> None:
        if not isinstance(self.outer_option, OptionContractTerms):
            raise OptionExoticValidationError("compound outer option has invalid type")
        if not isinstance(self.underlying_option, OptionContractTerms):
            raise OptionExoticValidationError("compound underlying option has invalid type")
        if self.outer_option.terms_id == self.underlying_option.terms_id:
            raise OptionExoticValidationError("compound option terms ids must differ")
        if (
            self.outer_option.underlying_identity_id
            != self.underlying_option.instrument_identity_id
        ):
            raise OptionExoticValidationError(
                "compound outer underlying must equal underlying option instrument"
            )
        if not self.outer_option.expiry_date < self.underlying_option.expiry_date:
            raise OptionExoticValidationError(
                "compound outer expiry must precede underlying option expiry"
            )
        if not isinstance(self.evidence_ref, DerivativeEvidenceRef):
            raise OptionExoticValidationError("compound evidence has invalid type")

    def logical_values(self) -> tuple[object, ...]:
        return (
            "compound-option",
            self.outer_option.logical_values(),
            self.underlying_option.logical_values(),
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class CliquetStrikeConventionCode:
    value: str

    def __post_init__(self) -> None:
        _code(self.value, "cliquet strike convention code")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class CliquetOptionFeature:
    option: OptionContractTerms
    reset_dates: tuple[date, ...]
    local_strike_convention: CliquetStrikeConventionCode
    evidence_ref: DerivativeEvidenceRef
    local_cap: Decimal | None = None
    local_floor: Decimal | None = None
    local_reset_observation_window: tuple[date, date] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.option, OptionContractTerms):
            raise OptionExoticValidationError("cliquet option has invalid type")
        if type(self.reset_dates) is not tuple or not self.reset_dates:
            raise OptionExoticValidationError(
                "cliquet reset dates must be immutable non-empty tuple"
            )
        for reset_date in self.reset_dates:
            _date(reset_date, "cliquet reset date")
            if reset_date >= self.option.expiry_date:
                raise OptionExoticValidationError("cliquet reset date must precede option expiry")
        if len(set(self.reset_dates)) != len(self.reset_dates):
            raise OptionExoticValidationError("cliquet reset dates must be unique")
        object.__setattr__(self, "reset_dates", tuple(sorted(self.reset_dates)))
        if not isinstance(self.local_strike_convention, CliquetStrikeConventionCode):
            raise OptionExoticValidationError("cliquet strike convention has invalid type")
        if self.local_cap is not None:
            _finite(self.local_cap, "cliquet local cap")
        if self.local_floor is not None:
            _finite(self.local_floor, "cliquet local floor")
        if (
            self.local_cap is not None
            and self.local_floor is not None
            and self.local_floor > self.local_cap
        ):
            raise OptionExoticValidationError("cliquet local floor must not exceed local cap")
        if self.local_reset_observation_window is not None:
            if (
                type(self.local_reset_observation_window) is not tuple
                or len(self.local_reset_observation_window) != 2
            ):
                raise OptionExoticValidationError(
                    "cliquet reset observation window must be a two-date tuple"
                )
            start, end = self.local_reset_observation_window
            _date(start, "cliquet reset observation window start")
            _date(end, "cliquet reset observation window end")
            if not start < end:
                raise OptionExoticValidationError(
                    "cliquet reset observation window must be increasing"
                )
            if end > self.option.expiry_date:
                raise OptionExoticValidationError(
                    "cliquet reset observation window must not follow option expiry"
                )
        if not isinstance(self.evidence_ref, DerivativeEvidenceRef):
            raise OptionExoticValidationError("cliquet evidence has invalid type")

    def logical_values(self) -> tuple[object, ...]:
        return (
            "cliquet-option",
            self.option.logical_values(),
            tuple(value.isoformat() for value in self.reset_dates),
            self.local_strike_convention.logical_values(),
            _decimal(self.local_cap) if self.local_cap is not None else None,
            _decimal(self.local_floor) if self.local_floor is not None else None,
            tuple(value.isoformat() for value in self.local_reset_observation_window)
            if self.local_reset_observation_window is not None
            else None,
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class ShoutLockedInReferenceRuleCode:
    value: str

    def __post_init__(self) -> None:
        _code(self.value, "shout locked-in reference rule code")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class ShoutOptionFeature:
    option: OptionContractTerms
    shout_right_count: int
    shout_window_start: date
    shout_window_end: date
    locked_in_reference_rule: ShoutLockedInReferenceRuleCode
    evidence_ref: DerivativeEvidenceRef

    def __post_init__(self) -> None:
        if not isinstance(self.option, OptionContractTerms):
            raise OptionExoticValidationError("shout option has invalid type")
        if type(self.shout_right_count) is not int or self.shout_right_count <= 0:
            raise OptionExoticValidationError("shout right count must be a positive int")
        _date(self.shout_window_start, "shout window start")
        _date(self.shout_window_end, "shout window end")
        if not self.shout_window_start < self.shout_window_end:
            raise OptionExoticValidationError("shout window must be increasing")
        if self.shout_window_end > self.option.expiry_date:
            raise OptionExoticValidationError("shout window must not follow option expiry")
        if not isinstance(self.locked_in_reference_rule, ShoutLockedInReferenceRuleCode):
            raise OptionExoticValidationError("shout locked-in reference rule has invalid type")
        if not isinstance(self.evidence_ref, DerivativeEvidenceRef):
            raise OptionExoticValidationError("shout evidence has invalid type")

    def logical_values(self) -> tuple[object, ...]:
        return (
            "shout-option",
            self.option.logical_values(),
            str(self.shout_right_count),
            self.shout_window_start.isoformat(),
            self.shout_window_end.isoformat(),
            self.locked_in_reference_rule.logical_values(),
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class BarrierRebateTerms:
    barrier_option: BarrierOptionTerms
    barrier_feature_id: StructuredFeatureId
    payout: DigitalOptionPayout
    evidence_ref: DerivativeEvidenceRef

    def __post_init__(self) -> None:
        if not isinstance(self.barrier_option, BarrierOptionTerms):
            raise OptionExoticValidationError("barrier rebate option has invalid type")
        if not isinstance(self.barrier_feature_id, StructuredFeatureId):
            raise OptionExoticValidationError("barrier rebate feature id has invalid type")
        matches = tuple(
            barrier
            for barrier in self.barrier_option.barriers
            if barrier.feature_id == self.barrier_feature_id
        )
        if len(matches) != 1:
            raise OptionExoticValidationError(
                "barrier rebate feature id must bind exactly one option barrier"
            )
        if not isinstance(self.payout, DigitalOptionPayout):
            raise OptionExoticValidationError("barrier rebate payout has invalid type")
        if not isinstance(self.evidence_ref, DerivativeEvidenceRef):
            raise OptionExoticValidationError("barrier rebate evidence has invalid type")

    def logical_values(self) -> tuple[object, ...]:
        return (
            "barrier-rebate",
            self.barrier_option.logical_values(),
            self.barrier_feature_id.logical_values(),
            self.payout.logical_values(),
            self.evidence_ref.logical_values(),
        )

