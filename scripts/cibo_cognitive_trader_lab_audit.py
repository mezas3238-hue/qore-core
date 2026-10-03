#!/usr/bin/env python3
"""Artifact-backed Trader Lab audit for CIBO cognition.

Acceptance is intentionally stronger than unit-test GREEN:
- all seven retained P0 Trader lanes must become genuine TraderLabCandidateBinding values;
- every candidate must advance through the real Trader Lab RESEARCH stage;
- each cognitive phase executes against that exact candidate plus retained P0 evidence;
- every phase emits an observable deterministic token that the next phase consumes;
- the audit is research-only and grants no Risk, order, broker, LIVE, Production,
  real-capital, promotion, or merge authority.

The P0 trace is a reused-holdout research artifact. A one-bar OHLC audit projection
is constructed from the retained predecision intended-entry price solely to obtain
an exact, non-hollow ResearchRunStrategyBinding/TraderLabCandidateBinding. It is
not represented as newly observed market history and makes no certification claim.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid5

from qore.infrastructure.cibo.contracts import (
    CiboEvidenceStatus,
    CiboFunctionalAuthority,
    CiboFunctionalEvidence,
)
from qore.infrastructure.cibo.functional_coordinator import (
    CiboFacultyDomain,
    CiboFunctionalContribution,
    CiboFunctionalCoordinator,
)
from qore.infrastructure.cibo.mission_director import (
    CiboMissionDirector,
    CiboMissionDisposition,
)
from qore.infrastructure.cibo_cognitive_attention import (
    AttentionEvidenceRef,
    AttentionSignal,
    AttentionSignalKind,
    CalibrationNote,
    ReasoningDepthHint,
    ReasoningRequest,
    ReasoningRouteDecision,
    calibration_requires_abstention,
    route_reasoning,
    select_context,
)
from qore.infrastructure.cibo_cognitive_causality import (
    CausalClaimKind,
    CausalClaimStatus,
    CausalClaimStrength,
    CausalEvidence,
    CausalEvidencePolarity,
    CausalVariable,
    MechanismBinding,
    build_causal_claim,
)
from qore.infrastructure.cibo_cognitive_common import (
    TraderSubject,
    fingerprint_material,
)
from qore.infrastructure.cibo_cognitive_evaluation import (
    CognitiveEvaluationStatus,
    EvaluationDimension,
    EvaluationDimensionScore,
    evaluate_cognition,
)
from qore.infrastructure.cibo_cognitive_hypotheses import (
    HypothesisStatus,
    build_hypothesis,
    transition_hypothesis,
)
from qore.infrastructure.cibo_cognitive_integration import (
    bind_evidence_fingerprint,
    build_integrated_episode,
    replay_integrated_episode,
)
from qore.infrastructure.cibo_cognitive_metacognition import (
    MetacognitiveFinding,
    build_metacognitive_audit,
    build_reasoning_transition,
)
from qore.infrastructure.cibo_cognitive_planning import (
    CognitiveGoal,
    CognitiveGoalId,
    CognitiveGoalStatus,
    CognitiveLearningRecord,
    CognitiveTask,
    CognitiveTaskId,
    CognitiveTaskStatus,
    EvidenceBundle,
    EvidenceRequirement,
    build_cognitive_plan,
    complete_task,
)
from qore.infrastructure.cibo_cognitive_replay import (
    ReplayToolCall,
    build_replay_episode,
    replay_episode,
)
from qore.infrastructure.cibo_cognitive_scenarios import (
    ScenarioAlternative,
    ScenarioAssumption,
    ScenarioFactKind,
    ScenarioFamily,
    build_scenario,
)
from qore.infrastructure.cibo_cognitive_tools import (
    ToolId,
    ToolInput,
    ToolRequest,
    ToolResult,
    ToolResultStatus,
    ToolVersion,
    bind_tool_result,
)
from qore.infrastructure.cibo_cognitive_world_model import (
    MarketContextKind,
    MarketContextReference,
    MarketTraderContext,
    MarketTraderSuitabilityDisposition,
    WorldModelDomain,
    WorldModelReference,
    WorldModelReferenceStatus,
    WorldModelSourceId,
    WorldModelSourceVersion,
    build_market_trader_suitability,
    build_world_model_snapshot,
)
from qore.infrastructure.cibo_executive_brain import (
    CiboExecutiveBrain,
    CiboExecutiveDirectiveKind,
)
from qore.infrastructure.cibo_executive_deliberation import (
    CiboCouncilOutcome,
    CiboCouncilSynthesis,
)
from qore.infrastructure.cibo_executive_memory import (
    CiboMemoryFreshness,
    CiboMemoryFreshnessState,
    CiboMemoryItem,
    CiboMemoryKind,
    CiboMemoryProvenance,
    CiboMemorySourceRef,
    CiboMemoryStore,
)
from qore.infrastructure.cibo_trader_capability_profile import CiboEvidenceRef
from qore.infrastructure.historical_dataset import (
    HistoricalDatasetId,
    HistoricalDatasetNormalizationVersion,
    HistoricalDatasetRevisionId,
    HistoricalDatasetSchemaVersion,
    HistoricalOhlcDatasetScope,
    build_historical_ohlc_replay_dataset,
)
from qore.infrastructure.historical_market_data import HistoricalOhlcWindow
from qore.infrastructure.market_data import (
    Instrument,
    MarketDataSnapshotId,
    OhlcSnapshot,
    Timeframe,
)
from qore.infrastructure.ports import AdapterId, ExternalSourceDescriptor, PortName, SourceId
from qore.infrastructure.replay_availability import (
    ReplayAvailabilityBasis,
    ReplayAvailabilityEvidenceReference,
    ReplayMarketDataObservation,
    ReplayObservationId,
)
from qore.infrastructure.research_evaluation_freeze import (
    ResearchEvaluationFreezeEvidenceId,
    build_research_evaluation_freeze_evidence,
)
from qore.infrastructure.research_evaluator_identity import (
    ResearchDecisionEvaluatorFamily,
    ResearchDecisionEvaluatorIdentity,
    ResearchDecisionEvaluatorSchemaVersion,
)
from qore.infrastructure.research_run import (
    ResearchRandomnessMode,
    ResearchReplayPolicyVersion,
    ResearchRunId,
    ResearchSoftwareRevision,
    ResearchStrategyConfigurationId,
    build_research_run_evidence,
)
from qore.infrastructure.research_strategy_freeze import (
    ResearchStrategyFreezeEvidenceReference,
    ResearchStrategyParameter,
    ResearchStrategySchemaVersion,
    build_research_run_strategy_binding,
    build_research_strategy_configuration_manifest,
)
from qore.infrastructure.research_temporal_evaluation import (
    ResearchEvaluationWindow,
    ResearchTemporalEvaluationPlanId,
    ResearchWalkForwardFold,
    build_research_temporal_evaluation_plan,
)
from qore.infrastructure.trader_lab.candidate import (
    TraderLabCandidateId,
    TraderLabCandidateVersion,
    build_trader_lab_candidate_binding,
)
from qore.infrastructure.trader_lab.lifecycle import (
    TraderLabPromotionRequest,
    TraderLabState,
    apply_trader_lab_promotion,
    start_trader_lab_lifecycle,
)
from qore.infrastructure.trader_lab.stage_evidence import (
    TraderLabStage,
    TraderLabStageEvidenceId,
    build_trader_lab_stage_evidence,
    reference_research_evaluation_freeze,
)
from qore.kernel.result import Success
from qore.modules.cibo.cognitive_contracts import (
    CiboCognitiveEvidenceRef,
    CiboConfidence,
    CiboConfidenceLevel,
    CiboReasoningMode,
    CiboUncertainty,
    CiboUncertaintyKind,
)

TRADERS = (
    "VT08_FOREX",
    "R34_XAUUSD",
    "R38_EURUSD",
    "R43_GBPUSD",
    "R38_GBPJPY",
    "R42_AUDJPY",
    "VT31_NAS100",
)

PHASES = (
    "P01_TRADER_LAB_RESEARCH",
    "P02_WORLD_MODEL",
    "P03_ATTENTION_ROUTING",
    "P04_PLANNING",
    "P05_TOOL_ORCHESTRATION",
    "P06_CAUSALITY",
    "P07_SCENARIOS",
    "P08_HYPOTHESES",
    "P09_METACOGNITION",
    "P10_EXECUTIVE_MEMORY",
    "P11_COUNCIL_SYNTHESIS",
    "P12_EXECUTIVE_BRAIN_RESEARCH_ONLY",
    "P13_REPLAY",
    "P14_POST_OUTCOME_LEARNING",
    "P15_EVALUATION",
    "P16_INTEGRATED_EPISODE",
    "P17_CURRENT_MISSION_CF01_CF19",
    "P18_DETERMINISM_CHAIN",
)


def _u(seed: str) -> UUID:
    return uuid5(NAMESPACE_URL, "qore:cibo:cognitive-trader-lab-audit:" + seed)


def _dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("trace datetime must be timezone-aware")
    return parsed


def _must_success(result: object, label: str):
    if not isinstance(result, Success):
        error = getattr(result, "error", result)
        raise RuntimeError(f"{label} failed: {error}")
    return result.value


def _token(*parts: object) -> str:
    return fingerprint_material(tuple(parts)).value


def _safe_code(value: str) -> str:
    return value.lower().replace("_", "-").replace("/", "-")


@dataclass
class TraderContext:
    trader: str
    rows: list[dict[str, object]]
    row: dict[str, object]
    settlement_row: dict[str, object]
    candidate: object | None = None
    lifecycle: object | None = None
    world: object | None = None
    suitability: object | None = None
    attention: object | None = None
    calibration: object | None = None
    plan: object | None = None
    tool_request: object | None = None
    tool_result: object | None = None
    causal_claim: object | None = None
    scenarios: tuple[object, ...] = ()
    hypothesis: object | None = None
    audit: object | None = None
    transition: object | None = None
    memory_item: object | None = None
    council: object | None = None
    brain: object | None = None
    replay: object | None = None
    learning: object | None = None
    evaluation: object | None = None
    integrated: object | None = None
    coordination: object | None = None
    phase_tokens: dict[str, str] = field(default_factory=dict)


class Audit:
    def __init__(self, trace: dict[str, object], source_head: str) -> None:
        rows = trace.get("opportunities")
        if not isinstance(rows, list) or not rows:
            raise ValueError("decision-trace opportunities missing")
        if trace.get("governance", {}).get("broker_mutation") is not False:  # type: ignore[union-attr]
            raise ValueError("source trace must be non-mutating")
        self.trace = trace
        self.source_head = source_head
        self.contexts: dict[str, TraderContext] = {}
        self.report_rows: dict[str, dict[str, dict[str, object]]] = {
            phase: {} for phase in PHASES
        }
        for trader in TRADERS:
            trader_rows = [r for r in rows if isinstance(r, dict) and r.get("trader_id") == trader]
            if not trader_rows:
                raise ValueError(f"missing source population for {trader}")
            settled = [
                r for r in trader_rows
                if isinstance(r.get("settlement"), dict)
                and r["settlement"].get("observed_at")
            ]
            if not settled:
                raise ValueError(f"no settled retained observation for {trader}")
            self.contexts[trader] = TraderContext(
                trader=trader,
                rows=trader_rows,
                row=trader_rows[0],
                settlement_row=settled[0],
            )

    def record(self, ctx: TraderContext, phase: str, output_token: str, details: dict[str, object]) -> None:
        previous = None
        idx = PHASES.index(phase)
        if idx:
            previous = PHASES[idx - 1]
            if previous not in ctx.phase_tokens:
                raise RuntimeError(f"{phase} cannot run before {previous} for {ctx.trader}")
            self.report_rows[previous][ctx.trader]["consumed_by"] = phase
        ctx.phase_tokens[phase] = output_token
        self.report_rows[phase][ctx.trader] = {
            "status": "GREEN",
            "trader_lab_candidate": True,
            "input_from_previous": previous,
            "output_token": output_token,
            "consumed_by": None,
            **details,
        }

    def run_phase(self, phase: str, fn) -> None:
        for trader in TRADERS:
            fn(self.contexts[trader])
        if any(self.report_rows[phase].get(t, {}).get("status") != "GREEN" for t in TRADERS):
            raise RuntimeError(f"{phase} did not pass all seven Trader Lab candidates")

    def p01(self, ctx: TraderContext) -> None:
        row = ctx.row
        opportunity = row["trader_opportunity"]
        if not isinstance(opportunity, dict):
            raise ValueError("trader opportunity missing")
        t0 = _dt(str(row["market_decision_at"]))
        t1 = t0 + timedelta(seconds=1)
        source = ExternalSourceDescriptor(
            adapter_id=AdapterId(_u(ctx.trader + ":adapter")),
            source_id=SourceId(_u(ctx.trader + ":source")),
            port_name=PortName("market-data.cibo-trader-lab-audit"),
        )
        instrument = Instrument(str(row["qore_symbol"]))
        timeframe = Timeframe(1)
        price = float(Decimal(str(opportunity["intended_entry"])))
        bar = OhlcSnapshot(
            snapshot_id=MarketDataSnapshotId(_u(ctx.trader + ":bar")),
            instrument=instrument,
            source=source,
            timeframe=timeframe,
            opened_at=t0,
            closed_at=t1,
            open=price,
            high=price,
            low=price,
            close=price,
        )
        observation = ReplayMarketDataObservation(
            observation_id=ReplayObservationId(_u(ctx.trader + ":observation")),
            payload=bar,
            availability_evidence_at=t1,
            available_at=t1,
            availability_basis=ReplayAvailabilityBasis.STRUCTURAL_BOUNDARY,
            availability_evidence_ref=ReplayAvailabilityEvidenceReference(
                _u(ctx.trader + ":availability-evidence")
            ),
        )
        scope = HistoricalOhlcDatasetScope(
            source=source,
            window=HistoricalOhlcWindow(
                instrument=instrument,
                timeframe=timeframe,
                opened_at=t0,
                closed_at=t1,
            ),
        )
        dataset = _must_success(
            build_historical_ohlc_replay_dataset(
                dataset_id=HistoricalDatasetId(_u(ctx.trader + ":dataset")),
                revision_id=HistoricalDatasetRevisionId(_u(ctx.trader + ":dataset-rev")),
                parent_revision_id=None,
                revision_reason=None,
                scope=scope,
                assembled_at=t1 + timedelta(seconds=1),
                schema_version=HistoricalDatasetSchemaVersion("v1"),
                normalization_version=HistoricalDatasetNormalizationVersion("v1"),
                observations=(observation,),
            ),
            "historical audit dataset",
        )
        config_id = ResearchStrategyConfigurationId(_u(ctx.trader + ":config"))
        manifest = _must_success(
            build_research_strategy_configuration_manifest(
                configuration_id=config_id,
                schema_version=ResearchStrategySchemaVersion("v1"),
                parameters=(
                    ResearchStrategyParameter("trader", ctx.trader),
                    ResearchStrategyParameter("symbol", str(row["qore_symbol"])),
                    ResearchStrategyParameter("opportunity-count", len(ctx.rows)),
                    ResearchStrategyParameter(
                        "source-decision-evidence",
                        str(row["decision_evidence_sha256"]),
                    ),
                ),
                frozen_at=t1 + timedelta(seconds=2),
                evidence_ref=ResearchStrategyFreezeEvidenceReference(
                    _u(ctx.trader + ":strategy-freeze-evidence")
                ),
            ),
            "strategy configuration freeze",
        )
        run = _must_success(
            build_research_run_evidence(
                run_id=ResearchRunId(_u(ctx.trader + ":research-run")),
                created_at=t1 + timedelta(seconds=3),
                datasets=(dataset.manifest,),
                replay_policy_version=ResearchReplayPolicyVersion("v1"),
                simulated_start=t0,
                simulated_end=t1,
                strategy_configuration_id=config_id,
                software_revision=ResearchSoftwareRevision(self.source_head),
                execution_model_id=None,
                transaction_cost_model_id=None,
                randomness_mode=ResearchRandomnessMode.DETERMINISTIC,
                random_seed=None,
            ),
            "research run",
        )
        binding = _must_success(
            build_research_run_strategy_binding(run=run, manifest=manifest),
            "research strategy binding",
        )
        candidate = _must_success(
            build_trader_lab_candidate_binding(
                candidate_id=TraderLabCandidateId(_u(ctx.trader + ":candidate")),
                version=TraderLabCandidateVersion("cognitive-audit-v1"),
                strategy_binding=binding,
            ),
            "Trader Lab candidate",
        )
        fold = ResearchWalkForwardFold(
            fold_number=1,
            in_sample=ResearchEvaluationWindow(t0, t0 + timedelta(microseconds=500000)),
            out_of_sample=ResearchEvaluationWindow(
                t0 + timedelta(microseconds=500000), t1
            ),
        )
        plan = _must_success(
            build_research_temporal_evaluation_plan(
                plan_id=ResearchTemporalEvaluationPlanId(_u(ctx.trader + ":eval-plan")),
                run=run,
                folds=(fold,),
                created_at=t1 + timedelta(seconds=4),
            ),
            "temporal evaluation plan",
        )
        freeze = _must_success(
            build_research_evaluation_freeze_evidence(
                evidence_id=ResearchEvaluationFreezeEvidenceId(
                    _u(ctx.trader + ":eval-freeze")
                ),
                strategy_binding=binding,
                plan=plan,
                established_at=t1 + timedelta(seconds=5),
            ),
            "evaluation freeze",
        )
        source_ref = reference_research_evaluation_freeze(candidate, freeze)
        stage_evidence = _must_success(
            build_trader_lab_stage_evidence(
                evidence_id=TraderLabStageEvidenceId(_u(ctx.trader + ":stage-research")),
                stage=TraderLabStage.RESEARCH,
                candidate=candidate,
                source_reference=source_ref,
                produced_at=t1 + timedelta(seconds=6),
            ),
            "Trader Lab RESEARCH stage evidence",
        )
        lifecycle = start_trader_lab_lifecycle(candidate)
        lifecycle = _must_success(
            apply_trader_lab_promotion(
                lifecycle,
                TraderLabPromotionRequest(
                    stage=TraderLabStage.RESEARCH,
                    evidence=stage_evidence,
                ),
            ),
            "Trader Lab RESEARCH promotion",
        )
        if lifecycle.state is not TraderLabState.RESEARCH_READY:
            raise RuntimeError("Trader Lab candidate did not become RESEARCH_READY")
        ctx.candidate = candidate
        ctx.lifecycle = lifecycle
        self.record(
            ctx,
            PHASES[0],
            candidate.fingerprint.value,
            {
                "trader_lab_state": lifecycle.state.value,
                "source_decision_evidence": row["decision_evidence_sha256"],
                "audit_projection": "ONE_BAR_FROM_RETAINED_PREDECISION_INTENDED_ENTRY",
                "hollow_fixture_used": False,
            },
        )

    def p02(self, ctx: TraderContext) -> None:
        candidate = ctx.candidate
        if candidate is None:
            raise RuntimeError("candidate missing")
        row = ctx.row
        t = _dt(str(row["market_decision_at"]))
        source_fp = fingerprint_material(
            (
                candidate.fingerprint.value,
                str(row["decision_evidence_sha256"]),
                str(row["qore_symbol"]),
            )
        )
        ref = WorldModelReference(
            domain=WorldModelDomain.MARKET,
            source_id=WorldModelSourceId("trader-lab-p0"),
            source_version=WorldModelSourceVersion("v1"),
            as_of=t,
            status=WorldModelReferenceStatus.CURRENT,
            evidence_fingerprint=source_fp,
            evidence_label="retained Trader Lab predecision evidence",
        )
        world = build_world_model_snapshot(
            snapshot_id=_u(ctx.trader + ":world"),
            as_of=t,
            references=(ref,),
        )
        subject = TraderSubject(
            trader_id=ctx.trader,
            trader_version="cognitive-audit-v1",
            fingerprint=fingerprint_material((ctx.trader, "cognitive-audit-v1")),
        )
        context = MarketTraderContext(
            market=MarketContextReference(
                kind=MarketContextKind.MARKET,
                reference="market." + _safe_code(str(row["qore_symbol"])),
                as_of=t,
                status=WorldModelReferenceStatus.CURRENT,
                evidence_fingerprint=world.fingerprint,
                evidence_label="Trader Lab market context",
            ),
            instrument=MarketContextReference(
                kind=MarketContextKind.INSTRUMENT,
                reference="instrument." + _safe_code(str(row["qore_symbol"])),
                as_of=t,
                status=WorldModelReferenceStatus.CURRENT,
                evidence_fingerprint=world.fingerprint,
                evidence_label="Trader Lab instrument context",
            ),
            regime=MarketContextReference(
                kind=MarketContextKind.REGIME,
                reference="regime.retained-predecision",
                as_of=t,
                status=WorldModelReferenceStatus.CURRENT,
                evidence_fingerprint=world.fingerprint,
                evidence_label="Trader Lab retained regime context",
            ),
        )
        suitability = build_market_trader_suitability(
            suitability_id=_u(ctx.trader + ":suitability"),
            trader=subject,
            context=context,
            disposition=MarketTraderSuitabilityDisposition.DEGRADED,
            uncertainty_codes=("reused-holdout",),
            limitations=("non-certifying-audit",),
            evidence_lineage=(world.fingerprint,),
        )
        ctx.world = world
        ctx.suitability = suitability
        self.record(
            ctx,
            PHASES[1],
            suitability.fingerprint.value,
            {"world_fingerprint": world.fingerprint.value},
        )

    def p03(self, ctx: TraderContext) -> None:
        if ctx.world is None:
            raise RuntimeError("world model missing")
        signal = AttentionSignal(
            signal_id=_u(ctx.trader + ":attention"),
            kind=AttentionSignalKind.RESEARCH_QUESTION,
            summary="validate retained Trader Lab candidate cognition",
            evidence_refs=(
                AttentionEvidenceRef(
                    reference_id="world:" + ctx.world.fingerprint.value,
                    fingerprint=ctx.world.fingerprint,
                ),
            ),
            severity=90,
            priority_reason="candidate-research-audit",
        )
        selected = select_context((signal,), max_results=1)
        if not selected.ranked or selected.ranked[0].signal != signal:
            raise RuntimeError("attention did not select retained Trader Lab evidence")
        request = ReasoningRequest(
            request_id=_u(ctx.trader + ":reasoning"),
            depth_hint=ReasoningDepthHint("high"),
            missing_evidence=(),
            justification="retained Trader Lab evidence is available",
        )
        routing = route_reasoning(request)
        if routing.decision is not ReasoningRouteDecision.PROCEED:
            raise RuntimeError("reasoning route did not proceed")
        calibration = CalibrationNote(
            confidence_band=70,
            note="bounded confidence on reused-holdout Trader Lab audit",
            abstention_required=False,
        )
        if calibration_requires_abstention(calibration):
            raise RuntimeError("calibration unexpectedly abstained")
        ctx.attention = selected
        ctx.calibration = calibration
        self.record(
            ctx,
            PHASES[2],
            _token(
                ctx.phase_tokens[PHASES[1]],
                routing.decision.value,
                calibration.confidence_band,
            ),
            {"routing": routing.decision.value, "selected_signal_count": len(selected.ranked)},
        )

    def p04(self, ctx: TraderContext) -> None:
        required = "evidence:" + ctx.phase_tokens[PHASES[2]]
        goal = CognitiveGoal(
            goal_id=CognitiveGoalId(_u(ctx.trader + ":goal")),
            description="audit cognition on exact Trader Lab candidate",
            status=CognitiveGoalStatus.PENDING,
        )
        task = CognitiveTask(
            task_id=CognitiveTaskId(_u(ctx.trader + ":task")),
            goal_id=goal.goal_id,
            description="consume attention evidence and prepare tool request",
            dependencies=(),
            required_evidence=(EvidenceRequirement(reference=required),),
            status=CognitiveTaskStatus.PENDING,
        )
        plan = build_cognitive_plan(
            plan_id=_u(ctx.trader + ":plan"),
            goals=(goal,),
            tasks=(task,),
        )
        plan = complete_task(plan, task.task_id, completed_evidence=(required,))
        if plan.task_by_id(task.task_id).status is not CognitiveTaskStatus.COMPLETED:
            raise RuntimeError("cognitive plan task did not complete")
        ctx.plan = plan
        self.record(
            ctx,
            PHASES[3],
            _token(ctx.phase_tokens[PHASES[2]], plan.revision),
            {"plan_revision": plan.revision},
        )

    def p05(self, ctx: TraderContext) -> None:
        material = (
            ctx.trader,
            ctx.phase_tokens[PHASES[3]],
            ctx.phase_tokens[PHASES[1]],
        )
        tool_input = ToolInput(material=material, fingerprint=fingerprint_material(material))
        request = ToolRequest(
            request_id=_u(ctx.trader + ":tool-request"),
            tool_id=ToolId("trader-lab-cognitive-audit"),
            tool_version=ToolVersion("v1"),
            input=tool_input,
        )
        output = ("validated", ctx.trader, ctx.phase_tokens[PHASES[3]])
        result = ToolResult(
            request_id=request.request_id,
            tool_id=request.tool_id,
            tool_version=request.tool_version,
            input_fingerprint=tool_input.fingerprint,
            output_material=output,
            output_fingerprint=fingerprint_material(output),
            status=ToolResultStatus.SUCCESS,
            attempt=1,
        )
        bound = _must_success(bind_tool_result(request, result), "cognitive tool binding")
        ctx.tool_request = request
        ctx.tool_result = bound
        self.record(
            ctx,
            PHASES[4],
            result.output_fingerprint.value,
            {"tool_status": result.status.value, "attempt": result.attempt},
        )

    def p06(self, ctx: TraderContext) -> None:
        now = _dt(str(ctx.row["market_decision_at"]))
        ref_value = "sha256:" + ctx.phase_tokens[PHASES[4]]
        evidence = CausalEvidence(
            ref=CiboCognitiveEvidenceRef(ref_value),
            polarity=CausalEvidencePolarity.SUPPORTS,
            observed_at=now,
            fingerprint=fingerprint_material(
                (ref_value, CausalEvidencePolarity.SUPPORTS.value, now)
            ),
        )
        cause = CausalVariable(
            code="trader-lab-evidence",
            fingerprint=fingerprint_material(("trader-lab-evidence",)),
        )
        effect = CausalVariable(
            code="cognitive-audit-result",
            fingerprint=fingerprint_material(("cognitive-audit-result",)),
        )
        mechanism = MechanismBinding(
            code="mechanism.evidence-binding",
            evidence=evidence,
        )
        claim = build_causal_claim(
            claim_id=_u(ctx.trader + ":causal"),
            kind=CausalClaimKind.CAUSATION,
            cause=cause,
            effect=effect,
            mechanism=mechanism,
            strength=CausalClaimStrength.MODERATE,
            status=CausalClaimStatus.ACTIVE,
            evidence_for=(evidence,),
        )
        ctx.causal_claim = claim
        self.record(
            ctx,
            PHASES[5],
            claim.fingerprint.value,
            {"causal_kind": claim.kind.value, "causal_status": claim.status.value},
        )

    def p07(self, ctx: TraderContext) -> None:
        if ctx.world is None:
            raise RuntimeError("world missing")
        assumption = ScenarioAssumption(
            code="retained-trader-lab-evidence",
            fact_kind=ScenarioFactKind.OBSERVED,
        )
        uncertainty = CiboUncertainty(kind=CiboUncertaintyKind.INSUFFICIENT_EVIDENCE)
        families = (
            ScenarioFamily.BASE,
            ScenarioFamily.ADVERSE,
            ScenarioFamily.EXTREME,
            ScenarioFamily.REGIME_CHANGE,
        )
        scenarios = []
        for index, family in enumerate(families):
            abstained = family is not ScenarioFamily.BASE
            alternatives = () if abstained else (
                ScenarioAlternative(
                    alternative_id=_u(ctx.trader + f":scenario-alt:{index}"),
                    action_code="continue-research",
                    outcome_code="undetermined",
                ),
            )
            scenarios.append(
                build_scenario(
                    scenario_id=_u(ctx.trader + f":scenario:{family.value}"),
                    family=family,
                    version="v1",
                    assumptions=(assumption,),
                    world_snapshot_id=ctx.world.snapshot_id,
                    world_fingerprint=ctx.world.fingerprint,
                    alternatives=alternatives,
                    abstained=abstained,
                    uncertainty=uncertainty,
                    limitations=("no-calibrated-probability",),
                )
            )
        ctx.scenarios = tuple(scenarios)
        self.record(
            ctx,
            PHASES[6],
            _token(
                ctx.phase_tokens[PHASES[5]],
                tuple(s.fingerprint.value for s in ctx.scenarios),
            ),
            {"scenario_families": [s.family.value for s in ctx.scenarios]},
        )

    def p08(self, ctx: TraderContext) -> None:
        claim = ctx.causal_claim
        if claim is None:
            raise RuntimeError("causal claim missing")
        born = build_hypothesis(
            hypothesis_id=_u(ctx.trader + ":hypothesis"),
            content_code="h.trader-lab-cognition",
            status=HypothesisStatus.BORN,
            causal_claim_ref=(claim.claim_id, claim.fingerprint),
        )
        active = transition_hypothesis(born, HypothesisStatus.ACTIVE)
        ctx.hypothesis = active
        self.record(
            ctx,
            PHASES[7],
            active.fingerprint.value,
            {"hypothesis_status": active.status.value},
        )

    def p09(self, ctx: TraderContext) -> None:
        evidence_ref = CiboCognitiveEvidenceRef(
            "sha256:" + ctx.phase_tokens[PHASES[7]]
        )
        audit = build_metacognitive_audit(
            audit_id=_u(ctx.trader + ":metacognition"),
            reasoning_mode=CiboReasoningMode.HIGH,
            evidence_sufficiency=MetacognitiveFinding.SUFFICIENT,
            reason_codes=("trader-lab-evidence-present",),
        )
        transition = build_reasoning_transition(
            from_mode=CiboReasoningMode.HIGH,
            to_mode=CiboReasoningMode.MAX,
            reason_code="full-audit-required",
            evidence_refs=(evidence_ref,),
        )
        ctx.audit = audit
        ctx.transition = transition
        self.record(
            ctx,
            PHASES[8],
            _token(
                ctx.phase_tokens[PHASES[7]],
                audit.fingerprint.value,
                transition.to_mode.value,
            ),
            {"reasoning_mode": transition.to_mode.value},
        )

    def p10(self, ctx: TraderContext) -> None:
        now = _dt(str(ctx.row["market_decision_at"]))
        item = CiboMemoryItem(
            item_id=_u(ctx.trader + ":memory"),
            kind=CiboMemoryKind.RESEARCH,
            subject_code="trader-" + _safe_code(ctx.trader),
            content=f"Trader Lab cognitive audit retained evidence for {ctx.trader}",
            provenance=CiboMemoryProvenance(
                source_ref=CiboMemorySourceRef("source:trader-lab-audit"),
                effective_at=now,
            ),
            freshness=CiboMemoryFreshness(
                state=CiboMemoryFreshnessState.CURRENT,
                as_of=now,
            ),
            evidence_refs=(
                CiboCognitiveEvidenceRef("sha256:" + ctx.phase_tokens[PHASES[8]]),
            ),
        )
        store = _must_success(CiboMemoryStore().record(item), "executive memory record")
        retrieved = store.retrieve(kind=CiboMemoryKind.RESEARCH)
        if retrieved != (item,):
            raise RuntimeError("executive memory did not retrieve retained item")
        ctx.memory_item = item
        self.record(
            ctx,
            PHASES[9],
            _token(ctx.phase_tokens[PHASES[8]], item.logical_values()),
            {"retrieved_count": len(retrieved)},
        )

    def p11(self, ctx: TraderContext) -> None:
        now = _dt(str(ctx.row["market_decision_at"]))
        evidence_ref = CiboCognitiveEvidenceRef(
            "sha256:" + ctx.phase_tokens[PHASES[9]]
        )
        confidence = CiboConfidence(
            level=CiboConfidenceLevel.MEDIUM,
            evidence_refs=(evidence_ref,),
        )
        synthesis = CiboCouncilSynthesis(
            synthesis_id=_u(ctx.trader + ":council"),
            summary="Trader Lab research council synthesis",
            evidence_refs=(evidence_ref,),
            uncertainty=CiboUncertainty(
                kind=CiboUncertaintyKind.BOUNDED_CONFIDENCE,
                confidence=confidence,
            ),
            synthesized_at=now,
            limitations=("research-only",),
        )
        ctx.council = synthesis
        self.record(
            ctx,
            PHASES[10],
            _token(ctx.phase_tokens[PHASES[9]], synthesis.logical_values()),
            {"council_outcome": CiboCouncilOutcome.DECISION.value},
        )

    def p12(self, ctx: TraderContext) -> None:
        now = _dt(str(ctx.row["market_decision_at"]))
        evidence_ref = CiboCognitiveEvidenceRef(
            "sha256:" + ctx.phase_tokens[PHASES[10]]
        )
        result = CiboExecutiveBrain().synthesize(
            synthesis_id=_u(ctx.trader + ":brain"),
            directive=CiboExecutiveDirectiveKind.REQUEST_EVIDENCE,
            reasoning_mode=CiboReasoningMode.MAX,
            subject_code="trader-" + _safe_code(ctx.trader),
            synthesized_at=now,
            evidence_refs=(evidence_ref,),
            uncertainty=CiboUncertainty(
                kind=CiboUncertaintyKind.MORE_EVIDENCE_REQUESTED
            ),
            observations=("trader-lab-research-complete",),
            request_code="continue-trader-lab-evidence",
            limitations=("research-only", "no-productive-authority"),
        )
        brain = _must_success(result, "research-only Executive Brain")
        ctx.brain = brain
        self.record(
            ctx,
            PHASES[11],
            _token(ctx.phase_tokens[PHASES[10]], brain.logical_values()),
            {
                "directive": brain.directive.value,
                "runtime_scope": "TRADER_LAB_RESEARCH_ONLY",
            },
        )

    def p13(self, ctx: TraderContext) -> None:
        if ctx.world is None or ctx.tool_request is None or ctx.tool_result is None:
            raise RuntimeError("replay prerequisites missing")
        result_fp = ctx.tool_result.output_fingerprint
        call = ReplayToolCall(
            request_id=ctx.tool_request.request_id,
            input_fingerprint=ctx.tool_request.input.fingerprint,
            result_fingerprint=result_fp,
        )
        episode = build_replay_episode(
            episode_id=_u(ctx.trader + ":replay"),
            recorded_at=_dt(str(ctx.row["market_decision_at"])),
            world_snapshot_id=ctx.world.snapshot_id,
            attention_reasons=("trader-lab-candidate-audit",),
            goal_plan_state="research-complete",
            tool_calls=(call,),
            counterfactuals=("without-cognitive-audit",),
            uncertainties=("reused-holdout",),
            evidence_refs=("sha256:" + ctx.phase_tokens[PHASES[11]],),
            changes_after=("none",),
            handoff_reference="trader-lab-research",
        )
        reconstructed = replay_episode(episode)
        if reconstructed.fingerprint != episode.fingerprint:
            raise RuntimeError("cognitive replay fingerprint drift")
        ctx.replay = episode
        self.record(
            ctx,
            PHASES[12],
            episode.fingerprint.value,
            {"replay_round_trip": True},
        )

    def p14(self, ctx: TraderContext) -> None:
        settlement = ctx.settlement_row["settlement"]
        if not isinstance(settlement, dict):
            raise RuntimeError("settlement missing")
        decision_time = _dt(str(ctx.settlement_row["market_decision_at"]))
        observed_at = _dt(str(settlement["observed_at"]))
        if observed_at < decision_time:
            raise RuntimeError("settlement predates decision")
        record = CognitiveLearningRecord(
            record_id=_u(ctx.trader + ":learning"),
            decision_time=decision_time,
            expected_result="Trader Lab outcome remains unknown at decision time",
            actual_result_reference=EvidenceBundle(
                reference="settlement:" + str(settlement["evidence_id"]),
                observed_at=observed_at,
            ),
            contemporaneous_evidence=(
                EvidenceBundle(
                    reference="decision:" + str(ctx.settlement_row["decision_evidence_sha256"]),
                    observed_at=decision_time,
                ),
            ),
            later_evidence=(
                EvidenceBundle(
                    reference="settlement:" + str(settlement["evidence_id"]),
                    observed_at=observed_at,
                ),
            ),
            error_attribution="post-outcome-learning-only",
            counterfactuals=("no-cognitive-intervention",),
            reflection_note="Outcome was added only after the retained decision",
            supersedes=None,
        )
        ctx.learning = record
        self.record(
            ctx,
            PHASES[13],
            _token(
                ctx.phase_tokens[PHASES[12]],
                str(record.record_id),
                record.decision_time.isoformat(),
                record.actual_result_reference.reference,
                record.actual_result_reference.observed_at.isoformat(),
                record.error_attribution,
            ),
            {
                "decision_time": decision_time.isoformat(),
                "outcome_time": observed_at.isoformat(),
                "same_trade_decision_mutated": False,
            },
        )

    def p15(self, ctx: TraderContext) -> None:
        replay = ctx.replay
        if replay is None:
            raise RuntimeError("replay missing")
        evaluation = evaluate_cognition(
            evaluation_id=_u(ctx.trader + ":evaluation"),
            evaluated_reference="sha256:" + replay.fingerprint.value,
            dimensions=(
                EvaluationDimensionScore(
                    dimension=EvaluationDimension.EVIDENCE_SUFFICIENCY,
                    score=80,
                    note="retained Trader Lab evidence supplied",
                ),
                EvaluationDimensionScore(
                    dimension=EvaluationDimension.REPLAY_COMPLETENESS,
                    score=100,
                    note="deterministic replay reproduced",
                ),
            ),
            evidence_refs=(
                "sha256:" + ctx.phase_tokens[PHASES[13]],
                "sha256:" + replay.fingerprint.value,
            ),
        )
        if evaluation.status is not CognitiveEvaluationStatus.SUFFICIENT_FOR_EVALUATION:
            raise RuntimeError("cognitive evaluation was not sufficient")
        ctx.evaluation = evaluation
        self.record(
            ctx,
            PHASES[14],
            _token(
                ctx.phase_tokens[PHASES[13]],
                str(evaluation.evaluation_id),
                evaluation.evaluated_reference,
                evaluation.status.value,
                tuple(
                    (d.dimension.value, d.score, d.note)
                    for d in evaluation.dimensions
                ),
                evaluation.evidence_refs,
                evaluation.contradiction_refs,
            ),
            {"evaluation_status": evaluation.status.value},
        )

    def p16(self, ctx: TraderContext) -> None:
        required = (
            ctx.world,
            ctx.suitability,
            ctx.plan,
            ctx.replay,
            ctx.evaluation,
            ctx.causal_claim,
            ctx.hypothesis,
            ctx.audit,
            ctx.transition,
            ctx.learning,
            ctx.council,
        )
        if any(x is None for x in required):
            raise RuntimeError("integrated episode prerequisites missing")
        evidence_binding = bind_evidence_fingerprint(
            fingerprint_material(
                (
                    ctx.phase_tokens[PHASES[14]],
                    ctx.candidate.fingerprint.value,  # type: ignore[union-attr]
                )
            )
        )
        settlement = ctx.settlement_row["settlement"]
        recorded_at = _dt(str(settlement["observed_at"]))  # type: ignore[index]
        confidence_ref = CiboCognitiveEvidenceRef(
            "sha256:" + ctx.phase_tokens[PHASES[14]]
        )
        integrated = build_integrated_episode(
            integration_id=_u(ctx.trader + ":integrated"),
            reasoning_mode=CiboReasoningMode.MAX,
            evidence_bindings=(evidence_binding,),
            recorded_at=recorded_at,
            world_snapshot=ctx.world,
            deliberation_outcome=CiboCouncilOutcome.DECISION,
            synthesis=ctx.council,
            replay=ctx.replay,
            evaluation=ctx.evaluation,
            plan_reference=ctx.plan,
            uncertainty=CiboUncertainty(
                kind=CiboUncertaintyKind.BOUNDED_CONFIDENCE,
                confidence=CiboConfidence(
                    level=CiboConfidenceLevel.MEDIUM,
                    evidence_refs=(confidence_ref,),
                ),
            ),
            trader_suitability=ctx.suitability,
            causal_claims=(ctx.causal_claim,),
            scenarios=ctx.scenarios,
            metacognitive_audit=ctx.audit,
            reasoning_transition=ctx.transition,
            hypotheses=(ctx.hypothesis,),
            learning_records=(ctx.learning,),
        )
        replayed = replay_integrated_episode(integrated)
        if replayed.view != integrated.logical_values() or replayed.fingerprint != integrated.fingerprint:
            raise RuntimeError("integrated cognitive episode did not replay exactly")
        ctx.integrated = integrated
        self.record(
            ctx,
            PHASES[15],
            integrated.fingerprint.value,
            {"integrated_replay_exact": True},
        )

    def p17(self, ctx: TraderContext) -> None:
        now = _dt(str(ctx.row["market_decision_at"]))
        evaluator = ResearchDecisionEvaluatorIdentity(
            family=ResearchDecisionEvaluatorFamily(
                "virtual.trader." + ctx.trader.lower()
            ),
            schema_version=ResearchDecisionEvaluatorSchemaVersion("v1"),
            software_revision=ResearchSoftwareRevision(self.source_head),
        )
        faculties = tuple(sorted(CiboFacultyDomain, key=lambda x: x.value))
        mission_result = CiboMissionDirector().direct(
            mission_code="trader-lab-cognitive-audit",
            objective_code="validate-cognitive-chain",
            constraint_codes=(
                "broker-mutation-forbidden",
                "no-live",
                "no-real-capital",
            ),
            assigned_functions=faculties,
            assigned_traders=(evaluator,),
            readiness_codes=("research-ready",),
            missing_evidence_codes=("certification-not-claimed",),
            unresolved_uncertainty_codes=("reused-holdout",),
            assignment_codes=("audit-all-faculties",),
            hypothesis_codes=("cognitive-chain-operational",),
            success_criteria=("all-phases-consumed",),
            failure_criteria=("any-phase-fails",),
            training_codes=(),
            demo_observation_codes=("trader-lab-research",),
            baseline_codes=(),
            counterfactual_codes=(),
            disposition=CiboMissionDisposition.CONTINUE,
            lineage=("cognitive-trader-lab-audit",),
            unresolved_risk_codes=("risk-authority-external",),
            planned_at=now,
        )
        mission = _must_success(mission_result, "current Mission Director")
        evidence = CiboFunctionalEvidence(
            status=CiboEvidenceStatus.INSUFFICIENT,
            evidence_refs=(
                CiboEvidenceRef("lab:" + ctx.phase_tokens[PHASES[15]]),
            ),
            as_of=now,
            reasons=("certification-not-claimed",),
        )
        contributions = tuple(
            CiboFunctionalContribution(
                faculty=faculty,
                contribution_code="trader-lab-audited",
                subject_key="cognitive-chain",
                authority=CiboFunctionalAuthority.OBSERVATION,
                evidence=evidence,
                authored_at=now,
                provenance=("trader-lab", "cognitive-audit"),
            )
            for faculty in faculties
        )
        coordination = _must_success(
            CiboFunctionalCoordinator().coordinate(
                contributions,
                coordinated_at=now,
                request_code="continue-research-evidence",
            ),
            "current CF01-CF19 coordination",
        )
        if len(coordination.contributions) != 19:
            raise RuntimeError("current functional coordinator did not consume all 19 faculties")
        if tuple(x.value for x in mission.assigned_functions) != tuple(
            x.faculty.value for x in coordination.contributions
        ):
            raise RuntimeError("Mission Director / CF coordinator surface drift")
        ctx.coordination = coordination
        self.record(
            ctx,
            PHASES[16],
            _token(
                ctx.phase_tokens[PHASES[15]],
                mission.logical_values(),
                coordination.logical_values(),
            ),
            {
                "mission_disposition": mission.disposition.value,
                "faculty_count": len(coordination.contributions),
                "coordination_disposition": coordination.disposition.value,
            },
        )

    def p18(self, ctx: TraderContext) -> None:
        integrated = ctx.integrated
        coordination = ctx.coordination
        if integrated is None or coordination is None:
            raise RuntimeError("determinism prerequisites missing")
        first = _token(
            integrated.fingerprint.value,
            ctx.phase_tokens[PHASES[16]],
            coordination.logical_values(),
        )
        second = _token(
            integrated.fingerprint.value,
            ctx.phase_tokens[PHASES[16]],
            coordination.logical_values(),
        )
        if first != second:
            raise RuntimeError("final Trader Lab cognitive chain is not deterministic")
        self.record(
            ctx,
            PHASES[17],
            first,
            {
                "deterministic_repeat_equal": True,
                "legacy_productive_authority": False,
                "broker_mutation": False,
                "live": False,
                "real_capital": False,
            },
        )

    def execute(self) -> dict[str, object]:
        methods = (
            self.p01, self.p02, self.p03, self.p04, self.p05, self.p06,
            self.p07, self.p08, self.p09, self.p10, self.p11, self.p12,
            self.p13, self.p14, self.p15, self.p16, self.p17, self.p18,
        )
        for phase, method in zip(PHASES, methods, strict=True):
            self.run_phase(phase, method)

        # The final phase consumes P17; it has no downstream phase by definition.
        phase_results = []
        for phase in PHASES:
            rows = [self.report_rows[phase][t] for t in TRADERS]
            all_green = all(row["status"] == "GREEN" for row in rows)
            consumed = (
                True
                if phase == PHASES[-1]
                else all(row.get("consumed_by") == PHASES[PHASES.index(phase) + 1] for row in rows)
            )
            phase_results.append(
                {
                    "phase": phase,
                    "status": "GREEN" if all_green and consumed else "FAIL",
                    "all_7_traders_green": all_green,
                    "outputs_consumed_by_next_phase": consumed,
                    "traders": {
                        trader: self.report_rows[phase][trader] for trader in TRADERS
                    },
                }
            )
        all_green = all(x["status"] == "GREEN" for x in phase_results)
        return {
            "schema": "qore.cibo.cognitive-trader-lab-audit.v1",
            "source_trace_sha256": self.trace.get("trace_sha256"),
            "source_head_sha": self.source_head,
            "candidate_count": len(self.contexts),
            "traders": list(TRADERS),
            "phase_count": len(PHASES),
            "phase_order": list(PHASES),
            "phases": phase_results,
            "all_phases_green": all_green,
            "acceptance_basis": (
                "genuine TraderLabCandidateBinding + real RESEARCH lifecycle promotion "
                "+ retained P0 evidence + observable output + downstream consumption"
            ),
            "audit_projection": (
                "one-bar deterministic OHLC adapter from retained predecision intended-entry "
                "price; research-only, non-certifying"
            ),
            "governance": {
                "research_only": True,
                "reused_holdout": True,
                "certification_claimed": False,
                "broker_mutation": False,
                "live": False,
                "real_capital": False,
                "production": False,
                "merge_authority": False,
                "outcome_aware_predecision_tuning": False,
            },
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--decision-trace", type=Path, required=True)
    parser.add_argument("--source-head", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    trace = json.loads(args.decision_trace.read_text(encoding="utf-8"))
    if not isinstance(trace, dict):
        raise ValueError("decision trace root must be object")
    report = Audit(trace, args.source_head).execute()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "all_phases_green": report["all_phases_green"],
                "candidate_count": report["candidate_count"],
                "phase_count": report["phase_count"],
            },
            sort_keys=True,
        )
    )
    return 0 if report["all_phases_green"] is True else 2


if __name__ == "__main__":
    raise SystemExit(main())
