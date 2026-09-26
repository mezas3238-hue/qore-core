"""Shared VT31 causal tail-winner diagnostics V9.

Research-only diagnostic. R8 is discovery and R6 is consumed calibration.
R5 is deliberately not accepted as an input.

The diagnostic starts from the frozen V8 negative present-state population and
asks a narrower question: which CURRENT-MARKET facts distinguish rare,
high-payoff winners from ordinary losses inside states that otherwise look
adverse?

No runtime policy is created here. Outcome is used only as an offline label for
R8/R6 diagnostics.
"""
# ruff: noqa: E501
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_core_stack_v4_perception_first_v2 as v2
import vt31_core_stack_v4_perception_sequence_topology_v8 as v8
import vt31_core_stack_v4_perception_state_model_v5 as v5

SCHEMA = "qore.core_stack_v4.vt31.causal_tail_diagnostics.v9"

CATEGORICAL_FIELDS = (
    "sequence_chain",
    "sweep_alignment",
    "displacement_alignment",
    "fvg_alignment",
    "sweep_freshness",
    "displacement_freshness",
    "fvg_freshness",
    "sweep_displacement_order",
    "fvg_displacement_order",
    "alignment5",
    "alignment20",
    "perception_regime",
    "perception_transition",
    "momentum_state",
    "volatility_state",
    "structure_state",
    "peer_consensus",
    "first_peer_leader",
    "first_peer_lead_bucket",
    "pre_behavior_proxy",
    "prior_day_state_hr",
    "h4_state_hr",
    "h1_state_hr",
    "premarket_state_hr",
    "cash_open_state_hr",
    "position_in_prior_day_range_hr",
)

NUMERIC_FIELDS = (
    "trend_pressure",
    "range_pressure",
    "expansion_pressure",
    "exhaustion_pressure",
    "uncertainty_pressure",
    "pre_path_efficiency",
    "pre_overlap_rate",
    "pre_last5_range_fraction",
    "recent_path_efficiency_hr",
    "recent_overlap_rate_hr",
    "raid_depth_ref_hr",
    "current_path_vs_previous_hr",
    "reference_width_vs_prior5_hr",
)

RELATIONAL_VIEWS = (
    ("sequence_chain", "peer_consensus"),
    ("sequence_chain", "perception_transition"),
    ("sequence_chain", "cash_open_state_hr"),
    ("sequence_chain", "h1_state_hr"),
    ("displacement_alignment", "displacement_freshness", "peer_consensus"),
    ("sweep_alignment", "sweep_freshness", "perception_transition"),
    ("sweep_alignment", "displacement_alignment", "cash_open_state_hr"),
    ("alignment5", "alignment20", "peer_consensus"),
    ("perception_regime", "structure_state", "peer_consensus"),
    ("perception_transition", "structure_state", "peer_consensus"),
    ("h1_state_hr", "cash_open_state_hr", "peer_consensus"),
    ("position_in_prior_day_range_hr", "sequence_chain", "peer_consensus"),
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _bin(value: object) -> str:
    raw = str(value)
    if raw in {"unavailable", "None", "null", ""}:
        return "UNAVAILABLE"
    try:
        x = Decimal(raw)
    except Exception:
        return raw
    cuts = (
        Decimal("-0.50"),
        Decimal("-0.10"),
        Decimal("0"),
        Decimal("0.25"),
        Decimal("0.50"),
        Decimal("0.75"),
        Decimal("1.00"),
        Decimal("1.25"),
        Decimal("1.50"),
        Decimal("2.00"),
    )
    labels = (
        "LT_M050",
        "M050_M010",
        "M010_0",
        "0_025",
        "025_050",
        "050_075",
        "075_100",
        "100_125",
        "125_150",
        "150_200",
        "GE200",
    )
    for cut, label in zip(cuts, labels, strict=False):
        if x < cut:
            return label
    return labels[-1]


def _negative_population(
    rows: list[dict[str, object]],
    negative: dict[str, set[tuple[str, ...]]],
) -> list[dict[str, object]]:
    output: list[dict[str, object]] = []
    for row in rows:
        views = sum(
            v5._state(row, fields) in negative[name]
            for name, fields in v8.NEGATIVE_VIEWS.items()
        )
        if views:
            item = dict(row)
            item["negative_views"] = views
            output.append(item)
    return output


def _stats(rows: list[dict[str, object]]) -> dict[str, object]:
    values = [_d(row["net_r_after_friction"]) for row in rows]
    winners = [value for value in values if value > 0]
    losses = [value for value in values if value < 0]
    gp = sum(winners, Decimal(0))
    gl = -sum(losses, Decimal(0))
    return {
        "sample": len(rows),
        "wins": len(winners),
        "losses": len(losses),
        "profit_factor": None if gl == 0 else format(gp / gl, "f"),
        "total_r": format(gp - gl, "f"),
        "gross_winner_r": format(gp, "f"),
        "gross_loss_r": format(gl, "f"),
        "mean_winner_r": "0" if not winners else format(gp / Decimal(len(winners)), "f"),
    }


def _key(
    row: dict[str, object],
    fields: tuple[str, ...],
    numeric_fields: set[str],
) -> tuple[str, ...]:
    return tuple(
        _bin(row.get(field, "unavailable"))
        if field in numeric_fields
        else str(row.get(field, "unavailable"))
        for field in fields
    )


def _stable_states(
    r8: list[dict[str, object]],
    r6: list[dict[str, object]],
    fields: tuple[str, ...],
    *,
    minimum_r8: int = 4,
    minimum_r6: int = 4,
) -> list[dict[str, object]]:
    numeric = set(NUMERIC_FIELDS)
    g8: dict[tuple[str, ...], list[dict[str, object]]] = defaultdict(list)
    g6: dict[tuple[str, ...], list[dict[str, object]]] = defaultdict(list)
    for row in r8:
        g8[_key(row, fields, numeric)].append(row)
    for row in r6:
        g6[_key(row, fields, numeric)].append(row)

    output: list[dict[str, object]] = []
    for state in set(g8).intersection(g6):
        if len(g8[state]) < minimum_r8 or len(g6[state]) < minimum_r6:
            continue
        s8 = _stats(g8[state])
        s6 = _stats(g6[state])
        pf8 = None if s8["profit_factor"] is None else _d(s8["profit_factor"])
        pf6 = None if s6["profit_factor"] is None else _d(s6["profit_factor"])
        output.append({
            "fields": fields,
            "state": state,
            "r8": s8,
            "r6": s6,
            "positive_both": (
                pf8 is not None
                and pf6 is not None
                and pf8 >= Decimal("1")
                and pf6 >= Decimal("1")
                and _d(s8["total_r"]) > 0
                and _d(s6["total_r"]) > 0
            ),
            "tail_both": (
                int(s8["wins"]) >= 1
                and int(s6["wins"]) >= 1
                and _d(s8["mean_winner_r"]) >= Decimal("4")
                and _d(s6["mean_winner_r"]) >= Decimal("4")
            ),
        })
    output.sort(
        key=lambda item: (
            bool(item["positive_both"] and item["tail_both"]),
            min(_d(cast(dict[str, object], item["r8"])["total_r"]), _d(cast(dict[str, object], item["r6"])["total_r"])),
            min(int(cast(dict[str, object], item["r8"])["sample"]), int(cast(dict[str, object], item["r6"])["sample"])),
        ),
        reverse=True,
    )
    return output


def run(
    *,
    r8_trades: Path,
    r6_trades: Path,
    r8_raw: Path,
    r6_raw: Path,
    daily_path: Path,
) -> dict[str, object]:
    daily = v2.v3._load_daily(daily_path)
    r8 = v8._sequence_rows(
        r8_raw,
        v2.v3._decorate(v2.v3._load_trades(r8_trades), daily),
    )
    r6 = v8._sequence_rows(
        r6_raw,
        v2.v3._decorate(v2.v3._load_trades(r6_trades), daily),
    )
    if len(r8) != 228 or len(r6) != 278:
        raise AssertionError("VT31 R8/R6 challenge-set drift")

    negative = v8._negative_tables(r8)
    n8 = _negative_population(r8, negative)
    n6 = _negative_population(r6, negative)

    views: dict[str, object] = {}
    field_sets = [(field,) for field in CATEGORICAL_FIELDS + NUMERIC_FIELDS]
    field_sets.extend(RELATIONAL_VIEWS)
    for fields in field_sets:
        key = "|".join(fields)
        views[key] = _stable_states(n8, n6, fields)[:60]

    winners = [
        {
            "signal_at": row["signal_at"],
            "net_r_after_friction": row["net_r_after_friction"],
            "negative_views": row["negative_views"],
            "sequence_chain": row.get("sequence_chain"),
            "peer_consensus": row.get("peer_consensus"),
            "perception_regime": row.get("perception_regime"),
            "perception_transition": row.get("perception_transition"),
            "h1_state_hr": row.get("h1_state_hr"),
            "cash_open_state_hr": row.get("cash_open_state_hr"),
            "position_in_prior_day_range_hr": row.get("position_in_prior_day_range_hr"),
            "raid_depth_ref_hr": row.get("raid_depth_ref_hr"),
            "current_path_vs_previous_hr": row.get("current_path_vs_previous_hr"),
        }
        for row in n6
        if _d(row["net_r_after_friction"]) > 0
    ]
    winners.sort(key=lambda row: _d(row["net_r_after_friction"]), reverse=True)

    return {
        "schema": SCHEMA,
        "partition": "R8_DISCOVERY_R6_CALIBRATION_ONLY",
        "r5_opened": False,
        "r8_negative_population": _stats(n8),
        "r6_negative_population": _stats(n6),
        "stable_state_views": views,
        "r6_negative_population_winners": winners,
        "governance": {
            "r5_opened": False,
            "runtime_policy_created": False,
            "outcome_used_for_runtime_decision": False,
            "outcome_used_for_diagnostics_only": True,
            "future_m1_used": False,
            "capital_risk_weighting_used": False,
            "methodology_modified": False,
            "shared_order_authority": False,
            "shared_risk_authority": False,
            "shared_execution_authority": False,
            "live_authorized": False,
            "merge_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--r8-trades", type=Path, required=True)
    parser.add_argument("--r6-trades", type=Path, required=True)
    parser.add_argument("--r8-raw", type=Path, required=True)
    parser.add_argument("--r6-raw", type=Path, required=True)
    parser.add_argument("--daily-path", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = run(
        r8_trades=args.r8_trades,
        r6_trades=args.r6_trades,
        r8_raw=args.r8_raw,
        r6_raw=args.r6_raw,
        daily_path=args.daily_path,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    stable = []
    for name, states in cast(dict[str, list[dict[str, object]]], payload["stable_state_views"]).items():
        for state in states:
            if state["positive_both"] and state["tail_both"]:
                stable.append({"view": name, **state})
    print(json.dumps({
        "r5_opened": payload["r5_opened"],
        "r8_negative_population": payload["r8_negative_population"],
        "r6_negative_population": payload["r6_negative_population"],
        "stable_positive_tail_states": stable[:40],
        "r6_tail_winners": payload["r6_negative_population_winners"][:20],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
