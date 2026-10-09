#!/usr/bin/env python3
"""P0 entry-evidence preflight for the ORIGINAL 3368 seven-Trader opportunities.

Consumes an optional independently sourced per-fingerprint native market pack.
If no pack exists, reports 3368 explicit blockers. NEVER assumes historic
M5 midpoint/2026 spread/2026 USDJPY/fees were original broker executions.
This is an executable readiness/provenance report, NOT a market replay.
"""
from __future__ import annotations

import argparse
from collections import Counter,defaultdict
from datetime import datetime
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path

from qore.infrastructure.cibo_p0_native_causal_market import (
    NativeBar,HistoricalBidAsk,native_entry_context,CausalEvidenceError,
)
from scripts.cibo_p0_atr_four_arm_physical_budget import validate_config

SEVEN=frozenset({
    "R34_XAUUSD","R38_EURUSD","R38_GBPJPY","R42_AUDJPY",
    "R43_GBPUSD","VT31_NAS100","VT08_FOREX",
})
FRAMES={"M1","M15","H1","H4"}
ASSETS={"AUDJPY","EURUSD","GBPJPY","GBPUSD","XAUUSD","NDX100"}


class CorpusError(ValueError):
    pass


def _timestamp(value):
    d=datetime.fromisoformat(str(value))
    if d.tzinfo is None or d.utcoffset() is None:
        raise CorpusError("source decision must be timezone-aware")
    return d


def _unique(rows,label):
    if not isinstance(rows,list):
        raise CorpusError(label+" list missing")
    keyed={}
    for row in rows:
        if not isinstance(row,dict):
            raise CorpusError(label+" nonobject row")
        sid=row.get("signal_fingerprint")
        if not isinstance(sid,str) or not sid or sid in keyed:
            raise CorpusError(label+" missing/duplicate signal fingerprint")
        keyed[sid]=row
    return keyed


def _bar(row):
    return NativeBar(
        row["symbol"],row["timeframe"],
        _timestamp(row["opened_at"]),_timestamp(row["closed_at"]),
        *(Decimal(str(row[k])) for k in ("open","high","low","close")),
        row["content_sha256"],
    )


def _quote(row):
    return HistoricalBidAsk(
        row["symbol"],_timestamp(row["observed_at"]),
        Decimal(str(row["bid"])),Decimal(str(row["ask"])),
        row["content_sha256"],row["source_type"],
    )


def audit(manifest:dict,evidence_pack:dict|None,config:dict,
          *,expected_count:int=3368,require_original_seven:bool=True)->dict:
    validate_config(config)
    source=_unique(manifest.get("opportunities"),"original 3368 Trader source")
    if len(source)!=expected_count:
        raise CorpusError("source cardinality does not equal "+str(expected_count))
    if (require_original_seven and
        {r.get("trader_id") for r in source.values()}!=SEVEN):
        raise CorpusError("original seven-Trader identity drift")
    if require_original_seven and sum(
        r["trader_id"]=="VT31_NAS100" for r in source.values())!=484:
        raise CorpusError("original 484 VT31 M1 source signals drift")
    rows={}
    for sid,src in source.items():
        t=_timestamp(src["market_decision_at"])
        tf=dict(src["trader_opportunity"]["decision_context"]).get("ctx_timeframe")
        original_symbol=src.get("qore_symbol")
        # Market Atlas uses NDX100 while the VT31 original Trader labels
        # NAS100. Preserve original alias and canonicalize only this proven
        # execution instrument identity, NEVER invent a missing symbol.
        symbol="NDX100" if original_symbol=="NAS100" else original_symbol
        if tf not in FRAMES or symbol not in ASSETS:
            raise CorpusError(
                "source native timeframe/symbol absent: "+sid+
                " trader="+str(src.get("trader_id"))+
                " tf="+str(tf)+" original_symbol="+str(original_symbol))
        if require_original_seven and not 2019<=t.year<=2022:
            raise CorpusError("source year not 2019–2022")
        if src["trader_id"]=="VT31_NAS100" and (tf!="M1" or symbol!="NDX100"):
            raise CorpusError("VT31 M1/NDX100 source mislabelled")
        rows[sid]=dict(
            signal_fingerprint=sid,trader=src["trader_id"],
            symbol=symbol,source_timeframe=tf,
            market_decision_at=t.isoformat(),
        )
    packets={}
    errors={}
    if evidence_pack is not None:
        if evidence_pack.get("schema")!="qore.cibo.p0.native-broker-evidence-by-signal.v1":
            raise CorpusError("unsupported native broker evidence pack schema")
        packets=_unique(evidence_pack.get("signals"),"native market pack")
        unknown=set(packets)-set(source)
        if unknown:
            raise CorpusError("evidence pack contains fingerprints outside sealed source")
    for sid,record in rows.items():
        if sid not in packets:
            record["status"]="NO_CAUSAL_EVIDENCE_PACK_FOR_SIGNAL"
            record["broker_fills"]=0
            errors[sid]=record["status"]
            continue
        item=packets[sid]
        try:
            if (item.get("symbol")!=record["symbol"]
                    or item.get("source_timeframe")!=record["source_timeframe"]
                    or _timestamp(item.get("decision_at"))!=
                       _timestamp(record["market_decision_at"])):
                raise CausalEvidenceError("ORIGINAL_TRADER_IDENTITY_OR_EPOCH_DRIFT")
            bars=tuple(_bar(b) for b in item.get("native_closed_bars",[]))
            prices=tuple(_quote(q) for q in item.get("historical_bid_ask",[]))
            usd_rows=item.get("historical_usdjpy_bid_ask",[])
            if record["symbol"] in {"GBPJPY","AUDJPY"} and not usd_rows:
                raise CausalEvidenceError("NO_EPOCH_USDJPY_EVIDENCE")
            jpy=_quote(usd_rows[-1]) if usd_rows else None
            contract=Decimal(str(item["physical_contract_size"]))
            context=native_entry_context(
                symbol=record["symbol"],timeframe=record["source_timeframe"],
                side="BUY" if source[sid]["trader_opportunity"]["side"]=="long" else "SELL",
                decision_at=_timestamp(record["market_decision_at"]),
                bars=bars,quotes=prices,
                usd_jpy_quote=jpy,contract_size=contract,
            )
            record["causal_market_context"]=context
            # A published 2026 tariff is NOT independent 2019–22 MT5 deals.
            # This gate cannot infer deal-level historical commissions from OHLC.
            fee=item.get("account_fee_evidence",{})
            if (not isinstance(fee,dict) or
                fee.get("classification")!="BROKER_ACCOUNT_HISTORICALLY_VERIFIED"
                or not isinstance(fee.get("deal_receipts_sha256"),str)
                or not fee["deal_receipts_sha256"].startswith("sha256:")
                or len(fee["deal_receipts_sha256"])!=71):
                raise CausalEvidenceError("MISSING_VERIFIABLE_ACCOUNT_FEE_EVIDENCE")
            # A hash alone is not broker authentication. Later certification
            # must verify provenance against an independent account export.
            record["status"]="STRUCTURALLY_COMPLETE_BUT_NOT_BROKER_AUTHENTICATED"
        except (CausalEvidenceError,ValueError,TypeError,KeyError,IndexError) as exc:
            record["status"]=str(exc) if str(exc) else "INVALID_CAUSAL_DATA_PACK"
            errors[sid]=record["status"]
        record["broker_fills"]=0
    status_counts=Counter(r["status"] for r in rows.values())
    by_trader=defaultdict(Counter)
    for r in rows.values():
        by_trader[r["trader"]][r["status"]]+=1
    return {
        "schema":"qore.cibo.p0.native-3368-evidence-gate.v1",
        "source_signals":len(rows),"original_traders":sorted(
            {r["trader"] for r in rows.values()}),
        "original_timeframe_counts":dict(sorted(Counter(
            r["source_timeframe"] for r in rows.values()).items())),
        "source_year_counts":dict(sorted(Counter(
            _timestamp(r["market_decision_at"]).year for r in rows.values()
        ).items())),
        "status_counts":dict(sorted(status_counts.items())),
        "by_trader":{name:dict(sorted(v.items())) for name,v in sorted(by_trader.items())},
        "unassessable_count":len(errors),
        "full_replay_ready":False,  # structural hashes cannot authenticate a broker
        "external_broker_attestation_required":True,
        "missing_input_pack":evidence_pack is None,
        "source_only_frozen_not_OOS":True,
        "no_live":True,"broker_fills":0,
        "four_arms":[a["arm"] for a in config["scenarios"]],
        "opportunities":list(rows.values()),
        "note":"Native data presence != broker-authenticated fee/deal proofs; never relabel earlier 540/246 PF",
    }


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--manifest",type=Path,required=True)
    parser.add_argument("--contract",type=Path,required=True)
    parser.add_argument("--evidence-pack",type=Path)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    manifest=json.loads(args.manifest.read_text())
    contract=json.loads(args.contract.read_text())
    pack=json.loads(args.evidence_pack.read_text()) if args.evidence_pack else None
    report=audit(manifest,pack,contract)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print("CIBO_P0_NATIVE_3368_PREFLIGHT",json.dumps({
        "status_counts":report["status_counts"],
        "original_timeframe_counts":report["original_timeframe_counts"],
        "unassessable":report["unassessable_count"],
        "source_signals":report["source_signals"],
        "four_arms":report["four_arms"],
        "no_live":report["no_live"],"full_replay_ready":report["full_replay_ready"],
    },sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
