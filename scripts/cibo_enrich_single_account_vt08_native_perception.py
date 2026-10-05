#!/usr/bin/env python3
"""Enrich archived VT08 decisions with exact native B01 causal perception.

The native VT08 payload must be regenerated from raw M5/M15 causal sources using
cibo_phase22_vt08_fresh_runner after the setup_context transport repair.

Matching is exact on symbol, decision timestamp, side, entry, stop and target.
No realized_r, exit, P/L or outcome field is used for matching or perception.
"""

from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)


def _price(value: object) -> str:
    return format(Decimal(str(value)), "f")


def _native_key(row: dict[str, Any]) -> tuple[str, ...]:
    return (
        str(row["symbol"]),
        str(row["signal_at"]),
        str(row["side"]),
        _price(row["entry"]),
        _price(row["stop"]),
        _price(row["target"]),
    )


def _archived_key(row: dict[str, Any]) -> tuple[str, ...]:
    opportunity = row["trader_opportunity"]
    return (
        str(row["qore_symbol"]),
        str(row["market_decision_at"]),
        str(opportunity["side"]),
        _price(opportunity["intended_entry"]),
        _price(opportunity["stop_loss"]),
        _price(opportunity["take_profit"]),
    )


def enrich(
    manifest: dict[str, Any],
    native_payloads: tuple[dict[str, Any], ...],
) -> dict[str, Any]:
    native_by_key: dict[tuple[str, ...], dict[str, Any]] = {}
    for payload in native_payloads:
        rows = payload.get("opportunities")
        if not isinstance(rows, list):
            raise CiboCapitalManagementError(
                "VT08 native enrichment payload lacks opportunities"
            )
        for row in rows:
            if not isinstance(row, dict):
                raise CiboCapitalManagementError(
                    "VT08 native enrichment row invalid"
                )
            context = row.get("setup_context")
            if not isinstance(context, dict) or not context:
                raise CiboCapitalManagementError(
                    "VT08 native enrichment row lacks setup_context"
                )
            key = _native_key(row)
            if key in native_by_key:
                raise CiboCapitalManagementError(
                    "VT08 native enrichment duplicate exact causal identity"
                )
            native_by_key[key] = row

    opportunities = manifest.get("opportunities")
    if not isinstance(opportunities, list):
        raise CiboCapitalManagementError(
            "VT08 enrichment requires manifest opportunities"
        )

    enriched = 0
    blocked: list[dict[str, object]] = []
    result_rows: list[dict[str, Any]] = []
    for row in opportunities:
        if row.get("trader_id") != "VT08_FOREX":
            result_rows.append(row)
            continue

        key = _archived_key(row)
        native = native_by_key.get(key)
        if native is None:
            blocked.append(
                {
                    "signal_fingerprint": row.get("signal_fingerprint"),
                    "causal_key": list(key),
                    "reason": "no-exact-native-vt08-causal-match",
                }
            )
            result_rows.append(row)
            continue

        context = native["setup_context"]
        forbidden = (
            "outcome",
            "realized",
            "pnl",
            "mfe",
            "mae",
            "winner",
            "loser",
            "future",
        )
        if any(
            token in str(key_name).lower()
            for key_name in context
            for token in forbidden
        ):
            raise CiboCapitalManagementError(
                "VT08 native setup_context contains forbidden outcome field"
            )

        updated = dict(row)
        archived = dict(row["trader_opportunity"])
        existing = {
            str(item[0]): str(item[1])
            for item in archived.get("decision_context", [])
        }
        existing.update(
            {str(key_name): str(value) for key_name, value in context.items()}
        )
        archived["decision_context"] = [
            [key_name, value]
            for key_name, value in sorted(existing.items())
        ]
        updated["trader_opportunity"] = archived
        result_rows.append(updated)
        enriched += 1

    result = dict(manifest)
    result["opportunities"] = result_rows
    result["vt08_native_perception_enrichment"] = {
        "schema": "qore.cibo.vt08-native-perception-enrichment.v1",
        "attempted": sum(
            1
            for row in opportunities
            if row.get("trader_id") == "VT08_FOREX"
        ),
        "enriched": enriched,
        "blocked_count": len(blocked),
        "blocked": blocked,
        "native_candidate_count": len(native_by_key),
        "outcome_used": False,
        "future_lookup": False,
        "external_ai": False,
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument(
        "--native-vt08",
        action="append",
        type=Path,
        required=True,
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    payloads = tuple(
        json.loads(path.read_text(encoding="utf-8"))
        for path in args.native_vt08
    )
    result = enrich(manifest, payloads)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    summary = result["vt08_native_perception_enrichment"]
    print(json.dumps(summary, sort_keys=True))
    return 0 if summary["blocked_count"] == 0 else 3


if __name__ == "__main__":
    raise SystemExit(main())
