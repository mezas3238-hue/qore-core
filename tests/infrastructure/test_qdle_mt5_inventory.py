"""Synthetic MT5 inventory contract: QDLE never guesses the actual broker alias."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from qdle_mt5_read_only_inventory import discover


class MT5:
    def __init__(self, names):
        self.names = names
    def account_info(self):
        return SimpleNamespace(login=123, currency="USD", server="synthetic")
    def symbols_get(self):
        return tuple(SimpleNamespace(
            name=n, volume_min=0.01, volume_max=100, volume_step=0.01,
            volume_limit=10, trade_contract_size=100,
            trade_tick_size=0.01, trade_tick_value=1,
            trade_tick_value_profit=1, trade_tick_value_loss=1,
            currency_profit="USD", trade_mode=4, visible=True
        ) for n in self.names)


class TestInventory(unittest.TestCase):
    def test_six_contracts_are_observed_but_never_assumed(self):
        mt5 = MT5(["AUDJPY", "EURUSD", "GBPJPY", "GBPUSD", "NDX100", "XAUUSD"])
        evidence = discover(mt5, "123")
        self.assertEqual(evidence["missing_or_unresolved"], [])
        self.assertEqual(evidence["symbols"]["NAS100"][0]["mt5_exact_symbol"], "NDX100")
        self.assertEqual(evidence["symbols"]["XAUUSD"][0]["fee_usd_per_lot"], None)
        self.assertFalse(evidence["account_login_recorded"])
        self.assertNotIn("123", str(evidence))

    def test_alias_ambiguity_is_reported_not_guessed(self):
        mt5 = MT5(["AUDJPY", "EURUSD", "GBPJPY", "GBPUSD", "NDX100",
                   "NAS100.cash", "XAUUSD"])
        evidence = discover(mt5, "123")
        self.assertEqual(evidence["missing_or_unresolved"], ["NAS100"])
        self.assertEqual(len(evidence["symbols"]["NAS100"]), 2)

    def test_missing_symbol_and_wrong_account_fail_closed(self):
        mt5 = MT5(["AUDJPY"])
        self.assertIn("XAUUSD", discover(mt5, "123")["missing_or_unresolved"])
        with self.assertRaisesRegex(ValueError, "login mismatch"):
            discover(mt5, "456")


if __name__ == "__main__":
    unittest.main()
