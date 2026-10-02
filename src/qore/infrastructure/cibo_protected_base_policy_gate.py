"""Preregistered Protected Base numeric-policy and economic gate.

This module freezes numeric candidates before outcome use and evaluates them
against one control on an identical causal/provider surface. Safety and capital
preservation are non-compensatory: higher growth cannot rescue deterioration.
Passing means research eligibility only.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_protected_base_overlay import ProtectedBaseClass

PROTECTED_BASE_GATE_ID = "CIBO_PROTECTED_BASE_NONCOMPENSATORY_POLICY_GATE_V1"
PROTECTED_BASE_GATE_FROZEN_AT = datetime(2026, 9, 30, 19, 10, tzinfo=UTC)
PROTECTED_BASE_GATE_SHA256 = (
    "sha256:05fa878b3e6f824851d559550fe7137bf457dd589eb46192547b51d0eb91ebc0"
)


class ProtectedBaseCandidateRole(StrEnum):
    CONTROL = "CONTROL"
    TREATMENT = "TREATMENT"


class ProtectedBaseGateStatus(StrEnum):
    CONTROL = "CONTROL"
    ELIGIBLE_FOR_FURTHER_RESEARCH = "ELIGIBLE_FOR_FURTHER_RESEARCH"
    REJECTED_SAFETY_DETERIORATION = "REJECTED_SAFETY_DETERIORATION"
    REJECTED_NO_STRICT_IMPROVEMENT = "REJECTED_NO_STRICT_IMPROVEMENT"


@dataclass(frozen=True, slots=True)
class ProtectedBasePolicyCandidate:
    candidate_id: str
    role: ProtectedBaseCandidateRole
    policy_id: str
    policy_sha256: str
    frozen_at: datetime
    protected_base_usd: Decimal
    protection_class: ProtectedBaseClass
    broker_guarantee_evidence_sha256: str | None = None
    numeric_candidate_frozen: bool = True
    v3_mutated: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if not self.candidate_id or not self.policy_id:
            raise CiboCapitalManagementError(
                "protected-base candidate identity is required"
            )
        if type(self.role) is not ProtectedBaseCandidateRole:
            raise CiboCapitalManagementError(
                "protected-base candidate role is invalid"
            )
        _sha(self.policy_sha256, "policy_sha256")
        _aware(self.frozen_at, "frozen_at")
        if (
            not isinstance(self.protected_base_usd, Decimal)
            or not self.protected_base_usd.is_finite()
            or self.protected_base_usd < 0
        ):
            raise CiboCapitalManagementError(
                "protected-base amount must be finite non-negative Decimal"
            )
        if type(self.protection_class) is not ProtectedBaseClass:
            raise CiboCapitalManagementError(
                "protected-base protection class is invalid"
            )
        if self.role is ProtectedBaseCandidateRole.CONTROL:
            if self.protected_base_usd != 0:
                raise CiboCapitalManagementError(
                    "protected-base control must protect zero incremental base"
                )
        elif self.protected_base_usd <= 0:
            raise CiboCapitalManagementError(
                "protected-base treatment requires positive numeric candidate"
            )
        if self.protection_class is ProtectedBaseClass.BROKER_GUARANTEED:
            if self.broker_guarantee_evidence_sha256 is None:
                raise CiboCapitalManagementError(
                    "broker-guaranteed protected base requires provider evidence"
                )
            _sha(
                self.broker_guarantee_evidence_sha256,
                "broker_guarantee_evidence_sha256",
            )
        elif self.broker_guarantee_evidence_sha256 is not None:
            raise CiboCapitalManagementError(
                "non-broker protected base cannot claim broker guarantee evidence"
            )
        for name in (
            "numeric_candidate_frozen",
            "v3_mutated",
            "productive_authority",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(
                    f"protected-base candidate {name} must be bool"
                )
        if (
            not self.numeric_candidate_frozen
            or self.v3_mutated
            or self.productive_authority
        ):
            raise CiboCapitalManagementError(
                "protected-base candidate governance drift"
            )


@dataclass(frozen=True, slots=True)
class ProtectedBaseEconomicObservation:
    candidate: ProtectedBasePolicyCandidate
    population_sha256: str
    provider_surface_sha256: str
    fold_ids: tuple[str, ...]
    horizon_start: datetime
    horizon_end: datetime
    ending_realized_capital_usd: Decimal
    minimum_original_base_usd: Decimal
    maximum_drawdown_usd: Decimal
    p99_drawdown_usd: Decimal
    peak_plausible_loss_usd: Decimal
    peak_margin_occupancy_usd: Decimal
    p95_recovery_minutes: Decimal
    minimum_optionality_usd: Decimal
    provider_failure_incidence: Decimal
    capital_risk_time_productivity: Decimal
    hindsight_retuned: bool = False
    weighted_score_used: bool = False
    certification_ready: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.candidate, ProtectedBasePolicyCandidate):
            raise CiboCapitalManagementError(
                "protected-base observation requires canonical candidate"
            )
        _sha(self.population_sha256, "population_sha256")
        _sha(self.provider_surface_sha256, "provider_surface_sha256")
        if (
            not isinstance(self.fold_ids, tuple)
            or not self.fold_ids
            or any(
                not isinstance(item, str) or not item
                for item in self.fold_ids
            )
            or len(self.fold_ids) != len(set(self.fold_ids))
        ):
            raise CiboCapitalManagementError(
                "protected-base fold ids must be non-empty unique strings"
            )
        _aware(self.horizon_start, "horizon_start")
        _aware(self.horizon_end, "horizon_end")
        if self.horizon_end <= self.horizon_start:
            raise CiboCapitalManagementError(
                "protected-base horizon must be positive"
            )
        if self.candidate.frozen_at > self.horizon_start:
            raise CiboCapitalManagementError(
                "protected-base numeric candidate must freeze before evaluation"
            )
        for name in (
            "ending_realized_capital_usd",
            "minimum_original_base_usd",
            "maximum_drawdown_usd",
            "p99_drawdown_usd",
            "peak_plausible_loss_usd",
            "peak_margin_occupancy_usd",
            "p95_recovery_minutes",
            "minimum_optionality_usd",
            "provider_failure_incidence",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value < 0
            ):
                raise CiboCapitalManagementError(
                    f"protected-base {name} must be finite non-negative Decimal"
                )
        if (
            not isinstance(self.capital_risk_time_productivity, Decimal)
            or not self.capital_risk_time_productivity.is_finite()
        ):
            raise CiboCapitalManagementError(
                "protected-base capital_risk_time_productivity must be finite Decimal"
            )
        if self.p99_drawdown_usd > self.maximum_drawdown_usd:
            raise CiboCapitalManagementError(
                "protected-base p99 drawdown cannot exceed maximum drawdown"
            )
        if self.provider_failure_incidence > Decimal(1):
            raise CiboCapitalManagementError(
                "protected-base provider failure incidence must be <= 1"
            )
        for name in (
            "hindsight_retuned",
            "weighted_score_used",
            "certification_ready",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(
                    f"protected-base observation {name} must be bool"
                )
        if (
            self.hindsight_retuned
            or self.weighted_score_used
            or self.certification_ready
        ):
            raise CiboCapitalManagementError(
                "protected-base observation governance drift"
            )


@dataclass(frozen=True, slots=True)
class ProtectedBaseGateRow:
    candidate_id: str
    status: ProtectedBaseGateStatus
    safety_no_worse: bool
    strict_improvement: bool
    failed_dimensions: tuple[str, ...]
    production_promotion: bool = False

    def __post_init__(self) -> None:
        if not self.candidate_id or type(self.status) is not ProtectedBaseGateStatus:
            raise CiboCapitalManagementError(
                "protected-base gate row identity/status drift"
            )
        for name in (
            "safety_no_worse",
            "strict_improvement",
            "production_promotion",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(
                    f"protected-base gate row {name} must be bool"
                )
        if (
            not isinstance(self.failed_dimensions, tuple)
            or any(
                not isinstance(item, str) or not item
                for item in self.failed_dimensions
            )
            or len(self.failed_dimensions) != len(set(self.failed_dimensions))
        ):
            raise CiboCapitalManagementError(
                "protected-base gate row failed dimensions are invalid"
            )
        if self.production_promotion:
            raise CiboCapitalManagementError(
                "protected-base gate row cannot promote production"
            )
        if self.status is ProtectedBaseGateStatus.CONTROL:
            if (
                not self.safety_no_worse
                or self.strict_improvement
                or self.failed_dimensions
            ):
                raise CiboCapitalManagementError(
                    "protected-base CONTROL row drift"
                )
            return
        expected_status = (
            ProtectedBaseGateStatus.REJECTED_SAFETY_DETERIORATION
            if not self.safety_no_worse
            else (
                ProtectedBaseGateStatus.REJECTED_NO_STRICT_IMPROVEMENT
                if not self.strict_improvement
                else ProtectedBaseGateStatus.ELIGIBLE_FOR_FURTHER_RESEARCH
            )
        )
        if self.status is not expected_status:
            raise CiboCapitalManagementError(
                "protected-base gate row status/metric drift"
            )
        if self.safety_no_worse != (not self.failed_dimensions):
            raise CiboCapitalManagementError(
                "protected-base gate row safety/dimension drift"
            )


@dataclass(frozen=True, slots=True)
class ProtectedBaseGateReport:
    gate_id: str
    gate_sha256: str
    gate_frozen_at: datetime
    control_candidate_id: str
    rows: tuple[ProtectedBaseGateRow, ...]
    winner_candidate_id: None = None
    weighted_score_used: bool = False
    production_policy_selected: bool = False
    certification_ready: bool = False

    def __post_init__(self) -> None:
        if self.gate_id != PROTECTED_BASE_GATE_ID:
            raise CiboCapitalManagementError(
                "protected-base gate identity drift"
            )
        if self.gate_sha256 != PROTECTED_BASE_GATE_SHA256:
            raise CiboCapitalManagementError(
                "protected-base gate digest drift"
            )
        if self.gate_frozen_at != PROTECTED_BASE_GATE_FROZEN_AT:
            raise CiboCapitalManagementError(
                "protected-base gate freeze drift"
            )
        if not isinstance(self.rows, tuple) or not self.rows or any(
            not isinstance(row, ProtectedBaseGateRow) for row in self.rows
        ):
            raise CiboCapitalManagementError(
                "protected-base gate requires canonical rows"
            )
        ids = tuple(row.candidate_id for row in self.rows)
        if len(ids) != len(set(ids)) or self.control_candidate_id not in ids:
            raise CiboCapitalManagementError(
                "protected-base gate rows/control are invalid"
            )
        controls = tuple(
            row for row in self.rows
            if row.status is ProtectedBaseGateStatus.CONTROL
        )
        if (
            len(controls) != 1
            or controls[0].candidate_id != self.control_candidate_id
        ):
            raise CiboCapitalManagementError(
                "protected-base gate control row drift"
            )
        if (
            self.winner_candidate_id is not None
            or self.weighted_score_used
            or self.production_policy_selected
            or self.certification_ready
        ):
            raise CiboCapitalManagementError(
                "protected-base gate cannot score/promote/certify"
            )


def evaluate_protected_base_gate(
    observations: tuple[ProtectedBaseEconomicObservation, ...],
) -> ProtectedBaseGateReport:
    if not observations:
        raise CiboCapitalManagementError(
            "protected-base observations are required"
        )
    controls = tuple(
        item
        for item in observations
        if item.candidate.role is ProtectedBaseCandidateRole.CONTROL
    )
    if len(controls) != 1:
        raise CiboCapitalManagementError(
            "protected-base gate requires exactly one control"
        )
    control = controls[0]
    rows = tuple(_evaluate(control, item) for item in observations)
    return ProtectedBaseGateReport(
        gate_id=PROTECTED_BASE_GATE_ID,
        gate_sha256=PROTECTED_BASE_GATE_SHA256,
        gate_frozen_at=PROTECTED_BASE_GATE_FROZEN_AT,
        control_candidate_id=control.candidate.candidate_id,
        rows=rows,
    )


def _evaluate(
    control: ProtectedBaseEconomicObservation,
    candidate: ProtectedBaseEconomicObservation,
) -> ProtectedBaseGateRow:
    if candidate.candidate.candidate_id == control.candidate.candidate_id:
        return ProtectedBaseGateRow(
            candidate_id=candidate.candidate.candidate_id,
            status=ProtectedBaseGateStatus.CONTROL,
            safety_no_worse=True,
            strict_improvement=False,
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
            "p99_drawdown_usd",
            candidate.p99_drawdown_usd,
            control.p99_drawdown_usd,
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
            "p95_recovery_minutes",
            candidate.p95_recovery_minutes,
            control.p95_recovery_minutes,
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
            "ending_realized_capital_usd",
            candidate.ending_realized_capital_usd,
            control.ending_realized_capital_usd,
        ),
        (
            "minimum_original_base_usd",
            candidate.minimum_original_base_usd,
            control.minimum_original_base_usd,
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
            candidate.minimum_original_base_usd > control.minimum_original_base_usd,
            candidate.maximum_drawdown_usd < control.maximum_drawdown_usd,
            candidate.p99_drawdown_usd < control.p99_drawdown_usd,
            candidate.peak_plausible_loss_usd < control.peak_plausible_loss_usd,
            candidate.p95_recovery_minutes < control.p95_recovery_minutes,
            candidate.minimum_optionality_usd > control.minimum_optionality_usd,
            candidate.capital_risk_time_productivity
            > control.capital_risk_time_productivity,
        )
    )
    if failed:
        status = ProtectedBaseGateStatus.REJECTED_SAFETY_DETERIORATION
    elif not strict:
        status = ProtectedBaseGateStatus.REJECTED_NO_STRICT_IMPROVEMENT
    else:
        status = ProtectedBaseGateStatus.ELIGIBLE_FOR_FURTHER_RESEARCH

    return ProtectedBaseGateRow(
        candidate_id=candidate.candidate.candidate_id,
        status=status,
        safety_no_worse=not failed,
        strict_improvement=strict,
        failed_dimensions=tuple(failed),
    )


def _require_comparable(
    control: ProtectedBaseEconomicObservation,
    candidate: ProtectedBaseEconomicObservation,
) -> None:
    if (
        candidate.population_sha256 != control.population_sha256
        or candidate.provider_surface_sha256 != control.provider_surface_sha256
        or candidate.fold_ids != control.fold_ids
        or candidate.horizon_start != control.horizon_start
        or candidate.horizon_end != control.horizon_end
    ):
        raise CiboCapitalManagementError(
            "protected-base gate requires identical causal comparison surface"
        )


def _aware(value: datetime, name: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise CiboCapitalManagementError(
            f"protected-base {name} must be timezone-aware"
        )


def _sha(value: str, name: str) -> None:
    if (
        not isinstance(value, str)
        or not value.startswith("sha256:")
        or len(value) != 71
        or any(char not in "0123456789abcdef" for char in value[7:])
    ):
        raise CiboCapitalManagementError(
            f"protected-base {name} must be canonical SHA-256"
        )
