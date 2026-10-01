from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def _load_module() -> ModuleType:
    path = Path("scripts/cibo_t03_provider_equivalent_candidate_screen.py")
    spec = importlib.util.spec_from_file_location(
        "cibo_t03_provider_equivalent_candidate_screen",
        path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load T03 provider candidate screen")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


screen = _load_module()


def _catalog() -> dict:
    targets = {
        "AUDJPY": "Australian Dollar vs Japanese Yen",
        "EURUSD": "Euro vs US Dollar",
        "GBPJPY": "British Pound vs Japanese Yen",
        "GBPUSD": "British Pound vs US Dollar",
        "USTEC": "USA NASDAQ 100 Index",
        "XAUUSD": "Gold vs US Dollar",
    }
    symbols = [
        {
            "symbol_id": index,
            "symbol_name": symbol,
            "enabled": True,
            "description": description,
        }
        for index, (symbol, description) in enumerate(
            targets.items(),
            start=1,
        )
    ]
    symbols.append(
        {
            "symbol_id": 99,
            "symbol_name": "EURUSDt",
            "enabled": False,
            "description": "Euro vs US Dollar",
        }
    )
    return {
        "provider_key": "ctrader-demo",
        "environment": "demo",
        "account_fingerprint_sha256": "a" * 64,
        "catalog_sha256": "sha256:" + "b" * 64,
        "observed_at": "2026-10-01T04:01:14+00:00",
        "symbol_count": len(symbols),
        "taxonomy_binding_complete": True,
        "symbols": symbols,
    }


def test_t03_direct_screen_does_not_promote_disabled_duplicate() -> None:
    report = screen.build_report(_catalog())

    assert report["enabled_direct_candidate_count"] == 0
    assert report["disabled_same_identity_count"] == 1
    assert report["direct_single_instrument_candidate_identified"] is False
    assert report["normalized_exposure_equivalence_proven"] is False
    assert report["multi_leg_synthetic_universe_exhausted"] is False
    assert report["alternate_provider_universe_exhausted"] is False
    assert report["holdout_outcomes_used"] is False
    assert report["broker_mutation_performed"] is False
    assert report["productive_authority"] is False
    assert report["status"] == (
        "NO_DISTINCT_ENABLED_DIRECT_PROVIDER_EQUIVALENT_CANDIDATE"
    )
    assert report["blockers"] == [
        "MULTI_LEG_OR_ALTERNATE_PROVIDER_EQUIVALENT_EXPRESSION_NOT_PROVEN"
    ]


def test_t03_direct_screen_surfaces_enabled_duplicate_without_certifying_it() -> None:
    payload = _catalog()
    payload["symbols"].append(
        {
            "symbol_id": 100,
            "symbol_name": "EURUSD_ALT",
            "enabled": True,
            "description": "Euro vs US Dollar",
        }
    )
    payload["symbol_count"] += 1

    report = screen.build_report(payload)

    assert report["enabled_direct_candidate_count"] == 1
    assert report["direct_single_instrument_candidate_identified"] is True
    assert report["normalized_exposure_equivalence_proven"] is False
    assert report["status"] == (
        "DIRECT_PROVIDER_CANDIDATE_IDENTIFIED_REQUIRES_EQUIVALENCE_PROOF"
    )
