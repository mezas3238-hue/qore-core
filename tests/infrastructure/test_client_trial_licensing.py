from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import qore.functional.decisions as decisions
import qore.infrastructure.client_accounts as accounts
import qore.infrastructure.client_execution_agent as agent
import qore.infrastructure.client_trial_licensing as licensing
import qore.infrastructure.execution_boundary as execution
import qore.kernel.result as result

_NOW = datetime(2026, 8, 9, 11, 0, tzinfo=UTC)


def _uuid(suffix: int) -> UUID:
    return UUID(f"37000000-0000-0000-0000-{suffix:012d}")


def _snapshot() -> licensing.ClientAgentLicenseSnapshot:
    return licensing.ClientAgentLicenseSnapshot(
        account_id=accounts.TradingAccountId(_uuid(1)),
        entitlement_ref=accounts.ProductEntitlementReference(_uuid(2)),
        trial_state=licensing.ClientTrialState.NOT_STARTED,
        license_state=licensing.ClientLicenseState.TRIAL_PENDING,
        trial_started_at=None,
        trial_expires_at=None,
        first_live_evidence_ref=None,
        updated_at=_NOW,
        evidence_ref=licensing.LicensingEvidenceReference(_uuid(3)),
    )


def _live_evidence(
    snapshot: licensing.ClientAgentLicenseSnapshot,
    *,
    eligibility: licensing.TrialExecutionEligibility = (
        licensing.TrialExecutionEligibility.ELIGIBLE_LIVE
    ),
) -> licensing.FirstEligibleLiveExecutionEvidence:
    return licensing.FirstEligibleLiveExecutionEvidence(
        account_id=snapshot.account_id,
        entitlement_ref=snapshot.entitlement_ref,
        decision_id=decisions.DecisionId(_uuid(4)),
        execution_receipt_id=execution.ExecutionReceiptId(_uuid(5)),
        eligibility=eligibility,
        executed_at=_NOW + timedelta(hours=1),
        evidence_ref=licensing.TrialEvidenceReference(_uuid(6)),
    )


def _start_trial() -> licensing.ClientAgentLicenseSnapshot:
    snapshot = _snapshot()
    started = licensing.start_client_trial(
        snapshot,
        _live_evidence(snapshot),
        evidence_ref=licensing.LicensingEvidenceReference(_uuid(7)),
    )
    assert isinstance(started, result.Success)
    return started.value


def test_trial_starts_only_on_first_eligible_live_execution() -> None:
    snapshot = _snapshot()
    evidence = _live_evidence(snapshot)

    started = licensing.start_client_trial(
        snapshot,
        evidence,
        evidence_ref=licensing.LicensingEvidenceReference(_uuid(7)),
    )

    assert isinstance(started, result.Success)
    assert started.value.trial_state is licensing.ClientTrialState.ACTIVE
    assert started.value.license_state is licensing.ClientLicenseState.TRIAL_ACTIVE
    assert started.value.trial_started_at == evidence.executed_at
    assert started.value.trial_expires_at == evidence.executed_at + timedelta(days=14)
    assert started.value.first_live_evidence_ref == evidence.evidence_ref
    assert started.value.allows_new_trades is True


def test_install_download_or_noneligible_execution_cannot_start_trial() -> None:
    snapshot = _snapshot()
    evidence = _live_evidence(
        snapshot,
        eligibility=licensing.TrialExecutionEligibility.NOT_ELIGIBLE,
    )

    started = licensing.start_client_trial(
        snapshot,
        evidence,
        evidence_ref=licensing.LicensingEvidenceReference(_uuid(7)),
    )

    assert isinstance(started, result.Failure)
    assert snapshot.trial_state is licensing.ClientTrialState.NOT_STARTED
    assert not hasattr(snapshot, "installed_at")
    assert not hasattr(snapshot, "downloaded_at")
    assert not hasattr(snapshot, "registered_at")


def test_trial_start_and_expiry_are_immutable_and_cannot_be_reset() -> None:
    started = _start_trial()
    second_evidence = _live_evidence(started)

    restarted = licensing.start_client_trial(
        started,
        second_evidence,
        evidence_ref=licensing.LicensingEvidenceReference(_uuid(8)),
    )

    assert isinstance(restarted, result.Failure)
    assert str(restarted.error) == "trial has already been started"
    assert started.trial_started_at is not None
    assert started.trial_expires_at == started.trial_started_at + timedelta(days=14)


def test_runtime_host_change_cannot_reset_account_scoped_trial() -> None:
    started = _start_trial()

    assert not hasattr(started, "runtime_ref")
    assert not hasattr(started, "device_id")
    assert not hasattr(started, "vps_id")
    assert started.account_id == accounts.TradingAccountId(_uuid(1))


def test_trial_expiry_blocks_new_entries_but_preserves_open_position_lifecycle() -> None:
    started = _start_trial()
    assert started.trial_expires_at is not None

    evaluated = licensing.evaluate_client_license(
        started,
        payment_standing=licensing.CommercialPaymentStanding.CURRENT,
        open_positions=1,
        evaluated_at=started.trial_expires_at,
        evidence_ref=licensing.LicensingEvidenceReference(_uuid(9)),
    )

    assert isinstance(evaluated, result.Success)
    value = evaluated.value
    assert value.trial_state is licensing.ClientTrialState.EXPIRED
    assert value.license_state is licensing.ClientLicenseState.SUSPEND_PENDING_FLAT
    assert value.allows_new_trades is False
    projected = licensing.project_agent_entitlement(
        value,
        evaluated_at=value.updated_at,
    )
    assert projected.state is agent.ClientAgentEntitlementState.BLOCKED
    assert not hasattr(value, "close_position")


def test_payment_failure_moves_to_pending_flat_then_suspended() -> None:
    started = _start_trial()
    failed = licensing.evaluate_client_license(
        started,
        payment_standing=licensing.CommercialPaymentStanding.PAYMENT_FAILED,
        open_positions=2,
        evaluated_at=_NOW + timedelta(days=1),
        evidence_ref=licensing.LicensingEvidenceReference(_uuid(10)),
    )
    assert isinstance(failed, result.Success)
    assert failed.value.license_state is licensing.ClientLicenseState.SUSPEND_PENDING_FLAT
    assert failed.value.allows_new_trades is False

    flat = licensing.evaluate_client_license(
        failed.value,
        payment_standing=licensing.CommercialPaymentStanding.PAYMENT_FAILED,
        open_positions=0,
        evaluated_at=_NOW + timedelta(days=1, seconds=1),
        evidence_ref=licensing.LicensingEvidenceReference(_uuid(11)),
    )
    assert isinstance(flat, result.Success)
    assert flat.value.license_state is licensing.ClientLicenseState.SUSPENDED


def test_unknown_commercial_state_fails_closed_for_new_trades() -> None:
    started = _start_trial()
    evaluated = licensing.evaluate_client_license(
        started,
        payment_standing=licensing.CommercialPaymentStanding.UNKNOWN,
        open_positions=0,
        evaluated_at=_NOW + timedelta(days=1),
        evidence_ref=licensing.LicensingEvidenceReference(_uuid(12)),
    )

    assert isinstance(evaluated, result.Success)
    assert evaluated.value.license_state is licensing.ClientLicenseState.SUSPENDED
    assert licensing.project_agent_entitlement(
        evaluated.value,
        evaluated_at=evaluated.value.updated_at,
    ).state is agent.ClientAgentEntitlementState.BLOCKED


def test_paid_license_activation_does_not_modify_trial_origin() -> None:
    started = _start_trial()
    activated = licensing.activate_paid_license(
        started,
        activated_at=_NOW + timedelta(days=2),
        evidence_ref=licensing.LicensingEvidenceReference(_uuid(13)),
    )

    assert isinstance(activated, result.Success)
    assert activated.value.license_state is licensing.ClientLicenseState.LICENSED
    assert activated.value.trial_started_at == started.trial_started_at
    assert activated.value.trial_expires_at == started.trial_expires_at
    assert activated.value.first_live_evidence_ref == started.first_live_evidence_ref
    assert activated.value.allows_new_trades is True


def test_licensing_has_no_price_billing_or_trade_close_authority() -> None:
    assert not hasattr(licensing.ClientAgentLicenseSnapshot, "monthly_price")
    assert not hasattr(licensing.ClientAgentLicenseSnapshot, "charge")
    assert not hasattr(licensing.ClientAgentLicenseSnapshot, "close_trade")
    assert not hasattr(licensing.ClientAgentLicenseSnapshot, "submit_order")
