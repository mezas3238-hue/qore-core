from copy import deepcopy

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_single_account_manifest_integrity import (
    canonical_single_account_manifest_sha256,
    reseal_single_account_manifest,
    validate_single_account_manifest_sha256,
)


def _manifest() -> dict[str, object]:
    return {
        "schema": "qore.cibo.single-account-7trader-maximum-capability.v1",
        "initial_capital_usd": "60",
        "account_count": 1,
        "opportunities": [
            {
                "signal_fingerprint": "signal-1",
                "trader_id": "VT08_FOREX",
                "trader_opportunity": {
                    "decision_context": [["source_context_causal", "true"]],
                },
            }
        ],
    }


def test_reseal_and_validate_cover_current_manifest_content() -> None:
    sealed = reseal_single_account_manifest(_manifest())

    assert sealed["manifest_sha256"] == (
        canonical_single_account_manifest_sha256(sealed)
    )
    assert validate_single_account_manifest_sha256(sealed) == (
        sealed["manifest_sha256"]
    )


def test_manifest_mutation_without_reseal_fails_closed() -> None:
    sealed = reseal_single_account_manifest(_manifest())
    mutated = deepcopy(sealed)
    opportunities = mutated["opportunities"]
    assert isinstance(opportunities, list)
    opportunity = opportunities[0]
    assert isinstance(opportunity, dict)
    payload = opportunity["trader_opportunity"]
    assert isinstance(payload, dict)
    payload["decision_context"] = [
        ["source_context_causal", "true"],
        ["cibo_native_perception_complete", "true"],
    ]

    with pytest.raises(
        CiboCapitalManagementError,
        match="digest/content mismatch",
    ):
        validate_single_account_manifest_sha256(mutated)


def test_reseal_after_enrichment_changes_digest_and_restores_validity() -> None:
    source = reseal_single_account_manifest(_manifest())
    enriched = deepcopy(source)
    enriched["vt08_native_perception_enrichment"] = {
        "source_manifest_sha256": source["manifest_sha256"],
        "enriched": 1,
        "blocked_count": 0,
    }

    resealed = reseal_single_account_manifest(enriched)

    assert resealed["manifest_sha256"] != source["manifest_sha256"]
    assert validate_single_account_manifest_sha256(resealed) == (
        resealed["manifest_sha256"]
    )
    assert resealed["vt08_native_perception_enrichment"][
        "source_manifest_sha256"
    ] == source["manifest_sha256"]
