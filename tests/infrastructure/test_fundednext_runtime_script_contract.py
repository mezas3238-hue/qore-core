from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_RUNTIME = _ROOT / "scripts" / "qore_fundednext_runtime.py"
_ACTIVATOR = _ROOT / "scripts" / "authorize_fundednext_live.ps1"
_WATCHDOG = _ROOT / "scripts" / "qore_fundednext_watchdog.ps1"


def test_h4_exit_comment_uses_broker_verified_29_character_limit() -> None:
    source = _RUNTIME.read_text(encoding="utf-8-sig")
    expected = '"comment": f"qore-h4-exit-{str(position.ticket)}"[:29],'
    assert expected in source
    assert '"comment": f"qore-h4-exit-{str(position.ticket)}"[:31],' not in source


def test_live_activation_adds_rule_freshness_properties_safely() -> None:
    source = _ACTIVATOR.read_text(encoding="utf-8-sig")
    assert "Add-Member -NotePropertyName rules_verified_at" in source
    assert "Add-Member -NotePropertyName rules_valid_until" in source
    assert "$Activation.rules_verified_at =" not in source
    assert "$Activation.rules_valid_until =" not in source


def test_live_activation_waits_for_old_writer_and_requires_new_live_runtime() -> None:
    source = _ACTIVATOR.read_text(encoding="utf-8-sig")
    assert "Wait-QoreRuntimeStopped 30" in source
    assert "Assert-NewLiveRuntime $AttemptStartedAt $GitSha 60" in source
    assert "$ServiceStarted -ge $AttemptStartedAt" in source
    assert "$Heartbeat -ge $ServiceStarted" in source
    assert "$Reconciled -ge $ServiceStarted" in source
    assert 'CommandLine -match "--mode\\s+live' in source
    assert '$Processes.Count -gt 1' in source


def test_live_activation_rolls_back_fail_closed_and_self_checks_watchdog() -> None:
    source = _ACTIVATOR.read_text(encoding="utf-8-sig")
    assert "Restore-ShadowFailClosed $Activation $Python" in source
    assert "$Activation.order_submission_authorized = $false" in source
    assert "Remove-Item $OwnerArtifactPath" in source
    assert "LIVE watchdog self-check failed" in source
    assert 'schema = "qore.fundednext.owner-live-activation.v2"' in source
    assert "Write-JsonAtomic $Activation $ActivationPath" in source


def test_watchdog_detects_missing_wrong_mode_and_multiple_runtime_processes() -> None:
    source = _WATCHDOG.read_text(encoding="utf-8-sig")
    assert '"runtime-process-missing"' in source
    assert '"runtime-mode-mismatch"' in source
    assert '"multiple-runtime-processes"' in source
    assert '"WATCHDOG_FAIL_CLOSED"' in source
    assert '"WATCHDOG_RESTART"' in source
    assert "runtime.lock" in source
