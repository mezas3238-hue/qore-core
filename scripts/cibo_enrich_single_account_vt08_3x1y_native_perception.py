#!/usr/bin/env python3
"""Rebuild native VT08 perception for the burned 3x1Y single-account population.

Only the read-only M15 evidence files from the immutable VT08 3x1Y lane artifact
are consumed.  Backtest outputs, exits, returns and other outcomes are never
read.  Every archived VT08 opportunity must reproduce the same side, entry,
stop and target under the native B01 evaluator before its causal setup_context
may be attached to the single-account manifest.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_phase22_vt08_fresh_engine import (
    candidate_setup_context,
)
from qore.infrastructure.cibo_single_account_manifest_integrity import (
    reseal_single_account_manifest,
    validate_single_account_manifest_sha256,
)
from qore.infrastructure.traders.vt08_b01_r3_8 import (
    Vt08B01Bar,
    evaluate_b01_at_entry_indexed,
)


_NATIVE_VERSION = "vt08-b01-r3-8-max-intelligence-v1"


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _dt(value: object, name: str) -> datetime:
    if not isinstance(value, str):
        raise CiboCapitalManagementError(f"VT08 3x1Y {name} must be string")
    result = datetime.fromisoformat(value)
    if result.tzinfo is None or result.utcoffset() is None:
        raise CiboCapitalManagementError(
            f"VT08 3x1Y {name} must be timezone-aware"
        )
    return result


def _evidence_files(roots: tuple[Path, ...]) -> tuple[Path, ...]:
    files: set[Path] = set()
    for root in roots:
        if root.is_file() and root.name == "evidence.json":
            files.add(root)
            continue
        if not root.is_dir():
            raise CiboCapitalManagementError(
                f"VT08 3x1Y evidence root missing: {root}"
            )
        files.update(root.glob("GROUP_*/*/evidence.json"))
        files.update(root.glob("*/evidence.json"))
    ordered = tuple(sorted(files))
    if not ordered:
        raise CiboCapitalManagementError(
            "VT08 3x1Y native enrichment found no evidence.json files"
        )
    return ordered


def load_vt08_3x1y_m15(
    roots: tuple[Path, ...],
) -> tuple[dict[str, dict[datetime, Vt08B01Bar]], tuple[str, ...]]:
    """Load/deduplicate only causal M15 market evidence by symbol."""

    by_symbol: dict[str, dict[datetime, Vt08B01Bar]] = {}
    source_ids: list[str] = []
    for path in _evidence_files(roots):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise CiboCapitalManagementError(
                "VT08 3x1Y evidence payload must be object"
            )
        governance = payload.get("governance")
        if not isinstance(governance, dict):
            raise CiboCapitalManagementError(
                "VT08 3x1Y evidence governance missing"
            )
        for key in (
            "broker_mutation",
            "live",
            "production",
            "real_capital",
            "outcome_used_for_evidence_construction",
        ):
            if governance.get(key) is not False:
                raise CiboCapitalManagementError(
                    f"VT08 3x1Y evidence governance drift: {key}"
                )
        if payload.get("read_only") is not True:
            raise CiboCapitalManagementError(
                "VT08 3x1Y evidence must be read-only"
            )
        source = payload.get("source")
        symbol_payload = payload.get("symbol")
        symbol = None
        if isinstance(source, dict):
            symbol = source.get("canonical_symbol")
        if not symbol and isinstance(symbol_payload, dict):
            symbol = symbol_payload.get("symbol_name")
        if not isinstance(symbol, str) or not symbol:
            raise CiboCapitalManagementError(
                "VT08 3x1Y evidence symbol missing"
            )
        periods = payload.get("periods")
        rows = periods.get("M15") if isinstance(periods, dict) else None
        if not isinstance(rows, list) or not rows:
            raise CiboCapitalManagementError(
                f"VT08 3x1Y {symbol} M15 evidence missing"
            )

        target = by_symbol.setdefault(symbol, {})
        for raw in rows:
            if not isinstance(raw, Mapping):
                raise CiboCapitalManagementError(
                    "VT08 3x1Y M15 row must be object"
                )
            opened_at = _dt(raw.get("opened_at"), "opened_at")
            closed_at = _dt(raw.get("closed_at"), "closed_at")
            bar = Vt08B01Bar(
                opened_at=opened_at,
                closed_at=closed_at,
                open=_d(raw.get("open")),
                high=_d(raw.get("high")),
                low=_d(raw.get("low")),
                close=_d(raw.get("close")),
            )
            prior = target.get(opened_at)
            if prior is not None and prior != bar:
                raise CiboCapitalManagementError(
                    f"VT08 3x1Y duplicate M15 OHLC drift: {symbol} {opened_at}"
                )
            target[opened_at] = bar
        source_ids.append(str(path))
    return by_symbol, tuple(source_ids)


def _archived_geometry(row: Mapping[str, Any]) -> tuple[str, Decimal, Decimal, Decimal]:
    payload = row.get("trader_opportunity")
    if not isinstance(payload, Mapping):
        raise CiboCapitalManagementError(
            "VT08 3x1Y manifest trader_opportunity missing"
        )
    return (
        str(payload.get("side")),
        _d(payload.get("intended_entry")),
        _d(payload.get("stop_loss")),
        _d(payload.get("take_profit")),
    )


def enrich(
    manifest: dict[str, Any],
    bars_by_symbol: Mapping[str, dict[datetime, Vt08B01Bar]],
    *,
    source_ids: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Attach only exact, reproducible native VT08 predecision perception."""

    source_manifest_sha256 = validate_single_account_manifest_sha256(manifest)
    rows = manifest.get("opportunities")
    if not isinstance(rows, list):
        raise CiboCapitalManagementError(
            "VT08 3x1Y enrichment requires manifest opportunities"
        )

    attempted = 0
    enriched = 0
    blocked: list[dict[str, object]] = []
    result_rows: list[dict[str, Any]] = []
    for raw in rows:
        if not isinstance(raw, dict):
            raise CiboCapitalManagementError(
                "VT08 3x1Y manifest opportunity must be object"
            )
        if raw.get("trader_id") != "VT08_FOREX":
            result_rows.append(raw)
            continue

        attempted += 1
        signal = str(raw.get("signal_fingerprint"))
        symbol = str(raw.get("qore_symbol"))
        decision_at = _dt(raw.get("market_decision_at"), "market_decision_at")
        bars = bars_by_symbol.get(symbol)
        if not bars:
            blocked.append(
                {
                    "signal_fingerprint": signal,
                    "symbol": symbol,
                    "reason": "no-causal-m15-evidence-for-symbol",
                }
            )
            result_rows.append(raw)
            continue

        try:
            evaluation = evaluate_b01_at_entry_indexed(
                symbol=symbol,
                bars_by_open=bars,
                decision_at=decision_at,
            )
            candidate = evaluation.candidate
            if candidate is None:
                reason = getattr(evaluation, "abstain_reason", None)
                raise CiboCapitalManagementError(
                    "native-b01-no-candidate:"
                    + ("unknown" if reason is None else str(reason))
                )
            wanted = _archived_geometry(raw)
            observed = (
                candidate.side.value,
                candidate.setup.entry_price,
                candidate.setup.invalidation_price,
                candidate.setup.take_profit_price,
            )
            if observed != wanted:
                raise CiboCapitalManagementError(
                    "native-b01-geometry-drift"
                )
            context = {
                **candidate_setup_context(candidate),
                "cibo_native_perception_complete": "true",
                "cibo_native_perception_version": _NATIVE_VERSION,
            }
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
                token in key.lower()
                for key in context
                for token in forbidden
            ):
                raise CiboCapitalManagementError(
                    "VT08 3x1Y reconstructed context contains forbidden field"
                )

            updated = dict(raw)
            opportunity = dict(raw["trader_opportunity"])
            existing = {
                str(item[0]): str(item[1])
                for item in opportunity.get("decision_context", [])
            }
            existing.update(context)
            opportunity["decision_context"] = [
                [key, value] for key, value in sorted(existing.items())
            ]
            updated["trader_opportunity"] = opportunity
            result_rows.append(updated)
            enriched += 1
        except Exception as error:
            blocked.append(
                {
                    "signal_fingerprint": signal,
                    "symbol": symbol,
                    "reason": str(error),
                }
            )
            result_rows.append(raw)

    result = dict(manifest)
    result["opportunities"] = result_rows
    result["vt08_3x1y_native_perception_enrichment"] = {
        "schema": "qore.cibo.vt08-3x1y-native-perception-enrichment.v1",
        "source_manifest_sha256": source_manifest_sha256,
        "attempted": attempted,
        "enriched": enriched,
        "blocked_count": len(blocked),
        "blocked": blocked,
        "source_evidence_files": list(source_ids),
        "outcome_files_read": False,
        "outcome_used": False,
        "future_lookup": False,
        "external_ai": False,
        "broker_mutation": False,
        "certification_claimed": False,
    }
    return reseal_single_account_manifest(result)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument(
        "--evidence-root",
        action="append",
        type=Path,
        required=True,
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    bars, source_ids = load_vt08_3x1y_m15(tuple(args.evidence_root))
    result = enrich(manifest, bars, source_ids=source_ids)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    summary = result["vt08_3x1y_native_perception_enrichment"]
    print(json.dumps(summary, sort_keys=True))
    return 0 if summary["blocked_count"] == 0 else 3


if __name__ == "__main__":
    raise SystemExit(main())
