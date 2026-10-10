"""Sixth-audit directional null: deterministic random entries in same H1 thesis.

RESEARCH LABELS ONLY. The original 2876 V49 opportunities and their 2020
MAX3 executions are never modified. We draw M1 CLOSE times from the same
market, NY session date and H1 thesis, independent of future returns.
A candidate is within the thesis if no OPPOSING CONFIRMED H1 event occurred
between the source's as-of state origin and that candidate decision. The
future-derived V49 h1_state_until property is NEVER consulted.

The first baseline is uniform across all eligible close times. The second
is matched to the original within-H1 clock third; coin-flip negative control
runs at the actual timestamps. 15/30/60m labels require contiguous provider
M1 and remain ex-post, never used to draw candidates or authorize trades.
"""

from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import random
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
    iter_cibo_m1,
)
from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerSession
from qore.infrastructure.trader_lab.capitalizer_generic_scalp_census_v48 import (
    _aggregate,
    _build_h1_bias_events,
    _operating_date,
)
from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    DEFAULT_LOOKBACK,
    DEV_WINDOW_END,
    DEV_WINDOW_START,
    V49Opportunity,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_h1_timing_session_diagnostic_v1 import (
    HORIZONS,
    aware,
    session_end_at,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_v49_v50_g_waterfall_v1 import (
    _jsonl,
    source_id,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_winner_retention_v1 import (
    _origin,
    _source_table,
)
from qore.infrastructure.trader_lab.capitalizer_session_clock import (
    capitalizer_session_at,
)
from qore.infrastructure.trader_lab.capitalizer_v49_development_economics import (
    V49EconomicTrade,
)

IDENTITY = "QORE_SCALPER_A2_SIXTH_AUDIT_H1_SAME_STATE_DIRECTION_NULL_V1"
SALT = "A2_SIXTH_PREREG_20261010_SOURCE_SHA256_SEED_01"
DRAWS = 32
MODES = ("UNIFORM_H1_STATE", "MATCHED_H1_CLOCK_THIRD")


def _seed(source_identifier: str, mode: str) -> int:
    return int.from_bytes(
        hashlib.sha256(f"{SALT}|{source_identifier}|{mode}".encode()).digest()[:8],
        "big",
    )


def _third(at: datetime) -> int:
    return at.minute // 20


@dataclass(frozen=True, slots=True)
class DirectionNullRow:
    source_opportunity_id: str
    symbol: str
    session: str
    operating_date: str
    original_entry_at: str
    direction: str
    h1_state_from: str
    h1_basis: str
    trigger_family: str
    original_realized_gross_r: str
    original_exit_reason: str
    original_h1_clock_third: int
    h1_state_candidate_count: int
    uniform_candidate_count: int
    clock_matched_candidate_count: int
    original_signed_price_15: str | None
    original_signed_price_30: str | None
    original_signed_price_60: str | None
    uniform_positive_15: int
    uniform_negative_15: int
    uniform_flat_15: int
    uniform_covered_15: int
    uniform_positive_30: int
    uniform_negative_30: int
    uniform_flat_30: int
    uniform_covered_30: int
    uniform_positive_60: int
    uniform_negative_60: int
    uniform_flat_60: int
    uniform_covered_60: int
    matched_positive_15: int
    matched_negative_15: int
    matched_flat_15: int
    matched_covered_15: int
    matched_positive_30: int
    matched_negative_30: int
    matched_flat_30: int
    matched_covered_30: int
    matched_positive_60: int
    matched_negative_60: int
    matched_flat_60: int
    matched_covered_60: int
    coinflip_positive_15: int
    coinflip_positive_30: int
    coinflip_positive_60: int
    sample_n: int = DRAWS
    null_used_future_bias_expiry: bool = False
    draw_uses_forward_outcomes: bool = False
    changed_original_trade: bool = False
    hindsight_only: bool = True

    def __post_init__(self) -> None:
        if (
            self.null_used_future_bias_expiry
            or self.draw_uses_forward_outcomes
            or self.changed_original_trade
            or not self.hindsight_only
        ):
            raise ValueError("baseline is diagnostic only; must not authorize trades")


def _future_label(
    bars: tuple[CapitalizerM1Bar, ...],
    opened: tuple[datetime, ...],
    consecutive: tuple[int, ...],
    at: datetime,
    entry: Decimal,
    side: int,
    session: str,
) -> tuple[Decimal | None, ...]:
    index = bisect.bisect_left(opened, at)
    if index == len(bars) or bars[index].opened_at != at:
        return tuple(None for _ in HORIZONS)
    end = session_end_at(at, session)
    out: list[Decimal | None] = []
    for horizon in HORIZONS:
        if at + timedelta(minutes=horizon) > end or (
            consecutive[index] < horizon
        ):
            out.append(None)
            continue
        out.append((bars[index + horizon - 1].close - entry) * side)
    return tuple(out)


def _runs(bars: tuple[CapitalizerM1Bar, ...]) -> tuple[int, ...]:
    if not bars:
        return ()
    lengths = [1] * len(bars)
    for i in range(len(bars) - 2, -1, -1):
        if bars[i].closed_at == bars[i + 1].opened_at:
            lengths[i] = lengths[i + 1] + 1
    return tuple(lengths)


def eligible_h1_state_times(
    source: V49Opportunity,
    candidates: tuple[CapitalizerM1Bar, ...],
    opposite_events: tuple[datetime, ...],
) -> tuple[CapitalizerM1Bar, ...]:
    """As-of source state membership uses only already CONFIRMED opposites.

    Candidate selection NEVER uses source.h1_state_until and NEVER uses
    any future directional movement, target or trade win/loss.
    """

    origin = aware(source.h1_state_from)
    original_at = aware(source.m1_trigger_confirmed_at)
    session = CapitalizerSession(source.session)
    out: list[CapitalizerM1Bar] = []
    for bar in candidates:
        at = bar.closed_at
        if at <= origin or at == original_at:
            continue
        if capitalizer_session_at(bar.opened_at) is not session or (
            _operating_date(bar.opened_at, session) != source.operating_date
        ):
            continue
        if at > session_end_at(bar.opened_at, source.session):
            continue
        # Count ONLY opposite H1 signals CONFIRMED after source origin and
        # before the candidate bar's close. A later event cannot exclude a
        # candidate because it did not yet exist.
        left = bisect.bisect_right(opposite_events, origin)
        right = bisect.bisect_right(opposite_events, at)
        if right != left:
            continue
        out.append(bar)
    return tuple(out)


def analyze_market(
    original: Path, native_m1: Path
) -> tuple[dict[str, Any], tuple[DirectionNullRow, ...]]:
    files = sorted(original.rglob("capitalizer-*-v49-hf-capacity-opportunities.jsonl"))
    exits = sorted(original.rglob("capitalizer-*-v49-development-economics-trades.jsonl"))
    if len(files) != 1 or len(exits) != 1:
        raise ValueError("one native market requires one original opportunity and trade ledger")
    sources = tuple(V49Opportunity(**x) for x in _jsonl(files[0]))
    trades = tuple(V49EconomicTrade(**x) for x in _jsonl(exits[0]))
    if not sources or len(sources) != len(trades):
        raise ValueError("original V49 source count changed")
    symbol = sources[0].symbol
    if any(s.symbol != symbol or s.session != sources[0].session for s in sources):
        raise ValueError("market/session source ledger mixed")
    source_table = _source_table(sources)
    by_source = {_origin(t, source_table): t for t in trades}
    if len(by_source) != len(sources):
        raise ValueError("ambiguous original source-trade identity")
    all_bars = tuple(b for b in iter_cibo_m1(native_m1)
                     if DEV_WINDOW_START - DEFAULT_LOOKBACK <= b.opened_at < DEV_WINDOW_END)
    if not all_bars or any(b.symbol != symbol for b in all_bars):
        raise ValueError("native M1 market/symbol mismatch")
    # We must rebuild H1 bias events from this same native M1 and the SAME V49
    # source detectors, rather than copying state_until future metadata.
    events = _build_h1_bias_events(_aggregate(all_bars, minutes=60))
    opposite: dict[str, tuple[datetime, ...]] = {
        "BULLISH": tuple(x.confirmed_at for x in events if x.direction.value == "BEARISH"),
        "BEARISH": tuple(x.confirmed_at for x in events if x.direction.value == "BULLISH"),
    }
    bars = tuple(b for b in all_bars if DEV_WINDOW_START <= b.opened_at < DEV_WINDOW_END)
    opened = tuple(b.opened_at for b in bars)
    consecutive = _runs(bars)
    groups: dict[tuple[str, str], list[CapitalizerM1Bar]] = defaultdict(list)
    session = CapitalizerSession(sources[0].session)
    for bar in bars:
        if capitalizer_session_at(bar.opened_at) is session:
            groups[(session.value, _operating_date(bar.opened_at, session))].append(bar)
    rows: list[DirectionNullRow] = []
    for source in sources:
        identifier = source_id(source)
        original_trade = by_source[identifier]
        decision = aware(source.m1_trigger_confirmed_at)
        side = 1 if source.h1_state_direction == "BULLISH" else -1
        if (
            aware(original_trade.entry_at) != decision
            or original_trade.entry_price != source.decision_reference_price
            or original_trade.direction != ("LONG" if side == 1 else "SHORT")
            or original_trade.stop_price != source.m15_protected_swing_price
            or original_trade.target_price != source.structural_target_witness_price
        ):
            raise ValueError("source is not original V49 trade")
        i = bisect.bisect_left(opened, decision)
        if i == 0 or bars[i - 1].closed_at != decision or (
            bars[i - 1].close != Decimal(source.decision_reference_price)
        ):
            raise ValueError("entry not witnessed by original last completed M1")
        eligible = eligible_h1_state_times(
            source, tuple(groups.get((source.session, source.operating_date), ())),
            opposite[source.h1_state_direction],
        )
        matched = tuple(bar for bar in eligible if _third(bar.closed_at) == _third(decision))
        originals = _future_label(
            bars, opened, consecutive, decision,
            Decimal(source.decision_reference_price), side, source.session,
        )
        counters: dict[str, int] = {}
        for mode, candidates in zip(MODES, (eligible, matched), strict=True):
            rng = random.Random(_seed(identifier, mode))
            picks = (
                tuple(candidates[rng.randrange(len(candidates))] for _ in range(DRAWS))
                if candidates else ()
            )
            for horizon in HORIZONS:
                counters[f"{mode}_{horizon}_positive"] = 0
                counters[f"{mode}_{horizon}_negative"] = 0
                counters[f"{mode}_{horizon}_flat"] = 0
                counters[f"{mode}_{horizon}_covered"] = 0
            for bar in picks:
                labels = _future_label(
                    bars, opened, consecutive, bar.closed_at,
                    bar.close, side, source.session,
                )
                for horizon, label in zip(HORIZONS, labels, strict=True):
                    if label is None:
                        continue
                    prefix = f"{mode}_{horizon}_"
                    counters[prefix + "covered"] += 1
                    category = "positive" if label > 0 else "negative" if label < 0 else "flat"
                    counters[prefix + category] += 1
        coin = random.Random(_seed(identifier, "COINFLIP_DIRECTION_CONTROL"))
        coin_positive: dict[int, int] = {h: 0 for h in HORIZONS}
        for _ in range(DRAWS):
            randomized_side = 1 if coin.randrange(2) else -1
            for horizon, label in zip(HORIZONS, originals, strict=True):
                if label is not None and (label * randomized_side * side) > 0:
                    coin_positive[horizon] += 1
        def value(
            mode: str, horizon: int, kind: str,
            observed: dict[str, int] = counters,
        ) -> int:
            return observed[f"{mode}_{horizon}_{kind}"]
        rows.append(DirectionNullRow(
            source_opportunity_id=identifier, symbol=symbol,
            session=source.session, operating_date=source.operating_date,
            original_entry_at=original_trade.entry_at,
            direction=source.h1_state_direction,
            h1_state_from=source.h1_state_from,
            h1_basis=source.h1_state_basis,
            trigger_family=source.m1_trigger_family,
            original_realized_gross_r=original_trade.realized_gross_r,
            original_exit_reason=original_trade.exit_reason,
            original_h1_clock_third=_third(decision),
            h1_state_candidate_count=len(eligible),
            uniform_candidate_count=len(eligible),
            clock_matched_candidate_count=len(matched),
            original_signed_price_15=str(originals[0]) if originals[0] is not None else None,
            original_signed_price_30=str(originals[1]) if originals[1] is not None else None,
            original_signed_price_60=str(originals[2]) if originals[2] is not None else None,
            uniform_positive_15=value(MODES[0],15,"positive"),
            uniform_negative_15=value(MODES[0],15,"negative"),
            uniform_flat_15=value(MODES[0],15,"flat"),
            uniform_covered_15=value(MODES[0],15,"covered"),
            uniform_positive_30=value(MODES[0],30,"positive"),
            uniform_negative_30=value(MODES[0],30,"negative"),
            uniform_flat_30=value(MODES[0],30,"flat"),
            uniform_covered_30=value(MODES[0],30,"covered"),
            uniform_positive_60=value(MODES[0],60,"positive"),
            uniform_negative_60=value(MODES[0],60,"negative"),
            uniform_flat_60=value(MODES[0],60,"flat"),
            uniform_covered_60=value(MODES[0],60,"covered"),
            matched_positive_15=value(MODES[1],15,"positive"),
            matched_negative_15=value(MODES[1],15,"negative"),
            matched_flat_15=value(MODES[1],15,"flat"),
            matched_covered_15=value(MODES[1],15,"covered"),
            matched_positive_30=value(MODES[1],30,"positive"),
            matched_negative_30=value(MODES[1],30,"negative"),
            matched_flat_30=value(MODES[1],30,"flat"),
            matched_covered_30=value(MODES[1],30,"covered"),
            matched_positive_60=value(MODES[1],60,"positive"),
            matched_negative_60=value(MODES[1],60,"negative"),
            matched_flat_60=value(MODES[1],60,"flat"),
            matched_covered_60=value(MODES[1],60,"covered"),
            coinflip_positive_15=coin_positive[15],
            coinflip_positive_30=coin_positive[30],
            coinflip_positive_60=coin_positive[60],
        ))
    if len({r.source_opportunity_id for r in rows}) != len(sources):
        raise ValueError("duplicated null source ID")
    return {
        "identity": IDENTITY, "symbol": symbol,
        "sources": len(sources), "joined": len(rows),
        "h1_events_source_detector": len(events),
        "seed_policy": SALT, "draws_per_mode": DRAWS,
        "candidate_membership_uses_h1_state_until": False,
        "randomization_uses_future_price_path": False,
        "no_trader_rules_changed": True,
        "trader_certified": False, "live_authorized": False,
    }, tuple(rows)


def _row_null(r: DirectionNullRow, h: int, mode: str) -> Decimal | None:
    covered = int(getattr(r, f"{mode}_covered_{h}"))
    if covered <= 0:
        return None
    return Decimal(int(getattr(r, f"{mode}_positive_{h}"))) / covered


def _summary(rows: tuple[DirectionNullRow, ...]) -> dict[str, Any]:
    result: dict[str, Any] = {"n": len(rows)}
    for h in HORIZONS:
        real = [r for r in rows if getattr(r, f"original_signed_price_{h}") is not None]
        p = sum(Decimal(getattr(r, f"original_signed_price_{h}")) > 0 for r in real)
        result[str(h)] = {
            "actual_covered": len(real),
            "actual_positive": p,
            "actual_positive_fraction": str(Decimal(p)/len(real)) if real else None,
        }
        for mode in ("uniform", "matched"):
            paired = [
                (r, n) for r in real
                if (n := _row_null(r, h, mode)) is not None
            ]
            result[str(h)][mode] = {
                "original_paired_n": len(paired),
                "missing_random_coverage": len(real) - len(paired),
                "actual_positive_fraction_paired": (
                    str(
                        sum(Decimal(getattr(r, f"original_signed_price_{h}")) > 0
                            for r, _ in paired) / Decimal(len(paired))
                    )
                    if paired else None
                ),
                "null_positive_fraction_per_source_average": (
                    str(sum((n for r,n in paired),Decimal(0))/len(paired))
                    if paired else None
                ),
                "actual_minus_null_percentage_point": (
                    str(Decimal(100)*sum(
                        (Decimal(Decimal(getattr(r, f"original_signed_price_{h}")) > 0)-n
                         for r,n in paired), Decimal(0))/len(paired))
                    if paired else None
                ),
            }
        coin_n = [r for r in real if getattr(r,f"original_signed_price_{h}") is not None]
        result[str(h)]["coinflip_random_direction_on_actual_entries"] = {
            "expected_positive_fraction": (
                str(sum(Decimal(getattr(r, f"coinflip_positive_{h}"))/DRAWS
                        for r in coin_n)/len(coin_n)) if coin_n else None
            ),
            "interpretation": "NEGATIVE_CONTROL_ON_ORIGINAL_TIMESTAMPS_POSTHOC",
        }
    return result


def _bootstrap_date_cluster(
    rows: tuple[DirectionNullRow, ...],
    horizon: int,
    mode: str,
    *,
    repetitions: int = 1000,
) -> dict[str, Any]:
    by_date: dict[str, list[Decimal]] = defaultdict(list)
    for r in rows:
        val = getattr(r,f"original_signed_price_{horizon}")
        null = _row_null(r,horizon,mode)
        if val is None or null is None:
            continue
        by_date[r.operating_date].append(Decimal(Decimal(val)>0) - null)
    dates = sorted(by_date)
    if not dates:
        return {"paired_n": 0, "date_clusters": 0, "bootstrap_ci": None}
    rng = random.Random(_seed("ALL_MARKETS_NINE_ASSET",f"DATE_BOOTSTRAP_{horizon}_{mode}"))
    vals: list[float] = []
    for _ in range(repetitions):
        sampled = [by_date[dates[rng.randrange(len(dates))]] for _ in dates]
        total = sum((sum(d,Decimal(0)) for d in sampled),Decimal(0))
        size = sum(len(d) for d in sampled)
        vals.append(float(total / size))
    vals.sort()
    return {
        "paired_n": sum(len(x) for x in by_date.values()),
        "date_clusters": len(dates),
        "bootstrap_ci": [vals[24], vals[974]],
        "units": "original_success_probability_minus_random_same_bias_success_probability",
        "bootstrap_repetitions": repetitions,
        "cluster": "NY_OPERATING_DATE_ACROSS_ALL_MARKETS",
    }


def aggregate(root: Path) -> dict[str, Any]:
    market_files = sorted(root.rglob("scalper-h1-bias-null-market.json"))
    reports = [json.loads(p.read_text()) for p in market_files]
    if len(reports) != 9 or len({r["symbol"] for r in reports}) != 9:
        raise ValueError("nine distinct market null models required")
    rows = tuple(
        DirectionNullRow(**x)
        for path in sorted(root.rglob("scalper-h1-bias-null-rows.jsonl"))
        for x in _jsonl(path)
    )
    if len(rows) != 2876 or len({r.source_opportunity_id for r in rows}) != 2876:
        raise ValueError("null model original source population changed")
    grouped: dict[tuple[str,str],list[DirectionNullRow]] = defaultdict(list)
    for row in rows:
        grouped[(row.session,row.operating_date)].append(row)
    selected = tuple(
        row for key in sorted(grouped)
        for row in sorted(
            grouped[key],
            key=lambda r: (aware(r.original_entry_at), r.symbol, r.trigger_family),
        )[:3]
    )
    if len(selected)!=2020 or sum(Decimal(r.original_realized_gross_r)>0 for r in selected)!=1167:
        raise ValueError("original MAX3 winner population changed")
    pnl=sum((Decimal(r.original_realized_gross_r) for r in selected),Decimal(0))
    if abs(pnl-Decimal("-233.2693270763665099166092077"))>Decimal("1e-15"):
        raise ValueError("original frozen V49 economic source changed")
    groupby: dict[str,dict[str,list[DirectionNullRow]]] = {
        k:defaultdict(list) for k in ("session","market","family","bias_age")
    }
    for r in selected:
        groupby["session"][r.session].append(r)
        groupby["market"][r.symbol].append(r)
        groupby["family"][r.trigger_family].append(r)
        age=(aware(r.original_entry_at)-aware(r.h1_state_from)).total_seconds()/60
        groupby["bias_age"][
            "UNDER_60" if age<60 else "60_TO_180" if age<180 else "AT_LEAST_180"
        ].append(r)
    return {
        "identity": IDENTITY,
        "markets": 9, "sources": len(rows), "selected_max3":len(selected),
        "source_winners_unchanged":1167, "net_R_unchanged":str(pnl),
        "draws_each_mode":DRAWS, "fixed_seed_salt":SALT,
        "primary":_summary(selected),
        "cluster_bootstrap":{
            str(h):{mode:_bootstrap_date_cluster(selected,h,mode)
                    for mode in ("uniform","matched")}
            for h in HORIZONS
        },
        "by":{dimension:{name:_summary(tuple(vals)) for name,vals in d.items()}
              for dimension,d in groupby.items()},
        "count_no_candidate_state":sum(r.uniform_candidate_count==0 for r in selected),
        "count_no_clock_matched_state":sum(r.clock_matched_candidate_count==0 for r in selected),
        "h1_state_until_used":False,
        "outcomes_used_to_choose_null":False,
        "coinflip_random_side_only_research":True,
        "experimental_filter_promoted":False,
        "trader_certified":False,
        "live_authorized":False,
    }


def main() -> None:
    p=argparse.ArgumentParser()
    sub=p.add_subparsers(dest="mode",required=True)
    m=sub.add_parser("market")
    m.add_argument("control",type=Path)
    m.add_argument("native_m1",type=Path)
    m.add_argument("output",type=Path)
    a=sub.add_parser("matrix")
    a.add_argument("market_outputs",type=Path)
    a.add_argument("output",type=Path)
    args=p.parse_args()
    if args.mode=="market":
        report,rows=analyze_market(args.control,args.native_m1)
        args.output.mkdir(parents=True,exist_ok=True)
        (args.output/"scalper-h1-bias-null-market.json").write_text(
            json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8"
        )
        with (args.output/"scalper-h1-bias-null-rows.jsonl").open("w",encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(asdict(row),sort_keys=True)+"\n")
        print(json.dumps(report,sort_keys=True))
    else:
        report=aggregate(args.market_outputs)
        args.output.mkdir(parents=True,exist_ok=True)
        (args.output/"scalper-h1-bias-null-nine-market.json").write_text(
            json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8"
        )
        print(json.dumps({"identity":IDENTITY,"primary":report["primary"],
                          "bootstrap":report["cluster_bootstrap"],
                          "trader_certified":False},sort_keys=True))


if __name__=="__main__":
    main()
