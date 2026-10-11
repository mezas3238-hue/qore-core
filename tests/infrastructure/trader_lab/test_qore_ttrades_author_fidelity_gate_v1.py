"""Primary-author source certification gate: cannot turn proxies into trades."""
from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from qore.infrastructure.trader_lab.qore_ttrades_author_fidelity_gate_v1 import (
    AVAILABILITY_INVARIANTS,
    EVIDENCE_FLAGS,
    decide,
)

ROOT = Path(__file__).resolve().parents[3]
FILE = ROOT / "docs/research/qore_scalper_ttrades_author_fidelity_contract_2026-10-11.json"


class SourceGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.c = json.loads(FILE.read_text(encoding="utf-8"))

    def test_original_prereg_is_blocked_on_known_author_unknowns(self) -> None:
        r = decide(self.c)
        self.assertEqual(r["author_source_gate"], "BLOCKED_SOURCE_FIDELITY")
        self.assertFalse(r["economic_replay_authorized"])
        self.assertEqual(r["source_refs_checked"], 8)
        self.assertGreaterEqual(r["blocking_reason_count"], 14)
        self.assertTrue(any("NOT_RESOLVED:TT05" in x for x in r["blocking_reasons"]))

    def test_cannot_set_authorized_flag_without_independent_evidence(self) -> None:
        c = copy.deepcopy(self.c)
        c["verification"]["economic_replay_authorized"] = True
        r = decide(c)
        self.assertFalse(r["economic_replay_authorized"])
        self.assertIn("ILLEGAL_AUTHORIZATION_WHILE_BLOCKED", r["blocking_reasons"])

    def test_cannot_call_QORE_interpretation_author_exact(self) -> None:
        c = copy.deepcopy(self.c)
        for r in c["rules"]:
            if r["id"] == "TT06":
                r["status"] = "QORE_VARIANT_DOCUMENTED"
                r["reviewer_adjudication"] = "proxy"
                r["evidence_test_ref"] = "test_fake"
        errors = decide(c)["blocking_reasons"]
        self.assertTrue(any("NOT_RESOLVED:TT06" in x for x in errors))

    def test_cannot_pass_with_fake_complete_contract_without_video_fixtures(self) -> None:
        c = copy.deepcopy(self.c)
        for r in c["rules"]:
            if r["id"] == "TT01":
                continue
            idx = int(r["id"][2:])
            r["status"] = (
                "AUTHOR_EXACT_IMPLEMENTABLE" if idx < 11 else
                "QORE_VARIANT_DOCUMENTED" if idx < 14 else
                "EVIDENCE_VERIFIED"
            )
            r["reviewer_adjudication"] = "human review still must be genuine"
            r["evidence_test_ref"] = "example-to-code-test-still-required"
        for flag in EVIDENCE_FLAGS + AVAILABILITY_INVARIANTS:
            c["verification"][flag] = True
        c["verification"]["economic_replay_authorized"] = True
        report=decide(c)
        self.assertFalse(report["economic_replay_authorized"])
        self.assertIn("NO_AUTHOR_VIDEO_FIXTURE_TIMECODES", report["blocking_reasons"])

    def test_missing_author_source_cannot_pass_even_if_text_looks_plausible(self) -> None:
        c=copy.deepcopy(self.c)
        c["sources"]=[s for s in c["sources"] if s["id"] != "A0"]
        r=decide(c)
        self.assertIn("REQUIRED_PRIMARY_SOURCES_MISSING_OR_DUPLICATE",r["blocking_reasons"])
        self.assertFalse(r["economic_replay_authorized"])

    def test_gate_does_not_estimate_profit_factor_or_author_fidelity(self) -> None:
        r=decide(self.c)
        self.assertTrue(r["author_fidelity_not_measured_by_this_script"])
        self.assertTrue(r["profitability_not_measured"])


if __name__=="__main__":
    unittest.main()
