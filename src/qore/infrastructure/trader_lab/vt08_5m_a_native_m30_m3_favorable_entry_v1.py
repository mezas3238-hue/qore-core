"""Native M3 → M30 real source audit for TTrades favorable positional/retest entry.

Source M30 C1/C2 reconstructed from M3 10-bars each AND cross-attested
against native M15 two-bars each. New M30 C3 first open is observed at t.
M3 retest geometry is observed only AFTER each M3 bar closes; never fills.
No unproven HTF POI, daily EQ or author-valid protected swing assertion.
"""

from __future__ import annotations

import hashlib
from collections import Counter, defaultdict
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Final
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.vt08_5m_source_bias_asof_attestation_v1 import (
    SOURCE_SHA,
    attest_bias,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_backtest_v1 import (
    load_market_evidence,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_evaluator_v1 import (
    evaluate_expansion_at_entry_indexed,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_v1 import (
    ANCHORS_NY,
    EXPANSION_MARKETS,
)
from qore.infrastructure.trader_lab.vt08_cognitive_m3_fractal_density_recovery_v1 import (
    _load_m3,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_b01_r3_8 import (
    Vt08B01Bar,
    protected_swings_in_candle2,
)

SCHEMA: Final = "qore.vt08.a.native_m30_m3.favorable_entry_v1"
M3_RUN: Final = 35941643396
M15_RUN: Final = 35934924907
_NY = ZoneInfo("America/New_York")


def closed_source_window(
    source: dict[datetime, Vt08B01Bar],
    *,
    begin: datetime,
    count: int,
    minutes: int,
) -> tuple[Vt08B01Bar, ...] | None:
    start = begin.astimezone(UTC)
    unit = timedelta(minutes=minutes)
    collected: list[Vt08B01Bar] = []
    for _ in range(count):
        candle = source.get(start)
        if candle is None or candle.closed_at.astimezone(UTC) != start + unit:
            return None
        collected.append(candle)
        start += unit
    return tuple(collected)


def aggregate(
    bars: tuple[Vt08B01Bar, ...],
    *,
    period_minutes: int,
    member_minutes: int,
) -> Vt08B01Bar:
    if len(bars) != period_minutes // member_minutes:
        raise ValueError("incomplete source aggregate")
    t = bars[0].opened_at.astimezone(UTC)
    for bar in bars:
        if bar.opened_at.astimezone(UTC) != t:
            raise ValueError("missing/overlapping source bars")
        if bar.closed_at.astimezone(UTC) != (
            t + timedelta(minutes=member_minutes)
        ):
            raise ValueError("unclosed constituent")
        t = bar.closed_at.astimezone(UTC)
    return Vt08B01Bar(
        opened_at=bars[0].opened_at,
        closed_at=bars[-1].closed_at,
        open=bars[0].open,
        high=max(x.high for x in bars),
        low=min(x.low for x in bars),
        close=bars[-1].close,
    )


def same_ohlc(a: Vt08B01Bar, b: Vt08B01Bar) -> bool:
    return (
        a.opened_at.astimezone(UTC) == b.opened_at.astimezone(UTC)
        and a.closed_at.astimezone(UTC) == b.closed_at.astimezone(UTC)
        and (a.open, a.high, a.low, a.close)
        == (b.open, b.high, b.low, b.close)
    )


def eligible_owner_m30(t: datetime) -> bool:
    ny = t.astimezone(_NY)
    return (
        ny.minute in (0, 30)
        and ny.second == 0
        and ny.microsecond == 0
        and ((1 <= ny.hour < 5) or (5 <= ny.hour < 9) or (9 <= ny.hour < 13))
    )


def source_m30_reversal(
    c1: Vt08B01Bar,
    c2: Vt08B01Bar,
) -> DemoTradingSetupSide | None:
    if c1.closed_at.astimezone(UTC) != c2.opened_at.astimezone(UTC):
        raise ValueError("M30 C1/C2 must be contiguous")
    low_sweep = c2.low < c1.low
    high_sweep = c2.high > c1.high
    if low_sweep == high_sweep or not c1.low < c2.close < c1.high:
        return None
    return DemoTradingSetupSide.LONG if low_sweep else DemoTradingSetupSide.SHORT


def gross_geometry(
    *,
    side: DemoTradingSetupSide,
    entry: Decimal,
    stop: Decimal,
    target: Decimal,
) -> dict[str, str] | None:
    risk = entry - stop if side is DemoTradingSetupSide.LONG else stop - entry
    reward = target - entry if side is DemoTradingSetupSide.LONG else entry - target
    if risk <= 0 or reward <= 0:
        return None
    return {"risk": str(risk), "reward": str(reward), "rr": str(reward / risk)}


def retest_entry_opportunity(
    *,
    side: DemoTradingSetupSide,
    first_open: Decimal,
    stop: Decimal,
    target: Decimal,
    cisd_retest_level: Decimal,
    following_m3: tuple[Vt08B01Bar, ...],
    at: datetime,
) -> dict[str, object]:
    """One predeclared CISD-level retest; M3 OHLC touch ≠ BID/ASK fill.

    At t the LIMIT can be planned from *prior* PS. Later bar highs/lows are
    consulted ONLY to confirm opportunity at their CLOSED timestamps. Same
    M3 stop/target/touch order ambiguous => cannot label a clean touch.
    """
    if side is DemoTradingSetupSide.LONG:
        good = stop < cisd_retest_level < first_open < target
    else:
        good = target < first_open < cisd_retest_level < stop
    if not good:
        return {"status": "NO_FAVORABLE_PREDECLARED_CISD_LEVEL"}
    start = at.astimezone(UTC)
    for candle in following_m3:
        if candle.opened_at.astimezone(UTC) != start:
            raise ValueError("M3 future/missing or reordered")
        if candle.closed_at.astimezone(UTC) != start + timedelta(minutes=3):
            raise ValueError("M3 observation not closed")
        start = candle.closed_at.astimezone(UTC)
        touched = candle.low <= cisd_retest_level <= candle.high
        stopped = (
            candle.low <= stop
            if side is DemoTradingSetupSide.LONG
            else candle.high >= stop
        )
        targeted = (
            candle.high >= target
            if side is DemoTradingSetupSide.LONG
            else candle.low <= target
        )
        if touched and (stopped or targeted):
            return {
                "status": "SAME_BAR_ORDER_SEQUENCE_AMBIGUOUS",
                "observed_after_close": candle.closed_at.isoformat(),
            }
        if stopped:
            return {
                "status": "PREEMPTED_BY_STOP_BEFORE_TOUCH",
                "observed_after_close": candle.closed_at.isoformat(),
            }
        if targeted:
            return {
                "status": "TARGET_REACHED_BEFORE_RETEST",
                "observed_after_close": candle.closed_at.isoformat(),
            }
        if touched:
            return {
                "status": "CLEAN_OHLC_TOUCH_NOT_PHYSICAL_FILL",
                "observed_after_close": candle.closed_at.isoformat(),
                "predeclared_level": str(cisd_retest_level),
                "gross_geometry": gross_geometry(
                    side=side, entry=cisd_retest_level, stop=stop, target=target,
                ),
                "bid_ask_fill_proven": False,
            }
    return {"status": "NO_CISD_LEVEL_RETEST_IN_C3"}


def analyze_setup(
    *,
    market: str,
    c1: Vt08B01Bar,
    c2: Vt08B01Bar,
    c2_m3: tuple[Vt08B01Bar, ...],
    c3_first_m3: Vt08B01Bar,
    c3_m3: tuple[Vt08B01Bar, ...],
) -> dict[str, object]:
    """Predecision stops/targets and two execution styles on same mother."""
    if c3_first_m3.opened_at.astimezone(UTC) != c2.closed_at.astimezone(UTC):
        raise ValueError("M30 C3 open not aligned with completed C2")
    if c3_m3 and c3_m3[0] != c3_first_m3:
        raise ValueError("C3 M3 observations must start at C3 open")
    side = source_m30_reversal(c1, c2)
    if side is None:
        return {"status": "NO_M30_C2_REVERSAL_CLOSURE"}
    important = c1.low if side is DemoTradingSetupSide.LONG else c1.high
    swings = protected_swings_in_candle2(c2_m3, side=side, important_level=important)
    if not swings:
        return {"status": "NO_C2_M3_CISD_PS_PROXY"}
    if len(swings) > 1:
        return {"status": "MULTIPLE_PS_UNADJUDICATED", "ps_count": len(swings)}
    swing = swings[0]
    if swing.confirmed_at > c2.closed_at:
        raise AssertionError("M3 CISD confirmed in M30 future")
    target = c1.high if side is DemoTradingSetupSide.LONG else c1.low
    positional = gross_geometry(
        side=side, entry=c3_first_m3.open, stop=swing.price, target=target,
    )
    if positional is None:
        return {"status": "NO_POSITIVE_POS_EXIT_GEOMETRY"}
    retest = retest_entry_opportunity(
        side=side, first_open=c3_first_m3.open, stop=swing.price,
        target=target, cisd_retest_level=swing.cisd_level,
        following_m3=c3_m3, at=c2.closed_at,
    )
    sid = hashlib.sha256(
        (
            f"{SCHEMA}|{market}|{c2.opened_at.isoformat()}|"
            f"{side.value}|{swing.confirmed_at.isoformat()}"
        ).encode()
    ).hexdigest()
    return {
        "status": "M30_M3_SOURCE_GEOMETRY_ONLY",
        "origin_id": "vt08-m30m3:" + sid,
        "market": market,
        "side": side.value,
        "c1_closed_at": c1.closed_at.isoformat(),
        "c2_closed_at": c2.closed_at.isoformat(),
        "c2_m3_cisd_confirmed_at": swing.confirmed_at.isoformat(),
        "c2_m3_opposing_series_start": swing.opposing_series_opened_at.isoformat(),
        "c2_m3_ps_price": str(swing.price),
        "c2_m3_cisd_retest_level": str(swing.cisd_level),
        "source_poi_htf_confirmed": False,
        "entry_positional_proposed_at": c2.closed_at.isoformat(),
        "entry_positional_open": str(c3_first_m3.open),
        "opposite_c1_liquidity_target": str(target),
        "positional": positional,
        "retest": retest,
        "eq_intra_c2_used": False,
        "orders_authorized": False,
        "bid_ask_fill_verified": False,
    }


def earliest_clean_touch_per_market_day(
    observations: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Earliest independently CLOSED M3 retest per NY day, no PnL rank.

    Retest observation is posterior to the mother setup proposal; we never
    alter historical entry signals at their M30-open timestamps.
    Does not certify intrabar BID/ASK execution or authorize a trade.
    """
    selected: dict[str, dict[str, object]] = {}
    for record in observations:
        date_key = record.get("market_ny_date")
        retest = record.get("retest")
        positional = record.get("positional")
        if (
            not isinstance(date_key, str)
            or not isinstance(retest, dict)
            or retest.get("status") != "CLEAN_OHLC_TOUCH_NOT_PHYSICAL_FILL"
            or not isinstance(positional, dict)
        ):
            continue
        new_geom = retest.get("gross_geometry")
        observed = retest.get("observed_after_close")
        if not isinstance(new_geom, dict) or not isinstance(observed, str):
            raise ValueError("source closed M3 retest lacks geometry or clock")
        timestamp = datetime.fromisoformat(observed).astimezone(UTC)
        origin = record["origin_id"]
        if not isinstance(origin, str):
            raise ValueError("source event ID missing")
        opening = datetime.fromisoformat(
            str(record["entry_positional_proposed_at"])
        ).astimezone(UTC)
        if timestamp <= opening:
            raise AssertionError("retest selected before original M30 signal")
        original_risk = Decimal(str(positional["risk"]))
        refined_risk = Decimal(str(new_geom["risk"]))
        if original_risk <= refined_risk or refined_risk <= 0:
            raise AssertionError("retreat not favorable in risk units")
        pct = (Decimal(1) - refined_risk / original_risk) * 100
        candidate: dict[str, object] = {
            "market_ny_date": date_key,
            "origin_id": origin,
            "original_m30_open_at": opening.isoformat(),
            "first_clean_retest_m3_closed_at": timestamp.isoformat(),
            "positional_gross_rr": str(positional["rr"]),
            "retest_gross_rr": str(new_geom["rr"]),
            "risk_reduction_percent_gross": str(pct),
            "selection_policy": "EARLIEST_M3_CLOSED_TOUCH_THEN_STABLE_EVENT_ID",
            "bid_ask_fill_verified": False,
            "poi_author_source_verified": False,
            "trade_authorized": False,
        }
        old = selected.get(date_key)
        if old is None or (
            candidate["first_clean_retest_m3_closed_at"],
            candidate["origin_id"],
        ) < (
            old["first_clean_retest_m3_closed_at"],
            old["origin_id"],
        ):
            selected[date_key] = candidate
    return [selected[d] for d in sorted(selected)]


def median_decimals(values: list[Decimal]) -> str | None:
    if not values:
        return None
    ordered = sorted(values)
    n = len(ordered)
    return str(
        ordered[n // 2]
        if n % 2
        else (ordered[n // 2 - 1] + ordered[n // 2]) / 2
    )


def evaluate(base_path: Path, m3_path: Path) -> dict[str, object]:
    fingerprint, market, checked, sha, m15 = load_market_evidence(base_path)
    if market not in EXPANSION_MARKETS or sha != SOURCE_SHA:
        raise ValueError("source M15 outside consumed five markets")
    native_m3 = _load_m3(m3_path, expected_symbol=market)
    i3 = {x.opened_at: x for x in native_m3}
    i15 = {x.opened_at: x for x in m15}
    if len(i3) != len(native_m3) or len(i15) != len(m15):
        raise ValueError("duplicate source open")
    counts: Counter[str] = Counter()
    years: dict[str, Counter[str]] = defaultdict(Counter)
    daysets: dict[str, set[date]] = defaultdict(set)
    evidence: list[dict[str, object]] = []

    def mark(k: str, y: str, d: date) -> None:
        counts[k] += 1
        years[y][k] += 1
        daysets[k].add(d)

    for first in native_m3:
        local = first.opened_at.astimezone(_NY)
        if local.minute not in (0, 30) or local.second or local.microsecond:
            continue
        allowed = eligible_owner_m30(first.opened_at)
        if not allowed:
            counts["M30_OPENS_OUTSIDE_OWNER_H4"] += 1
            continue
        y, day = str(local.year), local.date()
        mark("OWNER_M30_C3_OPEN_ANCHORS", y, day)
        c1_start = first.opened_at - timedelta(minutes=60)
        c2_start = first.opened_at - timedelta(minutes=30)
        b1 = closed_source_window(i3, begin=c1_start, count=10, minutes=3)
        b2 = closed_source_window(i3, begin=c2_start, count=10, minutes=3)
        b15_c1 = closed_source_window(i15, begin=c1_start, count=2, minutes=15)
        b15_c2 = closed_source_window(i15, begin=c2_start, count=2, minutes=15)
        if not b1 or not b2 or not b15_c1 or not b15_c2:
            mark("M30_NATIVE_OR_M15_INCOMPLETE", y, day)
            continue
        c1, c2 = aggregate(b1, period_minutes=30, member_minutes=3), aggregate(
            b2, period_minutes=30, member_minutes=3,
        )
        if not (
            same_ohlc(c1, aggregate(b15_c1, period_minutes=30, member_minutes=15))
            and same_ohlc(c2, aggregate(b15_c2, period_minutes=30, member_minutes=15))
        ):
            mark("CROSS_TF_OHLC_MISMATCH", y, day)
            continue
        mark("M30_C1_C2_TWO_FEEDS_ATTESTED", y, day)
        side = source_m30_reversal(c1, c2)
        if side is None:
            mark("NOT_SINGLE_SWEEP_M30_C2_CLOSURE", y, day)
            continue
        mark("SINGLE_SWEEP_M30_C2_CLOSURE", y, day)
        c3_window = closed_source_window(
            i3, begin=first.opened_at, count=10, minutes=3,
        )
        if c3_window is None:
            mark("C3_M3_WINDOW_NOT_COMPLETE_FOR_RETEST_OBSERVATION", y, day)
            continue
        result = analyze_setup(
            market=market, c1=c1, c2=c2, c2_m3=b2,
            c3_first_m3=first, c3_m3=c3_window,
        )
        mark(result["status"], y, day)
        if result["status"] != "M30_M3_SOURCE_GEOMETRY_ONLY":
            continue
        gross = result["positional"]
        if not isinstance(gross, dict):
            raise AssertionError("gross positional geometry absent")
        rr = Decimal(gross["rr"])
        for threshold in (Decimal("1"), Decimal("1.5"), Decimal("2")):
            if rr >= threshold:
                mark(f"POSITIONAL_GROSS_RR_GE_{threshold}", y, day)
        r = result["retest"]
        if not isinstance(r, dict):
            raise AssertionError("missing retest status")
        mark(str(r["status"]), y, day)
        if r["status"] == "CLEAN_OHLC_TOUCH_NOT_PHYSICAL_FILL":
            geom = r.get("gross_geometry")
            if not isinstance(geom, dict):
                raise AssertionError("clean touch without known geometry")
            if Decimal(geom["risk"]) >= Decimal(gross["risk"]):
                raise AssertionError("predeclared favorable retracement didn't improve risk")
            mark("CLEAN_TOUCH_REDUCES_PRICE_RISK_VS_POSITIONAL", y, day)
            for threshold in (Decimal("1"), Decimal("1.5"), Decimal("2")):
                if Decimal(geom["rr"]) >= threshold:
                    mark(f"CLEAN_RETEST_GROSS_RR_GE_{threshold}", y, day)
        att = attest_bias(i15, decision_at=c2.closed_at)
        result["old_b01_bias_at_c2_close"] = (
            att.bias.value if att is not None and att.bias else None
        )
        result["old_b01_bias_relation"] = (
            "UNATTESTED" if att is None else
            "UNRESOLVED" if att.bias is None else
            "ALIGNED" if att.bias is side else "CONTRARY"
        )
        mark("OLD_B01_BIAS_" + str(result["old_b01_bias_relation"]), y, day)
        result["m30_owner_h4_eligible"] = allowed
        result["market_ny_date"] = day.isoformat()
        result["methodology_status"] = "SHAPE_ONLY_SOURCE_POI_UNVERIFIED"
        result["cognitive_ready"] = False
        evidence.append(result)

    # Post-census descriptive overlap only; never compare PnL or
    # selectively reject a M30/M3 setup based on old B01 membership.
    b01_per_day: Counter[str] = Counter()
    for bar in m15:
        ny = bar.opened_at.astimezone(_NY)
        if (
            ny.hour not in ANCHORS_NY
            or ny.minute != 0
            or ny.second != 0
            or ny.microsecond != 0
        ):
            continue
        evaluation = evaluate_expansion_at_entry_indexed(
            symbol=market, bars_by_open=i15, decision_at=bar.opened_at,
        )
        if evaluation.candidate is not None:
            b01_per_day[ny.date().isoformat()] += 1
    old_executable_days = {d for d, n in b01_per_day.items() if n == 1}
    all_b01_days = set(b01_per_day)
    if len(evidence) != counts["M30_M3_SOURCE_GEOMETRY_ONLY"]:
        raise AssertionError("M30/M3 geometry receipt mismatch")
    if len({r["origin_id"] for r in evidence}) != len(evidence):
        raise AssertionError("duplicate mother event origin ID")
    first_daily = earliest_clean_touch_per_market_day(evidence)
    m3_retest_days = {str(x["market_ny_date"]) for x in first_daily}
    cross_family_day_overlap = {
        "m15_b01_precardinality_candidates": sum(b01_per_day.values()),
        "m15_b01_candidate_days_including_conflicts": len(all_b01_days),
        "m15_b01_exactly_one_candidate_day_count": len(old_executable_days),
        "m30_m3_earliest_clean_retest_market_days": len(m3_retest_days),
        "overlap_with_m15_b01_selected_days": len(m3_retest_days & old_executable_days),
        "m30_m3_shape_days_absent_from_m15_b01": len(
            m3_retest_days - old_executable_days
        ),
        "m15_b01_days_without_m30_m3_clean_shape": len(
            old_executable_days - m3_retest_days
        ),
        "union_hypothetical_market_day_slots": len(
            old_executable_days | m3_retest_days
        ),
        "comparison_status": "STRUCTURAL_RESEARCH_ONLY_NO_ADDITIVE_TRADES",
    }
    if len(first_daily) != len(daysets["CLEAN_OHLC_TOUCH_NOT_PHYSICAL_FILL"]):
        raise AssertionError("daily first touch count not reconciled")
    median_improvement = median_decimals([
        Decimal(str(x["risk_reduction_percent_gross"])) for x in first_daily
    ])
    median_pos_rr = median_decimals([
        Decimal(str(x["positional_gross_rr"])) for x in first_daily
    ])
    median_retest_rr = median_decimals([
        Decimal(str(x["retest_gross_rr"])) for x in first_daily
    ])
    first_daily_rr_1_5 = sum(
        Decimal(str(x["retest_gross_rr"])) >= Decimal("1.5")
        for x in first_daily
    )
    return {
        "schema": SCHEMA,
        "market": market,
        "base_source_fingerprint": fingerprint,
        "checked_at": checked.isoformat(),
        "base_software_sha": sha,
        "m3_native_source_run": M3_RUN,
        "m15_base_source_run": M15_RUN,
        "counts": dict(sorted(counts.items())),
        "unique_ny_days_per_stage": {
            k: len(v) for k, v in sorted(daysets.items())
        },
        "per_year_counts": {k: dict(sorted(v.items())) for k, v in sorted(years.items())},
        "research_observations": evidence,
        "earliest_clean_retest_one_per_ny_day": first_daily,
        "cross_family_day_overlap": cross_family_day_overlap,
        "daily_retest_selection": {
            "market_days_with_first_clean_m3_retest": len(first_daily),
            "first_clean_retests_gross_rr_ge_1_5": first_daily_rr_1_5,
            "median_gross_risk_reduction_percent": median_improvement,
            "median_positional_gross_rr": median_pos_rr,
            "median_retest_gross_rr": median_retest_rr,
            "clock_rule": "FIRST_M3_CLOSE_OBSERVING_CLEAN_TOUCH_NOT_LIMIT_FILL",
            "candidate_count_without_daily_duplication": len(first_daily),
            "source_authority": "RESEARCH_ONLY_NOT_AUTHOR_COMPLETE",
            "physical_fills_certified": False,
        },
        "m30_m3_author_timeframe_pair_source_verified": True,
        "m30_m3_setup_poi_source_adjudicated": False,
        "gross_rr_only_no_bid_ask": True,
        "zero_execution_or_pnl": True,
        "broker_orders": 0, "fills": 0, "pnl_evaluated": False,
        "cognitive_ready": False,
        "sealed_7y_accessed": False,
    }
