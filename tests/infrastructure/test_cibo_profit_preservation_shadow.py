from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
)
from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError
from qore.infrastructure.cibo_profit_preservation_oos_binding import (
    Genc7OosBindingStatus,
    Genc7OutcomeEvidence,
    bind_genc7_to_observed_paths,
)
from qore.infrastructure.cibo_profit_preservation_population import (
    Genc7PopulationStatus,
    describe_genc7_fresh_population,
)
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
        evaluation_horizon_minutes=60,
        calibrated=calibrated,
        capital_eligible=capital_eligible,
    )


def test_genc7_policy_digest_is_frozen() -> None:
    assert genc7_policy_sha256() == (
        "sha256:fc6a9b32da8d6595cffb51a73525a929d976f84960439b8e0c22f90561a406e7"
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


def test_genc7_rejects_any_treatment_resize_or_action_drift() -> None:
    decision = evaluate_genc7_profit_preservation_shadow(
        state=_state(),
        proposal=_proposal(amount="10"),
        decision_id="genc7-exact-proposal",
    )

    with pytest.raises(
        CiboCompoundCapitalError,
        match="must equal exact proposal",
    ):
        replace(
            decision,
            treatment_amount_usd=Decimal("9"),
        )

    with pytest.raises(
        CiboCompoundCapitalError,
        match="must equal exact proposal",
    ):
        replace(
            decision,
            treatment_action=Genc7Action.HARVEST_TO_STRATEGIC_RESERVE,
        )


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
        base_drawdown_usd=Decimal("3"),
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


def test_genc7_population_is_descriptive_not_economic(tmp_path) -> None:
    decision = evaluate_genc7_profit_preservation_shadow(
        state=_state(),
        proposal=_proposal(),
        decision_id="genc7-population-decision",
    )
    store = DurableGenc7ProfitPreservationShadowStore(
        tmp_path / "genc7-population.json"
    )
    book = store.seal(
        decision,
        sealed_at=T0 + timedelta(seconds=1),
        expected_generation=0,
    )

    population = describe_genc7_fresh_population(book=book)

    assert population.status is Genc7PopulationStatus.DESCRIPTIVE_AVAILABLE
    assert population.decision_epoch_count == 1
    assert population.treatment_control_divergence_count == 1
    assert population.protect_count == 1
    assert population.hold_count == 0
    assert population.account_keys == ("ctrader:genc7-test",)
    assert population.decision_calendar_days == 1
    assert population.calendar_span_days == 1
    assert population.minimum_evaluation_horizon_minutes == 60
    assert population.maximum_evaluation_horizon_minutes == 60
    assert population.mean_giveback_amount_usd == Decimal("8")
    assert population.mean_profit_retention_ratio == Decimal("0.8")
    assert population.mean_base_drawdown_usd == Decimal("2")
    assert population.mean_compound_drawdown_usd == Decimal("6")
    assert population.mean_floor_growth_rate == Decimal("0.2")
    assert population.descriptive_only is True
    assert population.economic_utility_ready is False
    assert population.certification_ready is False
    assert "CAUSAL_EFFECT_IDENTIFICATION_NOT_EVALUATED" in population.blockers
    assert "OUTCOME_BINDING_NOT_EVALUATED" in population.blockers


def test_genc7_empty_population_fails_closed_descriptively() -> None:
    from qore.infrastructure.cibo_profit_preservation_store import (
        VersionedGenc7ShadowBook,
    )

    population = describe_genc7_fresh_population(
        book=VersionedGenc7ShadowBook(generation=0)
    )

    assert population.status is Genc7PopulationStatus.EMPTY
    assert population.decision_epoch_count == 0
    assert population.economic_utility_ready is False
    assert population.certification_ready is False
    assert population.blockers == ("NO_GENC7_DECISIONS",)


def _oos_book(tmp_path):
    decision = evaluate_genc7_profit_preservation_shadow(
        state=_state(),
        proposal=_proposal(),
        decision_id="genc7-oos-decision",
    )
    store = DurableGenc7ProfitPreservationShadowStore(
        tmp_path / "genc7-oos.json"
    )
    return store.seal(
        decision,
        sealed_at=T0 + timedelta(seconds=1),
        expected_generation=0,
    )


def _outcome_for_book(book, **changes):
    seal = book.seal_for_decision("genc7-oos-decision")
    assert seal is not None
    values = dict(
        outcome_id="genc7-outcome-001",
        decision_sha256=seal.decision_sha256,
        account_provider_key=seal.account_provider_key,
        account_ref=seal.account_ref,
        window_end_at=T0 + timedelta(minutes=60),
        observed_at=T0 + timedelta(minutes=61),
        ending_realized_capital_usd=Decimal("95"),
        ending_realized_profit_usd=Decimal("34"),
        ending_protected_floor_usd=Decimal("20"),
        ending_base_capital_usd=Decimal("59"),
        ending_compound_capital_usd=Decimal("25"),
        source_settlement_sha256="sha256:" + "c" * 64,
        source_t20_release_sha256="sha256:" + "d" * 64,
        path_evidence_sha256="sha256:" + "e" * 64,
        path_complete=True,
        settlement_coverage_complete=True,
        release_coverage_complete=True,
    )
    values.update(changes)
    return Genc7OutcomeEvidence(**values)


def test_genc7_oos_binds_exact_preregistered_horizon_without_claiming_effect(
    tmp_path,
) -> None:
    book = _oos_book(tmp_path)
    outcome = _outcome_for_book(book)

    report = bind_genc7_to_observed_paths(
        book=book,
        outcomes=(outcome,),
    )

    assert report.status is Genc7OosBindingStatus.COMPLETE
    assert report.decision_count == 1
    assert report.bound_count == 1
    assert report.failures == ()
    assert report.missing_decision_ids == ()
    row = report.rows[0]
    assert row.realized_capital_delta_usd == Decimal("3")
    assert row.realized_profit_delta_usd == Decimal("2")
    assert row.protected_floor_delta_usd == Decimal("2")
    assert row.base_capital_delta_usd == Decimal("1")
    assert row.compound_capital_delta_usd == Decimal("1")
    assert row.treatment_effect_identified is False
    assert row.counterfactual_treatment_pnl_computed is False
    assert row.economic_utility_claimed is False
    assert report.economic_utility_ready is False
    assert report.certification_ready is False


def test_genc7_oos_missing_outcome_stays_partial(tmp_path) -> None:
    book = _oos_book(tmp_path)

    report = bind_genc7_to_observed_paths(book=book, outcomes=())

    assert report.status is Genc7OosBindingStatus.PARTIAL
    assert report.bound_count == 0
    assert report.missing_decision_ids == ("genc7-oos-decision",)
    assert report.economic_utility_ready is False


def test_genc7_oos_wrong_horizon_is_invalid(tmp_path) -> None:
    book = _oos_book(tmp_path)
    outcome = _outcome_for_book(
        book,
        window_end_at=T0 + timedelta(minutes=59),
    )

    report = bind_genc7_to_observed_paths(
        book=book,
        outcomes=(outcome,),
    )

    assert report.status is Genc7OosBindingStatus.INVALID
    assert report.bound_count == 0
    assert report.failures == (
        "OUTCOME_HORIZON_BINDING_DRIFT:genc7-oos-decision",
    )


def test_genc7_oos_incomplete_release_coverage_is_invalid(tmp_path) -> None:
    book = _oos_book(tmp_path)
    outcome = _outcome_for_book(
        book,
        release_coverage_complete=False,
    )

    report = bind_genc7_to_observed_paths(
        book=book,
        outcomes=(outcome,),
    )

    assert report.status is Genc7OosBindingStatus.INVALID
    assert report.release_complete_count == 0
    assert report.failures == (
        "OUTCOME_COVERAGE_INCOMPLETE:genc7-oos-decision",
    )


def test_genc7_oos_refuses_counterfactual_effect_claim(tmp_path) -> None:
    book = _oos_book(tmp_path)

    with pytest.raises(
        CiboCompoundCapitalError,
        match="cannot invent treatment effect",
    ):
        _outcome_for_book(
            book,
            treatment_effect_identified=True,
        )


def test_genc7_bound_path_rejects_manual_horizon_or_observation_drift(
    tmp_path,
) -> None:
    book = _oos_book(tmp_path)
    report = bind_genc7_to_observed_paths(
        book=book,
        outcomes=(_outcome_for_book(book),),
    )
    row = report.rows[0]

    with pytest.raises(
        CiboCompoundCapitalError,
        match="bound path horizon binding drift",
    ):
        replace(
            row,
            window_end_at=row.window_end_at + timedelta(minutes=1),
        )

    with pytest.raises(
        CiboCompoundCapitalError,
        match="bound observation cannot predate horizon",
    ):
        replace(
            row,
            observed_at=row.window_end_at - timedelta(seconds=1),
        )
