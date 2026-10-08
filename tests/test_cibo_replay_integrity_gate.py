"""Regression tests for CIBO independent sovereignty/certification research gate."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from cibo_replay_integrity_gate import assess_replay


def sample():
    return {
        "ending_total_capital_usd": "600040",
        "ending_sovereign_bank_usd": "40",
        "ending_portfolio_cushion_usd": "600000",
        "minimum_sovereign_bank_usd": "30",
        "sovereign_floor_breach_usd": "0",
        "attack_sovereign_breach_usd": "0",
        "max_drawdown_fraction": "0.22",
        "decision_count": 3368,
        "trade_count": 3368,
        "economic_group_report": {"all_entries_preserved": True},
        "engineering_sensor_report": {"execution_funnel": {
            "final_trade_count": 3368,
            "sizing_medium_rejected_count": 0,
            "sizing_medium_deferred_count": 0,
        }},
    }


class CiboReplayIntegrityGateTest(unittest.TestCase):
    def test_clean_research_prerequisites_never_mean_certified(self):
        r = assess_replay(sample())
        self.assertTrue(r["replay_prerequisites_pass"])
        self.assertTrue(r["sovereign_integrity_pass"])
        self.assertFalse(r["certified"])
        self.assertFalse(r["provider_margin_feasibility_proven"])

    def test_negative_sovereign_fails_even_if_attack_breach_zero(self):
        x = sample()
        x["ending_sovereign_bank_usd"] = "-45"
        x["ending_portfolio_cushion_usd"] = "600085"
        x["minimum_sovereign_bank_usd"] = "-54"
        x["sovereign_floor_breach_usd"] = "84"
        r = assess_replay(x)
        self.assertTrue(r["checks"]["attack_sovereign_breach_zero"])
        self.assertTrue(r["checks"]["total_capital_reconciled"])
        self.assertFalse(r["checks"]["sovereign_protection_floor_breach_zero"])
        self.assertFalse(r["checks"]["no_negative_sovereign_bank"])
        self.assertFalse(r["sovereign_integrity_pass"])

    def test_floor_breach_without_negative_bank_is_still_hard_fail(self):
        x = sample()
        x["sovereign_floor_breach_usd"] = "0.01"
        self.assertFalse(assess_replay(x)["replay_prerequisites_pass"])

    def test_negative_bank_minimum_even_if_final_positive_fails(self):
        x = sample()
        x["minimum_sovereign_bank_usd"] = "-0.0001"
        self.assertFalse(assess_replay(x)["sovereign_integrity_pass"])

    def test_dd_above_target_fails(self):
        x = sample()
        x["max_drawdown_fraction"] = "0.3492401406"
        r = assess_replay(x)
        self.assertTrue(r["sovereign_integrity_pass"])
        self.assertFalse(r["checks"]["max_dd_target"])
        self.assertFalse(r["replay_prerequisites_pass"])

    def test_reconciliation_disagreement_fails(self):
        x = sample()
        x["ending_total_capital_usd"] = "600041"
        self.assertFalse(assess_replay(x)["checks"]["total_capital_reconciled"])

    def test_admission_and_deferral_invariants(self):
        x = sample()
        x["engineering_sensor_report"]["execution_funnel"]["sizing_medium_deferred_count"] = 1
        self.assertFalse(assess_replay(x)["checks"]["all_entries_preserved"])

    def test_nonfinite_accounting_is_rejected(self):
        x = sample()
        x["ending_sovereign_bank_usd"] = "NaN"
        with self.assertRaisesRegex(ValueError, "non-finite"):
            assess_replay(x)


if __name__ == "__main__":
    unittest.main()
