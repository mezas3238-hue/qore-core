"""VT08 Index R95 — full dynamic continuation POI hierarchy census.

R94 freezes VT08's primary source model as D1 bias -> H4 structure -> M15
execution. R95 stays inside that model.

R86 and R87 tested partial continuation mechanisms independently:
- R86: dynamically formed M15 FVG only;
- R87: new short-term-liquidity sweep only.

Primary TTrades continuation material says that after a new Protected Swing is
formed the trader repeats the POI process from that protected swing toward the
current range:
    FVG -> relevant swing -> CISD/retest.
The next Protected Swing still must be source-qualified by one of the two
authorized causes: liquidity sweep or FVG reaction.

R95 therefore rebuilds the complete causal continuation loop after every
source-exact executable Protected Swing:
1. preserve the initial R85 source-exact H4/M15 execution;
2. after that PS is confirmed, observe new causal M15 FVGs, relevant swings
   and CISD levels;
3. after the prior continuation, when price reaches an available level, apply
   source priority FVG -> relevant swing -> CISD;
4. for ties inside one family, choose the first level encountered from the
   prior Protected Swing toward current range;
5. require an R84 source-qualified PS reaction and exact V6 continuation;
6. advance the new Protected Swing and repeat.

Both an all-causal branch union (density upper bound) and one deterministic
earliest-continuation path are reported. No PnL, target, sizing or candidate is
created.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, deque
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    vt08_index_cibo_2y_density_round4 as r4,
)
from qore.infrastructure.trader_lab import (
    vt08_index_concurrent_market_contract as contract,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r6_five_year_validation as r6,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r59_candidate_freeze as freeze,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r67_r66_failure_forensics as r67,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r74_ambiguous_bias_resolvers as r74,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r84_source_exact_ps_event_census as r84,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r85_source_exact_ps_continuation_rearm as r85,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r86_dynamic_m15_fvg_rearm as r86,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r94_ttrades_timeframe_hierarchy_freeze as r94,
)
from qore.infrastructure.trader_lab import (
    vt08_index_v6_ttrades_source_faithful as v6,
)
from qore.infrastructure.trader_lab import (
    vt08_index_v7_ttrades_source_corrected as v7,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    Vt08IndexC2R1Bar,
)

SCHEMA = "qore.trader_lab.vt08_index_r95_full_dynamic_poi_hierarchy.v1"
IDENTITY = "VT08_INDEX_R95_FULL_DYNAMIC_CONTINUATION_POI_HIERARCHY_001"

SOURCE_R94_RUN_ID = 35531601091

_PRIORITY = {
    v6.PoiKind.FVG: 0,
    v6.PoiKind.RELEVANT_SWING: 1,
    v6.PoiKind.CISD: 2,
}


@dataclass(frozen=True, slots=True)
class DynamicPoi:
    poi: v6.SourcePoi
    observed_index: int

    def identity(self) -> tuple[object, ...]:
        return (
            self.poi.kind.value,
            self.poi.low,
            self.poi.high,
            self.observed_index,
        )


@dataclass(frozen=True, slots=True)
class JourneySeed:
    ps_confirm_index: int
    continuation_index: int
    protected_swing: Decimal

    def identity(self) -> tuple[object, ...]:
        return (
            self.ps_confirm_index,
            self.continuation_index,
            self.protected_swing,
        )


@dataclass(frozen=True, slots=True)
class HierarchyRearm:
    poi: v6.SourcePoi
    poi_observed_index: int
    touch_index: int
    family: str
    protected_swing: Decimal
    series_open: Decimal
    confirm_index: int
    continuation_index: int
    continuation_at: datetime
    entry: Decimal

    def identity(self) -> tuple[object, ...]:
        return (
            self.continuation_at.astimezone(UTC),
            self.entry,
            self.protected_swing,
        )

    def as_seed(self) -> JourneySeed:
        return JourneySeed(
            ps_confirm_index=self.confirm_index,
            continuation_index=self.continuation_index,
            protected_swing=self.protected_swing,
        )


def _dynamic_pois(
    bars: Sequence[Vt08IndexC2R1Bar],
    *,
    side: DemoTradingSetupSide,
    protected_swing: Decimal,
    earliest_observed_index: int,
) -> tuple[DynamicPoi, ...]:
    result: dict[tuple[object, ...], DynamicPoi] = {}

    for fvg in r86._directional_fvgs(
        bars,
        side=side,
        earliest_formed_index=earliest_observed_index,
    ):
        poi = fvg.as_source_poi(bars)
        row = DynamicPoi(poi=poi, observed_index=fvg.formed_index)
        result.setdefault(row.identity(), row)

    for _pivot_index, level, known_after_index in r84._short_term_swings(
        bars,
        side=side,
    ):
        if known_after_index < earliest_observed_index:
            continue
        poi = v6.SourcePoi(
            kind=v6.PoiKind.RELEVANT_SWING,
            low=level,
            high=level,
            observed_at=bars[known_after_index].closed_at,
        )
        row = DynamicPoi(poi=poi, observed_index=known_after_index)
        result.setdefault(row.identity(), row)

    for series in r84._confirmed_opposing_series(bars, side=side):
        if series.confirm_index < earliest_observed_index:
            continue
        poi = v6.SourcePoi(
            kind=v6.PoiKind.CISD,
            low=series.series_open,
            high=series.series_open,
            observed_at=bars[series.confirm_index].closed_at,
        )
        row = DynamicPoi(poi=poi, observed_index=series.confirm_index)
        result.setdefault(row.identity(), row)

    filtered = [
        row
        for row in result.values()
        if (
            row.poi.high > protected_swing
            if side is DemoTradingSetupSide.LONG
            else row.poi.low < protected_swing
        )
    ]
    return tuple(
        sorted(
            filtered,
            key=lambda row: (
                row.observed_index,
                _PRIORITY[row.poi.kind],
                row.poi.low,
                row.poi.high,
            ),
        )
    )


def _distance_from_protected_swing(
    row: DynamicPoi,
    *,
    side: DemoTradingSetupSide,
    protected_swing: Decimal,
) -> Decimal:
    if side is DemoTradingSetupSide.LONG:
        return max(Decimal(), row.poi.low - protected_swing)
    return max(Decimal(), protected_swing - row.poi.high)


def _priority_poi_at_touch(
    candidates: Sequence[DynamicPoi],
    *,
    bar: Vt08IndexC2R1Bar,
    touch_index: int,
    side: DemoTradingSetupSide,
    protected_swing: Decimal,
) -> DynamicPoi | None:
    available = tuple(
        row
        for row in candidates
        if row.observed_index < touch_index
        and row.poi.observed_at.astimezone(UTC)
        <= bar.opened_at.astimezone(UTC)
        and row.poi.touched_by(bar)
    )
    if not available:
        return None
    best_priority = min(_PRIORITY[row.poi.kind] for row in available)
    family = tuple(
        row
        for row in available
        if _PRIORITY[row.poi.kind] == best_priority
    )
    return min(
        family,
        key=lambda row: (
            _distance_from_protected_swing(
                row,
                side=side,
                protected_swing=protected_swing,
            ),
            -row.observed_index,
            row.poi.low,
            row.poi.high,
        ),
    )


def _hierarchy_rearms_after(
    *,
    inside: Sequence[Vt08IndexC2R1Bar],
    h4_bar: Vt08IndexC2R1Bar,
    side: DemoTradingSetupSide,
    model_kind: v6.H4ModelKind,
    seed: JourneySeed,
) -> tuple[HierarchyRearm, ...]:
    pois = _dynamic_pois(
        inside,
        side=side,
        protected_swing=seed.protected_swing,
        earliest_observed_index=seed.ps_confirm_index,
    )
    if not pois:
        return ()

    swings = r84._short_term_swings(inside, side=side)
    series_rows = r84._confirmed_opposing_series(inside, side=side)
    rows: dict[tuple[object, ...], HierarchyRearm] = {}

    for touch_index in range(seed.continuation_index + 1, len(inside)):
        chosen = _priority_poi_at_touch(
            pois,
            bar=inside[touch_index],
            touch_index=touch_index,
            side=side,
            protected_swing=seed.protected_swing,
        )
        if chosen is None:
            continue

        for series in series_rows:
            if series.confirm_index <= touch_index:
                continue
            liquidity = r84._swept_known_short_term_liquidity(
                swings,
                series=series,
                side=side,
                touch_index=touch_index,
            )
            fvg = r84._original_fvg_reaction(
                inside,
                poi=chosen.poi,
                series=series,
                touch_index=touch_index,
            )
            family = r84._event_family(liquidity=liquidity, fvg=fvg)
            if family is None:
                continue

            continuation_index = v6._first_continuation(
                inside,
                side=side,
                start_index=series.confirm_index + 1,
                protected_swing=series.extreme,
            )
            if (
                continuation_index is None
                or continuation_index <= seed.continuation_index
            ):
                continue
            continuation = inside[continuation_index]
            entry = continuation.close

            if model_kind is v6.H4ModelKind.SAME_C2:
                in_body = (
                    entry > h4_bar.open
                    if side is DemoTradingSetupSide.LONG
                    else entry < h4_bar.open
                )
                if not in_body:
                    continue

            risk = (
                entry - series.extreme
                if side is DemoTradingSetupSide.LONG
                else series.extreme - entry
            )
            if risk <= 0:
                continue

            row = HierarchyRearm(
                poi=chosen.poi,
                poi_observed_index=chosen.observed_index,
                touch_index=touch_index,
                family=family,
                protected_swing=series.extreme,
                series_open=series.series_open,
                confirm_index=series.confirm_index,
                continuation_index=continuation_index,
                continuation_at=continuation.closed_at.astimezone(UTC),
                entry=entry,
            )
            rows.setdefault(row.identity(), row)

    return tuple(
        sorted(
            rows.values(),
            key=lambda row: (
                row.continuation_index,
                row.confirm_index,
                _PRIORITY[row.poi.kind],
                row.touch_index,
                row.protected_swing,
            ),
        )
    )


def _initial_seeds(
    *,
    symbol: str,
    opened: datetime,
    side: DemoTradingSetupSide,
    pois: Sequence[v6.SourcePoi],
    inside: Sequence[Vt08IndexC2R1Bar],
    h4_bar: Vt08IndexC2R1Bar,
    model_kind: v6.H4ModelKind,
) -> tuple[JourneySeed, ...]:
    seeds: dict[tuple[object, ...], JourneySeed] = {}
    for candidate in r85._source_ps_candidates(
        symbol=symbol,
        opened=opened,
        side=side,
        pois=pois,
        inside=inside,
    ):
        executable, reason = r85._executable_from_event(
            candidate,
            inside=inside,
            h4_bar=h4_bar,
            model_kind=model_kind,
        )
        if executable is None or reason != "EXECUTABLE":
            continue
        seed = JourneySeed(
            ps_confirm_index=candidate.confirm_index,
            continuation_index=executable.continuation_index,
            protected_swing=candidate.event.protected_swing,
        )
        seeds.setdefault(seed.identity(), seed)

    return tuple(
        sorted(
            seeds.values(),
            key=lambda row: (
                row.continuation_index,
                row.ps_confirm_index,
                row.protected_swing,
            ),
        )
    )


def _journey_for_h4(
    *,
    symbol: str,
    opened: datetime,
    side: DemoTradingSetupSide,
    pois: Sequence[v6.SourcePoi],
    inside: Sequence[Vt08IndexC2R1Bar],
    h4_bar: Vt08IndexC2R1Bar,
    model_kind: v6.H4ModelKind,
) -> dict[str, Any]:
    initial = _initial_seeds(
        symbol=symbol,
        opened=opened,
        side=side,
        pois=pois,
        inside=inside,
        h4_bar=h4_bar,
        model_kind=model_kind,
    )
    if not initial:
        return {
            "initial_executable_count": 0,
            "hierarchy_union_rearm_count": 0,
            "earliest_path_rearm_count": 0,
            "union_by_poi": {},
            "path_by_poi": {},
        }

    union: dict[tuple[object, ...], HierarchyRearm] = {}
    queue: deque[JourneySeed] = deque(initial)
    seen_seeds = {seed.identity() for seed in initial}
    while queue:
        seed = queue.popleft()
        for row in _hierarchy_rearms_after(
            inside=inside,
            h4_bar=h4_bar,
            side=side,
            model_kind=model_kind,
            seed=seed,
        ):
            union.setdefault(row.identity(), row)
            next_seed = row.as_seed()
            if next_seed.identity() not in seen_seeds:
                seen_seeds.add(next_seed.identity())
                queue.append(next_seed)

    path_rows: list[HierarchyRearm] = []
    cursor = initial[0]
    used: set[tuple[object, ...]] = set()
    while True:
        later = tuple(
            row
            for row in _hierarchy_rearms_after(
                inside=inside,
                h4_bar=h4_bar,
                side=side,
                model_kind=model_kind,
                seed=cursor,
            )
            if row.identity() not in used
        )
        if not later:
            break
        selected = later[0]
        if selected.continuation_index <= cursor.continuation_index:
            raise ValueError("R95 continuation journey failed to advance")
        path_rows.append(selected)
        used.add(selected.identity())
        cursor = selected.as_seed()

    union_by_poi = Counter(row.poi.kind.value for row in union.values())
    path_by_poi = Counter(row.poi.kind.value for row in path_rows)
    return {
        "initial_executable_count": len(initial),
        "hierarchy_union_rearm_count": len(union),
        "earliest_path_rearm_count": len(path_rows),
        "union_by_poi": dict(sorted(union_by_poi.items())),
        "path_by_poi": dict(sorted(path_by_poi.items())),
    }


def _market(
    *,
    symbol: str,
    bars: Sequence[Vt08IndexC2R1Bar],
    start_date: Any,
    end_date: Any,
) -> dict[str, Any]:
    indexed = {
        bar.opened_at.astimezone(UTC): bar
        for bar in bars
    }
    h4 = v6._build_h4(indexed)
    h4_keys = tuple(sorted(h4))
    side_cache: dict[Any, DemoTradingSetupSide | None] = {}
    totals: Counter[str] = Counter()
    union_poi: Counter[str] = Counter()
    path_poi: Counter[str] = Counter()
    by_anchor: dict[str, Counter[str]] = {}

    for opened in h4_keys:
        local = opened.astimezone(v7._NY)
        local_date = local.date()
        if not (start_date <= local_date < end_date):
            continue
        if local.hour not in r4.V7_ANCHORS:
            continue
        if local_date not in side_cache:
            side_cache[local_date] = v7._daily_bias(
                indexed,
                before=opened,
            )
        side = side_cache[local_date]
        if side is None:
            continue

        pois = r6._source_pois_fast(
            indexed,
            h4,
            h4_keys,
            h4_opened_at=opened,
            side=side,
        )
        if not pois:
            continue
        inside = r6._bars_between_fast(
            indexed,
            start=opened,
            end=h4[opened].closed_at,
        )
        if not inside:
            continue

        model_kind = r6._completed_h4_model_fast(
            indexed,
            h4,
            h4_keys,
            current_h4_open=opened,
            side=side,
        )
        if model_kind is None:
            model_kind = v6.H4ModelKind.SAME_C2

        journey = _journey_for_h4(
            symbol=symbol,
            opened=opened,
            side=side,
            pois=pois,
            inside=inside,
            h4_bar=h4[opened],
            model_kind=model_kind,
        )
        anchor = str(local.hour)
        by_anchor.setdefault(anchor, Counter())
        for key in (
            "initial_executable_count",
            "hierarchy_union_rearm_count",
            "earliest_path_rearm_count",
        ):
            value = int(journey[key])
            totals[key] += value
            by_anchor[anchor][key] += value
        union_poi.update(journey["union_by_poi"])
        path_poi.update(journey["path_by_poi"])
        if int(journey["hierarchy_union_rearm_count"]) > 0:
            totals["h4_with_hierarchy_rearm"] += 1
            by_anchor[anchor]["h4_with_hierarchy_rearm"] += 1

    return {
        "symbol": symbol,
        "totals": dict(sorted(totals.items())),
        "union_by_poi": dict(sorted(union_poi.items())),
        "path_by_poi": dict(sorted(path_poi.items())),
        "by_anchor": {
            key: dict(sorted(value.items()))
            for key, value in sorted(by_anchor.items())
        },
    }


def _window(
    *,
    roots: dict[str, Path],
    window_id: str,
) -> dict[str, Any]:
    _stream, bars_by_symbol, provenance = r74._load_window(
        roots=roots,
        window_id=window_id,
    )
    _start, _end, canonical_reference = r74._window_contract(window_id)
    start_date, end_date, _canonical = r74._window_contract(window_id)

    markets = {
        symbol: _market(
            symbol=symbol,
            bars=bars_by_symbol[symbol],
            start_date=start_date,
            end_date=end_date,
        )
        for symbol in contract.MARKETS
    }
    totals: Counter[str] = Counter()
    union_poi: Counter[str] = Counter()
    path_poi: Counter[str] = Counter()
    for row in markets.values():
        totals.update(row["totals"])
        union_poi.update(row["union_by_poi"])
        path_poi.update(row["path_by_poi"])

    initial = int(totals["initial_executable_count"])
    union_rearm = int(totals["hierarchy_union_rearm_count"])
    path_rearm = int(totals["earliest_path_rearm_count"])
    union_surface = initial + union_rearm
    path_surface = initial + path_rearm

    if window_id == "5Y":
        density_min = contract.FIVE_YEAR_TRADE_RANGE[0]
        density_max: int | None = contract.FIVE_YEAR_TRADE_RANGE[1]
        union_pass = density_min <= union_surface <= density_max
        path_pass = density_min <= path_surface <= density_max
    elif window_id == "2Y":
        density_min = contract.TWO_YEAR_MIN_TRADES
        density_max = None
        union_pass = union_surface >= density_min
        path_pass = path_surface >= density_min
    else:
        density_min = 1000
        density_max = None
        union_pass = union_surface >= density_min
        path_pass = path_surface >= density_min

    return {
        "window_id": window_id,
        "canonical_signal_reference": canonical_reference,
        "initial_source_exact_executables": initial,
        "full_hierarchy_union_rearms": union_rearm,
        "full_hierarchy_earliest_path_rearms": path_rearm,
        "union_surface_count": union_surface,
        "strict_earliest_path_surface_count": path_surface,
        "density_minimum": density_min,
        "density_maximum": density_max,
        "union_density_pass": union_pass,
        "strict_earliest_path_density_pass": path_pass,
        "union_by_poi": dict(sorted(union_poi.items())),
        "path_by_poi": dict(sorted(path_poi.items())),
        "by_market": markets,
        "provenance": provenance,
    }


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, Any]:
    if not freeze.dependency_contract_matches():
        raise ValueError("R95 frozen R58/R59 dependency drift")
    if r67.SOURCE_R66_DECISION != (
        "FAIL_R66_FRESH_HOLDOUT_REJECT_FROZEN_IDENTITY"
    ):
        raise ValueError("R95 source failure decision drift")
    if r94.IDENTITY != (
        "VT08_INDEX_R94_TTRADES_TIMEFRAME_HIERARCHY_FREEZE_001"
    ):
        raise ValueError("R95 R94 hierarchy freeze drift")
    if 14 in r4.V7_ANCHORS or 18 in r4.V7_ANCHORS:
        raise ValueError("R95 executable anchor contract drift")

    hierarchy = r94.payload()["frozen_hierarchy"]
    if hierarchy["vt08_primary_model"] != {
        "bias_timeframe": "D1",
        "structure_timeframe": "H4",
        "entry_timeframe": "M15",
        "model_role": "PRIMARY_TTRADES_PREFERRED_MODEL",
    }:
        raise ValueError("R95 primary timeframe model drift")

    roots = {
        "NAS100": nas100_root,
        "SP500": sp500_root,
        "US30": us30_root,
    }
    five = _window(roots=roots, window_id="5Y")
    two = _window(roots=roots, window_id="2Y")
    failed = _window(roots=roots, window_id="R66")

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "source_r94_run_id": SOURCE_R94_RUN_ID,
        "dynamic_hierarchy_contract": {
            "primary_model": "D1_H4_M15",
            "seed": "R85_SOURCE_EXACT_EXECUTABLE",
            "poi_priority": ["fvg", "relevant-swing", "cisd"],
            "poi_rebuilt_after_each_protected_swing": True,
            "poi_touch_must_follow_prior_continuation": True,
            "poi_must_be_observed_before_touch": True,
            "same_family_tie_break": (
                "first level from protected swing toward current range"
            ),
            "protected_swing_families": [
                r84.FAMILY_LIQUIDITY,
                r84.FAMILY_FVG,
                r84.FAMILY_BOTH,
            ],
            "continuation": "EXACT_V6_FIRST_CONTINUATION",
            "same_c2_body_transition": "EXACT_V7",
            "h1_m5_independent_signals_added": False,
            "m15_m1_independent_signals_added": False,
            "pnl_evaluated": False,
        },
        "five_year": five,
        "recent_two_year": two,
        "r66_failed_holdout": failed,
        "decision": "R95_FULL_DYNAMIC_POI_HIERARCHY_CENSUS_COMPLETE_NO_TRADES",
        "governance": {
            "forensics_only": True,
            "consumed_evidence_only": True,
            "fresh_holdout_claim": False,
            "source_primary_model_only": True,
            "future_information_used": False,
            "pnl_evaluated": False,
            "numeric_threshold_search": False,
            "market_or_anchor_selection_by_outcome": False,
            "risk_changed": False,
            "target_changed": False,
            "anchors_changed": False,
            "owner_disabled_14_preserved": True,
            "candidate_created": False,
            "trader_certified": False,
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
                "five_year": {
                    key: report["five_year"][key]
                    for key in (
                        "initial_source_exact_executables",
                        "full_hierarchy_union_rearms",
                        "full_hierarchy_earliest_path_rearms",
                        "union_surface_count",
                        "strict_earliest_path_surface_count",
                        "union_density_pass",
                        "strict_earliest_path_density_pass",
                    )
                },
                "recent_two_year": {
                    key: report["recent_two_year"][key]
                    for key in (
                        "initial_source_exact_executables",
                        "full_hierarchy_union_rearms",
                        "full_hierarchy_earliest_path_rearms",
                        "union_surface_count",
                        "strict_earliest_path_surface_count",
                        "union_density_pass",
                        "strict_earliest_path_density_pass",
                    )
                },
                "r66": {
                    key: report["r66_failed_holdout"][key]
                    for key in (
                        "initial_source_exact_executables",
                        "full_hierarchy_union_rearms",
                        "full_hierarchy_earliest_path_rearms",
                        "union_surface_count",
                        "strict_earliest_path_surface_count",
                        "union_density_pass",
                        "strict_earliest_path_density_pass",
                    )
                },
                "decision": report["decision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
