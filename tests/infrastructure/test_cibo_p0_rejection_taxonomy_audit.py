"""P0 Native CIBO rule-level blocker classifier: no gate loosening or PnL."""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "cibo_block_audit", HERE / "scripts/cibo_p0_rejection_taxonomy_audit.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def sensor(code: str, **metrics) -> dict:
    return {
        "function_code": code,
        "input_metrics": [],
        "output_metrics": list(metrics.items()),
        "decision_gate_triggered": False,
    }


def row(kind: str, idx: int, *, note=None, pause=False, profit=False, multi="1"):
    default_note = note or "nonpositive-causal-expected-net-utility"
    return {
        "signal_fingerprint": "sha256:" + f"{idx:064x}",
        "trader_id": "VT_TEST",
        "decided_at": "2020-01-01T10:00:00+00:00",
        "capital_disposition": kind,
        "risk_decision": "ALLOW" if kind == "RISK_REVIEW_READY" else "NOT_REQUESTED",
        "authorized_volume": ".01" if kind == "RISK_REVIEW_READY" else "0",
        "cognitive_sensors": [{
            "component_code": "CALIBRATION", "input_metrics": [],
            "output_metrics": [
                ["note", default_note],
                ["abstention_required", "True" if kind == "COGNITIVE_BLOCK" else "False"]
            ],
        }],
        "function_sensors": [
            sensor("CAPITAL_SCIENCE:GEN-C12", consumer_action=(
                "PAUSE_NEW_CAPITAL" if pause else "CRISIS_ENVELOPE_ALLOWS_CAPITAL"
            )),
            sensor("CIBO_COMPOUND", realized_profit_source_requested=(
                "True" if profit else "False"
            ), allow_incremental_compound="False"),
            sensor("COMPOUND_PORTFOLIO", multiplier=multi),
            sensor("POSITION_COMPETITION", admit_opportunity="True"),
        ],
    }


class Taxonomy(unittest.TestCase):
    def test_rejection_codes_and_priority_of_first_effective_gate(self):
        for note, expected in MODULE.COGNITIVE.items():
            with self.subTest(note=note):
                self.assertEqual(MODULE.classify(row("COGNITIVE_BLOCK", 1, note=note))[0], expected)
        self.assertEqual(
            MODULE.classify(row("CAPITAL_BLOCK", 2, profit=True, multi="0"))[0],
            MODULE.CAP_COMPOUND,
        )
        self.assertEqual(
            MODULE.classify(row("CAPITAL_BLOCK", 3, profit=True, multi="0", pause=True))[0],
            MODULE.CAP_PAUSE,
        )
        self.assertEqual(
            MODULE.classify(row("CAPITAL_BLOCK", 4, multi="0"))[0],
            MODULE.CAP_PORTFOLIO,
        )
        self.assertEqual(MODULE.classify(row("RISK_REVIEW_READY", 5))[0], MODULE.READY)

    def test_unknown_codes_cannot_be_recategorized(self):
        with self.assertRaises(MODULE.AuditMismatch):
            MODULE.classify(row("COGNITIVE_BLOCK", 1, note="unknown"))
        with self.assertRaises(MODULE.AuditMismatch):
            MODULE.classify(row("CAPITAL_BLOCK", 2, profit=False, multi="1"))
        corrupt = row("COGNITIVE_BLOCK", 3)
        corrupt["risk_decision"] = "ALLOW"
        with self.assertRaises(MODULE.AuditMismatch):
            MODULE.classify(corrupt)

    def test_full_census_blind_sample_and_manifest_causality(self):
        a = ([row("COGNITIVE_BLOCK", i) for i in range(1629)]
             + [row("COGNITIVE_BLOCK", i+1629,
                    note="walk-forward-provisional-forecast-history-required")
                for i in range(140)]
             + [row("COGNITIVE_BLOCK", i+1769,
                    note="walk-forward-cold-start-history-required")
                for i in range(35)])
        b = ([row("CAPITAL_BLOCK", i+1804, profit=True)
              for i in range(1549)]
             + [row("CAPITAL_BLOCK", i+3353, multi="0") for i in range(3)]
             + [row("CAPITAL_BLOCK", 3356, pause=True, profit=True)])
        c = [row("RISK_REVIEW_READY", i+3357) for i in range(11)]
        native = {"decision_receipts": a+b+c}
        manifest = {"opportunities": [
            {"signal_fingerprint":r["signal_fingerprint"],
             "market_decision_at":r["decided_at"],
             "qore_symbol":"AUDJPY"} for r in native["decision_receipts"]
        ]}
        p, census, sample = MODULE.audit(native, manifest)
        self.assertEqual(len(census), 3368)
        self.assertEqual(len(sample), 200)
        self.assertEqual(p["primary_counts"][MODULE.CAP_COMPOUND], 1549)
        self.assertEqual(p["primary_counts"][MODULE.CAP_PAUSE], 1)
        self.assertEqual(p["primary_counts"][MODULE.CAP_PORTFOLIO], 3)
        self.assertEqual(p["primary_counts"][MODULE.READY], 11)
        self.assertEqual(p["sample_sha256"], MODULE.audit(native, manifest)[0]["sample_sha256"])
        self.assertEqual(len({x["signal_fingerprint"] for x in sample}), 200)
        manifest["opportunities"][0]["market_decision_at"] = "2030-01-01T10:00:00+00:00"
        with self.assertRaises(MODULE.AuditMismatch):
            MODULE.audit(native, manifest)


if __name__ == "__main__":
    unittest.main()
