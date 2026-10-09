import unittest
from dataclasses import replace
from datetime import timedelta

from qore.infrastructure.cibo_trade_ops_audit import (
    record_management_proposal, replay_trade_ops_events,
)
from qore.infrastructure.cibo_trade_ops_director import (
    Stage, TradeOpsError, decide_position_management,
)
from test_cibo_trade_ops_director import NOW, ev, open_position, quote


class TestCiboTradeOpsAudit(unittest.TestCase):
    def test_exhaustive_frozen_manifest_synthetic(self):
        ids = [f"s-{i}" for i in range(3368)]
        events = [
            ev(0, Stage.SIGNAL_RECEIVED, event_id=f"e-{i}", signal_id=signal)
            for i, signal in enumerate(ids)
        ]
        audit = replay_trade_ops_events(events, expected_signal_ids=ids)
        self.assertEqual(len(audit.snapshots), 3368)
        self.assertEqual(audit.events_seen, 3368)
        self.assertTrue(audit.manifest_verified)
        self.assertFalse(audit.financial_certified)
        self.assertEqual(audit.broker_deals_seen, 0)

    def test_missing_signal_cannot_claim_coverage(self):
        with self.assertRaisesRegex(TradeOpsError, "coverage mismatch"):
            replay_trade_ops_events(
                [ev(0, Stage.SIGNAL_RECEIVED)],
                expected_signal_ids=["signal-1", "missing"],
            )
        audit = replay_trade_ops_events([ev(0, Stage.SIGNAL_RECEIVED)])
        self.assertFalse(audit.manifest_verified)

    def test_duplicate_ids_are_globally_rejected(self):
        a = ev(0, Stage.SIGNAL_RECEIVED)
        b = ev(0, Stage.SIGNAL_RECEIVED, signal_id="another")
        with self.assertRaisesRegex(TradeOpsError, "duplicate global event"):
            replay_trade_ops_events([a, b])

    def test_replay_determinism_and_unfundable(self):
        events = [
            ev(0, Stage.SIGNAL_RECEIVED),
            ev(1, Stage.ECONOMICALLY_VALUED),
            ev(2, Stage.UNFUNDABLE),
        ]
        one = replay_trade_ops_events(events)
        two = replay_trade_ops_events(events)
        self.assertEqual(one.audit_sha256, two.audit_sha256)
        self.assertEqual(dict(one.stage_counts)["UNFUNDABLE"], 1)

    def test_advisory_journal_dedup_and_immutable(self):
        s = open_position()
        d = decide_position_management(s, quote())
        journal = record_management_proposal(None, s, d)
        self.assertEqual(journal.decision_ids, (d.decision_id,))
        self.assertFalse(journal.execution_authorized)
        with self.assertRaisesRegex(TradeOpsError, "duplicate management"):
            record_management_proposal(journal, s, d)
        d2 = decide_position_management(s, quote(
            observed_at=NOW + timedelta(seconds=6),
            quote_as_of=NOW + timedelta(seconds=5),
            atr_as_of=NOW + timedelta(seconds=5),
        ))
        next_journal = record_management_proposal(journal, s, d2)
        self.assertEqual(len(next_journal.decision_ids), 2)
        self.assertEqual(len(journal.decision_ids), 1)

    def test_journal_rejects_fake_authorization(self):
        s = open_position()
        d = decide_position_management(s, quote())
        with self.assertRaises(TradeOpsError):
            record_management_proposal(None, s, replace(d, execution_authorized=True))
        with self.assertRaises(TradeOpsError):
            record_management_proposal(None, s, replace(d, position_id="different"))
        with self.assertRaises(TradeOpsError):
            record_management_proposal(
                None, s, replace(d, occurred_at=NOW - timedelta(seconds=1))
            )


if __name__ == "__main__":
    unittest.main()
