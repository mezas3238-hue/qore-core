"""QORE Risk snapshot bridge for CIBO single-account ceiling discovery.

The bridge derives only facts owned by the CIBO replay account (equity and open
exposure). Provider limits, free margin and broker-side pending risk remain
explicit caller inputs so historical research never invents provider evidence.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from qore.infrastructure.account_wide_risk import (
    AccountRiskSnapshot,
    ProviderRiskBudget,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_single_account_ceiling_state import (
    CiboCeilingAccountState,
)


def _nonnegative(value: Decimal, name: str) -> None:
    if (
        not isinstance(value, Decimal)
        or not value.is_finite()
        or value < 0
    ):
        raise CiboCapitalManagementError(
            f"ceiling Risk {name} must be finite non-negative Decimal"
        )


def build_ceiling_risk_snapshot(
    *,
    account: CiboCeilingAccountState,
    provider_budget: ProviderRiskBudget,
    reconciled_at: datetime,
    provider_free_margin_usd: Decimal,
    open_floating_loss_usd: Decimal,
    pending_broker_worst_case_loss_usd: Decimal,
    qore_authorizable_headroom_usd: Decimal,
) -> AccountRiskSnapshot:
    """Bind one causal account state to an explicit provider Risk budget."""

    if not isinstance(account, CiboCeilingAccountState):
        raise CiboCapitalManagementError(
            "ceiling Risk snapshot requires canonical account state"
        )
    if reconciled_at.tzinfo is None or reconciled_at.utcoffset() is None:
        raise CiboCapitalManagementError(
            "ceiling Risk reconciled_at must be timezone-aware"
        )
    for value, name in (
        (provider_free_margin_usd, "provider_free_margin_usd"),
        (open_floating_loss_usd, "open_floating_loss_usd"),
        (
            pending_broker_worst_case_loss_usd,
            "pending_broker_worst_case_loss_usd",
        ),
        (
            qore_authorizable_headroom_usd,
            "qore_authorizable_headroom_usd",
        ),
    ):
        _nonnegative(value, name)

    equity = account.realized_capital_usd
    open_stop = sum(
        (item.stop_risk_usd for item in account.open_exposures),
        Decimal(0),
    )
    margin_used = sum(
        (item.margin_usd for item in account.open_exposures),
        Decimal(0),
    )
    if qore_authorizable_headroom_usd > equity:
        raise CiboCapitalManagementError(
            "ceiling Risk internal headroom cannot exceed realized equity"
        )

    return AccountRiskSnapshot(
        account_binding_id=account.account_identity.account_ref,
        equity=equity,
        margin_used=margin_used,
        free_margin=provider_free_margin_usd,
        open_stop_worst_case_loss=open_stop,
        open_floating_loss=open_floating_loss_usd,
        pending_broker_worst_case_loss=pending_broker_worst_case_loss_usd,
        qore_authorizable_headroom=qore_authorizable_headroom_usd,
        provider_budget=provider_budget,
        reconciled_at=reconciled_at,
    )
