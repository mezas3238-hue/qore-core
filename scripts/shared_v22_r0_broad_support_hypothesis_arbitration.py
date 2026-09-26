"""V22-R0 broad-support hypothesis arbitration for Shared.

DeepSeek and Claude converge on temporal local-vs-broad reasoning but disagree
on the mechanism behind V21 false-winner marks.  This research-only forensic
stage does not change Shared decisions.  It measures the bounded causal history
present at each V21 selected mark so the competing explanations can be
falsified before V22 adds new policy.

No symbol, market, fold, trader, methodology, current PnL, sizing, risk budget,
order or broker identity is used as an inference feature.  CLOSED outcome is
used only to label forensic groups after V21 has made its frozen selection.
"""

# ruff: noqa: E501,I001

from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any

import numpy as np
import shared_multi_state_competing_hazard_v20 as v20
import shared_relational_adversity_challenge_survival_v21 as v21

IDENTITY = "QORE_SHARED_V22_R0_BROAD_SUPPORT_HYPOTHESIS_ARBITRATION"
SCHEMA = "qore.shared.v22_r0_broad_support_hypothesis_arbitration"
SOURCE_V6_RUN = 36131607443
SOURCE_V21_RUN = 36156421332

WINDOWS = (v21.TRAIN_WINDOW, *v21.VALIDATION_WINDOWS)
HISTORY_CAP = 12


def _ratio(n: int, d: int) -> str:
    return str(Decimal(n) / Decimal(d)) if d else "0"


def _streak(values: list[bool]) -> int:
    total = 0
    for value in reversed(values):
        if not value:
            break
        total += 1
    return total


def _delta(values: list[int], lag: int) -> int:
    if len(values) <= lag:
        return 0
    return values[-1] - values[-1 - lag]


def _fraction(values: list[bool], width: int) -> Decimal:
    sample = values[-width:]
    if not sample:
        return Decimal("0")
    return Decimal(sum(sample)) / Decimal(len(sample))


def _profile(
    *,
    trade: dict[str, Any],
    item: dict[str, Any],
) -> dict[str, object]:
    target = item["row"]
    rows = v20._eligible(trade)
    index = next(
        i
        for i, row in enumerate(rows)
        if row["as_of"] == target["as_of"]
    )
    history = rows[: index + 1][-HISTORY_CAP:]
    reserves = [
        int(row["environment_support_bps"])
        - int(row["environment_adverse_bps"])
        for row in history
    ]
    positive = [value > 0 for value in reserves]
    named_support = [
        str(row["environment_state"]) in {"SUPPORTIVE", "STABILIZING"}
        for row in history
    ]
    challenge = item["challenge"]
    current = history[-1]
    geometry_balance = (
        int(current["geometry_recovery_horizon_count"])
        - int(current["geometry_collapse_horizon_count"])
    )
    futures_balance = (
        int(current["futures_recovery_evidence_bps"])
        - int(current["futures_terminal_evidence_bps"])
    )
    return {
        "actual": str(trade["actual"]),
        "bars_before_canonical_exit": int(current["bars_before_canonical_exit"]),
        "challenge_state": challenge.state.value,
        "environment_state": str(current["environment_state"]),
        "path_state": str(current["path_state"]),
        "recovery_state": str(current["recovery_challenge_state"]),
        "terminal_state": str(current["terminal_failure_state"]),
        "history_observations": len(history),
        "broad_reserve_bps": reserves[-1],
        "broad_reserve_delta_1": _delta(reserves, 1),
        "broad_reserve_delta_3": _delta(reserves, 3),
        "broad_reserve_delta_6": _delta(reserves, 6),
        "broad_positive_streak": _streak(positive),
        "broad_named_support_streak": _streak(named_support),
        "broad_positive_fraction_4": str(_fraction(positive, 4)),
        "broad_positive_fraction_8": str(_fraction(positive, 8)),
        "broad_positive_fraction_12": str(_fraction(positive, 12)),
        "challenge_broad_velocity_bps": int(challenge.broad_support_velocity_bps),
        "challenge_local_velocity_bps": int(challenge.local_pressure_velocity_bps),
        "challenge_recovery_reserve_bps": int(challenge.recovery_reserve_bps),
        "challenge_recovery_velocity_bps": int(challenge.recovery_velocity_bps),
        "challenge_terminal_convergence_bps": int(challenge.terminal_convergence_bps),
        "uncertainty_bps": int(challenge.uncertainty_bps),
        "geometry_horizon_balance": geometry_balance,
        "futures_recovery_minus_terminal_bps": futures_balance,
    }


def _med(values: list[int]) -> str | None:
    return None if not values else str(Decimal(str(median(values))))


def _group(profiles: list[dict[str, object]]) -> dict[str, object]:
    if not profiles:
        return {"count": 0}
    ints = (
        "bars_before_canonical_exit",
        "history_observations",
        "broad_reserve_bps",
        "broad_reserve_delta_1",
        "broad_reserve_delta_3",
        "broad_reserve_delta_6",
        "broad_positive_streak",
        "broad_named_support_streak",
        "challenge_broad_velocity_bps",
        "challenge_local_velocity_bps",
        "challenge_recovery_reserve_bps",
        "challenge_recovery_velocity_bps",
        "challenge_terminal_convergence_bps",
        "uncertainty_bps",
        "geometry_horizon_balance",
        "futures_recovery_minus_terminal_bps",
    )
    n = len(profiles)
    return {
        "count": n,
        "medians": {
            key: _med([int(profile[key]) for profile in profiles])
            for key in ints
        },
        "rates": {
            "broad_reserve_positive": _ratio(
                sum(int(profile["broad_reserve_bps"]) > 0 for profile in profiles), n
            ),
            "broad_velocity_negative": _ratio(
                sum(int(profile["challenge_broad_velocity_bps"]) < 0 for profile in profiles), n
            ),
            "broad_positive_streak_ge_4": _ratio(
                sum(int(profile["broad_positive_streak"]) >= 4 for profile in profiles), n
            ),
            "named_support_streak_ge_4": _ratio(
                sum(int(profile["broad_named_support_streak"]) >= 4 for profile in profiles), n
            ),
            "recovery_reserve_positive": _ratio(
                sum(int(profile["challenge_recovery_reserve_bps"]) > 0 for profile in profiles), n
            ),
            "recovery_velocity_positive": _ratio(
                sum(int(profile["challenge_recovery_velocity_bps"]) > 0 for profile in profiles), n
            ),
            "futures_balance_positive": _ratio(
                sum(int(profile["futures_recovery_minus_terminal_bps"]) > 0 for profile in profiles), n
            ),
            "geometry_balance_positive": _ratio(
                sum(int(profile["geometry_horizon_balance"]) > 0 for profile in profiles), n
            ),
        },
    }


def _selected(
    *,
    trades: list[dict[str, Any]],
    probabilities: np.ndarray,
    meta: list[dict[str, Any]],
    threshold: Decimal,
) -> dict[int, dict[str, Any]]:
    chosen: dict[int, dict[str, Any]] = {}
    limit = float(threshold)
    for probability, item in zip(probabilities, meta, strict=True):
        trade_index = int(item["trade_index"])
        if trade_index in chosen:
            continue
        if v21._relational_veto(item["challenge"]):
            continue
        if float(probability) > limit:
            continue
        chosen[trade_index] = item
    return chosen


def run(v6_json: Path) -> dict[str, object]:
    ledger = json.loads(v6_json.read_text())
    if ledger["identity"] != "QORE_SHARED_VT08_INDEX_STOP_TARGET_DISCRIMINATION_V6":
        raise ValueError("unexpected frozen external falsification ledger identity")

    hazard_model, categories = v21._fit_hazard(ledger)
    train_trades = list(ledger[v21.TRAIN_WINDOW]["rows"])
    survival_model, _, _, train_probabilities, train_meta = v21._fit_survival(
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
        raise ValueError("V21 frozen selection threshold unavailable")

    windows: dict[str, object] = {}
    for key in WINDOWS:
        trades = list(ledger[key]["rows"])
        x_rows, _, _, meta = v21._candidate_dataset(
            hazard_model=hazard_model,
            categories=categories,
            trades=trades,
        )
        probabilities = survival_model.predict_proba(x_rows)[:, 1]
        chosen = _selected(
            trades=trades,
            probabilities=probabilities,
            meta=meta,
            threshold=threshold,
        )
        profiles = [
            _profile(trade=trades[index], item=item)
            for index, item in chosen.items()
        ]
        false_winners = [p for p in profiles if p["actual"] == "WIN"]
        true_losses = [p for p in profiles if p["actual"] == "LOSS"]
        windows[key] = {
            "selected": len(profiles),
            "false_winner_count": len(false_winners),
            "true_loss_count": len(true_losses),
            "false_winner": _group(false_winners),
            "true_loss": _group(true_losses),
            "false_winner_profiles": false_winners,
        }

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "source_v6_run": SOURCE_V6_RUN,
        "source_v21_run": SOURCE_V21_RUN,
        "v21_selection_threshold": str(threshold),
        "research_only": True,
        "decision_policy_changed": False,
        "runtime_actuation": False,
        "consumed_evidence_only": True,
        "fresh_holdout_opened": False,
        "runtime_current_position_pnl_used": False,
        "runtime_future_market_used": False,
        "runtime_symbol_identity_used": False,
        "runtime_market_identity_used": False,
        "runtime_methodology_identity_used": False,
        "runtime_fold_identity_used": False,
        "sizing_used": False,
        "risk_weighting_used": False,
        "closed_outcome_used_for_forensic_grouping_only": True,
        "purpose": {
            "deepseek_hypothesis": "stable broad support is protective under local adversity",
            "claude_hypothesis": "point-in-time broad support may be temporally unstable or lagging",
            "arbitration": "measure bounded pre-selection broad persistence and velocity before changing V21 policy",
        },
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
