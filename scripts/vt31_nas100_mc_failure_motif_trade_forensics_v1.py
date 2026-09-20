"""Trade-level validation of MC terminal-failure motifs for VT31_NAS100.

Consumed development evidence only. Diagnostic-only.

MC Terminal Failure Block Forensics V1 found three causal features enriched in
terminal-negative 5-trade bootstrap blocks across R5/R6/R8/consumed:
- tier=CORE
- reference_volatility_state=compressed
- entry_family=breaker

Block enrichment is not sufficient for runtime use. This lab validates the
individual features and their intersections at the trade level on the exact
current strongest stack before any risk policy is proposed.

Calendar identity, block identity, terminal outcome and fold identity are
strictly diagnostic and never runtime inputs.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path

import vt31_nas100_alt_tier_bifurcation_forensics_v1 as alt
import vt31_nas100_residual_regime_forensics_v2 as residual

SCHEMA = "qore.vt31.nas100.mc_failure_motif_trade_forensics.v1"

MOTIFS = {
    "CORE": ("CORE", False, False),
    "COMPRESSED": (None, True, False),
    "BREAKER": (None, False, True),
    "CORE_COMPRESSED": ("CORE", True, False),
    "CORE_BREAKER": ("CORE", False, True),
    "COMPRESSED_BREAKER": (None, True, True),
    "CORE_COMPRESSED_BREAKER": ("CORE", True, True),
}


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _match(
    row: dict[str, object],
    *,
    tier: str | None,
    compressed: bool,
    breaker: bool,
) -> bool:
    if tier is not None and row.get("tier") != tier:
        return False
    if compressed and row.get("reference_volatility_state") != "compressed":
        return False
    if breaker and row.get("entry_family") != "breaker":
        return False
    return True


def _motif_stats(
    rows: list[dict[str, object]],
    *,
    tier: str | None,
    compressed: bool,
    breaker: bool,
) -> dict[str, object]:
    selected = [
        row
        for row in rows
        if _match(
            row,
            tier=tier,
            compressed=compressed,
            breaker=breaker,
        )
    ]
    losses = [
        row
        for row in selected
        if _d(row["capital_weighted_net_r"]) < 0
    ]
    return {
        "sample": len(selected),
        "loss_count": len(losses),
        "loss_rate": (
            "0"
            if not selected
            else format(Decimal(len(losses)) / Decimal(len(selected)), "f")
        ),
        "metrics": residual._metrics(selected),
    }


def replay(path: Path, *, partition: str) -> dict[str, object]:
    rows, evidence, diagnostics, stats = alt._current_rows(path)
    motifs = {
        name: _motif_stats(
            rows,
            tier=tier,
            compressed=compressed,
            breaker=breaker,
        )
        for name, (tier, compressed, breaker) in MOTIFS.items()
    }
    return {
        "schema": SCHEMA,
        "partition": partition,
        "overall_metrics": residual._metrics(rows),
        "motifs": motifs,
        "source_stats": stats,
        "diagnostics": diagnostics,
        "evidence": evidence,
        "governance": {
            "consumed_evidence_only": True,
            "diagnostic_only": True,
            "derived_from_mc_failure_block_forensics": True,
            "block_identity_runtime_forbidden": True,
            "calendar_runtime_forbidden": True,
            "fold_identity_runtime_forbidden": True,
            "terminal_outcome_runtime_forbidden": True,
            "trade_policy_changed": False,
            "opens_new_holdout": False,
            "policy_promoted": False,
            "candidate_certified": False,
            "live_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--partition", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    payload = replay(args.evidence, partition=args.partition)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "partition": payload["partition"],
                "overall_metrics": payload["overall_metrics"],
                "motifs": payload["motifs"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
