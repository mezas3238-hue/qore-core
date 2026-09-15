from __future__ import annotations

import importlib.util
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import ModuleType

_NOW = datetime(2026, 9, 15, 10, 0, tzinfo=UTC)
_SHA = "a" * 40
_FINGERPRINT = "b" * 64


def _load_script() -> ModuleType:
    path = Path(__file__).parents[2] / "scripts" / "fundednext_runtime_readiness.py"
    spec = importlib.util.spec_from_file_location("fundednext_runtime_readiness", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _evidence() -> tuple[dict[str, object], ...]:
    timestamp = _NOW.isoformat()
    no_send = {
        "ok": True,
        "git_sha": _SHA,
        "mode": "NO_SEND",
        "account": {
            "server": "FundedNext-Server",
            "identity_fingerprint": _FINGERPRINT,
        },
        "safety": {
            "order_send_called": False,
            "order_submission_authorized": False,
        },
    }
    shadow = {
        "ok": True,
        "git_sha": _SHA,
        "mode": "SHADOW_ORDER_CHECK_NO_SEND",
        "account": {
            "server": "FundedNext-Server",
            "identity_fingerprint": _FINGERPRINT,
        },
        "checks": [{"ok": True}, {"ok": True}, {"ok": True}],
        "safety": {
            "order_check_called": True,
            "order_send_called": False,
            "provider_mutation_requested": False,
        },
    }
    heartbeat = {
        "schema": "qore.fundednext.runtime-heartbeat.v1",
        "git_sha": _SHA,
        "state": "RUNNING",
        "timestamp_utc": timestamp,
    }
    guard = {
        "schema": "qore.fundednext.runtime-guard.v1",
        "git_sha": _SHA,
        "connected": True,
        "server": "FundedNext-Server",
        "timestamp_utc": timestamp,
        "safety": {"order_send_called": False},
    }
    autostart = {
        "schema": "qore.fundednext.windows-autostart.v1",
        "git_sha": _SHA,
        "task_name": "QORE FundedNext Runtime",
        "startup_mode": "AtLogOnCurrentInteractiveUser",
        "multiple_instances": "IgnoreNew",
    }
    reboot = {
        "schema": "qore.fundednext.reboot-recovery.v1",
        "git_sha": _SHA,
        "passed": True,
        "heartbeat_after_boot": True,
        "guard_after_boot": True,
        "heartbeat_running": True,
        "guard_connected": True,
        "task_healthy": True,
    }
    return no_send, shadow, heartbeat, guard, autostart, reboot


def test_complete_exact_sha_evidence_is_ready_for_owner_activation() -> None:
    module = _load_script()
    no_send, shadow, heartbeat, guard, autostart, reboot = _evidence()
    payload = module.build_readiness(
        git_sha=_SHA,
        no_send=no_send,
        shadow=shadow,
        heartbeat=heartbeat,
        guard=guard,
        autostart=autostart,
        reboot=reboot,
        now=_NOW,
        max_runtime_age=timedelta(seconds=90),
    )
    assert payload["ready_for_owner_activation"] is True
    assert payload["ready_to_operate_stellar_instant"] is False
    assert payload["owner_activation_record_required"] is True
    assert payload["safety"]["order_send_called_by_readiness"] is False


def test_sha_mismatch_or_stale_heartbeat_fails_closed() -> None:
    module = _load_script()
    no_send, shadow, heartbeat, guard, autostart, reboot = _evidence()
    no_send["git_sha"] = "c" * 40
    heartbeat["timestamp_utc"] = (_NOW - timedelta(minutes=5)).isoformat()
    payload = module.build_readiness(
        git_sha=_SHA,
        no_send=no_send,
        shadow=shadow,
        heartbeat=heartbeat,
        guard=guard,
        autostart=autostart,
        reboot=reboot,
        now=_NOW,
        max_runtime_age=timedelta(seconds=90),
    )
    assert payload["ready_for_owner_activation"] is False
    assert payload["checks"]["no_send_passed_on_this_sha"] is False
    assert payload["checks"]["runtime_heartbeat_current"] is False
