from __future__ import annotations

from dataclasses import dataclass
from datetime import date
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
    StructuredObservationMode,
)
from qore.infrastructure.universal_instrument_identity import EconomicIdentityId
from qore.kernel.errors import InfrastructureError


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


@dataclass(frozen=True, slots=True)
class AsianAveragingObservation:
    observation_date: date
    weight: Decimal | None = None

    def __post_init__(self) -> None:
        _date(self.observation_date, "asian observation date")
        if self.weight is not None:
            _positive(self.weight, "asian observation weight")

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.observation_date.isoformat(),
            _decimal(self.weight) if self.weight is not None else None,
        )


@dataclass(frozen=True, slots=True)
class AsianAveragingPeriod:
    explicit_observations: tuple[AsianAveragingObservation, ...] = ()
    schedule_code: AsianAveragingScheduleCode | None = None

    def __post_init__(self) -> None:
        if type(self.explicit_observations) is not tuple:
            raise OptionExoticValidationError("asian observations must be immutable tuple")
        if any(
            not isinstance(item, AsianAveragingObservation)
            for item in self.explicit_observations
        ):
            raise OptionExoticValidationError("asian observation has invalid type")
        if self.schedule_code is not None and not isinstance(
            self.schedule_code, AsianAveragingScheduleCode
        ):
            raise OptionExoticValidationError("asian schedule code has invalid type")
        if not self.explicit_observations and self.schedule_code is None:
            raise OptionExoticValidationError("asian period requires observations and/or schedule")
        dates = tuple(item.observation_date for item in self.explicit_observations)
        if len(set(dates)) != len(dates):
            raise OptionExoticValidationError("asian observation dates must be unique")
        object.__setattr__(
            self,
            "explicit_observations",
            tuple(sorted(self.explicit_observations, key=lambda item: item.observation_date)),
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            tuple(item.logical_values() for item in self.explicit_observations),
            self.schedule_code.logical_values() if self.schedule_code is not None else None,
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
            if period is not None and any(
                item.observation_date > self.expiry_date for item in period.explicit_observations
            ):
                raise OptionExoticValidationError("asian observation must not follow expiry")

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
            self.multiplier.logical_values() if self.multiplier is not None else None,
            self.notional.logical_values() if self.notional is not None else None,
        )
