"""Chronological Phase22 V4 counterfactual execution kernel.

This module consumes a predecision/outcome-separated replay plan. It keeps the
historical market clock distinct from the 2026 replay clock, starts with the
frozen USD60 protocol capital, lets frozen CIBO select minimum executable seeds,
then submits those requests to sovereign QORE Risk.

No broker mutation occurs. Provider execution economics are current empirical
counterfactuals applied exactly once at settlement. Floating PnL never funds new
capital. Regime/concentration evidence must be supplied explicitly and source-
bound; the executor does not invent those inputs.
"""
# ruff: noqa: I001, E402

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from pathlib import Path

from qore.infrastructure.account_wide_risk import (
    AccountRiskSnapshot,
    AccountWideRiskEngine,
    RiskDecision,
)
from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CapitalAction,
    CapitalSource,
    CapitalSourceLot,
    CapitalStage,
    CiboCapitalActionPlan,
    CiboCapitalManagementError,
    CiboCapitalState,
    TraderOpportunityEnvelope,
    minimum_seed_volume,
    plan_minimal_seed,
)
from qore.infrastructure.cibo_ce2i_full_surface import (
    AdvancedOpportunityEvidence,
    AdvancedPortfolioEvidence,
)
from qore.infrastructure.cibo_ce2i_t02_calibration_binding import (
    build_t02_structural_leverage_evidence,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_policy_store import (
    VersionedPhase20ForwardPolicyBook,
)
from qore.infrastructure.cibo_ce2i_regime_selector import (
    CiboCapitalRegimeState,
    CorrelationState,
    LiquidityState,
    ProviderCondition,
    VolatilityState,
)
from qore.infrastructure.cibo_ce2i_usd60_six_month_certification import (
    FROZEN_CIBO_USD60_SIX_MONTH_PROTOCOL,
)
from qore.infrastructure.cibo_cma_risk_request import build_cma_risk_request
from qore.infrastructure.cibo_phase22_v4_chronological_replay_plan import (
    Phase22ChronologicalReplayPlan,
    Phase22DecisionEpochPlan,
    Phase22OutcomeEvent,
    Phase22PredecisionCandidate,
)
from qore.infrastructure.cibo_phase22_historical_replay_economics_amendment import (
    Phase22HistoricalReplayEconomicsAmendment,
    Phase22ProviderCalibrationReceipt,
    freeze_phase22_historical_replay_economics_amendment,
)
from qore.infrastructure.cibo_phase22_v4_historical_replay_sealing import (
    Phase22HistoricalReplaySealPair,
    seal_phase22_historical_replay_epoch,
)
from qore.infrastructure.cibo_phase22_historical_replay_settlement import (
    VersionedPhase22HistoricalReplayEvidenceBook,
    build_phase22_historical_replay_outcome,
)
from qore.infrastructure.cibo_phase22_historical_replay_stores import (
    Phase22HistoricalExecutedRiskSeal,
    Phase22HistoricalReplayStoreSet,
    Phase22HistoricalT20ReleaseSeal,
    VersionedPhase22HistoricalExecutedRiskBook,
    VersionedPhase22HistoricalReleaseBook,
    VersionedPhase22HistoricalSettlementBook,
    build_phase22_historical_release_seal,
    build_phase22_historical_risk_seal,
)
from qore.infrastructure.cibo_phase22_v4_source_receipt import (
    load_phase22_v4_source_receipt,
)

V4_SOURCE_RECEIPT = load_phase22_v4_source_receipt(
    Path("docs/research/CIBO-PHASE22-V4-SOURCE-RECEIPT.json")
)
V4_SOURCE_BINDINGS = V4_SOURCE_RECEIPT.bindings
from qore.infrastructure.cibo_phase22_provider_execution_calibration_receipt import (
    PHASE22_PROVIDER_EXECUTION_CALIBRATION_RECEIPT,
)
from qore.infrastructure.market_test_environment import MarketRuntimeEnvironment


class Phase22HistoricalExecutionState(StrEnum):
    RESERVED = "RESERVED"
    OPEN = "OPEN"
    CLOSED = "CLOSED"


@dataclass(frozen=True, slots=True)
class Phase22HistoricalRegimeEvidence:
    decision_epoch_id: str
    observed_at: datetime
    liquidity: LiquidityState
    volatility: VolatilityState
    correlation: CorrelationState
    provider_condition: ProviderCondition
    concentration_limit_by_group: tuple[tuple[str, Decimal], ...]
    evidence_sha256: str
    source_evidence_ids: tuple[str, ...]
    regime_policy_sha256: str
    provider_numeric_freeze_sha256: str
    market_history_sufficient: bool
    counterfactual_provider_model: bool = True
    historical_provider_state_claimed: bool = False
    position_path_adverse: bool = False
    evidence_stale: bool = False
    outcome_fields_used: bool = False
    target_aware: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if not self.decision_epoch_id:
            raise CiboCapitalManagementError(
                "Phase22 regime evidence epoch id required"
            )
        _aware(self.observed_at, "regime observed_at")
        for name, enum_type in (
            ("liquidity", LiquidityState),
            ("volatility", VolatilityState),
            ("correlation", CorrelationState),
            ("provider_condition", ProviderCondition),
        ):
            if type(getattr(self, name)) is not enum_type:
                raise CiboCapitalManagementError(
                    f"Phase22 regime {name} must use canonical enum"
                )
        names = tuple(name for name, _ in self.concentration_limit_by_group)
        if len(names) != len(set(names)):
            raise CiboCapitalManagementError(
                "Phase22 regime concentration groups must be unique"
            )
        for name, limit in self.concentration_limit_by_group:
            if (
                not name
                or not isinstance(limit, Decimal)
                or not limit.is_finite()
                or limit < 0
            ):
                raise CiboCapitalManagementError(
                    "Phase22 regime concentration limit invalid"
                )
        _sha256(self.evidence_sha256, "regime evidence_sha256")
        _sha256(self.regime_policy_sha256, "regime policy SHA")
        _sha256(
            self.provider_numeric_freeze_sha256,
            "provider numeric freeze SHA",
        )
        if (
            not self.source_evidence_ids
            or len(self.source_evidence_ids) != len(set(self.source_evidence_ids))
            or any(not item for item in self.source_evidence_ids)
        ):
            raise CiboCapitalManagementError(
                "Phase22 regime source evidence required"
            )
        for name in (
            "market_history_sufficient",
            "counterfactual_provider_model",
            "historical_provider_state_claimed",
            "position_path_adverse",
            "evidence_stale",
            "outcome_fields_used",
            "target_aware",
            "productive_authority",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(
                    f"Phase22 regime {name} must be bool"
                )
        if not self.market_history_sufficient and not self.evidence_stale:
            raise CiboCapitalManagementError(
                "Phase22 insufficient regime history must fail closed as stale"
            )
        if (
            not self.counterfactual_provider_model
            or self.historical_provider_state_claimed
            or self.outcome_fields_used
            or self.target_aware
            or self.productive_authority
        ):
            raise CiboCapitalManagementError(
                "Phase22 regime evidence governance contamination"
            )


@dataclass(slots=True)
class _HistoricalSolvencyBudget:
    provider_headroom: Decimal
    max_risk_at_any_time: Decimal
    active_mll: Decimal
    hard_breach: bool


@dataclass(slots=True)
class _Exposure:
    candidate: Phase22PredecisionCandidate
    outcome_event: Phase22OutcomeEvent
    pair: Phase22HistoricalReplaySealPair
    risk: Phase22HistoricalExecutedRiskSeal
    authorization_id: str
    authorized_volume: Decimal
    execution_adjustment_usd: Decimal
    decision_provider_cost_proxy_usd: Decimal
    state: Phase22HistoricalExecutionState = Phase22HistoricalExecutionState.RESERVED


@dataclass(frozen=True, slots=True)
class Phase22HistoricalExecutionReport:
    books: Phase22HistoricalReplayStoreSet
    initial_realized_capital_usd: Decimal
    final_realized_capital_usd: Decimal
    peak_realized_capital_usd: Decimal
    max_realized_capital_drawdown_usd: Decimal
    selected_count: int
    allowed_count: int
    reduced_count: int
    rejected_count: int
    settled_count: int
    replay_risk_model_sha256: str
    regime_evidence_sha256s: tuple[str, ...]
    accounting_residual_usd: Decimal
    floating_pnl_used_as_funding: bool = False
    broker_mutation_performed: bool = False
    historical_broker_fills_claimed: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        for name in (
            "initial_realized_capital_usd",
            "peak_realized_capital_usd",
            "max_realized_capital_drawdown_usd",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value < 0
            ):
                raise CiboCapitalManagementError(
                    f"Phase22 execution report {name} invalid"
                )
        if (
            not isinstance(self.final_realized_capital_usd, Decimal)
            or not self.final_realized_capital_usd.is_finite()
        ):
            raise CiboCapitalManagementError(
                "Phase22 execution report final capital invalid"
            )
        for name in (
            "selected_count",
            "allowed_count",
            "reduced_count",
            "rejected_count",
            "settled_count",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 0
            ):
                raise CiboCapitalManagementError(
                    f"Phase22 execution report {name} invalid"
                )
        if self.allowed_count + self.reduced_count + self.rejected_count != (
            self.selected_count
        ):
            raise CiboCapitalManagementError(
                "Phase22 execution report Risk decision count drift"
            )
        if self.settled_count != self.allowed_count + self.reduced_count:
            raise CiboCapitalManagementError(
                "Phase22 execution report settlement count drift"
            )
        _sha256(self.replay_risk_model_sha256, "replay_risk_model_sha256")
        if (
            not self.regime_evidence_sha256s
            or len(self.regime_evidence_sha256s)
            != len(set(self.regime_evidence_sha256s))
        ):
            raise CiboCapitalManagementError(
                "Phase22 execution report regime evidence drift"
            )
        if self.accounting_residual_usd != 0:
            raise CiboCapitalManagementError(
                "Phase22 execution report accounting residual must be zero"
            )
        if (
            self.floating_pnl_used_as_funding
            or self.broker_mutation_performed
            or self.historical_broker_fills_claimed
            or self.productive_authority
        ):
            raise CiboCapitalManagementError(
                "Phase22 execution report governance contamination"
            )


def canonical_phase22_historical_economics_amendment(
) -> Phase22HistoricalReplayEconomicsAmendment:
    source = PHASE22_PROVIDER_EXECUTION_CALIBRATION_RECEIPT
    provider = Phase22ProviderCalibrationReceipt(
        artifact_sha256=source.empirical_artifact_digest,
        git_sha=source.empirical_run_head_sha,
        account_fingerprint_sha256=source.account_fingerprint_sha256,
        observed_at=datetime.fromisoformat(source.empirical_observed_at),
        status="READY",
        required_symbols=source.required_symbols,
        distinct_entry_orders_by_symbol=source.empirical_orders_by_symbol,
        empirical_slippage_calibrated=source.empirical_slippage_calibrated,
        execution_model_ready=source.execution_model_ready,
        execution_population_ready=source.execution_population_ready,
        created_positions_closed=source.created_positions_closed,
        minimum_volume_only=source.minimum_volume_only,
        historical_provider_economics_claimed=False,
        historical_holdout_execution_claimed=False,
        holdout_outcomes_used=False,
        fundednext_touched=False,
        vps_touched=False,
        live_authorized=False,
        real_capital_authorized=False,
        productive_authority=False,
        blockers=(),
    )
    return freeze_phase22_historical_replay_economics_amendment(
        provider_calibration=provider,
        fresh_outcomes_emitted=False,
        holdout_outcomes_inspected=False,
    )


def phase22_historical_risk_model_sha256() -> str:
    return _sha(
        {
            "schema": "qore.cibo.phase22.historical-solvency-risk.v1",
            "initial_realized_capital_usd": "60",
            "provider_rule": "COUNTERFACTUAL_SOLVENCY_ONLY",
            "provider_headroom": "CURRENT_REALIZED_CAPITAL",
            "max_risk_at_any_time": "CURRENT_REALIZED_CAPITAL",
            "active_mll": "ZERO_SOLVENCY_FLOOR",
            "qore_authorizable_headroom": "CURRENT_REALIZED_CAPITAL",
            "free_margin": "REALIZED_CAPITAL_MINUS_OPEN_MARGIN",
            "open_risk": "AUTHORIZED_STRUCTURAL_STOP_RISK",
            "pending_risk": "QORE_RISK_RESERVATION_ONLY",
            "floating_pnl_funding": False,
            "historical_provider_rule_claimed": False,
            "broker_mutation": False,
        }
    )


def execute_phase22_chronological_replay(
    *,
    plan: Phase22ChronologicalReplayPlan,
    regime_evidence: tuple[Phase22HistoricalRegimeEvidence, ...],
    replay_started_at: datetime,
    amendment: Phase22HistoricalReplayEconomicsAmendment | None = None,
    lab_allow_nonpositive_expectation: bool = False,
    lab_cibo_free_tool_choice: bool = False,
    lab_enable_t02_released_capacity: bool = False,
    lab_t02_research_admission_filter: (
        Callable[[TraderOpportunityEnvelope, datetime], bool] | None
    ) = None,
) -> Phase22HistoricalExecutionReport:
    """Run the frozen USD60 policy/Risk/settlement path chronologically."""

    if not isinstance(plan, Phase22ChronologicalReplayPlan):
        raise CiboCapitalManagementError(
            "Phase22 execution requires canonical chronological plan"
        )
    _aware(replay_started_at, "replay_started_at")
    if type(lab_allow_nonpositive_expectation) is not bool:
        raise CiboCapitalManagementError(
            "lab_allow_nonpositive_expectation must be bool"
        )
    if type(lab_cibo_free_tool_choice) is not bool:
        raise CiboCapitalManagementError(
            "lab_cibo_free_tool_choice must be bool"
        )
    if type(lab_enable_t02_released_capacity) is not bool:
        raise CiboCapitalManagementError(
            "lab_enable_t02_released_capacity must be bool"
        )
    if lab_t02_research_admission_filter is not None:
        if not lab_enable_t02_released_capacity:
            raise CiboCapitalManagementError(
                "T02 research admission filter requires T02 lab capacity mode"
            )
        if not callable(lab_t02_research_admission_filter):
            raise CiboCapitalManagementError(
                "T02 research admission filter must be callable"
            )
    if amendment is None:
        amendment = canonical_phase22_historical_economics_amendment()
    if not isinstance(amendment, Phase22HistoricalReplayEconomicsAmendment):
        raise CiboCapitalManagementError(
            "Phase22 execution requires canonical economics amendment"
        )

    evidence_by_epoch = {item.decision_epoch_id: item for item in regime_evidence}
    if (
        len(evidence_by_epoch) != len(regime_evidence)
        or set(evidence_by_epoch)
        != {item.decision_epoch_id for item in plan.epochs}
    ):
        raise CiboCapitalManagementError(
            "Phase22 execution regime evidence must cover exact epoch set"
        )

    outcome_by_signal = {
        item.signal_fingerprint: item for item in plan.outcome_events
    }
    initial = FROZEN_CIBO_USD60_SIX_MONTH_PROTOCOL.initial_capital_usd
    realized = initial
    peak = initial
    max_drawdown = Decimal(0)
    risk_engine = AccountWideRiskEngine()
    account_identity = CiboAccountCapitalIdentity(
        provider_key="ctrader-demo",
        account_ref="phase22-v4-counterfactual-usd60",
        environment=MarketRuntimeEnvironment.DEMO,
    )
    risk_model_sha = phase22_historical_risk_model_sha256()

    pairs: list[Phase22HistoricalReplaySealPair] = []
    risk_seals: list[Phase22HistoricalExecutedRiskSeal] = []
    outcomes = []
    releases: list[Phase22HistoricalT20ReleaseSeal] = []
    exposures: dict[str, _Exposure] = {}
    selected_count = 0
    allowed_count = 0
    reduced_count = 0
    rejected_count = 0
    released_risk_capacity = Decimal(0)

    def _advance(clock: datetime) -> None:
        nonlocal realized, peak, max_drawdown, released_risk_capacity
        while True:
            pending_events: list[tuple[datetime, str, str]] = []
            for signal, exposure in exposures.items():
                if (
                    exposure.state is Phase22HistoricalExecutionState.RESERVED
                    and exposure.candidate.entry_at <= clock
                ):
                    pending_events.append(
                        (exposure.candidate.entry_at, "ENTRY", signal)
                    )
                if (
                    exposure.state is not Phase22HistoricalExecutionState.CLOSED
                    and exposure.outcome_event.exit_at <= clock
                ):
                    pending_events.append(
                        (exposure.outcome_event.exit_at, "EXIT", signal)
                    )
            if not pending_events:
                return
            event_at, kind, signal = min(
                pending_events,
                key=lambda item: (
                    item[0],
                    0 if item[1] == "ENTRY" else 1,
                    item[2],
                ),
            )
            exposure = exposures[signal]
            if kind == "ENTRY":
                if exposure.state is not Phase22HistoricalExecutionState.RESERVED:
                    continue
                risk_engine.record_full_fill(exposure.authorization_id)
                risk_engine.reconcile_fill(exposure.authorization_id)
                exposure.state = Phase22HistoricalExecutionState.OPEN
                continue

            if exposure.state is Phase22HistoricalExecutionState.RESERVED:
                risk_engine.record_full_fill(exposure.authorization_id)
                risk_engine.reconcile_fill(exposure.authorization_id)
                exposure.state = Phase22HistoricalExecutionState.OPEN
            if exposure.state is not Phase22HistoricalExecutionState.OPEN:
                continue
            event = exposure.outcome_event
            settlement = build_phase22_historical_replay_outcome(
                amendment=amendment,
                decision=exposure.pair.decision,
                signal_fingerprint=signal,
                trader_id=event.trader_id,
                qore_symbol=event.qore_symbol,
                observed_at=event.exit_at,
                gross_structural_outcome_r=event.gross_structural_outcome_r,
                executed_initial_stop_risk_usd=(
                    exposure.risk.authorized_stop_risk_usd
                ),
                provider_execution_adjustment_usd=(
                    exposure.execution_adjustment_usd
                ),
                decision_provider_cost_proxy_usd=(
                    exposure.decision_provider_cost_proxy_usd
                ),
                capital_deployed_at=exposure.candidate.entry_at,
                capital_released_at=event.exit_at,
            )
            release = build_phase22_historical_release_seal(
                risk=exposure.risk,
                settlement=settlement,
            )
            outcomes.append(settlement)
            releases.append(release)
            if lab_enable_t02_released_capacity:
                released_risk_capacity += release.released_stop_risk_usd
            realized += settlement.realized_net_pnl_usd
            peak = max(peak, realized)
            max_drawdown = max(max_drawdown, peak - realized)
            exposure.state = Phase22HistoricalExecutionState.CLOSED

    for index, epoch in enumerate(plan.epochs):
        _advance(epoch.market_decision_at)
        evidence = evidence_by_epoch[epoch.decision_epoch_id]
        if evidence.observed_at > epoch.market_decision_at:
            raise CiboCapitalManagementError(
                "Phase22 execution regime evidence postdates decision"
            )
        if evidence.concentration_limit_by_group:
            raise CiboCapitalManagementError(
                "Phase22 historical execution forbids invented concentration limits"
            )

        snapshot = _snapshot(
            realized_capital_usd=realized,
            exposures=tuple(exposures.values()),
            reconciled_at=epoch.market_decision_at,
        )
        constraints = risk_engine.capital_constraint_envelope(
            snapshot,
            now=epoch.market_decision_at,
        )
        regime = _regime_state(
            evidence=evidence,
            epoch=epoch,
            realized_capital_usd=realized,
            peak_realized_capital_usd=peak,
            open_risk_usd=snapshot.open_stop_worst_case_loss,
            open_margin_usd=snapshot.margin_used,
        )
        advanced_evidence: AdvancedPortfolioEvidence | None = None
        if lab_enable_t02_released_capacity:
            remaining_released = released_risk_capacity
            evidence_rows: list[AdvancedOpportunityEvidence] = []
            for candidate in sorted(
                epoch.candidates,
                key=lambda item: (
                    item.trader_id,
                    item.qore_symbol,
                    item.signal_fingerprint,
                ),
            ):
                opportunity = (
                    candidate.projection.candidate.capital_input.opportunity
                )
                current_volume = minimum_seed_volume(opportunity)
                incremental_risk = (
                    opportunity.volume_step
                    * opportunity.stop_loss_per_volume
                )
                if incremental_risk <= 0 or remaining_released < incremental_risk:
                    continue
                structural = build_t02_structural_leverage_evidence(
                    opportunity=opportunity,
                    observed_at=epoch.market_decision_at,
                    released_risk_capacity_usd=incremental_risk,
                )
                if structural is None:
                    continue
                if (
                    lab_t02_research_admission_filter is not None
                    and not lab_t02_research_admission_filter(
                        opportunity,
                        epoch.market_decision_at,
                    )
                ):
                    continue
                evidence_rows.append(
                    AdvancedOpportunityEvidence(
                        signal_fingerprint=opportunity.signal_fingerprint,
                        current_volume=current_volume,
                        maximum_additional_volume=opportunity.volume_step,
                        structural_leverage=structural,
                    )
                )
                remaining_released -= incremental_risk
            advanced_evidence = AdvancedPortfolioEvidence(
                opportunities=tuple(evidence_rows)
            )

        sealed_at = replay_started_at + timedelta(microseconds=index + 1)
        pair = seal_phase22_historical_replay_epoch(
            decision_epoch_id=epoch.decision_epoch_id,
            market_decision_at=epoch.market_decision_at,
            replay_sealed_at=sealed_at,
            seal_deadline_at=sealed_at + timedelta(seconds=2),
            account_identity=account_identity,
            candidates=tuple(
                item.projection.candidate for item in epoch.candidates
            ),
            regime_state=regime,
            hard_risk_headroom_usd=constraints.hard_risk_headroom_usd,
            margin_headroom_usd=constraints.margin_headroom_usd,
            concentration_limit_by_group=evidence.concentration_limit_by_group,
            current_step=index,
            advanced_evidence=advanced_evidence,
            lab_allow_nonpositive_expectation=(
                lab_allow_nonpositive_expectation
            ),
            lab_cibo_free_tool_choice=lab_cibo_free_tool_choice,
        )
        pairs.append(pair)

        by_signal = {
            item.signal_fingerprint: item for item in epoch.candidates
        }
        execution_signals = tuple(
            pair.policy.selected_signal_fingerprints
        )
        for signal in execution_signals:
            selected_count += 1
            candidate = by_signal[signal]
            snapshot = _snapshot(
                realized_capital_usd=realized,
                exposures=tuple(exposures.values()),
                reconciled_at=epoch.market_decision_at,
            )
            constraints = risk_engine.capital_constraint_envelope(
                snapshot,
                now=epoch.market_decision_at,
            )
            if realized <= 0:
                raise CiboCapitalManagementError(
                    "Phase22 policy selected capital after realized capital exhaustion"
                )
            capital_state = CiboCapitalState(
                assigned_capital_usd=realized,
                hard_risk_headroom_usd=constraints.hard_risk_headroom_usd,
                margin_headroom_usd=constraints.margin_headroom_usd,
                base_capital_at_risk_usd=min(
                    initial,
                    max(realized, Decimal(0)),
                ),
                realized_net_profit_usd=max(
                    Decimal(0),
                    realized - initial,
                ),
                protected_open_economic_floor_usd=Decimal(0),
                proven_self_financing_capacity_usd=max(
                    Decimal(0),
                    realized - initial,
                ),
                reserved_expansion_risk_usd=Decimal(0),
                cost_reserve_usd=Decimal(0),
            )
            opportunity = candidate.projection.candidate.capital_input.opportunity
            baseline_plan = plan_minimal_seed(opportunity, capital_state)
            plan_row = baseline_plan
            effective_candidate = next(
                item
                for item in pair.policy_record.advanced_economic_application.candidates
                if item.signal_fingerprint == signal
            )
            if (
                lab_enable_t02_released_capacity
                and baseline_plan.volume > 0
                and effective_candidate.stop_risk_usd
                > baseline_plan.stop_risk_usd
            ):
                incremental_risk = (
                    effective_candidate.stop_risk_usd
                    - baseline_plan.stop_risk_usd
                )
                if incremental_risk > released_risk_capacity:
                    raise CiboCapitalManagementError(
                        "T02 requested released risk capacity beyond causal pool"
                    )
                t02_decisions = tuple(
                    decision
                    for assessment in (
                        pair.policy_record.full_surface.opportunity_assessments
                    )
                    if assessment.signal_fingerprint == signal
                    for decision in assessment.decisions
                    if (
                        decision.tool_code == "T02"
                        and decision.target_stop_risk_usd is not None
                    )
                )
                if len(t02_decisions) != 1:
                    raise CiboCapitalManagementError(
                        "T02 effective candidate requires one applied volume decision"
                    )
                t02_decision = t02_decisions[0]
                volume = t02_decision.approved_volume
                if volume <= baseline_plan.volume:
                    raise CiboCapitalManagementError(
                        "T02 approved volume must exceed baseline seed"
                    )
                if volume > opportunity.maximum_volume:
                    raise CiboCapitalManagementError(
                        "T02 effective volume exceeds provider maximum"
                    )
                step_ratio = volume / opportunity.volume_step
                if step_ratio != step_ratio.to_integral_value():
                    raise CiboCapitalManagementError(
                        "T02 approved volume is not provider-step aligned"
                    )
                exact_stop_risk = (
                    opportunity.stop_loss_per_volume * volume
                )
                if exact_stop_risk != effective_candidate.stop_risk_usd:
                    raise CiboCapitalManagementError(
                        "T02 approved volume/stop-risk identity drift"
                    )
                policy_ratio = (
                    effective_candidate.stop_risk_usd
                    / baseline_plan.stop_risk_usd
                )
                policy_margin = baseline_plan.margin_usd * policy_ratio
                if policy_margin != effective_candidate.margin_usd:
                    raise CiboCapitalManagementError(
                        "T02 policy margin scaling identity drift"
                    )
                margin = volume * opportunity.margin_per_volume
                plan_row = CiboCapitalActionPlan(
                    trader_id=opportunity.trader_id,
                    qore_symbol=opportunity.qore_symbol,
                    stage=CapitalStage.CAPITALIZE,
                    action=CapitalAction.OPEN_CAPABILITY_MAX,
                    volume=volume,
                    stop_risk_usd=effective_candidate.stop_risk_usd,
                    margin_usd=margin,
                    capital_source=None,
                    capital_source_amount_usd=effective_candidate.stop_risk_usd,
                    capital_source_lots=(
                        CapitalSourceLot(
                            source=CapitalSource.ORIGINAL_BASE_CAPITAL,
                            amount_usd=baseline_plan.stop_risk_usd,
                            source_id=f"phase22-base:{signal}",
                        ),
                        CapitalSourceLot(
                            source=CapitalSource.RELEASED_RISK_CAPACITY,
                            amount_usd=incremental_risk,
                            source_id=f"phase22-t20-released-risk:{signal}",
                        ),
                    ),
                    reason=(
                        "T02 one-step structural leverage consumes only causally "
                        "prior T20 released risk capacity; QORE Risk remains sovereign"
                    ),
                )
            if plan_row.volume <= 0:
                raise CiboCapitalManagementError(
                    "Phase22 selected signal cannot produce minimum seed"
                )
            request = build_cma_risk_request(
                request_id=f"phase22:{epoch.decision_epoch_id}:{signal}",
                opportunity=opportunity,
                plan=plan_row,
                requested_at=epoch.market_decision_at,
                expires_at=max(
                    candidate.entry_at,
                    epoch.market_decision_at + timedelta(seconds=1),
                ),
                capital_source_id=f"phase22-usd60-base:{signal}",
            )
            authorization = risk_engine.authorize(
                request,
                snapshot,
                now=epoch.market_decision_at,
            )
            if authorization.decision is RiskDecision.ALLOW:
                allowed_count += 1
            elif authorization.decision is RiskDecision.REDUCE:
                reduced_count += 1
            else:
                rejected_count += 1
            if (
                lab_enable_t02_released_capacity
                and authorization.decision is not RiskDecision.REJECT
                and baseline_plan.volume > 0
            ):
                consumed_released = max(
                    Decimal(0),
                    authorization.monetary_stop_loss
                    - baseline_plan.stop_risk_usd,
                )
                if consumed_released > released_risk_capacity:
                    raise CiboCapitalManagementError(
                        "T02 authorized released risk exceeds causal pool"
                    )
                released_risk_capacity -= consumed_released

            risk = build_phase22_historical_risk_seal(
                decision=pair.decision,
                signal_fingerprint=signal,
                trader_id=candidate.trader_id,
                qore_symbol=candidate.qore_symbol,
                decided_at=epoch.market_decision_at,
                risk_decision=authorization.decision,
                requested_stop_risk_usd=plan_row.stop_risk_usd,
                authorized_stop_risk_usd=authorization.monetary_stop_loss,
                authorized_margin_usd=authorization.margin_reserved,
                risk_model_sha256=risk_model_sha,
            )
            risk_seals.append(risk)
            if authorization.decision is RiskDecision.REJECT:
                continue

            envelope = candidate.projection.provider_envelope
            event = outcome_by_signal[signal]
            exposures[signal] = _Exposure(
                candidate=candidate,
                outcome_event=event,
                pair=pair,
                risk=risk,
                authorization_id=authorization.authorization_id,
                authorized_volume=authorization.authorized_volume,
                execution_adjustment_usd=(
                    envelope.execution_cost_per_volume_usd
                    * authorization.authorized_volume
                ),
                decision_provider_cost_proxy_usd=(
                    envelope.minimum_execution_cost_usd
                ),
            )

    if exposures:
        _advance(max(item.outcome_event.exit_at for item in exposures.values()))

    unresolved = tuple(
        signal
        for signal, exposure in exposures.items()
        if exposure.state is not Phase22HistoricalExecutionState.CLOSED
    )
    if unresolved:
        raise CiboCapitalManagementError(
            "Phase22 chronological execution left unsettled exposure"
        )

    decisions = tuple(item.decision for item in pairs)
    policies = tuple(item.policy for item in pairs)
    evidence_book = VersionedPhase22HistoricalReplayEvidenceBook(
        generation=1,
        amendment_sha256=amendment.fingerprint(),
        decisions=decisions,
        outcomes=tuple(outcomes),
        source_receipt_sha256=V4_SOURCE_RECEIPT.fingerprint(),
        source_collector_git_shas=(V4_SOURCE_RECEIPT.corpus_git_sha,),
    )
    books = Phase22HistoricalReplayStoreSet(
        holdout_evidence=evidence_book,
        holdout_policy=VersionedPhase20ForwardPolicyBook(
            generation=1,
            decisions=policies,
        ),
        executed_risk=VersionedPhase22HistoricalExecutedRiskBook(
            generation=1,
            executed_risk=tuple(risk_seals),
        ),
        cma_settlement=VersionedPhase22HistoricalSettlementBook(
            generation=1,
            settlements=tuple(outcomes),
        ),
        t20_release=VersionedPhase22HistoricalReleaseBook(
            generation=1,
            release_chain=tuple(releases),
        ),
    )
    expected_final = initial
    for item in outcomes:
        expected_final += item.realized_net_pnl_usd
    residual = realized - expected_final
    return Phase22HistoricalExecutionReport(
        books=books,
        initial_realized_capital_usd=initial,
        final_realized_capital_usd=realized,
        peak_realized_capital_usd=peak,
        max_realized_capital_drawdown_usd=max_drawdown,
        selected_count=selected_count,
        allowed_count=allowed_count,
        reduced_count=reduced_count,
        rejected_count=rejected_count,
        settled_count=len(outcomes),
        replay_risk_model_sha256=risk_model_sha,
        regime_evidence_sha256s=tuple(
            evidence_by_epoch[item.decision_epoch_id].evidence_sha256
            for item in plan.epochs
        ),
        accounting_residual_usd=residual,
    )


def _snapshot(
    *,
    realized_capital_usd: Decimal,
    exposures: tuple[_Exposure, ...],
    reconciled_at: datetime,
) -> AccountRiskSnapshot:
    equity = max(Decimal(0), realized_capital_usd)
    open_rows = tuple(
        item
        for item in exposures
        if item.state is Phase22HistoricalExecutionState.OPEN
    )
    open_risk = sum(
        (item.risk.authorized_stop_risk_usd for item in open_rows),
        Decimal(0),
    )
    open_margin = sum(
        (item.risk.authorized_margin_usd for item in open_rows),
        Decimal(0),
    )
    budget = _HistoricalSolvencyBudget(
        provider_headroom=equity,
        max_risk_at_any_time=equity,
        active_mll=Decimal(0),
        hard_breach=equity <= 0,
    )
    return AccountRiskSnapshot(
        account_binding_id="phase22-v4-counterfactual-usd60",
        equity=equity,
        margin_used=open_margin,
        free_margin=max(Decimal(0), equity - open_margin),
        open_stop_worst_case_loss=open_risk,
        open_floating_loss=Decimal(0),
        pending_broker_worst_case_loss=Decimal(0),
        qore_authorizable_headroom=equity,
        provider_budget=budget,
        reconciled_at=reconciled_at,
    )


def _regime_state(
    *,
    evidence: Phase22HistoricalRegimeEvidence,
    epoch: Phase22DecisionEpochPlan,
    realized_capital_usd: Decimal,
    peak_realized_capital_usd: Decimal,
    open_risk_usd: Decimal,
    open_margin_usd: Decimal,
) -> CiboCapitalRegimeState:
    capital = max(Decimal(0), realized_capital_usd)
    if capital > 0:
        risk_utilization = min(Decimal(1), open_risk_usd / capital)
        margin_utilization = min(Decimal(1), open_margin_usd / capital)
    else:
        risk_utilization = Decimal(1)
        margin_utilization = Decimal(1)
    drawdown = max(
        Decimal(0),
        peak_realized_capital_usd - realized_capital_usd,
    )
    drawdown_utilization = (
        Decimal(0)
        if peak_realized_capital_usd <= 0
        else min(Decimal(1), drawdown / peak_realized_capital_usd)
    )
    return CiboCapitalRegimeState(
        liquidity=evidence.liquidity,
        volatility=evidence.volatility,
        correlation=evidence.correlation,
        provider_condition=evidence.provider_condition,
        risk_utilization=risk_utilization,
        margin_utilization=margin_utilization,
        drawdown_utilization=drawdown_utilization,
        opportunity_count=len(epoch.candidates),
        position_path_adverse=evidence.position_path_adverse,
        evidence_stale=evidence.evidence_stale,
    )


def _aware(value: datetime, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise CiboCapitalManagementError(
            f"Phase22 execution {name} must be timezone-aware"
        )


def _sha(payload: dict[str, object]) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _sha256(value: str, name: str) -> None:
    if (
        not isinstance(value, str)
        or not value.startswith("sha256:")
        or len(value) != 71
        or any(char not in "0123456789abcdef" for char in value[7:])
    ):
        raise CiboCapitalManagementError(
            f"Phase22 execution {name} invalid"
        )
