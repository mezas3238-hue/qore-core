"""P0 independent Trader signal scheduler; legacy modes cannot schedule entries."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"scripts"))
from cibo_p0_replay_manifest_source import (
    CiboP0ManifestSourceError,original_chronological_signals,
)


class ManifestSourceTest(unittest.TestCase):
    def make_row(self,sid,time,trader="R34_XAUUSD"):
        return {"signal_fingerprint":sid,"market_decision_at":time,
                "qore_symbol":"XAUUSD","trader_id":trader}

    def test_original_signals_only_and_chronological_stable(self):
        data={"opportunities":[
            self.make_row("z","2021-01-01T10:05:00+00:00"),
            self.make_row("b","2021-01-01T10:00:00+00:00"),
            self.make_row("a","2021-01-01T10:00:00+00:00"),
        ],"decisions":[{"old_mode":"ATTACK","signal":"hindsight"}]}
        out=original_chronological_signals(data,expected_count=3)
        self.assertEqual([x["signal_fingerprint"] for x in out],["a","b","z"])
        self.assertTrue(all("mode" not in x for x in out))
    def test_canonical_nas100_alias_keeps_trader_identity(self):
        row=self.make_row("vt31","2021-01-01T10:00:00+00:00","VT31_NAS100")
        row["qore_symbol"]="NAS100"
        out=original_chronological_signals({"opportunities":[row]},expected_count=1)
        self.assertEqual(out[0]["symbol"],"NDX100")
        self.assertEqual(out[0]["trader"],"VT31_NAS100")

    def test_duplicates_and_naive_time_fail(self):
        r=self.make_row("a","2021-01-01T10:00:00+00:00")
        with self.assertRaisesRegex(CiboP0ManifestSourceError,"duplicate"):
            original_chronological_signals({"opportunities":[r,r]},expected_count=2)
        r=self.make_row("a","2021-01-01T10:00:00")
        with self.assertRaisesRegex(CiboP0ManifestSourceError,"aware"):
            original_chronological_signals({"opportunities":[r]},expected_count=1)


if __name__=="__main__":
    unittest.main()
