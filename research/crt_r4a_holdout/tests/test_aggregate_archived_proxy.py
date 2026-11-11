"""Synthetic contracts only. Never treat fixtures as historical QORE CRT results."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from research.crt_r4a_holdout.aggregate_archived_proxy import MODELS, aggregate
from research.crt_r4a_holdout.runner import SYMBOLS

ATLAS = {
    "AUDJPY", "GBPUSD", "GBPJPY", "XAUUSD", "USTEC", "US500",
    "US30", "AUDUSD", "USDCAD", "USDJPY", "EURUSD", "XAGUSD",
}


def fixture(symbol: str) -> dict:
    return {
        "symbol": symbol,
        "cohort": (
            "ATLAS_DEMO_BROKER_UNVERIFIED"
            if symbol in ATLAS else "ICMARKETS_DEMO_CONFIRMED"
        ),
        "status": "REAL_OHLC_EXPLORATORY_PROXY_ONLY",
        "period": "2024-01-01/2025-12-31",
        "native_M5_rows": 149_000,
        "closed_H4": 1_600,
        "incomplete_H4": 12,
        "source_sha256": "2024_AND_2025_VERIFIED",
        "is_Pine_parity_100pct": False,
        "costs_included": False,
        "holdout_certified": False,
        "portfolio_certified": False,
        "signals": {
            "A_2C_STRUCTURAL": 16,
            "A_MSS15_PROXY_CONFIRMED": 12,
            "B_TRUE3C_STRUCTURAL": 4,
            "B_MSS5_PROXY_CONFIRMED": 2,
        },
        "two_hypotheses": {
            model: {
                "closed_trades": 2,
                "gross_net_R_unscaled": -0.3,
                "gross_win_rate": 0.5,
                "gross_profit_factor": 0.8,
            }
            for model in MODELS
        },
    }


class AggregationContract(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        for sym in SYMBOLS:
            if sym == "BTCUSD":
                continue
            folder = self.root / f"crt-r4a-proxy-summary-{sym}"
            folder.mkdir()
            (folder / "crt-proxy-summary.json").write_text(
                json.dumps(fixture(sym)), encoding="utf-8"
            )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def replace(self, target: str, **changes: object) -> None:
        path = (
            self.root / f"crt-r4a-proxy-summary-{target}"
            / "crt-proxy-summary.json"
        )
        current = json.loads(path.read_text(encoding="utf-8"))
        current.update(changes)
        path.write_text(json.dumps(current), encoding="utf-8")

    def test_01_fixture_exactly_33_unique_original_sources(self) -> None:
        self.assertEqual(len(ATLAS), 12)
        self.assertEqual(len(SYMBOLS), 34)
        self.assertEqual(len(list(self.root.rglob("crt-proxy-summary.json"))), 33)

    def test_02_aggregate_has_all_33_and_two_models(self) -> None:
        result, markdown = aggregate(self.root)
        self.assertEqual(len(result["by_symbol"]), 33)
        self.assertEqual(set(result["pooled"]), set(MODELS))
        self.assertEqual(result["pooled"][MODELS[0]]["trades"], 66)
        self.assertEqual(result["totals"]["native_M5"], 149_000 * 33)
        self.assertIn("NO CERTIFICADO", markdown.upper())

    def test_03_portfolio_and_holdout_must_not_be_certified(self) -> None:
        result, _ = aggregate(self.root)
        self.assertIs(result["certified_holdout"], False)
        self.assertIs(result["certified_pine_parity"], False)
        self.assertIs(result["costs_included"], False)
        self.assertIs(result["unseen_holdout_proven"], False)

    def test_04_reject_missing_market(self) -> None:
        (self.root / "crt-r4a-proxy-summary-EURUSD" /
         "crt-proxy-summary.json").unlink()
        with self.assertRaises(ValueError):
            aggregate(self.root)

    def test_05_reject_wrong_symbol_filename(self) -> None:
        self.replace("EURUSD", symbol="USDCHF")
        with self.assertRaisesRegex(ValueError, "artifact name"):
            aggregate(self.root)

    def test_06_reject_false_parity_certification(self) -> None:
        self.replace("EURUSD", is_Pine_parity_100pct=True)
        with self.assertRaisesRegex(ValueError, "false certification"):
            aggregate(self.root)

    def test_07_reject_false_holdout_certification(self) -> None:
        self.replace("EURUSD", holdout_certified=True)
        with self.assertRaisesRegex(ValueError, "false certification"):
            aggregate(self.root)

    def test_08_reject_wrong_original_sha_status(self) -> None:
        self.replace("EURUSD", source_sha256="UNVERIFIED")
        with self.assertRaisesRegex(ValueError, "integrity"):
            aggregate(self.root)

    def test_09_reject_wrong_evaluation_period(self) -> None:
        self.replace("EURUSD", period="2025-01-01/2025-12-31")
        with self.assertRaisesRegex(ValueError, "period"):
            aggregate(self.root)

    def test_10_reject_missing_model(self) -> None:
        only_a = fixture("EURUSD")["two_hypotheses"][MODELS[0]]
        self.replace("EURUSD", two_hypotheses={MODELS[0]: only_a})
        with self.assertRaisesRegex(ValueError, "model missing"):
            aggregate(self.root)

    def test_11_reject_inadequate_source_window(self) -> None:
        self.replace("EURUSD", native_M5_rows=100)
        with self.assertRaisesRegex(ValueError, "insufficient"):
            aggregate(self.root)

    def test_13_hypothetical_cost_grid_is_not_broker_net(self) -> None:
        result, markdown = aggregate(self.root)
        self.assertIs(result["cost_sensitivity_is_hypothetical_only"], True)
        self.assertEqual(
            tuple(result["cost_stress_R_per_trade"]),
            (0.0, 0.02, 0.05, 0.10, 0.20),
        )
        for model in MODELS:
            rec = result["pooled"][model]
            self.assertEqual(rec["trades"], 66)
            self.assertAlmostEqual(rec["gross_mean_r"], -0.15)
            stress = rec["hypothetical_cost_stress_not_broker_net"]
            self.assertAlmostEqual(
                stress["0.05R"]["hypothetical_mean_R"], -0.20
            )
            self.assertAlmostEqual(
                stress["0.20R"]["hypothetical_sum_R_not_capital"], -23.1
            )
            self.assertEqual(
                rec["gross_break_even_cost_R_per_closed_trade"], 0.0
            )
        self.assertIn("NO cotizaciones broker", markdown)

    def test_14_reject_fabricated_net_cost_flag(self) -> None:
        self.replace("EURUSD", costs_included=True)
        with self.assertRaisesRegex(ValueError, "false certification"):
            aggregate(self.root)

    def test_15_original_atlas_indices_map_without_losing_provenance(self) -> None:
        for canonical, source in (("USTEC", "NAS100"), ("US500", "SP500")):
            original = self.root / f"crt-r4a-proxy-summary-{canonical}"
            target = self.root / f"crt-r4a-proxy-summary-{source}"
            original.rename(target)
            path = target / "crt-proxy-summary.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            data["symbol"] = source
            path.write_text(json.dumps(data), encoding="utf-8")
        result, _ = aggregate(self.root)
        by_symbol = {item["symbol"]: item for item in result["by_symbol"]}
        self.assertEqual(by_symbol["USTEC"]["source_symbol"], "NAS100")
        self.assertEqual(by_symbol["US500"]["source_symbol"], "SP500")

    def test_16_atlas_alias_must_not_impersonate_ic_provider(self) -> None:
        original = self.root / "crt-r4a-proxy-summary-USTEC"
        target = self.root / "crt-r4a-proxy-summary-NAS100"
        original.rename(target)
        path = target / "crt-proxy-summary.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["symbol"] = "NAS100"
        data["cohort"] = "ICMARKETS_DEMO_CONFIRMED"
        path.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Atlas source provenance"):
            aggregate(self.root)

    def test_12_reject_wrong_provider_cohort(self) -> None:
        self.replace("EURUSD", cohort="ICMARKETS_DEMO_CONFIRMED")
        with self.assertRaisesRegex(ValueError, "cohorts mismatch"):
            aggregate(self.root)


if __name__ == "__main__":
    unittest.main(verbosity=2)
