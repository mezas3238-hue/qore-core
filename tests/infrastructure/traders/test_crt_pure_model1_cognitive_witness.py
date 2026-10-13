"""Structural/causal tests only: no market PnL or historical optimization."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.traders.crt_pure_cognitive_contract import (
    CrtPureKnowledgeState,
    CrtPureReasoningAction,
)
from qore.infrastructure.traders.crt_pure_cognitive_state import reason
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket
from qore.infrastructure.traders.crt_pure_model1 import (
    CrtPureModel1Bar,
    CrtPureModel1Reference,
    CrtPureModel1ReferenceKind,
    CrtPureModel1State,
    assess_model1_confirmation,
    detect_model1_candidate,
)
from qore.infrastructure.traders.crt_pure_model1_cognitive_witness import (
    CrtPureModel1CausalWitness,
    build_model1_cognitive_situation,
)


def _bar(
    hour: int, minute: int, opened: int, high: int, low: int, closed: int
) -> CrtPureModel1Bar:
    return CrtPureModel1Bar(
        opened_at=datetime(2026, 1, 2, hour, minute, tzinfo=UTC),
        open_price=opened,
        high_price=high,
        low_price=low,
        close_price=closed,
    )


def _bearish_witness(
    *, confirm_close: int = 103
) -> CrtPureModel1CausalWitness:
    origin = _bar(9, 0, 104, 105, 102, 103)
    reference = CrtPureModel1Reference(
        kind=CrtPureModel1ReferenceKind.OLD_HIGH,
        price=origin.high_price,
        evidence_id="old-high-001",
    )
    candidate = detect_model1_candidate(
        reference=reference, candle=_bar(10, 0, 104, 108, 103, 107)
    )
    assert candidate is not None
    confirmation = assess_model1_confirmation(
        candidate=candidate, candle=_bar(10, 15, 105, 106, 100, confirm_close)
    )
    return CrtPureModel1CausalWitness(
        market=CrtPureMarket.AUDUSD,
        parent_crt_id="h4-parent-001",
        parent_c3_opened_at=datetime(2026, 1, 2, 8, 0, tzinfo=UTC),
        parent_c3_closed_at=datetime(2026, 1, 2, 12, 0, tzinfo=UTC),
        reference_bar=origin,
        reference_known_at=datetime(2026, 1, 2, 9, 15, tzinfo=UTC),
        eligible_reference_ids=("old-high-001",),
        confirmation=confirmation,
        observed_at=datetime(2026, 1, 2, 10, 30, tzinfo=UTC),
    )


def _reason(
    witness: CrtPureModel1CausalWitness, **overrides: bool
) -> tuple[CrtPureKnowledgeState, CrtPureReasoningAction, tuple[str, ...]]:
    flags = {
        "data_integrity_ok": True,
        "strategy_identity_ready": True,
        "destination_context_known": True,
        "destination_available": True,
        "execution_data_fresh": True,
    }
    flags.update(overrides)
    situation = build_model1_cognitive_situation(witness, **flags)
    result = reason(situation)
    return situation.knowledge_state, result.action, result.auditable_why


def test_confirmed_old_high_witness_remains_partial_until_source_ownership_closed() -> None:
    witness = _bearish_witness()
    knowledge, action, why = _reason(witness)
    assert witness.source_event_id.startswith("AUDUSD:h4-parent-001:")
    assert knowledge is CrtPureKnowledgeState.PARTIAL
    assert action is CrtPureReasoningAction.WAIT
    assert "MODEL_1_REFERENCE_SELECTION_AMBIGUOUS" in why
    assert "KNOWLEDGE_STATE_PARTIAL" in why


def test_source_candle_with_multiple_reference_ids_is_one_identity_not_two() -> None:
    witness = _bearish_witness()
    many = replace(
        witness,
        eligible_reference_ids=("old-high-001", "another-old-high-002"),
    )
    single_knowledge, _, _ = _reason(witness)
    multi_knowledge, action, _ = _reason(many)
    assert many.source_event_id == witness.source_event_id
    assert single_knowledge is multi_knowledge is CrtPureKnowledgeState.PARTIAL
    assert action is CrtPureReasoningAction.WAIT


def test_wick_only_cannot_promote_body_confirmation() -> None:
    # Source body bottom is 104, close 105 is still unconfirmed.
    witness = _bearish_witness(confirm_close=105)
    assert witness.confirmation.state is CrtPureModel1State.AWAITING_CONFIRMATION
    situation = build_model1_cognitive_situation(
        witness,
        data_integrity_ok=True,
        strategy_identity_ready=True,
        destination_context_known=True,
        destination_available=True,
        execution_data_fresh=True,
    )
    assert situation.confirmation_complete is False
    assert reason(situation).action is CrtPureReasoningAction.WAIT


def test_old_level_available_only_after_source_is_rejected() -> None:
    witness = _bearish_witness()
    with pytest.raises(ValueError, match="not known before source"):
        replace(witness, reference_known_at=witness.observed_at)


def test_old_level_origin_price_must_match_original_candle() -> None:
    witness = _bearish_witness()
    fake = _bar(9, 0, 104, 104, 102, 103)
    with pytest.raises(ValueError, match="price disagrees"):
        replace(witness, reference_bar=fake)


def test_pivot_candle_must_close_before_being_known() -> None:
    witness = _bearish_witness()
    with pytest.raises(ValueError, match="origin candle closes"):
        replace(
            witness,
            reference_known_at=witness.reference_bar.opened_at,
        )


def test_confirmation_status_is_recomputed_from_body_close() -> None:
    witness = _bearish_witness()
    forged = replace(
        witness.confirmation, state=CrtPureModel1State.AWAITING_CONFIRMATION
    )
    with pytest.raises(ValueError, match="confirmation does not match"):
        replace(witness, confirmation=forged)


def test_witness_cannot_use_confirmation_before_completed_m15_close() -> None:
    witness = _bearish_witness()
    with pytest.raises(ValueError, match="observe confirmation before close"):
        replace(witness, observed_at=witness.observed_at - timedelta(minutes=1))


def test_source_outside_parent_c3_is_rejected() -> None:
    witness = _bearish_witness()
    with pytest.raises(ValueError, match="source must open within parent C3"):
        replace(
            witness,
            parent_c3_opened_at=datetime(2026, 1, 2, 12, 0, tzinfo=UTC),
            parent_c3_closed_at=datetime(2026, 1, 2, 16, 0, tzinfo=UTC),
        )


def test_reference_set_requires_selected_evidence_id() -> None:
    witness = _bearish_witness()
    with pytest.raises(ValueError, match="selected reference absent"):
        replace(witness, eligible_reference_ids=("another-high",))


def test_unverified_external_data_fails_closed_without_claiming_profitability() -> None:
    knowledge, action, why = _reason(
        _bearish_witness(), data_integrity_ok=False
    )
    assert knowledge is CrtPureKnowledgeState.PARTIAL
    assert action is CrtPureReasoningAction.ABSTAIN
    assert "DATA_INTEGRITY_FAILED" in why


def test_unready_strategy_identity_stays_in_external_authority_boundary() -> None:
    _, action, why = _reason(_bearish_witness(), strategy_identity_ready=False)
    assert action is CrtPureReasoningAction.ABSTAIN
    assert "CRT_SOURCE_STRATEGY_NOT_CLOSED" in why


def test_origin_evidence_is_traceable_in_causal_observation_tokens() -> None:
    witness = _bearish_witness()
    situation = build_model1_cognitive_situation(
        witness,
        data_integrity_ok=True,
        strategy_identity_ready=True,
        destination_context_known=False,
        destination_available=False,
        execution_data_fresh=True,
    )
    names = {row.name for row in situation.observations}
    assert names == {
        "MODEL1_REFERENCE_ORIGIN",
        "MODEL1_ELIGIBLE_REFERENCE_SET",
        "MODEL1_SOURCE_BAR_CLOSE",
        "MODEL1_CONFIRMING_BODY_CLOSE",
    }
    assert all(row.observed_at <= situation.observed_at for row in situation.observations)
    assert reason(situation).action is CrtPureReasoningAction.WAIT
