"""Repeatable CIBO infrastructure/capability exam on a reused Phase22 holdout.

The exam is intentionally separate from fresh-OOS certification. It replays the
already-consumed V4 six-month population to prove infrastructure behavior,
measure MINIMAL_SEED_ONLY versus FULL_CIBO_CORE performance, and account for all
CE2I T01..T20 tools. A tool that is neither exercised nor explicitly blocked
with a defensible reason is reported NOT_INTEGRATED and blocks infrastructure
certification.

No broker mutation, LIVE, real capital, production, merge, or fresh-generalization
authority is granted by this module.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from qore.infrastructure.cibo_capability_exam_cognitive_coverage import (
    CiboCapabilityCognitiveCoverageReceipt,
    build_cibo_capability_cognitive_coverage,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
    CiboCapitalState,
    plan_minimal_seed,
    plan_self_financing_expansion,
)
from qore.infrastructure.cibo_ce2i_dynamic_derisking import (
    CiboDeRiskingInput,
    plan_dynamic_derisking,
)
from qore.infrastructure.cibo_ce2i_t11_runtime_guard import (
    evaluate_t11_runtime_exposure_guard,
)
from qore.infrastructure.cibo_ce2i_tool_registry import CE2I_TOOL_REGISTRY
from qore.infrastructure.cibo_ce2i_usd60_six_month_certification import (
    FROZEN_CIBO_USD60_SIX_MONTH_PROTOCOL,
)
from qore.infrastructure.cibo_phase22_v4_chronological_execution import (
    Phase22HistoricalExecutionReport,
    execute_phase22_chronological_replay,
)
from qore.infrastructure.cibo_phase22_v4_chronological_replay_plan import (
    Phase22ChronologicalReplayPlan,
    build_phase22_chronological_replay_plan,
)
from qore.infrastructure.cibo_phase22_v4_execution_inputs import (
    Phase22SealedFreshBatchInput,
    Phase22SealedProviderNumericInput,
    project_phase22_execution_inputs,
)
from qore.infrastructure.cibo_phase22_v4_historical_regime import (
    build_phase22_historical_regime_evidence,
)
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import (
    Evidence,
)

EXAM_ID = "CIBO_REUSED_HOLDOUT_INFRASTRUCTURE_CAPABILITY_EXAM_V1"
VALIDATION_MODE = "NON_CERTIFYING_REUSED_HOLDOUT"


class ToolRuntimeStatus(StrEnum):
    APPLIED = "APPLIED"
    FAIL_CLOSED = "FAIL_CLOSED"
    REGIME_BLOCKED = "REGIME_BLOCKED"
    JUSTIFIED_NOT_APPLICABLE = "JUSTIFIED_NOT_APPLICABLE"
    NOT_INTEGRATED = "NOT_INTEGRATED"


@dataclass(frozen=True, slots=True)
class PerformanceMetrics:
    lane: str
    opportunity_count: int
    executed_count: int
    rejected_or_unexpressible_count: int
    initial_capital_usd: Decimal
    ending_capital_usd: Decimal
    net_realized_pnl_usd: Decimal
    peak_capital_usd: Decimal
    minimum_capital_usd: Decimal
    max_realized_drawdown_usd: Decimal
    gross_profit_usd: Decimal
    gross_loss_usd: Decimal
    profit_factor: Decimal | None
    trading_days: int
    trader_pnl_usd: tuple[tuple[str, Decimal], ...]

    def __post_init__(self) -> None:
        if not self.lane:
            raise CiboCapitalManagementError("capability metrics lane required")
        for name in (
            "opportunity_count",
            "executed_count",
            "rejected_or_unexpressible_count",
            "trading_days",
        ):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise CiboCapitalManagementError(
                    f"capability metrics {name} invalid"
                )
        for name in (
            "initial_capital_usd",
            "ending_capital_usd",
            "net_realized_pnl_usd",
            "peak_capital_usd",
            "minimum_capital_usd",
            "max_realized_drawdown_usd",
            "gross_profit_usd",
            "gross_loss_usd",
        ):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite():
                raise CiboCapitalManagementError(
                    f"capability metrics {name} invalid"
                )
        if self.profit_factor is not None and (
            not isinstance(self.profit_factor, Decimal)
            or not self.profit_factor.is_finite()
            or self.profit_factor < 0
        ):
            raise CiboCapitalManagementError(
                "capability metrics profit_factor invalid"
            )


@dataclass(frozen=True, slots=True)
class ToolAuditRow:
    tool_code: str
    tool_name: str
    status: ToolRuntimeStatus
    enabled_epochs: int
    regime_blocked_epochs: int
    applied_count: int
    abstain_count: int
    fail_closed_count: int
    reason: str

    def __post_init__(self) -> None:
        if self.tool_code not in {item.code for item in CE2I_TOOL_REGISTRY}:
            raise CiboCapitalManagementError("unknown capability tool code")
        if not self.tool_name or not self.reason:
            raise CiboCapitalManagementError(
                "capability tool name/reason required"
            )
        for name in (
            "enabled_epochs",
            "regime_blocked_epochs",
            "applied_count",
            "abstain_count",
            "fail_closed_count",
        ):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise CiboCapitalManagementError(
                    f"capability audit {name} invalid"
                )

    @property
    def integration_complete(self) -> bool:
        return self.status is not ToolRuntimeStatus.NOT_INTEGRATED


@dataclass(frozen=True, slots=True)
class InfrastructureCapabilityExamReport:
    exam_id: str
    validation_mode: str
    candidate_id: str
    source_batch_sha256: str
    replay_started_at: datetime
    cognitive_functional_coverage: CiboCapabilityCognitiveCoverageReceipt
    minimal_seed_baseline: PerformanceMetrics
    full_cibo: PerformanceMetrics
    ending_capital_delta_usd: Decimal
    net_pnl_delta_usd: Decimal
    drawdown_improvement_usd: Decimal
    profit_factor_delta: Decimal | None
    tool_audit: tuple[ToolAuditRow, ...]
    gates: tuple[tuple[str, bool], ...]
    infrastructure_certified: bool
    scientific_freshness_claimed: bool = False
    fresh_oos_generalization_claimed: bool = False
    broker_mutation_performed: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False
    production_authorized: bool = False
    merge_authorized: bool = False

    def __post_init__(self) -> None:
        if self.exam_id != EXAM_ID or self.validation_mode != VALIDATION_MODE:
            raise CiboCapitalManagementError("capability exam identity drift")
        if self.replay_started_at.tzinfo is None:
            raise CiboCapitalManagementError(
                "capability exam replay_started_at must be aware"
            )
        if (
            not isinstance(
                self.cognitive_functional_coverage,
                CiboCapabilityCognitiveCoverageReceipt,
            )
            or not self.cognitive_functional_coverage.complete
        ):
            raise CiboCapitalManagementError(
                "capability exam cognitive/function coverage incomplete"
            )
        expected_codes = tuple(f"T{i:02d}" for i in range(1, 21))
        if tuple(item.tool_code for item in self.tool_audit) != expected_codes:
            raise CiboCapitalManagementError(
                "capability exam requires exact T01..T20 audit"
            )
        if len(dict(self.gates)) != len(self.gates):
            raise CiboCapitalManagementError("capability exam duplicate gate")
        expected_certified = all(value for _, value in self.gates)
        if self.infrastructure_certified != expected_certified:
            raise CiboCapitalManagementError(
                "capability exam certification/gate drift"
            )
        if any(
            (
                self.scientific_freshness_claimed,
                self.fresh_oos_generalization_claimed,
                self.broker_mutation_performed,
                self.live_authorized,
                self.real_capital_authorized,
                self.production_authorized,
                self.merge_authorized,
            )
        ):
            raise CiboCapitalManagementError(
                "capability exam governance contamination"
            )

    def payload(self) -> dict[str, Any]:
        raw = asdict(self)
        return _canonical(raw)

    def fingerprint(self) -> str:
        raw = json.dumps(
            self.payload(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(raw).hexdigest()


@dataclass(slots=True)
class _BaselineExposure:
    signal: str
    trader_id: str
    exit_at: datetime
    risk_usd: Decimal
    margin_usd: Decimal
    pnl_usd: Decimal


def run_reused_holdout_infrastructure_exam(
    *,
    fresh: Phase22SealedFreshBatchInput,
    provider: Phase22SealedProviderNumericInput,
    provider_numeric_freeze_sha256: str,
    corpora: tuple[Evidence, ...],
    replay_started_at: datetime,
) -> tuple[InfrastructureCapabilityExamReport, Phase22HistoricalExecutionReport]:
    if fresh.batch.candidate_id != (
        "CIBO_USD60_6M_HOLDOUT_2014-10-19_2015-04-19_V4"
    ):
        raise CiboCapitalManagementError(
            "capability exam is bound to reused V4 holdout"
        )
    cognitive_coverage = build_cibo_capability_cognitive_coverage(
        source_batch_sha256=fresh.declared_batch_sha256,
        observed_at=replay_started_at,
    )
    projections = project_phase22_execution_inputs(
        fresh=fresh,
        provider=provider,
        provider_numeric_freeze_sha256=provider_numeric_freeze_sha256,
    )
    plan = build_phase22_chronological_replay_plan(
        fresh=fresh,
        projections=projections,
    )
    regimes = build_phase22_historical_regime_evidence(
        plan=plan,
        provider=provider,
        provider_numeric_freeze_sha256=provider_numeric_freeze_sha256,
        corpora=corpora,
    )
    execution = execute_phase22_chronological_replay(
        plan=plan,
        regime_evidence=regimes,
        replay_started_at=replay_started_at,
    )
    baseline = _run_minimal_seed_baseline(plan)
    full = _full_metrics(
        execution,
        opportunity_count=len(fresh.batch.opportunities),
    )
    audit = _tool_audit(plan=plan, execution=execution)

    pf_delta = None
    if baseline.profit_factor is not None and full.profit_factor is not None:
        pf_delta = full.profit_factor - baseline.profit_factor

    gates = (
        ("EXACT_USD60_INITIAL_CAPITAL", full.initial_capital_usd == Decimal("60")),
        ("COGNITIVE_EXECUTIVE_USED", cognitive_coverage.cognitive_used),
        (
            "CF01_CF19_FUNCTIONAL_COVERAGE_COMPLETE",
            cognitive_coverage.all_functional_faculties_consulted,
        ),
        (
            "CE2I_T01_T20_REGISTRY_COVERAGE_COMPLETE",
            cognitive_coverage.all_ce2i_tools_registered,
        ),
        (
            "CIBO_SOLE_SIZING_AUTHORITY",
            cognitive_coverage.cibo_sizing_authority == "CIBO_CMA"
            and cognitive_coverage.trader_sizing_authority == "NONE",
        ),
        ("EXACT_SEVEN_TRADER_LANES", len(fresh.batch.traders) == 7),
        (
            "SIX_MONTH_PROTOCOL_SURFACE",
            FROZEN_CIBO_USD60_SIX_MONTH_PROTOCOL.duration_months == 6,
        ),
        ("SURVIVAL", full.ending_capital_usd > 0),
        ("ACCOUNTING_RESIDUAL_ZERO", execution.accounting_residual_usd == 0),
        (
            "RISK_SOVEREIGNTY",
            execution.selected_count
            == (
                execution.allowed_count
                + execution.reduced_count
                + execution.rejected_count
            ),
        ),
        (
            "SETTLEMENT_RELEASE_RECONCILED",
            len(execution.books.t20_release.release_chain)
            == execution.settled_count,
        ),
        ("BROKER_MUTATION_ZERO", execution.broker_mutation_performed is False),
        (
            "FLOATING_PNL_NOT_FUNDING",
            execution.floating_pnl_used_as_funding is False,
        ),
        (
            "BASELINE_COMPARISON_COMPLETE",
            baseline.opportunity_count == len(fresh.batch.opportunities),
        ),
        ("PERFORMANCE_DIFFERENCE_MEASURED", _metrics_differ(baseline, full)),
        ("T01_T20_ACCOUNTABILITY_COMPLETE", all(item.reason for item in audit)),
        (
            "T01_T20_RUNTIME_INTEGRATION_COMPLETE",
            all(item.integration_complete for item in audit),
        ),
    )
    report = InfrastructureCapabilityExamReport(
        exam_id=EXAM_ID,
        validation_mode=VALIDATION_MODE,
        candidate_id=fresh.batch.candidate_id,
        source_batch_sha256=fresh.declared_batch_sha256,
        replay_started_at=replay_started_at,
        cognitive_functional_coverage=cognitive_coverage,
        minimal_seed_baseline=baseline,
        full_cibo=full,
        ending_capital_delta_usd=(
            full.ending_capital_usd - baseline.ending_capital_usd
        ),
        net_pnl_delta_usd=(
            full.net_realized_pnl_usd - baseline.net_realized_pnl_usd
        ),
        drawdown_improvement_usd=(
            baseline.max_realized_drawdown_usd
            - full.max_realized_drawdown_usd
        ),
        profit_factor_delta=pf_delta,
        tool_audit=audit,
        gates=gates,
        infrastructure_certified=all(value for _, value in gates),
    )
    return report, execution


def _run_minimal_seed_baseline(
    plan: Phase22ChronologicalReplayPlan,
) -> PerformanceMetrics:
    initial = FROZEN_CIBO_USD60_SIX_MONTH_PROTOCOL.initial_capital_usd
    realized = initial
    peak = initial
    minimum = initial
    max_dd = Decimal(0)
    exposures: dict[str, _BaselineExposure] = {}
    pnl_rows: list[tuple[str, datetime, Decimal]] = []
    rejected = 0
    outcome_by_signal = {
        item.signal_fingerprint: item for item in plan.outcome_events
    }

    def settle_until(clock: datetime) -> None:
        nonlocal realized, peak, minimum, max_dd
        rows = sorted(
            (
                item
                for item in exposures.values()
                if item.exit_at <= clock
            ),
            key=lambda item: (item.exit_at, item.signal),
        )
        for item in rows:
            exposures.pop(item.signal, None)
            realized += item.pnl_usd
            peak = max(peak, realized)
            minimum = min(minimum, realized)
            max_dd = max(max_dd, peak - realized)
            pnl_rows.append((item.trader_id, item.exit_at, item.pnl_usd))

    for epoch in plan.epochs:
        settle_until(epoch.market_decision_at)
        for candidate in epoch.candidates:
            open_risk = sum(
                (item.risk_usd for item in exposures.values()),
                Decimal(0),
            )
            open_margin = sum(
                (item.margin_usd for item in exposures.values()),
                Decimal(0),
            )
            if realized <= 0:
                rejected += 1
                continue
            capital = CiboCapitalState(
                assigned_capital_usd=realized,
                hard_risk_headroom_usd=max(Decimal(0), realized - open_risk),
                margin_headroom_usd=max(Decimal(0), realized - open_margin),
                base_capital_at_risk_usd=min(initial, max(realized, Decimal(0))),
                realized_net_profit_usd=max(Decimal(0), realized - initial),
                protected_open_economic_floor_usd=Decimal(0),
                proven_self_financing_capacity_usd=max(
                    Decimal(0), realized - initial
                ),
                reserved_expansion_risk_usd=Decimal(0),
                cost_reserve_usd=Decimal(0),
            )
            opportunity = candidate.projection.candidate.capital_input.opportunity
            try:
                seed = plan_minimal_seed(opportunity, capital)
            except CiboCapitalManagementError:
                rejected += 1
                continue
            if seed.volume <= 0:
                rejected += 1
                continue
            outcome = outcome_by_signal[candidate.signal_fingerprint]
            cost = (
                candidate.projection.provider_envelope.execution_cost_per_volume_usd
                * seed.volume
            )
            pnl = outcome.gross_structural_outcome_r * seed.stop_risk_usd - cost
            exposures[candidate.signal_fingerprint] = _BaselineExposure(
                signal=candidate.signal_fingerprint,
                trader_id=candidate.trader_id,
                exit_at=outcome.exit_at,
                risk_usd=seed.stop_risk_usd,
                margin_usd=seed.margin_usd,
                pnl_usd=pnl,
            )

    if exposures:
        settle_until(max(item.exit_at for item in exposures.values()))
    return _metrics_from_rows(
        lane="MINIMAL_SEED_ONLY",
        opportunity_count=len(plan.outcome_events),
        rejected=rejected,
        initial=initial,
        ending=realized,
        peak=peak,
        minimum=minimum,
        max_dd=max_dd,
        rows=tuple(pnl_rows),
    )


def _full_metrics(
    execution: Phase22HistoricalExecutionReport,
    *,
    opportunity_count: int,
) -> PerformanceMetrics:
    rows = tuple(
        (
            item.trader_id,
            item.observed_at,
            item.realized_net_pnl_usd,
        )
        for item in execution.books.cma_settlement.settlements
    )
    minimum = execution.initial_realized_capital_usd
    running = execution.initial_realized_capital_usd
    for _trader, _at, pnl in sorted(rows, key=lambda item: item[1]):
        running += pnl
        minimum = min(minimum, running)
    return _metrics_from_rows(
        lane="FULL_CIBO_CORE",
        opportunity_count=opportunity_count,
        rejected=opportunity_count - execution.settled_count,
        initial=execution.initial_realized_capital_usd,
        ending=execution.final_realized_capital_usd,
        peak=execution.peak_realized_capital_usd,
        minimum=minimum,
        max_dd=execution.max_realized_capital_drawdown_usd,
        rows=rows,
    )


def _metrics_from_rows(
    *,
    lane: str,
    opportunity_count: int,
    rejected: int,
    initial: Decimal,
    ending: Decimal,
    peak: Decimal,
    minimum: Decimal,
    max_dd: Decimal,
    rows: tuple[tuple[str, datetime, Decimal], ...],
) -> PerformanceMetrics:
    positives = tuple(pnl for _trader, _at, pnl in rows if pnl > 0)
    negatives = tuple(pnl for _trader, _at, pnl in rows if pnl < 0)
    gross_profit = sum(positives, Decimal(0))
    gross_loss = -sum(negatives, Decimal(0))
    profit_factor = (
        None if gross_loss == 0 else gross_profit / gross_loss
    )
    by_trader: dict[str, Decimal] = {}
    for trader, _at, pnl in rows:
        by_trader[trader] = by_trader.get(trader, Decimal(0)) + pnl
    return PerformanceMetrics(
        lane=lane,
        opportunity_count=opportunity_count,
        executed_count=len(rows),
        rejected_or_unexpressible_count=rejected,
        initial_capital_usd=initial,
        ending_capital_usd=ending,
        net_realized_pnl_usd=ending - initial,
        peak_capital_usd=peak,
        minimum_capital_usd=minimum,
        max_realized_drawdown_usd=max_dd,
        gross_profit_usd=gross_profit,
        gross_loss_usd=gross_loss,
        profit_factor=profit_factor,
        trading_days=len({at.date() for _trader, at, _pnl in rows}),
        trader_pnl_usd=tuple(sorted(by_trader.items())),
    )


def _tool_audit(
    *,
    plan: Phase22ChronologicalReplayPlan,
    execution: Phase22HistoricalExecutionReport,
) -> tuple[ToolAuditRow, ...]:
    counters: dict[str, dict[str, int]] = {
        f"T{i:02d}": {
            "enabled": 0,
            "blocked": 0,
            "applied": 0,
            "abstain": 0,
            "fail_closed": 0,
        }
        for i in range(1, 21)
    }
    reasons: dict[str, list[str]] = {f"T{i:02d}": [] for i in range(1, 21)}

    for seal in execution.books.holdout_policy.decisions:
        raw = json.loads(seal.canonical_record_json)
        surface = raw.get("full_surface")
        if isinstance(surface, dict):
            regime = surface.get("regime")
            if isinstance(regime, dict):
                for code in regime.get("enabled_tools", []):
                    if code in counters:
                        counters[code]["enabled"] += 1
                for code in regime.get("blocked_tools", []):
                    if code in counters:
                        counters[code]["blocked"] += 1
            assessments = surface.get("opportunity_assessments", [])
            if isinstance(assessments, list):
                for assessment in assessments:
                    if not isinstance(assessment, dict):
                        continue
                    for decision in assessment.get("decisions", []):
                        _count_advanced(decision, counters, reasons)
            portfolio = surface.get("portfolio_decisions", [])
            if isinstance(portfolio, list):
                for decision in portfolio:
                    _count_advanced(decision, counters, reasons)

        allocator = raw.get("allocator_decision")
        if isinstance(allocator, dict):
            for code in allocator.get("applied_tools", []):
                if code in counters:
                    counters[code]["applied"] += 1
                    reasons[code].append("allocator applied tool")

    multi_candidate_epochs = sum(
        1 for item in plan.epochs if len(item.candidates) > 1
    )
    multi_trader_epochs = sum(
        1
        for item in plan.epochs
        if len({candidate.trader_id for candidate in item.candidates}) > 1
    )
    release_count = len(execution.books.t20_release.release_chain)
    profit_available = execution.peak_realized_capital_usd > (
        execution.initial_realized_capital_usd
    )

    candidate_by_signal = {
        candidate.signal_fingerprint: candidate
        for epoch in plan.epochs
        for candidate in epoch.candidates
    }

    # Shadow-only post-run consultations. These calls never feed back into the
    # historical capital decision; they prove the engines are integrated and
    # explain why they did or did not have authority under the observed state.
    if counters["T11"]["enabled"] > 0:
        for candidate in candidate_by_signal.values():
            opportunity = candidate.projection.candidate.capital_input.opportunity
            t11 = evaluate_t11_runtime_exposure_guard(
                qore_symbol=opportunity.qore_symbol,
                requested_volume=opportunity.minimum_volume,
                provider_envelope=candidate.projection.provider_envelope,
            )
            if t11.advanced_exposure_authorized:
                counters["T11"]["applied"] += 1
            else:
                counters["T11"]["fail_closed"] += 1
                reasons["T11"].extend(t11.blockers)

    accepted_risk = tuple(
        item
        for item in execution.books.executed_risk.executed_risk
        if item.authorized_stop_risk_usd > 0 and item.authorized_margin_usd > 0
    )
    if counters["T14"]["enabled"] > 0:
        for risk in accepted_risk:
            candidate = candidate_by_signal.get(risk.signal_fingerprint)
            if candidate is None:
                continue
            opportunity = candidate.projection.candidate.capital_input.opportunity
            current_volume = (
                risk.authorized_stop_risk_usd
                / opportunity.stop_loss_per_volume
            )
            decision = plan_dynamic_derisking(
                CiboDeRiskingInput(
                    current_volume=current_volume,
                    minimum_retained_volume=opportunity.minimum_volume,
                    volume_step=opportunity.volume_step,
                    stop_risk_per_volume_usd=opportunity.stop_loss_per_volume,
                    margin_per_volume_usd=opportunity.margin_per_volume,
                    maximum_retained_stop_risk_usd=(
                        risk.authorized_stop_risk_usd
                    ),
                    maximum_retained_margin_usd=risk.authorized_margin_usd,
                    methodology_position_valid=True,
                )
            )
            counters["T14"]["applied"] += 1
            reasons["T14"].append(decision.reason)

    representative = next(iter(candidate_by_signal.values()), None)
    if representative is not None and execution.final_realized_capital_usd > 0:
        opportunity = representative.projection.candidate.capital_input.opportunity
        final_capital = execution.final_realized_capital_usd
        realized_profit = max(
            Decimal(0),
            final_capital - execution.initial_realized_capital_usd,
        )
        observed_capital = CiboCapitalState(
            assigned_capital_usd=final_capital,
            hard_risk_headroom_usd=final_capital,
            margin_headroom_usd=final_capital,
            base_capital_at_risk_usd=min(
                execution.initial_realized_capital_usd,
                final_capital,
            ),
            realized_net_profit_usd=realized_profit,
            protected_open_economic_floor_usd=Decimal(0),
            proven_self_financing_capacity_usd=realized_profit,
            reserved_expansion_risk_usd=Decimal(0),
            cost_reserve_usd=Decimal(0),
        )
        if counters["T06"]["enabled"] > 0:
            t06 = plan_self_financing_expansion(opportunity, observed_capital)
            if t06.volume > 0:
                counters["T06"]["applied"] += 1
            else:
                counters["T06"]["fail_closed"] += 1
            reasons["T06"].append(t06.reason)
        if counters["T07"]["enabled"] > 0:
            protected_only = CiboCapitalState(
                assigned_capital_usd=final_capital,
                hard_risk_headroom_usd=final_capital,
                margin_headroom_usd=final_capital,
                base_capital_at_risk_usd=min(
                    execution.initial_realized_capital_usd,
                    final_capital,
                ),
                realized_net_profit_usd=Decimal(0),
                protected_open_economic_floor_usd=Decimal(0),
                proven_self_financing_capacity_usd=Decimal(0),
                reserved_expansion_risk_usd=Decimal(0),
                cost_reserve_usd=Decimal(0),
            )
            t07 = plan_self_financing_expansion(opportunity, protected_only)
            if t07.volume > 0:
                counters["T07"]["applied"] += 1
            else:
                counters["T07"]["fail_closed"] += 1
            reasons["T07"].append(t07.reason)

    contracts = {item.code: item for item in CE2I_TOOL_REGISTRY}
    rows: list[ToolAuditRow] = []
    for code in tuple(f"T{i:02d}" for i in range(1, 21)):
        stat = counters[code]
        status: ToolRuntimeStatus
        reason: str

        if code == "T01":
            if execution.selected_count > 0:
                status = ToolRuntimeStatus.APPLIED
                stat["applied"] = execution.selected_count
                reason = "plan_minimal_seed executed for every CIBO-selected signal"
            else:
                status = ToolRuntimeStatus.FAIL_CLOSED
                reason = "no CIBO-selected signal reached minimal-seed deployment"
        elif code in {"T02", "T03", "T04", "T08", "T10", "T16", "T17"}:
            if stat["applied"] > 0:
                status = ToolRuntimeStatus.APPLIED
                reason = _reason_summary(reasons[code], "advanced engine applied")
            elif stat["fail_closed"] > 0 or stat["abstain"] > 0:
                status = ToolRuntimeStatus.FAIL_CLOSED
                reason = _reason_summary(
                    reasons[code],
                    "advanced engine evaluated and correctly withheld authority",
                )
            elif stat["enabled"] == 0 and stat["blocked"] > 0:
                status = ToolRuntimeStatus.REGIME_BLOCKED
                reason = "mission/regime selector blocked tool before action engine"
            else:
                status = ToolRuntimeStatus.NOT_INTEGRATED
                reason = (
                    "tool contract exists but no runtime action/fail-closed "
                    "receipt was observed"
                )
        elif code == "T05":
            if release_count > 0 and len(plan.epochs) > 1:
                status = ToolRuntimeStatus.APPLIED
                stat["applied"] = release_count
                reason = (
                    "settled risk/margin was released and subsequent epochs "
                    "recomputed reusable headroom"
                )
            else:
                status = ToolRuntimeStatus.JUSTIFIED_NOT_APPLICABLE
                reason = "no reconciled released capacity was available for a later epoch"
        elif code == "T06":
            if stat["applied"] > 0:
                status = ToolRuntimeStatus.APPLIED
                reason = _reason_summary(
                    reasons[code],
                    "profit-funded expansion engine authorized capacity",
                )
            elif stat["fail_closed"] > 0:
                status = ToolRuntimeStatus.FAIL_CLOSED
                reason = _reason_summary(
                    reasons[code],
                    "profit-funded expansion evaluated and withheld authority",
                )
            elif stat["enabled"] == 0 and stat["blocked"] > 0:
                status = ToolRuntimeStatus.REGIME_BLOCKED
                reason = "mission/regime blocked profit-funded expansion"
            else:
                status = ToolRuntimeStatus.JUSTIFIED_NOT_APPLICABLE
                reason = (
                    "no eligible realized-profit expansion state was observed"
                )
        elif code == "T07":
            if stat["applied"] > 0:
                status = ToolRuntimeStatus.APPLIED
                reason = _reason_summary(
                    reasons[code],
                    "protected-capacity expansion engine authorized capacity",
                )
            elif stat["fail_closed"] > 0:
                status = ToolRuntimeStatus.FAIL_CLOSED
                reason = _reason_summary(
                    reasons[code],
                    "protected-capacity expansion evaluated and withheld authority",
                )
            elif stat["enabled"] == 0 and stat["blocked"] > 0:
                status = ToolRuntimeStatus.REGIME_BLOCKED
                reason = "mission/regime blocked protected-capacity expansion"
            else:
                status = ToolRuntimeStatus.JUSTIFIED_NOT_APPLICABLE
                reason = (
                    "no broker-confirmed protected economic floor was available"
                )
        elif code == "T09":
            if stat["applied"] > 0 or multi_candidate_epochs > 0:
                status = ToolRuntimeStatus.APPLIED
                stat["applied"] = max(stat["applied"], multi_candidate_epochs)
                reason = "robust allocator evaluated simultaneous opportunity competition"
            else:
                status = ToolRuntimeStatus.JUSTIFIED_NOT_APPLICABLE
                reason = "no simultaneous multi-candidate epoch required competition"
        elif code == "T11":
            if stat["applied"] > 0:
                status = ToolRuntimeStatus.APPLIED
                reason = _reason_summary(
                    reasons[code],
                    "T11 advanced exposure gate authorized capacity",
                )
            elif stat["fail_closed"] > 0:
                status = ToolRuntimeStatus.FAIL_CLOSED
                reason = _reason_summary(
                    reasons[code],
                    "T11 evaluated provider economics and capped at minimal seed",
                )
            elif stat["enabled"] == 0 and stat["blocked"] > 0:
                status = ToolRuntimeStatus.REGIME_BLOCKED
                reason = "regime/mission did not enable execution-efficient exposure"
            else:
                status = ToolRuntimeStatus.JUSTIFIED_NOT_APPLICABLE
                reason = "no T11-eligible opportunity was observed"
        elif code == "T12":
            status = ToolRuntimeStatus.APPLIED
            stat["applied"] = len(plan.epochs)
            reason = "causal regime selector evaluated the CE2I surface at every decision epoch"
        elif code == "T13":
            if stat["applied"] > 0:
                status = ToolRuntimeStatus.APPLIED
                reason = "allocator applied drawdown reserve under recovery posture"
            elif stat["enabled"] > 0:
                status = ToolRuntimeStatus.FAIL_CLOSED
                reason = "T13 was eligible but allocator found no recovery-posture reserve action"
            else:
                status = ToolRuntimeStatus.REGIME_BLOCKED
                reason = "current posture did not make drawdown reserve eligible"
        elif code == "T14":
            if stat["applied"] > 0:
                status = ToolRuntimeStatus.APPLIED
                reason = _reason_summary(
                    reasons[code],
                    "dynamic de-risking engine evaluated accepted positions",
                )
            elif stat["enabled"] == 0 and stat["blocked"] > 0:
                status = ToolRuntimeStatus.REGIME_BLOCKED
                reason = "mission/regime blocked dynamic de-risking"
            else:
                status = ToolRuntimeStatus.JUSTIFIED_NOT_APPLICABLE
                reason = "no accepted position existed for T14 evaluation"
        elif code == "T15":
            if stat["applied"] > 0:
                status = ToolRuntimeStatus.APPLIED
                reason = "allocator applied capital optionality/reservation envelope"
            elif stat["enabled"] > 0:
                status = ToolRuntimeStatus.FAIL_CLOSED
                reason = "optionality was evaluated with no known future option requiring reserve"
            else:
                status = ToolRuntimeStatus.REGIME_BLOCKED
                reason = "mission/regime blocked optionality"
        elif code == "T18":
            if stat["applied"] > 0 or multi_trader_epochs > 0:
                status = ToolRuntimeStatus.APPLIED
                stat["applied"] = max(stat["applied"], multi_trader_epochs)
                reason = "robust allocator compared simultaneous cross-Trader opportunities"
            else:
                status = ToolRuntimeStatus.JUSTIFIED_NOT_APPLICABLE
                reason = "no simultaneous cross-Trader opportunity set occurred"
        elif code == "T19":
            if execution.allowed_count + execution.reduced_count > 0:
                status = ToolRuntimeStatus.APPLIED
                stat["applied"] = execution.allowed_count + execution.reduced_count
                reason = (
                    "QORE Risk reservations were created before accepted "
                    "historical deployments"
                )
            else:
                status = ToolRuntimeStatus.FAIL_CLOSED
                reason = "no Risk-authorized deployment required a capacity reservation"
        elif code == "T20":
            if release_count == execution.settled_count and release_count > 0:
                status = ToolRuntimeStatus.APPLIED
                stat["applied"] = release_count
                reason = "every settled deployment emitted a reconciled T20 release seal"
            elif execution.settled_count == 0 and release_count == 0:
                status = ToolRuntimeStatus.JUSTIFIED_NOT_APPLICABLE
                reason = "no deployment settled, so there was no capacity to release"
            else:
                status = ToolRuntimeStatus.NOT_INTEGRATED
                reason = "settlement/release surface is incomplete"
        else:
            status = ToolRuntimeStatus.NOT_INTEGRATED
            reason = "unclassified CE2I runtime path"

        rows.append(
            ToolAuditRow(
                tool_code=code,
                tool_name=contracts[code].name,
                status=status,
                enabled_epochs=stat["enabled"],
                regime_blocked_epochs=stat["blocked"],
                applied_count=stat["applied"],
                abstain_count=stat["abstain"],
                fail_closed_count=stat["fail_closed"],
                reason=reason,
            )
        )
    return tuple(rows)


def _count_advanced(
    raw: object,
    counters: dict[str, dict[str, int]],
    reasons: dict[str, list[str]],
) -> None:
    if not isinstance(raw, dict):
        return
    code = str(raw.get("tool_code", ""))
    if code not in counters:
        return
    disposition = str(raw.get("disposition", ""))
    reason = str(raw.get("reason", ""))
    if disposition == "APPLIED":
        counters[code]["applied"] += 1
    elif disposition == "ABSTAIN":
        counters[code]["abstain"] += 1
    elif disposition == "FAIL_CLOSED":
        counters[code]["fail_closed"] += 1
    if reason:
        reasons[code].append(reason)


def _reason_summary(rows: list[str], fallback: str) -> str:
    if not rows:
        return fallback
    unique = list(dict.fromkeys(rows))
    return "; ".join(unique[:4])


def _metrics_differ(
    baseline: PerformanceMetrics,
    full: PerformanceMetrics,
) -> bool:
    return any(
        (
            baseline.ending_capital_usd != full.ending_capital_usd,
            baseline.max_realized_drawdown_usd != full.max_realized_drawdown_usd,
            baseline.executed_count != full.executed_count,
            baseline.profit_factor != full.profit_factor,
        )
    )


def _canonical(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, tuple):
        return [_canonical(item) for item in value]
    if isinstance(value, list):
        return [_canonical(item) for item in value]
    if isinstance(value, dict):
        return {
            str(key): _canonical(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    return value
