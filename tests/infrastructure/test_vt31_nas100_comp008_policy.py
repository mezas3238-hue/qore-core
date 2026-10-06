from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.traders.vt31_nas100_comp008_policy import (
    Comparator003PretargetExitFacts,
    Comparator008AdmissionFacts,
    ConfirmationLatencyState,
    ReclaimSequenceState,
    comparator003_pretarget_exit_allowed,
    comparator008_admission_decision,
    confirmation_latency_state,
    reclaim_sequence_state,
)


def _facts(**overrides: object) -> Comparator008AdmissionFacts:
    values: dict[str, object] = {
        "entry_family": "breaker",
        "side": "long",
        "prior_day_state": "bullish",
        "reference_volatility_state": "normal",
        "h4_state": "mixed",
        "h1_state": "mixed",
        "m15_state": "mixed",
        "premarket_state": "rotation",
        "cash_open_state": "rotation",
        "reference_reclaim_age_minutes": 20,
        "confirmation_latency_minutes": 4,
    }
    values.update(overrides)
    return Comparator008AdmissionFacts(**values)  # type: ignore[arg-type]


def test_confirmation_and_reclaim_buckets_are_exact() -> None:
    assert confirmation_latency_state(None) is ConfirmationLatencyState.NONE
    assert confirmation_latency_state(5) is ConfirmationLatencyState.FAST_LE5M
    assert confirmation_latency_state(6) is ConfirmationLatencyState.MID_6_10M
    assert confirmation_latency_state(10) is ConfirmationLatencyState.MID_6_10M
    assert confirmation_latency_state(11) is ConfirmationLatencyState.SLOW_GE11M
    assert reclaim_sequence_state(None) is ReclaimSequenceState.NONE
    assert reclaim_sequence_state(7) is ReclaimSequenceState.FRESH_LT8M
    assert reclaim_sequence_state(8) is ReclaimSequenceState.STALE_8_14M
    assert reclaim_sequence_state(14) is ReclaimSequenceState.STALE_8_14M
    assert reclaim_sequence_state(15) is ReclaimSequenceState.MATURE_GE15M


def test_expanded_reference_is_abstained() -> None:
    decision = comparator008_admission_decision(
        _facts(reference_volatility_state="expanded")
    )
    assert decision.admitted is False
    assert "COMP008:EXPANDED_REFERENCE" in decision.abstention_reasons


def test_order_block_requires_short_and_mature_reclaim() -> None:
    long_ob = comparator008_admission_decision(
        _facts(entry_family="order-block", side="long")
    )
    fresh_short = comparator008_admission_decision(
        _facts(
            entry_family="order-block",
            side="short",
            reference_reclaim_age_minutes=14,
        )
    )
    mature_short = comparator008_admission_decision(
        _facts(
            entry_family="order-block",
            side="short",
            reference_reclaim_age_minutes=15,
        )
    )
    assert long_ob.admitted is False
    assert fresh_short.admitted is False
    assert mature_short.admitted is True


def test_breaker_rotation_compressed_allows_exact_bullish_recovery() -> None:
    rejected = comparator008_admission_decision(
        _facts(
            side="short",
            prior_day_state="rotation",
            reference_volatility_state="compressed",
        )
    )
    recovered = comparator008_admission_decision(
        _facts(
            side="short",
            prior_day_state="rotation",
            reference_volatility_state="compressed",
            h1_state="bullish",
            m15_state="mixed",
            premarket_state="bullish",
            cash_open_state="rotation",
            reference_reclaim_age_minutes=7,
        )
    )
    assert rejected.admitted is False
    assert recovered.admitted is True


def test_fvg_fresh_fast_conflict_is_exact() -> None:
    rejected = comparator008_admission_decision(
        _facts(
            entry_family="fair-value-gap",
            side="short",
            reference_volatility_state="compressed",
            reference_reclaim_age_minutes=7,
            confirmation_latency_minutes=5,
        )
    )
    near_miss = comparator008_admission_decision(
        _facts(
            entry_family="fair-value-gap",
            side="short",
            reference_volatility_state="compressed",
            reference_reclaim_age_minutes=8,
            confirmation_latency_minutes=5,
        )
    )
    assert rejected.admitted is False
    assert near_miss.admitted is True


def test_breaker_bearish_compressed_h1_bullish_conflict() -> None:
    decision = comparator008_admission_decision(
        _facts(
            side="short",
            prior_day_state="bearish",
            reference_volatility_state="compressed",
            h1_state="bullish",
        )
    )
    assert decision.admitted is False
    assert (
        "COMP008:BREAKER_BEARISH_COMPRESSED_H1_BULLISH"
        in decision.abstention_reasons
    )


def test_rapid_conflicts_are_exact_conjunctions() -> None:
    a = comparator008_admission_decision(
        _facts(
            side="short",
            prior_day_state="bullish",
            reference_volatility_state="normal",
            h4_state="bullish",
            h1_state="mixed",
            m15_state="mixed",
            premarket_state="bearish",
            cash_open_state="bullish",
        )
    )
    b = comparator008_admission_decision(
        _facts(
            side="short",
            reference_volatility_state="normal",
            reference_reclaim_age_minutes=7,
            confirmation_latency_minutes=8,
        )
    )
    assert "COMP008:RAPID_BREAKER_CONFLICT_A" in a.abstention_reasons
    assert "COMP008:RAPID_BREAKER_CONFLICT_B" in b.abstention_reasons


def test_comp008_mid_confirmation_delta_is_exact() -> None:
    rejected = comparator008_admission_decision(
        _facts(
            side="short",
            prior_day_state="bullish",
            h1_state="bullish",
            cash_open_state="bullish",
            confirmation_latency_minutes=8,
            reference_reclaim_age_minutes=20,
        )
    )
    fast = comparator008_admission_decision(
        _facts(
            side="short",
            prior_day_state="bullish",
            h1_state="bullish",
            cash_open_state="bullish",
            confirmation_latency_minutes=5,
            reference_reclaim_age_minutes=20,
        )
    )
    assert (
        "COMP008:BULLISH_H1_MID_CONFIRMATION_CONFLICT"
        in rejected.abstention_reasons
    )
    assert fast.admitted is True


def test_negative_or_no_prefixed_strings_never_match_positive_states() -> None:
    decision = comparator008_admission_decision(
        _facts(
            prior_day_state="NO_bullish",
            h1_state="NO_bullish",
            cash_open_state="NO_bullish",
            reference_volatility_state="NO_expanded",
            side="short",
            confirmation_latency_minutes=8,
        )
    )
    assert decision.admitted is True


def _exit_facts(**overrides: object) -> Comparator003PretargetExitFacts:
    values: dict[str, object] = {
        "maximum_cognition_verified": True,
        "current_open_r": Decimal("-0.60"),
        "management_context": "SUPPORTIVE",
        "reference_reclaim_age_minutes": 20,
        "destination_state": "SHALLOW",
        "entry_family": "breaker",
        "reference_volatility_state": "compressed",
    }
    values.update(overrides)
    return Comparator003PretargetExitFacts(**values)  # type: ignore[arg-type]


def test_comp003_exit_requires_maximum_cognition_and_material_adverse() -> None:
    assert not comparator003_pretarget_exit_allowed(
        _exit_facts(maximum_cognition_verified=False)
    )
    assert not comparator003_pretarget_exit_allowed(
        _exit_facts(current_open_r=Decimal("-0.49"))
    )


def test_comp003_cautious_and_stale_mixed_routes() -> None:
    assert comparator003_pretarget_exit_allowed(
        _exit_facts(management_context="CAUTIOUS")
    )
    assert comparator003_pretarget_exit_allowed(
        _exit_facts(
            management_context="MIXED",
            reference_reclaim_age_minutes=8,
        )
    )
    assert not comparator003_pretarget_exit_allowed(
        _exit_facts(
            management_context="MIXED",
            reference_reclaim_age_minutes=15,
        )
    )


def test_comp003_fvg_nonshallow_and_nonob_normal_routes() -> None:
    assert comparator003_pretarget_exit_allowed(
        _exit_facts(
            entry_family="fair-value-gap",
            destination_state="DEEP",
        )
    )
    assert comparator003_pretarget_exit_allowed(
        _exit_facts(
            entry_family="breaker",
            reference_volatility_state="normal",
        )
    )
    assert not comparator003_pretarget_exit_allowed(
        _exit_facts(
            entry_family="order-block",
            reference_volatility_state="normal",
        )
    )
