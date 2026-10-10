"""Causal-as-of H1 phase/session runway plus POST-HOC direction/excursions.

Frozen V49 nine-market opportunity population; outcome NEVER selects signals.
Two distinct H1 metrics:
- clock phase: minute elapsed in the CURRENT H1; known at decision;
- price location in H1 range SEEN SO FAR, not final H1 high/low.
Forward directional returns use fixed +15/+30/+60 M1 windows and are
HINDSIGHT RESEARCH TARGETS, never pre-entry cognition, training or gates.
Same-bar MFE/MAE extremes remain upper envelopes, not tick-sequenced fills.
"""

from __future__ import annotations

import argparse
import bisect
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
    iter_cibo_m1,
)
from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    DEV_WINDOW_END,
    DEV_WINDOW_START,
    V49Opportunity,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_mfe_mae_v1 import ExcursionRow
from qore.infrastructure.trader_lab.capitalizer_scalper_v49_v50_g_waterfall_v1 import (
    _jsonl,
    source_id,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_winner_retention_v1 import (
    _key,
    _origin,
    _source_table,
)
from qore.infrastructure.trader_lab.capitalizer_session_clock import (
    capitalizer_session_at,
)
from qore.infrastructure.trader_lab.capitalizer_v49_development_economics import (
    V49EconomicTrade,
    _portfolio_select,
)

IDENTITY = "QORE_SCALPER_A2_H1_BIAS_PHASE_SESSION_RUNWAY_ASOF_V1"
NY = ZoneInfo("America/New_York")
HORIZONS = (15, 30, 60)


def aware(value: str) -> datetime:
    moment = datetime.fromisoformat(value)
    if moment.utcoffset() is None:
        raise ValueError("missing timezone on frozen source timestamp")
    return moment


def session_end_at(moment: datetime, session: str) -> datetime:
    """Fixed NY research-session clock, DST-aware, NOT an observed future price."""

    if moment.utcoffset() is None:
        raise ValueError("session clock needs aware datetime")
    local = moment.astimezone(NY)
    wall = local.timetz().replace(tzinfo=None)
    if session == "ASIA":
        if wall >= time(20):
            end_date = local.date() + timedelta(days=1)
        elif wall < time(2):
            end_date = local.date()
        else:
            raise ValueError("timestamp outside ASIA research session")
        end_time = time(2)
    elif session == "LONDON":
        if not time(2) <= wall < time(8, 30):
            raise ValueError("timestamp outside LONDON research session")
        end_date, end_time = local.date(), time(8, 30)
    elif session == "NEW_YORK":
        if not time(8, 30) <= wall < time(16):
            raise ValueError("timestamp outside NY research session")
        end_date, end_time = local.date(), time(16)
    else:
        raise ValueError("unknown research session")
    end = datetime.combine(end_date, end_time, tzinfo=NY)
    if end <= moment:
        raise ValueError("session runway must be positive")
    return end


def h1_observed_position(
    bars: tuple[CapitalizerM1Bar, ...],
    at: datetime,
    entry: Decimal,
    direction: str,
) -> tuple[Decimal | None, Decimal, int]:
    """Price rank WITHIN range known at the close that triggers entry."""

    h1_open = at.replace(minute=0, second=0, microsecond=0)
    elapsed = Decimal(str((at - h1_open).total_seconds())) / Decimal(3600)
    if not Decimal(0) <= elapsed < 1:
        raise ValueError("bad H1 clock phase")
    observed = tuple(
        bar for bar in bars
        if h1_open <= bar.opened_at and bar.closed_at <= at
    )
    if not observed:
        return None, elapsed, 0
    low = min(x.low for x in observed)
    high = max(x.high for x in observed)
    if entry < low or entry > high:
        raise ValueError("entry lies outside the as-of observed H1 range")
    if high == low:
        return None, elapsed, len(observed)
    if direction == "LONG":
        rank = (entry - low) / (high - low)
    elif direction == "SHORT":
        rank = (high - entry) / (high - low)
    else:
        raise ValueError("unsupported H1 bias direction")
    if not 0 <= rank <= 1:
        raise ValueError("invalid H1 observed range fraction")
    return rank, elapsed, len(observed)


def fixed_horizon_direction(
    bars: tuple[CapitalizerM1Bar, ...],
    opened: tuple[datetime, ...],
    *,
    entry_at: datetime,
    entry: Decimal,
    side: int,
    end_at: datetime,
) -> tuple[tuple[str, str | None], ...]:
    """Return signed forward return in PRICE units (not normalized R).

    Require exact contiguous native-M1 bars and full user-specified horizon
    available within the predetermined session, or return None. This is
    EX-POST directional labeling, NOT observable at order decision.
    """

    start = bisect.bisect_left(opened, entry_at)
    result: list[tuple[str, str | None]] = []
    for minutes in HORIZONS:
        deadline = entry_at + timedelta(minutes=minutes)
        if deadline > end_at:
            result.append((str(minutes), None))
            continue
        chunk = bars[start:start + minutes]
        if len(chunk) != minutes or any(
            bar.opened_at != entry_at + timedelta(minutes=i)
            or bar.closed_at > deadline
            for i, bar in enumerate(chunk)
        ):
            result.append((str(minutes), None))
            continue
        final = chunk[-1].close
        result.append((str(minutes), str((final - entry) * side)))
    return tuple(result)


@dataclass(frozen=True, slots=True)
class JointDiagnosticRow:
    source_opportunity_id: str
    symbol: str
    session: str
    operating_date: str
    entry_at: str
    trigger_family: str
    h1_state_basis: str
    h1_direction: str
    entry_h1_clock_fraction: str
    entry_h1_observed_favorable_range_fraction: str | None
    observed_current_h1_m1_count: int
    h1_context_age_minutes: str
    m15_setup_age_minutes: str
    session_runway_minutes: str
    planned_target_r: str
    stop_risk_price: str
    exit_reason: str
    realized_gross_r: str
    m1_bars_held: int
    mfe_preterminal_r: str
    mae_preterminal_r: str
    mfe_full_exitbar_observation_upper_r: str
    mae_full_exitbar_observation_upper_r: str
    forward_15m_signed_price: str | None
    forward_30m_signed_price: str | None
    forward_60m_signed_price: str | None
    target_hit_in_real_trade: bool
    target_hit_after_exit_hypothetical: bool
    target_first_touch_delay_minutes_hypothetical: int | None
    source_entry_and_exit_unchanged: bool = True
    decision_uses_forward_prices: bool = False
    outcome_data_used_for_admission: bool = False
    forward_returns_are_research_labels_only: bool = True

    def __post_init__(self) -> None:
        if (
            not self.source_entry_and_exit_unchanged
            or self.decision_uses_forward_prices
            or self.outcome_data_used_for_admission
            or not self.forward_returns_are_research_labels_only
        ):
            raise ValueError("post hoc observations cannot change trading decisions")


def diagnostic_one(
    source: V49Opportunity,
    trade: V49EconomicTrade,
    excursion: ExcursionRow,
    bars: tuple[CapitalizerM1Bar, ...],
    opened: tuple[datetime, ...],
) -> JointDiagnosticRow:
    at = aware(trade.entry_at)
    if (
        at != aware(source.m1_trigger_confirmed_at)
        or trade.entry_price != source.decision_reference_price
        or trade.stop_price != source.m15_protected_swing_price
        or trade.target_price != source.structural_target_witness_price
        or trade.direction != (
            "LONG" if source.h1_state_direction == "BULLISH" else "SHORT"
        )
        or trade.entry_at != excursion.entry_at
        or trade.exit_at != excursion.exit_at
        or trade.exit_reason != excursion.exit_reason
        or trade.realized_gross_r != excursion.realized_gross_r
        or trade.m1_bars_held != excursion.bars_reconciled
        or trade.h1_state_basis != excursion.h1_state_basis
        or source.m1_trigger_family != excursion.trigger_family
    ):
        raise ValueError("frozen V49 trade/source/MFE identity mismatch")
    h1_from = aware(source.h1_state_from)
    m15_from = aware(source.m15_setup_confirmed_at)
    if h1_from > m15_from or m15_from > at:
        raise ValueError("H1 M15 M1 confirmations not causally ordered")
    end = session_end_at(at, source.session)
    if capitalizer_session_at(at) is None or (
        capitalizer_session_at(at).value != source.session
    ):
        raise ValueError("trade outside its source session")
    if aware(trade.exit_at) > end:
        raise ValueError("trade exits after known session policy boundary")
    entry = Decimal(trade.entry_price)
    rank, clock, count = h1_observed_position(bars, at, entry, trade.direction)
    risk = abs(entry - Decimal(trade.stop_price))
    index = bisect.bisect_left(opened, at)
    target = Decimal(trade.target_price)
    side = 1 if trade.direction == "LONG" else -1
    first_touch: int | None = None
    hypothetical_after_exit = False
    for minute, bar in enumerate(bars[index:], start=1):
        if bar.opened_at >= end or bar.closed_at > end:
            break
        # Require contiguous M1; gaps are not a license to assume price paths.
        if bar.opened_at != at + timedelta(minutes=minute - 1):
            break
        touched = bar.high >= target if side == 1 else bar.low <= target
        if touched:
            first_touch = minute
            hypothetical_after_exit = (
                bar.opened_at >= aware(trade.exit_at)
            )
            break
    if trade.exit_reason == "TARGET" and (
        first_touch is None or first_touch > trade.m1_bars_held
    ):
        raise ValueError("V49 TARGET lacks its causal M1 OHLC touch")
    horizons = dict(fixed_horizon_direction(
        bars, opened, entry_at=at, entry=entry, side=side, end_at=end
    ))
    return JointDiagnosticRow(
        source_opportunity_id=source_id(source),
        symbol=source.symbol,
        session=source.session,
        operating_date=source.operating_date,
        entry_at=trade.entry_at,
        trigger_family=trade.trigger_family,
        h1_state_basis=trade.h1_state_basis,
        h1_direction=source.h1_state_direction,
        entry_h1_clock_fraction=str(clock),
        entry_h1_observed_favorable_range_fraction=(
            str(rank) if rank is not None else None
        ),
        observed_current_h1_m1_count=count,
        h1_context_age_minutes=str((at - h1_from).total_seconds() / 60),
        m15_setup_age_minutes=str((at - m15_from).total_seconds() / 60),
        session_runway_minutes=str((end - at).total_seconds() / 60),
        planned_target_r=trade.planned_reward_r,
        stop_risk_price=str(risk),
        exit_reason=trade.exit_reason,
        realized_gross_r=trade.realized_gross_r,
        m1_bars_held=trade.m1_bars_held,
        mfe_preterminal_r=excursion.mfe_preterminal_r,
        mae_preterminal_r=excursion.mae_preterminal_r,
        mfe_full_exitbar_observation_upper_r=excursion.mfe_full_exitbar_upper_r,
        mae_full_exitbar_observation_upper_r=excursion.mae_full_exitbar_upper_r,
        forward_15m_signed_price=horizons["15"],
        forward_30m_signed_price=horizons["30"],
        forward_60m_signed_price=horizons["60"],
        target_hit_in_real_trade=trade.exit_reason == "TARGET",
        target_hit_after_exit_hypothetical=hypothetical_after_exit,
        target_first_touch_delay_minutes_hypothetical=first_touch,
    )


def build_market(
    original: Path, excursions: Path, raw_m1: Path
) -> tuple[dict[str, Any], tuple[JointDiagnosticRow, ...]]:
    source_paths = sorted(original.rglob("capitalizer-*-v49-hf-capacity-opportunities.jsonl"))
    trade_paths = sorted(original.rglob("capitalizer-*-v49-development-economics-trades.jsonl"))
    excursion_paths = sorted(excursions.rglob("scalper-a2-mfe-mae-trades.jsonl"))
    if len(source_paths) != 1 or len(trade_paths) != 1 or len(excursion_paths) != 1:
        raise ValueError("one market requires original V49 source/economics/excursions")
    sources = tuple(V49Opportunity(**r) for r in _jsonl(source_paths[0]))
    trades = tuple(V49EconomicTrade(**r) for r in _jsonl(trade_paths[0]))
    observed = tuple(ExcursionRow(**r) for r in _jsonl(excursion_paths[0]))
    if not sources or len(sources) != len(trades) or len(trades) != len(observed):
        raise ValueError("incomplete original market source-trade-excursion join")
    symbol = sources[0].symbol
    source_table = _source_table(sources)
    sources_by_id = {source_id(s): s for s in sources}
    trades_by_id = {_origin(t, source_table): t for t in trades}
    key = lambda x: _key(
        x.symbol, x.session, x.operating_date,
        x.entry_at, x.entry_price, x.trigger_family, x.h1_state_basis,
    )
    excursions_by_key = {key(row): row for row in observed}
    if (
        len(sources_by_id) != len(sources) or len(trades_by_id) != len(sources)
        or len(excursions_by_key) != len(observed)
    ):
        raise ValueError("duplicate evidence/source identity")
    bars = tuple(
        b for b in iter_cibo_m1(raw_m1)
        if DEV_WINDOW_START <= b.opened_at < DEV_WINDOW_END
    )
    if not bars or any(b.symbol != symbol for b in bars):
        raise ValueError("provider native M1 market provenance mismatch")
    opened = tuple(b.opened_at for b in bars)
    out: list[JointDiagnosticRow] = []
    for identifier, source in sources_by_id.items():
        trade = trades_by_id[identifier]
        row = excursions_by_key.get(key(trade))
        if row is None:
            raise ValueError("source-matched trade lacks exact native M1 MFE ledger")
        out.append(diagnostic_one(source, trade, row, bars, opened))
    return {
        "identity": IDENTITY,
        "symbol": symbol,
        "source_opportunities": len(sources),
        "joined_trade_and_mfe_rows": len(out),
        "session_clock": "NY_DST_AWARE_AT_ORIGIN",
        "h1_range_position": "ASOF_PARTIAL_H1_RANGE_NOT_FINAL_H1",
        "fixed_forward_returns": "POST_HOC_ONLY_UNEXECUTABLE",
        "no_input_changed": True,
        "trader_certified": False,
        "live_authorized": False,
    }, tuple(out)


def _group_summary(rows: tuple[JointDiagnosticRow, ...]) -> dict[str, Any]:
    if not rows:
        return {"count": 0}
    r_values = tuple(Decimal(r.realized_gross_r) for r in rows)
    def avg(field: str) -> str:
        values = tuple(Decimal(getattr(r, field)) for r in rows)
        return str(sum(values, Decimal(0)) / len(values))
    signed: dict[str, Any] = {}
    for min_ in HORIZONS:
        label = str(min_)
        values = tuple(
            Decimal(value) for row in rows
            if (value := getattr(row, f"forward_{label}m_signed_price")) is not None
        )
        signed[label] = {
            "covered_trades": len(values),
            "directional_positive_count": sum(x > 0 for x in values),
            "directional_negative_count": sum(x < 0 for x in values),
            "directional_flat_count": sum(x == 0 for x in values),
            "positive_fraction_over_covered": (
                str(Decimal(sum(x > 0 for x in values)) / len(values))
                if values else None
            ),
        }
    return {
        "count": len(rows),
        "gross_r": str(sum(r_values, Decimal(0))),
        "wins": sum(r > 0 for r in r_values),
        "losses": sum(r < 0 for r in r_values),
        "session_exits": sum(x.exit_reason == "SESSION_EXIT" for x in rows),
        "stop_exits": sum(x.exit_reason == "STOP" for x in rows),
        "target_exits": sum(x.exit_reason == "TARGET" for x in rows),
        "mean_mfe_preterminal_r": avg("mfe_preterminal_r"),
        "mean_mae_preterminal_r": avg("mae_preterminal_r"),
        "median_session_runway_minutes": str(median(
            Decimal(r.session_runway_minutes) for r in rows
        )),
        "median_h1_context_age_minutes": str(median(
            Decimal(r.h1_context_age_minutes) for r in rows
        )),
        "median_m15_setup_age_minutes": str(median(
            Decimal(r.m15_setup_age_minutes) for r in rows
        )),
        "target_hit_within_actual_trade": sum(x.target_hit_in_real_trade for x in rows),
        "target_first_touched_after_exit_hypothetical": sum(
            x.target_hit_after_exit_hypothetical for x in rows
        ),
        "forward_directional": signed,
    }


def _third(value: Decimal) -> str:
    if value < Decimal(1) / 3:
        return "FIRST"
    if value < Decimal(2) / 3:
        return "MIDDLE"
    return "LAST"


def aggregate(root: Path) -> dict[str, Any]:
    markets = [
        json.loads(p.read_text(encoding="utf-8"))
        for p in sorted(root.rglob("scalper-h1-timing-market.json"))
    ]
    if len(markets) != 9 or len({m["symbol"] for m in markets}) != 9:
        raise ValueError("exactly 9 distinct frozen markets required")
    all_rows = tuple(
        JointDiagnosticRow(**r)
        for p in sorted(root.rglob("scalper-h1-timing-rows.jsonl"))
        for r in _jsonl(p)
    )
    if len(all_rows) != 2876 or len({r.source_opportunity_id for r in all_rows}) != 2876:
        raise ValueError("joint audit source opportunity identity mismatch")
    if sum(m["source_opportunities"] for m in markets) != len(all_rows):
        raise ValueError("different market denominator from frozen V49")
    # MAX3 is the untouched original earliest 3 per session/day.
    ordered: dict[tuple[str, str], list[JointDiagnosticRow]] = defaultdict(list)
    for r in all_rows:
        ordered[(r.session, r.operating_date)].append(r)
    chosen = tuple(
        r for key in sorted(ordered)
        for r in sorted(
            ordered[key], key=lambda x: (x.entry_at, x.symbol)
        )[:3]
    )
    if len(chosen) != 2020 or sum(Decimal(x.realized_gross_r) > 0 for x in chosen) != 1167:
        raise ValueError("same baseline MAX3 count and winners must reconcile")
    original_r = sum((Decimal(x.realized_gross_r) for x in chosen), Decimal(0))
    if abs(original_r - Decimal("-233.2693270763665099166092077")) > Decimal("1e-15"):
        raise ValueError("original V49 economic R not exactly reconciled")
    groups: dict[str, dict[str, list[JointDiagnosticRow]]] = {
        key: defaultdict(list)
        for key in (
            "session", "market", "trigger_family", "h1_basis", "exit_reason",
            "h1_clock_third", "h1_partial_range_third",
            "runway_bucket", "h1_age_bucket",
        )
    }
    for r in chosen:
        groups["session"][r.session].append(r)
        groups["market"][r.symbol].append(r)
        groups["trigger_family"][r.trigger_family].append(r)
        groups["h1_basis"][r.h1_state_basis].append(r)
        groups["exit_reason"][r.exit_reason].append(r)
        groups["h1_clock_third"][_third(Decimal(r.entry_h1_clock_fraction))].append(r)
        price_third = (
            _third(Decimal(r.entry_h1_observed_favorable_range_fraction))
            if r.entry_h1_observed_favorable_range_fraction is not None
            else "UNDEFINED_RANGE"
        )
        groups["h1_partial_range_third"][price_third].append(r)
        remaining = Decimal(r.session_runway_minutes)
        runway = (
            "UNDER_30_MIN" if remaining < 30
            else "30_TO_60_MIN" if remaining < 60
            else "60_TO_120_MIN" if remaining < 120
            else "AT_LEAST_120_MIN"
        )
        groups["runway_bucket"][runway].append(r)
        age = Decimal(r.h1_context_age_minutes)
        groups["h1_age_bucket"][
            "UNDER_60_MIN" if age < 60 else
            "60_TO_180_MIN" if age < 180 else "AT_LEAST_180_MIN"
        ].append(r)
    return {
        "identity": IDENTITY,
        "market_count": len(markets),
        "original_source_opportunities": len(all_rows),
        "max3_selected_source_opportunities": len(chosen),
        "max3_unselected_counterfactual": len(all_rows) - len(chosen),
        "selected": _group_summary(chosen),
        "unselected_simulated": _group_summary(tuple(
            r for r in all_rows if r.source_opportunity_id not in {
                x.source_opportunity_id for x in chosen
            }
        )),
        "selected_by": {
            kind: {name: _group_summary(tuple(rows))
                   for name, rows in sorted(data.items())}
            for kind, data in groups.items()
        },
        "clock_phase_asof": True,
        "partial_h1_range_not_future_h1": True,
        "future_15_30_60_prices_posthoc_only": True,
        "same_bar_extremes_not_tick_sequenced": True,
        "no_trade_outcome_used_for_admission": True,
        "no_policy_mutated": True,
        "trader_certified": False,
        "live_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="mode", required=True)
    m = sub.add_parser("market")
    m.add_argument("v49", type=Path)
    m.add_argument("native_m1", type=Path)
    m.add_argument("excursion_m1", type=Path)
    m.add_argument("out", type=Path)
    a = sub.add_parser("matrix")
    a.add_argument("market_reports", type=Path)
    a.add_argument("out", type=Path)
    args = parser.parse_args()
    if args.mode == "market":
        report, rows = build_market(args.v49, args.excursion_m1, args.native_m1)
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / "scalper-h1-timing-market.json").write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        with (args.out / "scalper-h1-timing-rows.jsonl").open(
            "w", encoding="utf-8"
        ) as f:
            for row in rows:
                f.write(json.dumps(asdict(row), sort_keys=True) + "\n")
        print(json.dumps(report, sort_keys=True))
    else:
        report = aggregate(args.market_reports)
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / "scalper-h1-timing-nine-market.json").write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(json.dumps({
            "identity": IDENTITY,
            "selected": report["selected"],
            "by_h1_clock": report["selected_by"]["h1_clock_third"],
            "by_h1_range": report["selected_by"]["h1_partial_range_third"],
            "by_session_runway": report["selected_by"]["runway_bucket"],
            "by_h1_age": report["selected_by"]["h1_age_bucket"],
            "trader_certified": False,
        }, sort_keys=True))


if __name__ == "__main__":
    main()
