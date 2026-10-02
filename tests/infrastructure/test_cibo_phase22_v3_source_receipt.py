from __future__ import annotations

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_next_policy_advanced_scientific_eligibility import (
    NEXT_POLICY_ADVANCED_SCIENTIFIC_ELIGIBILITY,
)
from qore.infrastructure.cibo_next_policy_code_bundle_lineage import (
    NEXT_POLICY_CODE_BUNDLE_LINEAGE,
)
from qore.infrastructure.cibo_phase22_v3_source_receipt import (
    Phase22V3SourceBinding,
    Phase22V3SourceReceipt,
)
import pytest


def _binding(
    symbol: str,
    timeframe: str,
    artifact_id: int,
) -> Phase22V3SourceBinding:
    return Phase22V3SourceBinding(
        symbol=symbol,
        timeframe=timeframe,
        artifact_id=artifact_id,
        artifact_digest="sha256:" + "a" * 64,
        collector_git_sha="b" * 40,
        manifest_sha256="sha256:" + "c" * 64,
        retained_bars=100,
        first_observed_at="2015-04-20T00:00:00+00:00",
        last_observed_at="2015-10-16T23:55:00+00:00",
    )


def _bindings() -> tuple[Phase22V3SourceBinding, ...]:
    rows = (
        ("AUDJPY", "M5"),
        ("AUDUSD", "M5"),
        ("EURUSD", "M5"),
        ("GBPJPY", "M5"),
        ("GBPUSD", "M5"),
        ("NAS100", "M1"),
        ("NAS100", "M5"),
        ("USDCAD", "M5"),
        ("USDJPY", "M5"),
        ("XAUUSD", "M5"),
    )
    return tuple(
        _binding(symbol, timeframe, index + 1)
        for index, (symbol, timeframe) in enumerate(rows)
    )


def test_v3_source_receipt_requires_exact_ten_source_surface() -> None:
    receipt = Phase22V3SourceReceipt(
        candidate_id=(
            "CIBO_USD60_6M_HOLDOUT_2015-04-19_2015-10-19_V3"
        ),
        source_availability_run_id=1,
        source_availability_artifact_id=2,
        source_availability_artifact_digest="sha256:" + "d" * 64,
        corpus_run_id=3,
        corpus_seal_artifact_id=4,
        corpus_seal_artifact_digest="sha256:" + "e" * 64,
        bindings=_bindings(),
        policy_bundle_sha256=(
            NEXT_POLICY_CODE_BUNDLE_LINEAGE.fingerprint()
        ),
        advanced_scientific_eligibility_sha256=(
            NEXT_POLICY_ADVANCED_SCIENTIFIC_ELIGIBILITY.fingerprint()
        ),
        source_validation_complete=True,
    )

    assert len(receipt.bindings) == 10
    assert receipt.payload()["source_validation_complete"] is True
    assert receipt.fingerprint().startswith("sha256:")


def test_v3_source_receipt_rejects_missing_source() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="exact 10-source surface",
    ):
        Phase22V3SourceReceipt(
            candidate_id=(
                "CIBO_USD60_6M_HOLDOUT_2015-04-19_2015-10-19_V3"
            ),
            source_availability_run_id=1,
            source_availability_artifact_id=2,
            source_availability_artifact_digest="sha256:" + "d" * 64,
            corpus_run_id=3,
            corpus_seal_artifact_id=4,
            corpus_seal_artifact_digest="sha256:" + "e" * 64,
            bindings=_bindings()[:-1],
            policy_bundle_sha256=(
                NEXT_POLICY_CODE_BUNDLE_LINEAGE.fingerprint()
            ),
            advanced_scientific_eligibility_sha256=(
                NEXT_POLICY_ADVANCED_SCIENTIFIC_ELIGIBILITY.fingerprint()
            ),
            source_validation_complete=True,
        )


def test_v3_source_receipt_cannot_authorize_fresh_execution() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="governance contamination",
    ):
        Phase22V3SourceReceipt(
            candidate_id=(
                "CIBO_USD60_6M_HOLDOUT_2015-04-19_2015-10-19_V3"
            ),
            source_availability_run_id=1,
            source_availability_artifact_id=2,
            source_availability_artifact_digest="sha256:" + "d" * 64,
            corpus_run_id=3,
            corpus_seal_artifact_id=4,
            corpus_seal_artifact_digest="sha256:" + "e" * 64,
            bindings=_bindings(),
            policy_bundle_sha256=(
                NEXT_POLICY_CODE_BUNDLE_LINEAGE.fingerprint()
            ),
            advanced_scientific_eligibility_sha256=(
                NEXT_POLICY_ADVANCED_SCIENTIFIC_ELIGIBILITY.fingerprint()
            ),
            source_validation_complete=True,
            fresh_trader_execution_authorized=True,
        )
