from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from re import fullmatch

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


class Mission03OperationalE2EPreparationError(ExternalPortError):
    """Base error for deterministic MISSION-03 Gate #13 preparation."""

    __slots__ = ()


class Mission03OperationalE2EPreparationValidationError(
    Mission03OperationalE2EPreparationError
):
    """The Gate #13 preparation matrix is incomplete or contradictory."""

    __slots__ = ()


class Mission03E2EGate(StrEnum):
    LIVE_MARKET_FEED = "gate-05-live-market-feed"
    MARKET_DATA_CERTIFICATION = "gate-06-market-data-certification"
    DEMO_ACCOUNT_ACTIVATION = "gate-07-demo-account-activation"
    DEMO_EXECUTION_ACTIVATION = "gate-08-demo-execution-activation"
    OPERATIONAL_SAFETY_CERTIFICATION = "gate-09-operational-safety-certification"
    CIBO_OPERATIONAL_SUPERVISION = "gate-10-cibo-operational-supervision"
    OBSERVABILITY = "gate-11-observability"
    RESILIENCE = "gate-12-resilience"
    REAL_MARKET_OPERATIONAL_E2E = "gate-13-real-market-operational-e2e"


_GATE_ORDER: tuple[Mission03E2EGate, ...] = (
    Mission03E2EGate.LIVE_MARKET_FEED,
    Mission03E2EGate.MARKET_DATA_CERTIFICATION,
    Mission03E2EGate.DEMO_ACCOUNT_ACTIVATION,
    Mission03E2EGate.DEMO_EXECUTION_ACTIVATION,
    Mission03E2EGate.OPERATIONAL_SAFETY_CERTIFICATION,
    Mission03E2EGate.CIBO_OPERATIONAL_SUPERVISION,
    Mission03E2EGate.OBSERVABILITY,
    Mission03E2EGate.RESILIENCE,
    Mission03E2EGate.REAL_MARKET_OPERATIONAL_E2E,
)

_PRE_E2E_GATES = _GATE_ORDER[:-1]


class Mission03GatePreparationStatus(StrEnum):
    READY = "ready"
    NOT_READY = "not-ready"


class Mission03E2EPreparationStatus(StrEnum):
    READY = "ready"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class Mission03E2EEvidenceRef:
    """Opaque sanitized reference to one Gate #5-#13 preparation artifact."""

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or fullmatch(
            r"[a-z][a-z0-9._:/-]*",
            self.value,
        ) is None:
            raise Mission03OperationalE2EPreparationValidationError(
                "MISSION-03 E2E evidence ref must use canonical lowercase syntax"
            )
        normalized = self.value.lower()
        if any(part in normalized for part in _SENSITIVE_PARTS):
            raise Mission03OperationalE2EPreparationValidationError(
                "MISSION-03 E2E evidence ref must not contain sensitive material"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class Mission03GatePreparationRecord:
    gate: Mission03E2EGate
    status: Mission03GatePreparationStatus
    evidence_refs: tuple[Mission03E2EEvidenceRef, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.gate, Mission03E2EGate):
            raise Mission03OperationalE2EPreparationValidationError(
                "MISSION-03 gate preparation requires explicit gate"
            )
        if not isinstance(self.status, Mission03GatePreparationStatus):
            raise Mission03OperationalE2EPreparationValidationError(
                "MISSION-03 gate preparation requires explicit status"
            )
        if not isinstance(self.evidence_refs, tuple) or not self.evidence_refs:
            raise Mission03OperationalE2EPreparationValidationError(
                "MISSION-03 gate preparation requires evidence refs"
            )
        if any(
            not isinstance(item, Mission03E2EEvidenceRef)
            for item in self.evidence_refs
        ):
            raise Mission03OperationalE2EPreparationValidationError(
                "MISSION-03 gate preparation refs must use typed values"
            )
        if len(set(self.evidence_refs)) != len(self.evidence_refs):
            raise Mission03OperationalE2EPreparationValidationError(
                "MISSION-03 gate preparation refs must not contain duplicates"
            )
        object.__setattr__(
            self,
            "evidence_refs",
            tuple(sorted(self.evidence_refs, key=lambda item: item.value)),
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.gate.value,
            self.status.value,
            tuple(item.logical_values() for item in self.evidence_refs),
        )


@dataclass(frozen=True, slots=True)
class Mission03ExternalPrerequisiteState:
    """Secret-free operational prerequisite state supplied by an authorized operator."""

    practice_account_provisioned: bool
    practice_token_provisioned: bool
    completed_operational_gates: tuple[Mission03E2EGate, ...] = ()

    def __post_init__(self) -> None:
        if type(self.practice_account_provisioned) is not bool:
            raise Mission03OperationalE2EPreparationValidationError(
                "Practice account provisioned flag must be bool"
            )
        if type(self.practice_token_provisioned) is not bool:
            raise Mission03OperationalE2EPreparationValidationError(
                "Practice token provisioned flag must be bool"
            )
        if not isinstance(self.completed_operational_gates, tuple):
            raise Mission03OperationalE2EPreparationValidationError(
                "completed operational gates must be immutable tuple"
            )
        if any(
            not isinstance(item, Mission03E2EGate)
            for item in self.completed_operational_gates
        ):
            raise Mission03OperationalE2EPreparationValidationError(
                "completed operational gates must use typed gate values"
            )
        if len(set(self.completed_operational_gates)) != len(
            self.completed_operational_gates
        ):
            raise Mission03OperationalE2EPreparationValidationError(
                "completed operational gates must not contain duplicates"
            )
        if any(
            gate not in _PRE_E2E_GATES
            for gate in self.completed_operational_gates
        ):
            raise Mission03OperationalE2EPreparationValidationError(
                "Gate #13 cannot be predeclared completed in preparation state"
            )
        completed = set(self.completed_operational_gates)
        if completed and (
            not self.practice_account_provisioned
            or not self.practice_token_provisioned
        ):
            raise Mission03OperationalE2EPreparationValidationError(
                "operational gate completion requires provisioned Practice account and token"
            )
        normalized = tuple(
            gate for gate in _PRE_E2E_GATES if gate in completed
        )
        if self.completed_operational_gates != normalized:
            raise Mission03OperationalE2EPreparationValidationError(
                "completed operational gates must follow canonical sequence"
            )
        prefix = _PRE_E2E_GATES[: len(normalized)]
        if normalized != prefix:
            raise Mission03OperationalE2EPreparationValidationError(
                "operational gates must be completed sequentially without gaps"
            )

    @property
    def missing_operational_gates(self) -> tuple[Mission03E2EGate, ...]:
        completed = set(self.completed_operational_gates)
        return tuple(gate for gate in _PRE_E2E_GATES if gate not in completed)

    @property
    def blocker_codes(self) -> tuple[str, ...]:
        blockers: list[str] = []
        if not self.practice_account_provisioned:
            blockers.append("oanda.practice.account.not-provisioned")
        if not self.practice_token_provisioned:
            blockers.append("oanda.practice.token.not-provisioned")
        blockers.extend(
            f"{gate.value}.operational-evidence-missing"
            for gate in self.missing_operational_gates
        )
        return tuple(blockers)

    @property
    def pre_e2e_operational_sequence_completed(self) -> bool:
        return not self.missing_operational_gates

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.practice_account_provisioned,
            self.practice_token_provisioned,
            tuple(gate.value for gate in self.completed_operational_gates),
            tuple(gate.value for gate in self.missing_operational_gates),
            self.blocker_codes,
        )


@dataclass(frozen=True, slots=True)
class Mission03OperationalE2EPreparationEvidence:
    """Gate #13 offline readiness evidence; never operational completion evidence."""

    provider_key: str
    environment: str
    gates: tuple[Mission03GatePreparationRecord, ...]
    external_prerequisites: Mission03ExternalPrerequisiteState

    def __post_init__(self) -> None:
        if self.provider_key != "oanda-v20":
            raise Mission03OperationalE2EPreparationValidationError(
                "MISSION-03 E2E provider must be oanda-v20"
            )
        if self.environment != "demo":
            raise Mission03OperationalE2EPreparationValidationError(
                "MISSION-03 E2E environment must be demo"
            )
        if not isinstance(self.gates, tuple):
            raise Mission03OperationalE2EPreparationValidationError(
                "MISSION-03 E2E gates must be immutable tuple"
            )
        if any(
            not isinstance(item, Mission03GatePreparationRecord)
            for item in self.gates
        ):
            raise Mission03OperationalE2EPreparationValidationError(
                "MISSION-03 E2E gates must use typed records"
            )
        if tuple(item.gate for item in self.gates) != _GATE_ORDER:
            raise Mission03OperationalE2EPreparationValidationError(
                "MISSION-03 E2E evidence must contain Gates #5-#13 exactly once"
            )
        if not isinstance(
            self.external_prerequisites,
            Mission03ExternalPrerequisiteState,
        ):
            raise Mission03OperationalE2EPreparationValidationError(
                "MISSION-03 E2E requires typed external prerequisite state"
            )

    @property
    def status(self) -> Mission03E2EPreparationStatus:
        if all(
            record.status is Mission03GatePreparationStatus.READY
            for record in self.gates
        ):
            return Mission03E2EPreparationStatus.READY
        return Mission03E2EPreparationStatus.BLOCKED

    @property
    def offline_preparation_ready(self) -> bool:
        return self.status is Mission03E2EPreparationStatus.READY

    @property
    def operational_e2e_attempt_permitted(self) -> bool:
        return (
            self.offline_preparation_ready
            and self.external_prerequisites.practice_account_provisioned
            and self.external_prerequisites.practice_token_provisioned
            and self.external_prerequisites.pre_e2e_operational_sequence_completed
        )

    @property
    def operationally_completed(self) -> bool:
        """Preparation evidence can never close Gate #13 by itself."""
        return False

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.provider_key,
            self.environment,
            self.status.value,
            tuple(record.logical_values() for record in self.gates),
            self.external_prerequisites.logical_values(),
            self.offline_preparation_ready,
            self.operational_e2e_attempt_permitted,
            self.operationally_completed,
        )

    def public_payload(self) -> dict[str, object]:
        return {
            "provider": self.provider_key,
            "environment": self.environment,
            "preparation_status": self.status.value,
            "offline_preparation_ready": self.offline_preparation_ready,
            "operational_e2e_attempt_permitted": self.operational_e2e_attempt_permitted,
            "operationally_completed": False,
            "practice_account_provisioned": (
                self.external_prerequisites.practice_account_provisioned
            ),
            "practice_token_provisioned": (
                self.external_prerequisites.practice_token_provisioned
            ),
            "completed_operational_gates": [
                gate.value
                for gate in self.external_prerequisites.completed_operational_gates
            ],
            "missing_operational_gates": [
                gate.value
                for gate in self.external_prerequisites.missing_operational_gates
            ],
            "blocker_codes": list(self.external_prerequisites.blocker_codes),
            "gates": [
                {
                    "gate": record.gate.value,
                    "status": record.status.value,
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


def build_mission03_operational_e2e_preparation_evidence(
    records: tuple[Mission03GatePreparationRecord, ...],
    *,
    external_prerequisites: Mission03ExternalPrerequisiteState,
) -> Result[
    Mission03OperationalE2EPreparationEvidence,
    Mission03OperationalE2EPreparationError,
]:
    """Build the exact Gate #5-#13 offline preparation matrix."""

    if not isinstance(records, tuple) or any(
        not isinstance(record, Mission03GatePreparationRecord)
        for record in records
    ):
        return Failure(
            Mission03OperationalE2EPreparationValidationError(
                "MISSION-03 E2E preparation requires typed record tuple"
            )
        )
    by_gate: dict[Mission03E2EGate, Mission03GatePreparationRecord] = {}
    for record in records:
        if record.gate in by_gate:
            return Failure(
                Mission03OperationalE2EPreparationValidationError(
                    "duplicate MISSION-03 E2E gate preparation is not allowed"
                )
            )
        by_gate[record.gate] = record
    if set(by_gate) != set(_GATE_ORDER):
        return Failure(
            Mission03OperationalE2EPreparationValidationError(
                "MISSION-03 E2E preparation matrix is incomplete"
            )
        )
    if not isinstance(
        external_prerequisites,
        Mission03ExternalPrerequisiteState,
    ):
        return Failure(
            Mission03OperationalE2EPreparationValidationError(
                "MISSION-03 E2E requires external prerequisite state"
            )
        )
    try:
        evidence = Mission03OperationalE2EPreparationEvidence(
            provider_key="oanda-v20",
            environment="demo",
            gates=tuple(by_gate[gate] for gate in _GATE_ORDER),
            external_prerequisites=external_prerequisites,
        )
    except Mission03OperationalE2EPreparationError as error:
        return Failure(error)
    return Success(evidence)
