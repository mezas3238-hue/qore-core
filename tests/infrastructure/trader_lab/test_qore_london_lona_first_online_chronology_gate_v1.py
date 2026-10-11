"""Synthetic chronology tests for LON-A: no market data, P&L or signals."""
import unittest
from dataclasses import replace

from qore.infrastructure.trader_lab.qore_london_lona_first_online_chronology_gate_v1 import (
    Evidence,
    evaluate_chronology,
)

D1 = Evidence(
    event_id="daily-closed-1", symbol="EURUSD", role="DAILY_BIAS_CLOSED",
    timeframe="D1", rule_id="LA02", source_id="fixture-only",
    knowledge_kind="CLOSED_BAR", bar_open_utc="2026-10-09T00:00:00Z",
    bar_close_utc="2026-10-10T00:00:00Z",
    observed_until_utc="2026-10-10T00:00:00Z",
    first_known_utc="2026-10-10T00:00:01Z",
)
H4 = Evidence(
    event_id="h4-closed-1", symbol="EURUSD", role="H4_SWING_CLOSED",
    timeframe="H4", rule_id="LA05", source_id="fixture-only",
    knowledge_kind="CLOSED_BAR", bar_open_utc="2026-10-10T04:00:00Z",
    bar_close_utc="2026-10-10T08:00:00Z",
    observed_until_utc="2026-10-10T08:00:00Z",
    first_known_utc="2026-10-10T08:00:01Z",
)
M15 = Evidence(
    event_id="m15-closed-1", symbol="EURUSD", role="M15_CISD_CLOSED",
    timeframe="M15", rule_id="LA08", source_id="fixture-only",
    knowledge_kind="CLOSED_BAR", bar_open_utc="2026-10-10T08:00:00Z",
    bar_close_utc="2026-10-10T08:15:00Z",
    observed_until_utc="2026-10-10T08:15:00Z",
    first_known_utc="2026-10-10T08:15:01Z",
)
DECISION = "2026-10-10T08:16:00Z"


def check(*events, at=DECISION, symbol="EURUSD"):
    return evaluate_chronology(symbol=symbol, decision_at_utc=at, evidence=events)


class LondonFirstOnlineChronology(unittest.TestCase):
    def test_closed_d1_h4_m15_chronology_pass_is_not_trade_authorization(self):
        result = check(D1, H4, M15)
        self.assertTrue(result["chronology_pass"])
        self.assertEqual(result["status"], "CHRONOLOGY_PASS_ONLY")
        for key in ("author_fidelity_certified", "wick_completion_certified",
                    "cisd_geometry_certified", "economic_replay_authorized",
                    "live_authorized"):
            self.assertFalse(result[key])

    def test_unconfirmed_h4_is_missing(self):
        result = check(D1, M15)
        self.assertIn("MISSING_CONFIRMED_ROLE:H4_SWING_CLOSED", result["blockers"])

    def test_future_h4_information_is_ignored_not_used(self):
        late = replace(H4, first_known_utc="2026-10-10T08:30:00Z")
        result = check(D1, late, M15)
        self.assertFalse(result["chronology_pass"])
        self.assertEqual(result["future_evidence_ignored"], 1)
        self.assertIn("MISSING_CONFIRMED_ROLE:H4_SWING_CLOSED", result["blockers"])

    def test_future_h4_closure_cannot_be_used_early(self):
        illegal = replace(H4, bar_close_utc="2026-10-10T09:00:00Z",
                          observed_until_utc="2026-10-10T09:00:00Z")
        result = check(D1, illegal, M15)
        self.assertIn("INVALID_EVIDENCE:h4-closed-1:FUTURE_BAR_CLOSE_LEAK", result["blockers"])

    def test_m15_cisd_cannot_be_known_before_m15_close(self):
        illegal = replace(M15, first_known_utc="2026-10-10T08:14:59Z")
        result = check(D1, H4, illegal)
        self.assertIn("INVALID_EVIDENCE:m15-closed-1:FUTURE_BAR_CLOSE_LEAK", result["blockers"])

    def test_partial_h4_cannot_masquerade_as_confirmed_h4(self):
        illegal = replace(H4, knowledge_kind="PARTIAL_OBSERVATION",
                          first_known_utc="2026-10-10T08:15:02Z")
        result = check(D1, illegal, M15)
        self.assertIn("INVALID_EVIDENCE:h4-closed-1:PARTIAL_CANNOT_CERTIFY_DAILY_H4_M15", result["blockers"])

    def test_partial_wick_is_context_not_wick_completion(self):
        partial = Evidence(
            event_id="h4-wick-partial-1", symbol="EURUSD", role="H4_WICK_PARTIAL",
            timeframe="H4", rule_id="LA06", source_id="fixture-only",
            knowledge_kind="PARTIAL_OBSERVATION",
            bar_open_utc="2026-10-10T08:00:00Z",
            bar_close_utc="2026-10-10T12:00:00Z",
            observed_until_utc="2026-10-10T08:10:00Z",
            first_known_utc="2026-10-10T08:10:01Z",
        )
        result = check(D1, H4, partial, M15)
        self.assertTrue(result["chronology_pass"])
        self.assertFalse(result["wick_completion_certified"])
        self.assertEqual(result["context_observation_ids_not_completion_proof"],
                         ["h4-wick-partial-1"])

    def test_partial_wick_cannot_fill_required_closed_role(self):
        partial = Evidence(
            event_id="wick-only", symbol="EURUSD", role="H4_WICK_PARTIAL",
            timeframe="H4", rule_id="LA06", source_id="fixture-only",
            knowledge_kind="PARTIAL_OBSERVATION",
            bar_open_utc="2026-10-10T08:00:00Z",
            bar_close_utc="2026-10-10T12:00:00Z",
            observed_until_utc="2026-10-10T08:10:00Z",
            first_known_utc="2026-10-10T08:10:01Z",
        )
        result = check(D1, partial, M15)
        self.assertFalse(result["chronology_pass"])

    def test_future_intrabar_wick_extreme_rejected(self):
        bad = Evidence(
            event_id="future-wick", symbol="EURUSD", role="H4_WICK_PARTIAL",
            timeframe="H4", rule_id="LA06", source_id="fixture-only",
            knowledge_kind="PARTIAL_OBSERVATION",
            bar_open_utc="2026-10-10T08:00:00Z",
            bar_close_utc="2026-10-10T12:00:00Z",
            observed_until_utc="2026-10-10T08:30:00Z",
            first_known_utc="2026-10-10T08:10:00Z",
        )
        result = check(D1, H4, M15, bad)
        self.assertIn("INVALID_EVIDENCE:future-wick:FUTURE_INTRABAR_EXTREME_LEAK", result["blockers"])

    def test_future_append_does_not_change_prefix(self):
        earlier = check(D1, H4, M15)
        later = replace(H4, event_id="future-h4", first_known_utc="2026-10-10T09:00:00Z")
        result = check(D1, H4, M15, later)
        self.assertEqual(earlier["chronology_pass"], result["chronology_pass"])
        self.assertEqual(earlier["blockers"], result["blockers"])
        self.assertEqual(earlier["required_evidence_ids"], result["required_evidence_ids"])
        self.assertEqual(result["future_evidence_ignored"], 1)

    def test_same_role_duplicate_blocks_ambiguous_origin(self):
        duplicate = replace(M15, event_id="another-m15")
        result = check(D1, H4, M15, duplicate)
        self.assertIn("DUPLICATE_REQUIRED_ROLE:M15_CISD_CLOSED", result["blockers"])

    def test_duplicate_event_id_blocks(self):
        result = check(D1, H4, M15, M15)
        self.assertIn("DUPLICATE_EVENT_ID:m15-closed-1", result["blockers"])

    def test_cross_symbol_provenance_fails(self):
        other = replace(H4, symbol="GBPUSD")
        result = check(D1, other, M15)
        self.assertIn("CROSS_SYMBOL_EVIDENCE:h4-closed-1", result["blockers"])

    def test_wrong_timeframe_or_rule_id_fails(self):
        wrong = replace(M15, timeframe="M1", rule_id="TT09")
        result = check(D1, H4, wrong)
        self.assertIn("INVALID_EVIDENCE:m15-closed-1:UNDECLARED_ROLE_OR_MISMATCHED_RULE", result["blockers"])

    def test_unlabelled_source_fails(self):
        result = check(D1, replace(H4, source_id=""), M15)
        self.assertIn("INVALID_EVIDENCE:h4-closed-1:MISSING_EVENT_OR_SOURCE_ID", result["blockers"])

    def test_late_h4_delivery_waits_until_it_is_known(self):
        late_h4 = replace(H4, first_known_utc="2026-10-10T08:15:30Z")
        early = check(D1, late_h4, M15, at="2026-10-10T08:15:20Z")
        self.assertIn("MISSING_CONFIRMED_ROLE:H4_SWING_CLOSED", early["blockers"])
        later = check(D1, late_h4, M15)
        self.assertTrue(later["chronology_pass"])
        self.assertEqual(later["chronology_ready_not_before_utc_not_a_fill"],
                         "2026-10-10T08:15:30+00:00")

    def test_cisd_inside_unclosed_h4_is_retrospective_only_after_h4_close(self):
        inside = replace(
            M15, bar_open_utc="2026-10-10T07:30:00Z",
            bar_close_utc="2026-10-10T07:45:00Z",
            observed_until_utc="2026-10-10T07:45:00Z",
            first_known_utc="2026-10-10T07:45:01Z",
        )
        premature = check(D1, H4, inside, at="2026-10-10T07:46:00Z")
        self.assertFalse(premature["chronology_pass"])
        self.assertIn("MISSING_CONFIRMED_ROLE:H4_SWING_CLOSED", premature["blockers"])
        mature = check(D1, H4, inside, at="2026-10-10T08:00:05Z")
        self.assertTrue(mature["chronology_pass"])
        self.assertEqual(mature["m15_h4_relation"], "INTRA_H4_RETROSPECTIVE_ONLY")
        self.assertEqual(mature["chronology_ready_not_before_utc_not_a_fill"],
                         "2026-10-10T08:00:01+00:00")
        self.assertFalse(mature["economic_replay_authorized"])

    def test_old_m15_outside_h4_context_cannot_be_relabelled(self):
        wrong = replace(
            M15, bar_open_utc="2026-10-10T03:15:00Z",
            bar_close_utc="2026-10-10T03:30:00Z",
            observed_until_utc="2026-10-10T03:30:00Z",
            first_known_utc="2026-10-10T03:30:01Z",
        )
        result = check(D1, H4, wrong)
        self.assertIn("M15_OUTSIDE_H4_CONFIRMATION_WINDOW", result["blockers"])

    def test_daily_bias_late_to_existing_structure_blocks(self):
        late_daily = replace(D1, first_known_utc="2026-10-10T08:15:05Z")
        result = check(late_daily, H4, M15)
        self.assertIn("DAILY_BIAS_NOT_KNOWN_BEFORE_LOWER_STRUCTURE", result["blockers"])

    def test_naive_decision_timestamp_rejected(self):
        with self.assertRaisesRegex(ValueError, "EXPLICIT_UTC_REQUIRED"):
            check(D1, H4, M15, at="2026-10-10T08:16:00")

    def test_ny_offset_not_silently_converted(self):
        with self.assertRaisesRegex(ValueError, "EXPLICIT_UTC_REQUIRED"):
            check(D1, H4, M15, at="2026-10-10T04:16:00-04:00")

    def test_bad_bar_end_rejected(self):
        bad = replace(M15, bar_close_utc=M15.bar_open_utc)
        result = check(D1, H4, bad)
        self.assertIn("INVALID_EVIDENCE:m15-closed-1:BAD_BAR_INTERVAL_OR_OBSERVATION_CUTOFF",
                      result["blockers"])

    def test_partial_exact_at_close_not_claimed_as_partial(self):
        partial = Evidence(
            event_id="partial-at-close", symbol="EURUSD", role="DAILY_WICK_PARTIAL",
            timeframe="D1", rule_id="LA04", source_id="fixture-only",
            knowledge_kind="PARTIAL_OBSERVATION",
            bar_open_utc="2026-10-10T00:00:00Z",
            bar_close_utc="2026-10-11T00:00:00Z",
            observed_until_utc="2026-10-11T00:00:00Z",
            first_known_utc="2026-10-11T00:00:01Z",
        )
        result = check(D1, H4, M15, partial, at="2026-10-11T00:00:02Z")
        self.assertIn("INVALID_EVIDENCE:partial-at-close:FUTURE_INTRABAR_EXTREME_LEAK", result["blockers"])

    def test_allows_late_delivery_after_close_as_long_as_decision_is_later(self):
        delayed = replace(M15, first_known_utc="2026-10-10T08:15:40Z")
        self.assertTrue(check(D1, H4, delayed)["chronology_pass"])

    def test_future_data_cannot_fill_missing_daily_bias(self):
        future = replace(D1, first_known_utc="2026-10-10T09:00:00Z")
        result = check(future, H4, M15)
        self.assertIn("MISSING_CONFIRMED_ROLE:DAILY_BIAS_CLOSED", result["blockers"])


if __name__ == "__main__":
    unittest.main()
