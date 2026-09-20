"""VT08 Index R98 — cross-H4 dynamic POI lifecycle census.

R95 rebuilt the full FVG -> relevant swing -> CISD hierarchy, but only inside
one H4. R97 allowed Protected-Swing state to persist across H4 boundaries, but
replacement swings still came only from each H4's static source-POI surface.

Primary TTrades continuation guidance says the POI hierarchy must be recalculated
from every newest Protected Swing toward current range. R98 combines those two
missing pieces without adding another timeframe or using PnL.

Contract
--------
- Primary model remains D1 bias -> H4 structure -> M15 execution.
- Lifecycle starts only after a closed C2/C3 Ideal Formation.
- An Ideal Formation at a later H4 close replaces the prior lifecycle.
- Between Ideal Formations, the active Protected Swing persists until:
  invalidation, daily-bias change/ambiguity, or a newer source-qualified M15
  Protected Swing.
- For every active swing, M15 POIs are rebuilt dynamically in strict priority:
  FVG -> relevant swing -> CISD.
- A newer source-qualified PS becomes the new stepping stone even if its
  continuation occurs later.
- One execution maximum per active PS. A continuation outside Owner-authorized
  H4 anchors consumes that swing but is not counted as a trade; this prevents
  chasing the same already-expanded swing later.
- Execution is exact M15 break-and-close continuation and only at
  22/02/06/10 NY.
- Ties where invalidation/replacement ordering is ambiguous fail closed.

R98 is a no-PnL consumed-evidence census. No target, risk, market/anchor
selection, candidate, certification or runtime authority is created.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, replace
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
    vt08_index_r94_ttrades_timeframe_hierarchy_freeze as r94,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r95_full_dynamic_poi_hierarchy as r95,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r96_ideal_formation_cross_h4_carry as r96,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r97_persistent_ps_lifecycle as r97,
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

SCHEMA = "qore.trader_lab.vt08_index_r98_cross_h4_dynamic_poi_lifecycle.v1"
IDENTITY = "VT08_INDEX_R98_CROSS_H4_DYNAMIC_POI_LIFECYCLE_001"

SOURCE_R97_RUN_ID = 35535136703
SOURCE_R97_ARTIFACT_ID = 10613125272
SOURCE_R97_ARTIFACT_DIGEST = (
    "sha256:97864b91f41ff6578d5c16ebb98a88559795e2698110cb7297d4afad949eebf7"
)


@dataclass(frozen=True, slots=True)
class IdealSeed:
    activation_at: datetime
    side: DemoTradingSetupSide
    protected_swing: Decimal
    confirmed_at: datetime
    formation_h4_opened_at: datetime
    closure_kind: str


@dataclass(frozen=True, slots=True)
class DynamicState:
    side: DemoTradingSetupSide
    protected_swing: Decimal
    confirmed_at: datetime
    origin_index: int
    consumed: bool
    source_kind: str


@dataclass(frozen=True, slots=True)
class DynamicReplacement:
    confirm_index: int
    protected_swing: Decimal
    family: str
    poi_kind: str


@dataclass(frozen=True, slots=True)
class DynamicExecution:
    symbol: str
    continuation_at: datetime
    side: DemoTradingSetupSide
    entry: Decimal
    protected_swing: Decimal
    source_kind: str

    def identity(self) -> tuple[object, ...]:
        return (
            self.symbol,
            self.continuation_at.astimezone(UTC),
            self.side.value,
            self.entry,
            self.protected_swing,
        )


def _first_invalidation_index(
    bars: Sequence[Vt08IndexC2R1Bar],
    *,
    start_index: int,
    end_index: int,
    side: DemoTradingSetupSide,
    protected_swing: Decimal,
) -> int | None:
    for index in range(start_index, end_index):
        bar = bars[index]
        invalidated = (
            bar.low <= protected_swing
            if side is DemoTradingSetupSide.LONG
            else bar.high >= protected_swing
        )
        if invalidated:
            return index
    return None


def _first_continuation_index(
    bars: Sequence[Vt08IndexC2R1Bar],
    *,
    start_index: int,
    end_index: int,
    side: DemoTradingSetupSide,
    protected_swing: Decimal,
) -> int | None:
    for index in range(start_index, end_index):
        bar = bars[index]
        invalidated = (
            bar.low <= protected_swing
            if side is DemoTradingSetupSide.LONG
            else bar.high >= protected_swing
        )
        if invalidated:
            return None
        if index <= 0:
            continue
        previous = bars[index - 1]
        continuation = (
            bar.high > previous.high and bar.close > previous.high
            if side is DemoTradingSetupSide.LONG
            else bar.low < previous.low and bar.close < previous.low
        )
        if continuation:
            return index
    return None


def _first_dynamic_replacement(
    bars: Sequence[Vt08IndexC2R1Bar],
    *,
    origin_index: int,
    after_index: int,
    end_index: int,
    side: DemoTradingSetupSide,
    protected_swing: Decimal,
) -> tuple[DynamicReplacement | None, bool]:
    """Return earliest new PS after cursor; ambiguity at same confirm fails closed."""
    if origin_index >= end_index:
        return None, False

    invalidation = _first_invalidation_index(
        bars,
        start_index=max(origin_index, after_index),
        end_index=end_index,
        side=side,
        protected_swing=protected_swing,
    )
    causal_end = invalidation if invalidation is not None else end_index
    if causal_end - origin_index < 3:
        return None, False

    segment = bars[origin_index:causal_end]
    pois = r95._dynamic_pois(
        segment,
        side=side,
        protected_swing=protected_swing,
        earliest_observed_index=0,
    )
    if not pois:
        return None, False

    swings = r84._short_term_swings(segment, side=side)
    series_rows = r84._confirmed_opposing_series(segment, side=side)
    candidates: list[DynamicReplacement] = []
    local_after = max(0, after_index - origin_index)

    for touch_index, bar in enumerate(segment):
        if touch_index < local_after:
            continue
        chosen = r95._priority_poi_at_touch(
            pois,
            bar=bar,
            touch_index=touch_index,
            side=side,
            protected_swing=protected_swing,
        )
        if chosen is None:
            continue
        for series in series_rows:
            if series.confirm_index <= touch_index:
                continue
            if series.confirm_index < local_after:
                continue
            liquidity = r84._swept_known_short_term_liquidity(
                swings,
                series=series,
                side=side,
                touch_index=touch_index,
            )
            fvg = r84._original_fvg_reaction(
                segment,
                poi=chosen.poi,
                series=series,
                touch_index=touch_index,
            )
            family = r84._event_family(
                liquidity=liquidity,
                fvg=fvg,
            )
            if family is None:
                continue
            candidates.append(
                DynamicReplacement(
                    confirm_index=origin_index + series.confirm_index,
                    protected_swing=series.extreme,
                    family=family,
                    poi_kind=chosen.poi.kind.value,
                )
            )

    if not candidates:
        return None, False
    earliest_index = min(row.confirm_index for row in candidates)
    earliest = tuple(
        row for row in candidates if row.confirm_index == earliest_index
    )
    by_swing: dict[Decimal, DynamicReplacement] = {}
    for row in earliest:
        by_swing.setdefault(row.protected_swing, row)
    if len(by_swing) != 1:
        return None, True
    return next(iter(by_swing.values())), False


def _ideal_seeds(
    *,
    symbol: str,
    indexed: dict[datetime, Vt08IndexC2R1Bar],
    h4: dict[datetime, Vt08IndexC2R1Bar],
    h4_keys: tuple[datetime, ...],
    start_date: Any,
    end_date: Any,
) -> tuple[IdealSeed, ...]:
    result: list[IdealSeed] = []
    side_cache: dict[Any, DemoTradingSetupSide | None] = {}

    for opened in h4_keys:
        local = opened.astimezone(v7._NY)
        if not (start_date <= local.date() < end_date):
            continue
        if local.date() not in side_cache:
            side_cache[local.date()] = v7._daily_bias(
                indexed,
                before=opened,
            )
        side = side_cache[local.date()]
        if side is None:
            continue
        closure = r96._closure_kind(
            h4,
            h4_keys,
            opened=opened,
            side=side,
        )
        if closure is None:
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
        candidates = r85._source_ps_candidates(
            symbol=symbol,
            opened=opened,
            side=side,
            pois=pois,
            inside=inside,
        )
        surviving = tuple(
            row
            for row in candidates
            if r96._survives_after_confirmation(
                inside,
                confirm_index=row.confirm_index,
                side=side,
                protected_swing=row.event.protected_swing,
            )
        )
        selected, ambiguous = r97._select_unique_newest(surviving)
        if ambiguous or selected is None:
            continue
        result.append(
            IdealSeed(
                activation_at=h4[opened].closed_at.astimezone(UTC),
                side=side,
                protected_swing=selected.event.protected_swing,
                confirmed_at=selected.event.confirmed_at.astimezone(UTC),
                formation_h4_opened_at=opened.astimezone(UTC),
                closure_kind=closure,
            )
        )
    return tuple(sorted(result, key=lambda row: row.activation_at))


def _bar_h4_map(
    *,
    indexed: dict[datetime, Vt08IndexC2R1Bar],
    h4: dict[datetime, Vt08IndexC2R1Bar],
) -> dict[datetime, datetime]:
    result: dict[datetime, datetime] = {}
    for opened, h4_bar in h4.items():
        for bar in r6._bars_between_fast(
            indexed,
            start=opened,
            end=h4_bar.closed_at,
        ):
            result[bar.opened_at.astimezone(UTC)] = opened.astimezone(UTC)
    return result


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
    ordered_bars = tuple(
        sorted(
            (
                bar
                for bar in bars
                if start_date
                <= bar.opened_at.astimezone(v7._NY).date()
                < end_date
            ),
            key=lambda row: row.opened_at,
        )
    )
    index_by_open = {
        bar.opened_at.astimezone(UTC): index
        for index, bar in enumerate(ordered_bars)
    }
    h4 = v6._build_h4(indexed)
    h4_keys = tuple(sorted(h4))
    bar_to_h4 = _bar_h4_map(indexed=indexed, h4=h4)
    h4_bias = {
        opened: v7._daily_bias(indexed, before=opened)
        for opened in h4_keys
    }
    seeds = _ideal_seeds(
        symbol=symbol,
        indexed=indexed,
        h4=h4,
        h4_keys=h4_keys,
        start_date=start_date,
        end_date=end_date,
    )

    same_h4: dict[tuple[object, ...], r85.ExecutableContinuation] = {}
    for opened in h4_keys:
        local = opened.astimezone(v7._NY)
        if not (start_date <= local.date() < end_date):
            continue
        side = h4_bias[opened]
        if side is None:
            continue
        for row in r96._intra_h4_executables(
            symbol=symbol,
            indexed=indexed,
            h4=h4,
            h4_keys=h4_keys,
            opened=opened,
            side=side,
        ):
            same_h4.setdefault(
                (
                    row.event.symbol,
                    row.continuation_at.astimezone(UTC),
                    row.event.side.value,
                    row.entry,
                    row.event.protected_swing,
                ),
                row,
            )

    executions: dict[tuple[object, ...], DynamicExecution] = {}
    diagnostics: Counter[str] = Counter()
    by_source: Counter[str] = Counter()
    by_poi: Counter[str] = Counter()
    by_anchor: Counter[str] = Counter()

    for seed_index, seed in enumerate(seeds):
        start_index = index_by_open.get(seed.activation_at)
        if start_index is None:
            continue
        next_seed_at = (
            seeds[seed_index + 1].activation_at
            if seed_index + 1 < len(seeds)
            else None
        )
        end_index = len(ordered_bars)
        if next_seed_at is not None:
            end_index = index_by_open.get(next_seed_at, end_index)
        if start_index >= end_index:
            continue

        state = DynamicState(
            side=seed.side,
            protected_swing=seed.protected_swing,
            confirmed_at=seed.confirmed_at,
            origin_index=start_index,
            consumed=False,
            source_kind=f"IDEAL_{seed.closure_kind}",
        )
        cursor = start_index

        while cursor < end_index:
            current_h4 = bar_to_h4.get(
                ordered_bars[cursor].opened_at.astimezone(UTC)
            )
            if current_h4 is None:
                cursor += 1
                continue
            if h4_bias.get(current_h4) is not state.side:
                diagnostics["LIFECYCLE_ENDED_BIAS_CHANGE_OR_AMBIGUITY"] += 1
                break

            bias_end = end_index
            for probe in range(cursor, end_index):
                probe_h4 = bar_to_h4.get(
                    ordered_bars[probe].opened_at.astimezone(UTC)
                )
                if probe_h4 is None:
                    continue
                if h4_bias.get(probe_h4) is not state.side:
                    bias_end = probe
                    break

            invalidation = _first_invalidation_index(
                ordered_bars,
                start_index=cursor,
                end_index=bias_end,
                side=state.side,
                protected_swing=state.protected_swing,
            )
            replacement_row, replacement_ambiguous = _first_dynamic_replacement(
                ordered_bars,
                origin_index=state.origin_index,
                after_index=cursor,
                end_index=bias_end,
                side=state.side,
                protected_swing=state.protected_swing,
            )
            if replacement_ambiguous:
                diagnostics["LIFECYCLE_ENDED_AMBIGUOUS_REPLACEMENT"] += 1
                break

            continuation = (
                None
                if state.consumed
                else _first_continuation_index(
                    ordered_bars,
                    start_index=cursor,
                    end_index=bias_end,
                    side=state.side,
                    protected_swing=state.protected_swing,
                )
            )

            event_indices = [
                value
                for value in (
                    invalidation,
                    replacement_row.confirm_index
                    if replacement_row is not None
                    else None,
                    continuation,
                )
                if value is not None
            ]
            if not event_indices:
                break
            event_index = min(event_indices)

            if invalidation is not None and invalidation == event_index:
                diagnostics["LIFECYCLE_ENDED_INVALIDATION"] += 1
                break

            if (
                replacement_row is not None
                and replacement_row.confirm_index == event_index
            ):
                state = DynamicState(
                    side=state.side,
                    protected_swing=replacement_row.protected_swing,
                    confirmed_at=ordered_bars[
                        replacement_row.confirm_index
                    ].closed_at.astimezone(UTC),
                    origin_index=replacement_row.confirm_index + 1,
                    consumed=False,
                    source_kind="DYNAMIC_STEPPING_STONE",
                )
                cursor = replacement_row.confirm_index + 1
                diagnostics["DYNAMIC_PS_REPLACEMENT"] += 1
                by_poi[replacement_row.poi_kind] += 1
                continue

            if continuation is not None and continuation == event_index:
                bar = ordered_bars[continuation]
                containing_h4 = bar_to_h4.get(bar.opened_at.astimezone(UTC))
                if containing_h4 is None:
                    cursor = continuation + 1
                    state = replace(state, consumed=True)
                    continue
                local_anchor = containing_h4.astimezone(v7._NY).hour
                if local_anchor in r4.V7_ANCHORS:
                    entry = bar.close
                    risk = (
                        entry - state.protected_swing
                        if state.side is DemoTradingSetupSide.LONG
                        else state.protected_swing - entry
                    )
                    if risk > 0:
                        row = DynamicExecution(
                            symbol=symbol,
                            continuation_at=bar.closed_at.astimezone(UTC),
                            side=state.side,
                            entry=entry,
                            protected_swing=state.protected_swing,
                            source_kind=state.source_kind,
                        )
                        executions.setdefault(row.identity(), row)
                        diagnostics["AUTHORIZED_CONTINUATION_EXECUTED"] += 1
                        by_source[row.source_kind] += 1
                        by_anchor[str(local_anchor)] += 1
                else:
                    diagnostics["CONTINUATION_OUTSIDE_EXECUTION_ANCHOR"] += 1
                state = replace(state, consumed=True)
                cursor = continuation + 1
                continue

            break

    overlap = len(set(same_h4) & set(executions))
    union = set(same_h4) | set(executions)
    return {
        "symbol": symbol,
        "ideal_seed_count": len(seeds),
        "same_h4_source_exact_executions": len(same_h4),
        "cross_h4_dynamic_lifecycle_executions": len(executions),
        "exact_overlap_same_vs_dynamic": overlap,
        "exact_union_count": len(union),
        "dynamic_execution_by_source": dict(sorted(by_source.items())),
        "dynamic_replacement_by_poi": dict(sorted(by_poi.items())),
        "dynamic_execution_by_anchor": dict(sorted(by_anchor.items())),
        "diagnostics": dict(sorted(diagnostics.items())),
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
    same = sum(
        int(row["same_h4_source_exact_executions"])
        for row in markets.values()
    )
    dynamic = sum(
        int(row["cross_h4_dynamic_lifecycle_executions"])
        for row in markets.values()
    )
    overlap = sum(
        int(row["exact_overlap_same_vs_dynamic"])
        for row in markets.values()
    )
    union = sum(int(row["exact_union_count"]) for row in markets.values())
    if union != same + dynamic - overlap:
        raise ValueError(f"R98 {window_id} union arithmetic drift")

    if window_id == "5Y":
        density_min = contract.FIVE_YEAR_TRADE_RANGE[0]
        five_year_max = contract.FIVE_YEAR_TRADE_RANGE[1]
        density_max: int | None = five_year_max
        density_pass = density_min <= union <= five_year_max
    elif window_id == "2Y":
        density_min = contract.TWO_YEAR_MIN_TRADES
        density_max = None
        density_pass = union >= density_min
    else:
        density_min = 1000
        density_max = None
        density_pass = union >= density_min

    return {
        "window_id": window_id,
        "canonical_signal_reference": canonical_reference,
        "same_h4_source_exact_executions": same,
        "cross_h4_dynamic_lifecycle_executions": dynamic,
        "exact_overlap_same_vs_dynamic": overlap,
        "exact_union_count": union,
        "density_minimum": density_min,
        "density_maximum": density_max,
        "density_pass": density_pass,
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
        raise ValueError("R98 frozen R58/R59 dependency drift")
    if r67.SOURCE_R66_DECISION != (
        "FAIL_R66_FRESH_HOLDOUT_REJECT_FROZEN_IDENTITY"
    ):
        raise ValueError("R98 source failure decision drift")
    if r94.IDENTITY != (
        "VT08_INDEX_R94_TTRADES_TIMEFRAME_HIERARCHY_FREEZE_001"
    ):
        raise ValueError("R98 R94 hierarchy freeze drift")
    if r97.IDENTITY != (
        "VT08_INDEX_R97_PERSISTENT_PROTECTED_SWING_LIFECYCLE_001"
    ):
        raise ValueError("R98 R97 identity drift")
    if 14 in r4.V7_ANCHORS or 18 in r4.V7_ANCHORS:
        raise ValueError("R98 execution anchor contract drift")

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
        "source_r97": {
            "run_id": SOURCE_R97_RUN_ID,
            "artifact_id": SOURCE_R97_ARTIFACT_ID,
            "artifact_digest": SOURCE_R97_ARTIFACT_DIGEST,
        },
        "dynamic_lifecycle_contract": {
            "primary_model": "D1_H4_M15",
            "start_requires_closed_ideal_formation": True,
            "later_ideal_formation_replaces_prior_lifecycle": True,
            "numeric_h4_ttl": None,
            "poi_priority": ["fvg", "relevant-swing", "cisd"],
            "poi_rebuilt_after_every_new_ps": True,
            "new_ps_can_form_across_h4_boundaries": True,
            "one_execution_per_active_ps": True,
            "continuation_outside_owner_anchor_consumes_ps": True,
            "execution_anchors_ny": list(r4.V7_ANCHORS),
            "owner_disabled_14_preserved": True,
            "context_only_18_preserved": True,
            "same_timestamp_invalidation_priority": "FAIL_CLOSED",
            "pnl_evaluated": False,
        },
        "five_year": five,
        "recent_two_year": two,
        "r66_failed_holdout": failed,
        "decision": "R98_CROSS_H4_DYNAMIC_POI_LIFECYCLE_CENSUS_COMPLETE_NO_TRADES",
        "governance": {
            "forensics_only": True,
            "consumed_evidence_only": True,
            "fresh_holdout_claim": False,
            "source_primary_model_only": True,
            "future_information_used": False,
            "numeric_ttl_search": False,
            "pnl_evaluated": False,
            "risk_changed": False,
            "target_changed": False,
            "anchors_changed": False,
            "market_or_anchor_selection_by_outcome": False,
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
                        "same_h4_source_exact_executions",
                        "cross_h4_dynamic_lifecycle_executions",
                        "exact_union_count",
                        "density_pass",
                    )
                },
                "recent_two_year": {
                    key: report["recent_two_year"][key]
                    for key in (
                        "same_h4_source_exact_executions",
                        "cross_h4_dynamic_lifecycle_executions",
                        "exact_union_count",
                        "density_pass",
                    )
                },
                "r66": {
                    key: report["r66_failed_holdout"][key]
                    for key in (
                        "same_h4_source_exact_executions",
                        "cross_h4_dynamic_lifecycle_executions",
                        "exact_union_count",
                        "density_pass",
                    )
                },
                "decision": report["decision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
