"""Cross-era STOP/TARGET separability using V40 path-only 18D state.

The V11/V38 blocks are intentionally excluded. V40 isolates whether genuinely
new provider-native pre-entry path information transports across eras.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_r_milestone_protection_2r_v1 as milestone,
)
from qore.infrastructure.trader_lab import (
    capitalizer_contextual_stability_router_2r_v1 as router,
)
from qore.infrastructure.trader_lab import (
    capitalizer_preentry_causal_m1_path_collector_v40 as collector,
)
from qore.infrastructure.trader_lab import (
    capitalizer_preentry_causal_m1_path_state_v40 as path_state,
)
from qore.infrastructure.trader_lab import (
    capitalizer_preentry_full_stop_causal_separability_v37 as v37,
)
from qore.infrastructure.trader_lab import (
    capitalizer_regularized_causal_state_space_v25 as v25,
)

IDENTITY = "QORE_CAPITALIZER_PREENTRY_CAUSAL_M1_PATH_STATE_SEPARABILITY_V40"
FEATURE_DIMENSION = len(path_state.FEATURE_NAMES)

PERIOD_SPECS = (
    ("DEVELOPMENT_2024_2026", "development", 948),
    ("CONSUMED_VALIDATION_2022_2024", "validation", 1034),
    ("CONSUMED_RESERVED_2020_2022", "reserved", 1088),
)


def _aware(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("V40 requires timezone-aware timestamp")
    return parsed


def _original_ledger(
    root: Path,
    *,
    expected: int,
) -> tuple[milestone.SimulatedTrade, ...]:
    ledgers = router._load_selected(root, expected=expected)
    return ledgers[milestone.ProtectionMode.ORIGINAL.value]


def _coverage(
    ledger: tuple[milestone.SimulatedTrade, ...],
    paths: dict[tuple[str, str], collector.SelectedPathState],
) -> dict[str, object]:
    ledger_keys = {(row.symbol, row.entry_at) for row in ledger}
    path_keys = set(paths)
    missing = ledger_keys - path_keys
    extra = path_keys - ledger_keys
    if missing or extra:
        raise ValueError(
            "V40 exact entrant coverage mismatch: "
            f"missing={len(missing)} extra={len(extra)}"
        )
    return {
        "selected_entrants": len(ledger_keys),
        "path_rows": len(path_keys),
        "coverage": "1",
        "missing": 0,
        "extra": 0,
    }


def _labeled_states(
    *,
    period: str,
    ledger: tuple[milestone.SimulatedTrade, ...],
    paths: dict[tuple[str, str], collector.SelectedPathState],
) -> tuple[v37.LabeledEntryState, ...]:
    result: list[v37.LabeledEntryState] = []
    for trade in sorted(
        ledger,
        key=lambda row: (_aware(row.entry_at), row.symbol),
    ):
        selected = paths[(trade.symbol, trade.entry_at)]

        # Freeze the causal path vector before touching the terminal label.
        frozen_vector = tuple(float(value) for value in selected.path.vector)
        if len(frozen_vector) != FEATURE_DIMENSION:
            raise ValueError("V40 path feature dimension drift")
        if any(not math.isfinite(value) for value in frozen_vector):
            raise ValueError("V40 path vector contains non-finite value")

        label = v37._label_original(trade)
        if label is None:
            continue
        result.append(
            v37.LabeledEntryState(
                period=period,
                symbol=trade.symbol,
                session=trade.session,
                operating_date=trade.operating_date,
                entry_at=trade.entry_at,
                label=label,
                original_realized_r=trade.realized_gross_r,
                vector=frozen_vector,
            )
        )
    if not result:
        raise ValueError(f"V40 {period} produced no STOP/TARGET states")
    return tuple(result)


def build_report(
    development_root: Path,
    validation_root: Path,
    reserved_root: Path,
    path_root: Path,
) -> tuple[dict[str, Any], tuple[v37.LabeledEntryState, ...]]:
    roots = {
        "development": development_root,
        "validation": validation_root,
        "reserved": reserved_root,
    }

    states_by_period: dict[str, tuple[v37.LabeledEntryState, ...]] = {}
    coverage_by_period: dict[str, dict[str, object]] = {}

    for period, slug, expected in PERIOD_SPECS:
        ledger = _original_ledger(roots[slug], expected=expected)
        paths = collector.load_path_rows(path_root, slug=slug)
        coverage = _coverage(ledger, paths)
        if coverage["selected_entrants"] != expected:
            raise ValueError("V40 selected population count drift")
        coverage_by_period[period] = coverage
        states_by_period[period] = _labeled_states(
            period=period,
            ledger=ledger,
            paths=paths,
        )

    models = {
        period: v25._fit_model(
            period=f"{period}:V40_PATH_ONLY_FULL_STOP_RISK",
            examples=v37._training_examples(states),
        )
        for period, states in states_by_period.items()
    }
    heldout = tuple(
        v37._heldout_report(
            heldout=period,
            states_by_period=states_by_period,
            models=models,
        )
        for period in states_by_period
    )
    representation_supported = all(
        row.both_external_auc_lower95_above_chance
        and row.consensus_auc_lower95_above_chance
        and row.target_count_preservation_at_least_90pct
        and row.risk_tail_enriched_above_base
        for row in heldout
    )

    all_states = tuple(
        row
        for period in states_by_period
        for row in states_by_period[period]
    )
    report: dict[str, Any] = {
        "identity": IDENTITY,
        "evaluation": "PREENTRY_STOP_VS_TARGET_CAUSAL_PATH_SEPARABILITY",
        "feature_source": "PROVIDER_NATIVE_PREENTRY_M1_PATH_ONLY_18D",
        "feature_dimension": FEATURE_DIMENSION,
        "feature_names": path_state.FEATURE_NAMES,
        "lookback_minutes": path_state.LOOKBACK_MINUTES,
        "v11_features_used": False,
        "v38_geometry_features_used": False,
        "training_label": "ORIGINAL_EXIT_REASON_STOP_VS_TARGET",
        "stop_target_labels_used_as_features": False,
        "current_outcome_visible_to_features": False,
        "future_exit_visible_to_features": False,
        "future_mfe_mae_visible_to_features": False,
        "entry_bar_used": False,
        "future_bar_used": False,
        "symbol_identity_feature_used": False,
        "date_identity_feature_used": False,
        "two_external_worlds_required": True,
        "l2_prior_strength_effective_trades": str(v25.L2_PRIOR_STRENGTH),
        "fixed_diagnostic_risk_quantile": str(v37.RISK_QUANTILE),
        "threshold_grid_searched": False,
        "policy_economics_run": False,
        "admission_changed": False,
        "sizing_changed": False,
        "protection_changed": False,
        "coverage_by_period": coverage_by_period,
        "heldout_results": [asdict(row) for row in heldout],
        "representation_transport_supported": representation_supported,
        "candidate_count": 0,
        "runtime_policy_candidate": False,
        "fresh_holdout_opened": False,
        "trader_certified": False,
        "next_phase": (
            "PREDECLARE_WINNER_PRESERVING_CAUSAL_POLICY_AFTER_V40"
            if representation_supported
            else (
                "V40_PATH_ONLY_REPRESENTATION_FALSIFIED_"
                "REQUIRE_SYNCHRONIZED_CROSS_MARKET_OR_REGIME_TRANSITION_STATE"
            )
        ),
    }
    return report, all_states


def write_report(
    report: dict[str, Any],
    states: tuple[v37.LabeledEntryState, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    stem = "capitalizer-preentry-causal-m1-path-state-separability-v40"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-states.jsonl").open(
        "w",
        encoding="utf-8",
    ) as handle:
        for row in states:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("development_root", type=Path)
    parser.add_argument("validation_root", type=Path)
    parser.add_argument("reserved_root", type=Path)
    parser.add_argument("path_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    report, states = build_report(
        args.development_root,
        args.validation_root,
        args.reserved_root,
        args.path_root,
    )
    write_report(report, states, args.output)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
