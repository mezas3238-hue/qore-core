from __future__ import annotations

import hashlib
import importlib.util
import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from qore.infrastructure.fundednext_live_guard import (
    DurableFundedNextLiveCapitalStore,
    FundedNextLiveCapitalCheckpoint,
)
from qore.infrastructure.fundednext_runtime_state import (
    DurableFundedNextRuntimeStateStore,
    FundedNextRuntimeState,
)

OLD_SHA = "5" * 40
NEW_SHA = "7" * 40
FINGERPRINT = "a" * 64


def _migration():
    path = Path(__file__).parents[2] / "scripts" / "rebind_fundednext_shadow_state.py"
    spec = importlib.util.spec_from_file_location(
        "rebind_fundednext_shadow_state",
        path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_target_activation(root: Path, *, authorized: bool = False) -> None:
    artifacts = root / "artifacts"
    artifacts.mkdir(parents=True)
    no_send = artifacts / "fundednext_mt5_no_send_probe.json"
    shadow = artifacts / "fundednext_mt5_order_check_probe.json"
    no_send.write_text(
        json.dumps(
            {
                "ok": True,
                "git_sha": NEW_SHA,
                "safety": {"order_send_called": False},
            },
            sort_keys=True,
        )
        + "\n"
    )
    shadow.write_text(
        json.dumps(
            {
                "ok": True,
                "git_sha": NEW_SHA,
                "order_send_called": False,
            },
            sort_keys=True,
        )
        + "\n"
    )

    state_dir = root / "var" / "fundednext"
    state_dir.mkdir(parents=True)
    activation = {
        "git_sha": NEW_SHA,
        "account_identity_fingerprint": FINGERPRINT,
        "expected_server": "FundedNext-Server",
        "no_send_evidence_sha256": hashlib.sha256(no_send.read_bytes()).hexdigest(),
        "shadow_evidence_sha256": hashlib.sha256(shadow.read_bytes()).hexdigest(),
        "no_send_passed": True,
        "shadow_passed": True,
        "order_submission_authorized": authorized,
    }
    (state_dir / "live-activation.json").write_text(
        json.dumps(activation, sort_keys=True) + "\n"
    )


def _seed_retained_state(root: Path) -> None:
    state_dir = root / "var" / "fundednext"
    state_dir.mkdir(parents=True, exist_ok=True)
    created = datetime(2026, 9, 16, 1, 54, tzinfo=UTC)
    updated = datetime(2026, 9, 18, 18, 1, tzinfo=UTC)
    capital_store = DurableFundedNextLiveCapitalStore(
        state_dir / "capital-checkpoint.json",
        state_dir / "capital-checkpoint.backup.json",
    )
    capital_store.store(
        FundedNextLiveCapitalCheckpoint(
            git_sha=OLD_SHA,
            account_identity_fingerprint=FINGERPRINT,
            highest_closed_balance=Decimal("2000"),
            active_mll=Decimal("1880.00"),
            created_at=created,
            updated_at=updated,
        )
    )
    DurableFundedNextRuntimeStateStore(
        state_dir / "runtime-state.json"
    ).store(
        FundedNextRuntimeState(
            git_sha=OLD_SHA,
            account_identity_fingerprint=FINGERPRINT,
            highest_closed_balance="2000",
            active_mll="1880.00",
            processed_anchors=(
                "R38_EURUSD|2026-09-18T17:00:00+00:00",
                "R43_GBPUSD|2026-09-18T17:00:00+00:00",
            ),
            heartbeat_at=updated,
            last_reconciliation_at=updated,
            service_started_at=created,
        )
    )


def test_sha_rebind_preserves_capital_and_runtime_continuity(tmp_path: Path) -> None:
    migration = _migration()
    _write_target_activation(tmp_path)
    _seed_retained_state(tmp_path)

    migration._validate_target_activation(
        tmp_path,
        target_sha=NEW_SHA,
        account_fingerprint=FINGERPRINT,
    )
    evidence = migration.migrate_state(
        tmp_path,
        target_sha=NEW_SHA,
        account_fingerprint=FINGERPRINT,
    )

    state_dir = tmp_path / "var" / "fundednext"
    checkpoint = DurableFundedNextLiveCapitalStore(
        state_dir / "capital-checkpoint.json",
        state_dir / "capital-checkpoint.backup.json",
    ).load_required()
    state = DurableFundedNextRuntimeStateStore(
        state_dir / "runtime-state.json"
    ).load()
    assert state is not None
    assert checkpoint.git_sha == NEW_SHA
    assert state.git_sha == NEW_SHA
    assert checkpoint.highest_closed_balance == Decimal("2000")
    assert checkpoint.active_mll == Decimal("1880.00")
    assert state.highest_closed_balance == "2000"
    assert state.active_mll == "1880.00"
    assert state.processed_anchors == (
        "R38_EURUSD|2026-09-18T17:00:00+00:00",
        "R43_GBPUSD|2026-09-18T17:00:00+00:00",
    )
    assert evidence["economic_values_changed"] is False
    assert evidence["processed_anchors_changed"] is False


def test_sha_rebind_refuses_live_authorization(tmp_path: Path) -> None:
    migration = _migration()
    _write_target_activation(tmp_path, authorized=True)
    with pytest.raises(ValueError, match="SHADOW no-send"):
        migration._validate_target_activation(
            tmp_path,
            target_sha=NEW_SHA,
            account_fingerprint=FINGERPRINT,
        )


def test_sha_rebind_fails_closed_on_partial_retained_state(tmp_path: Path) -> None:
    migration = _migration()
    state_dir = tmp_path / "var" / "fundednext"
    state_dir.mkdir(parents=True)
    (state_dir / "runtime-state.json").write_text("{}\n")
    with pytest.raises(ValueError, match="partial retained"):
        migration.migrate_state(
            tmp_path,
            target_sha=NEW_SHA,
            account_fingerprint=FINGERPRINT,
        )
