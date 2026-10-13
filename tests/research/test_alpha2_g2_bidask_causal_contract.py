"""G2 synthetic quote/side/chronology guards; zero actual broker fills."""
from datetime import UTC, datetime, timedelta

import pytest

from qore.research.alpha2_g2_bidask_causal_contract import (
    SOURCE_BLOCKED,
    BrokerEvidenceError,
    NetDataReadiness,
    QuoteObservation,
    asof_quote,
    causal_side_reference,
)


def quote(
    *, price=100., at=None, available=None, account="demo-a", bid=None, ask=None,
):
    at = at or datetime(2023, 6, 1, 14, 0, tzinfo=UTC)
    available = available or at + timedelta(milliseconds=100)
    return QuoteObservation(
        symbol="EURUSD", broker_source_id="ctrader-demo",
        account_scope_id=account, quote_at=at, available_at=available,
        bid=price if bid is None else bid,
        ask=price+0.02 if ask is None else ask,
    )


def select(q, at):
    return asof_quote(
        (q,), decision_at=at, expected_symbol="EURUSD",
        broker_source_id="ctrader-demo", account_scope_id="demo-a",
    )


def test_visible_quote_after_exact_availability_not_before():
    q = quote()
    with pytest.raises(BrokerEvidenceError, match="no quote visible"):
        select(q, q.quote_at)
    assert select(q, q.available_at) == q


def test_long_and_short_pay_spread_on_both_sides():
    q = quote()
    assert causal_side_reference(q, position_direction=1, action="entry") == q.ask
    assert causal_side_reference(q, position_direction=1, action="exit") == q.bid
    assert causal_side_reference(q, position_direction=-1, action="entry") == q.bid
    assert causal_side_reference(q, position_direction=-1, action="exit") == q.ask


def test_stale_quote_fails_even_if_it_is_latest_received():
    q = quote()
    with pytest.raises(BrokerEvidenceError, match="stale"):
        select(q, q.available_at + timedelta(minutes=1))


def test_crossed_bidask_and_quote_before_availability_invalid():
    with pytest.raises(BrokerEvidenceError, match="inverted"):
        quote(bid=100.5, ask=99.5)
    t = datetime(2023, 6, 1, tzinfo=UTC)
    with pytest.raises(BrokerEvidenceError, match="after availability"):
        quote(at=t, available=t-timedelta(seconds=1))


def test_no_mixing_original_and_new_account_cohorts():
    q = quote(account="different-account")
    with pytest.raises(BrokerEvidenceError, match="mismatch"):
        select(q, q.available_at)


def test_data_missing_is_blocked_not_zero_costs():
    assert NetDataReadiness().gate() == SOURCE_BLOCKED
    # A fully authenticated source is only a data prerequisite, not edge proof.
    all_evidence = NetDataReadiness(
        full_bidask_quotes_asof=True,
        broker_symbol_contract_verified=True,
        commissions_asof_verified=True,
        swap_rollover_asof_verified=True,
        quote_to_fill_slippage_verified=True,
        macro_release_asof_verified=True,
        independent_fresh_holdout_verified=True,
    )
    assert all_evidence.gate() == "G2_DATA_PREREQUISITES_PRESENT_NOT_CERTIFIED"


def test_non_utc_and_nonfinite_are_rejected():
    t = datetime(2023, 6, 1)
    with pytest.raises(BrokerEvidenceError, match="UTC-aware"):
        quote(at=t, available=t)
    with pytest.raises(BrokerEvidenceError, match="nonfinite"):
        quote(bid=float("nan"))


def test_zero_spread_research_quote_must_never_become_free_fill():
    q = quote(bid=100.0, ask=100.0)
    assert q.spread == 0
    with pytest.raises(BrokerEvidenceError, match="ZERO_OR_CROSSED_SPREAD_QUARANTINED"):
        causal_side_reference(q, position_direction=1, action="entry")
    with pytest.raises(BrokerEvidenceError, match="ZERO_OR_CROSSED_SPREAD_QUARANTINED"):
        causal_side_reference(q, position_direction=-1, action="exit")


def test_boolean_direction_is_not_an_actual_signed_order_direction():
    q = quote()
    with pytest.raises(BrokerEvidenceError, match="invalid trading side"):
        causal_side_reference(q, position_direction=True, action="entry")
