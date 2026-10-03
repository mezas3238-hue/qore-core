#!/usr/bin/env python3
"""Complete the CIBO Compound Trader Lab chain CC10..CC16 -> PC01.

Prerequisite CC01..CC09 is re-executed through the existing real Trader Lab
audit. Every later gate consumes the exact previous PASS receipt. The audit
uses the retained reused-holdout population for descriptive mechanics and a
clearly labelled post-freeze counterfactual policy replay for GEN-C5/C8. It
never relabels historical evidence as forward observed.

PASS means the function executed its contract correctly. A domain disposition
may still be ineligible/paused when the supplied evidence demands that result.

Research-only. No broker mutation, orders, sizing, Risk authority, LIVE,
Production, real capital, certification, deployment, or merge authority.
"""

from __future__ import annotations

import argparse
import json
import tempfile
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from cibo_compound_trader_lab_audit import (
    TRADERS,
    CompoundTraderLabAudit,
    _canonical_sha,
    _constant_summary_payload,
    _dt,
    _must,
    _output_sha,
    _research_capital_proxy,
    _settlement_state,
    _t19,
    _test_identity,
    _useful_compound_capital_usd,
)

from qore.infrastructure.cibo_adaptive_compound_speed_shadow import (
    Genc8AdaptiveSpeedFact,
    Genc8FactKind,
    Genc8RegimeEvidence,
    Genc8Severity,
    evaluate_genc8_adaptive_compound_speed,
)
from qore.infrastructure.cibo_ce2i_regime_selector import (
    CiboRegimePosture,
    ProviderCondition,
)
from qore.infrastructure.cibo_compound_capital import CompoundCapitalState
from qore.infrastructure.cibo_compound_constant_statistics import (
    CompoundConstantObservation,
    CompoundConstantSystem,
    summarize_compound_constants,
)
from qore.infrastructure.cibo_compound_cycle_replay import (
    BaseSettlementEvent,
    ClassificationEvent,
    PolicyProtectFloorEvent,
    ProtectProfitEvent,
    replay_compound_cycle,
)
from qore.infrastructure.cibo_compound_cycle_state import (
    initialize_compound_cycle,
)
from qore.infrastructure.cibo_compound_path_monte_carlo import (
    CompoundMonteCarloEpisode,
    CompoundMonteCarloInitialState,
)
from qore.infrastructure.cibo_compound_temporal_replication import (
    CompoundTemporalFold,
    run_compound_temporal_replication,
)
from qore.infrastructure.cibo_compound_temporal_replication_gate import (
    CompoundTemporalPopulationDisposition,
    assess_compound_temporal_population,
)
from qore.infrastructure.cibo_core_compound_portfolio import (
    QoreCoreCompoundPortfolio,
)
from qore.infrastructure.cibo_internal_capital_market import Genc6Action
from qore.infrastructure.cibo_marginal_capital_utility_evidence import (
    MarginalCapitalUtilityEvidence,
)
from qore.infrastructure.cibo_sequential_compounding_shadow_policy import (
    evaluate_genc5_sequential_compounding_shadow,
)
from qore.infrastructure.cibo_sequential_compounding_shadow_store import (
    DurableGenc5SequentialCompoundingShadowStore,
    Genc5ShadowDecisionSeal,
)
from qore.infrastructure.trader_lab.cibo_functional_receipt import (
    CiboTraderLabExecutionStatus,
    CiboTraderLabFunctionGate,
    build_cibo_function_execution,
    issue_trader_lab_cibo_function_pass,
)

POLICY_CAPABILITY_REPLAY_AT = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)

REMAINING_COMPOUND_GATES = (
    CiboTraderLabFunctionGate.CC10_TEMPORAL_REPLICATION,
    CiboTraderLabFunctionGate.CC11_TEMPORAL_REPLICATION_GATE,
    CiboTraderLabFunctionGate.CC12_SEQUENTIAL_COMPOUNDING,
    CiboTraderLabFunctionGate.CC13_INTERNAL_CAPITAL_MARKET,
    CiboTraderLabFunctionGate.CC14_ADAPTIVE_COMPOUND_SPEED,
    CiboTraderLabFunctionGate.CC15_ACCOUNT_CORE_COMPOUND_PORTFOLIO,
    CiboTraderLabFunctionGate.CC16_COMPOUND_CYCLE_REPLAY,
)
PORTFOLIO_GATE = CiboTraderLabFunctionGate.PC01_QORE_CORE_COMPOUND_PORTFOLIO


def _settled_rows(trace: dict[str, object], trader: str) -> tuple[dict[str, object], ...]:
    raw = trace.get("opportunities")
    if not isinstance(raw, list):
        raise RuntimeError("decision trace opportunities missing")
    rows: list[dict[str, object]] = []
    for row in raw:
        if not isinstance(row, dict) or row.get("trader_id") != trader:
            continue
        settlement = row.get("settlement")
        cma = row.get("cma")
        if not isinstance(settlement, dict) or not isinstance(cma, dict):
            continue
        deployed = settlement.get("capital_deployed_at")
        released = settlement.get("capital_released_at")
        margin = Decimal(str(cma.get("candidate_margin_usd", "0")))
        stop = Decimal(str(cma.get("candidate_stop_risk_usd", "0")))
        if not deployed or not released or margin <= 0 or stop <= 0:
            continue
        rows.append(row)
    ordered = tuple(
        sorted(
            rows,
            key=lambda item: (
                _dt(str(item["settlement"]["capital_deployed_at"])),
                _dt(str(item["settlement"]["capital_released_at"])),
                str(item["signal_fingerprint"]),
            ),
        )
    )
    if len(ordered) < 2:
        raise RuntimeError(f"{trader} needs at least two settled rows for CC10")
    return ordered


def _episode_from_row(
    trader: str,
    row: dict[str, object],
    *,
    suffix: str,
) -> CompoundMonteCarloEpisode:
    settlement = row["settlement"]
    cma = row["cma"]
    assert isinstance(settlement, dict) and isinstance(cma, dict)
    return CompoundMonteCarloEpisode(
        episode_id=f"{trader}:{suffix}:episode",
        deployment_id=f"{trader}:{suffix}:deployment",
        market_event_id=f"{trader}:{suffix}:market",
        decision_id=f"{trader}:{suffix}:decision",
        candidate_id=f"{trader}:{suffix}:candidate",
        trader_id=__import__(
            "qore.infrastructure.account_wide_risk",
            fromlist=["TraderLineage"],
        ).TraderLineage(trader),
        signal_fingerprint=str(row["signal_fingerprint"]),
        deployed_at=_dt(str(settlement["capital_deployed_at"])),
        settled_at=_dt(str(settlement["capital_released_at"])),
        source_generation=1,
        deployed_capital_usd=_research_capital_proxy(row),
        stop_risk_usd=Decimal(str(cma["candidate_stop_risk_usd"])),
        margin_usd=Decimal(str(cma["candidate_margin_usd"])),
        realized_pnl_usd=Decimal(str(settlement["realized_net_pnl_usd"])),
        protected_floor_graduation_usd=Decimal(0),
        floor_evidence_sha256=None,
        market_record_present=True,
        terminal_release_present=True,
        future_leakage_used=False,
    )


def _fold_from_episode(
    trader: str,
    row: dict[str, object],
    episode: CompoundMonteCarloEpisode,
    *,
    fold_id: str,
) -> CompoundTemporalFold:
    pre = row["market_predecision_state"]
    assert isinstance(pre, dict)
    provider = pre["provider_observation"]
    assert isinstance(provider, dict)
    hard_risk = Decimal(str(pre["hard_risk_headroom_usd"]))
    margin_headroom = Decimal(str(pre["margin_headroom_usd"]))
    initial = CompoundMonteCarloInitialState(
        original_base_usd=Decimal("100"),
        generation_capacity_usd=((1, max(episode.deployed_capital_usd, margin_headroom)),),
        protected_floor_usd=Decimal(0),
        total_stop_risk_capacity_usd=max(episode.stop_risk_usd, hard_risk),
        total_margin_capacity_usd=max(episode.margin_usd, margin_headroom),
    )
    return CompoundTemporalFold(
        fold_id=f"{trader}:{fold_id}",
        start_at=episode.deployed_at - timedelta(microseconds=1),
        end_at=episode.settled_at + timedelta(microseconds=1),
        initial_state=initial,
        episodes=(episode,),
        provider_economics_sha256=_canonical_sha(provider),
    )


def _two_non_overlapping_rows(
    trace: dict[str, object],
    trader: str,
) -> tuple[dict[str, object], dict[str, object]]:
    rows = _settled_rows(trace, trader)
    left = rows[0]
    left_settlement = left["settlement"]
    assert isinstance(left_settlement, dict)
    left_end = _dt(str(left_settlement["capital_released_at"]))
    for right in reversed(rows[1:]):
        settlement = right["settlement"]
        assert isinstance(settlement, dict)
        if _dt(str(settlement["capital_deployed_at"])) > left_end:
            return left, right
    raise RuntimeError(f"{trader} has no non-overlapping CC10 pair")


def _source_lot(portfolio):
    candidates = tuple(
        lot
        for lot in portfolio.compound_ledger.active_lots
        if lot.state
        in {
            CompoundCapitalState.COMPOUNDABLE,
            CompoundCapitalState.ACTIVE_COMPOUND_CAPACITY,
            CompoundCapitalState.RELEASED_COMPOUND_CAPITAL,
        }
        and lot.amount_usd > 0
    )
    if not candidates:
        raise RuntimeError("no compound candidate source lot")
    return sorted(candidates, key=lambda item: item.lot_id)[0]


class CompletionAudit:
    def __init__(self, trace: dict[str, object], source_head: str) -> None:
        self.trace = trace
        self.source_head = source_head
        self.base = CompoundTraderLabAudit(trace, source_head)
        prerequisite = self.base.execute()
        if prerequisite["all_cc01_cc09_pass"] is not True:
            raise RuntimeError("CC10 blocked: CC01-CC09 did not all PASS")
        self.contexts = self.base.contexts
        self.lanes = self.base.lanes
        self.temporal_reports: dict[str, object] = {}
        self.genc5_seals: dict[str, Genc5ShadowDecisionSeal] = {}

    def _issue(
        self,
        trader: str,
        gate: CiboTraderLabFunctionGate,
        output: object,
        semantic: str,
        *,
        domain_verdict: str,
        counterfactual_policy_epoch_replay: bool = False,
    ) -> None:
        lane = self.lanes[trader]
        ctx = self.contexts[trader]
        before = lane.previous_receipt
        now = before.approved_at + timedelta(minutes=1)
        execution = _must(
            build_cibo_function_execution(
                candidate=ctx.candidate,
                function=gate,
                input_sha256=_output_sha(
                    (
                        ctx.candidate.fingerprint.value,
                        gate.value,
                        before.receipt_sha256,
                    )
                ),
                output_sha256=_output_sha(output),
                executed_at=now,
                status=CiboTraderLabExecutionStatus.PASS,
            ),
            gate.value + " execution",
        )
        receipt = _must(
            issue_trader_lab_cibo_function_pass(
                ctx.lifecycle,
                execution,
                previous_receipt=before,
            ),
            gate.value + " PASS receipt",
        )
        if receipt.previous_receipt is not before:
            raise RuntimeError(f"{trader} {gate.value} receipt chain drift")
        lane.previous_receipt = receipt
        lane.reports.append(
            {
                "gate": gate.value,
                "technical_status": "PASS",
                "domain_verdict": domain_verdict,
                "execution_sha256": execution.execution_sha256,
                "receipt_sha256": receipt.receipt_sha256,
                "semantic_assertion": semantic,
                "used_holdout": True,
                "counterfactual_policy_epoch_replay": counterfactual_policy_epoch_replay,
                "forward_observed_claimed": False,
                "economic_replication_claimed": False,
                "certification_claimed": False,
                "broker_mutation": False,
                "orders": False,
                "risk_decision": False,
                "sizing": False,
                "live": False,
                "production": False,
                "real_capital": False,
            }
        )

    def cc10(self, trader: str) -> None:
        left, right = _two_non_overlapping_rows(self.trace, trader)
        left_episode = _episode_from_row(trader, left, suffix="cc10-a")
        right_episode = _episode_from_row(trader, right, suffix="cc10-b")
        folds = (
            _fold_from_episode(trader, left, left_episode, fold_id="fold-a"),
            _fold_from_episode(trader, right, right_episode, fold_id="fold-b"),
        )
        report = run_compound_temporal_replication(
            research_id=f"{trader}:cc10:used-holdout-mechanics",
            folds=folds,
            simulations_per_fold=2,
            draws_per_path=1,
            components_per_block=1,
            base_seed=31 + TRADERS.index(trader),
        )
        if (
            report.fold_count != 2
            or report.outcomes_pooled_across_folds
            or report.economic_replication_claimed
            or report.certification_ready
        ):
            raise RuntimeError("CC10 temporal mechanics/governance drift")
        self.temporal_reports[trader] = report
        self._issue(
            trader,
            CiboTraderLabFunctionGate.CC10_TEMPORAL_REPLICATION,
            report,
            "two non-overlapping retained episodes executed under unchanged Compound MC mechanics",
            domain_verdict="DESCRIPTIVE_TEMPORAL_MECHANICS_PASS",
        )

    def cc11(self, trader: str) -> None:
        row = self.lanes[trader].row
        pre = row["market_predecision_state"]
        assert isinstance(pre, dict)
        provider = pre["provider_observation"]
        assert isinstance(provider, dict)
        assessment = assess_compound_temporal_population(
            source_population_sha256=str(self.trace["trace_sha256"]),
            provider_economics_sha256=_canonical_sha(provider),
            forward_observed=False,
            outcomes_pooled=False,
        )
        if assessment.disposition is not (
            CompoundTemporalPopulationDisposition.INELIGIBLE_NOT_FORWARD
        ):
            raise RuntimeError("CC11 reused holdout was incorrectly relabelled")
        if assessment.eligible_for_strict_replication_gate:
            raise RuntimeError("CC11 reused holdout incorrectly unlocked strict gate")
        self._issue(
            trader,
            CiboTraderLabFunctionGate.CC11_TEMPORAL_REPLICATION_GATE,
            assessment,
            "universal temporal gate processed reused holdout and rejected forward relabelling",
            domain_verdict=assessment.disposition.value,
        )

    def _genc5_evidence(self, trader: str) -> MarginalCapitalUtilityEvidence:
        lane = self.lanes[trader]
        if lane.cycle is None:
            raise RuntimeError("CC12 blocked: compound cycle absent")
        portfolio = lane.cycle.core_portfolio
        capacity = (
            portfolio.compoundable_usd
            + portfolio.active_compound_capacity_usd
            + portfolio.released_compound_capital_usd
        )
        source = _source_lot(portfolio)
        request = min(source.amount_usd, capacity) / Decimal(2)
        if request <= 0:
            raise RuntimeError("CC12 capability replay request is not positive")
        row = lane.row
        pre = row["market_predecision_state"]
        assert isinstance(pre, dict)
        provider = pre["provider_observation"]
        assert isinstance(provider, dict)
        return MarginalCapitalUtilityEvidence(
            evidence_id=f"{trader}:cc12:counterfactual-capability-replay",
            decision_at=POLICY_CAPABILITY_REPLAY_AT,
            account_identity=portfolio.account_identity,
            trader_id=source.origin_trader,
            signal_fingerprint=str(row["signal_fingerprint"]),
            source_opportunity_decision_sha256=_canonical_sha(pre),
            source_baseline_policy_record_sha256=_canonical_sha(
                (trader, "CC12_COUNTERFACTUAL_CONTROL")
            ),
            current_compound_capacity_usd=capacity,
            requested_incremental_capital_usd=request,
            expected_incremental_return_usd=Decimal(0),
            incremental_stop_risk_usd=Decimal(0),
            incremental_margin_usd=Decimal(0),
            incremental_execution_cost_usd=Decimal(0),
            incremental_concentration_risk_usd=Decimal(0),
            incremental_drawdown_risk_proxy_usd=Decimal(0),
            incremental_optionality_consumed_usd=Decimal(0),
            expected_capital_minutes=Decimal(1),
            epistemic_uncertainty=Decimal(1),
            provider_evidence_sha256=_canonical_sha(provider),
            expectation_evidence_sha256=_canonical_sha(
                (trader, "NO_OUTCOME_EXPECTATION_USED")
            ),
            factor_evidence_sha256=None,
            duration_evidence_sha256=_canonical_sha((trader, "DURATION_UNKNOWN")),
            execution_evidence_sha256=_canonical_sha((trader, "EXECUTION_UNKNOWN")),
            optionality_evidence_sha256=_canonical_sha((trader, "OPTIONALITY_UNKNOWN")),
        )

    def cc12(self, trader: str) -> None:
        lane = self.lanes[trader]
        if lane.cycle is None:
            raise RuntimeError("CC12 blocked: compound cycle absent")
        portfolio = lane.cycle.core_portfolio
        source = _source_lot(portfolio)
        evidence = self._genc5_evidence(trader)
        decision = evaluate_genc5_sequential_compounding_shadow(
            portfolio=portfolio,
            evidence=evidence,
            source_lot_id=source.lot_id,
            decision_id=f"{trader}:cc12:genc5",
        )
        with tempfile.TemporaryDirectory(prefix="qore-cibo-genc5-") as root:
            store = DurableGenc5SequentialCompoundingShadowStore(
                Path(root) / "genc5.json"
            )
            book = store.seal(
                decision,
                sealed_at=POLICY_CAPABILITY_REPLAY_AT + timedelta(seconds=1),
                expected_generation=0,
            )
            seal = book.seal_for_decision(decision.decision_id)
            if seal is None:
                raise RuntimeError("CC12 GEN-C5 seal missing")
        self.genc5_seals[trader] = seal
        self._issue(
            trader,
            CiboTraderLabFunctionGate.CC12_SEQUENTIAL_COMPOUNDING,
            decision,
            (
                "post-freeze counterfactual capability replay used only "
                "predecision/unknown facts and no retained outcome"
            ),
            domain_verdict=decision.treatment_action.value,
            counterfactual_policy_epoch_replay=True,
        )

    def cc13(self, trader: str) -> None:
        lane = self.lanes[trader]
        if lane.cycle is None:
            raise RuntimeError("CC13 blocked: compound cycle absent")
        _event, decision = self.base._reserve_decision(
            trader,
            suffix="cc13",
            cycle=lane.cycle,
        )
        if decision.treatment_action is not Genc6Action.RESERVE_NO_DEPLOYMENT:
            raise RuntimeError("CC13 empty candidate market did not preserve reserve")
        self._issue(
            trader,
            CiboTraderLabFunctionGate.CC13_INTERNAL_CAPITAL_MARKET,
            decision,
            (
                "internal capital market evaluated the retained account state "
                "and preserved reserve with no legal candidate"
            ),
            domain_verdict=decision.treatment_action.value,
        )

    def cc14(self, trader: str) -> None:
        seal = self.genc5_seals.get(trader)
        if seal is None:
            raise RuntimeError("CC14 blocked: CC12 GEN-C5 seal absent")
        regime = Genc8RegimeEvidence(
            evidence_id=f"{trader}:cc14:stale-research-regime",
            decision_at=seal.decision_at,
            account_provider_key=seal.account_provider_key,
            account_ref=seal.account_ref,
            regime_posture=CiboRegimePosture.HALT_NEW_CAPITAL,
            provider_condition=ProviderCondition.UNAVAILABLE,
            evidence_sha256=_canonical_sha((trader, "STALE_REUSED_HOLDOUT_REGIME")),
            source="TRADER_LAB_REUSED_HOLDOUT",
            policy_version="CAPABILITY_REPLAY_V1",
            calibrated=False,
            capital_eligible=False,
        )
        facts = tuple(
            Genc8AdaptiveSpeedFact(
                fact_id=f"{trader}:cc14:{kind.value.lower()}",
                decision_at=seal.decision_at,
                account_provider_key=seal.account_provider_key,
                account_ref=seal.account_ref,
                kind=kind,
                severity=Genc8Severity.UNKNOWN,
                evidence_sha256=_canonical_sha((trader, kind.value, "UNKNOWN")),
                source="TRADER_LAB_REUSED_HOLDOUT",
                model_id="CAPABILITY_REPLAY_UNKNOWN",
                calibrated=False,
                capital_eligible=False,
            )
            for kind in Genc8FactKind
        )
        decision = evaluate_genc8_adaptive_compound_speed(
            decision_id=f"{trader}:cc14:genc8",
            genc5=seal,
            regime=regime,
            facts=facts,
        )
        if decision.treatment_posture.value != "PAUSE":
            raise RuntimeError("CC14 stale/unknown evidence must bind PAUSE")
        self._issue(
            trader,
            CiboTraderLabFunctionGate.CC14_ADAPTIVE_COMPOUND_SPEED,
            decision,
            (
                "adaptive speed consumed canonical post-freeze GEN-C5 seal and "
                "conservatively paused on stale/unknown research evidence"
            ),
            domain_verdict=decision.treatment_posture.value,
            counterfactual_policy_epoch_replay=True,
        )

    def cc15(self, trader: str) -> None:
        lane = self.lanes[trader]
        if lane.cycle is None:
            raise RuntimeError("CC15 blocked: compound cycle absent")
        portfolio = lane.cycle.core_portfolio
        if portfolio.runtime_authority or portfolio.cross_account_transfer_authority:
            raise RuntimeError("CC15 account portfolio authority drift")
        if portfolio.current_economic_value_usd != (
            portfolio.compound_ledger.current_economic_value_usd
        ):
            raise RuntimeError("CC15 account portfolio economic-value drift")
        self._issue(
            trader,
            CiboTraderLabFunctionGate.CC15_ACCOUNT_CORE_COMPOUND_PORTFOLIO,
            portfolio,
            (
                "canonical account Core Compound Portfolio reconciled ledger "
                "and protected floor as read-only economic view"
            ),
            domain_verdict="ACCOUNT_PORTFOLIO_RECONCILED",
        )

    def cc16(self, trader: str) -> None:
        lane = self.lanes[trader]
        row = lane.row
        settlement = row["settlement"]
        assert isinstance(settlement, dict)
        at = _dt(str(settlement["observed_at"]))
        blank = initialize_compound_cycle(
            account_identity=_test_identity(trader),
            opening_original_base_usd=Decimal("100"),
            t19_ledger=_t19(row),
        )
        cma = _settlement_state(row, lane_index=TRADERS.index(trader) + 1)
        amount = cma.realized_net_pnl_usd
        protected = amount / Decimal(4)
        remainder = amount - protected
        events = (
            BaseSettlementEvent(
                event_id=f"{trader}:cc16:origin",
                occurred_at=at,
                trader_id=__import__(
                    "qore.infrastructure.account_wide_risk",
                    fromlist=["TraderLineage"],
                ).TraderLineage(trader),
                settlement=cma,
            ),
            ProtectProfitEvent(
                event_id=f"{trader}:cc16:protect",
                occurred_at=at + timedelta(microseconds=1),
                source_lot_id=f"{trader}:cc16:origin:gen1",
                amount_usd=protected,
            ),
            PolicyProtectFloorEvent(
                event_id=f"{trader}:cc16:policy",
                occurred_at=at + timedelta(microseconds=2),
                tranche_id=f"{trader}:cc16:protect:tranche",
                policy_id="TRADER_LAB_REUSED_HOLDOUT_RESEARCH_FLOOR",
                policy_sha256=_canonical_sha((trader, "cc16-policy")),
            ),
            ClassificationEvent(
                event_id=f"{trader}:cc16:compoundable",
                occurred_at=at + timedelta(microseconds=3),
                source_lot_id=f"{trader}:cc16:protect:remainder",
                to_state=CompoundCapitalState.COMPOUNDABLE,
                amount_usd=remainder,
            ),
            ClassificationEvent(
                event_id=f"{trader}:cc16:active",
                occurred_at=at + timedelta(microseconds=4),
                source_lot_id=f"{trader}:cc16:compoundable:moved",
                to_state=CompoundCapitalState.ACTIVE_COMPOUND_CAPACITY,
                amount_usd=remainder,
            ),
        )
        replay = replay_compound_cycle(initial_state=blank, events=events)
        if (
            replay.event_count != 5
            or not replay.chronological
            or replay.future_leakage_used
            or not replay.reconciliation.accounting_integrity_pass
        ):
            raise RuntimeError("CC16 compound replay integrity drift")
        self._issue(
            trader,
            CiboTraderLabFunctionGate.CC16_COMPOUND_CYCLE_REPLAY,
            replay,
            (
                "exact chronological replay reproduced retained settlement -> "
                "floor -> active compound path with zero accounting residual"
            ),
            domain_verdict="REPLAY_RECONCILED",
        )

    def pc01(self) -> tuple[QoreCoreCompoundPortfolio, object]:
        accounts = tuple(
            self.lanes[trader].cycle.core_portfolio
            for trader in TRADERS
            if self.lanes[trader].cycle is not None
        )
        if len(accounts) != len(TRADERS):
            raise RuntimeError("PC01 blocked: missing account portfolio")
        global_portfolio = QoreCoreCompoundPortfolio(accounts=accounts)
        observations = tuple(
            CompoundConstantObservation(
                observation_id=account.account_identity.account_ref,
                source_capital_usd=account.admitted_realized_profit_usd,
                useful_output_capital_usd=_useful_compound_capital_usd(
                    account.compound_ledger
                ),
            )
            for account in accounts
        )
        summary = summarize_compound_constants(
            system=CompoundConstantSystem.COMPOUND_PORTFOLIO,
            observations=observations,
        )
        if global_portfolio.total_admitted_realized_profit_usd != (
            summary.total_source_capital_usd
        ):
            raise RuntimeError("PC01 portfolio source-capital aggregate drift")
        if global_portfolio.read_only is not True:
            raise RuntimeError("PC01 global portfolio must remain read-only")
        for trader in TRADERS:
            self._issue(
                trader,
                PORTFOLIO_GATE,
                (
                    global_portfolio.total_admitted_realized_profit_usd,
                    global_portfolio.total_current_economic_value_usd,
                    global_portfolio.total_protected_floor_usd,
                    summary.logical_values(),
                ),
                (
                    "global Core Compound Portfolio aggregated all seven account "
                    "domains without cross-account transfer authority"
                ),
                domain_verdict="GLOBAL_PORTFOLIO_RECONCILED",
            )
        return global_portfolio, summary

    def execute(self) -> dict[str, object]:
        methods = (
            self.cc10,
            self.cc11,
            self.cc12,
            self.cc13,
            self.cc14,
            self.cc15,
            self.cc16,
        )
        for gate, method in zip(REMAINING_COMPOUND_GATES, methods, strict=True):
            for trader in TRADERS:
                before = self.lanes[trader].previous_receipt
                method(trader)
                after = self.lanes[trader].previous_receipt
                if after.function is not gate:
                    raise RuntimeError(f"{trader} did not receive {gate.value}")
                if after.previous_receipt is not before:
                    raise RuntimeError(f"{trader} {gate.value} did not consume prior PASS")

        global_portfolio, portfolio_summary = self.pc01()
        lanes: dict[str, object] = {}
        for trader in TRADERS:
            lane = self.lanes[trader]
            if len(lane.reports) != 17:
                raise RuntimeError(
                    f"{trader} has {len(lane.reports)} CC gates; expected 17"
                )
            if lane.previous_receipt.function is not PORTFOLIO_GATE:
                raise RuntimeError(f"{trader} missing PC01 PASS receipt")
            lanes[trader] = {
                "status": "PASS",
                "compound_gate_count": 16,
                "portfolio_gate_count": 1,
                "gates": lane.reports,
                "final_receipt_sha256": lane.previous_receipt.receipt_sha256,
            }

        return {
            "schema": "qore.cibo.compound-trader-lab-completion.v1",
            "source_trace_sha256": self.trace["trace_sha256"],
            "source_head_sha": self.source_head,
            "candidate_count": len(TRADERS),
            "all_cc01_cc16_pass": True,
            "all_pc01_pass": True,
            "all_compound_and_portfolio_functions_pass": True,
            "compound_gate_count": 16,
            "portfolio_gate_count": 1,
            "compound_portfolio_constant_summary": _constant_summary_payload(
                portfolio_summary
            ),
            "global_portfolio": {
                "account_count": len(global_portfolio.accounts),
                "total_admitted_realized_profit_usd": format(
                    global_portfolio.total_admitted_realized_profit_usd,
                    "f",
                ),
                "total_current_economic_value_usd": format(
                    global_portfolio.total_current_economic_value_usd,
                    "f",
                ),
                "total_protected_floor_usd": format(
                    global_portfolio.total_protected_floor_usd,
                    "f",
                ),
                "read_only": global_portfolio.read_only,
                "cross_account_transfer_authority": (
                    global_portfolio.cross_account_transfer_authority
                ),
                "runtime_authority": global_portfolio.runtime_authority,
            },
            "lanes": lanes,
            "authority_chain": ["OWNER", "TRADER_LAB", "CIBO"],
            "governance": {
                "used_holdout": True,
                "burned_research": True,
                "counterfactual_policy_epoch_replay": True,
                "historical_policy_availability_claimed": False,
                "forward_observed_claimed": False,
                "economic_replication_claimed": False,
                "certification_claimed": False,
                "owner_global_approval_claimed": False,
                "broker_mutation": False,
                "orders": False,
                "risk_decision": False,
                "sizing": False,
                "live": False,
                "production": False,
                "real_capital": False,
                "merge_authority": False,
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
    report = CompletionAudit(trace, args.source_head).execute()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "all_cc01_cc16_pass": report["all_cc01_cc16_pass"],
                "all_pc01_pass": report["all_pc01_pass"],
                "compound_portfolio_constant_summary": (
                    report["compound_portfolio_constant_summary"]
                ),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
