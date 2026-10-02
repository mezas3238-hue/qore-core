"""Shared cognitive challenge V2 diagnostic against VT08 Index PR #604.

V1 proved that preserving density while routing only TERMINAL_ADVERSE signals to
an already-authorized retest produced essentially zero economic delta. V2 does
not add another execution rule. It tests the next root hypothesis first:

    scalar/relational compression hid the causal geometry that separates
    terminal deterioration from recoverable adversity.

The V2 classifier is built only from closed M15 NAS100/SP500/US30 bars observable
at the VT08 signal time. It uses Shared's generic multi-axis future-geometry
engine and freezes the state before reading the trade outcome.

No sizing, capital weighting, abstention, signal suppression, market removal,
calendar filtering, stop/target mutation, trailing, target extension or fresh
holdout is used. VT08 methodology remains owned by PR #604.
"""
# ruff: noqa: E501
from __future__ import annotations

import argparse
import bisect
import json
from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.core_stack_v2.future_geometry_intelligence import (
    FutureGeometryState,
    assess_future_geometry,
    build_horizon_geometry,
)
from qore.infrastructure.core_stack_v2.transition_intelligence import (
    MarketTransitionObservation,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r58_exact_r47_distributed_risk as r58,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r74_ambiguous_bias_resolvers as r74,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r102_source_confidence_risk_ablation as r102,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r108_standard_source_retest_execution_replay as r108,
)

SCHEMA = "qore.shared.vt08_index.cognitive_challenge.v2"
IDENTITY = "QORE_SHARED_VT08_INDEX_COGNITIVE_CHALLENGE_V2"
VT08_PR = 604
VT08_HEAD = "5e307ff861df136b92d857693997d8fb950f4d79"
ZERO = Decimal("0")
ONE = Decimal("1")
MARKETS = ("NAS100", "SP500", "US30")
HORIZONS: tuple[tuple[int, int], ...] = (
    (30, 2),
    (60, 4),
    (120, 8),
    (240, 16),
)
OBSERVATION_HISTORY = 16


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _clip(value: int) -> int:
    return max(0, min(10_000, value))


def _side_text(item: object) -> str:
    return str(item.opportunity.signal.side.value).lower()


def _recent_asof(
    bars: Sequence[object],
    closed: Sequence[datetime],
    *,
    as_of: datetime,
    count: int,
) -> tuple[object, ...]:
    end = bisect.bisect_right(closed, as_of)
    return tuple(bars[max(0, end - count):end])


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
    raw = (_d(bars[-1].close) - _d(bars[0].open)) / span
    signed = raw if side == "long" else -raw
    return max(Decimal("-1"), min(ONE, signed))


def _support_bps(value: Decimal | None) -> int:
    if value is None:
        return 5000
    return _clip(int(Decimal("5000") + value * Decimal("5000")))


def _adverse_bps(value: Decimal | None) -> int:
    return 10_000 - _support_bps(value)


def _sign(value: Decimal | None) -> int | None:
    if value is None:
        return None
    if value > ZERO:
        return 1
    if value < ZERO:
        return -1
    return 0


def _sign_stability(short: Decimal | None, long: Decimal | None) -> int:
    if short is None or long is None:
        return 5000
    a = _sign(short)
    b = _sign(long)
    if a == 0 or b == 0:
        return 6500
    return 8500 if a == b else 3500


def _correlation_stability(values: Sequence[Decimal | None]) -> int:
    signs = tuple(_sign(value) for value in values if value is not None)
    if len(signs) < 3:
        return 5000
    positive = sum(value is not None and value > 0 for value in signs)
    negative = sum(value is not None and value < 0 for value in signs)
    dominant = max(positive, negative)
    if dominant == len(signs):
        return 9000
    if dominant >= len(signs) - 1:
        return 7000
    return 3500


def _dispersion_bps(values: Sequence[int]) -> int:
    if not values:
        return 0
    return max(values) - min(values)


def _observation(
    *,
    symbol: str,
    side: str,
    as_of: datetime,
    bars_by_symbol: dict[str, Sequence[object]],
    closed_by_symbol: dict[str, tuple[datetime, ...]],
) -> MarketTransitionObservation:
    short_moves: dict[str, Decimal | None] = {}
    long_moves: dict[str, Decimal | None] = {}
    short_support: dict[str, int] = {}
    long_support: dict[str, int] = {}

    for market in MARKETS:
        short_rows = _recent_asof(
            bars_by_symbol[market],
            closed_by_symbol[market],
            as_of=as_of,
            count=3,
        )
        long_rows = _recent_asof(
            bars_by_symbol[market],
            closed_by_symbol[market],
            as_of=as_of,
            count=10,
        )
        short_moves[market] = _signed_move(short_rows, side=side)
        long_moves[market] = _signed_move(long_rows, side=side)
        short_support[market] = _support_bps(short_moves[market])
        long_support[market] = _support_bps(long_moves[market])

    peers = tuple(market for market in MARKETS if market != symbol)
    peer_short = sum(short_support[market] for market in peers) // len(peers)
    peer_long = sum(long_support[market] for market in peers) // len(peers)
    cross_confirmation = (peer_short + peer_long) // 2

    local_short = short_support[symbol]
    local_long = long_support[symbol]
    trend_support = (local_long + local_short + peer_long) // 3
    momentum = (local_short + peer_short) // 2
    displacement = local_short

    volatility_stability = _sign_stability(
        short_moves[symbol],
        long_moves[symbol],
    )
    correlation_stability = (
        _correlation_stability(tuple(short_moves.values()))
        + _correlation_stability(tuple(long_moves.values()))
    ) // 2

    breadth_adverse = max(
        10_000 - sum(short_support.values()) // len(MARKETS),
        10_000 - sum(long_support.values()) // len(MARKETS),
    )
    contradiction = max(
        breadth_adverse,
        10_000 - volatility_stability,
        10_000 - correlation_stability,
    )

    local_reversal = (
        _sign(short_moves[symbol]) not in {None, 0}
        and _sign(long_moves[symbol]) not in {None, 0}
        and _sign(short_moves[symbol]) != _sign(long_moves[symbol])
    )
    dispersion = max(
        _dispersion_bps(tuple(short_support.values())),
        _dispersion_bps(tuple(long_support.values())),
    )
    anomaly = 7000 if local_reversal else 2500
    if dispersion >= 4000:
        anomaly = max(anomaly, 6500)

    complete = all(
        value is not None
        for value in (*short_moves.values(), *long_moves.values())
    )
    uncertainty = 2500 if complete else 7000
    if dispersion >= 3000:
        uncertainty = max(uncertainty, 5500)

    opposite_pressure = max(
        _adverse_bps(short_moves[symbol]),
        _adverse_bps(long_moves[symbol]),
        breadth_adverse,
    )

    return MarketTransitionObservation(
        as_of=as_of.astimezone(UTC),
        data_integrity_bps=10_000 if complete else 7000,
        trend_support_bps=trend_support,
        momentum_bps=momentum,
        displacement_bps=displacement,
        # VT08 M15 source evidence has no generic causal liquidity-capacity
        # primitive. Keep the axis neutral rather than manufacture information.
        liquidity_capacity_bps=5000,
        volatility_stability_bps=volatility_stability,
        cross_market_confirmation_bps=cross_confirmation,
        correlation_stability_bps=correlation_stability,
        contradiction_bps=contradiction,
        anomaly_bps=anomaly,
        uncertainty_bps=uncertainty,
        opposite_pressure_bps=opposite_pressure,
    )


def _shared_geometry(
    item: object,
    *,
    bars_by_symbol: dict[str, Sequence[object]],
    closed_by_symbol: dict[str, tuple[datetime, ...]],
) -> dict[str, object]:
    signal = item.opportunity.signal
    decision_at = signal.signal_at.astimezone(UTC)
    symbol = str(signal.symbol)
    side = _side_text(item)

    local_closed = closed_by_symbol[symbol]
    end = bisect.bisect_right(local_closed, decision_at)
    observation_times = local_closed[max(0, end - OBSERVATION_HISTORY):end]
    history = tuple(
        _observation(
            symbol=symbol,
            side=side,
            as_of=as_of,
            bars_by_symbol=bars_by_symbol,
            closed_by_symbol=closed_by_symbol,
        )
        for as_of in observation_times
    )

    geometries = tuple(
        build_horizon_geometry(
            history[-min(count, len(history)):],
            horizon_minutes=minutes,
        )
        for minutes, count in HORIZONS
        if len(history) >= 2
    )
    if len(geometries) < 2:
        return {
            "state": FutureGeometryState.INSUFFICIENT.value,
            "history_observations": len(history),
            "horizons_available": tuple(
                geometry.horizon_minutes for geometry in geometries
            ),
            "assessment": None,
        }

    assessment = assess_future_geometry(geometries)
    return {
        "state": assessment.state.value,
        "history_observations": len(history),
        "horizons_available": tuple(
            geometry.horizon_minutes for geometry in assessment.horizons
        ),
        "assessment": {
            "collapse_horizon_count": assessment.collapse_horizon_count,
            "recovery_horizon_count": assessment.recovery_horizon_count,
            "resilient_horizon_count": assessment.resilient_horizon_count,
            "conflicted_horizon_count": assessment.conflicted_horizon_count,
            "broad_state": assessment.broad_state.value,
            "fast_state": assessment.fast_state.value,
            "structural_agreement_bps": assessment.structural_agreement_bps,
            "reasons": assessment.reasons,
            "horizons": tuple(
                {
                    "horizon_minutes": geometry.horizon_minutes,
                    "state": geometry.state.value,
                    "supportive_level_count": geometry.supportive_level_count,
                    "adverse_level_count": geometry.adverse_level_count,
                    "support_improving_count": geometry.support_improving_count,
                    "support_weakening_count": geometry.support_weakening_count,
                    "adversity_rising_count": geometry.adversity_rising_count,
                    "adversity_falling_count": geometry.adversity_falling_count,
                    "recovery_core_count": geometry.recovery_core_count,
                    "terminal_core_count": geometry.terminal_core_count,
                }
                for geometry in assessment.horizons
            ),
        },
    }


def _unitize(rows: Sequence[object]) -> tuple[object, ...]:
    return tuple(replace(item, weight=ONE) for item in rows)


def _primary(bundle: dict[str, Any]) -> dict[str, Any]:
    return dict(bundle["primary"])


def _state_diagnostics(
    rows_by_state: dict[str, list[object]],
) -> dict[str, object]:
    result: dict[str, object] = {}
    for state in sorted(rows_by_state):
        rows = tuple(rows_by_state[state])
        bundle = r108._cohort_bundle(rows)
        result[state] = {
            "sample": len(rows),
            "primary": bundle["primary"],
            "secondary": bundle["secondary"],
        }
    return result


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
        symbol: tuple(bar.opened_at.astimezone(UTC) for bar in rows)
        for symbol, rows in bars_by_symbol.items()
    }
    closed_by_symbol = {
        symbol: tuple(bar.closed_at.astimezone(UTC) for bar in rows)
        for symbol, rows in bars_by_symbol.items()
    }

    base, _ = r58._exact_r47(
        tuple(canonical),
        bars_by_symbol=bars_by_symbol,
    )
    control, _ = r102._apply_confidence_policy(
        tuple(base),
        bars_by_symbol=bars_by_symbol,
        policy_id=r102.POLICY_EXPLICIT_FULL,
    )
    control = _unitize(tuple(control))
    if len(control) != expected:
        raise ValueError(f"VT08 V2 {window_id} density drift")

    decisions: list[dict[str, object]] = []
    rows_by_state: dict[str, list[object]] = defaultdict(list)

    for item in control:
        cognition = _shared_geometry(
            item,
            bars_by_symbol=bars_by_symbol,
            closed_by_symbol=closed_by_symbol,
        )
        state = str(cognition["state"])
        rows_by_state[state].append(item)
        decisions.append(
            {
                "trade_id": item.trade_id,
                "symbol": item.symbol,
                "signal_at": item.opportunity.signal.signal_at.astimezone(
                    UTC
                ).isoformat(),
                "state": state,
                "history_observations": cognition["history_observations"],
                "horizons_available": cognition["horizons_available"],
                "assessment": cognition["assessment"],
            }
        )

    baseline = r108._bundle(
        control,
        bars_by_symbol=bars_by_symbol,
        opened_by_symbol=opened_by_symbol,
        window_id=window_id,
        start_date=start_date,
        end_date=end_date,
    )
    diagnostics = _state_diagnostics(rows_by_state)
    state_counts = dict(sorted(Counter(row["state"] for row in decisions).items()))

    terminal = diagnostics.get(FutureGeometryState.TERMINAL_COLLAPSE.value)
    supportive = diagnostics.get(
        FutureGeometryState.SUPPORTIVE_CONTINUATION.value
    )
    recoverable = diagnostics.get(
        FutureGeometryState.RECOVERABLE_ADVERSITY.value
    )

    baseline_pf = _d(baseline["primary"]["profit_factor"] or 0)

    def pf_less(section: object) -> bool | None:
        if section is None:
            return None
        return _d(section["primary"]["profit_factor"] or 0) < baseline_pf

    def pf_greater(section: object) -> bool | None:
        if section is None:
            return None
        return _d(section["primary"]["profit_factor"] or 0) > baseline_pf

    return {
        "window_id": window_id,
        "sample": len(control),
        "canonical_expected": expected,
        "density_retained": "1",
        "baseline": baseline,
        "state_counts": state_counts,
        "state_diagnostics": diagnostics,
        "hypothesis_checks": {
            "terminal_pf_below_window_baseline": pf_less(terminal),
            "supportive_pf_above_window_baseline": pf_greater(supportive),
            "recoverable_pf_above_window_baseline": pf_greater(recoverable),
            "terminal_state_observed": terminal is not None,
            "supportive_state_observed": supportive is not None,
        },
        "decisions": decisions,
        "provenance": provenance,
    }


def _contradiction_map(
    windows: dict[str, dict[str, object]],
) -> dict[str, object]:
    states = tuple(state.value for state in FutureGeometryState)
    result: dict[str, object] = {}
    for state in states:
        rows: dict[str, object] = {}
        for name, window in windows.items():
            section = window["state_diagnostics"].get(state)
            rows[name] = (
                {
                    "sample": 0,
                    "primary_profit_factor": None,
                    "primary_total_r": "0",
                    "primary_max_drawdown_r": "0",
                }
                if section is None
                else {
                    "sample": section["sample"],
                    "primary_profit_factor": section["primary"]["profit_factor"],
                    "primary_total_r": section["primary"]["total_r"],
                    "primary_max_drawdown_r": section["primary"]["max_drawdown_r"],
                }
            )
        result[state] = rows
    return result


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
    windows = {
        "five_year": _window(roots=roots, window_id="5Y"),
        "recent_two_year": _window(roots=roots, window_id="2Y"),
        "r66_consumed_failed_holdout": _window(roots=roots, window_id="R66"),
    }

    development = (
        windows["five_year"],
        windows["recent_two_year"],
    )
    cross_window_discrimination = all(
        window["hypothesis_checks"]["terminal_state_observed"]
        and window["hypothesis_checks"]["terminal_pf_below_window_baseline"]
        for window in development
    )

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "challenge": {
            "trader": "VT08_INDEX",
            "source_pr": VT08_PR,
            "source_head": VT08_HEAD,
            "shared_pr": 635,
            "markets": MARKETS,
            "official_book": "UNIT_R_EQUAL_RISK_PER_OPPORTUNITY",
            "diagnostic_only": True,
            "execution_route_changed": False,
            "entry_abstention": False,
            "signal_suppression": False,
            "market_removal": False,
            "side_removal": False,
            "anchor_removal": False,
            "calendar_filter": False,
            "sizing_used": False,
            "capital_weighting_used": False,
            "stop_geometry_mutated": False,
            "target_geometry_mutated": False,
            "trailing_used": False,
            "target_extension_used": False,
            "density_must_be_preserved": True,
            "outcome_used_by_classifier": False,
            "outcome_read_only_after_state_frozen": True,
            "numeric_threshold_grid_search": False,
            "future_market_input_used": False,
        },
        **windows,
        "contradiction_map": _contradiction_map(windows),
        "root_cause_model": {
            "v1_falsification": (
                "SCALAR_RELATIONAL_COMPETING_FUTURES_WAS_TOO_COARSE_AND_ROUTED "
                "TOO_FEW_TRADES_TO_CHANGE_ECONOMICS"
            ),
            "v2_hypothesis": (
                "MULTI_AXIS_CAUSAL_GEOMETRY_CAN_SEPARATE_TERMINAL_COLLAPSE_FROM "
                "RECOVERABLE_OR_SUPPORTIVE_CONTEXT_WITHOUT_REDUCING_DENSITY"
            ),
            "cross_window_discrimination_signal": cross_window_discrimination,
        },
        "information_still_missing": (
            "GENERIC_CAUSAL_LIQUIDITY_CAPACITY_AXIS_FROM_VT08_M15_SOURCE",
            "INTRABAR_SEQUENCE_BELOW_M15_FOR_AMBIGUOUS_PATHS",
            "INDEPENDENT_FRESH_HOLDOUT_REMAINS_CLOSED_DURING_DEVELOPMENT",
        ),
        "next_experiment_contract": {
            "if_cross_window_discrimination_present": (
                "PREREGISTER_V3_ROUTE_ACTUATION_USING_ONLY_SOURCE_AUTHORIZED "
                "EXECUTION_ALTERNATIVES; KEEP_100_PERCENT_SIGNAL_DENSITY"
            ),
            "if_cross_window_discrimination_absent": (
                "DO_NOT_ACTUATE; IMPROVE_PERCEPTION_AXES_AND_CAUSAL_SEQUENCE "
                "REPRESENTATION_FIRST"
            ),
        },
        "decision": (
            "V2_GEOMETRY_DISCRIMINATION_SIGNAL_PRESENT"
            if cross_window_discrimination
            else "V2_GEOMETRY_NOT_YET_DISCRIMINATIVE"
        ),
        "governance": {
            "research_only": True,
            "consumed_evidence_only": True,
            "r66_reopened_as_fresh": False,
            "fresh_holdout_opened": False,
            "candidate_certified": False,
            "vt08_methodology_modified": False,
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

    def compact(window: dict[str, object]) -> dict[str, object]:
        return {
            "sample": window["sample"],
            "baseline_primary": _primary(window["baseline"]),
            "state_counts": window["state_counts"],
            "state_diagnostics": {
                state: {
                    "sample": section["sample"],
                    "primary": section["primary"],
                }
                for state, section in window["state_diagnostics"].items()
            },
            "hypothesis_checks": window["hypothesis_checks"],
        }

    print(
        json.dumps(
            {
                "identity": IDENTITY,
                "decision": report["decision"],
                "root_cause_model": report["root_cause_model"],
                "five_year": compact(report["five_year"]),
                "recent_two_year": compact(report["recent_two_year"]),
                "r66": compact(report["r66_consumed_failed_holdout"]),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
