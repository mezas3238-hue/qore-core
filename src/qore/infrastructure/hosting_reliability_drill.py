from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from qore.kernel.errors import InfrastructureError


class HostingReliabilityDrillError(InfrastructureError):
    """Base error for deterministic Hosting reliability drills."""

    __slots__ = ()


class HostingReliabilityDrillValidationError(HostingReliabilityDrillError):
    """Violation of a Hosting reliability drill invariant."""

    __slots__ = ()


def _validate_uuid(value: UUID, *, field_name: str) -> None:
    if not isinstance(value, UUID):
        raise HostingReliabilityDrillValidationError(f"{field_name} must be UUID")


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise HostingReliabilityDrillValidationError(f"{field_name} must be datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise HostingReliabilityDrillValidationError(
            f"{field_name} must be timezone-aware"
        )


@dataclass(frozen=True, slots=True)
class HostingReliabilityDrillId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="reliability drill id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class HostingReliabilityDrillEvidenceReference:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="reliability drill evidence reference")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


class HostingReliabilityDrillScenario(StrEnum):
    SERVER_SHUTDOWN = "server_shutdown"
    HEARTBEAT_LOSS = "heartbeat_loss"
    NETWORK_DEGRADATION = "network_degradation"
    LATENCY_300MS_PLUS = "latency_300ms_plus"
    HIGH_JITTER = "high_jitter"
    PACKET_LOSS = "packet_loss"
    INGRESS_HEALTHY_EGRESS_BAD = "ingress_healthy_egress_bad"
    EGRESS_HEALTHY_INGRESS_BAD = "egress_healthy_ingress_bad"
    CANDIDATE_SERVER_UNHEALTHY = "candidate_server_unhealthy"
    STALE_LEASE = "stale_lease"
    DUPLICATE_EVENT = "duplicate_event"
    DELAYED_MESSAGE = "delayed_message"
    OUT_OF_ORDER_MARKET_DATA = "out_of_order_market_data"
    FEED_DISCONNECT = "feed_disconnect"
    PROVIDER_DISAGREEMENT = "provider_disagreement"
    AMBIGUOUS_ORDER_STATE = "ambiguous_order_state"
    PARTIAL_FILL = "partial_fill"
    REJECT = "reject"
    LOST_ACK = "lost_ack"


MANDATORY_DRILL_SCENARIOS = frozenset(HostingReliabilityDrillScenario)


class HostingReliabilityDrillDisposition(StrEnum):
    CONTAINED = "contained"
    BLOCKED = "blocked"
    QUARANTINED = "quarantined"
    RECONCILIATION_REQUIRED = "reconciliation_required"
    PRESERVE_AUTHORIZED_LIFECYCLE = "preserve_authorized_lifecycle"
    OBSERVED_NO_RETRY = "observed_no_retry"


_EXPECTED_DISPOSITIONS: dict[
    HostingReliabilityDrillScenario,
    frozenset[HostingReliabilityDrillDisposition],
] = {
    HostingReliabilityDrillScenario.SERVER_SHUTDOWN: frozenset(
        {HostingReliabilityDrillDisposition.CONTAINED}
    ),
    HostingReliabilityDrillScenario.HEARTBEAT_LOSS: frozenset(
        {HostingReliabilityDrillDisposition.CONTAINED}
    ),
    HostingReliabilityDrillScenario.NETWORK_DEGRADATION: frozenset(
        {HostingReliabilityDrillDisposition.CONTAINED}
    ),
    HostingReliabilityDrillScenario.LATENCY_300MS_PLUS: frozenset(
        {HostingReliabilityDrillDisposition.CONTAINED}
    ),
    HostingReliabilityDrillScenario.HIGH_JITTER: frozenset(
        {HostingReliabilityDrillDisposition.CONTAINED}
    ),
    HostingReliabilityDrillScenario.PACKET_LOSS: frozenset(
        {HostingReliabilityDrillDisposition.CONTAINED}
    ),
    HostingReliabilityDrillScenario.INGRESS_HEALTHY_EGRESS_BAD: frozenset(
        {HostingReliabilityDrillDisposition.CONTAINED}
    ),
    HostingReliabilityDrillScenario.EGRESS_HEALTHY_INGRESS_BAD: frozenset(
        {HostingReliabilityDrillDisposition.CONTAINED}
    ),
    HostingReliabilityDrillScenario.CANDIDATE_SERVER_UNHEALTHY: frozenset(
        {HostingReliabilityDrillDisposition.BLOCKED}
    ),
    HostingReliabilityDrillScenario.STALE_LEASE: frozenset(
        {HostingReliabilityDrillDisposition.BLOCKED}
    ),
    HostingReliabilityDrillScenario.DUPLICATE_EVENT: frozenset(
        {HostingReliabilityDrillDisposition.QUARANTINED}
    ),
    HostingReliabilityDrillScenario.DELAYED_MESSAGE: frozenset(
        {
            HostingReliabilityDrillDisposition.QUARANTINED,
            HostingReliabilityDrillDisposition.RECONCILIATION_REQUIRED,
        }
    ),
    HostingReliabilityDrillScenario.OUT_OF_ORDER_MARKET_DATA: frozenset(
        {HostingReliabilityDrillDisposition.QUARANTINED}
    ),
    HostingReliabilityDrillScenario.FEED_DISCONNECT: frozenset(
        {HostingReliabilityDrillDisposition.CONTAINED}
    ),
    HostingReliabilityDrillScenario.PROVIDER_DISAGREEMENT: frozenset(
        {HostingReliabilityDrillDisposition.BLOCKED}
    ),
    HostingReliabilityDrillScenario.AMBIGUOUS_ORDER_STATE: frozenset(
        {HostingReliabilityDrillDisposition.RECONCILIATION_REQUIRED}
    ),
    HostingReliabilityDrillScenario.PARTIAL_FILL: frozenset(
        {HostingReliabilityDrillDisposition.PRESERVE_AUTHORIZED_LIFECYCLE}
    ),
    HostingReliabilityDrillScenario.REJECT: frozenset(
        {HostingReliabilityDrillDisposition.OBSERVED_NO_RETRY}
    ),
    HostingReliabilityDrillScenario.LOST_ACK: frozenset(
        {HostingReliabilityDrillDisposition.RECONCILIATION_REQUIRED}
    ),
}


@dataclass(frozen=True, slots=True)
class HostingReliabilityDrillInjection:
    scenario: HostingReliabilityDrillScenario
    injected_at: datetime
    evidence_ref: HostingReliabilityDrillEvidenceReference

    def __post_init__(self) -> None:
        if not isinstance(self.scenario, HostingReliabilityDrillScenario):
            raise HostingReliabilityDrillValidationError(
                "scenario must be HostingReliabilityDrillScenario"
            )
        _validate_timestamp(self.injected_at, field_name="drill injected_at")
        if not isinstance(self.evidence_ref, HostingReliabilityDrillEvidenceReference):
            raise HostingReliabilityDrillValidationError(
                "injection evidence_ref must be HostingReliabilityDrillEvidenceReference"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.scenario.value,
            self.injected_at.isoformat(),
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class HostingReliabilityDrillResult:
    injection: HostingReliabilityDrillInjection
    disposition: HostingReliabilityDrillDisposition
    observed_at: datetime
    automatic_failover_triggered: bool
    order_redispatch_triggered: bool
    provider_switch_triggered: bool
    evidence_refs: tuple[HostingReliabilityDrillEvidenceReference, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.injection, HostingReliabilityDrillInjection):
            raise HostingReliabilityDrillValidationError(
                "injection must be HostingReliabilityDrillInjection"
            )
        if not isinstance(self.disposition, HostingReliabilityDrillDisposition):
            raise HostingReliabilityDrillValidationError(
                "disposition must be HostingReliabilityDrillDisposition"
            )
        if self.disposition not in _EXPECTED_DISPOSITIONS[self.injection.scenario]:
            raise HostingReliabilityDrillValidationError(
                "drill disposition is unsafe/incompatible with injected scenario"
            )
        _validate_timestamp(self.observed_at, field_name="drill observed_at")
        if self.observed_at < self.injection.injected_at:
            raise HostingReliabilityDrillValidationError(
                "drill result cannot predate injection"
            )
        for field_name, value in (
            ("automatic_failover_triggered", self.automatic_failover_triggered),
            ("order_redispatch_triggered", self.order_redispatch_triggered),
            ("provider_switch_triggered", self.provider_switch_triggered),
        ):
            if type(value) is not bool:
                raise HostingReliabilityDrillValidationError(
                    f"{field_name} must be bool"
                )
            if value:
                raise HostingReliabilityDrillValidationError(
                    f"{field_name} must remain false in this drill boundary"
                )
        if not isinstance(self.evidence_refs, tuple) or not self.evidence_refs or any(
            not isinstance(ref, HostingReliabilityDrillEvidenceReference)
            for ref in self.evidence_refs
        ):
            raise HostingReliabilityDrillValidationError(
                "drill result requires immutable non-empty evidence refs"
            )
        if len(self.evidence_refs) != len(set(self.evidence_refs)):
            raise HostingReliabilityDrillValidationError(
                "drill result evidence refs must be unique"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.injection.logical_values(),
            self.disposition.value,
            self.observed_at.isoformat(),
            self.automatic_failover_triggered,
            self.order_redispatch_triggered,
            self.provider_switch_triggered,
            tuple(ref.logical_values() for ref in self.evidence_refs),
        )


class HostingReliabilityDrillCertificationStatus(StrEnum):
    CERTIFIED_OFFLINE = "certified_offline"


@dataclass(frozen=True, slots=True)
class HostingReliabilityDrillReport:
    drill_id: HostingReliabilityDrillId
    results: tuple[HostingReliabilityDrillResult, ...]
    started_at: datetime
    ended_at: datetime
    reported_at: datetime
    evidence_ref: HostingReliabilityDrillEvidenceReference

    def __post_init__(self) -> None:
        if not isinstance(self.drill_id, HostingReliabilityDrillId):
            raise HostingReliabilityDrillValidationError(
                "drill_id must be HostingReliabilityDrillId"
            )
        if not isinstance(self.results, tuple) or any(
            not isinstance(item, HostingReliabilityDrillResult) for item in self.results
        ):
            raise HostingReliabilityDrillValidationError(
                "results must be immutable HostingReliabilityDrillResult tuple"
            )
        scenarios = {item.injection.scenario for item in self.results}
        if scenarios != MANDATORY_DRILL_SCENARIOS:
            raise HostingReliabilityDrillValidationError(
                "drill report must cover every mandatory failure-injection scenario"
            )
        if len(scenarios) != len(self.results):
            raise HostingReliabilityDrillValidationError(
                "drill report must contain exactly one result per scenario"
            )
        _validate_timestamp(self.started_at, field_name="drill started_at")
        _validate_timestamp(self.ended_at, field_name="drill ended_at")
        _validate_timestamp(self.reported_at, field_name="drill reported_at")
        if self.ended_at <= self.started_at:
            raise HostingReliabilityDrillValidationError(
                "drill ended_at must be after started_at"
            )
        if self.reported_at < self.ended_at:
            raise HostingReliabilityDrillValidationError(
                "drill report cannot predate drill end"
            )
        if any(
            item.injection.injected_at < self.started_at
            or item.observed_at > self.ended_at
            for item in self.results
        ):
            raise HostingReliabilityDrillValidationError(
                "all drill injections/results must fit inside drill window"
            )
        if not isinstance(self.evidence_ref, HostingReliabilityDrillEvidenceReference):
            raise HostingReliabilityDrillValidationError(
                "report evidence_ref must be HostingReliabilityDrillEvidenceReference"
            )

    @property
    def certification_status(self) -> HostingReliabilityDrillCertificationStatus:
        return HostingReliabilityDrillCertificationStatus.CERTIFIED_OFFLINE

    @property
    def automatic_failovers(self) -> int:
        return 0

    @property
    def order_redispatches(self) -> int:
        return 0

    @property
    def provider_switches(self) -> int:
        return 0

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.drill_id.logical_values(),
            tuple(item.logical_values() for item in self.results),
            self.started_at.isoformat(),
            self.ended_at.isoformat(),
            self.reported_at.isoformat(),
            self.evidence_ref.logical_values(),
        )
