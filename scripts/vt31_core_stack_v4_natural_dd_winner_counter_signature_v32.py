"""VT31 Shared natural DD winner-preservation counter-signature atlas V32.

Phase-1 diagnostic only. Starting from V31's best consumed-fold diagnostic
hypothesis, V32 studies why valuable winners are falsely classified as adverse.

No trades are changed. No sizing, capital weighting, abstention, stop/target
mutation, trailing, or target extension. Outcome labels are offline only.
"""
# ruff: noqa: E501
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_core_stack_v4_natural_dd_causal_discrimination_v31 as v31

SCHEMA = "qore.core_stack_v4.vt31.natural_dd_winner_counter_signature.v32"
IDENTITY = "VT31_NAS100_SHARED_NATURAL_DD_WINNER_COUNTER_SIGNATURE_V32"
ZERO = Decimal("0")

FEATURES = (
    "market_support_bps",
    "threat_bps",
    "urgency_bps",
    "shock_risk_bps",
    "structural_risk_bps",
    "resilience_bps",
    "threat_convergence_bps",
    "confidence_bps",
    "expansion_capacity_bps",
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _percentile(values: list[int], q: float) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    idx = int(round((len(ordered) - 1) * q))
    return ordered[idx]


def _stats(rows: list[dict[str, object]]) -> dict[str, object]:
    out: dict[str, object] = {
        "sample": len(rows),
        "total_r": format(sum((_d(r["baseline_r"]) for r in rows), ZERO), "f"),
    }
    for feature in FEATURES:
        vals = [int(r[feature]) for r in rows]
        out[feature] = {
            "min": None if not vals else min(vals),
            "p10": _percentile(vals, 0.10),
            "p25": _percentile(vals, 0.25),
            "p50": _percentile(vals, 0.50),
            "p75": _percentile(vals, 0.75),
            "p90": _percentile(vals, 0.90),
            "max": None if not vals else max(vals),
            "mean": None if not vals else sum(vals) // len(vals),
        }
    return out


def _categorical_atlas(
    rows: list[dict[str, object]],
    *,
    key: str,
) -> list[dict[str, object]]:
    groups: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        groups[str(row[key])].append(row)

    out: list[dict[str, object]] = []
    for value, members in groups.items():
        losses = [r for r in members if r["outcome"] == "LOSS"]
        wins = [r for r in members if r["outcome"] == "WIN"]
        winner_r = sum((_d(r["baseline_r"]) for r in wins), ZERO)
        loss_r = -sum((_d(r["baseline_r"]) for r in losses), ZERO)
        out.append(
            {
                "value": value,
                "sample": len(members),
                "losses": len(losses),
                "wins": len(wins),
                "winner_r": format(winner_r, "f"),
                "loss_r": format(loss_r, "f"),
                "net_r": format(winner_r - loss_r, "f"),
                "top3_dd_losses": sum(
                    bool(r["in_top3_dd_excursions"]) for r in losses
                ),
                "unobservable_losses": sum(
                    bool(r["unobservable_loss"]) for r in losses
                ),
            }
        )
    out.sort(
        key=lambda x: (
            _d(x["winner_r"]),
            int(x["wins"]),
            -int(x["losses"]),
        ),
        reverse=True,
    )
    return out


def _fold(
    rows: list[dict[str, object]],
    *,
    hypothesis: v31.CausalRiskHypothesis,
) -> dict[str, object]:
    flagged = [row for row in rows if hypothesis.matches(row)]
    flagged_losses = [r for r in flagged if r["outcome"] == "LOSS"]
    flagged_winners = [r for r in flagged if r["outcome"] == "WIN"]
    flagged_large_winners = [
        r for r in flagged_winners if _d(r["baseline_r"]) >= Decimal("5")
    ]
    top3_dd_losses = [
        r
        for r in flagged_losses
        if bool(r["in_top3_dd_excursions"])
    ]
    unobservable_losses = [
        r for r in flagged_losses if bool(r["unobservable_loss"])
    ]

    signature_counts: Counter[str] = Counter()
    for row in flagged:
        signature_counts[
            f"{row['situation']}|{row['environment_trajectory']}|"
            f"{row['semantic_signature']}|{row['outcome']}"
        ] += 1

    return {
        "flagged": len(flagged),
        "groups": {
            "FLAGGED_LOSSES": _stats(flagged_losses),
            "FLAGGED_TOP3_DD_LOSSES": _stats(top3_dd_losses),
            "FLAGGED_UNOBSERVABLE_LOSSES": _stats(unobservable_losses),
            "FLAGGED_WINNERS": _stats(flagged_winners),
            "FLAGGED_WINNERS_GE_5R": _stats(flagged_large_winners),
        },
        "winner_counter_atlas": {
            "situation": _categorical_atlas(flagged, key="situation"),
            "environment_trajectory": _categorical_atlas(
                flagged,
                key="environment_trajectory",
            ),
            "semantic_signature": _categorical_atlas(
                flagged,
                key="semantic_signature",
            ),
        },
        "full_joint_signature_counts": dict(sorted(signature_counts.items())),
        "largest_flagged_winners": sorted(
            (
                {
                    "signal_at": row["signal_at"],
                    "baseline_r": row["baseline_r"],
                    "situation": row["situation"],
                    "environment_trajectory": row["environment_trajectory"],
                    "semantic_signature": row["semantic_signature"],
                    **{feature: row[feature] for feature in FEATURES},
                }
                for row in flagged_winners
            ),
            key=lambda x: _d(x["baseline_r"]),
            reverse=True,
        )[:20],
        "actuation_used": False,
    }


def _cross_fold_winner_counter_signatures(
    r8: dict[str, object],
    r6: dict[str, object],
) -> dict[str, list[dict[str, object]]]:
    out: dict[str, list[dict[str, object]]] = {}
    a8 = cast(dict[str, list[dict[str, object]]], r8["winner_counter_atlas"])
    a6 = cast(dict[str, list[dict[str, object]]], r6["winner_counter_atlas"])
    for dimension in ("situation", "environment_trajectory", "semantic_signature"):
        m8 = {str(x["value"]): x for x in a8[dimension]}
        m6 = {str(x["value"]): x for x in a6[dimension]}
        rows: list[dict[str, object]] = []
        for value in sorted(set(m8).intersection(m6)):
            x, y = m8[value], m6[value]
            rows.append(
                {
                    "value": value,
                    "r8": x,
                    "r6": y,
                    "combined_wins": int(x["wins"]) + int(y["wins"]),
                    "combined_winner_r": format(
                        _d(x["winner_r"]) + _d(y["winner_r"]),
                        "f",
                    ),
                    "combined_losses": int(x["losses"]) + int(y["losses"]),
                    "combined_loss_r": format(
                        _d(x["loss_r"]) + _d(y["loss_r"]),
                        "f",
                    ),
                    "winner_r_to_loss_r_ratio": (
                        "0"
                        if _d(x["loss_r"]) + _d(y["loss_r"]) == ZERO
                        else format(
                            (_d(x["winner_r"]) + _d(y["winner_r"]))
                            / (_d(x["loss_r"]) + _d(y["loss_r"])),
                            "f",
                        )
                    ),
                    "runtime_policy_claim": False,
                }
            )
        rows.sort(
            key=lambda z: (
                _d(z["combined_winner_r"]),
                int(z["combined_wins"]),
            ),
            reverse=True,
        )
        out[dimension] = rows
    return out


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
    daily = v31.v30.v28.v27.v26.v23.v22.v21.v20.v19.v18.v2.v3._load_daily(
        daily_path
    )
    r8_source = v31.v30.v28.v27.v26.v23.v22.v21.v20.v19.v18._load_cross_rows(
        trades=r8_trades,
        nas=r8_nas,
        sp=r8_sp,
        us=r8_us,
        daily=daily,
    )
    r6_source = v31.v30.v28.v27.v26.v23.v22.v21.v20.v19.v18._load_cross_rows(
        trades=r6_trades,
        nas=r6_nas,
        sp=r6_sp,
        us=r6_us,
        daily=daily,
    )
    if len(r8_source) != 228 or len(r6_source) != 278:
        raise AssertionError("VT31 R8/R6 challenge-set drift")

    p8, _ = v31.v30.v28.v27.v26._prepare(
        r8_source,
        nas_evidence=r8_nas,
        sp_evidence=r8_sp,
        us_evidence=r8_us,
    )
    p6, _ = v31.v30.v28.v27.v26._prepare(
        r6_source,
        nas_evidence=r6_nas,
        sp_evidence=r6_sp,
        us_evidence=r6_us,
    )
    e8 = v31.v30._drawdown_excursions(p8)
    e6 = v31.v30._drawdown_excursions(p6)
    rows8 = v31.v30._signature_rows(p8, e8)
    rows6 = v31.v30._signature_rows(p6, e6)

    hypothesis = next(
        h for h in v31.HYPOTHESES if h.name == "COMPOSITE_PRECISION_ORIGIN"
    )
    f8 = _fold(rows8, hypothesis=hypothesis)
    f6 = _fold(rows6, hypothesis=hypothesis)

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "research_phase": "PHASE_1_NATURAL_DD_INTELLIGENCE",
        "status": "DIAGNOSTIC_WINNER_PRESERVATION_NO_ACTUATION",
        "source_hypothesis": hypothesis.payload(),
        "challenge_set": {"r8": 228, "r6": 278},
        "r8": f8,
        "r6": f6,
        "cross_fold_winner_counter_signatures": (
            _cross_fold_winner_counter_signatures(f8, f6)
        ),
        "phase_1_contract": {
            "same_trade_universe": True,
            "same_initial_position_size": True,
            "sizing_used": False,
            "capital_weighting_used": False,
            "entry_abstention_used": False,
            "stop_geometry_mutated": False,
            "target_geometry_mutated": False,
            "trailing_used": False,
            "target_extension_used": False,
            "runtime_outcome_input_used": False,
            "future_market_input_used": False,
            "outcomes_used_offline_for_evaluation_only": True,
            "r5_opened": False,
            "new_holdout_opened": False,
        },
        "governance": {
            "vt31_is_falsification_lab_only": True,
            "live_authorized": False,
            "production_authorized": False,
            "real_capital_authorized": False,
            "merge_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--r8-trades", type=Path, required=True)
    parser.add_argument("--r6-trades", type=Path, required=True)
    parser.add_argument("--r8-nas", type=Path, required=True)
    parser.add_argument("--r8-sp", type=Path, required=True)
    parser.add_argument("--r8-us", type=Path, required=True)
    parser.add_argument("--r6-nas", type=Path, required=True)
    parser.add_argument("--r6-sp", type=Path, required=True)
    parser.add_argument("--r6-us", type=Path, required=True)
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
    print(
        json.dumps(
            {
                "status": payload["status"],
                "r8": payload["r8"],
                "r6": payload["r6"],
                "cross_fold_winner_counter_signatures": payload[
                    "cross_fold_winner_counter_signatures"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
