import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_policy_store import (
    Phase20ForwardPolicyDecisionSeal,
    VersionedPhase20ForwardPolicyBook,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    Phase20ForwardDecisionSeal,
    Phase20ForwardOutcomeSeal,
    VersionedPhase20ForwardEvidenceBook,
)
from qore.infrastructure.cibo_compound_capital import (
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
from qore.infrastructure.cibo_marginal_capital_utility_evidence_store import (
    DurableGenc4MarginalEvidenceStore,
)
from qore.infrastructure.cibo_sequential_compounding_oos_binding import (
    Genc5OutcomeBindingStatus,
    bind_genc5_shadow_to_phase20_outcomes,
)
from qore.infrastructure.cibo_sequential_compounding_shadow_policy import (
    GENC5_SHADOW_POLICY_FROZEN_AT,
    evaluate_genc5_sequential_compounding_shadow,
)
from qore.infrastructure.cibo_sequential_compounding_shadow_store import (
    DurableGenc5SequentialCompoundingShadowStore,
)
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
)

T0 = GENC5_SHADOW_POLICY_FROZEN_AT + timedelta(minutes=5)
SOURCE_DECISION_SHA = "sha256:" + "7" * 64
SOURCE_POLICY_SHA = "sha256:" + "8" * 64
SIGNAL = "genc5-oos-signal"


def _identity() -> CiboAccountCapitalIdentity:
    return CiboAccountCapitalIdentity(
        provider_key="ctrader",
        account_ref="genc5-oos-demo",
        environment=MarketRuntimeEnvironment.DEMO,
    )


def _portfolio() -> tuple[AccountCoreCompoundPortfolio, str]:
    identity = _identity()
    realized = create_realized_profit_lot(
        CompoundRealizedProfitEvidence(
            evidence_id="oos-settlement",
            account_identity=identity,
            origin_trader=TraderLineage.VT31_NAS100,
            signal_fingerprint="origin-signal",
            position_id=1001,
            settlement_deal_ids=(2001,),
            realized_net_profit_usd=Decimal("100"),
            realized_at=T0 - timedelta(minutes=2),
            source_settlement_sha256="sha256:" + "a" * 64,
            settlement_reconciled=True,
            position_closed=True,
        ),
        lot_id="oos-realized-100",
        created_at=T0 - timedelta(minutes=1, seconds=59),
    )
    ledger = CompoundPortfolioLedger(
        account_identity=identity
    ).admit_realized_profit(
        realized,
        event_id="oos-admit",
        occurred_at=T0 - timedelta(minutes=1, seconds=58),
    )
    ledger = ledger.transition(
        source_lot_id=realized.lot_id,
        to_state=CompoundCapitalState.RETIRED_TO_PROTECTED_FLOOR,
        amount_usd=Decimal("40"),
        moved_lot_id="oos-floor-40",
        remainder_lot_id="oos-realized-60",
        event_id="oos-protect",
        occurred_at=T0 - timedelta(minutes=1, seconds=57),
    )
    ledger = ledger.transition(
        source_lot_id="oos-realized-60",
        to_state=CompoundCapitalState.COMPOUNDABLE,
        amount_usd=Decimal("60"),
        moved_lot_id="oos-compoundable-60",
        event_id="oos-compoundable",
        occurred_at=T0 - timedelta(minutes=1, seconds=56),
    )
    floor = ProtectedCapitalFloorLedger(
        account_identity=identity
    ).admit_retired_lot(
        ledger.lot("oos-floor-40"),
        tranche_id="oos-floor-tranche",
        event_id="oos-floor-admit",
        admitted_at=T0 - timedelta(minutes=1, seconds=55),
    )
    floor = floor.upgrade_to_policy_protected(
        tranche_id="oos-floor-tranche",
        event_id="oos-floor-policy",
        occurred_at=T0 - timedelta(minutes=1, seconds=54),
        policy_id="GEN-C2-OOS-POLICY",
        policy_sha256="sha256:" + "b" * 64,
    )
    return (
        AccountCoreCompoundPortfolio(
            account_identity=identity,
            compound_ledger=ledger,
            protected_floor_ledger=floor,
        ),
        "oos-compoundable-60",
    )


def _marginal(
    portfolio: AccountCoreCompoundPortfolio,
) -> MarginalCapitalUtilityEvidence:
    return MarginalCapitalUtilityEvidence(
        evidence_id="genc4-oos-evidence",
        decision_at=T0,
        account_identity=portfolio.account_identity,
        trader_id=TraderLineage.VT31_NAS100,
        signal_fingerprint=SIGNAL,
        source_opportunity_decision_sha256=SOURCE_DECISION_SHA,
        source_baseline_policy_record_sha256=SOURCE_POLICY_SHA,
        current_compound_capacity_usd=Decimal("60"),
        requested_incremental_capital_usd=Decimal("5"),
        expected_incremental_return_usd=Decimal("1.5"),
        incremental_stop_risk_usd=Decimal("1"),
        incremental_margin_usd=Decimal("4"),
        incremental_execution_cost_usd=Decimal("0.1"),
        incremental_concentration_risk_usd=Decimal("0.5"),
        incremental_drawdown_risk_proxy_usd=Decimal("0.4"),
        incremental_optionality_consumed_usd=Decimal("1"),
        expected_capital_minutes=Decimal("45"),
        epistemic_uncertainty=Decimal("0.2"),
        provider_evidence_sha256="sha256:" + "1" * 64,
        expectation_evidence_sha256="sha256:" + "2" * 64,
        factor_evidence_sha256="sha256:" + "3" * 64,
        duration_evidence_sha256="sha256:" + "4" * 64,
        execution_evidence_sha256="sha256:" + "5" * 64,
        optionality_evidence_sha256="sha256:" + "6" * 64,
    )


def _books(
    tmp_path: Path,
    *,
    include_outcome: bool = True,
) -> tuple[
    object,
    object,
    VersionedPhase20ForwardEvidenceBook,
    VersionedPhase20ForwardPolicyBook,
]:
    portfolio, source_lot_id = _portfolio()
    marginal = _marginal(portfolio)

    c4_store = DurableGenc4MarginalEvidenceStore(
        tmp_path / "genc4.json"
    )
    c4_book = c4_store.seal(
        marginal,
        sealed_at=T0 + timedelta(seconds=1),
        expected_generation=0,
    )

    c5_decision = evaluate_genc5_sequential_compounding_shadow(
        portfolio=portfolio,
        evidence=marginal,
        source_lot_id=source_lot_id,
        decision_id="genc5-oos-decision",
    )
    c5_store = DurableGenc5SequentialCompoundingShadowStore(
        tmp_path / "genc5.json"
    )
    c5_book = c5_store.seal(
        c5_decision,
        sealed_at=T0 + timedelta(seconds=1),
        expected_generation=0,
    )

    phase20_decision = Phase20ForwardDecisionSeal(
        evidence_id="phase20-source",
        decision_epoch_id="phase20-epoch",
        evidence_sha256=SOURCE_DECISION_SHA,
        decision_at=T0,
        candidate_id="CIBO_PHASE20_FULL_SURFACE_FORWARD_CANDIDATE_V3",
        code_sha="c" * 40,
        parameter_sha256="sha256:" + "d" * 64,
        signal_fingerprints=(SIGNAL,),
        canonical_payload_json=json.dumps(
            {
                "account_identity": {
                    "provider_key": "ctrader",
                    "account_ref": "genc5-oos-demo",
                },
                "evidence_kind": "FORWARD_OBSERVED",
            },
            sort_keys=True,
        ),
    )
    outcomes = ()
    if include_outcome:
        outcomes = (
            Phase20ForwardOutcomeSeal(
                evidence_id="phase20-terminal-outcome",
                decision_evidence_sha256=SOURCE_DECISION_SHA,
                signal_fingerprint=SIGNAL,
                position_id=3001,
                execution_risk_evidence_id="executed-risk-1",
                settlement_deal_ids=(4001,),
                fill_evidence_refs=("fill-1",),
                observed_at=T0 + timedelta(minutes=30),
                realized_net_pnl_usd=Decimal("2"),
                executed_initial_stop_risk_usd=Decimal("1"),
                realized_structural_outcome_r=Decimal("2"),
            ),
        )
    phase20_book = VersionedPhase20ForwardEvidenceBook(
        generation=1,
        decisions=(phase20_decision,),
        outcomes=outcomes,
    )
    phase20_policy = Phase20ForwardPolicyDecisionSeal(
        evidence_sha256=SOURCE_DECISION_SHA,
        policy_record_sha256=SOURCE_POLICY_SHA,
        allocator_disposition="ALLOW",
        selected_signal_fingerprints=(SIGNAL,),
        canonical_record_json="{}",
    )
    policy_book = VersionedPhase20ForwardPolicyBook(
        generation=1,
        decisions=(phase20_policy,),
    )
    return c4_book, c5_book, phase20_book, policy_book


def test_genc5_oos_binding_is_complete_without_counterfactual_pnl(
    tmp_path: Path,
) -> None:
    c4, c5, phase20, policy = _books(tmp_path)

    report = bind_genc5_shadow_to_phase20_outcomes(
        c4_book=c4,
        c5_book=c5,
        phase20_evidence_book=phase20,
        phase20_policy_book=policy,
    )

    assert report.status is Genc5OutcomeBindingStatus.COMPLETE
    assert report.shadow_decision_count == 1
    assert report.treatment_divergent_count == 1
    assert report.terminal_outcome_bound_count == 1
    assert report.treatment_divergent_outcome_count == 1
    assert report.failures == ()
    assert report.missing_outcome_decision_ids == ()
    assert report.counterfactual_compound_pnl_computed is False
    assert report.economic_utility_ready is False
    assert report.certification_ready is False

    row = report.rows[0]
    assert row.realized_structural_outcome_r == Decimal("2")
    assert row.proposed_incremental_stop_risk_usd == Decimal("1")
    assert row.treatment_requested_risk_review_usd == Decimal("5")
    assert row.counterfactual_compound_pnl_computed is False
    assert row.economic_utility_claimed is False


def test_genc5_oos_binding_reports_missing_terminal_outcome_as_partial(
    tmp_path: Path,
) -> None:
    c4, c5, phase20, policy = _books(
        tmp_path,
        include_outcome=False,
    )

    report = bind_genc5_shadow_to_phase20_outcomes(
        c4_book=c4,
        c5_book=c5,
        phase20_evidence_book=phase20,
        phase20_policy_book=policy,
    )

    assert report.status is Genc5OutcomeBindingStatus.PARTIAL
    assert report.terminal_outcome_bound_count == 0
    assert report.missing_outcome_decision_ids == (
        "genc5-oos-decision",
    )
    assert report.failures == ()


def test_genc5_oos_binding_fails_closed_on_source_policy_drift(
    tmp_path: Path,
) -> None:
    c4, c5, phase20, policy = _books(tmp_path)
    original = policy.decisions[0]
    bad_policy = VersionedPhase20ForwardPolicyBook(
        generation=1,
        decisions=(
            replace(
                original,
                policy_record_sha256="sha256:" + "9" * 64,
            ),
        ),
    )

    report = bind_genc5_shadow_to_phase20_outcomes(
        c4_book=c4,
        c5_book=c5,
        phase20_evidence_book=phase20,
        phase20_policy_book=bad_policy,
    )

    assert report.status is Genc5OutcomeBindingStatus.INVALID
    assert report.terminal_outcome_bound_count == 0
    assert report.failures == (
        "SOURCE_POLICY_BINDING_DRIFT:genc5-oos-decision",
    )


def test_genc5_oos_binding_rejects_temporally_impossible_outcome(
    tmp_path: Path,
) -> None:
    c4, c5, phase20, policy = _books(tmp_path)
    early = replace(
        phase20.outcomes[0],
        observed_at=T0,
    )
    contaminated = VersionedPhase20ForwardEvidenceBook(
        generation=1,
        decisions=phase20.decisions,
        outcomes=(early,),
    )

    report = bind_genc5_shadow_to_phase20_outcomes(
        c4_book=c4,
        c5_book=c5,
        phase20_evidence_book=contaminated,
        phase20_policy_book=policy,
    )

    assert report.status is Genc5OutcomeBindingStatus.INVALID
    assert report.failures == (
        "OUTCOME_TEMPORAL_CONTAMINATION:genc5-oos-decision",
    )
