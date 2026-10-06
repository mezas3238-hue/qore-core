#!/usr/bin/env python3
"""Enrich frozen VT31 opportunities with Phase18 predecision semantics only.

The Phase18 bound-trade artifact contains both predecision state and later
research outcomes. This adapter is deliberately whitelist-only: it reads only
the exact decision-time fields required for CIBO research and refuses any
chronology or shared-context mismatch.

It does not use exit, PnL, MAE/MFE, journey labels or any other postdecision
field. The output is a new resealed research manifest; the frozen source
artifact is never mutated.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_single_account_manifest_integrity import (
    reseal_single_account_manifest,
    validate_single_account_manifest_sha256,
)

_TRADER = "VT31_NAS100"
_SOURCE_SHA256 = (
    "sha256:eb107bafd5cb6a31c0d2448c88610b3722c5dda7ca8910f9f1260533ce25d416"
)
_CONTEXT_KEYS = (
    "vt31_entry_family",
    "vt31_confirmation_latency_minutes",
    "vt31_risk_ref",
    "vt31_phase18_predecision_source_sha256",
)
_SHARED_FIELDS = (
    "cash_open_state",
    "h1_state",
    "h4_state",
    "premarket_state",
    "prior_day_state",
    "reference_volatility_state",
    "side",
)


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _load_source(path: Path) -> list[dict[str, Any]]:
    if _sha256(path) != _SOURCE_SHA256:
        raise CiboCapitalManagementError(
            "VT31 Phase18 predecision source digest drift"
        )
    rows: list[dict[str, Any]] = []
    for number, raw in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        if not raw.strip():
            continue
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise CiboCapitalManagementError(
                f"VT31 Phase18 row {number} must be mapping"
            )
        rows.append(value)
    if not rows:
        raise CiboCapitalManagementError("VT31 Phase18 source is empty")
    return rows


def _context(row: dict[str, Any]) -> dict[str, str]:
    raw = row["trader_opportunity"]["decision_context"]
    if not isinstance(raw, list):
        raise CiboCapitalManagementError(
            "VT31 frozen decision context must be pair list"
        )
    result: dict[str, str] = {}
    for item in raw:
        if not isinstance(item, list) or len(item) != 2:
            raise CiboCapitalManagementError(
                "VT31 frozen decision context entry invalid"
            )
        key = str(item[0])
        value = str(item[1])
        if key in result:
            raise CiboCapitalManagementError(
                "VT31 frozen decision context duplicate key"
            )
        result[key] = value
    return result


def _source_index(
    rows: list[dict[str, Any]],
) -> dict[tuple[str, str], dict[str, Any]]:
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        signal_at = row.get("signal_at")
        entry_price = row.get("entry_price")
        if not isinstance(signal_at, str) or not signal_at:
            raise CiboCapitalManagementError(
                "VT31 Phase18 signal_at missing"
            )
        if entry_price is None:
            raise CiboCapitalManagementError(
                "VT31 Phase18 entry_price missing"
            )
        key = (signal_at, str(entry_price))
        if key in result:
            raise CiboCapitalManagementError(
                "VT31 Phase18 predecision join key is not unique"
            )
        result[key] = row
    return result


def _whitelist_payload(source: dict[str, Any]) -> dict[str, str]:
    entry_family = source.get("entry_family")
    confirmation = source.get("confirmation_latency_minutes")
    risk_ref = source.get("risk_ref")
    if not isinstance(entry_family, str) or not entry_family:
        raise CiboCapitalManagementError(
            "VT31 Phase18 entry_family missing"
        )
    if (
        not isinstance(confirmation, int)
        or isinstance(confirmation, bool)
        or confirmation < 0
    ):
        raise CiboCapitalManagementError(
            "VT31 Phase18 confirmation latency invalid"
        )
    if risk_ref is None or not str(risk_ref):
        raise CiboCapitalManagementError(
            "VT31 Phase18 risk_ref missing"
        )
    return {
        "vt31_entry_family": entry_family,
        "vt31_confirmation_latency_minutes": str(confirmation),
        "vt31_risk_ref": str(risk_ref),
        "vt31_phase18_predecision_source_sha256": _SOURCE_SHA256,
    }


def enrich(
    manifest: dict[str, Any],
    *,
    source_rows: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    source_manifest_sha = validate_single_account_manifest_sha256(manifest)
    opportunities = manifest.get("opportunities")
    if not isinstance(opportunities, list):
        raise CiboCapitalManagementError(
            "frozen ceiling manifest opportunities missing"
        )

    source = _source_index(source_rows)
    enriched_rows: list[dict[str, Any]] = []
    vt31_count = 0
    non_vt31_count = 0

    for raw_row in opportunities:
        if not isinstance(raw_row, dict):
            raise CiboCapitalManagementError(
                "frozen ceiling opportunity row invalid"
            )
        row = json.loads(json.dumps(raw_row))
        if row.get("trader_id") != _TRADER:
            non_vt31_count += 1
            enriched_rows.append(row)
            continue

        vt31_count += 1
        context = _context(row)
        decision_at = context.get("decision_at")
        intended_entry = row["trader_opportunity"].get("intended_entry")
        if not isinstance(decision_at, str) or intended_entry is None:
            raise CiboCapitalManagementError(
                "VT31 frozen predecision join identity missing"
            )
        key = (decision_at, str(intended_entry))
        phase18 = source.get(key)
        if phase18 is None:
            raise CiboCapitalManagementError(
                "VT31 Phase18 predecision source row missing"
            )

        if phase18.get("signal_at") != decision_at:
            raise CiboCapitalManagementError(
                "VT31 Phase18 signal_at/decision_at chronology drift"
            )
        for name in _SHARED_FIELDS:
            if str(phase18.get(name)) != context.get(name):
                raise CiboCapitalManagementError(
                    "VT31 Phase18 shared predecision context drift: " + name
                )

        additions = _whitelist_payload(phase18)
        overlap = set(context).intersection(additions)
        if overlap:
            raise CiboCapitalManagementError(
                "VT31 enrichment context collision: "
                + ",".join(sorted(overlap))
            )
        context.update(additions)
        row["trader_opportunity"]["decision_context"] = [
            [key_name, value]
            for key_name, value in sorted(context.items())
        ]
        enriched_rows.append(row)

    if vt31_count != 484 or non_vt31_count != 2884:
        raise CiboCapitalManagementError(
            "VT31 frozen population count drift"
        )

    updated = dict(manifest)
    updated["opportunities"] = enriched_rows
    updated["vt31_phase18_predecision_enrichment"] = {
        "schema": "qore.cibo.vt31-phase18-predecision-enrichment.v1",
        "source_manifest_sha256": source_manifest_sha,
        "source_bound_trades_sha256": _SOURCE_SHA256,
        "enriched_trader_id": _TRADER,
        "enriched_opportunity_count": vt31_count,
        "context_keys_added": list(_CONTEXT_KEYS),
        "source_signal_at_equals_frozen_decision_at": True,
        "source_outcome_fields_read": False,
        "future_market_used": False,
        "outcome_used": False,
        "pnl_used": False,
        "post_entry_path_used": False,
        "sizing_authority": False,
        "risk_authority": False,
        "execution_authority": False,
        "broker_mutation": False,
        "certification_claimed": False,
        "research_only": True,
    }
    resealed = reseal_single_account_manifest(updated)
    receipt = {
        "source_manifest_sha256": source_manifest_sha,
        "enriched_manifest_sha256": (
            validate_single_account_manifest_sha256(resealed)
        ),
        **updated["vt31_phase18_predecision_enrichment"],
    }
    return resealed, receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--vt31-source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    source_rows = _load_source(args.vt31_source)
    enriched, receipt = enrich(manifest, source_rows=source_rows)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(enriched, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.receipt.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
