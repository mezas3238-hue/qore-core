"""VT08 Index R134 — R98 dynamic-lifecycle economic replay + Shared atlas.

R133 closed the R75 ambiguous-bias density path: the raw added surface was
negative and the coarse Shared bridge did not isolate a sample-sufficient
transport-safe subset across 5Y, recent2Y and R66.

R134 moves to the materially different source-valid density mechanism from R98:
the cross-H4 dynamic Protected-Swing / POI lifecycle.

Contract
--------
- reproduce the exact R98 same-H4 + cross-H4 lifecycle execution surface;
- deduplicate it by the exact mechanical execution key
  (symbol, continuation_at, side, entry, protected_swing);
- separate exact overlap with the current canonical R74/V7 stream from genuinely
  added lifecycle executions;
- replay only the added executions economically with the current 2.5R target,
  Protected Swing stop, conservative gap/STOP-first intrabar semantics, and
  -0.05R / -0.10R per-trade stress;
- attach the exact R132 Shared causal context BEFORE outcome attachment;
- report period, source-kind, Shared future/regime, PF and drawdown.

No R102 weighting is used on the added-only surface. This prevents a risk
allocator from manufacturing apparent edge. R134 creates no filter, candidate
or runtime policy and changes no owner anchor.
"""

from __future__ import annotations

import argparse
import json
from bisect import bisect_left
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from qore.infrastructure.trader_lab import (
    vt08_index_cibo_2y_density_round4 as r4,
)
from qore.infrastructure.trader_lab import (
    vt08_index_concurrent_market_contract as contract,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r74_ambiguous_bias_resolvers as r74,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r96_ideal_formation_cross_h4_carry as r96,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r98_cross_h4_dynamic_poi_lifecycle as r98,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r108_standard_source_retest_execution_replay as r108,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r132_full_intelligence_bridge as r132,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r133_shared_r75_density_attribution as r133,
)
from qore.infrastructure.trader_lab.vt08_index_v2_candidate import (
    _gap_exit,
    _intrabar_exit,
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

SCHEMA = "qore.trader_lab.vt08_index_r134_r98_lifecycle_economic_replay.v1"
IDENTITY = "VT08_INDEX_R134_R98_DYNAMIC_LIFECYCLE_ECONOMIC_REPLAY_001"

SOURCE_R133_RUN_ID = 36174956716
SOURCE_R133_ARTIFACT_ID = 10882800411
SOURCE_R133_ARTIFACT_DIGEST = (
    "sha256:049a0a71b393413386abd87cbef82a7f"
    "0cd01442968eb2927f21411591475025"
)

TARGET_R = r108.TARGET_R
PRIMARY_STRESS = r108.PRIMARY_STRESS
SECONDARY_STRESS = r108.SECONDARY_STRESS
EXPECTED_CANONICAL = r108.EXPECTED_CANONICAL

ExecutionKey = tuple[str, datetime, str, Decimal, Decimal]


@dataclass(frozen=True, slots=True)
class LifecycleExecution:
    symbol: str
    side: DemoTradingSetupSide
    signal_at: datetime
    entry: Decimal
    stop: Decimal
    source_kind: str

    def key(self) -> ExecutionKey:
        return (
            self.symbol,
            self.signal_at.astimezone(UTC),
            self.side.value,
            self.entry,
            self.stop,
        )


@dataclass(frozen=True, slots=True)
class RawOutcome:
    exited_at: datetime
    r_multiple: Decimal
    exit_reason: str


def _same_h4_rows(
    *,
    symbol: str,
    indexed: dict[datetime, Vt08IndexC2R1Bar],
    h4: dict[datetime, Vt08IndexC2R1Bar],
    h4_keys: tuple[datetime, ...],
    h4_bias: dict[datetime, DemoTradingSetupSide | None],
    start_date: date,
    end_date: date,
) -> dict[ExecutionKey, LifecycleExecution]:
    result: dict[ExecutionKey, LifecycleExecution] = {}
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
            execution = LifecycleExecution(
                symbol=row.event.symbol,
                side=row.event.side,
                signal_at=row.continuation_at.astimezone(UTC),
                entry=row.entry,
                stop=row.event.protected_swing,
                source_kind=f"SAME_H4_{row.event.family}",
            )
            result.setdefault(execution.key(), execution)
    return result


def _dynamic_rows(
    *,
    symbol: str,
    bars: Sequence[Vt08IndexC2R1Bar],
    start_date: date,
    end_date: date,
) -> dict[ExecutionKey, LifecycleExecution]:
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
    bar_to_h4 = r98._bar_h4_map(indexed=indexed, h4=h4)
    h4_bias = {
        opened: v7._daily_bias(indexed, before=opened)
        for opened in h4_keys
    }
    seeds = r98._ideal_seeds(
        symbol=symbol,
        indexed=indexed,
        h4=h4,
        h4_keys=h4_keys,
        start_date=start_date,
        end_date=end_date,
    )

    result: dict[ExecutionKey, LifecycleExecution] = {}

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

        state = r98.DynamicState(
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
                break

            bias_end = end_index
            for probe in range(cursor, end_index):
                probe_h4 = bar_to_h4.get(
                    ordered_bars[probe].opened_at.astimezone(UTC)
                )
                if (
                    probe_h4 is not None
                    and h4_bias.get(probe_h4) is not state.side
                ):
                    bias_end = probe
                    break

            invalidation = r98._first_invalidation_index(
                ordered_bars,
                start_index=cursor,
                end_index=bias_end,
                side=state.side,
                protected_swing=state.protected_swing,
            )
            replacement, ambiguous = r98._first_dynamic_replacement(
                ordered_bars,
                origin_index=state.origin_index,
                after_index=cursor,
                end_index=bias_end,
                side=state.side,
                protected_swing=state.protected_swing,
            )
            if ambiguous:
                break

            continuation = (
                None
                if state.consumed
                else r98._first_continuation_index(
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
                    replacement.confirm_index
                    if replacement is not None
                    else None,
                    continuation,
                )
                if value is not None
            ]
            if not event_indices:
                break
            event_index = min(event_indices)

            if invalidation is not None and invalidation == event_index:
                break

            if (
                replacement is not None
                and replacement.confirm_index == event_index
            ):
                state = r98.DynamicState(
                    side=state.side,
                    protected_swing=replacement.protected_swing,
                    confirmed_at=ordered_bars[
                        replacement.confirm_index
                    ].closed_at.astimezone(UTC),
                    origin_index=replacement.confirm_index + 1,
                    consumed=False,
                    source_kind="DYNAMIC_STEPPING_STONE",
                )
                cursor = replacement.confirm_index + 1
                continue

            if continuation is not None and continuation == event_index:
                bar = ordered_bars[continuation]
                containing_h4 = bar_to_h4.get(
                    bar.opened_at.astimezone(UTC)
                )
                if containing_h4 is None:
                    state = r98.DynamicState(
                        side=state.side,
                        protected_swing=state.protected_swing,
                        confirmed_at=state.confirmed_at,
                        origin_index=state.origin_index,
                        consumed=True,
                        source_kind=state.source_kind,
                    )
                    cursor = continuation + 1
                    continue

                anchor = containing_h4.astimezone(v7._NY).hour
                if anchor in r4.V7_ANCHORS:
                    entry = bar.close
                    risk = abs(entry - state.protected_swing)
                    if risk > 0:
                        execution = LifecycleExecution(
                            symbol=symbol,
                            side=state.side,
                            signal_at=bar.closed_at.astimezone(UTC),
                            entry=entry,
                            stop=state.protected_swing,
                            source_kind=state.source_kind,
                        )
                        result.setdefault(execution.key(), execution)

                state = r98.DynamicState(
                    side=state.side,
                    protected_swing=state.protected_swing,
                    confirmed_at=state.confirmed_at,
                    origin_index=state.origin_index,
                    consumed=True,
                    source_kind=state.source_kind,
                )
                cursor = continuation + 1
                continue

            break

    return result


def _surface(
    *,
    symbol: str,
    bars: Sequence[Vt08IndexC2R1Bar],
    start_date: date,
    end_date: date,
) -> tuple[dict[ExecutionKey, LifecycleExecution], dict[str, int]]:
    indexed = {
        bar.opened_at.astimezone(UTC): bar
        for bar in bars
    }
    h4 = v6._build_h4(indexed)
    h4_keys = tuple(sorted(h4))
    h4_bias = {
        opened: v7._daily_bias(indexed, before=opened)
        for opened in h4_keys
    }
    same = _same_h4_rows(
        symbol=symbol,
        indexed=indexed,
        h4=h4,
        h4_keys=h4_keys,
        h4_bias=h4_bias,
        start_date=start_date,
        end_date=end_date,
    )
    dynamic = _dynamic_rows(
        symbol=symbol,
        bars=bars,
        start_date=start_date,
        end_date=end_date,
    )
    union = dict(same)
    for key, row in dynamic.items():
        union.setdefault(key, row)

    expected = r98._market(
        symbol=symbol,
        bars=bars,
        start_date=start_date,
        end_date=end_date,
    )
    if len(same) != int(expected["same_h4_source_exact_executions"]):
        raise ValueError(f"R134 {symbol} same-H4 reproduction drift")
    if len(dynamic) != int(
        expected["cross_h4_dynamic_lifecycle_executions"]
    ):
        raise ValueError(f"R134 {symbol} dynamic reproduction drift")
    if len(union) != int(expected["exact_union_count"]):
        raise ValueError(f"R134 {symbol} union reproduction drift")

    return union, {
        "same_h4": len(same),
        "dynamic": len(dynamic),
        "same_dynamic_overlap": len(set(same) & set(dynamic)),
        "union": len(union),
    }


def _canonical_key(opportunity: Any) -> ExecutionKey:
    signal = opportunity.signal
    return (
        signal.symbol,
        signal.signal_at.astimezone(UTC),
        signal.side.value,
        signal.entry,
        signal.stop,
    )


def _target_price(row: LifecycleExecution) -> Decimal:
    risk = abs(row.entry - row.stop)
    if row.side is DemoTradingSetupSide.LONG:
        return row.entry + TARGET_R * risk
    return row.entry - TARGET_R * risk


def _close_r(
    row: LifecycleExecution,
    bar: Vt08IndexC2R1Bar,
) -> Decimal:
    risk = abs(row.entry - row.stop)
    if row.side is DemoTradingSetupSide.LONG:
        return (bar.close - row.entry) / risk
    return (row.entry - bar.close) / risk


def _manage(
    row: LifecycleExecution,
    *,
    bars: Sequence[Vt08IndexC2R1Bar],
    opened: Sequence[datetime],
    end_date: date,
) -> RawOutcome:
    target = _target_price(row)
    risk = abs(row.entry - row.stop)
    if risk <= 0:
        raise ValueError("R134 execution risk must be positive")
    start = bisect_left(opened, row.signal_at.astimezone(UTC))
    boundary = v6._boundary_utc(end_date)
    last: Vt08IndexC2R1Bar | None = None

    for bar in bars[start:]:
        if bar.opened_at.astimezone(UTC) >= boundary:
            break
        last = bar
        resolved = _gap_exit(
            side=row.side,
            bar=bar,
            stop=row.stop,
            target=target,
        )
        if resolved is None:
            resolved = _intrabar_exit(
                bar=bar,
                stop=row.stop,
                target=target,
            )
        if resolved is None:
            continue
        exit_price, reason = resolved
        pnl = (
            exit_price - row.entry
            if row.side is DemoTradingSetupSide.LONG
            else row.entry - exit_price
        )
        return RawOutcome(
            exited_at=bar.closed_at.astimezone(UTC),
            r_multiple=pnl / risk,
            exit_reason=reason,
        )

    if last is None:
        return RawOutcome(
            exited_at=row.signal_at.astimezone(UTC),
            r_multiple=Decimal(),
            exit_reason="no-bars",
        )
    return RawOutcome(
        exited_at=last.closed_at.astimezone(UTC),
        r_multiple=_close_r(row, last),
        exit_reason="boundary-mark",
    )


def _metrics(
    rows: Sequence[dict[str, Any]],
    *,
    field: str,
) -> dict[str, Any]:
    ordered = sorted(
        rows,
        key=lambda row: (
            str(row["exited_at"]),
            str(row["symbol"]),
            str(row["signal_at"]),
        ),
    )
    values = tuple(Decimal(str(row[field])) for row in ordered)
    gains = sum((value for value in values if value > 0), Decimal())
    losses = -sum((value for value in values if value < 0), Decimal())
    equity = Decimal()
    peak = Decimal()
    drawdown = Decimal()
    streak = 0
    max_streak = 0
    for value in values:
        equity += value
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
        if value < 0:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0
    total = sum(values, Decimal())
    return {
        "sample": len(values),
        "wins": sum(value > 0 for value in values),
        "losses": sum(value < 0 for value in values),
        "flats": sum(value == 0 for value in values),
        "total_r": str(total),
        "profit_factor": str(gains / losses) if losses else None,
        "max_drawdown_r": str(drawdown),
        "max_losing_streak": max_streak,
    }


def _bundle(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    return {
        "raw": _metrics(rows, field="raw_r"),
        "primary": _metrics(rows, field="primary_r"),
        "secondary": _metrics(rows, field="secondary_r"),
    }


def _group(
    rows: Sequence[dict[str, Any]],
    field: str,
) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row[field])].append(row)
    return {
        key: _bundle(items)
        for key, items in sorted(grouped.items())
    }


def _pair_group(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = f"{row['future_state']}|{row['broad_regime']}"
        grouped[key].append(row)
    return {
        key: _bundle(items)
        for key, items in sorted(grouped.items())
    }


def _window(
    *,
    roots: dict[str, Path],
    window_id: str,
) -> dict[str, Any]:
    canonical, bars_raw, provenance = r74._load_window(
        roots=roots,
        window_id=window_id,
    )
    start_date, end_date, expected = r74._window_contract(window_id)
    if expected != EXPECTED_CANONICAL[window_id]:
        raise ValueError(f"R134 {window_id} canonical contract drift")

    bars_by_symbol: dict[
        str, Sequence[Vt08IndexC2R1Bar]
    ] = {
        symbol: tuple(bars)
        for symbol, bars in bars_raw.items()
    }
    opened_by_symbol = {
        symbol: tuple(
            bar.opened_at.astimezone(UTC)
            for bar in bars
        )
        for symbol, bars in bars_by_symbol.items()
    }
    states: dict[
        str,
        tuple[
            Sequence[Vt08IndexC2R1Bar],
            Sequence[datetime],
        ],
    ] = {
        symbol: (
            bars,
            tuple(bar.closed_at.astimezone(UTC) for bar in bars),
        )
        for symbol, bars in bars_by_symbol.items()
    }

    canonical_keys = {
        _canonical_key(opportunity)
        for opportunity, _outcome in canonical
    }
    if len(canonical_keys) != expected:
        raise ValueError(f"R134 {window_id} canonical identity drift")

    surface: dict[ExecutionKey, LifecycleExecution] = {}
    surface_diag: dict[str, Any] = {}
    for symbol in contract.MARKETS:
        rows, diag = _surface(
            symbol=symbol,
            bars=bars_by_symbol[symbol],
            start_date=start_date,
            end_date=end_date,
        )
        surface_diag[symbol] = diag
        for key, row in rows.items():
            if key in surface:
                raise ValueError("R134 cross-market execution collision")
            surface[key] = row

    overlap_keys = set(surface) & canonical_keys
    added_keys = set(surface) - canonical_keys
    added = tuple(
        surface[key]
        for key in sorted(
            added_keys,
            key=lambda key: (
                key[1],
                key[0],
                key[3],
                key[4],
            ),
        )
    )

    output_rows: list[dict[str, Any]] = []
    for row in added:
        outcome = _manage(
            row,
            bars=bars_by_symbol[row.symbol],
            opened=opened_by_symbol[row.symbol],
            end_date=end_date,
        )
        wrapper = SimpleNamespace(
            symbol=row.symbol,
            opportunity=SimpleNamespace(
                signal=SimpleNamespace(
                    side=row.side,
                    signal_at=row.signal_at,
                )
            ),
        )
        shared = r132._context(wrapper, states=states)
        output_rows.append(
            {
                "symbol": row.symbol,
                "side": row.side.value,
                "signal_at": row.signal_at.astimezone(UTC).isoformat(),
                "exited_at": outcome.exited_at.astimezone(UTC).isoformat(),
                "entry": str(row.entry),
                "stop": str(row.stop),
                "source_kind": row.source_kind,
                "exit_reason": outcome.exit_reason,
                "period": r133._period_label(
                    window_id=window_id,
                    exit_date=outcome.exited_at.astimezone(
                        r74._NY
                    ).date(),
                    start_date=start_date,
                    end_date=end_date,
                ),
                "raw_r": str(outcome.r_multiple),
                "primary_r": str(
                    outcome.r_multiple - PRIMARY_STRESS
                ),
                "secondary_r": str(
                    outcome.r_multiple - SECONDARY_STRESS
                ),
                **shared,
            }
        )

    expected_r98 = r98._window(
        roots=roots,
        window_id=window_id,
    )
    if len(surface) != int(expected_r98["exact_union_count"]):
        raise ValueError(f"R134 {window_id} R98 union drift")

    return {
        "window_id": window_id,
        "canonical_sample": expected,
        "r98_exact_union_sample": len(surface),
        "exact_overlap_with_canonical": len(overlap_keys),
        "added_only_sample": len(added),
        "hypothetical_exact_combined_density": (
            expected + len(added)
        ),
        "surface_by_market": surface_diag,
        "added_only_economics": _bundle(output_rows),
        "by_source_kind": _group(output_rows, "source_kind"),
        "by_competing_future": _group(output_rows, "future_state"),
        "by_broad_regime": _group(output_rows, "broad_regime"),
        "by_future_x_regime": _pair_group(output_rows),
        "by_period": _group(output_rows, "period"),
        "added_rows": output_rows,
        "provenance": provenance,
    }


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, Any]:
    if r133.IDENTITY != (
        "VT08_INDEX_R133_SHARED_R75_ADDED_DENSITY_ATTRIBUTION_001"
    ):
        raise ValueError("R134 R133 identity drift")
    if r98.IDENTITY != (
        "VT08_INDEX_R98_CROSS_H4_DYNAMIC_POI_LIFECYCLE_001"
    ):
        raise ValueError("R134 R98 identity drift")

    roots = {
        "NAS100": nas100_root,
        "SP500": sp500_root,
        "US30": us30_root,
    }
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "source_r133": {
            "run_id": SOURCE_R133_RUN_ID,
            "artifact_id": SOURCE_R133_ARTIFACT_ID,
            "artifact_digest": SOURCE_R133_ARTIFACT_DIGEST,
        },
        "replay_contract": {
            "source_surface": r98.IDENTITY,
            "target_r": str(TARGET_R),
            "stop": "R98_PROTECTED_SWING",
            "same_bar_ordering": "STOP_FIRST",
            "risk_allocator_applied": False,
            "primary_stress_r": str(PRIMARY_STRESS),
            "secondary_stress_r": str(SECONDARY_STRESS),
            "shared_context": r132.IDENTITY,
            "shared_classification_before_outcome_attachment": True,
            "canonical_overlap_removed_exactly": True,
            "fuzzy_dedup_used": False,
            "filter_selected": False,
            "candidate_selected": False,
        },
        "five_year": _window(roots=roots, window_id="5Y"),
        "recent_two_year": _window(roots=roots, window_id="2Y"),
        "r66_failed_holdout": _window(roots=roots, window_id="R66"),
        "decision": (
            "R134_R98_DYNAMIC_LIFECYCLE_ECONOMIC_REPLAY_COMPLETE_"
            "NO_CANDIDATE_SELECTED"
        ),
        "governance": {
            "research_only": True,
            "consumed_evidence_only": True,
            "fresh_holdout_claim": False,
            "risk_changed": False,
            "owner_anchors_changed": False,
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
                    "added": report["five_year"]["added_only_sample"],
                    "combined_density": report["five_year"][
                        "hypothetical_exact_combined_density"
                    ],
                    "secondary": report["five_year"][
                        "added_only_economics"
                    ]["secondary"],
                },
                "recent_two_year": {
                    "added": report["recent_two_year"]["added_only_sample"],
                    "combined_density": report["recent_two_year"][
                        "hypothetical_exact_combined_density"
                    ],
                    "secondary": report["recent_two_year"][
                        "added_only_economics"
                    ]["secondary"],
                },
                "r66": {
                    "added": report["r66_failed_holdout"][
                        "added_only_sample"
                    ],
                    "combined_density": report["r66_failed_holdout"][
                        "hypothetical_exact_combined_density"
                    ],
                    "secondary": report["r66_failed_holdout"][
                        "added_only_economics"
                    ]["secondary"],
                    "period": report["r66_failed_holdout"]["by_period"],
                },
                "decision": report["decision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
