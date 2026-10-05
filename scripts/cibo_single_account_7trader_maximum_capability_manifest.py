#!/usr/bin/env python3
"""Assemble one continuous 7-Trader maximum-capability research population.

This script does not perform economic decisions. It creates the immutable
chronological input manifest that Trader Lab must feed to the sovereign CIBO
runtime. Three reusable/burned research eras become one account history with no
capital reset at era boundaries.

The output is NON-CERTIFYING research evidence. Outcomes may remain attached to
rows for later settlement evaluation, but the manifest never exposes them as
predecision inputs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_single_account_maximum_capability import (
    CIBO_MAXIMUM_CAPABILITY_INITIAL_CAPITAL_USD,
    CIBO_MAXIMUM_CAPABILITY_TRADERS,
)


def _dt(value: object) -> datetime:
    if not isinstance(value, str):
        raise CiboCapitalManagementError(
            "single-account manifest timestamp must be string"
        )
    result = datetime.fromisoformat(value)
    if result.tzinfo is None or result.utcoffset() is None:
        raise CiboCapitalManagementError(
            "single-account manifest timestamp must be timezone-aware"
        )
    return result


def _sha(payload: object) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _load_trace(path: Path, index: int) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("opportunities")
    if not isinstance(rows, list) or not rows:
        raise CiboCapitalManagementError(
            f"single-account trace {index} has no opportunities"
        )
    trace_sha = payload.get("trace_sha256")
    if not isinstance(trace_sha, str) or not trace_sha.startswith("sha256:"):
        raise CiboCapitalManagementError(
            f"single-account trace {index} missing trace digest"
        )
    return payload


def build_manifest(
    traces: tuple[dict[str, Any], ...],
) -> dict[str, Any]:
    if not traces:
        raise CiboCapitalManagementError(
            "single-account manifest requires at least one trace"
        )

    combined: list[dict[str, Any]] = []
    era_rows: list[dict[str, Any]] = []
    signals: set[str] = set()
    epochs: set[tuple[str, str]] = set()
    trader_counts: Counter[str] = Counter()

    for era_index, trace in enumerate(traces, start=1):
        rows = trace["opportunities"]
        era_decisions = [_dt(row["market_decision_at"]) for row in rows]
        era_rows.append(
            {
                "era_index": era_index,
                "source_trace_sha256": trace["trace_sha256"],
                "opportunity_count": len(rows),
                "first_market_decision_at": min(era_decisions).isoformat(),
                "last_market_decision_at": max(era_decisions).isoformat(),
                "capital_reset_at_start": False,
            }
        )
        for row in rows:
            signal = str(row["signal_fingerprint"])
            if signal in signals:
                raise CiboCapitalManagementError(
                    "single-account population contains duplicate signal"
                )
            signals.add(signal)
            trader_id = str(row["trader_id"])
            trader_counts[trader_id] += 1

            decision_at = _dt(row["market_decision_at"])
            epoch_id = str(row["decision_epoch_id"])
            epoch_key = (decision_at.isoformat(), epoch_id)
            epochs.add(epoch_key)

            combined.append(
                {
                    "era_index": era_index,
                    "source_trace_sha256": trace["trace_sha256"],
                    "decision_epoch_id": epoch_id,
                    "market_decision_at": decision_at.isoformat(),
                    "trader_id": trader_id,
                    "qore_symbol": str(row["qore_symbol"]),
                    "signal_fingerprint": signal,
                    "decision_evidence_sha256": str(
                        row["decision_evidence_sha256"]
                    ),
                    "trader_opportunity": row["trader_opportunity"],
                    "market_predecision_state": row.get(
                        "market_predecision_state"
                    ),
                    "ce2i_predecision_evidence": row.get("ce2i"),
                    # Outcome is retained only for chronological settlement.
                    # Sovereign predecision consumers must never receive it.
                    "settlement_outcome_research_only": row.get(
                        "evaluation_outcome"
                    ),
                    "outcome_available_to_predecision": False,
                }
            )

    canonical_traders = tuple(item.value for item in CIBO_MAXIMUM_CAPABILITY_TRADERS)
    observed_traders = tuple(sorted(trader_counts))
    if observed_traders != tuple(sorted(canonical_traders)):
        raise CiboCapitalManagementError(
            "single-account population does not cover exact seven Traders"
        )

    combined.sort(
        key=lambda row: (
            row["market_decision_at"],
            row["decision_epoch_id"],
            row["signal_fingerprint"],
        )
    )
    decision_times = [_dt(row["market_decision_at"]) for row in combined]
    if decision_times != sorted(decision_times):
        raise CiboCapitalManagementError(
            "single-account population chronology is not monotonic"
        )

    era_rows.sort(key=lambda row: row["era_index"])
    for previous, current in zip(era_rows, era_rows[1:]):
        if _dt(current["first_market_decision_at"]) < _dt(
            previous["first_market_decision_at"]
        ):
            raise CiboCapitalManagementError(
                "single-account era order is reversed"
            )

    manifest_core = {
        "schema": "qore.cibo.single-account-7trader-maximum-capability.v1",
        "initial_capital_usd": format(
            CIBO_MAXIMUM_CAPABILITY_INITIAL_CAPITAL_USD,
            "f",
        ),
        "account_count": 1,
        "account_reset_count": 0,
        "economic_era_reset_count": 0,
        "continuous_realized_profit_compound": True,
        "shared_portfolio_state": True,
        "shared_qore_risk_state": True,
        "sovereign_cibo_required": True,
        "full_cognitive_semantics_required": True,
        "target_capital_used_for_tuning": False,
        "opportunity_decision_count": len(combined),
        "decision_epoch_count": len(epochs),
        "trader_ids": list(canonical_traders),
        "trader_opportunity_counts": {
            trader: trader_counts[trader] for trader in canonical_traders
        },
        "eras": era_rows,
        "first_market_decision_at": decision_times[0].isoformat(),
        "last_market_decision_at": decision_times[-1].isoformat(),
        "opportunities": combined,
        "governance": {
            "reused_burned_research_population": True,
            "fresh_oos_claimed": False,
            "certification_claimed": False,
            "outcome_aware_tuning": False,
            "broker_mutation": False,
            "live": False,
            "production": False,
            "real_capital": False,
        },
    }
    manifest_core["manifest_sha256"] = _sha(manifest_core)
    return manifest_core


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace",
        action="append",
        type=Path,
        required=True,
        help="Decision trace. Supply all research eras in chronological order.",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    traces = tuple(
        _load_trace(path, index)
        for index, path in enumerate(args.trace, start=1)
    )
    manifest = build_manifest(traces)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "manifest_sha256": manifest["manifest_sha256"],
                "initial_capital_usd": manifest["initial_capital_usd"],
                "account_count": manifest["account_count"],
                "account_reset_count": manifest["account_reset_count"],
                "economic_era_reset_count": manifest[
                    "economic_era_reset_count"
                ],
                "opportunity_decision_count": manifest[
                    "opportunity_decision_count"
                ],
                "decision_epoch_count": manifest["decision_epoch_count"],
                "trader_opportunity_counts": manifest[
                    "trader_opportunity_counts"
                ],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
