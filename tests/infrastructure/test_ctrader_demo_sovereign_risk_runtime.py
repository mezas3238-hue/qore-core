from __future__ import annotations

from pathlib import Path


RUNTIME = Path("scripts/qore_ctrader_demo_free_runtime.py")


def test_runtime_routes_every_direct_demo_submit_through_qore_risk() -> None:
    text = RUNTIME.read_text(encoding="utf-8")

    assert "def _submit_demo_request_through_qore_risk(" in text
    assert "authorize_phase20_demo_request(" in text
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
