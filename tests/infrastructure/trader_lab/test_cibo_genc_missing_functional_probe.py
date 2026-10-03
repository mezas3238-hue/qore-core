# ruff: noqa: E501,I001
from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_a1_genc2_phase22_profit_graduation import (
    Genc2EconomicRole,
    Genc2EconomicStatus,
    Genc2ProfitGraduationFoldObservation,
    evaluate_genc2_phase22_profit_graduation,
)
from qore.infrastructure.cibo_a1_phase22_historical_compound_dependency import (
    CONTRACT_ID,
    A1HistoricalCompoundLineageReceipt,
    admit_historical_compound_lineage_for_a1,
)
from qore.infrastructure.cibo_a1_phase22_scientific_consumption import (
    MANIFEST_ID,
    A1Phase22PopulationFold,
    A1Phase22ScientificConsumptionManifest,
)
from qore.infrastructure.cibo_account_capital_mission import CiboAccountCapitalIdentity
from qore.infrastructure.cibo_adaptive_compound_speed_economic_gate import (
    Genc8EconomicGateStatus,
    Genc8EconomicObservation,
    Genc8EconomicRole,
    evaluate_genc8_economic_gate,
)
from qore.infrastructure.cibo_adaptive_compound_speed_shadow import genc8_policy_sha256
from qore.infrastructure.cibo_capital_digital_twin import (
    Genc10CapitalFlow,
    Genc10EconomicBucket,
    Genc10FlowKind,
    Genc10KnownCapitalOption,
    Genc10ObservedCapitalTwin,
    Genc10WorldKind,
    Genc10WorldScenario,
    project_genc10_world,
)
from qore.infrastructure.cibo_ce2i_regime_selector import (
    CiboCapitalRegimeState,
    CiboRegimePosture,
    CorrelationState,
    LiquidityState,
    ProviderCondition,
    VolatilityState,
)
from qore.infrastructure.cibo_compound_capital import (
    CompoundCapitalState,
    CompoundRealizedProfitEvidence,
    create_realized_profit_lot,
)
from qore.infrastructure.cibo_compound_floor import ProtectedCapitalFloorLedger
from qore.infrastructure.cibo_compound_portfolio_ledger import CompoundPortfolioLedger
from qore.infrastructure.cibo_core_compound_portfolio import AccountCoreCompoundPortfolio
from qore.infrastructure.cibo_crisis_capital_intelligence import (
    Genc12CapitalResponse,
    Genc12CrisisFact,
    Genc12CrisisFactor,
    plan_genc12_crisis_capital,
)
from qore.infrastructure.cibo_executive_memory import CiboMemoryKind, CiboMemoryStore
from qore.infrastructure.cibo_governed_capital_science import (
    Genc14CapitalHypothesis,
    Genc14EvidenceKind,
    Genc14ScienceEvidence,
    Genc14ScienceStage,
    advance_genc14_science,
    start_genc14_science,
)
from qore.infrastructure.cibo_marginal_capital_utility_evidence import (
    MarginalCapitalUtilityEvidence,
    SharedCapitalFactKind,
    SharedCapitalIntelligenceFact,
    SharedToCiboCapitalIntelligenceSnapshot,
)
from qore.infrastructure.cibo_meta_capital_memory import (
    Genc13CapitalEpisode,
    Genc13CapitalPhenotype,
    Genc13CounterfactualKind,
    Genc13CounterfactualStudy,
    Genc13PhenotypeEvidence,
    Genc13SkepticReport,
    build_genc13_memory_item,
)
from qore.infrastructure.cibo_multi_period_capital_mpc import (
    Genc11KnownOptionSchedule,
    Genc11WorldPath,
    Genc11WorldStep,
    plan_genc11_multi_period_capital,
)
from qore.infrastructure.cibo_sequential_compounding_shadow_policy import (
    SequentialCompoundPosture,
    SequentialCompoundShadowAction,
    evaluate_genc5_sequential_compounding_shadow,
)
from qore.infrastructure.market_test_environment import MarketRuntimeEnvironment
from qore.infrastructure.trader_lab.candidate import TraderLabCandidateBinding
from qore.kernel.result import Success

NOW = datetime(2026, 10, 3, 4, 0, tzinfo=UTC)
FOLDS = ("WF1", "WF2", "WF3", "WF4")


def _tag(candidate: TraderLabCandidateBinding, suffix: str) -> str:
    return f"trader-lab:{candidate.fingerprint.value}:{suffix}"


def _sha(candidate: TraderLabCandidateBinding, label: str) -> str:
    raw = f"{candidate.fingerprint.value}:{label}".encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _identity(candidate: TraderLabCandidateBinding, suffix: str) -> CiboAccountCapitalIdentity:
    return CiboAccountCapitalIdentity(
        provider_key="trader-lab",
        account_ref=_tag(candidate, suffix),
        environment=MarketRuntimeEnvironment.TEST,
    )


# GEN-C2 ---------------------------------------------------------------------

def _genc2_manifest(candidate: TraderLabCandidateBinding) -> A1Phase22ScientificConsumptionManifest:
    base = datetime(2015, 10, 20, tzinfo=UTC)
    folds = tuple(
        A1Phase22PopulationFold(
            fold_id=fold_id,
            decision_count=20,
            first_decision_at=base + timedelta(days=index * 20),
            last_decision_at=base + timedelta(days=(index + 1) * 20 - 1),
            population_sha256=_sha(candidate, f"genc2-population-{fold_id}"),
        )
        for index, fold_id in enumerate(FOLDS)
    )
    return A1Phase22ScientificConsumptionManifest(
        manifest_id=MANIFEST_ID,
        candidate_id="CIBO_USD60_6M_HOLDOUT_2015-10-19_2016-04-19_V2",
        code_sha=candidate.fingerprint.value[:40],
        parameter_sha256=_sha(candidate, "genc2-params"),
        amendment_sha256=_sha(candidate, "genc2-amendment"),
        source_population_sha256=_sha(candidate, "genc2-source"),
        policy_population_sha256=_sha(candidate, "genc2-policy"),
        decision_count=80,
        policy_count=80,
        outcome_count=160,
        trader_ids=("R38_EURUSD", "VT31_NAS100"),
        folds=folds,
        exact_policy_coverage=True,
        historical_replay_only=True,
        folds_defined_without_outcomes=True,
    )


def _genc2_dependency(candidate: TraderLabCandidateBinding):
    manifest = _genc2_manifest(candidate)
    receipt = A1HistoricalCompoundLineageReceipt(
        contract_id=CONTRACT_ID,
        source_workstream="COMPOUND_ENGINE",
        source_head=candidate.fingerprint.value[:40],
        artifact_sha256=_sha(candidate, "genc2-compound"),
        source_population_sha256=manifest.source_population_sha256,
        a1_manifest_sha256=manifest.fingerprint(),
        adapter_identity="TRADER_LAB_GENC2_COMPOUND_LINEAGE_V1",
        historical_replay_supported=True,
        historical_broker_ids_required=False,
        historical_broker_ids_emitted=False,
        current_demo_ids_relabelled_as_historical=False,
        fabricated_execution_ids_used=False,
        realized_profit_only=True,
        floating_pnl_used_as_capital=False,
        capital_conservation_proven=True,
        double_spend_detected=False,
        decision_before_outcome_preserved=True,
        deterministic_replay=True,
    )
    return admit_historical_compound_lineage_for_a1(manifest=manifest, receipt=receipt)


def test_trader_lab_genc2_profit_graduation_executes(candidate_factory) -> None:
    candidate = candidate_factory(candidate_suffix=982)
    manifest = _genc2_manifest(candidate)
    dependency = _genc2_dependency(candidate)
    rows = []
    for fold in manifest.folds:
        common = dict(
            fold_id=fold.fold_id,
            population_sha256=fold.population_sha256,
            compound_dependency_receipt_sha256=dependency.receipt_sha256,
            provider_surface_sha256=_sha(candidate, "genc2-provider"),
            protocol_binding_sha256=_sha(candidate, "genc2-protocol"),
            realized_net_delta_usd=Decimal("10"),
            ending_realized_capital_usd=Decimal("70"),
            minimum_base_capital_usd=Decimal("60"),
            p99_drawdown_usd=Decimal("5"),
            peak_plausible_loss_usd=Decimal("5"),
            provider_cost_usd=Decimal("1"),
            provider_failure_count=0,
            minimum_liquid_reserve_usd=Decimal("10"),
            minimum_optionality_usd=Decimal("10"),
            capital_risk_time_productivity=Decimal("1"),
            source_realized_profit_usd=Decimal("10"),
            capital_conservation_breach_count=0,
            causal_effect_identified=True,
            treatment_preregistered_before_outcomes=True,
        )
        rows.append(Genc2ProfitGraduationFoldObservation(
            candidate_id=_tag(candidate, "genc2-control"),
            role=Genc2EconomicRole.CONTROL,
            ending_protected_floor_usd=Decimal("5"),
            maximum_drawdown_usd=Decimal("5"),
            graduated_realized_profit_usd=Decimal("0"),
            **common,
        ))
        rows.append(Genc2ProfitGraduationFoldObservation(
            candidate_id=_tag(candidate, "genc2-treatment"),
            role=Genc2EconomicRole.TREATMENT,
            ending_protected_floor_usd=Decimal("6"),
            maximum_drawdown_usd=Decimal("5"),
            graduated_realized_profit_usd=Decimal("2"),
            **common,
        ))
    report = evaluate_genc2_phase22_profit_graduation(
        manifest=manifest,
        compound_dependency=dependency,
        observations=tuple(rows),
    )
    treatment = next(row for row in report.verdicts if row.candidate_id.endswith("genc2-treatment"))
    assert treatment.status is Genc2EconomicStatus.ELIGIBLE_FOR_FURTHER_RESEARCH
    assert treatment.passed_fold_ids == FOLDS
    assert report.certification_ready is False


# GEN-C4 / GEN-C5 -----------------------------------------------------------

def _genc4_evidence(
    candidate: TraderLabCandidateBinding,
    *,
    identity: CiboAccountCapitalIdentity,
    capacity: Decimal = Decimal("60"),
) -> MarginalCapitalUtilityEvidence:
    fact = SharedCapitalIntelligenceFact(
        fact_id=_tag(candidate, "shared-hazard"),
        kind=SharedCapitalFactKind.FAILURE_HAZARD,
        normalized_value=Decimal("0.20"),
        value_semantics="trader-lab calibrated hazard",
        observed_at=NOW - timedelta(seconds=2),
        valid_until=NOW + timedelta(minutes=1),
        producer_identity="TRADER_LAB_SHARED_RESEARCH",
        producer_git_sha=candidate.fingerprint.value[:40],
        evidence_sha256=_sha(candidate, "shared-fact"),
        calibration_artifact_sha256=_sha(candidate, "shared-calibration"),
        calibrated=True,
        fresh_oos_validated=True,
        temporal_stability_validated=True,
        economic_utility_validated=True,
        eligible_for_capital_use=True,
    )
    snapshot = SharedToCiboCapitalIntelligenceSnapshot(
        snapshot_id=_tag(candidate, "shared-snapshot"),
        decision_at=NOW,
        facts=(fact,),
        snapshot_sha256=_sha(candidate, "shared-snapshot"),
    )
    return MarginalCapitalUtilityEvidence(
        evidence_id=_tag(candidate, "genc4"),
        decision_at=NOW,
        account_identity=identity,
        trader_id=TraderLineage.VT31_NAS100,
        signal_fingerprint=_tag(candidate, "genc4-signal"),
        source_opportunity_decision_sha256=_sha(candidate, "genc4-opportunity"),
        source_baseline_policy_record_sha256=_sha(candidate, "genc4-baseline"),
        current_compound_capacity_usd=capacity,
        requested_incremental_capital_usd=Decimal("5"),
        expected_incremental_return_usd=Decimal("1.2"),
        incremental_stop_risk_usd=Decimal("0.8"),
        incremental_margin_usd=Decimal("4"),
        incremental_execution_cost_usd=Decimal("0.1"),
        incremental_concentration_risk_usd=Decimal("0.5"),
        incremental_drawdown_risk_proxy_usd=Decimal("0.4"),
        incremental_optionality_consumed_usd=Decimal("1"),
        expected_capital_minutes=Decimal("45"),
        epistemic_uncertainty=Decimal("0.25"),
        provider_evidence_sha256=_sha(candidate, "genc4-provider"),
        expectation_evidence_sha256=_sha(candidate, "genc4-expectation"),
        factor_evidence_sha256=_sha(candidate, "genc4-factor"),
        duration_evidence_sha256=_sha(candidate, "genc4-duration"),
        execution_evidence_sha256=_sha(candidate, "genc4-execution"),
        optionality_evidence_sha256=_sha(candidate, "genc4-optionality"),
        shared_snapshot=snapshot,
        shared_fact_ids_used=(fact.fact_id,),
    )


def _genc5_portfolio(candidate: TraderLabCandidateBinding) -> tuple[AccountCoreCompoundPortfolio, str]:
    identity = _identity(candidate, "genc5-account")
    evidence = CompoundRealizedProfitEvidence(
        evidence_id=_tag(candidate, "genc5-settlement"),
        account_identity=identity,
        origin_trader=TraderLineage.VT31_NAS100,
        signal_fingerprint=_tag(candidate, "genc5-origin"),
        position_id=98301,
        settlement_deal_ids=(98310,),
        realized_net_profit_usd=Decimal("100"),
        realized_at=NOW - timedelta(minutes=10),
        source_settlement_sha256=_sha(candidate, "genc5-settlement"),
        settlement_reconciled=True,
        position_closed=True,
    )
    lot = create_realized_profit_lot(
        evidence,
        lot_id=_tag(candidate, "genc5-realized"),
        created_at=NOW - timedelta(minutes=9),
    )
    ledger = CompoundPortfolioLedger(account_identity=identity).admit_realized_profit(
        lot,
        event_id=_tag(candidate, "genc5-admit"),
        occurred_at=NOW - timedelta(minutes=8),
    )
    floor_id = _tag(candidate, "genc5-floor")
    remainder_id = _tag(candidate, "genc5-remainder")
    compoundable_id = _tag(candidate, "genc5-compoundable")
    ledger = ledger.transition(
        source_lot_id=lot.lot_id,
        to_state=CompoundCapitalState.RETIRED_TO_PROTECTED_FLOOR,
        amount_usd=Decimal("40"),
        moved_lot_id=floor_id,
        remainder_lot_id=remainder_id,
        event_id=_tag(candidate, "genc5-protect"),
        occurred_at=NOW - timedelta(minutes=7),
    )
    ledger = ledger.transition(
        source_lot_id=remainder_id,
        to_state=CompoundCapitalState.COMPOUNDABLE,
        amount_usd=Decimal("60"),
        moved_lot_id=compoundable_id,
        event_id=_tag(candidate, "genc5-classify"),
        occurred_at=NOW - timedelta(minutes=6),
    )
    floor = ProtectedCapitalFloorLedger(account_identity=identity).admit_retired_lot(
        ledger.lot(floor_id),
        tranche_id=_tag(candidate, "genc5-tranche"),
        event_id=_tag(candidate, "genc5-floor-admit"),
        admitted_at=NOW - timedelta(minutes=5),
    )
    floor = floor.upgrade_to_policy_protected(
        tranche_id=_tag(candidate, "genc5-tranche"),
        event_id=_tag(candidate, "genc5-floor-policy"),
        occurred_at=NOW - timedelta(minutes=4),
        policy_id="TRADER_LAB_GENC5_FLOOR",
        policy_sha256=_sha(candidate, "genc5-floor-policy"),
    )
    return AccountCoreCompoundPortfolio(
        account_identity=identity,
        compound_ledger=ledger,
        protected_floor_ledger=floor,
    ), compoundable_id


def test_trader_lab_genc4_and_genc5_execute(candidate_factory) -> None:
    candidate = candidate_factory(candidate_suffix=983)
    portfolio, source = _genc5_portfolio(candidate)
    evidence = _genc4_evidence(candidate, identity=portfolio.account_identity)
    assert evidence.shared_snapshot is not None
    assert evidence.utility_score_computed is False
    assert evidence.outcome_present is False
    assert evidence.capital_authority is False

    decision = evaluate_genc5_sequential_compounding_shadow(
        portfolio=portfolio,
        evidence=evidence,
        source_lot_id=source,
        decision_id=_tag(candidate, "genc5-decision"),
    )
    assert decision.control_posture is SequentialCompoundPosture.COMPOUND_PAUSED
    assert decision.treatment_posture is SequentialCompoundPosture.CAUTIOUS_COMPOUND
    assert decision.treatment_action is SequentialCompoundShadowAction.REQUEST_DOWNSTREAM_RISK_REVIEW
    assert decision.treatment_requested_risk_review_usd == Decimal("5")
    assert decision.blocker_codes == ()
    assert decision.runtime_authority is False
    assert decision.risk_authority is False
    assert decision.execution_authority is False


# GEN-C8 ---------------------------------------------------------------------

def _genc8_observation(
    candidate: TraderLabCandidateBinding,
    *,
    suffix: str,
    role: Genc8EconomicRole,
    ending: str,
    growth: str,
    productivity: str,
    missed: int,
) -> Genc8EconomicObservation:
    return Genc8EconomicObservation(
        candidate_id=_tag(candidate, suffix),
        role=role,
        policy_sha256=genc8_policy_sha256(),
        population_sha256=_sha(candidate, "genc8-population"),
        provider_surface_sha256=_sha(candidate, "genc8-provider"),
        fold_ids=FOLDS,
        horizon_start=NOW - timedelta(hours=2),
        horizon_end=NOW - timedelta(hours=1),
        ending_realized_capital_usd=Decimal(ending),
        geometric_growth_factor=Decimal(growth),
        maximum_drawdown_usd=Decimal("5"),
        p95_drawdown_usd=Decimal("4"),
        p99_drawdown_usd=Decimal("4.5"),
        maximum_time_underwater_minutes=Decimal("100"),
        p95_recovery_minutes=Decimal("50"),
        capital_risk_time_productivity=Decimal(productivity),
        profit_retention_usd=Decimal("20"),
        minimum_liquid_reserve_usd=Decimal("15"),
        minimum_optionality_usd=Decimal("10"),
        provider_cost_usd=Decimal("2"),
        positive_tail_capture_usd=Decimal("8"),
        unnecessary_acceleration_count=2,
        over_defensive_missed_opportunity_count=missed,
    )


def test_trader_lab_genc8_adaptive_speed_gate_executes(candidate_factory) -> None:
    candidate = candidate_factory(candidate_suffix=984)
    report = evaluate_genc8_economic_gate((
        _genc8_observation(candidate, suffix="genc8-control", role=Genc8EconomicRole.CONTROL, ending="110", growth="1.10", productivity="1.2", missed=4),
        _genc8_observation(candidate, suffix="genc8-treatment", role=Genc8EconomicRole.TREATMENT, ending="112", growth="1.12", productivity="1.3", missed=3),
    ))
    treatment = report.rows[1]
    assert treatment.status is Genc8EconomicGateStatus.ELIGIBLE_FOR_FURTHER_RESEARCH
    assert treatment.safety_no_worse is True
    assert treatment.strict_economic_improvement is True


# GEN-C10 / C11 / C12 -------------------------------------------------------

def _genc10_twin(candidate: TraderLabCandidateBinding) -> Genc10ObservedCapitalTwin:
    buckets = tuple(
        (bucket, Decimal("100") if bucket is Genc10EconomicBucket.ORIGINAL_BASE else Decimal(0))
        for bucket in Genc10EconomicBucket
    )
    option_id = _tag(candidate, "known-option")
    return Genc10ObservedCapitalTwin(
        twin_id=_tag(candidate, "genc10-twin"),
        account_identity=_identity(candidate, "genc10-account"),
        captured_at=NOW,
        capital_truth_sha256=_sha(candidate, "genc10-truth"),
        compound_cycle_sha256=_sha(candidate, "genc10-cycle"),
        source_ledger_sha256=_sha(candidate, "genc10-ledger"),
        provider_registry_sha256=_sha(candidate, "genc10-provider"),
        total_realized_capital_usd=Decimal("100"),
        original_base_usd=Decimal("100"),
        compound_economic_value_usd=Decimal("0"),
        protected_floor_usd=Decimal("0"),
        policy_protected_floor_usd=Decimal("0"),
        broker_guaranteed_floor_usd=Decimal("0"),
        economic_buckets=buckets,
        generation_balances=(),
        source_capacities=(),
        total_stop_risk_capacity_usd=Decimal("10"),
        used_stop_risk_usd=Decimal("0"),
        stop_risk_headroom_usd=Decimal("10"),
        total_margin_capacity_usd=Decimal("100"),
        used_margin_usd=Decimal("0"),
        margin_headroom_usd=Decimal("100"),
        active_deployment_count=0,
        provider_capability_counts=(),
        known_options=(
            Genc10KnownCapitalOption(
                option_id=option_id,
                known_at=NOW,
                earliest_action_at=NOW + timedelta(minutes=5),
                expires_at=NOW + timedelta(minutes=40),
                requested_capital_usd=Decimal("5"),
                stop_risk_usd=Decimal("1"),
                margin_usd=Decimal("2"),
                evidence_sha256=_sha(candidate, "genc10-option"),
            ),
        ),
    )


def _genc10_scenario(
    candidate: TraderLabCandidateBinding,
    *,
    suffix: str,
    kind: Genc10WorldKind,
    risk_delta: str = "0",
    margin_delta: str = "0",
) -> Genc10WorldScenario:
    return Genc10WorldScenario(
        scenario_id=_tag(candidate, suffix),
        kind=kind,
        declared_at=NOW,
        scenario_evidence_sha256=_sha(candidate, f"{suffix}-scenario"),
        transition_uncertainty_evidence_sha256=_sha(candidate, f"{suffix}-uncertainty"),
        stop_risk_capacity_delta_usd=Decimal(risk_delta),
        margin_capacity_delta_usd=Decimal(margin_delta),
        surviving_known_option_ids=(_tag(candidate, "known-option"),),
    )


def test_trader_lab_genc10_digital_twin_executes(candidate_factory) -> None:
    candidate = candidate_factory(candidate_suffix=985)
    twin = _genc10_twin(candidate)
    scenario = Genc10WorldScenario(
        scenario_id=_tag(candidate, "genc10-world"),
        kind=Genc10WorldKind.BALANCED,
        declared_at=NOW,
        scenario_evidence_sha256=_sha(candidate, "genc10-world"),
        transition_uncertainty_evidence_sha256=_sha(candidate, "genc10-transition"),
        flows=(
            Genc10CapitalFlow(
                flow_id=_tag(candidate, "genc10-gain"),
                kind=Genc10FlowKind.SETTLED_GAIN,
                amount_usd=Decimal("4"),
                target_bucket=Genc10EconomicBucket.REALIZED_PROFIT,
                evidence_sha256=_sha(candidate, "genc10-gain"),
            ),
            Genc10CapitalFlow(
                flow_id=_tag(candidate, "genc10-loss"),
                kind=Genc10FlowKind.REALIZED_LOSS,
                amount_usd=Decimal("2"),
                source_bucket=Genc10EconomicBucket.ORIGINAL_BASE,
                evidence_sha256=_sha(candidate, "genc10-loss"),
            ),
        ),
        surviving_known_option_ids=(_tag(candidate, "known-option"),),
    )
    projected = project_genc10_world(
        twin=twin,
        scenario=scenario,
        projected_at=NOW + timedelta(minutes=10),
    )
    assert projected.total_realized_capital_usd == Decimal("102")
    assert projected.conservation_residual_usd == 0
    assert projected.productive_authority is False
    assert projected.market_probability_claimed is False


def _genc11_path(
    candidate: TraderLabCandidateBinding,
    *,
    suffix: str,
    kind: Genc10WorldKind,
    risk_deltas: tuple[str, str, str],
    margin_deltas: tuple[str, str, str],
) -> Genc11WorldPath:
    steps = tuple(
        Genc11WorldStep(
            step_index=index,
            projected_at=NOW + timedelta(minutes=5 * index),
            posture=CiboRegimePosture.STABLE,
            scenario=_genc10_scenario(
                candidate,
                suffix=f"{suffix}-{index}",
                kind=kind,
                risk_delta=risk_deltas[index - 1],
                margin_delta=margin_deltas[index - 1],
            ),
        )
        for index in range(1, 4)
    )
    return Genc11WorldPath(
        path_id=_tag(candidate, suffix),
        world_kind=kind,
        steps=steps,
        factor_interaction_evidence_sha256=_sha(candidate, f"{suffix}-factor"),
        optionality_evidence_sha256=_sha(candidate, f"{suffix}-optionality"),
        reserve_need_evidence_sha256=_sha(candidate, f"{suffix}-reserve"),
    )


def test_trader_lab_genc11_multi_period_mpc_executes(candidate_factory) -> None:
    candidate = candidate_factory(candidate_suffix=986)
    plan = plan_genc11_multi_period_capital(
        plan_id=_tag(candidate, "genc11-plan"),
        twin=_genc10_twin(candidate),
        world_paths=(
            _genc11_path(candidate, suffix="balanced", kind=Genc10WorldKind.BALANCED, risk_deltas=("0", "0", "0"), margin_deltas=("0", "0", "0")),
            _genc11_path(candidate, suffix="crisis", kind=Genc10WorldKind.CRISIS, risk_deltas=("-2", "0", "0"), margin_deltas=("-20", "0", "0")),
        ),
        option_schedules=(
            Genc11KnownOptionSchedule(
                option_id=_tag(candidate, "known-option"),
                decision_step=1,
                schedule_evidence_sha256=_sha(candidate, "genc11-schedule"),
            ),
        ),
    )
    assert plan.horizon_steps == 3
    assert len(plan.world_step_plans) == 6
    assert plan.robust_step_envelopes[0].all_worlds_horizon_coverable is True
    assert plan.oracle_arrivals_used is False
    assert plan.production_policy_selected is False
    assert plan.certification_ready is False


def test_trader_lab_genc12_crisis_intelligence_executes(candidate_factory) -> None:
    candidate = candidate_factory(candidate_suffix=987)
    twin = _genc10_twin(candidate)
    regime = CiboCapitalRegimeState(
        liquidity=LiquidityState.NORMAL,
        volatility=VolatilityState.NORMAL,
        correlation=CorrelationState.NORMAL,
        provider_condition=ProviderCondition.UNAVAILABLE,
        risk_utilization=Decimal("0"),
        margin_utilization=Decimal("0"),
        drawdown_utilization=Decimal("0.20"),
        opportunity_count=3,
    )
    plan = plan_genc12_crisis_capital(
        plan_id=_tag(candidate, "genc12-plan"),
        evaluated_at=NOW,
        twin=twin,
        regime_state=regime,
        crisis_facts=(
            Genc12CrisisFact(
                factor=Genc12CrisisFactor.PROVIDER_DEGRADATION,
                observed_at=NOW,
                evidence_sha256=_sha(candidate, "genc12-provider"),
                active=True,
            ),
        ),
    )
    assert plan.posture is CiboRegimePosture.HALT_NEW_CAPITAL
    assert plan.enabled_ce2i_tools == ("T20",)
    assert Genc12CapitalResponse.NO_NEW_DEPLOYMENT in plan.responses
    assert Genc12CapitalResponse.RELEASE_CAPACITY in plan.responses
    assert plan.risk_boundary_overridden is False
    assert plan.productive_authority is False


# GEN-C13 --------------------------------------------------------------------

def test_trader_lab_genc13_meta_memory_executes(candidate_factory) -> None:
    candidate = candidate_factory(candidate_suffix=988)
    identity = _identity(candidate, "genc13-account")
    episode_id = _tag(candidate, "genc13-episode")
    episode = Genc13CapitalEpisode(
        episode_id=episode_id,
        account_identity=identity,
        trader_id=TraderLineage.VT31_NAS100,
        decision_id=_tag(candidate, "genc13-decision"),
        decision_sha256=_sha(candidate, "genc13-decision"),
        decision_at=NOW,
        outcome_at=NOW + timedelta(minutes=30),
        outcome_sha256=_sha(candidate, "genc13-outcome"),
        capital_state_before_sha256=_sha(candidate, "genc13-before"),
        capital_state_after_sha256=_sha(candidate, "genc13-after"),
        action_code="ALLOCATE_MARGINAL_UNIT",
        allocated_capital_usd=Decimal("20"),
        peak_plausible_loss_usd=Decimal("1.5"),
        capital_minutes=Decimal("600"),
        realized_pnl_usd=Decimal("-1.5"),
    )
    phenotype = Genc13PhenotypeEvidence(
        phenotype=Genc13CapitalPhenotype.PREMATURE_EXPANSION,
        evidence_sha256=_sha(candidate, "genc13-phenotype"),
        identified_at=NOW + timedelta(minutes=31),
    )
    counterfactual = Genc13CounterfactualStudy(
        study_id=_tag(candidate, "genc13-cf"),
        episode_id=episode_id,
        kind=Genc13CounterfactualKind.DEPLOY_LESS,
        created_at=NOW + timedelta(minutes=32),
        simulation_evidence_sha256=_sha(candidate, "genc13-sim"),
        counterfactual_decision_sha256=_sha(candidate, "genc13-cf-decision"),
        ending_capital_delta_usd=Decimal("0.5"),
        max_drawdown_delta_usd=Decimal("-0.4"),
        optionality_delta_usd=Decimal("0.2"),
    )
    report = Genc13SkepticReport(
        report_id=_tag(candidate, "genc13-report"),
        episode=episode,
        phenotypes=(phenotype,),
        counterfactuals=(counterfactual,),
        generated_at=NOW + timedelta(minutes=33),
        hypothesis_worth_preregistering=True,
    )
    item = build_genc13_memory_item(
        report=report,
        recorded_at=NOW + timedelta(minutes=34),
    )
    result = CiboMemoryStore().record(item)
    assert item.kind is CiboMemoryKind.FAILURE_LESSON
    assert item.subject_code == "meta-capital"
    assert isinstance(result, Success)
    assert result.value.items == (item,)


# GEN-C14 --------------------------------------------------------------------

def test_trader_lab_genc14_governed_science_executes_without_auto_promotion(
    candidate_factory,
) -> None:
    candidate = candidate_factory(candidate_suffix=989)
    candidate_sha = _sha(candidate, "genc14-candidate")
    control_sha = _sha(candidate, "genc14-control")
    hypothesis = Genc14CapitalHypothesis(
        hypothesis_id=_tag(candidate, "genc14-hypothesis"),
        research_question="Can candidate-bound reserve-aware compounding improve robust value?",
        candidate_policy_id=_tag(candidate, "genc14-candidate-policy"),
        candidate_policy_sha256=candidate_sha,
        current_control_policy_id=_tag(candidate, "genc14-control-policy"),
        current_control_policy_sha256=control_sha,
        created_at=NOW,
        protected_holdout_ref=None,
    )
    record = start_genc14_science(
        science_id=_tag(candidate, "genc14-science"),
        hypothesis=hypothesis,
    )
    gates = (
        Genc14EvidenceKind.PREREGISTRATION,
        Genc14EvidenceKind.SIMULATION,
        Genc14EvidenceKind.OOS,
        Genc14EvidenceKind.STRESS,
        Genc14EvidenceKind.TEMPORAL_REPLICATION,
    )
    for index, kind in enumerate(gates, start=1):
        record = advance_genc14_science(
            record,
            evidence=Genc14ScienceEvidence(
                evidence_id=_tag(candidate, f"genc14-{kind.value.lower()}"),
                kind=kind,
                candidate_policy_sha256=candidate_sha,
                evaluated_at=NOW + timedelta(minutes=index),
                evidence_sha256=_sha(candidate, f"genc14-{kind.value}"),
                passed=True,
            ),
            advanced_at=NOW + timedelta(minutes=index),
        )
    record = advance_genc14_science(
        record,
        evidence=None,
        advanced_at=NOW + timedelta(minutes=6),
    )
    assert record.stage is Genc14ScienceStage.OWNER_REVIEW_REQUIRED
    assert record.terminal is True
    assert record.automatic_promotion is False
    assert record.certification_claimed is False
    assert record.owner_decision_recorded is False
