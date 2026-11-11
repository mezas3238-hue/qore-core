"""No-data synthetic fail-closed source contracts for seven real-family reports."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from research.crt_r4a_holdout.aggregate_seven_family_events import (
    ATLAS,
    FAMILIES,
    aggregate,
)
from research.crt_r4a_holdout.runner import SYMBOLS
from research.crt_r4a_holdout.seven_family_contract import Family

ALIASES = {"USTEC": "NAS100", "US500": "SP500"}


def fixture(symbol: str) -> dict:
    original = ALIASES.get(symbol, symbol)
    counts = {
        f.value: 0 for f in Family
    }
    counts[Family.TWO_C_MSS_C2.value] = 2
    counts[Family.TWO_C_MSS_C3.value] = 1
    counts[Family.TRUE_3C.value] = 1
    counts[Family.INSIDE_RETURN.value] = 1
    counts[Family.MULTI4.value] = 1
    counts[Family.M15_RETEST.value] = 2
    return {
        "symbol": original,
        "provider_cohort": (
            "ATLAS_DEMO_BROKER_UNVERIFIED"
            if symbol in ATLAS else "ICMARKETS_DEMO_CONFIRMED"
        ),
        "status": "INTEGRATED_RESEARCH_DETECTOR_NOT_PINE_PARITY",
        "seven_families_registered": 7,
        "family_signals_integrated": 7,
        "seven_family_research_event_counts": counts,
        "events_a": 3, "events_b": 1, "events_total": 4,
        "secondary_family_own_mss_audit": {
            "family_events": {
                Family.INSIDE_RETURN.value: 1,
                Family.MULTI4.value: 1,
                Family.MULTIN.value: 0,
            },
            "total_extra_mss15_events": 2,
        },
        "secondary_family_geometry_audit": {
            "family_geometry_event_counts": {
                Family.M15_RETEST.value: 2
            }
        },
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
        "source_m5_rows": 149000,
        "stats": {"m5_processed": 149000},
        "events_per_year_model": {
            "2024_A_2C_MSS15": 2, "2025_A_2C_MSS15": 1,
            "2024_B_TRUE3C_MSS5": 1
        },
    }


class SevenAggregate(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        for symbol in SYMBOLS:
            if symbol == "BTCUSD":
                continue
            data = fixture(symbol)
            folder = self.root / f"qore-crt-r4a-seven-{data['symbol']}"
            folder.mkdir()
            (folder / "integrated.json").write_text(
                json.dumps(data), encoding="utf-8"
            )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def replace(self, canonical: str, **changes: object) -> None:
        original = ALIASES.get(canonical, canonical)
        path = (
            self.root / f"qore-crt-r4a-seven-{original}"
            / "integrated.json"
        )
        current = json.loads(path.read_text(encoding="utf-8"))
        current.update(changes)
        path.write_text(json.dumps(current), encoding="utf-8")

    def test_01_exact_seven_models_and_33_sources(self) -> None:
        report, md = aggregate(self.root)
        self.assertEqual(len(FAMILIES), 7)
        self.assertEqual(len(report["by_symbol"]), 33)
        self.assertEqual(report["totals"]["atlas_not_ic_certified"], 12)
        self.assertIn("Siete familias", md)

    def test_02_seven_total_is_not_order_count(self) -> None:
        report, _ = aggregate(self.root)
        total = report["totals"]
        self.assertEqual(total["family_event_sum_not_unique_trades"], 264)
        self.assertEqual(total["broker_orders_executed"], 0)
        self.assertIsNone(report["broker_profit_factor"])
        self.assertIsNone(report["broker_net_pnl"])

    def test_03_missing_original_market_blocked(self) -> None:
        p = self.root / "qore-crt-r4a-seven-USDCHF" / "integrated.json"
        p.unlink()
        with self.assertRaisesRegex(ValueError, "33 independent"):
            aggregate(self.root)

    def test_04_misnamed_original_feed_blocked(self) -> None:
        self.replace("EURUSD", symbol="USDCHF")
        with self.assertRaisesRegex(ValueError, "identity"):
            aggregate(self.root)

    def test_05_duplicate_or_fake_btc_blocked(self) -> None:
        self.replace("USDCHF", symbol="BTCUSD")
        with self.assertRaisesRegex(ValueError, "identity"):
            aggregate(self.root)

    def test_06_eighth_model_or_unknown_bit_blocked(self) -> None:
        data = fixture("USDCHF")
        data["seven_family_research_event_counts"]["2C_EXPANSION"] = 1
        self.replace(
            "USDCHF",
            seven_family_research_event_counts=data[
                "seven_family_research_event_counts"
            ],
        )
        with self.assertRaisesRegex(ValueError, "seven family IDs"):
            aggregate(self.root)

    def test_07_base_2c_c2_c3_sum_required(self) -> None:
        self.replace("USDCHF", events_a=99)
        with self.assertRaisesRegex(ValueError, "base event ownership"):
            aggregate(self.root)

    def test_08_owned_multi_mss_cannot_borrow_other_cycle(self) -> None:
        data = fixture("USDCHF")
        data["secondary_family_own_mss_audit"]["family_events"][
            Family.MULTI4.value
        ] = 3
        self.replace(
            "USDCHF", secondary_family_own_mss_audit=data[
                "secondary_family_own_mss_audit"
            ],
        )
        with self.assertRaisesRegex(ValueError, "MSS provenance"):
            aggregate(self.root)

    def test_09_retest_requires_parent_source(self) -> None:
        self.replace(
            "USDCHF",
            secondary_family_geometry_audit={
                "family_geometry_event_counts": {
                    Family.M15_RETEST.value: 1
                }
            },
        )
        with self.assertRaisesRegex(ValueError, "parent CRT"):
            aggregate(self.root)

    def test_10_false_pine_parity_blocked(self) -> None:
        self.replace("USDCHF", full_pine_f_engine_parity=True)
        with self.assertRaisesRegex(ValueError, "false"):
            aggregate(self.root)

    def test_11_false_holdout_virginity_blocked(self) -> None:
        self.replace("USDCHF", replay_period_used="2024_2025_UNSEEN")
        with self.assertRaisesRegex(ValueError, "unverified"):
            aggregate(self.root)

    def test_12_false_broker_trades_blocked(self) -> None:
        self.replace("USDCHF", trades_executed=1)
        with self.assertRaisesRegex(ValueError, "unverified"):
            aggregate(self.root)

    def test_13_atlas_cannot_impersonate_ic_markets(self) -> None:
        self.replace(
            "USTEC",
            provider_cohort="ICMARKETS_DEMO_CONFIRMED",
        )
        with self.assertRaisesRegex(ValueError, "provenance"):
            aggregate(self.root)

    def test_14_bad_source_m5_checksum_guard(self) -> None:
        self.replace("USDCHF", year_2024_2025_SHA256_verified=False)
        with self.assertRaisesRegex(ValueError, "unverified"):
            aggregate(self.root)

    def test_15_false_secondary_mss_total_rejected(self) -> None:
        data = fixture("USDCHF")
        data["secondary_family_own_mss_audit"][
            "total_extra_mss15_events"
        ] = 777
        self.replace(
            "USDCHF",
            secondary_family_own_mss_audit=data[
                "secondary_family_own_mss_audit"
            ],
        )
        with self.assertRaisesRegex(ValueError, "secondary owned"):
            aggregate(self.root)

    def test_16_no_economic_certification_claim(self) -> None:
        report, _ = aggregate(self.root)
        for key in (
            "full_pine_engine_parity_proven",
            "virgin_holdout",
            "real_trading_authorized",
        ):
            self.assertIs(report[key], False)


if __name__ == "__main__":
    unittest.main(verbosity=2)
