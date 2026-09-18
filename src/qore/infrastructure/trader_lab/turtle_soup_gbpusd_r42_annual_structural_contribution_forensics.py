"""GBPUSD R42 — annual structural contribution forensics.

Uses the exact R39 907-trade frozen set. Calendar blocks are diagnostic only.
No rule is selected here. The objective is to identify pre-entry structural
categories that systematically dilute the two negative annual blocks after
the R41 near-zero SHORT overlay.
"""
from __future__ import annotations

import hashlib
import json
import sys
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    turtle_soup_gbpusd_r37_structural_quality_governor as r37,
)

IDENTITY = "TURTLE_SOUP_GBPUSD_R42_ANNUAL_STRUCTURAL_CONTRIBUTION_FORENSICS_V1"
SOURCE_RUN_ID = 35353073610
SOURCE_ARTIFACT_ID = 10550866581
SOURCE_GIT_SHA = "e02d9384fbe6521040fc2779a085c43b8d5f0f92"
SOURCE_REPORT_SHA256 = "ba315d13aedf8ba65bce43d628a97b44925ccf810d55a39bfcf60f4a29544690"
SOURCE_TRADES_SHA256 = "693a55aa4f1bed4c211976e0aa54b469c62902caec88d7490268567af32ed8c0"

SHORT_SCALE = Decimal("0.005")
DRAWDOWN_GOVERNOR = r37.GOVERNORS["DD_1_3_SCALE_075_025"]

@dataclass(frozen=True, slots=True)
class Trade:
    entry_at: datetime
    side: str
    source: str
    family: str | None
    classification: str
    target_rank: int
    target_route: str
    raw_net_010_r: Decimal
    frozen_structural_scale: Decimal


def _single(root: Path, name: str) -> Path:
    matches=list(root.rglob(name))
    if len(matches)!=1:
        raise ValueError(f"expected one {name}, got {len(matches)}")
    return matches[0]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(root: Path) -> list[Trade]:
    report=_single(root,"r39-5y-validation-report.json")
    trades=_single(root,"r39-5y-scaled-trades.jsonl")
    git=_single(root,"git-sha.txt")
    if _sha256(report)!=SOURCE_REPORT_SHA256:
        raise ValueError("R39 report hash drift")
    if _sha256(trades)!=SOURCE_TRADES_SHA256:
        raise ValueError("R39 trade hash drift")
    if git.read_text().strip()!=SOURCE_GIT_SHA:
        raise ValueError("R39 git drift")
    rows=[]
    with trades.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row=json.loads(line)
            rows.append(Trade(
                entry_at=datetime.fromisoformat(str(row["entry_at"])),
                side=str(row["side"]),
                source=str(row["source"]),
                family=None if row["family"] is None else str(row["family"]),
                classification=str(row["classification"]),
                target_rank=int(row["target_rank"]),
                target_route=str(row["target_route"]),
                raw_net_010_r=Decimal(str(row["raw_net_010_r"])),
                frozen_structural_scale=Decimal(str(row["structural_scale"])),
            ))
    if len(rows)!=907:
        raise ValueError("trade count drift")
    return rows


def _pf(values: Sequence[Decimal]) -> Decimal | None:
    gains=sum((v for v in values if v>0),Decimal(0))
    losses=-sum((v for v in values if v<0),Decimal(0))
    return None if losses==0 else gains/losses


def _stats(values: Sequence[Decimal]) -> dict[str,Any]:
    pf=_pf(values)
    return {
        "trades":len(values),
        "total_r":str(sum(values,Decimal(0))),
        "profit_factor":None if pf is None else str(pf),
    }


def _year_index(at: datetime) -> int:
    boundaries=[
        datetime(2021,9,17,tzinfo=UTC),
        datetime(2022,9,17,tzinfo=UTC),
        datetime(2023,9,17,tzinfo=UTC),
        datetime(2024,9,17,tzinfo=UTC),
        datetime(2025,9,17,tzinfo=UTC),
        datetime(2026,9,17,tzinfo=UTC),
    ]
    for i,(a,b) in enumerate(zip(boundaries[:-1],boundaries[1:],strict=True),start=1):
        if a<=at<b:
            return i
    raise ValueError("trade outside 5Y window")


def _baseline_contributions(trades: Sequence[Trade]) -> list[tuple[Trade,Decimal]]:
    equity=Decimal(0)
    peak=Decimal(0)
    out=[]
    for trade in trades:
        overlay=SHORT_SCALE if trade.side=="short" else Decimal("1")
        dd_scale=r37._risk_scale(peak-equity,DRAWDOWN_GOVERNOR)
        scale=trade.frozen_structural_scale*overlay*dd_scale
        value=trade.raw_net_010_r*scale
        equity+=value
        peak=max(peak,equity)
        out.append((trade,value))
    return out


def run(source_root: Path, output: Path) -> dict[str,Any]:
    trades=_load(source_root)
    rows=_baseline_contributions(trades)

    feature_getters={
        "side":lambda t:t.side,
        "source":lambda t:t.source,
        "family":lambda t:"NONE" if t.family is None else t.family,
        "classification":lambda t:t.classification,
        "target_rank":lambda t:str(t.target_rank),
        "target_route":lambda t:t.target_route,
        "side+source":lambda t:f"{t.side}|{t.source}",
        "side+classification":lambda t:f"{t.side}|{t.classification}",
        "side+target_rank":lambda t:f"{t.side}|{t.target_rank}",
        "source+classification":lambda t:f"{t.source}|{t.classification}",
        "family+side":lambda t:f"{'NONE' if t.family is None else t.family}|{t.side}",
    }

    annual_total:dict[int,list[Decimal]]=defaultdict(list)
    groups:dict[str,dict[str,dict[int,list[Decimal]]]]=defaultdict(
        lambda:defaultdict(lambda:defaultdict(list))
    )
    for trade,value in rows:
        year=_year_index(trade.entry_at)
        annual_total[year].append(value)
        for feature,getter in feature_getters.items():
            groups[feature][getter(trade)][year].append(value)

    annual={
        str(y):_stats(annual_total[y])
        for y in range(1,6)
    }
    diagnostics:dict[str,dict[str,Any]]={}
    for feature,values in groups.items():
        diagnostics[feature]={}
        for value,by_year in values.items():
            yearly={str(y):_stats(by_year.get(y,[])) for y in range(1,6)}
            totals=[Decimal(yearly[str(y)]["total_r"]) for y in range(1,6)]
            diagnostics[feature][value]={
                "yearly":yearly,
                "positive_years":sum(v>0 for v in totals),
                "negative_years":sum(v<0 for v in totals),
                "total_5y_r":str(sum(totals,Decimal(0))),
                "worst_year_r":str(min(totals)),
            }

    report={
        "schema":"qore.turtle_soup_gbpusd.r42_annual_structural_contribution_forensics.v1",
        "identity":IDENTITY,
        "baseline":{
            "short_scale":str(SHORT_SCALE),
            "signals_suppressed":False,
            "calendar_time_used_as_rule":False,
            "annual":annual,
        },
        "diagnostics":diagnostics,
        "governance":{
            "research_only":True,
            "fresh_holdout_consumed":False,
            "candidate_certified":False,
            "live_authorized":False,
            "real_capital_authorized":False,
        },
    }
    output.mkdir(parents=True,exist_ok=True)
    (output/"r42-annual-structural-forensics-report.json").write_text(
        json.dumps(report,indent=2,sort_keys=True)+"\n"
    )
    return report


def main() -> None:
    if len(sys.argv)!=3:
        raise SystemExit("usage: module R39_ARTIFACT_ROOT OUTPUT_DIR")
    print(json.dumps(run(Path(sys.argv[1]),Path(sys.argv[2])),sort_keys=True))


if __name__=="__main__":
    main()
