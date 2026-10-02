from qore.infrastructure.cibo_arch2_terminal_recommendation_bundle import (
    ARCHITECT2_TERMINAL_RECOMMENDATION_BUNDLE,
    build_architect2_terminal_recommendation_bundle,
)


def test_terminal_bundle_contains_exact_four_ready_recommendations() -> None:
    bundle = build_architect2_terminal_recommendation_bundle()

    assert tuple(
        (item.workstream_id, item.recommendation)
        for item in bundle.recommendations
    ) == (
        ("T03", "FALSIFIED_AND_CLOSED"),
        ("T16", "FALSIFIED_AND_CLOSED"),
        ("PROVIDER_ECONOMICS", "SUPERSEDED_WITH_PROVEN_LINEAGE"),
        ("FORWARD_QUALIFICATION", "SUPERSEDED_WITH_PROVEN_LINEAGE"),
    )
    assert all(item.integrator_audit_required for item in bundle.recommendations)
    assert all(not item.canonical_ledger_modified for item in bundle.recommendations)
    assert all(not item.productive_authority for item in bundle.recommendations)


def test_terminal_bundle_is_deterministic_and_non_authoritative() -> None:
    first = ARCHITECT2_TERMINAL_RECOMMENDATION_BUNDLE
    second = build_architect2_terminal_recommendation_bundle()

    assert first == second
    assert first.fingerprint() == second.fingerprint()
    assert first.fingerprint().startswith("sha256:")
    assert len(first.fingerprint()) == 71
    assert first.canonical_ledger_modified is False
    assert first.phase22_v2_consumed is False
    assert first.merge_authority is False
    assert first.productive_authority is False
