from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from re import fullmatch
from uuid import UUID

from qore.infrastructure.order_intent import OrderIntent, OrderIntentId
from qore.infrastructure.ports import ExternalPortError
from qore.kernel.result import Failure, Result, Success

_SENSITIVE_TEXT_PARTS = (
    "authorization:",
    "bearer ",
    "client_secret=",
    "password=",
    "secret=",
    "token=",
)


class PreTradeSafetyError(ExternalPortError):
    """Base error for controlled pre-trade safety contracts."""

    __slots__ = ()


class PreTradeSafetyValidationError(PreTradeSafetyError):
    """Violation of a pre-trade safety invariant."""

    __slots__ = ()


class PreTradeSafetyBlockedError(PreTradeSafetyError):
    """Typed fail-closed result when authorization is not executable."""

    __slots__ = ()


class PreTradeDecision(StrEnum):
    APPROVED = "approved"
    BLOCKED = "blocked"


class ExecutionSwitchState(StrEnum):
    BLOCKED = "blocked"
    ENABLED = "enabled"


@dataclass(frozen=True, slots=True)
class PreTradeAuthorizationId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise PreTradeSafetyValidationError(
                "pre-trade authorization id must be UUID"
            )

    def logical_values(self) -> tuple[UUID, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class PreTradePolicyId:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or fullmatch(
            r"[a-z][a-z0-9._-]*", self.value
        ) is None:
            raise PreTradeSafetyValidationError(
                "pre-trade policy id must use canonical lowercase syntax"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


def _validate_datetime(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise PreTradeSafetyValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise PreTradeSafetyValidationError(f"{field_name} must be timezone-aware")


def _validate_reason(value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise PreTradeSafetyValidationError(
            "pre-trade safety reason must be a non-empty string"
        )
    normalized = value.lower()
    if any(part in normalized for part in _SENSITIVE_TEXT_PARTS):
        raise PreTradeSafetyValidationError(
            "pre-trade safety reason must not contain sensitive material"
        )


@dataclass(frozen=True, slots=True)
class PreTradeAuthorization:
    authorization_id: PreTradeAuthorizationId
    policy_id: PreTradePolicyId
    intent_id: OrderIntentId
    decision: PreTradeDecision
    evaluated_at: datetime
    expires_at: datetime
    reason: str

    def __post_init__(self) -> None:
        if not isinstance(self.authorization_id, PreTradeAuthorizationId):
            raise PreTradeSafetyValidationError(
                "authorization_id must be PreTradeAuthorizationId"
            )
        if not isinstance(self.policy_id, PreTradePolicyId):
            raise PreTradeSafetyValidationError("policy_id must be PreTradePolicyId")
        if not isinstance(self.intent_id, OrderIntentId):
            raise PreTradeSafetyValidationError("intent_id must be OrderIntentId")
        if not isinstance(self.decision, PreTradeDecision):
            raise PreTradeSafetyValidationError(
                "decision must be PreTradeDecision"
            )
        _validate_datetime(self.evaluated_at, field_name="evaluated_at")
        _validate_datetime(self.expires_at, field_name="expires_at")
        if self.expires_at <= self.evaluated_at:
            raise PreTradeSafetyValidationError(
                "pre-trade authorization expires_at must be after evaluated_at"
            )
        _validate_reason(self.reason)

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.authorization_id.logical_values(),
            self.policy_id.logical_values(),
            self.intent_id.logical_values(),
            self.decision.value,
            self.evaluated_at.isoformat(),
            self.expires_at.isoformat(),
            self.reason,
        )


@dataclass(frozen=True, slots=True)
class ExecutionSafetySwitchSnapshot:
    """Global execution switch. BLOCKED is the fail-closed state."""

    state: ExecutionSwitchState
    observed_at: datetime
    reason: str

    def __post_init__(self) -> None:
        if not isinstance(self.state, ExecutionSwitchState):
            raise PreTradeSafetyValidationError(
                "execution switch state must be ExecutionSwitchState"
            )
        _validate_datetime(self.observed_at, field_name="observed_at")
        _validate_reason(self.reason)

    @property
    def allows_execution(self) -> bool:
        return self.state is ExecutionSwitchState.ENABLED

    def logical_values(self) -> tuple[object, ...]:
        return (self.state.value, self.observed_at.isoformat(), self.reason)


@dataclass(frozen=True, slots=True)
class AuthorizedOrderIntent:
    """Order intent paired with valid, unexpired authorization evidence."""

    intent: OrderIntent
    authorization: PreTradeAuthorization
    switch: ExecutionSafetySwitchSnapshot
    authorized_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.intent, OrderIntent):
            raise PreTradeSafetyValidationError(
                "authorized order intent requires OrderIntent"
            )
        if not isinstance(self.authorization, PreTradeAuthorization):
            raise PreTradeSafetyValidationError(
                "authorized order intent requires PreTradeAuthorization"
            )
        if not isinstance(self.switch, ExecutionSafetySwitchSnapshot):
            raise PreTradeSafetyValidationError(
                "authorized order intent requires ExecutionSafetySwitchSnapshot"
            )
        _validate_datetime(self.authorized_at, field_name="authorized_at")

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.intent.logical_values(),
            self.authorization.logical_values(),
            self.switch.logical_values(),
            self.authorized_at.isoformat(),
        )


def authorize_order_intent(
    intent: OrderIntent,
    authorization: PreTradeAuthorization,
    switch: ExecutionSafetySwitchSnapshot,
    *,
    authorized_at: datetime,
) -> Result[AuthorizedOrderIntent, PreTradeSafetyError]:
    """Fail closed unless intent, authorization, expiry and kill switch all permit."""
    if not isinstance(intent, OrderIntent):
        return Failure(PreTradeSafetyValidationError("intent must be OrderIntent"))
    if not isinstance(authorization, PreTradeAuthorization):
        return Failure(
            PreTradeSafetyValidationError(
                "authorization must be PreTradeAuthorization"
            )
        )
    if not isinstance(switch, ExecutionSafetySwitchSnapshot):
        return Failure(
            PreTradeSafetyValidationError(
                "switch must be ExecutionSafetySwitchSnapshot"
            )
        )
    try:
        _validate_datetime(authorized_at, field_name="authorized_at")
    except PreTradeSafetyError as error:
        return Failure(error)
    if authorization.intent_id != intent.intent_id:
        return Failure(
            PreTradeSafetyBlockedError(
                "pre-trade authorization intent identity does not match"
            )
        )
    if authorization.evaluated_at < intent.created_at:
        return Failure(
            PreTradeSafetyBlockedError(
                "pre-trade authorization predates the order intent"
            )
        )
    if authorization.decision is not PreTradeDecision.APPROVED:
        return Failure(
            PreTradeSafetyBlockedError("pre-trade authorization is blocked")
        )
    if authorized_at > authorization.expires_at:
        return Failure(
            PreTradeSafetyBlockedError("pre-trade authorization is expired")
        )
    if switch.observed_at > authorized_at:
        return Failure(
            PreTradeSafetyBlockedError(
                "execution switch snapshot is newer than authorization instant"
            )
        )
    if not switch.allows_execution:
        return Failure(
            PreTradeSafetyBlockedError("global execution switch is blocked")
        )
    try:
        return Success(
            AuthorizedOrderIntent(
                intent=intent,
                authorization=authorization,
                switch=switch,
                authorized_at=authorized_at,
            )
        )
    except PreTradeSafetyError as error:
        return Failure(error)
