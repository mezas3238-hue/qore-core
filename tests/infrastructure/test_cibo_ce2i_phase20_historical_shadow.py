from datetime import UTC, datetime, timedelta

from qore.infrastructure.cibo_ce2i_phase20_historical_shadow import (
    EVIDENCE_KIND,
    FINAL_HOLDOUT_END_EXCLUSIVE,
    REQUIRED_LINEAGES,
    SHADOW_START,
    HistoricalShadowObservation,
    evaluate_historical_shadow_population,
    policy_invariants,
)


def _population() -> tuple[HistoricalShadowObservation, ...]:
    rows: list[HistoricalShadowObservation] = []
    start = datetime(2021, 9, 23, 5, tzinfo=UTC)
    for index in range(210):
        entry = start + timedelta(days=index)
        lineage = REQUIRED_LINEAGES[index % len(REQUIRED_LINEAGES)]
        rows.append(
            HistoricalShadowObservation(
                trader_id=lineage,
                signal_fingerprint=f"shadow-{index:04d}",
                entry_at=entry,
                exit_at=entry + timedelta(hours=1),
            )
        )
    return tuple(rows)


def test_shadow_closes_population_wait_without_false_forward() -> None:
    report = evaluate_historical_shadow_population(_population())

    assert report.passed is True
    assert report.decision_epochs == 210
    assert report.candidate_outcomes == 210
    assert report.distinct_trading_days == 210
    assert report.represented_lineages == 7
    assert report.minimum_outcomes_any_lineage == 30
    assert len(report.folds) == 4
    assert all(fold.represented_lineages == 7 for fold in report.folds)
    assert report.physical_forward_wait_required is False
    assert report.selected_outcomes_gate_deferred is True
    assert report.provider_usd_execution_claimed is False
    assert report.evidence_relabelled_forward_observed is False
    assert report.final_holdout_2017h1_read is False
    assert report.certification_ready is False
    assert report.productive_authority is False


def test_shadow_policy_is_disjoint_from_final_2017h1() -> None:
    invariants = policy_invariants()

    assert SHADOW_START >= FINAL_HOLDOUT_END_EXCLUSIVE
    assert invariants["windows_disjoint"] is True
    assert invariants["evidence_kind"] == EVIDENCE_KIND
    assert invariants["historical_relabelled_forward_observed"] is False
    assert invariants["provider_usd_execution_imputation_allowed"] is False
    assert invariants["selected_outcomes_gate_deferred"] is True
    assert invariants["final_holdout_2017h1_must_remain_sealed"] is True
