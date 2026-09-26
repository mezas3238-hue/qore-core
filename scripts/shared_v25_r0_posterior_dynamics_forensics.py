"""V25-R0 posterior-dynamics forensics for Shared Core.

V24's Bayesian filter ran successfully but changed zero frozen V21 decisions.
Before changing the filter again, this forensic stage measures the posterior
geometry at candidate decision points.

It reproduces V24 causally and groups candidate observations only after the
frozen decision has been made:
- V21 selected true losses;
- V21 selected false winners;
- survival-vetoed losses;
- survival-vetoed winners;
- relational-vetoed losses/winners.

CLOSED outcome is used only for offline grouping. No policy is fitted or
changed, no fresh holdout is opened, and no runtime PnL/future/identity/sizing
information is introduced.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

import shared_dynamic_bayesian_causal_state_v24 as v24
import shared_relational_adversity_challenge_survival_v21 as v21

IDENTITY = "QORE_SHARED_V25_R0_POSTERIOR_DYNAMICS_FORENSICS"
SCHEMA = "qore.shared.v25_r0_posterior_dynamics_forensics"

SOURCE_V6_RUN = 36131607443
SOURCE_V21_RUN = 36156421332
SOURCE_V24_RUN = 36185092496

WINDOWS = (v21.TRAIN_WINDOW, *v21.VALIDATION_WINDOWS)

NUMERIC_FIELDS = (
    "adverse_bps",
    "favorable_bps",
    "no_event_bps",
    "adverse_margin_bps",
    "favorable_margin_bps",
    "adverse_persistence",
    "favorable_persistence",
    "dominance_margin_bps",
    "entropy_bps",
    "confidence_bps",
    "survival_probability",
    "bars_before_canonical_exit",
)

MARGIN_LEVELS = (0, 100, 250, 500, 750, 1_000, 1_500, 2_000)
PERSISTENCE_LEVELS = (1, 2, 3, 4)


def _percentile(values: list[float], p: float) -> str | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return str(ordered[0])
    position = (len(ordered) - 1) * p
    left = int(position)
    right = min(left + 1, len(ordered) - 1)
    fraction = position - left
    value = ordered[left] * (1.0 - fraction) + ordered[right] * fraction
    return str(value)


def _summary(rows: list[dict[str, Any]]) -> dict[str, object]:
    if not rows:
        return {"count": 0}

    numeric: dict[str, object] = {}
    for field in NUMERIC_FIELDS:
        values = [float(row[field]) for row in rows]
        numeric[field] = {
            "p10": _percentile(values, 0.10),
            "p25": _percentile(values, 0.25),
            "p50": _percentile(values, 0.50),
            "p75": _percentile(values, 0.75),
            "p90": _percentile(values, 0.90),
            "min": str(min(values)),
            "max": str(max(values)),
        }

    adverse_grid: dict[str, int] = {}
    favorable_grid: dict[str, int] = {}
    for margin in MARGIN_LEVELS:
        for persistence in PERSISTENCE_LEVELS:
            key = f"M{margin}_P{persistence}"
            adverse_grid[key] = sum(
                int(row["adverse_margin_bps"]) >= margin
                and int(row["adverse_persistence"]) >= persistence
                for row in rows
            )
            favorable_grid[key] = sum(
                int(row["favorable_margin_bps"]) >= margin
                and int(row["favorable_persistence"]) >= persistence
                for row in rows
            )

    return {
        "count": len(rows),
        "numeric": numeric,
        "dominant_state_counts": dict(
            sorted(Counter(str(row["dominant_state"]) for row in rows).items())
        ),
        "adverse_confirmation_grid": adverse_grid,
        "favorable_confirmation_grid": favorable_grid,
    }


def _window(
    *,
    ledger: dict[str, Any],
    key: str,
    hazard_model: Any,
    survival_model: Any,
    event_model: Any,
    categories: dict[str, tuple[str, ...]],
    transition_bps: dict[str, dict[str, int]],
    threshold: Any,
) -> dict[str, object]:
    trades = list(ledger[key]["rows"])
    surface = v24._surface(
        hazard_model=hazard_model,
        survival_model=survival_model,
        event_model=event_model,
        categories=categories,
        transition_bps=transition_bps,
        trades=trades,
    )
    limit = float(threshold)
    groups: dict[str, list[dict[str, Any]]] = {
        "v21_selected_true_loss": [],
        "v21_selected_false_winner": [],
        "survival_vetoed_loss": [],
        "survival_vetoed_winner": [],
        "relational_vetoed_loss": [],
        "relational_vetoed_winner": [],
    }

    first_candidate_seen: set[int] = set()
    for item in surface:
        trade_index = int(item["trade_index"])
        if trade_index in first_candidate_seen:
            continue
        first_candidate_seen.add(trade_index)

        actual = str(trades[trade_index]["actual"])
        relational_veto = v21._relational_veto(item["challenge"])
        survival_veto = float(item["survival_probability"]) > limit
        state = item["dynamic_state"]
        row = item["row"]

        record = {
            "trade_index": trade_index,
            "actual": actual,
            "adverse_bps": state.adverse_bps,
            "favorable_bps": state.favorable_bps,
            "no_event_bps": state.no_event_bps,
            "adverse_margin_bps": state.adverse_margin_bps,
            "favorable_margin_bps": state.favorable_margin_bps,
            "adverse_persistence": state.adverse_persistence,
            "favorable_persistence": state.favorable_persistence,
            "dominance_margin_bps": state.belief.dominance_margin_bps,
            "entropy_bps": state.belief.entropy_bps,
            "confidence_bps": state.belief.confidence_bps,
            "dominant_state": state.belief.dominant_state,
            "survival_probability": float(item["survival_probability"]),
            "bars_before_canonical_exit": int(row["bars_before_canonical_exit"]),
        }

        suffix = "loss" if actual == "LOSS" else "winner"
        if relational_veto:
            groups[f"relational_vetoed_{suffix}"].append(record)
        elif survival_veto:
            groups[f"survival_vetoed_{suffix}"].append(record)
        else:
            groups[
                "v21_selected_true_loss"
                if actual == "LOSS"
                else "v21_selected_false_winner"
            ].append(record)

    return {
        "sample": len(trades),
        "candidate_trade_count": len(first_candidate_seen),
        "groups": {
            name: _summary(rows)
            for name, rows in groups.items()
        },
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

    event_model = v24.v23._fit_event_model(
        trades=train_trades,
        categories=categories,
    )
    transition_bps = v24._transition_matrix(train_trades)

    windows = {
        key: _window(
            ledger=ledger,
            key=key,
            hazard_model=hazard_model,
            survival_model=survival_model,
            event_model=event_model,
            categories=categories,
            transition_bps=transition_bps,
            threshold=threshold,
        )
        for key in WINDOWS
    }

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "source_v6_run": SOURCE_V6_RUN,
        "source_v21_run": SOURCE_V21_RUN,
        "source_v24_run": SOURCE_V24_RUN,
        "research_only": True,
        "decision_policy_changed": False,
        "posterior_forensics_only": True,
        "consumed_evidence_only": True,
        "fresh_holdout_opened": False,
        "runtime_current_position_pnl_used": False,
        "runtime_terminal_outcome_used": False,
        "runtime_future_market_used": False,
        "runtime_symbol_identity_used": False,
        "runtime_market_identity_used": False,
        "runtime_trader_identity_used": False,
        "runtime_methodology_identity_used": False,
        "runtime_calendar_identity_used": False,
        "runtime_fold_identity_used": False,
        "sizing_used": False,
        "risk_weighting_used": False,
        "runtime_actuation": False,
        "closed_outcome_used_for_forensic_grouping_only": True,
        "v21_survival_threshold_frozen": str(threshold),
        "transition_matrix_bps": transition_bps,
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
    print(
        json.dumps(
            {
                "identity": payload["identity"],
                "windows": payload["windows"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
