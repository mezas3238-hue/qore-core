"""VT08 Index 2Y density expansion lab — Round 4.

Purpose: determine whether VT08 can satisfy the owner's hard density contract of
at least 600 executed research opportunities over two years across NAS100,
SP500 and US30 without abandoning the VT08/TTrades structural identity.

V7 remains immutable and is retained as the benchmark. Round 4 introduces
research-only opportunity generators around the same core methodology:

- DAILY BIAS remains V7 source-corrected.
- POIs remain the V6/V7 TTrades families: FVG, relevant swing, CISD.
- Confirmation remains M15 CISD -> Protected Swing -> continuation.
- Initial stop remains Protected Swing.
- No future information is used to create a signal.
- Same-bar stop-first execution is retained through V6 modeling.

Variants:
1. V7_BASE: exact executable-anchor / priority-POI baseline.
2. PLUS_14: adds 14:00 NY as research execution anchor from the source H4 cycle.
3. MULTI_POI: exposes every valid pre-existing POI family instead of stopping at
   the first priority family.
4. MULTI_POI_REARM: after a distinct continuation, a new POI touch + new CISD +
   new continuation may create a new research opportunity in the same H4.

Round 4 does not certify these expansions. It diagnoses density, overlap,
profit factor and drawdown under fixed target-depth surfaces.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import Any, cast
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab import vt08_index_cibo_2y_tuning_round1 as r1
from qore.infrastructure.trader_lab import vt08_index_cibo_2y_tuning_round2 as r2
from qore.infrastructure.trader_lab import vt08_index_v6_ttrades_source_faithful as v6
from qore.infrastructure.trader_lab import vt08_index_v7_ttrades_source_corrected as v7
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import Vt08IndexC2R1Bar

SCHEMA = "qore.trader_lab.vt08_index_cibo_2y_density_round4.v1"
IDENTITY = "VT08_INDEX_CIBO_2Y_DENSITY_ROUND4"
DENSITY_HARD_GATE = 600
PRIMARY_STRESS = Decimal("0.05")
SECONDARY_STRESS = Decimal("0.10")
TARGET_GRID = tuple(Decimal(value) for value in ("1.25", "1.5", "1.75", "2.0", "2.5"))
V7_ANCHORS = tuple(v7.EXECUTABLE_H4_ANCHORS_NY)
PLUS_14_ANCHORS = (14,) + V7_ANCHORS
_NY = ZoneInfo("America/New_York")


class ExpansionVariant(StrEnum):
    V7_BASE = "v7-base"
    PLUS_14 = "plus-14"
    MULTI_POI = "multi-poi"
    MULTI_POI_PLUS_14 = "multi-poi-plus-14"
    MULTI_POI_REARM = "multi-poi-rearm"
    MULTI_POI_REARM_PLUS_14 = "multi-poi-rearm-plus-14"


@dataclass(frozen=True, slots=True)
class ExpandedOpportunity:
    signal: v6.CandidateSignal
    source_poi_kind: str
    poi_touch_at: datetime
    rearm_index: int

    def identity(self) -> tuple[object, ...]:
        signal = self.signal
        return (
            signal.symbol,
            signal.signal_at.astimezone(UTC),
            signal.side.value,
            signal.entry,
            signal.stop,
        )


@dataclass(frozen=True, slots=True)
class VariantSurface:
    variant: ExpansionVariant
    opportunities: tuple[ExpandedOpportunity, ...]
    source_counts: dict[str, int]


def _source_pois_for_h4(
    indexed: dict[datetime, Vt08IndexC2R1Bar],
    h4: dict[datetime, Vt08IndexC2R1Bar],
    *,
    h4_opened_at: datetime,
    side: DemoTradingSetupSide,
) -> tuple[v6.SourcePoi, ...]:
    prior_keys = v6._prior_h4_keys(h4, before=h4_opened_at, count=3)
    if len(prior_keys) < 3:
        return ()
    a, b, c = (h4[key] for key in prior_keys)
    result: list[v6.SourcePoi] = []

    if side is DemoTradingSetupSide.LONG and a.high < c.low:
        result.append(v6.SourcePoi(v6.PoiKind.FVG, a.high, c.low, c.closed_at))
    if side is DemoTradingSetupSide.SHORT and a.low > c.high:
        result.append(v6.SourcePoi(v6.PoiKind.FVG, c.high, a.low, c.closed_at))

    if side is DemoTradingSetupSide.LONG and b.low < a.low and b.low < c.low:
        result.append(
            v6.SourcePoi(v6.PoiKind.RELEVANT_SWING, b.low, b.low, c.closed_at)
        )
    if side is DemoTradingSetupSide.SHORT and b.high > a.high and b.high > c.high:
        result.append(
            v6.SourcePoi(v6.PoiKind.RELEVANT_SWING, b.high, b.high, c.closed_at)
        )

    last_key = prior_keys[-1]
    last_bars = v6._bars_between(indexed, start=last_key, end=h4[last_key].closed_at)
    cisd_poi = v6._last_cisd_poi(last_bars, side=side)
    if cisd_poi is not None:
        result.append(cisd_poi)

    unique: dict[tuple[object, ...], v6.SourcePoi] = {}
    for poi in result:
        key = (
            poi.kind.value,
            poi.low,
            poi.high,
            poi.observed_at.astimezone(UTC),
        )
        unique[key] = poi
    return tuple(unique.values())


def _touch_indices(
    bars: Sequence[Vt08IndexC2R1Bar],
    poi: v6.SourcePoi,
    *,
    start_index: int,
) -> tuple[int, ...]:
    return tuple(
        index
        for index in range(start_index, len(bars))
        if poi.observed_at.astimezone(UTC)
        <= bars[index].opened_at.astimezone(UTC)
        and poi.touched_by(bars[index])
    )


def _candidate_from_sequence(
    *,
    symbol: str,
    h4_bar: Vt08IndexC2R1Bar,
    h4_opened_at: datetime,
    bars: Sequence[Vt08IndexC2R1Bar],
    poi: v6.SourcePoi,
    side: DemoTradingSetupSide,
    model_kind: v6.H4ModelKind,
    touch_index: int,
) -> tuple[v6.CandidateSignal, int] | None:
    cisd = v6._first_cisd(bars, side=side, start_index=touch_index)
    if cisd is None:
        return None
    cisd_index, cisd_level, protected_swing = cisd
    continuation_index = v6._first_continuation(
        bars,
        side=side,
        start_index=cisd_index + 1,
        protected_swing=protected_swing,
    )
    if continuation_index is None:
        return None
    continuation = bars[continuation_index]
    entry = continuation.close
    if model_kind is v6.H4ModelKind.SAME_C2:
        in_body = (
            entry > h4_bar.open
            if side is DemoTradingSetupSide.LONG
            else entry < h4_bar.open
        )
        if not in_body:
            return None
    risk = (
        entry - protected_swing
        if side is DemoTradingSetupSide.LONG
        else protected_swing - entry
    )
    if risk <= 0:
        return None
    target = (
        entry + Decimal("2") * risk
        if side is DemoTradingSetupSide.LONG
        else entry - Decimal("2") * risk
    )
    if target <= 0:
        return None
    return (
        v6.CandidateSignal(
            symbol=symbol,
            side=side,
            model_kind=model_kind,
            h4_opened_at=h4_opened_at,
            signal_at=continuation.closed_at,
            entry=entry,
            stop=protected_swing,
            target=target,
            poi=poi,
            cisd_level=cisd_level,
            cisd_confirmed_at=bars[cisd_index].closed_at,
            protected_swing_extreme=protected_swing,
        ),
        continuation_index,
    )


def _opportunities_for_h4(
    *,
    symbol: str,
    indexed: dict[datetime, Vt08IndexC2R1Bar],
    h4: dict[datetime, Vt08IndexC2R1Bar],
    h4_opened_at: datetime,
    multi_poi: bool,
    rearm: bool,
) -> tuple[ExpandedOpportunity, ...]:
    h4_bar = h4.get(h4_opened_at.astimezone(UTC))
    if h4_bar is None:
        return ()
    side = v7._daily_bias(indexed, before=h4_opened_at)
    if side is None:
        return ()

    if multi_poi:
        pois = _source_pois_for_h4(
            indexed,
            h4,
            h4_opened_at=h4_opened_at,
            side=side,
        )
    else:
        priority = v6._source_poi_for_h4(
            indexed,
            h4,
            h4_opened_at=h4_opened_at,
            side=side,
        )
        pois = (priority,) if priority is not None else ()
    if not pois:
        return ()

    bars = v6._bars_between(indexed, start=h4_opened_at, end=h4_bar.closed_at)
    if not bars:
        return ()
    model_kind = v6._completed_h4_model(
        indexed,
        h4,
        current_h4_open=h4_opened_at,
        side=side,
    )
    if model_kind is None:
        model_kind = v6.H4ModelKind.SAME_C2

    result: list[ExpandedOpportunity] = []
    for poi in pois:
        cursor = 0
        rearm_index = 0
        while cursor < len(bars):
            touches = _touch_indices(bars, poi, start_index=cursor)
            if not touches:
                break
            touch_index = touches[0]
            built = _candidate_from_sequence(
                symbol=symbol,
                h4_bar=h4_bar,
                h4_opened_at=h4_opened_at,
                bars=bars,
                poi=poi,
                side=side,
                model_kind=model_kind,
                touch_index=touch_index,
            )
            if built is None:
                cursor = touch_index + 1
                if not rearm:
                    break
                continue
            signal, continuation_index = built
            result.append(
                ExpandedOpportunity(
                    signal=signal,
                    source_poi_kind=poi.kind.value,
                    poi_touch_at=bars[touch_index].opened_at.astimezone(UTC),
                    rearm_index=rearm_index,
                )
            )
            if not rearm:
                break
            rearm_index += 1
            cursor = continuation_index + 1

    poi_priority = {
        v6.PoiKind.FVG.value: 0,
        v6.PoiKind.RELEVANT_SWING.value: 1,
        v6.PoiKind.CISD.value: 2,
    }
    deduped: dict[tuple[object, ...], ExpandedOpportunity] = {}
    for item in sorted(
        result,
        key=lambda value: (
            value.signal.signal_at,
            poi_priority.get(value.source_poi_kind, 99),
            value.rearm_index,
        ),
    ):
        deduped.setdefault(item.identity(), item)
    return tuple(deduped.values())


def _variant_settings(
    variant: ExpansionVariant,
) -> tuple[tuple[int, ...], bool, bool]:
    if variant is ExpansionVariant.V7_BASE:
        return V7_ANCHORS, False, False
    if variant is ExpansionVariant.PLUS_14:
        return PLUS_14_ANCHORS, False, False
    if variant is ExpansionVariant.MULTI_POI:
        return V7_ANCHORS, True, False
    if variant is ExpansionVariant.MULTI_POI_PLUS_14:
        return PLUS_14_ANCHORS, True, False
    if variant is ExpansionVariant.MULTI_POI_REARM:
        return V7_ANCHORS, True, True
    if variant is ExpansionVariant.MULTI_POI_REARM_PLUS_14:
        return PLUS_14_ANCHORS, True, True
    raise ValueError(f"unsupported expansion variant: {variant}")


def _build_variant_surface(
    *,
    variant: ExpansionVariant,
    symbol: str,
    bars: Sequence[Vt08IndexC2R1Bar],
) -> VariantSurface:
    anchors, multi_poi, rearm = _variant_settings(variant)
    indexed = {bar.opened_at.astimezone(UTC): bar for bar in bars}
    h4 = v6._build_h4(indexed)
    opportunities: list[ExpandedOpportunity] = []
    for opened in sorted(h4):
        if opened.astimezone(_NY).hour not in anchors:
            continue
        local_date = opened.astimezone(_NY).date()
        if not (r1.START_DATE <= local_date < r1.END_DATE_EXCLUSIVE):
            continue
        opportunities.extend(
            _opportunities_for_h4(
                symbol=symbol,
                indexed=indexed,
                h4=h4,
                h4_opened_at=opened,
                multi_poi=multi_poi,
                rearm=rearm,
            )
        )

    opportunities.sort(
        key=lambda item: (
            item.signal.signal_at,
            item.signal.symbol,
            item.signal.entry,
            item.signal.stop,
        )
    )
    source_counts: dict[str, int] = {}
    for item in opportunities:
        source_counts[item.source_poi_kind] = (
            source_counts.get(item.source_poi_kind, 0) + 1
        )
    return VariantSurface(
        variant=variant,
        opportunities=tuple(opportunities),
        source_counts=source_counts,
    )


def _retarget(
    signal: v6.CandidateSignal,
    target_r: Decimal,
) -> v6.CandidateSignal:
    return r1._retarget(signal, target_r)


def _model_surface(
    surface: VariantSurface,
    *,
    bars: Sequence[Vt08IndexC2R1Bar],
    target_r: Decimal,
) -> tuple[v6.ModeledV6Trade, ...]:
    indexed = {bar.opened_at.astimezone(UTC): bar for bar in bars}
    trades: list[v6.ModeledV6Trade] = []
    for opportunity in surface.opportunities:
        trade = v6._model_trade(
            _retarget(opportunity.signal, target_r),
            indexed=indexed,
            end_date_exclusive=r1.END_DATE_EXCLUSIVE,
        )
        if trade is not None:
            trades.append(trade)
    return tuple(
        sorted(
            trades,
            key=lambda item: (item.signal.signal_at, item.signal.symbol),
        )
    )


def _metrics_from_trades(
    trades: Sequence[v6.ModeledV6Trade],
    *,
    stress: Decimal,
) -> dict[str, Any]:
    return cast(dict[str, Any], v6._metrics(trades, stress=stress))


def _overlap_diagnostics(
    trades: Sequence[v6.ModeledV6Trade],
) -> dict[str, Any]:
    by_symbol: dict[str, list[v6.ModeledV6Trade]] = {}
    for trade in trades:
        by_symbol.setdefault(trade.signal.symbol, []).append(trade)
    overlaps = 0
    sequential_count = 0
    for symbol_trades in by_symbol.values():
        last_exit: datetime | None = None
        for trade in sorted(symbol_trades, key=lambda item: item.signal.signal_at):
            if last_exit is not None and trade.signal.signal_at < last_exit:
                overlaps += 1
                continue
            sequential_count += 1
            last_exit = trade.exited_at
    total = len(trades)
    return {
        "independent_trade_count": total,
        "same_symbol_overlap_count": overlaps,
        "same_symbol_overlap_rate": (
            format(Decimal(overlaps) / Decimal(total), "f") if total else "0"
        ),
        "one_active_position_per_symbol_count": sequential_count,
    }


def _variant_report(
    *,
    variant: ExpansionVariant,
    surfaces: dict[str, VariantSurface],
    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]],
) -> dict[str, Any]:
    target_results: list[dict[str, Any]] = []
    for target_r in TARGET_GRID:
        all_trades: list[v6.ModeledV6Trade] = []
        by_market: dict[str, Any] = {}
        for symbol in r1.SYMBOLS:
            trades = _model_surface(
                surfaces[symbol],
                bars=bars_by_symbol[symbol],
                target_r=target_r,
            )
            all_trades.extend(trades)
            by_market[symbol] = {
                "primary": _metrics_from_trades(trades, stress=PRIMARY_STRESS),
                "secondary": _metrics_from_trades(trades, stress=SECONDARY_STRESS),
                "overlap": _overlap_diagnostics(trades),
                "source_poi_counts": surfaces[symbol].source_counts,
            }
        ordered = tuple(
            sorted(
                all_trades,
                key=lambda item: (item.signal.signal_at, item.signal.symbol),
            )
        )
        target_results.append(
            {
                "target_r": format(target_r, "f"),
                "primary": _metrics_from_trades(ordered, stress=PRIMARY_STRESS),
                "secondary": _metrics_from_trades(ordered, stress=SECONDARY_STRESS),
                "overlap": _overlap_diagnostics(ordered),
                "by_market": by_market,
            }
        )

    def rank(row: dict[str, Any]) -> tuple[int, Decimal, Decimal]:
        primary = cast(dict[str, Any], row["primary"])
        overlap = cast(dict[str, Any], row["overlap"])
        density_pass = int(
            int(primary["sample"]) >= DENSITY_HARD_GATE
            and int(overlap["one_active_position_per_symbol_count"])
            >= DENSITY_HARD_GATE
        )
        pf = Decimal(str(primary["profit_factor"] or "0"))
        dd = Decimal(str(primary["max_drawdown_r"]))
        return density_pass, pf, -dd

    target_results.sort(key=rank, reverse=True)
    best = target_results[0] if target_results else None
    anchors, multi_poi, rearm = _variant_settings(variant)
    return {
        "variant": variant.value,
        "anchors": list(anchors),
        "multi_poi": multi_poi,
        "structural_rearm": rearm,
        "opportunity_count": sum(
            len(surfaces[symbol].opportunities) for symbol in r1.SYMBOLS
        ),
        "by_market_opportunity_count": {
            symbol: len(surfaces[symbol].opportunities) for symbol in r1.SYMBOLS
        },
        "target_results": target_results,
        "best_fixed_target": best,
        "density_hard_gate": DENSITY_HARD_GATE,
    }


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, Any]:
    roots = {
        "NAS100": nas100_root,
        "SP500": sp500_root,
        "US30": us30_root,
    }
    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]] = {}
    provenance: dict[str, Any] = {}
    for symbol in r1.SYMBOLS:
        bars, source = r2._load_cibo_m15_available(roots[symbol], symbol=symbol)
        bars_by_symbol[symbol] = bars
        provenance[symbol] = source

    reports: list[dict[str, Any]] = []
    for variant in ExpansionVariant:
        surfaces = {
            symbol: _build_variant_surface(
                variant=variant,
                symbol=symbol,
                bars=bars_by_symbol[symbol],
            )
            for symbol in r1.SYMBOLS
        }
        reports.append(
            _variant_report(
                variant=variant,
                surfaces=surfaces,
                bars_by_symbol=bars_by_symbol,
            )
        )

    density_variants = [
        row
        for row in reports
        if int(row["opportunity_count"]) >= DENSITY_HARD_GATE
    ]
    sequential_density_variants: list[str] = []
    economic_density_candidates: list[dict[str, Any]] = []
    for row in reports:
        for target_row in cast(list[dict[str, Any]], row["target_results"]):
            primary = cast(dict[str, Any], target_row["primary"])
            overlap = cast(dict[str, Any], target_row["overlap"])
            sequential = int(overlap["one_active_position_per_symbol_count"])
            if sequential >= DENSITY_HARD_GATE:
                if str(row["variant"]) not in sequential_density_variants:
                    sequential_density_variants.append(str(row["variant"]))
                pf = Decimal(str(primary["profit_factor"] or "0"))
                dd = Decimal(str(primary["max_drawdown_r"]))
                if pf >= Decimal("1.30") and dd <= Decimal("12"):
                    economic_density_candidates.append(
                        {
                            "variant": row["variant"],
                            "target_r": target_row["target_r"],
                            "primary": primary,
                            "secondary": target_row["secondary"],
                            "overlap": overlap,
                        }
                    )
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "window": {
            "window_id": r1.WINDOW_ID,
            "start_date": r1.START_DATE.isoformat(),
            "end_date_exclusive": r1.END_DATE_EXCLUSIVE.isoformat(),
            "status": "CONSUMED_TUNING",
            "fresh_certification_holdout": False,
        },
        "owner_density_contract": {
            "minimum_trades_2y_three_markets": DENSITY_HARD_GATE,
            "drawdown_requirement": "LOW",
            "profit_factor_requirement": "HIGH",
            "density_must_not_be_achieved_by_duplicate_identical_signals": True,
        },
        "strategy": {
            "frozen_v7_candidate_id": v7.CANDIDATE_ID,
            "frozen_v7_rule_fingerprint": v7.RULE_FINGERPRINT,
            "v7_mutated": False,
            "round4_is_new_research_identity": True,
            "daily_bias": "V7_SOURCE_CORRECTED",
            "initial_stop": "PROTECTED_SWING",
            "confirmation": "M15_CISD_THEN_CONTINUATION",
        },
        "provenance": provenance,
        "variant_reports": reports,
        "density_variant_count": len(density_variants),
        "density_variants": [row["variant"] for row in density_variants],
        "sequential_density_variant_count": len(sequential_density_variants),
        "sequential_density_variants": sequential_density_variants,
        "economic_density_candidate_count": len(economic_density_candidates),
        "economic_density_candidates": economic_density_candidates,
        "governance": {
            "research_only": True,
            "tuning_window_consumed": True,
            "fresh_holdout_claim": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nas100-root", type=Path, required=True)
    parser.add_argument("--sp500-root", type=Path, required=True)
    parser.add_argument("--us30-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = build_report(
        nas100_root=args.nas100_root,
        sp500_root=args.sp500_root,
        us30_root=args.us30_root,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "identity": IDENTITY,
                "density_variant_count": report["density_variant_count"],
                "density_variants": report["density_variants"],
                "sequential_density_variant_count": (
                    report["sequential_density_variant_count"]
                ),
                "economic_density_candidate_count": (
                    report["economic_density_candidate_count"]
                ),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
