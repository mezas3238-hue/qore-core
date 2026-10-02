from datetime import UTC, datetime
from pathlib import Path

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_phase22_one_shot_batch import (
    Phase22OneShotBatchCompletionReceipt,
    build_phase22_one_shot_burn_receipt,
)
from qore.infrastructure.cibo_phase22_one_shot_guard import (
    Phase22OneShotGuardStatus,
    assess_phase22_one_shot_guard,
)
from qore.infrastructure.cibo_phase22_store_contract import (
    PHASE22_STORE_IDENTITIES,
)
from qore.infrastructure.cibo_phase22_trader_parity_manifest import (
    CANONICAL_PHASE22_TRADER_IDS,
)

NOW = datetime(2026, 10, 1, 22, 0, tzinfo=UTC)
SHA = "a" * 40


def _digest(label: str) -> str:
    import hashlib

    return "sha256:" + hashlib.sha256(label.encode()).hexdigest()


def test_burn_receipt_consumes_v2_before_first_fresh_engine(
    tmp_path: Path,
) -> None:
    root = tmp_path / "phase22-v2-stores"
    burn = build_phase22_one_shot_burn_receipt(
        runner_git_sha=SHA,
        started_at=NOW,
        store_root=root,
    )

    assert burn.trader_ids == CANONICAL_PHASE22_TRADER_IDS
    assert burn.store_paths == tuple(
        item.relative_path for item in PHASE22_STORE_IDENTITIES
    )
    assert burn.fresh_outcome_access_started is True
    assert burn.holdout_consumed is True

    consumed = assess_phase22_one_shot_guard(
        consumption_receipt=burn.consumption_receipt(),
    )
    assert consumed.status is Phase22OneShotGuardStatus.CONSUMED
    assert consumed.authorized_to_emit_first_fresh_outcome is False


def test_burn_receipt_refuses_non_pristine_store_surface(
    tmp_path: Path,
) -> None:
    root = tmp_path / "phase22-v2-stores"
    root.mkdir()
    (root / "holdout-policy.json").write_text("{}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="not pristine"):
        build_phase22_one_shot_burn_receipt(
            runner_git_sha=SHA,
            started_at=NOW,
            store_root=root,
        )


def test_completion_receipt_requires_exact_full_batch(
    tmp_path: Path,
) -> None:
    burn = build_phase22_one_shot_burn_receipt(
        runner_git_sha=SHA,
        started_at=NOW,
        store_root=tmp_path / "phase22-v2-stores",
    )
    completion = Phase22OneShotBatchCompletionReceipt(
        burn_receipt_sha256=burn.fingerprint(),
        trader_artifact_sha256s=tuple(
            (trader_id, _digest(trader_id))
            for trader_id in CANONICAL_PHASE22_TRADER_IDS
        ),
        store_sha256s=tuple(
            (item.name, _digest(item.name))
            for item in PHASE22_STORE_IDENTITIES
        ),
        completed_at=NOW,
        all_traders_completed=True,
        all_stores_sealed=True,
        fresh_outcomes_emitted=True,
    )
    assert completion.fingerprint().startswith("sha256:")


def test_completion_receipt_rejects_partial_trader_surface(
    tmp_path: Path,
) -> None:
    burn = build_phase22_one_shot_burn_receipt(
        runner_git_sha=SHA,
        started_at=NOW,
        store_root=tmp_path / "phase22-v2-stores",
    )
    with pytest.raises(
        CiboCapitalManagementError,
        match="exact ordered 7/7",
    ):
        Phase22OneShotBatchCompletionReceipt(
            burn_receipt_sha256=burn.fingerprint(),
            trader_artifact_sha256s=tuple(
                (trader_id, _digest(trader_id))
                for trader_id in CANONICAL_PHASE22_TRADER_IDS[:-1]
            ),
            store_sha256s=tuple(
                (item.name, _digest(item.name))
                for item in PHASE22_STORE_IDENTITIES
            ),
            completed_at=NOW,
            all_traders_completed=True,
            all_stores_sealed=True,
            fresh_outcomes_emitted=True,
        )
