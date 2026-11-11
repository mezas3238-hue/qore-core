"""Synthetic M5→H4→CRT→owned MSS regression; no historical PnL claims."""
from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from research.crt_r4a_holdout.causal_crt_m5_engine import (
    Candle,
    CausalCRTM5,
)

NY = ZoneInfo("America/New_York")
START = datetime(2024, 2, 1, 1, tzinfo=NY).astimezone(UTC)
M5 = timedelta(minutes=5)
MODEL_A = "A_2C_MSS15"
MODEL_B = "B_TRUE3C_MSS5"


def generated(kind: str, *, gap: bool = False) -> list[Candle]:
    data: list[Candle] = []
    for block in range(4):
        for i in range(48):
            minute = block * 48 + i
            when = START + minute * M5
            if block == 0:
                hi, low, cl = 110.0, 100.0, 105.0
            elif block == 1:
                hi, low, cl = 106.0, 101.0, 104.0
                if kind.startswith("A") and 6 <= i <= 8:
                    hi = 107.0
                if kind.startswith("A") and i == 16:
                    low = 99.0
                if kind == "A_C2_MSS" and i == 20:
                    hi, cl = 109.0, 108.0
                if kind.startswith("B") and i == 42:
                    hi = 108.0
            elif block == 2:
                hi, low, cl = 106.0, 101.0, 104.0
                if kind == "A_C3_MSS" and i == 2:
                    hi, cl = 109.0, 108.0
                if kind.startswith("B") and i == 4:
                    low, cl = 99.0, 102.0
                if kind.startswith("B") and i == 6:
                    hi, cl = 109.0, 109.0
                if kind == "B_C3_OUTSIDE" and i == 47:
                    hi, cl = 112.0, 111.0
                if kind == "B_DOUBLE_SWEEP" and i == 9:
                    hi = 111.0
            else:
                hi, low, cl = 106.0, 101.0, 104.0
            if gap and block == 1 and i == 24:
                continue
            data.append(Candle(when, cl, hi, low, cl))
    return data


def run(kind: str, *, gap: bool = False) -> CausalCRTM5:
    engine = CausalCRTM5("EURUSD", "forex")
    for c in generated(kind, gap=gap):
        engine.consume(c)
    return engine


class IntegratedEngine(unittest.TestCase):
    def test_01_valid_symbol_family_and_native_phase(self) -> None:
        with self.assertRaises(ValueError):
            CausalCRTM5("", "forex")
        with self.assertRaises(ValueError):
            CausalCRTM5("EURUSD", "unknown")
        with self.assertRaises(ValueError):
            CausalCRTM5("EURUSD", "forex", phase=5)

    def test_02_candle_geometry_checked(self) -> None:
        with self.assertRaises(ValueError):
            Candle(START, 111, 110, 100, 111)
        with self.assertRaises(ValueError):
            Candle(datetime(2024, 2, 1), 105, 110, 100, 105)

    def test_03_a_mss15_in_c2_only_after_h4_ratification(self) -> None:
        e = run("A_C2_MSS")
        a = [x for x in e.evidence if x.model == MODEL_A]
        self.assertEqual(len(a), 1)
        self.assertEqual(a[0].side, "LONG")
        self.assertEqual(a[0].ratified_at, START + timedelta(hours=8))
        self.assertLess(a[0].mss_at, a[0].ratified_at)
        self.assertEqual(a[0].available_at, a[0].ratified_at)

    def test_04_a_mss15_c3_after_c2_ratified_causal(self) -> None:
        e = run("A_C3_MSS")
        a = [x for x in e.evidence if x.model == MODEL_A]
        self.assertEqual(len(a), 1)
        self.assertLess(a[0].ratified_at, a[0].mss_at)
        self.assertEqual(a[0].available_at, a[0].mss_at)

    def test_05_a_without_crossover_m15_cannot_emit(self) -> None:
        e = run("A_NO_MSS")
        self.assertFalse([x for x in e.evidence if x.model == MODEL_A])

    def test_06_b_true3c_only_after_c3_h4_closes(self) -> None:
        e = run("B_VALID")
        b = [x for x in e.evidence if x.model == MODEL_B]
        self.assertEqual(len(b), 1)
        self.assertEqual(b[0].side, "LONG")
        self.assertEqual(b[0].ratified_at, START + timedelta(hours=12))
        self.assertLess(b[0].mss_at, b[0].ratified_at)
        self.assertEqual(b[0].available_at, b[0].ratified_at)

    def test_07_b_c3_outside_c1_rejected(self) -> None:
        e = run("B_C3_OUTSIDE")
        self.assertFalse([x for x in e.evidence if x.model == MODEL_B])

    def test_08_b_c3_double_sweep_rejected(self) -> None:
        e = run("B_DOUBLE_SWEEP")
        self.assertFalse([x for x in e.evidence if x.model == MODEL_B])

    def test_09_h4_incomplete_does_not_ratify(self) -> None:
        e = run("A_C2_MSS", gap=True)
        self.assertFalse([x for x in e.evidence if x.model == MODEL_A])

    def test_10_sorted_unique_and_non_future_evidence(self) -> None:
        for kind in ("A_C2_MSS", "A_C3_MSS", "B_VALID"):
            e = run(kind)
            ids = [x.identity for x in e.evidence]
            self.assertEqual(len(ids), len(set(ids)))
            for item in e.evidence:
                self.assertEqual(
                    item.available_at, max(item.ratified_at, item.mss_at)
                )
                self.assertLess(item.c1_at, item.sweep_at)
                self.assertLess(item.sweep_at, item.mss_at)

    def test_11_all_synthetic_outputs_explicitly_not_pine_parity(self) -> None:
        out = run("B_VALID").readout()
        self.assertIs(out["is_original_pine_f_engine"], False)
        self.assertIs(out["holdout_certified"], False)
        self.assertIs(out["trading_orders_permitted"], False)

    def test_12_reject_nonmonotone_input(self) -> None:
        engine = CausalCRTM5("EURUSD", "forex")
        first = generated("B_VALID")[0]
        engine.consume(first)
        with self.assertRaisesRegex(ValueError, "nonmonotone"):
            engine.consume(first)

    def test_13_reject_mismatch_provider_phase(self) -> None:
        engine = CausalCRTM5("EURUSD", "forex", phase=2)
        with self.assertRaisesRegex(ValueError, "phase"):
            engine.consume(generated("B_VALID")[0])

    def test_14_parity_row_has_frozen_identity_and_timestamps(self) -> None:
        e = run("B_VALID")
        b = [x for x in e.evidence if x.model == MODEL_B]
        self.assertEqual(len(b), 1)
        row = b[0].parity_row()
        self.assertEqual(row["symbol"], "EURUSD")
        self.assertEqual(row["model"], MODEL_B)
        self.assertEqual(row["side"], "LONG")
        self.assertEqual(row["available_at"], row["ratified_at"])
        self.assertTrue(row["mss_pivot"])

    def test_16_two_c_MSS_in_C2_routed_to_separate_family(self) -> None:
        e = run("A_C2_MSS")
        out = e.readout()
        families = out["seven_family_research_event_counts"]
        self.assertEqual(families["CRT_2C_RETURN_MSS15_IN_C2"], 1)
        self.assertEqual(families["CRT_2C_RETURN_MSS15_IN_C3"], 0)
        self.assertEqual(out["seven_families_registered"], 7)

    def test_17_two_c_MSS_in_C3_routed_to_separate_family(self) -> None:
        e = run("A_C3_MSS")
        out = e.readout()
        families = out["seven_family_research_event_counts"]
        self.assertEqual(families["CRT_2C_RETURN_MSS15_IN_C2"], 0)
        self.assertEqual(families["CRT_2C_RETURN_MSS15_IN_C3"], 1)

    def test_18_true3c_does_not_inherit_two_c_family(self) -> None:
        e = run("B_VALID")
        out = e.readout()
        families = out["seven_family_research_event_counts"]
        self.assertEqual(families["CRT_TRUE3C_MSS5"], 1)
        self.assertEqual(sum(families.values()), out["events_total"])
        self.assertEqual(out["family_only_geometry_until_own_mss"], 4)

    def test_15_new_c1_clock_not_restricted_to_legacy_three(self) -> None:
        engine = CausalCRTM5("EURUSD", "forex")
        for c in generated("A_C2_MSS"):
            engine.consume(c)
        self.assertGreaterEqual(engine.readout()["stats"]["h4_complete"], 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
