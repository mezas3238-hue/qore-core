"""Deterministic CE2I expansion policy pipeline V1.

Pipeline:
T11 execution-efficiency cap
-> choose one reconciled non-base economic source
-> T06/T07 expansion funding
-> T19 atomic reservation
-> build QORE Risk request

Research-only. No broker mutation and no Risk bypass.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_FLOOR, Decimal

from qore.infrastructure.cibo_capital_management_authority import (
    CapitalSource,
    CiboCapitalManagementError,
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_capital_source_ledger import CapitalSourceAccount
from qore.infrastructure.cibo_capital_source_ledger_store import (
    DurableCapitalSourceLedgerStore,
)
from qore.infrastructure.cibo_cma_capital_observation import CmaCapitalObservation
from qore.infrastructure.cibo_ce2i_execution_efficiency import (
    ExecutionCostCurveInput,
    ExecutionEfficientCap,
    execution_efficient_volume_cap,
)
from qore.infrastructure.cibo_ce2i_expansion_proposal import (
    CmaExpansionProposal,
    reserve_expansion_proposal,
)
from qore.infrastructure.cibo_ce2i_tool_registry import tool_by_code


@dataclass(frozen=True, slots=True)
class Ce2iExpansionPolicyDecision:
    applied_tools: tuple[str, ...]
    execution_cap: ExecutionEfficientCap
    proposal: CmaExpansionProposal | None
    reason: str

    def __post_init__(self) -> None:
        for code in self.applied_tools:
            tool_by_code(code)
        if self.proposal is None and "T19" in self.applied_tools:
            raise CiboCapitalManagementError(
                "T19 cannot be reported without durable reservation"
            )
        if self.proposal is not None and "T19" not in self.applied_tools:
            raise CiboCapitalManagementError(
                "reserved proposal must report T19"
            )


def propose_ce2i_expansion(
    *,
    reservation_id: str,
    request_id: str,
    opportunity: TraderOpportunityEnvelope,
    observation: CmaCapitalObservation,
    execution_curve: ExecutionCostCurveInput,
    assigned_capital_usd: Decimal,
    hard_risk_headroom_usd: Decimal,
    margin_headroom_usd: Decimal,
    requested_at: datetime,
    expires_at: datetime,
    ledger_store: DurableCapitalSourceLedgerStore,
) -> Ce2iExpansionPolicyDecision:
    """Select and reserve one bounded expansion source deterministically."""

    if execution_curve.volume_step != opportunity.volume_step:
        raise CiboCapitalManagementError(
            "execution curve volume step does not match opportunity"
        )
    if not observation.expansion_eligible or not observation.evidence_sufficient:
        cap = execution_efficient_volume_cap(execution_curve)
        return Ce2iExpansionPolicyDecision(
            applied_tools=("T11",),
            execution_cap=cap,
            proposal=None,
            reason="CMA capital observation is not expansion eligible",
        )

    cap = execution_efficient_volume_cap(execution_curve)
    if cap.volume_cap < opportunity.minimum_volume:
        return Ce2iExpansionPolicyDecision(
            applied_tools=("T11",),
            execution_cap=cap,
            proposal=None,
            reason="execution economics reject executable expansion minimum",
        )

    version = ledger_store.load()
    candidate = _select_single_source(
        accounts=version.ledger.accounts,
        observation=observation,
        opportunity=opportunity,
        execution_cap=cap.volume_cap,
        hard_risk_headroom_usd=hard_risk_headroom_usd,
        margin_headroom_usd=margin_headroom_usd,
    )
    if candidate is None:
        return Ce2iExpansionPolicyDecision(
            applied_tools=("T11",),
            execution_cap=cap,
            proposal=None,
            reason=(
                "no single reconciled economic source can fund executable "
                "expansion; multi-source policy not yet enabled"
            ),
        )

    source_code = (
        "T06"
        if candidate.source is CapitalSource.REALIZED_PROFIT
        else "T07"
    )
    proposal = reserve_expansion_proposal(
        reservation_id=reservation_id,
        source_id=candidate.source_id,
        opportunity=opportunity,
        observation=observation,
        hard_risk_headroom_usd=hard_risk_headroom_usd,
        margin_headroom_usd=margin_headroom_usd,
        assigned_capital_usd=assigned_capital_usd,
        requested_at=requested_at,
        expires_at=expires_at,
        request_id=request_id,
        ledger_store=ledger_store,
        maximum_expansion_volume=cap.volume_cap,
    )
    return Ce2iExpansionPolicyDecision(
        applied_tools=("T11", source_code, "T19"),
        execution_cap=cap,
        proposal=proposal,
        reason=(
            "execution-efficient self-financing expansion reserved for Risk review"
        ),
    )


def _select_single_source(
    *,
    accounts: tuple[CapitalSourceAccount, ...],
    observation: CmaCapitalObservation,
    opportunity: TraderOpportunityEnvelope,
    execution_cap: Decimal,
    hard_risk_headroom_usd: Decimal,
    margin_headroom_usd: Decimal,
) -> CapitalSourceAccount | None:
    """Prefer realized cash, then protected floor; choose largest available lot."""

    source_priority = (
        CapitalSource.REALIZED_PROFIT,
        CapitalSource.PROTECTED_ECONOMIC_FLOOR,
    )
    for source in source_priority:
        candidates = sorted(
            (
                account
                for account in accounts
                if account.source is source and account.available_usd > 0
            ),
            key=lambda account: (-account.available_usd, account.source_id),
        )
        for account in candidates:
            observed = _observed_source_capacity(observation, source)
            available_risk = min(
                account.available_usd,
                observed,
                observation.self_financing_capacity_usd or Decimal(0),
                hard_risk_headroom_usd,
            )
            if available_risk <= 0:
                continue
            by_risk = available_risk / opportunity.stop_loss_per_volume
            by_margin = margin_headroom_usd / opportunity.margin_per_volume
            raw = min(
                by_risk,
                by_margin,
                execution_cap,
                opportunity.maximum_volume,
            )
            steps = (raw / opportunity.volume_step).to_integral_value(
                rounding=ROUND_FLOOR
            )
            volume = steps * opportunity.volume_step
            if volume >= opportunity.minimum_volume:
                return account
    return None


def _observed_source_capacity(
    observation: CmaCapitalObservation,
    source: CapitalSource,
) -> Decimal:
    if source is CapitalSource.REALIZED_PROFIT:
        return max(Decimal(0), observation.realized_net_pnl_usd)
    if source is CapitalSource.PROTECTED_ECONOMIC_FLOOR:
        return max(
            Decimal(0),
            observation.protected_open_floor_usd or Decimal(0),
        )
    return Decimal(0)
