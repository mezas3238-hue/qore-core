"""Sovereign revalidation of LBB_PATH_SHALLOW_PS1 on the current VT31 population.

The experiment uses specialist.replay() as the only admission authority so the
baseline and candidate contain the exact same cognition-admitted trades.

Runtime eligibility is market/cognition native:
- latest observed structure family == breaker;
- CURRENT_PATH_NOT_COMPRESSED contradiction is present;
- full-cognition destination state == SHALLOW.

Eligible trades may improve the original structural stop once to the first
confirmed M1 protective swing. The swing is effective only from the next M1.
No R threshold, MFE/MAE threshold, fixed profit cap, volume, sizing, leverage,
compounding, or capital weighting is used by runtime decisions.

R is produced only after the resolved price path for evaluation.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_cognitive_structural_protection_frontier_v1 as cognitive
import vt31_nas100_full_cognition_attribution_v1 as cognition_lab
import vt31_nas100_pure_structural_protection_v1 as pure_protection
import vt31_nas100_specialist_r1_candidate as specialist

from qore.infrastructure.traders.vt31_nas100_position_intelligence import (
    assess_full_cognitive_position,
)

SCHEMA = "qore.vt31.nas100.sovereign_lbb_structural_survivor.v2"
VARIANTS = ("PURE_MARKET_BASELINE", "LBB_PATH_SHALLOW_PS1_PURE_V2")


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _eligible(
    *,
    executable: object,
    state: dict[str, object],
) -> bool:
    observation_at = getattr(executable, "decision_at")
    situation = cognition_lab._reconstruct_situation(
        state=state,
        selected=executable,
        source=getattr(executable, "source_setup"),
        observation_at=observation_at,
    )
    if situation.fingerprint() != state["situation_fingerprint"]:
        raise AssertionError("sovereign survivor situation fingerprint drift")
    reasoning = cognition_lab._reconstruct_reasoning(state)
    cognition = assess_full_cognitive_position(
        situation=situation,
        reasoning=reasoning,
        entry_tier="CORE",
        dol1_acceptance_observed=None,
    )
    return bool(
        state["last_structure_event_family"] == "breaker"
        and cognitive._is_path_not_compressed(cognition)
        and cognition.destination_state == "SHALLOW"
    )


def _candidate_simulator(
    day_bars: tuple[object, ...],
    executable: object,
    state: dict[str, object],
) -> dict[str, object]:
    eligible = _eligible(executable=executable, state=state)
    outcome = pure_protection._simulate_one_structural_move(
        day_bars,
        executable,
        eligible=eligible,
    )
    if outcome.get("status") == "terminal":
        outcome["target_plan"] = state["target_plan"]
        outcome["lbb_path_shallow_eligible"] = eligible
        outcome["runtime_r_decision_authority"] = False
        outcome["runtime_volume_decision_authority"] = False
    return outcome


def _winner_preservation(
    baseline: list[dict[str, object]],
    candidate: list[dict[str, object]],
) -> dict[str, object]:
    base = {
        str(row["signal_at"]): _d(row["r_multiple"]) - specialist.FRICTION
        for row in baseline
    }
    cand = {
        str(row["signal_at"]): _d(row["r_multiple"]) - specialist.FRICTION
        for row in candidate
    }
    winners = {key: value for key, value in base.items() if value > 0}
    if not winners:
        return {
            "baseline_winner_count": 0,
            "winner_count_preservation": None,
            "winner_r_preservation": None,
            "baseline_winner_to_loser_count": 0,
        }
    retained = {
        key: cand[key]
        for key in winners
        if key in cand and cand[key] > 0
    }
    winner_to_loser = sum(
        key in cand and cand[key] <= 0
        for key in winners
    )
    return {
        "baseline_winner_count": len(winners),
        "winner_count_preservation": format(
            Decimal(len(retained)) / Decimal(len(winners)),
            "f",
        ),
        "winner_r_preservation": format(
            sum(retained.values(), Decimal(0))
            / sum(winners.values(), Decimal(0)),
            "f",
        ),
        "baseline_winner_to_loser_count": winner_to_loser,
    }


def _changed_trade_rows(
    baseline: list[dict[str, object]],
    candidate: list[dict[str, object]],
) -> list[dict[str, object]]:
    base = {str(row["signal_at"]): row for row in baseline}
    changed: list[dict[str, object]] = []
    for row in candidate:
        key = str(row["signal_at"])
        before = base.get(key)
        if before is None:
            continue
        before_r = _d(before["r_multiple"])
        after_r = _d(row["r_multiple"])
        if after_r == before_r:
            continue
        changed.append(
            {
                "signal_at": key,
                "local_date": row["local_date"],
                "side": row["side"],
                "entry_family": row["entry_family"],
                "eligible": row.get("lbb_path_shallow_eligible"),
                "baseline_r": format(before_r, "f"),
                "candidate_r": format(after_r, "f"),
                "delta_r": format(after_r - before_r, "f"),
                "baseline_exit_reason": before["exit_reason"],
                "candidate_exit_reason": row["exit_reason"],
                "structural_protection_armed": row.get(
                    "structural_protection_armed"
                ),
            }
        )
    return changed


def replay(evidence_path: Path) -> dict[str, object]:
    original = specialist._simulate_selected_plan
    payloads: dict[str, dict[str, object]] = {}
    try:
        specialist._simulate_selected_plan = original
        payloads["PURE_MARKET_BASELINE"] = specialist.replay(evidence_path)

        specialist._simulate_selected_plan = _candidate_simulator
        payloads["LBB_PATH_SHALLOW_PS1_PURE_V2"] = specialist.replay(
            evidence_path
        )
    finally:
        specialist._simulate_selected_plan = original

    baseline = cast(
        list[dict[str, object]],
        payloads["PURE_MARKET_BASELINE"]["trades"],
    )
    candidate = cast(
        list[dict[str, object]],
        payloads["LBB_PATH_SHALLOW_PS1_PURE_V2"]["trades"],
    )
    if [row["signal_at"] for row in baseline] != [
        row["signal_at"] for row in candidate
    ]:
        raise AssertionError("candidate changed sovereign admission population")

    reports: dict[str, object] = {}
    for name, payload in payloads.items():
        trades = cast(list[dict[str, object]], payload["trades"])
        reports[name] = {
            "trade_count": len(trades),
            "stress_0_05r": payload["stress_0_05r"],
            "halfyear_stress": payload["halfyear_stress"],
            "quarter_stress": payload["quarter_stress"],
            "monte_carlo": payload["monte_carlo"],
            "winner_preservation_vs_baseline": (
                None
                if name == "PURE_MARKET_BASELINE"
                else _winner_preservation(baseline, trades)
            ),
            "protection_armed_count": sum(
                row.get("structural_protection_armed") is True
                for row in trades
            ),
            "eligible_count": sum(
                row.get("lbb_path_shallow_eligible") is True
                for row in trades
            ),
        }

    changed = _changed_trade_rows(baseline, candidate)
    return {
        "schema": SCHEMA,
        "market": "NAS100",
        "candidate_contract_fingerprint": specialist.contract_fingerprint(),
        "variants": reports,
        "changed_trade_rows": changed,
        "changed_trade_count": len(changed),
        "changed_delta_total_r": format(
            sum((_d(row["delta_r"]) for row in changed), Decimal(0)),
            "f",
        ),
        "governance": {
            "specialist_replay_is_admission_authority": True,
            "identical_admission_population": True,
            "trade_admission_changed": False,
            "entry_changed": False,
            "initial_structural_invalidation_changed": False,
            "primary_structural_target_changed": False,
            "lifecycle_changed": False,
            "runtime_r_decision_authority": False,
            "runtime_volume_decision_authority": False,
            "position_sizing_used": False,
            "leverage_used": False,
            "compounding_used": False,
            "capital_weighting_used": False,
            "partial_exit_used": False,
            "maximum_structural_protection_moves": 1,
            "protection_source": "confirmed-M1-protective-swing",
            "protection_effective_next_bar": True,
            "r_role": "post_trade_evaluation_only",
            "fresh_holdout_opened": False,
            "automatic_policy_promotion": False,
            "candidate_frozen": False,
            "candidate_certified": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = replay(args.evidence)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "variants": payload["variants"],
                "changed_trade_count": payload["changed_trade_count"],
                "changed_delta_total_r": payload["changed_delta_total_r"],
                "governance": payload["governance"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
