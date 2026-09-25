from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.traders.crt_pure_cognitive_contract import (
    COGNITIVE_LAYER_ORDER,
    CRT_PURE_MARKET_BRAINS,
    FROZEN_CRT_PURE_COGNITIVE_CONTRACT,
    CrtPureAttentionState,
    CrtPureHypothesisStage,
    CrtPureKnowledgeState,
    CrtPureReasoningAction,
)
from qore.infrastructure.traders.crt_pure_cognitive_state import (
    CrtPureCausalObservation,
    CrtPureSituationModel,
    reason,
    transition_hypothesis,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket
from qore.infrastructure.traders.crt_pure_position_intelligence import (
    CrtPureOpenPositionState,
    CrtPurePositionSide,
    rearm_is_genuinely_new,
)


def _state(**overrides: object) -> CrtPureSituationModel:
    now = datetime(2026, 9, 20, 15, 0, tzinfo=UTC)
    values: dict[str, object] = {
        "market": CrtPureMarket.AUDUSD,
        "observed_at": now,
        "hypothesis_id": "hyp-1",
        "source_event_id": "event-1",
        "event_generation": 1,
        "attention_state": CrtPureAttentionState.DECISION,
        "hypothesis_stage": CrtPureHypothesisStage.CONFIRMED,
        "data_integrity_ok": True,
        "strategy_identity_ready": True,
        "source_event_present": True,
        "confirmation_complete": True,
        "destination_context_known": True,
        "destination_available": True,
        "execution_data_fresh": True,
        "knowledge_state": CrtPureKnowledgeState.KNOWN,
        "observations": (
            CrtPureCausalObservation(
                name="decision-time-fact",
                observed_at=now,
                value_token="present",
            ),
        ),
    }
    values.update(overrides)
    return CrtPureSituationModel(**values)  # type: ignore[arg-type]


def test_hybrid_cognitive_contract_is_three_market_and_excludes_crt_amd() -> None:
    contract = FROZEN_CRT_PURE_COGNITIVE_CONTRACT
    assert contract.markets == (
        CrtPureMarket.AUDUSD,
        CrtPureMarket.USDJPY,
        CrtPureMarket.BTCUSD,
    )
    assert contract.crt_amd_allowed is False
    assert contract.layers == COGNITIVE_LAYER_ORDER
    assert contract.qore_risk_is_final_capital_authority is True


def test_market_brains_share_strategy_identity_but_not_experience_memory() -> None:
    assert len(CRT_PURE_MARKET_BRAINS) == 3
    assert len({item.strategy_identity_id for item in CRT_PURE_MARKET_BRAINS}) == 1
    assert len({item.experience_memory_id for item in CRT_PURE_MARKET_BRAINS}) == 3
    assert {item.market for item in CRT_PURE_MARKET_BRAINS} == {
        CrtPureMarket.AUDUSD,
        CrtPureMarket.USDJPY,
        CrtPureMarket.BTCUSD,
    }


def test_future_observation_is_rejected_from_situation_model() -> None:
    now = datetime(2026, 9, 20, 15, 0, tzinfo=UTC)
    with pytest.raises(ValueError, match="future observation"):
        _state(
            observed_at=now,
            observations=(
                CrtPureCausalObservation(
                    name="future",
                    observed_at=now + timedelta(seconds=1),
                    value_token="forbidden",
                ),
            ),
        )


def test_reasoning_executes_only_when_causal_and_adversarial_checks_pass() -> None:
    decision = reason(_state())
    assert decision.action is CrtPureReasoningAction.EXECUTE
    assert decision.grants_capital_authority is False
    assert "ACTION:EXECUTE" in decision.auditable_why


def test_incomplete_confirmation_waits_but_broken_evidence_abstains() -> None:
    wait = reason(
        _state(
            confirmation_complete=False,
            hypothesis_stage=CrtPureHypothesisStage.AWAITING_CONFIRMATION,
        )
    )
    assert wait.action is CrtPureReasoningAction.WAIT

    abstain = reason(_state(data_integrity_ok=False))
    assert abstain.action is CrtPureReasoningAction.ABSTAIN


def test_killed_thesis_cannot_resurrect() -> None:
    with pytest.raises(ValueError, match="invalid CRT hypothesis transition"):
        transition_hypothesis(
            CrtPureHypothesisStage.THESIS_KILLED,
            CrtPureHypothesisStage.HYPOTHESIS_FORMING,
        )


def test_position_stop_cannot_widen() -> None:
    with pytest.raises(ValueError, match="LONG stop cannot widen"):
        CrtPureOpenPositionState(
            hypothesis_id="hyp-1",
            source_event_id="event-1",
            side=CrtPurePositionSide.LONG,
            entry_price=Decimal("100"),
            original_stop_price=Decimal("95"),
            current_stop_price=Decimal("94"),
            original_target_price=Decimal("110"),
            current_target_price=Decimal("110"),
        )


def test_rearm_requires_new_hypothesis_source_and_generation() -> None:
    new_state = _state(
        hypothesis_id="hyp-2",
        source_event_id="event-2",
        event_generation=2,
    )
    assert rearm_is_genuinely_new(
        prior_hypothesis_id="hyp-1",
        prior_source_event_id="event-1",
        prior_event_generation=1,
        new_situation=new_state,
    )

    same_source = _state(
        hypothesis_id="hyp-2",
        source_event_id="event-1",
        event_generation=2,
    )
    assert not rearm_is_genuinely_new(
        prior_hypothesis_id="hyp-1",
        prior_source_event_id="event-1",
        prior_event_generation=1,
        new_situation=same_source,
    )
