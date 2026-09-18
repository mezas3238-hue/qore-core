"""Cross-period pre-entry context for VT31 NAS100 first-position routing.

Uses the exact original entry/authorization logic and baseline management. It
attaches only decision-time state already available before trade outcome.
Consumed-evidence diagnostics only.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_causal_hybrid_rearm_v1 as engine
import vt31_nas100_r5_corrective_management_frontier_v1 as corrective
import vt31_nas100_specialist_r1_candidate as specialist

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    load_market_evidence,
)

SCHEMA = "qore.vt31.nas100.r5.secondary_context_forensics.v1"


def _metrics(rows: list[dict[str, object]]) -> dict[str, object]:
    scaled = engine._scale_capital_rows(
        rows,
        scalar=Decimal("0.60"),
    )
    return engine._capital_metrics(scaled)


def _groups(
    rows: list[dict[str, object]],
    fields: tuple[str, ...],
) -> dict[str, dict[str, object]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        key = "|".join(f"{f}={row.get(f)}" for f in fields)
        grouped[key].append(row)
    return {
        key: _metrics(items)
        for key, items in sorted(grouped.items())
    }


def analyze(path: Path, *, partition: str) -> dict[str, object]:
    series, account, evidence, checked, evidence_sha, provider = (
        load_market_evidence(path)
    )
    raw: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        raw[_day(getattr(bar, "opened_at"))].append(bar)
    by_day = {
        local_day: tuple(
            sorted(items, key=lambda item: getattr(item, "opened_at"))
        )
        for local_day, items in raw.items()
    }
    context_by_day = specialist._context_map(by_day)
    rows, diagnostics = corrective._first_rows(
        by_day,
        context_by_day,
        evidence=evidence,
        alt_partial_r=None,
    )
    specs = {
        "tier_x_ref": ("tier", "reference_volatility_state"),
        "tier_x_h1": ("tier", "h1_state"),
        "tier_x_h4": ("tier", "h4_state"),
        "tier_x_structure": ("tier", "last_structure_event_family"),
        "tier_x_cash": ("tier", "cash_open_state"),
        "tier_x_premarket": ("tier", "premarket_state"),
        "secondary_family_x_ref": (
            "tier",
            "entry_family",
            "reference_volatility_state",
        ),
        "secondary_family_x_h1": ("tier", "entry_family", "h1_state"),
        "secondary_family_x_structure": (
            "tier",
            "entry_family",
            "last_structure_event_family",
        ),
        "secondary_side_x_ref": (
            "tier",
            "side",
            "reference_volatility_state",
        ),
    }
    return {
        "schema": SCHEMA,
        "partition": partition,
        "trade_count": len(rows),
        "overall": _metrics(rows),
        "interactions": {
            name: _groups(rows, fields)
            for name, fields in specs.items()
        },
        "diagnostics": diagnostics,
        "evidence": {
            "account_fingerprint": account,
            "evidence_fingerprint": evidence,
            "checked_at": checked.isoformat(),
            "evidence_software_sha": evidence_sha,
            "provider_symbol_name": provider,
        },
        "governance": {
            "consumed_evidence_only": True,
            "pre_entry_state_only": True,
            "diagnostic_only": True,
            "policy_promoted": False,
            "opens_new_holdout": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--partition", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = analyze(args.evidence, partition=args.partition)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
