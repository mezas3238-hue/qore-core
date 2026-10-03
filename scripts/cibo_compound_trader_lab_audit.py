#!/usr/bin/env python3
"""Trader Lab runtime audit for CIBO compound gates CC01..CC09.

Prerequisite: CF01..CF20 must PASS first for every retained Trader lane.  This
script reconstructs that exact authority chain in-memory, then continues from
the CF20 PASS receipt.  It stops at the first failing compound gate.

Historical/reused-holdout values are used only as research inputs.  Replay
ordinal position/deal identifiers are explicitly synthetic identifiers for the
local TEST ledger; they are not broker-fill claims.  CC08/CC09 use a documented
counterfactual research capital proxy derived from the retained candidate margin.

No broker mutation, orders, Risk decision, sizing, LIVE, Production, real
capital, deployment authority, certification authority, or merge authority.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path

from cibo_full_function_trader_lab_audit import FullFunctionAudit, TRADERS

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_account_capital_mission import CiboAccountCapitalIdentity
from qore.infrastructure.cibo_capital_management_authority import CapitalSource
from qore.infrastructure.cibo_capital_source_ledger import CapitalSourceLedger
from qore.infrastructure.cibo_ce2i_portfolio_allocation_ledger import (
    PortfolioAllocationLedger,
)
from qore.infrastructure.cibo_cma_settlement_ledger import (
    CmaSettlementRecord,
    CmaSettlementState,
    apply_settlement,
)
from qore.infrastructure.cibo_compound_capital import (
    CompoundCapitalState,
    CompoundRealizedProfitEvidence,
    create_realized_profit_lot,
)
from qore.infrastructure.cibo_compound_cycle_replay import (
    BaseSettlementEvent,
    ClassificationEvent,
    ProtectProfitEvent,
)
from qore.infrastructure.cibo_compound_cycle_state import (
    classify_compound_capital,
    ingest_base_settlement,
    initialize_compound_cycle,
    policy_protect_floor,
    protect_compound_capital,
)
from qore.infrastructure.cibo_compound_floor import ProtectedCapitalFloorLedger
from qore.infrastructure.cibo_compound_funding_coordination import (
    IntegratedCompoundFundingState,
    apply_funded_internal_market_decision,
)
from qore.infrastructure.cibo_compound_path_history import (
    materialize_compound_path_history,
)
from qore.infrastructure.cibo_compound_path_monte_carlo import (
    CompoundMonteCarloEpisode,
    CompoundMonteCarloInitialState,
    run_compound_path_monte_carlo,
)
from qore.infrastructure.cibo_compound_portfolio_ledger import CompoundPortfolioLedger
from qore.infrastructure.cibo_compound_real_population_binding import (
    CompoundPopulationEvidenceKind,
    TraderLabBurnedResearchCompoundRecord,
    bind_trader_lab_burned_research_population,
)
from qore.infrastructure.cibo_core_compound_portfolio import AccountCoreCompoundPortfolio
from qore.infrastructure.cibo_integrated_capital_truth import (
    RealizedProfitEquivalenceBinding,
)
from qore.infrastructure.cibo_internal_capital_market import (
    GENC6_RESERVE_ID,
    Genc6Action,
    Genc6ReserveAlternative,
    build_capital_scarcity_event,
    build_genc6_portfolio_state,
    evaluate_genc6_internal_capital_market_shadow,
)
from qore.infrastructure.cibo_compound_market_cycle import (
    apply_internal_capital_market_decision,
)
from qore.infrastructure.market_test_environment import MarketRuntimeEnvironment
from qore.infrastructure.trader_lab.cibo_functional_receipt import (
    CiboTraderLabExecutionStatus,
    CiboTraderLabFunctionGate,
    TraderLabCiboFunctionPassReceipt,
    build_cibo_function_execution,
    issue_trader_lab_cibo_function_pass,
)
from qore.kernel.result import Failure, Success


COMPOUND_GATES = tuple(
    gate
    for gate in CiboTraderLabFunctionGate
    if gate.value.startswith("cc")
)[:9]


def _must(result: object, label: str):
    if isinstance(result, Success):
        return result.value
    if isinstance(result, Failure):
        raise RuntimeError(f"{label} failed: {result.error}")
    raise RuntimeError(f"{label} returned unexpected type {type(result).__name__}")


def _dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise RuntimeError("retained timestamp is not timezone-aware")
    return parsed


def _canonical_sha(value: object) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    ).encode("utf-8")
    return "sha256:" + sha256(raw).hexdigest()


def _bare_sha(value: object) -> str:
    return _canonical_sha(value)[7:]


def _logical(value: object) -> object:
    logical = getattr(value, "logical_values", None)
    if callable(logical):
        return _logical(logical())
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): _logical(v) for k, v in sorted(value.items())}
    if isinstance(value, (tuple, list)):
        return [_logical(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _output_sha(value: object) -> str:
    return _bare_sha(_logical(value))


def _trader(value: str) -> TraderLineage:
    return TraderLineage(value)


def _positive_rows(trace: dict[str, object]) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    rows = trace.get("opportunities")
    if not isinstance(rows, list):
        raise RuntimeError("decision trace opportunities missing")
    for row in rows:
        if not isinstance(row, dict):
            continue
        trader = row.get("trader_id")
        settlement = row.get("settlement")
        if (
            trader in TRADERS
            and isinstance(settlement, dict)
            and Decimal(str(settlement.get("realized_net_pnl_usd", "0"))) > 0
            and trader not in result
        ):
            result[str(trader)] = row
    missing = tuple(trader for trader in TRADERS if trader not in result)
    if missing:
        raise RuntimeError("positive retained settlement missing for " + ",".join(missing))
    return result


def _test_identity(trader: str) -> CiboAccountCapitalIdentity:
    return CiboAccountCapitalIdentity(
        provider_key="trader-lab-replay",
        account_ref="compound-" + trader.lower(),
        environment=MarketRuntimeEnvironment.TEST,
    )


def _settlement_state(
    row: dict[str, object],
    *,
    lane_index: int,
) -> CmaSettlementState:
    settlement = row["settlement"]
    assert isinstance(settlement, dict)
    signal = str(row["signal_fingerprint"])
    # These integers are replay ordinals required by the local settlement
    # contract. They are deliberately not represented as broker IDs.
    position_id = 1_000_000 + lane_index
    deal_id = 2_000_000 + lane_index
    state = CmaSettlementState(
        signal_fingerprint=signal,
        position_id=position_id,
    )
    return apply_settlement(
        state,
        CmaSettlementRecord(
            event="CTRADER_DEMO_EXIT_SETTLEMENT",
            deal_id=deal_id,
            signal_fingerprint=signal,
            position_id=position_id,
            net_profit_usd=Decimal(str(settlement["realized_net_pnl_usd"])),
            position_open_after=False,
        ),
    )


def _t19(row: dict[str, object]) -> PortfolioAllocationLedger:
    pre = row["market_predecision_state"]
    assert isinstance(pre, dict)
    stop = Decimal(str(pre["hard_risk_headroom_usd"]))
    margin = Decimal(str(pre["margin_headroom_usd"]))
    if stop <= 0 or margin <= 0:
        raise RuntimeError("retained headroom must be positive")
    return PortfolioAllocationLedger(
        total_stop_risk_capacity_usd=stop,
        total_margin_capacity_usd=margin,
        concentration_limit_by_group=(("TRADER_LAB_REPLAY", stop),),
    )


def _research_capital_proxy(row: dict[str, object]) -> Decimal:
    cma = row["cma"]
    assert isinstance(cma, dict)
    value = Decimal(str(cma["candidate_margin_usd"]))
    if value <= 0:
        raise RuntimeError("retained candidate margin must be positive")
    return value


@dataclass
class CompoundLane:
    previous_receipt: TraderLabCiboFunctionPassReceipt
    row: dict[str, object]
    reports: list[dict[str, object]] = field(default_factory=list)
    ledger: CompoundPortfolioLedger | None = None
    floor: ProtectedCapitalFloorLedger | None = None
    cycle: object | None = None
    account_portfolio: AccountCoreCompoundPortfolio | None = None
    mc_summary: object | None = None
    research_binding: object | None = None


class CompoundTraderLabAudit:
    def __init__(self, trace: dict[str, object], source_head: str) -> None:
        self.trace = trace
        self.source_head = source_head
        functional = FullFunctionAudit(trace, source_head)
        functional_report = functional.execute()
        if functional_report["all_functions_pass"] is not True:
            raise RuntimeError("compound chain blocked: CF01-CF20 are not all PASS")
        positives = _positive_rows(trace)
        self.contexts = functional.contexts
        self.lanes = {
            trader: CompoundLane(
                previous_receipt=functional.lanes[trader].previous_receipt,
                row=positives[trader],
            )
            for trader in TRADERS
        }

    def _approval_time(self, trader: str, gate: CiboTraderLabFunctionGate) -> datetime:
        prior = self.lanes[trader].previous_receipt
        index = COMPOUND_GATES.index(gate)
        candidate = prior.approved_at + timedelta(minutes=1)
        # Each gate advances exactly once from the immediately prior receipt.
        if index < 0:
            raise RuntimeError("invalid compound gate index")
        return candidate

    def _issue(
        self,
        trader: str,
        gate: CiboTraderLabFunctionGate,
        output: object,
        semantic: str,
        *,
        domain_verdict: str = "OPERABLE",
    ) -> None:
        lane = self.lanes[trader]
        ctx = self.contexts[trader]
        now = self._approval_time(trader, gate)
        execution = _must(
            build_cibo_function_execution(
                candidate=ctx.candidate,
                function=gate,
                input_sha256=_output_sha(
                    (
                        ctx.candidate.fingerprint.value,
                        gate.value,
                        lane.previous_receipt.receipt_sha256,
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
                previous_receipt=lane.previous_receipt,
            ),
            gate.value + " PASS receipt",
        )
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

    def cc01(self, trader: str) -> None:
        lane = self.lanes[trader]
        row = lane.row
        settlement = row["settlement"]
        assert isinstance(settlement, dict)
        account = _test_identity(trader)
        realized_at = _dt(str(settlement["observed_at"]))
        ordinal = TRADERS.index(trader) + 1
        evidence = CompoundRealizedProfitEvidence(
            evidence_id=str(settlement["evidence_id"]),
            account_identity=account,
            origin_trader=_trader(trader),
            signal_fingerprint=str(row["signal_fingerprint"]),
            position_id=1_000_000 + ordinal,
            settlement_deal_ids=(2_000_000 + ordinal,),
            realized_net_profit_usd=Decimal(str(settlement["realized_net_pnl_usd"])),
            realized_at=realized_at,
            source_settlement_sha256=_canonical_sha(settlement),
            settlement_reconciled=True,
            position_closed=True,
            floating_pnl_used_as_capital=False,
        )
        lot = create_realized_profit_lot(
            evidence,
            lot_id=f"{trader}:cc01:realized",
            created_at=realized_at + timedelta(microseconds=1),
        )
        if lot.amount_usd != evidence.realized_net_profit_usd or lot.generation != 1:
            raise RuntimeError("CC01 realized-profit lot identity drift")
        self._issue(
            trader,
            CiboTraderLabFunctionGate.CC01_REALIZED_PROFIT_LOT,
            lot,
            "actual retained positive settlement admitted as GEN1 research lot; replay IDs are local ordinals",
        )

    def cc02(self, trader: str) -> None:
        lane = self.lanes[trader]
        row = lane.row
        settlement = row["settlement"]
        assert isinstance(settlement, dict)
        account = _test_identity(trader)
        realized_at = _dt(str(settlement["observed_at"]))
        ordinal = TRADERS.index(trader) + 1
        evidence = CompoundRealizedProfitEvidence(
            evidence_id=str(settlement["evidence_id"]),
            account_identity=account,
            origin_trader=_trader(trader),
            signal_fingerprint=str(row["signal_fingerprint"]),
            position_id=1_000_000 + ordinal,
            settlement_deal_ids=(2_000_000 + ordinal,),
            realized_net_profit_usd=Decimal(str(settlement["realized_net_pnl_usd"])),
            realized_at=realized_at,
            source_settlement_sha256=_canonical_sha(settlement),
            settlement_reconciled=True,
            position_closed=True,
        )
        lot = create_realized_profit_lot(
            evidence,
            lot_id=f"{trader}:cc02:realized",
            created_at=realized_at + timedelta(microseconds=1),
        )
        ledger = CompoundPortfolioLedger(account_identity=account).admit_realized_profit(
            lot,
            event_id=f"{trader}:cc02:admit",
            occurred_at=realized_at + timedelta(microseconds=2),
        )
        if ledger.current_partition_usd != lot.amount_usd:
            raise RuntimeError("CC02 partition identity drift")
        if ledger.admitted_realized_profit_usd != lot.amount_usd:
            raise RuntimeError("CC02 admitted-profit identity drift")
        lane.ledger = ledger
        self._issue(
            trader,
            CiboTraderLabFunctionGate.CC02_COMPOUND_PORTFOLIO_LEDGER,
            ledger,
            "portfolio ledger admitted exact CC01 realized amount with conserved partition",
        )

    def cc03(self, trader: str) -> None:
        lane = self.lanes[trader]
        if lane.ledger is None:
            raise RuntimeError("CC03 blocked: CC02 ledger absent")
        row = lane.row
        settlement = row["settlement"]
        assert isinstance(settlement, dict)
        at = _dt(str(settlement["observed_at"])) + timedelta(microseconds=3)
        source = lane.ledger.active_lots[0]
        amount = source.amount_usd / Decimal(4)
        if amount <= 0:
            raise RuntimeError("CC03 floor amount is not positive")
        remainder_id = f"{trader}:cc03:remainder"
        ledger = lane.ledger.transition(
            source_lot_id=source.lot_id,
            to_state=CompoundCapitalState.RETIRED_TO_PROTECTED_FLOOR,
            amount_usd=amount,
            moved_lot_id=f"{trader}:cc03:retired",
            remainder_lot_id=remainder_id,
            event_id=f"{trader}:cc03:retire",
            occurred_at=at,
        )
        floor = ProtectedCapitalFloorLedger(
            account_identity=ledger.account_identity
        ).admit_retired_lot(
            ledger.lot(f"{trader}:cc03:retired"),
            tranche_id=f"{trader}:cc03:tranche",
            event_id=f"{trader}:cc03:floor-admit",
            admitted_at=at + timedelta(microseconds=1),
        )
        floor = floor.upgrade_to_policy_protected(
            tranche_id=f"{trader}:cc03:tranche",
            event_id=f"{trader}:cc03:policy",
            occurred_at=at + timedelta(microseconds=2),
            policy_id="TRADER_LAB_REUSED_HOLDOUT_RESEARCH_FLOOR",
            policy_sha256=_canonical_sha(
                (trader, "TRADER_LAB_REUSED_HOLDOUT_RESEARCH_FLOOR")
            ),
        )
        if floor.policy_protected_floor_usd != amount:
            raise RuntimeError("CC03 policy-protected floor identity drift")
        if floor.broker_guaranteed_floor_usd != 0:
            raise RuntimeError("CC03 must not fabricate broker guarantee")
        lane.ledger = ledger
        lane.floor = floor
        self._issue(
            trader,
            CiboTraderLabFunctionGate.CC03_PROTECTED_CAPITAL_FLOOR,
            (ledger, floor),
            "policy floor ratchet works; broker-guaranteed floor remains zero without broker evidence",
        )

    def _build_cycle(self, trader: str):
        lane = self.lanes[trader]
        row = lane.row
        settlement = row["settlement"]
        assert isinstance(settlement, dict)
        at = _dt(str(settlement["observed_at"]))
        state = initialize_compound_cycle(
            account_identity=_test_identity(trader),
            opening_original_base_usd=Decimal("100"),
            t19_ledger=_t19(row),
        )
        cma = _settlement_state(row, lane_index=TRADERS.index(trader) + 1)
        state = ingest_base_settlement(
            state,
            event_id=f"{trader}:cc04:origin",
            occurred_at=at,
            trader_id=_trader(trader),
            settlement=cma,
        )
        total = cma.realized_net_pnl_usd
        protected = total / Decimal(4)
        compoundable = total - protected
        state = protect_compound_capital(
            state,
            event_id=f"{trader}:cc04:protect",
            occurred_at=at + timedelta(microseconds=1),
            source_lot_id=f"{trader}:cc04:origin:gen1",
            amount_usd=protected,
        )
        state = policy_protect_floor(
            state,
            event_id=f"{trader}:cc04:policy",
            occurred_at=at + timedelta(microseconds=2),
            tranche_id=f"{trader}:cc04:protect:tranche",
            policy_id="TRADER_LAB_REUSED_HOLDOUT_RESEARCH_FLOOR",
            policy_sha256=_canonical_sha((trader, "cc04-policy")),
        )
        state = classify_compound_capital(
            state,
            event_id=f"{trader}:cc04:compoundable",
            occurred_at=at + timedelta(microseconds=3),
            source_lot_id=f"{trader}:cc04:protect:remainder",
            to_state=CompoundCapitalState.COMPOUNDABLE,
            amount_usd=compoundable,
        )
        state = classify_compound_capital(
            state,
            event_id=f"{trader}:cc04:active",
            occurred_at=at + timedelta(microseconds=4),
            source_lot_id=f"{trader}:cc04:compoundable:moved",
            to_state=CompoundCapitalState.ACTIVE_COMPOUND_CAPACITY,
            amount_usd=compoundable,
        )
        return state

    def cc04(self, trader: str) -> None:
        lane = self.lanes[trader]
        state = self._build_cycle(trader)
        if state.highest_generation != 1:
            raise RuntimeError("CC04 failed to create GEN1 compound cycle")
        if state.accounting_identity_usd != state.closing_realized_capital_usd:
            raise RuntimeError("CC04 accounting identity drift")
        lane.cycle = state
        self._issue(
            trader,
            CiboTraderLabFunctionGate.CC04_COMPOUND_CYCLE_STATE,
            state,
            "cycle ingested retained positive settlement, protected 25%, and exposed active compound capacity",
        )

    def _reserve_decision(self, trader: str, *, suffix: str, cycle):
        lane = self.lanes[trader]
        row = lane.row
        pre = row["market_predecision_state"]
        assert isinstance(pre, dict)
        provider = pre["provider_observation"]
        assert isinstance(provider, dict)
        decision_at = _dt(str(provider["observed_at"])) + (
            timedelta(minutes=1) if suffix == "cc06" else timedelta(0)
        )
        portfolio = cycle.core_portfolio
        snapshot = build_genc6_portfolio_state(
            snapshot_id=f"{trader}:{suffix}:snapshot",
            decision_at=decision_at,
            portfolio=portfolio,
            t19_ledger=cycle.t19_ledger,
        )
        reserve = Genc6ReserveAlternative(
            alternative_id=GENC6_RESERVE_ID,
            account_identity=cycle.account_identity,
            decision_at=decision_at,
            evidence_facts=(),
        )
        event = build_capital_scarcity_event(
            event_id=f"{trader}:{suffix}:scarcity",
            decision_at=decision_at,
            portfolio_state=snapshot,
            candidates=(),
            reserve_alternative=reserve,
        )
        decision = evaluate_genc6_internal_capital_market_shadow(
            event=event,
            decision_id=f"{trader}:{suffix}:decision",
        )
        if decision.treatment_action is not Genc6Action.RESERVE_NO_DEPLOYMENT:
            raise RuntimeError("empty legal candidate set must preserve capital")
        return event, decision

    def cc05(self, trader: str) -> None:
        lane = self.lanes[trader]
        if lane.cycle is None:
            raise RuntimeError("CC05 blocked: CC04 cycle absent")
        state = lane.cycle
        pnl = state.compound_ledger.admitted_realized_profit_usd
        source = CapitalSourceLedger().add_source(
            source_id=f"{trader}:cc05:realized-source",
            source=CapitalSource.REALIZED_PROFIT,
            proven_amount_usd=pnl,
        )
        integrated = IntegratedCompoundFundingState(
            cycle=state,
            source_ledger=source,
            realized_profit_bindings=(
                RealizedProfitEquivalenceBinding(
                    source_id=f"{trader}:cc05:realized-source",
                    admission_lot_ids=(f"{trader}:cc04:origin:gen1",),
                ),
            ),
        )
        event, decision = self._reserve_decision(
            trader,
            suffix="cc05",
            cycle=integrated.cycle,
        )
        integrated = apply_funded_internal_market_decision(
            integrated,
            event_id=f"{trader}:cc05:reserve",
            scarcity_event=event,
            decision=decision,
            source_lot_id=None,
        )
        if integrated.funding_links:
            raise RuntimeError("CC05 reserve path must not invent deployed funding")
        if integrated.capital_truth.no_double_counting_pass is not True:
            raise RuntimeError("CC05 integrated capital truth double-counting failure")
        lane.cycle = integrated.cycle
        self._issue(
            trader,
            CiboTraderLabFunctionGate.CC05_FUNDING_COORDINATION,
            integrated,
            "funding coordination executed reserve path and preserved exact realized-profit capital truth",
            domain_verdict="RESERVE_NO_DEPLOYMENT",
        )

    def cc06(self, trader: str) -> None:
        lane = self.lanes[trader]
        if lane.cycle is None:
            raise RuntimeError("CC06 blocked: CC05 cycle absent")
        event, decision = self._reserve_decision(
            trader,
            suffix="cc06",
            cycle=lane.cycle,
        )
        state = apply_internal_capital_market_decision(
            lane.cycle,
            event_id=f"{trader}:cc06:reserve",
            scarcity_event=event,
            decision=decision,
            source_lot_id=None,
        )
        if state.deployments:
            raise RuntimeError("CC06 reserve decision must not create deployment")
        if state.market_records[-1].action != Genc6Action.RESERVE_NO_DEPLOYMENT.value:
            raise RuntimeError("CC06 market record action drift")
        lane.cycle = state
        self._issue(
            trader,
            CiboTraderLabFunctionGate.CC06_MARKET_CYCLE,
            state.market_records[-1],
            "market-cycle application reproduced frozen GEN-C6 reserve decision without deployment",
            domain_verdict="RESERVE_NO_DEPLOYMENT",
        )

    def cc07(self, trader: str) -> None:
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
        protect = amount / Decimal(4)
        events = (
            BaseSettlementEvent(
                event_id=f"{trader}:cc07:win",
                occurred_at=at,
                trader_id=_trader(trader),
                settlement=cma,
            ),
            ClassificationEvent(
                event_id=f"{trader}:cc07:compoundable",
                occurred_at=at + timedelta(microseconds=1),
                source_lot_id=f"{trader}:cc07:win:gen1",
                to_state=CompoundCapitalState.COMPOUNDABLE,
                amount_usd=amount,
            ),
            ProtectProfitEvent(
                event_id=f"{trader}:cc07:protect",
                occurred_at=at + timedelta(microseconds=2),
                source_lot_id=f"{trader}:cc07:compoundable:moved",
                amount_usd=protect,
            ),
        )
        history = materialize_compound_path_history(
            initial_state=blank,
            initial_observed_at=at - timedelta(microseconds=1),
            events=events,
        )
        if history.event_count != 3 or history.future_leakage_used:
            raise RuntimeError("CC07 path history chronology/governance drift")
        if history.summary.descriptive_only is not True:
            raise RuntimeError("CC07 used holdout must remain descriptive")
        self._issue(
            trader,
            CiboTraderLabFunctionGate.CC07_PATH_HISTORY,
            history,
            "chronological path history materialized retained settlement without causal/certification claim",
        )

    def _episode(self, trader: str) -> CompoundMonteCarloEpisode:
        lane = self.lanes[trader]
        row = lane.row
        settlement = row["settlement"]
        cma = row["cma"]
        assert isinstance(settlement, dict) and isinstance(cma, dict)
        deployed_at = _dt(str(settlement["capital_deployed_at"]))
        settled_at = _dt(str(settlement["capital_released_at"]))
        proxy = _research_capital_proxy(row)
        return CompoundMonteCarloEpisode(
            episode_id=f"{trader}:used-holdout",
            deployment_id=f"{trader}:used-holdout:research-deployment",
            market_event_id=f"{trader}:used-holdout:research-market",
            decision_id=f"{trader}:used-holdout:research-decision",
            candidate_id=f"{trader}:used-holdout:research-candidate",
            trader_id=_trader(trader),
            signal_fingerprint=str(row["signal_fingerprint"]),
            deployed_at=deployed_at,
            settled_at=settled_at,
            source_generation=1,
            deployed_capital_usd=proxy,
            stop_risk_usd=Decimal(str(cma["candidate_stop_risk_usd"])),
            margin_usd=Decimal(str(cma["candidate_margin_usd"])),
            realized_pnl_usd=Decimal(str(settlement["realized_net_pnl_usd"])),
            protected_floor_graduation_usd=Decimal(0),
            floor_evidence_sha256=None,
            market_record_present=True,
            terminal_release_present=True,
            future_leakage_used=False,
        )

    def cc08(self, trader: str) -> None:
        episode = self._episode(trader)
        initial = CompoundMonteCarloInitialState(
            original_base_usd=Decimal("100"),
            generation_capacity_usd=((1, episode.deployed_capital_usd),),
            protected_floor_usd=Decimal(0),
            total_stop_risk_capacity_usd=episode.stop_risk_usd,
            total_margin_capacity_usd=episode.margin_usd,
        )
        summary = run_compound_path_monte_carlo(
            initial=initial,
            episodes=(episode,),
            simulations=4,
            draws_per_path=1,
            components_per_block=1,
            base_seed=17,
        )
        if summary.market_probability_claimed or summary.certification_ready:
            raise RuntimeError("CC08 used holdout cannot claim probability/certification")
        self.lanes[trader].mc_summary = summary
        self._issue(
            trader,
            CiboTraderLabFunctionGate.CC08_PATH_MONTE_CARLO,
            summary,
            "deterministic dependency-aware MC executed on retained outcome with margin-as-research-capital proxy only",
        )

    def cc09(self, trader: str) -> None:
        lane = self.lanes[trader]
        row = lane.row
        settlement = row["settlement"]
        cma = row["cma"]
        assert isinstance(settlement, dict) and isinstance(cma, dict)
        trace_sha = str(self.trace["trace_sha256"])
        record = TraderLabBurnedResearchCompoundRecord(
            episode_id=f"{trader}:burned-research",
            trader_id=_trader(trader),
            signal_fingerprint=str(row["signal_fingerprint"]),
            account_identity_fingerprint=(
                f"trader-lab-replay:test:compound-{trader.lower()}"
            ),
            decision_at=_dt(str(row["market_decision_at"])),
            deployed_at=_dt(str(settlement["capital_deployed_at"])),
            settled_at=_dt(str(settlement["capital_released_at"])),
            source_generation=1,
            deployed_capital_usd=_research_capital_proxy(row),
            stop_risk_usd=Decimal(str(cma["candidate_stop_risk_usd"])),
            margin_usd=Decimal(str(cma["candidate_margin_usd"])),
            realized_pnl_usd=Decimal(str(settlement["realized_net_pnl_usd"])),
            source_trace_sha256=trace_sha,
            evidence_kind=CompoundPopulationEvidenceKind.BURNED_RESEARCH,
        )
        binding = bind_trader_lab_burned_research_population((record,))
        if (
            binding.forward_observed
            or binding.economic_replication_claimed
            or binding.certification_ready
            or binding.productive_authority
        ):
            raise RuntimeError("CC09 burned holdout laundering detected")
        lane.research_binding = binding
        self._issue(
            trader,
            CiboTraderLabFunctionGate.CC09_REAL_POPULATION_BINDING,
            binding,
            "used holdout bound into canonical MC episode as BURNED_RESEARCH only; forward binder untouched",
            domain_verdict="BURNED_RESEARCH_DESCRIPTIVE_ONLY",
        )

    def execute(self) -> dict[str, object]:
        methods = (
            self.cc01,
            self.cc02,
            self.cc03,
            self.cc04,
            self.cc05,
            self.cc06,
            self.cc07,
            self.cc08,
            self.cc09,
        )
        if len(methods) != len(COMPOUND_GATES):
            raise RuntimeError("CC01-CC09 gate count mismatch")
        for gate, method in zip(COMPOUND_GATES, methods, strict=True):
            for trader in TRADERS:
                before = self.lanes[trader].previous_receipt
                method(trader)
                after = self.lanes[trader].previous_receipt
                if after.function is not gate:
                    raise RuntimeError(f"{trader} did not receive {gate.value} receipt")
                if after.previous_receipt is not before:
                    raise RuntimeError(f"{trader} {gate.value} did not consume prior receipt")

        lanes: dict[str, object] = {}
        for trader in TRADERS:
            lane = self.lanes[trader]
            if len(lane.reports) != 9:
                raise RuntimeError(f"{trader} has {len(lane.reports)} compound PASS gates")
            lanes[trader] = {
                "status": "PASS",
                "gate_count": len(lane.reports),
                "gates": lane.reports,
                "final_receipt_sha256": lane.previous_receipt.receipt_sha256,
                "retained_settlement_evidence_id": lane.row["settlement"]["evidence_id"],
            }
        return {
            "schema": "qore.cibo.compound-trader-lab-audit.v1",
            "source_trace_sha256": self.trace["trace_sha256"],
            "source_head_sha": self.source_head,
            "candidate_count": len(TRADERS),
            "compound_gate_count": 9,
            "all_cc01_cc09_pass": True,
            "next_stage_unlocked": "CC10_TEMPORAL_REPLICATION_TRADER_LAB",
            "lanes": lanes,
            "authority_chain": ["OWNER", "TRADER_LAB", "CIBO"],
            "governance": {
                "used_holdout": True,
                "burned_research": True,
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
    report = CompoundTraderLabAudit(trace, args.source_head).execute()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "all_cc01_cc09_pass": report["all_cc01_cc09_pass"],
                "candidate_count": report["candidate_count"],
                "compound_gate_count": report["compound_gate_count"],
                "next_stage_unlocked": report["next_stage_unlocked"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
