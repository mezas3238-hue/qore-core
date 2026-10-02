from datetime import UTC, datetime

from qore.infrastructure.cibo_ce2i_phase20_policy_candidate import (
    FROZEN_PHASE20_POLICY_CANDIDATE,
)
from qore.infrastructure.cibo_ce2i_phase20_train_prior import (
    prior_digest_sha256,
)
from qore.infrastructure.cibo_ce2i_phase21_shadow_policy_freeze import (
    PHASE21_SHADOW_SOURCE_ARTIFACT_DIGEST,
    PHASE21_SHADOW_SOURCE_ARTIFACT_ID,
    PHASE21_SHADOW_SOURCE_HEAD,
    PHASE21_SHADOW_SOURCE_RUN_ID,
    build_phase21_shadow_policy_freeze,
)


def _screen() -> dict[str, object]:
    candidate = FROZEN_PHASE20_POLICY_CANDIDATE
    return {
        "schema": "qore.cibo.phase21.historical-shadow-screen.v1",
        "status": "PASS",
        "candidate_id": candidate.candidate_id,
        "candidate_code_sha": candidate.code_sha,
        "candidate_parameter_sha256": candidate.parameter_sha256(),
        "train_prior_sha256": prior_digest_sha256(),
        "source_population": {
            "validation_rows": 332,
            "historical_provider_usd_economics": False,
        },
        "screen": {
            "passed": True,
            "validation_rows": 332,
            "selected_outcomes": 256,
            "represented_lineages": 7,
            "decision_epochs": 326,
            "distinct_trading_days": 91,
            "policy": {
                "realized_delta_ncu": "20",
                "max_drawdown_ncu": "4",
                "capital_productivity_ncu_per_risk_minute": "0.004",
            },
            "baseline": {
                "realized_delta_ncu": "15",
                "max_drawdown_ncu": "6",
                "capital_productivity_ncu_per_risk_minute": "0.002",
            },
            "folds": [
                {
                    "baseline_outcomes": 83,
                    "represented_lineages": 7,
                }
                for _ in range(4)
            ],
            "monte_carlo": {
                "simulation_count": 1000,
                "policy_median_ending_delta_ncu": "20",
                "baseline_median_ending_delta_ncu": "15",
                "policy_p95_drawdown_ncu": "5",
                "baseline_p95_drawdown_ncu": "7",
                "policy_capacity_breach_paths": 0,
                "baseline_capacity_breach_paths": 0,
            },
        },
        "governance": {
            "policy_retuned_from_shadow_outcomes": False,
            "historical_usd_claimed": False,
            "historical_provider_economics_claimed": False,
            "final_holdout_2017h1_read": False,
            "final_holdout_2017h1_status": "SEALED_UNTOUCHED",
        },
    }


def test_phase21_shadow_policy_freeze_seals_passed_screen() -> None:
    freeze = build_phase21_shadow_policy_freeze(
        screen=_screen(),
        frozen_at=datetime(2026, 10, 1, 13, 30, tzinfo=UTC),
    )

    assert freeze.sealed is True
    assert freeze.validation_rows == 332
    assert freeze.selected_outcomes == 256
    assert freeze.represented_lineages == 7
    assert freeze.monte_carlo_simulations == 1000
    assert freeze.source_run_id == PHASE21_SHADOW_SOURCE_RUN_ID
    assert freeze.source_artifact_id == PHASE21_SHADOW_SOURCE_ARTIFACT_ID
    assert freeze.source_artifact_digest == PHASE21_SHADOW_SOURCE_ARTIFACT_DIGEST
    assert freeze.source_head_sha == PHASE21_SHADOW_SOURCE_HEAD
    assert freeze.holdout_2017h1_read is False
