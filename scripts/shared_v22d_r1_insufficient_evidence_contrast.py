"""V22-D R1 forensic contrast of V21 INSUFFICIENT selections.

V22-C proved that treating every INSUFFICIENT candidate as non-actionable
destroys too much recall.  This stage does not change Shared decisions.  It
measures which already-causal point-in-time dimensions distinguish V21
INSUFFICIENT true losses from false winners across consumed windows.

The report is intentionally descriptive.  It does not fit a policy, search a
threshold, open a fresh holdout, or use identity features at inference.
CLOSED outcomes are used only for offline grouping after the frozen V21
selection is reproduced.
"""

# ruff: noqa: E501,I001

from __future__ import annotations

import argparse
import json
from collections import Counter
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any

import shared_relational_adversity_challenge_survival_v21 as v21

from qore.infrastructure.core_stack_v2.adversity_challenge_intelligence import (
    AdversityChallengeState,
)

IDENTITY = "QORE_SHARED_V22D_R1_INSUFFICIENT_EVIDENCE_CONTRAST"
SCHEMA = "qore.shared.v22d_r1_insufficient_evidence_contrast"

SOURCE_V6_RUN = 36131607443
SOURCE_V21_RUN = 36156421332
SOURCE_V22C_RUN = 36166613310

WINDOWS = (v21.TRAIN_WINDOW, *v21.VALIDATION_WINDOWS)

RAW_FIELDS = (
    "stop_pressure_bps",
    "stop_formation_bps",
    "target_capacity_bps",
    "recovery_strength_bps",
    "uncertainty_bps",
    "stop_hazard_proxy_bps",
    "target_hazard_proxy_bps",
    "risk_separation_margin_bps",
    "path_support_bps",
    "path_adverse_dominance_bps",
    "path_adverse_persistence_bps",
    "path_recovery_persistence_bps",
    "path_winner_protection_bps",
    "path_terminal_failure_risk_bps",
    "trajectory_support_bps",
    "trajectory_adversity_bps",
    "trajectory_deterioration_pressure_bps",
    "trajectory_deterioration_velocity_bps",
    "trajectory_recovery_velocity_bps",
    "environment_support_bps",
    "environment_adverse_bps",
    "environment_adverse_velocity_bps",
    "environment_recovery_velocity_bps",
    "futures_terminal_evidence_bps",
    "futures_recovery_evidence_bps",
    "futures_separation_margin_bps",
    "futures_horizon_agreement_bps",
    "geometry_structural_agreement_bps",
)

DERIVED_FIELDS = (
    "environment_balance_bps",
    "path_balance_bps",
    "recovery_minus_stop_bps",
    "futures_balance_bps",
    "trajectory_balance_bps",
    "terminal_minus_winner_protection_bps",
)


def _ratio(n: int, d: int) -> str:
    return "0" if d <= 0 else str(Decimal(n) / Decimal(d))


def _derived(row: dict[str, Any]) -> dict[str, int]:
    return {
        "environment_balance_bps": int(row["environment_support_bps"])
        - int(row["environment_adverse_bps"]),
        "path_balance_bps": int(row["path_support_bps"])
        - int(row["path_adverse_dominance_bps"]),
        "recovery_minus_stop_bps": int(row["recovery_strength_bps"])
        - int(row["stop_pressure_bps"]),
        "futures_balance_bps": int(row["futures_recovery_evidence_bps"])
        - int(row["futures_terminal_evidence_bps"]),
        "trajectory_balance_bps": int(row["trajectory_support_bps"])
        - int(row["trajectory_adversity_bps"]),
        "terminal_minus_winner_protection_bps": int(
            row["path_terminal_failure_risk_bps"]
        )
        - int(row["path_winner_protection_bps"]),
    }


def _hazard_scores(
    *,
    hazard_model: Any,
    categories: dict[str, tuple[str, ...]],
    trades: list[dict[str, Any]],
) -> dict[tuple[int, str], dict[str, float]]:
    x_rows, _, _, meta = v21.v20._dataset(trades, categories)
    probabilities = hazard_model.predict_proba(x_rows)
    classes = tuple(str(value) for value in hazard_model.classes_)
    result: dict[tuple[int, str], dict[str, float]] = {}
    for values, (trade_index, row) in zip(probabilities, meta, strict=True):
        p = {cause: 0.0 for cause in v21.v20.CAUSES}
        for label, probability in zip(classes, values, strict=True):
            p[label] = float(probability)
        result[(trade_index, str(row["as_of"]))] = p
    return result


def _selected_insufficient(
    *,
    hazard_model: Any,
    survival_model: Any,
    categories: dict[str, tuple[str, ...]],
    trades: list[dict[str, Any]],
    threshold: Decimal,
) -> list[dict[str, object]]:
    x_rows, _, _, meta = v21._candidate_dataset(
        hazard_model=hazard_model,
        categories=categories,
        trades=trades,
    )
    survival_probabilities = survival_model.predict_proba(x_rows)[:, 1]
    hazards = _hazard_scores(
        hazard_model=hazard_model,
        categories=categories,
        trades=trades,
    )
    chosen: dict[int, dict[str, object]] = {}
    limit = float(threshold)

    for probability, item in zip(survival_probabilities, meta, strict=True):
        trade_index = int(item["trade_index"])
        if trade_index in chosen:
            continue
        challenge = item["challenge"]
        if v21._relational_veto(challenge) or float(probability) > limit:
            continue
        if challenge.state != AdversityChallengeState.INSUFFICIENT:
            continue

        row = item["row"]
        hazard = hazards[(trade_index, str(row["as_of"]))]
        adverse = hazard[v21.v20.CAUSE_STOP] + hazard[v21.v20.CAUSE_TERMINAL]
        favorable = hazard[v21.v20.CAUSE_TARGET] + hazard[v21.v20.CAUSE_RECOVERY]
        values: dict[str, object] = {
            "actual": str(trades[trade_index]["actual"]),
            "bars_before_canonical_exit": int(row["bars_before_canonical_exit"]),
            "bar_index": int(row["bar_index"]),
            "survival_probability": float(probability),
            "hazard_adverse": adverse,
            "hazard_favorable": favorable,
            "hazard_margin": adverse - favorable,
            "hazard_stop": hazard[v21.v20.CAUSE_STOP],
            "hazard_terminal": hazard[v21.v20.CAUSE_TERMINAL],
            "hazard_recovery": hazard[v21.v20.CAUSE_RECOVERY],
            "hazard_target": hazard[v21.v20.CAUSE_TARGET],
            "environment_state": str(row["environment_state"]),
            "path_state": str(row["path_state"]),
            "recovery_state": str(row["recovery_challenge_state"]),
            "terminal_state": str(row["terminal_failure_state"]),
        }
        for field in RAW_FIELDS:
            values[field] = int(row[field])
        values.update(_derived(row))
        chosen[trade_index] = values

    return list(chosen.values())


def _med(values: list[float]) -> str | None:
    return None if not values else str(Decimal(str(median(values))))


def _group(rows: list[dict[str, object]]) -> dict[str, object]:
    if not rows:
        return {"count": 0}
    numeric = (
        "bars_before_canonical_exit",
        "bar_index",
        "survival_probability",
        "hazard_adverse",
        "hazard_favorable",
        "hazard_margin",
        "hazard_stop",
        "hazard_terminal",
        "hazard_recovery",
        "hazard_target",
        *RAW_FIELDS,
        *DERIVED_FIELDS,
    )
    categorical = (
        "environment_state",
        "path_state",
        "recovery_state",
        "terminal_state",
    )
    return {
        "count": len(rows),
        "medians": {
            field: _med([float(row[field]) for row in rows])
            for field in numeric
        },
        "categorical_counts": {
            field: dict(sorted(Counter(str(row[field]) for row in rows).items()))
            for field in categorical
        },
    }


def _window(
    *,
    hazard_model: Any,
    survival_model: Any,
    categories: dict[str, tuple[str, ...]],
    trades: list[dict[str, Any]],
    threshold: Decimal,
) -> dict[str, object]:
    rows = _selected_insufficient(
        hazard_model=hazard_model,
        survival_model=survival_model,
        categories=categories,
        trades=trades,
        threshold=threshold,
    )
    losses = [row for row in rows if row["actual"] == "LOSS"]
    winners = [row for row in rows if row["actual"] == "WIN"]
    return {
        "sample": len(trades),
        "selected_insufficient": len(rows),
        "true_loss_count": len(losses),
        "false_winner_count": len(winners),
        "precision": _ratio(len(losses), len(rows)),
        "true_loss": _group(losses),
        "false_winner": _group(winners),
        "false_winner_profiles": winners,
    }


def run(v6_json: Path) -> dict[str, object]:
    ledger = json.loads(v6_json.read_text())
    if ledger["identity"] != "QORE_SHARED_VT08_INDEX_STOP_TARGET_DISCRIMINATION_V6":
        raise ValueError("unexpected frozen external falsification ledger identity")

    hazard_model, categories = v21._fit_hazard(ledger)
    train_trades = list(ledger[v21.TRAIN_WINDOW]["rows"])
    (
        survival_model,
        _,
        _,
        train_probabilities,
        train_meta,
    ) = v21._fit_survival(
        hazard_model=hazard_model,
        categories=categories,
        trades=train_trades,
    )
    threshold, _, _ = v21._choose_threshold(
        trades=train_trades,
        probabilities=train_probabilities,
        meta=train_meta,
    )
    if threshold is None:
        raise ValueError("V21 frozen threshold unavailable")

    windows = {
        key: _window(
            hazard_model=hazard_model,
            survival_model=survival_model,
            categories=categories,
            trades=list(ledger[key]["rows"]),
            threshold=threshold,
        )
        for key in WINDOWS
    }

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "source_v6_run": SOURCE_V6_RUN,
        "source_v21_run": SOURCE_V21_RUN,
        "source_v22c_run": SOURCE_V22C_RUN,
        "research_only": True,
        "decision_policy_changed": False,
        "v21_survival_threshold_frozen": str(threshold),
        "consumed_evidence_only": True,
        "fresh_holdout_opened": False,
        "runtime_current_position_pnl_used": False,
        "runtime_future_market_used": False,
        "runtime_symbol_identity_used": False,
        "runtime_market_identity_used": False,
        "runtime_methodology_identity_used": False,
        "runtime_calendar_identity_used": False,
        "runtime_fold_identity_used": False,
        "sizing_used": False,
        "risk_weighting_used": False,
        "runtime_actuation": False,
        "closed_outcome_used_for_forensic_grouping_only": True,
        "purpose": (
            "contrast frozen V21 INSUFFICIENT true losses vs false winners "
            "before defining any new V22 policy"
        ),
        "windows": windows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--v6-json", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    payload = run(args.v6_json)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
