from __future__ import annotations

import json

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_phase22_v4_source_receipt import (
    EXPECTED_SOURCE_KEYS,
    FROZEN_V4_ADVANCED_ELIGIBILITY_SHA256,
    FROZEN_V4_POLICY_BUNDLE_SHA256,
    Phase22V4SourceBinding,
    Phase22V4SourceReceipt,
    load_phase22_v4_source_receipt,
)
from qore.infrastructure.cibo_phase22_v4_governance import V4_CANDIDATE_ID


def _receipt() -> Phase22V4SourceReceipt:
    bindings = tuple(
        Phase22V4SourceBinding(
            symbol=symbol,
            timeframe=timeframe,
            artifact_id=index + 1,
            artifact_digest="sha256:" + f"{index + 1:064x}",
            manifest_sha256="sha256:" + f"{index + 101:064x}",
            retained_bars=100 + index,
        )
        for index, (symbol, timeframe) in enumerate(EXPECTED_SOURCE_KEYS)
    )
    return Phase22V4SourceReceipt(
        candidate_id=V4_CANDIDATE_ID,
        source_availability_run_id=1,
        source_availability_artifact_id=2,
        source_availability_artifact_digest="sha256:" + "a" * 64,
        corpus_run_id=3,
        corpus_git_sha="c" * 40,
        corpus_seal_artifact_id=4,
        corpus_seal_artifact_digest="sha256:" + "b" * 64,
        bindings=bindings,
        policy_bundle_sha256=FROZEN_V4_POLICY_BUNDLE_SHA256,
        advanced_scientific_eligibility_sha256=(
            FROZEN_V4_ADVANCED_ELIGIBILITY_SHA256
        ),
        source_validation_complete=True,
    )


def test_v4_source_receipt_preserves_pre_v3_policy_and_no_authority() -> None:
    receipt = _receipt()
    assert receipt.policy_bundle_sha256 == FROZEN_V4_POLICY_BUNDLE_SHA256
    assert receipt.source_outcomes_inspected is False
    assert receipt.trader_logic_executed is False
    assert receipt.broker_mutation is False
    assert receipt.fresh_trader_execution_authorized is False


def test_v4_source_receipt_rejects_policy_drift() -> None:
    receipt = _receipt()
    payload = receipt.payload()
    payload["policy_bundle_sha256"] = "sha256:" + "f" * 64
    with pytest.raises(CiboCapitalManagementError, match="policy changed"):
        Phase22V4SourceReceipt(
            **{key: value for key, value in payload.items() if key != "schema"}
        )


def test_v4_source_receipt_roundtrip(tmp_path) -> None:
    receipt = _receipt()
    path = tmp_path / "receipt.json"
    path.write_text(json.dumps(receipt.payload()), encoding="utf-8")
    loaded = load_phase22_v4_source_receipt(path)
    assert loaded.fingerprint() == receipt.fingerprint()
