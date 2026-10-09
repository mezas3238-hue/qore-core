"""ATR stop candidate contract tests: causal SHADOW only, no live sender."""
from __future__ import annotations

import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D

from qore.infrastructure.cibo_atr_stop_shadow import (
    ATR_SL_POLICY_VERSION,
    CausalATR14,
    CausalATRStopError,
    propose_cibo_atr_stop_shadow,
)

NOW = datetime(2026, 10, 8, 15, tzinfo=timezone.utc)
HASH = "sha256:" + "a" * 64


def valid_atr(*, symbol="EURUSD", timeframe="H1", attr="0.0012"):
    return CausalATR14(
        symbol=symbol, timeframe=timeframe, atr14_price_units=D(attr),
        last_bar_closed_at=NOW - timedelta(minutes=60),
        evidence_available_at=NOW - timedelta(minutes=59),
        evidence_sha256=HASH, closed_bar_count=27,
    )


def proposal(**overrides):
    p = dict(
        mode="BANK", symbol="EURUSD", timeframe="H1", side="BUY",
        entry_price=D("1.10000"), original_stop_price=D("1.09800"),
        tick_size_price=D("0.00001"),
        broker_min_stop_distance_price=D("0.0002"),
        structure_min_stop_distance_price=D("0.0004"),
        decision_at=NOW, atr=valid_atr(),
    )
    p.update(overrides)
    return propose_cibo_atr_stop_shadow(**p)


class TestCausalAtrStopShadow(unittest.TestCase):
    def test_eurusd_bank_medium_attack_causal_distances(self):
        for mode, stop in (
            ("BANK", "1.09940"), ("MEDIUM", "1.09880"),
            ("ATTACK", "1.09820")
        ):
            with self.subTest(mode=mode):
                result = proposal(mode=mode)
                self.assertEqual(result.proposed_stop_price, D(stop))
                self.assertEqual(result.status, "SHADOW_GEOMETRY_VALID")
                self.assertFalse(result.is_live_authorized)
                self.assertEqual(result.policy_version, ATR_SL_POLICY_VERSION)

    def test_stop_away_from_entry_on_both_sides(self):
        a = proposal(side="SELL", original_stop_price=D("1.10200"),
                     entry_price=D("1.10000"))
        self.assertEqual(a.proposed_stop_price, D("1.10060"))
        self.assertEqual(a.status, "SHADOW_GEOMETRY_VALID")

    def test_rounding_never_makes_risk_smaller_than_atr(self):
        original = D("1.10002")
        r = proposal(entry_price=original, original_stop_price=D("1.098"),
                     tick_size_price=D(".0001"),
                     broker_min_stop_distance_price=D("0"),
                     structure_min_stop_distance_price=D(".0001"))
        self.assertEqual(r.proposed_stop_price, D("1.0994"))
        self.assertGreaterEqual(r.proposed_stop_distance_price, D(".0006"))

    def test_missing_structural_evidence_cannot_release_to_execution(self):
        r = proposal(structure_min_stop_distance_price=None)
        self.assertEqual(r.status, "SHADOW_NOT_EXECUTABLE")
        self.assertIn("STRUCTURAL_INVALIDATION_NOT_VERIFIED", r.reason_codes)

    def test_intrabar_future_data_cannot_be_used(self):
        with self.assertRaisesRegex(CausalATRStopError, "future"):
            proposal(atr=replace(valid_atr(),
                    last_bar_closed_at=NOW + timedelta(seconds=1),
                    evidence_available_at=NOW + timedelta(seconds=2)))
        with self.assertRaisesRegex(CausalATRStopError, "future"):
            proposal(atr=replace(valid_atr(),
                    evidence_available_at=NOW + timedelta(seconds=1)))

    def test_stale_atr_and_short_warmup_fails(self):
        with self.assertRaisesRegex(CausalATRStopError, "stale"):
            proposal(atr=replace(valid_atr(),
                    last_bar_closed_at=NOW - timedelta(hours=4),
                    evidence_available_at=NOW - timedelta(hours=4)))
        with self.assertRaisesRegex(CausalATRStopError, "warmup"):
            valid_atr().__class__(
                symbol="EURUSD", timeframe="H1", atr14_price_units=D("0.0012"),
                last_bar_closed_at=NOW-timedelta(hours=1),
                evidence_available_at=NOW-timedelta(minutes=59),
                evidence_sha256=HASH, closed_bar_count=14,
            )

    def test_stop_violation_broker_or_strategy_does_not_silently_widen(self):
        b = proposal(broker_min_stop_distance_price=D(".0007"))
        self.assertEqual(b.status, "SHADOW_NOT_EXECUTABLE")
        self.assertEqual(b.proposed_stop_price, D("1.09940"))
        self.assertIn("BROKER_MIN_STOP_DISTANCE", b.reason_codes)
        c = proposal(structure_min_stop_distance_price=D(".0008"))
        self.assertIn("INVALID_STRUCTURE_TOO_TIGHT", c.reason_codes)

    def test_nas100_alias_and_price_units_not_fx_pips(self):
        a = CausalATR14("NDX100", "M1", D("56.5"),
                        NOW-timedelta(minutes=1),
                        NOW-timedelta(seconds=55), HASH, 30)
        c = proposal(symbol="NAS100", timeframe="M1",
                     side="BUY", entry_price=D("7778.85"),
                     original_stop_price=D("7700"),
                     tick_size_price=D(".01"),
                     broker_min_stop_distance_price=D("1"),
                     structure_min_stop_distance_price=D("10"),
                     atr=a)
        self.assertEqual(c.symbol, "NDX100")
        self.assertEqual(c.multiplier, D(".5"))
        self.assertEqual(c.proposed_stop_price, D("7750.60"))
        self.assertEqual(c.status, "SHADOW_GEOMETRY_VALID")

    def test_reject_missing_or_invalid_values(self):
        with self.assertRaises(CausalATRStopError):
            proposal(mode="UNKNOWN")
        with self.assertRaises(CausalATRStopError):
            proposal(symbol="XAUUSD")
        with self.assertRaises(CausalATRStopError):
            proposal(side="BUY", original_stop_price=D("1.101"))
        with self.assertRaises(CausalATRStopError):
            proposal(atr=replace(valid_atr(),atr14_price_units=D("NaN")))
        with self.assertRaises(CausalATRStopError):
            proposal(atr=replace(valid_atr(),evidence_sha256="not-valid"))


if __name__ == "__main__":
    unittest.main()
