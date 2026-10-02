from __future__ import annotations

from pathlib import Path

RUNTIME = Path("scripts/qore_ctrader_demo_free_runtime.py")


def test_runtime_routes_every_direct_demo_submit_through_qore_risk() -> None:
    text = RUNTIME.read_text(encoding="utf-8")

    assert "def _submit_demo_request_through_qore_risk(" in text
    assert "authorize_phase20_demo_request(" in text
    assert "assert_phase20_demo_authorization_active(" in text
    assert "demo_result = submit_demo_request(request)" not in text
    assert text.count("_submit_demo_request_through_qore_risk(") >= 7
    assert '"account_wide_risk_active": True' in text
    assert '"risk_role": "SOVEREIGN_HARD_GOVERNOR"' in text


def test_sink_helper_requires_explicit_risk_authorization() -> None:
    text = Path(
        "src/qore/infrastructure/ctrader_demo_free_sink.py"
    ).read_text(encoding="utf-8")

    assert "risk_authorization: RiskAuthorization," in text
    assert "risk_authorization: RiskAuthorization | None" not in text


def test_runtime_reconciles_durable_risk_before_new_authorization() -> None:
    text = RUNTIME.read_text(encoding="utf-8")

    assert "def reconcile_execution_risk_reservations(" in text
    assert "confirmed_fill_authorization_ids(" in text
    assert "reconcile_demo_risk_reservations(" in text
    assert "risk.complete_boot_reconciliation(" in text
    assert "CTRADER_DEMO_RISK_BOOT_RECONCILED" in text
    snapshot_definition = text.index("def current_execution_risk_snapshot(")
    reconcile_call = text.index(
        "reconcile_execution_risk_reservations(observed_at=observed_at)",
        snapshot_definition,
    )
    account_read = text.index(
        "account_state = _account_state_from_demo_api(",
        snapshot_definition,
    )
    assert reconcile_call < account_read
