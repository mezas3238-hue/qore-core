"""Non-bypassable DEMO Risk -> cTrader operational composition.

Risk owns execution authority; cTrader owns broker mutation and reconciliation.
This module binds the two without inferring internal account identity from a broker
account number and without granting any Production/LIVE authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import InvalidOperation
from typing import Protocol, runtime_checkable

from qore.infrastructure.account_policy import AccountPolicyVersion
from qore.infrastructure.client_accounts import TradingAccountId
from qore.infrastructure.ctrader_demo_execution_configuration import (
    CTraderDemoRuntimeConfiguration,
)
from qore.infrastructure.ctrader_demo_execution_contracts import (
    CTraderDemoFillReconciliation,
)
from qore.infrastructure.ctrader_demo_operational_runtime import (
    CTraderDemoSubmissionResult,
)
from qore.infrastructure.execution_boundary import (
    ExecutionBoundaryError,
    ExecutionReceiptId,
    ExecutionRequestId,
    ExecutionSubmission,
)
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
    MarketTestAccountIdentity,
)
from qore.infrastructure.order_intent import OrderIntent
from qore.infrastructure.ports import (
    ExternalHealth,
    ExternalPortError,
    ExternalRequestMetadata,
)
from qore.infrastructure.risk_authority import (
    RiskAuthorization,
    RiskAuthorizationId,
    RiskDecision,
    RiskEnvironment,
    RiskFingerprint,
    RiskReservationId,
    RiskScopeSnapshot,
)
from qore.infrastructure.risk_runtime import DemoRiskRuntime, RiskAuthorizedSubmission
from qore.kernel.result import Failure, Result, Success


class CTraderDemoRiskOperationalRuntimeError(ExecutionBoundaryError):
    """Sanitized fail-closed Risk/cTrader composition error."""

    __slots__ = ()


def validate_ctrader_authorized_quantity(
    configuration: CTraderDemoRuntimeConfiguration,
    authorization: RiskAuthorization,
) -> Result[None, CTraderDemoRiskOperationalRuntimeError]:
    """Prove Risk-authorized quantity is broker-valid before capacity commit.

    Risk is provider-neutral and may REDUCE to any positive canonical quantity.
    The cTrader composition must therefore reject a quantity that cannot be
    represented by the exact broker volume_step/min/max/step constraints before
    ``DemoRiskRuntime.prepare_execution_submission`` commits the reservation.
    """

    if not isinstance(configuration, CTraderDemoRuntimeConfiguration):
        return Failure(
            CTraderDemoRiskOperationalRuntimeError(
                "quantity validation requires CTraderDemoRuntimeConfiguration"
            )
        )
    if not isinstance(authorization, RiskAuthorization):
        return Failure(
            CTraderDemoRiskOperationalRuntimeError(
                "quantity validation requires RiskAuthorization"
            )
        )
    mapping = configuration.symbol_mapping(authorization.instrument)
    if mapping is None:
        return Failure(
            CTraderDemoRiskOperationalRuntimeError(
                "Risk-authorized instrument is not mapped by cTrader DEMO"
            )
        )
    quantity = authorization.authorized_quantity.value
    try:
        quotient, remainder = divmod(quantity, mapping.volume_step)
    except InvalidOperation:
        return Failure(
            CTraderDemoRiskOperationalRuntimeError(
                "Risk-authorized quantity cannot be mapped to cTrader volume units"
            )
        )
    if remainder != 0 or quotient != quotient.to_integral_value():
        return Failure(
            CTraderDemoRiskOperationalRuntimeError(
                "Risk-authorized quantity is not an exact cTrader volume_step multiple"
            )
        )
    units = int(quotient)
    if not mapping.min_volume_units <= units <= mapping.max_volume_units:
        return Failure(
            CTraderDemoRiskOperationalRuntimeError(
                "Risk-authorized quantity is outside cTrader broker volume bounds"
            )
        )
    if units % mapping.step_volume_units != 0:
        return Failure(
            CTraderDemoRiskOperationalRuntimeError(
                "Risk-authorized quantity does not align to cTrader stepVolume"
            )
        )
    return Success(None)


@dataclass(frozen=True, slots=True)
class RiskCTraderDemoAccountBinding:
    """Explicit binding; an internal UUID is never inferred from broker account_ref."""

    risk_account_id: TradingAccountId
    ctrader_account: MarketTestAccountIdentity

    def __post_init__(self) -> None:
        if not isinstance(self.risk_account_id, TradingAccountId):
            raise CTraderDemoRiskOperationalRuntimeError(
                "risk_account_id must be TradingAccountId"
            )
        if not isinstance(self.ctrader_account, MarketTestAccountIdentity):
            raise CTraderDemoRiskOperationalRuntimeError(
                "ctrader_account must be MarketTestAccountIdentity"
            )
        if self.ctrader_account.provider_key != "ctrader-demo":
            raise CTraderDemoRiskOperationalRuntimeError(
                "broker account binding must target ctrader-demo"
            )
        if self.ctrader_account.environment is not MarketRuntimeEnvironment.DEMO:
            raise CTraderDemoRiskOperationalRuntimeError(
                "broker account binding must target DEMO"
            )


@runtime_checkable
class CTraderDemoOperationalBoundary(Protocol):
    @property
    def configuration(self) -> CTraderDemoRuntimeConfiguration: ...

    @property
    def has_unresolved_mutations(self) -> bool: ...

    def connect(
        self,
        *,
        checked_at: datetime,
        metadata: ExternalRequestMetadata,
    ) -> Result[ExternalHealth, ExternalPortError]: ...

    def submit_authorized(
        self,
        submission: ExecutionSubmission,
    ) -> Result[CTraderDemoSubmissionResult, ExecutionBoundaryError]: ...

    def stage_risk_fence(
        self,
        submission: ExecutionSubmission,
        *,
        risk_authorization_id: str,
        risk_authorization_fingerprint: str,
        risk_reservation_id: str,
    ) -> Result[None, ExecutionBoundaryError]: ...

    def poll_and_reconcile(
        self,
        submission: ExecutionSubmission,
        *,
        provider_order_ref: str,
        metadata: ExternalRequestMetadata,
    ) -> Result[CTraderDemoFillReconciliation, ExecutionBoundaryError]: ...


@dataclass(frozen=True, slots=True)
class RiskCTraderDemoSubmissionResult:
    """Exact immutable link from Risk admission to one broker submission."""

    risk: RiskAuthorizedSubmission
    broker: CTraderDemoSubmissionResult

    def __post_init__(self) -> None:
        if not isinstance(self.risk, RiskAuthorizedSubmission):
            raise CTraderDemoRiskOperationalRuntimeError(
                "risk result must be RiskAuthorizedSubmission"
            )
        if not isinstance(self.broker, CTraderDemoSubmissionResult):
            raise CTraderDemoRiskOperationalRuntimeError(
                "broker result must be CTraderDemoSubmissionResult"
            )
        if self.risk.submission.receipt_id != self.broker.receipt.receipt_id:
            raise CTraderDemoRiskOperationalRuntimeError(
                "Risk submission and broker receipt must bind the same receipt"
            )


@dataclass(frozen=True, slots=True)
class RiskCTraderDemoReconciliationResult:
    """Risk-linked terminal/cumulative broker reconciliation evidence."""

    risk_authorization_id: RiskAuthorizationId
    risk_authorization_fingerprint: RiskFingerprint
    reservation_id: RiskReservationId
    provider_order_ref: str
    reconciliation: CTraderDemoFillReconciliation

    def __post_init__(self) -> None:
        if not isinstance(self.risk_authorization_id, RiskAuthorizationId):
            raise CTraderDemoRiskOperationalRuntimeError(
                "risk_authorization_id must be RiskAuthorizationId"
            )
        if not isinstance(self.risk_authorization_fingerprint, RiskFingerprint):
            raise CTraderDemoRiskOperationalRuntimeError(
                "risk_authorization_fingerprint must be RiskFingerprint"
            )
        if not isinstance(self.reservation_id, RiskReservationId):
            raise CTraderDemoRiskOperationalRuntimeError(
                "reservation_id must be RiskReservationId"
            )
        if not isinstance(self.provider_order_ref, str) or not self.provider_order_ref:
            raise CTraderDemoRiskOperationalRuntimeError(
                "provider_order_ref must be non-empty"
            )
        if not isinstance(self.reconciliation, CTraderDemoFillReconciliation):
            raise CTraderDemoRiskOperationalRuntimeError(
                "reconciliation must be CTraderDemoFillReconciliation"
            )


class CTraderDemoRiskOperationalRuntime:
    """Compose exact Risk authorization with exactly one cTrader DEMO account."""

    __slots__ = ("_binding", "_ctrader", "_risk")

    def __init__(
        self,
        *,
        risk: DemoRiskRuntime,
        ctrader: CTraderDemoOperationalBoundary,
        account_binding: RiskCTraderDemoAccountBinding,
    ) -> None:
        if not isinstance(risk, DemoRiskRuntime):
            raise CTraderDemoRiskOperationalRuntimeError(
                "risk must be DemoRiskRuntime"
            )
        if not isinstance(ctrader, CTraderDemoOperationalBoundary):
            raise CTraderDemoRiskOperationalRuntimeError(
                "ctrader must satisfy CTraderDemoOperationalBoundary"
            )
        if not isinstance(account_binding, RiskCTraderDemoAccountBinding):
            raise CTraderDemoRiskOperationalRuntimeError(
                "account_binding must be RiskCTraderDemoAccountBinding"
            )
        configuration = ctrader.configuration
        if configuration.environment is not MarketRuntimeEnvironment.DEMO:
            raise CTraderDemoRiskOperationalRuntimeError(
                "cTrader operational boundary must be DEMO"
            )
        if configuration.account != account_binding.ctrader_account:
            raise CTraderDemoRiskOperationalRuntimeError(
                "cTrader runtime account must match explicit account binding"
            )
        self._risk = risk
        self._ctrader = ctrader
        self._binding = account_binding

    @property
    def configuration(self) -> CTraderDemoRuntimeConfiguration:
        return self._ctrader.configuration

    @property
    def account_binding(self) -> RiskCTraderDemoAccountBinding:
        return self._binding

    @property
    def has_unresolved_mutations(self) -> bool:
        return self._ctrader.has_unresolved_mutations

    def connect(
        self,
        *,
        checked_at: datetime,
        metadata: ExternalRequestMetadata,
    ) -> Result[ExternalHealth, ExternalPortError]:
        """Run the existing read-only authenticated cTrader DEMO preflight."""

        return self._ctrader.connect(checked_at=checked_at, metadata=metadata)

    def submit_risk_authorized(
        self,
        decision: RiskDecision,
        intent: OrderIntent,
        *,
        scope: RiskScopeSnapshot,
        account_policy_version: AccountPolicyVersion,
        expected_authorization_fingerprint: RiskFingerprint,
        request_id: ExecutionRequestId,
        receipt_id: ExecutionReceiptId,
        authorized_at: datetime,
        submitted_at: datetime,
    ) -> Result[RiskCTraderDemoSubmissionResult, CTraderDemoRiskOperationalRuntimeError]:
        """Prepare through Risk and immediately submit the exact resulting DEMO order.

        Account/environment/provider-quantity checks happen before Risk reservation
        commit and before broker mutation. Once Risk commits a reservation, a broker
        failure does not release it here; ambiguous provider outcomes must be
        reconciled first.
        """

        if not isinstance(decision, RiskDecision):
            return Failure(
                CTraderDemoRiskOperationalRuntimeError("decision must be RiskDecision")
            )
        authorization = decision.authorization
        if authorization is None:
            return Failure(
                CTraderDemoRiskOperationalRuntimeError(
                    "Risk decision must carry an execution authorization"
                )
            )
        if authorization.environment is not RiskEnvironment.DEMO:
            return Failure(
                CTraderDemoRiskOperationalRuntimeError(
                    "Risk authorization must be DEMO"
                )
            )
        if authorization.account_id != self._binding.risk_account_id:
            return Failure(
                CTraderDemoRiskOperationalRuntimeError(
                    "Risk authorization account must match explicit account binding"
                )
            )
        provider_quantity = validate_ctrader_authorized_quantity(
            self.configuration,
            authorization,
        )
        if isinstance(provider_quantity, Failure):
            return provider_quantity
        prepared = self._risk.prepare_execution_submission(
            decision,
            intent,
            scope=scope,
            account_policy_version=account_policy_version,
            expected_authorization_fingerprint=expected_authorization_fingerprint,
            request_id=request_id,
            receipt_id=receipt_id,
            authorized_at=authorized_at,
            submitted_at=submitted_at,
        )
        if isinstance(prepared, Failure):
            return Failure(CTraderDemoRiskOperationalRuntimeError(str(prepared.error)))
        fenced = self._ctrader.stage_risk_fence(
            prepared.value.submission,
            risk_authorization_id=str(authorization.authorization_id.value),
            risk_authorization_fingerprint=expected_authorization_fingerprint.value,
            risk_reservation_id=str(prepared.value.reservation.reservation_id.value),
        )
        if isinstance(fenced, Failure):
            return Failure(CTraderDemoRiskOperationalRuntimeError(str(fenced.error)))
        submitted = self._ctrader.submit_authorized(prepared.value.submission)
        if isinstance(submitted, Failure):
            return Failure(CTraderDemoRiskOperationalRuntimeError(str(submitted.error)))
        try:
            return Success(
                RiskCTraderDemoSubmissionResult(
                    risk=prepared.value,
                    broker=submitted.value,
                )
            )
        except CTraderDemoRiskOperationalRuntimeError as error:
            return Failure(error)

    def poll_and_reconcile(
        self,
        submitted: RiskCTraderDemoSubmissionResult,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[RiskCTraderDemoReconciliationResult, CTraderDemoRiskOperationalRuntimeError]:
        """Reconcile one exact provider order while preserving its Risk provenance."""

        if not isinstance(submitted, RiskCTraderDemoSubmissionResult):
            return Failure(
                CTraderDemoRiskOperationalRuntimeError(
                    "submitted must be RiskCTraderDemoSubmissionResult"
                )
            )
        reconciled = self._ctrader.poll_and_reconcile(
            submitted.risk.submission,
            provider_order_ref=submitted.broker.provider_order_ref,
            metadata=metadata,
        )
        if isinstance(reconciled, Failure):
            return Failure(CTraderDemoRiskOperationalRuntimeError(str(reconciled.error)))
        authorization = submitted.risk.risk_authorization
        try:
            return Success(
                RiskCTraderDemoReconciliationResult(
                    risk_authorization_id=authorization.authorization_id,
                    risk_authorization_fingerprint=(
                        submitted.risk.risk_authorization_fingerprint
                    ),
                    reservation_id=submitted.risk.reservation.reservation_id,
                    provider_order_ref=submitted.broker.provider_order_ref,
                    reconciliation=reconciled.value,
                )
            )
        except CTraderDemoRiskOperationalRuntimeError as error:
            return Failure(error)
