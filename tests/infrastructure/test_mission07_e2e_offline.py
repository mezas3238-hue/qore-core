from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import qore.domain.events as domain_events
import qore.functional.decisions as decisions
import qore.infrastructure.account_policy as account_policy
import qore.infrastructure.adapter_configuration as adapter_configuration
import qore.infrastructure.client_accounts as accounts
import qore.infrastructure.client_decision_security as security
import qore.infrastructure.client_execution_agent as agent
import qore.infrastructure.client_multiaccount_read_model as read_model
import qore.infrastructure.client_performance_ledger as performance
import qore.infrastructure.client_position_lifecycle as lifecycle
import qore.infrastructure.client_trial_licensing as licensing
import qore.infrastructure.client_widget_multiaccount as widget
import qore.infrastructure.commercial_billing as billing
import qore.infrastructure.commercial_products as products
import qore.infrastructure.corporate_profit_vault as vault
import qore.infrastructure.execution_boundary as execution
import qore.infrastructure.execution_reconciliation as reconciliation
import qore.infrastructure.order_intent as orders
import qore.infrastructure.proprietary_accounts as money
import qore.infrastructure.secrets as secrets
import qore.kernel.result as result

_NOW = datetime(2026, 8, 9, 15, 30, tzinfo=UTC)
_DECISION_AT = _NOW - timedelta(seconds=50)
_ISSUED_AT = _NOW - timedelta(seconds=40)
_SECURITY_AT = _NOW - timedelta(seconds=30)
_OBSERVED_AT = _NOW - timedelta(seconds=20)
_CALCULATED_AT = _NOW - timedelta(seconds=10)
_USD = money.CurrencyCode("USD")


def _uuid(suffix: int) -> UUID:
    return UUID(f"43000000-0000-0000-0000-{suffix:012d}")


def _amount(value: str) -> money.MoneyAmount:
    return money.MoneyAmount(currency=_USD, amount=Decimal(value))


def _decision() -> agent.CoreTradeDecision:
    functional = decisions.FunctionalDecision(
        decision_id=decisions.DecisionId(_uuid(1)),
        timestamp=_DECISION_AT,
        decision_type=decisions.DecisionType("core.trade"),
        status=decisions.DecisionStatus.RESOLVED,
        priority=decisions.DecisionPriority.NORMAL,
        metadata=decisions.DecisionMetadata(
            correlation_id=domain_events.CorrelationId(_uuid(2)),
        ),
        reasons=(
            decisions.DecisionReason(
                code=decisions.DecisionReasonCode("strategy.approved"),
                summary="MISSION-07 deterministic E2E Core Decision",
            ),
        ),
        outcome=decisions.DecisionOutcome.APPROVED,
    )
    return agent.CoreTradeDecision(
        decision=functional,
        instrument=orders.ExecutionInstrument("EUR_USD"),
        side=orders.OrderSide.BUY,
        order_type=orders.OrderType.MARKET,
        expires_at=_NOW + timedelta(minutes=4),
    )


def _binding(
    *,
    account_suffix: int,
    policy_suffix: int,
    entitlement_suffix: int,
    runtime_suffix: int,
) -> accounts.ClientTradingAccountBinding:
    return accounts.ClientTradingAccountBinding(
        client_id=accounts.ClientId(_uuid(10)),
        account_id=accounts.TradingAccountId(_uuid(account_suffix)),
        account_kind=accounts.TradingAccountKind.PROP_FIRM,
        lifecycle_state=accounts.TradingAccountLifecycleState.ACTIVE,
        policy_ref=accounts.AccountPolicyReference(_uuid(policy_suffix)),
        product_entitlement_ref=accounts.ProductEntitlementReference(
            _uuid(entitlement_suffix)
        ),
        runtime_ref=accounts.ExecutionRuntimeReference(_uuid(runtime_suffix)),
    )


def _account_policy(
    binding: accounts.ClientTradingAccountBinding,
    *,
    snapshot_suffix: int,
) -> account_policy.AccountPropPolicySnapshot:
    return account_policy.AccountPropPolicySnapshot(
        snapshot_id=account_policy.AccountPolicySnapshotId(_uuid(snapshot_suffix)),
        policy_ref=binding.policy_ref,
        account_id=binding.account_id,
        account_kind=binding.account_kind,
        version=account_policy.AccountPolicyVersion(1),
        effective_at=_NOW - timedelta(days=1),
        expires_at=None,
        account_size=_amount("100000"),
        max_drawdown=money.DrawdownBps(1000),
        daily_loss_limit=money.DrawdownBps(500),
        drawdown_mode=account_policy.DrawdownMode.STATIC,
        phase=account_policy.AccountPhase.FUNDED,
        client_profit_split=account_policy.ProfitSplitBps(8000),
        firm_ref=account_policy.PropFirmReference(_uuid(snapshot_suffix + 1)),
        program_ref=account_policy.PropProgramReference(_uuid(snapshot_suffix + 2)),
        rules=(),
    )


def _observed(
    binding: accounts.ClientTradingAccountBinding,
    *,
    observation_suffix: int,
    daily_loss_bps: int = 50,
) -> agent.ClientAccountObservedState:
    return agent.ClientAccountObservedState(
        observation_id=agent.ClientAccountObservationId(_uuid(observation_suffix)),
        account_id=binding.account_id,
        observed_at=_OBSERVED_AT,
        balance=_amount("100000"),
        equity=_amount("100000"),
        current_drawdown=money.DrawdownBps(100),
        daily_loss=money.DrawdownBps(daily_loss_bps),
        open_positions=0,
    )


def _execution_policy() -> agent.ClientExecutionPolicy:
    return agent.ClientExecutionPolicy(
        policy_id=agent.ClientExecutionPolicyId(_uuid(60)),
        sizing_policy_ref=agent.SizingPolicyReference(_uuid(61)),
        protection_policy_ref=agent.ProtectionPolicyReference(_uuid(62)),
        trailing_policy_ref=agent.TrailingPolicyReference(_uuid(63)),
        max_risk_per_trade=money.DrawdownBps(100),
        max_account_state_age_seconds=120,
        max_entitlement_age_seconds=120,
        max_security_attestation_age_seconds=120,
    )


def _calculation(
    decision: agent.CoreTradeDecision,
    binding: accounts.ClientTradingAccountBinding,
    policy: agent.ClientExecutionPolicy,
) -> agent.ClientExecutionCalculation:
    return agent.ClientExecutionCalculation(
        decision_id=decision.decision.decision_id,
        account_id=binding.account_id,
        calculated_at=_CALCULATED_AT,
        quantity=orders.OrderQuantity(Decimal("1.25")),
        entry_reference_price=orders.OrderPrice(Decimal("1.1000")),
        stop_loss=orders.OrderPrice(Decimal("1.0950")),
        take_profit=orders.OrderPrice(Decimal("1.1100")),
        estimated_risk=money.DrawdownBps(50),
        sizing_policy_ref=policy.sizing_policy_ref,
        protection_policy_ref=policy.protection_policy_ref,
        trailing_policy_ref=policy.trailing_policy_ref,
    )


class _KeySource:
    def __init__(self, snapshot: security.DecisionKeySnapshot) -> None:
        self.snapshot = snapshot

    def resolve(
        self,
        key_id: security.DecisionKeyId,
        version: security.DecisionKeyVersion,
        *,
        evaluated_at: datetime,
    ) -> result.Result[
        security.DecisionKeySnapshot,
        security.ClientDecisionSecurityError,
    ]:
        del evaluated_at
        if key_id != self.snapshot.key_id or version != self.snapshot.version:
            return result.Failure(
                security.ClientDecisionSecurityVerificationError(
                    "decision key resolution binding mismatch"
                )
            )
        return result.Success(self.snapshot)


class _CryptoVerifier:
    def __init__(self, decision: agent.CoreTradeDecision) -> None:
        self.decision = decision
        self.calls = 0

    def verify_and_decrypt(
        self,
        envelope: security.ClientDecisionEnvelope,
        key: security.DecisionKeySnapshot,
    ) -> result.Result[
        security.DecisionCryptographicVerification,
        security.ClientDecisionSecurityError,
    ]:
        del key
        self.calls += 1
        return result.Success(
            security.DecisionCryptographicVerification(
                decision=self.decision,
                protected_payload_digest=security.protected_payload_digest(
                    envelope.protected_payload
                ),
            )
        )


class _ReplayPort:
    def __init__(self) -> None:
        self.claims: dict[security.ClientDecisionReplayKey, str] = {}
        self.calls = 0

    def claim(
        self,
        key: security.ClientDecisionReplayKey,
        fingerprint: str,
    ) -> result.Result[
        security.ClientDecisionReplayClaim,
        security.ClientDecisionSecurityError,
    ]:
        self.calls += 1
        existing = self.claims.get(key)
        if existing is None:
            self.claims[key] = fingerprint
            status = security.ClientDecisionReplayClaimStatus.ACQUIRED
        elif existing == fingerprint:
            status = security.ClientDecisionReplayClaimStatus.DUPLICATE
        else:
            status = security.ClientDecisionReplayClaimStatus.CONFLICT
        return result.Success(
            security.ClientDecisionReplayClaim(
                key=key,
                fingerprint=fingerprint,
                status=status,
            )
        )


def _secret_ref() -> secrets.SecretRef:
    return secrets.SecretRef(
        ref_id=secrets.SecretRefId(_uuid(70)),
        name=adapter_configuration.AdapterSecretName("qore-decision-verification-key"),
        external_reference=secrets.SecretExternalReference(
            "qore/client-decision/verification-key"
        ),
    )


def _key() -> security.DecisionKeySnapshot:
    return security.DecisionKeySnapshot(
        key_id=security.DecisionKeyId(_uuid(71)),
        version=security.DecisionKeyVersion(1),
        status=security.DecisionKeyStatus.ACTIVE,
        material_ref=_secret_ref(),
        effective_at=_NOW - timedelta(days=1),
        expires_at=None,
    )


def _envelope(
    decision: agent.CoreTradeDecision,
    binding: accounts.ClientTradingAccountBinding,
    *,
    envelope_suffix: int,
) -> security.ClientDecisionEnvelope:
    key = _key()
    return security.ClientDecisionEnvelope(
        envelope_id=security.ClientDecisionEnvelopeId(_uuid(envelope_suffix)),
        protocol_version=security.DecisionProtocolVersion("qore.client-decision.v1"),
        protection_profile=security.DecisionProtectionProfile.SIGNED_ENCRYPTED,
        decision_id=decision.decision.decision_id,
        account_id=binding.account_id,
        runtime_ref=binding.runtime_ref,
        entitlement_ref=binding.product_entitlement_ref,
        issued_at=_ISSUED_AT,
        expires_at=decision.expires_at,
        nonce=security.DecisionNonce(
            f"mission07-{envelope_suffix:06d}".encode("ascii")
        ),
        key_id=key.key_id,
        key_version=key.version,
        protected_payload=security.ProtectedDecisionPayload(
            ciphertext=f"ciphertext-{envelope_suffix}".encode("ascii"),
            authentication_tag=b"mission07-auth-tag",
            signature=b"mission07-signature",
        ),
    )


def _secure(
    decision: agent.CoreTradeDecision,
    binding: accounts.ClientTradingAccountBinding,
    replay: _ReplayPort,
    *,
    envelope_suffix: int,
) -> result.Result[
    security.VerifiedClientDecision,
    security.ClientDecisionSecurityError,
]:
    return security.verify_client_decision_envelope(
        _envelope(decision, binding, envelope_suffix=envelope_suffix),
        binding,
        _KeySource(_key()),
        _CryptoVerifier(decision),
        replay,
        evidence_ref=agent.DecisionSecurityEvidenceReference(
            _uuid(envelope_suffix + 100)
        ),
        evaluated_at=_SECURITY_AT,
    )


def _evaluate_account(
    verified: security.VerifiedClientDecision,
    binding: accounts.ClientTradingAccountBinding,
    *,
    snapshot_suffix: int,
    observation_suffix: int,
    daily_loss_bps: int = 50,
) -> result.Result[agent.ClientExecutionEvaluation, agent.ClientExecutionAgentError]:
    execution_policy = _execution_policy()
    return agent.evaluate_client_execution(
        verified.decision,
        verified.attestation,
        binding,
        _account_policy(binding, snapshot_suffix=snapshot_suffix),
        _observed(
            binding,
            observation_suffix=observation_suffix,
            daily_loss_bps=daily_loss_bps,
        ),
        agent.ClientAgentEntitlementSnapshot(
            entitlement_ref=binding.product_entitlement_ref,
            account_id=binding.account_id,
            state=agent.ClientAgentEntitlementState.ENABLED,
            evaluated_at=_OBSERVED_AT,
        ),
        execution_policy,
        _calculation(verified.decision, binding, execution_policy),
        evaluated_at=_NOW,
    )


def _receipt(suffix: int, at: datetime) -> execution.ExecutionReceipt:
    return execution.ExecutionReceipt(
        receipt_id=execution.ExecutionReceiptId(_uuid(suffix)),
        request_id=execution.ExecutionRequestId(_uuid(suffix + 100)),
        idempotency_key=orders.ExecutionIdempotencyKey(_uuid(suffix + 200)),
        status=execution.ExecutionStatus.ACCEPTED,
        recorded_at=at,
    )


def _matched(
    receipt: execution.ExecutionReceipt,
    at: datetime,
) -> reconciliation.ExecutionReconciliationSnapshot:
    observation = reconciliation.ExecutionObservation(
        receipt_id=receipt.receipt_id,
        request_id=receipt.request_id,
        idempotency_key=receipt.idempotency_key,
        status=receipt.status,
        observed_at=at,
    )
    return reconciliation.ExecutionReconciliationSnapshot(
        status=reconciliation.ExecutionReconciliationStatus.MATCHED,
        reconciled_at=at,
        expected=receipt,
        observed=observation,
        issues=(),
    )


def _open_and_close(
    plan: agent.ClientExecutionPlan,
) -> tuple[
    lifecycle.ClientPositionLifecycle,
    execution.ExecutionReceipt,
]:
    entry_receipt = _receipt(300, _NOW + timedelta(seconds=1))
    confirmation = lifecycle.ClientExecutionConfirmation(
        plan=plan,
        receipt=entry_receipt,
        reconciliation=_matched(entry_receipt, _NOW + timedelta(seconds=2)),
        fill_price=plan.entry_reference_price,
        confirmed_at=_NOW + timedelta(seconds=3),
        evidence_ref=lifecycle.ClientPositionEvidenceReference(_uuid(301)),
    )
    opened = lifecycle.open_client_position(
        confirmation,
        position_id=lifecycle.ClientPositionId(_uuid(302)),
        action_id=lifecycle.ClientPositionActionId(_uuid(303)),
        rationale_code=lifecycle.ClientPositionRationaleCode("execution.confirmed"),
        opened_at=_NOW + timedelta(seconds=4),
    )
    assert isinstance(opened, result.Success)
    trailed = lifecycle.apply_client_trailing_stop(
        opened.value,
        action_id=lifecycle.ClientPositionActionId(_uuid(304)),
        new_stop=orders.OrderPrice(Decimal("1.1005")),
        evidence_ref=lifecycle.ClientPositionEvidenceReference(_uuid(305)),
        rationale_code=lifecycle.ClientPositionRationaleCode("trailing.policy_trigger"),
        occurred_at=_NOW + timedelta(seconds=5),
    )
    assert isinstance(trailed, result.Success)
    exit_receipt = _receipt(310, _NOW + timedelta(seconds=6))
    closed = lifecycle.close_client_position(
        trailed.value,
        exit_receipt,
        _matched(exit_receipt, _NOW + timedelta(seconds=7)),
        action_id=lifecycle.ClientPositionActionId(_uuid(311)),
        exit_price=orders.OrderPrice(Decimal("1.1080")),
        exit_reason=lifecycle.ClientPositionExitReason.TAKE_PROFIT,
        evidence_ref=lifecycle.ClientPositionEvidenceReference(_uuid(312)),
        rationale_code=lifecycle.ClientPositionRationaleCode("exit.take_profit"),
        closed_at=_NOW + timedelta(seconds=8),
    )
    assert isinstance(closed, result.Success)
    return closed.value, entry_receipt


def test_mission07_core_decision_to_position_is_account_scoped_and_replay_safe() -> None:
    decision = _decision()
    account_a = _binding(
        account_suffix=11,
        policy_suffix=12,
        entitlement_suffix=13,
        runtime_suffix=14,
    )
    account_b = _binding(
        account_suffix=21,
        policy_suffix=22,
        entitlement_suffix=23,
        runtime_suffix=24,
    )
    replay = _ReplayPort()

    secured_a = _secure(decision, account_a, replay, envelope_suffix=80)
    secured_b = _secure(decision, account_b, replay, envelope_suffix=81)
    duplicate_a = _secure(decision, account_a, replay, envelope_suffix=80)

    assert isinstance(secured_a, result.Success)
    assert isinstance(secured_b, result.Success)
    assert secured_a.value.decision.decision.decision_id == (
        secured_b.value.decision.decision.decision_id
    )
    assert secured_a.value.attestation.account_id != secured_b.value.attestation.account_id
    assert isinstance(duplicate_a, result.Failure)
    assert str(duplicate_a.error) == "decision replay duplicate rejected"
    assert len(replay.claims) == 2
    assert not hasattr(replay, "release")
    assert not hasattr(replay, "retry")

    evaluated_a = _evaluate_account(
        secured_a.value,
        account_a,
        snapshot_suffix=90,
        observation_suffix=93,
    )
    evaluated_b = _evaluate_account(
        secured_b.value,
        account_b,
        snapshot_suffix=100,
        observation_suffix=103,
        daily_loss_bps=500,
    )
    assert isinstance(evaluated_a, result.Success)
    assert evaluated_a.value.verdict is agent.ClientExecutionVerdict.EXECUTE
    plan_a = evaluated_a.value.plan
    assert plan_a is not None
    assert plan_a.account_id == account_a.account_id
    assert plan_a.decision_id == decision.decision.decision_id
    assert isinstance(evaluated_b, result.Success)
    assert evaluated_b.value.verdict is agent.ClientExecutionVerdict.RISK_BLOCKED
    assert evaluated_b.value.plan is None

    closed, _ = _open_and_close(plan_a)
    assert closed.state is lifecycle.ClientPositionState.CLOSED
    assert closed.plan.account_id == account_a.account_id
    assert closed.plan.decision_id == decision.decision.decision_id
    assert tuple(action.kind for action in closed.actions) == (
        lifecycle.ClientPositionActionKind.OPEN,
        lifecycle.ClientPositionActionKind.TRAILING_STOP,
        lifecycle.ClientPositionActionKind.EXIT,
    )
    assert all(action.decision_id == plan_a.decision_id for action in closed.actions)
    assert all(action.account_id == account_a.account_id for action in closed.actions)


def test_mission07_performance_trial_billing_and_vault_preserve_evidence_chain() -> None:
    decision = _decision()
    binding = _binding(
        account_suffix=11,
        policy_suffix=12,
        entitlement_suffix=13,
        runtime_suffix=14,
    )
    secured = _secure(decision, binding, _ReplayPort(), envelope_suffix=120)
    assert isinstance(secured, result.Success)
    evaluated = _evaluate_account(
        secured.value,
        binding,
        snapshot_suffix=130,
        observation_suffix=133,
    )
    assert isinstance(evaluated, result.Success)
    plan = evaluated.value.plan
    assert plan is not None
    closed, entry_receipt = _open_and_close(plan)

    client_ledger = performance.ClientPerformanceLedger(
        account_id=binding.account_id,
        currency=_USD,
    )
    realized = performance.append_realized_performance(
        client_ledger,
        closed,
        record_id=performance.ClientPerformanceRecordId(_uuid(400)),
        realized_pnl=_amount("100"),
        evidence_ref=performance.ClientPerformanceEvidenceReference(_uuid(401)),
        recorded_at=_NOW + timedelta(seconds=9),
    )
    assert isinstance(realized, result.Success)
    entitled = performance.ClientEntitledProfitRecord(
        record_id=performance.ClientPerformanceRecordId(_uuid(402)),
        account_id=binding.account_id,
        amount=_amount("80"),
        payout_policy_ref=performance.ClientPayoutPolicyReference(_uuid(403)),
        evaluated_at=_NOW + timedelta(seconds=10),
        evidence_ref=performance.ClientPerformanceEvidenceReference(_uuid(404)),
    )
    entitled_result = performance.append_entitled_profit(realized.value, entitled)
    assert isinstance(entitled_result, result.Success)
    paid = performance.ClientPaidProfitRecord(
        record_id=performance.ClientPerformanceRecordId(_uuid(405)),
        account_id=binding.account_id,
        entitlement_record_id=entitled.record_id,
        amount=_amount("80"),
        paid_at=_NOW + timedelta(days=1),
        payout_evidence_ref=performance.ClientPayoutEvidenceReference(_uuid(406)),
    )
    paid_result = performance.append_paid_profit(entitled_result.value, paid)
    assert isinstance(paid_result, result.Success)
    eligible = performance.EligibleClientPaidProfitRecord(
        record_id=performance.ClientPerformanceRecordId(_uuid(407)),
        account_id=binding.account_id,
        paid_profit_record_id=paid.record_id,
        amount=_amount("80"),
        payout_policy_ref=entitled.payout_policy_ref,
        evaluated_at=_NOW + timedelta(days=1, seconds=1),
        evidence_ref=performance.ClientPerformanceEvidenceReference(_uuid(408)),
    )
    eligible_result = performance.append_eligible_paid_profit(
        paid_result.value,
        eligible,
    )
    assert isinstance(eligible_result, result.Success)
    assert eligible_result.value.net_realized_pnl == _amount("100")

    license_snapshot = licensing.ClientAgentLicenseSnapshot(
        account_id=binding.account_id,
        entitlement_ref=binding.product_entitlement_ref,
        trial_state=licensing.ClientTrialState.NOT_STARTED,
        license_state=licensing.ClientLicenseState.TRIAL_PENDING,
        trial_started_at=None,
        trial_expires_at=None,
        first_live_evidence_ref=None,
        updated_at=_NOW - timedelta(minutes=1),
        evidence_ref=licensing.LicensingEvidenceReference(_uuid(420)),
    )
    trial_evidence = licensing.FirstEligibleLiveExecutionEvidence(
        account_id=binding.account_id,
        entitlement_ref=binding.product_entitlement_ref,
        decision_id=decision.decision.decision_id,
        execution_receipt_id=entry_receipt.receipt_id,
        eligibility=licensing.TrialExecutionEligibility.ELIGIBLE_LIVE,
        executed_at=_NOW + timedelta(seconds=4),
        evidence_ref=licensing.TrialEvidenceReference(_uuid(421)),
    )
    trial = licensing.start_client_trial(
        license_snapshot,
        trial_evidence,
        evidence_ref=licensing.LicensingEvidenceReference(_uuid(422)),
    )
    assert isinstance(trial, result.Success)
    assert trial.value.trial_expires_at == (
        trial_evidence.executed_at + timedelta(days=14)
    )

    ea_product = products.CommercialProduct(
        product_id=products.CommercialProductId(_uuid(430)),
        kind=products.CommercialProductKind.CLIENT_EXECUTION_AGENT,
        availability=products.CommercialProductAvailability.CONFIRMED,
    )
    ea_plan = products.CommercialPlan(
        plan_id=products.CommercialPlanId(_uuid(431)),
        version=products.CommercialPlanVersion(1),
        product=ea_product,
        billing_unit=products.CommercialBillingUnit.ACCOUNT,
        cadence=products.CommercialBillingCadence.MONTHLY,
        price=_amount("29"),
    )
    invoice = billing.CommercialInvoice.from_plan(
        invoice_id=billing.CommercialInvoiceId(_uuid(432)),
        client_id=binding.client_id,
        account_id=binding.account_id,
        plan=ea_plan,
        period_started_at=_NOW,
        period_ended_at=_NOW + timedelta(days=30),
        issued_at=_NOW,
        due_at=_NOW + timedelta(days=7),
    )
    billing_result = billing.append_invoice(billing.CommercialBillingLedger(), invoice)
    assert isinstance(billing_result, result.Success)
    billing_ledger = billing_result.value
    assert billing_ledger.invoice_status(invoice.invoice_id) is (
        billing.CommercialInvoiceStatus.DUE
    )

    revenue = vault.attribute_invoice_revenue(
        invoice,
        record_id=vault.CorporateVaultRecordId(_uuid(440)),
        attributed_at=_NOW,
    )
    receivable = vault.snapshot_accounts_receivable(
        billing_ledger,
        invoice.invoice_id,
        record_id=vault.CorporateVaultRecordId(_uuid(441)),
        recorded_at=_NOW,
    )
    corporate = vault.CorporateProfitVault(
        revenue_attributions=(revenue,),
        receivables=(receivable,),
    )
    assert corporate.cash_received == ()
    assert receivable.state is vault.CorporateReceivableState.OPEN

    payment = billing.VerifiedCommercialPayment(
        payment_id=billing.CommercialPaymentId(_uuid(450)),
        client_id=binding.client_id,
        amount=_amount("29"),
        paid_at=_NOW + timedelta(days=1),
        verification=billing.CommercialPaymentVerification.VERIFIED,
        evidence_ref=billing.CommercialPaymentEvidenceReference(_uuid(451)),
    )
    with_payment = billing.append_verified_payment(billing_ledger, payment)
    assert isinstance(with_payment, result.Success)
    allocation = billing.CommercialPaymentAllocation(
        allocation_id=billing.CommercialPaymentAllocationId(_uuid(452)),
        invoice_id=invoice.invoice_id,
        payment_id=payment.payment_id,
        amount=_amount("29"),
        allocated_at=_NOW + timedelta(days=1, seconds=1),
        evidence_ref=billing.CommercialBillingEvidenceReference(_uuid(453)),
    )
    allocated = billing.allocate_verified_payment(with_payment.value, allocation)
    assert isinstance(allocated, result.Success)
    assert allocated.value.invoice_status(invoice.invoice_id) is (
        billing.CommercialInvoiceStatus.PAID
    )
    cash = vault.cash_received_from_allocation(
        allocated.value,
        allocation.allocation_id,
        record_id=vault.CorporateVaultRecordId(_uuid(454)),
        recorded_at=_NOW + timedelta(days=1, seconds=2),
    )
    cash_result = vault.append_cash_received(corporate, cash)
    assert isinstance(cash_result, result.Success)
    assert cash.payment_evidence_ref == payment.evidence_ref

    fee_policy = billing.PerformanceFeePolicy(
        policy_id=billing.PerformanceFeePolicyId(_uuid(460)),
        version=billing.PerformanceFeePolicyVersion(1),
    )
    assessment = billing.calculate_performance_fee(fee_policy, eligible)
    assert assessment.fee_amount == _amount("16")
    fee_revenue = vault.attribute_performance_fee_revenue(
        assessment,
        client_id=binding.client_id,
        record_id=vault.CorporateVaultRecordId(_uuid(461)),
        period_started_at=_NOW,
        period_ended_at=_NOW + timedelta(days=30),
        attributed_at=_NOW + timedelta(days=1),
    )
    assert fee_revenue.eligible_paid_profit_record_id == eligible.record_id
    assert fee_revenue.amount == _amount("16")


def test_mission07_safe_suspension_and_widget_are_isolated_from_execution() -> None:
    client_id = accounts.ClientId(_uuid(10))
    account_a = accounts.TradingAccountId(_uuid(11))
    account_b = accounts.TradingAccountId(_uuid(21))
    entitlement = accounts.ProductEntitlementReference(_uuid(13))
    started_at = _NOW - timedelta(days=1)
    license_snapshot = licensing.ClientAgentLicenseSnapshot(
        account_id=account_a,
        entitlement_ref=entitlement,
        trial_state=licensing.ClientTrialState.ACTIVE,
        license_state=licensing.ClientLicenseState.TRIAL_ACTIVE,
        trial_started_at=started_at,
        trial_expires_at=started_at + timedelta(days=14),
        first_live_evidence_ref=licensing.TrialEvidenceReference(_uuid(500)),
        updated_at=_NOW - timedelta(seconds=10),
        evidence_ref=licensing.LicensingEvidenceReference(_uuid(501)),
    )
    suspended = licensing.evaluate_client_license(
        license_snapshot,
        payment_standing=licensing.CommercialPaymentStanding.PAYMENT_FAILED,
        open_positions=1,
        evaluated_at=_NOW,
        evidence_ref=licensing.LicensingEvidenceReference(_uuid(502)),
    )
    assert isinstance(suspended, result.Success)
    assert suspended.value.license_state is (
        licensing.ClientLicenseState.SUSPEND_PENDING_FLAT
    )
    assert licensing.project_agent_entitlement(
        suspended.value,
        evaluated_at=_NOW,
    ).state is agent.ClientAgentEntitlementState.BLOCKED
    assert not hasattr(suspended.value, "close_position")

    account_snapshot_a = read_model.ClientAccountReadSnapshot(
        client_id=client_id,
        account_id=account_a,
        account_state=accounts.TradingAccountLifecycleState.ACTIVE,
        balance=_amount("10100"),
        generated_today=_amount("100"),
        generated_week=_amount("250"),
        service_status=read_model.ClientServiceStatus.ONLINE,
        license_state=suspended.value.license_state,
        billing_state=billing.CommercialBillingStandingState.PAYMENT_FAILED,
        trade_pulses=(),
        captured_at=_NOW,
    )
    account_snapshot_b = read_model.ClientAccountReadSnapshot(
        client_id=client_id,
        account_id=account_b,
        account_state=accounts.TradingAccountLifecycleState.ACTIVE,
        balance=_amount("5000"),
        generated_today=_amount("25"),
        generated_week=_amount("75"),
        service_status=read_model.ClientServiceStatus.ONLINE,
        license_state=licensing.ClientLicenseState.LICENSED,
        billing_state=billing.CommercialBillingStandingState.CURRENT,
        trade_pulses=(),
        captured_at=_NOW,
    )
    generated_at = _NOW + timedelta(seconds=1)
    client_read_model = read_model.build_client_multiaccount_read_model(
        read_model_id=read_model.ClientReadModelId(_uuid(510)),
        client_id=client_id,
        today_window=read_model.ClientPerformanceWindow(
            started_at=generated_at - timedelta(hours=15),
            ended_at=generated_at,
        ),
        week_window=read_model.ClientPerformanceWindow(
            started_at=generated_at - timedelta(days=6, hours=15),
            ended_at=generated_at,
        ),
        accounts=(account_snapshot_b, account_snapshot_a),
        generated_at=generated_at,
    )
    assert len(client_read_model.accounts) == 2
    assert client_read_model.currency_summaries[0].balance == _amount("15100")

    widget_product = products.CommercialProduct(
        product_id=products.CommercialProductId(_uuid(520)),
        kind=products.CommercialProductKind.CLIENT_WIDGET,
        availability=products.CommercialProductAvailability.CONFIRMED,
    )
    widget_plan = products.CommercialPlan(
        plan_id=products.CommercialPlanId(_uuid(521)),
        version=products.CommercialPlanVersion(1),
        product=widget_product,
        billing_unit=products.CommercialBillingUnit.CLIENT,
        cadence=products.CommercialBillingCadence.MONTHLY,
        price=money.MoneyAmount(currency=_USD, amount=Decimal("9.99")),
    )
    widget_standing = widget.ClientWidgetCommercialStanding.from_plan(
        client_id=client_id,
        plan=widget_plan,
        billing_state=billing.CommercialBillingStandingState.PAYMENT_FAILED,
        evaluated_at=generated_at,
        evidence_ref=billing.CommercialBillingEvidenceReference(_uuid(522)),
    )
    widget_view = widget.build_client_widget_view_model(
        widget_id=widget.ClientWidgetId(_uuid(523)),
        standing=widget_standing,
        read_model=client_read_model,
        generated_at=generated_at,
    )
    assert widget_view.access_state is widget.ClientWidgetAccessState.SUSPENDED
    assert widget_view.read_model is None
    assert len(client_read_model.accounts) == 2
    assert client_read_model.accounts[1].license_state is (
        licensing.ClientLicenseState.LICENSED
    )
    assert not hasattr(widget_view, "suspend_ea")
    assert not hasattr(widget_view, "set_risk")
    assert not hasattr(widget_view, "submit_order")
