"""Restart-safe cTrader DEMO execution reconciliation for Phase20D.

This module has no sizing, Risk or broker-mutation authority. It joins already
sealed pre-decision evidence with durable cTrader execution facts and terminal
CMA settlements. Legacy registry/mutation rows that lack exact execution facts
are intentionally ineligible for economic qualification.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from qore.infrastructure.account_wide_risk import (
    CiboCapitalProvenanceLot,
    CiboRiskRequest,
    TraderLineage,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_ctrader_executed_risk import (
    build_ctrader_phase20_executed_risk,
)
from qore.infrastructure.cibo_ce2i_phase20_execution_risk_store import (
    DurablePhase20ExecutedRiskStore,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    DurablePhase20ForwardEvidenceStore,
    Phase20ForwardDecisionSeal,
)
from qore.infrastructure.cibo_ce2i_phase20_outcome_reconciliation import (
    Phase20ExecutedRiskEvidence,
    append_reconciled_phase20_forward_outcome_from_seal,
)
from qore.infrastructure.cibo_cma_settlement_store import (
    DurableCmaSettlementStore,
)
from qore.infrastructure.ctrader_demo_allocation_only import (
    CTraderDemoBrokerContract,
)
from qore.infrastructure.ctrader_demo_execution_contracts import (
    CTraderDemoAttemptState,
    CTraderDemoFillObservation,
    CTraderDemoFillReconciliation,
    CTraderDemoFillReconciliationStatus,
)
from qore.infrastructure.ctrader_demo_mutation_ledger import (
    CTraderDemoMutationLedger,
    CTraderDemoMutationLedgerRecord,
)
from qore.infrastructure.ctrader_demo_trade_registry import (
    DemoTradeRegistryEntry,
)
from qore.infrastructure.execution_boundary import ExecutionReceiptId
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
    MarketTestAccountIdentity,
)
from qore.infrastructure.order_intent import (
    ExecutionIdempotencyKey,
    ExecutionInstrument,
    OrderSide,
)


class Phase20CTraderRecoveryStatus(StrEnum):
    RISK_SEALED_OUTCOME_PENDING = "RISK_SEALED_OUTCOME_PENDING"
    OUTCOME_SEALED = "OUTCOME_SEALED"
    ALREADY_COMPLETE = "ALREADY_COMPLETE"


@dataclass(frozen=True, slots=True)
class Phase20CTraderRecoveryResult:
    status: Phase20CTraderRecoveryStatus
    decision_evidence_sha256: str
    signal_fingerprint: str
    position_id: int
    executed_risk_evidence_id: str
    outcome_evidence_id: str | None
    broker_mutation_performed: bool = False
    sizing_authority: bool = False
    risk_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        if not self.decision_evidence_sha256.startswith("sha256:"):
            raise CiboCapitalManagementError(
                "Phase20D recovery requires decision SHA256"
            )
        if not self.signal_fingerprint:
            raise CiboCapitalManagementError(
                "Phase20D recovery signal is required"
            )
        if self.position_id <= 0:
            raise CiboCapitalManagementError(
                "Phase20D recovery position_id must be positive"
            )
        if not self.executed_risk_evidence_id:
            raise CiboCapitalManagementError(
                "Phase20D recovery executed-risk identity is required"
            )
        if (
            self.broker_mutation_performed
            or self.sizing_authority
            or self.risk_authority
            or self.execution_authority
        ):
            raise CiboCapitalManagementError(
                "Phase20D recovery cannot acquire runtime authority"
            )


def reconcile_ctrader_demo_phase20_entry(
    *,
    entry: DemoTradeRegistryEntry,
    account: MarketTestAccountIdentity,
    mutation_ledger: CTraderDemoMutationLedger,
    forward_store: DurablePhase20ForwardEvidenceStore,
    executed_risk_store: DurablePhase20ExecutedRiskStore,
    settlement_store: DurableCmaSettlementStore,
    reconciled_at: datetime,
) -> Phase20CTraderRecoveryResult:
    """Reconcile one registry entry from durable evidence only."""

    if not isinstance(entry, DemoTradeRegistryEntry):
        raise CiboCapitalManagementError(
            "Phase20D recovery requires canonical demo registry entry"
        )
    if not isinstance(account, MarketTestAccountIdentity):
        raise CiboCapitalManagementError(
            "Phase20D recovery requires canonical account identity"
        )
    if (
        account.provider_key != "ctrader-demo"
        or account.environment is not MarketRuntimeEnvironment.DEMO
    ):
        raise CiboCapitalManagementError(
            "Phase20D cTrader recovery is DEMO-only"
        )
    _aware(reconciled_at, name="reconciled_at")
    if not callable(getattr(mutation_ledger, "records", None)):
        raise CiboCapitalManagementError(
            "Phase20D recovery requires durable mutation ledger"
        )

    forward_book = forward_store.load()
    decision = _decision_for_signal(
        decisions=forward_book.decisions,
        signal_fingerprint=entry.signal_fingerprint,
    )
    if decision is None:
        raise CiboCapitalManagementError(
            "Phase20D execution has no pre-sealed forward decision"
        )
    if entry.position_id is None or entry.position_id <= 0:
        raise CiboCapitalManagementError(
            "Phase20D execution requires reconciled broker position_id"
        )
    request, contract, authorized_volume = _execution_basis(entry)
    if request.requested_at < decision.decision_at:
        raise CiboCapitalManagementError(
            "Phase20D CIBO request predates sealed forward decision"
        )

    existing_outcome = tuple(
        item
        for item in forward_book.outcomes
        if (
            item.decision_evidence_sha256 == decision.evidence_sha256
            and item.signal_fingerprint == entry.signal_fingerprint
        )
    )
    if len(existing_outcome) > 1:
        raise CiboCapitalManagementError(
            "Phase20D duplicate forward outcome identity"
        )

    risk_book = executed_risk_store.load()
    risk_evidence = risk_book.risk_for(
        decision_evidence_sha256=decision.evidence_sha256,
        signal_fingerprint=entry.signal_fingerprint,
        position_id=entry.position_id,
    )
    if risk_evidence is None:
        mutation = _mutation_for_entry(
            entry=entry,
            records=mutation_ledger.records(),
        )
        risk_evidence = _build_executed_risk(
            decision=decision,
            entry=entry,
            request=request,
            contract=contract,
            authorized_volume=authorized_volume,
            mutation=mutation,
            account=account,
        )
        executed_risk_store.seal(
            risk_evidence,
            expected_generation=risk_book.generation,
        )

    if existing_outcome:
        existing = existing_outcome[0]
        if (
            existing.position_id != entry.position_id
            or existing.execution_risk_evidence_id
            != risk_evidence.evidence_id
        ):
            raise CiboCapitalManagementError(
                "Phase20D completed outcome conflicts with execution evidence"
            )
        return Phase20CTraderRecoveryResult(
            status=Phase20CTraderRecoveryStatus.ALREADY_COMPLETE,
            decision_evidence_sha256=decision.evidence_sha256,
            signal_fingerprint=entry.signal_fingerprint,
            position_id=entry.position_id,
            executed_risk_evidence_id=risk_evidence.evidence_id,
            outcome_evidence_id=existing.evidence_id,
        )

    settlement = settlement_store.load().state_for(
        signal_fingerprint=entry.signal_fingerprint,
        position_id=entry.position_id,
    )
    if settlement is None or not settlement.position_closed:
        return Phase20CTraderRecoveryResult(
            status=Phase20CTraderRecoveryStatus.RISK_SEALED_OUTCOME_PENDING,
            decision_evidence_sha256=decision.evidence_sha256,
            signal_fingerprint=entry.signal_fingerprint,
            position_id=entry.position_id,
            executed_risk_evidence_id=risk_evidence.evidence_id,
            outcome_evidence_id=None,
        )
    if reconciled_at <= risk_evidence.observed_at:
        raise CiboCapitalManagementError(
            "Phase20D outcome reconciliation must follow executed-risk evidence"
        )

    updated = append_reconciled_phase20_forward_outcome_from_seal(
        store=forward_store,
        decision=decision,
        settlement=settlement,
        executed_risk=risk_evidence,
        reconciled_at=reconciled_at,
    )
    outcomes = tuple(
        item
        for item in updated.outcomes
        if (
            item.decision_evidence_sha256 == decision.evidence_sha256
            and item.signal_fingerprint == entry.signal_fingerprint
        )
    )
    if len(outcomes) != 1:
        raise CiboCapitalManagementError(
            "Phase20D terminal outcome was not sealed uniquely"
        )
    return Phase20CTraderRecoveryResult(
        status=Phase20CTraderRecoveryStatus.OUTCOME_SEALED,
        decision_evidence_sha256=decision.evidence_sha256,
        signal_fingerprint=entry.signal_fingerprint,
        position_id=entry.position_id,
        executed_risk_evidence_id=risk_evidence.evidence_id,
        outcome_evidence_id=outcomes[0].evidence_id,
    )


def _execution_basis(
    entry: DemoTradeRegistryEntry,
) -> tuple[CiboRiskRequest, CTraderDemoBrokerContract, Decimal]:
    required = {
        "receipt_id": entry.receipt_id,
        "idempotency_key": entry.idempotency_key,
        "provider_symbol": entry.provider_symbol,
        "side": entry.side,
        "entry_type": entry.entry_type,
        "intended_entry": entry.intended_entry,
        "stop_loss": entry.stop_loss,
        "take_profit": entry.take_profit,
        "volume_step": entry.volume_step,
        "minimum_volume": entry.minimum_volume,
        "stop_loss_per_volume": entry.stop_loss_per_volume,
        "margin_per_volume": entry.margin_per_volume,
        "requested_at": entry.requested_at,
        "authorized_source_volume": entry.authorized_source_volume,
        "source_contract_size_units": entry.source_contract_size_units,
        "ctrader_lot_size_units": entry.ctrader_lot_size_units,
    }
    missing = tuple(name for name, value in required.items() if value is None)
    if missing or entry.minimum_volume_uplifted is None:
        raise CiboCapitalManagementError(
            "Phase20D legacy/incomplete registry entry is ineligible: "
            + ",".join((*missing, *(
                ("minimum_volume_uplifted",)
                if entry.minimum_volume_uplifted is None
                else ()
            )))
        )
    try:
        provenance = tuple(
            CiboCapitalProvenanceLot(
                source_kind=source_kind,
                source_id=source_id,
                amount_usd=Decimal(amount),
            )
            for source_kind, source_id, amount in entry.capital_provenance
        )
        request = CiboRiskRequest(
            request_id=entry.request_id,
            trader_id=TraderLineage(entry.trader),
            signal_fingerprint=entry.signal_fingerprint,
            qore_symbol=entry.qore_symbol,
            provider_symbol=str(entry.provider_symbol),
            side=str(entry.side),
            entry_type=str(entry.entry_type),
            intended_entry=Decimal(str(entry.intended_entry)),
            stop_loss=Decimal(str(entry.stop_loss)),
            take_profit=Decimal(str(entry.take_profit)),
            requested_volume=Decimal(entry.requested_volume),
            volume_step=Decimal(str(entry.volume_step)),
            minimum_volume=Decimal(str(entry.minimum_volume)),
            stop_loss_per_volume=Decimal(str(entry.stop_loss_per_volume)),
            margin_per_volume=Decimal(str(entry.margin_per_volume)),
            requested_at=datetime.fromisoformat(str(entry.requested_at)),
            expires_at=datetime.fromisoformat(entry.expires_at),
            minimum_volume_uplifted=entry.minimum_volume_uplifted,
            capital_provenance=provenance,
        )
        contract = CTraderDemoBrokerContract(
            qore_symbol=entry.qore_symbol,
            provider_symbol=str(entry.provider_symbol),
            source_contract_size_units=Decimal(
                str(entry.source_contract_size_units)
            ),
            ctrader_lot_size_units=Decimal(
                str(entry.ctrader_lot_size_units)
            ),
        )
        authorized = Decimal(str(entry.authorized_source_volume))
        UUID(str(entry.receipt_id))
        UUID(str(entry.idempotency_key))
    except (ValueError, TypeError) as error:
        raise CiboCapitalManagementError(
            "Phase20D registry execution basis is invalid"
        ) from error
    return request, contract, authorized


def _decision_for_signal(
    *,
    decisions: tuple[Phase20ForwardDecisionSeal, ...],
    signal_fingerprint: str,
) -> Phase20ForwardDecisionSeal | None:
    matches = tuple(
        item
        for item in decisions
        if signal_fingerprint in item.signal_fingerprints
    )
    if len(matches) > 1:
        raise CiboCapitalManagementError(
            "Phase20D signal appears in multiple sealed decisions"
        )
    return matches[0] if matches else None


def _mutation_for_entry(
    *,
    entry: DemoTradeRegistryEntry,
    records: tuple[CTraderDemoMutationLedgerRecord, ...],
) -> CTraderDemoMutationLedgerRecord:
    matches = tuple(
        item
        for item in records
        if (
            item.receipt_id == entry.receipt_id
            and item.idempotency_key == entry.idempotency_key
            and item.provider_order_ref == entry.provider_order_ref
        )
    )
    if len(matches) != 1:
        raise CiboCapitalManagementError(
            "Phase20D execution mutation identity is missing or ambiguous"
        )
    mutation = matches[0]
    if mutation.state not in {
        CTraderDemoAttemptState.DEFINITIVE_OUTCOME,
        CTraderDemoAttemptState.RESOLVED,
    }:
        raise CiboCapitalManagementError(
            "Phase20D execution mutation outcome is not definitive"
        )
    if not mutation.fill_observations:
        raise CiboCapitalManagementError(
            "Phase20D exact durable fills are unavailable"
        )
    return mutation


def _build_executed_risk(
    *,
    decision: Phase20ForwardDecisionSeal,
    entry: DemoTradeRegistryEntry,
    request: CiboRiskRequest,
    contract: CTraderDemoBrokerContract,
    authorized_volume: Decimal,
    mutation: CTraderDemoMutationLedgerRecord,
    account: MarketTestAccountIdentity,
) -> Phase20ExecutedRiskEvidence:
    assert entry.position_id is not None
    expected_provider_quantity = (
        authorized_volume * contract.source_contract_size_units
    )
    if not mutation.is_complete:
        raise CiboCapitalManagementError(
            "Phase20D durable fill sequence is not terminal"
        )
    if Decimal(mutation.cumulative_quantity) != expected_provider_quantity:
        raise CiboCapitalManagementError(
            "Phase20D durable fill quantity does not match authorization"
        )

    receipt_id = ExecutionReceiptId(UUID(str(entry.receipt_id)))
    idempotency_key = ExecutionIdempotencyKey(
        UUID(str(entry.idempotency_key))
    )
    side = OrderSide.BUY if request.side == "long" else OrderSide.SELL
    fills = tuple(
        CTraderDemoFillObservation(
            receipt_id=receipt_id,
            idempotency_key=idempotency_key,
            account=account,
            instrument=ExecutionInstrument(request.qore_symbol),
            side=side,
            provider_order_ref=entry.provider_order_ref,
            fill_ref=item.fill_ref,
            fill_quantity=Decimal(item.fill_quantity),
            cumulative_quantity=Decimal(item.cumulative_quantity),
            fill_price=Decimal(item.fill_price),
            provider_timestamp=item.provider_timestamp,
            received_at=item.received_at,
            is_complete=item.is_complete,
        )
        for item in mutation.fill_observations
    )
    latest_received = max(item.received_at for item in fills)
    if latest_received <= decision.decision_at:
        raise CiboCapitalManagementError(
            "Phase20D broker fills must follow sealed decision"
        )
    reconciliation = CTraderDemoFillReconciliation(
        status=CTraderDemoFillReconciliationStatus.MATCHED,
        reconciled_at=latest_received,
        requested_quantity=expected_provider_quantity,
        filled_quantity=expected_provider_quantity,
        issues=(),
    )
    return build_ctrader_phase20_executed_risk(
        decision_evidence_sha256=decision.evidence_sha256,
        position_id=entry.position_id,
        authorized_source_volume=authorized_volume,
        request=request,
        contract=contract,
        fills=fills,
        reconciliation=reconciliation,
    )


def _aware(value: datetime, *, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise CiboCapitalManagementError(
            f"Phase20D {name} must be timezone-aware"
        )
