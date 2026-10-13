"""Purely synthetic GO/NO-GO H6 2010 preflight tests, no PnL."""
from __future__ import annotations

import datetime as dt
import io
import json
import lzma
import struct
import unittest

from qore.infrastructure.trader_lab import qore_native_h6_2010_fx_policy_source_preflight_v1 as h


def bis_xml(ccy:str,only_after:dt.date|None=None):
    period=h.months(h.BIS_START,h.BIS_END)
    if only_after is not None:
        period=[d for d in period if d>=only_after]
    obs="".join(f'<Obs TIME_PERIOD="{d:%Y-%m}" OBS_VALUE="1.50"/>'
                for d in period)
    return (f'<StructureSpecificData><DataSet><Series REF_AREA="{h.CURRENCY_BIS[ccy]}" FREQ="M">'
            +obs+"</Series></DataSet></StructureSpecificData>").encode()


def valid_duka(pair,day):
    tick=struct.pack(">3I2f",1000,111100,111101,1.0,1.0)
    return lzma.compress(tick,format=lzma.FORMAT_ALONE)


class H6DataGate(unittest.TestCase):
    def test_fixed_28_pairs_eight_policy_source(self):
        h.validate_contract()
        self.assertEqual(len(h.FX28),28)
        self.assertEqual(len(h.CURRENCY_BIS),8)
        self.assertEqual(len(h.DUKA_DATES),2)
        self.assertEqual(h.BIS_START,dt.date(2010,5,1))
        self.assertEqual(h.BIS_END,dt.date(2015,12,1))

    def test_bis_complete_six_years_source_not_pnl(self):
        z=h.parse_bis_source(bis_xml("USD"),"USD")
        self.assertEqual(z["observed_months"],68)
        self.assertEqual(z["missing_months"],0)
        self.assertFalse(z["PIT_2010_2015_unrevised_evidence"])
        self.assertFalse(z["rates_exported"])

    def test_japan_start_gap_detected_without_filling(self):
        z=h.parse_bis_source(bis_xml("JPY",only_after=dt.date(2012,1,1)),"JPY")
        self.assertGreater(z["missing_months"],0)
        self.assertEqual(z["first_month"],"2012-01-01")

    def test_bis_wrong_country_aborts(self):
        with self.assertRaisesRegex(ValueError,"MISMATCH_ID_COUNTRY"):
            h.parse_bis_source(bis_xml("JPY"),"USD")

    def test_valid_dukascopy_hour_only_metadata(self):
        r=h.inspect_duka(valid_duka("EURUSD",h.DUKA_DATES[0]),
                         "EURUSD",h.DUKA_DATES[0])
        self.assertEqual(r["ticks_count"],1)
        self.assertFalse(r["underlying_tick_prices_exported"])
        self.assertNotIn("111100",json.dumps(r))

    def test_forbidden_dukascopy_future_holdout_or_unknown(self):
        with self.assertRaisesRegex(ValueError,"NOT_PREREG"):
            h.duka_url("EURUSD",dt.date(2025,2,1))
        with self.assertRaisesRegex(ValueError,"NOT_PREREG"):
            h.duka_url("BTCUSD",h.DUKA_DATES[0])

    def test_uncompressed_junk_or_html_fails(self):
        with self.assertRaisesRegex(ValueError,"NOT_A_BI5_LZMA"):
            h.inspect_duka(b"<!DOCTYPE html>",h.FX28[0],h.DUKA_DATES[0])

    def test_all_sources_full_means_only_go_for_acquisition_not_backtest(self):
        r=h.source_audit(
            bis_downloader=lambda c:bis_xml(c),
            duka_downloader=valid_duka)
        self.assertEqual(r["status"],
                         "TWO_HOUR_SAMPLES_GO_FOR_EXPANDED_DATA_ACQUISITION_ONLY")
        self.assertTrue(r["BIS_full_8_policy_2010_2015"])
        self.assertEqual(r["Dukascopy_valid_samples"],56)
        self.assertFalse(r["full_history_2010_2015_28_FX_data_retrieved"])
        self.assertFalse(r["FX_H6_vol20_Sortino_economic_returns_calculated"])
        self.assertFalse(r["holdout_from_2024_09_17_read"])

    def test_one_rate_gap_is_blocking(self):
        r=h.source_audit(
            bis_downloader=lambda c:bis_xml(
                c, only_after=dt.date(2011,1,1) if c=="JPY" else None),
            duka_downloader=valid_duka)
        self.assertEqual(r["status"],"H6_DATA_CONDITION_NOT_MET")
        self.assertFalse(r["BIS_full_8_policy_2010_2015"])
        self.assertEqual(r["Dukascopy_valid_samples"],56)

    def test_missing_one_hour_is_not_silent(self):
        r=h.source_audit(
            bis_downloader=lambda c:bis_xml(c),
            duka_downloader=lambda s,d:(b"garbage" if s=="AUDUSD" else valid_duka(s,d)))
        self.assertEqual(r["status"],"H6_DATA_CONDITION_NOT_MET")
        self.assertEqual(r["Dukascopy_valid_samples"],54)
        self.assertFalse(r["Dukascopy_all_56_one_hour_samples_valid"])


if __name__=="__main__":
    unittest.main()
