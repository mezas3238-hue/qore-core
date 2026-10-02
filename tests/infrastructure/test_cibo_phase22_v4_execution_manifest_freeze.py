from __future__ import annotations

from scripts.cibo_phase22_v4_materialize_execution_manifest import (
    build_freeze_payload,
    canonical_sha256,
)


def test_v4_execution_manifest_freeze_is_deterministic_and_nonexecuting() -> None:
    payload = build_freeze_payload(source_head_sha="a" * 40)
    frozen = dict(payload)
    digest = frozen.pop("freeze_sha256")

    assert digest == canonical_sha256(frozen)
    assert payload["source_head_sha"] == "a" * 40
    assert payload["exact_seven_trader_bindings"] is True
    assert len(payload["execution_manifest"]["trader_bindings"]) == 7
    assert payload["fresh_outcomes_executed"] is False
    assert payload["owner_authorization_present"] is False
    assert payload["broker_mutation_authorized"] is False
    assert payload["live_authorized"] is False
    assert payload["real_capital_authorized"] is False
    assert payload["production_authorized"] is False
    assert payload["merge_authorized"] is False
    assert payload["productive_authority"] is False


def test_v4_freeze_forbids_prior_store_reuse() -> None:
    payload = build_freeze_payload(source_head_sha="b" * 40)

    assert payload["v4_store_namespace_required"] is True
    assert payload["v2_store_reuse_authorized"] is False
    assert payload["v3_store_reuse_authorized"] is False
