"""CIBO decides WHAT and how much; QDLE computes HOW MANY broker lots."""
from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal as D
from pathlib import Path

from qore.infrastructure.cibo_account_sizing_authority import propose_p0_sizing_vote
from qore.infrastructure.cibo_compound_capital import propose_p0_compound_vote
from qore.infrastructure.cibo_marginal_leverage_utility import propose_p0_adaptive_leverage_vote
from qore.infrastructure.cibo_core_compound_portfolio import propose_p0_portfolio_vote
from qore.infrastructure.cibo_four_motor_policy import FourMotorObservation, FourMotorPolicyError
from qore.infrastructure.qdle_cibo_authority import (
    CiboEconomicInstruction, build_cibo_directed_qdle_intent,
)
from qore.infrastructure.qore_dynamic_lot_engine import (
    BrokerValuation, QDLE, QDLEAccount, QDLESymbol,
)

T = datetime(2026, 10, 8, 12, tzinfo=UTC)
HASH = "sha256:" + "a" * 64


class Broker:
    def value(self, instrument, intent, now):
        return BrokerValuation(D("100"), D("1000"), now, "SYNTHETIC_ONLY")
    def check_volume(self, instrument, intent, lots):
        pass


def observation(*, nav="60", lane="PORTFOLIO_CUSHION", source="50",
                signal="attack-eurusd-1"):
    return FourMotorObservation(
        request_id=signal, trader_id="ATTACK", symbol="EURUSD", side="BUY",
        source_lane=lane, observed_at=T, account_sequence=1,
        broker_evidence_sha256=HASH, initial_qore_nav_usd=D(nav),
        reconciled_cashflows=(), protected_capital_usd=D("0"),
        floating_loss_reserve_usd=D("0"), risk_reservations_usd=D("0"),
        bank_unreserved_usd=D(source) if lane == "SOVEREIGN_BANK" else D("0"),
        cushion_unreserved_usd=D(source) if lane == "PORTFOLIO_CUSHION" else D("0"),
        total_open_stop_risk_usd=D("0"), correlated_open_stop_risk_usd=D("0"),
        trader_open_stop_risk_usd=D("0"), broker_free_margin_usd=D("1900"),
        broker_margin_reservations_usd=D("0"), stop_loss_usd_per_lot=D("100"),
        roundtrip_fees_usd_per_lot=D("14"), execution_buffer_usd_per_lot=D("0"),
        stress_extra_loss_usd_per_lot=D("0"), broker_margin_usd_per_lot=D("1000"),
        symbol_max_lots=D("40"), provider_direction_max_lots=D("40"),
        open_and_reserved_direction_lots=D("0"), broker_quote_at=T,
        broker_fees_complete=True, broker_profit_valuation_complete=True,
        broker_margin_valuation_complete=True,
    )


def votes(o):
    return (propose_p0_sizing_vote(o), propose_p0_compound_vote(o),
            propose_p0_adaptive_leverage_vote(o), propose_p0_portfolio_vote(o))


def directive(o, *, budget="3", allocation="50", maximum="100"):
    return CiboEconomicInstruction(
        signal_id=o.request_id, trader_id=o.trader_id, symbol=o.symbol,
        side=o.side, entry_price=D("1.1000"), stop_price=D("1.0990"),
        source_lane=o.source_lane, allocated_source_funds_usd=D(allocation),
        authorized_all_in_risk_usd=D(budget),
        maximum_requested_lots=D(maximum) if maximum is not None else None,
        account_sequence=o.account_sequence, issued_at=T, evidence_sha256=HASH,
    )


class TestCiboQdleAuthority(unittest.TestCase):
    def test_allocation_fifty_is_not_fifty_risk(self):
        obs = observation()
        actual = build_cibo_directed_qdle_intent(
            cibo=directive(obs), observation=obs, votes=votes(obs),
        )
        self.assertEqual(actual.source_lane, "PORTFOLIO_CUSHION")
        self.assertEqual(actual.requested_risk_usd, D("3"))
        self.assertLessEqual(actual.portfolio_cap_usd, D("50"))
        self.assertEqual(actual.requested_target_lots, D("100"))

    def test_cibo_smaller_budget_always_shrinks_qdle_risk(self):
        obs = observation()
        intent = build_cibo_directed_qdle_intent(
            cibo=directive(obs, budget="1", allocation="50"),
            observation=obs, votes=votes(obs),
        )
        self.assertEqual(intent.requested_risk_usd, D("1"))

    def test_qdle_fund_real_stop_and_roundtrip_from_cibo(self):
        obs = observation()
        intent = build_cibo_directed_qdle_intent(
            cibo=directive(obs), observation=obs, votes=votes(obs),
        )
        with tempfile.TemporaryDirectory() as work:
            q = QDLE(Path(work) / "qdle.sqlite", Broker(),
                     strict_four_motor_evidence=False, strict_provider_floor=False)
            q.publish_account(QDLEAccount(
                "123", "FundedNext", "USD", 1, T,
                D("2000"), D("2000"), D("1900"),
                D("3"), D("0"), D("50"), D("60"),
            ))
            q.publish_symbol(QDLESymbol(
                "EURUSD", ("EURUSD",), D(".01"), D("40"), D(".01"), D("0"),
                D(".00001"), D("1"), D("100000"), "USD",
                D("14"), "SYNTHETIC_OPEN_7_CLOSE_7", T,
            ))
            result = q.reserve_for_trader(intent, T)
        self.assertEqual(result.lots, D("0.02"))
        self.assertEqual(result.stop_usd, D("2.00"))
        self.assertEqual(result.total_risk_usd, D("2.28"))
        self.assertLessEqual(result.total_risk_usd, D("3"))

    def test_cibo_cannot_forge_50_dollar_risk_on_60_nav(self):
        obs = observation()
        with self.assertRaisesRegex(FourMotorPolicyError, "5pct"):
            build_cibo_directed_qdle_intent(
                cibo=directive(obs, budget="50"), observation=obs, votes=votes(obs),
            )

    def test_wrong_lane_or_signal_cannot_be_auto_substituted(self):
        obs = observation()
        cibo = directive(obs)
        for mismatch in (replace(cibo, source_lane="SOVEREIGN_BANK"),
                         replace(cibo, signal_id="other-signal"),
                         replace(cibo, trader_id="MEDIUM"),
                         replace(cibo, account_sequence=2)):
            with self.subTest(mismatch=mismatch):
                with self.assertRaisesRegex(FourMotorPolicyError, "mismatch"):
                    build_cibo_directed_qdle_intent(
                        cibo=mismatch, observation=obs, votes=votes(obs),
                    )

    def test_unbacked_attack_allocation_is_rejected(self):
        obs = observation(source="0")
        with self.assertRaisesRegex(FourMotorPolicyError, "unbacked"):
            build_cibo_directed_qdle_intent(
                cibo=directive(obs), observation=obs, votes=votes(obs),
            )

    def test_missing_explicit_directive_does_not_fall_back_to_sizing(self):
        obs = observation()
        with self.assertRaisesRegex(FourMotorPolicyError, "instruction required"):
            build_cibo_directed_qdle_intent(cibo=None, observation=obs, votes=votes(obs))

    def test_tampered_epoch_fails_closed(self):
        obs = observation()
        cibo = directive(obs)
        from datetime import timedelta
        with self.assertRaisesRegex(FourMotorPolicyError, "share economic epoch"):
            build_cibo_directed_qdle_intent(
                cibo=replace(cibo, issued_at=T + timedelta(seconds=1)),
                observation=obs, votes=votes(obs),
            )

    def test_zero_budget_never_becomes_forced_min_lot(self):
        obs = observation()
        intent = build_cibo_directed_qdle_intent(
            cibo=directive(obs, budget="0"), observation=obs, votes=votes(obs),
        )
        self.assertEqual(intent.requested_risk_usd, D("0"))


if __name__ == "__main__":
    unittest.main()
