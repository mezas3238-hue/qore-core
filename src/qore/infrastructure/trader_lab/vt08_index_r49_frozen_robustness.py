"""VT08 Index R49 — frozen-candidate robustness and temporal hardening.

R49 replays the exact R47 identity frozen by R48. It does not select or retune
rules. The stage adds:
- exact dual-window reproduction checks,
- six-month temporal blocks and chronological halves,
- extra friction at -0.15R and -0.20R per trade,
- 10,000-path fixed-seed moving-block bootstrap at -0.10R,
- losing-streak and realized drawdown distributions,
- market/side/anchor/POI/rearm stability tables,
- concurrency and committed structural-risk diagnostics,
- cross-index daily PnL dependence,
- static causal/leakage guards over the R47 runtime rule functions.

Both economic windows are already consumed. Results are robustness evidence,
not a fresh holdout and not operational authorization.
"""

from __future__ import annotations

import argparse
import inspect
import json
import math
import random
from collections import defaultdict
from collections.abc import Sequence
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab import vt08_index_r6_5y_failure_forensics as fx
from qore.infrastructure.trader_lab import vt08_index_r15_concurrent_portfolio_validation as r15
from qore.infrastructure.trader_lab import (
    vt08_index_r31_source_complete_structural_concurrency as r31,
)
from qore.infrastructure.trader_lab import vt08_index_r34_hybrid_formation_poi_health as r34
from qore.infrastructure.trader_lab import vt08_index_r43_sp500_long_stability_prior as r43
from qore.infrastructure.trader_lab import (
    vt08_index_r45_frozen_recent_2y_reproduction as r45,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r46_cross_window_transport_forensics as r46,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r47_transport_safe_structural_demotion as r47,
)
from qore.infrastructure.trader_lab import vt08_index_r48_candidate_freeze as freeze
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import Vt08IndexC2R1Bar

SCHEMA = "qore.trader_lab.vt08_index_r49_frozen_robustness.v1"
IDENTITY = "VT08_INDEX_R49_R47_FROZEN_ROBUSTNESS_001"
CANDIDATE_ID = freeze.CANDIDATE_ID
CANDIDATE_RULE_FINGERPRINT = freeze.CANDIDATE_RULE_FINGERPRINT

PRIMARY_STRESS = Decimal("0.05")
SECONDARY_STRESS = Decimal("0.10")
EXTRA_STRESSES = (Decimal("0.15"), Decimal("0.20"))
PORTFOLIO_DD_MAX_R = Decimal("6")
BOOTSTRAP_SEED = 20260919
BOOTSTRAP_PATHS = 10_000
BOOTSTRAP_BLOCK_LENGTH = 5
BOOTSTRAP_POSITIVE_TERMINAL_MIN = 0.90
BOOTSTRAP_P95_DD_MAX_R = 6.0
_NY = ZoneInfo("America/New_York")

FIVE_YEAR_HALF_YEAR_BOUNDARIES = (
    date(2018, 9, 15),
    date(2019, 3, 15),
    date(2019, 9, 15),
    date(2020, 3, 15),
    date(2020, 9, 15),
    date(2021, 3, 15),
    date(2021, 9, 15),
    date(2022, 3, 15),
    date(2022, 9, 15),
    date(2023, 3, 15),
    date(2023, 9, 15),
)
TWO_YEAR_HALF_YEAR_BOUNDARIES = (
    date(2024, 9, 15),
    date(2025, 3, 15),
    date(2025, 9, 15),
    date(2026, 3, 15),
    date(2026, 9, 15),
)

STABILITY_DIMENSIONS = ("symbol", "side", "anchor", "poi", "rearm")


def _realized_values(
    assigned: Sequence[r15.AssignedTrade],
    *,
    stress: Decimal,
) -> tuple[Decimal, ...]:
    return r15._realized_values(assigned, stress=stress)


def _quantile(values: Sequence[float], probability: float) -> float:
    if not values:
        raise ValueError("quantile requires values")
    if not 0.0 <= probability <= 1.0:
        raise ValueError("quantile probability outside [0,1]")
    ordered = sorted(values)
    index = int(round((len(ordered) - 1) * probability))
    return ordered[index]


def _max_drawdown(values: Sequence[float]) -> float:
    equity = 0.0
    peak = 0.0
    maximum = 0.0
    for value in values:
        equity += value
        peak = max(peak, equity)
        maximum = max(maximum, peak - equity)
    return maximum


def _max_losing_streak(values: Sequence[float]) -> int:
    current = 0
    maximum = 0
    for value in values:
        if value < 0.0:
            current += 1
            maximum = max(maximum, current)
        else:
            current = 0
    return maximum


def _moving_block_bootstrap(
    values: Sequence[Decimal],
    *,
    seed: int,
    paths: int,
    block_length: int,
) -> dict[str, Any]:
    source = tuple(float(value) for value in values)
    if len(source) < block_length:
        raise ValueError("bootstrap source shorter than block length")
    rng = random.Random(seed)
    max_start = len(source) - block_length
    terminals: list[float] = []
    drawdowns: list[float] = []
    losing_streaks: list[float] = []
    positive = 0

    for _ in range(paths):
        sample: list[float] = []
        while len(sample) < len(source):
            start = rng.randint(0, max_start)
            sample.extend(source[start : start + block_length])
        sample = sample[: len(source)]
        terminal = sum(sample)
        positive += int(terminal > 0.0)
        terminals.append(terminal)
        drawdowns.append(_max_drawdown(sample))
        losing_streaks.append(float(_max_losing_streak(sample)))

    positive_fraction = positive / paths
    p95_dd = _quantile(drawdowns, 0.95)
    return {
        "algorithm": "MOVING_BLOCK_BOOTSTRAP_CONTIGUOUS_TRADES",
        "seed": seed,
        "paths": paths,
        "block_length": block_length,
        "source_sample": len(source),
        "source_terminal_r": str(sum(values, Decimal())),
        "positive_terminal_fraction": positive_fraction,
        "terminal_r_p05": _quantile(terminals, 0.05),
        "terminal_r_p50": _quantile(terminals, 0.50),
        "terminal_r_p95": _quantile(terminals, 0.95),
        "max_drawdown_r_p50": _quantile(drawdowns, 0.50),
        "max_drawdown_r_p95": p95_dd,
        "max_drawdown_r_p99": _quantile(drawdowns, 0.99),
        "max_losing_streak_p50": int(_quantile(losing_streaks, 0.50)),
        "max_losing_streak_p95": int(_quantile(losing_streaks, 0.95)),
        "max_losing_streak_p99": int(_quantile(losing_streaks, 0.99)),
        "qualification": {
            "positive_terminal_min": BOOTSTRAP_POSITIVE_TERMINAL_MIN,
            "p95_max_drawdown_limit_r": BOOTSTRAP_P95_DD_MAX_R,
            "pass": (
                positive_fraction >= BOOTSTRAP_POSITIVE_TERMINAL_MIN
                and p95_dd <= BOOTSTRAP_P95_DD_MAX_R
            ),
        },
    }


def _date_of(item: r15.AssignedTrade) -> date:
    return item.exited_at.astimezone(_NY).date()


def _temporal_blocks(
    assigned: Sequence[r15.AssignedTrade],
    *,
    boundaries: tuple[date, ...],
    stress: Decimal,
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for index in range(len(boundaries) - 1):
        start = boundaries[index]
        end = boundaries[index + 1]
        items = tuple(item for item in assigned if start <= _date_of(item) < end)
        metrics = fx._metrics(_realized_values(items, stress=stress))
        result.append(
            {
                "block": f"H{index + 1}",
                "start_date": start.isoformat(),
                "end_date_exclusive": end.isoformat(),
                **metrics,
                "positive": Decimal(str(metrics["total_r"])) > 0,
            }
        )
    return result


def _chronological_halves(
    assigned: Sequence[r15.AssignedTrade],
    *,
    midpoint: date,
    stress: Decimal,
) -> dict[str, Any]:
    ordered = tuple(sorted(assigned, key=lambda item: (item.exited_at, item.trade_id)))
    first = tuple(item for item in ordered if _date_of(item) < midpoint)
    second = tuple(item for item in ordered if _date_of(item) >= midpoint)
    return {
        "first": fx._metrics(_realized_values(first, stress=stress)),
        "second": fx._metrics(_realized_values(second, stress=stress)),
    }


def _row_metrics(
    rows: Sequence[dict[str, Any]],
    *,
    stress: Decimal,
) -> dict[str, Any]:
    ordered = sorted(
        rows,
        key=lambda row: (
            str(row["exit_timestamp"]),
            str(row["symbol"]),
            str(row["timestamp"]),
        ),
    )
    values = tuple(
        (Decimal(str(row["outcome_r"])) - stress)
        * Decimal(str(row["effective_weight"]))
        for row in ordered
    )
    return fx._metrics(values)


def _stability_breakdown(
    rows: Sequence[dict[str, Any]],
    *,
    key: str,
) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row[key])].append(row)
    return {
        label: {
            "secondary": _row_metrics(items, stress=SECONDARY_STRESS),
            "extra_020": _row_metrics(items, stress=Decimal("0.20")),
        }
        for label, items in sorted(grouped.items())
    }


def _concurrency(assigned: Sequence[r15.AssignedTrade]) -> dict[str, Any]:
    events: list[tuple[datetime, int, int, Decimal]] = []
    for item in assigned:
        events.append((item.signal_at, 1, item.trade_id, item.weight))
        events.append((item.exited_at, 0, item.trade_id, item.weight))
    active: dict[int, Decimal] = {}
    max_open = 0
    max_committed = Decimal()
    for _when, kind, trade_id, weight in sorted(events):
        if kind == 0:
            active.pop(trade_id, None)
        else:
            active[trade_id] = weight
        max_open = max(max_open, len(active))
        max_committed = max(max_committed, sum(active.values(), Decimal()))
    return {
        "max_concurrent_open_positions": max_open,
        "max_committed_structural_risk_r": str(max_committed),
        "signals_suppressed": 0,
    }


def _pearson(left: Sequence[float], right: Sequence[float]) -> float | None:
    if len(left) != len(right) or len(left) < 2:
        return None
    left_mean = sum(left) / len(left)
    right_mean = sum(right) / len(right)
    numerator = sum(
        (a - left_mean) * (b - right_mean)
        for a, b in zip(left, right, strict=True)
    )
    left_var = sum((a - left_mean) ** 2 for a in left)
    right_var = sum((b - right_mean) ** 2 for b in right)
    denominator = math.sqrt(left_var * right_var)
    if denominator == 0.0:
        return None
    return numerator / denominator


def _cross_index_dependence(
    assigned: Sequence[r15.AssignedTrade],
    *,
    stress: Decimal,
) -> dict[str, Any]:
    daily: dict[str, dict[date, Decimal]] = {
        "NAS100": defaultdict(Decimal),
        "SP500": defaultdict(Decimal),
        "US30": defaultdict(Decimal),
    }
    for item in assigned:
        daily[item.symbol][_date_of(item)] += (
            item.outcome.r_multiple - stress
        ) * item.weight
    all_dates = sorted(set().union(*(set(rows) for rows in daily.values())))
    pairs: dict[str, float | None] = {}
    symbols = ("NAS100", "SP500", "US30")
    for index, left_symbol in enumerate(symbols):
        for right_symbol in symbols[index + 1 :]:
            left = [float(daily[left_symbol].get(day, Decimal())) for day in all_dates]
            right = [float(daily[right_symbol].get(day, Decimal())) for day in all_dates]
            pairs[f"{left_symbol}|{right_symbol}"] = _pearson(left, right)
    finite = [abs(value) for value in pairs.values() if value is not None]
    return {
        "basis": "NY_EXIT_DATE_SECONDARY_STRESSED_REALIZED_R",
        "calendar_days": len(all_dates),
        "pairwise_pearson": pairs,
        "max_absolute_pairwise_correlation": max(finite) if finite else None,
    }


def _causal_leakage_guard() -> dict[str, Any]:
    labels_source = inspect.getsource(r47._rule_labels)
    cross_source = inspect.getsource(r47._cross_index_state)
    latest_source = inspect.getsource(r47._latest_completed_h4)
    forbidden = ("outcome", "r_multiple", "exited_at", "profit_factor", "calendar", "year")
    labels_forbidden = [token for token in forbidden if token in labels_source]
    cross_forbidden = [token for token in forbidden if token in cross_source]
    completed_h4_guard = "closed_at.astimezone(UTC) <= decision" in latest_source
    return {
        "rule_labels_forbidden_tokens": labels_forbidden,
        "cross_index_forbidden_tokens": cross_forbidden,
        "completed_h4_requires_close_before_decision": completed_h4_guard,
        "candidate_rule_fingerprint_matches_freeze": (
            r47.RULE_FINGERPRINT == freeze.CANDIDATE_RULE_FINGERPRINT
        ),
        "pass": (
            not labels_forbidden
            and not cross_forbidden
            and completed_h4_guard
            and r47.RULE_FINGERPRINT == freeze.CANDIDATE_RULE_FINGERPRINT
        ),
    }


def _build_window(
    *,
    stream: Sequence[Any],
    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]],
    opened_by_symbol: dict[str, tuple[Any, ...]],
    window_id: str,
    boundaries: tuple[date, ...],
    midpoint: date,
) -> dict[str, Any]:
    _base_row, baseline = r34._row(stream, overlay=r43.BASE_POI_OVERLAY)
    assigned, diagnostics = r47._apply_transport_rules(
        baseline,
        bars_by_symbol=bars_by_symbol,
    )
    trace = r46._causal_trace(stream)
    for item, state in zip(baseline, trace, strict=True):
        if item.weight != Decimal(str(state["base_r34_weight"])):
            raise ValueError("R49 causal trace drifted from R34 baseline")
    rows = r46._feature_rows(
        assigned=assigned,
        trace=trace,
        window_id=window_id,
        bars_by_symbol=bars_by_symbol,
    )

    primary = fx._metrics(_realized_values(assigned, stress=PRIMARY_STRESS))
    secondary = fx._metrics(_realized_values(assigned, stress=SECONDARY_STRESS))
    secondary_mtm = r15._portfolio_mark_to_market(
        assigned,
        bars_by_symbol=bars_by_symbol,
        opened_by_symbol=opened_by_symbol,
        stress=SECONDARY_STRESS,
        adverse=True,
    )

    extra: dict[str, Any] = {}
    for stress in EXTRA_STRESSES:
        metrics = fx._metrics(_realized_values(assigned, stress=stress))
        mtm = r15._portfolio_mark_to_market(
            assigned,
            bars_by_symbol=bars_by_symbol,
            opened_by_symbol=opened_by_symbol,
            stress=stress,
            adverse=True,
        )
        extra[str(stress)] = {
            "realized": metrics,
            "conservative_mark_to_market": mtm,
            "positive_terminal": Decimal(str(metrics["total_r"])) > 0,
            "dd_within_contract": Decimal(str(mtm["max_drawdown_r"])) <= PORTFOLIO_DD_MAX_R,
        }

    blocks = _temporal_blocks(
        assigned,
        boundaries=boundaries,
        stress=SECONDARY_STRESS,
    )
    halves = _chronological_halves(
        assigned,
        midpoint=midpoint,
        stress=SECONDARY_STRESS,
    )
    bootstrap = _moving_block_bootstrap(
        _realized_values(assigned, stress=SECONDARY_STRESS),
        seed=BOOTSTRAP_SEED,
        paths=BOOTSTRAP_PATHS,
        block_length=BOOTSTRAP_BLOCK_LENGTH,
    )
    stability = {
        dimension: _stability_breakdown(rows, key=dimension)
        for dimension in STABILITY_DIMENSIONS
    }
    negative_stability = {
        dimension: [
            label
            for label, metrics in groups.items()
            if int(metrics["secondary"]["sample"]) >= 30
            and Decimal(str(metrics["secondary"]["total_r"])) <= 0
        ]
        for dimension, groups in stability.items()
    }

    return {
        "sample": len(assigned),
        "primary": primary,
        "secondary": secondary,
        "secondary_conservative_mark_to_market": secondary_mtm,
        "extra_stress": extra,
        "half_year_blocks_secondary": blocks,
        "half_year_positive_count": sum(bool(row["positive"]) for row in blocks),
        "chronological_halves_secondary": halves,
        "bootstrap_secondary": bootstrap,
        "stability": stability,
        "negative_stability_cohorts_min30": negative_stability,
        "concurrency": _concurrency(assigned),
        "cross_index_dependence": _cross_index_dependence(
            assigned,
            stress=SECONDARY_STRESS,
        ),
        "diagnostics": diagnostics,
    }


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, Any]:
    if not freeze.dependency_contract_matches():
        raise ValueError("R49 R48 freeze dependency drift")
    if r47.RULE_FINGERPRINT != freeze.CANDIDATE_RULE_FINGERPRINT:
        raise ValueError("R49 R47 fingerprint drift")

    roots = {
        "NAS100": nas100_root,
        "SP500": sp500_root,
        "US30": us30_root,
    }
    five_stream, five_bars, five_opened, five_provenance = (
        r31._build_source_complete_stream(roots=roots)
    )
    two_stream, two_bars, two_opened, two_provenance = (
        r45._build_source_complete_stream_2y(roots=roots)
    )

    five = _build_window(
        stream=five_stream,
        bars_by_symbol={key: tuple(value) for key, value in five_bars.items()},
        opened_by_symbol=five_opened,
        window_id="5Y",
        boundaries=FIVE_YEAR_HALF_YEAR_BOUNDARIES,
        midpoint=date(2021, 3, 15),
    )
    two = _build_window(
        stream=two_stream,
        bars_by_symbol={key: tuple(value) for key, value in two_bars.items()},
        opened_by_symbol=two_opened,
        window_id="2Y",
        boundaries=TWO_YEAR_HALF_YEAR_BOUNDARIES,
        midpoint=date(2025, 9, 15),
    )

    exact_reproduction = (
        five["sample"] == freeze.FIVE_YEAR["sample"]
        and two["sample"] == freeze.RECENT_TWO_YEAR["sample"]
        and str(five["primary"]["profit_factor"]) == freeze.FIVE_YEAR["primary_pf"]
        and str(five["secondary"]["profit_factor"]) == freeze.FIVE_YEAR["secondary_pf"]
        and str(two["primary"]["profit_factor"]) == freeze.RECENT_TWO_YEAR["primary_pf"]
        and str(two["secondary"]["profit_factor"]) == freeze.RECENT_TWO_YEAR["secondary_pf"]
    )

    extra_stress_pass = all(
        bool(window["extra_stress"][str(stress)]["positive_terminal"])
        and bool(window["extra_stress"][str(stress)]["dd_within_contract"])
        for window in (five, two)
        for stress in EXTRA_STRESSES
    )
    bootstrap_pass = all(
        bool(window["bootstrap_secondary"]["qualification"]["pass"])
        for window in (five, two)
    )
    leakage = _causal_leakage_guard()
    hard_gate_pass = (
        exact_reproduction
        and extra_stress_pass
        and bootstrap_pass
        and bool(leakage["pass"])
        and int(five["diagnostics"]["suppressed_trade_count"]) == 0
        and int(two["diagnostics"]["suppressed_trade_count"]) == 0
        and int(five["diagnostics"]["risk_increase_count"]) == 0
        and int(two["diagnostics"]["risk_increase_count"]) == 0
    )

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "candidate": {
            "candidate_id": CANDIDATE_ID,
            "candidate_rule_fingerprint": CANDIDATE_RULE_FINGERPRINT,
            "freeze_id": freeze.FREEZE_ID,
            "freeze_evidence_fingerprint": freeze.FREEZE_EVIDENCE_FINGERPRINT,
            "rules_changed": False,
            "retuning_performed": False,
        },
        "preregistered_robustness": {
            "extra_stresses_r_per_trade": [str(value) for value in EXTRA_STRESSES],
            "bootstrap_seed": BOOTSTRAP_SEED,
            "bootstrap_paths": BOOTSTRAP_PATHS,
            "bootstrap_block_length": BOOTSTRAP_BLOCK_LENGTH,
            "bootstrap_positive_terminal_min": BOOTSTRAP_POSITIVE_TERMINAL_MIN,
            "bootstrap_p95_dd_max_r": BOOTSTRAP_P95_DD_MAX_R,
            "temporal_resolution": "FIXED_6_MONTH_BLOCKS",
            "stability_dimensions": list(STABILITY_DIMENSIONS),
        },
        "five_year": five,
        "recent_two_year": two,
        "causal_leakage_guard": leakage,
        "exact_frozen_reproduction": exact_reproduction,
        "extra_stress_hard_gate_pass": extra_stress_pass,
        "bootstrap_hard_gate_pass": bootstrap_pass,
        "hard_gate_pass": hard_gate_pass,
        "decision": (
            "PASS_R49_ROBUSTNESS_HARD_GATES_CONTINUE_CERTIFICATION"
            if hard_gate_pass
            else "FAIL_R49_ROBUSTNESS_RETURN_TO_FORENSICS"
        ),
        "provenance": {
            "five_year": five_provenance,
            "recent_two_year": two_provenance,
        },
        "governance": {
            "candidate_frozen_before_robustness": True,
            "five_year_window_consumed": True,
            "two_year_window_consumed": True,
            "fresh_holdout_claim": False,
            "retuning_performed": False,
            "calendar_or_year_runtime_feature": False,
            "post_entry_outcome_runtime_feature": False,
            "all_signals_preserved": True,
            "freed_risk_reallocated": False,
            "certified": False,
            "demo_eligible": False,
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
                "candidate": report["candidate"],
                "five_year": {
                    "sample": report["five_year"]["sample"],
                    "secondary": report["five_year"]["secondary"],
                    "extra_stress": report["five_year"]["extra_stress"],
                    "half_year_blocks_secondary": report["five_year"][
                        "half_year_blocks_secondary"
                    ],
                    "bootstrap_secondary": report["five_year"]["bootstrap_secondary"],
                    "negative_stability_cohorts_min30": report["five_year"][
                        "negative_stability_cohorts_min30"
                    ],
                    "concurrency": report["five_year"]["concurrency"],
                    "cross_index_dependence": report["five_year"][
                        "cross_index_dependence"
                    ],
                },
                "recent_two_year": {
                    "sample": report["recent_two_year"]["sample"],
                    "secondary": report["recent_two_year"]["secondary"],
                    "extra_stress": report["recent_two_year"]["extra_stress"],
                    "half_year_blocks_secondary": report["recent_two_year"][
                        "half_year_blocks_secondary"
                    ],
                    "bootstrap_secondary": report["recent_two_year"][
                        "bootstrap_secondary"
                    ],
                    "negative_stability_cohorts_min30": report["recent_two_year"][
                        "negative_stability_cohorts_min30"
                    ],
                    "concurrency": report["recent_two_year"]["concurrency"],
                    "cross_index_dependence": report["recent_two_year"][
                        "cross_index_dependence"
                    ],
                },
                "causal_leakage_guard": report["causal_leakage_guard"],
                "exact_frozen_reproduction": report["exact_frozen_reproduction"],
                "extra_stress_hard_gate_pass": report["extra_stress_hard_gate_pass"],
                "bootstrap_hard_gate_pass": report["bootstrap_hard_gate_pass"],
                "hard_gate_pass": report["hard_gate_pass"],
                "decision": report["decision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
