#!/usr/bin/env python3
"""Execute the managed-exit engine only on evidence-complete market paths.

On the 3368-source artifact (structural Trader R + dates, no executable OHLC)
this emits all 3368 signal receipts, marks the missing paths, never invents
profits/ATR/bars, and explicitly distinguishes 300 revised stops from 359
original-stop QDLE research reservations.

A supplied OHLC path may test management of an ORIGINAL-STOP hypothetical fill
but the resulting isolated trade PnL cannot be presented as a recomputed
portfolio/NAV without rerunning sequential four-motor QDLE after every exit.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal as D, localcontext
from pathlib import Path

from qore.infrastructure.cibo_managed_exit_replay import (
    CiboManagedTrade, ExecutableOhlcBar, replay_cibo_managed_position,
)


class MissingPathError(ValueError):
    pass


def _load_market_paths(path: Path | None, expected_ids: set[str]) -> dict[str, tuple]:
    if path is None:
        return {}
    data = json.loads(path.read_text())
    if data.get("schema") != "qore.market.executable-bid-ask-ohlc-paths.v1":
        raise MissingPathError("authorized executable bid/ask OHLC path schema required")
    out = {}
    paths = data.get("paths")
    if not isinstance(paths, list):
        raise MissingPathError("typed market paths list required")
    for p in paths:
        signal = p["signal_fingerprint"]
        if signal in out or signal not in expected_ids:
            raise MissingPathError("duplicate or foreign OHLC price path")
        bs = p["bars"]
        if not isinstance(bs, list) or not bs:
            raise MissingPathError("do not call missing OHLC bars evidence")
        out[signal] = tuple(ExecutableOhlcBar(
            opened_at=datetime.fromisoformat(str(b["opened_at"])),
            closed_at=datetime.fromisoformat(str(b["closed_at"])),
            evidence_sha256=str(b["evidence_sha256"]),
            **{k:D(str(b[k])) for k in (
                "bid_open", "bid_high", "bid_low", "bid_close",
                "ask_open", "ask_high", "ask_low", "ask_close"
            )}
        ) for b in bs)
    return out


def audit(manifest: dict, manager: dict, qdle: dict,
          *, paths: dict[str, tuple] | None = None) -> dict:
    inputs = manifest["opportunities"]
    m = manager["receipts"]
    q = qdle["decisions"]
    if len(inputs) != len(m) or len(m) != len(q) or len(q) != 3368:
        raise MissingPathError("3368 fully-accounted signal receptions required")
    if (len({r["signal_fingerprint"] for r in inputs}) != 3368
        or len({r["signal_fingerprint"] for r in m}) != 3368
        or len({r["signal_fingerprint"] for r in q}) != 3368):
        raise MissingPathError("not 3368 distinct signal IDs")
    if qdle["native_cibo_cognitive_decisions_consumed"] != 0:
        raise MissingPathError("Native CIBO selector not allowed in manager replay")
    by_input={r["signal_fingerprint"]:r for r in inputs}
    by_manager={r["signal_fingerprint"]:r for r in m}
    paths=paths or {}
    if not set(paths).issubset(by_input):
        raise MissingPathError("foreign bar data")
    statuses=Counter()
    symbol_stats=defaultdict(Counter)
    receipts=[]
    for event in q:
        id=event["signal_fingerprint"]
        orig=by_input[id]
        mr=by_manager[id]
        symbol=event["symbol"]
        if (mr["symbol"] != symbol or mr["trader_id"] != event["trader"]
            or mr["intake"] != "CIBO_MANAGEMENT_RECEIVED"):
            raise MissingPathError("Manager/Trader/QDLE identity mismatch")
        t=orig["trader_opportunity"]
        change="ECONOMIC_PROTECTIVE_STOP_PROPOSED" in mr["reason_codes"]
        financed=event["status"]=="RESERVED_FOR_TRADER"
        result=None
        if change:
            if financed:
                raise MissingPathError("changed stop incorrectly financed at original stop")
            status="ECONOMIC_STOP_NEEDS_QDLE_REQUOTE_AND_PATH"
        elif not financed:
            status="ORIGINAL_STOP_NOT_FINANCED"
        else:
            with localcontext() as ctx:
                ctx.prec=100
                entry=D(str(t["intended_entry"]))
                stop=D(str(t["stop_loss"]))
                per_price=D(event["stop_loss_usd_per_lot"])/abs(entry-stop)
                trade=CiboManagedTrade(
                    signal_id=id, symbol=symbol,
                    side="BUY" if t["side"]=="long" else "SELL",
                    entry_at=datetime.fromisoformat(event["at"]),
                    entry_price=entry,
                    trader_structural_stop_price=stop,
                    economic_stop_price=stop,
                    trader_take_profit_price=D(str(t["take_profit"])),
                    lots=D(event["lots"]),min_lot=D(".01"),lot_step=D(".01"),
                    price_pnl_usd_per_lot_per_unit=per_price,
                    roundtrip_commission_usd_per_lot=D(
                        event["commission_roundtrip_proxy_per_lot"]
                    ),
                    maximum_all_in_risk_usd=D(event["risk_budget_usd"])+D(".000000001"),
                )
            # If path missing, call actual engine with tuple(): legitimate
            # non-performance receipt rather than extrapolating Trader R.
            result=replay_cibo_managed_position(trade,paths.get(id,tuple()))
            status=("MANAGED_EXIT_ISOLATED_RESEARCH_ONLY"
                    if result.status=="SHADOW_SETTLED"
                    else "MANAGED_EXIT_MISSING_PRICE_PATH")
        statuses[status]+=1
        symbol_stats[symbol][status]+=1
        symbol_stats[symbol]["signals_received"]+=1
        receipts.append({
            "signal_fingerprint":id,
            "symbol":symbol,
            "trader_id":event["trader"],
            "intake_status":"CIBO_MANAGEMENT_RECEIVED",
            "qdle_original_stop_state":event["status"],
            "economic_stop_alternative_proposed":change,
            "managed_exit_status":status,
            "original_exit_history_not_reused_for_modified_stop":True,
            "actual_economic_exit_at": (
                result.exit_at.isoformat() if result and result.exit_at else None
            ),
            "managed_exit_isolated_net_pnl_proxy": (
                str(result.net_pnl_usd_proxy) if result and
                result.net_pnl_usd_proxy is not None else None
            ),
            "real_mt5_fills":0,
        })
    if sum(statuses.values())!=3368:
        raise MissingPathError("lost a Trader signal")
    if (qdle["real_fundednext_fills"]!=0 or qdle["certified"]
        or manager["summary"]["old_cibo_cognitive_admission_gate_used"]):
        raise MissingPathError("replay authority/certification drift")
    summary={
        "schema":"qore.cibo.p0.managed-exit-3368-price-path-audit.v1",
        "signals_received":3368,
        "qdle_original_stop_funded_proposals":qdle["research_financed_proposals"],
        "qdle_original_stop_not_funded":qdle["research_unfundable_or_invalid"],
        "reason_counts":dict(sorted(statuses.items())),
        "by_symbol":{k:dict(sorted(v.items())) for k,v in sorted(symbol_stats.items())},
        "supplied_executable_price_paths":len(paths),
        "historical_manifest_contains_complete_bid_ask_ohlc":False,
        "manager_exit_engine_invocations":qdle["research_financed_proposals"],
        "managed_replay_sequential_NAV_recomputed":False,
        "policy_partial_trailing_breakeven_defensive_tested_in_unit_tests":True,
        "real_mt5_fills":0,
        "certified":False,
        "managed_strategy_final_NAV_USD":None,
        "managed_strategy_profit_factor":None,
        "managed_strategy_max_drawdown_pct":None,
        "note":"Original Trader R is control data, not changed economic SL/managed exit cashflow. Rebuild paths and sequential four-engine QDLE for managed NAV/PF/DD.",
    }
    return {"summary":summary,"receipts":receipts}


def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("--manifest",type=Path,required=True)
    p.add_argument("--manager",type=Path,required=True)
    p.add_argument("--qdle",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--executable-ohlc-paths",type=Path,default=None)
    a=p.parse_args()
    man=json.loads(a.manifest.read_text())
    mgr=json.loads(a.manager.read_text())
    qd=json.loads(a.qdle.read_text())
    paths=_load_market_paths(a.executable_ohlc_paths,{
        x["signal_fingerprint"] for x in man["opportunities"]
    })
    result=audit(man,mgr,qd,paths=paths)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("CIBO_P0_MANAGED_PRICE_PATH_AUDIT",json.dumps(result["summary"],sort_keys=True))


if __name__=="__main__":
    main()
