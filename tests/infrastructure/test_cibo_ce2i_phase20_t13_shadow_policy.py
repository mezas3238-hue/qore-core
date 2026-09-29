from __future__ import annotations

import json
from datetime import timedelta
from decimal import Decimal

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    Phase20ForwardDecisionSeal,
    Phase20ForwardOutcomeSeal,
    VersionedPhase20ForwardEvidenceBook,
)
from qore.infrastructure.cibo_ce2i_phase20_t13_shadow_policy import (
    T13_SHADOW_POLICY_FROZEN_AT,
    T13_SHADOW_POLICY_ID,
    assess_phase20_t13_shadow_policy,
    t13_shadow_policy_sha256,
)


def _candidate(index: int, decision_at) -> dict[str, object]:
    signal = f"signal-{index}"
    opportunity = {
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
    }
    provider = {
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
    }
    return {
        "provider_evidence_id": f"provider:{index}",
        "opportunity": opportunity,
        "provider_observation": provider,
        "candidate": {
            "signal_fingerprint": signal,
            "trader_id": TraderLineage.R43_GBPUSD.value,
            "qore_symbol": "GBPUSD",
            "provider_symbol": "GBPUSD",
        },
    }


def _decision(
    index: int,
    *,
    decision_at,
    hard_headroom: Decimal = Decimal("20"),
) -> Phase20ForwardDecisionSeal:
    candidate = _candidate(index, decision_at)
    payload = {
        "evidence_kind": "FORWARD_OBSERVED",
        "hard_risk_headroom_usd": str(hard_headroom),
        "candidates": [candidate],
    }
    return Phase20ForwardDecisionSeal(
        evidence_id=f"decision-{index}",
        decision_epoch_id=f"epoch-{index}",
        evidence_sha256="sha256:" + f"{index + 1:064x}",
        decision_at=decision_at,
        candidate_id="phase20-candidate",
        code_sha="a" * 40,
        parameter_sha256="sha256:" + ("b" * 64),
        signal_fingerprints=(f"signal-{index}",),
        canonical_payload_json=json.dumps(payload, sort_keys=True),
        collector_git_sha="c" * 40,
        sealed_at=decision_at + timedelta(milliseconds=100),
        seal_deadline_at=decision_at + timedelta(seconds=2),
    )


def _outcome(
    decision: Phase20ForwardDecisionSeal,
    index: int,
    pnl: Decimal,
) -> Phase20ForwardOutcomeSeal:
    risk = Decimal("5")
    return Phase20ForwardOutcomeSeal(
        evidence_id=f"outcome-{index}",
        decision_evidence_sha256=decision.evidence_sha256,
        signal_fingerprint=f"signal-{index}",
        position_id=index + 1,
        execution_risk_evidence_id=f"risk-{index}",
        settlement_deal_ids=(5000 + index,),
        fill_evidence_refs=(f"fill-{index}",),
        observed_at=decision.decision_at + timedelta(minutes=10),
        realized_net_pnl_usd=pnl,
        executed_initial_stop_risk_usd=risk,
        realized_structural_outcome_r=pnl / risk,
    )


def test_t13_shadow_policy_is_preregistered_and_parameter_free() -> None:
    assert T13_SHADOW_POLICY_ID.endswith("_V1")
    assert T13_SHADOW_POLICY_FROZEN_AT.isoformat() == (
        "2026-09-29T03:30:00+00:00"
    )
    assert t13_shadow_policy_sha256().startswith("sha256:")


def test_t13_shadow_policy_triggers_after_causal_loss_pressure() -> None:
    first_at = T13_SHADOW_POLICY_FROZEN_AT + timedelta(minutes=5)
    second_at = first_at + timedelta(hours=1)
    first = _decision(0, decision_at=first_at)
    second = _decision(1, decision_at=second_at)
    book = VersionedPhase20ForwardEvidenceBook(
        generation=3,
        decisions=(first, second),
        outcomes=(_outcome(first, 0, Decimal("-3")),),
    )

    audit = assess_phase20_t13_shadow_policy(book)

    assert audit.post_freeze_decision_epochs == 2
    assert audit.candidate_epochs == 2
    assert audit.causal_pressure_epochs == 1
    assert audit.arrival_evidence_epochs == 1
    assert audit.reserve_trigger_epochs == 1
    assert audit.full_seed_reserve_epochs == 1
    assert audit.partial_headroom_reserve_epochs == 0
    assert audit.total_shadow_reserved_risk_usd == Decimal("10")
    assert audit.maximum_shadow_reserved_risk_usd == Decimal("10")
    assert audit.shadow_policy_preregistered is True
    assert audit.reserve_policy_empirically_identified is False
    assert audit.fresh_oos_utility_demonstrated is False
    assert audit.runtime_authority is False


def test_t13_shadow_policy_excludes_pre_freeze_decisions() -> None:
    before = _decision(
        0,
        decision_at=T13_SHADOW_POLICY_FROZEN_AT - timedelta(minutes=1),
    )
    book = VersionedPhase20ForwardEvidenceBook(
        generation=1,
        decisions=(before,),
    )

    audit = assess_phase20_t13_shadow_policy(book)

    assert audit.post_freeze_decision_epochs == 0
    assert audit.reserve_trigger_epochs == 0
    assert "NO_POST_FREEZE_T13_SHADOW_DECISIONS" in audit.blockers


def test_t13_shadow_policy_reserves_remaining_headroom_if_below_seed() -> None:
    first_at = T13_SHADOW_POLICY_FROZEN_AT + timedelta(minutes=5)
    second_at = first_at + timedelta(hours=1)
    first = _decision(0, decision_at=first_at)
    second = _decision(
        1,
        decision_at=second_at,
        hard_headroom=Decimal("4"),
    )
    book = VersionedPhase20ForwardEvidenceBook(
        generation=3,
        decisions=(first, second),
        outcomes=(_outcome(first, 0, Decimal("-2")),),
    )

    audit = assess_phase20_t13_shadow_policy(book)

    assert audit.reserve_trigger_epochs == 1
    assert audit.full_seed_reserve_epochs == 0
    assert audit.partial_headroom_reserve_epochs == 1
    assert audit.total_shadow_reserved_risk_usd == Decimal("4")
    assert "FRESH_OOS_T13_RESERVE_UTILITY_REQUIRED" in audit.blockers
