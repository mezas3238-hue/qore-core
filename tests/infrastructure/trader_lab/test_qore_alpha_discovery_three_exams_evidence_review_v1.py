"""Adversarial synthetic artifact fixtures for QORE closed-experiment decision review."""
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import qore_alpha_discovery_three_exams_evidence_review_v1 as a


def _write(root: Path, name: str, content: str) -> None:
    (root / name).write_text(content, encoding="utf-8")


def _write_receipted(root: Path, name: str, doc: dict) -> None:
    compact = json.dumps(doc, sort_keys=True, separators=(",", ":"), allow_nan=False)
    payload = dict(doc)
    payload["receipt_sha256"] = hashlib.sha256(compact.encode()).hexdigest()
    _write(root, name, json.dumps(payload))


def _signed(root: Path, content_name: str, all_files: list[str], ledger: str) -> None:
    lines = [
        hashlib.sha256((root / file).read_bytes()).hexdigest() + "  " + file
        for file in all_files
    ]
    _write(root, ledger, "\n".join(lines) + "\n")


def _tom_doc() -> dict:
    symbols = {}
    for symbol, gross in (("SP500", -3.08), ("US30", -11.94), ("NAS100", -0.21)):
        def part(n: int, ret: float, verdict: str) -> dict:
            return {
                "months": n, "adequate_months": True,
                "gross_TOM_mean_bps": ret,
                "gross_midmonth_control_mean_bps": ret - 10,
                "paired_excess_mean_bps": 10.0,
                "gross_TOM_after_hypothetical_RT_cost_bps": {
                    str(cost): ret - cost for cost in (5, 10, 20)
                },
                "bootstrap_lower_excess_bps": -100.0,
                "verdict": verdict,
            }
        symbols[symbol] = {
            "source_all_11_years_SHA_verified": True,
            "prices_post_2024_09_17_read": False,
            "historical_bidask_net_calculated": False,
            "dev": part(70, 30.0, "NO_SUPPORT" if symbol == "SP500" else "PRELIMINARY_SUPPORT"),
            "diag": part(23, gross, "NO_SUPPORT" if symbol != "NAS100" else "PRELIMINARY_SUPPORT"),
        }
    return {
        "prereg_sha": a.TOM_PREREG,
        "verdict": "NO_SUPPORT_UNDER_PREREG",
        "next_action": "CLOSE_H_TOM_1_NO_PARAMETER_SEARCH",
        "holdout_2024_09_17_plus_consumed": False,
        "broker_historical_net_executed": False,
        "edge_certified": False, "traders_certified": 0,
        "symbols": symbols,
    }


def _e3_doc() -> dict:
    return {
        "identity": "QORE_NATIVE_E3_POSTHOC_SEVEN_METHOD_MULTIWEEK_SHRINKAGE_V1",
        "source_33_signed_market_witnesses": 33,
        "source_7_methods_per_market": 7,
        "total_cells_source": 231,
        "source_e1_code_head": "dfe78f115957a40f4188c30e78bd7f88c2ce6c42",
        "original_2024_plus_OHLC_unopened": True, "traders_certified": 0,
        "cross_period_seven_method_descriptive_screen": [
            {
                "method_id": str(n),
                "positive_gross_and_delta_both_periods_all_L": False,
                "BH_q_below_10pct_both_periods_all_L": False,
            }
            for n in range(7)
        ],
    }


def _cftc_doc() -> dict:
    return {
        "prereg_commit": a.CFTC_PREREG,
        "final_scientific_verdict": "CLOSED_INCONCLUSIVE_LOW_POWER",
        "holdout_2022_2024_opened": False,
        "native_futures_execution_data_available": False,
        "profit_factor_or_net_pnl_calculated": False,
        "trader_certified": False,
        "roots": {
            root: {
                window: {
                    "decision": "INCONCLUSIVE_INSUFFICIENT_INDEPENDENT_EXTREMES",
                    "exact_one_sided_p": None, "accuracy": None,
                    "n_independent_events": n,
                    "minimum_events": 8,
                }
                for window, n in (("dev", 7 if root == "WTI" else 5),
                                  ("diag", 1 if root == "WTI" else 3))
            }
            for root in a.CFTC_MARKETS
        },
    }


class TestPostmortemZeroNewOutcomes(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dir = Path(self.temp.name)
        self.t, self.e, self.c = (
            self.dir / name for name in ("tom", "e3", "cftc")
        )
        for folder in (self.t, self.e, self.c):
            folder.mkdir()
        _write_receipted(self.t, "qore-tom-final-three-index.json", _tom_doc())
        _write(self.t, "exact-code-head-sha.txt", a.TOM_SHA + "\n")
        _signed(
            self.t, "qore-tom-final-three-index.json",
            ["qore-tom-final-three-index.json", "exact-code-head-sha.txt"],
            "SHA256SUMS.txt",
        )
        _write(self.e, "qore-native-e3-seven-method-block-shrinkage-posthoc.json",
               json.dumps(_e3_doc()))
        _write(self.e, "exact-E3-code-head-sha.txt", a.E3_SHA)
        _signed(
            self.e, "qore-native-e3-seven-method-block-shrinkage-posthoc.json",
            ["qore-native-e3-seven-method-block-shrinkage-posthoc.json",
             "exact-E3-code-head-sha.txt"],
            "OUTPUT_SHA256SUMS.txt",
        )
        _write_receipted(
            self.c, "cftc_extreme_z2_final_exam.json", _cftc_doc()
        )

    def test_categories_are_not_conflated(self) -> None:
        report = a.review(self.t, self.e, self.c)
        self.assertEqual(len(report["studies"]), 3)
        self.assertIn("GROSS_IN_DIAGNOSTIC", report["studies"][0]["decision"])
        self.assertIn("NOT_ROBUST", report["studies"][1]["decision"])
        self.assertIn("INSUFFICIENT", report["studies"][2]["decision"])
        self.assertFalse(report["result_is_certification"])
        self.assertFalse(report["new_market_prices_downloaded"])

    def test_cash_gross_negative_even_if_paired_excess_positive(self) -> None:
        report = a._check_tom(self.t)
        self.assertTrue(report["three_of_three_diag_absolute_gross_negative"])
        self.assertTrue(all(
            not v["diag_possible_positive_mean_after_nonnegative_cost"]
            for v in report["gross_per_market"].values()
        ))

    def test_corrupted_tom_sha_fails_closed(self) -> None:
        with (self.t / "qore-tom-final-three-index.json").open("a") as file:
            file.write(" ")
        with self.assertRaisesRegex(a.EvidenceError, "SIGNED_ARTIFACT_CHANGED"):
            a._check_tom(self.t)

    def test_forged_tom_result_with_rehashed_sha_fails_receipt(self) -> None:
        p = self.t / "qore-tom-final-three-index.json"
        doc = json.loads(p.read_text())
        doc["symbols"]["US30"]["diag"]["gross_TOM_mean_bps"] = 300
        _write(self.t, p.name, json.dumps(doc))
        _signed(
            self.t, p.name, [p.name, "exact-code-head-sha.txt"], "SHA256SUMS.txt"
        )
        with self.assertRaisesRegex(a.EvidenceError, "RECEIPT_SHA256"):
            a._check_tom(self.t)

    def test_same_value_positive_tom_diag_requires_scope_update(self) -> None:
        p = self.t / "qore-tom-final-three-index.json"
        doc = json.loads(p.read_text())
        diag = doc["symbols"]["US30"]["diag"]
        diag["gross_TOM_mean_bps"] = 20.0
        diag["gross_midmonth_control_mean_bps"] = 10.0
        diag["gross_TOM_after_hypothetical_RT_cost_bps"] = {
            str(cost): 20.0 - cost for cost in (5, 10, 20)
        }
        del doc["receipt_sha256"]
        _write_receipted(self.t, p.name, doc)
        _signed(
            self.t, p.name, [p.name, "exact-code-head-sha.txt"], "SHA256SUMS.txt"
        )
        with self.assertRaisesRegex(a.EvidenceError, "ALL_THREE_GROSS_NEGATIVE_FALSE"):
            a._check_tom(self.t)

    def test_cftc_insufficient_cannot_be_reinterpreted_as_no_edge(self) -> None:
        x = a._check_cftc(self.c)
        self.assertFalse(x["trading_edge_refuted_universally"])
        self.assertEqual(x["power_splits"]["NG"]["diag"]["independent_effective_episodes"], 3)

    def test_cftc_does_not_invent_pvalue_to_claim_falsification(self) -> None:
        p = self.c / "cftc_extreme_z2_final_exam.json"
        doc = json.loads(p.read_text())
        doc["roots"]["WTI"]["dev"]["exact_one_sided_p"] = 0.9
        del doc["receipt_sha256"]
        _write_receipted(self.c, p.name, doc)
        with self.assertRaisesRegex(a.EvidenceError, "REINTERPRETED"):
            a._check_cftc(self.c)

    def test_one_method_claim_fails_conservatively(self) -> None:
        p = self.e / "qore-native-e3-seven-method-block-shrinkage-posthoc.json"
        doc = json.loads(p.read_text())
        doc["cross_period_seven_method_descriptive_screen"][0][
            "positive_gross_and_delta_both_periods_all_L"
        ] = True
        _write(self.e, p.name, json.dumps(doc))
        _signed(
            self.e, p.name, [p.name, "exact-E3-code-head-sha.txt"],
            "OUTPUT_SHA256SUMS.txt",
        )
        # If the old data *had* a positive method, the review must surface
        # it rather than assert it was zero.
        result = a._check_e3(self.e)
        self.assertEqual(
            result["positive_gross_and_delta_both_periods_all_block_sensitivities"],
            1,
        )


if __name__ == "__main__":
    unittest.main()
