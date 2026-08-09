from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from enum import StrEnum
from re import fullmatch
from uuid import UUID

from qore.infrastructure.proprietary_accounts import MoneyAmount
from qore.infrastructure.research_run import ResearchRunEvidence
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success

_DECIMAL128 = Context(prec=34, rounding=ROUND_HALF_EVEN)


class ResearchPeriodicEquityError(InfrastructureError):
    """Base error for fixed-period research equity evidence."""

    __slots__ = ()


class ResearchPeriodicEquityValidationError(ResearchPeriodicEquityError):
    """Violation of a fixed-period equity-return invariant."""

    __slots__ = ()


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise ResearchPeriodicEquityValidationError(f"{field_name} must be datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ResearchPeriodicEquityValidationError(
            f"{field_name} must be timezone-aware"
        )


def _validate_token(value: str, *, field_name: str) -> None:
    if not isinstance(value, str) or fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9._/+:-]*",
        value,
    ) is None:
        raise ResearchPeriodicEquityValidationError(
            f"{field_name} must use canonical token syntax"
        )


class ResearchEquityValuationBasis(StrEnum):
    GROSS = "gross"
    NET = "net"


class ResearchEquityFlowStatus(StrEnum):
    BASELINE = "baseline"
    NO_EXTERNAL_FLOW = "no_external_flow"
    EXTERNAL_FLOW_PRESENT = "external_flow_present"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ResearchValuationModelId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ResearchPeriodicEquityValidationError(
                "valuation model id must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ResearchEquityEvidenceReference:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ResearchPeriodicEquityValidationError(
                "equity evidence reference must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ResearchValuationModelBinding:
    """Bind one explicit valuation model to a research run.

    The valuation model is an evidence source, not implemented here. QORE does
    not infer mark-to-market cash value from raw price multiplied by quantity.
    """

    run: ResearchRunEvidence
    model_id: ResearchValuationModelId
    model_version: str
    basis: ResearchEquityValuationBasis
    bound_at: datetime
    evidence_ref: ResearchEquityEvidenceReference

    def __post_init__(self) -> None:
        if not isinstance(self.run, ResearchRunEvidence):
            raise ResearchPeriodicEquityValidationError(
                "valuation binding requires ResearchRunEvidence"
            )
        if not isinstance(self.model_id, ResearchValuationModelId):
            raise ResearchPeriodicEquityValidationError(
                "model_id must be ResearchValuationModelId"
            )
        _validate_token(self.model_version, field_name="valuation model version")
        if not isinstance(self.basis, ResearchEquityValuationBasis):
            raise ResearchPeriodicEquityValidationError(
                "valuation basis must be ResearchEquityValuationBasis"
            )
        if (
            self.basis is ResearchEquityValuationBasis.NET
            and self.run.transaction_cost_model_id is None
        ):
            raise ResearchPeriodicEquityValidationError(
                "net equity valuation requires a transaction-cost model bound to the run"
            )
        _validate_timestamp(self.bound_at, field_name="valuation model bound_at")
        if not isinstance(self.evidence_ref, ResearchEquityEvidenceReference):
            raise ResearchPeriodicEquityValidationError(
                "valuation binding evidence_ref must be ResearchEquityEvidenceReference"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.run.logical_values(),
            self.model_id.logical_values(),
            self.model_version,
            self.basis.value,
            self.bound_at.isoformat(),
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class ResearchEquityObservationId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ResearchPeriodicEquityValidationError(
                "equity observation id must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ResearchEquityValuationObservation:
    """Explicit model-produced equity evidence at one simulated timestamp."""

    observation_id: ResearchEquityObservationId
    binding: ResearchValuationModelBinding
    valued_at: datetime
    equity: MoneyAmount
    flow_status_since_prior: ResearchEquityFlowStatus
    recorded_at: datetime
    evidence_ref: ResearchEquityEvidenceReference

    def __post_init__(self) -> None:
        if not isinstance(self.observation_id, ResearchEquityObservationId):
            raise ResearchPeriodicEquityValidationError(
                "observation_id must be ResearchEquityObservationId"
            )
        if not isinstance(self.binding, ResearchValuationModelBinding):
            raise ResearchPeriodicEquityValidationError(
                "equity observation requires ResearchValuationModelBinding"
            )
        _validate_timestamp(self.valued_at, field_name="equity valued_at")
        if not (
            self.binding.run.simulated_start
            <= self.valued_at
            <= self.binding.run.simulated_end
        ):
            raise ResearchPeriodicEquityValidationError(
                "equity valued_at must remain inside research simulated bounds"
            )
        if not isinstance(self.equity, MoneyAmount) or self.equity.amount <= 0:
            raise ResearchPeriodicEquityValidationError(
                "equity must be a positive MoneyAmount"
            )
        if not isinstance(self.flow_status_since_prior, ResearchEquityFlowStatus):
            raise ResearchPeriodicEquityValidationError(
                "flow_status_since_prior must be ResearchEquityFlowStatus"
            )
        _validate_timestamp(self.recorded_at, field_name="equity recorded_at")
        if self.recorded_at < self.binding.bound_at:
            raise ResearchPeriodicEquityValidationError(
                "equity evidence cannot be recorded before valuation model binding"
            )
        if not isinstance(self.evidence_ref, ResearchEquityEvidenceReference):
            raise ResearchPeriodicEquityValidationError(
                "equity observation evidence_ref must be ResearchEquityEvidenceReference"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.observation_id.logical_values(),
            self.binding.logical_values(),
            self.valued_at.isoformat(),
            self.equity.logical_values(),
            self.flow_status_since_prior.value,
            self.recorded_at.isoformat(),
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class ResearchPeriodicEquityPolicy:
    interval_seconds: int

    def __post_init__(self) -> None:
        if type(self.interval_seconds) is not int or self.interval_seconds <= 0:
            raise ResearchPeriodicEquityValidationError(
                "periodic equity interval_seconds must be a positive integer"
            )

    def logical_values(self) -> tuple[int, ...]:
        return (self.interval_seconds,)


@dataclass(frozen=True, slots=True)
class ResearchPeriodicReturnPoint:
    opened_at: datetime
    closed_at: datetime
    opening_observation_id: ResearchEquityObservationId
    closing_observation_id: ResearchEquityObservationId
    opening_equity: MoneyAmount
    closing_equity: MoneyAmount
    return_rate: Decimal

    def __post_init__(self) -> None:
        _validate_timestamp(self.opened_at, field_name="period opened_at")
        _validate_timestamp(self.closed_at, field_name="period closed_at")
        if self.closed_at <= self.opened_at:
            raise ResearchPeriodicEquityValidationError(
                "period closed_at must be after opened_at"
            )
        if not isinstance(self.opening_observation_id, ResearchEquityObservationId):
            raise ResearchPeriodicEquityValidationError(
                "opening_observation_id must be ResearchEquityObservationId"
            )
        if not isinstance(self.closing_observation_id, ResearchEquityObservationId):
            raise ResearchPeriodicEquityValidationError(
                "closing_observation_id must be ResearchEquityObservationId"
            )
        if not isinstance(self.opening_equity, MoneyAmount):
            raise ResearchPeriodicEquityValidationError(
                "opening_equity must be MoneyAmount"
            )
        if not isinstance(self.closing_equity, MoneyAmount):
            raise ResearchPeriodicEquityValidationError(
                "closing_equity must be MoneyAmount"
            )
        if self.opening_equity.currency != self.closing_equity.currency:
            raise ResearchPeriodicEquityValidationError(
                "period equity values must use one currency"
            )
        if self.opening_equity.amount <= 0 or self.closing_equity.amount <= 0:
            raise ResearchPeriodicEquityValidationError(
                "period equity values must remain positive"
            )
        if not isinstance(self.return_rate, Decimal) or not self.return_rate.is_finite():
            raise ResearchPeriodicEquityValidationError(
                "period return_rate must be a finite Decimal"
            )
        with localcontext(_DECIMAL128):
            expected = self.closing_equity.amount / self.opening_equity.amount - Decimal(1)
        if self.return_rate != expected:
            raise ResearchPeriodicEquityValidationError(
                "period return_rate must equal closing/opening equity minus one"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.opened_at.isoformat(),
            self.closed_at.isoformat(),
            self.opening_observation_id.logical_values(),
            self.closing_observation_id.logical_values(),
            self.opening_equity.logical_values(),
            self.closing_equity.logical_values(),
            format(self.return_rate, "f"),
        )


def _canonical_observations(
    observations: tuple[ResearchEquityValuationObservation, ...],
) -> tuple[ResearchEquityValuationObservation, ...]:
    if not isinstance(observations, tuple) or len(observations) < 2 or any(
        not isinstance(item, ResearchEquityValuationObservation) for item in observations
    ):
        raise ResearchPeriodicEquityValidationError(
            "periodic equity requires at least two immutable valuation observations"
        )
    ordered = tuple(
        sorted(
            observations,
            key=lambda item: (item.valued_at, str(item.observation_id.value)),
        )
    )
    ids = tuple(item.observation_id for item in ordered)
    if len(set(ids)) != len(ids):
        raise ResearchPeriodicEquityValidationError(
            "equity observation ids must be unique"
        )
    binding = ordered[0].binding
    if any(item.binding != binding for item in ordered):
        raise ResearchPeriodicEquityValidationError(
            "periodic equity observations must use one exact valuation binding"
        )
    currency = ordered[0].equity.currency
    if any(item.equity.currency != currency for item in ordered):
        raise ResearchPeriodicEquityValidationError(
            "periodic equity observations must use one currency"
        )
    return ordered


def _expected_timestamps(
    run: ResearchRunEvidence,
    policy: ResearchPeriodicEquityPolicy,
) -> tuple[datetime, ...]:
    duration_seconds = (run.simulated_end - run.simulated_start).total_seconds()
    if not duration_seconds.is_integer():
        raise ResearchPeriodicEquityValidationError(
            "research simulated duration must contain whole seconds"
        )
    duration = int(duration_seconds)
    if duration % policy.interval_seconds != 0:
        raise ResearchPeriodicEquityValidationError(
            "research simulated duration must be exactly divisible by equity interval"
        )
    interval_count = duration // policy.interval_seconds
    return tuple(
        run.simulated_start + timedelta(seconds=index * policy.interval_seconds)
        for index in range(interval_count + 1)
    )


def _derive_returns(
    observations: tuple[ResearchEquityValuationObservation, ...],
) -> tuple[ResearchPeriodicReturnPoint, ...]:
    points: list[ResearchPeriodicReturnPoint] = []
    for opening, closing in zip(observations, observations[1:]):
        with localcontext(_DECIMAL128):
            return_rate = closing.equity.amount / opening.equity.amount - Decimal(1)
        points.append(
            ResearchPeriodicReturnPoint(
                opened_at=opening.valued_at,
                closed_at=closing.valued_at,
                opening_observation_id=opening.observation_id,
                closing_observation_id=closing.observation_id,
                opening_equity=opening.equity,
                closing_equity=closing.equity,
                return_rate=return_rate,
            )
        )
    return tuple(points)


@dataclass(frozen=True, slots=True)
class ResearchPeriodicEquityReturnSeries:
    """Fixed-period simple returns from explicit equity valuation evidence.

    The first observation is a baseline and every later observation must explicitly
    confirm NO_EXTERNAL_FLOW since the prior point. This prevents deposits,
    withdrawals, or unknown flows from silently becoming investment returns.
    The series does not calculate valuation itself and does not claim Sharpe,
    Sortino, significance, stationarity, or production readiness.
    """

    binding: ResearchValuationModelBinding
    policy: ResearchPeriodicEquityPolicy
    observations: tuple[ResearchEquityValuationObservation, ...]
    returns: tuple[ResearchPeriodicReturnPoint, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.binding, ResearchValuationModelBinding):
            raise ResearchPeriodicEquityValidationError(
                "periodic series requires ResearchValuationModelBinding"
            )
        if not isinstance(self.policy, ResearchPeriodicEquityPolicy):
            raise ResearchPeriodicEquityValidationError(
                "periodic series requires ResearchPeriodicEquityPolicy"
            )
        ordered = _canonical_observations(self.observations)
        if self.observations != ordered:
            raise ResearchPeriodicEquityValidationError(
                "periodic equity observations must use canonical time order"
            )
        if self.binding != ordered[0].binding:
            raise ResearchPeriodicEquityValidationError(
                "periodic series binding must match source observations"
            )
        expected_times = _expected_timestamps(self.binding.run, self.policy)
        actual_times = tuple(item.valued_at for item in ordered)
        if actual_times != expected_times:
            raise ResearchPeriodicEquityValidationError(
                "periodic equity observations must cover the exact fixed schedule"
            )
        if ordered[0].flow_status_since_prior is not ResearchEquityFlowStatus.BASELINE:
            raise ResearchPeriodicEquityValidationError(
                "first periodic equity observation must declare BASELINE flow status"
            )
        if any(
            item.flow_status_since_prior is not ResearchEquityFlowStatus.NO_EXTERNAL_FLOW
            for item in ordered[1:]
        ):
            raise ResearchPeriodicEquityValidationError(
                "periodic returns require explicit NO_EXTERNAL_FLOW for every interval"
            )
        expected_returns = _derive_returns(ordered)
        if self.returns != expected_returns:
            raise ResearchPeriodicEquityValidationError(
                "periodic returns must equal values derived from equity observations"
            )

    @property
    def period_count(self) -> int:
        return len(self.returns)

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.binding.logical_values(),
            self.policy.logical_values(),
            tuple(item.logical_values() for item in self.observations),
            tuple(item.logical_values() for item in self.returns),
        )


def build_research_periodic_equity_return_series(
    *,
    binding: ResearchValuationModelBinding,
    policy: ResearchPeriodicEquityPolicy,
    observations: tuple[ResearchEquityValuationObservation, ...],
) -> Result[ResearchPeriodicEquityReturnSeries, ResearchPeriodicEquityError]:
    """Build fixed-period returns without inventing mark-to-market economics."""

    try:
        if not isinstance(binding, ResearchValuationModelBinding):
            raise ResearchPeriodicEquityValidationError(
                "binding must be ResearchValuationModelBinding"
            )
        if not isinstance(policy, ResearchPeriodicEquityPolicy):
            raise ResearchPeriodicEquityValidationError(
                "policy must be ResearchPeriodicEquityPolicy"
            )
        ordered = _canonical_observations(observations)
        returns = _derive_returns(ordered)
        return Success(
            ResearchPeriodicEquityReturnSeries(
                binding=binding,
                policy=policy,
                observations=ordered,
                returns=returns,
            )
        )
    except ResearchPeriodicEquityError as error:
        return Failure(error)
