"""Per-engine efficiency sensors for CIBO Maximum Capability.

Research-only observability.  The sensor measures whether a native engine is
being invoked, whether its outputs alter downstream decisions, whether those
changes have measurable causal economic value, and whether the engine is
blocked, redundant, near-zero, or destructive.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)


class CiboEngineEfficiencyClass(StrEnum):
    VALUE_ADD = "VALUE_ADD"
    LOW_ACTUATION = "LOW_ACTUATION"
    NEAR_ZERO = "NEAR_ZERO"
    DESTRUCTIVE = "DESTRUCTIVE"
    BLOCKED = "BLOCKED"
    UNIDENTIFIED = "UNIDENTIFIED"


@dataclass(frozen=True, slots=True)
class CiboEngineEfficiencyEvidence:
    engine_id: str
    eligible_count: int
    invoked_count: int
    output_consumed_count: int
    decision_changed_count: int
    economically_effective_count: int
    blocked_count: int
    marginal_value_usd: Decimal
    opportunity_value_available_usd: Decimal
    latency_minutes_total: Decimal = Decimal(0)
    latency_observations: int = 0
    destructive_value_usd: Decimal = Decimal(0)
    unidentified_value_usd: Decimal = Decimal(0)
    value_identified: bool = True

    def __post_init__(self) -> None:
        if not self.engine_id:
            raise CiboCapitalManagementError("engine efficiency identity required")
        for name in (
            "eligible_count",
            "invoked_count",
            "output_consumed_count",
            "decision_changed_count",
            "economically_effective_count",
            "blocked_count",
            "latency_observations",
        ):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise CiboCapitalManagementError(
                    f"engine efficiency {name} must be non-negative int"
                )
        for name in (
            "marginal_value_usd",
            "opportunity_value_available_usd",
            "latency_minutes_total",
            "destructive_value_usd",
            "unidentified_value_usd",
        ):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
                raise CiboCapitalManagementError(
                    f"engine efficiency {name} must be finite non-negative Decimal"
                )
        if type(self.value_identified) is not bool:
            raise CiboCapitalManagementError(
                "engine efficiency value_identified must be bool"
            )
        if self.invoked_count > self.eligible_count:
            raise CiboCapitalManagementError(
                "engine invoked_count cannot exceed eligible_count"
            )
        if self.output_consumed_count > self.invoked_count:
            raise CiboCapitalManagementError(
                "engine consumed_count cannot exceed invoked_count"
            )
        if self.decision_changed_count > self.output_consumed_count:
            raise CiboCapitalManagementError(
                "engine changed_count cannot exceed consumed_count"
            )
        if self.economically_effective_count > self.decision_changed_count:
            raise CiboCapitalManagementError(
                "engine effective_count cannot exceed changed_count"
            )


@dataclass(frozen=True, slots=True)
class CiboEngineEfficiencyReport:
    engine_id: str
    availability_efficiency: Decimal
    consumption_efficiency: Decimal
    actuation_efficiency: Decimal
    economic_effect_efficiency: Decimal
    value_capture_efficiency: Decimal
    latency_efficiency: Decimal
    engine_efficiency: Decimal
    classification: CiboEngineEfficiencyClass
    causal_loss_usd: Decimal
    primary_cause: str
    productive_authority: bool = False

    def __post_init__(self) -> None:
        for name in (
            "availability_efficiency",
            "consumption_efficiency",
            "actuation_efficiency",
            "economic_effect_efficiency",
            "value_capture_efficiency",
            "latency_efficiency",
            "engine_efficiency",
        ):
            value = getattr(self, name)
            if value < 0 or value > 1:
                raise CiboCapitalManagementError(
                    f"engine efficiency {name} outside [0,1]"
                )
        if self.productive_authority:
            raise CiboCapitalManagementError(
                "engine efficiency sensor cannot acquire productive authority"
            )
        if not self.primary_cause:
            raise CiboCapitalManagementError(
                "engine efficiency primary cause required"
            )


def _ratio(numerator: int | Decimal, denominator: int | Decimal) -> Decimal:
    num = Decimal(numerator)
    den = Decimal(denominator)
    if den <= 0:
        return Decimal(1) if num == 0 else Decimal(0)
    return max(Decimal(0), min(Decimal(1), num / den))


def measure_engine_efficiency(
    evidence: CiboEngineEfficiencyEvidence,
    *,
    latency_target_minutes: Decimal = Decimal("5"),
) -> CiboEngineEfficiencyReport:
    """Measure one engine without averaging away weak surfaces."""

    availability = _ratio(evidence.invoked_count, evidence.eligible_count)
    consumption = _ratio(
        evidence.output_consumed_count,
        evidence.invoked_count,
    )
    actuation = _ratio(
        evidence.decision_changed_count,
        evidence.output_consumed_count,
    )
    economic_effect = _ratio(
        evidence.economically_effective_count,
        evidence.decision_changed_count,
    )
    value_capture = _ratio(
        evidence.marginal_value_usd,
        evidence.opportunity_value_available_usd,
    )

    if evidence.latency_observations == 0:
        latency_efficiency = Decimal(1)
    else:
        avg_latency = (
            evidence.latency_minutes_total
            / Decimal(evidence.latency_observations)
        )
        latency_efficiency = (
            Decimal(1)
            if avg_latency <= latency_target_minutes
            else max(
                Decimal(0),
                min(
                    Decimal(1),
                    latency_target_minutes / avg_latency,
                ),
            )
        )

    engine_efficiency = min(
        availability,
        consumption,
        actuation,
        economic_effect,
        value_capture,
        latency_efficiency,
    )
    causal_loss = max(
        Decimal(0),
        evidence.opportunity_value_available_usd
        - evidence.marginal_value_usd
        + evidence.destructive_value_usd
        + evidence.unidentified_value_usd,
    )

    if evidence.destructive_value_usd > 0:
        classification = CiboEngineEfficiencyClass.DESTRUCTIVE
        cause = "engine destroys measurable causal economic value"
    elif evidence.blocked_count and evidence.invoked_count == 0:
        classification = CiboEngineEfficiencyClass.BLOCKED
        cause = "engine is eligible but blocked before native invocation"
    elif not evidence.value_identified or evidence.unidentified_value_usd > 0:
        classification = CiboEngineEfficiencyClass.UNIDENTIFIED
        cause = "engine marginal economic value is not yet identified"
    elif engine_efficiency <= Decimal("0.01"):
        classification = CiboEngineEfficiencyClass.NEAR_ZERO
        cause = "engine contributes near-zero end-to-end economic efficiency"
    elif actuation <= Decimal("0.25") or economic_effect <= Decimal("0.25"):
        classification = CiboEngineEfficiencyClass.LOW_ACTUATION
        cause = "engine runs but rarely changes an economically effective decision"
    else:
        classification = CiboEngineEfficiencyClass.VALUE_ADD
        cause = "engine demonstrates consumed, actuating economic value"

    return CiboEngineEfficiencyReport(
        engine_id=evidence.engine_id,
        availability_efficiency=availability,
        consumption_efficiency=consumption,
        actuation_efficiency=actuation,
        economic_effect_efficiency=economic_effect,
        value_capture_efficiency=value_capture,
        latency_efficiency=latency_efficiency,
        engine_efficiency=engine_efficiency,
        classification=classification,
        causal_loss_usd=causal_loss,
        primary_cause=cause,
    )


def rank_engine_efficiency(
    reports: tuple[CiboEngineEfficiencyReport, ...],
) -> tuple[CiboEngineEfficiencyReport, ...]:
    """Worst engines first: low efficiency, then high causal loss."""

    ids = tuple(item.engine_id for item in reports)
    if len(ids) != len(set(ids)):
        raise CiboCapitalManagementError(
            "engine efficiency report ids must be unique"
        )
    return tuple(
        sorted(
            reports,
            key=lambda item: (
                item.engine_efficiency,
                -item.causal_loss_usd,
                item.engine_id,
            ),
        )
    )
