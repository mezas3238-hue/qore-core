"""Build the official consumed NAS100 CIBO Market Intelligence Dossier V1.

Source: immutable CIBO VT31 Eight-Ledger bundle.
Output is association-only research memory and cannot promote a runtime rule.
The sealed 2015-04-19..2016-04-19 holdout is never opened.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any

IDENTITY = "CIBO_NAS100_MARKET_INTELLIGENCE_DOSSIER_V1"
SOURCE_SCHEMA = "qore.cibo_atlas.vt31.eight_ledger_bundle.v1"
SOURCE_RUN_ID = 35175782935
SOURCE_ARTIFACT_ID = 10478487667
SOURCE_ARTIFACT_DIGEST = (
    "sha256:17c8d1909152d87ed67a05cd986fa9cca39b2ac92598d36822c38e8afccde192"
)


def _rows(root: Path, name: str, market: str | None = None) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    with (root / name).open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            if market is None or row.get("market") == market:
                result.append(row)
    return result


def _quantile(values: list[Decimal], p: Decimal) -> Decimal | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = p * Decimal(len(ordered) - 1)
    lo = int(position)
    hi = min(lo + 1, len(ordered) - 1)
    weight = position - Decimal(lo)
    return ordered[lo] * (Decimal(1) - weight) + ordered[hi] * weight


def _quantiles(values: list[int]) -> dict[str, str | None]:
    decimals = [Decimal(value) for value in values]
    return {
        "p25": _fmt(_quantile(decimals, Decimal("0.25"))),
        "p50": _fmt(_quantile(decimals, Decimal("0.50"))),
        "p75": _fmt(_quantile(decimals, Decimal("0.75"))),
        "p90": _fmt(_quantile(decimals, Decimal("0.90"))),
    }


def _fmt(value: Decimal | None) -> str | None:
    return None if value is None else format(value, "f")


def _rate(numerator: int, denominator: int) -> str | None:
    if denominator == 0:
        return None
    return format(Decimal(numerator) / Decimal(denominator), "f")


def _median_decimal(values: list[Decimal]) -> str | None:
    return None if not values else format(median(values), "f")


def _daily_summary(rows: list[dict[str, Any]]) -> dict[str, object]:
    regimes = Counter(str(row["day_regime"]) for row in rows)
    breaches = Counter(str(row["first_breach"]) for row in rows)
    widths = [Decimal(str(row["reference_width"])) for row in rows]
    lifecycle = [Decimal(str(row["lifecycle_range_ref"])) for row in rows]
    return {
        "days": len(rows),
        "regimes": dict(sorted(regimes.items())),
        "first_breach": dict(sorted(breaches.items())),
        "objective_hit_by_16_rate": _rate(
            sum(bool(row["opposite_boundary_hit_by_16"]) for row in rows),
            len(rows),
        ),
        "both_sides_by_11_rate": _rate(
            sum(bool(row["both_sides_by_11"]) for row in rows),
            len(rows),
        ),
        "both_sides_by_16_rate": _rate(
            sum(bool(row["both_sides_by_16"]) for row in rows),
            len(rows),
        ),
        "reference_width_median": _median_decimal(widths),
        "lifecycle_range_ref_median": _median_decimal(lifecycle),
    }


def _sha_manifest(root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in (root / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        digest, name = line.split(maxsplit=1)
        result[name.removeprefix("./")] = digest
    return result


def build(root: Path) -> dict[str, object]:
    summary = json.loads(
        (root / "CIBO_ATLAS_VT31_EIGHT_LEDGER_SUMMARY.json").read_text(
            encoding="utf-8"
        )
    )
    if summary.get("schema") != SOURCE_SCHEMA:
        raise ValueError("unexpected CIBO Eight-Ledger schema")
    if summary.get("research_only") is not True:
        raise ValueError("source must remain research-only")
    if summary.get("opens_new_holdout") is not False:
        raise ValueError("source unexpectedly opens holdout")

    daily = _rows(root, "DAILY_PATH_LEDGER.jsonl", "NAS100")
    departures = _rows(root, "DEPARTURE_TIMING_LEDGER.jsonl", "NAS100")
    sequences = _rows(root, "PRE_DEPARTURE_SEQUENCE_LEDGER.jsonl", "NAS100")
    structures = _rows(root, "STRUCTURE_TOUCH_LEDGER.jsonl", "NAS100")
    targets = _rows(root, "TARGET_DESTINATION_LEDGER.jsonl", "NAS100")
    trader = _rows(root, "TRADER_MARKET_SYNC_LEDGER.jsonl", "NAS100")
    cross_index = _rows(root, "CROSS_INDEX_JOURNEY_LEDGER.jsonl")

    partitions: dict[str, object] = {}
    for partition in sorted({str(row["partition"]) for row in daily}):
        part = [row for row in daily if row["partition"] == partition]
        dates = [str(row["ny_date"]) for row in part]
        partitions[partition] = {
            "date_start": min(dates),
            "date_end": max(dates),
            **_daily_summary(part),
        }

    by_weekday = {
        weekday: _daily_summary(
            [row for row in daily if row["weekday"] == weekday]
        )
        for weekday in (
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
        )
    }

    last_structure = Counter(
        str(row.get("last_structure_before_departure") or "none")
        for row in departures
    )
    departure_buckets = Counter(
        str(row["departure_bucket_15m"]) for row in departures
    )
    journey_memory = {
        "completed_reversal_episodes": len(departures),
        "last_structure_before_departure_counts": dict(
            sorted(last_structure.items())
        ),
        "minutes_breach_to_departure": _quantiles(
            [
                int(row["minutes_breach_to_departure"])
                for row in departures
                if isinstance(row.get("minutes_breach_to_departure"), int)
            ]
        ),
        "minutes_last_structure_touch_to_departure": _quantiles(
            [
                int(row["minutes_last_structure_touch_to_departure"])
                for row in departures
                if isinstance(
                    row.get("minutes_last_structure_touch_to_departure"),
                    int,
                )
            ]
        ),
        "minutes_departure_to_objective": _quantiles(
            [
                int(row["minutes_departure_to_objective"])
                for row in departures
                if isinstance(row.get("minutes_departure_to_objective"), int)
            ]
        ),
        "departure_15m_bucket_counts": dict(
            sorted(departure_buckets.items())
        ),
    }

    family_counts = Counter(str(row["structure_family"]) for row in structures)
    structure_memory = {
        "rows": len(structures),
        "family_counts": dict(sorted(family_counts.items())),
    }

    available = [
        row for row in targets if bool(row["opposite_boundary_available"])
    ]
    hit = [
        row for row in available if bool(row["opposite_boundary_hit_by_16"])
    ]
    extension = {
        level: _rate(
            sum(bool(row["post_boundary_ladder"][level]) for row in hit),
            len(hit),
        )
        for level in ("0.25", "0.5", "1", "1.5", "2")
    }
    target_memory = {
        "episodes": len(targets),
        "opposite_boundary_available": len(available),
        "opposite_boundary_hit_by_16": len(hit),
        "hit_rate_given_available": _rate(len(hit), len(available)),
        "minutes_breach_to_opposite": _quantiles(
            [
                int(row["minutes_breach_to_opposite"])
                for row in hit
                if isinstance(row.get("minutes_breach_to_opposite"), int)
            ]
        ),
        "post_boundary_extension_rate_given_hit": extension,
    }

    event_counts: Counter[str] = Counter()
    tails: Counter[str] = Counter()
    sequence_lengths: list[int] = []
    for row in sequences:
        before: list[str] = []
        departure_at = str(row["departure_pivot_at"])
        for event in row["event_sequence"]:
            event_at = str(event["at"])
            if departure_at and event_at > departure_at:
                continue
            name = str(event["event"])
            event_counts[name] += 1
            if name not in {"departure_pivot", "opposite_09_boundary"}:
                before.append(name)
        sequence_lengths.append(len(before))
        if before:
            tails[before[-1]] += 1
    sequence_memory = {
        "episodes": len(sequences),
        "event_counts_pre_departure": dict(sorted(event_counts.items())),
        "last_predeparture_event_counts": dict(sorted(tails.items())),
        "sequence_length_quantiles": _quantiles(sequence_lengths),
    }

    cross_states = Counter(str(row["direction_state"]) for row in cross_index)
    breach_leaders = Counter(
        str(row["breach_leader"])
        for row in cross_index
        if row.get("breach_leader")
    )
    departure_leaders = Counter(
        str(row["departure_leader"])
        for row in cross_index
        if row.get("departure_leader")
    )
    cross_memory = {
        "days": len(cross_index),
        "direction_state_counts": dict(sorted(cross_states.items())),
        "breach_leader_counts": dict(sorted(breach_leaders.items())),
        "departure_leader_counts": dict(sorted(departure_leaders.items())),
        "breach_lead_lag_minutes": _quantiles(
            [
                int(row["breach_lead_lag_minutes"])
                for row in cross_index
                if isinstance(row.get("breach_lead_lag_minutes"), int)
            ]
        ),
        "departure_lead_lag_minutes": _quantiles(
            [
                int(row["departure_lead_lag_minutes"])
                for row in cross_index
                if isinstance(row.get("departure_lead_lag_minutes"), int)
            ]
        ),
        "role": "context_only_not_individual_memory_replacement",
    }

    overlay = {
        "roots": len(trader),
        "terminal_family_counts": dict(
            sorted(
                Counter(
                    str(row["terminal_family"]) for row in trader
                ).items()
            )
        ),
        "entry_family_counts": dict(
            sorted(
                Counter(str(row["entry_family"]) for row in trader).items()
            )
        ),
        "side_counts": dict(
            sorted(Counter(str(row["side"]) for row in trader).items())
        ),
        "pre_entry_behavior_proxy_counts": dict(
            sorted(
                Counter(
                    str(row["pre_entry_behavior_proxy"]) for row in trader
                ).items()
            )
        ),
        "stopped_before_eventual_source_objective_count": sum(
            bool(row["trader_stopped_before_eventual_source_objective"])
            for row in trader
        ),
        "timing_class": "MIXED_PRE_ENTRY_AND_POST_OUTCOME_RESEARCH",
        "runtime_rule_promotion_allowed": False,
    }

    payload: dict[str, object] = {
        "identity": IDENTITY,
        "schema": "qore.cibo.vt31.nas100.market-intelligence-dossier.v1",
        "market": "NAS100",
        "provider": "USTEC",
        "timezone": "America/New_York",
        "source": {
            "cibo_bundle_schema": SOURCE_SCHEMA,
            "run_id": SOURCE_RUN_ID,
            "artifact_id": SOURCE_ARTIFACT_ID,
            "artifact_digest": SOURCE_ARTIFACT_DIGEST,
            "source_git_sha": (root / "git-sha.txt")
            .read_text(encoding="utf-8")
            .strip(),
            "ledger_sha256": _sha_manifest(root),
            "consumed_date_start": min(str(row["ny_date"]) for row in daily),
            "consumed_date_end": max(str(row["ny_date"]) for row in daily),
            "partitions": partitions,
        },
        "evidence_tier": "E1_ASSOCIATION_ONLY",
        "market_overall": _daily_summary(daily),
        "by_partition": partitions,
        "by_weekday": by_weekday,
        "journey_memory": journey_memory,
        "structure_memory": structure_memory,
        "target_destination_memory": target_memory,
        "pre_departure_sequence_memory": sequence_memory,
        "cross_index_context_memory": cross_memory,
        "trader_overlay_research_source": overlay,
        "governance": {
            "research_only": True,
            "consumed_evidence": True,
            "rule_promotion_allowed": False,
            "date_level_runtime_lookup_allowed": False,
            "post_outcome_runtime_lookup_allowed": False,
            "future_bar_lookup_allowed": False,
            "fresh_holdout_opened": False,
            "live_authorized": False,
            "production_authorized": False,
        },
        "limitations": [
            "association-only",
            "consumed-research-evidence",
            "no-rule-promotion",
            (
                "post-outcome-aggregate-sections-must-not-be-used-as-"
                "date-level-runtime-oracle"
            ),
            "cross-index-memory-is-context-only",
            "holdout-2015-04-19..2016-04-19-remains-sealed",
        ],
    }
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    payload["dossier_fingerprint_sha256"] = hashlib.sha256(encoded).hexdigest()
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("ledger_dir", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = build(args.ledger_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "identity": payload["identity"],
                "fingerprint": payload["dossier_fingerprint_sha256"],
                "market_overall": payload["market_overall"],
                "journey_memory": payload["journey_memory"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
