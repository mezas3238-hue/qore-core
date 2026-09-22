"""Account-bound FundedNext operational controls for the approved VT-08 Forex line.

This module deliberately does not grant order authority.  It hardens the generic
MT5 boundary with account-discovered symbols, the frozen three-market Forex
universe, scoped kill switches, and an immutable binding between the provider
symbol approved by Risk and the provider symbol observed in the terminal.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta
from decimal import Decimal
from re import sub
from threading import RLock
from typing import Protocol

from qore.infrastructure.account_wide_risk import RiskAuthorization
from qore.infrastructure.execution_boundary import ExecutionSubmission
from qore.infrastructure.fundednext_execution_bridge import (
    build_fundednext_execution_submission,
)
from qore.infrastructure.fundednext_mt5 import (
    FundedNextMt5ExecutionGateway,
    FundedNextMt5OrderPlan,
    FundedNextMt5TransportBoundary,
    Mt5ExecutionBlockedError,
    Mt5ExecutionValidationError,
    Mt5SymbolSpecification,
)
from qore.infrastructure.fundednext_mt5_mutation_ledger import (
    FundedNextMt5MutationLedger,
)
from qore.infrastructure.fundednext_stellar_instant import (
    StellarInstantRuleVerification,
)
from qore.infrastructure.market_test_environment import MarketTestAccountIdentity
from qore.infrastructure.ports import ExternalRequestMetadata
from qore.infrastructure.pretrade_safety import ExecutionSafetySwitchSnapshot

VT08_FOREX_RETAINED_MARKETS = frozenset({"AUDJPY", "GBPUSD", "GBPJPY"})


class AccountBoundMt5Transport(FundedNextMt5TransportBoundary, Protocol):
    """MT5 transport that can enumerate the exact account terminal symbols."""

    def available_symbols(self) -> tuple[str, ...]: ...


def resolve_account_provider_symbol(
    qore_symbol: str,
    available_symbols: tuple[str, ...],
) -> str:
    """Resolve one retained Forex symbol from the terminal inventory.

    Exact account symbol identity wins. Common broker prefix/suffix decoration
    is accepted only when it produces exactly one candidate. Zero or ambiguous
    matches fail closed. Index aliases are intentionally not inferred here.
    """

    if qore_symbol not in VT08_FOREX_RETAINED_MARKETS:
        raise Mt5ExecutionBlockedError("qore-symbol-outside-approved-forex-universe")
    if not available_symbols:
        raise Mt5ExecutionBlockedError("mt5-symbol-catalog-empty")
    if any(not isinstance(item, str) or not item.strip() for item in available_symbols):
        raise Mt5ExecutionValidationError("mt5-symbol-catalog-invalid")
    exact = tuple(item for item in available_symbols if item == qore_symbol)
    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        raise Mt5ExecutionBlockedError("mt5-symbol-resolution-ambiguous")

    canonical = _symbol_key(qore_symbol)
    decorated = tuple(
        item
        for item in available_symbols
        if _decorated_forex_match(canonical, _symbol_key(item))
    )
    if len(decorated) == 1:
        return decorated[0]
    if not decorated:
        raise Mt5ExecutionBlockedError("mt5-symbol-resolution-missing")
    raise Mt5ExecutionBlockedError("mt5-symbol-resolution-ambiguous")


def build_account_bound_submission(
    authorization: RiskAuthorization,
    *,
    switch: ExecutionSafetySwitchSnapshot,
    authorized_at: datetime,
    submitted_at: datetime,
) -> ExecutionSubmission:
    """Bind the exact Risk-approved provider symbol into canonical execution."""

    submission = build_fundednext_execution_submission(
        authorization,
        switch=switch,
        authorized_at=authorized_at,
        submitted_at=submitted_at,
    )
    intent = submission.authorized_intent.intent
    metadata = intent.metadata
    attributes = dict(metadata.attributes)
    attributes["provider-symbol"] = authorization.provider_symbol
    bound_metadata = ExternalRequestMetadata(
        correlation_id=metadata.correlation_id,
        causation_id=metadata.causation_id,
        attributes=attributes,
    )
    bound_intent = replace(intent, metadata=bound_metadata)
    bound_authorized = replace(submission.authorized_intent, intent=bound_intent)
    return replace(submission, authorized_intent=bound_authorized)


class OperationalSafetyController:
    """Scoped new-order kill switches; recovery/cancel paths remain unaffected."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._account_enabled = True
        self._gateway_enabled = True
        self._disabled_traders: set[str] = set()
        self._disabled_markets: set[str] = set()

    def set_account_enabled(self, enabled: bool) -> None:
        with self._lock:
            self._account_enabled = bool(enabled)

    def set_gateway_enabled(self, enabled: bool) -> None:
        with self._lock:
            self._gateway_enabled = bool(enabled)

    def set_trader_enabled(self, trader_id: str, enabled: bool) -> None:
        if not trader_id:
            raise Mt5ExecutionValidationError("trader kill-switch identity is required")
        with self._lock:
            if enabled:
                self._disabled_traders.discard(trader_id)
            else:
                self._disabled_traders.add(trader_id)

    def set_market_enabled(self, qore_symbol: str, enabled: bool) -> None:
        if qore_symbol not in VT08_FOREX_RETAINED_MARKETS:
            raise Mt5ExecutionValidationError(
                "market kill-switch is outside approved Forex"
            )
        with self._lock:
            if enabled:
                self._disabled_markets.discard(qore_symbol)
            else:
                self._disabled_markets.add(qore_symbol)

    def assert_new_order_allowed(self, submission: ExecutionSubmission) -> None:
        intent = submission.authorized_intent.intent
        attrs = intent.metadata.attributes
        trader_id = attrs.get("trader-id")
        qore_symbol = intent.instrument.value
        with self._lock:
            if not self._account_enabled:
                raise Mt5ExecutionBlockedError("account-kill-switch-disabled")
            if not self._gateway_enabled:
                raise Mt5ExecutionBlockedError("gateway-kill-switch-disabled")
            if isinstance(trader_id, str) and trader_id in self._disabled_traders:
                raise Mt5ExecutionBlockedError("trader-kill-switch-disabled")
            if qore_symbol in self._disabled_markets:
                raise Mt5ExecutionBlockedError("market-kill-switch-disabled")


class FundedNextAccountBoundMt5Gateway(FundedNextMt5ExecutionGateway):
    """Operational MT5 gateway that trusts the account terminal, not alias docs."""

    def __init__(
        self,
        *,
        account: MarketTestAccountIdentity,
        transport: AccountBoundMt5Transport,
        mutation_ledger: FundedNextMt5MutationLedger,
        rule_verification: StellarInstantRuleVerification,
        safety: OperationalSafetyController,
        owner_submission_enabled: bool = False,
        max_spec_age: timedelta = timedelta(seconds=10),
        max_spread_points: Decimal | None = None,
    ) -> None:
        if not isinstance(safety, OperationalSafetyController):
            raise Mt5ExecutionValidationError("operational safety controller is required")
        super().__init__(
            account=account,
            transport=transport,
            mutation_ledger=mutation_ledger,
            rule_verification=rule_verification,
            owner_submission_enabled=owner_submission_enabled,
            max_spec_age=max_spec_age,
            max_spread_points=max_spread_points,
        )
        if not callable(getattr(transport, "available_symbols", None)):
            raise Mt5ExecutionValidationError("MT5 transport requires available_symbols")
        self._account_bound_transport = transport
        self._operational_safety = safety

    def read_symbol(self, qore_symbol: str, *, now: datetime) -> Mt5SymbolSpecification:
        _aware(now, "now")
        transport = self._account_bound_transport
        if not transport.connected():
            raise Mt5ExecutionBlockedError("mt5-disconnected")
        provider_symbol = resolve_account_provider_symbol(
            qore_symbol,
            transport.available_symbols(),
        )
        spec = transport.symbol_info(provider_symbol)
        if spec is None:
            raise Mt5ExecutionBlockedError("mt5-symbol-info-missing")
        if spec.provider_symbol != provider_symbol:
            raise Mt5ExecutionValidationError("mt5-symbol-account-binding-mismatch")
        _fresh(spec.observed_at, now, self._max_spec_age, "symbol-info")
        if not spec.trade_enabled or not spec.session_open:
            raise Mt5ExecutionBlockedError("mt5-symbol-not-tradable")
        if (
            self._max_spread_points is not None
            and spec.spread_points > self._max_spread_points
        ):
            raise Mt5ExecutionBlockedError("spread-outside-operational-containment")
        return spec

    def plan_submission(
        self,
        submission: ExecutionSubmission,
        *,
        now: datetime,
    ) -> FundedNextMt5OrderPlan:
        self._operational_safety.assert_new_order_allowed(submission)
        plan = super().plan_submission(submission, now=now)
        expected = submission.authorized_intent.intent.metadata.attributes.get(
            "provider-symbol"
        )
        if not isinstance(expected, str) or not expected:
            raise Mt5ExecutionBlockedError("risk-provider-symbol-binding-missing")
        if expected != plan.provider_symbol:
            raise Mt5ExecutionBlockedError("risk-provider-symbol-account-mismatch")
        return plan


def _symbol_key(value: str) -> str:
    return sub(r"[^A-Z0-9]", "", value.upper())


def _decorated_forex_match(canonical: str, candidate: str) -> bool:
    if candidate == canonical:
        return True
    return candidate.startswith(canonical) or candidate.endswith(canonical)


def _fresh(observed_at: datetime, now: datetime, max_age: timedelta, name: str) -> None:
    _aware(observed_at, f"{name}.observed_at")
    if observed_at > now:
        raise Mt5ExecutionValidationError(f"{name}-timestamp-from-future")
    if now - observed_at > max_age:
        raise Mt5ExecutionBlockedError(f"{name}-stale")


def _aware(value: datetime, name: str) -> None:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise Mt5ExecutionValidationError(f"{name} must be timezone-aware")
