from qore.infrastructure.core_stack_v2.shared_lab_seven_trader import (
    TraderControlTreatmentReceipt,
    TraderMetricVector,
    assess_seven_trader_reality,
)


def metrics() -> TraderMetricVector:
    return TraderMetricVector(
        pf=1.8,
        expectancy_r=0.2,
        drawdown_r=6.0,
        sharpe=1.7,
        sortino=2.2,
        payoff=1.4,
        post_cost_pf=1.5,
        winner_preservation=0.92,
        trade_count=100,
    )


def receipt(trader_id: str, *, changed: int = 5) -> TraderControlTreatmentReceipt:
    return TraderControlTreatmentReceipt(
        trader_id=trader_id,
        control=metrics(),
        treatment=metrics(),
        shared_signal_count=20,
        shared_consumed_count=20,
        changed_decision_count=changed,
        false_veto_count=0,
        false_opportunity_count=0,
        causal_lineage_exact=True,
        no_sizing_authority=True,
    )


def test_metric_uplift_alone_cannot_replace_mechanism_proof():
    item = receipt("VT31", changed=0)
    assert item.mechanism_proven is False


def test_one_dead_trader_cannot_be_pooled_rescued():
    expected = frozenset({"VT31", "VT08"})
    result = assess_seven_trader_reality(
        (receipt("VT31"), receipt("VT08", changed=0)),
        expected_trader_ids=expected,
    )
    assert result.failed_trader_ids == ("VT08",)
    assert result.l8_proven is False


def test_every_expected_trader_must_prove_causal_consumption():
    expected = frozenset({"VT31", "VT08"})
    result = assess_seven_trader_reality(
        (receipt("VT31"), receipt("VT08")),
        expected_trader_ids=expected,
    )
    assert result.l8_proven is True
