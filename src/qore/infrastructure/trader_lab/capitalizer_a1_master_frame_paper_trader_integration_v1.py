"""Actual A1 full Master Cognitive Frame → Trader PAPER admission and R ledger.

Unlike standalone A1 packet or A2 sensor-report adapters, this module passes
the evaluated Master Frame decision into an observable PAPER execution
selection. A PASS is not live authority. PAPER cash flows remain the frozen
V49 fills/exits; a new entry price or timing requires a fresh native-M1 replay.

Inputs require REAL nine-market observed barriers and A2 sensor evidence tokens
constructed without forward labels. This module WILL NOT manufacture missing
market perceptions, H1/M15 provenance, regimes, graph or broker quotes.
Chosen outcomes enter cognitive memory strictly AFTER actual paper settlement.
No reject/counterfactual trade outcome enters the Master Frame.

Research note: outcome rows are supplied as frozen V49 evidence but only
consulted for an already PASSed and admitted trade, *after* that decision.
Do not interpret this as live MT5, physical-cost P&L, or scientific certification.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_a1_full_frame_research_adapter import (
    A1CausalSettledMemory,
    A1SettledChosenTrade,
)
from qore.infrastructure.trader_lab.capitalizer_a1_multi_hypothesis_research import (
    A1MultiHypothesisBarrier,
)
from qore.infrastructure.trader_lab.capitalizer_a1_trader_cognition_port import (
    prepare_trader_cognition_packet,
)
from qore.infrastructure.trader_lab.capitalizer_memory import CapitalizerLossCause
from qore.infrastructure.trader_lab.capitalizer_v49_development_economics import (
    V49EconomicTrade,
    _metrics,
    _portfolio_select,
)

IDENTITY = "QORE_SCALPER_A1_REAL_MASTER_FRAME_TO_PAPER_TRADER_V1"


@dataclass(frozen=True, slots=True)
class A1PaperSource:
    """Only historical books with a joined exact source-ID may be scored."""

    source_opportunity_id: str
    trade: V49EconomicTrade
    independently_attested_settled_loss: CapitalizerLossCause | None = None

    def __post_init__(self) -> None:
        if not self.source_opportunity_id:
            raise ValueError("original source ID required")
        if self.independently_attested_settled_loss is not None and (
            self.independently_attested_settled_loss.symbol != self.trade.symbol
            or self.independently_attested_settled_loss.realized_r
            != Decimal(self.trade.realized_gross_r)
        ):
            raise ValueError("loss-cause witness does not match paper settlement")


@dataclass(frozen=True, slots=True)
class A1PaperTraderDecision:
    source_opportunity_id: str
    symbol: str
    decision_at: str
    cognitive_gate: str
    paper_disposition: str
    why_tokens: tuple[str, ...]
    memory_settled_count_asof: int
    sensor_evidence_present: bool
    selected_for_paper: bool
    outcome_used_for_admission: bool = False
    authorizes_real_order: bool = False

    def __post_init__(self) -> None:
        if self.outcome_used_for_admission or self.authorizes_real_order:
            raise ValueError("cognitive PAPER decision cannot grant live authority")
        if not self.why_tokens or not self.sensor_evidence_present:
            raise ValueError("each cognitive PAPER decision needs actual sensor WHY")


@dataclass(frozen=True, slots=True)
class A1PaperTraderReport:
    identity: str
    source_candidates_seen: int
    cognitively_passed: int
    cognitively_waited: int
    cognitively_abstained: int
    paper_selected: int
    source_ledger: tuple[A1PaperTraderDecision, ...]
    selected_source_ids: tuple[str, ...]
    reference_control_metrics: dict[str, Any]
    master_frame_paper_metrics: dict[str, Any]
    source_winners_retained: int
    source_winner_r_preserved: str
    paired_original_source_count: int
    nine_market_frame_per_candidate: bool
    all_sensor_inputs_evidenced: bool
    economics_are_frozen_v49_fills: bool = True
    physical_broker_costs_verified: bool = False
    full_historical_native_nine_market_run: bool = False
    trader_certified: bool = False
    live_authorized: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY or any((
            self.physical_broker_costs_verified,
            self.full_historical_native_nine_market_run,
            self.trader_certified,
            self.live_authorized,
        )):
            raise ValueError("A1 PAPER report is not broker or certification evidence")


def _summary(trades: tuple[V49EconomicTrade, ...]) -> dict[str, Any]:
    if not trades:
        return {"trades": 0, "profit_factor": None,
                "total_r": "0", "max_drawdown_r": None, "wins": 0}
    m = _metrics(trades)
    return {
        "trades": m.trades,
        "profit_factor": m.profit_factor,
        "total_r": m.total_r,
        "max_drawdown_r": m.max_drawdown_r,
        "wins": m.wins,
    }


def run_real_master_frame_paper_trader(
    *,
    barriers: tuple[A1MultiHypothesisBarrier, ...],
    original_sources: tuple[A1PaperSource, ...],
    baseline_selected_source_ids: tuple[str, ...],
    settlement_confirmed_after_exit_seconds: int = 0,
    require_all_source_cognitive_sensors: bool = True,
) -> A1PaperTraderReport:
    """Decision before outcome, FULL nine-market frame every source, MAX3.

    The supplied barrier must independently represent all nine genuine,
    complete as-of observations and correct H1→M15→M1 clocks. This function
    does not self-attest upstream market data that were never supplied.
    """

    if not barriers or not original_sources or settlement_confirmed_after_exit_seconds < 0:
        raise ValueError("needs observed barriers and original source trade books")
    by_id = {row.source_opportunity_id: row for row in original_sources}
    if len(by_id) != len(original_sources):
        raise ValueError("duplicate source in original economic book")
    original_ids = tuple(row.source_opportunity_id for row in original_sources)
    if (
        not baseline_selected_source_ids
        or len(set(baseline_selected_source_ids)) != len(baseline_selected_source_ids)
        or not set(baseline_selected_source_ids) <= set(by_id)
    ):
        raise ValueError("baseline source IDs must be exact original universe")
    if set(baseline_selected_source_ids) != set(
        x.source_opportunity_id for x in original_sources
        if x.source_opportunity_id in baseline_selected_source_ids
    ):
        raise ValueError("unreconciled original baseline source IDs")

    seen: set[str] = set()
    last_at: datetime | None = None
    decisions: list[A1PaperTraderDecision] = []
    chosen: list[A1PaperSource] = []
    capacity: Counter[tuple[str, str]] = Counter()
    chosen_receipts: list[tuple[str, A1SettledChosenTrade]] = []
    newly_settled: set[str] = set()
    all_pass = all_sensors = True

    for barrier in barriers:
        at = barrier.observed_at
        if last_at is not None and at <= last_at:
            raise ValueError("same-clock must form one barrier; time must progress")
        last_at = at
        source_ids = tuple(alt.binding.source_opportunity_id
                           for alt in barrier.alternatives)
        if (
            len(source_ids) != len(set(source_ids))
            or set(source_ids) & seen
            or not set(source_ids) <= set(by_id)
            or set(source_ids) != set(barrier.expected_source_ids)
        ):
            raise ValueError("A1 barrier lost or invented original source identities")
        seen.update(source_ids)
        for alt in barrier.alternatives:
            historical = by_id[alt.binding.source_opportunity_id].trade
            if (
                alt.binding.symbol != historical.symbol
                or alt.binding.confirmed_at != datetime.fromisoformat(historical.entry_at)
                or alt.h1_confirmed_at > alt.m15_confirmed_at
                or alt.m15_confirmed_at > at
            ):
                raise ValueError("A1 source time/symbol incompatible with original V49")
            tokens = alt.context.observation_tokens
            has_sensors = (
                any(s.startswith("SCALPER_SENSOR:") for s in tokens)
                and "SCALPER_NATIVE_M1_ASOF=YES" in tokens
            )
            if require_all_source_cognitive_sensors and not has_sensors:
                raise ValueError("A1 must receive REAL predecision A2 sensor tokens")
            all_sensors = all_sensors and has_sensors
        from datetime import timedelta

        known = A1CausalSettledMemory(tuple(
            receipt for _, receipt in chosen_receipts
            if receipt.confirmed_at is not None and receipt.confirmed_at < at
        ))
        packet = prepare_trader_cognition_packet(
            barrier=barrier, settled_memory=known,
        )
        if not packet.nine_market_frame_called_for_each_source:
            raise ValueError("Master Frame not actually evaluated per source")
        if (
            set(packet.source_opportunity_ids) != set(source_ids)
            or len(packet.candidates) != len(source_ids)
        ):
            raise ValueError("full-frame candidate result lost source identities")
        all_pass = all_pass and packet.nine_market_frame_called_for_each_source
        for candidate in sorted(packet.candidates,
                                key=lambda c: (c.decision_at, c.symbol,
                                               c.source_opportunity_id)):
            item = by_id[candidate.source_opportunity_id]
            trade = item.trade
            key = (trade.session, trade.operating_date)
            passed = candidate.cognitive_gate == "PASS_TO_STRATEGY"
            selected = passed and capacity[key] < 3
            if selected:
                capacity[key] += 1
                chosen.append(item)
                # PAPER settlement becomes visible only after selected trade
                # really exits, NEVER before confirmation. Without independent
                # cause, losses must not magically teach a specific fingerprint.
                exit_time = datetime.fromisoformat(trade.exit_at)
                chosen_receipts.append((
                    candidate.source_opportunity_id,
                    A1SettledChosenTrade(
                        execution_id="PAPER:"+candidate.source_opportunity_id,
                        entry_at=at, exit_at=exit_time,
                        loss_cause=item.independently_attested_settled_loss,
                        confirmed_at=exit_time+timedelta(
                            seconds=settlement_confirmed_after_exit_seconds
                        ),
                    ),
                ))
            decisions.append(A1PaperTraderDecision(
                source_opportunity_id=candidate.source_opportunity_id,
                symbol=candidate.symbol, decision_at=candidate.decision_at.isoformat(),
                cognitive_gate=candidate.cognitive_gate,
                paper_disposition=(
                    "PAPER_EXECUTED_ORIGINAL_V49_FILL"
                    if selected else "PAPER_CAPACITY_FULL"
                    if passed else "PAPER_WAIT" if candidate.cognitive_gate == "WAIT"
                    else "PAPER_ABSTAIN"
                ),
                why_tokens=candidate.why_tokens,
                memory_settled_count_asof=candidate.closed_chosen_history_count,
                sensor_evidence_present=all_sensors,
                selected_for_paper=selected,
            ))
    if seen != set(original_ids):
        raise ValueError("not every source opportunity received full Master Frame")
    if any(cap > 3 for cap in capacity.values()):
        raise ValueError("paper MAX3 exceeded")
    baseline = tuple(by_id[sid].trade for sid in baseline_selected_source_ids)
    experimental = tuple(item.trade for item in chosen)
    baseline_winners = {
        sid: Decimal(by_id[sid].trade.realized_gross_r)
        for sid in baseline_selected_source_ids
        if Decimal(by_id[sid].trade.realized_gross_r) > 0
    }
    preserved = {
        item.source_opportunity_id
        for item in chosen
    } & set(baseline_winners)
    return A1PaperTraderReport(
        identity=IDENTITY,
        source_candidates_seen=len(seen),
        cognitively_passed=sum(d.cognitive_gate == "PASS_TO_STRATEGY" for d in decisions),
        cognitively_waited=sum(d.cognitive_gate == "WAIT" for d in decisions),
        cognitively_abstained=sum(d.cognitive_gate == "ABSTAIN" for d in decisions),
        paper_selected=len(chosen),
        source_ledger=tuple(decisions),
        selected_source_ids=tuple(item.source_opportunity_id for item in chosen),
        reference_control_metrics=_summary(baseline),
        master_frame_paper_metrics=_summary(experimental),
        source_winners_retained=len(preserved),
        source_winner_r_preserved=str(sum(
            (baseline_winners[sid] for sid in preserved), Decimal(0)
        )),
        paired_original_source_count=len(original_sources),
        nine_market_frame_per_candidate=all_pass,
        all_sensor_inputs_evidenced=all_sensors,
    )
