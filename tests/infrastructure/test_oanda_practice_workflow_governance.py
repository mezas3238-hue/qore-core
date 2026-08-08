from __future__ import annotations

from pathlib import Path

_WORKFLOW_PATH = Path(".github/workflows/oanda-practice-market-feed.yml")


def _workflow() -> str:
    return _WORKFLOW_PATH.read_text(encoding="utf-8")


def test_practice_probe_workflow_remains_manual_only() -> None:
    content = _workflow()
    trigger_surface = content.split("permissions:", maxsplit=1)[0]

    assert "workflow_dispatch:" in trigger_surface
    assert "push:" not in trigger_surface
    assert "pull_request:" not in trigger_surface
    assert "schedule:" not in trigger_surface
    assert "workflow_call:" not in trigger_surface


def test_practice_probe_workflow_has_only_closed_approved_instrument_choices() -> None:
    content = _workflow()
    input_surface = content.split("permissions:", maxsplit=1)[0]

    assert "type: choice" in input_surface
    assert input_surface.count("- EUR_USD") == 1
    assert input_surface.count("- GBP_USD") == 1
    assert "USD_JPY" not in input_surface


def test_practice_probe_workflow_uses_only_external_secret_bindings() -> None:
    content = _workflow()

    assert (
        "QORE_OANDA_PRACTICE_ACCOUNT_ID: "
        "${{ secrets.QORE_OANDA_PRACTICE_ACCOUNT_ID }}"
    ) in content
    assert (
        "QORE_OANDA_PRACTICE_TOKEN: "
        "${{ secrets.QORE_OANDA_PRACTICE_TOKEN }}"
    ) in content
    assert "Bearer " not in content
    assert "personal-access-token" not in content


def test_practice_probe_workflow_audits_before_artifact_upload() -> None:
    content = _workflow()
    probe_index = content.index(
        "python -m qore.infrastructure.oanda_practice_operational_probe"
    )
    audit_index = content.index(
        "python -m qore.infrastructure.oanda_practice_evidence_audit_cli"
    )
    upload_index = content.index("uses: actions/upload-artifact@v4")

    assert probe_index < audit_index < upload_index
    assert '--expected-run-key "$QORE_PROBE_RUN_KEY"' in content
    assert '--expected-instrument "$QORE_OANDA_PRACTICE_INSTRUMENT"' in content
    assert '--audited-at "$QORE_EVIDENCE_AUDITED_AT"' in content
    assert "--maximum-observation-age-seconds 300" in content
    assert "Upload audited sanitized operational evidence" in content


def test_practice_probe_workflow_has_no_production_surface() -> None:
    content = _workflow().lower()

    assert "api-fxtrade.oanda.com" not in content
    assert "stream-fxtrade.oanda.com" not in content
    assert "production" not in content
    assert "live_account" not in content
    assert "real_capital" not in content
