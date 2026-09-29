from __future__ import annotations

import json
from datetime import timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    Phase20ForwardDecisionSeal,
    Phase20ForwardOutcomeSeal,
    VersionedPhase20ForwardEvidenceBook,
)
from qore.infrastructure.cibo_ce2i_phase20_t13_shadow_policy import (
    T13_SHADOW_POLICY_FROZEN_AT,
    evaluate_phase20_t13_shadow_decision,
)
from qore.infrastructure.cibo_ce2i_phase20_t13_shadow_store import (
    DurableT13ShadowDecisionError,
    DurableT13ShadowDecisionStore,
)


def _candidate(index: int, decision_at) -> dict[str, object]:
    signal = f"signal-{index}"
    return {
        "provider_evidence_id": f"provider:{index}",
        "opportunity": {
            "trader_id": TraderLineage.R43_GBPUSD.value,
            "signal_fingerprint": signal,
            "qore_symbol": "GBPUSD",
            "provider_symbol": "GBPUSD",
            "side": "long",
            "entry_type": "market",
            "intended_entry": "1.25",
            "stop_loss": "1.24",
            "take_profit": "1.27",
            "stop_loss_per_volume": "1000",
            "margin_per_volume": "1000",
            "volume_step": "0.01",
            "minimum_volume": "0.01",
            "maximum_volume": "10",
            "minimum_execution_steps": 1,
            "decision_context": [],
        },
        "provider_observation": {
            "provider_key": "ctrader-demo",
            "qore_symbol": "GBPUSD",
            "provider_symbol": "GBPUSD",
            "bid": "1.25",
            "ask": "1.25",
            "contract_size": "100000",
            "tick_size": "0.0001",
            "tick_value": "10",
            "minimum_volume": "0.01",
            "maximum_volume": "10",
            "volume_step": "0.01",
            "margin_per_volume": "1000",
            "commission_per_volume_usd": "0",
            "slippage_reserve_per_volume_usd": "0",
            "observed_at": (
                decision_at - timedelta(milliseconds=200)
            ).isoformat(),
        },
        "candidate": {
            "signal_fingerprint": signal,
            "trader_id": TraderLineage.R43_GBPUSD.value,
            "qore_symbol": "GBPUSD",
            "provider_symbol": "GBPUSD",
        },
    }


def _decision(index: int, decision_at) -> Phase20ForwardDecisionSeal:
    signal = f"signal-{index}"
    payload = {
        "evidence_kind": "FORWARD_OBSERVED",
        "hard_risk_headroom_usd": "20",
        "candidates": [_candidate(index, decision_at)],
    }
    return Phase20ForwardDecisionSeal(
        evidence_id=f"decision-{index}",
        decision_epoch_id=f"epoch-{index}",
        evidence_sha256="sha256:" + f"{index + 1:064x}",
        decision_at=decision_at,
        candidate_id="phase20-candidate",
        code_sha="a" * 40,
        parameter_sha256="sha256:" + ("b" * 64),
        signal_fingerprints=(signal,),
        canonical_payload_json=json.dumps(payload, sort_keys=True),
        collector_git_sha="c" * 40,
        sealed_at=decision_at + timedelta(milliseconds=100),
        seal_deadline_at=decision_at + timedelta(seconds=2),
    )


def _outcome(
    decision: Phase20ForwardDecisionSeal,
    index: int,
) -> Phase20ForwardOutcomeSeal:
    risk = Decimal("5")
    pnl = Decimal("-2")
    return Phase20ForwardOutcomeSeal(
        evidence_id=f"outcome-{index}",
        decision_evidence_sha256=decision.evidence_sha256,
        signal_fingerprint=f"signal-{index}",
        position_id=index + 1,
        execution_risk_evidence_id=f"risk-{index}",
        settlement_deal_ids=(7000 + index,),
        fill_evidence_refs=(f"fill-{index}",),
        observed_at=decision.decision_at + timedelta(minutes=10),
        realized_net_pnl_usd=pnl,
        executed_initial_stop_risk_usd=risk,
        realized_structural_outcome_r=pnl / risk,
    )


def _recommendation_fixture():
    first_at = T13_SHADOW_POLICY_FROZEN_AT + timedelta(minutes=5)
    second_at = first_at + timedelta(hours=1)
    first = _decision(0, first_at)
    second = _decision(1, second_at)
    prior = _outcome(first, 0)
    book = VersionedPhase20ForwardEvidenceBook(
        generation=3,
        decisions=(first, second),
        outcomes=(prior,),
    )
    recommendation = evaluate_phase20_t13_shadow_decision(
        evidence_book=book,
        decision=second,
    )
    return book, recommendation


def test_t13_shadow_store_seals_before_outcome(tmp_path) -> None:
    book, recommendation = _recommendation_fixture()
    def clock():
        return recommendation.decision_at + timedelta(milliseconds=500)

    store = DurableT13ShadowDecisionStore(
        tmp_path / "t13-shadow.json",
        clock=clock,
    )

    sealed = store.seal_recommendation(
        recommendation,
        evidence_book=book,
        expected_generation=0,
    )

    assert sealed.generation == 1
    assert sealed.chain_sha256.startswith("sha256:")
    assert len(sealed.decisions) == 1
    decision = sealed.decisions[0]
    assert decision.decision_evidence_sha256 == (
        recommendation.decision_evidence_sha256
    )
    assert decision.reserve_triggered is True
    assert decision.reserved_risk_usd == Decimal("10")
    assert store.load() == sealed


def test_t13_shadow_store_rejects_after_same_epoch_outcome(tmp_path) -> None:
    book, recommendation = _recommendation_fixture()
    second = book.decision_for_sha(recommendation.decision_evidence_sha256)
    assert second is not None
    contaminated = VersionedPhase20ForwardEvidenceBook(
        generation=book.generation + 1,
        decisions=book.decisions,
        outcomes=book.outcomes + (_outcome(second, 1),),
    )
    store = DurableT13ShadowDecisionStore(
        tmp_path / "t13-shadow.json",
        clock=lambda: recommendation.decision_at + timedelta(seconds=1),
    )

    with pytest.raises(
        DurableT13ShadowDecisionError,
        match="cannot seal after outcome exists",
    ):
        store.seal_recommendation(
            recommendation,
            evidence_book=contaminated,
            expected_generation=0,
        )


def test_t13_shadow_store_rejects_late_physical_seal(tmp_path) -> None:
    book, recommendation = _recommendation_fixture()
    store = DurableT13ShadowDecisionStore(
        tmp_path / "t13-shadow.json",
        clock=lambda: recommendation.decision_at + timedelta(seconds=3),
    )

    with pytest.raises(
        DurableT13ShadowDecisionError,
        match="exceeds frozen two-second window",
    ):
        store.seal_recommendation(
            recommendation,
            evidence_book=book,
            expected_generation=0,
        )


def test_t13_shadow_store_detects_chain_tampering(tmp_path) -> None:
    book, recommendation = _recommendation_fixture()
    path = tmp_path / "t13-shadow.json"
    store = DurableT13ShadowDecisionStore(
        path,
        clock=lambda: recommendation.decision_at + timedelta(seconds=1),
    )
    store.seal_recommendation(
        recommendation,
        evidence_book=book,
        expected_generation=0,
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["chain_sha256"] = "sha256:" + ("f" * 64)
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(
        DurableT13ShadowDecisionError,
        match="terminal chain mismatch",
    ):
        store.load()


def test_t13_shadow_store_generation_conflict_fails_closed(tmp_path) -> None:
    book, recommendation = _recommendation_fixture()
    store = DurableT13ShadowDecisionStore(
        tmp_path / "t13-shadow.json",
        clock=lambda: recommendation.decision_at + timedelta(seconds=1),
    )

    with pytest.raises(
        DurableT13ShadowDecisionError,
        match="generation conflict",
    ):
        store.seal_recommendation(
            recommendation,
            evidence_book=book,
            expected_generation=1,
        )
