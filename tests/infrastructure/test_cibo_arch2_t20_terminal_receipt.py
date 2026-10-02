from decimal import Decimal

from qore.infrastructure.cibo_arch2_t20_forward_release_qualification import (
    TERMINAL_RECOMMENDATION,
    WAITING_RECOMMENDATION,
    T20ForwardReleaseQualification,
)
from qore.infrastructure.cibo_arch2_t20_terminal_receipt import (
    build_t20_terminal_receipt,
)


def _qualification(*, ready: bool) -> T20ForwardReleaseQualification:
    return T20ForwardReleaseQualification(
        manifest_candidate_rows=200,
        complete_release_lifecycles=200 if ready else 0,
        blocking_gap_count=0 if ready else 200,
        t20_release_gap_count=0 if ready else 200,
        release_coverage=Decimal("1") if ready else Decimal("0"),
        minimum_candidate_outcomes=200,
        required_candidate_coverage=Decimal("0.95"),
        all_complete_rows_capacity_reconciled=ready,
        four_fold_coverage_complete=ready,
        seven_lineage_coverage_complete=ready,
        population_minimum_met=True,
        empirical_t20_ready=ready,
        recommendation=(
            TERMINAL_RECOMMENDATION if ready else WAITING_RECOMMENDATION
        ),
        canonical_ledger_modified=False,
        phase22_v2_consumed=False,
        productive_authority=False,
    )


def test_t20_terminal_receipt_completes_only_on_frozen_population_gate() -> None:
    receipt = build_t20_terminal_receipt(_qualification(ready=True))

    assert receipt.terminal_ready is True
    assert receipt.recommendation == TERMINAL_RECOMMENDATION
    assert receipt.waiting_reason is None
    assert receipt.canonical_ledger_modified is False


def test_t20_terminal_receipt_waits_without_authoritative_lifecycles() -> None:
    receipt = build_t20_terminal_receipt(_qualification(ready=False))

    assert receipt.terminal_ready is False
    assert receipt.recommendation is None
    assert receipt.waiting_reason == WAITING_RECOMMENDATION
