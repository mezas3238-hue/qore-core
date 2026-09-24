"""VT31 Shared journey observability floor diagnostic V25.

Consumed diagnostic evidence only.

This diagnostic asks whether the current closed-M1 post-fill journey interface
can theoretically reach the Owner drawdown objective while preserving every
trade. It does NOT create a trading policy.

For each consumed fold it reconstructs every methodology-valid opportunity and
separates trades with at least one causal post-fill journey snapshot from trades
that exit before any such snapshot exists.

It then computes an intentionally impossible best-case oracle bound:
- every observable losing trade is replaced by 0R;
- observable winners remain unchanged;
- unobservable trades remain exactly baseline.

The oracle uses realized outcomes ONLY offline to establish an upper bound on
what the current observation interface could ever achieve. It is forbidden as
runtime logic and cannot be promoted as a Shared policy.
"""
# ruff: noqa: E501
from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_core_stack_v4_full_universe_asymmetric_journey_v23 as v23

SCHEMA = "qore.core_stack_v4.vt31.journey_observability_floor.v25"
IDENTITY = "VT31_NAS100_SHARED_JOURNEY_OBSERVABILITY_FLOOR_V25"
ZERO = Decimal("0")
DD_ACCEPTABLE_MAX_R = Decimal("6")
DD_EXCEPTIONAL_R = Decimal("4")
v22 = v23.v22


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _metrics(values: list[Decimal]) -> dict[str, object]:
    return v22._metrics(values)


def _fold(prepared: list[dict[str, object]]) -> dict[str, object]:
    baseline_values: list[Decimal] = []
    oracle_values: list[Decimal] = []
    observable: list[dict[str, object]] = []
    unobservable: list[dict[str, object]] = []

    for item in prepared:
        row = cast(dict[str, object], item["row"])
        baseline_r = cast(Decimal, item["baseline_r"])
        baseline_values.append(baseline_r)
        events = cast(list[dict[str, object]], item["events"])
        record = {
            "signal_at": row["signal_at"],
            "baseline_r": format(baseline_r, "f"),
            "event_count": len(events),
        }
        if events:
            observable.append(record)
            oracle_values.append(ZERO if baseline_r < ZERO else baseline_r)
        else:
            unobservable.append(record)
            oracle_values.append(baseline_r)

    baseline = _metrics(baseline_values)
    oracle = _metrics(oracle_values)
    observable_losses = [x for x in observable if _d(x["baseline_r"]) < ZERO]
    observable_winners = [x for x in observable if _d(x["baseline_r"]) > ZERO]
    unobservable_losses = [x for x in unobservable if _d(x["baseline_r"]) < ZERO]
    unobservable_winners = [x for x in unobservable if _d(x["baseline_r"]) > ZERO]

    return {
        "baseline": baseline,
        "coverage": {
            "trade_count": len(prepared),
            "observable_trade_count": len(observable),
            "unobservable_trade_count": len(unobservable),
            "observable_fraction": format(
                Decimal(len(observable)) / Decimal(len(prepared)), "f"
            ),
            "observable_losses": len(observable_losses),
            "observable_winners": len(observable_winners),
            "unobservable_losses": len(unobservable_losses),
            "unobservable_winners": len(unobservable_winners),
            "unobservable_gross_loss_r": format(
                -sum(
                    (_d(x["baseline_r"]) for x in unobservable_losses),
                    ZERO,
                ),
                "f",
            ),
            "unobservable_gross_winner_r": format(
                sum(
                    (_d(x["baseline_r"]) for x in unobservable_winners),
                    ZERO,
                ),
                "f",
            ),
            "unobservable_examples": unobservable[:30],
        },
        "oracle_observable_loss_elimination": {
            "description": (
                "offline impossible upper bound: observable losses -> 0R, "
                "all winners and unobservable trades unchanged"
            ),
            "metrics": oracle,
            "dd_at_most_6r": (
                _d(oracle["max_drawdown_r"]) <= DD_ACCEPTABLE_MAX_R
            ),
            "dd_below_4r": _d(oracle["max_drawdown_r"]) < DD_EXCEPTIONAL_R,
            "profit_factor_above_baseline": (
                _d(oracle["profit_factor"]) > _d(baseline["profit_factor"])
            ),
        },
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
    daily = v22.v21.v20.v19.v18.v2.v3._load_daily(daily_path)
    r8 = v22.v21.v20.v19.v18._load_cross_rows(
        trades=r8_trades, nas=r8_nas, sp=r8_sp, us=r8_us, daily=daily
    )
    r6 = v22.v21.v20.v19.v18._load_cross_rows(
        trades=r6_trades, nas=r6_nas, sp=r6_sp, us=r6_us, daily=daily
    )
    if len(r8) != 228 or len(r6) != 278:
        raise AssertionError("VT31 R8/R6 challenge-set drift")

    p8 = v23._prepare_full_universe(
        r8, nas_evidence=r8_nas, sp_evidence=r8_sp, us_evidence=r8_us
    )
    p6 = v23._prepare_full_universe(
        r6, nas_evidence=r6_nas, sp_evidence=r6_sp, us_evidence=r6_us
    )

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "diagnostic_only": True,
        "challenge_set": {"r8": 228, "r6": 278},
        "r8": _fold(p8),
        "r6": _fold(p6),
        "owner_objective": {
            "acceptable_drawdown_r": [4, 6],
            "exceptional_drawdown_r": "<4",
            "density_must_be_preserved": True,
            "profit_factor_must_increase": True,
        },
        "governance": {
            "offline_terminal_outcomes_used_for_oracle_bound_only": True,
            "runtime_terminal_outcomes_used": False,
            "oracle_policy_promotable": False,
            "full_methodology_valid_universe_reconstructed": True,
            "trade_count_changed": False,
            "entry_abstention_used": False,
            "risk_weighting_used": False,
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
                "r8": payload["r8"],
                "r6": payload["r6"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
