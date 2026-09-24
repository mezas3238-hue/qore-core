"""VT31 Shared resident instinct signature atlas V28.

Diagnostic-only consumed-fold laboratory. It asks whether the generic resident
Instinct dimensions separate fast/unobservable losses from valuable winners
before any new intervention policy is invented.

Runtime outcomes are NEVER fed to Instinct. Outcomes are used only after each
causal assessment for offline grouping and falsification. R5 and fresh holdouts
remain closed.
"""
# ruff: noqa: E501
from __future__ import annotations

import argparse
import json
from collections import Counter
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_core_stack_v4_ultrafast_instinct_prearm_v27 as v27

SCHEMA = "qore.core_stack_v4.vt31.resident_instinct_signature_atlas.v28"
IDENTITY = "VT31_NAS100_SHARED_RESIDENT_INSTINCT_SIGNATURE_ATLAS_V28"
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
    index = int(round((len(ordered) - 1) * q))
    return ordered[index]


def _stats(rows: list[dict[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {"sample": len(rows)}
    for feature in FEATURES:
        values = [int(row[feature]) for row in rows]
        result[feature] = {
            "min": None if not values else min(values),
            "p10": _percentile(values, 0.10),
            "p25": _percentile(values, 0.25),
            "p50": _percentile(values, 0.50),
            "p75": _percentile(values, 0.75),
            "p90": _percentile(values, 0.90),
            "max": None if not values else max(values),
            "mean": None if not values else sum(values) // len(values),
        }
    return result


def _band(value: int) -> str:
    if value >= 7_500:
        return "EXTREME"
    if value >= 6_000:
        return "HIGH"
    if value >= 4_000:
        return "MID"
    return "LOW"


def _fold_atlas(prepared: list[dict[str, object]]) -> dict[str, object]:
    groups: dict[str, list[dict[str, object]]] = {
        "LOSSES": [],
        "UNOBSERVABLE_LOSSES": [],
        "OBSERVABLE_LOSSES": [],
        "WINNERS": [],
        "WINNERS_GE_2R": [],
        "WINNERS_GE_5R": [],
    }
    situation_outcome: Counter[str] = Counter()
    methodology_outcome: Counter[str] = Counter()
    signature_outcome: Counter[str] = Counter()
    env_traj_outcome: Counter[str] = Counter()

    for item in prepared:
        baseline_r = cast(Decimal, item["baseline_r"])
        context = cast(dict[str, object], item["entry_context"])
        instinct = v27._instinct(context)
        observable = bool(cast(list[dict[str, object]], item["events"]))
        outcome = "LOSS" if baseline_r < ZERO else "WIN" if baseline_r > ZERO else "FLAT"

        row = {
            "market_support_bps": instinct.market_support_bps,
            "threat_bps": instinct.threat_bps,
            "urgency_bps": instinct.urgency_bps,
            "shock_risk_bps": instinct.shock_risk_bps,
            "structural_risk_bps": instinct.structural_risk_bps,
            "resilience_bps": instinct.resilience_bps,
            "threat_convergence_bps": instinct.threat_convergence_bps,
            "confidence_bps": instinct.confidence_bps,
            "expansion_capacity_bps": instinct.expansion_capacity_bps,
        }

        if outcome == "LOSS":
            groups["LOSSES"].append(row)
            groups["OBSERVABLE_LOSSES" if observable else "UNOBSERVABLE_LOSSES"].append(row)
        elif outcome == "WIN":
            groups["WINNERS"].append(row)
            if baseline_r >= Decimal("2"):
                groups["WINNERS_GE_2R"].append(row)
            if baseline_r >= Decimal("5"):
                groups["WINNERS_GE_5R"].append(row)

        situation_outcome[f"{instinct.situation.value}|{outcome}"] += 1
        methodology_outcome[f"{instinct.support_methodology.value}|{outcome}"] += 1
        signature = (
            f"T={_band(instinct.threat_bps)}|"
            f"U={_band(instinct.urgency_bps)}|"
            f"S={_band(instinct.structural_risk_bps)}|"
            f"R={_band(instinct.resilience_bps)}"
        )
        signature_outcome[f"{signature}|{outcome}"] += 1
        env_traj_outcome[
            f"{context['environment_state']}|{context['trajectory_state']}|{outcome}"
        ] += 1

    return {
        "group_stats": {name: _stats(rows) for name, rows in groups.items()},
        "situation_outcome_atlas": dict(sorted(situation_outcome.items())),
        "methodology_outcome_atlas": dict(sorted(methodology_outcome.items())),
        "semantic_signature_outcome_atlas": dict(sorted(signature_outcome.items())),
        "environment_trajectory_outcome_atlas": dict(sorted(env_traj_outcome.items())),
        "runtime_outcome_used_by_instinct": False,
        "offline_outcome_used_for_evaluation_only": True,
    }


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
    daily = v27.v26.v23.v22.v21.v20.v19.v18.v2.v3._load_daily(daily_path)
    r8 = v27.v26.v23.v22.v21.v20.v19.v18._load_cross_rows(
        trades=r8_trades,
        nas=r8_nas,
        sp=r8_sp,
        us=r8_us,
        daily=daily,
    )
    r6 = v27.v26.v23.v22.v21.v20.v19.v18._load_cross_rows(
        trades=r6_trades,
        nas=r6_nas,
        sp=r6_sp,
        us=r6_us,
        daily=daily,
    )
    if len(r8) != 228 or len(r6) != 278:
        raise AssertionError("VT31 R8/R6 challenge-set drift")

    p8, _ = v27.v26._prepare(
        r8,
        nas_evidence=r8_nas,
        sp_evidence=r8_sp,
        us_evidence=r8_us,
    )
    p6, _ = v27.v26._prepare(
        r6,
        nas_evidence=r6_nas,
        sp_evidence=r6_sp,
        us_evidence=r6_us,
    )

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "economic_status": "DIAGNOSTIC_ONLY_NO_POLICY_FREEZE",
        "challenge_set": {"r8": 228, "r6": 278},
        "r5_opened": False,
        "new_holdout_opened": False,
        "r8": _fold_atlas(p8),
        "r6": _fold_atlas(p6),
        "governance": {
            "vt31_is_falsification_lab_only": True,
            "generic_instinct_engine_used": True,
            "resident_preentry_state_used": True,
            "runtime_outcome_used_by_instinct": False,
            "future_m1_used": False,
            "entry_abstention_used": False,
            "capital_risk_weighting_used": False,
            "sizing_changed": False,
            "r5_opened": False,
            "new_holdout_opened": False,
            "live_authorized": False,
            "production_authorized": False,
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
                "economic_status": payload["economic_status"],
                "r8": payload["r8"],
                "r6": payload["r6"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
