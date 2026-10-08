"""Research-only invariants for H8 real-cash sovereign liquidity bridge."""
from decimal import Decimal as D
import unittest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.trader_lab.cibo_three_mode_capital_lab import _State


class TestCiboH8CashConservedBridge(unittest.TestCase):
    def test_moves_only_unreserved_cash_and_preserves_total(self):
        state = _State(
            sovereign_bank_usd=D("35"),
            portfolio_cushion_usd=D("20"),
            cushion_reserved_usd=D("5"),
            portfolio_attack_credit_usd=D("20"),
        )
        total_before = state.total_capital_usd
        state.bridge_from_unreserved_cushion(D("12"))
        self.assertEqual(state.total_capital_usd, total_before)
        self.assertEqual(state.sovereign_bank_usd, D("47"))
        self.assertEqual(state.portfolio_cushion_usd, D("8"))
        self.assertEqual(state.cushion_available_usd, D("3"))
        self.assertEqual(state.attack_credit_available_usd, D("3"))
        self.assertEqual(state.physical_cushion_to_sovereign_bridge_count, 1)
        self.assertEqual(state.physical_cushion_to_sovereign_bridge_total_usd, D("12"))
        self.assertGreaterEqual(state.sovereign_bank_usd, state.sovereign_protection_floor_usd)

    def test_refuses_to_borrow_reserved_or_nonexistent_cushion(self):
        state = _State(
            sovereign_bank_usd=D("35"),
            portfolio_cushion_usd=D("20"),
            cushion_reserved_usd=D("15"),
        )
        total_before = state.total_capital_usd
        with self.assertRaises(CiboCapitalManagementError):
            state.bridge_from_unreserved_cushion(D("6"))
        self.assertEqual(state.total_capital_usd, total_before)
        self.assertEqual(state.sovereign_bank_usd, D("35"))
        self.assertEqual(state.portfolio_cushion_usd, D("20"))
        self.assertEqual(state.physical_cushion_to_sovereign_bridge_count, 0)

    def test_zero_transfer_is_no_op(self):
        state = _State()
        total_before = state.total_capital_usd
        state.bridge_from_unreserved_cushion(D("0"))
        self.assertEqual(state.total_capital_usd, total_before)
        self.assertEqual(state.physical_cushion_to_sovereign_bridge_count, 0)


if __name__ == "__main__":
    unittest.main()
