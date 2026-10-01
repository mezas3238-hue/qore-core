from datetime import UTC, datetime
from pathlib import Path

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_phase22_one_shot_batch import (
    Phase22OneShotBatchCompletionReceipt,
    build_phase22_one_shot_claim_receipt,
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
RUN_ID = 123456
RUN_ATTEMPT = 1


def _digest(label: str) -> str:
    import hashlib

    return "sha256:" + hashlib.sha256(label.encode()).hexdigest()


def _claim(tmp_path: Path):
    return build_phase22_one_shot_claim_receipt(
        runner_git_sha=SHA,
        run_id=RUN_ID,
        run_attempt=RUN_ATTEMPT,
        started_at=NOW,
        store_root=tmp_path / "phase22-v2-stores",
    )


def _completion(claim_sha: str) -> Phase22OneShotBatchCompletionReceipt:
    return Phase22OneShotBatchCompletionReceipt(
        claim_receipt_sha256=claim_sha,
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


def test_claim_blocks_rerun_before_any_outcome(tmp_path: Path) -> None:
    claim_receipt = _claim(tmp_path)
    claim = claim_receipt.consumption_claim()

    assert claim.claim_committed is True
    assert claim.outcomes_emitted is False
    assert claim.claim_head_sha == SHA
    assert claim.claim_run_id == RUN_ID
    assert claim.claim_run_attempt == RUN_ATTEMPT

    guarded = assess_phase22_one_shot_guard(consumption_receipt=claim)
    assert guarded.status is Phase22OneShotGuardStatus.CLAIMED
    assert guarded.execution_claimed is True
    assert guarded.fresh_outcomes_already_emitted is False
    assert guarded.authorized_to_emit_first_fresh_outcome is False


def test_completion_finalizes_same_claim_as_consumed(tmp_path: Path) -> None:
    claim_receipt = _claim(tmp_path)
    claim = claim_receipt.consumption_claim()
    completion = _completion(claim_receipt.fingerprint())

    consumed = completion.consumed_receipt(claim=claim)

    assert consumed.claim_head_sha == claim.claim_head_sha
    assert consumed.claim_run_id == claim.claim_run_id
    assert consumed.claim_run_attempt == claim.claim_run_attempt
    assert consumed.outcomes_emitted is True
    assert consumed.outcome_bundle_sha256 == completion.fingerprint()

    guarded = assess_phase22_one_shot_guard(consumption_receipt=consumed)
    assert guarded.status is Phase22OneShotGuardStatus.CONSUMED
    assert guarded.authorized_to_emit_first_fresh_outcome is False


def test_claim_refuses_non_pristine_store_surface(tmp_path: Path) -> None:
    root = tmp_path / "phase22-v2-stores"
    root.mkdir()
    (root / "holdout-policy.json").write_text("{}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="not pristine"):
        build_phase22_one_shot_claim_receipt(
            runner_git_sha=SHA,
            run_id=RUN_ID,
            run_attempt=RUN_ATTEMPT,
            started_at=NOW,
            store_root=root,
        )


def test_completion_rejects_partial_trader_surface(tmp_path: Path) -> None:
    claim_receipt = _claim(tmp_path)
    with pytest.raises(
        CiboCapitalManagementError,
        match="exact ordered 7/7",
    ):
        Phase22OneShotBatchCompletionReceipt(
            claim_receipt_sha256=claim_receipt.fingerprint(),
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
