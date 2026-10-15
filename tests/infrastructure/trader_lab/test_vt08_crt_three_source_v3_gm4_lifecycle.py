"""G-M4 V3 causal lifecycle: independent outcome observation, no trade/sizing."""
from copy import deepcopy

import pytest

from qore.infrastructure.trader_lab.vt08_crt_three_source_v3_gm3_cognitive_replay import (
    audit_v3_positive_cognition,
)
from qore.infrastructure.trader_lab.vt08_crt_three_source_v3_gm4_lifecycle import (
    reconcile_v3_gm4_case,
)

SOURCE_POLICY = "VT08_CRT_THREE_SOURCE_QORE_V3_CSD_THIRD_CANDLE"


def _source() -> dict[str, object]:
    return {
        "schema": "qore.vt08.crt_three_source.v3.third_candle_development.v1",
        "policy_id": SOURCE_POLICY,
        "market": "AUDUSD",
        "source_event_id": "gm4-test-realistic-source",
        "c3_H4_opened_at_utc": "2025-03-03T08:00:00+00:00",
        "year_utc": "2025",
        "parent_direction": "BULLISH",
        "decision_clock_utc": "2025-03-03T08:45:00+00:00",
        "m15_confirmed_triples_checked": 1,
        "opposing_micro_patterns": 0,
        "structural_invalidation_price_if_candidate": "90",
        "conceptual_state": "CONCEPTUAL_CANDIDATE_V3",
        "why": "H4_PURGE_THEN_M15_SOURCE_AND_BODY_CONFIRM",
        "source_authority_adjudicated": False,
        "independent_method_review_complete": False,
        "not_a_trade": True,
        "no_sizing_or_capital_authority": True,
        "prior_dev_sample_not_fresh_holdout": True,
    }


def _post(
    outcome: str, hit: str | None = "2025-03-03T08:50:00+00:00"
) -> dict[str, object]:
    return {
        "schema": "qore.vt08.crt_three_source.v3.price_only_lifecycle.dev.v1",
        "policy_id": SOURCE_POLICY,
        "market": "AUDUSD",
        "source_event_id": "gm4-test-realistic-source",
        "c3_H4_opened_at_utc": "2025-03-03T08:00:00+00:00",
        "decision_clock_utc": "2025-03-03T08:45:00+00:00",
        "year_utc": "2025",
        "source_direction": "BULLISH",
        "source_m15_invalidating_extreme_relative": 90,
        "fixed_parent_h4_target_twice_relative": 200,
        "price_path_outcome": outcome,
        "first_hit_opened_at_utc": hit,
        "observed_m5_after_decision": 2,
        "not_a_trade": True,
        "no_PnL_or_sizing": True,
        "not_fresh_OOS": True,
    }


def _apply(outcome: str, hit: str | None = "2025-03-03T08:50:00+00:00") -> dict:
    src = _source()
    return reconcile_v3_gm4_case(src, audit_v3_positive_cognition(src), _post(outcome, hit))


def test_earliest_price_invalidation_is_causally_final_without_rearm() -> None:
    result = _apply("INVALIDATION_FIRST")
    assert result["initial_cognitive_action"] == "ABSTAIN"
    assert result["gm5_router_blocked_at_decision"]
    assert result["initial_confirmation_recognized"]
    assert result["stage_path"] == (
        "OBSERVED_EVENT", "HYPOTHESIS_FORMING", "AWAITING_CONFIRMATION",
        "CONFIRMED", "THESIS_INVALIDATED", "THESIS_KILLED",
    )
    assert result["terminal_observed_at_utc"] == "2025-03-03T08:55:00+00:00"
    assert result["terminal_observation_proven"] is True
    assert result["not_a_trade"] and result["no_PnL_or_sizing"]
    assert not result["GLOBAL_CERTIFIED"]


def test_ambiguous_same_m5_must_never_look_like_destination_win() -> None:
    result = _apply("INVALIDATION_FIRST_AMBIGUOUS_SAME_M5")
    assert result["last_causal_stage"] == "THESIS_KILLED"
    assert "THESIS_INVALIDATED" in result["stage_path"]


def test_destination_first_terminates_same_identity_without_position() -> None:
    result = _apply("DESTINATION_FIRST")
    assert result["stage_path"][-2:] == ("CONFIRMED", "THESIS_KILLED")
    assert result["no_resurrection_or_rearm"]
    assert result["terminal_observation_proven"]


def test_expiry_at_h4_c3_close_not_at_decision_clock() -> None:
    result = _apply("EXPIRED_WITHOUT_TOUCH", None)
    assert result["terminal_observed_at_utc"] == "2025-03-03T12:00:00+00:00"
    assert result["stage_path"][-1] == "THESIS_KILLED"
    assert result["terminal_observation_proven"]


@pytest.mark.parametrize("state", (
    "UNKNOWN_MISSING_ENTRY_OPEN_PRICE",
    "UNKNOWN_ENTRY_ALREADY_BEYOND_BARRIER",
    "UNKNOWN_MISSING_M5_BEFORE_TERMINAL",
    "UNKNOWN_BARRIER_GEOMETRY_INVALID",
))
def test_unknown_price_path_stays_unresolved_not_fake_terminal(state: str) -> None:
    r = _apply(state, None)
    assert r["terminal_observed_at_utc"] is None
    assert r["last_causal_stage"] == "CONFIRMED"
    assert r["terminal_observation_proven"] is False
    assert r["G_M4_PASS"] is False


def test_postdecision_different_prices_may_change_terminal_only() -> None:
    win = _apply("DESTINATION_FIRST")
    loss = _apply("INVALIDATION_FIRST")
    assert win["source_event_id"] == loss["source_event_id"]
    assert win["initial_cognitive_action"] == loss["initial_cognitive_action"]
    assert win["initial_cognitive_why"] == loss["initial_cognitive_why"]
    assert win["price_path_outcome_only_post_decision"] != loss[
        "price_path_outcome_only_post_decision"
    ]


@pytest.mark.parametrize("field", (
    "source_event_id", "market", "decision_clock_utc", "source_direction",
    "c3_H4_opened_at_utc",
))
def test_mismatched_postdecision_identity_causes_failure(field: str) -> None:
    src = _source()
    outcome = _post("DESTINATION_FIRST")
    outcome[field] = "FORGED"
    with pytest.raises(ValueError, match="identity or causal clock"):
        reconcile_v3_gm4_case(src, audit_v3_positive_cognition(src), outcome)


def test_contradictory_cognitive_authority_cannot_open_route() -> None:
    src = _source()
    cog = audit_v3_positive_cognition(src)
    for key, fake in (
        ("cognitive_action", "EXECUTE"),
        ("no_broker_order", False),
        ("cognition_GM3_pass", True),
    ):
        poisoned = deepcopy(cog)
        poisoned[key] = fake
        with pytest.raises(ValueError, match="fail-closed"):
            reconcile_v3_gm4_case(src, poisoned, _post("DESTINATION_FIRST"))


@pytest.mark.parametrize("where,key", (
    ("source", "future_H4_C3_close"),
    ("cognition", "sizing_lots"),
    ("price", "broker_fill_profit_factor"),
))
def test_any_future_sizing_or_pnl_payload_denied(where: str, key: str) -> None:
    src = _source()
    cog = audit_v3_positive_cognition(src)
    post = _post("INVALIDATION_FIRST")
    subject = {"source": src, "cognition": cog, "price": post}[where]
    subject[key] = 999
    with pytest.raises(ValueError, match="unexpected future/sizing"):
        reconcile_v3_gm4_case(src, cog, post)


@pytest.mark.parametrize("when", (
    "2025-03-03T08:40:00+00:00",
    "2025-03-03T12:00:00+00:00",
    "2025-03-03T12:05:00+00:00",
))
def test_market_first_hit_before_decision_or_after_h4_rejected(when: str) -> None:
    src = _source()
    with pytest.raises(ValueError, match="not causally observable"):
        reconcile_v3_gm4_case(
            src, audit_v3_positive_cognition(src), _post("DESTINATION_FIRST", when)
        )


def test_unknown_path_may_not_claim_hit_and_expiry_may_not_claim_winner() -> None:
    src = _source()
    cog = audit_v3_positive_cognition(src)
    with pytest.raises(ValueError, match="may not invent"):
        reconcile_v3_gm4_case(src, cog, _post("UNKNOWN_MISSING_ENTRY_OPEN_PRICE"))
    with pytest.raises(ValueError, match="fabricated price hit"):
        reconcile_v3_gm4_case(src, cog, _post("EXPIRED_WITHOUT_TOUCH"))


def test_terminal_cannot_relabel_unexpected_source_or_early_exec() -> None:
    src = _source()
    cog = audit_v3_positive_cognition(src)
    with pytest.raises(ValueError, match="unexpected price-only"):
        reconcile_v3_gm4_case(src, cog, _post("PROFIT_FACTOR_APPROVED"))
    src["conceptual_state"] = "WAIT_M15"
    with pytest.raises(ValueError, match="non-confirmed"):
        reconcile_v3_gm4_case(src, cog, _post("DESTINATION_FIRST"))
