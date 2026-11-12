"""The CRT release report must not be unlockable by changing flags alone."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from research.crt_r4a_holdout.crt_operational_release_preflight import (
    SCHEMA,
    evaluate,
)
from research.crt_r4a_holdout.runner import SYMBOLS

REPO = Path(__file__).resolve().parents[3]


def test_current_research_repo_is_blocked() -> None:
    report = evaluate(REPO)
    assert report.status == "BLOCKED_NOT_CERTIFIABLE"
    assert report.schema == SCHEMA
    assert not report.release_authorized
    assert not report.live_execution_allowed
    assert report.supported_market_catalog == 34
    assert report.historical_broker_coverage == 0
    assert report.historical_economic_trades_certified == 0
    statuses = {item.id: item.status for item in report.checks}
    assert statuses["01_CATALOG_34"] == "PASS"
    assert statuses["05_NATIVE_SERVER_SLTP_ORDER"] == "BLOCKED"
    assert statuses["08_UNSEEN_24M_HOLDOUT"] == "BLOCKED"
    assert statuses["09_OOS_POSITIVE_EDGE_NET"] == "BLOCKED"
    assert len(statuses) == 11


def _create_minimal_repo(tmp_path: Path) -> Path:
    manifest_path = tmp_path / "research/crt_r4a_holdout/data/manifest.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(
        json.dumps({
            "quotes": {symbol: None for symbol in SYMBOLS},
            "window_consumed_for_crt_research": True,
            "parity_verified": False,
            "costs_verified": False,
            "provider_data_verified": False,
        }),
        encoding="utf-8",
    )
    infra = tmp_path / "src/qore/infrastructure"
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
    return tmp_path


def test_self_asserted_manifest_flags_cannot_certify(tmp_path: Path) -> None:
    root = _create_minimal_repo(tmp_path)
    manifest_path = root / "research/crt_r4a_holdout/data/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["parity_verified"] = True
    manifest["costs_verified"] = True
    manifest["provider_data_verified"] = True
    manifest["holdout_unseen_attested"] = True
    manifest["window_consumed_for_crt_research"] = False
    manifest["quotes"] = {symbol: {"sha256": "a" * 64} for symbol in SYMBOLS}
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    report = evaluate(root)
    assert report.status == "BLOCKED_NOT_CERTIFIABLE"
    assert all(
        item.status != "PASS"
        for item in report.checks
        if item.id != "01_CATALOG_34"
    )
    assert "manifest flag alone is insufficient" in str(report.to_dict())


def test_missing_btc_market_fails_manifest_identity(tmp_path: Path) -> None:
    root = _create_minimal_repo(tmp_path)
    path = root / "research/crt_r4a_holdout/data/manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["quotes"].pop("BTCUSD")
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="34-market"):
        evaluate(root)


def test_adding_wire_tokens_is_not_actual_authorization(tmp_path: Path) -> None:
    root = _create_minimal_repo(tmp_path)
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
    assert checks["05_NATIVE_SERVER_SLTP_ORDER"] == "PASS_STATIC_ONLY"
    assert report.status == "BLOCKED_NOT_CERTIFIABLE"
    assert not report.release_authorized


def test_missing_manifest_is_a_hard_error(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="manifest"):
        evaluate(tmp_path)
