from __future__ import annotations

import importlib.util
import json
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType

CATALOG_SHA = "4c10aede99704b937caa772e1ae07257c8e12c3d0644c06ca751b6885b9a363f"


def _load_runner() -> ModuleType:
    path = (
        Path(__file__).resolve().parents[2]
        / "scripts"
        / "shared_global_sensor_registry_from_catalog.py"
    )
    spec = importlib.util.spec_from_file_location(
        "shared_global_sensor_registry_from_catalog",
        path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_catalog_materializes_discovery_only_registry(tmp_path: Path) -> None:
    catalog = {
        "identity": "QORE_SHARED_WP05_POST_V14_PROVIDER_CATALOG_AUDIT_001",
        "provider_catalog_sha256": CATALOG_SHA,
        "enabled_symbol_count": 3,
        "enabled_symbols": [
            {
                "provider_symbol_id": 10012,
                "provider_symbol": "US2000",
                "normalized_symbol": "US2000",
            },
            {
                "provider_symbol_id": 41,
                "provider_symbol": "XAUUSD",
                "normalized_symbol": "XAUUSD",
            },
            {
                "provider_symbol_id": 10019,
                "provider_symbol": "XTIUSD",
                "normalized_symbol": "XTIUSD",
            },
        ],
        "candidate_selection_performed": False,
        "historical_market_data_read": False,
        "target_or_outcome_read": False,
    }
    source = tmp_path / "catalog.json"
    output = tmp_path / "registry.json"
    source.write_text(json.dumps(catalog), encoding="utf-8")

    report = _load_runner().run(
        catalog_path=source,
        output_path=output,
        provider="CTRADER_DEMO",
        expected_catalog_sha256=CATALOG_SHA,
        catalog_frozen_at=datetime(2026, 9, 29, 11, 29, 45, tzinfo=UTC),
        source_run_id=36561967069,
        source_artifact_id=11030242325,
        source_git_sha="420e6aca7b450a3e215c28dbab4a3efb13ece04a",
    )

    assert report["sensor_count"] == 3
    assert report["disposition_counts"] == {
        "DISCOVERED": 3,
        "QUALIFYING": 0,
        "OBSERVE_ONLY": 0,
        "ADMITTED": 0,
        "REJECTED": 0,
    }
    assert report["all_sensor_families_unclassified"] is True
    assert report["provider_discovery_is_not_scientific_admission"] is True
    assert report["current_trader_universe_defines_ceiling"] is False
    assert report["target_or_outcome_read"] is False
    assert report["execution_authority"] is False
    assert report["risk_authority"] is False
