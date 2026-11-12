"""CRT release readiness is permanently fail-closed on self-declarations."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from research.crt_r4a_holdout.crt_operational_release_preflight import (
    SCHEMA,
    evaluate,
)
from research.crt_r4a_holdout.runner import SYMBOLS

REPO = Path(__file__).resolve().parents[3]


def _make_fake_repo(root: Path) -> None:
    manifest = root / "research/crt_r4a_holdout/data/manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        json.dumps({
            "quotes": {symbol: None for symbol in SYMBOLS},
            "window_consumed_for_crt_research": True,
            "parity_verified": False,
            "costs_verified": False,
            "provider_data_verified": False,
        }),
        encoding="utf-8",
    )
    infra = root / "src/qore/infrastructure"
    infra.mkdir(parents=True)
    (infra / "ctrader_open_api_transport.py").write_text(
        "    def submit_order(self):\n        fields = {}\n"
        "    def cancel_order(self):\n        pass\n",
        encoding="utf-8",
    )
    (infra / "ctrader_demo_execution_codec.py").write_text(
        "def build_ctrader_demo_order_create_plan():\n"
        "    body = {}\n\n@dataclass()\nclass Dummy:\n    pass\n",
        encoding="utf-8",
    )


class CRTReleaseGateQA(unittest.TestCase):
    def test_01_actual_repo_is_blocked(self) -> None:
        report = evaluate(REPO)
        self.assertEqual(report.status, "BLOCKED_NOT_CERTIFIABLE")
        self.assertEqual(report.schema, SCHEMA)
        self.assertFalse(report.release_authorized)
        self.assertFalse(report.live_execution_allowed)
        self.assertEqual(report.supported_market_catalog, 34)
        self.assertEqual(report.historical_broker_coverage, 0)
        self.assertEqual(report.historical_economic_trades_certified, 0)
        statuses = {item.id: item.status for item in report.checks}
        self.assertEqual(statuses["01_CATALOG_34"], "PASS")
        for code in (
            "05_NATIVE_SERVER_SLTP_ORDER",
            "08_UNSEEN_24M_HOLDOUT",
            "09_OOS_POSITIVE_EDGE_NET",
        ):
            self.assertEqual(statuses[code], "BLOCKED")
        self.assertEqual(len(statuses), 11)

    def test_02_self_attested_flags_never_certify(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            _make_fake_repo(root)
            path = root / "research/crt_r4a_holdout/data/manifest.json"
            manifest = json.loads(path.read_text(encoding="utf-8"))
            manifest.update({
                "parity_verified": True,
                "costs_verified": True,
                "provider_data_verified": True,
                "holdout_unseen_attested": True,
                "window_consumed_for_crt_research": False,
                "quotes": {
                    symbol: {"sha256": "a" * 64}
                    for symbol in SYMBOLS
                },
            })
            path.write_text(json.dumps(manifest), encoding="utf-8")
            report = evaluate(root)
            self.assertEqual(report.status, "BLOCKED_NOT_CERTIFIABLE")
            self.assertTrue(all(
                item.status != "PASS"
                for item in report.checks
                if item.id != "01_CATALOG_34"
            ))
            self.assertIn("manifest flag alone is insufficient", str(report.to_dict()))

    def test_03_missing_btc_does_not_pass_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            _make_fake_repo(root)
            path = root / "research/crt_r4a_holdout/data/manifest.json"
            manifest = json.loads(path.read_text(encoding="utf-8"))
            manifest["quotes"].pop("BTCUSD")
            path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "34-market"):
                evaluate(root)

    def test_04_dummy_native_fields_do_not_grant_authority(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            _make_fake_repo(root)
            infra = root / "src/qore/infrastructure"
            (infra / "ctrader_open_api_transport.py").write_text(
                "    def submit_order(self):\n"
                "        fields = {}\n"
                '        fields["relativeStopLoss"] = 100\n'
                '        fields["relativeTakeProfit"] = 100\n'
                "    def cancel_order(self):\n        pass\n",
                encoding="utf-8",
            )
            (infra / "ctrader_demo_execution_codec.py").write_text(
                "def build_ctrader_demo_order_create_plan():\n"
                '    body = {"relativeStopLoss": 100, "relativeTakeProfit": 100}\n\n'
                "@dataclass()\nclass Dummy:\n    pass\n",
                encoding="utf-8",
            )
            report = evaluate(root)
            checks = {item.id: item.status for item in report.checks}
            self.assertEqual(checks["05_NATIVE_SERVER_SLTP_ORDER"], "PASS_STATIC_ONLY")
            self.assertEqual(report.status, "BLOCKED_NOT_CERTIFIABLE")
            self.assertFalse(report.release_authorized)

    def test_05_missing_manifest_is_hard_error(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            with self.assertRaisesRegex(FileNotFoundError, "manifest"):
                evaluate(Path(name))


if __name__ == "__main__":
    unittest.main(verbosity=2)
