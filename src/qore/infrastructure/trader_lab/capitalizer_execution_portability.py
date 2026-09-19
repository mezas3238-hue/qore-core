"""Multi-environment execution certification contracts for QORE Capitalizer.

The Capitalizer is not considered portable/certified merely because it survives one broker.
Certification requires the same frozen strategy/cognitive candidate to pass all mandatory
execution environments and an adverse portability envelope. This module records evidence
status only; it does not fabricate provider costs or grant promotion/execution authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from re import fullmatch


class CapitalizerExecutionEnvironment(StrEnum):
    IC_MARKETS_RAW = "IC_MARKETS_RAW"
    FTMO = "FTMO"
    FUNDEDNEXT = "FUNDEDNEXT"
    ADVERSE_PORTABILITY_ENVELOPE = "ADVERSE_PORTABILITY_ENVELOPE"


MANDATORY_EXECUTION_ENVIRONMENTS: tuple[CapitalizerExecutionEnvironment, ...] = (
    CapitalizerExecutionEnvironment.IC_MARKETS_RAW,
    CapitalizerExecutionEnvironment.FTMO,
    CapitalizerExecutionEnvironment.FUNDEDNEXT,
    CapitalizerExecutionEnvironment.ADVERSE_PORTABILITY_ENVELOPE,
)


class CapitalizerEnvironmentStatus(StrEnum):
    UNTESTED = "UNTESTED"
    QUALIFIED = "QUALIFIED"
    REJECTED = "REJECTED"


@dataclass(frozen=True, slots=True)
class CapitalizerExecutionProfileEvidence:
    """One exact cost/execution profile bound to externally measured or frozen research data."""

    environment: CapitalizerExecutionEnvironment
    profile_fingerprint: str
    spread_cost_r: Decimal
    commission_cost_r: Decimal
    slippage_cost_r: Decimal
    latency_ms: int

    def __post_init__(self) -> None:
        if fullmatch(r"[0-9a-f]{64}", self.profile_fingerprint) is None:
            raise ValueError("profile_fingerprint must be canonical sha256")
        for name, value in (
            ("spread_cost_r", self.spread_cost_r),
            ("commission_cost_r", self.commission_cost_r),
            ("slippage_cost_r", self.slippage_cost_r),
        ):
            if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
                raise ValueError(f"{name} must be finite non-negative Decimal")
        if type(self.latency_ms) is not int or self.latency_ms < 0:
            raise ValueError("latency_ms must be a non-negative int")

    @property
    def total_cost_r(self) -> Decimal:
        return self.spread_cost_r + self.commission_cost_r + self.slippage_cost_r


@dataclass(frozen=True, slots=True)
class CapitalizerEnvironmentQualification:
    """Result of evaluating one frozen candidate under one execution profile."""

    environment: CapitalizerExecutionEnvironment
    profile_fingerprint: str
    status: CapitalizerEnvironmentStatus
    evidence_fingerprint: str

    def __post_init__(self) -> None:
        if fullmatch(r"[0-9a-f]{64}", self.profile_fingerprint) is None:
            raise ValueError("profile_fingerprint must be canonical sha256")
        if fullmatch(r"[0-9a-f]{64}", self.evidence_fingerprint) is None:
            raise ValueError("evidence_fingerprint must be canonical sha256")


@dataclass(frozen=True, slots=True)
class CapitalizerPortabilityDecision:
    """Fail-closed portability result. This is not Trader Lab promotion authority."""

    qualified: bool
    reasons: tuple[str, ...]


def evaluate_execution_portability(
    qualifications: tuple[CapitalizerEnvironmentQualification, ...],
) -> CapitalizerPortabilityDecision:
    """Require exact, unique QUALIFIED evidence for every mandatory environment."""

    by_environment: dict[
        CapitalizerExecutionEnvironment, CapitalizerEnvironmentQualification
    ] = {}
    reasons: list[str] = []
    for qualification in qualifications:
        if qualification.environment in by_environment:
            reasons.append(f"DUPLICATE:{qualification.environment.value}")
            continue
        by_environment[qualification.environment] = qualification

    for environment in MANDATORY_EXECUTION_ENVIRONMENTS:
        qualification = by_environment.get(environment)
        if qualification is None:
            reasons.append(f"MISSING:{environment.value}")
        elif qualification.status is not CapitalizerEnvironmentStatus.QUALIFIED:
            reasons.append(
                f"NOT_QUALIFIED:{environment.value}:{qualification.status.value}"
            )

    extras = tuple(
        environment
        for environment in by_environment
        if environment not in MANDATORY_EXECUTION_ENVIRONMENTS
    )
    if extras:
        reasons.extend(f"UNEXPECTED:{item.value}" for item in sorted(extras, key=str))

    return CapitalizerPortabilityDecision(
        qualified=not reasons,
        reasons=tuple(reasons),
    )
