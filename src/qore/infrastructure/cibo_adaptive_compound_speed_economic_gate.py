"""Preregistered non-compensatory economic gate for GEN-C8.

The gate evaluates adaptive compound-speed treatments only after their causal
population is frozen. Return cannot compensate for worse tail, recovery,
provider-cost, reserve, optionality or unnecessary-acceleration behavior.
Passing is research eligibility only.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.cibo_adaptive_compound_speed_shadow import (
    genc8_policy_sha256,
)
from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError

GENC8_ECONOMIC_GATE_ID = "CIBO_GENC8_NONCOMPENSATORY_ECONOMIC_GATE_V1"
GENC8_ECONOMIC_GATE_FROZEN_AT = datetime(
    2026, 9, 30, 18, 45, tzinfo=UTC
)
GENC8_ECONOMIC_GATE_SHA256 = (
    "sha256:57e2434ccf3b7a8aa34fe414366a419bd9924e50c5546cf658cffb6d130bd3a3"
)


class Genc8EconomicRole(StrEnum):
    CONTROL = "CONTROL"
    TREATMENT = "TREATMENT"


class Genc8EconomicGateStatus(StrEnum):
    CONTROL = "CONTROL"
    ELIGIBLE_FOR_FURTHER_RESEARCH = "ELIGIBLE_FOR_FURTHER_RESEARCH"
    REJECTED_SAFETY_DETERIORATION = "REJECTED_SAFETY_DETERIORATION"
    REJECTED_NO_STRICT_ECONOMIC_IMPROVEMENT = (
        "REJECTED_NO_STRICT_ECONOMIC_IMPROVEMENT"
    )


@dataclass(frozen=True, slots=True)
class Genc8EconomicObservation:
    candidate_id: str
    role: Genc8EconomicRole
    policy_sha256: str
    population_sha256: str
    provider_surface_sha256: str
    fold_ids: tuple[str, ...]
    horizon_start: datetime
    horizon_end: datetime
    ending_realized_capital_usd: Decimal
    geometric_growth_factor: Decimal
    maximum_drawdown_usd: Decimal
    p95_drawdown_usd: Decimal
    p99_drawdown_usd: Decimal
    maximum_time_underwater_minutes: Decimal
    p95_recovery_minutes: Decimal
    capital_risk_time_productivity: Decimal
    profit_retention_usd: Decimal
    minimum_liquid_reserve_usd: Decimal
    minimum_optionality_usd: Decimal
    provider_cost_usd: Decimal
    positive_tail_capture_usd: Decimal
    unnecessary_acceleration_count: int
    over_defensive_missed_opportunity_count: int
    causal_population_locked: bool = True
    hindsight_retuned: bool = False
    weighted_score_used: bool = False
    productive_authority: bool = False
    certification_ready: bool = False

    def __post_init__(self) -> None:
        if not self.candidate_id:
            raise CiboCompoundCapitalError(
                "GEN-C8 economic candidate_id is required"
            )
        if type(self.role) is not Genc8EconomicRole:
            raise CiboCompoundCapitalError(
                "GEN-C8 economic role is invalid"
            )
        if self.policy_sha256 != genc8_policy_sha256():
            raise CiboCompoundCapitalError(
                "GEN-C8 economic policy digest drift"
            )
        _sha(self.population_sha256, "population_sha256")
        _sha(self.provider_surface_sha256, "provider_surface_sha256")
        if not self.fold_ids or len(self.fold_ids) != len(set(self.fold_ids)):
            raise CiboCompoundCapitalError(
                "GEN-C8 economic fold ids must be non-empty and unique"
            )
        _aware(self.horizon_start, "horizon_start")
        _aware(self.horizon_end, "horizon_end")
        if self.horizon_end <= self.horizon_start:
            raise CiboCompoundCapitalError(
                "GEN-C8 economic horizon must be positive"
            )
        nonnegative = (
            self.ending_realized_capital_usd,
            self.geometric_growth_factor,
            self.maximum_drawdown_usd,
            self.p95_drawdown_usd,
            self.p99_drawdown_usd,
            self.maximum_time_underwater_minutes,
            self.p95_recovery_minutes,
            self.profit_retention_usd,
            self.minimum_liquid_reserve_usd,
            self.minimum_optionality_usd,
            self.provider_cost_usd,
            self.positive_tail_capture_usd,
        )
        if any(value < 0 for value in nonnegative):
            raise CiboCompoundCapitalError(
                "GEN-C8 economic non-negative metric violated"
            )
        for name in (
            "unnecessary_acceleration_count",
            "over_defensive_missed_opportunity_count",
        ):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise CiboCompoundCapitalError(
                    f"GEN-C8 economic {name} must be non-negative int"
                )
        if (
            not self.causal_population_locked
            or self.hindsight_retuned
            or self.weighted_score_used
            or self.productive_authority
            or self.certification_ready
        ):
            raise CiboCompoundCapitalError(
                "GEN-C8 economic observation governance drift"
            )


@dataclass(frozen=True, slots=True)
class Genc8EconomicGateRow:
    candidate_id: str
    status: Genc8EconomicGateStatus
    safety_no_worse: bool
    strict_economic_improvement: bool
    failed_dimensions: tuple[str, ...]
    weighted_score_used: bool = False
    production_promotion: bool = False

    def __post_init__(self) -> None:
        if not self.candidate_id or type(self.status) is not Genc8EconomicGateStatus:
            raise CiboCompoundCapitalError("Genc8EconomicGateRow identity/status drift")
        for name in (
            "safety_no_worse",
            "strict_economic_improvement",
            "weighted_score_used",
            "production_promotion",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCompoundCapitalError(f"Genc8EconomicGateRow {name} must be bool")
        if (
            not isinstance(self.failed_dimensions, tuple)
            or any(not isinstance(item, str) or not item for item in self.failed_dimensions)
            or len(self.failed_dimensions) != len(set(self.failed_dimensions))
        ):
            raise CiboCompoundCapitalError("Genc8EconomicGateRow failed dimensions are invalid")
        if self.weighted_score_used or self.production_promotion:
            raise CiboCompoundCapitalError("Genc8EconomicGateRow cannot score/promote production")
        if self.status is Genc8EconomicGateStatus.CONTROL:
            if (
                not self.safety_no_worse
                or self.strict_economic_improvement
                or self.failed_dimensions
            ):
                raise CiboCompoundCapitalError("Genc8EconomicGateRow CONTROL row drift")
            return
        expected_status = (
            Genc8EconomicGateStatus.REJECTED_SAFETY_DETERIORATION
            if not self.safety_no_worse
            else (
                Genc8EconomicGateStatus.REJECTED_NO_STRICT_ECONOMIC_IMPROVEMENT
                if not self.strict_economic_improvement
                else Genc8EconomicGateStatus.ELIGIBLE_FOR_FURTHER_RESEARCH
            )
        )
        if self.status is not expected_status:
            raise CiboCompoundCapitalError("Genc8EconomicGateRow status/metric drift")
        if self.safety_no_worse != (not self.failed_dimensions):
            raise CiboCompoundCapitalError("Genc8EconomicGateRow safety/dimension drift")


@dataclass(frozen=True, slots=True)
class Genc8EconomicGateReport:
    gate_id: str
    gate_sha256: str
    gate_frozen_at: datetime
    control_candidate_id: str
    rows: tuple[Genc8EconomicGateRow, ...]
    winner_candidate_id: None = None
    weighted_score_used: bool = False
    production_policy_selected: bool = False
    certification_ready: bool = False

    def __post_init__(self) -> None:
        if self.gate_id != GENC8_ECONOMIC_GATE_ID:
            raise CiboCompoundCapitalError(
                "GEN-C8 economic gate identity drift"
            )
        if self.gate_sha256 != GENC8_ECONOMIC_GATE_SHA256:
            raise CiboCompoundCapitalError(
                "GEN-C8 economic gate digest drift"
            )
        if self.gate_frozen_at != GENC8_ECONOMIC_GATE_FROZEN_AT:
            raise CiboCompoundCapitalError(
                "GEN-C8 economic gate freeze drift"
            )
        candidate_ids = tuple(row.candidate_id for row in self.rows)
        if len(candidate_ids) != len(set(candidate_ids)):
            raise CiboCompoundCapitalError(
                "GEN-C8 economic gate rows must be unique"
            )
        if self.control_candidate_id not in candidate_ids:
            raise CiboCompoundCapitalError(
                "GEN-C8 economic control row is missing"
            )
        controls = tuple(
            row for row in self.rows if row.status is Genc8EconomicGateStatus.CONTROL
        )
        if (
            len(controls) != 1
            or controls[0].candidate_id != self.control_candidate_id
        ):
            raise CiboCompoundCapitalError("GEN-C8 economic gate control row drift")
        if (
            self.winner_candidate_id is not None
            or self.weighted_score_used
            or self.production_policy_selected
            or self.certification_ready
        ):
            raise CiboCompoundCapitalError(
                "GEN-C8 economic gate cannot score/promote/certify"
            )


def evaluate_genc8_economic_gate(
    observations: tuple[Genc8EconomicObservation, ...],
) -> Genc8EconomicGateReport:
    """Apply the frozen GEN-C8 non-compensatory gate."""

    if not observations:
        raise CiboCompoundCapitalError(
            "GEN-C8 economic observations are required"
        )
    controls = tuple(
        item for item in observations if item.role is Genc8EconomicRole.CONTROL
    )
    if len(controls) != 1:
        raise CiboCompoundCapitalError(
            "GEN-C8 economic gate requires exactly one control"
        )
    control = controls[0]
    rows = tuple(_evaluate(control, item) for item in observations)
    return Genc8EconomicGateReport(
        gate_id=GENC8_ECONOMIC_GATE_ID,
        gate_sha256=GENC8_ECONOMIC_GATE_SHA256,
        gate_frozen_at=GENC8_ECONOMIC_GATE_FROZEN_AT,
        control_candidate_id=control.candidate_id,
        rows=rows,
    )


def _evaluate(
    control: Genc8EconomicObservation,
    candidate: Genc8EconomicObservation,
) -> Genc8EconomicGateRow:
    if candidate.candidate_id == control.candidate_id:
        return Genc8EconomicGateRow(
            candidate_id=candidate.candidate_id,
            status=Genc8EconomicGateStatus.CONTROL,
            safety_no_worse=True,
            strict_economic_improvement=False,
            failed_dimensions=(),
        )
    _require_comparable(control, candidate)

    failed: list[str] = []
    for name, candidate_value, control_value in (
        ("maximum_drawdown_usd", candidate.maximum_drawdown_usd, control.maximum_drawdown_usd),
        ("p95_drawdown_usd", candidate.p95_drawdown_usd, control.p95_drawdown_usd),
        ("p99_drawdown_usd", candidate.p99_drawdown_usd, control.p99_drawdown_usd),
        (
            "maximum_time_underwater_minutes",
            candidate.maximum_time_underwater_minutes,
            control.maximum_time_underwater_minutes,
        ),
        ("p95_recovery_minutes", candidate.p95_recovery_minutes, control.p95_recovery_minutes),
        ("provider_cost_usd", candidate.provider_cost_usd, control.provider_cost_usd),
        (
            "unnecessary_acceleration_count",
            candidate.unnecessary_acceleration_count,
            control.unnecessary_acceleration_count,
        ),
    ):
        if candidate_value > control_value:
            failed.append(name)
    for name, candidate_value, control_value in (
        (
            "profit_retention_usd",
            candidate.profit_retention_usd,
            control.profit_retention_usd,
        ),
        (
            "minimum_liquid_reserve_usd",
            candidate.minimum_liquid_reserve_usd,
            control.minimum_liquid_reserve_usd,
        ),
        (
            "minimum_optionality_usd",
            candidate.minimum_optionality_usd,
            control.minimum_optionality_usd,
        ),
    ):
        if candidate_value < control_value:
            failed.append(name)

    strict = any(
        (
            candidate.ending_realized_capital_usd
            > control.ending_realized_capital_usd,
            candidate.geometric_growth_factor
            > control.geometric_growth_factor,
            candidate.capital_risk_time_productivity
            > control.capital_risk_time_productivity,
            candidate.profit_retention_usd > control.profit_retention_usd,
            candidate.positive_tail_capture_usd
            > control.positive_tail_capture_usd,
            candidate.over_defensive_missed_opportunity_count
            < control.over_defensive_missed_opportunity_count,
        )
    )

    if failed:
        status = Genc8EconomicGateStatus.REJECTED_SAFETY_DETERIORATION
    elif not strict:
        status = (
            Genc8EconomicGateStatus.REJECTED_NO_STRICT_ECONOMIC_IMPROVEMENT
        )
    else:
        status = Genc8EconomicGateStatus.ELIGIBLE_FOR_FURTHER_RESEARCH

    return Genc8EconomicGateRow(
        candidate_id=candidate.candidate_id,
        status=status,
        safety_no_worse=not failed,
        strict_economic_improvement=strict,
        failed_dimensions=tuple(failed),
    )


def _require_comparable(
    control: Genc8EconomicObservation,
    candidate: Genc8EconomicObservation,
) -> None:
    if (
        candidate.policy_sha256 != control.policy_sha256
        or candidate.population_sha256 != control.population_sha256
        or candidate.provider_surface_sha256 != control.provider_surface_sha256
        or candidate.fold_ids != control.fold_ids
        or candidate.horizon_start != control.horizon_start
        or candidate.horizon_end != control.horizon_end
    ):
        raise CiboCompoundCapitalError(
            "GEN-C8 economic gate requires identical causal comparison surface"
        )


def _aware(value: datetime, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise CiboCompoundCapitalError(
            f"GEN-C8 economic {name} must be timezone-aware"
        )


def _sha(value: str, name: str) -> None:
    if (
        not value.startswith("sha256:")
        or len(value) != 71
        or any(char not in "0123456789abcdef" for char in value[7:])
    ):
        raise CiboCompoundCapitalError(
            f"GEN-C8 economic {name} must be canonical SHA-256"
        )
