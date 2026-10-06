from qore.infrastructure.cibo_phase22_turtle_auxiliary_manifest import (
    AUXILIARY_ROLES,
    PHASE22_TURTLE_AUXILIARY_ARTIFACTS,
    TURTLE_SYMBOLS,
    phase22_turtle_auxiliary_manifest_payload,
    phase22_turtle_auxiliary_manifest_sha256,
)


def test_auxiliary_manifest_is_exact_ordered_five_by_three_surface() -> None:
    assert tuple(
        (item.symbol, item.role)
        for item in PHASE22_TURTLE_AUXILIARY_ARTIFACTS
    ) == tuple(
        (symbol, role)
        for symbol in TURTLE_SYMBOLS
        for role in AUXILIARY_ROLES
    )
    assert len(PHASE22_TURTLE_AUXILIARY_ARTIFACTS) == 15
    assert len(
        {item.artifact_id for item in PHASE22_TURTLE_AUXILIARY_ARTIFACTS}
    ) == 15


def test_auxiliary_manifest_contains_no_phase18_outcome_ledgers() -> None:
    payload = phase22_turtle_auxiliary_manifest_payload()
    assert payload["phase18_outcome_ledgers_included"] is False
    assert all(
        item.phase18_outcome_ledger is False
        for item in PHASE22_TURTLE_AUXILIARY_ARTIFACTS
    )
    assert all(
        item.pre_outcome_dependency is True
        for item in PHASE22_TURTLE_AUXILIARY_ARTIFACTS
    )


def test_auxiliary_manifest_digest_is_deterministic() -> None:
    first = phase22_turtle_auxiliary_manifest_sha256()
    second = phase22_turtle_auxiliary_manifest_sha256()
    assert first == second
    assert first.startswith("sha256:")
    assert len(first) == 71
