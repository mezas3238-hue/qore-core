"""Build immutable GBPJPY R38 live confidence-tier memory snapshot."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, cast

from qore.infrastructure.trader_lab import (
    turtle_soup_gbpjpy_r34_coarse_causal_memory as r34,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_gbpjpy_r35_confidence_tier_ensemble as r35,
)

IDENTITY = "TURTLE_SOUP_GBPJPY_R38_LIVE_MEMORY_V1"
SOURCE_RUN_ID = 35349300927
SOURCE_ARTIFACT_ID = 10549575964
SOURCE_ARTIFACT_DIGEST = (
    "sha256:9e9b57f3a108d4f26b3e0b3600705859dc2491dd735972d563f7a350fe0798d2"
)
SOURCE_OBSERVATIONS_SHA256 = (
    "6b3c7ecf75616ba6d428d23286ec2d9c525aca50ee090c687b9c91e9b2b63066"
)
SELECTED_ENSEMBLE = "R35_RANGE_DIRECTION_MINIMAL_ROBUST"
SELECTED_POLICY = "CONFIDENCE_100_050_010"
EXPECTED_LAYERS = (
    ("R34_RANGE_ROUTE_TYPES", (r35.ROBUST, r35.MAJORITY)),
    ("R34_DIRECTION_REGIME_ROUTE_TYPES", (r35.ROBUST, r35.MAJORITY)),
    ("R34_MINIMAL_ROUTE_TYPES", (r35.ROBUST,)),
)


def _single(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {name}, got {len(matches)}")
    return matches[0]


def build(source_root: Path, output: Path) -> dict[str, Any]:
    observations_path = _single(
        source_root,
        "turtle-soup-gbpjpy-specialist-observations-v2.jsonl",
    )
    digest = hashlib.sha256(observations_path.read_bytes()).hexdigest()
    if digest != SOURCE_OBSERVATIONS_SHA256:
        raise ValueError("GBPJPY R27 observation hash drift")

    if tuple(r35.ENSEMBLES[SELECTED_ENSEMBLE]) != EXPECTED_LAYERS:
        raise ValueError("GBPJPY certified ensemble layer drift")
    if r35.RISK_POLICIES[SELECTED_POLICY] != (
        r35.Decimal("1"),
        r35.Decimal("0.50"),
        r35.Decimal("0.10"),
    ):
        raise ValueError("GBPJPY certified risk policy drift")

    rows = r34._load_observations(source_root)
    schemes: dict[str, Any] = {}
    for scheme, _classes in EXPECTED_LAYERS:
        fields, route_mode = r34.SCHEMES[scheme]
        memory, summary = r34._build_memory(
            rows,
            fields=fields,
            route_mode=route_mode,
        )
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
        schemes[scheme] = {
            "fields": list(fields),
            "route_mode": route_mode,
            "summary": summary,
            "profiles": profiles,
        }

    payload: dict[str, Any] = {
        "schema": "qore.turtle_soup_gbpjpy.r38.live_memory.v1",
        "identity": IDENTITY,
        "source": {
            "run_id": SOURCE_RUN_ID,
            "artifact_id": SOURCE_ARTIFACT_ID,
            "artifact_digest": SOURCE_ARTIFACT_DIGEST,
            "observations_sha256": SOURCE_OBSERVATIONS_SHA256,
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
