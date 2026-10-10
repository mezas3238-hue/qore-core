"""Architect 2 P0 SHADOW tests: six-symbol-independent synthetic economics."""
from __future__ import annotations

import hashlib
import hmac
import json
import tempfile
import unittest
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.cibo_account_sizing_authority import propose_p0_sizing_vote
from qore.infrastructure.cibo_compound_capital import propose_p0_compound_vote
from qore.infrastructure.cibo_core_compound_portfolio import propose_p0_portfolio_vote
from qore.infrastructure.cibo_four_motor_policy import (
    FourMotorObservation,
    FourMotorPolicyError,
    ReconciledQoreCashflow,
    sign_producer_receipt,
)
from qore.infrastructure.cibo_four_motor_qdle_proposal import build_four_motor_qdle_intent
from qore.infrastructure.cibo_marginal_leverage_utility import propose_p0_adaptive_leverage_vote
from qore.infrastructure.qore_dynamic_lot_engine import (
    QDLE,
    BrokerValuation,
    QDLEAccount,
    QDLEError,
    QDLESymbol,
)

T = datetime(2026, 10, 8, 12, tzinfo=UTC)
H = "sha256:" + "a"*64
KEYS = {n: (n + "-test-only-key-").encode().ljust(64, b"X") for n in (
    "SIZING", "CIBO_COMPOUND", "ADAPTIVE_LEVERAGE", "PORTFOLIO_COMPOUND",
)}


def cash(n, amount, offset=-1):
    return ReconciledQoreCashflow(str(n), T + timedelta(seconds=offset), Decimal(amount), H, True)


def observation(**kwargs):
    options = dict(
        request_id="sig1", trader_id="r38", symbol="EURUSD", side="BUY",
        source_lane="SOVEREIGN_BANK", observed_at=T, account_sequence=7,
        broker_evidence_sha256=H, initial_qore_nav_usd=Decimal("60"),
        reconciled_cashflows=(), protected_capital_usd=Decimal("0"),
        floating_loss_reserve_usd=Decimal("0"), risk_reservations_usd=Decimal("0"),
        bank_unreserved_usd=Decimal("60"), cushion_unreserved_usd=Decimal("0"),
        total_open_stop_risk_usd=Decimal("0"), correlated_open_stop_risk_usd=Decimal("0"),
        trader_open_stop_risk_usd=Decimal("0"), broker_free_margin_usd=Decimal("1900"),
        broker_margin_reservations_usd=Decimal("0"), stop_loss_usd_per_lot=Decimal("100"),
        roundtrip_fees_usd_per_lot=Decimal("14"), execution_buffer_usd_per_lot=Decimal("2"),
        stress_extra_loss_usd_per_lot=Decimal("0"), broker_margin_usd_per_lot=Decimal("1000"),
        symbol_max_lots=Decimal("40"), provider_direction_max_lots=Decimal("40"),
        open_and_reserved_direction_lots=Decimal("0"),
        broker_quote_at=T,
        broker_fees_complete=True,
        broker_profit_valuation_complete=True,
        broker_margin_valuation_complete=True,
    )
    options.update(kwargs)
    return FourMotorObservation(**options)


def votes(o):
    return (propose_p0_sizing_vote(o), propose_p0_compound_vote(o),
            propose_p0_adaptive_leverage_vote(o), propose_p0_portfolio_vote(o))


class FakeBroker:
    def value(self, spec, intent, now):
        return BrokerValuation(Decimal("100"), Decimal("1000"), now, "SYNTHETIC_ONLY")
    def check_volume(self, spec, intent, lots):
        pass


class FourMotorEconomicTest(unittest.TestCase):
    def test_qore_nav_dynamic_60_100_40_buy_sell(self):
        for nav, risk in ((60, 3), (100, 5), (40, 2)):
            for side in ("BUY", "SELL"):
                o = observation(side=side, reconciled_cashflows=()
                                if nav == 60 else (cash(nav, nav-60),))
                self.assertEqual(o.base_entry_budget_usd, Decimal(risk))
                self.assertEqual(Decimal(votes(o)[0].limits["approved_risk_usd"]), Decimal(risk))
                self.assertEqual(Decimal(votes(o)[1].limits["approved_risk_usd"]), Decimal(risk))

    def test_four_distinct_units_and_constraints(self):
        o = observation()
        sizing, compound, leverage, portfolio = votes(o)
        self.assertEqual(sizing.limits["approved_risk_usd"], "3.00")
        self.assertEqual(Decimal(leverage.limits["approved_margin_usd"]), Decimal("1520"))
        self.assertEqual(Decimal(leverage.limits["approved_max_lots"]), Decimal("1.52"))
        self.assertEqual(Decimal(portfolio.limits["approved_source_funds_usd"]), Decimal("4.5"))
        self.assertNotIn("approved_risk_usd", leverage.limits)

    def test_stress_protected_bank_and_margin_reservations(self):
        o = observation(stress_extra_loss_usd_per_lot=Decimal("109"),
                        protected_capital_usd=Decimal("58"), floating_loss_reserve_usd=Decimal("1"),
                        broker_margin_reservations_usd=Decimal("1800"),
                        total_open_stop_risk_usd=Decimal("3"),
                        correlated_open_stop_risk_usd=Decimal("3"),
                        trader_open_stop_risk_usd=Decimal("2"))
        s, c, leverage_vote, p = votes(o)
        self.assertEqual(Decimal(s.limits["approved_risk_usd"]), Decimal("3") * Decimal("116") / Decimal("225"))
        self.assertEqual(Decimal(c.limits["approved_risk_usd"]), Decimal("1"))
        self.assertEqual(Decimal(leverage_vote.limits["approved_max_lots"]), Decimal(".08"))
        self.assertEqual(Decimal(p.limits["approved_source_funds_usd"]), Decimal("1"))

    def test_reconciled_loss_streak_and_no_floating_wins(self):
        o = observation(reconciled_cashflows=(cash(1, "-8", -4),
                        cash(2, "-2", -3), cash(3, "-10", -2)))
        self.assertEqual(o.qore_nav_usd, Decimal("40"))
        # NAV $40 * 5% = $2; no second 0.5x three-loss haircut.
        self.assertEqual(Decimal(votes(o)[1].limits["approved_risk_usd"]), Decimal("2"))
        self.assertEqual(
            observation(floating_loss_reserve_usd=Decimal("59")).qore_nav_usd,
            Decimal("60"),
        )
        with self.assertRaisesRegex(FourMotorPolicyError, "future"):
            observation(reconciled_cashflows=(cash(1, "900", +1),))
        with self.assertRaisesRegex(FourMotorPolicyError, "double-counted"):
            observation(reconciled_cashflows=(cash(1, "1"), cash(1, "1")))
        with self.assertRaisesRegex(FourMotorPolicyError, "reconciled"):
            ReconciledQoreCashflow("wrong", T, Decimal("5"), H, False)

    def test_source_and_concurrent_capacity_are_not_double_spent(self):
        o = observation(risk_reservations_usd=Decimal("4"), total_open_stop_risk_usd=Decimal("6"),
                        correlated_open_stop_risk_usd=Decimal("4"),
                        trader_open_stop_risk_usd=Decimal("4"),
                        provider_direction_max_lots=Decimal("1"),
                        open_and_reserved_direction_lots=Decimal("1"))
        self.assertEqual(Decimal(votes(o)[3].limits["approved_source_funds_usd"]), Decimal("0"))
        self.assertEqual(Decimal(votes(o)[2].limits["approved_max_lots"]), Decimal("0"))
        o2 = observation(source_lane="PORTFOLIO_CUSHION",
                         bank_unreserved_usd=Decimal("200"), cushion_unreserved_usd=Decimal("0"))
        self.assertEqual(Decimal(votes(o2)[3].limits["approved_source_funds_usd"]), Decimal("0"))

    def test_producer_hmac_independence_and_epoch_guards(self):
        o = observation()
        signed = {}
        for p in votes(o):
            r = sign_producer_receipt(p, producer=p.producer, secret=KEYS[p.producer])
            self.assertEqual(r["decision_state"], "SHADOW_ADVISORY_ONLY")
            self.assertTrue(r["rationale"])
            with self.assertRaises(TypeError):
                p.limits["approved_risk_usd" if p.producer in ("SIZING", "CIBO_COMPOUND") else
                         "approved_max_lots" if p.producer == "ADAPTIVE_LEVERAGE" else
                         "approved_source_funds_usd"] = "999"
            body = {k:v for k,v in r.items() if k not in ("hmac_sha256", "source_event_sha256")}
            canonical = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
            self.assertEqual(
                r["source_event_sha256"], "sha256:" + hashlib.sha256(canonical).hexdigest()
            )
            self.assertEqual(
                r["hmac_sha256"],
                hmac.new(KEYS[p.producer], canonical, hashlib.sha256).hexdigest(),
            )
            signed[p.producer] = r
        self.assertEqual(len({r["source_event_sha256"] for r in signed.values()}), 4)
        with self.assertRaisesRegex(FourMotorPolicyError, "cross-producer"):
            sign_producer_receipt(
                votes(o)[0], producer="CIBO_COMPOUND", secret=KEYS["CIBO_COMPOUND"]
            )
        with self.assertRaisesRegex(FourMotorPolicyError, "unavailable"):
            sign_producer_receipt(votes(o)[0], producer="SIZING", secret=b"weak")
        with self.assertRaisesRegex(FourMotorPolicyError, "cross-epoch"):
            build_four_motor_qdle_intent(observation=o,
                votes=(votes(o)[0], *votes(replace(o, account_sequence=8))[1:]),
                entry_price=Decimal("1.1"), stop_price=Decimal("1.09"))

    def test_four_motor_intent_supports_independently_requested_target_lots(self):
        o = observation()
        for target in ("5", "10", "20", "100"):
            with self.subTest(target=target):
                intent = build_four_motor_qdle_intent(
                    observation=o, votes=votes(o),
                    entry_price=Decimal("1.1"), stop_price=Decimal("1.09"),
                    requested_target_lots=Decimal(target),
                )
                self.assertEqual(intent.requested_target_lots, Decimal(target))
                self.assertEqual(intent.requested_risk_usd, Decimal("3"))
                self.assertEqual(intent.sizing_cap_usd, Decimal("3"))
        with self.assertRaisesRegex(FourMotorPolicyError, "positive"):
            build_four_motor_qdle_intent(
                observation=o, votes=votes(o),
                entry_price=Decimal("1.1"), stop_price=Decimal("1.09"),
                requested_target_lots=Decimal("0"),
            )

    def test_qdle_accepts_native_signed_votes_and_keeps_no_send(self):
        o = observation()
        producer_votes = votes(o)
        intent = build_four_motor_qdle_intent(
            observation=o, votes=producer_votes, entry_price=Decimal("1.1"),
            stop_price=Decimal("1.09"))
        self.assertEqual(intent.requested_risk_usd, Decimal("3"))
        signed = {v.producer: sign_producer_receipt(
            v, producer=v.producer, secret=KEYS[v.producer]) for v in producer_votes}
        with tempfile.TemporaryDirectory() as temp:
            q = QDLE(Path(temp)/"broker.sqlite", FakeBroker(),
                     enforce_finance_approval=True, motor_hmac_keys=KEYS,
                     strict_provider_floor=False)
            q.publish_account(QDLEAccount(
                "123", "FundedNext", "USD", 7, T, Decimal("2000"), Decimal("2000"),
                Decimal("1900"), Decimal("60"), Decimal("60"), Decimal("0"), Decimal("60")))
            q.publish_symbol(QDLESymbol(
                "EURUSD", ("EURUSD",), Decimal(".01"), Decimal("40"), Decimal(".01"), Decimal("0"),
                Decimal(".00001"), Decimal("1"), Decimal("100000"), "USD", Decimal("14"),
                "SYNTHETIC_ONLY", T))
            q.publish_finance_approval(intent, T, signed)
            reserved = q.reserve_for_trader(intent, T)
            self.assertEqual(reserved.lots, Decimal(".02"))
            self.assertEqual(reserved.total_risk_usd, Decimal("2.32"))
            self.assertLessEqual(reserved.total_risk_usd, Decimal("3"))
            broken = dict(signed)
            broken["SIZING"] = dict(signed["SIZING"], hmac_sha256="0"*64)
            with self.assertRaisesRegex(QDLEError, "signature invalid"):
                q._validate_motor_receipts(intent, broken, T)


    def test_five_arm_ablation_independent_constraints_same_costs(self):
        from qore.infrastructure.cibo_four_motor_ablation import ablate_four_motors
        cases = (
            ("SIZING", observation(stress_extra_loss_usd_per_lot=Decimal("109"))),
            ("CIBO_COMPOUND", observation(reconciled_cashflows=(
                cash(1, "-8", -4), cash(2, "-2", -3), cash(3, "-10", -2)))),
            ("ADAPTIVE_LEVERAGE", observation(
                broker_free_margin_usd=Decimal("10"), broker_margin_usd_per_lot=Decimal("500"))),
            ("PORTFOLIO_COMPOUND", observation(
                total_open_stop_risk_usd=Decimal("4.1"),
                correlated_open_stop_risk_usd=Decimal("4.1"))),
        )
        for binding_motor, obs in cases:
            report = ablate_four_motors(obs, minimum_lot=Decimal(".01"), lot_step=Decimal(".01"))
            self.assertEqual(len(report.arms), 5)
            self.assertFalse(report.pnl_attributed)
            self.assertFalse(report.drawdown_attributed)
            impacts = dict(report.incremental_lots_if_disabled)
            if binding_motor == "CIBO_COMPOUND":
                # Removing an arbitrary loss-streak haircut eliminates that
                # old standalone veto. It must not be reintroduced to pass CI.
                self.assertEqual(impacts[binding_motor], 0)
            else:
                self.assertGreater(impacts[binding_motor], 0, binding_motor)
            self.assertTrue(all(delta >= 0 for delta in impacts.values()))
            self.assertTrue(all(arm.potential_risk_usd <= arm.potential_lots *
                                obs.full_stop_cost_per_lot_usd for arm in report.arms))

    def test_3368_distinct_signal_coverage_is_not_historical_fills(self):
        from qore.infrastructure.cibo_four_motor_ablation import ablate_four_motors
        seen = set()
        for i in range(3368):
            obs = replace(observation(), request_id=f"research-{i}")
            report = ablate_four_motors(obs, minimum_lot=Decimal(".01"), lot_step=Decimal(".01"))
            self.assertNotIn(report.request_id, seen)
            seen.add(report.request_id)
            self.assertEqual(len(report.arms), 5)
            self.assertFalse(report.pnl_attributed)
        self.assertEqual(len(seen), 3368)


    def test_six_symbol_both_sides_provenance_and_staleness(self):
        symbols = ("AUDJPY", "EURUSD", "GBPJPY", "GBPUSD", "XAUUSD", "NDX100")
        for i, symbol in enumerate(symbols, start=1):
            for side in ("BUY", "SELL"):
                o = observation(symbol=symbol, side=side,
                                stop_loss_usd_per_lot=Decimal(50*i),
                                broker_margin_usd_per_lot=Decimal(200*i))
                four = votes(o)
                intent = build_four_motor_qdle_intent(
                    observation=o, votes=four,
                    entry_price=Decimal("100"),
                    stop_price=Decimal("99") if side == "BUY" else Decimal("101"))
                self.assertEqual(intent.symbol, symbol)
                self.assertEqual(intent.side, side)
                self.assertLessEqual(intent.sizing_cap_usd, Decimal("3"))
        with self.assertRaisesRegex(FourMotorPolicyError, "stale"):
            observation(broker_quote_at=T-timedelta(seconds=11))
        with self.assertRaisesRegex(FourMotorPolicyError, "future"):
            observation(broker_quote_at=T+timedelta(seconds=1))
        for flag in ("broker_fees_complete", "broker_profit_valuation_complete",
                     "broker_margin_valuation_complete"):
            with self.assertRaisesRegex(FourMotorPolicyError, "incomplete"):
                observation(**{flag:False})


if __name__ == "__main__":
    unittest.main()
