"""L3 DEMO Risk/Policy budget authority (fail-closed, deterministic).

This module owns the concrete budget evaluation engine behind the
:class:`qore.infrastructure.risk_authority.RiskBudgetEvaluator` protocol. It
creates no Production or LIVE authority and no provider credentials.

Everything here is deterministic and fail-closed:

* no ambient clock (every timestamp is caller-supplied and timezone-aware);
* no ambient UUID generation (every identity is caller-supplied);
* exact runtime types (``type(x) is int`` rejects ``bool``);
* exact ``Decimal`` semantics for money/quantity arithmetic (never ``float``);
* missing, stale, ambiguous or mismatched state never admits new risk.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal
from uuid import UUID

from qore.infrastructure.order_intent import ExecutionInstrument, OrderQuantity
from qore.infrastructure.proprietary_accounts import MoneyAmount
from qore.infrastructure.risk_authority import (
    RiskBudgetEvaluation,
    RiskError,
    RiskEvidence,
    RiskFingerprint,
    RiskPolicyId,
    RiskPolicySnapshot,
    RiskPolicyVersion,
    RiskReason,
    RiskReasonCode,
    RiskValidationError,
)
from qore.kernel.result import Failure, Result, Success

__all__ = [
    "RiskBudgetError",
    "RiskBudgetValidationError",
    "CorrelationGroup",
    "RiskBudgetPolicy",
    "ExternalAccountRiskLimits",
    "compute_effective_limit_bps",
    "apply_safety_buffer_bps",
    "RiskBudgetEngine",
]


class RiskBudgetError(RiskError):
    """Base error for the L3 budget authority."""

    __slots__ = ()


class RiskBudgetValidationError(RiskBudgetError):
    """Violation of a budget-authority invariant."""

    __slots__ = ()


def _validate_uuid(value: object, *, field_name: str) -> None:
    if not isinstance(value, UUID):
        raise RiskBudgetValidationError(f"{field_name} must be a UUID")


def _validate_bps(value: object, *, field_name: str, minimum: int) -> None:
    if type(value) is not int:
        raise RiskBudgetValidationError(f"{field_name} must be an integer")
    if not minimum <= value <= 10_000:
        raise RiskBudgetValidationError(
            f"{field_name} must be between {minimum} and 10000"
        )


def _validate_bool(value: object, *, field_name: str) -> None:
    if type(value) is not bool:
        raise RiskBudgetValidationError(f"{field_name} must be a bool")


@dataclass(frozen=True, slots=True)
class CorrelationGroup:
    """One correlation group bounding aggregate exposure across instruments."""

    group_id: UUID
    instruments: tuple[ExecutionInstrument, ...]
    limit_bps: int

    def __post_init__(self) -> None:
        _validate_uuid(self.group_id, field_name="correlation group id")
        if not isinstance(self.instruments, tuple):
            raise RiskBudgetValidationError(
                "correlation group instruments must be a tuple"
            )
        if not self.instruments:
            raise RiskBudgetValidationError(
                "correlation group instruments must not be empty"
            )
        if any(not isinstance(item, ExecutionInstrument) for item in self.instruments):
            raise RiskBudgetValidationError(
                "correlation group instruments must contain only ExecutionInstrument values"
            )
        if len(set(self.instruments)) != len(self.instruments):
            raise RiskBudgetValidationError("correlation group instruments must be unique")
        _validate_bps(self.limit_bps, field_name="correlation group limit_bps", minimum=1)


@dataclass(frozen=True, slots=True)
class RiskBudgetPolicy:
    """Immutable internal budget configuration bound to one policy fingerprint."""

    policy_id: RiskPolicyId
    version: RiskPolicyVersion
    fingerprint: RiskFingerprint
    per_trade_limit_bps: int
    per_trader_limit_bps: int
    per_instrument_limit_bps: int
    group_limit_bps: int
    portfolio_heat_limit_bps: int
    account_risk_capacity_bps: int
    safety_buffer_bps: int
    require_stop_loss: bool
    stress_enabled: bool
    correlation_groups: tuple[CorrelationGroup, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.policy_id, RiskPolicyId):
            raise RiskBudgetValidationError("budget policy policy_id must be RiskPolicyId")
        if not isinstance(self.version, RiskPolicyVersion):
            raise RiskBudgetValidationError("budget policy version must be RiskPolicyVersion")
        if not isinstance(self.fingerprint, RiskFingerprint):
            raise RiskBudgetValidationError("budget policy fingerprint must be RiskFingerprint")
        for field_name in (
            "per_trade_limit_bps",
            "per_trader_limit_bps",
            "per_instrument_limit_bps",
            "group_limit_bps",
            "portfolio_heat_limit_bps",
            "account_risk_capacity_bps",
        ):
            _validate_bps(getattr(self, field_name), field_name=field_name, minimum=1)
        _validate_bps(self.safety_buffer_bps, field_name="safety_buffer_bps", minimum=0)
        _validate_bool(self.require_stop_loss, field_name="require_stop_loss")
        _validate_bool(self.stress_enabled, field_name="stress_enabled")
        if not isinstance(self.correlation_groups, tuple):
            raise RiskBudgetValidationError("correlation_groups must be a tuple")
        if any(not isinstance(group, CorrelationGroup) for group in self.correlation_groups):
            raise RiskBudgetValidationError(
                "correlation_groups must contain only CorrelationGroup values"
            )
        group_ids = [group.group_id for group in self.correlation_groups]
        if len(set(group_ids)) != len(group_ids):
            raise RiskBudgetValidationError("correlation group ids must be unique")
        seen_instruments: set[ExecutionInstrument] = set()
        for group in self.correlation_groups:
            for instrument in group.instruments:
                if instrument in seen_instruments:
                    raise RiskBudgetValidationError(
                        "correlation group instruments must not overlap across groups"
                    )
                seen_instruments.add(instrument)


@dataclass(frozen=True, slots=True)
class ExternalAccountRiskLimits:
    """Immutable account-level risk limits supplied by an external authority."""

    max_drawdown_bps: int
    daily_loss_limit_bps: int
    max_notional: MoneyAmount | None = None
    max_quantity: OrderQuantity | None = None
    require_stop_loss: bool = False
    max_concentration_bps: int = 10_000

    def __post_init__(self) -> None:
        _validate_bps(self.max_drawdown_bps, field_name="max_drawdown_bps", minimum=0)
        _validate_bps(self.daily_loss_limit_bps, field_name="daily_loss_limit_bps", minimum=0)
        if self.max_notional is not None and not isinstance(self.max_notional, MoneyAmount):
            raise RiskBudgetValidationError("max_notional must be MoneyAmount or None")
        if self.max_quantity is not None and not isinstance(self.max_quantity, OrderQuantity):
            raise RiskBudgetValidationError("max_quantity must be OrderQuantity or None")
        _validate_bool(self.require_stop_loss, field_name="require_stop_loss")
        _validate_bps(
            self.max_concentration_bps, field_name="max_concentration_bps", minimum=0
        )


def compute_effective_limit_bps(internal_bps: int, external_bps: int | None) -> int:
    """Return the safest applicable bound: ``min(internal, external)``.

    When ``external_bps`` is ``None`` the internal bound applies unchanged.
    """

    if type(internal_bps) is not int:
        raise RiskBudgetValidationError("internal_bps must be an integer")
    if external_bps is not None and type(external_bps) is not int:
        raise RiskBudgetValidationError("external_bps must be an integer or None")
    if external_bps is None:
        return internal_bps
    return internal_bps if internal_bps < external_bps else external_bps


def apply_safety_buffer_bps(limit_bps: int, safety_buffer_bps: int) -> int:
    """Scale a limit down by a safety buffer and floor, never below zero."""

    if type(limit_bps) is not int:
        raise RiskBudgetValidationError("limit_bps must be an integer")
    if type(safety_buffer_bps) is not int:
        raise RiskBudgetValidationError("safety_buffer_bps must be an integer")
    if safety_buffer_bps < 0 or safety_buffer_bps > 10_000:
        raise RiskBudgetValidationError("safety_buffer_bps must be between 0 and 10000")
    scaled = limit_bps * (10_000 - safety_buffer_bps)
    result = scaled // 10_000
    return result if result > 0 else 0


def _rejection(code: RiskReasonCode, summary: str) -> RiskBudgetEvaluation:
    return RiskBudgetEvaluation(
        admitted=False,
        reduced=False,
        authorized_quantity=None,
        bounded_loss_at_stop=None,
        reason=RiskReason(code, summary),
    )


def _admission(
    *,
    reduced: bool,
    authorized_quantity: OrderQuantity,
    bounded_loss_at_stop: MoneyAmount | None,
) -> RiskBudgetEvaluation:
    code = RiskReasonCode.reduced if reduced else RiskReasonCode.admitted
    summary = "reduced to available budget" if reduced else "admitted within budget"
    return RiskBudgetEvaluation(
        admitted=True,
        reduced=reduced,
        authorized_quantity=authorized_quantity,
        bounded_loss_at_stop=bounded_loss_at_stop,
        reason=RiskReason(code, summary),
    )


class RiskBudgetEngine:
    """Concrete structural implementation of the L3 budget evaluator protocol."""

    __slots__ = ("policy", "external")

    def __init__(
        self,
        policy: RiskBudgetPolicy,
        external: ExternalAccountRiskLimits | None = None,
    ) -> None:
        if not isinstance(policy, RiskBudgetPolicy):
            raise RiskBudgetValidationError("policy must be RiskBudgetPolicy")
        if external is not None and not isinstance(external, ExternalAccountRiskLimits):
            raise RiskBudgetValidationError(
                "external must be ExternalAccountRiskLimits or None"
            )
        self.policy = policy
        self.external = external

    @property
    def policy_fingerprint(self) -> RiskFingerprint:
        return self.policy.fingerprint

    def evaluate(
        self,
        evidence: RiskEvidence,
        policy: RiskPolicySnapshot,
        *,
        evaluated_at: datetime,
    ) -> Result[RiskBudgetEvaluation, RiskError]:
        if not isinstance(evidence, RiskEvidence):
            return Failure(RiskValidationError("evidence must be RiskEvidence"))
        if not isinstance(policy, RiskPolicySnapshot):
            return Failure(RiskValidationError("policy must be RiskPolicySnapshot"))
        if not isinstance(evaluated_at, datetime):
            return Failure(RiskValidationError("evaluated_at must be a datetime"))
        if evaluated_at.tzinfo is None or evaluated_at.utcoffset() is None:
            return Failure(RiskValidationError("evaluated_at must be timezone-aware"))
        if policy.budget_config_fingerprint != self.policy_fingerprint:
            return Failure(
                RiskValidationError("budget config fingerprint mismatch")
            )
        if evaluated_at != evidence.evaluated_at:
            return Failure(
                RiskValidationError("evaluated_at must match evidence.evaluated_at")
            )
        if evaluated_at < evidence.account_state.observed_at:
            return Failure(
                RiskValidationError("evaluated_at must not predate account state")
            )
        if evaluated_at < evidence.market_evidence.observed_at:
            return Failure(
                RiskValidationError("evaluated_at must not predate market evidence")
            )

        equity = evidence.account_state.equity
        currency = equity.currency

        external = self.external
        if external is not None and external.max_notional is not None:
            if external.max_notional.currency != currency:
                return Failure(
                    RiskValidationError(
                        "external max_notional currency must match account equity currency"
                    )
                )

        require_stop = self.policy.require_stop_loss or (
            external is not None and external.require_stop_loss
        )
        if require_stop and evidence.stop_loss is None:
            return Success(
                _rejection(RiskReasonCode.missing_stop, "mandatory stop loss missing")
            )

        budget = self.policy
        safety = budget.safety_buffer_bps

        def notional_for(bps: int) -> Decimal:
            return equity.amount * Decimal(bps) / Decimal(10_000)

        per_trade_bps = apply_safety_buffer_bps(
            compute_effective_limit_bps(budget.per_trade_limit_bps, None), safety
        )
        available_per_trade = notional_for(per_trade_bps)

        requested_notional = evidence.requested_notional.amount
        if requested_notional <= 0:
            return Failure(
                RiskValidationError("requested notional must be positive")
            )

        if requested_notional > available_per_trade:
            ratio = available_per_trade / requested_notional
            authorized_qty = (
                evidence.requested_quantity.value * ratio
            ).quantize(Decimal("0.00000001"), rounding=ROUND_FLOOR)
            if authorized_qty <= 0:
                return Success(
                    _rejection(RiskReasonCode.budget_exceeded, "per-trade budget exceeded")
                )
            authorized_quantity = OrderQuantity(authorized_qty)
            reduced = True
            authorized_notional = available_per_trade
        else:
            authorized_quantity = evidence.requested_quantity
            reduced = False
            authorized_notional = requested_notional

        available_per_trader = notional_for(
            apply_safety_buffer_bps(budget.per_trader_limit_bps, safety)
        )
        if (
            evidence.per_trader_exposure.amount + authorized_notional
            > available_per_trader
        ):
            return Success(
                _rejection(RiskReasonCode.budget_exceeded, "per-trader budget exceeded")
            )

        per_instrument_bps = compute_effective_limit_bps(
            budget.per_instrument_limit_bps,
            external.max_concentration_bps if external is not None else None,
        )
        available_per_instrument = notional_for(
            apply_safety_buffer_bps(per_instrument_bps, safety)
        )
        if (
            evidence.per_instrument_exposure.amount + authorized_notional
            > available_per_instrument
        ):
            return Success(
                _rejection(
                    RiskReasonCode.concentration_exceeded,
                    "per-instrument concentration exceeded",
                )
            )

        for group in budget.correlation_groups:
            if evidence.instrument in group.instruments:
                group_available = notional_for(
                    apply_safety_buffer_bps(group.limit_bps, safety)
                )
                if evidence.group_exposure.amount + authorized_notional > group_available:
                    return Success(
                        _rejection(
                            RiskReasonCode.concentration_exceeded,
                            "correlation group concentration exceeded",
                        )
                    )

        available_heat = notional_for(
            apply_safety_buffer_bps(budget.portfolio_heat_limit_bps, safety)
        )
        if evidence.portfolio_heat.amount + authorized_notional > available_heat:
            return Success(
                _rejection(RiskReasonCode.heat_exceeded, "portfolio heat exceeded")
            )

        available_account_capacity = notional_for(
            apply_safety_buffer_bps(budget.account_risk_capacity_bps, safety)
        )
        if evidence.committed_capacity.amount + authorized_notional > available_account_capacity:
            return Success(
                _rejection(RiskReasonCode.capacity_exhausted, "account risk capacity exhausted")
            )

        if external is not None:
            if (
                external.max_notional is not None
                and authorized_notional > external.max_notional.amount
            ):
                return Success(
                    _rejection(
                        RiskReasonCode.external_limit_exceeded,
                        "external max notional exceeded",
                    )
                )
            if (
                external.max_quantity is not None
                and authorized_quantity.value > external.max_quantity.value
            ):
                return Success(
                    _rejection(
                        RiskReasonCode.external_limit_exceeded,
                        "external max quantity exceeded",
                    )
                )

        if budget.stress_enabled and evidence.bounded_loss_at_stop is not None:
            bounded_loss = evidence.bounded_loss_at_stop.amount
            post_stop_equity = equity.amount - bounded_loss
            if post_stop_equity <= 0:
                return Success(
                    _rejection(
                        RiskReasonCode.stress_breach,
                        "stress post-stop equity is not positive",
                    )
                )
            # Round the projected loss UP to the next integer basis point so a
            # fractional bounded loss at stop can never be under-reported (a
            # fail-closed stress projection). ROUND_FLOOR would under-estimate
            # the loss and admit an intent whose bounded adverse outcome would
            # breach the effective policy by a sub-basis-point margin.
            loss_bps = int(
                (bounded_loss * Decimal(10_000) / equity.amount).to_integral_value(
                    rounding=ROUND_CEILING
                )
            )
            projected_daily_loss = evidence.account_state.daily_loss.value + loss_bps
            projected_drawdown = evidence.account_state.drawdown.value + loss_bps
            if external is not None:
                if projected_daily_loss > external.daily_loss_limit_bps:
                    return Success(
                        _rejection(
                            RiskReasonCode.stress_breach,
                            "stress projected daily loss exceeds external limit",
                        )
                    )
                if projected_drawdown > external.max_drawdown_bps:
                    return Success(
                        _rejection(
                            RiskReasonCode.stress_breach,
                            "stress projected drawdown exceeds external limit",
                        )
                    )
            elif projected_drawdown > budget.account_risk_capacity_bps:
                return Success(
                    _rejection(
                        RiskReasonCode.stress_breach,
                        "stress projected drawdown exceeds internal capacity",
                    )
                )

        if (
            require_stop
            and evidence.stop_loss is not None
            and evidence.bounded_loss_at_stop is None
        ):
            return Success(
                _rejection(
                    RiskReasonCode.missing_stop,
                    "loss-at-stop cannot be determined",
                )
            )

        return Success(
            _admission(
                reduced=reduced,
                authorized_quantity=authorized_quantity,
                bounded_loss_at_stop=evidence.bounded_loss_at_stop,
            )
        )
