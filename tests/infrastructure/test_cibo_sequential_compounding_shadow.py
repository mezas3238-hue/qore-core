from dataclasses import replace
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
)
from qore.infrastructure.cibo_compound_capital import (
    CiboCompoundCapitalError,
    CompoundCapitalState,
    CompoundRealizedProfitEvidence,
    create_realized_profit_lot,
)
from qore.infrastructure.cibo_compound_floor import (
    ProtectedCapitalFloorLedger,
)
from qore.infrastructure.cibo_compound_portfolio_ledger import (
    CompoundPortfolioLedger,
)
from qore.infrastructure.cibo_core_compound_portfolio import (
    AccountCoreCompoundPortfolio,
)
from qore.infrastructure.cibo_marginal_capital_utility_evidence import (
    MarginalCapitalUtilityEvidence,
)
from qore.infrastructure.cibo_sequential_compounding_shadow_policy import (
    GENC5_SHADOW_POLICY_FROZEN_AT,
    SequentialCompoundPosture,
    SequentialCompoundShadowAction,
    evaluate_genc5_sequential_compounding_shadow,
    genc5_shadow_policy_sha256,
)
from qore.infrastructure.cibo_sequential_compounding_shadow_store import (
    DurableGenc5SequentialCompoundingShadowStore,
)
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
)

T0 = GENC5_SHADOW_POLICY_FROZEN_AT + timedelta(seconds=10)


def _identity(
    account_ref: str = "genc5-demo",
) -> CiboAccountCapitalIdentity:
    return CiboAccountCapitalIdentity(
        provider_key="ctrader",
        account_ref=account_ref,
        environment=MarketRuntimeEnvironment.DEMO,
    )


def _profit_lot(
    *,
    identity: CiboAccountCapitalIdentity,
    lot_id: str,
    evidence_id: str,
    profit: str,
    position_id: int,
    deal_id: int,
):
    evidence = CompoundRealizedProfitEvidence(
        evidence_id=evidence_id,
        account_identity=identity,
        origin_trader=TraderLineage.VT31_NAS100,
        signal_fingerprint=f"{evidence_id}-signal",
        position_id=position_id,
        settlement_deal_ids=(deal_id,),
        realized_net_profit_usd=Decimal(profit),
        realized_at=T0 - timedelta(seconds=4),
        source_settlement_sha256="sha256:" + "a" * 64,
        settlement_reconciled=True,
        position_closed=True,
    )
    return create_realized_profit_lot(
        evidence,
        lot_id=lot_id,
        created_at=T0 - timedelta(seconds=3),
    )


def _portfolio(
    *,
    policy_protected: bool,
    account_ref: str = "genc5-demo",
) -> tuple[AccountCoreCompoundPortfolio, str]:
    identity = _identity(account_ref)
    lot = _profit_lot(
        identity=identity,
        lot_id="realized-100",
        evidence_id="settlement-100",
        profit="100",
        position_id=1001,
        deal_id=2001,
    )
    ledger = CompoundPortfolioLedger(
        account_identity=identity
    ).admit_realized_profit(
        lot,
        event_id="admit-100",
        occurred_at=T0 - timedelta(seconds=2),
    )
    ledger = ledger.transition(
        source_lot_id=lot.lot_id,
        to_state=CompoundCapitalState.RETIRED_TO_PROTECTED_FLOOR,
        amount_usd=Decimal("40"),
        moved_lot_id="floor-40",
        remainder_lot_id="realized-60",
        event_id="protect-40",
        occurred_at=T0 - timedelta(seconds=1),
    )
    ledger = ledger.transition(
        source_lot_id="realized-60",
        to_state=CompoundCapitalState.COMPOUNDABLE,
        amount_usd=Decimal("60"),
        moved_lot_id="compoundable-60",
        event_id="compoundable-60-event",
        occurred_at=T0,
    )
    floor = ProtectedCapitalFloorLedger(
        account_identity=identity
    ).admit_retired_lot(
        ledger.lot("floor-40"),
        tranche_id="floor-tranche",
        event_id="floor-admit",
        admitted_at=T0,
    )
    if policy_protected:
        floor = floor.upgrade_to_policy_protected(
            tranche_id="floor-tranche",
            event_id="floor-policy",
            occurred_at=T0,
            policy_id="GEN-C2-FLOOR-TEST",
            policy_sha256="sha256:" + "b" * 64,
        )
    return (
        AccountCoreCompoundPortfolio(
            account_identity=identity,
            compound_ledger=ledger,
            protected_floor_ledger=floor,
        ),
        "compoundable-60",
    )


def _evidence(
    portfolio: AccountCoreCompoundPortfolio,
    *,
    requested: str = "5",
    capacity: str | None = None,
    decision_at: datetime = T0,
) -> MarginalCapitalUtilityEvidence:
    current = (
        portfolio.compoundable_usd
        + portfolio.active_compound_capacity_usd
        + portfolio.released_compound_capital_usd
    )
    return MarginalCapitalUtilityEvidence(
        evidence_id="genc5-marginal",
        decision_at=decision_at,
        account_identity=portfolio.account_identity,
        trader_id=TraderLineage.VT31_NAS100,
        signal_fingerprint="genc5-signal",
        source_opportunity_decision_sha256="sha256:" + "7" * 64,
        source_baseline_policy_record_sha256="sha256:" + "8" * 64,
        current_compound_capacity_usd=(
            Decimal(capacity) if capacity is not None else current
        ),
        requested_incremental_capital_usd=Decimal(requested),
        expected_incremental_return_usd=Decimal("1.2"),
        incremental_stop_risk_usd=Decimal("0.8"),
        incremental_margin_usd=Decimal("4"),
        incremental_execution_cost_usd=Decimal("0.1"),
        incremental_concentration_risk_usd=Decimal("0.5"),
        incremental_drawdown_risk_proxy_usd=Decimal("0.4"),
        incremental_optionality_consumed_usd=Decimal("1"),
        expected_capital_minutes=Decimal("45"),
        epistemic_uncertainty=Decimal("0.25"),
        provider_evidence_sha256="sha256:" + "1" * 64,
        expectation_evidence_sha256="sha256:" + "2" * 64,
        factor_evidence_sha256="sha256:" + "3" * 64,
        duration_evidence_sha256="sha256:" + "4" * 64,
        execution_evidence_sha256="sha256:" + "5" * 64,
        optionality_evidence_sha256="sha256:" + "6" * 64,
    )


def test_genc5_policy_is_frozen_pre_outcome_and_authority_free() -> None:
    portfolio, source = _portfolio(policy_protected=True)
    evidence = _evidence(portfolio)

    decision = evaluate_genc5_sequential_compounding_shadow(
        portfolio=portfolio,
        evidence=evidence,
        source_lot_id=source,
        decision_id="decision-1",
    )

    assert decision.policy_sha256 == genc5_shadow_policy_sha256()
    assert (
        decision.control_posture
        is SequentialCompoundPosture.COMPOUND_PAUSED
    )
    assert (
        decision.control_action
        is SequentialCompoundShadowAction.HOLD_CURRENT_STATE
    )
    assert decision.control_requested_risk_review_usd == Decimal("0")
    assert (
        decision.treatment_posture
        is SequentialCompoundPosture.CAUTIOUS_COMPOUND
    )
    assert (
        decision.treatment_action
        is SequentialCompoundShadowAction.REQUEST_DOWNSTREAM_RISK_REVIEW
    )
    assert decision.treatment_requested_risk_review_usd == Decimal("5")
    assert decision.blocker_codes == ()
    assert decision.treatment_differs_from_control is True
    assert decision.outcome_present_at_seal is False
    assert decision.runtime_authority is False
    assert decision.risk_authority is False
    assert decision.execution_authority is False
    assert decision.live_authority is False
    assert decision.real_capital_authority is False


def test_genc5_does_not_resize_gen_c4_increment() -> None:
    portfolio, source = _portfolio(policy_protected=True)
    evidence = _evidence(portfolio, requested="7.25")

    decision = evaluate_genc5_sequential_compounding_shadow(
        portfolio=portfolio,
        evidence=evidence,
        source_lot_id=source,
        decision_id="decision-exact-amount",
    )

    assert (
        decision.treatment_requested_risk_review_usd
        == evidence.requested_incremental_capital_usd
        == Decimal("7.25")
    )


def test_genc5_requires_policy_protected_floor_before_forwarding() -> None:
    portfolio, source = _portfolio(policy_protected=False)
    evidence = _evidence(portfolio)

    decision = evaluate_genc5_sequential_compounding_shadow(
        portfolio=portfolio,
        evidence=evidence,
        source_lot_id=source,
        decision_id="decision-defensive",
    )

    assert decision.treatment_posture is SequentialCompoundPosture.DEFENSIVE
    assert (
        decision.treatment_action
        is SequentialCompoundShadowAction.HOLD_CURRENT_STATE
    )
    assert decision.treatment_requested_risk_review_usd == Decimal("0")
    assert decision.blocker_codes == (
        "POLICY_PROTECTED_FLOOR_ABSENT",
    )
    assert decision.treatment_differs_from_control is False


def test_genc5_requires_exact_gen_c4_portfolio_capacity_binding() -> None:
    portfolio, source = _portfolio(policy_protected=True)
    evidence = _evidence(portfolio, capacity="61")

    with pytest.raises(
        CiboCompoundCapitalError,
        match="capacity binding drift",
    ):
        evaluate_genc5_sequential_compounding_shadow(
            portfolio=portfolio,
            evidence=evidence,
            source_lot_id=source,
            decision_id="decision-capacity-drift",
        )


def test_genc5_rejects_pre_freeze_evidence() -> None:
    portfolio, source = _portfolio(policy_protected=True)
    evidence = _evidence(
        portfolio,
        decision_at=GENC5_SHADOW_POLICY_FROZEN_AT
        - timedelta(microseconds=1),
    )

    with pytest.raises(
        CiboCompoundCapitalError,
        match="pre-freeze",
    ):
        evaluate_genc5_sequential_compounding_shadow(
            portfolio=portfolio,
            evidence=evidence,
            source_lot_id=source,
            decision_id="decision-pre-freeze",
        )


def test_genc5_rejects_outcome_aware_gen_c4_contract() -> None:
    portfolio, source = _portfolio(policy_protected=True)
    base = _evidence(portfolio)

    with pytest.raises(
        CiboCompoundCapitalError,
        match="cannot contain outcomes",
    ):
        replace(base, outcome_present=True)

    decision = evaluate_genc5_sequential_compounding_shadow(
        portfolio=portfolio,
        evidence=base,
        source_lot_id=source,
        decision_id="decision-clean",
    )
    assert decision.outcome_present_at_seal is False


def test_genc5_store_hash_chain_cas_restart_idempotency_and_conflict(
    tmp_path: Path,
) -> None:
    portfolio, source = _portfolio(policy_protected=True)
    evidence = _evidence(portfolio)
    decision = evaluate_genc5_sequential_compounding_shadow(
        portfolio=portfolio,
        evidence=evidence,
        source_lot_id=source,
        decision_id="durable-decision",
    )

    path = tmp_path / "genc5-shadow.json"
    store = DurableGenc5SequentialCompoundingShadowStore(path)
    sealed_at = T0 + timedelta(seconds=1)

    first = store.seal(
        decision,
        sealed_at=sealed_at,
        expected_generation=0,
    )
    assert first.generation == 1
    assert first.chain_sha256.startswith("sha256:")
    assert store.load() == first

    idempotent = store.seal(
        decision,
        sealed_at=sealed_at,
        expected_generation=1,
    )
    assert idempotent == first

    with pytest.raises(
        CiboCompoundCapitalError,
        match="generation conflict",
    ):
        store.seal(
            decision,
            sealed_at=sealed_at,
            expected_generation=0,
        )

    changed_evidence = _evidence(portfolio, requested="6")
    conflicting = evaluate_genc5_sequential_compounding_shadow(
        portfolio=portfolio,
        evidence=changed_evidence,
        source_lot_id=source,
        decision_id="durable-decision",
    )
    with pytest.raises(
        CiboCompoundCapitalError,
        match="conflicting shadow decision rewrite",
    ):
        store.seal(
            conflicting,
            sealed_at=sealed_at,
            expected_generation=1,
        )
