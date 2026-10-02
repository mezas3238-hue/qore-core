from __future__ import annotations

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_next_policy_advanced_scientific_eligibility import (
    NEXT_POLICY_ADVANCED_SCIENTIFIC_ELIGIBILITY,
)
from qore.infrastructure.cibo_next_policy_code_bundle_lineage import (
    NEXT_POLICY_CODE_BUNDLE_LINEAGE,
)
from qore.infrastructure.cibo_phase22_v4_source_receipt import (
    EXPECTED_V4_SOURCE_KEYS,
    Phase22V4SourceBinding,
    Phase22V4SourceReceipt,
)


def _binding(
    symbol: str,
    timeframe: str,
    artifact_id: int,
) -> Phase22V4SourceBinding:
    return Phase22V4SourceBinding(
        symbol=symbol,
        timeframe=timeframe,
        artifact_id=artifact_id,
        artifact_digest="sha256:" + "a" * 64,
        collector_git_sha="b" * 40,
        manifest_sha256="sha256:" + "c" * 64,
        retained_bars=100,
        first_observed_at="2014-10-20T00:00:00+00:00",
        last_observed_at="2015-04-17T23:55:00+00:00",
    )


def _bindings() -> tuple[Phase22V4SourceBinding, ...]:
    return tuple(
        _binding(symbol, timeframe, index + 1)
        for index, (symbol, timeframe) in enumerate(EXPECTED_V4_SOURCE_KEYS)
    )


def _receipt(**overrides: object) -> Phase22V4SourceReceipt:
    values: dict[str, object] = {
        "candidate_id": (
            "CIBO_USD60_6M_HOLDOUT_2014-10-19_2015-04-19_V4"
        ),
        "source_availability_run_id": 1,
        "source_availability_artifact_id": 2,
        "source_availability_artifact_digest": "sha256:" + "d" * 64,
        "corpus_run_id": 3,
        "corpus_seal_artifact_id": 4,
        "corpus_seal_artifact_digest": "sha256:" + "e" * 64,
        "bindings": _bindings(),
        "policy_bundle_sha256": (
            NEXT_POLICY_CODE_BUNDLE_LINEAGE.fingerprint()
        ),
        "advanced_scientific_eligibility_sha256": (
            NEXT_POLICY_ADVANCED_SCIENTIFIC_ELIGIBILITY.fingerprint()
        ),
        "source_validation_complete": True,
    }
    values.update(overrides)
    return Phase22V4SourceReceipt(**values)  # type: ignore[arg-type]


def test_v4_source_receipt_requires_exact_ten_source_surface() -> None:
    receipt = _receipt()

    assert len(receipt.bindings) == 10
    assert receipt.payload()["source_validation_complete"] is True
    assert receipt.payload()["v3_lane_artifact_contents_used"] is False
    assert receipt.fingerprint().startswith("sha256:")


def test_v4_source_receipt_rejects_missing_source() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="exact 10-source surface",
    ):
        _receipt(bindings=_bindings()[:-1])


def test_v4_source_receipt_rejects_v3_lane_content_use() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="governance contamination",
    ):
        _receipt(v3_lane_artifact_contents_used=True)


def test_v4_source_receipt_cannot_authorize_fresh_execution() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="governance contamination",
    ):
        _receipt(fresh_trader_execution_authorized=True)
