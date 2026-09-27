from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.account_wide_risk import (
    AccountRiskSnapshot,
    RiskCapitalConstraintEnvelope,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CapitalSource,
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_capital_source_ledger import CapitalSourceLedger
from qore.infrastructure.cibo_capital_source_ledger_store import (
    VersionedCapitalSourceLedger,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_snapshots import (
    build_phase20_forward_snapshot_bundle,
)

OBSERVED_AT = datetime(2026, 9, 27, 15, 0, tzinfo=UTC)


@dataclass(frozen=True)
class _ProviderBudget:
    provider_headroom: Decimal = Decimal("100")
    max_risk_at_any_time: Decimal = Decimal("100")
    active_mll: Decimal = Decimal("1000")
    hard_breach: bool = False


def _account(*, account: str = "account-1") -> AccountRiskSnapshot:
    return AccountRiskSnapshot(
        account_binding_id=account,
        equity=Decimal("2000"),
        margin_used=Decimal("100"),
        free_margin=Decimal("1900"),
        open_stop_worst_case_loss=Decimal("10"),
        open_floating_loss=Decimal("0"),
        pending_broker_worst_case_loss=Decimal("0"),
        qore_authorizable_headroom=Decimal("100"),
        provider_budget=_ProviderBudget(),
        reconciled_at=OBSERVED_AT,
    )


def _constraints(
    *,
    account: str = "account-1",
    reconciled_at: datetime = OBSERVED_AT,
) -> RiskCapitalConstraintEnvelope:
    return RiskCapitalConstraintEnvelope(
        account_binding_id=account,
        aggregate_pre_order_worst_case_usd=Decimal("10"),
        active_reserved_stop_risk_usd=Decimal("0"),
        active_reserved_margin_usd=Decimal("0"),
        provider_remaining_headroom_usd=Decimal("90"),
        internal_qore_remaining_headroom_usd=Decimal("90"),
        max_risk_remaining_usd=Decimal("90"),
        hard_risk_headroom_usd=Decimal("90"),
        margin_headroom_usd=Decimal("1900"),
        provider_hard_breach=False,
        survival_blocked=False,
        reason="hard-constraints-observed",
        reconciled_at=reconciled_at,
    )


def _capital(*, generation: int = 1) -> VersionedCapitalSourceLedger:
    ledger = CapitalSourceLedger().add_source(
        source_id="base-1",
        source=CapitalSource.ORIGINAL_BASE_CAPITAL,
        proven_amount_usd=Decimal("100"),
    )
    return VersionedCapitalSourceLedger(
        generation=generation,
        ledger=ledger,
    )


def test_forward_snapshot_bundle_is_deterministic_and_content_bound() -> None:
    first = build_phase20_forward_snapshot_bundle(
        account_snapshot=_account(),
        risk_constraints=_constraints(),
        capital_state=_capital(),
        captured_at=OBSERVED_AT + timedelta(seconds=1),
    )
    second = build_phase20_forward_snapshot_bundle(
        account_snapshot=_account(),
        risk_constraints=_constraints(),
        capital_state=_capital(),
        captured_at=OBSERVED_AT + timedelta(seconds=1),
    )

    assert first == second
    assert first.capital_snapshot_id.startswith("sha256:")
    assert first.risk_snapshot_id.startswith("sha256:")
    assert first.hard_risk_headroom_usd == Decimal("90")
    assert first.margin_headroom_usd == Decimal("1900")


def test_forward_capital_digest_changes_with_generation() -> None:
    first = build_phase20_forward_snapshot_bundle(
        account_snapshot=_account(),
        risk_constraints=_constraints(),
        capital_state=_capital(generation=1),
        captured_at=OBSERVED_AT + timedelta(seconds=1),
    )
    second = build_phase20_forward_snapshot_bundle(
        account_snapshot=_account(),
        risk_constraints=_constraints(),
        capital_state=_capital(generation=2),
        captured_at=OBSERVED_AT + timedelta(seconds=1),
    )

    assert first.capital_snapshot_id != second.capital_snapshot_id
    assert first.risk_snapshot_id == second.risk_snapshot_id


def test_forward_risk_digest_changes_with_account_state() -> None:
    base = _account()
    changed = AccountRiskSnapshot(
        account_binding_id=base.account_binding_id,
        equity=Decimal("1999"),
        margin_used=base.margin_used,
        free_margin=base.free_margin,
        open_stop_worst_case_loss=base.open_stop_worst_case_loss,
        open_floating_loss=base.open_floating_loss,
        pending_broker_worst_case_loss=base.pending_broker_worst_case_loss,
        qore_authorizable_headroom=base.qore_authorizable_headroom,
        provider_budget=base.provider_budget,
        reconciled_at=base.reconciled_at,
    )
    first = build_phase20_forward_snapshot_bundle(
        account_snapshot=base,
        risk_constraints=_constraints(),
        capital_state=_capital(),
        captured_at=OBSERVED_AT + timedelta(seconds=1),
    )
    second = build_phase20_forward_snapshot_bundle(
        account_snapshot=changed,
        risk_constraints=_constraints(),
        capital_state=_capital(),
        captured_at=OBSERVED_AT + timedelta(seconds=1),
    )

    assert first.risk_snapshot_id != second.risk_snapshot_id


def test_forward_snapshot_rejects_risk_account_mismatch() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="Risk/account binding mismatch",
    ):
        build_phase20_forward_snapshot_bundle(
            account_snapshot=_account(),
            risk_constraints=_constraints(account="account-2"),
            capital_state=_capital(),
            captured_at=OBSERVED_AT + timedelta(seconds=1),
        )


def test_forward_snapshot_rejects_reconciliation_timestamp_mismatch() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="reconciliation timestamp mismatch",
    ):
        build_phase20_forward_snapshot_bundle(
            account_snapshot=_account(),
            risk_constraints=_constraints(
                reconciled_at=OBSERVED_AT - timedelta(seconds=1)
            ),
            capital_state=_capital(),
            captured_at=OBSERVED_AT + timedelta(seconds=1),
        )


def test_forward_snapshot_rejects_capture_before_reconciliation() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="capture cannot predate",
    ):
        build_phase20_forward_snapshot_bundle(
            account_snapshot=_account(),
            risk_constraints=_constraints(),
            capital_state=_capital(),
            captured_at=OBSERVED_AT - timedelta(microseconds=1),
        )
