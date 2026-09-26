"""FundedNext CIBO seed bridge.

Risk exposes hard constraints; CIBO chooses the minimum executable volume.
No Trader sizing inputs are accepted.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from qore.infrastructure.account_wide_risk import (
    AccountRiskSnapshot,
)
from qore.infrastructure.account_wide_risk_ledger import (
    DurableAccountWideRiskEngine,
)
from qore.infrastructure.cibo_capital_management_authority import (
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_cma_initial_seed import (
    CmaInitialSeed,
    build_initial_seed_from_risk_constraints,
)


def build_fundednext_cibo_seed(
    *,
    request_id: str,
    opportunity: TraderOpportunityEnvelope,
    risk: DurableAccountWideRiskEngine,
    snapshot: AccountRiskSnapshot,
    assigned_capital_usd: Decimal,
    requested_at: datetime,
    expires_at: datetime,
) -> CmaInitialSeed:
    """Build one CIBO seed strictly inside current sovereign Risk constraints."""

    if risk.recovery_required:
        risk.complete_boot_reconciliation(snapshot, now=requested_at)
    constraints = risk.capital_constraint_envelope(
        snapshot,
        now=requested_at,
    )
    return build_initial_seed_from_risk_constraints(
        request_id=request_id,
        opportunity=opportunity,
        assigned_capital_usd=assigned_capital_usd,
        constraints=constraints,
        requested_at=requested_at,
        expires_at=expires_at,
    )
