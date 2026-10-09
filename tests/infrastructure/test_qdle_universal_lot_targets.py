"""Universal QDLE lot targets: synthetic economics, no order_send or broker certification.

A requested 5/10/20/100-lot quantity is an *upper bound*. Trader stop geometry,
USD stop valuation, all-in fees, four economic motor caps, MT5 margin/lot grid,
and the shared sovereign risk ledger always retain final authority.
"""
import tempfile
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D
from pathlib import Path

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import TraderOpportunityEnvelope
from qore.infrastructure.qdle_cibo_bridge import CiboFourEngineLimits, reserve_cibo_entry
from qore.infrastructure.qdle_local_api import _intent
from qore.infrastructure.qore_dynamic_lot_engine import (
    BrokerValuation, QDLE, QDLEAccount, QDLEError, QDLESymbol,
)

T = datetime(2026, 10, 8, 12, tzinfo=timezone.utc)


class SyntheticNativeValuation:
    """Test-only quote: USD stop/lot = abs(entry - stop) * 1000; margin = $50/lot."""

    def __init__(self):
        self.order_checks = []

    def value(self, spec, intent, now):
        return BrokerValuation(
            abs(intent.entry_price - intent.stop_price) * D("1000"),
            D("50"), now, "SYNTHETIC_NATIVE_QUOTE",
        )

    def check_volume(self, spec, intent, lots):
        self.order_checks.append((intent.request_id, lots))


def opportunity(request_id, *, stop="9.99", trader=TraderLineage.R38_EURUSD):
    return TraderOpportunityEnvelope(
        trader_id=trader, signal_fingerprint=request_id,
        qore_symbol="EURUSD", provider_symbol="EURUSD", side="long",
        entry_type="MARKET", intended_entry=D("10"), stop_loss=D(stop),
        take_profit=D("11"), stop_loss_per_volume=D("10"),
        margin_per_volume=D("50"), volume_step=D("0.01"),
        minimum_volume=D("0.01"), maximum_volume=D("100"),
    )


def limits(*, target=None, requested="50000", sizing="50000", compound="50000",
           portfolio="50000", leverage="100", margin="50000", seq=1):
    return CiboFourEngineLimits(
        requested_stop_loss_budget_usd=D(requested),
        sizing_approved_stop_loss_usd=D(sizing),
        compound_approved_stop_loss_usd=D(compound),
        portfolio_approved_funds_usd=D(portfolio),
        adaptive_leverage_max_broker_lots=D(leverage),
        adaptive_leverage_margin_budget_usd=D(margin),
        slippage_buffer_usd_per_lot=D("0"),
        funded_source_lane="SOVEREIGN_BANK", account_sequence=seq,
        requested_target_lots=None if target is None else D(target),
    )


def snapshot(seq=1, risk="5000", source="5000", time=T):
    return QDLEAccount(
        "broker-account-test", "FundedNext", "USD", seq, time,
        D("100000"), D("100000"), D("100000"), D(risk),
        D(source), D("0"), D("100000"),
    )


class UniversalLotTargetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.broker = SyntheticNativeValuation()
        self.engine = QDLE(Path(self.temp.name) / "qdle.sqlite", self.broker)
        self.engine.publish_account(snapshot())
        self.engine.publish_symbol(QDLESymbol(
            broker_symbol="EURUSD", aliases=("EURUSD",),
            min_lot=D("0.01"), max_lot=D("100"), lot_step=D("0.01"),
            directional_volume_limit=D("0"), tick_size=D("0.00001"),
            tick_value_loss_usd=D("1"), contract_size=D("100000"),
            currency_profit="USD", fee_usd_per_lot=D("2"),
            fee_provenance="SYNTHETIC_ROUND_TRIP_ONLY", as_of=T,
        ))

    def tearDown(self):
        self.temp.cleanup()

    def test_five_ten_twenty_one_hundred_target_lots_are_proposed_and_checked(self):
        for amount in ("5", "10", "20", "100"):
            with self.subTest(target=amount):
                decision = reserve_cibo_entry(
                    self.engine, opportunity("target-" + amount),
                    limits(target=amount), T,
                )
                self.assertEqual(decision.state, "RESERVED_FOR_TRADER")
                self.assertEqual(decision.lots, D(amount))
                self.assertEqual(decision.stop_usd, D(amount) * D("10"))
                self.assertEqual(decision.cost_usd, D(amount) * D("2"))
                self.assertEqual(decision.margin_usd, D(amount) * D("50"))
                self.assertIn("REQUESTED_TARGET_LOTS", decision.binding_limits)
        self.assertEqual(len(self.broker.order_checks), 4)

    def test_without_explicit_target_remains_dynamic_risk_sizing(self):
        decision = reserve_cibo_entry(
            self.engine, opportunity("no-target"),
            limits(requested="120", sizing="120", compound="120"), T,
        )
        self.assertEqual(decision.lots, D("10"))
        self.assertNotIn("REQUESTED_TARGET_LOTS", decision.binding_limits)

    def test_trader_stop_distance_changes_lots_even_for_same_target(self):
        tight = reserve_cibo_entry(
            self.engine, opportunity("tight", stop="9.99"),
            limits(target="100", requested="200", sizing="200", compound="200"), T,
        )
        wide = reserve_cibo_entry(
            self.engine, opportunity("wide", stop="9.90"),
            limits(target="100", requested="200", sizing="200", compound="200"), T,
        )
        self.assertEqual(tight.lots, D("16.66"))
        self.assertEqual(wide.lots, D("1.96"))
        self.assertLessEqual(tight.total_risk_usd, D("200"))
        self.assertLessEqual(wide.total_risk_usd, D("200"))

    def test_sizing_compound_leverage_portfolio_each_reduces_requested_target(self):
        scenarios = [
            ("sizing", dict(sizing="180"), "15", "SIZING"),
            ("compound", dict(compound="96"), "8", "CIBO_COMPOUND"),
            ("leverage", dict(leverage="7.5"), "7.5", "ADAPTIVE_LEVERAGE_MAX"),
            ("margin", dict(margin="125"), "2.5", "ADAPTIVE_LEVERAGE_MARGIN"),
            ("portfolio", dict(portfolio="60"), "5", "SOVEREIGN_BANK"),
        ]
        for name, overrides, expected, binding in scenarios:
            with self.subTest(name=name):
                decision = reserve_cibo_entry(
                    self.engine, opportunity("motor-" + name),
                    limits(target="20", **overrides), T,
                )
                self.assertEqual(decision.lots, D(expected))
                self.assertIn(binding, decision.binding_limits)

    def test_two_traders_share_account_risk_reservations_atomically(self):
        self.engine.publish_account(snapshot(2, risk="300", source="300",
                                             time=T + timedelta(seconds=1)))
        trader1 = reserve_cibo_entry(
            self.engine, opportunity("trader-a", trader=TraderLineage.R38_EURUSD),
            limits(target="20", seq=2), T + timedelta(seconds=1),
        )
        trader2 = reserve_cibo_entry(
            self.engine, opportunity("trader-b", trader=TraderLineage("R99_EURUSD")),
            limits(target="20", seq=2), T + timedelta(seconds=1),
        )
        self.assertEqual(trader1.lots, D("20"))
        self.assertEqual(trader2.lots, D("5"))
        self.assertEqual(trader1.total_risk_usd + trader2.total_risk_usd, D("300"))
        blocked = reserve_cibo_entry(
            self.engine, opportunity("trader-c", trader=TraderLineage("R100_EURUSD")),
            limits(target="20", seq=2), T + timedelta(seconds=1),
        )
        self.assertEqual((blocked.state, blocked.lots), ("UNFUNDABLE", D("0")))

    def test_eurusd_ten_pips_60_usd_nav_includes_seven_each_way(self):
        # Synthetic EURUSD 10 pips = $100 loss/lot; $7 opening + $7 closing
        # = $14/lot all-in. Thus 0.03 lots risks $3.42 (> $3 allowed).
        # Exact broker grid floors to 0.02 lots ($2 SL + $0.28 fee).
        at = T + timedelta(seconds=1)
        self.engine.publish_account(QDLEAccount(
            "broker-account-test", "FundedNext", "USD", 2, at,
            D("2000"), D("2000"), D("1900"), D("3"),
            D("3"), D("0"), D("60"),
        ))
        self.engine.publish_symbol(QDLESymbol(
            broker_symbol="EURUSD", aliases=("EURUSD",),
            min_lot=D(".01"), max_lot=D("100"), lot_step=D(".01"),
            directional_volume_limit=D("0"), tick_size=D(".00001"),
            tick_value_loss_usd=D("1"), contract_size=D("100000"),
            currency_profit="USD", fee_usd_per_lot=D("14"),
            fee_provenance="TEST_ONLY_SEVEN_OPEN_AND_SEVEN_CLOSE", as_of=at,
        ))
        # SyntheticNativeValuation: 0.10 price gap * $1000/price= $100/lot.
        result = reserve_cibo_entry(
            self.engine, opportunity("fee14", stop="9.90"),
            limits(seq=2, target="100"), at,
        )
        self.assertEqual(result.lots, D("0.02"))
        self.assertEqual(result.stop_usd, D("2.00"))
        self.assertEqual(result.cost_usd, D("0.28"))
        self.assertEqual(result.total_risk_usd, D("2.28"))
        self.assertLessEqual(result.total_risk_usd, D("3.00"))

    def test_hundred_lot_demand_never_overrides_dynamic_five_percent_nav(self):
        # Broker equity $2000 is only a margin constraint. The risk base is
        # QORE's genuine $60 NAV, giving a $3 all-in per-entry ceiling.
        first_time = T + timedelta(seconds=1)
        self.engine.publish_account(QDLEAccount(
            "broker-account-test", "FundedNext", "USD", 2, first_time,
            D("2000"), D("2000"), D("1900"), D("3"),
            D("3"), D("0"), D("60"),
        ))
        small = reserve_cibo_entry(
            self.engine, opportunity("nav60"),
            limits(target="100", seq=2), first_time,
        )
        self.assertEqual(small.lots, D("0.25"))
        self.assertEqual(small.total_risk_usd, D("3.00"))
        self.engine.confirm_rejection("nav60", "SYNTHETIC_BROKER_NO_FILL")

        # No fixed $3 ceiling: with fresh, independently provided NAV $120,
        # the same stop, fees and 100-lot request can fund up to $6.
        next_time = T + timedelta(seconds=2)
        self.engine.publish_account(QDLEAccount(
            "broker-account-test", "FundedNext", "USD", 3, next_time,
            D("2000"), D("2000"), D("1900"), D("6"),
            D("6"), D("0"), D("120"),
        ))
        doubled = reserve_cibo_entry(
            self.engine, opportunity("nav120"),
            limits(target="100", seq=3), next_time,
        )
        self.assertEqual(doubled.lots, D("0.50"))
        self.assertEqual(doubled.total_risk_usd, D("6.00"))

    def test_broker_grid_and_target_smaller_than_minimum_fail_closed(self):
        unrepresentable = reserve_cibo_entry(
            self.engine, opportunity("sub-minimum"),
            limits(target="0.005"), T,
        )
        self.assertEqual((unrepresentable.state, unrepresentable.lots),
                         ("UNFUNDABLE", D("0")))
        rounded = reserve_cibo_entry(
            self.engine, opportunity("rounded"), limits(target="10.009"), T,
        )
        self.assertEqual(rounded.lots, D("10.00"))

    def test_invalid_target_volume_fails_closed(self):
        for bad in ("0", "-1", "NaN", "Infinity"):
            with self.subTest(bad=bad), self.assertRaises(QDLEError):
                reserve_cibo_entry(
                    self.engine, opportunity("bad-" + bad), limits(target=bad), T,
                )

    def test_optional_target_is_authenticated_intent_payload_and_immutable(self):
        payload = dict(
            request_id="signed-target", trader_id="R38_EURUSD", symbol="EURUSD",
            side="BUY", entry_price="10", stop_price="9.99",
            requested_risk_usd="2000", sizing_cap_usd="2000",
            cibo_compound_cap_usd="2000", portfolio_cap_usd="2000",
            leverage_cap_lots="100", margin_cap_usd="50000",
            source_lane="SOVEREIGN_BANK", slippage_usd_per_lot="0",
            expected_account_sequence=1, requested_target_lots="20",
        )
        parsed = _intent(payload)
        self.assertEqual(parsed.requested_target_lots, D("20"))
        secured = QDLE(
            Path(self.temp.name) / "secured.sqlite", SyntheticNativeValuation(),
            enforce_finance_approval=True, strict_four_motor_evidence=False,
            strict_live_fee_evidence=False, strict_provider_floor=False,
        )
        secured.publish_account(snapshot())
        secured.publish_symbol(QDLESymbol(
            broker_symbol="EURUSD", aliases=("EURUSD",),
            min_lot=D("0.01"), max_lot=D("100"), lot_step=D("0.01"),
            directional_volume_limit=D("0"), tick_size=D("0.00001"),
            tick_value_loss_usd=D("1"), contract_size=D("100000"),
            currency_profit="USD", fee_usd_per_lot=D("2"),
            fee_provenance="SYNTHETIC_TEST_ONLY", as_of=T,
        ))
        secured.publish_finance_approval(parsed, approved_at=T)
        with self.assertRaises(QDLEError):
            secured.reserve_for_trader(replace(parsed, requested_target_lots=D("100")), now=T)
        good = secured.reserve_for_trader(parsed, now=T)
        self.assertEqual(good.lots, D("20"))
        self.assertIn("REQUESTED_TARGET_LOTS", good.binding_limits)
        # The persisted approval must reconstruct the optional Decimal target
        # during one-shot pre-send validation, without placing any broker order.
        secured.arm_for_live_send(
            request_id="signed-target", provider_symbol="EURUSD",
            side="BUY", lots=D("20"), executable_entry=D("10"),
            stop_price=D("9.99"), now=T,
        )
        with self.assertRaises(QDLEError):
            secured.arm_for_live_send(
                request_id="signed-target", provider_symbol="EURUSD",
                side="BUY", lots=D("20"), executable_entry=D("10"),
                stop_price=D("9.99"), now=T,
            )


if __name__ == "__main__":
    unittest.main()
