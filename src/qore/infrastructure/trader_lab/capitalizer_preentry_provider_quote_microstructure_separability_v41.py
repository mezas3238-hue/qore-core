"""Cross-era STOP/TARGET separability for frozen V41 microstructure 18D.\n\nThe frozen V37 cross-era protocol is materialized on this research branch so\nV41 reuses the exact predeclared scoring contract without changing any gate.\n"""

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
    capitalizer_preentry_full_stop_causal_separability_v37 as v37,
)
from qore.infrastructure.trader_lab import (
    capitalizer_preentry_provider_quote_microstructure_v41 as v41,
)
from qore.infrastructure.trader_lab import (
    capitalizer_regularized_causal_state_space_v25 as v25,
)

IDENTITY = (
    "QORE_CAPITALIZER_PREENTRY_PROVIDER_QUOTE_MICROSTRUCTURE_SEPARABILITY_V41"
)
PERIOD_SPECS = (
    ("DEVELOPMENT_2024_2026", "development", 948),
    ("CONSUMED_VALIDATION_2022_2024", "validation", 1034),
    ("CONSUMED_RESERVED_2020_2022", "reserved", 1088),
)


def _aware(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("V41 requires timezone-aware timestamp")
    return parsed


def _original_ledger(
    root: Path,
    *,
    expected: int,
) -> tuple[milestone.SimulatedTrade, ...]:
    ledgers = router._load_selected(root, expected=expected)
    rows = ledgers[milestone.ProtectionMode.ORIGINAL.value]
    if len(rows) != expected:
        raise ValueError("V41 selected population count drift")
    return rows


def _states_for_period(
    microstructure_root: Path,
    *,
    period: str,
) -> dict[tuple[str, str], v41.ProviderQuoteMicrostructureState]:
    return v41.load_states(microstructure_root, period=period)


def _coverage(
    ledger: tuple[milestone.SimulatedTrade, ...],
    states: dict[tuple[str, str], v41.ProviderQuoteMicrostructureState],
) -> dict[str, object]:
    ledger_keys = {(row.symbol, row.entry_at) for row in ledger}
    state_keys = set(states)
    missing = ledger_keys - state_keys
    extra = state_keys - ledger_keys
    if missing or extra:
        raise ValueError(
            "V41 exact entrant coverage mismatch: "
            f"missing={len(missing)} extra={len(extra)}"
        )
    return {
        "selected_entrants": len(ledger_keys),
        "microstructure_states": len(state_keys),
        "coverage": "1",
        "missing": 0,
        "extra": 0,
    }


def _labeled_states(
    *,
    period: str,
    ledger: tuple[milestone.SimulatedTrade, ...],
    states: dict[tuple[str, str], v41.ProviderQuoteMicrostructureState],
) -> tuple[v37.LabeledEntryState, ...]:
    result: list[v37.LabeledEntryState] = []
    for trade in sorted(
        ledger,
        key=lambda row: (_aware(row.entry_at), row.symbol),
    ):
        state = states[(trade.symbol, trade.entry_at)]

        # Freeze the causal vector before touching terminal label/economics.
        vector = tuple(float(value) for value in state.vector)
        if len(vector) != len(v41.FEATURE_NAMES):
            raise ValueError("V41 feature dimension drift")
        if any(not math.isfinite(value) for value in vector):
            raise ValueError("V41 vector contains non-finite value")

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
                vector=vector,
            )
        )
    if not result:
        raise ValueError(f"V41 {period} produced no STOP/TARGET states")
    return tuple(result)


def build_report(
    development_root: Path,
    validation_root: Path,
    reserved_root: Path,
    microstructure_root: Path,
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
        states = _states_for_period(microstructure_root, period=period)
        coverage = _coverage(ledger, states)
        if coverage["selected_entrants"] != expected:
            raise ValueError("V41 exact selected population count drift")
        coverage_by_period[period] = coverage
        states_by_period[period] = _labeled_states(
            period=period,
            ledger=ledger,
            states=states,
        )

    models = {
        period: v25._fit_model(
            period=f"{period}:V41_PROVIDER_MICROSTRUCTURE_STOP_RISK",
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
        state
        for period in states_by_period
        for state in states_by_period[period]
    )
    report: dict[str, Any] = {
        "identity": IDENTITY,
        "evaluation": "PREENTRY_STOP_VS_TARGET_PROVIDER_MICROSTRUCTURE_SEPARABILITY",
        "feature_source": "PROVIDER_NATIVE_BID_ASK_PREENTRY_60S_ONLY_18D",
        "feature_dimension": len(v41.FEATURE_NAMES),
        "feature_names": v41.FEATURE_NAMES,
        "v11_features_used": False,
        "v38_geometry_features_used": False,
        "v40_m1_path_features_used": False,
        "training_label": "ORIGINAL_EXIT_REASON_STOP_VS_TARGET",
        "stop_target_labels_used_as_features": False,
        "current_outcome_visible_to_features": False,
        "future_exit_visible_to_features": False,
        "future_mfe_mae_visible_to_features": False,
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
            "PREDECLARE_WINNER_PRESERVING_CAUSAL_POLICY_AFTER_V41"
            if representation_supported
            else (
                "V41_PROVIDER_MICROSTRUCTURE_REPRESENTATION_FALSIFIED_"
                "REQUIRE_SYNCHRONIZED_CROSS_MARKET_REGIME_STATE"
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
    stem = "capitalizer-preentry-provider-quote-microstructure-separability-v41"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-states.jsonl").open("w", encoding="utf-8") as handle:
        for state in states:
            handle.write(json.dumps(asdict(state), sort_keys=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("development_root", type=Path)
    parser.add_argument("validation_root", type=Path)
    parser.add_argument("reserved_root", type=Path)
    parser.add_argument("microstructure_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    report, states = build_report(
        args.development_root,
        args.validation_root,
        args.reserved_root,
        args.microstructure_root,
    )
    write_report(report, states, args.output)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
