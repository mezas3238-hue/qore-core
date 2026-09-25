"""VT08 Index R87 — dynamic short-term-liquidity rearm census.

This laboratory isolates the second source-authorized continuation mechanism
from R86's dynamic FVG path.

Primary TTrades Protected-Swing semantics:
- bullish: run below a short-term low, then close above the down-close series
  that formed the low;
- bearish: run above a short-term high, then close below the up-close series;
- once a Protected Swing exists, later valid Protected Swings become stepping
  stones for continuation entries.

R87 starts only after an R85 source-exact executable continuation. It then
requires a *new post-continuation liquidity raid* of a causally known three-M15
short-term swing, exact R84 opposing-series confirmation, exact V6
continuation, and the frozen V7 SAME_C2 body transition.

No FVG dynamic rearm is included here. No PnL, target, risk allocator or
selection by outcome is evaluated.
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

SCHEMA = "qore.trader_lab.vt08_index_r87_dynamic_liquidity_rearm.v1"
IDENTITY = "VT08_INDEX_R87_DYNAMIC_SHORT_TERM_LIQUIDITY_REARM_CENSUS_001"

SOURCE_R85_RUN_ID = 35525680874
SOURCE_R85_ARTIFACT_ID = 10609721617
SOURCE_R85_ARTIFACT_DIGEST = (
    "sha256:fa2c1516354ba38a9b0d9fccf1853b5b7e62eb25a080c69150f57faef1e1e059"
)


@dataclass(frozen=True, slots=True)
class DynamicLiquidityRearm:
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


def _dynamic_liquidity_rearms_after(
    *,
    inside: Sequence[Vt08IndexC2R1Bar],
    h4_bar: Vt08IndexC2R1Bar,
    side: DemoTradingSetupSide,
    model_kind: v6.H4ModelKind,
    after_continuation_index: int,
) -> tuple[DynamicLiquidityRearm, ...]:
    swings = r84._short_term_swings(inside, side=side)
    series_rows = r84._confirmed_opposing_series(inside, side=side)
    result: dict[tuple[object, ...], DynamicLiquidityRearm] = {}

    for series in series_rows:
        if (
            series.extreme_index <= after_continuation_index
            or series.confirm_index <= after_continuation_index
        ):
            continue
        if not r84._swept_known_short_term_liquidity(
            swings,
            series=series,
            side=side,
            touch_index=after_continuation_index + 1,
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

        row = DynamicLiquidityRearm(
            protected_swing=series.extreme,
            series_open=series.series_open,
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
) -> dict[str, int]:
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

    union: dict[tuple[object, ...], DynamicLiquidityRearm] = {}
    for seed in initial:
        for row in _dynamic_liquidity_rearms_after(
            inside=inside,
            h4_bar=h4_bar,
            side=side,
            model_kind=model_kind,
            after_continuation_index=seed.continuation_index,
        ):
            union.setdefault(row.identity(), row)

    cursor = initial[0].continuation_index
    earliest_path = 0
    while True:
        later = _dynamic_liquidity_rearms_after(
            inside=inside,
            h4_bar=h4_bar,
            side=side,
            model_kind=model_kind,
            after_continuation_index=cursor,
        )
        if not later:
            break
        selected = later[0]
        if selected.continuation_index <= cursor:
            raise ValueError("R87 dynamic journey failed to advance causally")
        earliest_path += 1
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
            totals[key] += value
            by_anchor[anchor][key] += value
        if journey["dynamic_union_rearm_count"] > 0:
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
    union_rearm = int(totals["dynamic_union_rearm_count"])
    path_rearm = int(totals["earliest_path_rearm_count"])
    union_surface = initial + union_rearm
    path_surface = initial + path_rearm

    if window_id == "5Y":
        density_min = contract.FIVE_YEAR_TRADE_RANGE[0]
        five_year_density_max = contract.FIVE_YEAR_TRADE_RANGE[1]
        density_max: int | None = five_year_density_max
        union_pass = density_min <= union_surface <= five_year_density_max
        path_pass = density_min <= path_surface <= five_year_density_max
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
        "dynamic_liquidity_union_rearms": union_rearm,
        "dynamic_liquidity_earliest_path_rearms": path_rearm,
        "union_surface_count": union_surface,
        "strict_earliest_path_surface_count": path_surface,
        "density_minimum": density_min,
        "density_maximum": density_max,
        "union_density_pass": union_pass,
        "strict_earliest_path_density_pass": path_pass,
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
        raise ValueError("R87 frozen R58/R59 dependency drift")
    if r67.SOURCE_R66_DECISION != (
        "FAIL_R66_FRESH_HOLDOUT_REJECT_FROZEN_IDENTITY"
    ):
        raise ValueError("R87 source failure decision drift")
    if r85.IDENTITY != (
        "VT08_INDEX_R85_SOURCE_EXACT_PS_CONTINUATION_REARM_CENSUS_001"
    ):
        raise ValueError("R87 R85 identity drift")
    if 14 in r4.V7_ANCHORS:
        raise ValueError("R87 Owner-disabled 14:00 anchor unexpectedly enabled")

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
            "dynamic_cause": "SHORT_TERM_LIQUIDITY_SWEEP",
            "short_term_swing": (
                "causal three-M15 pivot known after right neighbor closes"
            ),
            "sweep_must_occur_after_prior_continuation": True,
            "confirmation": "exact_R84_opposing_series_close_through",
            "continuation": "exact_V6_first_continuation",
            "same_c2_body_transition": "exact_V7",
            "dynamic_fvg_included": False,
            "pnl_evaluated": False,
        },
        "five_year": five,
        "recent_two_year": two,
        "r66_failed_holdout": failed,
        "decision": "R87_DYNAMIC_LIQUIDITY_REARM_CENSUS_COMPLETE_NO_TRADES",
        "governance": {
            "forensics_only": True,
            "consumed_evidence_only": True,
            "fresh_holdout_claim": False,
            "future_information_used": False,
            "pnl_evaluated": False,
            "numeric_separation_threshold": None,
            "dynamic_fvg_included": False,
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
                        "dynamic_liquidity_union_rearms",
                        "dynamic_liquidity_earliest_path_rearms",
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
                        "dynamic_liquidity_union_rearms",
                        "dynamic_liquidity_earliest_path_rearms",
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
                        "dynamic_liquidity_union_rearms",
                        "dynamic_liquidity_earliest_path_rearms",
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
