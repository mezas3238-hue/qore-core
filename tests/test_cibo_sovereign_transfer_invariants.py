"""Isolated research contract for causal Portfolio -> Sovereign transfers.

These tests do not enable transfers in production or justify broker
executable margin. They guard exact ledger accounting and reservation
semantics of the experimental post-settlement transfer only.
"""
from __future__ import annotations

import sys
import unittest
from decimal import Decimal as D
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from cibo_sovereign_causal_rebalance_replay import reconcile_available_cushion
from qore.infrastructure.trader_lab.cibo_three_mode_capital_lab import _State


def make_state(bank="20", cushion="70", reserved="20", credit="50"):
    state = _State()
    state.sovereign_bank_usd = D(bank)
    state.portfolio_cushion_usd = D(cushion)
    state.cushion_reserved_usd = D(reserved)
    state.portfolio_attack_credit_usd = D(credit)
    return state


class CausalSovereignTransferContractTest(unittest.TestCase):
    def test_exact_conservation_and_credit_debit(self):
        state = make_state()
        original = state.total_capital_usd
        transferred = reconcile_available_cushion(state, D("30"))
        self.assertEqual(transferred, D("10"))
        self.assertEqual(state.sovereign_bank_usd, D("30"))
        self.assertEqual(state.portfolio_cushion_usd, D("60"))
        self.assertEqual(state.portfolio_attack_credit_usd, D("40"))
        self.assertEqual(state.cushion_reserved_usd, D("20"))
        self.assertEqual(state.total_capital_usd, original)

    def test_same_snapshot_is_idempotent(self):
        state = make_state()
        reconcile_available_cushion(state, D("30"))
        before = (state.total_capital_usd, state.portfolio_attack_credit_usd)
        self.assertEqual(reconcile_available_cushion(state, D("30")), 0)
        self.assertEqual((state.total_capital_usd, state.portfolio_attack_credit_usd), before)

    def test_reserved_portfolio_capital_never_reallocated(self):
        state = make_state(bank="20", cushion="25", reserved="22", credit="3")
        self.assertEqual(reconcile_available_cushion(state, D("30")), D("3"))
        self.assertEqual(state.sovereign_bank_usd, D("23"))
        self.assertEqual(state.portfolio_cushion_usd, D("22"))
        self.assertEqual(state.cushion_reserved_usd, D("22"))
        self.assertEqual(state.portfolio_attack_credit_usd, D("0"))

    def test_complete_reservation_prevents_transfer(self):
        state = make_state(bank="20", cushion="25", reserved="25", credit="0")
        before = state.total_capital_usd
        self.assertEqual(reconcile_available_cushion(state, D("30")), 0)
        self.assertEqual(state.total_capital_usd, before)
        self.assertEqual(state.sovereign_bank_usd, D("20"))

    def test_only_zero_recovery_is_not_floor_recovery(self):
        state = make_state(bank="-6.34", cushion="200", reserved="0", credit="200")
        self.assertEqual(reconcile_available_cushion(state, D("0")), D("6.34"))
        self.assertEqual(state.sovereign_bank_usd, D("0"))
        self.assertGreater(D("30") - state.sovereign_bank_usd, 0)

    def test_nonzero_sovereign_repair_is_only_internal_transfer(self):
        state = make_state(bank="-6.34", cushion="200", reserved="0", credit="200")
        before = state.total_capital_usd
        self.assertEqual(reconcile_available_cushion(state, D("30")), D("36.34"))
        self.assertEqual(state.sovereign_bank_usd, D("30"))
        self.assertEqual(state.portfolio_cushion_usd, D("163.66"))
        self.assertEqual(state.portfolio_attack_credit_usd, D("163.66"))
        self.assertEqual(state.total_capital_usd, before)

    def test_credit_can_be_less_than_available_cushion(self):
        state = make_state(bank="20", cushion="100", reserved="40", credit="5")
        self.assertEqual(reconcile_available_cushion(state, D("30")), D("10"))
        self.assertEqual(state.portfolio_attack_credit_usd, D("0"))
        self.assertEqual(state.cushion_reserved_usd, D("40"))
        self.assertEqual(state.total_capital_usd, D("120"))

    def test_high_precision_exact_ledger_conservation(self):
        state = make_state(
            bank="26.50342695591957875951644191",
            cushion="68.33166195542809971775742412",
            reserved="0.00000000000000000000000000000775",
            credit="68.33166195542809971775742411",
        )
        expected = D("30.0000000000000000000000000100")
        before = state.total_capital_usd
        transferred = reconcile_available_cushion(state, expected)
        self.assertEqual(transferred, D("3.4965730440804212404835581000"))
        self.assertEqual(state.total_capital_usd, before)
        self.assertEqual(state.sovereign_bank_usd, expected)

    def test_no_transfer_when_sovereign_already_protected(self):
        state = make_state(bank="35", cushion="70", reserved="0", credit="70")
        self.assertEqual(reconcile_available_cushion(state, D("30")), D("0"))


if __name__ == "__main__":
    unittest.main()
