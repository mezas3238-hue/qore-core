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

LANE_ID = "FULL_CIBO_COMPOUND_PORTFOLIO"


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
) -> CompoundPortfolioLaneResult:
    """Add causal profit-funded seeds without changing Core policy selection."""

    initial = FROZEN_CIBO_USD60_SIX_MONTH_PROTOCOL.initial_capital_usd
    core_realized = initial
    pool = Decimal(0)
    incremental = Decimal(0)
    source_traders: set[str] = set()
    risk_engine = AccountWideRiskEngine()
    open_rows: dict[str, _Open] = {}
    trades: list[CompoundPortfolioTrade] = []
    blockers: Counter[str] = Counter()
    selected = allowed = reduced = rejected = cross_trader = 0

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
        nonlocal core_index, core_realized, pool, incremental
        while (
            core_index < len(core_settlements)
            and core_settlements[core_index].capital_released_at <= clock
        ):
            item = core_settlements[core_index]
            core_realized += item.realized_net_pnl_usd
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
            if pool < 0:
                raise CiboCapitalManagementError(
                    "compound pool became negative despite fail-closed funding"
                )
            risk_engine.reconcile_terminal_release(item.authorization_id)
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

        for signal in policy.selected_signal_fingerprints:
            selected += 1
            candidate = by_signal[signal]
            opportunity = candidate.projection.candidate.capital_input.opportunity
            volume = minimum_seed_volume(opportunity)
            risk = volume * opportunity.stop_loss_per_volume
            margin = volume * opportunity.margin_per_volume
            cost = (
                candidate.projection.provider_envelope.execution_cost_per_volume_usd
                * volume
            )
            reserved = risk_engine.active_reserved_stop_risk()
            available = max(Decimal(0), pool - reserved)
            if risk + cost > available:
                blockers["REALIZED_PROFIT_POOL_BELOW_MINIMUM_SEED_PLUS_COST"] += 1
                rejected += 1
                continue
            equity = max(Decimal(0), core_realized + incremental)
            headroom = min(equity, max(Decimal(0), available - cost))
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
            external_headroom = max(Decimal(0), equity - core_open_risk)
            snapshot = AccountRiskSnapshot(
                account_binding_id="phase22-v4-compound-shadow",
                equity=equity,
                margin_used=core_open_margin,
                free_margin=max(Decimal(0), equity - core_open_margin),
                open_stop_worst_case_loss=core_open_risk,
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
                source_traders_before_entry=source_snapshot,
            )

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
    functions = (
        {
            "function_code": "GEN-C1_COMPOUND_CAPITAL",
            "function_type": "COMPOUND",
            "status": "APPLIED" if admitted else "FAIL_CLOSED",
            "eligible_epochs": len(plan.epochs),
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
            "executed_count": applied,
            "blocked_count": rejected,
            "reason": (
                "account-local realized-profit pool was redeployed across the "
                f"Core selection surface; cross-Trader deployments={cross_trader}"
                if applied
                else "realized-profit pool never reached one legal minimum seed"
            ),
        },
        {
            "function_code": "GEN-C5_SEQUENTIAL_COMPOUNDING",
            "function_type": "COMPOUND",
            "status": "APPLIED" if applied else "FAIL_CLOSED",
            "eligible_epochs": selected,
            "executed_count": applied,
            "blocked_count": rejected,
            "reason": (
                "causally prior realized profit funded later incremental seeds"
                if applied
                else "no later selected opportunity could consume realized-profit capacity"
            ),
        },
        {
            "function_code": "GEN-C6_INTERNAL_CAPITAL_MARKET",
            "function_type": "COMPOUND_PORTFOLIO",
            "status": "JUSTIFIED_NOT_APPLICABLE",
            "eligible_epochs": 0,
            "executed_count": 0,
            "blocked_count": 0,
            "reason": (
                "this ablation measures the frozen Core selection plus a shared "
                "Compound Portfolio; it does not replace Core selection with a "
                "new scarcity-ranking policy"
            ),
        },
    )

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
    )
