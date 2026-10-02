from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.cibo_a2_phase22_historical_compound import (
    ADAPTER_ID,
    A1_CONSUMER_CONTRACT_ID,
    build_a1_historical_compound_lineage_receipt,
    build_phase22_historical_compound_ledger,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    Phase20ForwardDecisionSeal,
)
from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError
from qore.infrastructure.cibo_phase22_historical_replay_economics_amendment import (
    Phase22ProviderCalibrationReceipt,
    freeze_phase22_historical_replay_economics_amendment,
)
from qore.infrastructure.cibo_phase22_historical_replay_settlement import (
    VersionedPhase22HistoricalReplayEvidenceBook,
    build_phase22_historical_replay_outcome,
)


def _sha(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode()).hexdigest()


def _amendment():
    calibration = Phase22ProviderCalibrationReceipt(
        artifact_sha256=_sha("calibration"),
        git_sha="a" * 40,
        account_fingerprint_sha256=hashlib.sha256(b"account").hexdigest(),
        observed_at=datetime(2026, 10, 1, 20, 40, tzinfo=UTC),
        status="READY",
        required_symbols=(
            "AUDJPY",
            "EURUSD",
            "GBPJPY",
            "GBPUSD",
            "NAS100",
            "XAUUSD",
        ),
        distinct_entry_orders_by_symbol=(
            ("AUDJPY", 8),
            ("EURUSD", 8),
            ("GBPJPY", 8),
            ("GBPUSD", 8),
            ("NAS100", 8),
            ("XAUUSD", 8),
        ),
        empirical_slippage_calibrated=True,
        execution_model_ready=True,
        execution_population_ready=True,
        created_positions_closed=True,
        minimum_volume_only=True,
        historical_provider_economics_claimed=False,
        historical_holdout_execution_claimed=False,
        holdout_outcomes_used=False,
        fundednext_touched=False,
        vps_touched=False,
        live_authorized=False,
        real_capital_authorized=False,
        productive_authority=False,
        blockers=(),
    )
    return freeze_phase22_historical_replay_economics_amendment(
        provider_calibration=calibration,
        fresh_outcomes_emitted=False,
        holdout_outcomes_inspected=False,
    )


def _decision() -> Phase20ForwardDecisionSeal:
    payload = {
        "evidence_kind": "FORWARD_OBSERVED",
        "population_slots": [],
        "candidates": [],
    }
    return Phase20ForwardDecisionSeal(
        evidence_id="decision:a2-compound",
        decision_epoch_id="epoch:a2-compound",
        candidate_id="CIBO_CAPITAL_MANAGEMENT_AUTHORITY_CANDIDATE_V3",
        code_sha="a" * 40,
        parameter_sha256=_sha("params"),
        decision_at=datetime(2015, 10, 20, 12, tzinfo=UTC),
        sealed_at=datetime(2015, 10, 20, 12, 0, 1, tzinfo=UTC),
        seal_deadline_at=datetime(2015, 10, 20, 12, 1, tzinfo=UTC),
        collector_git_sha="b" * 40,
        signal_fingerprints=("signal-1",),
        canonical_payload_json=json.dumps(payload, sort_keys=True),
        evidence_sha256=_sha("decision"),
    )


def _book(*, gross_r: Decimal = Decimal("2")):
    decision = _decision()
    amendment = _amendment()
    deployed = datetime(2015, 10, 20, 12, 5, tzinfo=UTC)
    released = deployed + timedelta(minutes=30)
    outcome = build_phase22_historical_replay_outcome(
        amendment=amendment,
        decision=decision,
        signal_fingerprint="signal-1",
        trader_id="R43_GBPUSD",
        qore_symbol="GBPUSD",
        observed_at=released,
        gross_structural_outcome_r=gross_r,
        executed_initial_stop_risk_usd=Decimal("10"),
        provider_execution_adjustment_usd=Decimal("1"),
        decision_provider_cost_proxy_usd=Decimal("0.80"),
        capital_deployed_at=deployed,
        capital_released_at=released,
    )
    return VersionedPhase22HistoricalReplayEvidenceBook(
        generation=1,
        amendment_sha256=amendment.fingerprint(),
        decisions=(decision,),
        outcomes=(outcome,),
    )


def test_a2_historical_compound_uses_only_positive_realized_profit() -> None:
    ledger = build_phase22_historical_compound_ledger(
        evidence_book=_book(),
        source_population_sha256=_sha("population"),
        a1_manifest_sha256=_sha("a1-manifest"),
    )

    assert ledger.adapter_identity == ADAPTER_ID
    assert ledger.total_realized_profit_usd == Decimal("19")
    assert len(ledger.lots) == 1
    assert ledger.lots[0].broker_position_id is None
    assert ledger.lots[0].broker_deal_ids == ()
    assert ledger.capital_conservation_proven is True
    assert ledger.double_spend_detected is False


def test_a2_historical_compound_rejects_population_without_realized_profit() -> None:
    with pytest.raises(
        CiboCompoundCapitalError,
        match="positive realized-profit lineage",
    ):
        build_phase22_historical_compound_ledger(
            evidence_book=_book(gross_r=Decimal("-1")),
            source_population_sha256=_sha("population"),
            a1_manifest_sha256=_sha("a1-manifest"),
        )


def test_a2_emits_exact_a1_historical_compound_contract() -> None:
    ledger = build_phase22_historical_compound_ledger(
        evidence_book=_book(),
        source_population_sha256=_sha("population"),
        a1_manifest_sha256=_sha("a1-manifest"),
    )
    receipt = build_a1_historical_compound_lineage_receipt(
        ledger=ledger,
        source_head="c" * 40,
        artifact_sha256=_sha("artifact"),
    )

    assert receipt.contract_id == A1_CONSUMER_CONTRACT_ID
    assert receipt.source_workstream == "COMPOUND_ENGINE"
    assert receipt.historical_replay_supported is True
    assert receipt.historical_broker_ids_required is False
    assert receipt.historical_broker_ids_emitted is False
    assert receipt.fabricated_execution_ids_used is False
    assert receipt.realized_profit_only is True
    assert receipt.floating_pnl_used_as_capital is False
    assert receipt.capital_conservation_proven is True
    assert receipt.deterministic_replay is True


def test_a2_historical_compound_receipt_rejects_demo_id_relabelling() -> None:
    ledger = build_phase22_historical_compound_ledger(
        evidence_book=_book(),
        source_population_sha256=_sha("population"),
        a1_manifest_sha256=_sha("a1-manifest"),
    )
    receipt = build_a1_historical_compound_lineage_receipt(
        ledger=ledger,
        source_head="c" * 40,
        artifact_sha256=_sha("artifact"),
    )

    with pytest.raises(
        CiboCompoundCapitalError,
        match="not scientifically admissible",
    ):
        replace(receipt, current_demo_ids_relabelled_as_historical=True)
