"""Trust-boundary tests for a science-only bridge, not trader qualification."""
from __future__ import annotations

import copy
import unittest
from typing import Any

from qore.infrastructure.trader_lab import qore_eia_research_science_handoff_v1 as gate


def _window(
    year: str, b: int, c: int, ub: int, uc: int, delta: float, p: float,
    decision: str,
) -> dict[str, Any]:
    return {
        "window": year,
        "n_months": b + c,
        "n_backwardation_months": b,
        "n_contango_months": c,
        "up_backwardation": ub,
        "down_backwardation": b - ub,
        "up_contango": uc,
        "down_contango": c - uc,
        "delta_probability_up": delta,
        "one_sided_fisher_p": p,
        "min_months_per_state": 8,
        "minimum_positive_delta": 0.1,
        "family_alpha_per_root": 0.025,
        "decision": decision,
    }


def fixture_from_original_actions_log() -> dict[str, Any]:
    """Diagnostic counts transcribed from SUCCESS #38448311219, no market prices."""
    wti_dev = _window(
        "2012-2018", 22, 61, 10, 30, -0.0372578241, 0.7077117236,
        "NO_POSITIVE_DIRECTION",
    )
    wti_diag = _window(
        "2019-2021", 14, 22, 12, 14, 0.2207792208, 0.1444197256,
        "NO_SUPPORT_UNDER_PREREG",
    )
    ng_dev = _window(
        "2012-2018", 14, 69, 3, 43, -0.4089026915, 0.9992107844,
        "NO_POSITIVE_DIRECTION",
    )
    ng_diag = _window(
        "2019-2021", 10, 25, 8, 11, 0.36, 0.0579600229,
        "NO_SUPPORT_UNDER_PREREG",
    )
    return {
        "identity": "QORE_FUTURES_A_EIA_FRONT_RANK_PROSPECTIVE_V1",
        "preregistered_hypothesis_count": 2,
        "source_SHA256": dict(gate.SOURCE_SHA),
        "scope": "monthly_first_common_day_signal_2_day_embargo_to_5_day_reference_change",
        "dev": "2012-2018",
        "diag": "2019-2021",
        "holdout_2022_2024": "SEALED_NO_VALUES_LOADED",
        "forward_reference_price_change_not_executable_roll_net": True,
        "market_data_budget_USD": 0,
        "trading_orders": 0,
        "trader_certified": 0,
        "full_source_ready_for_6_roots": False,
        "fx_holdout_touched": False,
        "results": [
            {
                "root": "WTI",
                "months_audit": {
                    "eligible_months": 120,
                    "not_enough_same_month_observations": 0,
                    "spread_ties": 0,
                    "outcome_ties": 1,
                    "valid_one_per_month": 119,
                },
                "dev": wti_dev,
                "diag": wti_diag,
                "decision": "NO_POSITIVE_DIRECTION",
                "is_tradable_edge_certified": False,
            },
            {
                "root": "NG",
                "months_audit": {
                    "eligible_months": 120,
                    "not_enough_same_month_observations": 0,
                    "spread_ties": 2,
                    "outcome_ties": 0,
                    "valid_one_per_month": 118,
                },
                "dev": ng_dev,
                "diag": ng_diag,
                "decision": "NO_POSITIVE_DIRECTION",
                "is_tradable_edge_certified": False,
            },
        ],
    }


class TestQoreResearchTraderLabScientificHandoff(unittest.TestCase):
    def test_exact_fisher_hand_calculated(self) -> None:
        self.assertAlmostEqual(gate._one_sided_fisher(3, 0, 0, 3), 0.05)
        self.assertAlmostEqual(gate._one_sided_fisher(0, 3, 3, 0), 1.0)

    def test_actual_counts_bridge_to_research_without_admitting_trader(self) -> None:
        witness = gate.build_handoff_receipt(fixture_from_original_actions_log())
        self.assertEqual(witness.qore_research_classification, "NO_SUPPORT_UNDER_PREREG")
        self.assertEqual(witness.cibo_research_contract_stage, "experiment")
        self.assertEqual(witness.trader_lab_state, "draft")
        self.assertEqual(witness.trader_lab_first_mandatory_stage, "research")
        self.assertFalse(witness.trader_lab_stage_evidence_produced)
        self.assertFalse(witness.demo_eligible)
        self.assertFalse(witness.execution_authority)
        self.assertFalse(witness.has_economic_returns_or_fills)
        self.assertFalse(witness.fresh_holdout_consumed)
        self.assertEqual(dict(witness.result_by_root), {
            "WTI": "NO_POSITIVE_DIRECTION",
            "NG": "NO_POSITIVE_DIRECTION",
        })

    def test_shuffled_root_order_keeps_fingerprint(self) -> None:
        orig = fixture_from_original_actions_log()
        shuffled = copy.deepcopy(orig)
        shuffled["results"].reverse()
        # Report JSON byte digest preserves source list order; classification must be stable.
        left = gate.build_handoff_receipt(orig)
        right = gate.build_handoff_receipt(shuffled)
        self.assertEqual(left.result_by_root, right.result_by_root)
        self.assertNotEqual(left.scientific_receipt_sha256, right.scientific_receipt_sha256)

    def test_forged_fisher_p_rejected(self) -> None:
        data = fixture_from_original_actions_log()
        data["results"][1]["diag"]["one_sided_fisher_p"] = 0.0001
        with self.assertRaisesRegex(ValueError, "TAMPERED_FISHER_P"):
            gate.build_handoff_receipt(data)

    def test_forged_positive_probability_rejected(self) -> None:
        data = fixture_from_original_actions_log()
        data["results"][0]["dev"]["delta_probability_up"] = 0.90
        with self.assertRaisesRegex(ValueError, "TAMPERED_DELTA"):
            gate.build_handoff_receipt(data)

    def test_forged_significance_decision_rejected(self) -> None:
        data = fixture_from_original_actions_log()
        data["results"][0]["diag"]["decision"] = "PRELIMINARY_PREREG_WINDOW_PASS"
        with self.assertRaisesRegex(ValueError, "TAMPERED_WINDOW_DECISION"):
            gate.build_handoff_receipt(data)

    def test_forged_trader_certification_rejected(self) -> None:
        data = fixture_from_original_actions_log()
        data["trader_certified"] = 1
        with self.assertRaisesRegex(ValueError, "CONTRADICTS_FROZEN_PROTOCOL"):
            gate.build_handoff_receipt(data)

    def test_hiding_holdout_opening_rejected(self) -> None:
        data = fixture_from_original_actions_log()
        data["holdout_2022_2024"] = "CONSUMED"
        with self.assertRaisesRegex(ValueError, "CONTRADICTS_FROZEN_PROTOCOL"):
            gate.build_handoff_receipt(data)

    def test_source_replacement_rejected(self) -> None:
        data = fixture_from_original_actions_log()
        data["source_SHA256"]["NG_F2"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "UNVERIFIED_SOURCE_DATA_HASH"):
            gate.build_handoff_receipt(data)

    def test_hidden_extra_prediction_or_sharpe_rejected(self) -> None:
        data = fixture_from_original_actions_log()
        data["sharpe"] = 3.2
        with self.assertRaisesRegex(ValueError, "SCHEMA_ENVELOPE"):
            gate.build_handoff_receipt(data)

    def test_swap_or_repeat_root_rejected(self) -> None:
        data = fixture_from_original_actions_log()
        data["results"][1]["root"] = "WTI"
        with self.assertRaisesRegex(ValueError, "ROOT_SWAP_OR_DUPLICATION"):
            gate.build_handoff_receipt(data)

    def test_raise_minimum_delta_after_outcomes_rejected(self) -> None:
        data = fixture_from_original_actions_log()
        data["results"][1]["diag"]["minimum_positive_delta"] = 0.2
        with self.assertRaisesRegex(ValueError, "PREREG_THRESHOLD_MUTATED"):
            gate.build_handoff_receipt(data)

    def test_fill_count_tampering_rejected(self) -> None:
        data = fixture_from_original_actions_log()
        data["results"][0]["dev"]["up_backwardation"] = 11
        with self.assertRaisesRegex(ValueError, "INVALID_CONTINGENCY_COUNTS"):
            gate.build_handoff_receipt(data)

    def test_forged_months_rejected(self) -> None:
        data = fixture_from_original_actions_log()
        data["results"][1]["months_audit"]["eligible_months"] = 119
        with self.assertRaisesRegex(ValueError, "MONTH_AUDIT_INCONSISTENT"):
            gate.build_handoff_receipt(data)


if __name__ == "__main__":
    unittest.main()
