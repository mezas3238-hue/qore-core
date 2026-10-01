from qore.infrastructure.cibo_phase22_execution_manifest import (
    build_phase22_execution_manifest,
)
from qore.infrastructure.cibo_phase22_trader_parity_manifest import (
    CANONICAL_PHASE22_TRADER_IDS,
)


def test_execution_manifest_binds_exact_frozen_7_of_7_surface() -> None:
    manifest = build_phase22_execution_manifest()

    assert tuple(
        item.trader_id for item in manifest.trader_bindings
    ) == CANONICAL_PHASE22_TRADER_IDS
    assert manifest.candidate_id == (
        "CIBO_USD60_6M_HOLDOUT_2015-10-19_2016-04-19_V2"
    )
    assert manifest.source_receipt_sha256.startswith("sha256:")
    assert manifest.parity_manifest_sha256.startswith("sha256:")
    assert manifest.fresh_outcomes_executed is False
    assert manifest.productive_authority is False
    assert manifest.fingerprint().startswith("sha256:")
    assert manifest.payload()["manifest_sha256"] == manifest.fingerprint()
