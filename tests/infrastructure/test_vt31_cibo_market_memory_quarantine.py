from qore.infrastructure.cibo_research_memory import (
    CiboResearchMemoryStore,
)
from qore.infrastructure.traders.vt31_nas100_cibo_market_memory import (
    DOSSIER_FINGERPRINT,
    build_market_memory_store,
    dossier_payload,
    market_memory_manifest,
)


def test_vt31_market_memory_uses_non_executive_research_store() -> None:
    store = build_market_memory_store()

    assert type(store) is CiboResearchMemoryStore
    assert len(store.retrieve()) > 1
    assert all(
        item.__class__.__module__
        == "qore.infrastructure.cibo_research_memory"
        for item in store.retrieve()
    )


def test_vt31_market_memory_preserves_governed_dossier_identity() -> None:
    dossier = dossier_payload()
    manifest = market_memory_manifest()

    assert dossier["dossier_fingerprint_sha256"] == DOSSIER_FINGERPRINT
    assert manifest["dossier_fingerprint"] == DOSSIER_FINGERPRINT
    assert manifest["governed_cibo_memory_store"] is True
    assert manifest["external_cibo_runtime_dependency"] is False
    assert manifest["rule_promotion_allowed"] is False
    assert manifest["fresh_holdout_opened"] is False
