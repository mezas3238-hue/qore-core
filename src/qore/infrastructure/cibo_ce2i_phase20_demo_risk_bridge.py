"""Canonical QORE Risk bridge for cTrader DEMO Phase20D execution.

CIBO remains sizing/capital authority. This bridge does not size and does not
submit broker orders. It applies the sovereign AccountWideRiskEngine to one
already-built CiboRiskRequest against a canonical DEMO solvency snapshot.

ALLOW preserves CIBO volume. REDUCE creates an execution request at the Risk
authorized volume while preserving the original request identity and scaling
capital provenance from the canonical RiskAuthorization. REJECT produces no
execution request.

The bridge grants no LIVE, FundedNext, real-capital or merge authority.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime

from qore.infrastructure.account_wide_risk import (
    AccountRiskSnapshot,
    CiboRiskRequest,
    ReservationState,
    RiskAuthorization,
    RiskDecision,
)
from qore.infrastructure.account_wide_risk_ledger import (
    DurableAccountWideRiskEngine,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)


@dataclass(frozen=True, slots=True)
class Phase20DemoRiskAuthorizationResult:
    authorization: RiskAuthorization
    execution_request: CiboRiskRequest | None
    account_snapshot: AccountRiskSnapshot

    def __post_init__(self) -> None:
        if not isinstance(self.authorization, RiskAuthorization):
            raise CiboCapitalManagementError(
                "Phase20D DEMO Risk result requires canonical authorization"
            )
        if not isinstance(self.account_snapshot, AccountRiskSnapshot):
            raise CiboCapitalManagementError(
                "Phase20D DEMO Risk result requires canonical snapshot"
            )
        if self.authorization.decision is RiskDecision.REJECT:
            if self.execution_request is not None:
                raise CiboCapitalManagementError(
                    "Phase20D rejected Risk result cannot carry execution request"
                )
        elif not isinstance(self.execution_request, CiboRiskRequest):
            raise CiboCapitalManagementError(
                "Phase20D approved Risk result requires execution request"
            )


def assert_phase20_demo_authorization_active(
    *,
    risk: DurableAccountWideRiskEngine,
    authorization: RiskAuthorization,
    observed_at: datetime,
) -> None:
    """Require the exact durable Risk reservation immediately before mutation."""

    if not isinstance(risk, DurableAccountWideRiskEngine):
        raise CiboCapitalManagementError(
            "Phase20D DEMO execution requires durable QORE Risk"
        )
    if not isinstance(authorization, RiskAuthorization):
        raise CiboCapitalManagementError(
            "Phase20D DEMO execution requires canonical RiskAuthorization"
        )
    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise CiboCapitalManagementError(
            "Phase20D DEMO execution observed_at must be timezone-aware"
        )

    risk.expire(now=observed_at)
    reservation = risk.reservation_for(authorization.authorization_id)
    if reservation is None:
        raise CiboCapitalManagementError(
            "Phase20D DEMO Risk reservation is missing"
        )
    if reservation.authorization != authorization:
        raise CiboCapitalManagementError(
            "Phase20D DEMO Risk authorization/reservation drift"
        )
    if reservation.state is not ReservationState.RESERVED:
        raise CiboCapitalManagementError(
            "Phase20D DEMO Risk reservation is not executable"
        )
    if observed_at > authorization.expires_at:
        raise CiboCapitalManagementError(
            "Phase20D DEMO Risk authorization expired before execution"
        )


def authorize_phase20_demo_request(
    *,
    risk: DurableAccountWideRiskEngine,
    request: CiboRiskRequest,
    snapshot: AccountRiskSnapshot,
    observed_at: datetime,
) -> Phase20DemoRiskAuthorizationResult:
    """Apply sovereign Risk to a CIBO-sized DEMO request, fail-closed."""

    if not isinstance(risk, DurableAccountWideRiskEngine):
        raise CiboCapitalManagementError(
            "Phase20D DEMO authorization requires durable QORE Risk"
        )
    if not isinstance(request, CiboRiskRequest):
        raise CiboCapitalManagementError(
            "Phase20D DEMO authorization requires CiboRiskRequest"
        )
    if not isinstance(snapshot, AccountRiskSnapshot):
        raise CiboCapitalManagementError(
            "Phase20D DEMO authorization requires AccountRiskSnapshot"
        )
    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise CiboCapitalManagementError(
            "Phase20D DEMO Risk observed_at must be timezone-aware"
        )
    if snapshot.reconciled_at > observed_at:
        raise CiboCapitalManagementError(
            "Phase20D DEMO Risk snapshot cannot postdate authorization"
        )

    if risk.recovery_required:
        risk.complete_boot_reconciliation(
            snapshot,
            now=observed_at,
        )

    authorization = risk.authorize(
        request,
        snapshot,
        now=observed_at,
    )
    if authorization.decision is RiskDecision.REJECT:
        return Phase20DemoRiskAuthorizationResult(
            authorization=authorization,
            execution_request=None,
            account_snapshot=snapshot,
        )

    execution_request = replace(
        request,
        requested_volume=authorization.authorized_volume,
        capital_provenance=authorization.capital_provenance,
    )
    if execution_request.requested_stop_risk != authorization.monetary_stop_loss:
        raise CiboCapitalManagementError(
            "Phase20D DEMO execution request/Risk stop-risk drift"
        )
    if execution_request.requested_margin != authorization.margin_reserved:
        raise CiboCapitalManagementError(
            "Phase20D DEMO execution request/Risk margin drift"
        )

    return Phase20DemoRiskAuthorizationResult(
        authorization=authorization,
        execution_request=execution_request,
        account_snapshot=snapshot,
    )
