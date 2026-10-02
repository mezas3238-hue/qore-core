from pathlib import Path

import pytest

from qore.infrastructure.cibo_phase22_consumption_ledger import (
    build_phase22_execution_claim,
    load_phase22_execution_consumption_receipt,
    mark_phase22_outcomes_emitted,
    persist_phase22_consumed_receipt,
    persist_phase22_execution_claim,
)


def _claim() -> object:
    return build_phase22_execution_claim(
        candidate_id="CIBO_USD60_6M_HOLDOUT_2015-10-19_2016-04-19_V2",
        execution_manifest_sha256="sha256:" + "a" * 64,
        claim_head_sha="b" * 40,
        claim_run_id=123,
        claim_run_attempt=1,
    )


def test_durable_claim_is_create_once_and_replayable(tmp_path: Path) -> None:
    path = tmp_path / "receipt.json"
    claim = _claim()

    persist_phase22_execution_claim(claim=claim, path=path)
    loaded = load_phase22_execution_consumption_receipt(path)

    assert loaded == claim
    with pytest.raises(FileExistsError):
        persist_phase22_execution_claim(claim=claim, path=path)


def test_consumed_receipt_requires_same_immutable_claim(tmp_path: Path) -> None:
    path = tmp_path / "receipt.json"
    claim = _claim()
    persist_phase22_execution_claim(claim=claim, path=path)

    consumed = mark_phase22_outcomes_emitted(
        claim=claim,
        outcome_bundle_sha256="sha256:" + "c" * 64,
    )
    persist_phase22_consumed_receipt(consumed=consumed, path=path)

    loaded = load_phase22_execution_consumption_receipt(path)
    assert loaded == consumed
    assert loaded is not None
    assert loaded.outcomes_emitted is True

    with pytest.raises(FileExistsError):
        persist_phase22_consumed_receipt(consumed=consumed, path=path)


def test_outcome_cannot_exist_without_prior_durable_claim() -> None:
    with pytest.raises(ValueError, match="durable prior claim"):
        mark_phase22_outcomes_emitted(
            claim=build_phase22_execution_claim(
                candidate_id="candidate",
                execution_manifest_sha256="sha256:" + "d" * 64,
                claim_head_sha="e" * 40,
                claim_run_id=1,
                claim_run_attempt=1,
            ).__class__(
                candidate_id="candidate",
                execution_manifest_sha256="sha256:" + "d" * 64,
                outcomes_emitted=False,
            ),
            outcome_bundle_sha256="sha256:" + "f" * 64,
        )
