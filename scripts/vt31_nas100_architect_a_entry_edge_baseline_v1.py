"""VT31 NAS100 Architect A pure-entry baseline V1.

Consumed/burned evidence development only.

This harness isolates admission quality. It keeps Architect A's causal
pre-entry reasoning and executable geometry, but forces every admitted setup to
use the same source structural boundary exit. Position management, target
extension, sizing, leverage, compounding and capital weighting are not allowed
to improve the result.

Purpose: determine whether the current Architect A admission brain itself
produces a cross-fold positive population before changing any entry rule.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import vt31_nas100_specialist_r1_candidate as specialist

SCHEMA = "qore.vt31.nas100.architect_a_entry_edge_baseline.v1"


def replay(evidence_path: Path) -> dict[str, object]:
    original = specialist._simulate_selected_plan

    def structural_only(
        day_bars: tuple[object, ...],
        executable: object,
        state: dict[str, object],
    ) -> dict[str, object]:
        outcome = specialist.baseline._simulate(day_bars, executable)
        if outcome.get("status") == "terminal":
            outcome["target_plan"] = "FORCED_SOURCE_STRUCTURAL_BOUNDARY"
        return outcome

    try:
        specialist._simulate_selected_plan = structural_only
        payload = specialist.replay(evidence_path)
    finally:
        specialist._simulate_selected_plan = original

    return {
        "schema": SCHEMA,
        "market": "NAS100",
        "candidate_id": payload["candidate_id"],
        "contract_fingerprint": payload["contract_fingerprint"],
        "evidence": payload["evidence"],
        "market_days": payload["market_days"],
        "status_counts": payload["status_counts"],
        "stress_0_05r": payload["stress_0_05r"],
        "halfyear_stress": payload["halfyear_stress"],
        "quarter_stress": payload["quarter_stress"],
        "monte_carlo": payload["monte_carlo"],
        "trade_count": payload["trade_count"],
        "trades": payload["trades"],
        "reasoning_trace": payload["reasoning_trace"],
        "governance": {
            "consumed_evidence_only": True,
            "architect_a_admission_logic_preserved": True,
            "forced_common_structural_exit": True,
            "position_management_optimization_used": False,
            "target_extension_used": False,
            "position_sizing_used": False,
            "leverage_used": False,
            "compounding_used": False,
            "capital_weighting_used": False,
            "absolute_volume_used": False,
            "future_outcome_used_for_admission": False,
            "fold_identity_used_for_admission": False,
            "fresh_holdout_opened": False,
            "policy_promoted": False,
            "candidate_frozen": False,
            "candidate_certified": False,
            "live_authorized": False,
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
                "stress_0_05r": payload["stress_0_05r"],
                "monte_carlo": payload["monte_carlo"],
                "trade_count": payload["trade_count"],
                "status_counts": payload["status_counts"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
