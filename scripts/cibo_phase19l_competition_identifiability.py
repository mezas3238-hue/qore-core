"""Run Phase19L exact-epoch T09/T18 identifiability audit.

This is burned/post-disclosure research. It distinguishes exact simultaneous
competition from ordinary overlap/capital occupancy and never treats the small
historical collision population as fresh OOS evidence.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from cibo_phase19_integrated_chronology_replay import (
    EXPECTED_COMMON_END,
    EXPECTED_COMMON_ROWS,
    EXPECTED_SOURCE_ROWS,
    SOURCE_SPECS,
    _jsonl,
)
from cibo_phase19_normalized_capital_mechanics import _parse_trade
from cibo_phase19_temporal_stability_validation import (
    EXPECTED_SPLIT_AT,
    EXPECTED_VALIDATION_OPPORTUNITIES,
)

from qore.infrastructure.cibo_ce2i_phase19_normalized_capital import (
    Phase19NormalizedReplayTrade,
)
from qore.infrastructure.cibo_ce2i_phase19_temporal_concordance import (
    PHASE19K_POLICY,
    phase19k_priority_order,
)
from qore.infrastructure.cibo_ce2i_phase19l_competition import (
    exact_competition_epochs,
    one_slot_delta_ncu,
    select_identity_reference_candidate,
    select_train_priority_candidate,
)
from qore.infrastructure.cibo_ce2i_phase20_train_prior import (
    prior_digest_sha256,
)


def run(
    *,
    paths: dict[str, Path],
    output_path: Path,
) -> dict[str, Any]:
    if set(paths) != set(SOURCE_SPECS):
        raise ValueError("Phase19L source set drift")

    freeze_at = datetime.fromisoformat(EXPECTED_SPLIT_AT)
    common_end = datetime.fromisoformat(EXPECTED_COMMON_END)
    validation: list[Phase19NormalizedReplayTrade] = []

    for key, spec in SOURCE_SPECS.items():
        rows = _jsonl(paths[key])
        if len(rows) != EXPECTED_SOURCE_ROWS[spec.trader_id]:
            raise ValueError(
                f"{spec.trader_id.value} Phase19L source row-count drift"
            )
        common_count = 0
        for row in rows:
            item = _parse_trade(row, spec=spec)
            if (
                item.opportunity.entry_at
                >= datetime.fromisoformat("2021-09-23T05:00:00+00:00")
                and item.opportunity.exit_at <= common_end
            ):
                common_count += 1
            if (
                item.allocation.decision_at >= freeze_at
                and item.opportunity.exit_at <= common_end
            ):
                validation.append(item)
        if common_count != EXPECTED_COMMON_ROWS[spec.trader_id]:
            raise ValueError(
                f"{spec.trader_id.value} Phase19L common row-count drift"
            )
    if len(validation) != EXPECTED_VALIDATION_OPPORTUNITIES:
        raise ValueError("Phase19L validation population drift")

    epochs = exact_competition_epochs(tuple(validation))
    causal_selected = tuple(
        select_train_priority_candidate(epoch)
        for epoch in epochs
    )
    reference_selected = tuple(
        select_identity_reference_candidate(epoch)
        for epoch in epochs
    )
    causal_delta = one_slot_delta_ncu(
        causal_selected,
        risk_budget_ncu=PHASE19K_POLICY.risk_budget_ncu,
    )
    reference_delta = one_slot_delta_ncu(
        reference_selected,
        risk_budget_ncu=PHASE19K_POLICY.risk_budget_ncu,
    )

    report: dict[str, Any] = {
        "schema": "qore.cibo.phase19l.competition_identifiability.v1",
        "identity": "CIBO_PHASE19L_EXACT_EPOCH_COMPETITION_AUDIT_V1",
        "status": "LIMITED_BURNED_COMPETITION_POPULATION_IDENTIFIED",
        "source": {
            "phase18_artifact_set": "IMMUTABLE_7_OF_7",
            "train_prior_digest_sha256": prior_digest_sha256(),
            "phase19j_validation_previously_disclosed": True,
            "phase19k_policy_id": PHASE19K_POLICY.policy_id,
        },
        "identifiability": {
            "exact_competition_epoch_count": len(epochs),
            "candidate_count_in_exact_epochs": sum(
                len(epoch.candidates) for epoch in epochs
            ),
            "minimum_robust_epoch_count": 30,
            "robust_competition_population_available": len(epochs) >= 30,
            "ordinary_overlap_treated_as_competition": False,
        },
        "frozen_rule": {
            "priority_order": [
                item.value for item in phase19k_priority_order()
            ],
            "risk_budget_ncu": str(PHASE19K_POLICY.risk_budget_ncu),
            "causal_selected_delta_ncu_diagnostic": str(causal_delta),
            "identity_reference_delta_ncu_diagnostic": str(reference_delta),
            "diagnostic_improvement_ncu": str(
                causal_delta - reference_delta
            ),
            "outcomes_used_to_rank_at_decision": False,
        },
        "epochs": [
            {
                "entry_at": epoch.entry_at.isoformat(),
                "candidate_traders": [
                    item.opportunity.trader_id.value
                    for item in epoch.candidates
                ],
                "train_priority_selected": (
                    select_train_priority_candidate(
                        epoch
                    ).opportunity.trader_id.value
                ),
                "identity_reference_selected": (
                    select_identity_reference_candidate(
                        epoch
                    ).opportunity.trader_id.value
                ),
            }
            for epoch in epochs
        ],
        "interpretation": {
            "t09_t18_causal_candidate_exists": True,
            "historical_scarcity_identification_robust": len(epochs) >= 30,
            "promotion_from_phase19l_alone": False,
            "fresh_oos_scarcity_generalization_required": True,
        },
        "governance": {
            "holdout_2017h1_used": False,
            "historical_provider_usd_claimed": False,
            "future_opportunities_used_to_reorder_past_decisions": False,
            "outcome_aware_at_decision": False,
            "policy_certified": False,
            "oos_ready": False,
            "allocation_authority": False,
            "risk_authority": False,
            "execution_authority": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "merge_authorized": False,
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    for key in SOURCE_SPECS:
        parser.add_argument(f"--{key}", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run(
        paths={key: getattr(args, key) for key in SOURCE_SPECS},
        output_path=args.output,
    )
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
