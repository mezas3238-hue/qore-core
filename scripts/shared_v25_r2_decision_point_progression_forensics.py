"""V25-R2 decision-point progression forensics for Shared Core.

V25-R1 produced a real but incomplete result: loss recall improved on five-year
and recent-two-year consumed windows without adding false winners, while R66
remained unchanged and below winner-safety floors.

This stage inspects the exact frozen V21 decision point, not the first candidate
in a trade. It separates:
- raw event-model emission,
- filtered event readiness,
- conditional adverse/favorable direction,
- one/two/three-step progression in those quantities.

The goal is to determine whether false winner marks are adverse *plateaus*
while true losses show terminal *progression*. No policy is changed here.
Closed outcome and bars-before-exit are used only after selection for offline
forensic grouping. Fresh holdout remains closed.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import shared_dynamic_bayesian_causal_state_v24 as v24
import shared_relational_adversity_challenge_survival_v21 as v21
import shared_v25_r1_factorized_posterior_arbitration as v25r1

IDENTITY = "QORE_SHARED_V25_R2_DECISION_POINT_PROGRESSION_FORENSICS"
SCHEMA = "qore.shared.v25_r2_decision_point_progression_forensics"

SOURCE_V6_RUN = 36131607443
SOURCE_V21_RUN = 36156421332
SOURCE_V24_RUN = 36185092496
SOURCE_V25_R1_RUN = 36187557918

WINDOWS = (v21.TRAIN_WINDOW, *v21.VALIDATION_WINDOWS)

FIELDS = (
    "posterior_event_bps",
    "posterior_adverse_conditional_bps",
    "posterior_favorable_conditional_bps",
    "posterior_directional_margin_bps",
    "posterior_event_delta1_bps",
    "posterior_event_delta2_bps",
    "posterior_event_delta3_bps",
    "posterior_adverse_conditional_delta1_bps",
    "posterior_adverse_conditional_delta2_bps",
    "posterior_adverse_conditional_delta3_bps",
    "raw_event_bps",
    "raw_adverse_bps",
    "raw_favorable_bps",
    "raw_adverse_conditional_bps",
    "raw_directional_margin_bps",
    "raw_event_delta1_bps",
    "raw_event_delta2_bps",
    "raw_event_delta3_bps",
    "raw_adverse_delta1_bps",
    "raw_adverse_delta2_bps",
    "raw_adverse_delta3_bps",
    "belief_evidence_count",
    "bars_before_canonical_exit",
    "survival_probability",
)


def _quantile(values: list[float], fraction: float) -> str | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return str(ordered[0])
    position = (len(ordered) - 1) * fraction
    left = int(position)
    right = min(left + 1, len(ordered) - 1)
    weight = position - left
    return str(ordered[left] * (1.0 - weight) + ordered[right] * weight)


def _summary(rows: list[dict[str, Any]]) -> dict[str, object]:
    if not rows:
        return {"count": 0}
    numeric: dict[str, object] = {}
    for field in FIELDS:
        values = [float(row[field]) for row in rows]
        numeric[field] = {
            "min": str(min(values)),
            "p10": _quantile(values, 0.10),
            "p25": _quantile(values, 0.25),
            "p50": _quantile(values, 0.50),
            "p75": _quantile(values, 0.75),
            "p90": _quantile(values, 0.90),
            "max": str(max(values)),
        }
    return {
        "count": len(rows),
        "numeric": numeric,
        "posterior_direction_counts": dict(
            sorted(Counter(str(row["posterior_direction"]) for row in rows).items())
        ),
        "raw_direction_counts": dict(
            sorted(Counter(str(row["raw_direction"]) for row in rows).items())
        ),
    }


def _conditional(adverse: int, favorable: int) -> tuple[int, int, int]:
    total = adverse + favorable
    if total <= 0:
        return 5_000, 5_000, 0
    adverse_conditional = adverse * 10_000 // total
    favorable_conditional = favorable * 10_000 // total
    return (
        adverse_conditional,
        favorable_conditional,
        adverse_conditional - favorable_conditional,
    )


def _raw_map(
    *,
    event_model: Any,
    trades: list[dict[str, Any]],
    categories: dict[str, tuple[str, ...]],
) -> dict[tuple[int, str], dict[str, int]]:
    x_rows, _, _, meta = v24.v23._dataset(trades, categories)
    probabilities = event_model.predict_proba(x_rows)
    classes = tuple(str(value) for value in event_model.classes_)
    result: dict[tuple[int, str], dict[str, int]] = {}

    for values, (trade_index, row) in zip(probabilities, meta, strict=True):
        p = {state: 0.0 for state in v24.STATES}
        for label, probability in zip(classes, values, strict=True):
            p[label] = float(probability)
        raw_adverse = int(
            round(
                (
                    p[v21.v20.CAUSE_STOP]
                    + p[v21.v20.CAUSE_TERMINAL]
                )
                * 10_000
            )
        )
        raw_favorable = int(
            round(
                (
                    p[v21.v20.CAUSE_RECOVERY]
                    + p[v21.v20.CAUSE_TARGET]
                )
                * 10_000
            )
        )
        raw_no_event = int(round(p[v21.v20.CAUSE_NONE] * 10_000))
        adverse_conditional, favorable_conditional, margin = _conditional(
            raw_adverse,
            raw_favorable,
        )
        result[(trade_index, str(row["as_of"]))] = {
            "event_bps": max(0, min(10_000, 10_000 - raw_no_event)),
            "adverse_bps": raw_adverse,
            "favorable_bps": raw_favorable,
            "adverse_conditional_bps": adverse_conditional,
            "favorable_conditional_bps": favorable_conditional,
            "directional_margin_bps": margin,
        }
    return result


def _deltas(
    series: list[dict[str, int]],
    index: int,
    field: str,
) -> tuple[int, int, int]:
    current = int(series[index][field])

    def delta(back: int) -> int:
        prior_index = max(0, index - back)
        return current - int(series[prior_index][field])

    return delta(1), delta(2), delta(3)


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
    surface = v25r1._surface(
        hazard_model=hazard_model,
        survival_model=survival_model,
        event_model=event_model,
        categories=categories,
        transition_bps=transition_bps,
        trades=trades,
    )
    raw = _raw_map(
        event_model=event_model,
        trades=trades,
        categories=categories,
    )
    factorized_by_trade: dict[int, list[tuple[str, Any]]] = defaultdict(list)
    raw_by_trade: dict[int, list[tuple[str, dict[str, int]]]] = defaultdict(list)

    for item in surface:
        trade_index = int(item["trade_index"])
        as_of = str(item["row"]["as_of"])
        factorized_by_trade[trade_index].append(
            (as_of, item["factorized_state"])
        )
        raw_by_trade[trade_index].append((as_of, raw[(trade_index, as_of)]))

    for items in factorized_by_trade.values():
        items.sort(key=lambda pair: pair[0])
    for items in raw_by_trade.values():
        items.sort(key=lambda pair: pair[0])

    factorized_index = {
        trade_index: {as_of: index for index, (as_of, _) in enumerate(items)}
        for trade_index, items in factorized_by_trade.items()
    }
    raw_index = {
        trade_index: {as_of: index for index, (as_of, _) in enumerate(items)}
        for trade_index, items in raw_by_trade.items()
    }

    selected: dict[int, dict[str, Any]] = {}
    limit = float(threshold)
    for item in surface:
        trade_index = int(item["trade_index"])
        if trade_index in selected:
            continue
        if v21._relational_veto(item["challenge"]):
            continue
        if float(item["survival_probability"]) > limit:
            continue
        selected[trade_index] = item

    groups: dict[str, list[dict[str, Any]]] = {
        "selected_true_loss": [],
        "selected_false_winner": [],
    }

    for trade_index, item in selected.items():
        actual = str(trades[trade_index]["actual"])
        as_of = str(item["row"]["as_of"])

        factorized_items = factorized_by_trade[trade_index]
        factorized_values = [
            {
                "event_bps": pair[1].state.event_bps,
                "adverse_conditional_bps": pair[1].state.adverse_conditional_bps,
            }
            for pair in factorized_items
        ]
        f_index = factorized_index[trade_index][as_of]
        factorized = factorized_items[f_index][1]
        event_deltas = _deltas(factorized_values, f_index, "event_bps")
        conditional_deltas = _deltas(
            factorized_values,
            f_index,
            "adverse_conditional_bps",
        )

        raw_items = raw_by_trade[trade_index]
        raw_values = [pair[1] for pair in raw_items]
        r_index = raw_index[trade_index][as_of]
        raw_now = raw_items[r_index][1]
        raw_event_deltas = _deltas(raw_values, r_index, "event_bps")
        raw_adverse_deltas = _deltas(raw_values, r_index, "adverse_bps")

        record = {
            "posterior_event_bps": factorized.state.event_bps,
            "posterior_adverse_conditional_bps": (
                factorized.state.adverse_conditional_bps
            ),
            "posterior_favorable_conditional_bps": (
                factorized.state.favorable_conditional_bps
            ),
            "posterior_directional_margin_bps": (
                factorized.state.directional_margin_bps
            ),
            "posterior_event_delta1_bps": event_deltas[0],
            "posterior_event_delta2_bps": event_deltas[1],
            "posterior_event_delta3_bps": event_deltas[2],
            "posterior_adverse_conditional_delta1_bps": conditional_deltas[0],
            "posterior_adverse_conditional_delta2_bps": conditional_deltas[1],
            "posterior_adverse_conditional_delta3_bps": conditional_deltas[2],
            "raw_event_bps": raw_now["event_bps"],
            "raw_adverse_bps": raw_now["adverse_bps"],
            "raw_favorable_bps": raw_now["favorable_bps"],
            "raw_adverse_conditional_bps": raw_now["adverse_conditional_bps"],
            "raw_directional_margin_bps": raw_now["directional_margin_bps"],
            "raw_event_delta1_bps": raw_event_deltas[0],
            "raw_event_delta2_bps": raw_event_deltas[1],
            "raw_event_delta3_bps": raw_event_deltas[2],
            "raw_adverse_delta1_bps": raw_adverse_deltas[0],
            "raw_adverse_delta2_bps": raw_adverse_deltas[1],
            "raw_adverse_delta3_bps": raw_adverse_deltas[2],
            "belief_evidence_count": factorized.state.evidence_count,
            "bars_before_canonical_exit": int(
                item["row"]["bars_before_canonical_exit"]
            ),
            "survival_probability": float(item["survival_probability"]),
            "posterior_direction": factorized.state.dominant_direction,
            "raw_direction": (
                "ADVERSE"
                if raw_now["directional_margin_bps"] > 0
                else "FAVORABLE"
                if raw_now["directional_margin_bps"] < 0
                else "CONTESTED"
            ),
        }
        groups[
            "selected_true_loss"
            if actual == "LOSS"
            else "selected_false_winner"
        ].append(record)

    return {
        "sample": len(trades),
        "selected_trade_count": len(selected),
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
        "source_v25_r1_run": SOURCE_V25_R1_RUN,
        "research_only": True,
        "decision_policy_changed": False,
        "exact_v21_decision_point_forensics": True,
        "raw_emission_vs_filtered_posterior": True,
        "progression_deltas_only_use_current_and_prior_rows": True,
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
        "closed_outcome_and_exit_distance_used_for_offline_grouping_only": True,
        "v21_survival_threshold_frozen": str(threshold),
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
