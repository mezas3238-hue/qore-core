"""Run Phase19K burned post-disclosure temporal-concordance research.

The candidate rule is causal at decision time because it uses only the frozen
Phase19 TRAIN priors. The old Phase19J validation is already burned/disclosed,
so this replay is a diagnostic and may not be called fresh OOS, independent
walk-forward qualification, or final certification evidence.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
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
    Phase19CapitalNumeraireContract,
    Phase19NormalizedCapitalReplay,
    Phase19NormalizedReplayTrade,
    replay_phase19_normalized_capital,
)
from qore.infrastructure.cibo_ce2i_phase19_simple_policy import (
    Phase19SimpleCapitalPolicy,
    replay_phase19_simple_policy,
)
from qore.infrastructure.cibo_ce2i_phase19_temporal_concordance import (
    PHASE19K_POLICY,
    build_phase19k_candidate_allocation,
    phase19k_eligible_traders,
    phase19k_priority_order,
)
from qore.infrastructure.cibo_ce2i_phase19_walk_forward import (
    Phase19WalkForwardFold,
    build_phase19j_walk_forward_folds,
    phase19j_survival_failures,
)
from qore.infrastructure.cibo_ce2i_phase20_train_prior import (
    prior_digest_sha256,
)

CONTRACT_ID = "CIBO_PHASE19C_STRUCTURAL_STOP_NCU_V1"
REFERENCE_POLICY = Phase19SimpleCapitalPolicy(
    policy_id="P19K_REFERENCE_P19I_EQUAL_025_NO_RESERVE",
    gross_initial_capital_ncu=PHASE19K_POLICY.gross_initial_capital_ncu,
    fixed_reserve_ncu=PHASE19K_POLICY.gross_initial_capital_ncu * 0,
    risk_budget_ncu=PHASE19K_POLICY.risk_budget_ncu,
)


def _metrics(replay: Phase19NormalizedCapitalReplay) -> dict[str, Any]:
    counts = Counter(item.status.value for item in replay.decisions)
    return {
        "opportunities": len(replay.decisions),
        "accepted_opportunities": replay.accepted_opportunities,
        "rejected_opportunities": replay.rejected_opportunities,
        "decision_status_counts": dict(sorted(counts.items())),
        "ending_capital_ncu": str(replay.ending_capital_ncu),
        "total_realized_delta_ncu": str(replay.total_realized_delta_ncu),
        "max_drawdown_ncu": str(replay.max_drawdown_ncu),
        "peak_reserved_risk_ncu": str(replay.peak_reserved_risk_ncu),
        "risk_capacity_minutes_ncu": str(
            replay.risk_capacity_minutes_ncu
        ),
        "capacity_breach_observed": replay.capacity_breach_observed,
    }


def _fold_trades(
    trades: tuple[Phase19NormalizedReplayTrade, ...],
    *,
    fold: Phase19WalkForwardFold,
) -> tuple[Phase19NormalizedReplayTrade, ...]:
    return tuple(
        item
        for item in trades
        if item.allocation.decision_at >= fold.validation_start_at
        and item.opportunity.exit_at <= fold.validation_end_at
    )


def _candidate_trade(
    item: Phase19NormalizedReplayTrade,
) -> Phase19NormalizedReplayTrade | None:
    allocation = build_phase19k_candidate_allocation(
        opportunity=item.opportunity,
        source_allocation=item.allocation,
    )
    if allocation is None:
        return None
    return Phase19NormalizedReplayTrade(
        opportunity=item.opportunity,
        allocation=allocation,
        normalized_outcome_r=item.normalized_outcome_r,
        outcome_evidence_id=item.outcome_evidence_id,
    )


def run(
    *,
    paths: dict[str, Path],
    output_path: Path,
) -> dict[str, Any]:
    if set(paths) != set(SOURCE_SPECS):
        raise ValueError("Phase19K source set drift")

    freeze_at = datetime.fromisoformat(EXPECTED_SPLIT_AT)
    common_end = datetime.fromisoformat(EXPECTED_COMMON_END)
    folds = build_phase19j_walk_forward_folds(
        frozen_at=freeze_at,
        common_end=common_end,
    )

    validation: list[Phase19NormalizedReplayTrade] = []
    for key, spec in SOURCE_SPECS.items():
        rows = _jsonl(paths[key])
        if len(rows) != EXPECTED_SOURCE_ROWS[spec.trader_id]:
            raise ValueError(
                f"{spec.trader_id.value} Phase19K source row-count drift"
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
                f"{spec.trader_id.value} Phase19K common row-count drift"
            )
    if len(validation) != EXPECTED_VALIDATION_OPPORTUNITIES:
        raise ValueError("Phase19K validation population drift")

    validation_tuple = tuple(validation)
    candidate = tuple(
        transformed
        for item in validation_tuple
        if (transformed := _candidate_trade(item)) is not None
    )
    if not candidate:
        raise ValueError("Phase19K candidate selected no opportunities")

    contract = Phase19CapitalNumeraireContract(contract_id=CONTRACT_ID)
    reference = replay_phase19_simple_policy(
        policy=REFERENCE_POLICY,
        contract=contract,
        trades=validation_tuple,
    )
    candidate_replay = replay_phase19_normalized_capital(
        contract=contract,
        initial_capital_ncu=PHASE19K_POLICY.gross_initial_capital_ncu,
        trades=candidate,
    )

    reference_fold_replays = tuple(
        replay_phase19_simple_policy(
            policy=REFERENCE_POLICY,
            contract=contract,
            trades=_fold_trades(validation_tuple, fold=fold),
        )
        for fold in folds
    )
    candidate_fold_replays = tuple(
        replay_phase19_normalized_capital(
            contract=contract,
            initial_capital_ncu=PHASE19K_POLICY.gross_initial_capital_ncu,
            trades=_fold_trades(candidate, fold=fold),
        )
        for fold in folds
    )
    candidate_failures = phase19j_survival_failures(
        combined=type(reference)(
            policy=REFERENCE_POLICY,
            replay=candidate_replay,
        ),
        folds=tuple(
            type(reference)(
                policy=REFERENCE_POLICY,
                replay=item,
            )
            for item in candidate_fold_replays
        ),
    )

    report: dict[str, Any] = {
        "schema": "qore.cibo.phase19k.temporal_concordance_research.v1",
        "identity": "CIBO_PHASE19K_TEMPORAL_CONCORDANCE_RESEARCH_V1",
        "status": "BURNED_POST_DISCLOSURE_RESEARCH_COMPLETE",
        "source": {
            "phase18_artifact_set": "IMMUTABLE_7_OF_7",
            "train_prior_digest_sha256": prior_digest_sha256(),
            "phase19j_validation_previously_disclosed": True,
        },
        "candidate": {
            "policy_id": PHASE19K_POLICY.policy_id,
            "gross_initial_capital_ncu": str(
                PHASE19K_POLICY.gross_initial_capital_ncu
            ),
            "risk_budget_ncu": str(PHASE19K_POLICY.risk_budget_ncu),
            "risk_budget_origin": "PREDECLARED_PHASE19I_0_25_NCU",
            "eligibility_rule": (
                "TRAIN_MOM_R_GT_0_AND_MOST_RECENT_TRAIN_BLOCK_R_GT_0"
            ),
            "priority_rule": (
                "DESC_TRAIN_EXPECTED_STRUCTURAL_R_PER_CAPITAL_MINUTE"
            ),
            "eligible_traders": [
                item.value for item in phase19k_eligible_traders()
            ],
            "priority_order": [
                item.value for item in phase19k_priority_order()
            ],
            "selected_validation_opportunities": len(candidate),
        },
        "reference_equal_025": {
            "combined": _metrics(reference.replay),
            "folds": [
                {
                    "fold_id": fold.fold_id,
                    "metrics": _metrics(result.replay),
                }
                for fold, result in zip(
                    folds,
                    reference_fold_replays,
                    strict=True,
                )
            ],
        },
        "candidate_burned_diagnostic": {
            "combined": _metrics(candidate_replay),
            "folds": [
                {
                    "fold_id": fold.fold_id,
                    "metrics": _metrics(result),
                }
                for fold, result in zip(
                    folds,
                    candidate_fold_replays,
                    strict=True,
                )
            ],
            "original_phase19j_sign_gate_failures": list(candidate_failures),
            "diagnostic_survives_original_phase19j_sign_gates": (
                not candidate_failures
            ),
        },
        "interpretation": {
            "causal_rule_available_before_each_candidate_decision": True,
            "phase19j_validation_is_fresh_for_this_hypothesis": False,
            "independent_walk_forward_survivor_claimed": False,
            "t09_t18_calibration_promotion_from_this_report_alone": False,
            "fresh_oos_still_required": True,
        },
        "governance": {
            "holdout_2017h1_used": False,
            "historical_provider_usd_claimed": False,
            "validation_outcomes_consumed_at_decision": False,
            "validation_outcomes_previously_disclosed_to_research_process": True,
            "future_market_used_at_decision": False,
            "post_entry_path_used_at_decision": False,
            "outcome_aware_at_decision": False,
            "policy_certified": False,
            "oos_ready": False,
            "allocation_authority": False,
            "risk_authority": False,
            "execution_authority": False,
            "demo_execution_authorized": False,
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
