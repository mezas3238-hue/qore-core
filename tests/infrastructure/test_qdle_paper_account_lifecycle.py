"""Atomic P0 research-only QDLE lifecycle tests. No VPS or broker orders."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D

import pytest
from qore.infrastructure.qore_dynamic_lot_engine import (
    QDLE, QDLEAccount, QDLESymbol, QDLEIntent, QDLEError, BrokerValuation,
)

T = datetime(2020, 1, 1, tzinfo=timezone.utc)


class SyntheticBroker:
    def value(self, symbol, intent, now):
        return BrokerValuation(D("100"), D("10"), now, "PAPER_TEST_ONLY")

    def check_volume(self, symbol, intent, lots):
        assert lots >= D(".01")


def account(n, now):
    return QDLEAccount(
        "PAPER", "FundedNext", "USD", n, now, D("2000"), D("2000"),
        D("1900"), D("3"), D("60"), D("0"), D("60"),
    )


def symbol(now):
    return QDLESymbol(
        "EURUSD", ("EURUSD",), D(".01"), D("40"), D(".01"),
        D(0), D(".00001"), D("1"), D("100000"), "USD",
        D("7"), "PAPER_TEST_ONLY", now,
    )


def intent(rid, seq):
    return QDLEIntent(
        rid, "trader", "EURUSD", "BUY", D("1.1"), D("1.09"),
        D("3"), D("3"), D("3"), D("60"), D("4"), D("1900"),
        "SOVEREIGN_BANK", D(0), seq,
    )


def engine(tmp_path):
    q = QDLE(
        tmp_path / "research.sqlite", SyntheticBroker(),
        research_paper_mode=True, strict_live_fee_evidence=False,
        strict_four_motor_evidence=False,
    )
    q.publish_account(account(1, T))
    q.publish_symbol(symbol(T))
    return q


def test_single_sqlite_research_holds_and_releases(tmp_path):
    q = engine(tmp_path)
    first = q.reserve_for_trader(intent("a", 1), T)
    assert first.lots == D(".02")
    assert first.total_risk_usd == D("2.14")
    q.paper_transition("a", "paper-fill-a", "PAPER_FILL")
    assert q.health(T)["pending_or_unreconciled_reservations"] == 1

    now = T + timedelta(seconds=2)
    q.publish_account(account(2, now))
    q.publish_symbol(symbol(now))
    second = q.reserve_for_trader(intent("b", 2), now)
    assert second.lots == 0  # minimum all-in $1.07 > remaining $0.86

    q.paper_transition("a", "paper-settle-a", "PAPER_SETTLE")
    assert q.health(now)["pending_or_unreconciled_reservations"] == 0
    later = now + timedelta(seconds=1)
    q.publish_account(account(3, later))
    q.publish_symbol(symbol(later))
    assert q.reserve_for_trader(intent("c", 3), later).lots == D(".02")
    assert all("BROKER" not in item["event"] for item in q.ledger())


def test_paper_transitions_idempotent_and_conflicts_rejected(tmp_path):
    q = engine(tmp_path)
    q.reserve_for_trader(intent("a", 1), T)
    q.paper_transition("a", "fill", "PAPER_FILL")
    q.paper_transition("a", "fill", "PAPER_FILL")
    with pytest.raises(QDLEError, match="reassigned"):
        q.paper_transition("a", "fill", "PAPER_SETTLE")
    q.paper_transition("a", "settle", "PAPER_SETTLE")
    q.paper_transition("a", "settle", "PAPER_SETTLE")
    with pytest.raises(QDLEError):
        q.paper_transition("a", "different-settle", "PAPER_SETTLE")


def test_missing_geometry_gets_durable_non_quote_assessment(tmp_path):
    q = engine(tmp_path)
    received = q.paper_unassessable("geom", "INVALID_ORIGINAL_GEOMETRY", T)
    assert received.lots == 0
    assert received.state == "RESEARCH_UNASSESSABLE_NOT_QUOTED"
    assert q.paper_unassessable("geom", "INVALID_ORIGINAL_GEOMETRY", T) == received
    with pytest.raises(QDLEError, match="identity reused"):
        q.paper_unassessable("geom", "NO_ATLAS_M5_ENTRY", T)


def test_paper_db_can_never_arm_live_send(tmp_path):
    q = engine(tmp_path)
    q.reserve_for_trader(intent("a", 1), T)
    with pytest.raises(QDLEError, match="forbidden"):
        q.arm_for_live_send(
            request_id="a", provider_symbol="EURUSD", side="BUY",
            lots=D(".02"), executable_entry=D("1.1"),
            stop_price=D("1.09"), now=T,
        )
    with pytest.raises(QDLEError, match="cannot be opened in LIVE"):
        QDLE(tmp_path / "research.sqlite", SyntheticBroker())
    with pytest.raises(QDLEError, match="PAPER needs"):
        QDLE(tmp_path / "bad.sqlite", SyntheticBroker(), research_paper_mode=True)


def test_research_no_fill_releases_without_broker_rejection(tmp_path):
    q = engine(tmp_path)
    q.reserve_for_trader(intent("a", 1), T)
    q.paper_transition("a", "cancel-a", "PAPER_NO_FILL")
    assert q.health(T)["pending_or_unreconciled_reservations"] == 0
    with pytest.raises(QDLEError):
        q.paper_transition("a", "late-fill", "PAPER_FILL")
    assert any(x["event"] == "RESEARCH_PAPER_NO_FILL" for x in q.ledger())
