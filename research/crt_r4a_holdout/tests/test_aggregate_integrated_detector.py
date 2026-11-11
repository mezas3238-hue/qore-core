"""Synthetic-only 33 market integrated research event aggregation contracts."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from research.crt_r4a_holdout.aggregate_integrated_detector import aggregate
from research.crt_r4a_holdout.runner import SYMBOLS

ATLAS = {
    "AUDJPY", "GBPUSD", "GBPJPY", "XAUUSD", "USTEC", "US500",
    "US30", "AUDUSD", "USDCAD", "USDJPY", "EURUSD", "XAGUSD",
}
ALIASES = {"USTEC": "NAS100", "US500": "SP500"}


def fixture(canonical: str) -> dict:
    raw = ALIASES.get(canonical, canonical)
    return {
        "symbol": raw, "family": "index" if canonical in (
            "USTEC", "US500", "US30"
        ) else "forex",
        "m5_phase": 0, "source_m5_rows": 149000,
        "events_a": 2, "events_b": 1, "events_total": 3,
        "status": "INTEGRATED_RESEARCH_DETECTOR_NOT_PINE_PARITY",
        "provider_cohort": (
            "ATLAS_DEMO_BROKER_UNVERIFIED" if canonical in ATLAS
            else "ICMARKETS_DEMO_CONFIRMED"
        ),
        "is_original_pine_f_engine": False,
        "holdout_certified": False,
        "trading_orders_permitted": False,
        "full_pine_f_engine_parity": False,
        "mss_with_exact_provider_phase_parity": False,
        "bid_ask_costs_included": False,
        "real_money_authorized": False,
        "trades_executed": 0,
        "year_2024_2025_SHA256_verified": True,
        "replay_period_used": "2024_2025_ALREADY_RESEARCHED",
        "stats": {"m5_processed": 149000},
        "events_per_year_model": {
            "2024_A_2C_MSS15": 1,
            "2024_B_TRUE3C_MSS5": 1,
            "2025_A_2C_MSS15": 1,
        },
    }


class AggregateCausal(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        for c in SYMBOLS:
            if c == "BTCUSD":
                continue
            record = fixture(c)
            folder = self.root / f"qore-crt-r4a-integrated-{record['symbol']}"
            folder.mkdir()
            (folder / "integrated.json").write_text(
                json.dumps(record), encoding="utf-8"
            )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def replace(self, canonical: str, **changes: object) -> None:
        raw = ALIASES.get(canonical, canonical)
        path = self.root / f"qore-crt-r4a-integrated-{raw}" / "integrated.json"
        r = json.loads(path.read_text(encoding="utf-8"))
        r.update(changes)
        path.write_text(json.dumps(r), encoding="utf-8")

    def test_01_fixed_market_count_and_correct_aliases(self) -> None:
        summary, _ = aggregate(self.root)
        self.assertEqual(len(summary["by_symbol"]), 33)
        names = {r["canonical_symbol"] for r in summary["by_symbol"]}
        self.assertEqual(names, set(SYMBOLS) - {"BTCUSD"})
        self.assertEqual(summary["totals"]["atlas_not_ic_certified"], 12)

    def test_02_events_sum_both_models_without_trades(self) -> None:
        result, _ = aggregate(self.root)
        self.assertEqual(result["totals"]["events_a_2c_mss15"], 66)
        self.assertEqual(result["totals"]["events_b_true3c_mss5"], 33)
        self.assertEqual(result["totals"]["events_total"], 99)
        self.assertEqual(result["totals"]["trades_executed"], 0)

    def test_03_never_claims_pine_parity_or_economic_backtest(self) -> None:
        report, md = aggregate(self.root)
        self.assertIs(report["exact_pine_event_parity"], False)
        self.assertIs(report["broker_net_pnl_measured"], False)
        self.assertIs(report["virgin_holdout"], False)
        self.assertIn("sin operaciones ni rentabilidad", md)

    def test_04_missing_source_fails_closed(self) -> None:
        (self.root / "qore-crt-r4a-integrated-USDCHF" /
         "integrated.json").unlink()
        with self.assertRaisesRegex(ValueError, "33 historical"):
            aggregate(self.root)

    def test_05_wrong_canonical_symbol_cannot_impersonate_another(self) -> None:
        self.replace("EURUSD", symbol="USDCHF")
        with self.assertRaisesRegex(ValueError, "misnamed"):
            aggregate(self.root)

    def test_06_forged_real_trade_count_rejected(self) -> None:
        self.replace("EURUSD", trades_executed=1)
        with self.assertRaisesRegex(ValueError, "trading orders"):
            aggregate(self.root)

    def test_07_forged_parity_rejected(self) -> None:
        self.replace("USDCHF", full_pine_f_engine_parity=True)
        with self.assertRaisesRegex(ValueError, "false certification"):
            aggregate(self.root)

    def test_08_forged_fresh_holdout_rejected(self) -> None:
        self.replace("USDCHF", replay_period_used="2024_2025_UNSEEN")
        with self.assertRaisesRegex(ValueError, "burned"):
            aggregate(self.root)

    def test_09_event_count_reconciliation_required(self) -> None:
        self.replace("USDCHF", events_total=55)
        with self.assertRaisesRegex(ValueError, "reconciled"):
            aggregate(self.root)

    def test_10_annual_event_count_reconciliation_required(self) -> None:
        self.replace(
            "USDCHF",
            events_per_year_model={"2024_A_2C_MSS15": 1}
        )
        with self.assertRaisesRegex(ValueError, "year/model"):
            aggregate(self.root)

    def test_11_index_alias_cannot_fake_ic_provider(self) -> None:
        self.replace("USTEC", provider_cohort="ICMARKETS_DEMO_CONFIRMED")
        with self.assertRaisesRegex(ValueError, "impersonation"):
            aggregate(self.root)

    def test_12_forged_data_sha_rejected(self) -> None:
        self.replace("USDCHF", year_2024_2025_SHA256_verified=False)
        with self.assertRaisesRegex(ValueError, "SHA"):
            aggregate(self.root)


if __name__ == "__main__":
    unittest.main(verbosity=2)
