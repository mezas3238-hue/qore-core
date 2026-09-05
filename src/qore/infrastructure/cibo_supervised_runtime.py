from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from re import fullmatch

from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
    MarketTestEnvironmentAuthorization,
)
from qore.infrastructure.order_intent import OrderIntent
from qore.infrastructure.ports import ExternalPortError, ExternalRequestMetadata
from qore.infrastructure.real_market_decision_runtime import (
    RealMarketDecisionBoundary,
    RealMarketDecisionContext,
)
from qore.kernel.result import Failure, Result


class CiboSupervisedRuntimeError(ExternalPortError):
    """Base error for the MISSION-02 supervised CIBO boundary."""

    __slots__ = ()


class CiboSupervisedRuntimeValidationError(CiboSupervisedRuntimeError):
    """Violation of a CIBO supervision invariant."""

    __slots__ = ()


class CiboSupervisionBlockedError(CiboSupervisedRuntimeError):
    """Fail-closed result when CIBO lacks valid human supervision."""

    __slots__ = ()


class CiboSupervisionDecision(StrEnum):
    APPROVED = "approved"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class CiboSupervisorId:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or fullmatch(
            r"[a-z][a-z0-9._-]*", self.value
        ) is None:
            raise CiboSupervisedRuntimeValidationError(
                "CIBO supervisor id must use canonical lowercase syntax"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class CiboSupervisionAuthorization:
    """Explicit, expiring authorization to let CIBO decide in TEST/DEMO only."""

    supervisor_id: CiboSupervisorId
    environment_authorization: MarketTestEnvironmentAuthorization
    decision: CiboSupervisionDecision
    authorized_at: datetime
    expires_at: datetime
    reason: str

    def __post_init__(self) -> None:
        if not isinstance(self.supervisor_id, CiboSupervisorId):
            raise CiboSupervisedRuntimeValidationError(
                "CIBO supervision requires CiboSupervisorId"
            )
        if not isinstance(
            self.environment_authorization,
            MarketTestEnvironmentAuthorization,
        ):
            raise CiboSupervisedRuntimeValidationError(
                "CIBO supervision requires market-test environment authorization"
            )
        if self.environment_authorization.account.environment not in {
            MarketRuntimeEnvironment.DEMO,
            MarketRuntimeEnvironment.TEST,
        }:
            raise CiboSupervisedRuntimeValidationError(
                "CIBO supervision is valid only for TEST or DEMO"
            )
        if not isinstance(self.decision, CiboSupervisionDecision):
            raise CiboSupervisedRuntimeValidationError(
                "CIBO supervision decision must be explicit"
            )
        for field_name, value in (
            ("authorized_at", self.authorized_at),
            ("expires_at", self.expires_at),
        ):
            if type(value) is not datetime:
                raise CiboSupervisedRuntimeValidationError(
                    f"{field_name} must be a datetime"
                )
            if value.tzinfo is None or value.utcoffset() is None:
                raise CiboSupervisedRuntimeValidationError(
                    f"{field_name} must be timezone-aware"
                )
        if self.expires_at <= self.authorized_at:
            raise CiboSupervisedRuntimeValidationError(
                "CIBO supervision expiry must be after authorization"
            )
        if self.authorized_at < self.environment_authorization.authorized_at:
            raise CiboSupervisedRuntimeValidationError(
                "CIBO supervision must not predate environment authorization"
            )
        if not isinstance(self.reason, str) or not self.reason.strip():
            raise CiboSupervisedRuntimeValidationError(
                "CIBO supervision reason must be non-empty"
            )
        lowered = self.reason.lower()
        if any(part in lowered for part in ("password=", "secret=", "token=", "bearer ")):
            raise CiboSupervisedRuntimeValidationError(
                "CIBO supervision reason must not contain secret material"
            )

    @property
    def allows_decision(self) -> bool:
        return self.decision is CiboSupervisionDecision.APPROVED

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.supervisor_id.logical_values(),
            self.environment_authorization.logical_values(),
            self.decision.value,
            self.authorized_at.isoformat(),
            self.expires_at.isoformat(),
            self.reason,
        )


@dataclass(frozen=True, slots=True)
class SupervisedCiboDecisionBoundary(RealMarketDecisionBoundary):
    """Permit CIBO decisions only under explicit, unexpired TEST/DEMO supervision."""

    delegate: RealMarketDecisionBoundary
    supervision: CiboSupervisionAuthorization

    def __post_init__(self) -> None:
        if not isinstance(self.supervision, CiboSupervisionAuthorization):
            raise CiboSupervisedRuntimeValidationError(
                "supervised CIBO boundary requires CiboSupervisionAuthorization"
            )
        CiboSupervisionAuthorization.__post_init__(self.supervision)

    def decide(
        self,
        context: RealMarketDecisionContext,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[OrderIntent | None, ExternalPortError]:
        if not isinstance(context, RealMarketDecisionContext):
            return Failure(
                CiboSupervisedRuntimeValidationError(
                    "CIBO decision requires RealMarketDecisionContext"
                )
            )
        if not isinstance(metadata, ExternalRequestMetadata):
            return Failure(
                CiboSupervisedRuntimeValidationError(
                    "CIBO decision requires explicit metadata"
                )
            )
        try:
            CiboSupervisionAuthorization.__post_init__(self.supervision)
            RealMarketDecisionContext.__post_init__(context)
        except ExternalPortError as error:
            return Failure(error)
        if not self.supervision.allows_decision:
            return Failure(
                CiboSupervisionBlockedError("CIBO supervision is blocked")
            )
        if context.decided_at < self.supervision.authorized_at:
            return Failure(
                CiboSupervisionBlockedError(
                    "CIBO decision must not predate supervision authorization"
                )
            )
        if context.decided_at > self.supervision.expires_at:
            return Failure(
                CiboSupervisionBlockedError("CIBO supervision authorization expired")
            )
        return self.delegate.decide(context, metadata=metadata)
