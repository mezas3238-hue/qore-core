#!/usr/bin/env python3
"""Validate GC futures contract identity against sealed provider metadata."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast

IDENTITY = "QORE_SHARED_GW2_GC_FUTURES_CONTRACT_BINDING_001"
EXPECTED_PROVIDER_IDENTITY = "QORE_SHARED_GEN2_CTRADER_PROVIDER_SCHEDULE_CATALOG_001"
EXPECTED_AUTHORITY_IDENTITY = "QORE_SHARED_GW2_GC_FUTURES_CONTRACT_AUTHORITY_EVIDENCE_001"
MONTH_CODES = {
    "F": 1,
    "G": 2,
    "H": 3,
    "J": 4,
    "K": 5,
    "M": 6,
    "N": 7,
    "Q": 8,
    "U": 9,
    "V": 10,
    "X": 11,
    "Z": 12,
}


def run(
    *,
    provider_schedule: Path,
    authority_evidence: Path,
    output: Path,
) -> dict[str, object]:
    provider = json.loads(provider_schedule.read_text())
    authority = json.loads(authority_evidence.read_text())
    if provider.get("identity") != EXPECTED_PROVIDER_IDENTITY:
        raise ValueError("unexpected provider schedule")
    if authority.get("identity") != EXPECTED_AUTHORITY_IDENTITY:
        raise ValueError("unexpected GC authority evidence")

    raw_symbols = provider.get("symbols")
    if not isinstance(raw_symbols, list):
        raise ValueError("provider symbols missing")
    symbols = {
        str(row.get("provider_symbol")): cast(dict[str, Any], row)
        for row in raw_symbols
        if isinstance(row, dict)
    }

    bindings = authority.get("provider_contract_bindings")
    if not isinstance(bindings, list) or len(bindings) != 5:
        raise ValueError("expected five GC contract bindings")

    records: list[dict[str, object]] = []
    for raw in bindings:
        if not isinstance(raw, dict):
            raise ValueError("invalid GC binding")
        binding = cast(dict[str, Any], raw)
        symbol = str(binding["provider_symbol"])
        row = symbols.get(symbol)
        if row is None:
            raise ValueError(f"missing provider GC contract {symbol}")
        description = str(row.get("provider_description", ""))
        if description != str(binding["expected_provider_description"]):
            raise ValueError(f"{symbol} description drift")

        if not symbol.startswith("GC") or len(symbol) != 5:
            raise ValueError(f"{symbol} is not expected GC display-code shape")
        month_code = symbol[2]
        year_text = symbol[3:]
        if MONTH_CODES.get(month_code) != int(binding["contract_month"]):
            raise ValueError(f"{symbol} month-code mismatch")
        if int("20" + year_text) != int(binding["contract_year"]):
            raise ValueError(f"{symbol} year-code mismatch")
        if month_code != str(binding["contract_month_code"]):
            raise ValueError(f"{symbol} authority month code mismatch")

        records.append(
            {
                "provider_symbol": symbol,
                "provider_description": description,
                "canonical_product": binding["canonical_product"],
                "product_code": binding["product_code"],
                "venue": "COMEX",
                "economic_underlying": "GOLD",
                "contract_size": "100_TROY_OUNCES",
                "pricing_currency": "USD",
                "contract_month_code": month_code,
                "contract_month": binding["contract_month"],
                "contract_month_name": binding["contract_month_name"],
                "contract_year": binding["contract_year"],
                "contract_identity_verified": True,
                "front_contract_status": "UNRESOLVED",
                "most_liquid_status": "UNRESOLVED",
                "roll_status": "UNRESOLVED",
                "continuous_series_status": "UNRESOLVED",
            }
        )

    records.sort(key=lambda item: str(item["provider_symbol"]))
    result = {
        "identity": IDENTITY,
        "status": "GW2_GC_FUTURES_CONTRACT_IDENTITIES_BOUND",
        "records": records,
        "provider_gc_contract_count": len(records),
        "contract_identity_verified_count": len(records),
        "front_contract_verified_count": 0,
        "roll_semantics_verified_count": 0,
        "continuous_series_verified_count": 0,
        "sensor_admission_authorized": False,
        "relational_claims_authorized": False,
        "protected_holdout_opened": False,
        "productive_authority": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider-schedule", type=Path, required=True)
    parser.add_argument("--authority-evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    p = run(
        provider_schedule=args.provider_schedule,
        authority_evidence=args.authority_evidence,
        output=args.output,
    )
    print(
        json.dumps(
            {
                "status": p["status"],
                "provider_gc_contract_count": p["provider_gc_contract_count"],
                "contract_identity_verified_count": p[
                    "contract_identity_verified_count"
                ],
                "roll_semantics_verified_count": p[
                    "roll_semantics_verified_count"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
