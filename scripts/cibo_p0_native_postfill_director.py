"""Event-causal Native MAX postfill research director (NO LIVE / NO BROKER).

This is a separate postfill cognition route, not a hardcoded BANK/MEDIUM/ATTACK
exit-policy table. It rebuilds real CF01-CF19 and Native MAX with the just
observed executable bar close + provided contemporary QORE account snapshot.

Only an evidence-sealed instruction is returned. The physical PAPER exit
engine applies it NEXT BAR OPEN, never on the observed bar or in the past.
A caller MUST supply portfolio-causal snapshots to claim account-wide fidelity.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Callable

from cibo_p0_native_replay_runtime import reconstruct_native_max_at_epoch
from qore.infrastructure.cibo_managed_exit_replay import (
    CiboCognitivePostfillAction, CiboPositionCloseObservation,
    ManagedReplayError,
)


@dataclass(frozen=True)
class ResearchAccountAtClose:
    observed_at: datetime
    qore_cash_usd: Decimal
    peak_cash_usd: Decimal
    open_stop_risk_usd: Decimal
    broker_margin_held_usd: Decimal
    open_positions: int
    broker_cash_usd: Decimal
    source: str = "RESEARCH_PAPER_GLOBAL_SCHEDULER_NOT_LIVE"

    def __post_init__(self):
        if self.source != "RESEARCH_PAPER_GLOBAL_SCHEDULER_NOT_LIVE":
            raise ManagedReplayError("postfill account snapshot must be PAPER provenance")
        for name in ("qore_cash_usd", "peak_cash_usd",
                     "open_stop_risk_usd", "broker_margin_held_usd",
                     "broker_cash_usd"):
            v=getattr(self,name)
            if not isinstance(v,Decimal) or not v.is_finite() or v<0:
                raise ManagedReplayError("postfill account snapshot invalid: "+name)
        if self.open_positions < 1:
            raise ManagedReplayError("postfill account must include the managed position")
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise ManagedReplayError("postfill account timestamp must be timezone-aware")


class CiboNativeMaxPostfillResearchDirector:
    """Genuine Native MAX at each invoked bar-close boundary.

    Unlike the fixed exit policy this recomputes the faculties, account
    utilization, uncertainty, causal mark, and signed decision every time.
    The mapping from an episode into executable actions remains experimental;
    its reasoning does not establish a profitable broker exit strategy.
    """
    def __init__(
        self, *, original: dict, account_at_close: Callable[[datetime],ResearchAccountAtClose],
        min_lot: Decimal, partial_fraction: Decimal = Decimal("0.5")
    ):
        self.original=original
        self.account_at_close=account_at_close
        self.min_lot=min_lot
        self.partial_fraction=partial_fraction
        self.receipts: list[dict]=[]
        if not isinstance(min_lot,Decimal) or min_lot<=0:
            raise ManagedReplayError("cognitive postfill minimum lot invalid")
        if not isinstance(partial_fraction,Decimal) or not 0<partial_fraction<1:
            raise ManagedReplayError("cognitive postfill partial fraction invalid")

    def __call__(self, observation: CiboPositionCloseObservation)->CiboCognitivePostfillAction:
        if not isinstance(observation,CiboPositionCloseObservation):
            raise ManagedReplayError("typed closed-bar observation required")
        if observation.signal_id != self.original["signal_fingerprint"]:
            raise ManagedReplayError("cognitive position signal mismatch")
        snapshot=self.account_at_close(observation.observed_at)
        if not isinstance(snapshot,ResearchAccountAtClose) or snapshot.observed_at!=observation.observed_at:
            raise ManagedReplayError("postfill account snapshot must match closed-bar time")

        # Copy, never modify sealed Trader source. Add ONLY already-observed
        # position and executable close. Avoid forbidden outcome/future labels.
        enriched=dict(self.original)
        opportunity=dict(self.original["trader_opportunity"])
        context=list(opportunity.get("decision_context",[]))
        new={
            "position_mark_r_at_observation":str(observation.favorable_r),
            "position_close_executable_at_observation":str(observation.executable_close),
            "position_stop_at_observation":str(observation.protective_stop),
            "position_lots_at_observation":str(observation.remaining_lots),
            "position_bar_evidence_at_observation":observation.bar_evidence_sha256,
        }
        if any(k in dict(context) for k in new):
            raise ManagedReplayError("Native MAX postfill cannot overwrite Trader context")
        opportunity["decision_context"]=context+list(new.items())
        enriched["trader_opportunity"]=opportunity
        ce2i=dict(enriched["ce2i_predecision_evidence"])
        records=[]
        for receipt in ce2i["runtime_receipts"]:
            receipt_copy=dict(receipt)
            if receipt_copy.get("engine_name")=="select_ce2i_tools_for_regime":
                inputs=dict(receipt_copy["input_payload"])
                inputs["position_path_adverse"]=observation.favorable_r < 0
                receipt_copy["input_payload"]=inputs
            records.append(receipt_copy)
        ce2i["runtime_receipts"]=records
        enriched["ce2i_predecision_evidence"]=ce2i

        instruction,trace=reconstruct_native_max_at_epoch(
            original=enriched, decision_at=observation.observed_at,
            qore_cash_usd=snapshot.qore_cash_usd,
            peak_cash_usd=snapshot.peak_cash_usd,
            open_stop_risk_usd=snapshot.open_stop_risk_usd,
            broker_margin_held_usd=snapshot.broker_margin_held_usd,
            open_positions=snapshot.open_positions,
            broker_cash_usd=snapshot.broker_cash_usd,
        )
        confidence=instruction.calibration_confidence
        mark=observation.favorable_r
        # Conservatively tighten stops; do not widen, create lot fragments
        # below broker-min, invent expected profit, or apply on the same bar.
        if mark <= Decimal("-0.25") and (instruction.abstention_required or confidence<34):
            action="EXIT_NEXT_OPEN"
            stop=None
            fraction=None
        elif (mark >= Decimal("1.0") and confidence>=67
              and observation.remaining_lots >= self.min_lot*2):
            action="PARTIAL_NEXT_OPEN"
            stop=None
            fraction=self.partial_fraction
        elif mark >= Decimal("0.5") and (confidence>=34 or instruction.abstention_required):
            # Bank principal with a next-bar breakeven stop where it truly
            # improves the current protective stop, else HOLD.
            stop=observation.entry_price
            improves = (stop > observation.protective_stop
                        if observation.side=="BUY"
                        else stop < observation.protective_stop)
            action="TIGHTEN_STOP_NEXT_OPEN" if improves else "HOLD"
            if not improves:
                stop=None
            fraction=None
        else:
            action="HOLD"
            stop=None
            fraction=None
        decision=CiboCognitivePostfillAction(
            signal_id=observation.signal_id,decided_at=observation.observed_at,
            action=action,native_episode_digest=instruction.decision_digest,
            proposed_stop=stop,partial_fraction=fraction,
        )
        self.receipts.append({
            **trace,"position_observed_at":observation.observed_at.isoformat(),
            "position_mark_r":str(mark),
            "postfill_action":action,
            "observation_broker_side_price":str(observation.executable_close),
            "next_open_only":True,
            "broker_fills":0,
            "certified":False,
        })
        return decision
