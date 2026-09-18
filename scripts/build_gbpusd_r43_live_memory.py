"""Build the immutable GBPUSD R43 live R32 regime-memory snapshot."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from qore.infrastructure.trader_lab import (
    turtle_soup_gbpusd_r32_causal_memory_defragmentation as r32,
)

IDENTITY = "TURTLE_SOUP_GBPUSD_R43_LIVE_MEMORY_V1"
SOURCE_RUN_ID = 35339237432
SOURCE_ARTIFACT_ID = 10544098544
SOURCE_ARTIFACT_DIGEST = (
    "sha256:be89206b847934fd62cb7f63daabb3032cbeec5a1652575b59022353bb9b2978"
)
SOURCE_OBSERVATIONS_SHA256 = (
    "cc9176146a6d20b27ae8c55d0ec807156c7de3a82f651a9c2bca308d733b719c"
)
SCHEME = "R32_REGIME_ROUTE_TYPES"


def _single(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {name}, got {len(matches)}")
    return matches[0]


def build(source_root: Path, output: Path) -> dict[str, object]:
    observations_path = _single(
        source_root,
        "turtle-soup-gbpusd-specialist-observations-v2.jsonl",
    )
    digest = hashlib.sha256(observations_path.read_bytes()).hexdigest()
    if digest != SOURCE_OBSERVATIONS_SHA256:
        raise ValueError("GBPUSD R27 observation hash drift")

    rows = r32._load_observations(source_root)
    fields, route_mode = r32.SCHEMES[SCHEME]
    memory, summary = r32._build_memory(
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
    payload: dict[str, object] = {
        "schema": "qore.turtle_soup_gbpusd.r43.live_memory.v1",
        "identity": IDENTITY,
        "source": {
            "run_id": SOURCE_RUN_ID,
            "artifact_id": SOURCE_ARTIFACT_ID,
            "artifact_digest": SOURCE_ARTIFACT_DIGEST,
            "observations_sha256": SOURCE_OBSERVATIONS_SHA256,
        },
        "scheme": SCHEME,
        "fields": list(fields),
        "route_mode": route_mode,
        "summary": summary,
        "profiles": profiles,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n")
    return payload


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: module R27_ARTIFACT_ROOT OUTPUT_JSON")
    payload = build(Path(sys.argv[1]), Path(sys.argv[2]))
    print(
        json.dumps(
            {
                "identity": payload["identity"],
                "profiles": len(payload["profiles"]),
                "scheme": payload["scheme"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
