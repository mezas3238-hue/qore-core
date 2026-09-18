"""Fail-closed SHA rebinding for retained FundedNext SHADOW state.

This migration exists only for exact-SHA deployments of the same resident
runtime. It preserves capital economics and processed-anchor continuity while
changing the immutable deployment binding from the prior SHA to the checked-out
target SHA.

It never changes activation authority, entitlements, risk values or strategy
state. Broker positions/orders must be empty and the target activation must
remain order_submission_authorized=false.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import subprocess
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from qore.infrastructure.fundednext_live_guard import (
    DurableFundedNextLiveCapitalStore,
)
from qore.infrastructure.fundednext_runtime_state import (
    DurableFundedNextRuntimeStateStore,
)

EXPECTED_SERVER = "FundedNext-Server"


def _git_sha(root: Path) -> str:
    value = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if len(value) != 40:
        raise RuntimeError("target git SHA unavailable")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(raw, dict):
        raise ValueError(f"{path.name} must contain an object")
    return raw


def _account_fingerprint(account: object) -> str:
    material = "|".join(
        (
            str(account.login),
            str(account.server),
            str(account.company),
            str(account.currency),
        )
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _validate_target_activation(
    root: Path,
    *,
    target_sha: str,
    account_fingerprint: str,
) -> dict[str, Any]:
    path = root / "var" / "fundednext" / "live-activation.json"
    activation = _read_json(path)
    if activation.get("git_sha") != target_sha:
        raise ValueError("activation target SHA mismatch")
    if activation.get("account_identity_fingerprint") != account_fingerprint:
        raise ValueError("activation account fingerprint mismatch")
    if activation.get("expected_server") != EXPECTED_SERVER:
        raise ValueError("activation server mismatch")
    if activation.get("order_submission_authorized") is not False:
        raise ValueError("SHA migration requires SHADOW no-send authorization")
    if activation.get("no_send_passed") is not True:
        raise ValueError("target NO-SEND evidence missing")
    if activation.get("shadow_passed") is not True:
        raise ValueError("target order_check SHADOW evidence missing")

    for field, name in (
        ("no_send_evidence_sha256", "fundednext_mt5_no_send_probe.json"),
        ("shadow_evidence_sha256", "fundednext_mt5_order_check_probe.json"),
    ):
        evidence = root / "artifacts" / name
        if not evidence.exists() or _sha256(evidence) != activation.get(field):
            raise ValueError(f"{field} evidence binding mismatch")
        payload = _read_json(evidence)
        if payload.get("git_sha") != target_sha or payload.get("ok") is not True:
            raise ValueError(f"{name} target evidence mismatch")
        if payload.get("order_send_called") is True:
            raise ValueError(f"{name} reports order_send activity")
    return activation


def migrate_state(
    root: Path,
    *,
    target_sha: str,
    account_fingerprint: str,
) -> dict[str, Any]:
    state_dir = root / "var" / "fundednext"
    primary = state_dir / "capital-checkpoint.json"
    backup = state_dir / "capital-checkpoint.backup.json"
    runtime_path = state_dir / "runtime-state.json"

    any_capital = primary.exists() or backup.exists()
    if not any_capital and not runtime_path.exists():
        return {
            "schema": "qore.fundednext.shadow-sha-rebind.v1",
            "status": "INITIAL_DEPLOYMENT_NO_PRIOR_STATE",
            "target_sha": target_sha,
            "economic_values_changed": False,
            "processed_anchors_changed": False,
        }
    if not any_capital or not runtime_path.exists():
        raise ValueError("partial retained runtime state cannot be rebound")

    capital_store = DurableFundedNextLiveCapitalStore(primary, backup)
    runtime_store = DurableFundedNextRuntimeStateStore(runtime_path)
    checkpoint = capital_store.load_required()
    runtime_state = runtime_store.load()
    if runtime_state is None:
        raise ValueError("retained runtime state missing")

    if checkpoint.account_identity_fingerprint != account_fingerprint:
        raise ValueError("capital checkpoint account fingerprint drift")
    if runtime_state.account_identity_fingerprint != account_fingerprint:
        raise ValueError("runtime state account fingerprint drift")
    if checkpoint.git_sha != runtime_state.git_sha:
        raise ValueError("retained checkpoint/runtime SHA divergence")

    prior_sha = checkpoint.git_sha
    before = {
        "highest_closed_balance": str(checkpoint.highest_closed_balance),
        "active_mll": str(checkpoint.active_mll),
        "checkpoint_created_at": checkpoint.created_at.isoformat(),
        "checkpoint_updated_at": checkpoint.updated_at.isoformat(),
        "processed_anchors": runtime_state.processed_anchors,
        "runtime_highest_closed_balance": runtime_state.highest_closed_balance,
        "runtime_active_mll": runtime_state.active_mll,
        "runtime_service_started_at": runtime_state.service_started_at.isoformat(),
    }

    if prior_sha != target_sha:
        capital_store.store(replace(checkpoint, git_sha=target_sha))
        runtime_store.store(replace(runtime_state, git_sha=target_sha))

    after_checkpoint = capital_store.load_required()
    after_runtime = runtime_store.load()
    if after_runtime is None:
        raise ValueError("runtime state disappeared during SHA rebind")
    after = {
        "highest_closed_balance": str(after_checkpoint.highest_closed_balance),
        "active_mll": str(after_checkpoint.active_mll),
        "checkpoint_created_at": after_checkpoint.created_at.isoformat(),
        "checkpoint_updated_at": after_checkpoint.updated_at.isoformat(),
        "processed_anchors": after_runtime.processed_anchors,
        "runtime_highest_closed_balance": after_runtime.highest_closed_balance,
        "runtime_active_mll": after_runtime.active_mll,
        "runtime_service_started_at": after_runtime.service_started_at.isoformat(),
    }
    if before != after:
        raise ValueError("SHA rebind changed retained economic/runtime state")
    if after_checkpoint.git_sha != target_sha or after_runtime.git_sha != target_sha:
        raise ValueError("SHA rebind did not bind all retained state")

    evidence = {
        "schema": "qore.fundednext.shadow-sha-rebind.v1",
        "status": "REBOUND" if prior_sha != target_sha else "ALREADY_BOUND",
        "prior_sha": prior_sha,
        "target_sha": target_sha,
        "capital_checkpoint_preserved": True,
        "runtime_state_preserved": True,
        "economic_values_changed": False,
        "processed_anchors_changed": False,
        "processed_anchor_count": len(after_runtime.processed_anchors),
        "highest_closed_balance": str(after_checkpoint.highest_closed_balance),
        "active_mll": str(after_checkpoint.active_mll),
        "recorded_at": datetime.now(UTC).isoformat(),
    }
    out = root / "artifacts" / "fundednext_shadow_sha_rebind.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    return evidence


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    target_sha = _git_sha(root)

    mt5 = importlib.import_module("MetaTrader5")
    if not mt5.initialize():
        raise SystemExit(f"MT5 initialize failed: {mt5.last_error()}")
    try:
        account = mt5.account_info()
        if account is None:
            raise SystemExit("MT5 account unavailable")
        if str(account.server) != EXPECTED_SERVER:
            raise SystemExit("FundedNext server mismatch")
        positions = mt5.positions_get()
        orders = mt5.orders_get()
        if positions is None or orders is None:
            raise SystemExit("broker reconciliation unavailable")
        if len(positions) != 0 or len(orders) != 0:
            raise SystemExit("SHA migration requires zero positions and pending orders")
        fingerprint = _account_fingerprint(account)
        _validate_target_activation(
            root,
            target_sha=target_sha,
            account_fingerprint=fingerprint,
        )
        evidence = migrate_state(
            root,
            target_sha=target_sha,
            account_fingerprint=fingerprint,
        )
        print(json.dumps(evidence, sort_keys=True))
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
