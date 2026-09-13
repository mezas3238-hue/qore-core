"""Provider-scoped MT5 execution boundary for the FundedNext six-symbol pilot.

The adapter translates an already-issued RiskAuthorization.  It never discovers
strategy signals and never decides Risk.  Real submission remains separately
gated by runtime Owner authorization and current provider-rule verification.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from threading import RLock
from typing import Protocol

from qore.infrastructure.account_wide_risk import RiskAuthorization, RiskDecision
from qore.infrastructure.fundednext_stellar_instant import (
    StellarInstantRuleVerification,
    resolve_pilot_symbol,
)
from qore.kernel.errors import InfrastructureError


class Mt5ExecutionError(InfrastructureError):
    """MT5 execution precondition failed closed."""

    __slots__ = ()


class ExecutionMode(StrEnum):
    READ_ONLY = "read-only"
    SHADOW = "shadow"
    LIVE = "live"


class SubmissionStatus(StrEnum):
    NOT_SUBMITTED = "not-submitted"
    ACKNOWLEDGED = "acknowledged"
    REJECTED = "rejected"
    UNKNOWN_RECONCILE_REQUIRED = "unknown-reconcile-required"
    DUPLICATE_BLOCKED = "duplicate-blocked"


@dataclass(frozen=True, slots=True)
class Mt5AccountState:
    balance: Decimal
    equity: Decimal
    margin: Decimal
    free_margin: Decimal
    observed_at: datetime

    def __post_init__(self) -> None:
        for name, value in (
            ("balance", self.balance),
            ("equity", self.equity),
            ("margin", self.margin),
            ("free_margin", self.free_margin),
        ):
            _nonnegative(value, name)
        _aware(self.observed_at, "observed_at")


@dataclass(frozen=True, slots=True)
class Mt5SymbolSpecification:
    provider_symbol: str
    bid: Decimal
    ask: Decimal
    spread_points: Decimal
    digits: int
    point: Decimal
    contract_size: Decimal
    tick_size: Decimal
    tick_value: Decimal
    minimum_volume: Decimal
    maximum_volume: Decimal
    volume_step: Decimal
    minimum_stop_distance_points: Decimal
    freeze_level_points: Decimal
    margin_per_volume: Decimal
    trade_enabled: bool
    session_open: bool
    observed_at: datetime

    def __post_init__(self) -> None:
        if not self.provider_symbol:
            raise Mt5ExecutionError("provider_symbol must be non-empty")
        for name, value in (
            ("bid", self.bid),
            ("ask", self.ask),
            ("point", self.point),
            ("contract_size", self.contract_size),
            ("tick_size", self.tick_size),
            ("tick_value", self.tick_value),
            ("minimum_volume", self.minimum_volume),
            ("maximum_volume", self.maximum_volume),
            ("volume_step", self.volume_step),
            ("margin_per_volume", self.margin_per_volume),
        ):
            _positive(value, name)
        for name, value in (
            ("spread_points", self.spread_points),
            ("minimum_stop_distance_points", self.minimum_stop_distance_points),
            ("freeze_level_points", self.freeze_level_points),
        ):
            _nonnegative(value, name)
        if self.ask < self.bid:
            raise Mt5ExecutionError("ask cannot be below bid")
        if type(self.digits) is not int or self.digits < 0:
            raise Mt5ExecutionError("digits must be non-negative int")
        if self.maximum_volume < self.minimum_volume:
            raise Mt5ExecutionError("maximum_volume cannot be below minimum_volume")
        _aware(self.observed_at, "observed_at")


@dataclass(frozen=True, slots=True)
class Mt5OrderIntent:
    idempotency_key: str
    authorization_id: str
    authorization_fingerprint: str
    qore_symbol: str
    provider_symbol: str
    side: str
    volume: Decimal
    intended_entry: Decimal
    stop_loss: Decimal
    take_profit: Decimal
    entry_type: str
    created_at: datetime
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class ProviderSubmission:
    status: SubmissionStatus
    idempotency_key: str
    provider_order_id: str | None
    message: str

    def __post_init__(self) -> None:
        if type(self.status) is not SubmissionStatus:
            raise Mt5ExecutionError("submission status must be canonical")
        if not self.idempotency_key or not self.message:
            raise Mt5ExecutionError("submission requires identity and message")
        if self.status is SubmissionStatus.ACKNOWLEDGED and not self.provider_order_id:
            raise Mt5ExecutionError("acknowledged submission requires provider order id")


class Mt5Gateway(Protocol):
    """Secret-bearing concrete MT5 client injected outside repository configuration."""

    def connected(self) -> bool: ...

    def account_state(self) -> Mt5AccountState | None: ...

    def symbol_info(self, provider_symbol: str) -> Mt5SymbolSpecification | None: ...

    def submit(self, intent: Mt5OrderIntent) -> ProviderSubmission: ...

    def reconcile(self, idempotency_key: str) -> ProviderSubmission | None: ...


class FundedNextMt5Adapter:
    """Read/shadow/live MT5 boundary with idempotency and unknown-result suspension."""

    def __init__(
        self,
        gateway: Mt5Gateway,
        *,
        max_market_data_age: timedelta = timedelta(seconds=10),
        live_submission_enabled: bool = False,
    ) -> None:
        if max_market_data_age <= timedelta(0):
            raise Mt5ExecutionError("max_market_data_age must be positive")
        self._gateway = gateway
        self._max_market_data_age = max_market_data_age
        self._live_submission_enabled = live_submission_enabled
        self._lock = RLock()
        self._submitted: dict[str, ProviderSubmission] = {}
        self._unknown: set[str] = set()

    def read_account(self, *, now: datetime) -> Mt5AccountState:
        _aware(now, "now")
        if not self._gateway.connected():
            raise Mt5ExecutionError("mt5-disconnected")
        state = self._gateway.account_state()
        if state is None:
            raise Mt5ExecutionError("mt5-account-state-unavailable")
        _fresh(state.observed_at, now, self._max_market_data_age, "account-state")
        return state

    def read_symbol(self, qore_symbol: str, *, now: datetime) -> Mt5SymbolSpecification:
        _aware(now, "now")
        if not self._gateway.connected():
            raise Mt5ExecutionError("mt5-disconnected")
        provider_symbol = resolve_pilot_symbol(qore_symbol)
        spec = self._gateway.symbol_info(provider_symbol)
        if spec is None:
            raise Mt5ExecutionError("mt5-symbol-info-missing")
        if spec.provider_symbol != provider_symbol:
            raise Mt5ExecutionError("mt5-symbol-alias-mismatch")
        _fresh(spec.observed_at, now, self._max_market_data_age, "symbol-info")
        if not spec.trade_enabled or not spec.session_open:
            raise Mt5ExecutionError("mt5-symbol-not-tradable")
        return spec

    def build_intent(
        self,
        authorization: RiskAuthorization,
        *,
        now: datetime,
        max_spread_points: Decimal | None = None,
    ) -> Mt5OrderIntent:
        _aware(now, "now")
        if not isinstance(authorization, RiskAuthorization):
            raise Mt5ExecutionError("authorization must be RiskAuthorization")
        if authorization.decision is RiskDecision.REJECT:
            raise Mt5ExecutionError("rejected RiskAuthorization cannot become order")
        if now > authorization.expires_at:
            raise Mt5ExecutionError("risk-authorization-expired")
        spec = self.read_symbol(authorization.qore_symbol, now=now)
        expected_symbol = resolve_pilot_symbol(authorization.qore_symbol)
        if authorization.provider_symbol != expected_symbol:
            raise Mt5ExecutionError("authorization-provider-symbol-mismatch")
        self._validate_volume(authorization.authorized_volume, spec)
        self._validate_geometry(authorization, spec)
        if max_spread_points is not None:
            _nonnegative(max_spread_points, "max_spread_points")
            if spec.spread_points > max_spread_points:
                raise Mt5ExecutionError("spread-outside-operational-containment")
        key = f"mt5:{authorization.authorization_fingerprint}"
        return Mt5OrderIntent(
            idempotency_key=key,
            authorization_id=authorization.authorization_id,
            authorization_fingerprint=authorization.authorization_fingerprint,
            qore_symbol=authorization.qore_symbol,
            provider_symbol=authorization.provider_symbol,
            side=authorization.side,
            volume=authorization.authorized_volume,
            intended_entry=authorization.intended_entry,
            stop_loss=authorization.stop_loss,
            take_profit=authorization.take_profit,
            entry_type=authorization.entry_type,
            created_at=now,
            expires_at=authorization.expires_at,
        )

    def execute(
        self,
        intent: Mt5OrderIntent,
        *,
        mode: ExecutionMode,
        rule_verification: StellarInstantRuleVerification,
        now: datetime,
    ) -> ProviderSubmission:
        _aware(now, "now")
        if type(mode) is not ExecutionMode:
            raise Mt5ExecutionError("mode must be ExecutionMode")
        if now > intent.expires_at:
            raise Mt5ExecutionError("order-intent-expired")
        with self._lock:
            previous = self._submitted.get(intent.idempotency_key)
            if previous is not None:
                return ProviderSubmission(
                    status=SubmissionStatus.DUPLICATE_BLOCKED,
                    idempotency_key=intent.idempotency_key,
                    provider_order_id=previous.provider_order_id,
                    message="idempotency-key-already-used",
                )
            if self._unknown:
                raise Mt5ExecutionError("unresolved-provider-state-suspends-new-orders")
            if mode in {ExecutionMode.READ_ONLY, ExecutionMode.SHADOW}:
                result = ProviderSubmission(
                    status=SubmissionStatus.NOT_SUBMITTED,
                    idempotency_key=intent.idempotency_key,
                    provider_order_id=None,
                    message=f"{mode.value}-submission-suppressed",
                )
                self._submitted[intent.idempotency_key] = result
                return result
            if not self._live_submission_enabled:
                raise Mt5ExecutionError("owner-order-submission-authorization-disabled")
            if not rule_verification.automated_mt5_allowed(now):
                raise Mt5ExecutionError("fundednext-automation-rules-not-current-and-verified")
            if not self._gateway.connected():
                raise Mt5ExecutionError("mt5-disconnected")
            result = self._gateway.submit(intent)
            if result.idempotency_key != intent.idempotency_key:
                raise Mt5ExecutionError("provider-ack-idempotency-mismatch")
            self._submitted[intent.idempotency_key] = result
            if result.status is SubmissionStatus.UNKNOWN_RECONCILE_REQUIRED:
                self._unknown.add(intent.idempotency_key)
            return result

    def reconcile_unknown(self, idempotency_key: str) -> ProviderSubmission:
        with self._lock:
            if idempotency_key not in self._unknown:
                raise Mt5ExecutionError("idempotency key is not awaiting reconciliation")
            result = self._gateway.reconcile(idempotency_key)
            if result is None or result.status is SubmissionStatus.UNKNOWN_RECONCILE_REQUIRED:
                raise Mt5ExecutionError("provider-result-still-unknown")
            if result.idempotency_key != idempotency_key:
                raise Mt5ExecutionError("reconciliation-idempotency-mismatch")
            self._submitted[idempotency_key] = result
            self._unknown.remove(idempotency_key)
            return result

    @property
    def reconciliation_required(self) -> bool:
        with self._lock:
            return bool(self._unknown)

    @staticmethod
    def _validate_volume(volume: Decimal, spec: Mt5SymbolSpecification) -> None:
        _positive(volume, "authorized_volume")
        if not spec.minimum_volume <= volume <= spec.maximum_volume:
            raise Mt5ExecutionError("authorized-volume-outside-broker-range")
        units = volume / spec.volume_step
        if units != units.to_integral_value():
            raise Mt5ExecutionError("authorized-volume-not-on-broker-step")

    @staticmethod
    def _validate_geometry(
        authorization: RiskAuthorization,
        spec: Mt5SymbolSpecification,
    ) -> None:
        entry = authorization.intended_entry
        stop = authorization.stop_loss
        target = authorization.take_profit
        if authorization.side == "long":
            if not stop < entry < target:
                raise Mt5ExecutionError("invalid-long-order-geometry")
        elif authorization.side == "short":
            if not target < entry < stop:
                raise Mt5ExecutionError("invalid-short-order-geometry")
        else:
            raise Mt5ExecutionError("unsupported-order-side")
        minimum_distance = spec.minimum_stop_distance_points * spec.point
        if abs(entry - stop) < minimum_distance:
            raise Mt5ExecutionError("stop-inside-broker-minimum-distance")
        if abs(target - entry) < minimum_distance:
            raise Mt5ExecutionError("target-inside-broker-minimum-distance")


def _fresh(observed_at: datetime, now: datetime, max_age: timedelta, name: str) -> None:
    _aware(observed_at, f"{name}.observed_at")
    if observed_at > now:
        raise Mt5ExecutionError(f"{name}-timestamp-from-future")
    if now - observed_at > max_age:
        raise Mt5ExecutionError(f"{name}-stale")


def _aware(value: datetime, name: str) -> None:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise Mt5ExecutionError(f"{name} must be timezone-aware")


def _positive(value: Decimal, name: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite() or value <= 0:
        raise Mt5ExecutionError(f"{name} must be positive finite Decimal")


def _nonnegative(value: Decimal, name: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
        raise Mt5ExecutionError(f"{name} must be non-negative finite Decimal")
