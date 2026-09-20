"""Monte Carlo terminal-failure block forensics for VT31_NAS100.

Consumed development evidence only. Diagnostic-only.

This lab uses the current strongest base stack and the same moving-block idea
as certification MC. It records which historical 5-trade source blocks are
overrepresented in terminal-negative bootstrap paths, then summarizes their
causal state composition and post-outcome loss anatomy for research.

Dates and block identity are diagnostic only and can never become runtime
features. H4/H1 are excluded from the causal motif fields.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_alt_tier_bifurcation_forensics_v1 as alt
import vt31_nas100_residual_regime_forensics_v2 as residual

SCHEMA = "qore.vt31.nas100.mc_terminal_failure_block_forensics.v1"
MC_PATHS = 10000
BLOCK = 5

CAUSAL_FIELDS = (
    "tier",
    "entry_family",
    "side",
    "reference_volatility_state",
    "prior_day_state",
    "premarket_state",
    "cash_open_state",
    "last_structure_event_family",
    "current_path_bucket",
    "risk_ref_bucket",
    "reclaim_age_bucket",
    "confirmation_latency_bucket",
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _block_rows(
    rows: list[dict[str, object]],
    start: int,
) -> list[dict[str, object]]:
    n = len(rows)
    return [rows[(start + offset) % n] for offset in range(BLOCK)]


def _block_descriptor(
    rows: list[dict[str, object]],
    start: int,
) -> dict[str, object]:
    items = _block_rows(rows, start)
    values = [_d(row["capital_weighted_net_r"]) for row in items]
    losses = [row for row in items if _d(row["capital_weighted_net_r"]) < 0]
    feature_counts: Counter[str] = Counter()
    for row in items:
        for field in CAUSAL_FIELDS:
            feature_counts[f"{field}={row.get(field)}"] += 1
    path_counts = Counter(str(row.get("loss_path_class")) for row in losses)
    return {
        "start_index": start,
        "start_signal_at": items[0]["signal_at"],
        "end_signal_at": items[-1]["signal_at"],
        "block_total_r": format(sum(values, Decimal(0)), "f"),
        "loss_count": len(losses),
        "non_loss_count": BLOCK - len(losses),
        "loss_path_counts": dict(sorted(path_counts.items())),
        "causal_feature_counts": dict(sorted(feature_counts.items())),
    }


def replay(path: Path, *, partition: str) -> dict[str, object]:
    rows, evidence, diagnostics, stats = alt._current_rows(path)
    rows = sorted(rows, key=lambda row: cast(str, row["signal_at"]))
    n = len(rows)
    values = [_d(row["capital_weighted_net_r"]) for row in rows]

    descriptors = [_block_descriptor(rows, start) for start in range(n)]
    total_occ: Counter[int] = Counter()
    failure_occ: Counter[int] = Counter()
    success_occ: Counter[int] = Counter()
    failure_paths = 0

    domain = f"VT31_MC_FAILURE_BLOCK:{partition}".encode()

    for path_index in range(MC_PATHS):
        starts: list[int] = []
        sampled_values: list[Decimal] = []
        block_index = 0
        while len(sampled_values) < n:
            digest = hashlib.sha256(
                domain
                + b":"
                + str(path_index).encode()
                + b":"
                + str(block_index).encode()
            ).digest()
            start = int.from_bytes(digest, "big") % n
            starts.append(start)
            sampled_values.extend(
                values[(start + offset) % n]
                for offset in range(BLOCK)
            )
            block_index += 1

        terminal = sum(sampled_values[:n], Decimal(0))
        failed = terminal <= 0
        if failed:
            failure_paths += 1

        for start in starts:
            total_occ[start] += 1
            if failed:
                failure_occ[start] += 1
            else:
                success_occ[start] += 1

    base_failure_rate = Decimal(failure_paths) / Decimal(MC_PATHS)
    ranked: list[dict[str, object]] = []
    for descriptor in descriptors:
        start = int(descriptor["start_index"])
        total = total_occ[start]
        failed = failure_occ[start]
        rate = Decimal(failed) / Decimal(total) if total else Decimal(0)
        enrichment = (
            rate / base_failure_rate
            if base_failure_rate > 0
            else Decimal(0)
        )
        ranked.append(
            {
                **descriptor,
                "mc_occurrences": total,
                "failure_path_occurrences": failed,
                "success_path_occurrences": success_occ[start],
                "failure_rate_when_selected": format(rate, "f"),
                "failure_enrichment_vs_baseline": format(
                    enrichment,
                    "f",
                ),
            }
        )

    ranked.sort(
        key=lambda item: (
            Decimal(cast(str, item["failure_enrichment_vs_baseline"])),
            -Decimal(cast(str, item["block_total_r"])),
        ),
        reverse=True,
    )
    top = ranked[:30]

    top_feature_blocks: Counter[str] = Counter()
    all_feature_blocks: Counter[str] = Counter()
    top_path_classes: Counter[str] = Counter()
    all_path_classes: Counter[str] = Counter()

    for descriptor in descriptors:
        for feature in cast(
            dict[str, int],
            descriptor["causal_feature_counts"],
        ):
            all_feature_blocks[feature] += 1
        for path_class, count in cast(
            dict[str, int],
            descriptor["loss_path_counts"],
        ).items():
            all_path_classes[path_class] += count

    for descriptor in top:
        for feature in cast(
            dict[str, int],
            descriptor["causal_feature_counts"],
        ):
            top_feature_blocks[feature] += 1
        for path_class, count in cast(
            dict[str, int],
            descriptor["loss_path_counts"],
        ).items():
            top_path_classes[path_class] += count

    feature_enrichment: list[dict[str, object]] = []
    for feature, top_count in top_feature_blocks.items():
        all_count = all_feature_blocks[feature]
        top_share = Decimal(top_count) / Decimal(len(top))
        all_share = Decimal(all_count) / Decimal(len(descriptors))
        enrichment = (
            top_share / all_share if all_share > 0 else Decimal(0)
        )
        feature_enrichment.append(
            {
                "feature": feature,
                "top_block_presence_share": format(top_share, "f"),
                "all_block_presence_share": format(all_share, "f"),
                "enrichment": format(enrichment, "f"),
            }
        )
    feature_enrichment.sort(
        key=lambda item: Decimal(cast(str, item["enrichment"])),
        reverse=True,
    )

    return {
        "schema": SCHEMA,
        "partition": partition,
        "trade_count": n,
        "metrics": residual._metrics(rows),
        "monte_carlo": {
            "algorithm": "sha256-moving-block-terminal-failure-forensics-v1",
            "paths": MC_PATHS,
            "block_length": BLOCK,
            "terminal_failure_paths": failure_paths,
            "terminal_failure_probability": format(
                base_failure_rate,
                "f",
            ),
        },
        "top_failure_enriched_blocks": top,
        "top_causal_feature_enrichment": feature_enrichment[:40],
        "top_block_loss_path_counts": dict(sorted(top_path_classes.items())),
        "all_block_loss_path_counts": dict(sorted(all_path_classes.items())),
        "source_stats": stats,
        "diagnostics": diagnostics,
        "evidence": evidence,
        "governance": {
            "consumed_evidence_only": True,
            "diagnostic_only": True,
            "block_identity_runtime_forbidden": True,
            "calendar_date_runtime_forbidden": True,
            "h4_h1_excluded_from_causal_motifs": True,
            "terminal_path_sign_research_label_only": True,
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
                "monte_carlo": payload["monte_carlo"],
                "top_causal_feature_enrichment": (
                    payload["top_causal_feature_enrichment"][:15]
                ),
                "top_block_loss_path_counts": (
                    payload["top_block_loss_path_counts"]
                ),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
