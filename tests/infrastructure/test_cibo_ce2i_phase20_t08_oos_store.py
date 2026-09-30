import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.cibo_ce2i_phase20_t08_oos_store import (
    DurableT08OosShadowError,
    DurableT08OosShadowStore,
    T08ShadowDecisionSeal,
    T08ShadowOutcomeSeal,
)

BASE = datetime(2026, 9, 29, 2, tzinfo=UTC)


def _decision(index: int = 0) -> T08ShadowDecisionSeal:
    decision_at = BASE + timedelta(minutes=5 * index)
    return T08ShadowDecisionSeal(
        epoch_id=f"epoch-{index}",
        decision_at=decision_at,
        shadow_sealed_at=decision_at + timedelta(milliseconds=100),
        baseline_selected_count=1,
        treatment_selected_count=2,
        treatment_gross_stop_risk_usd=Decimal("10"),
        treatment_netted_risk_usd=Decimal("8"),
        netting_credit_usd=Decimal("2"),
        risk_mapping_evidence_id=f"risk-map:{index}",
        correlation_evidence_id=f"correlation:{index}",
    )


def _outcome(
    decision: T08ShadowDecisionSeal,
    *,
    pnl: Decimal = Decimal("1.5"),
) -> T08ShadowOutcomeSeal:
    return T08ShadowOutcomeSeal(
        epoch_id=decision.epoch_id,
        decision_sha256=decision.decision_sha256,
        outcome_observed_at=decision.shadow_sealed_at + timedelta(hours=1),
        baseline_realized_net_pnl_usd=Decimal("1"),
        treatment_realized_net_pnl_usd=pnl,
        baseline_peak_loss_usd=Decimal("5"),
        treatment_peak_loss_usd=Decimal("4"),
        outcome_evidence_ids=(f"outcome:{decision.epoch_id}",),
    )


def test_store_seals_decision_before_outcome_and_materializes_epoch(
    tmp_path,
) -> None:
    store = DurableT08OosShadowStore(tmp_path / "t08-oos.json")
    decision = _decision()
    book = store.append_decision(decision, expected_generation=0)
    assert book.generation == 1
    assert book.chain_sha256.startswith("sha256:")
    assert book.complete_epochs() == ()

    outcome = _outcome(decision)
    book = store.append_outcome(outcome, expected_generation=1)
    assert book.generation == 2
    assert len(book.complete_epochs()) == 1
    epoch = book.complete_epochs()[0]
    assert epoch.epoch_id == decision.epoch_id
    assert epoch.shadow_sealed_at < epoch.outcome_observed_at
    assert epoch.netting_credit_usd == Decimal("2")
    assert epoch.treatment_realized_net_pnl_usd == Decimal("1.5")

    reloaded = store.load()
    assert reloaded == book
    assert reloaded.complete_epochs() == book.complete_epochs()


def test_store_rejects_outcome_without_sealed_decision(tmp_path) -> None:
    store = DurableT08OosShadowStore(tmp_path / "t08-oos.json")
    decision = _decision()
    outcome = _outcome(decision)

    with pytest.raises(
        DurableT08OosShadowError,
        match="decision epoch not found",
    ):
        store.append_outcome(outcome, expected_generation=0)


def test_store_rejects_outcome_bound_to_wrong_decision_sha(tmp_path) -> None:
    store = DurableT08OosShadowStore(tmp_path / "t08-oos.json")
    decision = _decision()
    book = store.append_decision(decision, expected_generation=0)
    wrong = T08ShadowOutcomeSeal(
        epoch_id=decision.epoch_id,
        decision_sha256="sha256:" + ("f" * 64),
        outcome_observed_at=decision.shadow_sealed_at + timedelta(hours=1),
        baseline_realized_net_pnl_usd=Decimal("1"),
        treatment_realized_net_pnl_usd=Decimal("1"),
        baseline_peak_loss_usd=Decimal("1"),
        treatment_peak_loss_usd=Decimal("1"),
        outcome_evidence_ids=("outcome",),
    )

    with pytest.raises(
        DurableT08OosShadowError,
        match="decision SHA mismatch",
    ):
        store.append_outcome(wrong, expected_generation=book.generation)


def test_store_rejects_conflicting_decision_for_same_epoch(tmp_path) -> None:
    store = DurableT08OosShadowStore(tmp_path / "t08-oos.json")
    decision = _decision()
    store.append_decision(decision, expected_generation=0)
    conflict = T08ShadowDecisionSeal(
        epoch_id=decision.epoch_id,
        decision_at=decision.decision_at,
        shadow_sealed_at=decision.shadow_sealed_at,
        baseline_selected_count=1,
        treatment_selected_count=3,
        treatment_gross_stop_risk_usd=Decimal("10"),
        treatment_netted_risk_usd=Decimal("8"),
        netting_credit_usd=Decimal("2"),
        risk_mapping_evidence_id=decision.risk_mapping_evidence_id,
        correlation_evidence_id=decision.correlation_evidence_id,
    )

    with pytest.raises(
        DurableT08OosShadowError,
        match="conflicting decision",
    ):
        store.append_decision(conflict, expected_generation=1)


def test_store_detects_terminal_chain_tampering(tmp_path) -> None:
    path = tmp_path / "t08-oos.json"
    store = DurableT08OosShadowStore(path)
    store.append_decision(_decision(), expected_generation=0)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["chain_sha256"] = "sha256:" + ("f" * 64)
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(
        DurableT08OosShadowError,
        match="terminal chain mismatch",
    ):
        store.load()


def test_generation_conflict_fails_closed(tmp_path) -> None:
    store = DurableT08OosShadowStore(tmp_path / "t08-oos.json")

    with pytest.raises(
        DurableT08OosShadowError,
        match="generation conflict",
    ):
        store.append_decision(_decision(), expected_generation=1)
