"""MC-20 descriptive Stability Engine.

The engine keeps market, QORE Core, provider/broker, cognition and systemic
stress as separate descriptive channels. Missing operational evidence remains
UNKNOWN rather than being inferred from market prices.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import StrEnum


class StabilityDomain(StrEnum):
    MARKET = "MARKET"
    QORE_CORE = "QORE_CORE"
    PROVIDER_BROKER = "PROVIDER_BROKER"
    COGNITION = "COGNITION"
    SYSTEMIC_STRESS = "SYSTEMIC_STRESS"


class StabilityState(StrEnum):
    STABLE = "STABLE"
    WATCH = "WATCH"
    DEFENSIVE_CONTEXT = "DEFENSIVE_CONTEXT"
    RECOVERY = "RECOVERY"
    DISLOCATION = "DISLOCATION"
    UNKNOWN = "UNKNOWN"
    SYSTEM_DEGRADED = "SYSTEM_DEGRADED"


@dataclass(frozen=True, slots=True)
class StabilityEvidence:
    domain: StabilityDomain
    evidence_available: bool
    stability_bps: int
    degradation_bps: int
    recovery_bps: int
    dislocation_bps: int
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in (
            "stability_bps",
            "degradation_bps",
            "recovery_bps",
            "dislocation_bps",
        ):
            value = getattr(self, name)
            if type(value) is not int or not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be int within 0..10000")
        if (
            not self.evidence_refs
            or self.evidence_refs != tuple(sorted(set(self.evidence_refs)))
        ):
            raise ValueError("stability evidence refs must be canonical")


@dataclass(frozen=True, slots=True)
class StabilityChannelAssessment:
    domain: StabilityDomain
    state: StabilityState
    stability_bps: int
    degradation_bps: int
    recovery_bps: int
    dislocation_bps: int
    evidence_available: bool
    evidence_refs: tuple[str, ...]
    trading_command: bool = False
    execution_authority: bool = False
    risk_authority: bool = False
    sizing_authority: bool = False

    def __post_init__(self) -> None:
        if (
            self.trading_command
            or self.execution_authority
            or self.risk_authority
            or self.sizing_authority
        ):
            raise ValueError("stability states are descriptive only")


@dataclass(frozen=True, slots=True)
class StabilitySnapshot:
    channels: tuple[StabilityChannelAssessment, ...]

    def __post_init__(self) -> None:
        if self.channels != tuple(
            sorted(self.channels, key=lambda item: item.domain.value)
        ):
            raise ValueError("stability channels must be canonical")
        domains = {item.domain for item in self.channels}
        if domains != set(StabilityDomain):
            raise ValueError("stability snapshot requires all five domains")

    def fingerprint(self) -> str:
        payload = {
            "channels": tuple(
                {
                    **asdict(item),
                    "domain": item.domain.value,
                    "state": item.state.value,
                }
                for item in self.channels
            )
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()


def assess_stability_channel(
    evidence: StabilityEvidence,
) -> StabilityChannelAssessment:
    if not evidence.evidence_available:
        state = StabilityState.UNKNOWN
    elif evidence.domain in {
        StabilityDomain.QORE_CORE,
        StabilityDomain.PROVIDER_BROKER,
    } and evidence.degradation_bps >= 8_000:
        state = StabilityState.SYSTEM_DEGRADED
    elif evidence.dislocation_bps >= 8_000:
        state = StabilityState.DISLOCATION
    elif (
        evidence.recovery_bps >= 6_500
        and evidence.recovery_bps > evidence.degradation_bps
        and evidence.stability_bps < 7_500
    ):
        state = StabilityState.RECOVERY
    elif evidence.degradation_bps >= 6_500:
        state = StabilityState.DEFENSIVE_CONTEXT
    elif evidence.degradation_bps >= 4_000 or evidence.stability_bps < 6_500:
        state = StabilityState.WATCH
    else:
        state = StabilityState.STABLE

    return StabilityChannelAssessment(
        domain=evidence.domain,
        state=state,
        stability_bps=evidence.stability_bps,
        degradation_bps=evidence.degradation_bps,
        recovery_bps=evidence.recovery_bps,
        dislocation_bps=evidence.dislocation_bps,
        evidence_available=evidence.evidence_available,
        evidence_refs=evidence.evidence_refs,
    )


def build_stability_snapshot(
    evidence: tuple[StabilityEvidence, ...],
) -> StabilitySnapshot:
    if {item.domain for item in evidence} != set(StabilityDomain):
        raise ValueError("stability evidence requires all five distinct domains")
    channels = tuple(
        sorted(
            (assess_stability_channel(item) for item in evidence),
            key=lambda item: item.domain.value,
        )
    )
    return StabilitySnapshot(channels=channels)
