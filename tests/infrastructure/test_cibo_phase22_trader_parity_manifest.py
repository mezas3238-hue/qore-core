import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_phase22_trader_parity_manifest import (
    ACTIVE_PHASE22_TRADER_PARITY_MANIFEST,
    CANONICAL_PHASE22_TRADER_IDS,
    CiboPhase22TraderParityManifest,
    Phase22TraderParityReceipt,
)


def _receipt(trader_id: str, population: int) -> Phase22TraderParityReceipt:
    return Phase22TraderParityReceipt(
        trader_id=trader_id,
        methodology_git_sha="1" * 40,
        replay_engine_sha256="sha256:" + "2" * 64,
        parameter_sha256="sha256:" + "3" * 64,
        historical_artifact_ref=f"artifact:historical:{trader_id}",
        parity_artifact_ref=f"artifact:parity:{trader_id}",
        parity_artifact_digest="sha256:" + "4" * 64,
        expected_population=population,
        observed_population=population,
        exact_match=True,
    )


def test_active_parity_manifest_binds_exact_7_of_7_evidence() -> None:
    manifest = ACTIVE_PHASE22_TRADER_PARITY_MANIFEST

    assert manifest is not None
    assert tuple(item.trader_id for item in manifest.receipts) == (
        CANONICAL_PHASE22_TRADER_IDS
    )
    assert tuple(item.observed_population for item in manifest.receipts) == (
        124,
        921,
        863,
        907,
        897,
        1039,
        806,
    )
    assert all(item.exact_match for item in manifest.receipts)
    assert all(not item.methodology_changed for item in manifest.receipts)
    assert all(not item.fresh_outcomes_executed for item in manifest.receipts)
    assert manifest.productive_authority is False
    assert manifest.fingerprint().startswith("sha256:")


def test_manifest_requires_exact_ordered_7_of_7_surface() -> None:
    receipts = tuple(
        _receipt(trader_id, index + 1)
        for index, trader_id in enumerate(CANONICAL_PHASE22_TRADER_IDS)
    )
    manifest = CiboPhase22TraderParityManifest(receipts=receipts)

    assert tuple(item.trader_id for item in manifest.receipts) == (
        CANONICAL_PHASE22_TRADER_IDS
    )
    assert manifest.fingerprint().startswith("sha256:")


def test_parity_receipt_rejects_population_drift() -> None:
    with pytest.raises(CiboCapitalManagementError, match="exact population"):
        Phase22TraderParityReceipt(
            trader_id="VT31_NAS100",
            methodology_git_sha="1" * 40,
            replay_engine_sha256="sha256:" + "2" * 64,
            parameter_sha256="sha256:" + "3" * 64,
            historical_artifact_ref="artifact:historical",
            parity_artifact_ref="artifact:parity",
            parity_artifact_digest="sha256:" + "4" * 64,
            expected_population=806,
            observed_population=805,
            exact_match=False,
        )
