"""Negative safety regression suite for the actual CRT -> broker risk proposal.

All tests are synthetic fixtures. None proves economic return or authorizes orders.
"""
from __future__ import annotations

import inspect
import unittest
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.market_test_environment import MarketRuntimeEnvironment
from qore.infrastructure.traders.crt_r4a_protected_candidate import (
    PINE_SOURCE_BLOB,
    QORE_CRT_34,
    CRTBrokerContract,
    CRTBrokerQuote,
    CRTCandidateError,
    CRTClosedSignal,
    CRTDemoAccountRisk,
    CRTFamily,
    CRTProtectedProposal,
    plan_crt_protected_candidate,
)


class TestCRTR4AProtectedCandidate(unittest.TestCase):
    def setUp(self) -> None:
        self.at = datetime(2026, 11, 12, 10, 25, 20, tzinfo=UTC)
        self.signal = CRTClosedSignal(
            event_id="ic-eurusd-f1-c1-20261112-10",
            symbol="EURUSD",
            family=CRTFamily.TWO_C_MSS_C2,
            direction=1,
            c1_at=self.at - timedelta(hours=4),
            sweep_at=self.at - timedelta(minutes=15),
            mss_at=self.at - timedelta(minutes=5, seconds=20),
            ratified_at=self.at - timedelta(seconds=20),
            available_at=self.at - timedelta(seconds=20),
            c1_high=Decimal("1.12000"),
            c1_low=Decimal("1.10000"),
            sweep_high=Decimal("1.11800"),
            sweep_low=Decimal("1.09900"),
        )
        self.quote = CRTBrokerQuote(
            symbol="EURUSD",
            broker="ICMARKETS_DEMO",
            symbol_id=1,
            bid=Decimal("1.10298"),
            ask=Decimal("1.10300"),
            observed_at=self.at - timedelta(seconds=10),
        )
        self.contract = CRTBrokerContract(
            symbol="EURUSD",
            symbol_id=1,
            price_tick=Decimal("0.00001"),
            value_per_tick_per_unit=Decimal("0.00001"),
            volume_step=Decimal("1000"),
            volume_min=Decimal("1000"),
            volume_max=Decimal("200000"),
            account_currency="USD",
            verified_at=self.at - timedelta(hours=1),
            provider_evidence_sha256="a" * 64,
        )
        self.risk = CRTDemoAccountRisk(
            account_ref="demo-test-123",
            environment=MarketRuntimeEnvironment.DEMO,
            currency="USD",
            equity=Decimal("10000"),
            risk_fraction=Decimal("0.01"),
            max_spread_ticks=3,
            slippage_reserve_ticks=2,
            max_open_and_pending=0,
            daily_loss_fraction=Decimal("0"),
        )

    def propose(
        self,
        *,
        signal: CRTClosedSignal | None = None,
        quote: CRTBrokerQuote | None = None,
        contract: CRTBrokerContract | None = None,
        risk: CRTDemoAccountRisk | None = None,
        at: datetime | None = None,
    ) -> CRTProtectedProposal:
        return plan_crt_protected_candidate(
            signal if signal is not None else self.signal,
            quote if quote is not None else self.quote,
            contract if contract is not None else self.contract,
            risk if risk is not None else self.risk,
            evaluated_at=at if at is not None else self.at,
        )

    def test_01_exact_34_symbols_including_btc(self) -> None:
        self.assertEqual(len(QORE_CRT_34), 34)
        self.assertEqual(len(set(QORE_CRT_34)), 34)
        self.assertIn("BTCUSD", QORE_CRT_34)
        self.assertEqual(len(tuple(CRTFamily)), 7)
        self.assertEqual(PINE_SOURCE_BLOB, "693e3f49719e86e2ea0702f7b355af33bd0c4c7c")

    def test_02_real_quote_and_risk_math_creates_nonexecutable_candidate(self) -> None:
        result = self.propose()
        self.assertEqual(result.direction, 1)
        self.assertEqual(result.symbol_id, 1)
        self.assertEqual(result.entry_reference, Decimal("1.10300"))
        self.assertEqual(result.stop_loss, Decimal("1.09600"))
        self.assertEqual(result.take_profit, Decimal("1.12000"))
        self.assertEqual(result.quantity % Decimal("1000"), 0)
        self.assertGreater(result.quantity, 0)
        self.assertLessEqual(result.money_risk_including_slippage, Decimal("100"))
        self.assertGreater(result.gross_reward_risk_ratio, Decimal("1.5"))
        self.assertTrue(result.native_bracket_required)
        self.assertFalse(result.can_submit)
        self.assertNotEqual(type(result).__name__, "ExecutionSubmission")

    def test_03_same_event_uses_deterministic_idempotency_key(self) -> None:
        a = self.propose()
        b = self.propose()
        self.assertEqual(a.idempotency_key, b.idempotency_key)
        different = self.propose(signal=replace(self.signal, event_id="new-event"))
        self.assertNotEqual(a.idempotency_key, different.idempotency_key)

    def test_04_runtime_cannot_activate_proposal(self) -> None:
        with self.assertRaises(CRTCandidateError):
            replace(self.propose(), can_submit=True)

    def test_05_live_account_is_never_accepted(self) -> None:
        with self.assertRaisesRegex(CRTCandidateError, "LIVE"):
            replace(self.risk, environment=MarketRuntimeEnvironment.PRODUCTION)

    def test_06_rejects_unknown_market_or_provider_feed(self) -> None:
        for changes in (
            {"symbol": "USDTRY"},
            {"source_feed": "OANDA"},
            {"source_pine_blob": "0" * 40},
        ):
            with self.subTest(changes=changes), self.assertRaises(CRTCandidateError):
                replace(self.signal, **changes)

    def test_07_rejects_foreign_quote_broker(self) -> None:
        with self.assertRaises(CRTCandidateError):
            replace(self.quote, broker="COINBASE")

    def test_08_rejects_mismatched_symbols_or_provider_symbol_id(self) -> None:
        for changes in (
            {"symbol": "AUDJPY"},
            {"symbol_id": 999},
        ):
            with self.subTest(changes=changes), self.assertRaises(CRTCandidateError):
                self.propose(quote=replace(self.quote, **changes))

    def test_09_rejects_unaligned_prices(self) -> None:
        with self.assertRaisesRegex(CRTCandidateError, "tick"):
            self.propose(quote=replace(self.quote, ask=Decimal("1.103001")))

    def test_10_rejects_crossed_quotes(self) -> None:
        with self.assertRaises(CRTCandidateError):
            replace(self.quote, bid=Decimal("1.1031"))

    def test_11_requires_fresh_quote(self) -> None:
        with self.assertRaises(CRTCandidateError):
            self.propose(quote=replace(self.quote, observed_at=self.at - timedelta(minutes=1)))

    def test_12_requires_fresh_event_and_no_future_data(self) -> None:
        with self.assertRaises(CRTCandidateError):
            self.propose(at=self.at + timedelta(minutes=6))
        with self.assertRaises(CRTCandidateError):
            self.propose(quote=replace(self.quote, observed_at=self.at + timedelta(minutes=1)))

    def test_13_rejects_noncausal_mss_or_forged_availability(self) -> None:
        with self.assertRaises(CRTCandidateError):
            replace(self.signal, available_at=self.signal.available_at - timedelta(minutes=10))
        with self.assertRaises(CRTCandidateError):
            replace(self.signal, sweep_at=self.signal.mss_at + timedelta(minutes=1))

    def test_14_separates_c2_and_c3_family_timing(self) -> None:
        with self.assertRaises(CRTCandidateError):
            replace(self.signal, family=CRTFamily.TWO_C_MSS_C3)

    def test_15_rejects_wide_spread(self) -> None:
        with self.assertRaisesRegex(CRTCandidateError, "spread"):
            self.propose(quote=replace(self.quote, bid=Decimal("1.10290")))

    def test_16_no_portfolio_reentry_when_pending_or_open(self) -> None:
        with self.assertRaises(CRTCandidateError):
            self.propose(risk=replace(self.risk, max_open_and_pending=1))

    def test_17_daily_drawdown_suspends_candidates(self) -> None:
        with self.assertRaises(CRTCandidateError):
            self.propose(risk=replace(self.risk, daily_loss_fraction=Decimal("0.02")))

    def test_18_cannot_increase_unapproved_risk_above_one_percent(self) -> None:
        with self.assertRaises(CRTCandidateError):
            replace(self.risk, risk_fraction=Decimal("0.02"))

    def test_19_unaffordable_broker_min_volume_rejected(self) -> None:
        with self.assertRaisesRegex(CRTCandidateError, "minimum volume"):
            self.propose(contract=replace(self.contract, volume_min=Decimal("100000")))

    def test_20_currency_conversion_must_be_external_broker_verified(self) -> None:
        with self.assertRaisesRegex(CRTCandidateError, "lineage mismatch"):
            self.propose(contract=replace(self.contract, account_currency="EUR"))

    def test_21_expired_contract_metadata_rejected(self) -> None:
        with self.assertRaises(CRTCandidateError):
            self.propose(contract=replace(
                self.contract, verified_at=self.at - timedelta(days=2)
            ))

    def test_22_requires_positive_valid_stop_and_take_profit(self) -> None:
        with self.assertRaisesRegex(CRTCandidateError, "reward/risk"):
            self.propose(quote=replace(
                self.quote, bid=Decimal("1.11898"), ask=Decimal("1.11900")
            ))

    def test_23_short_side_has_proper_broker_bid_and_stops(self) -> None:
        short = replace(self.signal, direction=-1)
        quote = replace(
            self.quote, bid=Decimal("1.11600"), ask=Decimal("1.11602")
        )
        candidate = self.propose(signal=short, quote=quote)
        self.assertEqual(candidate.entry_reference, Decimal("1.11600"))
        self.assertEqual(candidate.stop_loss, Decimal("1.12300"))
        self.assertEqual(candidate.take_profit, Decimal("1.10000"))
        self.assertFalse(candidate.can_submit)

    def test_24_no_broker_access_or_approval_is_embedded(self) -> None:
        source = inspect.getsource(plan_crt_protected_candidate)
        for fragment in (
            "submit_authorized(", "ProtoOANewOrderReq", "request.security",
            "approve(", "ExecutionSubmission(",
        ):
            self.assertNotIn(fragment, source)
        self.assertIn("can_submit: bool = False", inspect.getsource(CRTProtectedProposal))


if __name__ == "__main__":
    unittest.main()
