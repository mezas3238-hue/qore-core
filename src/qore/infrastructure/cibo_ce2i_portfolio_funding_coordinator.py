"""Recoverable coordinator for CE2I portfolio + funding reservations.

The coordinator intentionally uses a durable saga instead of pretending the
portfolio allocation store and capital-source ledger can commit atomically.

Research-only. It may reserve/release internal CIBO capacity, but it never calls
QORE Risk and never mutates broker state.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_capital_source_ledger_store import (
    DurableCapitalSourceLedgerStore,
)
from qore.infrastructure.cibo_cma_capital_observation import CmaCapitalObservation
from qore.infrastructure.cibo_ce2i_execution_efficiency import (
    ExecutionCostCurveInput,
)
from qore.infrastructure.cibo_ce2i_expansion_proposal import (
    CmaExpansionProposal,
    release_rejected_expansion,
)
from qore.infrastructure.cibo_ce2i_multi_source import (
    CmaMultiSourceExpansionProposal,
    release_multi_source_expansion,
)
from qore.infrastructure.cibo_ce2i_opportunity_competition import (
    CapitalOpportunityCandidate,
)
from qore.infrastructure.cibo_ce2i_policy_pipeline import (
    Ce2iExpansionPolicyDecision,
    propose_ce2i_expansion,
)
from qore.infrastructure.cibo_ce2i_portfolio_allocation_store import (
    DurablePortfolioAllocationStore,
)
from qore.infrastructure.cibo_ce2i_portfolio_funding_saga import (
    DurablePortfolioFundingSagaStore,
    PortfolioFundingSagaState,
)


@dataclass(frozen=True, slots=True)
class PortfolioFundingTransactionResult:
    transaction_id: str
    state: PortfolioFundingSagaState
    policy_decision: Ce2iExpansionPolicyDecision | None
    reason: str

    @property
    def ready_for_risk(self) -> bool:
        return self.state is PortfolioFundingSagaState.READY_FOR_RISK

    @property
    def proposal(
        self,
    ) -> CmaExpansionProposal | CmaMultiSourceExpansionProposal | None:
        if self.policy_decision is None:
            return None
        return self.policy_decision.proposal


def reserve_portfolio_and_funding(
    *,
    transaction_id: str,
    candidate: CapitalOpportunityCandidate,
    opportunity: TraderOpportunityEnvelope,
    observation: CmaCapitalObservation,
    execution_curve: ExecutionCostCurveInput,
    assigned_capital_usd: Decimal,
    hard_risk_headroom_usd: Decimal,
    margin_headroom_usd: Decimal,
    requested_at: datetime,
    expires_at: datetime,
    allocation_store: DurablePortfolioAllocationStore,
    funding_store: DurableCapitalSourceLedgerStore,
    saga_store: DurablePortfolioFundingSagaStore,
) -> PortfolioFundingTransactionResult:
    """Reserve portfolio capacity and funding with recoverable saga semantics."""

    _assert_identity(candidate, opportunity, observation)
    if not transaction_id:
        raise CiboCapitalManagementError("transaction_id required")

    saga_book = saga_store.load()
    saga_book = saga_store.prepare(
        transaction_id=transaction_id,
        signal_fingerprint=candidate.signal_fingerprint,
        funding_reservation_prefix=transaction_id,
        updated_at=requested_at,
        expected_generation=saga_book.generation,
    )

    allocation_version = allocation_store.load()
    if allocation_version is None:
        return _rollback_without_resources(
            transaction_id=transaction_id,
            saga_store=saga_store,
            saga_book_generation=saga_book.generation,
            now=requested_at,
            reason="portfolio allocation store not initialized",
        )

    next_allocation, allocation_decision = (
        allocation_version.ledger.allocate_and_reserve((candidate,))
    )
    if candidate.signal_fingerprint not in allocation_decision.selected_signal_fingerprints:
        return _rollback_without_resources(
            transaction_id=transaction_id,
            saga_store=saga_store,
            saga_book_generation=saga_book.generation,
            now=requested_at,
            reason="opportunity not selected by portfolio competition",
        )

    try:
        stored_allocation = allocation_store.store(
            next_allocation,
            expected_generation=allocation_version.generation,
        )
    except Exception as error:
        saga_store.transition(
            transaction_id=transaction_id,
            target=PortfolioFundingSagaState.RECONCILIATION_REQUIRED,
            updated_at=requested_at,
            expected_generation=saga_book.generation,
            reason=f"portfolio reservation persistence ambiguous:{type(error).__name__}",
        )
        raise

    saga_book = saga_store.transition(
        transaction_id=transaction_id,
        target=PortfolioFundingSagaState.PORTFOLIO_RESERVED,
        updated_at=requested_at,
        expected_generation=saga_book.generation,
        reason="portfolio risk/margin/concentration reservation durable",
        portfolio_generation=stored_allocation.generation,
    )

    try:
        policy = propose_ce2i_expansion(
            reservation_id=transaction_id,
            request_id=f"{transaction_id}:risk",
            opportunity=opportunity,
            observation=observation,
            execution_curve=execution_curve,
            assigned_capital_usd=assigned_capital_usd,
            hard_risk_headroom_usd=hard_risk_headroom_usd,
            margin_headroom_usd=margin_headroom_usd,
            requested_at=requested_at,
            expires_at=expires_at,
            ledger_store=funding_store,
        )
    except Exception as error:
        saga_store.transition(
            transaction_id=transaction_id,
            target=PortfolioFundingSagaState.RECONCILIATION_REQUIRED,
            updated_at=requested_at,
            expected_generation=saga_book.generation,
            reason=f"funding reservation outcome ambiguous:{type(error).__name__}",
        )
        raise

    if policy.proposal is None:
        released = stored_allocation.ledger.release(candidate.signal_fingerprint)
        released_version = allocation_store.store(
            released,
            expected_generation=stored_allocation.generation,
        )
        saga_book = saga_store.transition(
            transaction_id=transaction_id,
            target=PortfolioFundingSagaState.COMPENSATION_REQUIRED,
            updated_at=requested_at,
            expected_generation=saga_book.generation,
            reason=f"funding unavailable:{policy.reason}",
            portfolio_generation=released_version.generation,
        )
        saga_book = saga_store.transition(
            transaction_id=transaction_id,
            target=PortfolioFundingSagaState.ROLLED_BACK,
            updated_at=requested_at,
            expected_generation=saga_book.generation,
            reason="portfolio reservation released; no funding reserved",
        )
        return PortfolioFundingTransactionResult(
            transaction_id=transaction_id,
            state=PortfolioFundingSagaState.ROLLED_BACK,
            policy_decision=policy,
            reason=policy.reason,
        )

    proposal_risk, proposal_margin = _proposal_economics(policy.proposal)
    if (
        proposal_risk != candidate.stop_risk_usd
        or proposal_margin != candidate.margin_usd
    ):
        _compensate_known_resources(
            candidate=candidate,
            policy=policy,
            allocation_store=allocation_store,
            allocation_generation=stored_allocation.generation,
            funding_store=funding_store,
        )
        saga_book = saga_store.transition(
            transaction_id=transaction_id,
            target=PortfolioFundingSagaState.COMPENSATION_REQUIRED,
            updated_at=requested_at,
            expected_generation=saga_book.generation,
            reason="portfolio/funding economics mismatch",
        )
        saga_store.transition(
            transaction_id=transaction_id,
            target=PortfolioFundingSagaState.ROLLED_BACK,
            updated_at=requested_at,
            expected_generation=saga_book.generation,
            reason="known portfolio and funding reservations released",
        )
        return PortfolioFundingTransactionResult(
            transaction_id=transaction_id,
            state=PortfolioFundingSagaState.ROLLED_BACK,
            policy_decision=policy,
            reason="portfolio/funding economics mismatch",
        )

    saga_book = saga_store.transition(
        transaction_id=transaction_id,
        target=PortfolioFundingSagaState.FUNDING_RESERVED,
        updated_at=requested_at,
        expected_generation=saga_book.generation,
        reason="capital-source funding reservation durable",
        funding_generation=policy.proposal.ledger_generation,
    )
    saga_store.transition(
        transaction_id=transaction_id,
        target=PortfolioFundingSagaState.READY_FOR_RISK,
        updated_at=requested_at,
        expected_generation=saga_book.generation,
        reason="portfolio and funding reservations agree",
    )
    return PortfolioFundingTransactionResult(
        transaction_id=transaction_id,
        state=PortfolioFundingSagaState.READY_FOR_RISK,
        policy_decision=policy,
        reason="portfolio and funding reservations durable and reconciled",
    )


def _assert_identity(
    candidate: CapitalOpportunityCandidate,
    opportunity: TraderOpportunityEnvelope,
    observation: CmaCapitalObservation,
) -> None:
    if candidate.signal_fingerprint != opportunity.signal_fingerprint:
        raise CiboCapitalManagementError("candidate/opportunity signal mismatch")
    if candidate.trader_id is not opportunity.trader_id:
        raise CiboCapitalManagementError("candidate/opportunity trader mismatch")
    if candidate.qore_symbol != opportunity.qore_symbol:
        raise CiboCapitalManagementError("candidate/opportunity symbol mismatch")
    if observation.signal_fingerprint != opportunity.signal_fingerprint:
        raise CiboCapitalManagementError("observation/opportunity signal mismatch")
    if observation.symbol != opportunity.qore_symbol:
        raise CiboCapitalManagementError("observation/opportunity symbol mismatch")


def _rollback_without_resources(
    *,
    transaction_id: str,
    saga_store: DurablePortfolioFundingSagaStore,
    saga_book_generation: int,
    now: datetime,
    reason: str,
) -> PortfolioFundingTransactionResult:
    book = saga_store.transition(
        transaction_id=transaction_id,
        target=PortfolioFundingSagaState.COMPENSATION_REQUIRED,
        updated_at=now,
        expected_generation=saga_book_generation,
        reason=reason,
    )
    saga_store.transition(
        transaction_id=transaction_id,
        target=PortfolioFundingSagaState.ROLLED_BACK,
        updated_at=now,
        expected_generation=book.generation,
        reason="no durable resource reservation exists",
    )
    return PortfolioFundingTransactionResult(
        transaction_id=transaction_id,
        state=PortfolioFundingSagaState.ROLLED_BACK,
        policy_decision=None,
        reason=reason,
    )


def _proposal_economics(
    proposal: CmaExpansionProposal | CmaMultiSourceExpansionProposal,
) -> tuple[Decimal, Decimal]:
    if isinstance(proposal, CmaExpansionProposal):
        return proposal.plan.stop_risk_usd, proposal.plan.margin_usd
    return proposal.stop_risk_usd, proposal.margin_usd


def _compensate_known_resources(
    *,
    candidate: CapitalOpportunityCandidate,
    policy: Ce2iExpansionPolicyDecision,
    allocation_store: DurablePortfolioAllocationStore,
    allocation_generation: int,
    funding_store: DurableCapitalSourceLedgerStore,
) -> None:
    proposal = policy.proposal
    if proposal is None:
        raise CiboCapitalManagementError("funding proposal required for compensation")

    if isinstance(proposal, CmaExpansionProposal):
        release_rejected_expansion(
            reservation_id=proposal.reservation_id,
            ledger_store=funding_store,
        )
    else:
        release_multi_source_expansion(
            proposal,
            ledger_store=funding_store,
        )

    current = allocation_store.load()
    if current is None or current.generation != allocation_generation:
        raise CiboCapitalManagementError(
            "portfolio allocation generation changed before compensation"
        )
    released = current.ledger.release(candidate.signal_fingerprint)
    allocation_store.store(
        released,
        expected_generation=current.generation,
    )
