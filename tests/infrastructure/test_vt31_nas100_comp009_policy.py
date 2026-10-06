from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.traders.vt31_nas100_comp008_policy import (
    Comparator008AdmissionFacts,
)
from qore.infrastructure.traders.vt31_nas100_comp009_policy import (
    POLICY_ID,
    Comparator009PretargetExitFacts,
    comparator009_admission_decision,
    comparator009_pretarget_exit_decision,
)


def _admission(**overrides: object) -> Comparator008AdmissionFacts:
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


def _exit(**overrides: object) -> Comparator009PretargetExitFacts:
    values: dict[str, object] = {
        "pre_dol1": True,
        "maximum_cognition_verified": True,
        "current_open_r": Decimal("-0.60"),
        "management_context": "MIXED",
        "reference_reclaim_age_minutes": 20,
        "destination_state": "SHALLOW",
        "entry_family": "breaker",
        "reference_volatility_state": "compressed",
        "recent_path_efficiency": Decimal("0.20"),
    }
    values.update(overrides)
    return Comparator009PretargetExitFacts(**values)  # type: ignore[arg-type]


def test_comp009_admission_is_exact_comp008_semantics() -> None:
    admitted = comparator009_admission_decision(_admission())
    blocked = comparator009_admission_decision(
        _admission(
            side="short",
            prior_day_state="bullish",
            cash_open_state="bullish",
            h1_state="bullish",
            confirmation_latency_minutes=8,
        )
    )
    assert admitted.policy_id == POLICY_ID
    assert admitted.admitted is True
    assert blocked.admitted is False
    assert (
        "COMP008:BULLISH_H1_MID_CONFIRMATION_CONFLICT"
        in blocked.abstention_reasons
    )


def test_comp009_weak_efficiency_exit_exact_boundary() -> None:
    at_boundary = comparator009_pretarget_exit_decision(
        _exit(recent_path_efficiency=Decimal("0.30"))
    )
    above = comparator009_pretarget_exit_decision(
        _exit(recent_path_efficiency=Decimal("0.3000001"))
    )
    assert at_boundary.exit_authorized is True
    assert at_boundary.comp003_base_exit_authorized is False
    assert at_boundary.weak_efficiency_exit_authorized is True
    assert above.exit_authorized is False
    assert above.weak_efficiency_exit_authorized is False


def test_comp009_weak_exit_requires_pre_dol1() -> None:
    decision = comparator009_pretarget_exit_decision(
        _exit(pre_dol1=False)
    )
    assert decision.exit_authorized is False
    assert decision.comp003_base_exit_authorized is False
    assert decision.weak_efficiency_exit_authorized is False


def test_comp009_weak_exit_requires_breaker_mixed_adverse_full_cognition() -> None:
    assert not comparator009_pretarget_exit_decision(
        _exit(entry_family="fair-value-gap")
    ).weak_efficiency_exit_authorized
    assert not comparator009_pretarget_exit_decision(
        _exit(management_context="SUPPORTIVE")
    ).weak_efficiency_exit_authorized
    assert not comparator009_pretarget_exit_decision(
        _exit(current_open_r=Decimal("-0.49"))
    ).weak_efficiency_exit_authorized
    assert not comparator009_pretarget_exit_decision(
        _exit(maximum_cognition_verified=False)
    ).weak_efficiency_exit_authorized
    assert not comparator009_pretarget_exit_decision(
        _exit(recent_path_efficiency=None)
    ).weak_efficiency_exit_authorized


def test_comp009_preserves_comp003_base_exit_routes() -> None:
    cautious = comparator009_pretarget_exit_decision(
        _exit(
            management_context="CAUTIOUS",
            recent_path_efficiency=None,
        )
    )
    assert cautious.exit_authorized is True
    assert cautious.comp003_base_exit_authorized is True
    assert cautious.weak_efficiency_exit_authorized is False


def test_no_capital_or_identity_fields_exist_in_comp009_exit_facts() -> None:
    names = set(Comparator009PretargetExitFacts.__dataclass_fields__)
    forbidden = {
        "volume",
        "lot",
        "lot_size",
        "equity",
        "balance",
        "leverage",
        "sizing",
        "capital",
        "portfolio_weight",
        "fold",
        "date",
        "terminal_outcome",
    }
    assert names.isdisjoint(forbidden)
