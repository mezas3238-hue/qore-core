"""VT31 Shared cross-market DD-tail diagnostics V14.

Research-only diagnostic over consumed R8 discovery and R6 calibration folds.
R5 is deliberately not accepted as input.

Starts from the strongest Cross-Market Sequence V13 R6 near-pass policy and
asks which decision-time cross-market/liquidity facts characterize the rescued
losses that keep R6 drawdown 0.0854R above the hard DD gate.

Outcomes are offline diagnostic labels only. No runtime policy is created.
"""
# ruff: noqa: E501
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_core_stack_v4_cross_market_sequence_hypothesis_v13 as v13
import vt31_core_stack_v4_perception_first_v2 as v2
import vt31_core_stack_v4_perception_sequence_topology_v8 as v8

SCHEMA = "qore.core_stack_v4.vt31.cross_market_dd_tail_diagnostics.v14"
POLICY = v13.Policy(
    score_threshold=0.0,
    minimum_supportive_channels=1,
    maximum_adverse_channels=4,
    minimum_cross_sequence_score=-0.25,
    rescue_n2_threshold=None,
)

DIAG_FIELDS = (
    "sp500_move3_bin",
    "sp500_move10_bin",
    "sp500_transition",
    "sp500_run_state",
    "sp500_run_age",
    "us30_move3_bin",
    "us30_move10_bin",
    "us30_transition",
    "us30_run_state",
    "us30_run_age",
    "peer_sync3",
    "peer_confirmation_latency",
    "peer_sequence_leader",
    "peer_divergence_age",
    "breadth3",
    "breadth10",
    "breadth_transition",
    "destination_room_ref_bin",
    "reference_room_ref_bin",
    "prior_range_location_causal",
    "sequence_chain",
    "perception_transition",
    "structure_state",
    "h1_relation",
    "cash_open_relation",
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _load(
    *,
    trades: Path,
    nas: Path,
    sp: Path,
    us: Path,
    daily: object,
) -> list[dict[str, object]]:
    return v13._cross_rows(
        nas_path=nas,
        sp_path=sp,
        us_path=us,
        rows=v2.v3._decorate(v2.v3._load_trades(trades), daily),
    )


def _decision(
    row: dict[str, object],
    *,
    negative: dict[str, set[tuple[str, ...]]],
    model: dict[str, dict[str, dict[str, float]]],
) -> dict[str, object]:
    n_views = v13._negative_views(row, negative)
    scores = v13._channel_scores(row, model)
    total_score, supportive, adverse = v13._tail_score(scores)
    cross_score = scores.get("CROSS_SEQUENCE", 0.0)
    if n_views == 0:
        kept = True
        rescued = False
    elif n_views == 1:
        rescued = (
            total_score >= POLICY.score_threshold
            and supportive >= POLICY.minimum_supportive_channels
            and adverse <= POLICY.maximum_adverse_channels
            and cross_score >= POLICY.minimum_cross_sequence_score
        )
        kept = rescued
    else:
        rescued = False
        kept = False
    return {
        "kept": kept,
        "rescued": rescued,
        "negative_views": n_views,
        "total_score": total_score,
        "supportive_channels": supportive,
        "adverse_channels": adverse,
        "cross_sequence_score": cross_score,
        "channel_scores": scores,
    }


def _annotate(
    rows: list[dict[str, object]],
    *,
    negative: dict[str, set[tuple[str, ...]]],
    model: dict[str, dict[str, dict[str, float]]],
) -> list[dict[str, object]]:
    output: list[dict[str, object]] = []
    for source in sorted(rows, key=lambda row: cast(str, row["signal_at"])):
        row = dict(source)
        row["_decision"] = _decision(row, negative=negative, model=model)
        output.append(row)
    return output


def _max_dd_segment(rows: list[dict[str, object]]) -> dict[str, object]:
    kept = [
        row for row in rows
        if cast(dict[str, object], row["_decision"])["kept"]
    ]
    equity = Decimal("0")
    peak = Decimal("0")
    peak_index = -1
    maximum = Decimal("0")
    max_start = -1
    max_end = -1
    for idx, row in enumerate(kept):
        equity += _d(row["net_r_after_friction"])
        if equity > peak:
            peak = equity
            peak_index = idx
        drawdown = peak - equity
        if drawdown > maximum:
            maximum = drawdown
            max_start = peak_index + 1
            max_end = idx
    segment = kept[max_start : max_end + 1] if max_start >= 0 else []
    return {
        "max_drawdown_r": format(maximum, "f"),
        "start_signal_at": None if not segment else segment[0]["signal_at"],
        "end_signal_at": None if not segment else segment[-1]["signal_at"],
        "trades": len(segment),
        "losses": sum(_d(row["net_r_after_friction"]) < 0 for row in segment),
        "wins": sum(_d(row["net_r_after_friction"]) > 0 for row in segment),
        "rescued_losses": sum(
            _d(row["net_r_after_friction"]) < 0
            and bool(cast(dict[str, object], row["_decision"])["rescued"])
            for row in segment
        ),
        "rescued_winners": sum(
            _d(row["net_r_after_friction"]) > 0
            and bool(cast(dict[str, object], row["_decision"])["rescued"])
            for row in segment
        ),
        "segment_rows": [
            {
                "signal_at": row["signal_at"],
                "net_r_after_friction": row["net_r_after_friction"],
                "side": row.get("side"),
                "entry_family": row.get("entry_family"),
                "decision": row["_decision"],
                "facts": {field: row.get(field) for field in DIAG_FIELDS},
            }
            for row in segment
        ],
    }


def _rescues(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    return [
        row for row in rows
        if bool(cast(dict[str, object], row["_decision"])["rescued"])
    ]


def _field_stats(rows: list[dict[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for field in DIAG_FIELDS:
        groups: dict[str, dict[str, object]] = defaultdict(
            lambda: {"sample": 0, "wins": 0, "losses": 0, "total_r": Decimal("0")}
        )
        for row in rows:
            key = str(row.get(field, "unavailable"))
            group = groups[key]
            group["sample"] = int(group["sample"]) + 1
            value = _d(row["net_r_after_friction"])
            group["total_r"] = cast(Decimal, group["total_r"]) + value
            if value > 0:
                group["wins"] = int(group["wins"]) + 1
            elif value < 0:
                group["losses"] = int(group["losses"]) + 1
        items: list[dict[str, object]] = []
        for value, group in groups.items():
            sample = int(group["sample"])
            losses = int(group["losses"])
            items.append(
                {
                    "value": value,
                    "sample": sample,
                    "wins": int(group["wins"]),
                    "losses": losses,
                    "loss_rate": "0" if not sample else format(Decimal(losses) / Decimal(sample), "f"),
                    "total_r": format(cast(Decimal, group["total_r"]), "f"),
                }
            )
        result[field] = sorted(
            items,
            key=lambda item: (
                int(item["sample"]),
                _d(item["loss_rate"]),
                -_d(item["total_r"]),
            ),
            reverse=True,
        )
    return result


def _stable_bad_states(
    r8_rescues: list[dict[str, object]],
    r6_rescues: list[dict[str, object]],
) -> list[dict[str, object]]:
    s8 = cast(dict[str, list[dict[str, object]]], _field_stats(r8_rescues))
    s6 = cast(dict[str, list[dict[str, object]]], _field_stats(r6_rescues))
    output: list[dict[str, object]] = []
    for field in DIAG_FIELDS:
        m8 = {str(row["value"]): row for row in s8[field]}
        m6 = {str(row["value"]): row for row in s6[field]}
        for value in set(m8).intersection(m6):
            a, b = m8[value], m6[value]
            if min(int(a["sample"]), int(b["sample"])) < 2:
                continue
            if _d(a["loss_rate"]) < Decimal("0.70") or _d(b["loss_rate"]) < Decimal("0.70"):
                continue
            output.append(
                {
                    "field": field,
                    "value": value,
                    "r8": a,
                    "r6": b,
                    "worst_loss_rate": format(min(_d(a["loss_rate"]), _d(b["loss_rate"])), "f"),
                    "combined_total_r": format(_d(a["total_r"]) + _d(b["total_r"]), "f"),
                }
            )
    output.sort(
        key=lambda row: (
            _d(row["worst_loss_rate"]),
            -_d(row["combined_total_r"]),
            min(int(cast(dict[str, object], row["r8"])["sample"]), int(cast(dict[str, object], row["r6"])["sample"])),
        ),
        reverse=True,
    )
    return output


def _compact_rescues(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    return [
        {
            "signal_at": row["signal_at"],
            "net_r_after_friction": row["net_r_after_friction"],
            "side": row.get("side"),
            "entry_family": row.get("entry_family"),
            "decision": row["_decision"],
            "facts": {field: row.get(field) for field in DIAG_FIELDS},
        }
        for row in rows
    ]


def run(
    *,
    r8_trades: Path,
    r6_trades: Path,
    r8_nas: Path,
    r8_sp: Path,
    r8_us: Path,
    r6_nas: Path,
    r6_sp: Path,
    r6_us: Path,
    daily_path: Path,
) -> dict[str, object]:
    daily = v2.v3._load_daily(daily_path)
    r8 = _load(trades=r8_trades, nas=r8_nas, sp=r8_sp, us=r8_us, daily=daily)
    r6 = _load(trades=r6_trades, nas=r6_nas, sp=r6_sp, us=r6_us, daily=daily)
    if len(r8) != 228 or len(r6) != 278:
        raise AssertionError("VT31 R8/R6 challenge-set drift")

    negative = v8._negative_tables(r8)
    r8_n1 = [row for row in r8 if v13._negative_views(row, negative) == 1]
    model, _ = v13._learn_model(r8_n1)

    a8 = _annotate(r8, negative=negative, model=model)
    a6 = _annotate(r6, negative=negative, model=model)
    r8_eval = v13._evaluate(r8, negative=negative, model=model, policy=POLICY)
    r6_eval = v13._evaluate(r6, negative=negative, model=model, policy=POLICY)
    r8_rescues = _rescues(a8)
    r6_rescues = _rescues(a6)

    return {
        "schema": SCHEMA,
        "partition": "R8_DISCOVERY_R6_CALIBRATION_ONLY",
        "r5_opened": False,
        "policy": POLICY.payload(),
        "r8": {
            "evaluation": r8_eval,
            "gates": v13._gates(r8_eval),
            "rescues": _compact_rescues(r8_rescues),
            "max_dd_segment": _max_dd_segment(a8),
        },
        "r6": {
            "evaluation": r6_eval,
            "gates": v13._gates(r6_eval),
            "rescues": _compact_rescues(r6_rescues),
            "max_dd_segment": _max_dd_segment(a6),
        },
        "stable_bad_rescue_states": _stable_bad_states(r8_rescues, r6_rescues),
        "governance": {
            "r5_opened": False,
            "runtime_policy_created": False,
            "outcome_used_for_runtime_decision": False,
            "outcome_used_for_diagnostics_only": True,
            "three_index_closed_m1_used": True,
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
    for fold in ("r8", "r6"):
        parser.add_argument(f"--{fold}-nas", type=Path, required=True)
        parser.add_argument(f"--{fold}-sp", type=Path, required=True)
        parser.add_argument(f"--{fold}-us", type=Path, required=True)
    parser.add_argument("--daily-path", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = run(
        r8_trades=args.r8_trades,
        r6_trades=args.r6_trades,
        r8_nas=args.r8_nas,
        r8_sp=args.r8_sp,
        r8_us=args.r8_us,
        r6_nas=args.r6_nas,
        r6_sp=args.r6_sp,
        r6_us=args.r6_us,
        daily_path=args.daily_path,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(json.dumps({
        "r5_opened": payload["r5_opened"],
        "policy": payload["policy"],
        "r8_evaluation": cast(dict[str, object], payload["r8"])["evaluation"],
        "r6_evaluation": cast(dict[str, object], payload["r6"])["evaluation"],
        "r6_max_dd_segment": cast(dict[str, object], payload["r6"])["max_dd_segment"],
        "stable_bad_rescue_states": cast(list[object], payload["stable_bad_rescue_states"])[:20],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
