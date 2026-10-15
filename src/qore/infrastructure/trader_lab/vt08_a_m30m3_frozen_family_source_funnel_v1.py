"""VT08 A: frozen bullish M30 C2 -> C3 M3 source-funnel evidence.

This is a census of first-fail *shapes*, not a TTrades complete entry, fill,
economics or new model-selection trial. All 5 frozen markets are scanned at
the previously fixed NY windows 01-05 / 05-09 / 09-13, and no profit, stop,
target, or post-entry bar participates in a source decision.

Every candidate and negative first-fail is counted. Time-stratified
blinded examples retain native M3/M15 bar lineage for independent B adjudication.
"""
from __future__ import annotations

import hashlib
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.vt08_5m_a_native_m30_m3_favorable_entry_v1 import (
    aggregate,
    closed_source_window,
    same_ohlc,
)
from qore.infrastructure.trader_lab.vt08_a_m30m3_raw_bar_custody_v1 import (
    MARKETS,
    _bar_receipt,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_backtest_v1 import (
    load_market_evidence,
)
from qore.infrastructure.trader_lab.vt08_cognitive_m3_fractal_density_recovery_v1 import (
    _load_m3,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_b01_r3_8 import (
    Vt08B01Bar,
    protected_swings_in_candle2,
)

SCHEMA = "qore.vt08.a.frozen_bullish_m30m3.source_funnel.v1"
NY = ZoneInfo("America/New_York")
STAGES = (
    "MISSING_M30_M3_OR_M15",
    "M30_CROSS_SOURCE_MISMATCH",
    "C2_NOT_BULLISH_SINGLE_LOW_SWEEP",
    "NO_M3_CISD_PS_SHAPE",
    "MULTIPLE_M3_CISD_PS_SHAPES_D",
    "UNIQUE_M3_CISD_PS_SHAPE_REQUIRES_AUTHOR_ADJUDICATION",
)


def _iso(t: datetime) -> str:
    return t.astimezone(UTC).isoformat()


def _within_frozen_owner_windows(t: datetime) -> bool:
    ny=t.astimezone(NY)
    return (
        1 <= ny.hour < 13
        and ny.minute in (0,30)
        and ny.second == 0 and ny.microsecond == 0
    )


def bullish_c2_geometry(c1: Vt08B01Bar, c2: Vt08B01Bar) -> bool:
    """Only source C2 closed OHLC shape. DOES NOT authenticate swept POI."""
    if c1.closed_at.astimezone(UTC) != c2.opened_at.astimezone(UTC):
        raise ValueError("noncontiguous C1/C2")
    return (
        c2.low < c1.low
        and c2.high <= c1.high
        and c1.low < c2.close < c1.high
        and c2.close > c2.open
    )


def classify(
    *,
    c1: tuple[Vt08B01Bar, ...] | None,
    c2: tuple[Vt08B01Bar, ...] | None,
    c1_m15: tuple[Vt08B01Bar, ...] | None,
    c2_m15: tuple[Vt08B01Bar, ...] | None,
) -> tuple[str, dict[str, object]]:
    """First-fail order fixed BEFORE run, never consult C3's future bars."""
    if c1 is None or c2 is None or c1_m15 is None or c2_m15 is None:
        return STAGES[0], {}
    m30_c1=aggregate(c1,period_minutes=30,member_minutes=3)
    m30_c2=aggregate(c2,period_minutes=30,member_minutes=3)
    m15_c1=aggregate(c1_m15,period_minutes=30,member_minutes=15)
    m15_c2=aggregate(c2_m15,period_minutes=30,member_minutes=15)
    if not same_ohlc(m30_c1,m15_c1) or not same_ohlc(m30_c2,m15_c2):
        return STAGES[1], {}
    if not bullish_c2_geometry(m30_c1,m30_c2):
        return STAGES[2], {
            "single_low_sweep":m30_c2.low < m30_c1.low,
            "high_also_swept":m30_c2.high > m30_c1.high,
            "bullish_body_close":m30_c2.close > m30_c2.open,
        }
    ps=protected_swings_in_candle2(
        c2,side=DemoTradingSetupSide.LONG,important_level=m30_c1.low,
    )
    if not ps:
        return STAGES[3], {}
    if len(ps)>1:
        return STAGES[4], {"m3_ps_proxy_count":len(ps)}
    p=ps[0]
    if p.confirmed_at.astimezone(UTC) > m30_c2.closed_at.astimezone(UTC):
        raise ValueError("M3 PS confirmation after C3 entry decision")
    return STAGES[5], {
        "m3_ps_proxy_count":1,
        "cisd_confirmed_at_utc":_iso(p.confirmed_at),
        "opposing_series_opened_at_utc":_iso(p.opposing_series_opened_at),
        "ps_proxy_price":str(p.price),
        "cisd_level_proxy":str(p.cisd_level),
        "proxy_not_author_validated":True,
        "reference_swing_author_valid":False,
        "significant_poi_author_valid":False,
        "breaker_low_author_valid":False,
        "htf_untouched_target_author_valid":False,
        "methodology_complete":False,
    }


def closed_pre_c2_h1_receipts(
    i15: dict[datetime, Vt08B01Bar],
    *,
    c2_open: datetime,
    raw_m15_sha: str,
) -> list[dict[str, object]]:
    """Three H1 closed candles as 12 original M15 bars, NEVER C2 future.

    The author's relevant swing still cannot be inferred solely from this
    window. B must independently judge semantic relevance; this method only
    supplies complete preceding clock-bounded physical context.
    """
    cutoff=c2_open.astimezone(UTC)
    latest_hour_end=cutoff.replace(minute=0,second=0,microsecond=0)
    begin=latest_hour_end-timedelta(hours=3)
    bars=closed_source_window(i15,begin=begin,count=12,minutes=15)
    if bars is None:
        return []
    if any(bar.closed_at.astimezone(UTC) > cutoff for bar in bars):
        raise ValueError("pre-C2 H1 source contains future information")
    return [_bar_receipt(bar,raw_m15_sha,"M15_PRE_C2_H1") for bar in bars]


def _sample_records(rows: list[dict[str, object]], n: int=8) -> list[dict[str, object]]:
    if len(rows) <= n:
        return rows
    indices=[i*(len(rows)-1)//(n-1) for i in range(n)]
    return [rows[i] for i in indices]


def run(market: str, m3_path: Path, m15_path: Path) -> dict[str, object]:
    if market not in MARKETS or not m3_path.is_file() or not m15_path.is_file():
        raise ValueError("missing physical source / unsupported market")
    m3_sha=hashlib.sha256(m3_path.read_bytes()).hexdigest()
    m15_sha=hashlib.sha256(m15_path.read_bytes()).hexdigest()
    _,base_market,_,_,m15=load_market_evidence(m15_path)
    if base_market != market:
        raise ValueError("M15 symbol incompatible")
    m3=_load_m3(m3_path,expected_symbol=market)
    i3={bar.opened_at.astimezone(UTC):bar for bar in m3}
    i15={bar.opened_at.astimezone(UTC):bar for bar in m15}
    if len(i3)!=len(m3) or len(i15)!=len(m15):
        raise ValueError("duplicate physical bar clock")
    counts:Counter[str]=Counter()
    years:dict[str,Counter[str]]=defaultdict(Counter)
    rows:dict[str,list[dict[str,object]]]=defaultdict(list)
    for c2_open in sorted(t for t in i3 if _within_frozen_owner_windows(t)):
        c1_open=c2_open-timedelta(minutes=30)
        c3_open=c2_open+timedelta(minutes=30)
        c1=closed_source_window(i3,begin=c1_open,count=10,minutes=3)
        c2=closed_source_window(i3,begin=c2_open,count=10,minutes=3)
        c1_15=closed_source_window(i15,begin=c1_open,count=2,minutes=15)
        c2_15=closed_source_window(i15,begin=c2_open,count=2,minutes=15)
        stage,detail=classify(
            c1=c1,c2=c2,c1_m15=c1_15,c2_m15=c2_15,
        )
        counts[stage]+=1
        years[str(c2_open.astimezone(NY).year)][stage]+=1
        # Keep only compact pre-entry classification for complete census.
        # Materialize full source receipts for 8 time-stratified cases/stage.
        rows[stage].append({"c2_open":c2_open,"details":detail})
    # The Owner cap is earliest geometrically eligible C2 per market/NY day.
    # This is an UPPER BOUND on true TTrades entries, not a selection by PnL.
    first_by_ny_day:dict[str,datetime]={}
    for item in rows[STAGES[5]]:
        c2_at=item["c2_open"]
        assert isinstance(c2_at,datetime)
        day=c2_at.astimezone(NY).date().isoformat()
        first_by_ny_day.setdefault(day,c2_at)
    examples:dict[str,list[dict[str,object]]]={}
    for stage in STAGES:
        # Export ALL pre-outcome single-PS geometry for independent reviewer B;
        # sample negatives chronologically with no PnL. Full positive precursor
        # disclosure prevents choosing only favorable visual examples later.
        selected=(
            rows[stage] if stage == STAGES[5]
            else _sample_records(rows[stage])
        )
        examples[stage]=[]
        for item in selected:
            c2_open=item["c2_open"]
            assert isinstance(c2_open,datetime)
            c2=closed_source_window(i3,begin=c2_open,count=10,minutes=3)
            c2_15=closed_source_window(i15,begin=c2_open,count=2,minutes=15)
            c1=closed_source_window(
                i3,begin=c2_open-timedelta(minutes=30),count=10,minutes=3,
            )
            pre_h1=closed_pre_c2_h1_receipts(
                i15,c2_open=c2_open,raw_m15_sha=m15_sha,
            )
            c3_open=c2_open+timedelta(minutes=30)
            examples[stage].append({
                "market":market,
                "family":"BULLISH_M30_C2_REVERSAL_M3_CISD_C3_POSITIONAL",
                "c1_opened_at_utc":_iso(c2_open-timedelta(minutes=30)),
                "c2_opened_at_utc":_iso(c2_open),
                "decision_at_utc":_iso(c3_open),
                "ny_date":c2_open.astimezone(NY).date().isoformat(),
                "stage":stage,
                "details":item["details"],
                "source_m3_file_sha256":m3_sha,
                "source_m15_file_sha256":m15_sha,
                "c1_m3_raw_bar_receipts":[
                    _bar_receipt(x,m3_sha,"M3") for x in c1
                ] if c1 is not None else [],
                "pre_c2_h1_m15_raw_bar_receipts":pre_h1,
                "pre_c2_h1_context_available":len(pre_h1)==12,
                "reference_swing_author_relevance_validated":False,
                "c2_m3_raw_bar_receipts":[
                    _bar_receipt(x,m3_sha,"M3") for x in c2
                ] if c2 is not None else [],
                "c2_m15_raw_bar_receipts":[
                    _bar_receipt(x,m15_sha,"M15") for x in c2_15
                ] if c2_15 is not None else [],
                "A_rule_complete":False,
                "B_signoff":False,
                "cognitive_ready":False,
                "broker_fill":False,
                "pnl_read":False,
            })
    return {
        "schema":SCHEMA,
        "market":market,
        "source_m3_sha256":m3_sha,
        "source_m15_sha256":m15_sha,
        "selection":"ALL_C2_M30_OPEN_WITHIN_OWNER_WINDOWS_FIRST_FAIL_PRE_PNL",
        "c2_windows_total":sum(counts.values()),
        "stage_counts":{s:counts[s] for s in STAGES},
        "stage_counts_by_year":{y:{s:c[s] for s in STAGES}
                                for y,c in sorted(years.items())},
        "all_unique_proxy_cases_with_raw_receipts":len(rows[STAGES[5]]),
        "earliest_unique_proxy_per_market_ny_day_upper_bound":len(first_by_ny_day),
        "same_day_extra_structural_precursors_excluded_by_owner_cap":(
            len(rows[STAGES[5]])-len(first_by_ny_day)
        ),
        "examples_by_stage":examples,
        "M30_SOURCE_GEOMETRY_ONLY":True,
        "AUTHOR_RELEVANT_SWING_POI_BREAKER_TARGET_PENDING":True,
        "source_complete_entries":0,
        "A_B_signed_manifest":False,
        "real_cognitive_admissions":0,
        "fills":0,
        "pnl_evaluated":False,
        "sealed_holdout_accessed":False,
        "sizing_applied":False,
    }
