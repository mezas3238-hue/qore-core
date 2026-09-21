"""VT08 Index R107 — STANDARD economic-root attribution.

R106 proved that most transport-adverse STANDARD cohorts cannot be repaired by
further risk demotion because they are already at the existing 0.005R floor.

R107 moves one layer deeper, without creating a candidate. It asks:
1. How saturated is STANDARD at the risk floor?
2. Is STANDARD weakness caused by the inherited 2.5R target rather than the
   source-authorized initial 2R target?
3. How often does the same source-valid continuation offer a causal retest
   after the close entry, which could improve entry geometry without creating a
   second setup?

Source contract:
- TTrades 2026 strategy material: close or retest are valid executions of the
  same continuation setup; initial target is 2R, HTF objectives optional.
- R89 already froze retest as alternate fill, never a second setup.
- R80 already froze 2R as the single source-authorized target counterfactual.

This stage does NOT change runtime rules, allocator decisions, signal count,
entries, stops or target of any candidate. 2R outcomes are counterfactual
forensic labels evaluated at fixed R102 control weights so target effect is
isolated from allocator/concurrency feedback.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from collections.abc import Sequence
from datetime import UTC, date
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    vt08_index_r6_5y_failure_forensics as fx,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r15_concurrent_portfolio_validation as r15,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r35_five_year_temporal_contract as r35,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r45_frozen_recent_2y_reproduction as r45,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r55_distributed_causal_risk as r55,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r58_exact_r47_distributed_risk as r58,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r66_fresh_historical_holdout as r66,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r74_ambiguous_bias_resolvers as r74,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r80_source_2r_target_transport as r80,
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
    vt08_index_r106_standard_causal_demotion_ablation as r106,
)
from qore.infrastructure.trader_lab import (
    vt08_index_v7_ttrades_source_corrected as v7,
)
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    Vt08IndexC2R1Bar,
)

SCHEMA = "qore.trader_lab.vt08_index_r107_standard_economic_root_attribution.v1"
IDENTITY = "VT08_INDEX_R107_STANDARD_ECONOMIC_ROOT_ATTRIBUTION_001"

SOURCE_R106_RUN_ID = 35557035781
SOURCE_R106_ARTIFACT_ID = 10620887519
SOURCE_R106_ARTIFACT_DIGEST = (
    "sha256:6a58a578618ba34bdb960a08d12649220d457823b59e16d871e7cb6f31933efc"
)
CONTROL_POLICY_ID = r102.POLICY_EXPLICIT_FULL
FLOOR = r55.MIN_EFFECTIVE_WEIGHT

TTRADES_2026_STRATEGY_URL = (
    "https://ttrades.com/the-only-trading-strategy-you-need-for-2026/"
)
TTRADES_CONTINUATION_URL = (
    "https://ttrades.com/using-order-blocks-for-continuations/"
)


def _period_id(window_id: str, exited_date: date) -> str:
    if window_id == "5Y":
        boundaries = r35._annual_boundaries()
        for index in range(5):
            if boundaries[index] <= exited_date < boundaries[index + 1]:
                return f"Y{index + 1}"
        return "OUTSIDE"
    if window_id == "2Y":
        boundaries = (
            r45.START_DATE,
            date(2025, 9, 15),
            r45.END_DATE_EXCLUSIVE,
        )
        for index in range(2):
            if boundaries[index] <= exited_date < boundaries[index + 1]:
                return f"Y{index + 1}"
        return "OUTSIDE"
    if window_id == "R66":
        boundaries = (
            r66.START_DATE,
            r66.BLOCK_BOUNDARY,
            r66.END_DATE_EXCLUSIVE,
        )
        for index in range(2):
            if boundaries[index] <= exited_date < boundaries[index + 1]:
                return f"B{index + 1}"
        return "OUTSIDE"
    raise ValueError(f"R107 unsupported window {window_id}")


def _metrics(
    values: Sequence[Decimal],
) -> dict[str, Any]:
    return fx._metrics(tuple(values))


def _rows_metrics(
    rows: Sequence[dict[str, Any]],
    *,
    outcome_key: str,
    weighted: bool,
    stress: Decimal,
) -> dict[str, Any]:
    values: list[Decimal] = []
    for row in sorted(
        rows,
        key=lambda x: (
            str(x["exit_timestamp"]),
            str(x["symbol"]),
            str(x["signal_timestamp"]),
        ),
    ):
        value = Decimal(str(row[outcome_key])) - stress
        if weighted:
            value *= Decimal(str(row["weight"]))
        values.append(value)
    return _metrics(values)


def _metric_bundle(
    rows: Sequence[dict[str, Any]],
    *,
    outcome_key: str,
) -> dict[str, Any]:
    return {
        "raw_primary": _rows_metrics(
            rows,
            outcome_key=outcome_key,
            weighted=False,
            stress=r102.PRIMARY_STRESS,
        ),
        "raw_secondary": _rows_metrics(
            rows,
            outcome_key=outcome_key,
            weighted=False,
            stress=r102.SECONDARY_STRESS,
        ),
        "fixed_weight_primary": _rows_metrics(
            rows,
            outcome_key=outcome_key,
            weighted=True,
            stress=r102.PRIMARY_STRESS,
        ),
        "fixed_weight_secondary": _rows_metrics(
            rows,
            outcome_key=outcome_key,
            weighted=True,
            stress=r102.SECONDARY_STRESS,
        ),
    }


def _period_metrics(
    rows: Sequence[dict[str, Any]],
    *,
    outcome_key: str,
) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(row["period_id"])].append(row)
    return {
        key: {
            "sample": len(items),
            **_metric_bundle(items, outcome_key=outcome_key),
        }
        for key, items in sorted(groups.items())
        if key != "OUTSIDE"
    }


def _standard_ids(
    assigned: Sequence[r15.AssignedTrade],
    *,
    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]],
) -> set[tuple[object, ...]]:
    h4_cache = {
        symbol: r82._h4_bar_cache(bars)
        for symbol, bars in bars_by_symbol.items()
    }
    result: set[tuple[object, ...]] = set()
    for item in assigned:
        classification = r82._classify_opportunity(
            item.opportunity,
            h4_bars=h4_cache[item.symbol],
        )
        if str(classification["family"]) == r82.FAMILY_UNQUALIFIED:
            result.add(item.opportunity.identity())
    return result


def _retest_context(
    item: r15.AssignedTrade,
    *,
    h4_cache: dict[str, dict[Any, tuple[Vt08IndexC2R1Bar, ...]]],
) -> dict[str, Any]:
    signal = item.opportunity.signal
    h4_opened = signal.h4_opened_at.astimezone(UTC)
    inside = h4_cache[item.symbol].get(h4_opened)
    if inside is None:
        return {
            "retest_available": False,
            "reason": "H4_NOT_FOUND",
            "entry_improvement_risk_fraction": None,
        }

    signal_at = signal.signal_at.astimezone(UTC)
    continuation_index = next(
        (
            index
            for index, bar in enumerate(inside)
            if bar.closed_at.astimezone(UTC) == signal_at
        ),
        None,
    )
    if continuation_index is None or continuation_index <= 0:
        return {
            "retest_available": False,
            "reason": "CONTINUATION_BAR_NOT_FOUND",
            "entry_improvement_risk_fraction": None,
        }

    retest_index = r89._retest_fill_index(
        inside,
        continuation_index=continuation_index,
        side=signal.side,
        protected_swing=signal.protected_swing_extreme,
        model_kind=signal.model_kind,
        h4_open=inside[0].open,
    )
    if retest_index is None:
        return {
            "retest_available": False,
            "reason": "NO_CAUSAL_RETEST",
            "entry_improvement_risk_fraction": None,
        }

    level = r89._continuation_breakout_level(
        inside,
        continuation_index=continuation_index,
        side=signal.side,
    )
    original_risk = abs(signal.entry - signal.stop)
    improvement = (
        signal.entry - level
        if signal.side.value == "long"
        else level - signal.entry
    )
    fraction = (
        improvement / original_risk
        if original_risk > 0
        else Decimal()
    )
    return {
        "retest_available": True,
        "reason": "CAUSAL_RETEST_AVAILABLE",
        "retest_index": retest_index,
        "retest_level": str(level),
        "entry_improvement": str(improvement),
        "entry_improvement_risk_fraction": str(fraction),
    }


def _window(
    *,
    roots: dict[str, Path],
    window_id: str,
) -> dict[str, Any]:
    canonical, bars_by_symbol, provenance = r74._load_window(
        roots=roots,
        window_id=window_id,
    )
    _start, _end, expected = r74._window_contract(window_id)
    bars: dict[str, Sequence[Vt08IndexC2R1Bar]] = {
        key: tuple(value)
        for key, value in bars_by_symbol.items()
    }

    base, _base_diag = r58._exact_r47(
        tuple(canonical),
        bars_by_symbol=bars,
    )
    base = tuple(base)
    control, _control_diag = r102._apply_confidence_policy(
        base,
        bars_by_symbol=bars,
        policy_id=CONTROL_POLICY_ID,
    )
    control = tuple(control)
    if len(control) != expected:
        raise ValueError(f"R107 {window_id} control sample drift")

    standard = _standard_ids(
        control,
        bars_by_symbol=bars,
    )
    source_2r_stream = r80._replay_target(
        canonical,
        bars_by_symbol=bars,
        target_r=r80.SOURCE_TARGET_R,
    )
    source_2r_by_id = {
        opportunity.identity(): outcome
        for opportunity, outcome in source_2r_stream
    }
    canonical_by_id = {
        opportunity.identity(): outcome
        for opportunity, outcome in canonical
    }
    h4_cache = {
        symbol: r82._h4_bar_cache(symbol_bars)
        for symbol, symbol_bars in bars.items()
    }

    rows: list[dict[str, Any]] = []
    for item in control:
        identity = item.opportunity.identity()
        if identity not in standard:
            continue
        canonical_outcome = canonical_by_id[identity]
        source_outcome = source_2r_by_id[identity]
        retest = _retest_context(
            item,
            h4_cache=h4_cache,
        )
        rows.append(
            {
                "symbol": item.symbol,
                "side": item.opportunity.signal.side.value,
                "anchor": str(
                    item.opportunity.signal.h4_opened_at.astimezone(
                        v7._NY
                    ).hour
                ),
                "signal_timestamp": (
                    item.opportunity.signal.signal_at.astimezone(UTC).isoformat()
                ),
                "exit_timestamp": item.exited_at.astimezone(UTC).isoformat(),
                "period_id": _period_id(
                    window_id,
                    item.exited_at.astimezone(v7._NY).date(),
                ),
                "weight": str(item.weight),
                "at_floor": item.weight == FLOOR,
                "canonical_2_5r": str(canonical_outcome.r_multiple),
                "source_2r": str(source_outcome.r_multiple),
                **retest,
            }
        )

    if len(rows) != len(standard):
        raise ValueError(f"R107 {window_id} STANDARD row drift")

    floor_rows = [row for row in rows if bool(row["at_floor"])]
    above_rows = [row for row in rows if not bool(row["at_floor"])]
    retest_rows = [
        row for row in rows
        if bool(row["retest_available"])
    ]
    retest_floor = [
        row for row in floor_rows
        if bool(row["retest_available"])
    ]

    improvement_fractions = [
        Decimal(str(row["entry_improvement_risk_fraction"]))
        for row in retest_rows
        if row["entry_improvement_risk_fraction"] is not None
    ]

    return {
        "window_id": window_id,
        "canonical_sample": expected,
        "standard_sample": len(rows),
        "floor_saturation": {
            "floor_count": len(floor_rows),
            "above_floor_count": len(above_rows),
            "floor_fraction": str(
                Decimal(len(floor_rows)) / Decimal(len(rows))
            ),
            "floor_metrics_2_5r": _metric_bundle(
                floor_rows,
                outcome_key="canonical_2_5r",
            ),
            "above_floor_metrics_2_5r": _metric_bundle(
                above_rows,
                outcome_key="canonical_2_5r",
            ),
        },
        "canonical_2_5r": {
            **_metric_bundle(rows, outcome_key="canonical_2_5r"),
            "periods": _period_metrics(
                rows,
                outcome_key="canonical_2_5r",
            ),
        },
        "source_2r_counterfactual": {
            **_metric_bundle(rows, outcome_key="source_2r"),
            "periods": _period_metrics(
                rows,
                outcome_key="source_2r",
            ),
            "target_grid_searched": False,
            "allocator_recomputed": False,
        },
        "retest_coverage": {
            "available_count": len(retest_rows),
            "available_fraction": str(
                Decimal(len(retest_rows)) / Decimal(len(rows))
            ),
            "floor_available_count": len(retest_floor),
            "floor_available_fraction": (
                str(Decimal(len(retest_floor)) / Decimal(len(floor_rows)))
                if floor_rows
                else "0"
            ),
            "mean_entry_improvement_risk_fraction": (
                str(
                    sum(improvement_fractions, Decimal())
                    / Decimal(len(improvement_fractions))
                )
                if improvement_fractions
                else None
            ),
            "retest_is_alternate_same_setup": True,
            "pnl_replayed_at_retest": False,
        },
        "provenance": provenance,
    }


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, Any]:
    if r106.IDENTITY != (
        "VT08_INDEX_R106_STANDARD_CAUSAL_DEMOTION_ABLATION_001"
    ):
        raise ValueError("R107 R106 identity drift")
    if r80.SOURCE_TARGET_R != Decimal("2"):
        raise ValueError("R107 source target drift")

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
        "source_r106": {
            "run_id": SOURCE_R106_RUN_ID,
            "artifact_id": SOURCE_R106_ARTIFACT_ID,
            "artifact_digest": SOURCE_R106_ARTIFACT_DIGEST,
        },
        "source_contract": {
            "canonical_research_target_r": str(r80.CANONICAL_TARGET_R),
            "source_initial_target_r": str(r80.SOURCE_TARGET_R),
            "close_or_retest_same_setup": True,
            "retest_creates_new_setup": False,
            "ttrades_2026_strategy_url": TTRADES_2026_STRATEGY_URL,
            "ttrades_continuation_url": TTRADES_CONTINUATION_URL,
        },
        "five_year": five,
        "recent_two_year": two,
        "r66_failed_holdout": failed,
        "decision": "R107_STANDARD_ECONOMIC_ROOT_ATTRIBUTION_COMPLETE_NO_RULE_CHANGE",
        "governance": {
            "forensics_only": True,
            "consumed_evidence_only": True,
            "fresh_holdout_claim": False,
            "signal_surface_changed": False,
            "signals_suppressed": False,
            "runtime_target_changed": False,
            "runtime_entry_changed": False,
            "allocator_recomputed_for_counterfactual": False,
            "target_grid_searched": False,
            "retest_pnl_evaluated": False,
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
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "identity": IDENTITY,
                "five_year": {
                    "floor": report["five_year"]["floor_saturation"],
                    "canonical_2_5r": report["five_year"]["canonical_2_5r"],
                    "source_2r": report["five_year"]["source_2r_counterfactual"],
                    "retest": report["five_year"]["retest_coverage"],
                },
                "recent_two_year": {
                    "floor": report["recent_two_year"]["floor_saturation"],
                    "canonical_2_5r": report["recent_two_year"]["canonical_2_5r"],
                    "source_2r": report["recent_two_year"]["source_2r_counterfactual"],
                    "retest": report["recent_two_year"]["retest_coverage"],
                },
                "r66": {
                    "floor": report["r66_failed_holdout"]["floor_saturation"],
                    "canonical_2_5r": report["r66_failed_holdout"]["canonical_2_5r"],
                    "source_2r": report["r66_failed_holdout"]["source_2r_counterfactual"],
                    "retest": report["r66_failed_holdout"]["retest_coverage"],
                },
                "decision": report["decision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
