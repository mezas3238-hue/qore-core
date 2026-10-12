"""Frozen TSMOM risk-scaled 33-source weekly 4w bootstrap; costs hypothetical."""
from __future__ import annotations

import argparse
import json
import math
import random
from collections import defaultdict
from pathlib import Path
from statistics import mean

from qore.research.alpha2_intermarket import MARKETS, sha256_file
from qore.research.alpha2_tsmom_daily_weekly_panel import era_weeks
from qore.research.alpha2_tsmom_final_scaled import IDENTITY as WORKER_ID
from qore.research.alpha2_tsmom_final_scaled import PREREG

IDENTITY = "QORE_ALPHA2_FINAL_TSMOM_RISK33_4WK_ASSUMED_COST_SCREEN_V1"
CROSSES = frozenset({
    "AUDJPY", "AUDCAD", "AUDCHF", "AUDNZD", "CADCHF", "CADJPY",
    "CHFJPY", "EURAUD", "EURCAD", "EURCHF", "EURGBP", "EURJPY",
    "EURNZD", "GBPAUD", "GBPCAD", "GBPCHF", "GBPJPY", "GBPNZD",
    "NZDCAD", "NZDCHF", "NZDJPY",
})
NONFX = frozenset({"NAS100", "SP500", "US30", "XAUUSD", "XAGUSD"})
MAJORS = frozenset(MARKETS) - CROSSES - NONFX
GROUPS = {"FULL33": frozenset(MARKETS), "FX_CROSSES21": CROSSES,
          "FX_MAJORS7": MAJORS, "NONFX5": NONFX}
B = 2000
SEED = 20261012


def source_load(root: Path, head: str) -> dict[str, dict]:
    files = sorted(root.rglob("alpha2-tsmom-final-risk-*.json"))
    if len(files) != 33:
        raise ValueError("FINAL_TSMOM_EXACT33_SOURCE_WORKERS_REQUIRED")
    output = {}
    for p in files:
        if p.with_name(p.name+".sha256").read_text(encoding="utf-8").strip() != (
            sha256_file(p)+"  "+p.name
        ):
            raise ValueError("FINAL_TSMOM_SOURCE_WORKER_SHA_MISMATCH")
        if (p.parent/"exact-code-head-sha.txt").read_text(encoding="utf-8").strip() != head:
            raise ValueError("FINAL_TSMOM_EXACT_HEAD_REQUIRED")
        x = json.loads(p.read_text(encoding="utf-8"))
        s = x.get("symbol")
        if (x.get("identity") != WORKER_ID or x.get("prereg_ancestor") != PREREG
            or s not in MARKETS or s in output
            or x.get("original_11year_RAW_QUALITY_sha_verified") is not True
            or x.get("embargoed_2024_plus_OHLC_not_read") is not True
            or x.get("prior_panel_previously_exposed_exploratory") is not True
            or x.get("broker_NET_not_computed") is not True
            or x.get("UTC001_certified") is not False
            or x.get("orders") != 0
            or x.get("count_events") != len(x.get("events", []))
        ):
            raise ValueError("FINAL_TSMOM_PROVENANCE_DENIED")
        output[s] = x
    if set(output) != set(MARKETS):
        raise ValueError("FINAL_TSMOM_ORIGINAL33_INCOMPLETE")
    return output


def _bootstrap(weekly: list[float], seed: int) -> list[float]:
    if not weekly:
        raise ValueError("FINAL_TSMOM_NO_CALENDAR_WEEKS")
    n = len(weekly)
    r = random.Random(seed)
    samples = []
    for _ in range(B):
        idx = []
        for _block in range(math.ceil(n/4)):
            first = r.randrange(n)
            idx.extend((first+k)%n for k in range(4))
        samples.append(sum(weekly[k] for k in idx[:n])/n)
    samples.sort()
    return [samples[int(B*.025)], samples[int(B*.975)-1]]


def report(workers: dict[str, dict]) -> dict:
    if set(workers) != set(MARKETS) or (len(CROSSES),len(MAJORS),len(NONFX)) != (21,7,5):
        raise ValueError("FINAL_TSMOM_FROZEN_FX28_NONFX5_ROSTER")
    eras = {}
    for ei, era in enumerate(("DEVELOPMENT","DIAGNOSTIC")):
        calendar = era_weeks(era)
        series = {}
        for gi, (name, group) in enumerate(GROUPS.items()):
            gross = defaultdict(float)
            assumed = defaultdict(float)
            seen = set()
            count = 0
            capped = 0
            for sym in group:
                for e in workers[sym]["events"]:
                    if e["era"] != era:
                        continue
                    wk = e["iso_week"]
                    key = (sym,wk)
                    if wk not in calendar or key in seen:
                        raise ValueError("FINAL_TSMOM_DUPLICATE_OR_OUTSIDE_ERA_WEEK")
                    seen.add(key)
                    g = e["gross_risk_scaled_reference_bps"]
                    cost = e["assumed_1bp_each_side_cost_bps"]
                    w = e["signed_risk_scaled_exposure"]
                    if (not all(isinstance(z,(float,int)) and math.isfinite(z)
                                for z in (g,cost,w))
                        or abs(w)>3 or cost <= 0 or
                        abs(cost-2*abs(w))>1e-8 or
                        abs(e["gross_minus_assumed_cost_proxy_bps"]-(g-cost))>1e-8
                        or e["broker_NET_NOT_VERIFIED"] is not True):
                        raise ValueError("FINAL_TSMOM_COST_OR_EXPOSURE_CONTRACT")
                    gross[wk] += g/len(group)
                    assumed[wk] += (g-cost)/len(group)
                    count += 1
                    capped += int(e["vol_target_cap_applied"])
            weekly = [assumed[w] for w in calendar]
            allgross = [gross[w] for w in calendar]
            active = sum(any((sym,w) in seen for sym in group) for w in calendar)
            sufficient = (active >= (52 if era=="DEVELOPMENT" else 26)
                          if name=="FULL33" else
                          active >= (26 if era=="DEVELOPMENT" else 13))
            series[name] = {
                "symbols":len(group), "events":count,
                "active_calendar_weeks":active,"calendar_weeks_all_including_cash":len(calendar),
                "cap_hit_events":capped,
                "cap_hit_frequency":capped/count if count else None,
                "sample_gate":sufficient,
                "weekly_gross_reference_mean_bps":mean(allgross),
                "weekly_gross_minus_1bp_per_side_assumed_cost_mean_bps":mean(weekly),
                "CI95_fourweek_block_assumed_cost_proxy_bps":_bootstrap(weekly,SEED+ei*100+gi),
                "not_broker_NET":True,
            }
        eras[era]=series
    enough = all(eras[e]["FULL33"]["sample_gate"] for e in eras)
    primary = all(
        eras[e]["FULL33"]["weekly_gross_minus_1bp_per_side_assumed_cost_mean_bps"]>0
        and eras[e]["FULL33"]["CI95_fourweek_block_assumed_cost_proxy_bps"][0]>0
        for e in eras
    )
    sector = all(
        eras[e]["NONFX5"]["sample_gate"]
        and eras[e]["NONFX5"]["weekly_gross_minus_1bp_per_side_assumed_cost_mean_bps"]>0
        and eras[e]["NONFX5"]["CI95_fourweek_block_assumed_cost_proxy_bps"][0]>0
        for e in eras
    )
    status = (
        "FINAL_TSMOM_INCONCLUSIVE_STOP_ANYWAY" if not enough else
        "EXPLORATORY_TSMOM_COST_PROXY_POSITIVE_NEEDS_NEW_OOS" if primary else
        "FINAL_TSMOM_FAIL_CLOSE_FAMILY_ON_EXPOSED_DATA"
    )
    return {
        "identity":IDENTITY, "prereg_ancestor":PREREG,
        "status":status, "last_TSMOM_spec_closed_regardless_outcome":True,
        "sector_only_exploratory_not_selected":bool(sector and not primary),
        "full33_exact":33,"FX_total28":28, "FX_crosses21":21,"FX_majors7":7,"nonFX5":5,
        "groups":{k:sorted(v) for k,v in GROUPS.items()},
        "eras":eras,
        "num_original_source_m5_SHA_verification_workers":33,
        "gross_minus_assumed_cost_only_not_broker_NET":True,
        "not_virgin_OOS":True,"NET_PF_DD_Sharpe_not_computed":True,
        "UTC001_certified":False,"orders":0,
    }


def main() -> None:
    p=argparse.ArgumentParser()
    p.add_argument("workers",type=Path)
    p.add_argument("out",type=Path)
    p.add_argument("--head",required=True)
    a=p.parse_args()
    data=report(source_load(a.workers,a.head))
    a.out.mkdir(parents=True,exist_ok=True)
    target=a.out/"alpha2-final-tsmom-risk33-sector-gross-minus-cost.json"
    target.write_text(json.dumps(data,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({
        "status":data["status"],"sector_only_signal":data["sector_only_exploratory_not_selected"],
        "DEV_FX21":data["eras"]["DEVELOPMENT"]["FX_CROSSES21"]["weekly_gross_minus_1bp_per_side_assumed_cost_mean_bps"],
        "DEV_NONFX5":data["eras"]["DEVELOPMENT"]["NONFX5"]["weekly_gross_minus_1bp_per_side_assumed_cost_mean_bps"],
        "DEV_FULL33":data["eras"]["DEVELOPMENT"]["FULL33"]["weekly_gross_minus_1bp_per_side_assumed_cost_mean_bps"],
        "DIAG_FULL33":data["eras"]["DIAGNOSTIC"]["FULL33"]["weekly_gross_minus_1bp_per_side_assumed_cost_mean_bps"],
        "NET":"BLOCKED",
    },sort_keys=True))


if __name__=="__main__":
    main()
