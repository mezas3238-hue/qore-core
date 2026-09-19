"""Causal DOL1 extension forensics for VT31 NAS100.

Consumes the immutable CIBO NAS100 target-destination and market-journey
ledgers.  Silver Bullet is not modified.

The lab only uses state knowable at the moment the opposite 09:00 reference
boundary (DOL1) is reached:
- first breach side;
- minutes from first breach to DOL1;
- minutes from source confirmation to DOL1 when confirmation exists;
- DOL1 hit clock in New York;
- interactions of those fields.

Future extension (+0.25/+0.50/+1.00 reference widths and beyond) is a
research-only label.  The lab does not directly promote a target-extension
policy.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

SCHEMA = "qore.vt31.nas100.dol1_extension_forensics.v1"
IDENTITY = "VT31_NAS100_DOL1_EXTENSION_FORENSICS_V1"
MARKET = "NAS100"
NY = ZoneInfo("America/New_York")
PARTITIONS = ("r8_fresh", "r6", "r5")
MIN_SAMPLE_PER_PARTITION = 10

FEATURES = (
    "first_breach",
    "breach_to_dol1_bucket",
    "confirmation_to_dol1_bucket",
    "dol1_clock_bucket",
    "first_breach_x_breach_to_dol1",
    "first_breach_x_dol1_clock",
)


def _bucket(
    value: int | None,
    *,
    cuts: tuple[int, ...],
    labels: tuple[str, ...],
) -> str:
    if value is None:
        return "missing"
    for cut, label in zip(cuts, labels, strict=True):
        if value <= cut:
            return label
    return labels[-1]


def _dol1_clock_bucket(value: str) -> str:
    dt = datetime.fromisoformat(value).astimezone(NY)
    minute = dt.hour * 60 + dt.minute
    if minute < 11 * 60:
        return "10_00_10_59"
    if minute < 12 * 60:
        return "11_00_11_59"
    if minute < 13 * 60:
        return "12_00_12_59"
    if minute < 14 * 60:
        return "13_00_13_59"
    if minute < 15 * 60:
        return "14_00_14_59"
    return "15_00_15_59"


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _build_rows(
    target_path: Path,
    journey_path: Path,
) -> list[dict[str, object]]:
    target = {
        row["episode_id"]: row
        for row in _load_jsonl(target_path)
        if row.get("market") == MARKET
    }
    journey = {
        row["episode_id"]: row
        for row in _load_jsonl(journey_path)
        if row.get("market") == MARKET
    }

    rows: list[dict[str, object]] = []
    for episode_id, destination in target.items():
        if destination.get("opposite_boundary_hit_by_16") is not True:
            continue
        boundary_at_raw = destination.get("opposite_boundary_at")
        if not isinstance(boundary_at_raw, str):
            continue

        source = journey.get(episode_id, {})
        confirmation_raw = source.get("source_confirmation_at")
        confirm_to_dol1: int | None = None
        if isinstance(confirmation_raw, str):
            confirm_to_dol1 = int(
                (
                    datetime.fromisoformat(boundary_at_raw)
                    - datetime.fromisoformat(confirmation_raw)
                ).total_seconds()
                // 60
            )

        breach_to_dol1_raw = destination.get("minutes_breach_to_opposite")
        breach_to_dol1 = (
            None
            if breach_to_dol1_raw is None
            else int(breach_to_dol1_raw)
        )

        breach_bucket = _bucket(
            breach_to_dol1,
            cuts=(60, 120, 180, 240, 10_000),
            labels=(
                "le_60m",
                "61_120m",
                "121_180m",
                "181_240m",
                "gt_240m",
            ),
        )
        confirm_bucket = _bucket(
            confirm_to_dol1,
            cuts=(15, 30, 60, 120, 10_000),
            labels=(
                "le_15m",
                "16_30m",
                "31_60m",
                "61_120m",
                "gt_120m",
            ),
        )
        clock_bucket = _dol1_clock_bucket(boundary_at_raw)
        first_breach = str(destination.get("first_breach"))

        extension_raw = destination.get("post_boundary_extension_ref")
        extension = (
            Decimal(0)
            if extension_raw is None
            else Decimal(str(extension_raw))
        )

        rows.append(
            {
                "episode_id": episode_id,
                "partition": destination["partition"],
                "first_breach": first_breach,
                "movement_side": (
                    "short"
                    if first_breach == "high"
                    else "long"
                    if first_breach == "low"
                    else "none"
                ),
                "breach_to_dol1_minutes": breach_to_dol1,
                "breach_to_dol1_bucket": breach_bucket,
                "confirmation_to_dol1_minutes": confirm_to_dol1,
                "confirmation_to_dol1_bucket": confirm_bucket,
                "dol1_clock_bucket": clock_bucket,
                "first_breach_x_breach_to_dol1": (
                    f"{first_breach}|{breach_bucket}"
                ),
                "first_breach_x_dol1_clock": (
                    f"{first_breach}|{clock_bucket}"
                ),
                "extension_ref": format(extension, "f"),
                "extended_0_25": extension >= Decimal("0.25"),
                "extended_0_50": extension >= Decimal("0.50"),
                "extended_1_00": extension >= Decimal("1.00"),
                "extended_1_50": extension >= Decimal("1.50"),
                "extended_2_00": extension >= Decimal("2.00"),
                "future_extension_label_research_only": True,
            }
        )
    return rows


def _stats(rows: list[dict[str, object]]) -> dict[str, object]:
    n = len(rows)

    def rate(field: str) -> str:
        if n == 0:
            return "0"
        return format(
            Decimal(sum(bool(row[field]) for row in rows)) / Decimal(n),
            "f",
        )

    return {
        "sample": n,
        "extension_0_25_rate": rate("extended_0_25"),
        "extension_0_50_rate": rate("extended_0_50"),
        "extension_1_00_rate": rate("extended_1_00"),
        "extension_1_50_rate": rate("extended_1_50"),
        "extension_2_00_rate": rate("extended_2_00"),
    }


def _feature_stats(
    rows: list[dict[str, object]],
) -> dict[str, dict[str, object]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        for feature in FEATURES:
            grouped[f"{feature}={row.get(feature)}"].append(row)
    return {
        key: _stats(items)
        for key, items in sorted(grouped.items())
    }


def analyze(
    target_path: Path,
    journey_path: Path,
) -> dict[str, object]:
    rows = _build_rows(target_path, journey_path)
    partitions = {
        partition: [row for row in rows if row["partition"] == partition]
        for partition in PARTITIONS
    }

    by_partition = {
        partition: {
            "overall": _stats(items),
            "feature_diagnostics": _feature_stats(items),
        }
        for partition, items in partitions.items()
    }

    common = set.intersection(
        *(
            set(by_partition[partition]["feature_diagnostics"])
            for partition in PARTITIONS
        )
    )
    stable_extension_enriched: list[dict[str, object]] = []
    stable_extension_depleted: list[dict[str, object]] = []

    for state in sorted(common):
        per_partition = {
            partition: by_partition[partition]["feature_diagnostics"][state]
            for partition in PARTITIONS
        }
        if min(
            int(per_partition[partition]["sample"])
            for partition in PARTITIONS
        ) < MIN_SAMPLE_PER_PARTITION:
            continue

        deltas_050: dict[str, Decimal] = {}
        deltas_100: dict[str, Decimal] = {}
        for partition in PARTITIONS:
            baseline = by_partition[partition]["overall"]
            deltas_050[partition] = (
                Decimal(per_partition[partition]["extension_0_50_rate"])
                - Decimal(baseline["extension_0_50_rate"])
            )
            deltas_100[partition] = (
                Decimal(per_partition[partition]["extension_1_00_rate"])
                - Decimal(baseline["extension_1_00_rate"])
            )

        item = {
            "state": state,
            "min_sample_per_partition": min(
                int(per_partition[partition]["sample"])
                for partition in PARTITIONS
            ),
            "per_partition": per_partition,
            "extension_0_50_delta_vs_partition": {
                partition: format(deltas_050[partition], "f")
                for partition in PARTITIONS
            },
            "extension_1_00_delta_vs_partition": {
                partition: format(deltas_100[partition], "f")
                for partition in PARTITIONS
            },
        }

        if all(
            deltas_050[partition] > 0
            and deltas_100[partition] > 0
            for partition in PARTITIONS
        ):
            stable_extension_enriched.append(item)
        if all(
            deltas_050[partition] < 0
            and deltas_100[partition] < 0
            for partition in PARTITIONS
        ):
            stable_extension_depleted.append(item)

    stable_extension_enriched.sort(
        key=lambda item: -int(item["min_sample_per_partition"])
    )
    stable_extension_depleted.sort(
        key=lambda item: -int(item["min_sample_per_partition"])
    )

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "market": MARKET,
        "partitions": list(PARTITIONS),
        "overall": _stats(rows),
        "by_partition": by_partition,
        "stable_extension_enriched_states": stable_extension_enriched,
        "stable_extension_depleted_states": stable_extension_depleted,
        "observations": rows,
        "governance": {
            "cibo_consumed_research_only": True,
            "dol1_state_is_causal_at_boundary_touch": True,
            "future_extension_is_research_label_only": True,
            "future_extension_allowed_at_runtime": False,
            "post_departure_pivot_used_as_runtime_feature": False,
            "silver_bullet_modified": False,
            "minimum_sample_per_partition": MIN_SAMPLE_PER_PARTITION,
            "requires_direction_3_of_3": True,
            "opens_new_holdout": False,
            "policy_promoted": False,
            "candidate_certified": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("target_destination", type=Path)
    parser.add_argument("market_journey", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    payload = analyze(args.target_destination, args.market_journey)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "overall": payload["overall"],
                "stable_extension_enriched_states": payload[
                    "stable_extension_enriched_states"
                ],
                "stable_extension_depleted_states": payload[
                    "stable_extension_depleted_states"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
