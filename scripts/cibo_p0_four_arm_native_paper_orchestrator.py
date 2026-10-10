#!/usr/bin/env python3
"""P0 four-arm PAPER *orchestration* on ONE PaperQDLE SQLite per scenario.

This adapter joins the 3368 original source gate with 4 independent
PaperQDLE + CanonicalPaperPortfolioMtm accounts. Where market/exit/motor
proof is missing, every signal receives an UNASSESSABLE receipt in EVERY
scenario. No fabricated trades, NAV, PF or MTM DD. Future physical
executor must use the arm's SAME QDLE and MTM objects, never another book.

This is NOT the four-arm trade replay. Synthetic isolated integration tests
may book hypothetical trades through the provided paper-only arm API.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal as D
import hashlib
import json
from pathlib import Path
import sqlite3

from qore.infrastructure.cibo_p0_native_causal_market import HistoricalBidAsk
from qore.infrastructure.cibo_p0_paper_portfolio_mtm import (
    CanonicalPaperPortfolioMtm, PaperMtmError,
)
from qore.infrastructure.qdle_paper_book import PaperQDLE
from qore.infrastructure.qore_dynamic_lot_engine import (
    BrokerValuation, QDLEAccount, QDLEError, QDLEIntent, QDLESymbol,
)
from scripts.cibo_p0_atr_four_arm_physical_budget import validate_config
from scripts.cibo_p0_native_3368_evidence_gate import audit

ARM_IDS=("A-X","A-Y","B-X","B-Y")
ZERO=D(0)


class OrchestrationError(ValueError):
    pass


class NoNativeBrokerCalculator:
    """An intentionally non-executable calculator.

    Real valuations cannot be manufactured by the coordinator. Once
    historical broker data and producer votes exist, an independently
    audited broker calculator must replace this explicit blocker.
    """
    def value(self, spec, intent, now):
        raise QDLEError("NO_VERIFIED_HISTORICAL_BROKER_VALUATION")
    def check_volume(self, spec, intent, lots):
        raise QDLEError("NO_VERIFIED_HISTORICAL_BROKER_LOT_GRID")


@dataclass
class ArmBook:
    arm: str
    sqlite_path: Path
    qdle: PaperQDLE
    mtm: CanonicalPaperPortfolioMtm

    @classmethod
    def open(cls, arm:str, path:Path)->"ArmBook":
        if arm not in ARM_IDS:
            raise OrchestrationError("unknown frozen scenario")
        if path.exists():
            raise OrchestrationError("refusing to overwrite or combine a prior PAPER run")
        path.parent.mkdir(parents=True,exist_ok=True)
        qdle=PaperQDLE(path,NoNativeBrokerCalculator())
        # Bind the single SQLite authority to EXACTLY ONE scenario. Even if
        # all 3368 source receipts happen to be identical before market data,
        # the books must remain independently attributable and distinguishable.
        with qdle._tx() as db:
            db.execute("INSERT INTO meta(key,value) VALUES(?,?)",
                       ("canonical_paper_scenario_arm",json.dumps(arm)))
            qdle._audit(db,"PAPER_SCENARIO_ARM_BOUND",None,
                        {"arm":arm,"paper_only":True})
        mtm=CanonicalPaperPortfolioMtm(qdle,starting_nav_usd=D("60"))
        return cls(arm,path,qdle,mtm)

    def unassessable(self,sid:str,at:datetime,reason:str)->None:
        self.qdle.paper_unassessable(sid,at,reason)

    def mark_and_publish(self, *, at:datetime,
                         historical_quotes:tuple[HistoricalBidAsk,...],
                         sequence:int,free_margin:D,
                         broker_equity:D,
                         broker_balance:D)->dict:
        """Exact engine bridge, usable by a FUTURE causal executor.

        All open lots must receive an executable quote. QORE capital is
        marked equity, not cash. The result is a noncertified PAPER mark.
        """
        marked=self.mtm.mark(at=at,quotes=historical_quotes)
        nav=D(marked["equity_usd"])
        if nav<ZERO:
            raise OrchestrationError("negative NAV cannot finance a new position")
        self.qdle.publish_account(QDLEAccount(
            account_id="RESEARCH_PAPER_"+self.arm,
            provider="FundedNext",currency="USD",
            sequence=sequence,as_of=at,
            balance=broker_balance,equity=broker_equity,
            free_margin=free_margin,
            qore_unreserved_risk_usd=nav,
            sovereign_free_source_usd=nav,
            cushion_free_source_usd=ZERO,
            qore_trading_capital_usd=nav,
            positions=(),covered_fill_tickets=(),
        ))
        return marked

    def reserve(self,intent:QDLEIntent,at:datetime):
        """Delegates to SAME SQLite authority; cannot fabricate prices."""
        return self.qdle.reserve_for_trader(intent,now=at)

    def filled(self,*,sid:str,at:datetime,side:str,symbol:str,
               entry_price:D,lots:D,unit_usd_per_lot:D,
               opening_fee_usd:D):
        """Exactly-once QDLE fill and cash OPEN, within one canonical book.

        A caller must have an admitted QDLE reservation and a truly causal
        PAPER fill epoch. Real MT5 execution methods remain forbidden.
        """
        self.qdle.paper_fill(sid,at)
        self.mtm.book_open(
            request_id=sid,at=at,side=side,symbol=symbol,
            entry=entry_price,lots=lots,
            contract_usd_per_price_unit_lot=unit_usd_per_lot,
            commission_open_usd=opening_fee_usd,
        )

    def settled(self,*,sid:str,at:datetime,gross_usd:D,closing_fee_usd:D=ZERO):
        self.qdle.paper_settle(sid,at,gross_usd)
        self.mtm.book_close(request_id=sid,at=at,
                            gross_pnl_usd=gross_usd,
                            commission_close_usd=closing_fee_usd)

    def snapshot(self)->dict:
        with self.qdle._tx() as db:
            groups=db.execute(
                "SELECT state,COUNT(*) FROM reservations GROUP BY state"
            ).fetchall()
            unassessable=db.execute(
                "SELECT reason,COUNT(*) FROM paper_unassessable GROUP BY reason"
            ).fetchall()
        return dict(
            arm=self.arm,coverage=self.qdle.paper_coverage(),
            state_counts=dict(groups),
            unassessable_reasons=dict(unassessable),
            mtm=self.mtm.summary(),
            journal_digest=self.qdle.paper_audit_digest(),
            broker_fills=0,
        )


def _sha_file(path:Path)->str:
    return "sha256:"+hashlib.sha256(path.read_bytes()).hexdigest()


def _backup(book:ArmBook)->dict:
    """Store stable WAL-safe book bytes for exact artifact verification."""
    copy=book.sqlite_path.with_name(book.sqlite_path.stem+"-audit.sqlite")
    with sqlite3.connect(book.sqlite_path) as src,sqlite3.connect(copy) as dest:
        src.backup(dest)
    return dict(path=str(copy),sha256=_sha_file(copy))


def orchestrate(*,manifest:dict,config:dict,output:Path,
                evidence_pack:dict|None=None,
                expected_count:int=3368,
                require_original_seven:bool=True)->dict:
    validate_config(config)
    report=audit(manifest,evidence_pack,config,
                 expected_count=expected_count,
                 require_original_seven=require_original_seven)
    if report["four_arms"]!=list(ARM_IDS):
        raise OrchestrationError("four scenario configuration/order drift")
    if output.exists() and any(output.iterdir()):
        raise OrchestrationError("refusing to mix scenario data with a prior run")
    output.mkdir(parents=True,exist_ok=True)
    books={arm:ArmBook.open(arm,output/(arm.replace("-","_")+".sqlite"))
           for arm in ARM_IDS}
    evidence_by_id={
        r["signal_fingerprint"]:r for r in report["opportunities"]
    }
    normalized=[]
    for r in report["opportunities"]:
        at=datetime.fromisoformat(r["market_decision_at"])
        normalized.append((at,r["signal_fingerprint"]))
    normalized.sort()
    per_arm_rows={arm:[] for arm in ARM_IDS}
    for at,sid in normalized:
        observed=evidence_by_id[sid]
        reason=observed["status"]
        # An authenticated input source + predecision ATR is NOT a complete
        # executable PAPER trade. Until original exits, comprehensive marks
        # and fresh Native MAX/four-motor votes are supplied and bound, NO
        # positive quote or settlement is authorized in this orchestrator.
        if reason=="STRUCTURALLY_COMPLETE_BUT_NOT_BROKER_AUTHENTICATED":
            reason="NO_INDEPENDENT_BROKER_ATTESTATION_AND_CAUSAL_EXIT_MTM_VOTES"
        for arm,book in books.items():
            book.unassessable(sid,at,reason)
            per_arm_rows[arm].append(dict(
                signal_fingerprint=sid,source_at=at.isoformat(),
                source_trader=observed["trader"],
                source_timeframe=observed["source_timeframe"],
                status="PAPER_UNASSESSABLE_NOT_EXECUTED",
                reason=reason,physical_lots="0",
                real_broker_fills=0,
            ))
    expected_source={r["signal_fingerprint"] for r in report["opportunities"]}
    arms={}
    for arm in ARM_IDS:
        snapshot=books[arm].snapshot()
        if (snapshot["coverage"]["received_accounted"]!=len(expected_source)
            or snapshot["coverage"]["paper_filled"]!=0
            or snapshot["coverage"]["unassessable"]!=len(expected_source)
            or snapshot["mtm"]["total_paper_openings"]!=0):
            raise OrchestrationError("scenario receipt conservation / no-execution failed")
        with books[arm].qdle._tx() as db:
            actual={x[0] for x in db.execute("SELECT request_id FROM paper_unassessable")}
        if actual!=expected_source:
            raise OrchestrationError("per-arm original fingerprint drift")
        receipts_file=output/(arm.replace("-","_")+"-source-receipts.json")
        receipts_file.write_text(
            json.dumps(per_arm_rows[arm],sort_keys=True,indent=2)+"\n",
            encoding="utf-8")
        snapshot["sqlite_archive"]=_backup(books[arm])
        snapshot["receipts_sha256"]=_sha_file(receipts_file)
        arms[arm]=snapshot
    if len({a["sqlite_archive"]["sha256"] for a in arms.values()})!=4:
        raise OrchestrationError("four scenarios must have distinct arm-bound SQLite archives")
    if len({a["journal_digest"]["audit_sha256"] for a in arms.values()})!=4:
        raise OrchestrationError("four PAPER audit digests must bind their scenario identity")
    summary=dict(
        schema="qore.cibo.p0.four-arm-canonical-paper-orchestration.v1",
        original_signal_count=len(expected_source),
        total_source_arm_receipts=len(expected_source)*len(ARM_IDS),
        original_traders=report["original_traders"],
        source_timeframe_counts=report["original_timeframe_counts"],
        same_sealed_corpus_all_arms=True,
        arm_results=arms,
        source_preflight_status_counts=report["status_counts"],
        economic_fills=0,broker_fills=0,
        new_profit_factor=None,new_drawdown_pct=None,
        not_a_four_arm_financial_replay=True,
        real_market_pack_provenance_verified=False,
        missing_requirements=[
            "historical_broker_authenticated_bidask_2019_2022",
            "native_M1_M15_H1_H4_closed_ATR14",
            "historical_epoch_USDJPY_and_account_fee_proofs",
            "fresh_Native_MAX_and_four_economic_motor_votes",
            "causal_broker_executable_full_exit_MTM_price_paths",
            "integrated_event_scheduler_for_overlap_partial_exit",
        ],
        research_only=True,no_vps=True,
    )
    (output/"four-arm-orchestration-readiness.json").write_text(
        json.dumps(summary,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    return summary


def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--manifest",required=True,type=Path)
    p.add_argument("--contract",required=True,type=Path)
    p.add_argument("--out-dir",required=True,type=Path)
    p.add_argument("--evidence-pack",type=Path)
    args=p.parse_args()
    data=json.loads(args.manifest.read_text())
    cfg=json.loads(args.contract.read_text())
    pack=json.loads(args.evidence_pack.read_text()) if args.evidence_pack else None
    result=orchestrate(manifest=data,config=cfg,output=args.out_dir,
                       evidence_pack=pack)
    print("P0_FOUR_ARM_CANONICAL_PAPER_ORCHESTRATION",json.dumps({
        "original":result["original_signal_count"],
        "source_arm_receipts":result["total_source_arm_receipts"],
        "arm_counts":{a:r["coverage"]["unassessable"]
                      for a,r in result["arm_results"].items()},
        "new_pf":result["new_profit_factor"],
        "no_live":result["research_only"],
    },sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
