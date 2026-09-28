from qore.infrastructure.cibo_ce2i_burned_non_promotion import (
    BURNED_NON_PROMOTION_REASONS,
    burned_non_promotion_payload,
    burned_non_promotion_sha256,
)


def test_phase19_descriptive_evidence_is_not_promoted_to_causal() -> None:
    payload = burned_non_promotion_payload()

    assert payload["source_findings"]["correlation_claimed"] is False
    assert payload["source_findings"]["walk_forward_surviving_policy_count"] == 0
    assert payload["governance"]["descriptive_evidence_promoted_to_causal"] is False
    assert payload["governance"]["failed_wfo_policy_promoted"] is False
    assert payload["governance"]["holdout_2017h1_used"] is False


def test_non_promoted_tools_are_exactly_portfolio_regime_failures() -> None:
    assert set(BURNED_NON_PROMOTION_REASONS) == {
        "T08",
        "T09",
        "T12",
        "T13",
        "T18",
    }
    assert "FACTOR_MAP_NOT_CERTIFIED" in BURNED_NON_PROMOTION_REASONS["T08"]
    assert "ZERO_WALK_FORWARD_POLICY_SURVIVORS" in BURNED_NON_PROMOTION_REASONS["T09"]
    assert (
        "CAUSAL_REGIME_BOUNDARIES_NOT_IDENTIFIED"
        in BURNED_NON_PROMOTION_REASONS["T12"]
    )


def test_non_promotion_hash_is_stable() -> None:
    first = burned_non_promotion_sha256()
    second = burned_non_promotion_sha256()

    assert first == second
    assert len(first) == 64
