"""Build immutable AUDJPY R42 live causal-authority memory snapshot."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, cast

from qore.infrastructure.trader_lab import (
    turtle_soup_audjpy_r32_causal_memory_defragmentation as r32,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_audjpy_r34_coarse_causal_memory as r34,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_audjpy_r38_structural_fragility_risk_correction as r38,
)

IDENTITY = "TURTLE_SOUP_AUDJPY_R42_LIVE_MEMORY_V1"
SOURCE_RUN_ID = 35383377176
SOURCE_ARTIFACT_ID = 10562458144
SOURCE_ARTIFACT_DIGEST = (
    "sha256:ed5a0928e83be7af171864c37335d8f3edeb9af096f29eb9e0a23078745b255c"
)
SOURCE_GIT_SHA = "e0bec233ed40197a1e969786b24a9dc8a1e5869f"
SOURCE_OBSERVATIONS_SHA256 = (
    "4fb9c6d1c9c4537bb5e0de7f4a728ee0725677422ac396cbd63fb606a52c1b11"
)

CERTIFICATION_IDENTITY = "TURTLE_SOUP_AUDJPY_R43_FINAL_CERTIFICATION_SUITE_V1"
CERTIFICATION_RUN_ID = 35400542409
CERTIFICATION_ARTIFACT_ID = 10570670638
CERTIFICATION_ARTIFACT_DIGEST = (
    "sha256:6e4c0cdae038f4d8a0819a6eb4714d922f07d7a6360ac1e711c4434565567473"
)
CERTIFICATION_GIT_SHA = "e4801f5bb2c5b2eb2c03f8ae83593f226101f8c9"
CERTIFICATION_REPORT_SHA256 = (
    "701cefb92afbc1c871315969559beed5f232e929de60ea61484000729dbf683d"
)
CERTIFICATION_MANIFEST_SHA256 = (
    "c9984463dda62dbb7efa5d1b87c8d1eb32bfd166dc4935c28abb40f62b2dd3f1"
)

SELECTED_ENSEMBLE = "R38_FROZEN_SIGNAL_BASELINE"
SELECTED_POLICY = "AUDJPY_CONFIDENCE_100_075_025"
EXPECTED_LAYERS = (
    (r38.CORE, (r38.ROBUST, r38.MAJORITY)),
    (r38.DIRECTION, (r38.ROBUST, r38.MAJORITY)),
    (r38.TIMEFRAME, (r38.ROBUST, r38.MAJORITY)),
)

FIRST_LAYER_FLAGS = r38.FRAGILITY_FLAGS
FIRST_LAYER_POLICY = r38.FRAGILITY_POLICY
SECOND_LAYER_FLAGS = (
    "D1_BODY_ALIGNMENT_OPPOSED",
    "RAID_DEPTH_Q4_LE_0_50",
    "SOURCE_RANGE_Q2_LE_1_0",
)
SECOND_LAYER_POLICY = ("1", "0.50", "0.25", "0.10")


def _single(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {name}, got {len(matches)}")
    return matches[0]


def _serialize_memory(
    memory: dict[tuple[str, str], Any],
    summary: dict[str, Any],
    fields: tuple[str, ...],
    route_mode: str,
) -> dict[str, Any]:
    profiles = [
        {
            "signature": signature,
            "target_family": target_family,
            "observations": profile.observations,
            "distinct_quarters": profile.distinct_quarters,
            "reach_rate": str(profile.reach_rate),
            "posture": profile.posture,
            "classification": profile.classification,
            "validated": profile.validated,
        }
        for (signature, target_family), profile in sorted(memory.items())
    ]
    return {
        "fields": list(fields),
        "route_mode": route_mode,
        "summary": summary,
        "profiles": profiles,
    }


def build(source_root: Path, output: Path) -> dict[str, Any]:
    observations_path = _single(
        source_root,
        "turtle-soup-audjpy-specialist-observations-v2.jsonl",
    )
    digest = hashlib.sha256(observations_path.read_bytes()).hexdigest()
    if digest != SOURCE_OBSERVATIONS_SHA256:
        raise ValueError("AUDJPY R27 observation hash drift")

    if tuple(r38.ENSEMBLES[SELECTED_ENSEMBLE]) != EXPECTED_LAYERS:
        raise ValueError("AUDJPY certified ensemble layer drift")
    if r38.RISK_POLICIES[SELECTED_POLICY] != (
        r38.Decimal("1"),
        r38.Decimal("0.75"),
        r38.Decimal("0.25"),
    ):
        raise ValueError("AUDJPY certified confidence policy drift")
    if tuple(r38.FRAGILITY_POLICY) != (
        r38.Decimal("1"),
        r38.Decimal("0.20"),
        r38.Decimal("0.05"),
        r38.Decimal("0.01"),
    ):
        raise ValueError("AUDJPY first-layer fragility drift")

    rows = r34._load_observations(source_root)
    schemes: dict[str, Any] = {}

    core_fields, core_route_mode = r32.SCHEMES[r38.CORE]
    core_memory, core_summary = r32._build_memory(
        rows,
        fields=core_fields,
        route_mode=core_route_mode,
    )
    schemes[r38.CORE] = _serialize_memory(
        core_memory,
        core_summary,
        core_fields,
        core_route_mode,
    )

    for scheme in (r38.DIRECTION, r38.TIMEFRAME):
        fields, route_mode = r34.SCHEMES[scheme]
        memory, summary = r34._build_memory(
            rows,
            fields=fields,
            route_mode=route_mode,
        )
        schemes[scheme] = _serialize_memory(
            memory,
            summary,
            fields,
            route_mode,
        )

    payload: dict[str, Any] = {
        "schema": "qore.turtle_soup_audjpy.r42.live_memory.v1",
        "identity": IDENTITY,
        "source": {
            "run_id": SOURCE_RUN_ID,
            "artifact_id": SOURCE_ARTIFACT_ID,
            "artifact_digest": SOURCE_ARTIFACT_DIGEST,
            "git_sha": SOURCE_GIT_SHA,
            "observations_sha256": SOURCE_OBSERVATIONS_SHA256,
        },
        "certification": {
            "identity": CERTIFICATION_IDENTITY,
            "run_id": CERTIFICATION_RUN_ID,
            "artifact_id": CERTIFICATION_ARTIFACT_ID,
            "artifact_digest": CERTIFICATION_ARTIFACT_DIGEST,
            "git_sha": CERTIFICATION_GIT_SHA,
            "report_sha256": CERTIFICATION_REPORT_SHA256,
            "manifest_sha256": CERTIFICATION_MANIFEST_SHA256,
        },
        "selected_ensemble": SELECTED_ENSEMBLE,
        "selected_policy": SELECTED_POLICY,
        "layers": [
            {
                "scheme": scheme,
                "allowed_validation_classes": list(classes),
            }
            for scheme, classes in EXPECTED_LAYERS
        ],
        "first_layer_fragility": {
            "flags": list(FIRST_LAYER_FLAGS),
            "policy_0_1_2_3plus": [str(value) for value in FIRST_LAYER_POLICY],
        },
        "second_layer_fragility": {
            "flags": list(SECOND_LAYER_FLAGS),
            "policy_0_1_2_3plus": list(SECOND_LAYER_POLICY),
        },
        "schemes": schemes,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
    )
    return payload


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: module R27_ARTIFACT_ROOT OUTPUT_JSON")
    payload = build(Path(sys.argv[1]), Path(sys.argv[2]))
    schemes = cast(dict[str, Any], payload["schemes"])
    print(
        json.dumps(
            {
                "identity": payload["identity"],
                "selected_ensemble": payload["selected_ensemble"],
                "selected_policy": payload["selected_policy"],
                "profiles": {
                    name: len(cast(list[object], body["profiles"]))
                    for name, body in schemes.items()
                },
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

# AUDJPY_R42_MEMORY_TRIGGER
