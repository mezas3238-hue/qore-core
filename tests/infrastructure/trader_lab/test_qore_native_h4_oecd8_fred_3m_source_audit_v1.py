"""Pure mock-data source parsing tests for eight OECD/FRED 3M rate series."""
from __future__ import annotations

import csv
import io
import json
import unittest
from datetime import date

from qore.infrastructure.trader_lab import qore_native_h4_oecd8_fred_3m_source_audit_v1 as a


def fake(currency="AUD",na=None,extra=False,duplicate=False,header_bad=False):
    stream=io.StringIO()
    w=csv.writer(stream)
    w.writerow(["DATE", a.SERIES[currency] if not header_bad else "WRONG"])
    d=a.START
    while d<=a.END:
        w.writerow([d.isoformat(), "." if d==na else "1.23"])
        d=date(d.year+1,1,1) if d.month==12 else date(d.year,d.month+1,1)
    if duplicate:
        w.writerow([a.END.isoformat(),"2.00"])
    if extra:
        w.writerow(["2024-10-01","1.24"])
    return stream.getvalue().encode("utf-8")


class FREDH4CoverageSynthetic(unittest.TestCase):
    def test_eight_documented_rates_currency_map(self):
        a.validate_source_roster()
        self.assertEqual(a.MONTH_COUNT,104)
        self.assertEqual(set(a.SERIES),set(("AUD","CAD","CHF","EUR","GBP","JPY","NZD","USD")))

    def test_well_formed_full_104_monthly_points(self):
        r=a.parse_fred_csv(fake(),"AUD")
        self.assertEqual(r["present_valid_months"],104)
        self.assertEqual(r["missing_months_including_na"],0)
        self.assertEqual(r["first_present_month"],"2016-01-01")
        self.assertEqual(r["last_present_month"],"2024-08-01")
        self.assertTrue(r["monthly_values_may_have_been_revised_after_asof"])
        self.assertFalse(r["proves_1_month_forward_quotes"])

    def test_one_missing_month_blocks_complete_panel(self):
        r=a.parse_fred_csv(fake(na=date(2023,4,1)),"AUD")
        self.assertEqual(r["present_valid_months"],103)
        self.assertEqual(r["missing_months_including_na"],1)
        self.assertEqual(r["missing_first_5_month_stamps"],["2023-04-01"])

    def test_reject_wrong_series_header(self):
        with self.assertRaisesRegex(ValueError,"NOT_EXPECTED_CSV"):
            a.parse_fred_csv(fake(header_bad=True),"AUD")

    def test_reject_html_body(self):
        with self.assertRaisesRegex(ValueError,"NOT_EXPECTED_CSV"):
            a.parse_fred_csv(b"<!DOCTYPE html><html>blocked</html>","AUD")

    def test_reject_duplicate_and_out_of_order_months(self):
        with self.assertRaisesRegex(ValueError,"NOT_SORTED_MONTH"):
            a.parse_fred_csv(fake(duplicate=True),"AUD")

    def test_exclude_unrequested_historical_holdout_months(self):
        r=a.parse_fred_csv(fake(extra=True),"AUD")
        self.assertEqual(r["out_of_requested_period_month_records"],1)
        self.assertEqual(r["present_valid_months"],104)
        self.assertNotIn("2024-10-01",json.dumps(r))

    def test_eight_sources_count_not_an_economic_run(self):
        result=a.source_audit(
            downloader=lambda series:fake(
                currency=next(c for c,s in a.SERIES.items() if s==series))
        )
        self.assertEqual(result["currency_count"],8)
        self.assertEqual(result["historical_complete_currency_count"],8)
        self.assertIn("PIT_UNPROVEN",result["status"])
        self.assertTrue(result["not_verified_2016_2024_asof_vintages"])
        self.assertTrue(result["not_one_month_tenor"])
        self.assertTrue(result["no_historical_rates_republished"])
        self.assertFalse(result["monthly_carry_backtest_executed"])
        self.assertFalse(result["historical_holdout_2024_09_17_onward_economics_read"])
        self.assertIsNone(result["sharpe_or_CAGR"])
        self.assertEqual(result["certified_traders"],0)
        self.assertNotIn("1.23",json.dumps(result))

    def test_missing_is_visible_without_imputation(self):
        result=a.source_audit(
            downloader=lambda series:fake(
                currency=next(c for c,s in a.SERIES.items() if s==series),
                na=date(2022,2,1) if series==a.SERIES["EUR"] else None
            )
        )
        self.assertEqual(result["historical_complete_currency_count"],7)
        self.assertIn("PARTIAL",result["status"])

    def test_only_whitelisted_ids_accessed(self):
        with self.assertRaisesRegex(ValueError,"UNAPPROVED_FRED_SERIES"):
            a.source_url("DFF")
        url=a.source_url(a.SERIES["USD"])
        self.assertTrue(url.startswith("https://fred.stlouisfed.org/graph/fredgraph.csv?"))
        self.assertIn("coed=2024-08-01",url)


if __name__=="__main__":
    unittest.main()
