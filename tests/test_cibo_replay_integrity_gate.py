"""Regression tests for CIBO independent sovereignty/certification research gate."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from cibo_replay_integrity_gate import assess_replay, assess_research_pareto


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
        "economic_group_report": {
            "all_entries_preserved": True,
            "portfolio_loss_report": {
                "total_gross_loss_usd": "960000",
                "attack_gross_loss_usd": "959000",
            },
        },
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


    def test_control_itself_cannot_be_strict_pareto(self):
        x = sample()
        r = assess_research_pareto(x, x)
        self.assertFalse(r["checks"]["meaningful_dd_improvement"])
        self.assertFalse(r["strict_sovereign_safe_research_pareto"])

    def test_tiny_dd_serialization_drift_not_strict_pareto(self):
        baseline = sample()
        x = sample()
        x["max_drawdown_fraction"] = "0.21999999999999999999999999999999998"
        r = assess_research_pareto(x, baseline)
        self.assertFalse(r["strict_sovereign_safe_research_pareto"])

    def test_materially_lower_dd_and_nonworse_loss_passes_research_only(self):
        baseline = sample()
        x = sample()
        x["max_drawdown_fraction"] = "0.219"
        x["economic_group_report"]["portfolio_loss_report"]["total_gross_loss_usd"] = "959900"
        x["economic_group_report"]["portfolio_loss_report"]["attack_gross_loss_usd"] = "958900"
        r = assess_research_pareto(x, baseline)
        self.assertTrue(r["strict_sovereign_safe_research_pareto"])
        self.assertFalse(r["certified"])

    def test_research_pareto_does_not_override_sovereign_breach(self):
        baseline = sample()
        x = sample()
        x["max_drawdown_fraction"] = "0.210"
        x["ending_sovereign_bank_usd"] = "-50"
        x["ending_portfolio_cushion_usd"] = "600090"
        x["minimum_sovereign_bank_usd"] = "-60"
        x["sovereign_floor_breach_usd"] = "90"
        r = assess_research_pareto(x, baseline)
        self.assertFalse(r["strict_sovereign_safe_research_pareto"])
        self.assertFalse(r["checks"]["full_sovereign_integrity"])


if __name__ == "__main__":
    unittest.main()
