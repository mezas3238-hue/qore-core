"""Synthetic H4-M15 linkage tests: first-known only, never author exact/live."""
import unittest
from dataclasses import replace

from qore.infrastructure.trader_lab.qore_london_lona_swing_h4_m15_link_audit_v1 import (
    H4Reference, adjudicate_schematic_swing,
)

H4 = H4Reference(
    symbol="EURUSD", provider_id="TEST-PROVIDER",
    opened_at_utc="2026-10-09T08:00:00Z",
    closed_at_utc="2026-10-09T12:00:00Z",
    first_known_utc="2026-10-09T12:00:01Z",
    high="1.1050", low="1.0980", closure_claim="C2",
)
CANDIDATE = {
    "candidate_id": "synthetic-1", "direction": "BULLISH",
    "source_id": "TEST-PROVIDER",
    "first_series_bar_open_utc": "2026-10-09T08:00:00Z",
    "last_series_bar_close_utc": "2026-10-09T08:30:00Z",
    "cross_bar_close_utc": "2026-10-09T08:45:00Z",
    "cross_first_known_utc": "2026-10-09T08:45:01Z",
    "raw_series_extreme_not_protected_swing": "1.0990",
    "multiple_series_cross_same_bar": False,
    "post_series_extreme_worse_before_cross": False,
}
DECISION = "2026-10-09T12:00:02Z"


def check(h4=H4, candidates=(CANDIDATE,), at=DECISION, direction="BULLISH", symbol="EURUSD"):
    return adjudicate_schematic_swing(
        h4=h4, candidates=candidates, decision_at_utc=at,
        direction=direction, symbol=symbol
    )


class H4M15LinkTests(unittest.TestCase):
    def test_contained_schematic_is_reviewer_only_not_author_exact(self):
        result = check()
        self.assertEqual(result["status"], "OBSERVATIONAL_ONLY")
        event = result["observed_candidates"][0]
        self.assertEqual(event["status"], "REVIEW_ONLY")
        self.assertEqual(event["decision_not_before_utc"], "2026-10-09T12:00:01+00:00")
        self.assertIsNone(event["fill_price"])
        for label in ("author_exact", "protected_swing_certified",
                      "entry_authorized", "economic_replay_authorized",
                      "live_authorized"):
            self.assertFalse(result[label])

    def test_early_decision_does_not_see_future_h4_close(self):
        result = check(at="2026-10-09T08:46:00Z")
        self.assertEqual(result["status"], "BLOCKED_CONTEXT")
        self.assertIn("H4_NOT_YET_KNOWN_AT_DECISION", result["blockers"])

    def test_late_h4_delivery_delays_readiness(self):
        reference = replace(H4, first_known_utc="2026-10-09T12:02:00Z")
        self.assertEqual(check(h4=reference, at="2026-10-09T12:01:00Z")["status"], "BLOCKED_CONTEXT")
        later = check(h4=reference, at="2026-10-09T12:03:00Z")
        self.assertEqual(later["observed_candidates"][0]["decision_not_before_utc"],
                         "2026-10-09T12:02:00+00:00")

    def test_future_cisd_delivery_excluded(self):
        event = dict(CANDIDATE, cross_first_known_utc="2026-10-09T13:00:00Z")
        output = check(candidates=(event,))
        self.assertEqual(output["future_candidates_ignored"], 1)
        self.assertEqual(output["observed_candidates"], [])

    def test_provenance_from_other_provider_cannot_be_mixed(self):
        event = dict(CANDIDATE, source_id="ANOTHER")
        self.assertIn("PROVIDER_ID_MISMATCH", check(candidates=(event,))["observed_candidates"][0]["reasons"])

    def test_opposite_direction_flagged_not_interpreted(self):
        event = dict(CANDIDATE, direction="BEARISH")
        self.assertIn("OPPOSITE_DIRECTION", check(candidates=(event,))["observed_candidates"][0]["reasons"])

    def test_multiple_candidate_same_m15_requires_adjudication(self):
        event = dict(CANDIDATE, multiple_series_cross_same_bar=True)
        self.assertIn("MULTIPLE_SERIES_NOT_ADJUDICATED",
                      check(candidates=(event,))["observed_candidates"][0]["reasons"])

    def test_extended_extreme_not_passed_as_protected(self):
        event = dict(CANDIDATE, post_series_extreme_worse_before_cross=True)
        self.assertIn("EXTREME_EXTENDED_BEFORE_CROSS_NEEDS_AUTHOR_REVIEW",
                      check(candidates=(event,))["observed_candidates"][0]["reasons"])

    def test_candidate_with_series_before_h4_rejected(self):
        event = dict(CANDIDATE, first_series_bar_open_utc="2026-10-09T07:45:00Z")
        self.assertIn("CISD_SERIES_NOT_FULLY_INSIDE_H4",
                      check(candidates=(event,))["observed_candidates"][0]["reasons"])

    def test_candidate_after_h4_close_rejected(self):
        event = dict(CANDIDATE, cross_bar_close_utc="2026-10-09T12:15:00Z",
                     cross_first_known_utc="2026-10-09T12:15:01Z")
        result = check(candidates=(event,), at="2026-10-09T12:30:00Z")
        self.assertIn("CISD_SERIES_NOT_FULLY_INSIDE_H4", result["observed_candidates"][0]["reasons"])

    def test_candidate_early_known_before_close_leak(self):
        event = dict(CANDIDATE, cross_first_known_utc="2026-10-09T08:44:59Z")
        self.assertIn("FUTURE_M15_CLOSE_LEAK", check(candidates=(event,))["observed_candidates"][0]["reasons"])

    def test_extreme_outside_h4_requires_review(self):
        event = dict(CANDIDATE, raw_series_extreme_not_protected_swing="1.0970")
        self.assertIn("SERIES_EXTREME_OUTSIDE_H4_HIGH_LOW",
                      check(candidates=(event,))["observed_candidates"][0]["reasons"])

    def test_unknown_closure_claim_blocks_adjudication(self):
        reference = replace(H4, closure_claim="UNKNOWN")
        self.assertIn("H4_C2_C3_CLOSURE_UNDETERMINED",
                      check(h4=reference)["observed_candidates"][0]["reasons"])

    def test_fabricated_c2_label_never_makes_certification_true(self):
        reference = replace(H4, closure_claim="C3")
        output = check(h4=reference)
        self.assertTrue(output["observed_candidates"][0]["h4_c2_c3_label_unverified"])
        self.assertFalse(output["protected_swing_certified"])

    def test_bad_h4_time_range_blocks(self):
        reference = replace(H4, closed_at_utc="2026-10-09T11:00:00Z")
        self.assertIn("BAD_H4_REFERENCE:NOT_EXACTLY_H4_UTC_REFERENCE", check(h4=reference)["blockers"])

    def test_future_h4_claim_fails(self):
        reference = replace(H4, first_known_utc="2026-10-09T11:59:00Z")
        self.assertIn("BAD_H4_REFERENCE:H4_FUTURE_CLOSE_LEAK", check(h4=reference)["blockers"])

    def test_other_symbol_h4_does_not_contaminate(self):
        reference = replace(H4, symbol="GBPUSD")
        self.assertIn("H4_CROSS_SYMBOL", check(h4=reference)["blockers"])

    def test_new_future_candidate_does_not_change_previous_classification(self):
        original = check()
        future = dict(CANDIDATE, candidate_id="future", cross_first_known_utc="2026-10-09T13:00:00Z")
        later = check(candidates=(CANDIDATE, future))
        self.assertEqual(original["observed_candidates"], later["observed_candidates"])

    def test_no_callback_or_trading_codes_on_empty_evidence(self):
        result = check(candidates=())
        self.assertEqual(result["observed_candidates"], [])
        self.assertFalse(result["economic_replay_authorized"])

    def test_utc_offset_local_rejected(self):
        with self.assertRaisesRegex(ValueError, "EXPLICIT_UTC_REQUIRED"):
            check(at="2026-10-09T08:00:02-04:00")

if __name__ == "__main__":
    unittest.main()
