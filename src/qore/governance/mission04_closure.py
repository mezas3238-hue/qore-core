from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from re import fullmatch

from qore.kernel.errors import DomainError
from qore.kernel.result import Failure, Result, Success

_SENSITIVE_PARTS = (
    "authorization:",
    "bearer ",
    "client_secret",
    "credential",
    "password",
    "private_key",
    "secret",
    "token",
)


class Mission04ClosureError(DomainError):
    """Base error for MISSION-04 closure-readiness contracts."""

    __slots__ = ()


class Mission04ClosureValidationError(Mission04ClosureError):
    """MISSION-04 closure evidence is incomplete or contradictory."""

    __slots__ = ()


class Mission04Delivery(StrEnum):
    DOCS = "mission04-docs"
    AUTHENTICATED_PRINCIPAL = "authenticated-principal"
    AUTHORITY_STATE = "authority-state"
    REQUEST_GUARD = "request-guard"
    COMMAND_DISPATCH = "command-dispatch"
    QUERY_DISPATCH = "query-dispatch"
    GOVERNANCE_MUTATION = "governance-mutation"
    AUDIT_EVIDENCE = "audit-evidence"
    REPLAY_PROTECTION = "replay-protection"
    TRANSPORT_ENVELOPE = "transport-envelope"
    CONTROL_PLANE_OBSERVABILITY = "control-plane-observability"
    CONTROL_PLANE_RESILIENCE = "control-plane-resilience"
    OFFLINE_E2E = "offline-e2e"


_DELIVERY_ORDER: tuple[Mission04Delivery, ...] = tuple(Mission04Delivery)


class Mission04ClosureReadinessStatus(StrEnum):
    READY = "ready"
    BLOCKED = "blocked"


def _validate_evidence_ref(value: str) -> str:
    if not isinstance(value, str) or fullmatch(r"[a-z][a-z0-9._:/-]*", value) is None:
        raise Mission04ClosureValidationError(
            "MISSION-04 evidence ref must use canonical lowercase syntax"
        )
    normalized = value.lower()
    if any(part in normalized for part in _SENSITIVE_PARTS):
        raise Mission04ClosureValidationError(
            "MISSION-04 evidence ref must not contain sensitive material"
        )
    return value


@dataclass(frozen=True, slots=True)
class Mission04ClosureEvidenceRef:
    """Opaque secret-free reference to merged delivery/quality evidence."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", _validate_evidence_ref(self.value))

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class Mission04DeliveryClosureRecord:
    delivery: Mission04Delivery
    completed: bool
    evidence_refs: tuple[Mission04ClosureEvidenceRef, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.delivery, Mission04Delivery):
            raise Mission04ClosureValidationError(
                "MISSION-04 closure record requires Mission04Delivery"
            )
        if type(self.completed) is not bool:
            raise Mission04ClosureValidationError(
                "MISSION-04 closure completed flag must be bool"
            )
        if not isinstance(self.evidence_refs, tuple) or any(
            not isinstance(item, Mission04ClosureEvidenceRef)
            for item in self.evidence_refs
        ):
            raise Mission04ClosureValidationError(
                "MISSION-04 closure evidence refs must be typed immutable values"
            )
        if len(set(self.evidence_refs)) != len(self.evidence_refs):
            raise Mission04ClosureValidationError(
                "MISSION-04 closure evidence refs must not contain duplicates"
            )
        if self.completed and not self.evidence_refs:
            raise Mission04ClosureValidationError(
                "completed MISSION-04 delivery requires evidence"
            )
        if not self.completed and self.evidence_refs:
            raise Mission04ClosureValidationError(
                "incomplete MISSION-04 delivery must not carry completion evidence"
            )
        object.__setattr__(
            self,
            "evidence_refs",
            tuple(sorted(self.evidence_refs, key=lambda item: item.value)),
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.delivery.value,
            self.completed,
            tuple(item.logical_values() for item in self.evidence_refs),
        )


@dataclass(frozen=True, slots=True)
class Mission04ClosureReadiness:
    """Fail-closed readiness matrix for Deliveries 1-13; never self-closes the mission."""

    deliveries: tuple[Mission04DeliveryClosureRecord, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.deliveries, tuple) or any(
            not isinstance(item, Mission04DeliveryClosureRecord)
            for item in self.deliveries
        ):
            raise Mission04ClosureValidationError(
                "MISSION-04 closure readiness requires typed delivery records"
            )
        if tuple(item.delivery for item in self.deliveries) != _DELIVERY_ORDER:
            raise Mission04ClosureValidationError(
                "MISSION-04 closure readiness must contain Deliveries 1-13 exactly once"
            )
        completed = tuple(item.completed for item in self.deliveries)
        first_incomplete: int | None = None
        for index, is_completed in enumerate(completed):
            if not is_completed:
                first_incomplete = index
                break
        if first_incomplete is not None and any(completed[first_incomplete + 1 :]):
            raise Mission04ClosureValidationError(
                "MISSION-04 deliveries must complete sequentially without gaps"
            )

    @property
    def status(self) -> Mission04ClosureReadinessStatus:
        if all(item.completed for item in self.deliveries):
            return Mission04ClosureReadinessStatus.READY
        return Mission04ClosureReadinessStatus.BLOCKED

    @property
    def closure_attempt_permitted(self) -> bool:
        return self.status is Mission04ClosureReadinessStatus.READY

    @property
    def missing_deliveries(self) -> tuple[Mission04Delivery, ...]:
        return tuple(item.delivery for item in self.deliveries if not item.completed)

    @property
    def blocker_codes(self) -> tuple[str, ...]:
        return tuple(
            f"{delivery.value}.not-completed" for delivery in self.missing_deliveries
        )

    @property
    def mission_closed(self) -> bool:
        """A readiness value cannot declare its own Delivery-14 merge complete."""

        return False

    @property
    def external_control_plane_activation_authorized(self) -> bool:
        return False

    @property
    def production_authorized(self) -> bool:
        return False

    @property
    def mission03_operationally_closed(self) -> bool:
        return False

    @property
    def mission05_opened(self) -> bool:
        return False

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.status.value,
            tuple(item.logical_values() for item in self.deliveries),
            tuple(item.value for item in self.missing_deliveries),
            self.blocker_codes,
            self.closure_attempt_permitted,
            self.mission_closed,
            self.external_control_plane_activation_authorized,
            self.production_authorized,
            self.mission03_operationally_closed,
            self.mission05_opened,
        )

    def public_payload(self) -> dict[str, object]:
        return {
            "mission": "mission-04",
            "scope": "offline-provider-independent-control-plane",
            "readiness_status": self.status.value,
            "closure_attempt_permitted": self.closure_attempt_permitted,
            "mission_closed": False,
            "external_control_plane_activation_authorized": False,
            "production_authorized": False,
            "mission03_operationally_closed": False,
            "mission05_opened": False,
            "missing_deliveries": [item.value for item in self.missing_deliveries],
            "blocker_codes": list(self.blocker_codes),
            "deliveries": [
                {
                    "delivery": record.delivery.value,
                    "completed": record.completed,
                    "evidence_refs": [item.value for item in record.evidence_refs],
                }
                for record in self.deliveries
            ],
        }

    def to_json(self) -> str:
        return json.dumps(
            self.public_payload(),
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )


def build_mission04_closure_readiness(
    records: tuple[Mission04DeliveryClosureRecord, ...],
) -> Result[Mission04ClosureReadiness, Mission04ClosureError]:
    """Build the exact Delivery 1-13 readiness matrix for final closure review."""

    if not isinstance(records, tuple) or any(
        not isinstance(record, Mission04DeliveryClosureRecord) for record in records
    ):
        return Failure(
            Mission04ClosureValidationError(
                "MISSION-04 closure readiness requires typed record tuple"
            )
        )
    by_delivery: dict[Mission04Delivery, Mission04DeliveryClosureRecord] = {}
    for record in records:
        if record.delivery in by_delivery:
            return Failure(
                Mission04ClosureValidationError(
                    "duplicate MISSION-04 closure delivery is not allowed"
                )
            )
        by_delivery[record.delivery] = record
    if set(by_delivery) != set(_DELIVERY_ORDER):
        return Failure(
            Mission04ClosureValidationError(
                "MISSION-04 closure readiness matrix is incomplete"
            )
        )
    try:
        readiness = Mission04ClosureReadiness(
            deliveries=tuple(by_delivery[item] for item in _DELIVERY_ORDER),
        )
    except Mission04ClosureError as error:
        return Failure(error)
    return Success(readiness)
