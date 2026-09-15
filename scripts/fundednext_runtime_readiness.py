from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any


def _git_sha() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    sha = result.stdout.strip().lower()
    if len(sha) != 40 or any(ch not in "0123456789abcdef" for ch in sha):
        raise RuntimeError("git_head_is_not_full_sha")
    return sha


def _load(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"evidence_unavailable_or_invalid:{path}") from error
    if not isinstance(payload, dict):
        raise RuntimeError(f"evidence_not_object:{path}")
    return payload


def _time(value: object, name: str) -> datetime:
    if not isinstance(value, str):
        raise RuntimeError(f"timestamp_missing:{name}")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise RuntimeError(f"timestamp_not_aware:{name}")
    return parsed.astimezone(UTC)


def _fresh(payload: dict[str, Any], *, now: datetime, max_age: timedelta, name: str) -> bool:
    observed = _time(payload.get("timestamp_utc"), name)
    return observed <= now and now - observed <= max_age


def build_readiness(
    *,
    git_sha: str,
    no_send: dict[str, Any],
    shadow: dict[str, Any],
    heartbeat: dict[str, Any],
    guard: dict[str, Any],
    autostart: dict[str, Any],
    reboot: dict[str, Any],
    now: datetime,
    max_runtime_age: timedelta,
) -> dict[str, Any]:
    no_send_account = no_send.get("account", {})
    shadow_account = shadow.get("account", {})
    no_send_safety = no_send.get("safety", {})
    shadow_safety = shadow.get("safety", {})
    fingerprint = no_send_account.get("identity_fingerprint")

    no_send_ok = (
        no_send.get("ok") is True
        and no_send.get("git_sha") == git_sha
        and no_send.get("mode") == "NO_SEND"
        and no_send_account.get("server") == "FundedNext-Server"
        and isinstance(fingerprint, str)
        and len(fingerprint) == 64
        and no_send_safety.get("order_send_called") is False
        and no_send_safety.get("order_submission_authorized") is False
    )
    checks = shadow.get("checks")
    shadow_ok = (
        shadow.get("ok") is True
        and shadow.get("git_sha") == git_sha
        and shadow.get("mode") == "SHADOW_ORDER_CHECK_NO_SEND"
        and shadow_account.get("server") == "FundedNext-Server"
        and shadow_account.get("identity_fingerprint") == fingerprint
        and isinstance(checks, list)
        and len(checks) == 3
        and all(isinstance(item, dict) and item.get("ok") is True for item in checks)
        and shadow_safety.get("order_check_called") is True
        and shadow_safety.get("order_send_called") is False
        and shadow_safety.get("provider_mutation_requested") is False
    )
    heartbeat_ok = (
        heartbeat.get("schema") == "qore.fundednext.runtime-heartbeat.v1"
        and heartbeat.get("git_sha") == git_sha
        and heartbeat.get("state") == "RUNNING"
        and _fresh(
            heartbeat,
            now=now,
            max_age=max_runtime_age,
            name="heartbeat",
        )
    )
    guard_ok = (
        guard.get("schema") == "qore.fundednext.runtime-guard.v1"
        and guard.get("git_sha") == git_sha
        and guard.get("connected") is True
        and guard.get("server") == "FundedNext-Server"
        and _fresh(guard, now=now, max_age=max_runtime_age, name="guard")
        and guard.get("safety", {}).get("order_send_called") is False
    )
    autostart_ok = (
        autostart.get("schema") == "qore.fundednext.windows-autostart.v1"
        and autostart.get("git_sha") == git_sha
        and autostart.get("task_name") == "QORE FundedNext Runtime"
        and autostart.get("startup_mode") == "AtLogOnCurrentInteractiveUser"
        and autostart.get("multiple_instances") == "IgnoreNew"
    )
    reboot_ok = (
        reboot.get("schema") == "qore.fundednext.reboot-recovery.v1"
        and reboot.get("git_sha") == git_sha
        and reboot.get("passed") is True
        and reboot.get("heartbeat_after_boot") is True
        and reboot.get("guard_after_boot") is True
        and reboot.get("heartbeat_running") is True
        and reboot.get("guard_connected") is True
        and reboot.get("task_healthy") is True
    )
    actual_account_bound = no_send_ok and shadow_ok and fingerprint is not None
    ready = all(
        (
            actual_account_bound,
            heartbeat_ok,
            guard_ok,
            autostart_ok,
            reboot_ok,
        )
    )
    return {
        "schema": "qore.fundednext.first-execution-readiness.v1",
        "timestamp_utc": now.isoformat(),
        "git_sha": git_sha,
        "account_identity_fingerprint": fingerprint,
        "checks": {
            "actual_account_bound_on_this_sha": actual_account_bound,
            "no_send_passed_on_this_sha": no_send_ok,
            "shadow_order_check_passed_on_this_sha": shadow_ok,
            "runtime_heartbeat_current": heartbeat_ok,
            "runtime_guard_connected": guard_ok,
            "windows_autostart_installed": autostart_ok,
            "reboot_recovery_passed_on_this_sha": reboot_ok,
        },
        "safety": {
            "order_send_called_by_readiness": False,
            "provider_mutation_requested_by_readiness": False,
            "owner_activation_inferred": False,
        },
        "ready_for_owner_activation": ready,
        "ready_to_operate_stellar_instant": False,
        "remaining_after_readiness": (
            [] if ready else ["one-or-more-exact-sha-runtime-evidence-checks-failed"]
        ),
        "owner_activation_record_required": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--git-sha")
    parser.add_argument(
        "--no-send",
        type=Path,
        default=Path("artifacts/fundednext_mt5_no_send_probe.json"),
    )
    parser.add_argument(
        "--shadow",
        type=Path,
        default=Path("artifacts/fundednext_mt5_shadow_probe.json"),
    )
    parser.add_argument("--state-dir", type=Path, default=Path(r"C:\QORE\state"))
    parser.add_argument("--max-runtime-age-seconds", type=int, default=90)
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("artifacts/fundednext_first_execution_readiness.json"),
    )
    args = parser.parse_args()
    git_sha = (args.git_sha or _git_sha()).lower()
    if len(git_sha) != 40 or any(ch not in "0123456789abcdef" for ch in git_sha):
        raise RuntimeError("git_sha_must_be_full_lowercase_sha")
    now = datetime.now(UTC)
    payload = build_readiness(
        git_sha=git_sha,
        no_send=_load(args.no_send),
        shadow=_load(args.shadow),
        heartbeat=_load(args.state_dir / "heartbeat.json"),
        guard=_load(args.state_dir / "guard.json"),
        autostart=_load(args.state_dir / "autostart.json"),
        reboot=_load(args.state_dir / "reboot-recovery.json"),
        now=now,
        max_runtime_age=timedelta(seconds=args.max_runtime_age_seconds),
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    print(f"ARTIFACT={args.out.resolve()}")
    return 0 if payload["ready_for_owner_activation"] is True else 2


if __name__ == "__main__":
    sys.exit(main())
