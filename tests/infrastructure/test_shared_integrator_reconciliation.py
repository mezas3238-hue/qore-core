from qore.infrastructure.core_stack_v2.shared_integrator_reconciliation import (
    build_integrator_reconciliation,
)


def test_integrator_reconciliation_never_auto_promotes() -> None:
    report = build_integrator_reconciliation()
    assert report["auto_promotions"] == 0
    assert report["canonical_ledger_mutated"] is False
    assert report["final_holdout_authority"] is False
    assert report["productive_authority"] is False


def test_new_a_evidence_is_exposed_for_formal_closure_audit() -> None:
    report = build_integrator_reconciliation()
    ids = {
        row["master_work_id"]
        for row in report["closure_audit_candidates"]
    }
    assert {"MC-09", "MC-10", "MC-11", "MC-16", "WP-06"}.issubset(ids)
    assert {"STI-10", "STI-11", "STI-12", "STI-14"}.issubset(ids)


def test_b_dependency_open_evidence_stays_blocked() -> None:
    report = build_integrator_reconciliation()
    blocked = {
        row["master_work_id"]
        for row in report["blocked_candidates"]
    }
    assert {"GW-18", "GW-20", "GW-21", "MC-28"}.issubset(blocked)


def test_integrated_provider_capability_is_recognized_as_already_closed() -> None:
    report = build_integrator_reconciliation()
    closed = {
        row["master_work_id"]
        for row in report["already_closed"]
    }
    assert "GW-1" in closed
