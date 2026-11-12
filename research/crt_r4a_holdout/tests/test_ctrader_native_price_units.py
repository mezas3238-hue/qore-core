"""Provider-native OHLC scale must not become fake certified broker profits."""
from __future__ import annotations

import unittest
from decimal import Decimal

from research.crt_r4a_holdout.ctrader_native_price_units import (
    VerifiedUnitMetadata,
    convert_structural_geometry,
    native_to_quote,
)

D = Decimal
SHA = "e" * 64


def meta(
    symbol: str = "AUDCAD", *, cohort: str = "ICMARKETS_DEMO_CONFIRMED",
    digits: int = 5, tick: str = "0.00001",
) -> VerifiedUnitMetadata:
    return VerifiedUnitMetadata(
        symbol, cohort, 301, digits, D(tick), SHA
    )


def raw() -> dict:
    return {
        "source_event_id": "AUDCAD|CRT|SOURCE",
        "symbol": "AUDCAD",
        "provider_cohort": "ICMARKETS_DEMO_CONFIRMED",
        "economic_ready": False,
        "broker_orders_executed": 0,
        "geometry": {
            "c1_high": "90577.0",
            "c1_low": "90150.0",
            "sweep_high": "90431.0",
            "sweep_low": "90142.0",
        },
    }


class CTraderPriceUnitsQA(unittest.TestCase):
    def test_01_audcad_source_integer_to_real_decimal(self) -> None:
        self.assertEqual(
            native_to_quote("90577.0", metadata=meta()), D("0.90577")
        )

    def test_02_jpy_symbol_digits_are_explicit(self) -> None:
        self.assertEqual(
            native_to_quote(
                "14167200.0",
                metadata=meta("USDJPY", digits=3, tick="0.001"),
            ),
            D("141.672"),
        )

    def test_03_gold_quoted_price_not_integer_scale(self) -> None:
        self.assertEqual(
            native_to_quote(
                "203466000.0",
                metadata=meta("XAUUSD", digits=2, tick="0.01"),
            ),
            D("2034.66"),
        )

    def test_04_index_with_explicit_tick_metadata(self) -> None:
        self.assertEqual(
            native_to_quote(
                "1656000000.0",
                metadata=meta("USTEC", digits=1, tick="0.1"),
            ),
            D("16560.0"),
        )

    def test_05_reject_unfounded_quote_tick_rounding(self) -> None:
        with self.assertRaisesRegex(ValueError, "aligned"):
            native_to_quote(
                "90577.0",
                metadata=meta(tick="0.0001"),
            )

    def test_06_no_assumed_tick_from_symbol_ticker(self) -> None:
        with self.assertRaisesRegex(ValueError, "provenance"):
            VerifiedUnitMetadata(
                "AUDCAD", "ICMARKETS_DEMO_CONFIRMED", 301, 5,
                D("0"), SHA,
            )

    def test_07_invalid_symbol_metadata_hash_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "provenance"):
            VerifiedUnitMetadata(
                "AUDCAD", "ICMARKETS_DEMO_CONFIRMED", 301, 5,
                D("0.00001"), "not-a-hash",
            )

    def test_08_raw_nonintegral_price_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "integer units"):
            native_to_quote("90577.5", metadata=meta())

    def test_09_negative_and_nan_prices_rejected(self) -> None:
        for value in ("-1", "NaN", "Infinity", "0"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "integer units"):
                    native_to_quote(value, metadata=meta())

    def test_10_symbol_mismatch_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "identity mismatch"):
            convert_structural_geometry(
                raw(), metadata=meta("USDJPY", digits=3, tick="0.001")
            )

    def test_11_converted_price_is_not_a_bid_ask_or_trade_claim(self) -> None:
        result = convert_structural_geometry(raw(), metadata=meta())
        self.assertEqual(
            result["converted_quote_geometry"]["c1_high"], "0.90577"
        )
        self.assertEqual(
            result["raw_native_price_geometry"]["c1_high"], "90577.0"
        )
        self.assertFalse(result["economic_ready"])
        self.assertFalse(result["bid_ask_historical_evidence"])
        self.assertFalse(result["pine_f_engine_parity_certified"])
        self.assertEqual(result["broker_orders_executed"], 0)

    def test_12_unknown_raw_geometry_field_rejected(self) -> None:
        event = raw()
        event["geometry"]["future_target_price"] = "250000"
        with self.assertRaisesRegex(ValueError, "unknown"):
            convert_structural_geometry(event, metadata=meta())

    def test_13_no_source_digits_inference_from_raw_integer(self) -> None:
        with self.assertRaisesRegex(TypeError, "missing"):
            native_to_quote("90577.0")  # type: ignore[call-arg]

    def test_14_invalid_tick_finer_than_digits(self) -> None:
        with self.assertRaisesRegex(ValueError, "finer"):
            meta(digits=2, tick="0.001")


if __name__ == "__main__":
    unittest.main(verbosity=2)
