from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_RUNTIME = _ROOT / "scripts" / "qore_fundednext_runtime.py"
_ACTIVATOR = _ROOT / "scripts" / "authorize_fundednext_live.ps1"
_WATCHDOG = _ROOT / "scripts" / "qore_fundednext_watchdog.ps1"


def test_h4_exit_comment_uses_broker_verified_29_character_limit() -> None:
    source = _RUNTIME.read_text(encoding="utf-8-sig")
    expected = '"comment": f"qore-exit-{exit_label}-{str(position.ticket)}"[:29],'
    assert expected in source
    assert '"comment": f"qore-exit-{exit_label}-{str(position.ticket)}"[:31],' not in source


def test_live_activation_has_no_owner_rule_expiry_and_uses_automated_verification() -> None:
    source = _ACTIVATOR.read_text(encoding="utf-8-sig")
    assert "rules_verified_at" not in source
    assert "rules_valid_until" not in source
    assert "--lease-hours" not in source
    assert "qore.fundednext.provider-rules-refresh.v3" in source
    assert 'maximum_loss_fraction -ne "0.06"' in source
    assert 'reclassified_open_risk_fraction -ne "0.01"' in source
    assert "stop_loss_required" in source
    assert "AUTOMATIC_JIT_BEFORE_ORDER_SEND_PLUS_6H_PREWARM" in source
    assert "manual_rule_expiry_required = $false" in source


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
    assert 'schema = "qore.fundednext.owner-live-activation.v3"' in source
    assert "Write-JsonAtomic $Activation $ActivationPath" in source


def test_watchdog_detects_missing_wrong_mode_and_multiple_runtime_processes() -> None:
    source = _WATCHDOG.read_text(encoding="utf-8-sig")
    assert '"runtime-process-missing"' in source
    assert '"runtime-mode-mismatch"' in source
    assert '"multiple-runtime-processes"' in source
    assert '"WATCHDOG_FAIL_CLOSED"' in source
    assert '"WATCHDOG_RESTART"' in source
    assert "runtime.lock" in source

def test_live_runtime_accepts_only_010509_new_york_entry_anchors() -> None:
    source = _RUNTIME.read_text(encoding="utf-8-sig")
    assert "local.hour not in LIVE_ENTRY_ANCHORS_NY" in source
    assert "current_anchor_hour=anchor_local.hour" in source
    assert "if hour > anchor_local.hour:" in source
    assert "FINAL_CAUSAL_ENTRY_ANCHOR_NY" not in source


def test_runtime_gates_new_risk_on_certified_prop_policy() -> None:
    source = _RUNTIME.read_text(encoding="utf-8-sig")
    assert "load_certified_stellar_instant_policy" in source
    assert "certified-prop-policy-unavailable" in source
    assert '"CERTIFIED_PROP_POLICY_FAIL_CLOSED"' in source
    assert "or not certified_policy_ready" in source
    assert "certified_open_risk_fraction=(" in source
    assert "reclassified_open_risk_fraction" in source
