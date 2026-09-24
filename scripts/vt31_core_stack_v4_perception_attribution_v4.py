"""Perception attribution lab for VT31 Shared.

Discovery-only diagnostics on R8. It measures which PRESENT-MARKET perception
states concentrate winner R versus loser R. No policy is certified here and no
R5 data is consumed.
"""
# ruff: noqa: B009,E501
from __future__ import annotations

import argparse
import itertools
import json
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

import vt31_core_stack_v4_perception_first_v2 as v2

SCHEMA = "qore.core_stack_v4.vt31.perception_attribution.v4"

FEATURES = (
    "alignment5",
    "alignment20",
    "perception_regime",
    "perception_transition",
    "momentum_state",
    "volatility_state",
    "structure_state",
    "peer_consensus",
    "pre_behavior_proxy",
    "h1_state_hr",
    "h4_state_hr",
    "premarket_state_hr",
    "cash_open_state_hr",
)

NUMERIC_FEATURES = (
    "trend_pressure",
    "range_pressure",
    "expansion_pressure",
    "exhaustion_pressure",
    "uncertainty_pressure",
    "pre_path_efficiency",
    "pre_overlap_rate",
    "recent_path_efficiency_hr",
    "recent_overlap_rate_hr",
    "raid_depth_ref_hr",
    "current_path_vs_previous_hr",
    "reference_width_vs_prior5_hr",
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _stats(rows: list[dict[str, object]]) -> dict[str, object]:
    values = [_d(row["net_r_after_friction"]) for row in rows]
    wins = [v for v in values if v > 0]
    losses = [v for v in values if v < 0]
    gp = sum(wins, Decimal(0))
    gl = -sum(losses, Decimal(0))
    total = gp - gl
    return {
        "sample": len(rows),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": "0" if not rows else format(Decimal(len(wins)) / Decimal(len(rows)), "f"),
        "profit_factor": None if gl == 0 else format(gp / gl, "f"),
        "total_r": format(total, "f"),
        "gross_winner_r": format(gp, "f"),
        "gross_loss_r": format(gl, "f"),
        "mean_winner_r": "0" if not wins else format(gp / Decimal(len(wins)), "f"),
        "mean_loss_r": "0" if not losses else format(gl / Decimal(len(losses)), "f"),
    }


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
        "GE150",
    )
    for cut, label in zip(cuts, labels, strict=False):
        if x < cut:
            return label
    return labels[-1]


def _group_stats(
    rows: list[dict[str, object]],
    fields: tuple[str, ...],
    *,
    numeric: bool = False,
    minimum_sample: int = 4,
) -> list[dict[str, object]]:
    groups: dict[tuple[str, ...], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        key = tuple(
            _bin(row.get(field, "unavailable"))
            if numeric
            else str(row.get(field, "unavailable"))
            for field in fields
        )
        groups[key].append(row)

    output: list[dict[str, object]] = []
    for key, members in groups.items():
        if len(members) < minimum_sample:
            continue
        stats = _stats(members)
        output.append({
            "fields": fields,
            "state": key,
            **stats,
        })
    output.sort(
        key=lambda item: (
            Decimal(str(item["profit_factor"])) if item["profit_factor"] is not None else Decimal("999"),
            Decimal(str(item["total_r"])),
            int(item["sample"]),
        ),
        reverse=True,
    )
    return output


def run(
    *,
    r8_trades: Path,
    r8_raw: Path,
    daily_path: Path,
) -> dict[str, object]:
    daily = v2.v3._load_daily(daily_path)
    rows = v2._perception_rows(
        r8_raw,
        v2.v3._decorate(v2.v3._load_trades(r8_trades), daily),
    )
    if len(rows) != 228:
        raise AssertionError("R8 challenge-set drift")

    singles = {
        field: _group_stats(rows, (field,), minimum_sample=4)
        for field in FEATURES
    }
    numeric = {
        field: _group_stats(rows, (field,), numeric=True, minimum_sample=4)
        for field in NUMERIC_FEATURES
    }

    core = (
        "alignment5",
        "alignment20",
        "perception_regime",
        "structure_state",
        "peer_consensus",
        "volatility_state",
    )
    pairs: list[dict[str, object]] = []
    for left, right in itertools.combinations(core, 2):
        pairs.extend(_group_stats(rows, (left, right), minimum_sample=5))

    triples: list[dict[str, object]] = []
    for combo in (
        ("alignment5", "perception_regime", "peer_consensus"),
        ("alignment5", "structure_state", "peer_consensus"),
        ("alignment5", "volatility_state", "peer_consensus"),
        ("alignment20", "perception_regime", "peer_consensus"),
        ("perception_regime", "structure_state", "peer_consensus"),
    ):
        triples.extend(_group_stats(rows, combo, minimum_sample=5))

    def negative_rank(item: dict[str, object]) -> tuple[Decimal, Decimal, int]:
        return (
            -Decimal(str(item["total_r"])),
            Decimal(str(item["gross_loss_r"])),
            int(item["sample"]),
        )

    positive_pairs = sorted(
        pairs,
        key=lambda item: (
            Decimal(str(item["total_r"])),
            Decimal(str(item["gross_winner_r"])),
            Decimal(str(item["profit_factor"])) if item["profit_factor"] is not None else Decimal("999"),
        ),
        reverse=True,
    )[:80]
    negative_pairs = sorted(pairs, key=negative_rank, reverse=True)[:80]
    positive_triples = sorted(
        triples,
        key=lambda item: (
            Decimal(str(item["total_r"])),
            Decimal(str(item["gross_winner_r"])),
        ),
        reverse=True,
    )[:80]
    negative_triples = sorted(triples, key=negative_rank, reverse=True)[:80]

    return {
        "schema": SCHEMA,
        "partition": "R8_DISCOVERY_ONLY",
        "sample": len(rows),
        "baseline": _stats(rows),
        "single_feature_states": singles,
        "numeric_feature_bins": numeric,
        "positive_pair_states": positive_pairs,
        "negative_pair_states": negative_pairs,
        "positive_triple_states": positive_triples,
        "negative_triple_states": negative_triples,
        "governance": {
            "r6_consumed": False,
            "r5_consumed": False,
            "runtime_policy_created": False,
            "current_outcome_as_runtime_input": False,
            "future_m1_used": False,
            "capital_weighting_used": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--r8-trades", type=Path, required=True)
    parser.add_argument("--r8-raw", type=Path, required=True)
    parser.add_argument("--daily-path", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = run(
        r8_trades=args.r8_trades,
        r8_raw=args.r8_raw,
        daily_path=args.daily_path,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(json.dumps({
        "sample": payload["sample"],
        "baseline": payload["baseline"],
        "top_positive_pairs": payload["positive_pair_states"][:10],
        "top_negative_pairs": payload["negative_pair_states"][:10],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
