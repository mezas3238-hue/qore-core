import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_ctrader_recovery import (
    Phase20CTraderRecoveryStatus,
    reconcile_ctrader_demo_phase20_entry,
)
from qore.infrastructure.cibo_ce2i_phase20_execution_risk_store import (
    DurablePhase20ExecutedRiskStore,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    DurablePhase20ForwardEvidenceStore,
)
from qore.infrastructure.cibo_cma_settlement_ledger import CmaSettlementRecord
from qore.infrastructure.cibo_cma_settlement_store import DurableCmaSettlementStore
from qore.infrastructure.ctrader_demo_execution_contracts import (
    CTraderDemoAttemptState,
    CTraderDemoFillObservation,
)
from qore.infrastructure.ctrader_demo_execution_gateway import (
    ctrader_fill_identity_digest,
)
from qore.infrastructure.ctrader_demo_mutation_ledger import (
    CTraderDemoDurableFillRecord,
    CTraderDemoMutationLedgerRecord,
    JsonFileCTraderDemoMutationLedger,
)
from qore.infrastructure.ctrader_demo_trade_registry import DemoTradeRegistryEntry
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

NOW = datetime(2026, 9, 27, 18, 0, tzinfo=UTC)
SIGNAL = "phase20-recovery-vt31"
DECISION_SHA = "sha256:" + "a" * 64
RECEIPT = UUID("32000000-0000-0000-4000-000000000088")
IDEMPOTENCY = UUID("32000000-0000-0000-1000-000000000088")
ACCOUNT = MarketTestAccountIdentity(
    provider_key="ctrader-demo",
    account_ref="phase20-recovery-demo",
    environment=MarketRuntimeEnvironment.DEMO,
)


def _forward_store(path: Path) -> DurablePhase20ForwardEvidenceStore:
    path.write_text(
        json.dumps(
            {
                "schema": "CIBO_PHASE20D_FORWARD_EVIDENCE_BOOK_V3",
                "generation": 1,
                "decisions": [
                    {
                        "evidence_id": "decision-88",
                        "decision_epoch_id": "epoch-88",
                        "evidence_sha256": DECISION_SHA,
                        "decision_at": NOW.isoformat(),
                        "candidate_id": (
                            "CIBO_PHASE20H20I_FORWARD_CANDIDATE_V2"
                        ),
                        "code_sha": "7acce68c6ece61fae1adacf3f8e60815839b6f6a",
                        "parameter_sha256": "sha256:" + "b" * 64,
                        "signal_fingerprints": [SIGNAL],
                        "canonical_payload_json": json.dumps(
                            {"evidence_kind": "FORWARD_OBSERVED"},
                            sort_keys=True,
                        ),
                    }
                ],
                "outcomes": [],
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return DurablePhase20ForwardEvidenceStore(path)


def _entry() -> DemoTradeRegistryEntry:
    return DemoTradeRegistryEntry(
        trader="VT31_NAS100",
        signal_fingerprint=SIGNAL,
        request_id="request-88",
        client_order_id="qore-client-88",
        provider_order_ref="provider-order-88",
        qore_symbol="NAS100",
        requested_volume="1",
        requested_stop_risk="10",
        submitted_at=(NOW + timedelta(milliseconds=150)).isoformat(),
        expires_at=(NOW + timedelta(seconds=30)).isoformat(),
        position_id=88,
        receipt_id=str(RECEIPT),
        idempotency_key=str(IDEMPOTENCY),
        provider_symbol="NDX100",
        side="long",
        entry_type="market",
        intended_entry="100",
        stop_loss="99",
        take_profit="102",
        volume_step="1",
        minimum_volume="1",
        stop_loss_per_volume="10",
        margin_per_volume="8",
        requested_at=(NOW + timedelta(milliseconds=100)).isoformat(),
        authorized_source_volume="1",
        minimum_volume_uplifted=False,
        source_contract_size_units="100",
        ctrader_lot_size_units="100",
    )


def _mutation_ledger(path: Path) -> JsonFileCTraderDemoMutationLedger:
    ledger = JsonFileCTraderDemoMutationLedger(path)
    fill = CTraderDemoFillObservation(
        receipt_id=ExecutionReceiptId(RECEIPT),
        idempotency_key=ExecutionIdempotencyKey(IDEMPOTENCY),
        account=ACCOUNT,
        instrument=ExecutionInstrument("NAS100"),
        side=OrderSide.BUY,
        provider_order_ref="provider-order-88",
        fill_ref="fill-88",
        fill_quantity=Decimal("100"),
        cumulative_quantity=Decimal("100"),
        fill_price=Decimal("100.1"),
        provider_timestamp=NOW + timedelta(milliseconds=400),
        received_at=NOW + timedelta(milliseconds=500),
        is_complete=True,
    )
    ledger.upsert(
        CTraderDemoMutationLedgerRecord(
            idempotency_key=str(IDEMPOTENCY),
            receipt_id=str(RECEIPT),
            submission_digest="sha256:" + "c" * 64,
            client_order_id="qore-client-88",
            state=CTraderDemoAttemptState.DEFINITIVE_OUTCOME,
            transitioned_at=NOW + timedelta(milliseconds=200),
            provider_order_ref="provider-order-88",
            outcome="filled",
            fill_refs=("fill-88",),
            fill_identities=(
                ("fill-88", ctrader_fill_identity_digest(fill)),
            ),
            fill_observations=(
                CTraderDemoDurableFillRecord(
                    fill_ref="fill-88",
                    fill_quantity="100",
                    cumulative_quantity="100",
                    fill_price="100.1",
                    provider_timestamp=NOW + timedelta(milliseconds=400),
                    received_at=NOW + timedelta(milliseconds=500),
                    is_complete=True,
                ),
            ),
            cumulative_quantity="100",
            is_complete=True,
        )
    )
    return JsonFileCTraderDemoMutationLedger(path)


def test_restart_safe_recovery_seals_exact_risk_and_terminal_outcome(
    tmp_path: Path,
) -> None:
    forward = _forward_store(tmp_path / "forward.json")
    risk = DurablePhase20ExecutedRiskStore(tmp_path / "risk.json")
    settlements = DurableCmaSettlementStore(tmp_path / "settlements.json")
    settlement_book = settlements.load()
    settlements.apply(
        CmaSettlementRecord(
            event="CTRADER_DEMO_EXIT_SETTLEMENT",
            deal_id=88001,
            signal_fingerprint=SIGNAL,
            position_id=88,
            net_profit_usd=Decimal("22"),
            position_open_after=False,
        ),
        expected_generation=settlement_book.generation,
    )
    mutation = _mutation_ledger(tmp_path / "mutations.json")

    result = reconcile_ctrader_demo_phase20_entry(
        entry=_entry(),
        account=ACCOUNT,
        mutation_ledger=mutation,
        forward_store=forward,
        executed_risk_store=risk,
        settlement_store=settlements,
        reconciled_at=NOW + timedelta(seconds=2),
    )

    assert result.status is Phase20CTraderRecoveryStatus.OUTCOME_SEALED
    assert result.broker_mutation_performed is False
    assert result.sizing_authority is False
    assert result.risk_authority is False
    assert result.execution_authority is False
    risk_rows = risk.load().evidences
    assert len(risk_rows) == 1
    assert risk_rows[0].weighted_fill_price == Decimal("100.1")
    assert risk_rows[0].executed_initial_stop_risk_usd == Decimal("11")
    outcomes = forward.load().outcomes
    assert len(outcomes) == 1
    assert outcomes[0].realized_net_pnl_usd == Decimal("22")
    assert outcomes[0].realized_structural_outcome_r == Decimal("2")

    # A restart/retry consumes only durable stores and cannot rewrite evidence.
    retried = reconcile_ctrader_demo_phase20_entry(
        entry=_entry(),
        account=ACCOUNT,
        mutation_ledger=JsonFileCTraderDemoMutationLedger(
            tmp_path / "mutations.json"
        ),
        forward_store=DurablePhase20ForwardEvidenceStore(
            tmp_path / "forward.json"
        ),
        executed_risk_store=DurablePhase20ExecutedRiskStore(
            tmp_path / "risk.json"
        ),
        settlement_store=DurableCmaSettlementStore(
            tmp_path / "settlements.json"
        ),
        reconciled_at=NOW + timedelta(seconds=3),
    )
    assert retried.status is Phase20CTraderRecoveryStatus.ALREADY_COMPLETE
    assert risk.load().generation == 1
    assert forward.load().generation == 2


def test_recovery_seals_risk_but_waits_for_terminal_settlement(
    tmp_path: Path,
) -> None:
    result = reconcile_ctrader_demo_phase20_entry(
        entry=_entry(),
        account=ACCOUNT,
        mutation_ledger=_mutation_ledger(tmp_path / "mutations.json"),
        forward_store=_forward_store(tmp_path / "forward.json"),
        executed_risk_store=DurablePhase20ExecutedRiskStore(
            tmp_path / "risk.json"
        ),
        settlement_store=DurableCmaSettlementStore(
            tmp_path / "settlements.json"
        ),
        reconciled_at=NOW + timedelta(seconds=2),
    )

    assert (
        result.status
        is Phase20CTraderRecoveryStatus.RISK_SEALED_OUTCOME_PENDING
    )
    assert result.outcome_evidence_id is None


def test_legacy_registry_entry_cannot_fabricate_phase20_execution_basis(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="legacy/incomplete registry entry is ineligible",
    ):
        reconcile_ctrader_demo_phase20_entry(
            entry=replace(_entry(), receipt_id=None),
            account=ACCOUNT,
            mutation_ledger=_mutation_ledger(
                tmp_path / "mutations.json"
            ),
            forward_store=_forward_store(tmp_path / "forward.json"),
            executed_risk_store=DurablePhase20ExecutedRiskStore(
                tmp_path / "risk.json"
            ),
            settlement_store=DurableCmaSettlementStore(
                tmp_path / "settlements.json"
            ),
            reconciled_at=NOW + timedelta(seconds=2),
        )



def test_recovery_rejects_tampered_durable_fill_economics(
    tmp_path: Path,
) -> None:
    mutation_path = tmp_path / "mutations.json"
    _mutation_ledger(mutation_path)
    raw = json.loads(mutation_path.read_text(encoding="utf-8"))
    raw["records"][0]["fill_observations"][0]["fill_price"] = "101.5"
    mutation_path.write_text(
        json.dumps(raw, sort_keys=True),
        encoding="utf-8",
    )

    with pytest.raises(
        CiboCapitalManagementError,
        match="durable fill identity digest mismatch",
    ):
        reconcile_ctrader_demo_phase20_entry(
            entry=_entry(),
            account=ACCOUNT,
            mutation_ledger=JsonFileCTraderDemoMutationLedger(
                mutation_path
            ),
            forward_store=_forward_store(tmp_path / "forward.json"),
            executed_risk_store=DurablePhase20ExecutedRiskStore(
                tmp_path / "risk.json"
            ),
            settlement_store=DurableCmaSettlementStore(
                tmp_path / "settlements.json"
            ),
            reconciled_at=NOW + timedelta(seconds=2),
        )
