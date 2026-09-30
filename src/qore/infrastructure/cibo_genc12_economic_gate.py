"""Preregistered non-compensatory economic gate for GEN-C12 crisis capital.

The gate compares crisis-capital treatments with one frozen control on the
same causal crisis population, provider surface, horizon and factor set.
Safety deterioration cannot be compensated by higher return. Passing only
means eligibility for further research.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)

GENC12_ECONOMIC_GATE_ID = (
    "CIBO_GENC12_NONCOMPENSATORY_CRISIS_ECONOMIC_GATE_V1"
)
GENC12_ECONOMIC_GATE_FROZEN_AT = datetime(
    2026, 9, 30, 18, 30, tzinfo=UTC
)
GENC12_ECONOMIC_GATE_SHA256 = (
    "sha256:75cfebe62297b84a709359f64d5093138808fa9732a395b8b97c327ab99921a9"
)


class Genc12EconomicRole(StrEnum):
    CONTROL = "CONTROL"
    TREATMENT = "TREATMENT"


class Genc12EconomicGateStatus(StrEnum):
    CONTROL = "CONTROL"
    ELIGIBLE_FOR_FURTHER_RESEARCH = "ELIGIBLE_FOR_FURTHER_RESEARCH"
    REJECTED_SAFETY_DETERIORATION = "REJECTED_SAFETY_DETERIORATION"
    REJECTED_NO_STRICT_ECONOMIC_IMPROVEMENT = (
        "REJECTED_NO_STRICT_ECONOMIC_IMPROVEMENT"
    )


@dataclass(frozen=True, slots=True)
class Genc12CrisisEconomicObservation:
    candidate_id: str
    role: Genc12EconomicRole
    population_sha256: str
    provider_surface_sha256: str
    crisis_factor_set_sha256: str
    horizon_start: datetime
    horizon_end: datetime
    net_delta_usd: Decimal
    maximum_drawdown_usd: Decimal
    peak_plausible_loss_usd: Decimal
    peak_margin_occupancy_usd: Decimal
    capital_lockup_minutes: Decimal
    compound_giveback_usd: Decimal
    simultaneous_loss_cluster_count: int
    provider_failure_incidence: Decimal
    minimum_realized_capital_usd: Decimal
    minimum_liquid_reserve_usd: Decimal
    future_outcome_used: bool = False
    risk_boundary_overridden: bool = False
    trader_methodology_changed: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if not self.candidate_id:
            raise CiboCapitalManagementError(
                "GEN-C12 economic candidate_id is required"
            )
        if type(self.role) is not Genc12EconomicRole:
            raise CiboCapitalManagementError(
                "GEN-C12 economic role is invalid"
            )
        for value, name in (
            (self.population_sha256, "population_sha256"),
            (self.provider_surface_sha256, "provider_surface_sha256"),
            (self.crisis_factor_set_sha256, "crisis_factor_set_sha256"),
        ):
            _sha(value, name)
        _aware(self.horizon_start, "horizon_start")
        _aware(self.horizon_end, "horizon_end")
        if self.horizon_end <= self.horizon_start:
            raise CiboCapitalManagementError(
                "GEN-C12 economic horizon must be positive"
            )
        nonnegative = (
            self.maximum_drawdown_usd,
            self.peak_plausible_loss_usd,
            self.peak_margin_occupancy_usd,
            self.capital_lockup_minutes,
            self.compound_giveback_usd,
            self.provider_failure_incidence,
            self.minimum_realized_capital_usd,
            self.minimum_liquid_reserve_usd,
        )
        if any(value < 0 for value in nonnegative):
            raise CiboCapitalManagementError(
                "GEN-C12 economic metrics must be non-negative"
            )
        if self.simultaneous_loss_cluster_count < 0:
            raise CiboCapitalManagementError(
                "GEN-C12 loss-cluster count must be non-negative"
            )
        if self.provider_failure_incidence > Decimal(1):
            raise CiboCapitalManagementError(
                "GEN-C12 provider-failure incidence must be <= 1"
            )
        if (
            self.future_outcome_used
            or self.risk_boundary_overridden
            or self.trader_methodology_changed
            or self.productive_authority
        ):
            raise CiboCapitalManagementError(
                "GEN-C12 economic observation governance drift"
            )


@dataclass(frozen=True, slots=True)
class Genc12EconomicGateRow:
    candidate_id: str
    status: Genc12EconomicGateStatus
    safety_no_worse: bool
    strict_economic_improvement: bool
    failed_dimensions: tuple[str, ...]
    weighted_score_used: bool = False
    production_promotion: bool = False


@dataclass(frozen=True, slots=True)
class Genc12EconomicGateReport:
    gate_id: str
    gate_sha256: str
    gate_frozen_at: datetime
    control_candidate_id: str
    rows: tuple[Genc12EconomicGateRow, ...]
    weighted_score_used: bool = False
    production_policy_selected: bool = False
    certification_ready: bool = False

    def __post_init__(self) -> None:
        if self.gate_id != GENC12_ECONOMIC_GATE_ID:
            raise CiboCapitalManagementError(
                "GEN-C12 economic gate identity drift"
            )
        if self.gate_sha256 != GENC12_ECONOMIC_GATE_SHA256:
            raise CiboCapitalManagementError(
                "GEN-C12 economic gate digest drift"
            )
        if self.gate_frozen_at != GENC12_ECONOMIC_GATE_FROZEN_AT:
            raise CiboCapitalManagementError(
                "GEN-C12 economic gate freeze drift"
            )
        candidate_ids = tuple(row.candidate_id for row in self.rows)
        if len(candidate_ids) != len(set(candidate_ids)):
            raise CiboCapitalManagementError(
                "GEN-C12 economic rows must be unique"
            )
        if self.control_candidate_id not in candidate_ids:
            raise CiboCapitalManagementError(
                "GEN-C12 economic control row is missing"
            )
        if (
            self.weighted_score_used
            or self.production_policy_selected
            or self.certification_ready
        ):
            raise CiboCapitalManagementError(
                "GEN-C12 economic gate cannot score/promote/certify"
            )


def evaluate_genc12_economic_gate(
    observations: tuple[Genc12CrisisEconomicObservation, ...],
) -> Genc12EconomicGateReport:
    """Apply the frozen non-compensatory crisis economic gate."""

    if not observations:
        raise CiboCapitalManagementError(
            "GEN-C12 economic observations are required"
        )
    controls = tuple(
        item for item in observations if item.role is Genc12EconomicRole.CONTROL
    )
    if len(controls) != 1:
        raise CiboCapitalManagementError(
            "GEN-C12 economic gate requires exactly one control"
        )
    control = controls[0]
    rows = tuple(_evaluate(control, item) for item in observations)
    return Genc12EconomicGateReport(
        gate_id=GENC12_ECONOMIC_GATE_ID,
        gate_sha256=GENC12_ECONOMIC_GATE_SHA256,
        gate_frozen_at=GENC12_ECONOMIC_GATE_FROZEN_AT,
        control_candidate_id=control.candidate_id,
        rows=rows,
    )


def _evaluate(
    control: Genc12CrisisEconomicObservation,
    candidate: Genc12CrisisEconomicObservation,
) -> Genc12EconomicGateRow:
    if candidate.candidate_id == control.candidate_id:
        return Genc12EconomicGateRow(
            candidate_id=candidate.candidate_id,
            status=Genc12EconomicGateStatus.CONTROL,
            safety_no_worse=True,
            strict_economic_improvement=False,
            failed_dimensions=(),
        )
    _require_comparable(control, candidate)

    failed: list[str] = []
    for name, candidate_value, control_value in (
        (
            "maximum_drawdown_usd",
            candidate.maximum_drawdown_usd,
            control.maximum_drawdown_usd,
        ),
        (
            "peak_plausible_loss_usd",
            candidate.peak_plausible_loss_usd,
            control.peak_plausible_loss_usd,
        ),
        (
            "peak_margin_occupancy_usd",
            candidate.peak_margin_occupancy_usd,
            control.peak_margin_occupancy_usd,
        ),
        (
            "capital_lockup_minutes",
            candidate.capital_lockup_minutes,
            control.capital_lockup_minutes,
        ),
        (
            "compound_giveback_usd",
            candidate.compound_giveback_usd,
            control.compound_giveback_usd,
        ),
        (
            "simultaneous_loss_cluster_count",
            candidate.simultaneous_loss_cluster_count,
            control.simultaneous_loss_cluster_count,
        ),
        (
            "provider_failure_incidence",
            candidate.provider_failure_incidence,
            control.provider_failure_incidence,
        ),
    ):
        if candidate_value > control_value:
            failed.append(name)
    for name, candidate_value, control_value in (
        (
            "minimum_realized_capital_usd",
            candidate.minimum_realized_capital_usd,
            control.minimum_realized_capital_usd,
        ),
        (
            "minimum_liquid_reserve_usd",
            candidate.minimum_liquid_reserve_usd,
            control.minimum_liquid_reserve_usd,
        ),
    ):
        if candidate_value < control_value:
            failed.append(name)

    strict = any(
        (
            candidate.net_delta_usd > control.net_delta_usd,
            candidate.minimum_realized_capital_usd
            > control.minimum_realized_capital_usd,
            candidate.minimum_liquid_reserve_usd
            > control.minimum_liquid_reserve_usd,
            candidate.capital_lockup_minutes
            < control.capital_lockup_minutes,
            candidate.compound_giveback_usd
            < control.compound_giveback_usd,
        )
    )
    if failed:
        status = Genc12EconomicGateStatus.REJECTED_SAFETY_DETERIORATION
    elif not strict:
        status = (
            Genc12EconomicGateStatus.REJECTED_NO_STRICT_ECONOMIC_IMPROVEMENT
        )
    else:
        status = Genc12EconomicGateStatus.ELIGIBLE_FOR_FURTHER_RESEARCH
    return Genc12EconomicGateRow(
        candidate_id=candidate.candidate_id,
        status=status,
        safety_no_worse=not failed,
        strict_economic_improvement=strict,
        failed_dimensions=tuple(failed),
    )


def _require_comparable(
    control: Genc12CrisisEconomicObservation,
    candidate: Genc12CrisisEconomicObservation,
) -> None:
    if (
        candidate.population_sha256 != control.population_sha256
        or candidate.provider_surface_sha256 != control.provider_surface_sha256
        or candidate.crisis_factor_set_sha256
        != control.crisis_factor_set_sha256
        or candidate.horizon_start != control.horizon_start
        or candidate.horizon_end != control.horizon_end
    ):
        raise CiboCapitalManagementError(
            "GEN-C12 economic gate requires identical causal comparison surface"
        )


def _aware(value: datetime, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise CiboCapitalManagementError(
            f"GEN-C12 economic {name} must be timezone-aware"
        )


def _sha(value: str, name: str) -> None:
    if (
        not value.startswith("sha256:")
        or len(value) != 71
        or any(char not in "0123456789abcdef" for char in value[7:])
    ):
        raise CiboCapitalManagementError(
            f"GEN-C12 economic {name} must be canonical SHA-256"
        )
