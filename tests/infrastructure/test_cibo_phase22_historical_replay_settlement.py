from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from hashlib import sha256

from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    Phase20ForwardDecisionSeal,
)
from qore.infrastructure.cibo_phase22_historical_replay_economics_amendment import (
    Phase22ProviderCalibrationReceipt,
    freeze_phase22_historical_replay_economics_amendment,
)
from qore.infrastructure.cibo_phase22_historical_replay_settlement import (
    VersionedPhase22HistoricalReplayEvidenceBook,
    build_phase22_historical_replay_outcome,
)


def _sha(label: str) -> str:
    return "sha256:" + sha256(label.encode()).hexdigest()


def _amendment():
    calibration = Phase22ProviderCalibrationReceipt(
        artifact_sha256=_sha("calibration"),
        git_sha="a" * 40,
        account_fingerprint_sha256=sha256(b"account").hexdigest(),
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
        evidence_id="decision:test",
        decision_epoch_id="epoch:test",
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


def test_replay_settlement_applies_empirical_adjustment_once() -> None:
    decision = _decision()
    deployed = datetime(2015, 10, 20, 12, 5, tzinfo=UTC)
    released = deployed + timedelta(minutes=30)
    outcome = build_phase22_historical_replay_outcome(
        amendment=_amendment(),
        decision=decision,
        signal_fingerprint="signal-1",
        trader_id="R43_GBPUSD",
        qore_symbol="GBPUSD",
        observed_at=released,
        gross_structural_outcome_r=Decimal("2"),
        executed_initial_stop_risk_usd=Decimal("10"),
        provider_execution_adjustment_usd=Decimal("1.25"),
        decision_provider_cost_proxy_usd=Decimal("0.80"),
        capital_deployed_at=deployed,
        capital_released_at=released,
    )
    assert outcome.realized_net_pnl_usd == Decimal("18.75")
    assert outcome.gross_structural_outcome_r == Decimal("2")
    assert outcome.decision_provider_cost_proxy_usd == Decimal("0.80")
    assert outcome.historical_broker_fills_claimed is False
    assert outcome.capital_minutes == Decimal("30")


def test_replay_book_keeps_decision_outcome_lineage_without_broker_ids() -> None:
    decision = _decision()
    deployed = datetime(2015, 10, 20, 12, 5, tzinfo=UTC)
    released = deployed + timedelta(minutes=30)
    amendment = _amendment()
    outcome = build_phase22_historical_replay_outcome(
        amendment=amendment,
        decision=decision,
        signal_fingerprint="signal-1",
        trader_id="R43_GBPUSD",
        qore_symbol="GBPUSD",
        observed_at=released,
        gross_structural_outcome_r=Decimal("-1"),
        executed_initial_stop_risk_usd=Decimal("10"),
        provider_execution_adjustment_usd=Decimal("1"),
        decision_provider_cost_proxy_usd=Decimal("0.80"),
        capital_deployed_at=deployed,
        capital_released_at=released,
    )
    book = VersionedPhase22HistoricalReplayEvidenceBook(
        generation=1,
        amendment_sha256=amendment.fingerprint(),
        decisions=(decision,),
        outcomes=(outcome,),
    )
    assert book.outcomes[0].realized_net_pnl_usd == Decimal("-11")
    payload = book.outcomes[0].as_dict()
    assert "position_id" not in payload
    assert "settlement_deal_ids" not in payload
    assert "fill_evidence_refs" not in payload
