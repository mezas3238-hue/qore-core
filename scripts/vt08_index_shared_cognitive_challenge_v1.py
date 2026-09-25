"""Shared cognitive challenge V1 against VT08 Index PR #604.

Purpose
-------
Measure Shared's own market intelligence against the current VT08 Index control
without allowing sizing to manufacture a better result.

Official benchmark:
- every trade is normalized to exactly 1.0 unit of initial risk;
- Shared never receives or reads the VT08 weight / risk budget;
- every canonical VT08 setup remains present (100% density);
- no entry is vetoed;
- no market, side, anchor or calendar period is removed;
- the Protected Swing stop and fixed 2.5R target geometry remain canonical;
- Shared may only choose the execution route for the SAME STANDARD setup:
  canonical continuation close vs the already-source-authorized continuation
  retest when that retest causally exists;
- TERMINAL_ADVERSE -> prefer retest when available;
- all other / conflicted / insufficient states -> canonical route.

The Shared decision is produced from closed M15 NAS100/SP500/US30 evidence at
the candidate signal time using the generic multi-horizon competing-futures
engine. Outcomes are read only after the route is frozen for evaluation.

This is consumed-evidence research only. It is not certification and it does
not reopen R66 as fresh.
"""
# ruff: noqa: E501
from __future__ import annotations

import argparse
import bisect
import json
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Sequence

from qore.infrastructure.core_stack_v2.competing_future_intelligence import (
    CausalHorizonSnapshot,
    CompetingFutureState,
    assess_competing_futures,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r58_exact_r47_distributed_risk as r58,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r74_ambiguous_bias_resolvers as r74,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r82_protected_swing_source_qualification as r82,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r89_execution_path_coverage as r89,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r102_source_confidence_risk_ablation as r102,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r107_standard_economic_root_attribution as r107,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r108_standard_source_retest_execution_replay as r108,
)

SCHEMA = "qore.shared.vt08_index.cognitive_challenge.v1"
IDENTITY = "QORE_SHARED_VT08_INDEX_COGNITIVE_CHALLENGE_V1"
VT08_PR = 604
VT08_HEAD = "5e307ff861df136b92d857693997d8fb950f4d79"
SHARED_SIZING_AUTHORITY = False
ZERO = Decimal("0")
ONE = Decimal("1")

# M15 causal horizons: 30m / 1h / 2h / 4h.
HORIZONS: tuple[tuple[int, int], ...] = (
    (30, 2),
    (60, 4),
    (120, 8),
    (240, 16),
)


def _clip(value: int) -> int:
    return max(0, min(10_000, value))


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _side_text(signal: object) -> str:
    return str(signal.side.value).lower()


def _signed_move(
    bars: Sequence[object],
    *,
    side: str,
) -> Decimal | None:
    if len(bars) < 2:
        return None
    high = max(_d(bar.high) for bar in bars)
    low = min(_d(bar.low) for bar in bars)
    span = high - low
    if span <= ZERO:
        return ZERO
    move = _d(bars[-1].close) - _d(bars[0].open)
    sign = ONE if side == "long" else -ONE
    return sign * move / span


def _support_bps(move: Decimal | None) -> int:
    if move is None:
        return 5000
    scaled = Decimal("5000") + move * Decimal("5000")
    return _clip(int(scaled))


def _recent_closed(
    bars: Sequence[object],
    closed: Sequence[datetime],
    *,
    decision_at: datetime,
    count: int,
) -> tuple[object, ...]:
    end = bisect.bisect_right(closed, decision_at)
    start = max(0, end - count)
    return tuple(bars[start:end])


def _body_persistence(
    bars: Sequence[object],
    *,
    side: str,
) -> tuple[int, int]:
    if not bars:
        return (5000, 5000)
    aligned = 0
    adverse = 0
    for bar in bars:
        move = _d(bar.close) - _d(bar.open)
        if side == "short":
            move = -move
        if move > ZERO:
            aligned += 1
        elif move < ZERO:
            adverse += 1
    n = len(bars)
    return (
        aligned * 10_000 // n,
        adverse * 10_000 // n,
    )


def _horizon_snapshot(
    *,
    symbol: str,
    side: str,
    decision_at: datetime,
    horizon_minutes: int,
    bar_count: int,
    bars_by_symbol: dict[str, Sequence[object]],
    closed_by_symbol: dict[str, tuple[datetime, ...]],
) -> CausalHorizonSnapshot:
    recent: dict[str, tuple[object, ...]] = {
        market: _recent_closed(
            bars_by_symbol[market],
            closed_by_symbol[market],
            decision_at=decision_at,
            count=bar_count,
        )
        for market in ("NAS100", "SP500", "US30")
    }
    local = recent[symbol]

    moves = {
        market: _signed_move(rows, side=side)
        for market, rows in recent.items()
    }
    supports = {
        market: _support_bps(move)
        for market, move in moves.items()
    }

    local_support = supports[symbol]
    peers = [
        supports[market]
        for market in ("NAS100", "SP500", "US30")
        if market != symbol
    ]
    cross_confirmation = sum(peers) // len(peers)
    market_support = (2 * local_support + cross_confirmation) // 3
    adversity = 10_000 - market_support

    half = max(2, len(local) // 2)
    early = tuple(local[:half])
    late = tuple(local[-half:])
    early_support = _support_bps(_signed_move(early, side=side))
    late_support = _support_bps(_signed_move(late, side=side))
    delta = late_support - early_support
    recovery_velocity = _clip(5000 + delta // 2)
    deterioration_velocity = 10_000 - recovery_velocity

    recovery_persistence, deterioration_persistence = _body_persistence(
        local,
        side=side,
    )

    cross_fragility = 10_000 - cross_confirmation
    structural_fragility = (
        adversity
        + deterioration_persistence
        + cross_fragility
    ) // 3

    dispersion = max(supports.values()) - min(supports.values())
    incomplete = sum(len(rows) < 2 for rows in recent.values())
    uncertainty = _clip(2500 + dispersion // 2 + incomplete * 1500)
    integrity = 10_000 if incomplete == 0 else 7000

    return CausalHorizonSnapshot(
        horizon_minutes=horizon_minutes,
        as_of=decision_at,
        evidence_count=max(1, len(local)),
        data_integrity_bps=integrity,
        support_bps=market_support,
        adversity_bps=adversity,
        deterioration_velocity_bps=deterioration_velocity,
        recovery_velocity_bps=recovery_velocity,
        deterioration_persistence_bps=deterioration_persistence,
        recovery_persistence_bps=recovery_persistence,
        cross_market_confirmation_bps=cross_confirmation,
        cross_market_fragility_bps=cross_fragility,
        structural_fragility_bps=structural_fragility,
        trend_support_bps=local_support,
        uncertainty_bps=uncertainty,
    )


def _shared_state(
    item: object,
    *,
    bars_by_symbol: dict[str, Sequence[object]],
    closed_by_symbol: dict[str, tuple[datetime, ...]],
) -> dict[str, object]:
    signal = item.opportunity.signal
    decision_at = signal.signal_at.astimezone(UTC)
    symbol = str(signal.symbol)
    side = _side_text(signal)

    snapshots = tuple(
        _horizon_snapshot(
            symbol=symbol,
            side=side,
            decision_at=decision_at,
            horizon_minutes=minutes,
            bar_count=count,
            bars_by_symbol=bars_by_symbol,
            closed_by_symbol=closed_by_symbol,
        )
        for minutes, count in HORIZONS
    )
    assessment = assess_competing_futures(snapshots)
    return {
        "state": assessment.state.value,
        "terminal_horizon_count": assessment.terminal_horizon_count,
        "recovery_horizon_count": assessment.recovery_horizon_count,
        "conflicted_horizon_count": assessment.conflicted_horizon_count,
        "terminal_evidence_bps": assessment.terminal_evidence_bps,
        "recovery_evidence_bps": assessment.recovery_evidence_bps,
        "separation_margin_bps": assessment.separation_margin_bps,
        "horizon_agreement_bps": assessment.horizon_agreement_bps,
        "confidence_bps": assessment.confidence_bps,
        "reasons": assessment.reasons,
    }


def _unitize(rows: Sequence[object]) -> tuple[object, ...]:
    return tuple(replace(item, weight=ONE) for item in rows)


def _delta(
    after: dict[str, Any],
    before: dict[str, Any],
    field: str,
) -> str:
    return str(_d(after[field]) - _d(before[field]))


def _window(
    *,
    roots: dict[str, Path],
    window_id: str,
) -> dict[str, object]:
    canonical, bars_raw, provenance = r74._load_window(
        roots=roots,
        window_id=window_id,
    )
    start_date, end_date, expected = r74._window_contract(window_id)
    bars_by_symbol: dict[str, Sequence[object]] = {
        symbol: tuple(rows)
        for symbol, rows in bars_raw.items()
    }
    opened_by_symbol = {
        symbol: tuple(
            bar.opened_at.astimezone(UTC)
            for bar in rows
        )
        for symbol, rows in bars_by_symbol.items()
    }
    closed_by_symbol = {
        symbol: tuple(
            bar.closed_at.astimezone(UTC)
            for bar in rows
        )
        for symbol, rows in bars_by_symbol.items()
    }

    base, _base_diag = r58._exact_r47(
        tuple(canonical),
        bars_by_symbol=bars_by_symbol,
    )
    control, _control_diag = r102._apply_confidence_policy(
        tuple(base),
        bars_by_symbol=bars_by_symbol,
        policy_id=r102.POLICY_EXPLICIT_FULL,
    )
    control = tuple(control)
    if len(control) != expected:
        raise ValueError(f"VT08 challenge {window_id} density drift")

    standard_ids = r107._standard_ids(
        control,
        bars_by_symbol=bars_by_symbol,
    )
    h4_cache = {
        symbol: r82._h4_bar_cache(rows)
        for symbol, rows in bars_by_symbol.items()
    }

    replayed: list[object] = []
    decisions: list[dict[str, object]] = []
    selected_retests = 0
    available_retests = 0
    terminal_without_retest = 0

    for item in control:
        cognition = _shared_state(
            item,
            bars_by_symbol=bars_by_symbol,
            closed_by_symbol=closed_by_symbol,
        )
        identity = item.opportunity.identity()
        signal = item.opportunity.signal
        route = "CANONICAL"

        if identity in standard_ids:
            inside = h4_cache[item.symbol].get(
                signal.h4_opened_at.astimezone(UTC)
            )
            if inside is None:
                raise ValueError("VT08 challenge canonical H4 not found")

            continuation_index = next(
                (
                    index
                    for index, bar in enumerate(inside)
                    if bar.closed_at.astimezone(UTC)
                    == signal.signal_at.astimezone(UTC)
                ),
                None,
            )
            if continuation_index is None or continuation_index <= 0:
                raise ValueError("VT08 challenge continuation bar not found")

            retest_index = r89._retest_fill_index(
                inside,
                continuation_index=continuation_index,
                side=signal.side,
                protected_swing=signal.protected_swing_extreme,
                model_kind=signal.model_kind,
                h4_open=inside[0].open,
            )
            if retest_index is not None:
                available_retests += 1

            if (
                cognition["state"]
                == CompetingFutureState.TERMINAL_ADVERSE.value
                and retest_index is not None
            ):
                retest_level = r89._continuation_breakout_level(
                    inside,
                    continuation_index=continuation_index,
                    side=signal.side,
                )
                fill_bar = inside[retest_index]
                new_signal = r108._build_retest_signal(
                    signal,
                    retest_level=retest_level,
                    retest_window_opened_at=fill_bar.opened_at,
                )
                new_outcome = r108._manage_retest(
                    new_signal,
                    fill_bar=fill_bar,
                    bars=bars_by_symbol[item.symbol],
                    opened=opened_by_symbol[item.symbol],
                )
                item = replace(
                    item,
                    opportunity=replace(
                        item.opportunity,
                        signal=new_signal,
                    ),
                    outcome=new_outcome,
                )
                route = "SHARED_TERMINAL_RETEST"
                selected_retests += 1
            elif (
                cognition["state"]
                == CompetingFutureState.TERMINAL_ADVERSE.value
                and retest_index is None
            ):
                terminal_without_retest += 1

        replayed.append(item)
        decisions.append(
            {
                "trade_id": item.trade_id,
                "symbol": item.symbol,
                "signal_at": signal.signal_at.astimezone(UTC).isoformat(),
                "shared": cognition,
                "route": route,
            }
        )

    replayed_tuple = tuple(replayed)
    if len(replayed_tuple) != len(control):
        raise ValueError("Shared VT08 challenge changed density")

    official_baseline_rows = _unitize(control)
    official_shared_rows = _unitize(replayed_tuple)
    if any(item.weight != ONE for item in official_shared_rows):
        raise ValueError("Shared official benchmark is not unit-R")

    baseline = r108._bundle(
        official_baseline_rows,
        bars_by_symbol=bars_by_symbol,
        opened_by_symbol=opened_by_symbol,
        window_id=window_id,
        start_date=start_date,
        end_date=end_date,
    )
    shared = r108._bundle(
        official_shared_rows,
        bars_by_symbol=bars_by_symbol,
        opened_by_symbol=opened_by_symbol,
        window_id=window_id,
        start_date=start_date,
        end_date=end_date,
    )

    # Secondary compatibility view only. It cannot establish Shared success.
    compatibility_baseline = r108._bundle(
        control,
        bars_by_symbol=bars_by_symbol,
        opened_by_symbol=opened_by_symbol,
        window_id=window_id,
        start_date=start_date,
        end_date=end_date,
    )
    compatibility_shared = r108._bundle(
        replayed_tuple,
        bars_by_symbol=bars_by_symbol,
        opened_by_symbol=opened_by_symbol,
        window_id=window_id,
        start_date=start_date,
        end_date=end_date,
    )

    primary_pf_up = (
        _d(shared["primary"]["profit_factor"] or 0)
        > _d(baseline["primary"]["profit_factor"] or 0)
    )
    secondary_pf_up = (
        _d(shared["secondary"]["profit_factor"] or 0)
        > _d(baseline["secondary"]["profit_factor"] or 0)
    )
    primary_dd_down = (
        _d(shared["primary_conservative_mtm"]["max_drawdown_r"])
        < _d(baseline["primary_conservative_mtm"]["max_drawdown_r"])
    )
    secondary_dd_down = (
        _d(shared["secondary_conservative_mtm"]["max_drawdown_r"])
        < _d(baseline["secondary_conservative_mtm"]["max_drawdown_r"])
    )

    state_counts: dict[str, int] = {}
    for row in decisions:
        state = str(row["shared"]["state"])
        state_counts[state] = state_counts.get(state, 0) + 1

    return {
        "window_id": window_id,
        "sample": len(control),
        "density_retained": "1",
        "canonical_expected": expected,
        "standard_sample": len(standard_ids),
        "available_retests": available_retests,
        "shared_selected_retests": selected_retests,
        "terminal_without_retest": terminal_without_retest,
        "shared_state_counts": dict(sorted(state_counts.items())),
        "official_unit_r": {
            "baseline": baseline,
            "shared": shared,
            "delta": {
                "primary_pf": _delta(
                    shared["primary"],
                    baseline["primary"],
                    "profit_factor",
                ),
                "secondary_pf": _delta(
                    shared["secondary"],
                    baseline["secondary"],
                    "profit_factor",
                ),
                "primary_total_r": _delta(
                    shared["primary"],
                    baseline["primary"],
                    "total_r",
                ),
                "secondary_total_r": _delta(
                    shared["secondary"],
                    baseline["secondary"],
                    "total_r",
                ),
                "primary_mtm_dd_r": str(
                    _d(shared["primary_conservative_mtm"]["max_drawdown_r"])
                    - _d(baseline["primary_conservative_mtm"]["max_drawdown_r"])
                ),
                "secondary_mtm_dd_r": str(
                    _d(shared["secondary_conservative_mtm"]["max_drawdown_r"])
                    - _d(baseline["secondary_conservative_mtm"]["max_drawdown_r"])
                ),
            },
            "gates": {
                "density_preserved": len(replayed_tuple) == len(control),
                "primary_pf_increased": primary_pf_up,
                "secondary_pf_increased": secondary_pf_up,
                "primary_dd_decreased": primary_dd_down,
                "secondary_dd_decreased": secondary_dd_down,
                "primary_total_r_not_lower": (
                    _d(shared["primary"]["total_r"])
                    >= _d(baseline["primary"]["total_r"])
                ),
                "secondary_total_r_not_lower": (
                    _d(shared["secondary"]["total_r"])
                    >= _d(baseline["secondary"]["total_r"])
                ),
            },
        },
        "compatibility_only_frozen_vt08_weights": {
            "success_claim_allowed": False,
            "baseline": compatibility_baseline,
            "shared": compatibility_shared,
        },
        "decisions": decisions,
        "provenance": provenance,
    }


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, object]:
    roots = {
        "NAS100": nas100_root,
        "SP500": sp500_root,
        "US30": us30_root,
    }
    five = _window(roots=roots, window_id="5Y")
    two = _window(roots=roots, window_id="2Y")
    r66 = _window(roots=roots, window_id="R66")

    development_windows = (five, two)
    official_pass = all(
        all(
            bool(value)
            for value in window["official_unit_r"]["gates"].values()
        )
        for window in development_windows
    )

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "challenge": {
            "trader": "VT08_INDEX",
            "source_pr": VT08_PR,
            "source_head": VT08_HEAD,
            "markets": ("NAS100", "SP500", "US30"),
            "shared_must_use_own_intelligence": True,
            "official_book": "UNIT_R_EQUAL_RISK_PER_OPPORTUNITY",
            "shared_sizing_authority": SHARED_SIZING_AUTHORITY,
            "shared_reads_vt08_weight": False,
            "shared_reads_risk_budget": False,
            "shared_changes_order_quantity": False,
            "shared_changes_position_size": False,
            "shared_capital_weighting": False,
            "entry_abstention": False,
            "signal_suppression": False,
            "market_removal": False,
            "side_removal": False,
            "anchor_removal": False,
            "calendar_filter": False,
            "same_setup_only": True,
            "density_must_be_preserved": True,
            "route_choice": (
                "TERMINAL_ADVERSE=>SOURCE_AUTHORIZED_RETEST_IF_AVAILABLE;"
                "OTHERWISE_CANONICAL"
            ),
            "density_expansion_attempted_in_batch_1": False,
            "density_expansion_reason": (
                "CURRENT_R131_CANONICAL_CONTROL_ALREADY_HAS_ZERO_SIGNAL_SUPPRESSION;"
                "BATCH_1_TESTS_COGNITIVE_QUALITY_WITH_100_PERCENT_DENSITY"
            ),
        },
        "five_year": five,
        "recent_two_year": two,
        "r66_consumed_failed_holdout": r66,
        "batch_1_pass": official_pass,
        "decision": (
            "SHARED_VT08_BATCH_1_PASSED"
            if official_pass
            else "SHARED_VT08_BATCH_1_FALSIFIED_OR_INCOMPLETE"
        ),
        "governance": {
            "research_only": True,
            "consumed_evidence_only": True,
            "r66_reopened_as_fresh": False,
            "fresh_holdout_opened": False,
            "candidate_certified": False,
            "merge_authorized": False,
            "live_authorized": False,
            "production_authorized": False,
            "real_capital_authorized": False,
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

    def compact(section: dict[str, object]) -> dict[str, object]:
        official = section["official_unit_r"]
        return {
            "sample": section["sample"],
            "shared_state_counts": section["shared_state_counts"],
            "available_retests": section["available_retests"],
            "shared_selected_retests": section["shared_selected_retests"],
            "delta": official["delta"],
            "gates": official["gates"],
            "baseline_primary": official["baseline"]["primary"],
            "shared_primary": official["shared"]["primary"],
            "baseline_primary_mtm": official["baseline"][
                "primary_conservative_mtm"
            ],
            "shared_primary_mtm": official["shared"][
                "primary_conservative_mtm"
            ],
        }

    print(
        json.dumps(
            {
                "identity": IDENTITY,
                "five_year": compact(report["five_year"]),
                "recent_two_year": compact(report["recent_two_year"]),
                "r66": compact(report["r66_consumed_failed_holdout"]),
                "batch_1_pass": report["batch_1_pass"],
                "decision": report["decision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
