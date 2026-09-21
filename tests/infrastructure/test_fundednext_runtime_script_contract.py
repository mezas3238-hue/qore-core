from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_RUNTIME = _ROOT / "scripts" / "qore_fundednext_runtime.py"
_ACTIVATOR = _ROOT / "scripts" / "authorize_fundednext_live.ps1"
_WATCHDOG = _ROOT / "scripts" / "qore_fundednext_watchdog.ps1"
_NO_SEND = _ROOT / "scripts" / "fundednext_mt5_no_send_probe.py"
_ORDER_CHECK = _ROOT / "scripts" / "fundednext_mt5_order_check_probe.py"
_VT31_LIVE = _ROOT / "src" / "qore" / "infrastructure" / "vt31_nas100_live.py"


def test_h4_exit_comment_uses_broker_verified_29_character_limit() -> None:
    source = _RUNTIME.read_text(encoding="utf-8-sig")
    expected = '"comment": f"qore-h4-exit-{str(position.ticket)}"[:29],'
    assert expected in source
    assert '"comment": f"qore-h4-exit-{str(position.ticket)}"[:31],' not in source


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
    assert "$Processes.Count -gt 1" in source


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
    assert '"WATCHDOG_MAINTENANCE"' in source
    assert "owner-maintenance-fence-active" in source
    assert "FileShare]::Delete" in source
    assert "restart-storm-fenced" in source
    assert "$MaximumRestartsPerWindow = 3" in source


def test_runtime_has_one_supervisor_and_cannot_self_restart_storm() -> None:
    source = _RUNTIME.read_text(encoding="utf-8-sig")
    main = source[source.index("def main() -> None:") :]
    assert "RUNTIME_FATAL_EXIT" in main
    assert "external-watchdog-with-storm-fence" in main
    assert "RUNTIME_FATAL_RECOVERY" not in main
    assert "restart_delay_seconds" not in main


def test_completed_m5_actor_portfolio_is_not_reported_as_unarmed() -> None:
    source = _RUNTIME.read_text(encoding="utf-8-sig")
    assert "m5_portfolio_keys = (" in source
    assert "key not in state.processed_anchors for key in m5_portfolio_keys" in source
    assert "armed_m5_snapshots is None and any(" in source


def test_startup_overlaps_immutable_memory_loading_without_parallel_mt5_preload() -> None:
    source = _RUNTIME.read_text(encoding="utf-8-sig")
    assert 'thread_name_prefix="qore-startup-memory"' in source
    assert "r34_cognitive_future = startup_memory.submit(" in source
    assert "audjpy_r42_memory_future = startup_memory.submit(" in source
    assert "for cache in m5_caches.values():\n        cache.preload(mt5" in source
    assert "startup_memory.shutdown(wait=True, cancel_futures=True)" in source


def test_live_runtime_accepts_only_010509_new_york_entry_anchors() -> None:
    source = _RUNTIME.read_text(encoding="utf-8-sig")
    assert "local.hour not in LIVE_ENTRY_ANCHORS_NY" in source
    assert "current_anchor_hour=anchor_local.hour" in source
    assert "if hour > anchor_local.hour:" in source
    assert "FINAL_CAUSAL_ENTRY_ANCHOR_NY" not in source


def test_live_runtime_registers_vt31_as_seventh_single_writer_trader() -> None:
    source = _RUNTIME.read_text(encoding="utf-8-sig")
    assert '"VT31_NAS100",' in source
    assert "**vt31_runtime_started_fields()" in source
    assert "manage_vt31_open_trade(" in source
    assert "evaluate_vt31_boundary(" in source
    assert "await_vt31_boundary_snapshot(" in source
    assert "vt31_cache.preload(mt5" in source
    assert "vt31_cache.refresh_incremental(mt5" in source


def test_vt31_lifecycle_is_not_routed_through_vt08_h4_exit_manager() -> None:
    source = _RUNTIME.read_text(encoding="utf-8-sig")
    assert "if lineage is TraderLineage.VT31_NAS100:" in source
    assert "VT31 owns its 16:00 NY lifecycle" in source


def test_vt31_nas100_is_broker_probed_before_shadow_or_live() -> None:
    no_send = _NO_SEND.read_text(encoding="utf-8-sig")
    order_check = _ORDER_CHECK.read_text(encoding="utf-8-sig")
    assert '"NAS100"' in no_send
    assert '"NAS100"' in order_check
    assert "PILOT_SYMBOL_MAP.get(symbol, symbol)" in no_send
    assert "PILOT_SYMBOL_MAP.get(symbol, symbol)" in order_check


def test_vt31_m1_feed_uses_ndx100_provider_symbol_for_preload_and_incremental() -> None:
    source = _VT31_LIVE.read_text(encoding="utf-8-sig")
    assert source.count("copy_rates_from_pos(\n            PROVIDER_SYMBOL,") >= 2
    assert "symbol_info_tick(PROVIDER_SYMBOL)" in source


def test_runtime_binds_certified_policy_and_capitalization_without_changing_vt31() -> None:
    source = _RUNTIME.read_text(encoding="utf-8-sig")
    assert "load_certified_stellar_instant_policy" in source
    assert "certified-prop-policy-unavailable" in source
    assert '"CERTIFIED_PROP_POLICY_FAIL_CLOSED"' in source
    assert "build_5k_mission_config" in source
    assert "DurableCapitalizationMissionStore" in source
    assert '"capitalization-mission.json"' in source
    assert "CapitalizationMissionState.BANK" in source
    assert "Vt08ForexCiboPosture.BANK" in source
    assert "mission_snapshot.new_risk_allowed_by_mission" in source
    assert '"CAPITALIZATION_MISSION_STATE_CHANGED"' in source
    assert '"capitalization_balance_target"' in source
    assert "VT31_DECISION_DEADLINE" in source
    assert "await_vt31_boundary_snapshot" in source
