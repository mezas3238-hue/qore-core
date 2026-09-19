from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import vt08_index_r49_frozen_robustness as r49


def test_r49_binds_exact_frozen_candidate() -> None:
    assert r49.CANDIDATE_ID == "VT08_INDEX_R47_TRANSPORT_SAFE_STRUCTURAL_DEMOTION_001"
    assert (
        r49.CANDIDATE_RULE_FINGERPRINT
        == "013bffb847dff546cdb2a31ac9931bdb1336596c540f6a72c5c729d1762c36c8"
    )
    assert r49.BOOTSTRAP_SEED == 20260919
    assert r49.BOOTSTRAP_PATHS == 10_000
    assert r49.BOOTSTRAP_BLOCK_LENGTH == 5
    assert r49.EXTRA_STRESSES == (Decimal("0.15"), Decimal("0.20"))


def test_r49_drawdown_and_losing_streak_helpers() -> None:
    values = (1.0, -0.5, -0.75, 0.25, -0.1)
    assert r49._max_drawdown(values) == 1.25
    assert r49._max_losing_streak(values) == 2


def test_r49_bootstrap_is_fixed_seed_and_fail_closed() -> None:
    values = tuple(Decimal(value) for value in ("0.2", "-0.1", "0.3", "-0.05", "0.1"))
    first = r49._moving_block_bootstrap(
        values,
        seed=7,
        paths=100,
        block_length=2,
    )
    second = r49._moving_block_bootstrap(
        values,
        seed=7,
        paths=100,
        block_length=2,
    )
    assert first == second
    assert first["source_sample"] == 5
    assert 0.0 <= first["positive_terminal_fraction"] <= 1.0


def test_r49_causal_leakage_guard_passes_frozen_rules() -> None:
    guard = r49._causal_leakage_guard()
    assert guard["rule_labels_forbidden_tokens"] == []
    assert guard["cross_index_forbidden_tokens"] == []
    assert guard["completed_h4_requires_close_before_decision"] is True
    assert guard["candidate_rule_fingerprint_matches_freeze"] is True
    assert guard["pass"] is True
