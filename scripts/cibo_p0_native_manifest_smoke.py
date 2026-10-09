#!/usr/bin/env python3
"""Probe true native CF01-CF19 on original sealed opportunities; NO MT5."""
from __future__ import annotations
import argparse
import json
from collections import Counter
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from cibo_p0_native_replay_runtime import reconstruct_native_max_at_epoch


def run(manifest):
    rows=manifest["opportunities"]
    sample={}
    for r in rows:
        sample.setdefault(r["trader_id"],r)
    successes=[]
    failures=[]
    for trader,r in sorted(sample.items()):
        try:
            inst, proof=reconstruct_native_max_at_epoch(
                original=r,decision_at=datetime.fromisoformat(r["market_decision_at"]),
                qore_cash_usd=Decimal("60"),peak_cash_usd=Decimal("60"),
                open_stop_risk_usd=Decimal("0"),broker_margin_held_usd=Decimal("0"),
                open_positions=0,broker_cash_usd=Decimal("2000"),
            )
            successors=dict(trader=trader,signal=r["signal_fingerprint"],
                            mode=inst.mode,digest=proof["native_decision_digest"],
                            faculty_count=proof["native_faculties_applicable"])
            successes.append(successors)
        except Exception as e:
            failures.append(dict(trader=trader,signal=r["signal_fingerprint"],
                                 error=f"{type(e).__name__}: {e}"[:600]))
    return {"tested":len(sample),"native_genuine":len(successes),
            "native_blocked":len(failures),"samples":successes,"blockers":failures,
            "certified":False,"no_broker_fills":True}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--manifest",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    opts=p.parse_args()
    result=run(json.loads(opts.manifest.read_text()))
    opts.output.parent.mkdir(parents=True,exist_ok=True)
    opts.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("P0_NATIVE_MAX_MANIFEST_SMOKE",json.dumps(result,sort_keys=True),flush=True)
    return 0 if result["native_blocked"]==0 else 1


if __name__=="__main__":
    raise SystemExit(main())
