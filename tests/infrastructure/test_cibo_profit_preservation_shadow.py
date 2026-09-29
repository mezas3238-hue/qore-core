from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
)
from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError
from qore.infrastructure.cibo_profit_preservation_shadow import (
    GENC7_POLICY_FROZEN_AT,
    Genc7Action,
    Genc7CapitalStateEvidence,
    Genc7PreservationProposalEvidence,
    Genc7SourceBucket,
    evaluate_genc7_profit_preservation_shadow,
    genc7_policy_sha256,
)
from qore.infrastructure.cibo_profit_preservation_store import (
    DurableGenc7ProfitPreservationShadowStore,
)
from qore.infrastructure.market_test_environment import MarketRuntimeEnvironment

T0 = datetime(2026, 9, 29, 23, 35, tzinfo=UTC)


def _identity(
    account_ref: str = "genc7-test",
) -> CiboAccountCapitalIdentity:
    return CiboAccountCapitalIdentity(
        provider_key="ctrader",
        account_ref=account_ref,
        environment=MarketRuntimeEnvironment.TEST,
    )


def _state(
    *,
    identity: CiboAccountCapitalIdentity | None = None,
) -> Genc7CapitalStateEvidence:
    return Genc7CapitalStateEvidence(
        evidence_id="genc7-state-001",
        decision_at=T0,
        account_identity=identity or _identity(),
        current_realized_capital_usd=Decimal("92"),
        current_realized_profit_usd=Decimal("32"),
        peak_realized_profit_usd=Decimal("40"),
        current_base_capital_usd=Decimal("58"),
        peak_base_capital_usd=Decimal("60"),
        current_compound_capital_usd=Decimal("24"),
        peak_compound_capital_usd=Decimal("30"),
        protected_profit_usd=Decimal("12"),
        protected_floor_usd=Decimal("18"),
        previous_protected_floor_usd=Decimal("15"),
        strategic_reserve_usd=Decimal("5"),
        opportunity_reserve_usd=Decimal("3"),
        compoundable_usd=Decimal("14"),
        released_compound_capital_usd=Decimal("4"),
        source_evidence_sha256="sha256:" + "a" * 64,
    )


def _proposal(
    *,
    action: Genc7Action = Genc7Action.PROTECT,
    source_bucket: Genc7SourceBucket = (
        Genc7SourceBucket.REALIZED_UNPROTECTED_PROFIT
    ),
    amount: str = "10",
    identity: CiboAccountCapitalIdentity | None = None,
    calibrated: bool = True,
    capital_eligible: bool = True,
) -> Genc7PreservationProposalEvidence:
    return Genc7PreservationProposalEvidence(
        proposal_id="genc7-proposal-001",
        decision_at=T0,
        account_identity=identity or _identity(),
        action=action,
        source_bucket=source_bucket,
        amount_usd=Decimal(amount),
        evidence_sha256="sha256:" + "b" * 64,
        rationale_code="FROZEN_CAUSAL_PROPOSAL",
        calibrated=calibrated,
        capital_eligible=capital_eligible,
    )


def test_genc7_metrics_are_explicit_and_realized_only() -> None:
    state = _state()

    assert state.giveback_amount_usd == Decimal("8")
    assert state.profit_retention_ratio == Decimal("0.8")
    assert state.base_drawdown_usd == Decimal("2")
    assert state.compound_drawdown_usd == Decimal("6")
    assert state.floor_growth_rate == Decimal("0.2")
    assert state.realized_unprotected_profit_usd == Decimal("20")
    assert state.compound_candidate_capacity_usd == Decimal("18")
    assert state.floating_pnl_included is False
    assert state.future_outcome_present is False


def test_genc7_uses_exact_preregistered_amount_without_resizing() -> None:
    decision = evaluate_genc7_profit_preservation_shadow(
        state=_state(),
        proposal=_proposal(amount="10"),
        decision_id="genc7-decision-001",
    )

    assert decision.policy_frozen_at == GENC7_POLICY_FROZEN_AT
    assert decision.policy_sha256 == genc7_policy_sha256()
    assert decision.control_action is Genc7Action.HOLD_CURRENT_CAPITAL_STATE
    assert decision.control_amount_usd == Decimal("0")
    assert decision.treatment_action is Genc7Action.PROTECT
    assert decision.treatment_amount_usd == Decimal("10")
    assert decision.blocker_codes == ()
    assert decision.treatment_differs_from_control is True
    assert decision.outcome_present_at_seal is False
    assert decision.runtime_authority is False
    assert decision.sizing_authority is False
    assert decision.risk_authority is False
    assert decision.execution_authority is False


def test_genc7_holds_when_proposal_not_capital_eligible() -> None:
    decision = evaluate_genc7_profit_preservation_shadow(
        state=_state(),
        proposal=_proposal(capital_eligible=False),
        decision_id="genc7-ineligible",
    )

    assert decision.treatment_action is Genc7Action.HOLD_CURRENT_CAPITAL_STATE
    assert decision.treatment_amount_usd == 0
    assert decision.blocker_codes == ("PROPOSAL_NOT_CAPITAL_ELIGIBLE",)
    assert decision.treatment_differs_from_control is False


def test_genc7_holds_when_source_bucket_cannot_fund_proposal() -> None:
    decision = evaluate_genc7_profit_preservation_shadow(
        state=_state(),
        proposal=_proposal(amount="21"),
        decision_id="genc7-over-capacity",
    )

    assert decision.treatment_action is Genc7Action.HOLD_CURRENT_CAPITAL_STATE
    assert decision.treatment_amount_usd == 0
    assert decision.blocker_codes == ("SOURCE_BUCKET_CAPACITY_INSUFFICIENT",)


def test_genc7_compound_can_only_use_compoundable_or_released_capacity() -> None:
    proposal = _proposal(
        action=Genc7Action.COMPOUND,
        source_bucket=Genc7SourceBucket.COMPOUNDABLE_OR_RELEASED_CAPACITY,
        amount="18",
    )
    decision = evaluate_genc7_profit_preservation_shadow(
        state=_state(),
        proposal=proposal,
        decision_id="genc7-compound",
    )

    assert decision.treatment_action is Genc7Action.COMPOUND
    assert decision.treatment_amount_usd == Decimal("18")

    with pytest.raises(
        CiboCompoundCapitalError,
        match="action/source bucket mismatch",
    ):
        replace(
            proposal,
            source_bucket=Genc7SourceBucket.REALIZED_UNPROTECTED_PROFIT,
        )


def test_genc7_rejects_floating_pnl_house_money_and_cross_account() -> None:
    with pytest.raises(
        CiboCompoundCapitalError,
        match="realized-only pre-outcome",
    ):
        replace(_state(), floating_pnl_included=True)

    with pytest.raises(
        CiboCompoundCapitalError,
        match="forbidden outcome/bias/authority",
    ):
        replace(_proposal(), house_money_bias=True)

    with pytest.raises(
        CiboCompoundCapitalError,
        match="account binding drift",
    ):
        evaluate_genc7_profit_preservation_shadow(
            state=_state(),
            proposal=_proposal(identity=_identity("other-account")),
            decision_id="genc7-cross-account",
        )


def test_genc7_rejects_protected_floor_ratchet_down() -> None:
    with pytest.raises(
        CiboCompoundCapitalError,
        match="cannot ratchet downward",
    ):
        replace(
            _state(),
            protected_floor_usd=Decimal("14"),
            previous_protected_floor_usd=Decimal("15"),
        )


def test_genc7_rejects_pre_freeze_decision() -> None:
    state = replace(
        _state(),
        decision_at=GENC7_POLICY_FROZEN_AT - timedelta(seconds=1),
    )
    proposal = replace(
        _proposal(),
        decision_at=state.decision_at,
    )
    with pytest.raises(
        CiboCompoundCapitalError,
        match="pre-freeze state",
    ):
        evaluate_genc7_profit_preservation_shadow(
            state=state,
            proposal=proposal,
            decision_id="genc7-pre-freeze",
        )


def test_genc7_store_hash_chain_restart_cas_and_conflict(tmp_path) -> None:
    decision = evaluate_genc7_profit_preservation_shadow(
        state=_state(),
        proposal=_proposal(),
        decision_id="genc7-store-decision",
    )
    path = tmp_path / "genc7-shadow.json"
    store = DurableGenc7ProfitPreservationShadowStore(path)
    sealed_at = T0 + timedelta(seconds=1)

    first = store.seal(
        decision,
        sealed_at=sealed_at,
        expected_generation=0,
    )
    assert first.generation == 1
    assert first.chain_sha256.startswith("sha256:")
    assert first.seal_for_decision(decision.decision_id) is not None

    restarted = DurableGenc7ProfitPreservationShadowStore(path)
    assert restarted.load() == first

    idempotent = restarted.seal(
        decision,
        sealed_at=sealed_at,
        expected_generation=1,
    )
    assert idempotent == first

    with pytest.raises(
        CiboCompoundCapitalError,
        match="generation conflict",
    ):
        restarted.seal(
            decision,
            sealed_at=sealed_at,
            expected_generation=0,
        )

    changed = replace(
        decision,
        treatment_amount_usd=Decimal("9"),
    )
    with pytest.raises(
        CiboCompoundCapitalError,
        match="conflicting decision rewrite",
    ):
        restarted.seal(
            changed,
            sealed_at=sealed_at,
            expected_generation=1,
        )
