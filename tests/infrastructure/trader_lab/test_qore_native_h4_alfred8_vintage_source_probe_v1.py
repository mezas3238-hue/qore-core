"""Synthetic historical ALFRED vintage source parsing, no real rate values."""
import csv
import io
import json
import unittest
from datetime import date

from qore.infrastructure.trader_lab import qore_native_h4_alfred8_vintage_source_probe_v1 as a


def fake(currency="USD",future=False,wrong_header=False,missing=False):
    s=io.StringIO()
    w=csv.writer(s)
    sid=a.SERIES[currency]
    dates=a.VINTAGES
    if wrong_header:
        w.writerow(["observation_date",sid+"_20261012",sid+"_20261012"])
    else:
        w.writerow(["observation_date",*(sid+"_"+x.strftime("%Y%m%d") for x in dates)])
    w.writerow(["2016-10-01","1.00","2.00"])
    w.writerow(["2019-12-01","1.10","1.20"])
    w.writerow(["2023-12-01", "." if missing else "", "2.10"])
    if future:
        w.writerow(["2024-09-01","1.00","2.00"])
    return s.getvalue().encode()


class AlfredH4(unittest.TestCase):
    def test_exact_vintage_dates_and_roster(self):
        self.assertEqual(len(a.SERIES),8)
        self.assertEqual([x.isoformat() for x in a.VINTAGES],
                         ["2019-12-31","2023-12-29"])
        self.assertEqual(a.BASE,"https://alfred.stlouisfed.org/graph/alfredgraph.csv")

    def test_strict_real_vintage_headers_and_observed_to_vintage(self):
        z=a.validate_vintage_csv(fake(),"USD")
        self.assertEqual(z["non_missing_monthly_values_by_vintage"],
                         {"2019-12-31":2,"2023-12-29":3})
        self.assertEqual(z["last_observation_available_as_of_vintage"],
                         {"2019-12-31":"2019-12-01",
                          "2023-12-29":"2023-12-01"})
        self.assertTrue(z["no_numeric_rates_exported"])

    def test_reject_current_vintage_falsified_old_header(self):
        with self.assertRaisesRegex(ValueError,"VINTAGE_HEADERS_MISMATCH"):
            a.validate_vintage_csv(fake(wrong_header=True),"USD")

    def test_reject_future_month_in_earlier_asof(self):
        with self.assertRaisesRegex(ValueError,"VALUE_FROM_FUTURE"):
            a.validate_vintage_csv(fake(future=True),"USD")

    def test_missing_values_no_forward_fill(self):
        z=a.validate_vintage_csv(fake(missing=True),"USD")
        self.assertEqual(z["non_missing_monthly_values_by_vintage"]["2023-12-29"],3)
        self.assertFalse(z["forward_one_month_quotes_found"])

    def test_source_coverage_readonly_not_sharpe(self):
        z=a.audit(downloader=lambda currency:fake(currency))
        self.assertEqual(z["currency_count"],8)
        self.assertIsNone(z["claimed_Sharpe"])
        self.assertTrue(z["not_pit_monthly_all_2016_2024_yet"])
        self.assertFalse(z["FX_carry_backtest_performed"])
        self.assertFalse(z["broker_NET_backtest_performed"])
        self.assertTrue(z["holdout_2024_09_17_onward_not_accessed"])
        self.assertNotIn("1.10",json.dumps(z))


if __name__=="__main__":
    unittest.main()
