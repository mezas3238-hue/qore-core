"""Synthetic-only unit tests; they are NOT historical holdout outcomes."""
from __future__ import annotations

import csv
import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from research.crt_r4a_holdout.runner import (
    END,
    MODELS,
    PINE_BLOB,
    START,
    SYMBOLS,
    Event,
    Quote,
    read_events,
    read_quotes,
    readiness,
    report_trades,
    simulate_event,
    timestamp,
)


def t(hour: int = 8, minute: int = 0) -> datetime:
    return datetime(2024, 2, 1, hour, minute, tzinfo=UTC)


def example_event(side: str = "LONG", model: str = "B_TRUE3C_MSS5") -> Event:
    if side == "LONG":
        body_open, body_close, c1_high, c1_low, sh, sl, atr = (
            102.0, 104.0, 110.0, 95.0, 106.0, 93.0, 20.0
        )
    else:
        body_open, body_close, c1_high, c1_low, sh, sl, atr = (
            99.0, 97.0, 110.0, 90.0, 115.0, 93.0, 12.0
        )
    return Event(
        "evt1", "EURUSD", model, side, t(5), t(6), t(8), t(8),
        c1_high, c1_low, body_open, body_close, sh, sl, atr,
    )


def q(opened: datetime, bo=103.0, bh=111.0, bl=102.0, bc=108.0,
      ao=103.2, ah=111.2, al=102.2, ac=108.2) -> Quote:
    return Quote(opened, bo, bh, bl, bc, ao, ah, al, ac)


def event_row(**kwargs: str) -> dict[str, str]:
    d = {
        "event_id": "evt1", "symbol": "EURUSD",
        "model": "B_TRUE3C_MSS5", "side": "LONG",
        "sweep_at": "2024-02-01T05:00:00Z",
        "mss_at": "2024-02-01T06:00:00Z",
        "ratified_at": "2024-02-01T08:00:00Z",
        "available_at": "2024-02-01T08:00:00Z",
        "c1_high": "110", "c1_low": "95", "body_open": "102",
        "body_close": "104", "sweep_high": "106",
        "sweep_low": "93", "atr_h4": "20",
    }
    d.update(kwargs)
    return d


class ContractTests(unittest.TestCase):
    def test_01_fixed_34_instruments_unique(self):
        self.assertEqual(len(SYMBOLS), 34)
        self.assertEqual(len(set(SYMBOLS)), 34)

    def test_02_expected_index_and_btc_positions(self):
        self.assertEqual(SYMBOLS[4:8], ("USTEC", "US500", "US30", "BTCUSD"))

    def test_03_fixed_two_model_hypotheses(self):
        self.assertEqual(MODELS, ("A_2C_MSS15", "B_TRUE3C_MSS5"))

    def test_04_pinned_source_git_blob(self):
        self.assertEqual(PINE_BLOB, "693e3f49719e86e2ea0702f7b355af33bd0c4c7c")

    def test_05_exact_24_months(self):
        self.assertEqual(START.isoformat(), "2024-01-01T00:00:00+00:00")
        self.assertEqual(END.isoformat(), "2026-01-01T00:00:00+00:00")

    def test_06_reject_naive_timestamp(self):
        with self.assertRaises(ValueError):
            timestamp("2024-01-01T00:00:00")

    def test_07_normalize_timezone(self):
        self.assertEqual(timestamp("2024-02-01T05:00:00-03:00"), t(8))

    def test_08_event_good(self):
        self.assertEqual(Event.parse(event_row()).available_at, t(8))

    def test_09_event_invalid_model(self):
        with self.assertRaises(ValueError):
            Event.parse(event_row(model="INSIDE_DEMO"))

    def test_10_event_invalid_symbol(self):
        with self.assertRaises(ValueError):
            Event.parse(event_row(symbol="NOT_IC_MARKET"))

    def test_11_event_anticipatory(self):
        with self.assertRaises(ValueError):
            Event.parse(event_row(available_at="2024-02-01T07:55:00Z"))

    def test_12_true3c_mss_after_ratification_rejected(self):
        with self.assertRaises(ValueError):
            Event.parse(event_row(mss_at="2024-02-01T08:05:00Z"))

    def test_13_a_mss_after_ratification_allowed_if_visible(self):
        e = Event.parse(event_row(
            model="A_2C_MSS15", mss_at="2024-02-01T08:15:00Z",
            available_at="2024-02-01T08:15:00Z",
        ))
        self.assertEqual(e.mss_at, t(8, 15))

    def test_14_no_holdout_event_outside_window(self):
        with self.assertRaises(ValueError):
            Event.parse(event_row(available_at="2026-01-01T00:00:00Z"))

    def test_15_reject_duplicate_event_ids(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "events.csv"
            rows = [event_row(), event_row()]
            with path.open("w", encoding="utf-8", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=list(rows[0]))
                w.writeheader()
                w.writerows(rows)
            with self.assertRaises(ValueError):
                read_events(path)

    def test_16_quote_reject_crossed_bid_ask(self):
        row = {
            "opened_at": "2024-02-01T08:00:00Z",
            "bid_open": "103", "bid_high": "111", "bid_low": "102",
            "bid_close": "108", "ask_open": "102",
            "ask_high": "112", "ask_low": "101", "ask_close": "109",
        }
        with self.assertRaises(ValueError):
            Quote.parse(row)

    def test_17_quote_reject_unaligned_m5(self):
        row = {
            "opened_at": "2024-02-01T08:02:00Z",
            "bid_open": "103", "bid_high": "111", "bid_low": "102",
            "bid_close": "108", "ask_open": "103.2",
            "ask_high": "111.2", "ask_low": "102.2", "ask_close": "108.2",
        }
        with self.assertRaises(ValueError):
            Quote.parse(row)

    def test_18_quote_reject_unordered_rows(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "quotes.csv"
            row = {
                "opened_at": "2024-02-01T08:00:00Z",
                "bid_open": "103", "bid_high": "111", "bid_low": "102",
                "bid_close": "108", "ask_open": "103.2",
                "ask_high": "111.2", "ask_low": "102.2", "ask_close": "108.2",
            }
            with path.open("w", encoding="utf-8", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=list(row))
                w.writeheader()
                w.writerow(row)
                w.writerow(row)
            with self.assertRaises(ValueError):
                read_quotes(path)


class ExecutionTests(unittest.TestCase):
    def test_19_long_tp_with_bid_and_costs(self):
        status, trade = simulate_event(
            example_event(), [
                q(t(), bh=106, bl=100, bc=104, ah=106.2, al=102.2, ac=104.2),
                q(t(8, 5)),
            ],
            commission_price=0.3, slippage_price=0.2,
        )
        self.assertEqual(status, "TRADE")
        assert trade is not None
        self.assertEqual(trade.exit_reason, "TP")
        self.assertAlmostEqual(trade.r_net, (110 - 0.2 - 103 - 0.3) / 15)

    def test_20_skip_last_bar_before_available(self):
        status, trade = simulate_event(
            example_event(), [
                q(t(7, 55)),
                q(t(), bh=106, bl=100, bc=104, ah=106.2, al=102.2, ac=104.2),
                q(t(8, 5)),
            ],
            commission_price=0, slippage_price=0,
        )
        self.assertEqual(status, "TRADE")
        assert trade is not None
        self.assertEqual(trade.entered, t())

    def test_21_prefill_stop_ambiguous_cancel_no_profit(self):
        status, trade = simulate_event(
            example_event(), [q(t(), bl=87)],
            commission_price=0, slippage_price=0,
        )
        self.assertEqual(status, "UNFILLED_INVALIDATED_OR_AMBIGUOUS")
        self.assertIsNone(trade)

    def test_22_sl_gap_conservatism(self):
        first = q(t(), bh=106, bl=100, bc=104, ah=106.2, al=102.2, ac=104.2)
        second = q(
            t(8, 5), bo=84, bh=85, bl=82, bc=83,
            ao=84.2, ah=85.2, al=82.2, ac=83.2,
        )
        status, trade = simulate_event(
            example_event(), [first, second],
            commission_price=0, slippage_price=0,
        )
        self.assertEqual(status, "TRADE")
        assert trade is not None
        self.assertEqual(trade.exit_reason, "SL")
        self.assertAlmostEqual(trade.r_net, (84 - 103) / 15)

    def test_23_short_uses_ask_to_exit(self):
        bar = q(
            t(), bo=98, bh=99, bl=89, bc=94,
            ao=98.2, ah=99.2, al=89.2, ac=94.2,
        )
        status, trade = simulate_event(
            example_event("SHORT"), [
                q(t(), bo=98, bh=99, bl=94, bc=95,
                  ao=98.2, ah=99.2, al=94.2, ac=95.2),
                bar.__class__(t(8, 5), bar.bo, bar.bh, bar.bl,
                              bar.bc, bar.ao, bar.ah, bar.al, bar.ac),
            ],
            commission_price=0.2, slippage_price=0.1,
        )
        self.assertEqual(status, "TRADE")
        assert trade is not None
        self.assertEqual(trade.exit_reason, "TP")
        self.assertAlmostEqual(trade.r_net, (98 - 90 - 0.1 - 0.2) / 20)

    def test_24_unfilled_limit_expiry(self):
        bar = q(t(21))
        status, trade = simulate_event(
            example_event(), [bar],
            commission_price=0, slippage_price=0,
        )
        self.assertEqual(status, "LIMIT_EXPIRED")
        self.assertIsNone(trade)

    def test_25_invalid_tp_discards(self):
        e = example_event()
        e = Event(
            e.identity, e.symbol, e.model, e.side, e.sweep_at,
            e.mss_at, e.ratified_at, e.available_at, 102.0,
            95.0, e.body_open, e.body_close, e.sweep_high,
            e.sweep_low, e.atr_h4,
        )
        status, trade = simulate_event(
            e, [q(t())], commission_price=0, slippage_price=0
        )
        self.assertEqual(status, "INVALID_SL_OR_TP")
        self.assertIsNone(trade)

    def test_26_unclosed_position_not_counted_win(self):
        first = q(t(), bh=106, bl=100, bc=104, ah=106.2, al=102.2, ac=104.2)
        status, trade = simulate_event(
            example_event(), [first],
            commission_price=0, slippage_price=0,
        )
        self.assertEqual(status, "OPEN_AT_END_OF_DATA")
        self.assertIsNone(trade)

    def test_27_empty_trade_report_not_fictitious_pf(self):
        r = report_trades([])
        self.assertIsNone(r["profit_factor"])
        self.assertIsNone(r["win_rate"])
        self.assertEqual(r["trades"], 0)

    def test_35_entry_and_target_same_M5_never_credit_win(self):
        status, trade = simulate_event(
            example_event(), [q(t())],
            commission_price=0, slippage_price=0,
        )
        self.assertEqual(status, "AMBIGUOUS_ENTRY_AND_TARGET_SAME_M5")
        self.assertIsNone(trade)

    def test_36_short_entry_target_same_M5_never_credit_win(self):
        bar = q(
            t(), bo=98, bh=99, bl=89, bc=94,
            ao=98.2, ah=99.2, al=89.2, ac=94.2,
        )
        status, trade = simulate_event(
            example_event("SHORT"), [bar],
            commission_price=0, slippage_price=0,
        )
        self.assertEqual(status, "AMBIGUOUS_ENTRY_AND_TARGET_SAME_M5")
        self.assertIsNone(trade)

    def test_28_reject_negative_slippage_costs(self):
        with self.assertRaises(ValueError):
            simulate_event(
                example_event(), [q(t())],
                commission_price=-1, slippage_price=0,
            )


class HoldoutGateTests(unittest.TestCase):
    def test_29_missing_manifest_is_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            result = readiness(Path(d))
            self.assertEqual(result["status"], "BLOCKED")

    def test_30_committed_manifest_is_blocked(self):
        root = Path(__file__).resolve().parents[1] / "data"
        r = readiness(root)
        self.assertEqual(r["status"], "BLOCKED")
        self.assertEqual(r["symbols_required"], 34)
        self.assertIn("not independently attested", " ".join(r["issues"]))

    def test_31_manifest_sha_and_24_month_window(self):
        root = Path(__file__).resolve().parents[1] / "data"
        m = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(m["pine_git_blob_sha"], PINE_BLOB)
        self.assertEqual(m["start"], START.isoformat())
        self.assertEqual(m["end_exclusive"], END.isoformat())

    def test_32_manifest_lists_all_34_missing(self):
        root = Path(__file__).resolve().parents[1] / "data"
        m = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(set(m["quotes"]), set(SYMBOLS))
        self.assertTrue(all(v is None for v in m["quotes"].values()))

    def test_33_manual_certification_without_market_data_fails(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            original = Path(__file__).resolve().parents[1] / "data" / "manifest.json"
            m = json.loads(original.read_text(encoding="utf-8"))
            for k in ("holdout_unseen_attested", "parity_verified",
                      "provider_data_verified", "costs_verified"):
                m[k] = True
            for k in ("holdout_attestation_ref", "parity_evidence_ref",
                      "data_evidence_ref", "cost_evidence_ref"):
                m[k] = "fake-assertion"
            (root / "manifest.json").write_text(json.dumps(m), encoding="utf-8")
            out = readiness(root)
            self.assertEqual(out["status"], "BLOCKED")
            self.assertTrue(any("missing declared sha256" in x for x in out["issues"]))

    def test_34_manifest_incorrect_time_window_fails(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            original = Path(__file__).resolve().parents[1] / "data" / "manifest.json"
            m = json.loads(original.read_text(encoding="utf-8"))
            m["end_exclusive"] = "2025-01-01T00:00:00+00:00"
            (root / "manifest.json").write_text(json.dumps(m), encoding="utf-8")
            out = readiness(root)
            self.assertTrue(any("exactly" in x for x in out["issues"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
