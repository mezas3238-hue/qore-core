#!/usr/bin/env python3
"""Slice immutable VT31 Phase18 V4 trades into fixed 3x1Y research groups."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_ce2i_chronological_replay import (
    reconstructed_signal_fingerprint,
)
from qore.infrastructure.trader_lab.cibo_three_holdout_1y_contract import (
    expected_windows,
)

EVIDENCE_IDS = (
    "github-actions:r8:10402199719",
    "github-actions:r6:10389112524",
    "github-actions:r5:10380044761",
    "github-actions:vt31-v4:10610673464",
)


def _window(group_id: str) -> tuple[datetime, datetime]:
    for item in expected_windows():
        if item.group_id == group_id:
            return item.start_at, item.end_exclusive_at
    raise ValueError(group_id)


def _max_drawdown(values: list[Decimal]) -> Decimal:
    equity = Decimal(0)
    peak = Decimal(0)
    worst = Decimal(0)
    for value in values:
        equity += value
        peak = max(peak, equity)
        worst = max(worst, peak - equity)
    return worst


def slice_group(
    *,
    source: Path,
    group_id: str,
) -> dict[str, Any]:
    start_at, end_at = _window(group_id)
    raw_rows = [
        json.loads(line)
        for line in source.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    selected: list[dict[str, Any]] = []
    for row in raw_rows:
        signal_at = datetime.fromisoformat(str(row["signal_at"]))
        entry_at = datetime.fromisoformat(str(row["entry_at"]))
        exit_at = datetime.fromisoformat(str(row["exit_at"]))
        if not (
            start_at <= signal_at
            and start_at <= entry_at < end_at
            and exit_at <= end_at
        ):
            continue
        fingerprint = reconstructed_signal_fingerprint(
            trader_id=TraderLineage.VT31_NAS100,
            qore_symbol="NAS100",
            side=str(row["side"]),
            signal_at=signal_at,
            entry_at=entry_at,
            entry_price=Decimal(str(row["entry_price"])),
            structural_stop=Decimal(str(row["structural_stop"])),
            technical_target=Decimal(str(row["technical_target"])),
            source_evidence_ids=EVIDENCE_IDS,
        )
        item = dict(row)
        item["signal_fingerprint"] = "sha256:" + fingerprint
        item["source_evidence_ids"] = list(EVIDENCE_IDS)
        selected.append(item)

    selected.sort(key=lambda row: (row["entry_at"], row["signal_fingerprint"]))
    values = [Decimal(str(row["r_multiple"])) for row in selected]
    if not values:
        raise ValueError(f"{group_id}: VT31 group has no terminal trades")
    gross_profit = sum((x for x in values if x > 0), Decimal(0))
    gross_loss = -sum((x for x in values if x < 0), Decimal(0))
    return {
        "schema": "qore.cibo.trader-lab.vt31-1y-group-lane.v1",
        "group_id": group_id,
        "trader_id": TraderLineage.VT31_NAS100.value,
        "start_at": start_at.isoformat(),
        "end_exclusive_at": end_at.isoformat(),
        "source_population": len(raw_rows),
        "sample_size": len(selected),
        "profit_factor": (
            None if gross_loss == 0 else format(gross_profit / gross_loss, "f")
        ),
        "expectancy_r": format(
            sum(values, Decimal(0)) / Decimal(len(values)),
            "f",
        ),
        "total_r": format(sum(values, Decimal(0)), "f"),
        "max_drawdown_r": format(_max_drawdown(values), "f"),
        "trades": selected,
        "source": {
            "phase18_artifact_id": 10912945588,
            "authoritative_v4_artifact_id": 10610673464,
            "certified_strategy_fingerprint": (
                "089c41f98a72295278063cfc29caf8419538f68315d9f5e57be144fbdae15e08"
            ),
        },
        "governance": {
            "methodology_changed": False,
            "outcome_aware_selection": False,
            "adaptive_research_only": True,
            "fresh_oos_claimed": False,
            "certification_claimed": False,
            "broker_mutation": False,
            "live": False,
            "production": False,
            "real_capital": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument(
        "--group-id",
        choices=("GROUP_1", "GROUP_2", "GROUP_3"),
        required=True,
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = slice_group(source=args.source, group_id=args.group_id)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "group_id": args.group_id,
                "sample_size": payload["sample_size"],
                "profit_factor": payload["profit_factor"],
                "total_r": payload["total_r"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
