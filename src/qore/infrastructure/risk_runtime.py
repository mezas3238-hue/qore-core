"""DEMO Risk runtime composition (sovereignty integration seam).

This module composes the deterministic Risk authority (``risk_authority``) with
the budget engine (``risk_budgets``), the capacity store (``risk_capacity``),
and the existing account-policy / pre-trade-safety seams. It issues NO
Production/LIVE authority and no real-capital authority.

Responsibilities:

* :class:`DemoRiskRuntime` — one fail-closed admission runtime that resolves the
  account-policy snapshot against an explicit registry and then delegates to
  ``evaluate_risk_admission`` (the only sovereignty core).
* :func:`validate_risk_authorization` — the DEMO execution-boundary seam that
  validates an exact immutable :class:`~qore.infrastructure.risk_authority.RiskAuthorization`
  (fingerprint, scope generation, policy version, environment, status) rather
  than trusting free-form CIBO/Trader output.
* :func:`compose_execution_safety_from_scope` — bridges the Risk governance scope
  to the existing pre-trade execution switch (kill/contain => BLOCKED).
* :func:`compose_demo_risk_runtime` — constructs a coherent runtime from explicit,
  versioned, fingerprinted configuration.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from qore.infrastructure.account_policy import (
    AccountPolicyRegistrySnapshot,
    AccountPolicyVersion,
    AccountPropPolicySnapshot,
)
from qore.infrastructure.pretrade_safety import (
    ExecutionSafetySwitchSnapshot,
    ExecutionSwitchState,
    PreTradeSafetyError,
)
from qore.infrastructure.proprietary_accounts import MoneyAmount
from qore.infrastructure.risk_authority import (
    DEFAULT_MAX_EVIDENCE_AGE_SECONDS,
    RiskArm,
    RiskAuthorization,
    RiskAuthorizationId,
    RiskBudgetEvaluator,
    RiskCapacityStore,
    RiskDecision,
    RiskDecisionId,
    RiskEnvironment,
    RiskError,
    RiskEvidence,
    RiskFingerprint,
    RiskOutcome,
    RiskPolicySnapshot,
    RiskReason,
    RiskReasonCode,
    RiskReservationId,
    RiskScopeSnapshot,
    RiskScopeState,
    compute_authorization_fingerprint,
    evaluate_risk_admission,
    is_authorization_reusable,
)
from qore.infrastructure.risk_budgets import (
    ExternalAccountRiskLimits,
    RiskBudgetEngine,
    RiskBudgetPolicy,
)
from qore.infrastructure.risk_capacity import InMemoryRiskCapacityStore
from qore.kernel.result import Failure, Result, Success

__all__ = [
    "DemoRiskRuntime",
    "RiskPolicyResolutionError",
    "RiskRuntimeError",
    "RiskRuntimeValidationError",
    "compose_demo_risk_runtime",
    "compose_execution_safety_from_scope",
    "resolve_account_policy_for_evidence",
    "validate_risk_authorization",
]

_BLOCKING_SCOPE_STATES = frozenset(
    {
        RiskScopeState.FREEZE_TRADER,
        RiskScopeState.CONTAIN_ACCOUNT,
        RiskScopeState.KILL,
    }
)


class RiskRuntimeError(RiskError):
    """Base error for the DEMO risk runtime composition."""

    __slots__ = ()


class RiskRuntimeValidationError(RiskRuntimeError):
    """Violation of a risk-runtime composition invariant."""

    __slots__ = ()


class RiskPolicyResolutionError(RiskRuntimeError):
    """Typed fail-closed account-policy resolution with a ``RiskReason`` payload."""

    __slots__ = ("reason",)

    def __init__(self, reason: RiskReason) -> None:
        super().__init__(reason.summary)
        self.reason = reason


@dataclass(frozen=True, slots=True)
class DemoRiskRuntime:
    """Fail-closed DEMO admission runtime above the deterministic Risk authority."""

    budget_engine: RiskBudgetEvaluator
    capacity: RiskCapacityStore

    def __post_init__(self) -> None:
        if not isinstance(self.budget_engine, RiskBudgetEvaluator):
            raise RiskRuntimeValidationError(
                "runtime budget_engine must satisfy RiskBudgetEvaluator"
            )
        if not isinstance(self.capacity, RiskCapacityStore):
            raise RiskRuntimeValidationError(
                "runtime capacity must satisfy RiskCapacityStore"
            )

    def admit(
        self,
        evidence: RiskEvidence,
        internal_policy: RiskPolicySnapshot,
        *,
        decision_id: RiskDecisionId,
        authorization_id: RiskAuthorizationId,
        reservation_id: RiskReservationId,
        reservation_generation: int,
        account_policy_registry: AccountPolicyRegistrySnapshot | None = None,
        max_evidence_age_seconds: int = DEFAULT_MAX_EVIDENCE_AGE_SECONDS,
    ) -> Result[RiskDecision, RiskError]:
        """Resolve the account policy (when a registry is supplied) then admit.

        Account-policy resolution failures produce a typed ``REJECT`` decision
        (never a lateral exception) so the runtime never admits new risk under
        an unresolved, substituted, expired, or not-yet-effective policy.
        """

        if not isinstance(evidence, RiskEvidence):
            return Failure(RiskRuntimeValidationError("evidence must be RiskEvidence"))
        if not isinstance(internal_policy, RiskPolicySnapshot):
            return Failure(
                RiskRuntimeValidationError("internal_policy must be RiskPolicySnapshot")
            )
        if account_policy_registry is not None:
            if not isinstance(account_policy_registry, AccountPolicyRegistrySnapshot):
                return Failure(
                    RiskRuntimeValidationError(
                        "account_policy_registry must be AccountPolicyRegistrySnapshot or None"
                    )
                )
            resolved = resolve_account_policy_for_evidence(
                evidence, account_policy_registry
            )
            if isinstance(resolved, Failure):
                return Success(_reject(evidence, decision_id, resolved.error.reason))
        return evaluate_risk_admission(
            evidence,
            internal_policy,
            self.budget_engine,
            self.capacity,
            decision_id=decision_id,
            authorization_id=authorization_id,
            reservation_id=reservation_id,
            reservation_generation=reservation_generation,
            max_evidence_age_seconds=max_evidence_age_seconds,
        )


def resolve_account_policy_for_evidence(
    evidence: RiskEvidence,
    registry: AccountPolicyRegistrySnapshot,
) -> Result[AccountPropPolicySnapshot, RiskPolicyResolutionError]:
    """Resolve the exact effective account policy for ``evidence`` or fail closed.

    Reuses the same effective/expiry/completeness semantics as
    ``AccountPolicyRegistrySnapshot.resolve_for_new_trading`` but returns typed
    :class:`RiskReason` values (wrapped in :class:`RiskPolicyResolutionError`) so
    the admission layer can emit a typed REJECT.
    """

    if not isinstance(evidence, RiskEvidence):
        raise RiskRuntimeValidationError("evidence must be RiskEvidence")
    if not isinstance(registry, AccountPolicyRegistrySnapshot):
        raise RiskRuntimeValidationError(
            "registry must be AccountPolicyRegistrySnapshot"
        )
    evaluated_at = evidence.evaluated_at
    for policy in registry.policies:
        if policy.policy_ref != evidence.account_policy_ref:
            continue
        if policy.account_id != evidence.account_id:
            return _policy_failure(
                RiskReason(
                    RiskReasonCode.account_mismatch,
                    "account policy reference belongs to a different account",
                )
            )
        if evaluated_at < policy.effective_at:
            return _policy_failure(
                RiskReason(
                    RiskReasonCode.policy_not_effective,
                    "account policy is not yet effective",
                )
            )
        if policy.expires_at is not None and evaluated_at >= policy.expires_at:
            return _policy_failure(
                RiskReason(RiskReasonCode.policy_expired, "account policy is expired")
            )
        if not policy.is_complete_for_new_trading():
            return _policy_failure(
                RiskReason(
                    RiskReasonCode.policy_ambiguous,
                    "mandatory account-policy semantics are unresolved",
                )
            )
        if policy.snapshot_id != evidence.account_policy_snapshot_id:
            return _policy_failure(
                RiskReason(
                    RiskReasonCode.account_mismatch,
                    "account policy snapshot identity does not match evidence",
                )
            )
        if policy.version != evidence.account_policy_version:
            return _policy_failure(
                RiskReason(
                    RiskReasonCode.policy_version_mismatch,
                    "account policy version does not match evidence",
                )
            )
        return Success(policy)
    return _policy_failure(
        RiskReason(RiskReasonCode.account_mismatch, "account policy reference not found")
    )


def _policy_failure(reason: RiskReason) -> Failure[RiskPolicyResolutionError]:
    return Failure(RiskPolicyResolutionError(reason))


def validate_risk_authorization(
    auth: RiskAuthorization,
    *,
    scope: RiskScopeSnapshot,
    account_policy_version: AccountPolicyVersion,
    expected_fingerprint: RiskFingerprint,
    evaluated_at: datetime,
) -> Result[RiskAuthorization, RiskError]:
    """Validate an exact risk authorization at the DEMO execution boundary.

    Success returns the authorization unchanged only when it is issued, in a
    non-Production environment, still bound to the current scope generation and
    account-policy version, and byte-identical to the fingerprint recorded at
    issuance (which invalidates any post-issuance mutation).
    """

    if not isinstance(auth, RiskAuthorization):
        return Failure(RiskRuntimeValidationError("auth must be RiskAuthorization"))
    if not isinstance(scope, RiskScopeSnapshot):
        return Failure(RiskRuntimeValidationError("scope must be RiskScopeSnapshot"))
    if not isinstance(account_policy_version, AccountPolicyVersion):
        return Failure(
            RiskRuntimeValidationError(
                "account_policy_version must be AccountPolicyVersion"
            )
        )
    if not isinstance(expected_fingerprint, RiskFingerprint):
        return Failure(
            RiskRuntimeValidationError("expected_fingerprint must be RiskFingerprint")
        )
    try:
        if not isinstance(evaluated_at, datetime) or evaluated_at.tzinfo is None:
            raise RiskRuntimeValidationError("evaluated_at must be timezone-aware")
    except RiskRuntimeValidationError as error:
        return Failure(error)

    if auth.environment in (RiskEnvironment.PRODUCTION, RiskEnvironment.UNKNOWN):
        return Failure(
            RiskRuntimeValidationError(
                "risk authorization is not valid in this environment"
            )
        )
    if compute_authorization_fingerprint(auth) != expected_fingerprint:
        return Failure(
            RiskRuntimeValidationError(
                "risk authorization was mutated after issuance"
            )
        )
    if not is_authorization_reusable(
        auth,
        scope=scope,
        account_policy_version=account_policy_version,
        evaluated_at=evaluated_at,
    ):
        return Failure(
            RiskRuntimeValidationError("risk authorization is no longer reusable")
        )
    return Success(auth)


def compose_execution_safety_from_scope(
    scope: RiskScopeSnapshot,
    *,
    observed_at: datetime,
) -> Result[ExecutionSafetySwitchSnapshot, RiskError]:
    """Bridge a Risk governance scope to the existing execution switch.

    A frozen/contained/killed scope maps to a BLOCKED switch; a normal or
    reduced-capacity scope maps to an ENABLED switch. This reuses the existing
    ``ExecutionSafetySwitchSnapshot`` kill-switch seam instead of inventing a
    competing one.
    """

    if not isinstance(scope, RiskScopeSnapshot):
        return Failure(RiskRuntimeValidationError("scope must be RiskScopeSnapshot"))
    try:
        if not isinstance(observed_at, datetime) or observed_at.tzinfo is None:
            raise RiskRuntimeValidationError("observed_at must be timezone-aware")
        if observed_at < scope.since:
            raise RiskRuntimeValidationError(
                "execution switch observation must not predate the scope"
            )
    except RiskRuntimeValidationError as error:
        return Failure(error)

    if scope.state in _BLOCKING_SCOPE_STATES:
        state = ExecutionSwitchState.BLOCKED
        reason = f"risk.scope.{scope.state.value}"
    else:
        state = ExecutionSwitchState.ENABLED
        reason = "risk.scope.enabled"
    try:
        return Success(
            ExecutionSafetySwitchSnapshot(
                state=state,
                observed_at=observed_at,
                reason=reason,
            )
        )
    except PreTradeSafetyError as error:
        return Failure(RiskRuntimeValidationError(str(error)))


def compose_demo_risk_runtime(
    budget_policy: RiskBudgetPolicy,
    internal_policy: RiskPolicySnapshot,
    *,
    external: ExternalAccountRiskLimits | None = None,
    capacity: MoneyAmount,
    arm: RiskArm,
) -> Result[DemoRiskRuntime, RiskError]:
    """Construct a coherent runtime from explicit, fingerprinted configuration.

    Fails closed unless the internal policy's ``budget_config_fingerprint``
    matches the budget policy fingerprint and the arm is consistent with the
    internal policy arm.
    """

    if not isinstance(budget_policy, RiskBudgetPolicy):
        return Failure(
            RiskRuntimeValidationError("budget_policy must be RiskBudgetPolicy")
        )
    if not isinstance(internal_policy, RiskPolicySnapshot):
        return Failure(
            RiskRuntimeValidationError("internal_policy must be RiskPolicySnapshot")
        )
    if not isinstance(arm, RiskArm):
        return Failure(RiskRuntimeValidationError("arm must be RiskArm"))
    if external is not None and not isinstance(external, ExternalAccountRiskLimits):
        return Failure(
            RiskRuntimeValidationError(
                "external must be ExternalAccountRiskLimits or None"
            )
        )
    if not isinstance(capacity, MoneyAmount):
        return Failure(RiskRuntimeValidationError("capacity must be MoneyAmount"))
    if capacity.amount < 0:
        return Failure(RiskRuntimeValidationError("capacity must not be negative"))
    if internal_policy.budget_config_fingerprint != budget_policy.fingerprint:
        return Failure(
            RiskRuntimeValidationError(
                "internal policy budget_config_fingerprint must match budget policy"
            )
        )
    if internal_policy.arm is not arm:
        return Failure(
            RiskRuntimeValidationError("internal policy arm does not match runtime arm")
        )
    try:
        return Success(
            DemoRiskRuntime(
                budget_engine=RiskBudgetEngine(budget_policy, external),
                capacity=InMemoryRiskCapacityStore(capacity),
            )
        )
    except RiskError as error:
        return Failure(error)


def _reject(
    evidence: RiskEvidence,
    decision_id: RiskDecisionId,
    reason: RiskReason,
) -> RiskDecision:
    """Build a REJECT decision bound to the given reason."""

    return RiskDecision(
        decision_id=decision_id,
        outcome=RiskOutcome.REJECT,
        reasons=(reason,),
        evidence=evidence,
        evaluated_at=evidence.evaluated_at,
        arm=evidence.arm,
        authorization=None,
    )
