"""VT08 FINAL #1 tri-state decision: never market-test incomplete TTrades."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab.vt08_a_final1_three_verdict_author_fidelity_gate_v1 import (
    FAMILY,
    MARKETS,
    REQUIRED_SOURCE_FIELDS,
    REQUIRED_VALIDATION_FIELDS,
    Final1Preflight,
    FinalVerdict,
    InterimState,
    RuleReceipt,
    SelectorMethod,
    VerifiedEconomicEvidence,
    final1_decision,
    long_stop_below_two_verified_levels,
)

T = datetime(2026, 10, 11, 8, tzinfo=UTC)
HASH_A = "a" * 64
HASH_B = "b" * 64
HASH_C = "c" * 64
HASH_D = "d" * 64
HASH_E = "e" * 64


def rule(key, *, method=SelectorMethod.DETERMINISTIC_ASOF, **kwargs):
    return RuleReceipt(
        key=key,
        source_uri="https://ttrades.com/timeframe-alignment-how-to-align-higher-and-lower-time-frames-for-precision-entries/",
        source_class="A_WRITTEN",
        selector_method=method,
        known_at=T, decision_at=T+timedelta(minutes=30),
        source_snapshot_sha256=HASH_A, verifier_sha256=HASH_B,
        **kwargs,
    )


def source(*, remove=frozenset(), receipts=None, validation=None):
    return Final1Preflight(
        receipts=(
            tuple(rule(k) for k in sorted(REQUIRED_SOURCE_FIELDS-remove))
            if receipts is None else tuple(receipts)
        ),
        validation_evidence=(
            REQUIRED_VALIDATION_FIELDS if validation is None else validation
        ),
        manifest_a_sha256=HASH_A,manifest_b_sha256=HASH_B,
        independent_period_sha256=HASH_C,
        broker_quote_and_fee_source_sha256=HASH_D,
    )


def econ(
    *, fills=100, profit="115", loss="100", expectancy="0.15",
    family=FAMILY, markets=MARKETS,
):
    return VerifiedEconomicEvidence(
        family=family,markets=markets,fills=fills,
        gross_profit_net_of_costs_r=Decimal(profit),
        gross_loss_net_of_costs_r=Decimal(loss),
        net_expectancy_per_fill_r=Decimal(expectancy),
        total_entry_decisions=100,
        event_history_sha256=HASH_C,
        independent_broker_executions_sha256=HASH_E,
    )


def test_missing_critical_eq_is_pending_not_go_when_active():
    s=source(remove=frozenset({"C2_EQ_REGIME_CONFIRMED"}))
    decision=final1_decision(
        source=s,source_adjudication_closed=False,
        economic=econ(profit="250"),
    )
    assert decision.status is InterimState.PENDING_SOURCE
    assert "UNRESOLVED_SOURCE_OR_CAUSAL_C2_EQ_REGIME_CONFIRMED" in decision.reasons
    assert decision.profit_factor_net is None
    assert not decision.live_orders_authorized


def test_unresolved_after_closed_is_no_evaluable_not_no_go():
    s=source(remove=frozenset({"RELEVANT_SWING_REFERENCE_PRE_C2"}))
    decision=final1_decision(
        source=s,source_adjudication_closed=True,economic=None,
    )
    assert decision.status is FinalVerdict.NO_EVALUABLE


def test_complete_source_without_test_is_not_claimed_go():
    decision=final1_decision(
        source=source(),source_adjudication_closed=True,economic=None,
    )
    assert decision.status is InterimState.READY_FOR_ONE_INDEPENDENT_TEST
    assert decision.fills is None


def test_pf_equals_1_15_is_not_go():
    d=final1_decision(
        source=source(),source_adjudication_closed=True,economic=econ(),
    )
    assert d.status is FinalVerdict.NO_GO
    assert d.profit_factor_net == "1.15"


def test_pf_above_1_15_and_positive_expectancy_go_research_only():
    d=final1_decision(
        source=source(),source_adjudication_closed=True,
        economic=econ(profit="116"),
    )
    assert d.status is FinalVerdict.GO
    assert d.profit_factor_net == "1.16"
    assert d.research_only
    assert not d.live_orders_authorized


def test_negative_expectancy_overrides_pf_success():
    d=final1_decision(
        source=source(),source_adjudication_closed=True,
        economic=econ(profit="130",expectancy="-0.03"),
    )
    assert d.status is FinalVerdict.NO_GO


def test_99_fills_no_evaluable_underpowered_not_no_go():
    d=final1_decision(
        source=source(),source_adjudication_closed=True,
        economic=econ(fills=99,profit="8"),
    )
    assert d.status is FinalVerdict.NO_EVALUABLE
    assert "FEWER_THAN_100_VERIFIABLE_FILLS" in d.reasons


def test_no_costs_cannot_promote_to_go_even_with_high_pf():
    s=source(
        validation=REQUIRED_VALIDATION_FIELDS-frozenset({
            "REPRODUCIBLE_BID_ASK_AND_FEES",
        }),
    )
    d=final1_decision(
        source=s,source_adjudication_closed=True,
        economic=econ(profit="600"),
    )
    assert d.status is FinalVerdict.NO_EVALUABLE
    assert "UNVERIFIED_REPRODUCIBLE_BID_ASK_AND_FEES" in d.reasons


def test_wrong_family_and_fewer_markets_no_evaluable():
    d=final1_decision(
        source=source(),source_adjudication_closed=True,
        economic=econ(profit="999",family="M30_M3_SHORT"),
    )
    assert d.status is FinalVerdict.NO_EVALUABLE
    d2=final1_decision(
        source=source(),source_adjudication_closed=True,
        economic=econ(profit="999",markets=frozenset({"NZDUSD"})),
    )
    assert d2.status is FinalVerdict.NO_EVALUABLE


def test_discretionary_source_without_two_blind_reviewers_is_unresolved():
    k="RELEVANT_SWING_REFERENCE_PRE_C2"
    receipts=[
        rule(v,method=(
            SelectorMethod.BLINDED_DISCRETIONARY_ASOF
            if v==k else SelectorMethod.DETERMINISTIC_ASOF
        ))
        for v in sorted(REQUIRED_SOURCE_FIELDS)
    ]
    d=final1_decision(
        source=source(receipts=receipts),
        source_adjudication_closed=True,economic=econ(profit="500"),
    )
    assert d.status is FinalVerdict.NO_EVALUABLE


def test_discretionary_two_agreeing_independent_raters_source_c_still_not_author_algorithm():
    k="RELEVANT_SWING_REFERENCE_PRE_C2"
    receipts=[
        rule(v,method=(
            SelectorMethod.BLINDED_DISCRETIONARY_ASOF
            if v==k else SelectorMethod.DETERMINISTIC_ASOF
        ),**({
            "reviewer1_id":"rater_A","reviewer2_id":"rater_B",
            "reviewer1_annotation_sha256":HASH_C,
            "reviewer2_annotation_sha256":HASH_D,
            "reviewers_agree":True,
        } if v==k else {}))
        for v in sorted(REQUIRED_SOURCE_FIELDS)
    ]
    d=final1_decision(
        source=source(receipts=receipts),
        source_adjudication_closed=True,economic=None,
    )
    assert d.status is InterimState.READY_FOR_ONE_INDEPENDENT_TEST


def test_future_source_clock_cannot_be_past_verified():
    k="RELEVANT_SWING_REFERENCE_PRE_C2"
    rules=[r for r in source().receipts if r.key != k]
    rules.append(RuleReceipt(
        key=k,source_uri="https://ttrades.com/relevant-swings-which-swing-highs-and-lows-matter-in-trading/",
        source_class="A_WRITTEN",selector_method=SelectorMethod.DETERMINISTIC_ASOF,
        known_at=T+timedelta(hours=2),decision_at=T,
        source_snapshot_sha256=HASH_A,verifier_sha256=HASH_B,
    ))
    d=final1_decision(
        source=source(receipts=rules),source_adjudication_closed=True,economic=None,
    )
    assert d.status is FinalVerdict.NO_EVALUABLE


def test_duplicate_receipts_no_green():
    rules=source().receipts
    d=final1_decision(
        source=source(receipts=rules+(rules[0],)),
        source_adjudication_closed=True,economic=econ(profit="999"),
    )
    assert d.status is FinalVerdict.NO_EVALUABLE
    assert "DUPLICATE_SOURCE_RECEIPTS" in d.reasons


def test_broker_tick_stop_below_min_both_is_unambiguous_comparison():
    assert long_stop_below_two_verified_levels(
        eq=Decimal("101.50"),breaker_low=Decimal("100.20"),
        stop=Decimal("100.19"),broker_tick=Decimal("0.01"),
    )
    assert not long_stop_below_two_verified_levels(
        eq=Decimal("101.50"),breaker_low=Decimal("100.20"),
        stop=Decimal("100.20"),broker_tick=Decimal("0.01"),
    )
    assert long_stop_below_two_verified_levels(
        eq=Decimal("99.30"),breaker_low=Decimal("100.20"),
        stop=Decimal("99.29"),broker_tick=Decimal("0.01"),
    )
    assert not long_stop_below_two_verified_levels(
        eq=Decimal("99.30"),breaker_low=Decimal("100.20"),
        stop=Decimal("99.35"),broker_tick=Decimal("0.01"),
    )


def test_invalid_broker_tick_fails_closed():
    with pytest.raises(ValueError,match="positive"):
        long_stop_below_two_verified_levels(
            eq=Decimal("101"),breaker_low=Decimal("100"),
            stop=Decimal("99"),broker_tick=Decimal("0"),
        )
