from qore.infrastructure.traders.crt_pure_source_registry import CrtPureConceptId
from qore.infrastructure.traders.crt_pure_strategy_identity_memory import (
    CRT_PURE_CORE_EXECUTION_CONCEPTS,
    strategy_identity_fingerprint,
    strategy_identity_payload,
    strategy_identity_ready,
    unresolved_core_execution_concepts,
    validate_strategy_identity,
)


def test_strategy_identity_exposes_only_canonical_source_rules() -> None:
    payload = strategy_identity_payload()
    assert payload["methodology_family"] == "CRT"
    assert payload["methodology_variant"] == "PURE"
    assert payload["markets"] == ("AUDUSD", "USDJPY", "BTCUSD")
    assert payload["canonical_concepts"] == ("make_or_break_level",)
    rules = payload["canonical_rules"]
    assert isinstance(rules, dict)
    assert set(rules) == {"make_or_break_level"}


def test_core_execution_remains_fail_closed_until_source_closure() -> None:
    assert strategy_identity_ready() is False
    unresolved = unresolved_core_execution_concepts()
    assert unresolved == CRT_PURE_CORE_EXECUTION_CONCEPTS
    assert CrtPureConceptId.MAKE_OR_BREAK_LEVEL not in unresolved


def test_strategy_identity_guards_exclude_amd_and_level_b_authority() -> None:
    payload = strategy_identity_payload()
    guards = payload["identity_guards"]
    assert isinstance(guards, dict)
    assert guards["crt_amd_allowed"] is False
    assert guards["level_b_may_define_methodology"] is False
    assert guards["unresolved_rule_may_execute"] is False
    assert payload["strategy_identity_ready"] is False


def test_strategy_identity_is_fingerprinted_and_valid() -> None:
    validate_strategy_identity()
    assert len(strategy_identity_fingerprint()) == 64
