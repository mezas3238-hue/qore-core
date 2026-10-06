from qore.infrastructure.cibo_phase22_store_contract import (
    PHASE22_STORE_IDENTITIES,
    phase22_store_contract_payload,
)


def test_phase22_store_surface_is_exactly_five_and_disjoint() -> None:
    assert len(PHASE22_STORE_IDENTITIES) == 5
    paths = tuple(item.relative_path for item in PHASE22_STORE_IDENTITIES)
    schemas = tuple(item.schema for item in PHASE22_STORE_IDENTITIES)
    hashes = tuple(item.empty_sha256() for item in PHASE22_STORE_IDENTITIES)

    assert len(paths) == len(set(paths))
    assert len(schemas) == len(set(schemas))
    assert len(hashes) == len(set(hashes))
    assert all(path.startswith("phase22-v2-stores/") for path in paths)


def test_phase22_store_contract_forbids_reuse_and_authority() -> None:
    payload = phase22_store_contract_payload()

    assert payload["store_reuse_allowed"] is False
    assert payload["fresh_outcomes_executed"] is False
    assert payload["productive_authority"] is False
