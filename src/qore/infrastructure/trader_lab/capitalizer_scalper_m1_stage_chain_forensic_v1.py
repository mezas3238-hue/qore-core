"""Read-only original V49 M15→M1 source-stage timing forensic.

Rebuild the exact first winning ROUTE observer at the confirmed M1 entry,
using only provider-native M1 bars closed by that instant. Compare historical
directional post-stage returns at M15, sweep/FVG, CISD and entry. Stage
observations are NOT executable entries, and must NEVER decide trading gates.

Important: SWEEP+CISD observer exposes a sweep extreme/causal series but does
NOT independently confirm an M1 protected swing. It is labeled UNOBSERVABLE,
not silently promoted into a protected swing. FVG structural-CISD observer
does expose a pivot bar and protects it only at CISD confirmation.
"""

from __future__ import annotations

import argparse
import bisect
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
    iter_cibo_m1,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    DEV_WINDOW_END,
    DEV_WINDOW_START,
    V49Opportunity,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_h1_direction_random_baseline_v1 import (
    _future_label,
    _runs,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_h1_timing_session_diagnostic_v1 import (
    HORIZONS,
    aware,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_v49_v50_g_waterfall_v1 import (
    _jsonl,
    source_id,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_winner_retention_v1 import (
    _origin,
    _source_table,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceDirection,
)
from qore.infrastructure.trader_lab.capitalizer_ttrades_m1_cisd_observer_v48 import (
    observe_first_m1_cisd,
)
from qore.infrastructure.trader_lab.capitalizer_ttrades_m1_fvg_cisd_continuation_v48 import (
    _timed,
    observe_first_m1_fvg_cisd_continuation,
)
from qore.infrastructure.trader_lab.capitalizer_ttrades_structural_cisd_v48 import (
    observe_first_structural_cisd,
)
from qore.infrastructure.trader_lab.capitalizer_v49_development_economics import (
    V49EconomicTrade,
)

IDENTITY = "QORE_SCALPER_A2_SEVENTH_ORIGINAL_M1_STAGE_CHAIN_FORENSIC_V1"
STAGES = (
    "M15_SETUP_CONFIRMED",
    "M1_SWEEP_CONFIRMED_BAR",
    "M1_CAUSAL_OPPOSING_SERIES_END",
    "M1_FVG_FORMATION_CONFIRMED",
    "M1_FVG_RETRACE_CONFIRMED_BAR",
    "M1_FVG_PIVOT_BAR_CLOSE_UNPROTECTED",
    "M1_CISD_CONFIRMED",
    "M1_PROTECTED_SWING_BECOMES_VALID",
    "ORIGINAL_ENTRY_EXECUTED",
)


@dataclass(frozen=True, slots=True)
class StageObservation:
    kind: str
    confirmed_at: str | None
    price_close_asof: str | None
    forward_signed_price_15: str | None
    forward_signed_price_30: str | None
    forward_signed_price_60: str | None
    hypothetically_tradeable: bool = False
    label_uses_future_return: bool = True

    def __post_init__(self) -> None:
        if self.kind not in STAGES:
            raise ValueError("unregistered stage label")
        if self.hypothetically_tradeable or not self.label_uses_future_return:
            raise ValueError("diagnostic stage must not claim live trade authority")


@dataclass(frozen=True, slots=True)
class M1StageChainRow:
    source_opportunity_id: str
    symbol: str
    session: str
    operating_date: str
    family: str
    direction: str
    m15_confirmed_at: str
    original_entry_at: str
    original_realized_gross_r: str
    original_exit_reason: str
    stages: tuple[StageObservation, ...]
    fvg_or_sweep_to_cisd_minutes: str
    m15_to_cisd_minutes: str
    cisd_to_entry_minutes: str
    m1_protected_swing_before_cisd: bool = False
    original_trade_changed: bool = False
    decision_uses_outcome: bool = False
    outcome_label_used_for_admission: bool = False

    def __post_init__(self) -> None:
        if self.original_trade_changed or self.decision_uses_outcome:
            raise ValueError("original trade or decision may not change")
        if self.outcome_label_used_for_admission:
            raise ValueError("post-trade label may not choose entry")
        if self.m1_protected_swing_before_cisd:
            raise ValueError("protected swing must be confirmed by CISD")
        if Decimal(self.cisd_to_entry_minutes) != 0:
            raise ValueError("V49 source has no delay between CISD close and entry")


def _as_stage(
    name: str,
    at: datetime | None,
    bars: tuple[CapitalizerM1Bar, ...],
    opened: tuple[datetime, ...],
    consecutive: tuple[int, ...],
    side: int,
    session: str,
) -> StageObservation:
    if at is None:
        return StageObservation(name, None, None, None, None, None)
    position = bisect.bisect_left(opened, at)
    if position == 0 or bars[position - 1].closed_at != at:
        # Real original M1 gaps may mean a stage cannot be priced; report
        # coverage loss transparently rather than manufacturing fill prices.
        return StageObservation(name, at.isoformat(), None, None, None, None)
    entry = bars[position - 1].close
    labels = _future_label(bars, opened, consecutive, at, entry, side, session)
    return StageObservation(
        kind=name, confirmed_at=at.isoformat(), price_close_asof=str(entry),
        forward_signed_price_15=str(labels[0]) if labels[0] is not None else None,
        forward_signed_price_30=str(labels[1]) if labels[1] is not None else None,
        forward_signed_price_60=str(labels[2]) if labels[2] is not None else None,
    )


def reconstruct_source_chain(
    source: V49Opportunity,
    trade: V49EconomicTrade,
    bars: tuple[CapitalizerM1Bar, ...],
    opened: tuple[datetime, ...],
    consecutive: tuple[int, ...],
) -> M1StageChainRow:
    at = aware(source.m1_trigger_confirmed_at)
    thesis_at = aware(source.m15_setup_confirmed_at)
    if thesis_at >= at or aware(trade.entry_at) != at:
        raise ValueError("M15→M1 chronology or original source entry mismatch")
    side = 1 if source.h1_state_direction == "BULLISH" else -1
    if (
        trade.direction != ("LONG" if side == 1 else "SHORT")
        or trade.entry_price != source.decision_reference_price
        or trade.stop_price != source.m15_protected_swing_price
        or trade.target_price != source.structural_target_witness_price
        or trade.trigger_family != source.m1_trigger_family
    ):
        raise ValueError("source V49 trade contract mismatch")
    first = bisect.bisect_left(opened, thesis_at)
    last = bisect.bisect_left(opened, at)
    window = bars[first:last]
    if len(window) < 4 or window[-1].closed_at != at:
        raise ValueError("original source trigger is not at native-M1 close")
    direction = (
        CapitalizerSourceDirection.BULLISH
        if side == 1 else CapitalizerSourceDirection.BEARISH
    )
    stage_at: dict[str, datetime | None] = dict.fromkeys(STAGES)
    stage_at["M15_SETUP_CONFIRMED"] = thesis_at
    stage_at["M1_CISD_CONFIRMED"] = at
    stage_at["ORIGINAL_ENTRY_EXECUTED"] = at
    if source.m1_trigger_family == "LIQUIDITY_SWEEP_CISD":
        o = observe_first_m1_cisd(
            window, thesis_at=thesis_at, deadline_at=at,
            side=CapitalizerSide.LONG if side == 1 else CapitalizerSide.SHORT,
        )
        if (
            not o.confirmed or o.confirmed_at != at
            or o.confirmation_close != Decimal(trade.entry_price)
            or o.sweep_at is None
            or o.causal_series_ended_at is None
        ):
            raise ValueError("original V49 Sweep+CISD reconstruction failed")
        stage_at["M1_SWEEP_CONFIRMED_BAR"] = o.sweep_at
        stage_at["M1_CAUSAL_OPPOSING_SERIES_END"] = o.causal_series_ended_at
        anchor = o.sweep_at
        # No M1 protected-swing confirmation emitted for this branch.
        # The M15 protected swing belongs to a distinct upstream detector.
    elif source.m1_trigger_family == "FVG_RETRACE_CISD":
        o2 = observe_first_m1_fvg_cisd_continuation(
            window, thesis_at=thesis_at, deadline_at=at, direction=direction,
        )
        if (
            not o2.confirmed or o2.cisd_confirmed_at != at
            or o2.fvg_confirmed_at is None
            or o2.fvg_interaction_at is None
        ):
            raise ValueError("original V49 FVG+CISD reconstruction failed")
        stage_at["M1_FVG_FORMATION_CONFIRMED"] = o2.fvg_confirmed_at
        stage_at["M1_FVG_RETRACE_CONFIRMED_BAR"] = o2.fvg_interaction_at
        stage_at["M1_PROTECTED_SWING_BECOMES_VALID"] = at
        idx = next(
            (i for i, bar in enumerate(window)
             if bar.closed_at == o2.fvg_interaction_at), None
        )
        if idx is None:
            raise ValueError("original FVG interaction M1 missing")
        structural = observe_first_structural_cisd(
            tuple(_timed(x) for x in window[max(0, idx - 3):]),
            direction=direction, after=window[idx].opened_at,
            before=at, higher_timeframe_closure_confirmed=True,
        )
        if (
            not structural.source_valid or structural.confirmed_at != at
            or structural.swing_occurred_at is None
        ):
            raise ValueError("original FVG route protected-swing witness missing")
        pivot_bar = next(
            (bar for bar in window
             if bar.opened_at == structural.swing_occurred_at), None
        )
        if pivot_bar is None:
            raise ValueError("original M1 pivot bar is missing")
        stage_at["M1_FVG_PIVOT_BAR_CLOSE_UNPROTECTED"] = pivot_bar.closed_at
        anchor = o2.fvg_confirmed_at
    else:
        raise ValueError("unknown source family, no HARKing fallback")
    # Do not invent a protected swing before CISD; swing pivot appearance is
    # NOT confirmation/protection. Stage times are causal observed bar closes.
    if not thesis_at <= anchor <= at:
        raise ValueError("inconsistent original stage chronology")
    observations = tuple(
        _as_stage(name, stage_at[name], bars, opened, consecutive, side, source.session)
        for name in STAGES
    )
    executed = observations[-1]
    if executed.price_close_asof != trade.entry_price:
        raise ValueError("original executed V49 close was not independently witnessed")
    return M1StageChainRow(
        source_opportunity_id=source_id(source),
        symbol=source.symbol, session=source.session,
        operating_date=source.operating_date,
        family=source.m1_trigger_family, direction=trade.direction,
        m15_confirmed_at=source.m15_setup_confirmed_at,
        original_entry_at=trade.entry_at,
        original_realized_gross_r=trade.realized_gross_r,
        original_exit_reason=trade.exit_reason,
        stages=observations,
        fvg_or_sweep_to_cisd_minutes=str((at-anchor).total_seconds() / 60),
        m15_to_cisd_minutes=str((at-thesis_at).total_seconds() / 60),
        cisd_to_entry_minutes="0",
    )


def build_market(
    source_dir: Path,
    native_m1: Path,
) -> tuple[dict[str, Any], tuple[M1StageChainRow, ...]]:
    paths = sorted(source_dir.rglob("capitalizer-*-v49-hf-capacity-opportunities.jsonl"))
    trade_paths = sorted(source_dir.rglob(
        "capitalizer-*-v49-development-economics-trades.jsonl"
    ))
    if len(paths) != 1 or len(trade_paths) != 1:
        raise ValueError("exactly one market V49 frozen source and trades")
    sources = tuple(V49Opportunity(**raw) for raw in _jsonl(paths[0]))
    trades = tuple(V49EconomicTrade(**raw) for raw in _jsonl(trade_paths[0]))
    if not sources or len(sources) != len(trades):
        raise ValueError("original native market trades/sources not identical in count")
    symbol = sources[0].symbol
    if any(s.symbol != symbol or s.session != sources[0].session for s in sources):
        raise ValueError("mixed market source")
    source_table = _source_table(sources)
    by_source = {_origin(trade, source_table): trade for trade in trades}
    if len(by_source) != len(sources):
        raise ValueError("duplicated original trade identity")
    bars = tuple(b for b in iter_cibo_m1(native_m1)
                 if DEV_WINDOW_START <= b.opened_at < DEV_WINDOW_END)
    if not bars or any(b.symbol != symbol for b in bars):
        raise ValueError("wrong original provider native M1 source market")
    opened = tuple(b.opened_at for b in bars)
    consecutive = _runs(bars)
    rows = tuple(reconstruct_source_chain(
        source, by_source[source_id(source)], bars, opened, consecutive
    ) for source in sources)
    if len({r.source_opportunity_id for r in rows}) != len(sources):
        raise ValueError("source stage identity repeated")
    return {
        "identity": IDENTITY, "symbol": symbol,
        "sources": len(sources), "forensic_rows": len(rows),
        "post_cisd_execution_delay": False,
        "sweep_has_explicit_m1_protected_swing": False,
        "original_trade_changed": False,
        "outcome_used_for_stage_selection": False,
        "trader_certified": False, "live_authorized": False,
    }, rows


def _summarize(rows: tuple[M1StageChainRow, ...]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "n": len(rows),
        "m15_to_cisd_median_min": str(median(
            Decimal(r.m15_to_cisd_minutes) for r in rows
        )) if rows else None,
        "sweep_or_fvg_to_cisd_median_min": str(median(
            Decimal(r.fvg_or_sweep_to_cisd_minutes) for r in rows
        )) if rows else None,
        "post_cisd_delay_count": sum(
            Decimal(r.cisd_to_entry_minutes) != 0 for r in rows
        ),
    }
    for stage in STAGES:
        obs = [next(s for s in row.stages if s.kind == stage) for row in rows]
        horizons: dict[str, Any] = {}
        for h in HORIZONS:
            field = f"forward_signed_price_{h}"
            valid = [Decimal(getattr(s, field)) for s in obs
                     if getattr(s, field) is not None]
            horizons[str(h)] = {
                "covered": len(valid),
                "positive": sum(v > 0 for v in valid),
                "positive_fraction": (
                    str(Decimal(sum(v > 0 for v in valid)) / len(valid))
                    if valid else None
                ),
            }
        result[stage] = {"observed_stage_n": sum(s.confirmed_at is not None
                                                for s in obs), "horizons": horizons}
    # Actual paired source IDs where both observations have complete M1 followup.
    if rows:
        step = (
            "M1_SWEEP_CONFIRMED_BAR"
            if rows[0].family == "LIQUIDITY_SWEEP_CISD"
            else "M1_FVG_FORMATION_CONFIRMED"
        )
        if len({r.family for r in rows}) == 1:
            for h in HORIZONS:
                pairs: list[tuple[Decimal, Decimal]] = []
                for row in rows:
                    stages = {s.kind: s for s in row.stages}
                    first = getattr(stages[step], f"forward_signed_price_{h}")
                    last = getattr(stages["M1_CISD_CONFIRMED"],
                                   f"forward_signed_price_{h}")
                    if first is not None and last is not None:
                        pairs.append((Decimal(first), Decimal(last)))
                result[f"paired_{step}_to_CISD_{h}m"] = {
                    "paired_n": len(pairs),
                    "early_positive": sum(a > 0 for a, b in pairs),
                    "late_positive": sum(b > 0 for a, b in pairs),
                    "late_minus_early_pp": (
                        str(Decimal(100) * sum(
                            (Decimal(b > 0) - Decimal(a > 0)
                             for a, b in pairs), Decimal(0)) / len(pairs))
                        if pairs else None
                    ),
                }
    return result


def aggregate(root: Path) -> dict[str, Any]:
    markets = [json.loads(p.read_text(encoding="utf-8"))
               for p in sorted(root.rglob("scalper-m1-stage-market.json"))]
    if len(markets) != 9 or len({r["symbol"] for r in markets}) != 9:
        raise ValueError("nine source markets mandatory")
    all_rows = tuple(
        M1StageChainRow(
            **{**raw, "stages": tuple(StageObservation(**s)
                                     for s in raw["stages"])}
        )
        for p in sorted(root.rglob("scalper-m1-stage-rows.jsonl"))
        for raw in _jsonl(p)
    )
    if len(all_rows) != 2876 or len({r.source_opportunity_id for r in all_rows}) != 2876:
        raise ValueError("stage source identity census mismatch")
    by_day: dict[tuple[str, str], list[M1StageChainRow]] = defaultdict(list)
    for row in all_rows:
        by_day[(row.session, row.operating_date)].append(row)
    selected = tuple(
        row for key in sorted(by_day)
        for row in sorted(
            by_day[key],
            key=lambda x: (aware(x.original_entry_at), x.symbol, x.family),
        )[:3]
    )
    if len(selected) != 2020 or sum(
        Decimal(r.original_realized_gross_r) > 0 for r in selected
    ) != 1167:
        raise ValueError("unchanged MAX3 and original winner count required")
    original_r = sum((Decimal(r.original_realized_gross_r)
                      for r in selected), Decimal(0))
    if abs(original_r - Decimal("-233.2693270763665099166092077")) > Decimal("1e-15"):
        raise ValueError("source net R changed")
    family_rows: dict[str, list[M1StageChainRow]] = defaultdict(list)
    market_rows: dict[str, list[M1StageChainRow]] = defaultdict(list)
    session_rows: dict[str, list[M1StageChainRow]] = defaultdict(list)
    for r in selected:
        family_rows[r.family].append(r)
        market_rows[r.symbol].append(r)
        session_rows[r.session].append(r)
    return {
        "identity": IDENTITY,
        "sources": 2876, "market_count": 9, "max3_selected": 2020,
        "original_positive_winners": 1167, "original_gross_R": str(original_r),
        "all": _summarize(selected),
        "family": {k:_summarize(tuple(v)) for k,v in family_rows.items()},
        "market": {k:_summarize(tuple(v)) for k,v in market_rows.items()},
        "session": {k:_summarize(tuple(v)) for k,v in session_rows.items()},
        "no_source_outcome_used_to_choose_stage": True,
        "stage_outcomes_are_posthoc_labels": True,
        "sweep_pivot_not_claimed_to_be_protected": True,
        "no_original_v49_rule_changed": True,
        "trader_certified": False, "live_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="mode", required=True)
    m = sub.add_parser("market")
    m.add_argument("original", type=Path)
    m.add_argument("m1", type=Path)
    m.add_argument("out", type=Path)
    a = sub.add_parser("matrix")
    a.add_argument("market_reports", type=Path)
    a.add_argument("out", type=Path)
    args = parser.parse_args()
    if args.mode == "market":
        report, rows = build_market(args.original, args.m1)
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out/"scalper-m1-stage-market.json").write_text(
            json.dumps(report, indent=2, sort_keys=True)+"\n", encoding="utf-8"
        )
        with (args.out/"scalper-m1-stage-rows.jsonl").open("w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(asdict(row), sort_keys=True)+"\n")
        print(json.dumps(report,sort_keys=True))
    else:
        report = aggregate(args.market_reports)
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out/"scalper-m1-stage-nine-market.json").write_text(
            json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8"
        )
        print(json.dumps({
            "identity": IDENTITY,"all":report["all"],"family":report["family"],
            "market":report["market"],"trader_certified":False
        },sort_keys=True))


if __name__ == "__main__":
    main()
