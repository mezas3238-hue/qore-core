"""Compound + portfolio-compound ablation for the reused USD60 capability exam.

The treatment consumes the exact FULL_CIBO_CORE selection surface. It may add
only an incremental minimum executable seed funded by profit that was already
realized before the decision epoch. Positive Core settlements and earlier
compound settlements form one account-local pool, so capital can be redeployed
across Traders without changing Trader edge or the Core selection.

QORE Risk remains sovereign over every incremental request. This is a
NON_CERTIFYING_REUSED_HOLDOUT research lane and grants no broker/LIVE/real/
production/merge authority.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from qore.infrastructure.account_wide_risk import (
    AccountRiskSnapshot,
    AccountWideRiskEngine,
    RiskDecision,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CapitalAction,
    CapitalSource,
    CapitalStage,
    CiboCapitalActionPlan,
    CiboCapitalManagementError,
    minimum_seed_volume,
)
from qore.infrastructure.cibo_capital_science_runtime_bridge import (
    CapitalSciencePredecisionInput,
    CapitalScienceReceipt,
    aggregate_capital_science_receipts,
    build_capital_science_postrun_receipts,
    evaluate_capital_science_predecision,
)
from qore.infrastructure.cibo_ce2i_phase20_train_prior import (
    build_frozen_train_expectation,
)
from qore.infrastructure.cibo_ce2i_usd60_six_month_certification import (
    FROZEN_CIBO_USD60_SIX_MONTH_PROTOCOL,
)
from qore.infrastructure.cibo_cma_risk_request import build_cma_risk_request
from qore.infrastructure.cibo_phase22_v4_chronological_execution import (
    Phase22HistoricalExecutionReport,
)
from qore.infrastructure.cibo_phase22_v4_chronological_replay_plan import (
    Phase22ChronologicalReplayPlan,
)
from qore.infrastructure.cibo_protected_reinvestment_policy import (
    POLICY_ID,
    maximum_reinvestment_capital_need_usd,
    protected_loss_reserve_usd,
    protected_reinvestment_candidate_allowed,
)

LANE_ID = "FULL_CIBO_COMPOUND_PORTFOLIO"



@dataclass(frozen=True, slots=True)
class CompoundRedeployAuthorization:
    """Fresh/OOS predecision evidence for productive-policy qualification."""

    signal_fingerprint: str
    known_at: datetime
    evidence_id: str
    marginal_utility_oos: bool
    profit_preservation_ready: bool
    adaptive_speed_ready: bool
    growth_ruin_ready: bool
    forward_controller_ready: bool
    crisis_governance_ready: bool
    policy_authorized: bool

    def __post_init__(self) -> None:
        if not self.signal_fingerprint or not self.evidence_id:
            raise CiboCapitalManagementError(
                "compound redeploy authorization identity required"
            )
        if self.known_at.tzinfo is None or self.known_at.utcoffset() is None:
            raise CiboCapitalManagementError(
                "compound redeploy authorization known_at must be timezone-aware"
            )
        prerequisites = (
            self.marginal_utility_oos,
            self.profit_preservation_ready,
            self.adaptive_speed_ready,
            self.growth_ruin_ready,
            self.forward_controller_ready,
            self.crisis_governance_ready,
        )
        if any(type(item) is not bool for item in (*prerequisites, self.policy_authorized)):
            raise CiboCapitalManagementError(
                "compound redeploy authorization flags must be bool"
            )
        if self.policy_authorized and not all(prerequisites):
            raise CiboCapitalManagementError(
                "compound redeploy policy cannot outrun GEN-C readiness"
            )


@dataclass(frozen=True, slots=True)
class CompoundResearchRedeployAuthorization:
    """Research-only causal redeploy permission for reused-holdout capability work.

    This contract exists specifically so a reused holdout never has to lie by
    setting marginal_utility_oos=True. It cannot grant productive authority.
    Candidate admission remains independently governed by the frozen protected
    reinvestment policy plus CMA and sovereign QORE Risk.
    """

    signal_fingerprint: str
    known_at: datetime
    evidence_id: str
    policy_id: str
    calibration_mode: str
    research_redeploy_authorized: bool = True
    fresh_oos_utility_demonstrated: bool = False
    certification_claimed: bool = False
    broker_mutation_authorized: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False
    production_authorized: bool = False

    def __post_init__(self) -> None:
        if not self.signal_fingerprint or not self.evidence_id or not self.policy_id:
            raise CiboCapitalManagementError(
                "compound research redeploy identity required"
            )
        if self.known_at.tzinfo is None or self.known_at.utcoffset() is None:
            raise CiboCapitalManagementError(
                "compound research redeploy known_at must be timezone-aware"
            )
        if self.calibration_mode != "NON_CERTIFYING_REUSED_HOLDOUT":
            raise CiboCapitalManagementError(
                "compound research redeploy requires reused-holdout calibration"
            )
        flags = (
            self.research_redeploy_authorized,
            self.fresh_oos_utility_demonstrated,
            self.certification_claimed,
            self.broker_mutation_authorized,
            self.live_authorized,
            self.real_capital_authorized,
            self.production_authorized,
        )
        if any(type(item) is not bool for item in flags):
            raise CiboCapitalManagementError(
                "compound research redeploy flags must be bool"
            )
        if (
            not self.research_redeploy_authorized
            or self.fresh_oos_utility_demonstrated
            or self.certification_claimed
            or self.broker_mutation_authorized
            or self.live_authorized
            or self.real_capital_authorized
            or self.production_authorized
        ):
            raise CiboCapitalManagementError(
                "compound research redeploy governance contamination"
            )


@dataclass(frozen=True, slots=True)
class _Budget:
    provider_headroom: Decimal
    max_risk_at_any_time: Decimal
    active_mll: Decimal
    hard_breach: bool


@dataclass(slots=True)
class _Open:
    signal_fingerprint: str
    trader_id: str
    exit_at: datetime
    authorization_id: str
    authorized_volume: Decimal
    authorized_stop_risk_usd: Decimal
    authorized_margin_usd: Decimal
    gross_structural_outcome_r: Decimal
    provider_cost_usd: Decimal
    protected_loss_reserve_usd: Decimal
    source_traders_before_entry: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CompoundPortfolioTrade:
    signal_fingerprint: str
    trader_id: str
    exit_at: datetime
    authorized_volume: Decimal
    authorized_stop_risk_usd: Decimal
    authorized_margin_usd: Decimal
    gross_structural_outcome_r: Decimal
    provider_cost_usd: Decimal
    incremental_realized_pnl_usd: Decimal
    source_traders_before_entry: tuple[str, ...]
    cross_trader_pool_used: bool

    def payload(self) -> dict[str, Any]:
        raw = asdict(self)
        for key, value in tuple(raw.items()):
            if isinstance(value, Decimal):
                raw[key] = format(value, "f")
            elif isinstance(value, datetime):
                raw[key] = value.isoformat()
        return raw


@dataclass(frozen=True, slots=True)
class CompoundPortfolioLaneResult:
    core_ending_capital_usd: Decimal
    compound_incremental_pnl_usd: Decimal
    ending_capital_usd: Decimal
    net_realized_pnl_usd: Decimal
    compound_selected_count: int
    compound_allowed_count: int
    compound_reduced_count: int
    compound_rejected_count: int
    compound_settled_count: int
    cross_trader_compound_deployments: int
    profit_factor: Decimal | None
    trader_incremental_pnl_usd: tuple[tuple[str, Decimal], ...]
    trader_compound_entries: tuple[tuple[str, int], ...]
    trades: tuple[CompoundPortfolioTrade, ...]
    blocker_reasons: tuple[tuple[str, int], ...]
    function_accountability: tuple[dict[str, object], ...]
    capital_science_receipts: tuple[dict[str, object], ...]
    rational_redeploy_gate_enabled: bool = False
    noncertifying_research_redeploy_enabled: bool = False
    protected_reinvestment_policy_id: str = ""
    lane_id: str = LANE_ID
    same_core_selection_surface: bool = True
    realized_profit_only: bool = True
    floating_pnl_used_as_funding: bool = False
    qore_risk_sovereign: bool = True
    outcome_aware_tuning_used: bool = False
    broker_mutation_performed: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False
    production_authorized: bool = False
    merge_authorized: bool = False

    def __post_init__(self) -> None:
        initial = FROZEN_CIBO_USD60_SIX_MONTH_PROTOCOL.initial_capital_usd
        if self.ending_capital_usd != (
            self.core_ending_capital_usd + self.compound_incremental_pnl_usd
        ):
            raise CiboCapitalManagementError("compound lane capital identity drift")
        if self.net_realized_pnl_usd != self.ending_capital_usd - initial:
            raise CiboCapitalManagementError("compound lane PnL identity drift")
        if self.compound_selected_count != (
            self.compound_allowed_count
            + self.compound_reduced_count
            + self.compound_rejected_count
        ):
            raise CiboCapitalManagementError("compound lane Risk count drift")
        if self.compound_settled_count != (
            self.compound_allowed_count + self.compound_reduced_count
        ):
            raise CiboCapitalManagementError("compound lane settlement count drift")
        if self.compound_settled_count != len(self.trades):
            raise CiboCapitalManagementError("compound lane trade count drift")
        if type(self.rational_redeploy_gate_enabled) is not bool:
            raise CiboCapitalManagementError(
                "compound rational redeploy gate flag must be bool"
            )
        if type(self.noncertifying_research_redeploy_enabled) is not bool:
            raise CiboCapitalManagementError(
                "compound research redeploy flag must be bool"
            )
        if not isinstance(self.protected_reinvestment_policy_id, str):
            raise CiboCapitalManagementError(
                "compound protected reinvestment policy id must be str"
            )
        if not all(
            (
                self.same_core_selection_surface,
                self.realized_profit_only,
                self.qore_risk_sovereign,
            )
        ) or any(
            (
                self.floating_pnl_used_as_funding,
                self.outcome_aware_tuning_used,
                self.broker_mutation_performed,
                self.live_authorized,
                self.real_capital_authorized,
                self.production_authorized,
                self.merge_authorized,
            )
        ):
            raise CiboCapitalManagementError("compound lane governance drift")

    def payload(self, *, core_executed_count: int) -> dict[str, Any]:
        return {
            "lane_id": self.lane_id,
            "initial_capital_usd": format(
                FROZEN_CIBO_USD60_SIX_MONTH_PROTOCOL.initial_capital_usd, "f"
            ),
            "core_ending_capital_usd": format(self.core_ending_capital_usd, "f"),
            "compound_incremental_pnl_usd": format(
                self.compound_incremental_pnl_usd, "f"
            ),
            "ending_capital_usd": format(self.ending_capital_usd, "f"),
            "net_realized_pnl_usd": format(self.net_realized_pnl_usd, "f"),
            "core_executed_count": core_executed_count,
            "compound_selected_count": self.compound_selected_count,
            "compound_allowed_count": self.compound_allowed_count,
            "compound_reduced_count": self.compound_reduced_count,
            "compound_rejected_count": self.compound_rejected_count,
            "compound_settled_count": self.compound_settled_count,
            "total_executed_count": core_executed_count + self.compound_settled_count,
            "cross_trader_compound_deployments": (
                self.cross_trader_compound_deployments
            ),
            "profit_factor": (
                None if self.profit_factor is None else format(self.profit_factor, "f")
            ),
            "trader_incremental_pnl_usd": {
                trader: format(value, "f")
                for trader, value in self.trader_incremental_pnl_usd
            },
            "trader_compound_entries": {
                trader: count for trader, count in self.trader_compound_entries
            },
            "trades": [item.payload() for item in self.trades],
            "blocker_reasons": [
                {"reason": reason, "count": count}
                for reason, count in self.blocker_reasons
            ],
            "function_accountability": list(self.function_accountability),
            "capital_science_receipts": list(self.capital_science_receipts),
            "rational_redeploy_gate_enabled": self.rational_redeploy_gate_enabled,
            "noncertifying_research_redeploy_enabled": (
                self.noncertifying_research_redeploy_enabled
            ),
            "protected_reinvestment_policy_id": (
                self.protected_reinvestment_policy_id
            ),
            "same_core_selection_surface": self.same_core_selection_surface,
            "realized_profit_only": self.realized_profit_only,
            "floating_pnl_used_as_funding": self.floating_pnl_used_as_funding,
            "qore_risk_sovereign": self.qore_risk_sovereign,
            "outcome_aware_tuning_used": self.outcome_aware_tuning_used,
            "broker_mutation_performed": self.broker_mutation_performed,
            "live_authorized": self.live_authorized,
            "real_capital_authorized": self.real_capital_authorized,
            "production_authorized": self.production_authorized,
            "merge_authorized": self.merge_authorized,
        }


def run_compound_portfolio_lane(
    *,
    plan: Phase22ChronologicalReplayPlan,
    core_execution: Phase22HistoricalExecutionReport,
    lab_use_executed_core_surface: bool = False,
    lab_require_rational_redeploy: bool = False,
    redeploy_authorizations: tuple[CompoundRedeployAuthorization, ...] = (),
    lab_allow_noncertifying_research_redeploy: bool = False,
    research_redeploy_authorizations: tuple[
        CompoundResearchRedeployAuthorization, ...
    ] = (),
) -> CompoundPortfolioLaneResult:
    """Add causal profit-funded seeds without changing Core policy selection."""

    if type(lab_use_executed_core_surface) is not bool:
        raise CiboCapitalManagementError(
            "lab_use_executed_core_surface must be bool"
        )
    if type(lab_require_rational_redeploy) is not bool:
        raise CiboCapitalManagementError(
            "lab_require_rational_redeploy must be bool"
        )
    if type(lab_allow_noncertifying_research_redeploy) is not bool:
        raise CiboCapitalManagementError(
            "lab_allow_noncertifying_research_redeploy must be bool"
        )
    if any(
        not isinstance(item, CompoundRedeployAuthorization)
        for item in redeploy_authorizations
    ):
        raise CiboCapitalManagementError(
            "compound redeploy authorizations must use canonical contract"
        )
    authorization_by_signal = {
        item.signal_fingerprint: item for item in redeploy_authorizations
    }
    if len(authorization_by_signal) != len(redeploy_authorizations):
        raise CiboCapitalManagementError(
            "compound redeploy authorization fingerprints must be unique"
        )
    if any(
        not isinstance(item, CompoundResearchRedeployAuthorization)
        for item in research_redeploy_authorizations
    ):
        raise CiboCapitalManagementError(
            "compound research redeploy authorizations must use canonical contract"
        )
    research_authorization_by_signal = {
        item.signal_fingerprint: item
        for item in research_redeploy_authorizations
    }
    if len(research_authorization_by_signal) != len(
        research_redeploy_authorizations
    ):
        raise CiboCapitalManagementError(
            "compound research redeploy fingerprints must be unique"
        )
    if (
        research_redeploy_authorizations
        and not lab_allow_noncertifying_research_redeploy
    ):
        raise CiboCapitalManagementError(
            "research redeploy authorizations require explicit lab opt-in"
        )

    initial = FROZEN_CIBO_USD60_SIX_MONTH_PROTOCOL.initial_capital_usd
    core_realized = initial
    pool = Decimal(0)
    incremental = Decimal(0)
    source_traders: set[str] = set()
    risk_engine = AccountWideRiskEngine()
    open_rows: dict[str, _Open] = {}
    trades: list[CompoundPortfolioTrade] = []
    blockers: Counter[str] = Counter()
    capital_science_receipts: list[CapitalScienceReceipt] = []
    selected = allowed = reduced = rejected = cross_trader = 0
    peak_realized_capital = initial

    outcomes = {item.signal_fingerprint: item for item in plan.outcome_events}
    core_settlements = sorted(
        core_execution.books.cma_settlement.settlements,
        key=lambda item: (item.capital_released_at, item.signal_fingerprint),
    )
    core_index = 0
    evidence_by_epoch = {
        item.decision_epoch_id: item
        for item in core_execution.books.holdout_evidence.decisions
    }
    core_release_by_signal = {
        item.signal_fingerprint: item.capital_released_at
        for item in core_execution.books.cma_settlement.settlements
    }
    core_risk_rows = tuple(
        item
        for item in core_execution.books.executed_risk.executed_risk
        if item.risk_decision is not RiskDecision.REJECT
    )

    core_selected_by_epoch: dict[datetime, tuple[str, ...]] = {}
    if lab_use_executed_core_surface:
        grouped: dict[datetime, list[str]] = defaultdict(list)
        for item in core_risk_rows:
            grouped[item.decided_at].append(item.signal_fingerprint)
        core_selected_by_epoch = {
            key: tuple(sorted(values))
            for key, values in grouped.items()
        }

    def core_open_capacity(clock: datetime) -> tuple[Decimal, Decimal]:
        rows = tuple(
            item
            for item in core_risk_rows
            if item.decided_at <= clock
            and item.signal_fingerprint in core_release_by_signal
            and clock < core_release_by_signal[item.signal_fingerprint]
        )
        return (
            sum((item.authorized_stop_risk_usd for item in rows), Decimal(0)),
            sum((item.authorized_margin_usd for item in rows), Decimal(0)),
        )

    def settle_until(clock: datetime) -> None:
        nonlocal core_index, core_realized, pool, incremental, peak_realized_capital
        while (
            core_index < len(core_settlements)
            and core_settlements[core_index].capital_released_at <= clock
        ):
            item = core_settlements[core_index]
            core_realized += item.realized_net_pnl_usd
            peak_realized_capital = max(
                peak_realized_capital,
                core_realized + incremental,
            )
            if item.realized_net_pnl_usd > 0:
                pool += item.realized_net_pnl_usd
                source_traders.add(item.trader_id)
            core_index += 1

        due = sorted(
            (item for item in open_rows.values() if item.exit_at <= clock),
            key=lambda item: (item.exit_at, item.signal_fingerprint),
        )
        for item in due:
            open_rows.pop(item.signal_fingerprint, None)
            pnl = (
                item.gross_structural_outcome_r
                * item.authorized_stop_risk_usd
                - item.provider_cost_usd
            )
            pool += pnl
            incremental += pnl
            peak_realized_capital = max(
                peak_realized_capital,
                core_realized + incremental,
            )
            if pool < 0:
                raise CiboCapitalManagementError(
                    "compound pool became negative despite fail-closed funding"
                )
            cross = any(
                source != item.trader_id
                for source in item.source_traders_before_entry
            )
            trades.append(
                CompoundPortfolioTrade(
                    signal_fingerprint=item.signal_fingerprint,
                    trader_id=item.trader_id,
                    exit_at=item.exit_at,
                    authorized_volume=item.authorized_volume,
                    authorized_stop_risk_usd=item.authorized_stop_risk_usd,
                    authorized_margin_usd=item.authorized_margin_usd,
                    gross_structural_outcome_r=item.gross_structural_outcome_r,
                    provider_cost_usd=item.provider_cost_usd,
                    incremental_realized_pnl_usd=pnl,
                    source_traders_before_entry=item.source_traders_before_entry,
                    cross_trader_pool_used=cross,
                )
            )

    for epoch in plan.epochs:
        settle_until(epoch.market_decision_at)
        decision = evidence_by_epoch.get(epoch.decision_epoch_id)
        if decision is None:
            raise CiboCapitalManagementError("compound lane missing Core decision")
        policy = core_execution.books.holdout_policy.decision_for_evidence(
            decision.evidence_sha256
        )
        if policy is None:
            raise CiboCapitalManagementError("compound lane missing Core policy")
        by_signal = {item.signal_fingerprint: item for item in epoch.candidates}
        selected_signals = (
            core_selected_by_epoch.get(epoch.market_decision_at, ())
            if lab_use_executed_core_surface
            else tuple(policy.selected_signal_fingerprints)
        )

        for signal in selected_signals:
            selected += 1
            if lab_require_rational_redeploy:
                redeploy = authorization_by_signal.get(signal)
                research_redeploy = research_authorization_by_signal.get(signal)
                if redeploy is not None:
                    if redeploy.known_at > epoch.market_decision_at:
                        blockers["COMPOUND_REDEPLOY_EVIDENCE_FUTURE_KNOWN"] += 1
                        rejected += 1
                        continue
                    if not redeploy.policy_authorized:
                        blockers["COMPOUND_REDEPLOY_UTILITY_NOT_AUTHORIZED"] += 1
                        rejected += 1
                        continue
                elif (
                    lab_allow_noncertifying_research_redeploy
                    and research_redeploy is not None
                ):
                    if research_redeploy.known_at > epoch.market_decision_at:
                        blockers[
                            "COMPOUND_RESEARCH_REDEPLOY_EVIDENCE_FUTURE_KNOWN"
                        ] += 1
                        rejected += 1
                        continue
                else:
                    blockers["COMPOUND_REDEPLOY_UTILITY_NOT_AUTHORIZED"] += 1
                    rejected += 1
                    continue
            candidate = by_signal[signal]
            opportunity = candidate.projection.candidate.capital_input.opportunity
            volume = minimum_seed_volume(opportunity)
            risk = volume * opportunity.stop_loss_per_volume
            margin = volume * opportunity.margin_per_volume
            cost = (
                candidate.projection.provider_envelope.execution_cost_per_volume_usd
                * volume
            )
            loss_reserve = protected_loss_reserve_usd(risk)
            committed_loss = sum(
                (
                    item.authorized_stop_risk_usd
                    + item.provider_cost_usd
                    + item.protected_loss_reserve_usd
                    for item in open_rows.values()
                ),
                Decimal(0),
            )
            available = max(Decimal(0), pool - committed_loss)
            equity = max(Decimal(0), core_realized + incremental)
            if equity <= 0:
                blockers["CURRENT_REALIZED_CAPITAL_NOT_POSITIVE"] += 1
                rejected += 1
                continue
            dynamic_limit = maximum_reinvestment_capital_need_usd(equity)
            expectation = build_frozen_train_expectation(
                trader_id=opportunity.trader_id,
                stop_risk_usd=risk,
                as_of=epoch.market_decision_at,
            )

            core_open_risk_cs, core_open_margin_cs = core_open_capacity(
                epoch.market_decision_at
            )
            compound_open_risk_cs = sum(
                (item.authorized_stop_risk_usd for item in open_rows.values()),
                Decimal(0),
            )
            compound_open_margin_cs = sum(
                (item.authorized_margin_usd for item in open_rows.values()),
                Decimal(0),
            )
            total_open_risk_cs = core_open_risk_cs + compound_open_risk_cs
            total_open_margin_cs = core_open_margin_cs + compound_open_margin_cs
            capital_science = evaluate_capital_science_predecision(
                CapitalSciencePredecisionInput(
                    decision_epoch_id=epoch.decision_epoch_id,
                    signal_fingerprint=signal,
                    trader_id=candidate.trader_id,
                    decision_at=epoch.market_decision_at,
                    realized_capital_usd=equity,
                    peak_realized_capital_usd=max(
                        peak_realized_capital,
                        equity,
                    ),
                    realized_profit_pool_usd=pool,
                    protected_capacity_usd=min(pool, committed_loss),
                    open_stop_risk_usd=total_open_risk_cs,
                    open_margin_usd=total_open_margin_cs,
                    requested_stop_risk_usd=risk,
                    requested_margin_usd=margin,
                    provider_cost_usd=cost,
                    expected_net_value_usd=expectation.expected_net_value_usd,
                    expected_capital_minutes=expectation.expected_capital_minutes,
                    hard_risk_headroom_usd=max(
                        Decimal(0),
                        equity - total_open_risk_cs,
                    ),
                    margin_headroom_usd=max(
                        Decimal(0),
                        equity - total_open_margin_cs,
                    ),
                    competing_candidates=len(selected_signals),
                )
            )
            capital_science_receipts.extend(capital_science.receipts)
            available = min(
                available,
                capital_science.deployable_profit_usd,
            )
            if not capital_science.allow_incremental_compound:
                blockers[
                    "CAPITAL_SCIENCE_PREDECISION_ABSTAINED_OR_FAIL_CLOSED"
                ] += 1
                rejected += 1
                continue
            if risk + cost + loss_reserve > available:
                blockers[
                    "REALIZED_PROFIT_POOL_BELOW_SEED_COST_AND_LOSS_RESERVE"
                ] += 1
                rejected += 1
                continue
            if risk + cost > dynamic_limit:
                blockers[
                    "DYNAMIC_CURRENT_CAPITAL_REINVESTMENT_LIMIT_EXCEEDED"
                ] += 1
                rejected += 1
                continue
            if not protected_reinvestment_candidate_allowed(
                side=opportunity.side,
                capital_need_usd=risk + cost,
                eligible_current_capital_usd=equity,
                entry_type=opportunity.entry_type,
                expected_net_value_usd=expectation.expected_net_value_usd,
                expected_capital_minutes=expectation.expected_capital_minutes,
            ):
                blockers["PROTECTED_REINVESTMENT_V2_CAUSAL_GATE_REJECTED"] += 1
                rejected += 1
                continue
            headroom = min(
                equity,
                max(Decimal(0), available - cost - loss_reserve),
            )
            if risk > headroom or margin > headroom:
                blockers["COMPOUND_RISK_OR_MARGIN_HEADROOM_INSUFFICIENT"] += 1
                rejected += 1
                continue

            plan_row = CiboCapitalActionPlan(
                trader_id=opportunity.trader_id,
                qore_symbol=opportunity.qore_symbol,
                stage=CapitalStage.CAPITALIZE,
                action=CapitalAction.EXPAND,
                volume=volume,
                stop_risk_usd=risk,
                margin_usd=margin,
                capital_source=CapitalSource.REALIZED_PROFIT,
                capital_source_amount_usd=risk,
                reason=(
                    "incremental seed funded only by causally prior realized "
                    "profit in the account-local Compound Portfolio"
                ),
            )
            request = build_cma_risk_request(
                request_id=f"compound:{epoch.decision_epoch_id}:{signal}",
                opportunity=opportunity,
                plan=plan_row,
                requested_at=epoch.market_decision_at,
                expires_at=max(
                    candidate.entry_at,
                    epoch.market_decision_at + timedelta(seconds=1),
                ),
                capital_source_id=f"compound-realized-profit-pool:{signal}",
            )
            core_open_risk, core_open_margin = core_open_capacity(
                epoch.market_decision_at
            )
            compound_open_risk = sum(
                (item.authorized_stop_risk_usd for item in open_rows.values()),
                Decimal(0),
            )
            compound_open_margin = sum(
                (item.authorized_margin_usd for item in open_rows.values()),
                Decimal(0),
            )
            total_open_risk = core_open_risk + compound_open_risk
            total_open_margin = core_open_margin + compound_open_margin
            external_headroom = max(Decimal(0), equity - total_open_risk)
            snapshot = AccountRiskSnapshot(
                account_binding_id="phase22-v4-compound-shadow",
                equity=equity,
                margin_used=total_open_margin,
                free_margin=max(Decimal(0), equity - total_open_margin),
                open_stop_worst_case_loss=total_open_risk,
                open_floating_loss=Decimal(0),
                pending_broker_worst_case_loss=Decimal(0),
                qore_authorizable_headroom=min(headroom, external_headroom),
                provider_budget=_Budget(
                    provider_headroom=equity,
                    max_risk_at_any_time=equity,
                    active_mll=Decimal(0),
                    hard_breach=equity <= 0,
                ),
                reconciled_at=epoch.market_decision_at,
            )
            auth = risk_engine.authorize(
                request,
                snapshot,
                now=epoch.market_decision_at,
            )
            if auth.decision is RiskDecision.REJECT:
                rejected += 1
                blockers["QORE_RISK_REJECTED_COMPOUND_SEED"] += 1
                continue
            if auth.decision is RiskDecision.ALLOW:
                allowed += 1
            else:
                reduced += 1
            event = outcomes[signal]
            source_snapshot = tuple(sorted(source_traders))
            if any(item != candidate.trader_id for item in source_snapshot):
                cross_trader += 1
            risk_engine.record_full_fill(auth.authorization_id)
            reservation = next(
                (
                    item
                    for item in risk_engine.reservations()
                    if item.authorization.authorization_id
                    == auth.authorization_id
                ),
                None,
            )
            if reservation is None:
                raise CiboCapitalManagementError(
                    "compound Risk reservation disappeared after fill"
                )
            state = reservation.state.value
            if state == "filled-unreconciled":
                risk_engine.reconcile_fill(auth.authorization_id)
            elif state != "released":
                raise CiboCapitalManagementError(
                    "compound Risk fill reached unexpected reservation state: "
                    + state
                )
            open_rows[signal] = _Open(
                signal_fingerprint=signal,
                trader_id=candidate.trader_id,
                exit_at=event.exit_at,
                authorization_id=auth.authorization_id,
                authorized_volume=auth.authorized_volume,
                authorized_stop_risk_usd=auth.monetary_stop_loss,
                authorized_margin_usd=auth.margin_reserved,
                gross_structural_outcome_r=event.gross_structural_outcome_r,
                provider_cost_usd=(
                    candidate.projection.provider_envelope.execution_cost_per_volume_usd
                    * auth.authorized_volume
                ),
                protected_loss_reserve_usd=protected_loss_reserve_usd(
                    auth.monetary_stop_loss
                ),
                source_traders_before_entry=source_snapshot,
            )
            # The open position is represented explicitly in open_rows and
            # therefore in subsequent AccountRiskSnapshot open-risk/margin.

    if core_settlements or open_rows:
        final_clock = max(
            [item.capital_released_at for item in core_settlements]
            + [item.exit_at for item in open_rows.values()]
        )
        settle_until(final_clock)

    by_trader: dict[str, Decimal] = defaultdict(Decimal)
    entries: Counter[str] = Counter()
    pnl_rows = [
        item.realized_net_pnl_usd
        for item in core_execution.books.cma_settlement.settlements
    ]
    for item in trades:
        by_trader[item.trader_id] += item.incremental_realized_pnl_usd
        entries[item.trader_id] += 1
        pnl_rows.append(item.incremental_realized_pnl_usd)
    positives = sum((item for item in pnl_rows if item > 0), Decimal(0))
    losses = -sum((item for item in pnl_rows if item < 0), Decimal(0))
    pf = None if losses == 0 else positives / losses

    admitted = sum(
        1 for item in core_execution.books.cma_settlement.settlements
        if item.realized_net_pnl_usd > 0
    )
    applied = len(trades)

    final_observed_at = max(
        (
            [epoch.market_decision_at for epoch in plan.epochs]
            + [item.capital_released_at for item in core_settlements]
            + [item.exit_at for item in trades]
        )
    )
    postrun_receipts = build_capital_science_postrun_receipts(
        observed_at=final_observed_at,
        ending_capital_usd=core_execution.final_realized_capital_usd + incremental,
        net_realized_pnl_usd=(
            core_execution.final_realized_capital_usd + incremental - initial
        ),
        settlement_rows=tuple(
            (
                item.signal_fingerprint,
                item.trader_id,
                item.realized_net_pnl_usd,
            )
            for item in core_execution.books.cma_settlement.settlements
        )
        + tuple(
            (
                item.signal_fingerprint,
                item.trader_id,
                item.incremental_realized_pnl_usd,
            )
            for item in trades
        ),
    )
    capital_science_receipts.extend(postrun_receipts)
    capital_science_functions = aggregate_capital_science_receipts(
        capital_science_receipts
    )

    functions = (
        {
            "function_code": "GEN-C1_COMPOUND_CAPITAL",
            "function_type": "COMPOUND",
            "status": "APPLIED" if admitted else "FAIL_CLOSED",
            "eligible_epochs": len(plan.epochs),
            "invoked_count": len(plan.epochs),
            "executed_count": admitted,
            "blocked_count": 0 if admitted else len(plan.epochs),
            "reason": (
                "positive terminal Core settlements admitted as realized-profit-only "
                "compound capacity"
                if admitted
                else "no positive realized Core settlement existed before deployment"
            ),
        },
        {
            "function_code": "GEN-C3_CORE_COMPOUND_PORTFOLIO",
            "function_type": "COMPOUND_PORTFOLIO",
            "status": "APPLIED" if applied else "FAIL_CLOSED",
            "eligible_epochs": selected,
            "invoked_count": selected,
            "executed_count": applied,
            "blocked_count": rejected,
            "reason": (
                "account-local realized-profit pool was redeployed across the "
                f"Core selection surface; cross-Trader deployments={cross_trader}"
                if applied
                else (
                    "rational redeploy utility/preservation/governance evidence "
                    "did not authorize incremental capital"
                    if lab_require_rational_redeploy
                    else "realized-profit pool never reached one legal minimum seed"
                )
            ),
        },
        {
            "function_code": "GEN-C5_SEQUENTIAL_COMPOUNDING",
            "function_type": "COMPOUND",
            "status": "APPLIED" if applied else "FAIL_CLOSED",
            "eligible_epochs": selected,
            "invoked_count": selected,
            "executed_count": applied,
            "blocked_count": rejected,
            "reason": (
                "causally prior realized profit funded later incremental seeds"
                if applied
                else (
                    "sequential compound remained fail-closed because rational "
                    "redeploy policy authorization was absent"
                    if lab_require_rational_redeploy
                    else "no later selected opportunity could consume realized-profit capacity"
                )
            ),
        },
        {
            "function_code": "GEN-C6_INTERNAL_CAPITAL_MARKET",
            "function_type": "COMPOUND_PORTFOLIO",
            "status": "JUSTIFIED_NOT_APPLICABLE",
            "eligible_epochs": 0,
            "invoked_count": len(plan.epochs),
            "executed_count": 0,
            "blocked_count": 0,
            "reason": (
                "this ablation measures the frozen Core selection plus a shared "
                "Compound Portfolio; it does not replace Core selection with a "
                "new scarcity-ranking policy"
            ),
        },
    ) + capital_science_functions

    return CompoundPortfolioLaneResult(
        core_ending_capital_usd=core_execution.final_realized_capital_usd,
        compound_incremental_pnl_usd=incremental,
        ending_capital_usd=core_execution.final_realized_capital_usd + incremental,
        net_realized_pnl_usd=(
            core_execution.final_realized_capital_usd + incremental - initial
        ),
        compound_selected_count=selected,
        compound_allowed_count=allowed,
        compound_reduced_count=reduced,
        compound_rejected_count=rejected,
        compound_settled_count=len(trades),
        cross_trader_compound_deployments=cross_trader,
        profit_factor=pf,
        trader_incremental_pnl_usd=tuple(sorted(by_trader.items())),
        trader_compound_entries=tuple(sorted(entries.items())),
        trades=tuple(trades),
        blocker_reasons=tuple(sorted(blockers.items())),
        function_accountability=functions,
        capital_science_receipts=tuple(
            item.payload() for item in capital_science_receipts
        ),
        rational_redeploy_gate_enabled=lab_require_rational_redeploy,
        noncertifying_research_redeploy_enabled=(
            lab_allow_noncertifying_research_redeploy
        ),
        protected_reinvestment_policy_id=POLICY_ID,
    )
