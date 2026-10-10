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
from qore.infrastructure.cibo_four_motor_policy import FourMotorObservation, FourMotorPolicyError, ReconciledQoreCashflow
from qore.infrastructure.qdle_cibo_authority import (
    CiboEconomicInstruction, build_cibo_directed_qdle_intent, audit_cibo_qdle_lotage,
)
from qore.infrastructure.qore_dynamic_lot_engine import (
    BrokerValuation, QDLE, QDLEAccount, QDLESymbol, QDLEResult,
)

T = datetime(2026, 10, 8, 12, tzinfo=UTC)
HASH = "sha256:" + "a" * 64


class Broker:
    def value(self, instrument, intent, now):
        return BrokerValuation(D("100"), D("1000"), now, "SYNTHETIC_ONLY")
    def check_volume(self, instrument, intent, lots):
        pass



class StopBroker(Broker):
    def __init__(self, stop_usd_per_lot, margin="1000"):
        self.stop_usd_per_lot = D(stop_usd_per_lot)
        self.margin_per_lot = D(margin)

    def value(self, instrument, intent, now):
        return BrokerValuation(self.stop_usd_per_lot, self.margin_per_lot, now,
                               "TEST_DETERMINISTIC_USD_STOP_AND_MARGIN")


def run_cibo_physical_quote(
    *, nav, stop_pips, risk=None, fee="14", broker_free_margin="1900",
    allocation=None, min_lot=".01", step=".01", symbol="EURUSD",
):
    """Test-only physical QDLE, with reconciled profits never floating."""
    nav, stop_pips = D(nav), D(stop_pips)
    budget = risk if risk is not None else nav * D(".05")
    source = D(allocation) if allocation is not None else nav
    original = observation(source=str(source))
    flows = (ReconciledQoreCashflow(
        "settlement-for-"+str(nav), T, nav - D("60"), HASH, True,
    ),) if nav != D("60") else ()
    stop_per_lot = stop_pips * D("10")
    obs = replace(original, initial_qore_nav_usd=D("60"),
                  reconciled_cashflows=flows,
                  stop_loss_usd_per_lot=stop_per_lot,
                  roundtrip_fees_usd_per_lot=D(fee),
                  symbol=symbol)
    entry_price = D("2100") if symbol == "XAUUSD" else D("1.1000")
    stop_price = entry_price - stop_pips * (
        D(".1") if symbol == "XAUUSD" else D(".0001")
    )
    cibo = replace(directive(obs, budget=str(budget), allocation=str(source)),
                   symbol=symbol, entry_price=entry_price, stop_price=stop_price)
    motor_votes = votes(obs)
    intent = build_cibo_directed_qdle_intent(
        cibo=cibo, observation=obs, votes=motor_votes)
    with tempfile.TemporaryDirectory() as tmp:
        qdle = QDLE(Path(tmp)/"cibo-test.sqlite", StopBroker(stop_per_lot))
        qdle.publish_account(QDLEAccount(
            "acct", "FundedNext", "USD", 1, T,
            D("2000"), D("2000"), D(broker_free_margin),
            nav, D("0"), source, nav,
        ))
        qdle.publish_symbol(QDLESymbol(
            symbol, (symbol,), D(min_lot), D("40"), D(step), D("0"),
            D(".00001"), D("1"), D("100000"), "USD",
            D(fee), "SYNTHETIC_FEE_SCHEDULE_NOT_FUNDedNEXT", T,
        ))
        result = qdle.reserve_for_trader(intent, T)
        receipt = audit_cibo_qdle_lotage(
            cibo=cibo, observation=obs, votes=motor_votes,
            result=result, broker_min_lot=D(min_lot),
            broker_lot_step=D(step),
        )
    return result, receipt, obs, cibo, motor_votes


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


    def test_qdle_dynamic_5pct_replayed_from_realized_qore_cashflows(self):
        """20 pip EURUSD; never round the 5pct result up to exceed loss budget."""
        for nav, expected in [
            ("60", ".01"), ("100", ".02"), ("150", ".03"),
            ("200", ".04"), ("300", ".07"), ("500", ".11"),
            ("1000", ".23"),
        ]:
            with self.subTest(nav=nav):
                actual, receipt, observation_at_entry, _, _ = run_cibo_physical_quote(
                    nav=nav, stop_pips="20",
                )
                self.assertEqual(actual.lots, D(expected))
                self.assertEqual(receipt.qore_nav_usd, D(nav))
                self.assertEqual(receipt.sovereign_5pct_ceiling_usd, D(nav)*D(".05"))
                self.assertLessEqual(receipt.all_in_risk_usd, D(nav)*D(".05"))
                self.assertEqual(receipt.all_in_risk_usd, D(expected)*D("214"))
                self.assertFalse(receipt.real_mt5_fill_proven)

    def test_bank_medium_attack_examples_are_cibo_stop_not_qdle_strategy(self):
        for nav, stop, lots, all_in in [
            ("60", "10", ".02", "2.28"),
            ("60", "18", ".01", "1.94"),
            ("60", "25", ".01", "2.64"),
            ("150", "10", ".06", "6.84"),
            ("150", "18", ".03", "5.82"),
            ("150", "25", ".02", "5.28"),
        ]:
            with self.subTest(nav=nav, trader_setup_stop_pips=stop):
                result, receipt, _, cibo, _ = run_cibo_physical_quote(
                    nav=nav, stop_pips=stop,
                )
                self.assertEqual(result.lots, D(lots))
                self.assertEqual(receipt.all_in_risk_usd, D(all_in))
                self.assertEqual(receipt.stop_price, cibo.stop_price)
                self.assertEqual(receipt.total_roundtrip_cost_usd, result.lots*D("14"))
                self.assertEqual(receipt.decision_state, "RESERVED_FOR_TRADER")

    def test_qdle_does_not_force_minimum_when_fees_or_margin_unfundable(self):
        cases = [
            dict(nav="60", stop_pips="40", fee="14"),
            dict(nav="60", stop_pips="10", fee="14",
                 broker_free_margin="5"),
            dict(nav="60", stop_pips="10", fee="14", allocation="0"),
        ]
        for params in cases:
            with self.subTest(params=params):
                result, receipt, *_ = run_cibo_physical_quote(**params)
                self.assertEqual(result.lots, D("0"))
                self.assertEqual(receipt.decision_state, "UNFUNDABLE")
                self.assertIn("NO_FINANCEABLE_BROKER_LOT", receipt.reason_codes)
                self.assertEqual(receipt.all_in_risk_usd, D("0"))

    def test_cibo_smaller_risk_preserved_even_when_5pct_headroom_exists(self):
        result, receipt, *_ = run_cibo_physical_quote(
            nav="150", stop_pips="10", risk="2", allocation="40",
        )
        self.assertEqual(receipt.cibo_risk_budget_usd, D("2"))
        self.assertEqual(receipt.cibo_allocated_funds_usd, D("40"))
        self.assertEqual(result.lots, D(".01"))
        self.assertEqual(receipt.all_in_risk_usd, D("1.14"))

    def test_symbol_specific_fee_not_universal_forex_14(self):
        result, receipt, *_ = run_cibo_physical_quote(
            nav="60", stop_pips="10", fee="30", symbol="XAUUSD",
        )
        self.assertEqual(result.lots, D(".02"))
        self.assertEqual(receipt.total_roundtrip_cost_usd, D(".60"))
        self.assertEqual(receipt.all_in_risk_usd, D("2.60"))

    def test_high_precision_stop_plus_roundtrip_fee_does_not_false_reject(self):
        """QDLE prec=100 USDJPY-like risk must survive default Decimal 28 audit."""
        result, receipt, _, _, _ = run_cibo_physical_quote(
            nav="60", stop_pips="8.536303839023913079784226386",
            fee="14", symbol="EURUSD",
        )
        self.assertEqual(result.lots, D("0.03"))
        self.assertEqual(receipt.decision_state, "RESERVED_FOR_TRADER")
        self.assertEqual(receipt.all_in_risk_usd, result.total_risk_usd)
        self.assertLessEqual(receipt.all_in_risk_usd, D("3"))

    def test_audit_detects_corrupted_fee_risk_and_grid(self):
        result, _, obs, cibo, evotes = run_cibo_physical_quote(
            nav="60", stop_pips="10",
        )
        bad = [
            replace(result, total_risk_usd=D("0")),
            replace(result, lots=D("0.015")),
            replace(result, account_sequence=999),
            replace(result, total_risk_usd=D("4")),
        ]
        for forged in bad:
            with self.subTest(forged=forged):
                with self.assertRaises(FourMotorPolicyError):
                    audit_cibo_qdle_lotage(
                        cibo=cibo, observation=obs, votes=evotes,
                        result=forged, broker_min_lot=D(".01"),
                        broker_lot_step=D(".01"),
                    )

    def test_audit_and_directive_are_not_mt5_orders(self):
        _, receipt, *_ = run_cibo_physical_quote(nav="60", stop_pips="10")
        self.assertFalse(receipt.real_mt5_fill_proven)
        self.assertEqual(receipt.reason_codes[0], "RESERVED_NOT_EXECUTED")
        self.assertEqual(receipt.broker_margin_usd, D("20"))
        self.assertEqual(receipt.stop_loss_usd, D("2"))
        self.assertEqual(receipt.total_roundtrip_cost_usd, D(".28"))


if __name__ == "__main__":
    unittest.main()
