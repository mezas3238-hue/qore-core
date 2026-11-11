"""Seven separate operable CRT research models ≠ seven Pine QA category bits."""
from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta

from research.crt_r4a_holdout.seven_family_contract import (
    FAMILY_SPECS,
    NON_TRADABLE_CATALOG,
    PINE_CATALOG_BITS,
    Certification,
    Family,
    Readiness,
    catalog_labels,
    readiness_summary,
    research_family_from_base_event,
)

T = datetime(2024, 2, 1, 8, tzinfo=UTC)


class SevenResearchFamilies(unittest.TestCase):
    def test_01_seven_unique_family_models(self) -> None:
        self.assertEqual(len(FAMILY_SPECS), 7)
        self.assertEqual({s.family for s in FAMILY_SPECS}, set(Family))

    def test_02_original_seven_catalog_bits_are_separate(self) -> None:
        self.assertEqual(set(PINE_CATALOG_BITS), {1, 2, 4, 8, 16, 32, 64})
        self.assertEqual(len(catalog_labels(127)), 7)

    def test_03_pine_non_entry_roles_remain_non_tradable(self) -> None:
        self.assertEqual(NON_TRADABLE_CATALOG, frozenset((2, 4, 16)))
        self.assertIn("REJECTED", catalog_labels(4)[0])

    def test_04_both_multi_models_share_catalog_role_only(self) -> None:
        multi = [s for s in FAMILY_SPECS if s.catalog_bit == 32]
        self.assertEqual(len(multi), 2)
        self.assertEqual(
            {m.family for m in multi}, {Family.MULTI4, Family.MULTIN}
        )

    def test_05_two_c_source_is_outside_seven_bit_catalog(self) -> None:
        specs = [s for s in FAMILY_SPECS if s.catalog_bit is None]
        self.assertEqual(
            {x.family for x in specs},
            {Family.TWO_C_MSS_C2, Family.TWO_C_MSS_C3},
        )

    def test_06_original_catalog_mask_requires_seven_bits_only(self) -> None:
        for value in (-1, 128, 256, True, None):
            with self.assertRaises(ValueError):
                catalog_labels(value)

    def test_07_split_2c_mss_in_c2(self) -> None:
        self.assertEqual(
            research_family_from_base_event(
                model="A_2C_MSS15", mss_at=T - timedelta(minutes=15),
                ratified_at=T
            ), Family.TWO_C_MSS_C2
        )

    def test_08_split_2c_mss_in_c3(self) -> None:
        self.assertEqual(
            research_family_from_base_event(
                model="A_2C_MSS15", mss_at=T + timedelta(minutes=15),
                ratified_at=T
            ), Family.TWO_C_MSS_C3
        )

    def test_09_true3c_not_2c_mss(self) -> None:
        self.assertEqual(
            research_family_from_base_event(
                model="B_TRUE3C_MSS5", mss_at=T - timedelta(minutes=5),
                ratified_at=T
            ), Family.TRUE_3C
        )

    def test_10_true3c_future_mss_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "lookahead"):
            research_family_from_base_event(
                model="B_TRUE3C_MSS5",
                mss_at=T + timedelta(minutes=5), ratified_at=T
            )

    def test_11_wrong_source_model_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown"):
            research_family_from_base_event(
                model="A_C3_TUNED", mss_at=T, ratified_at=T
            )

    def test_12_all_families_need_own_mss_and_economic_evidence(self) -> None:
        for spec in FAMILY_SPECS:
            self.assertTrue(spec.mss_ownership)
            self.assertTrue(spec.requires_independent_strategy_spec)
            self.assertTrue(spec.requires_original_pine_parity)
            self.assertTrue(spec.requires_net_cost_testing)

    def test_13_only_first_three_have_research_event_detector(self) -> None:
        already = {
            s.family for s in FAMILY_SPECS
            if s.readiness == Readiness.DETECTOR_RESEARCH_ONLY
        }
        self.assertEqual(
            already,
            {Family.TWO_C_MSS_C2, Family.TWO_C_MSS_C3, Family.TRUE_3C},
        )
        self.assertEqual(
            len([s for s in FAMILY_SPECS
                 if s.readiness == Readiness.NOT_IMPLEMENTED]), 4
        )

    def test_14_default_no_order_permission_for_all(self) -> None:
        c = [Certification(f) for f in Family]
        report = readiness_summary(c)
        self.assertEqual(report["expected_trade_research_families"], 7)
        for state in report["families"].values():
            self.assertFalse(state["qualified_for_certified_simulation"])
            self.assertFalse(state["eligible_for_broker_execution"])

    def test_15_simulation_gate_requires_all_evidence(self) -> None:
        cert = Certification(
            Family.TRUE_3C, detector_implemented=True,
            original_pine_parity=True, provider_market_parity=True,
            own_mss_confirmed=True, entry_stop_take_profit_frozen=True,
            bid_ask_costs_verified=True, unseen_24_months_attested=True,
            broker_execution_permissions=True
        )
        self.assertTrue(cert.can_simulate_certified_trades)
        self.assertFalse(cert.can_place_orders)

    def test_16_missing_any_family_blocks_aggregate(self) -> None:
        with self.assertRaisesRegex(ValueError, "7 unique"):
            readiness_summary([Certification(f) for f in list(Family)[:6]])

    def test_17_duplicate_family_blocks_aggregate(self) -> None:
        x = [Certification(f) for f in list(Family)[:6]]
        x.append(Certification(Family.TRUE_3C))
        with self.assertRaisesRegex(ValueError, "7 unique"):
            readiness_summary(x)


if __name__ == "__main__":
    unittest.main(verbosity=2)
