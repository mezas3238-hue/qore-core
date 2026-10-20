"""VT08 FINAL #1 tri-state decision: never market-test incomplete TTrades."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab.vt08_a_final1_three_verdict_author_fidelity_gate_v1 import (
    C2_CLOSE_OBSERVABLE_FIELDS,
    FAMILY,
    MARKETS,
    REQUIRED_SOURCE_FIELDS,
    REQUIRED_VALIDATION_FIELDS,
    SOURCE_PAGES_BY_RULE,
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
        source_uri=sorted(SOURCE_PAGES_BY_RULE[key])[0],
        source_class="A_WRITTEN",
        selector_method=method,
        known_at=(
            T + timedelta(minutes=30) if key in C2_CLOSE_OBSERVABLE_FIELDS else T
        ),
        decision_at=T+timedelta(minutes=30),
        c2_opened_at=T, c3_opened_at=T+timedelta(minutes=30),
        source_snapshot_sha256=HASH_A, verifier_sha256=HASH_B,
        market="EURJPY", scenario_id="EURJPY-EXAMPLE-FROZEN",
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
    *, fills=100, profit="115", loss="100", expectancy=None,
    family=FAMILY, markets=MARKETS,
):
    return VerifiedEconomicEvidence(
        family=family,markets=markets,fills=fills,
        gross_profit_net_of_costs_r=Decimal(profit),
        gross_loss_net_of_costs_r=Decimal(loss),
        net_expectancy_per_fill_r=(
            Decimal(expectancy) if expectancy is not None
            else (Decimal(profit) - Decimal(loss)) / Decimal(fills)
        ),
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


def test_contradictory_negative_expectancy_and_positive_pf_are_not_accepted():
    d=final1_decision(
        source=source(),source_adjudication_closed=True,
        economic=econ(profit="130",expectancy="-0.03"),
    )
    assert d.status is FinalVerdict.NO_EVALUABLE
    assert "ECONOMIC_PROVENANCE_INVALID" in d.reasons


def test_real_negative_expectancy_and_pf_below_one_are_no_go():
    d=final1_decision(
        source=source(),source_adjudication_closed=True,
        economic=econ(profit="60",loss="100"),
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
        known_at=T+timedelta(hours=2),decision_at=T+timedelta(minutes=30),
        c2_opened_at=T,c3_opened_at=T+timedelta(minutes=30),
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


def test_prior_swing_confirmed_after_c2_open_is_rejected_even_if_before_c3():
    k="RELEVANT_SWING_REFERENCE_PRE_C2"
    rules=[r for r in source().receipts if r.key!=k]
    rules.append(RuleReceipt(
        key=k, source_uri="https://ttrades.com/relevant-swings-which-swing-highs-and-lows-matter-in-trading/",
        source_class="A_WRITTEN",
        selector_method=SelectorMethod.DETERMINISTIC_ASOF,
        known_at=T+timedelta(minutes=3),
        decision_at=T+timedelta(minutes=30),
        c2_opened_at=T, c3_opened_at=T+timedelta(minutes=30),
        source_snapshot_sha256=HASH_A,
        verifier_sha256=HASH_B,
    ))
    d=final1_decision(
        source=source(receipts=rules),source_adjudication_closed=True,
        economic=econ(profit="900"),
    )
    assert d.status is FinalVerdict.NO_EVALUABLE
    assert "UNRESOLVED_SOURCE_OR_CAUSAL_RELEVANT_SWING_REFERENCE_PRE_C2" in d.reasons


def test_wrong_c3_open_anchor_cannot_fool_source_contract():
    k="C3_POSITIONAL_OPEN_AND_ORDER_CLOCK"
    rules=[r for r in source().receipts if r.key!=k]
    rules.append(RuleReceipt(
        key=k, source_uri="https://ttrades.com/positional-entries-enter-before-the-expansion/",
        source_class="A_WRITTEN",
        selector_method=SelectorMethod.DETERMINISTIC_ASOF,
        known_at=T,
        decision_at=T+timedelta(minutes=33),
        c2_opened_at=T,c3_opened_at=T+timedelta(minutes=30),
        source_snapshot_sha256=HASH_A,
        verifier_sha256=HASH_B,
    ))
    d=final1_decision(
        source=source(receipts=rules),source_adjudication_closed=True,economic=None,
    )
    assert d.status is FinalVerdict.NO_EVALUABLE

def test_generic_ttrades_page_is_not_valid_for_unrelated_eq_receipt():
    receipt = rule("C2_EQ_REGIME_CONFIRMED")
    spoofed = replace(
        receipt, source_uri="https://ttrades.com/relevant-swings-which-swing-highs-and-lows-matter-in-trading/",
    )
    assert not spoofed.validated()
    assert receipt.validated()


def test_source_page_with_trailing_query_or_fragment_is_not_canonical():
    receipt = rule("C2_EQ_REGIME_CONFIRMED")
    assert not replace(receipt, source_uri=receipt.source_uri + "?test=yes").validated()
    assert not replace(receipt, source_uri=receipt.source_uri + "#different").validated()


@pytest.mark.parametrize("profit,loss,expectancy", [
    ("NaN", "100", "0"),
    ("Infinity", "100", "0"),
    ("200", "NaN", "0"),
    ("200", "100", "NaN"),
    ("200", "100", "Infinity"),
])
def test_nonfinite_economic_numbers_cannot_be_certified(profit, loss, expectancy):
    d = final1_decision(
        source=source(), source_adjudication_closed=True,
        economic=econ(profit=profit, loss=loss, expectancy=expectancy),
    )
    assert d.status is FinalVerdict.NO_EVALUABLE
    assert "ECONOMIC_PROVENANCE_INVALID" in d.reasons


def test_bool_fill_count_cannot_pass_as_integer():
    evidence = replace(econ(profit="116"), fills=True)
    d = final1_decision(
        source=source(), source_adjudication_closed=True, economic=evidence,
    )
    assert d.status is FinalVerdict.NO_EVALUABLE


def test_stop_rejects_nan_and_infinity_levels():
    with pytest.raises(ValueError, match="finite positive"):
        long_stop_below_two_verified_levels(
            eq=Decimal("NaN"), breaker_low=Decimal("100"),
            stop=Decimal("99"), broker_tick=Decimal("0.01"),
        )
    with pytest.raises(ValueError, match="finite positive"):
        long_stop_below_two_verified_levels(
            eq=Decimal("101"), breaker_low=Decimal("100"),
            stop=Decimal("99"), broker_tick=Decimal("Infinity"),
        )


def test_all_frozen_source_fields_have_explicit_primary_pages():
    assert set(SOURCE_PAGES_BY_RULE) == REQUIRED_SOURCE_FIELDS
    assert all(
        uris and all(uri.startswith("https://ttrades.com/") for uri in uris)
        for uris in SOURCE_PAGES_BY_RULE.values()
    )

def test_false_c2_eq_known_at_open_is_not_admitted():
    r = rule("C2_EQ_REGIME_CONFIRMED")
    assert r.validated()
    assert not replace(r, known_at=T).validated()


def test_target_not_verified_at_entry_cannot_be_declared_untouched():
    r = rule("EXTERNAL_TARGET_UNTOUCHED_ASOF")
    assert r.validated()
    assert not replace(r, known_at=T + timedelta(minutes=12)).validated()


def test_early_cisd_receipt_cannot_claim_final_c2_close_in_advance():
    r = rule("C2_CLOSURE_AND_M3_CISD_PS_ASOF")
    assert not replace(r, known_at=T + timedelta(minutes=27)).validated()


def test_cross_market_receipt_join_must_not_be_ready():
    rules = list(source().receipts)
    rules[0] = replace(rules[0], market="USDCHF")
    d = final1_decision(
        source=source(receipts=rules), source_adjudication_closed=True,
        economic=econ(profit="160"),
    )
    assert d.status is FinalVerdict.NO_EVALUABLE
    assert "CROSS_RECEIPT_SCENARIO_OR_CLOCK_MISMATCH" in d.reasons


def test_cross_event_or_clock_receipt_join_must_not_be_ready():
    rules = list(source().receipts)
    rules[0] = replace(rules[0], scenario_id="EURJPY-OTHER")
    d = final1_decision(
        source=source(receipts=rules), source_adjudication_closed=True,
        economic=None,
    )
    assert d.status is FinalVerdict.NO_EVALUABLE
    assert "CROSS_RECEIPT_SCENARIO_OR_CLOCK_MISMATCH" in d.reasons
    rules[0] = replace(
        rules[0], scenario_id="EURJPY-EXAMPLE-FROZEN",
        c2_opened_at=T + timedelta(minutes=30),
        c3_opened_at=T + timedelta(minutes=60),
        decision_at=T + timedelta(minutes=60),
        known_at=T + timedelta(minutes=60),
    )
    d2 = final1_decision(
        source=source(receipts=rules), source_adjudication_closed=True,
        economic=None,
    )
    assert d2.status is FinalVerdict.NO_EVALUABLE
    assert "CROSS_RECEIPT_SCENARIO_OR_CLOCK_MISMATCH" in d2.reasons


def test_missing_market_or_scenario_cannot_create_fidelity_receipt():
    r = rule("RELEVANT_SWING_REFERENCE_PRE_C2")
    assert r.validated()
    assert not replace(r, market="").validated()
    assert not replace(r, scenario_id="").validated()
    assert not replace(r, market="NAS100").validated()
