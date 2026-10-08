"""Offline invariants for the four-engine per-entry physical lot calculator."""
from decimal import Decimal as D
from dataclasses import replace
from unittest import TestCase

from qore.infrastructure.cibo_physical_lot_sizing import (
    CiboLotSizingError,
    CiboLotSizingInput,
    compute_cibo_lot_sizing,
    stop_loss_usd_per_lot,
)


def quote(**changes: D) -> CiboLotSizingInput:
    default = CiboLotSizingInput(
        requested_loss_budget_usd=D("3"),
        stop_risk_usd_per_lot=D("30"),
        provider_cost_usd_per_lot=D("0"),
        margin_usd_per_lot=D("50"),
        broker_min_lot=D("0.01"),
        broker_max_lot=D("100"),
        broker_lot_step=D("0.01"),
        sizing_risk_cap_usd=D("3"),
        cibo_compound_risk_cap_usd=D("3"),
        portfolio_unreserved_cash_usd=D("0"),
        sovereign_unreserved_cash_usd=D("3"),
        source_lane="SOVEREIGN_BANK",
        leverage_available_margin_usd=D("500"),
        sovereign_unreserved_risk_usd=D("3"),
        leverage_max_lots=D("100"),
    )
    return replace(default, **changes)


class CiboDynamicLotSizingTests(TestCase):
    def test_three_dollars_equals_point_ten_lot_for_thirty_per_lot(self) -> None:
        result = compute_cibo_lot_sizing(quote())
        self.assertEqual(result.status, "FUNDED_PROPOSAL_NOT_EXECUTION")
        self.assertEqual(result.lots, D("0.10"))
        self.assertEqual(result.all_in_loss_if_stopped_usd, D("3.00"))

    def test_stop_distance_drives_volume_not_fixed_one_lot(self) -> None:
        for dollars_per_lot, expected_lots in [
            ("300", "0.01"), ("150", "0.02"),
            ("30", "0.10"), ("15", "0.20"),
        ]:
            with self.subTest(stop_risk_per_lot=dollars_per_lot):
                result = compute_cibo_lot_sizing(
                    quote(stop_risk_usd_per_lot=D(dollars_per_lot),
                          margin_usd_per_lot=D("10"))
                )
                self.assertEqual(result.lots, D(expected_lots))
                self.assertEqual(result.all_in_loss_if_stopped_usd, D("3"))

    def test_fee_is_within_three_dollars_not_added_afterward(self) -> None:
        result = compute_cibo_lot_sizing(
            quote(provider_cost_usd_per_lot=D("3"))
        )
        self.assertEqual(result.lots, D("0.09"))
        self.assertEqual(result.all_in_loss_if_stopped_usd, D("2.97"))
        self.assertEqual(result.stop_risk_usd, D("2.70"))

    def test_minimum_broker_lot_unfundable_fails_closed(self) -> None:
        result = compute_cibo_lot_sizing(
            quote(stop_risk_usd_per_lot=D("400"),
                  broker_min_lot=D("0.01"))
        )
        self.assertEqual(result.status, "UNFUNDABLE_BROKER_MINIMUM")
        self.assertEqual(result.lots, D("0"))
        self.assertIn("REQUESTED_USD", result.binding_constraints)

    def test_step_aligned_round_down_only(self) -> None:
        result = compute_cibo_lot_sizing(
            quote(broker_lot_step=D("0.03"), broker_min_lot=D("0.03"),
                  stop_risk_usd_per_lot=D("20"),
                  margin_usd_per_lot=D("10"))
        )
        self.assertEqual(result.lots, D("0.15"))
        self.assertLessEqual(result.all_in_loss_if_stopped_usd, D("3"))

    def test_sizing_cap_binds(self) -> None:
        result = compute_cibo_lot_sizing(
            quote(sizing_risk_cap_usd=D("0.9"))
        )
        self.assertEqual(result.lots, D("0.03"))
        self.assertIn("SIZING", result.binding_constraints)

    def test_compound_cap_binds(self) -> None:
        result = compute_cibo_lot_sizing(
            quote(cibo_compound_risk_cap_usd=D("0.6"))
        )
        self.assertEqual(result.lots, D("0.02"))
        self.assertIn("CIBO_COMPOUND", result.binding_constraints)

    def test_portfolio_cannot_spend_reserved_cash(self) -> None:
        result = compute_cibo_lot_sizing(
            quote(source_lane="PORTFOLIO_CUSHION", portfolio_unreserved_cash_usd=D("0.3"))
        )
        self.assertEqual(result.lots, D("0.01"))
        self.assertIn("COMPOUND_PORTFOLIO", result.binding_constraints)

    def test_medium_does_not_require_unfunded_cushion(self) -> None:
        result = compute_cibo_lot_sizing(quote(portfolio_unreserved_cash_usd=D("0")))
        self.assertEqual(result.lots, D("0.10"))
        self.assertNotIn("COMPOUND_PORTFOLIO", dict(result.engine_max_lots))

    def test_source_isolation_never_borrows_cushion_for_bank(self) -> None:
        result = compute_cibo_lot_sizing(
            quote(sovereign_unreserved_cash_usd=D("0"),
                  portfolio_unreserved_cash_usd=D("5000"))
        )
        self.assertEqual(result.status, "UNFUNDABLE_BROKER_MINIMUM")
        self.assertIn("SOVEREIGN_BANK", result.binding_constraints)

    def test_leverage_margin_restricts_without_inventing_cash(self) -> None:
        result = compute_cibo_lot_sizing(
            quote(leverage_available_margin_usd=D("1.2"))
        )
        self.assertEqual(result.lots, D("0.02"))
        self.assertIn("ADAPTIVE_LEVERAGE_MARGIN", result.binding_constraints)

    def test_leverage_volume_cap_binds(self) -> None:
        result = compute_cibo_lot_sizing(
            quote(leverage_max_lots=D("0.04"))
        )
        self.assertEqual(result.lots, D("0.04"))

    def test_sovereign_headroom_binds(self) -> None:
        result = compute_cibo_lot_sizing(
            quote(sovereign_unreserved_risk_usd=D("0.3"))
        )
        self.assertEqual(result.lots, D("0.01"))
        self.assertIn("QORE_RISK", result.binding_constraints)

    def test_stop_loss_quote_uses_broker_confirmed_tick_value(self) -> None:
        value = stop_loss_usd_per_lot(
            entry_price=D("100"), stop_price=D("99.5"),
            tick_size=D("0.1"), tick_value_usd_per_lot=D("6"),
        )
        self.assertEqual(value, D("30"))
        self.assertEqual(
            compute_cibo_lot_sizing(
                quote(stop_risk_usd_per_lot=value)
            ).lots,
            D("0.10"),
        )

    def test_invalid_or_unknown_broker_values_fail_closed(self) -> None:
        for overrides in (
            {"broker_lot_step": D("0")},
            {"broker_min_lot": D("200")},
            {"stop_risk_usd_per_lot": D("NaN")},
            {"margin_usd_per_lot": D("-1")},
        ):
            with self.subTest(overrides=overrides):
                with self.assertRaises(CiboLotSizingError):
                    quote(**overrides)


if __name__ == "__main__":
    import unittest
    unittest.main()
