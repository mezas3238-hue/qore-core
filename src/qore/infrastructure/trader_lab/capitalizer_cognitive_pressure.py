"""Causal cognitive-pressure posture for QORE Capitalizer.

Pressure changes selectivity/observation posture only. It cannot size positions, recover losses,
or override QORE Risk.
"""

from __future__ import annotations

from dataclasses import dataclass

from qore.infrastructure.trader_lab.capitalizer_master_cognitive_contract import (
    CapitalizerCognitivePressure,
)


@dataclass(frozen=True, slots=True)
class CapitalizerCognitivePressureFacts:
    upstream_day_stop_required: bool = False
    upstream_session_stop_required: bool = False
    same_failure_repeat_active: bool = False
    loss_cluster_active: bool = False
    uncertainty_high: bool = False
    execution_degraded: bool = False
    genuinely_new_causal_event_present: bool = False


@dataclass(frozen=True, slots=True)
class CapitalizerCognitivePressureAssessment:
    pressure: CapitalizerCognitivePressure
    reasons: tuple[str, ...]
    increases_risk_to_recover: bool = False
    grants_capital_authority: bool = False

    def __post_init__(self) -> None:
        if self.increases_risk_to_recover:
            raise ValueError("Capitalizer cognitive pressure cannot become recovery martingale")
        if self.grants_capital_authority:
            raise ValueError("cognitive pressure cannot grant capital authority")


def assess_cognitive_pressure(
    facts: CapitalizerCognitivePressureFacts,
) -> CapitalizerCognitivePressureAssessment:
    if facts.upstream_day_stop_required:
        return CapitalizerCognitivePressureAssessment(
            pressure=CapitalizerCognitivePressure.STOP_DAY,
            reasons=("UPSTREAM_DAY_STOP_REQUIRED",),
        )
    if facts.upstream_session_stop_required:
        return CapitalizerCognitivePressureAssessment(
            pressure=CapitalizerCognitivePressure.STOP_SESSION,
            reasons=("UPSTREAM_SESSION_STOP_REQUIRED",),
        )
    if facts.same_failure_repeat_active and not facts.genuinely_new_causal_event_present:
        return CapitalizerCognitivePressureAssessment(
            pressure=CapitalizerCognitivePressure.RECOVERY_OBSERVATION,
            reasons=("SAME_FAILURE_REPEAT_REQUIRES_NEW_CAUSAL_EVENT",),
        )
    if facts.loss_cluster_active:
        return CapitalizerCognitivePressureAssessment(
            pressure=CapitalizerCognitivePressure.HIGH_SELECTIVITY,
            reasons=("LOSS_CLUSTER_ACTIVE",),
        )

    cautious: list[str] = []
    if facts.uncertainty_high:
        cautious.append("UNCERTAINTY_HIGH")
    if facts.execution_degraded:
        cautious.append("EXECUTION_DEGRADED")
    if cautious:
        return CapitalizerCognitivePressureAssessment(
            pressure=CapitalizerCognitivePressure.CAUTIOUS,
            reasons=tuple(cautious),
        )

    return CapitalizerCognitivePressureAssessment(
        pressure=CapitalizerCognitivePressure.NORMAL,
        reasons=("NO_CAUSAL_PRESSURE",),
    )
