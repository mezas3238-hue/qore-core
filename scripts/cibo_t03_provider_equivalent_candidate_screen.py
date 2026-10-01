"""Screen the full cTrader DEMO catalog for direct T03 equivalents.

This is a conservative provider-catalog screen. It may identify only distinct,
enabled, single-instrument listings with the same provider description as a
governed target. It never claims that description equality proves normalized
exposure equivalence, and it never rules out multi-leg synthetics or a future
provider universe.

The screen is read-only, target/outcome independent and does not consume the
2017H1 holdout.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

_TARGETS = {
    "AUDJPY": ("AUDJPY", "Australian Dollar vs Japanese Yen"),
    "EURUSD": ("EURUSD", "Euro vs US Dollar"),
    "GBPJPY": ("GBPJPY", "British Pound vs Japanese Yen"),
    "GBPUSD": ("GBPUSD", "British Pound vs US Dollar"),
    "NAS100": ("USTEC", "USA NASDAQ 100 Index"),
    "XAUUSD": ("XAUUSD", "Gold vs US Dollar"),
}


def build_report(account_payload: dict[str, Any]) -> dict[str, object]:
    if account_payload.get("provider_key") != "ctrader-demo":
        raise ValueError("T03 catalog screen requires ctrader-demo evidence")
    if account_payload.get("environment") != "demo":
        raise ValueError("T03 catalog screen requires DEMO evidence")
    if account_payload.get("taxonomy_binding_complete") is not True:
        raise ValueError("T03 catalog screen requires complete taxonomy binding")
    symbols = account_payload.get("symbols")
    if not isinstance(symbols, list) or not symbols:
        raise ValueError("T03 catalog screen requires full symbol catalog")

    catalog_sha = account_payload.get("catalog_sha256")
    if not isinstance(catalog_sha, str) or not catalog_sha.startswith("sha256:"):
        raise ValueError("T03 catalog screen requires catalog SHA-256")

    rows: list[dict[str, object]] = []
    enabled_candidates_total = 0
    disabled_same_identity_total = 0
    for qore_symbol, (target_provider_symbol, target_description) in _TARGETS.items():
        exact = [
            item
            for item in symbols
            if isinstance(item, dict)
            and item.get("description") == target_description
        ]
        target = [
            item
            for item in exact
            if item.get("symbol_name") == target_provider_symbol
        ]
        if len(target) != 1 or target[0].get("enabled") is not True:
            raise ValueError(
                f"T03 target provider identity unavailable: {qore_symbol}"
            )
        distinct = [
            item
            for item in exact
            if item.get("symbol_name") != target_provider_symbol
        ]
        enabled = [
            str(item.get("symbol_name"))
            for item in distinct
            if item.get("enabled") is True
        ]
        disabled = [
            str(item.get("symbol_name"))
            for item in distinct
            if item.get("enabled") is False
        ]
        enabled_candidates_total += len(enabled)
        disabled_same_identity_total += len(disabled)
        rows.append(
            {
                "qore_symbol": qore_symbol,
                "target_provider_symbol": target_provider_symbol,
                "provider_description": target_description,
                "enabled_distinct_same_description_candidates": sorted(enabled),
                "disabled_distinct_same_description_candidates": sorted(disabled),
                "direct_candidate_identified": bool(enabled),
            }
        )

    return {
        "schema": "qore.cibo.t03.provider_direct_candidate_screen.v1",
        "provider_key": "ctrader-demo",
        "environment": "demo",
        "account_fingerprint_sha256": account_payload.get(
            "account_fingerprint_sha256"
        ),
        "catalog_sha256": catalog_sha,
        "catalog_observed_at": account_payload.get("observed_at"),
        "symbol_count": account_payload.get("symbol_count"),
        "taxonomy_binding_complete": True,
        "targets": rows,
        "enabled_direct_candidate_count": enabled_candidates_total,
        "disabled_same_identity_count": disabled_same_identity_total,
        "direct_single_instrument_candidate_identified": (
            enabled_candidates_total > 0
        ),
        "normalized_exposure_equivalence_proven": False,
        "multi_leg_synthetic_universe_exhausted": False,
        "alternate_provider_universe_exhausted": False,
        "holdout_outcomes_used": False,
        "holdout_market_data_read": False,
        "broker_mutation_performed": False,
        "productive_authority": False,
        "status": (
            "DIRECT_PROVIDER_CANDIDATE_IDENTIFIED_REQUIRES_EQUIVALENCE_PROOF"
            if enabled_candidates_total > 0
            else "NO_DISTINCT_ENABLED_DIRECT_PROVIDER_EQUIVALENT_CANDIDATE"
        ),
        "blockers": (
            [
                "DIRECT_CANDIDATE_REQUIRES_NORMALIZED_EXPOSURE_AND_ECONOMIC_PROOF"
            ]
            if enabled_candidates_total > 0
            else [
                "MULTI_LEG_OR_ALTERNATE_PROVIDER_EQUIVALENT_EXPRESSION_NOT_PROVEN"
            ]
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--account", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = json.loads(args.account.read_text(encoding="utf-8"))
    report = build_report(payload)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
