from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from re import fullmatch

from qore.infrastructure.mission03_operational_e2e_preparation import Mission03E2EGate
from qore.infrastructure.ports import ExternalPortError
from qore.kernel.result import Failure, Result, Success

_SENSITIVE_PARTS = (
    "authorization:",
    "bearer ",
    "client_secret",
    "password=",
    "secret=",
    "token=",
)

_GATE_ORDER: tuple[Mission03E2EGate, ...] = tuple(Mission03E2EGate)


class Mission03ClosurePreparationError(ExternalPortError):
    """Base error for deterministic MISSION-03 closure preparation."""

    __slots__ = ()


class Mission03ClosurePreparationValidationError(Mission03ClosurePreparationError):
    """MISSION-03 closure preparation is incomplete or contradictory."""

    __slots__ = ()


class Mission03ClosurePreparationStatus(StrEnum):
    ELIGIBLE = "eligible"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class Mission03OperationalGateEvidenceRef:
    """Opaque sanitized reference to successful operational Gate evidence."""

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or fullmatch(
            r"[a-z][a-z0-9._:/-]*",
            self.value,
        ) is None:
            raise Mission03ClosurePreparationValidationError(
                "MISSION-03 operational evidence ref must use canonical lowercase syntax"
            )
        normalized = self.value.lower()
        if any(part in normalized for part in _SENSITIVE_PARTS):
            raise Mission03ClosurePreparationValidationError(
                "MISSION-03 operational evidence ref must not contain sensitive material"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class Mission03OperationalGateClosureRecord:
    """Closure-facing completion state for one operational Gate #5-#13."""

    gate: Mission03E2EGate
    completed: bool
    evidence_refs: tuple[Mission03OperationalGateEvidenceRef, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.gate, Mission03E2EGate):
            raise Mission03ClosurePreparationValidationError(
                "MISSION-03 closure record requires explicit Gate #5-#13"
            )
        if type(self.completed) is not bool:
            raise Mission03ClosurePreparationValidationError(
                "MISSION-03 closure completed flag must be bool"
            )
        if not isinstance(self.evidence_refs, tuple) or any(
            not isinstance(item, Mission03OperationalGateEvidenceRef)
            for item in self.evidence_refs
        ):
            raise Mission03ClosurePreparationValidationError(
                "MISSION-03 closure evidence refs must be typed immutable values"
            )
        if len(set(self.evidence_refs)) != len(self.evidence_refs):
            raise Mission03ClosurePreparationValidationError(
                "MISSION-03 closure evidence refs must not contain duplicates"
            )
        if self.completed and not self.evidence_refs:
            raise Mission03ClosurePreparationValidationError(
                "completed operational Gate requires operational evidence"
            )
        if not self.completed and self.evidence_refs:
            raise Mission03ClosurePreparationValidationError(
                "incomplete operational Gate must not carry completion evidence"
            )
        object.__setattr__(
            self,
            "evidence_refs",
            tuple(sorted(self.evidence_refs, key=lambda item: item.value)),
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.gate.value,
            self.completed,
            tuple(item.logical_values() for item in self.evidence_refs),
        )


@dataclass(frozen=True, slots=True)
class Mission03ClosurePreparationEvidence:
    """Exact closure prerequisite matrix; never the final mission closure itself."""

    provider_key: str
    environment: str
    gates: tuple[Mission03OperationalGateClosureRecord, ...]

    def __post_init__(self) -> None:
        if self.provider_key != "oanda-v20":
            raise Mission03ClosurePreparationValidationError(
                "MISSION-03 closure provider must be oanda-v20"
            )
        if self.environment != "demo":
            raise Mission03ClosurePreparationValidationError(
                "MISSION-03 closure environment must be demo"
            )
        if not isinstance(self.gates, tuple) or any(
            not isinstance(item, Mission03OperationalGateClosureRecord)
            for item in self.gates
        ):
            raise Mission03ClosurePreparationValidationError(
                "MISSION-03 closure gates must be typed immutable records"
            )
        if tuple(item.gate for item in self.gates) != _GATE_ORDER:
            raise Mission03ClosurePreparationValidationError(
                "MISSION-03 closure evidence must contain Gates #5-#13 exactly once"
            )
        completed = tuple(record.completed for record in self.gates)
        first_incomplete: int | None = None
        for index, is_completed in enumerate(completed):
            if not is_completed:
                first_incomplete = index
                break
        if first_incomplete is not None and any(completed[first_incomplete + 1 :]):
            raise Mission03ClosurePreparationValidationError(
                "MISSION-03 operational Gates must close sequentially without gaps"
            )

    @property
    def status(self) -> Mission03ClosurePreparationStatus:
        if all(record.completed for record in self.gates):
            return Mission03ClosurePreparationStatus.ELIGIBLE
        return Mission03ClosurePreparationStatus.BLOCKED

    @property
    def closure_attempt_permitted(self) -> bool:
        return self.status is Mission03ClosurePreparationStatus.ELIGIBLE

    @property
    def mission_closed(self) -> bool:
        """Closure preparation can never close MISSION-03 by itself."""
        return False

    @property
    def missing_gates(self) -> tuple[Mission03E2EGate, ...]:
        return tuple(record.gate for record in self.gates if not record.completed)

    @property
    def blocker_codes(self) -> tuple[str, ...]:
        return tuple(f"{gate.value}.not-completed" for gate in self.missing_gates)

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.provider_key,
            self.environment,
            self.status.value,
            tuple(record.logical_values() for record in self.gates),
            tuple(gate.value for gate in self.missing_gates),
            self.blocker_codes,
            self.closure_attempt_permitted,
            self.mission_closed,
        )

    def public_payload(self) -> dict[str, object]:
        return {
            "provider": self.provider_key,
            "environment": self.environment,
            "closure_preparation_status": self.status.value,
            "closure_attempt_permitted": self.closure_attempt_permitted,
            "mission_closed": False,
            "missing_gates": [gate.value for gate in self.missing_gates],
            "blocker_codes": list(self.blocker_codes),
            "gates": [
                {
                    "gate": record.gate.value,
                    "completed": record.completed,
                    "evidence_refs": [item.value for item in record.evidence_refs],
                }
                for record in self.gates
            ],
        }

    def to_json(self) -> str:
        return json.dumps(
            self.public_payload(),
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )


def build_mission03_closure_preparation_evidence(
    records: tuple[Mission03OperationalGateClosureRecord, ...],
) -> Result[Mission03ClosurePreparationEvidence, Mission03ClosurePreparationError]:
    """Build the exact Gate #5-#13 mission-closure prerequisite matrix."""

    if not isinstance(records, tuple) or any(
        not isinstance(record, Mission03OperationalGateClosureRecord)
        for record in records
    ):
        return Failure(
            Mission03ClosurePreparationValidationError(
                "MISSION-03 closure preparation requires typed record tuple"
            )
        )
    by_gate: dict[Mission03E2EGate, Mission03OperationalGateClosureRecord] = {}
    for record in records:
        if record.gate in by_gate:
            return Failure(
                Mission03ClosurePreparationValidationError(
                    "duplicate MISSION-03 closure Gate is not allowed"
                )
            )
        by_gate[record.gate] = record
    if set(by_gate) != set(_GATE_ORDER):
        return Failure(
            Mission03ClosurePreparationValidationError(
                "MISSION-03 closure prerequisite matrix is incomplete"
            )
        )
    try:
        evidence = Mission03ClosurePreparationEvidence(
            provider_key="oanda-v20",
            environment="demo",
            gates=tuple(by_gate[gate] for gate in _GATE_ORDER),
        )
    except Mission03ClosurePreparationError as error:
        return Failure(error)
    return Success(evidence)
