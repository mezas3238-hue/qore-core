from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from re import fullmatch
from typing import cast

from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
    MarketTestAccountIdentity,
)
from qore.infrastructure.oanda_practice_configuration import (
    OandaPracticeCapability,
    OandaPracticeRuntimeConfiguration,
)
from qore.infrastructure.ports import ExternalPortError
from qore.infrastructure.transport import (
    ExternalTransportMethod,
    ExternalTransportRequest,
    ExternalTransportResponse,
)
from qore.kernel.result import Failure, Result, Success


class OandaPracticeAccountActivationError(ExternalPortError):
    """Base error for OANDA Practice demo-account activation preparation."""

    __slots__ = ()


class OandaPracticeAccountActivationValidationError(
    OandaPracticeAccountActivationError
):
    """An OANDA Practice account response violates activation invariants."""

    __slots__ = ()


def _json_object(payload: bytes) -> Result[Mapping[str, object], ExternalPortError]:
    try:
        decoded: object = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return Failure(
            OandaPracticeAccountActivationValidationError(
                "OANDA account response must be a UTF-8 JSON object"
            )
        )
    if not isinstance(decoded, dict) or any(not isinstance(key, str) for key in decoded):
        return Failure(
            OandaPracticeAccountActivationValidationError(
                "OANDA account response root must be a string-keyed object"
            )
        )
    return Success(cast(dict[str, object], decoded))


def _timestamp(value: object, *, field_name: str) -> Result[datetime, ExternalPortError]:
    if not isinstance(value, str) or not value:
        return Failure(
            OandaPracticeAccountActivationValidationError(
                f"OANDA {field_name} must be a non-empty RFC3339 string"
            )
        )
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return Failure(
            OandaPracticeAccountActivationValidationError(
                f"OANDA {field_name} must be parseable RFC3339"
            )
        )
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return Failure(
            OandaPracticeAccountActivationValidationError(
                f"OANDA {field_name} must be timezone-aware"
            )
        )
    return Success(parsed)


def _transaction_ref(value: object, *, field_name: str) -> Result[str, ExternalPortError]:
    if not isinstance(value, str) or fullmatch(r"[0-9]+", value) is None:
        return Failure(
            OandaPracticeAccountActivationValidationError(
                f"OANDA {field_name} must be a numeric transaction reference"
            )
        )
    return Success(value)


def _nonnegative_count(value: object, *, field_name: str) -> Result[int, ExternalPortError]:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        return Failure(
            OandaPracticeAccountActivationValidationError(
                f"OANDA {field_name} must be a non-negative int"
            )
        )
    return Success(value)


def _positive_decimal(value: object, *, field_name: str) -> Result[str, ExternalPortError]:
    if not isinstance(value, str) or not value:
        return Failure(
            OandaPracticeAccountActivationValidationError(
                f"OANDA {field_name} must be a decimal string"
            )
        )
    try:
        parsed = Decimal(value)
    except InvalidOperation:
        return Failure(
            OandaPracticeAccountActivationValidationError(
                f"OANDA {field_name} must be a decimal string"
            )
        )
    if not parsed.is_finite() or parsed <= 0:
        return Failure(
            OandaPracticeAccountActivationValidationError(
                f"OANDA {field_name} must be positive and finite"
            )
        )
    return Success(value)


def _account_fingerprint(account_ref: str) -> str:
    digest = hashlib.sha256(account_ref.encode("utf-8")).hexdigest()
    return f"sha256:{digest[:24]}"


@dataclass(frozen=True, slots=True)
class OandaPracticeAccountSummaryRequestFactory:
    """Build the exact read-only account-summary request for one Practice account."""

    configuration: OandaPracticeRuntimeConfiguration

    def __post_init__(self) -> None:
        if not isinstance(self.configuration, OandaPracticeRuntimeConfiguration):
            raise OandaPracticeAccountActivationValidationError(
                "account request factory requires OandaPracticeRuntimeConfiguration"
            )
        if OandaPracticeCapability.ACCOUNT not in self.configuration.capabilities:
            raise OandaPracticeAccountActivationValidationError(
                "OANDA Practice configuration must authorize account capability"
            )

    def build(self) -> ExternalTransportRequest:
        account_ref = self.configuration.account.account_ref
        return ExternalTransportRequest(
            endpoint=self.configuration.rest_endpoint,
            method=ExternalTransportMethod.GET,
            path=f"/v3/accounts/{account_ref}/summary",
            timeout=self.configuration.rest_timeout,
            headers={
                "accept": "application/json",
                "accept-datetime-format": "RFC3339",
            },
        )


@dataclass(frozen=True, slots=True)
class OandaPracticeAccountSummarySnapshot:
    """Sanitized account identity/state decoded from one Practice summary response."""

    account: MarketTestAccountIdentity
    currency: str
    created_at: datetime
    observed_at: datetime
    hedging_enabled: bool
    pending_order_count: int
    open_trade_count: int
    open_position_count: int
    margin_rate: str
    last_transaction_ref: str

    def __post_init__(self) -> None:
        if not isinstance(self.account, MarketTestAccountIdentity):
            raise OandaPracticeAccountActivationValidationError(
                "account summary requires MarketTestAccountIdentity"
            )
        if self.account.provider_key != "oanda-v20":
            raise OandaPracticeAccountActivationValidationError(
                "account summary provider must be oanda-v20"
            )
        if self.account.environment is not MarketRuntimeEnvironment.DEMO:
            raise OandaPracticeAccountActivationValidationError(
                "account summary environment must be demo"
            )
        if not isinstance(self.currency, str) or fullmatch(r"[A-Z]{3}", self.currency) is None:
            raise OandaPracticeAccountActivationValidationError(
                "account summary currency must use ISO-like uppercase syntax"
            )
        for value, field_name in (
            (self.created_at, "created_at"),
            (self.observed_at, "observed_at"),
        ):
            if not isinstance(value, datetime):
                raise OandaPracticeAccountActivationValidationError(
                    f"account summary {field_name} must be a datetime"
                )
            if value.tzinfo is None or value.utcoffset() is None:
                raise OandaPracticeAccountActivationValidationError(
                    f"account summary {field_name} must be timezone-aware"
                )
        if self.observed_at < self.created_at:
            raise OandaPracticeAccountActivationValidationError(
                "account summary observation must not predate account creation"
            )
        if type(self.hedging_enabled) is not bool:
            raise OandaPracticeAccountActivationValidationError(
                "account summary hedging_enabled must be bool"
            )
        for value, field_name in (
            (self.pending_order_count, "pending_order_count"),
            (self.open_trade_count, "open_trade_count"),
            (self.open_position_count, "open_position_count"),
        ):
            if type(value) is not int or value < 0:
                raise OandaPracticeAccountActivationValidationError(
                    f"account summary {field_name} must be a non-negative int"
                )
        margin = _positive_decimal(self.margin_rate, field_name="marginRate")
        if isinstance(margin, Failure):
            raise OandaPracticeAccountActivationValidationError(
                "account summary margin_rate must be a positive finite decimal string"
            ) from margin.error
        transaction = _transaction_ref(
            self.last_transaction_ref,
            field_name="lastTransactionID",
        )
        if isinstance(transaction, Failure):
            raise OandaPracticeAccountActivationValidationError(
                "account summary last_transaction_ref must be numeric"
            ) from transaction.error

    @property
    def account_fingerprint(self) -> str:
        return _account_fingerprint(self.account.account_ref)

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.account.logical_values(),
            self.currency,
            self.created_at.isoformat(),
            self.observed_at.isoformat(),
            self.hedging_enabled,
            self.pending_order_count,
            self.open_trade_count,
            self.open_position_count,
            self.margin_rate,
            self.last_transaction_ref,
        )

    def sanitized_values(self) -> tuple[object, ...]:
        """Return stable evidence values without exposing the external account reference."""
        return (
            self.account.provider_key,
            self.account.environment.value,
            self.account_fingerprint,
            self.currency,
            self.created_at.isoformat(),
            self.observed_at.isoformat(),
            self.hedging_enabled,
            self.pending_order_count,
            self.open_trade_count,
            self.open_position_count,
            self.margin_rate,
            self.last_transaction_ref,
        )


class OandaPracticeAccountSummaryDecoder:
    """Decode one Practice account-summary response and bind it to exact configuration."""

    __slots__ = ()

    def decode(
        self,
        response: ExternalTransportResponse,
        *,
        configuration: OandaPracticeRuntimeConfiguration,
    ) -> Result[OandaPracticeAccountSummarySnapshot, ExternalPortError]:
        if not isinstance(response, ExternalTransportResponse):
            return Failure(
                OandaPracticeAccountActivationValidationError(
                    "account decoder requires ExternalTransportResponse"
                )
            )
        if not isinstance(configuration, OandaPracticeRuntimeConfiguration):
            return Failure(
                OandaPracticeAccountActivationValidationError(
                    "account decoder requires OandaPracticeRuntimeConfiguration"
                )
            )
        if not response.is_success:
            return Failure(
                OandaPracticeAccountActivationValidationError(
                    "OANDA account summary request did not return success"
                )
            )
        root = _json_object(response.payload)
        if isinstance(root, Failure):
            return root
        account_value = root.value.get("account")
        if not isinstance(account_value, dict) or any(
            not isinstance(key, str) for key in account_value
        ):
            return Failure(
                OandaPracticeAccountActivationValidationError(
                    "OANDA account summary account must be a string-keyed object"
                )
            )
        account = cast(dict[str, object], account_value)
        if account.get("id") != configuration.account.account_ref:
            return Failure(
                OandaPracticeAccountActivationValidationError(
                    "OANDA account summary identity must match configured account"
                )
            )
        currency = account.get("currency")
        if not isinstance(currency, str) or fullmatch(r"[A-Z]{3}", currency) is None:
            return Failure(
                OandaPracticeAccountActivationValidationError(
                    "OANDA account currency must use uppercase three-letter syntax"
                )
            )
        created_at = _timestamp(account.get("createdTime"), field_name="createdTime")
        if isinstance(created_at, Failure):
            return created_at
        hedging_enabled = account.get("hedgingEnabled")
        if not isinstance(hedging_enabled, bool):
            return Failure(
                OandaPracticeAccountActivationValidationError(
                    "OANDA hedgingEnabled must be bool"
                )
            )
        pending_order_count = _nonnegative_count(
            account.get("pendingOrderCount"),
            field_name="pendingOrderCount",
        )
        if isinstance(pending_order_count, Failure):
            return pending_order_count
        open_trade_count = _nonnegative_count(
            account.get("openTradeCount"),
            field_name="openTradeCount",
        )
        if isinstance(open_trade_count, Failure):
            return open_trade_count
        open_position_count = _nonnegative_count(
            account.get("openPositionCount"),
            field_name="openPositionCount",
        )
        if isinstance(open_position_count, Failure):
            return open_position_count
        margin_rate = _positive_decimal(account.get("marginRate"), field_name="marginRate")
        if isinstance(margin_rate, Failure):
            return margin_rate
        root_transaction = _transaction_ref(
            root.value.get("lastTransactionID"),
            field_name="root.lastTransactionID",
        )
        if isinstance(root_transaction, Failure):
            return root_transaction
        account_transaction = _transaction_ref(
            account.get("lastTransactionID"),
            field_name="account.lastTransactionID",
        )
        if isinstance(account_transaction, Failure):
            return account_transaction
        if root_transaction.value != account_transaction.value:
            return Failure(
                OandaPracticeAccountActivationValidationError(
                    "OANDA account transaction references must match"
                )
            )
        try:
            snapshot = OandaPracticeAccountSummarySnapshot(
                account=configuration.account,
                currency=currency,
                created_at=created_at.value,
                observed_at=response.received_at,
                hedging_enabled=hedging_enabled,
                pending_order_count=pending_order_count.value,
                open_trade_count=open_trade_count.value,
                open_position_count=open_position_count.value,
                margin_rate=margin_rate.value,
                last_transaction_ref=root_transaction.value,
            )
        except OandaPracticeAccountActivationError as error:
            return Failure(error)
        return Success(snapshot)
