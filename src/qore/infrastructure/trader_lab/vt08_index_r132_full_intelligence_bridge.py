"""VT08 Index R132 — full-intelligence causal bridge and density atlas.

R123-R131 showed that local risk/entry/target ablations cannot solve the Owner's
joint objective because they preserve the same canonical opportunity set.
R132 changes architecture, not trading rules:

1. Reuse exact generic Shared/Core perception and competing-futures modules
   from PR #635 at a pinned source HEAD.
2. Translate those generic market facts through a VT08-specific adapter without
   giving Shared order/risk/sizing/entry/stop/target authority.
3. Attribute the frozen R102 canonical stream by Shared regime and
   multi-horizon competing-future state.
4. Re-open density research by reporting two already source-valid expansion
   surfaces side-by-side:
   - strict cross-index ambiguous-bias consensus (R75), and
   - cross-H4 dynamic Protected-Swing / POI lifecycle (R98).

R132 is an attribution/architecture bridge. It does not select a filter,
candidate or runtime policy. All classifications are decision-time causal and
use no trade outcome or PnL.
"""

from __future__ import annotations

import argparse
import json
from bisect import bisect_right
from collections import defaultdict
from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.core_stack_v2.competing_future_intelligence import (
    CausalHorizonSnapshot,
    assess_competing_futures,
)
from qore.infrastructure.core_stack_v2.perception_engine import (
    PerceptionBar,
    infer_situation,
    perceive_market,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r58_exact_r47_distributed_risk as r58,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r74_ambiguous_bias_resolvers as r74,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r75_cross_index_ambiguous_bias_consensus as r75,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r98_cross_h4_dynamic_poi_lifecycle as r98,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r102_source_confidence_risk_ablation as r102,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    Vt08IndexC2R1Bar,
)

SCHEMA = "qore.trader_lab.vt08_index_r132_full_intelligence_bridge.v1"
IDENTITY = "VT08_INDEX_R132_FULL_INTELLIGENCE_CAUSAL_BRIDGE_001"

SHARED_SOURCE_PR = 635
SHARED_SOURCE_HEAD = "0429fbe210246f04e1b572191737e86a490781fc"
SHARED_SNAPSHOT_FILES = {
    "architecture_freeze.py": "ffbb102be42e6a4a53307622873b8a3a46e98555",
    "perception_engine.py": "696cf267a5f2e17ae40cdb7b322a7e6be9612d32",
    "competing_future_intelligence.py": "f6e2624100c8457e9c7c79dc35b12c79e51e9bd8",
    "market_state_intelligence.py": "bf869db2a83569e69bfe561ea165d3b68a5669c4",
}
HORIZON_BARS = ((60, 4), (240, 16), (960, 64))
EXPECTED_CANONICAL = {"5Y": 2448, "2Y": 1017, "R66": 773}


def _shared_bar(bar: Vt08IndexC2R1Bar) -> PerceptionBar:
    return PerceptionBar(
        opened_at=bar.opened_at.astimezone(UTC).isoformat(),
        closed_at=bar.closed_at.astimezone(UTC).isoformat(),
        open=bar.open,
        high=bar.high,
        low=bar.low,
        close=bar.close,
    )


def _closed_before(
    bars: Sequence[Vt08IndexC2R1Bar],
    closed_times: Sequence[datetime],
    *,
    as_of: datetime,
    count: int,
) -> tuple[Vt08IndexC2R1Bar, ...]:
    index = bisect_right(closed_times, as_of.astimezone(UTC))
    return tuple(bars[max(0, index - count):index])


def _clamp_bps(value: Decimal) -> int:
    return int(max(Decimal(), min(Decimal("1"), value)) * Decimal("10000"))


def _direction(
    bars: Sequence[Vt08IndexC2R1Bar],
) -> int:
    if not bars:
        return 0
    if bars[-1].close > bars[0].open:
        return 1
    if bars[-1].close < bars[0].open:
        return -1
    return 0


def _side_sign(side: DemoTradingSetupSide) -> int:
    return 1 if side is DemoTradingSetupSide.LONG else -1


def _peer_bps(
    *,
    target_symbol: str,
    side: DemoTradingSetupSide,
    as_of: datetime,
    count: int,
    states: dict[str, tuple[
        Sequence[Vt08IndexC2R1Bar],
        Sequence[datetime],
    ]],
) -> tuple[int, int]:
    expected = _side_sign(side)
    votes: list[int] = []
    for symbol, (bars, closed) in states.items():
        if symbol == target_symbol:
            continue
        sample = _closed_before(
            bars,
            closed,
            as_of=as_of,
            count=count,
        )
        if len(sample) < max(2, count // 2):
            continue
        votes.append(int(_direction(sample) == expected))
    if not votes:
        return 5000, 5000
    confirmation = sum(votes) * 10000 // len(votes)
    return confirmation, 10000 - confirmation


def _horizon_snapshot(
    *,
    symbol: str,
    side: DemoTradingSetupSide,
    as_of: datetime,
    horizon_minutes: int,
    count: int,
    states: dict[str, tuple[
        Sequence[Vt08IndexC2R1Bar],
        Sequence[datetime],
    ]],
) -> tuple[CausalHorizonSnapshot, dict[str, Any]]:
    bars, closed = states[symbol]
    sample = _closed_before(
        bars,
        closed,
        as_of=as_of,
        count=count,
    )
    if len(sample) < max(3, count // 2):
        raise ValueError(
            f"R132 insufficient {horizon_minutes}m history for {symbol}"
        )

    perception_bars = tuple(_shared_bar(bar) for bar in sample)
    current = perceive_market(
        perception_bars,
        as_of=as_of.astimezone(UTC).isoformat(),
        short_window=min(5, len(perception_bars)),
        long_window=len(perception_bars),
    )
    previous = None
    if len(perception_bars) >= 4:
        prior_bars = perception_bars[:-1]
        previous = perceive_market(
            prior_bars,
            as_of=prior_bars[-1].closed_at,
            short_window=min(5, len(prior_bars)),
            long_window=len(prior_bars),
        )
    situation = infer_situation(current, previous=previous)

    trend = _clamp_bps(situation.trend_pressure)
    range_bps = _clamp_bps(situation.range_pressure)
    expansion = _clamp_bps(situation.expansion_pressure)
    exhaustion = _clamp_bps(situation.exhaustion_pressure)
    uncertainty = _clamp_bps(situation.uncertainty_pressure)
    aligned = _direction(sample) * _side_sign(side)

    if aligned > 0:
        support = min(10000, trend + expansion // 2)
        adversity = min(10000, max(range_bps, exhaustion))
        recovery_velocity = min(10000, expansion + trend // 2)
        deterioration_velocity = max(exhaustion, range_bps // 2)
        recovery_persistence = trend
        deterioration_persistence = range_bps
    elif aligned < 0:
        support = max(0, expansion // 3)
        adversity = min(10000, trend + max(exhaustion, range_bps // 2))
        recovery_velocity = expansion // 2
        deterioration_velocity = min(10000, trend + exhaustion // 2)
        recovery_persistence = max(0, 10000 - trend)
        deterioration_persistence = trend
    else:
        support = expansion // 2
        adversity = max(range_bps, exhaustion)
        recovery_velocity = expansion // 2
        deterioration_velocity = max(range_bps, exhaustion)
        recovery_persistence = 5000
        deterioration_persistence = 5000

    peer_confirm, peer_fragility = _peer_bps(
        target_symbol=symbol,
        side=side,
        as_of=as_of,
        count=count,
        states=states,
    )
    snapshot = CausalHorizonSnapshot(
        horizon_minutes=horizon_minutes,
        as_of=as_of.astimezone(UTC),
        evidence_count=len(sample),
        data_integrity_bps=10000,
        support_bps=support,
        adversity_bps=adversity,
        deterioration_velocity_bps=deterioration_velocity,
        recovery_velocity_bps=recovery_velocity,
        deterioration_persistence_bps=deterioration_persistence,
        recovery_persistence_bps=recovery_persistence,
        cross_market_confirmation_bps=peer_confirm,
        cross_market_fragility_bps=peer_fragility,
        structural_fragility_bps=max(range_bps, exhaustion),
        trend_support_bps=(trend if aligned > 0 else 0),
        uncertainty_bps=uncertainty,
    )
    return snapshot, {
        "horizon_minutes": horizon_minutes,
        "regime": situation.regime,
        "transition": situation.transition,
        "structure_state": current.structure_state,
        "volatility_state": current.volatility_state,
        "momentum_state": current.momentum_state,
        "anomaly_flags": list(current.anomaly_flags),
        "trend_pressure_bps": trend,
        "range_pressure_bps": range_bps,
        "expansion_pressure_bps": expansion,
        "exhaustion_pressure_bps": exhaustion,
        "uncertainty_bps": uncertainty,
        "cross_market_confirmation_bps": peer_confirm,
        "cross_market_fragility_bps": peer_fragility,
    }


def _context(
    item: Any,
    *,
    states: dict[str, tuple[
        Sequence[Vt08IndexC2R1Bar],
        Sequence[datetime],
    ]],
) -> dict[str, Any]:
    signal = item.opportunity.signal
    horizon_rows: list[dict[str, Any]] = []
    snapshots: list[CausalHorizonSnapshot] = []
    for minutes, count in HORIZON_BARS:
        snapshot, row = _horizon_snapshot(
            symbol=item.symbol,
            side=signal.side,
            as_of=signal.signal_at,
            horizon_minutes=minutes,
            count=count,
            states=states,
        )
        snapshots.append(snapshot)
        horizon_rows.append(row)
    futures = assess_competing_futures(tuple(snapshots))
    broad = horizon_rows[-1]
    return {
        "future_state": futures.state.value,
        "future_confidence_bps": futures.confidence_bps,
        "future_terminal_evidence_bps": futures.terminal_evidence_bps,
        "future_recovery_evidence_bps": futures.recovery_evidence_bps,
        "future_separation_margin_bps": futures.separation_margin_bps,
        "broad_regime": broad["regime"],
        "broad_transition": broad["transition"],
        "broad_structure_state": broad["structure_state"],
        "broad_volatility_state": broad["volatility_state"],
        "broad_momentum_state": broad["momentum_state"],
        "broad_cross_market_confirmation_bps": broad[
            "cross_market_confirmation_bps"
        ],
        "horizons": horizon_rows,
    }


def _metrics(rows: Sequence[dict[str, Any]], field: str) -> dict[str, Any]:
    values = tuple(Decimal(str(row[field])) for row in rows)
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
    return {
        "sample": len(values),
        "wins": sum(value > 0 for value in values),
        "losses": sum(value < 0 for value in values),
        "total_r": str(sum(values, Decimal())),
        "profit_factor": str(gains / losses) if losses else None,
        "max_drawdown_r": str(drawdown),
        "max_losing_streak": max_streak,
    }


def _group(
    rows: Sequence[dict[str, Any]],
    field: str,
) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row[field])].append(row)
    return {
        key: {
            "primary": _metrics(items, "primary_r"),
            "secondary": _metrics(items, "secondary_r"),
        }
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
    _start, _end, expected = r74._window_contract(window_id)
    if expected != EXPECTED_CANONICAL[window_id]:
        raise ValueError(f"R132 {window_id} canonical contract drift")

    bars_by_symbol: dict[
        str, Sequence[Vt08IndexC2R1Bar]
    ] = {
        symbol: tuple(bars)
        for symbol, bars in bars_raw.items()
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

    base, _base_diag = r58._exact_r47(
        tuple(canonical),
        bars_by_symbol=bars_by_symbol,
    )
    control, control_diag = r102._apply_confidence_policy(
        tuple(base),
        bars_by_symbol=bars_by_symbol,
        policy_id=r102.POLICY_EXPLICIT_FULL,
    )
    control = tuple(control)
    if len(control) != expected:
        raise ValueError(f"R132 {window_id} control density drift")

    rows: list[dict[str, Any]] = []
    for item in control:
        context = _context(item, states=states)
        rows.append(
            {
                "trade_id": item.trade_id,
                "symbol": item.symbol,
                "signal_at": item.opportunity.signal.signal_at
                .astimezone(UTC)
                .isoformat(),
                "side": item.opportunity.signal.side.value,
                "primary_r": str(
                    (
                        item.outcome.r_multiple
                        - r102.PRIMARY_STRESS
                    )
                    * item.weight
                ),
                "secondary_r": str(
                    (
                        item.outcome.r_multiple
                        - r102.SECONDARY_STRESS
                    )
                    * item.weight
                ),
                **context,
            }
        )

    peer_density = r75._window(
        roots=roots,
        window_id=window_id,
    )
    lifecycle_density = r98._window(
        roots=roots,
        window_id=window_id,
    )

    return {
        "window_id": window_id,
        "canonical_sample": expected,
        "shared_context_sample": len(rows),
        "control_policy": r102.POLICY_EXPLICIT_FULL,
        "control_diagnostics": control_diag,
        "by_competing_future": _group(rows, "future_state"),
        "by_broad_regime": _group(rows, "broad_regime"),
        "by_broad_transition": _group(rows, "broad_transition"),
        "density_reopening": {
            "canonical_signal_reference": expected,
            "cross_index_ambiguous_bias": {
                "added_signals": peer_density["added_consensus_signals"],
                "hypothetical_combined_sample": peer_density[
                    "hypothetical_combined_sample"
                ],
                "secondary": peer_density["secondary"],
                "all_secondary_blocks_positive": peer_density[
                    "all_secondary_blocks_positive"
                ],
            },
            "cross_h4_dynamic_lifecycle": {
                "same_h4_source_exact_executions": lifecycle_density[
                    "same_h4_source_exact_executions"
                ],
                "cross_h4_dynamic_lifecycle_executions": lifecycle_density[
                    "cross_h4_dynamic_lifecycle_executions"
                ],
                "exact_union_count": lifecycle_density["exact_union_count"],
                "density_pass": lifecycle_density["density_pass"],
            },
            "surfaces_are_not_summed_without_exact_dedup": True,
        },
        "provenance": provenance,
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
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "shared_source": {
            "pr": SHARED_SOURCE_PR,
            "head": SHARED_SOURCE_HEAD,
            "exact_blob_snapshot": SHARED_SNAPSHOT_FILES,
        },
        "adapter_contract": {
            "shared_core_is_context_only": True,
            "vt08_methodology_sovereign": True,
            "qore_risk_sovereign": True,
            "shared_order_authority": False,
            "shared_risk_authority": False,
            "shared_sizing_authority": False,
            "shared_entry_authority": False,
            "shared_stop_authority": False,
            "shared_target_authority": False,
            "classification_cutoff": "SIGNAL_AT",
            "trade_outcome_used_for_classification": False,
            "pnl_used_for_classification": False,
            "cross_index_context_used": True,
            "multi_horizon_context_used": True,
            "density_research_reopened": True,
        },
        "five_year": _window(roots=roots, window_id="5Y"),
        "recent_two_year": _window(roots=roots, window_id="2Y"),
        "r66_failed_holdout": _window(roots=roots, window_id="R66"),
        "decision": (
            "R132_FULL_INTELLIGENCE_BRIDGE_COMPLETE_"
            "NO_FILTER_OR_CANDIDATE_SELECTED"
        ),
        "governance": {
            "research_only": True,
            "consumed_evidence_only": True,
            "fresh_holdout_claim": False,
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
                    "future": report["five_year"]["by_competing_future"],
                    "density": report["five_year"]["density_reopening"],
                },
                "recent_two_year": {
                    "future": report["recent_two_year"]["by_competing_future"],
                    "density": report["recent_two_year"]["density_reopening"],
                },
                "r66": {
                    "future": report["r66_failed_holdout"][
                        "by_competing_future"
                    ],
                    "density": report["r66_failed_holdout"][
                        "density_reopening"
                    ],
                },
                "decision": report["decision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
