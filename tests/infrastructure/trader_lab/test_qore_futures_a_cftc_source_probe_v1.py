"""Synthetic tests for CFTC six-root official source metadata audit."""
from __future__ import annotations

import csv
import io
import unittest
import zipfile
from datetime import date, timedelta
from typing import Any

# Source script lives under .github/scripts, available in CI PYTHONPATH.
import qore_futures_a_cftc_sixroots_public_source_probe_v1 as c

from qore.infrastructure.trader_lab import qore_research_zero_budget_intake_v1 as q


_EXCHANGES = {
    "CL": "WTI-PHYSICAL - NEW YORK MERCANTILE EXCHANGE",
    "NG": "NATURAL GAS - NEW YORK MERCANTILE EXCHANGE",
    "GC": "GOLD - COMMODITY EXCHANGE INC.",
    "HG": "COPPER-GRADE #1 - COMMODITY EXCHANGE INC.",
    "ZC": "CORN - CHICAGO BOARD OF TRADE",
    "ZS": "SOYBEANS - CHICAGO BOARD OF TRADE",
}


def _synthetic_zip(
    *, exclude: str | None = None, wrong_year: bool = False,
    duplicate: bool = False, negative: bool = False,
    mismatched_venue: bool = False,
) -> bytes:
    buf = io.StringIO()
    fields = list(c.REQUIRED_COLUMNS)
    writer = csv.DictWriter(buf, fieldnames=fields)
    writer.writeheader()
    base = date(2018, 1, 2)
    for root, code in c.CONTRACT_CODES.items():
        if exclude == root:
            continue
        for i in range(50):
            day = base + timedelta(days=i * 7)
            if wrong_year:
                day = day.replace(year=2022)
            info: dict[str, Any] = {
                "CFTC_Contract_Market_Code": code,
                "As_of_Date_Form_YYYY-MM-DD": day.isoformat(),
                "Market_and_Exchange_Names": (
                    "FAKE - SOME EXCHANGE" if mismatched_venue else _EXCHANGES[root]
                ),
                "Open_Interest_All": "-1" if negative else "40000",
                "M_Money_Positions_Long_All": "5000",
                "M_Money_Positions_Short_All": "2000",
            }
            writer.writerow(info)
            if duplicate and root == "CL" and i == 0:
                writer.writerow(info)
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as handle:
        handle.writestr("fut_disagg_2018.txt", buf.getvalue())
    return out.getvalue()


class TestCftcOfficialSourceAudit(unittest.TestCase):
    def test_six_roots_real_code_identity_and_weekly_counts(self) -> None:
        out = c.parse_cftc_source(_synthetic_zip(), 2018)
        self.assertEqual(set(out["records_by_root"]), set(c.CONTRACT_CODES))
        for details in out["records_by_root"].values():
            self.assertEqual(details["weekly_reports"], 50)
            self.assertFalse(details["expiry_specific"])
            self.assertFalse(details["has_bidask"])
            self.assertFalse(details["known_original_release_timestamp_each_report"])
        self.assertEqual(out["year"], 2018)

    def test_no_reserved_2022_or_future_data(self) -> None:
        with self.assertRaisesRegex(ValueError, "UNAUTHORIZED_YEAR"):
            c.parse_cftc_source(_synthetic_zip(), 2022)
        with self.assertRaisesRegex(ValueError, "REPORT_DATE_OUTSIDE_AUDIT_SCOPE"):
            c.parse_cftc_source(_synthetic_zip(wrong_year=True), 2018)

    def test_missing_roots_fail(self) -> None:
        with self.assertRaisesRegex(ValueError, "ROOT_MISSING_WEEKS"):
            c.parse_cftc_source(_synthetic_zip(exclude="NG"), 2018)

    def test_duplicate_week_cannot_inflate_population(self) -> None:
        with self.assertRaisesRegex(ValueError, "DUPLICATE_CFTC_MARKET_WEEK"):
            c.parse_cftc_source(_synthetic_zip(duplicate=True), 2018)

    def test_no_borrowed_exchange_identity(self) -> None:
        with self.assertRaisesRegex(ValueError, "UNVERIFIED_EXCHANGE_NAME"):
            c.parse_cftc_source(_synthetic_zip(mismatched_venue=True), 2018)

    def test_negative_position_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "NEGATIVE_POSITION_FIELD"):
            c.parse_cftc_source(_synthetic_zip(negative=True), 2018)

    def test_random_bytes_fail_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "ZIP_EMPTY_OR_UNTRUSTED_SIZE"):
            c.parse_cftc_source(b"not zip", 2018)
        with self.assertRaisesRegex(ValueError, "CORRUPT_CFTC_ARCHIVE"):
            c.parse_cftc_source(b"x" * 1024, 2018)

    def test_source_never_issues_prereg_or_trading_permission(self) -> None:
        self.assertEqual(c.SCHEMA, "qore.futures-a.cftc-sixroots.source-audit.v1")
        self.assertEqual(len(c.CONTRACT_CODES), 6)
        self.assertEqual(q.blocked_futures_a_m0().status.value, "source_blocked")


if __name__ == "__main__":
    unittest.main()
