"""VT08 Index R86 — dynamic intra-H4 FVG continuation/rearm census.

R85 proved that source-exact Protected Swings built only from the POI snapshot
available at the H4 open cannot satisfy density: 546 executable continuations in
5Y, 237 in recent2Y and 168 in R66.

Primary TTrades continuation semantics explicitly allow a protected trend to
create new protected swings when price subsequently reaches an important level
and closes through the causal opposing series. The lower-timeframe refinement
example explicitly uses a new FVG or liquidity sweep for continuation.

R86 tests exactly one missing causal mechanism, without PnL:
- start only from an R85 source-exact executable continuation;
- after that continuation, discover direction-consistent M15 FVGs as they are
  causally formed inside the same H4;
- the FVG must be observed before its later retest;
- after retest, require an exact R84 opposing-series close-through reaction;
- require the exact V6 continuation rule and V7 SAME_C2 body transition;
- a subsequent dynamic rearm must form after the previous continuation;
- do not use future bars to declare the FVG before its third bar closes.

Both an all-valid union (upper bound) and a deterministic earliest-continuation
path are reported. Neither is a candidate and no PnL is evaluated.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
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
    vt08_index_v6_ttrades_source_faithful as v6,
)
from qore.infrastructure.trader_lab import (
    vt08_index_v7_ttrades_source_corrected as v7,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    Vt08IndexC2R1Bar,
)

SCHEMA = "qore.trader_lab.vt08_index_r86_dynamic_m15_fvg_rearm.v1"
IDENTITY = "VT08_INDEX_R86_DYNAMIC_M15_FVG_REARM_CENSUS_001"

SOURCE_R85_RUN_ID = 35525680874
SOURCE_R85_ARTIFACT_ID = 10609721617
SOURCE_R85_ARTIFACT_DIGEST = (
    "sha256:fa2c1516354ba38a9b0d9fccf1853b5b7e62eb25a080c69150f57faef1e1e059"
)


@dataclass(frozen=True, slots=True)
class DynamicFvg:
    low: Decimal
    high: Decimal
    formed_index: int

    def as_source_poi(
        self,
        bars: Sequence[Vt08IndexC2R1Bar],
    ) -> v6.SourcePoi:
        return v6.SourcePoi(
            kind=v6.PoiKind.FVG,
            low=self.low,
            high=self.high,
            observed_at=bars[self.formed_index].closed_at,
        )

    def identity(self) -> tuple[object, ...]:
        return (self.low, self.high, self.formed_index)


@dataclass(frozen=True, slots=True)
class DynamicRearm:
    protected_swing: Decimal
    series_open: Decimal
    fvg: DynamicFvg
    touch_index: int
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


def _directional_fvgs(
    bars: Sequence[Vt08IndexC2R1Bar],
    *,
    side: DemoTradingSetupSide,
    earliest_formed_index: int,
) -> tuple[DynamicFvg, ...]:
    result: list[DynamicFvg] = []
    for index in range(2, len(bars)):
        if index < earliest_formed_index:
            continue
        a = bars[index - 2]
        c = bars[index]
        if side is DemoTradingSetupSide.LONG and a.high < c.low:
            result.append(
                DynamicFvg(
                    low=a.high,
                    high=c.low,
                    formed_index=index,
                )
            )
        elif side is DemoTradingSetupSide.SHORT and a.low > c.high:
            result.append(
                DynamicFvg(
                    low=c.high,
                    high=a.low,
                    formed_index=index,
                )
            )
    return tuple(result)


def _dynamic_rearms_after(
    *,
    inside: Sequence[Vt08IndexC2R1Bar],
    h4_bar: Vt08IndexC2R1Bar,
    side: DemoTradingSetupSide,
    model_kind: v6.H4ModelKind,
    after_continuation_index: int,
) -> tuple[DynamicRearm, ...]:
    series_rows = r84._confirmed_opposing_series(inside, side=side)
    result: dict[tuple[object, ...], DynamicRearm] = {}

    for fvg in _directional_fvgs(
        inside,
        side=side,
        earliest_formed_index=after_continuation_index,
    ):
        poi = fvg.as_source_poi(inside)
        touch_indices = tuple(
            index
            for index in range(fvg.formed_index + 1, len(inside))
            if poi.touched_by(inside[index])
        )
        for touch_index in touch_indices:
            if touch_index <= after_continuation_index:
                continue
            for series in series_rows:
                if series.confirm_index <= touch_index:
                    continue
                if not r84._original_fvg_reaction(
                    inside,
                    poi=poi,
                    series=series,
                    touch_index=touch_index,
                ):
                    continue

                continuation_index = v6._first_continuation(
                    inside,
                    side=side,
                    start_index=series.confirm_index + 1,
                    protected_swing=series.extreme,
                )
                if (
                    continuation_index is None
                    or continuation_index <= after_continuation_index
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

                row = DynamicRearm(
                    protected_swing=series.extreme,
                    series_open=series.series_open,
                    fvg=fvg,
                    touch_index=touch_index,
                    confirm_index=series.confirm_index,
                    continuation_index=continuation_index,
                    continuation_at=continuation.closed_at.astimezone(UTC),
                    entry=entry,
                )
                result.setdefault(row.identity(), row)

    return tuple(
        sorted(
            result.values(),
            key=lambda row: (
                row.continuation_index,
                row.confirm_index,
                row.fvg.formed_index,
                row.protected_swing,
            ),
        )
    )


def _initial_executables(
    *,
    symbol: str,
    opened: datetime,
    side: DemoTradingSetupSide,
    pois: Sequence[v6.SourcePoi],
    inside: Sequence[Vt08IndexC2R1Bar],
    h4_bar: Vt08IndexC2R1Bar,
    model_kind: v6.H4ModelKind,
) -> tuple[r85.ExecutableContinuation, ...]:
    candidates = r85._source_ps_candidates(
        symbol=symbol,
        opened=opened,
        side=side,
        pois=pois,
        inside=inside,
    )
    rows: dict[tuple[object, ...], r85.ExecutableContinuation] = {}
    for candidate in candidates:
        row, reason = r85._executable_from_event(
            candidate,
            inside=inside,
            h4_bar=h4_bar,
            model_kind=model_kind,
        )
        if row is not None and reason == "EXECUTABLE":
            rows.setdefault(row.identity(), row)
    return tuple(
        sorted(
            rows.values(),
            key=lambda row: (
                row.continuation_index,
                row.continuation_at,
                row.event.protected_swing,
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
    initial = _initial_executables(
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
            "dynamic_union_rearm_count": 0,
            "earliest_path_rearm_count": 0,
        }

    union: dict[tuple[object, ...], DynamicRearm] = {}
    for seed in initial:
        for row in _dynamic_rearms_after(
            inside=inside,
            h4_bar=h4_bar,
            side=side,
            model_kind=model_kind,
            after_continuation_index=seed.continuation_index,
        ):
            union.setdefault(row.identity(), row)

    # Deterministic causal journey: take the earliest initial continuation,
    # then repeatedly take the earliest later source-valid dynamic FVG rearm.
    cursor = initial[0].continuation_index
    earliest_path = 0
    used: set[tuple[object, ...]] = set()
    while True:
        later = tuple(
            row
            for row in _dynamic_rearms_after(
                inside=inside,
                h4_bar=h4_bar,
                side=side,
                model_kind=model_kind,
                after_continuation_index=cursor,
            )
            if row.identity() not in used
        )
        if not later:
            break
        selected = later[0]
        used.add(selected.identity())
        earliest_path += 1
        if selected.continuation_index <= cursor:
            raise ValueError("R86 dynamic journey failed to advance causally")
        cursor = selected.continuation_index

    return {
        "initial_executable_count": len(initial),
        "dynamic_union_rearm_count": len(union),
        "earliest_path_rearm_count": earliest_path,
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
        for key, value in journey.items():
            totals[key] += int(value)
            by_anchor[anchor][key] += int(value)
        if int(journey["dynamic_union_rearm_count"]) > 0:
            totals["h4_with_dynamic_rearm"] += 1
            by_anchor[anchor]["h4_with_dynamic_rearm"] += 1

    return {
        "symbol": symbol,
        "totals": dict(sorted(totals.items())),
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
    start_date, end_date, canonical_reference = r74._window_contract(window_id)

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
    for row in markets.values():
        totals.update(row["totals"])

    initial = int(totals["initial_executable_count"])
    dynamic_union = int(totals["dynamic_union_rearm_count"])
    earliest_path = int(totals["earliest_path_rearm_count"])
    union_surface = initial + dynamic_union
    strict_path_surface = initial + earliest_path

    if window_id == "5Y":
        density_min = contract.FIVE_YEAR_TRADE_RANGE[0]
        five_year_density_max = contract.FIVE_YEAR_TRADE_RANGE[1]
        density_max: int | None = five_year_density_max
        union_density_pass = (
            density_min <= union_surface <= five_year_density_max
        )
        strict_density_pass = (
            density_min <= strict_path_surface <= five_year_density_max
        )
    elif window_id == "2Y":
        density_min = contract.TWO_YEAR_MIN_TRADES
        density_max = None
        union_density_pass = union_surface >= density_min
        strict_density_pass = strict_path_surface >= density_min
    else:
        density_min = 1000
        density_max = None
        union_density_pass = union_surface >= density_min
        strict_density_pass = strict_path_surface >= density_min

    return {
        "window_id": window_id,
        "canonical_signal_reference": canonical_reference,
        "initial_source_exact_executables": initial,
        "dynamic_fvg_union_rearms": dynamic_union,
        "dynamic_fvg_earliest_path_rearms": earliest_path,
        "union_surface_count": union_surface,
        "strict_earliest_path_surface_count": strict_path_surface,
        "density_minimum": density_min,
        "density_maximum": density_max,
        "union_density_pass": union_density_pass,
        "strict_earliest_path_density_pass": strict_density_pass,
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
        raise ValueError("R86 frozen R58/R59 dependency drift")
    if r67.SOURCE_R66_DECISION != (
        "FAIL_R66_FRESH_HOLDOUT_REJECT_FROZEN_IDENTITY"
    ):
        raise ValueError("R86 source failure decision drift")
    if r85.IDENTITY != (
        "VT08_INDEX_R85_SOURCE_EXACT_PS_CONTINUATION_REARM_CENSUS_001"
    ):
        raise ValueError("R86 R85 identity drift")
    if 14 in r4.V7_ANCHORS:
        raise ValueError("R86 Owner-disabled 14:00 anchor unexpectedly enabled")

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
        "source_r85": {
            "identity": r85.IDENTITY,
            "run_id": SOURCE_R85_RUN_ID,
            "artifact_id": SOURCE_R85_ARTIFACT_ID,
            "artifact_digest": SOURCE_R85_ARTIFACT_DIGEST,
        },
        "dynamic_rearm_contract": {
            "seed_requires_r85_source_exact_executable": True,
            "dynamic_level": "M15_FVG",
            "fvg_requires_three_closed_m15_bars": True,
            "retest_must_occur_after_fvg_observation": True,
            "protected_swing_confirmation": (
                "exact_R84_opposing_series_close_through"
            ),
            "continuation": "exact_V6_first_continuation",
            "same_c2_body_transition": "exact_V7",
            "rearm_requires_new_post_continuation_structure": True,
            "owner_disabled_14_preserved": True,
            "pnl_evaluated": False,
        },
        "five_year": five,
        "recent_two_year": two,
        "r66_failed_holdout": failed,
        "decision": "R86_DYNAMIC_M15_FVG_REARM_CENSUS_COMPLETE_NO_TRADES",
        "governance": {
            "forensics_only": True,
            "consumed_evidence_only": True,
            "fresh_holdout_claim": False,
            "future_information_used": False,
            "pnl_evaluated": False,
            "fvg_grid_or_threshold_search": False,
            "dynamic_relevant_swing_added": False,
            "dynamic_cisd_poi_added": False,
            "signals_created_for_trading": False,
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
                        "dynamic_fvg_union_rearms",
                        "dynamic_fvg_earliest_path_rearms",
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
                        "dynamic_fvg_union_rearms",
                        "dynamic_fvg_earliest_path_rearms",
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
                        "dynamic_fvg_union_rearms",
                        "dynamic_fvg_earliest_path_rearms",
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
