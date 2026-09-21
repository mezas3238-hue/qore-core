"""Economic validation overlay for Turtle Soup AUDJPY Cognitive Memory V2.

The causal situation, regime match, target support and management posture are
already frozen by V2 before this layer runs.  V3 is not allowed to redefine
those elements.  It only validates whether the already-defined full lifecycle
remains economically sufficient after 0.10R friction.

Temporal stability uses equal-count chronological terciles inside each causal
profile, never fixed calendar-year rules.  A profile is validated when the
combined full-lifecycle mean is positive and at least two of three chronological
terciles are positive.
"""
from __future__ import annotations

import copy
import json
import sys
from collections import Counter, defaultdict
from collections.abc import Sequence
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

from qore.infrastructure.trader_lab import (
    turtle_soup_audjpy_specialist_cognitive_memory_v2 as v2,
)

IDENTITY = "TURTLE_SOUP_AUDJPY_SPECIALIST_COGNITIVE_MEMORY_V3"
SOURCE_V2_IDENTITY = v2.IDENTITY
SOURCE_V2_RUN_ID = 35383377176
SOURCE_V2_ARTIFACT_ID = 10562458144
SOURCE_V2_ARTIFACT_DIGEST = "sha256:ed5a0928e83be7af171864c37335d8f3edeb9af096f29eb9e0a23078745b255c"

VALID_CLASSES = ("ROBUST_VALIDATED_010", "MAJORITY_VALIDATED_010")


def _single(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {name}, got {len(matches)}")
    return matches[0]


def _mean(rows: Sequence[dict[str, Any]], field: str) -> Decimal:
    return sum((Decimal(str(row[field])) for row in rows), Decimal(0)) / Decimal(len(rows))


def _terciles(rows: Sequence[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    ordered = sorted(rows, key=lambda row: str(row["strategy_entry_at"]))
    n = len(ordered)
    first = n // 3
    second = (2 * n) // 3
    parts = [ordered[:first], ordered[first:second], ordered[second:]]
    if any(not part for part in parts):
        raise ValueError("economic validation requires three non-empty terciles")
    return parts


def _validation(
    rows: Sequence[dict[str, Any]],
    *,
    posture: str,
) -> dict[str, Any]:
    field = f"{posture}_net_010_r"
    combined = _mean(rows, field)
    temporal = [_mean(part, field) for part in _terciles(rows)]
    positives = sum(value > 0 for value in temporal)
    if combined > 0 and positives == 3:
        classification = "ROBUST_VALIDATED_010"
    elif combined > 0 and positives >= 2:
        classification = "MAJORITY_VALIDATED_010"
    else:
        classification = "NOT_VALIDATED_010"
    return {
        "classification": classification,
        "validated": classification in VALID_CLASSES,
        "posture_frozen_before_economic_validation": posture,
        "full_lifecycle_field": field,
        "combined_mean_net_010_r": str(combined),
        "chronological_tercile_mean_net_010_r": [str(value) for value in temporal],
        "positive_terciles": positives,
        "situation_definition_changed": False,
        "target_definition_changed": False,
        "management_posture_changed": False,
    }


def build(v2_root: Path, output: Path) -> dict[str, Any]:
    report_v2 = json.loads(
        _single(
            v2_root,
            "turtle-soup-audjpy-specialist-cognitive-memory-v2-report.json",
        ).read_text()
    )
    if report_v2["identity"] != SOURCE_V2_IDENTITY:
        raise ValueError("unexpected Cognitive Memory V2 identity")
    if report_v2["decision_contract"]["economic_fields_authorize_trade"]:
        raise ValueError("V2 structural contract drift")

    cognitive_v2 = json.loads(
        _single(
            v2_root,
            "turtle-soup-audjpy-specialist-cognitive-memory-v2.json",
        ).read_text()
    )
    cognitive = copy.deepcopy(cognitive_v2)

    observations: list[dict[str, Any]] = []
    with _single(
        v2_root,
        "turtle-soup-audjpy-specialist-observations-v2.jsonl",
    ).open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                observations.append(json.loads(line))
    if len(observations) != 40980:
        raise ValueError("Cognitive Memory V2 observation drift")

    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for level, fields in v2.LEVELS:
        for row in observations:
            grouped[(level, v2._key(row, fields), v2._target_key(row))].append(row)

    counts: Counter[str] = Counter()
    validated_by_level: Counter[str] = Counter()
    for level, payload in cognitive.items():
        signatures = cast(dict[str, Any], payload["signatures"])
        for signature, item in signatures.items():
            targets = cast(dict[str, Any], item["targets"])
            for target_key, profile in targets.items():
                if not bool(profile["structurally_supported"]):
                    profile["economic_validation"] = {
                        "classification": "NOT_EVALUATED_STRUCTURALLY_UNSUPPORTED",
                        "validated": False,
                    }
                    counts["NOT_EVALUATED_STRUCTURALLY_UNSUPPORTED"] += 1
                    continue
                rows = grouped[(level, signature, target_key)]
                posture = str(profile["preferred_posture"])
                validation = _validation(rows, posture=posture)
                profile["economic_validation"] = validation
                counts[str(validation["classification"])] += 1
                if validation["validated"]:
                    validated_by_level[level] += 1

    output.mkdir(parents=True, exist_ok=True)
    (output / "turtle-soup-audjpy-specialist-cognitive-memory-v3.json").write_text(
        json.dumps(cognitive, indent=2, sort_keys=True) + "\n"
    )
    report = {
        "schema": "qore.turtle_soup_audjpy.specialist_cognitive_memory.v3",
        "identity": IDENTITY,
        "source_v2": {
            "identity": SOURCE_V2_IDENTITY,
            "run_id": SOURCE_V2_RUN_ID,
            "artifact_id": SOURCE_V2_ARTIFACT_ID,
            "artifact_digest": SOURCE_V2_ARTIFACT_DIGEST,
        },
        "decision_contract": {
            "causal_structure_frozen_before_economic_validation": True,
            "regime_definition_frozen_before_economic_validation": True,
            "target_support_frozen_before_economic_validation": True,
            "management_posture_frozen_before_economic_validation": True,
            "economic_validation_uses_full_lifecycle": True,
            "economic_validation_friction_r": "0.10",
            "calendar_year_rule": False,
            "temporal_validation": "EQUAL_COUNT_CHRONOLOGICAL_TERCILES",
            "combined_mean_must_be_positive": True,
            "minimum_positive_terciles": 2,
            "economic_mean_magnitude_used_for_target_ranking": False,
            "r27_result_used_as_input": False,
        },
        "reproduction": {
            "observations": len(observations),
        },
        "economic_validation_counts": dict(counts),
        "validated_profiles_by_level": dict(validated_by_level),
        "governance": {
            "research_only": True,
            "fresh_holdout_consumed": False,
            "candidate_promoted": False,
            "demo_eligible": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }
    (output / "turtle-soup-audjpy-specialist-cognitive-memory-v3-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    return report


def resolve_validated(
    hierarchy: dict[str, Any],
    row: dict[str, Any],
) -> tuple[dict[str, Any] | None, str | None, str | None]:
    target_key = v2._target_key(row)
    for level, fields in v2.LEVELS:
        if level not in v2.AUTHORITATIVE_LEVELS:
            continue
        signature = v2._key(row, fields)
        item = cast(dict[str, Any], hierarchy[level]["signatures"]).get(signature)
        if item is None or item["decision_authority"] != "AUTHORITATIVE":
            continue
        profile = cast(dict[str, Any], item["targets"]).get(target_key)
        if profile is None or not bool(profile["structurally_supported"]):
            continue
        validation = cast(dict[str, Any], profile.get("economic_validation", {}))
        if not bool(validation.get("validated", False)):
            continue
        return profile, level, signature
    return None, None, None


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: module COGNITIVE_V2_ROOT OUTPUT_DIR")
    print(json.dumps(build(Path(sys.argv[1]), Path(sys.argv[2])), sort_keys=True))


if __name__ == "__main__":
    main()
