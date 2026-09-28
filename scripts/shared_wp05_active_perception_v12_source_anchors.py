"""Build the frozen WP-05 V12 source-only evaluation-anchor manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from shared_wp05_active_perception_v12_acquisition_manifest import (
    _causal_source_times,
)

from qore.infrastructure.core_stack_v2.active_perception_v12_acquisition_manifest import (
    build_v12_tick_acquisition_manifest,
)
from qore.infrastructure.core_stack_v2.active_perception_v12_source_anchors import (
    EXPECTED_ACQUISITION_MANIFEST_SHA256,
    build_v12_source_anchor_manifest,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--r8-nas", type=Path, required=True)
    parser.add_argument("--r8-sp", type=Path, required=True)
    parser.add_argument("--r8-us", type=Path, required=True)
    parser.add_argument("--provider-symbol", default="USTEC")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    evidence_paths = {
        "NAS100": args.r8_nas,
        "SP500": args.r8_sp,
        "US30": args.r8_us,
    }
    source_times = _causal_source_times(evidence_paths=evidence_paths)
    rebuilt = build_v12_tick_acquisition_manifest(
        source_times=source_times,
        provider_symbol=args.provider_symbol,
        evidence_sha256={
            market: _sha256(path)
            for market, path in evidence_paths.items()
        },
    )
    if rebuilt.digest_sha256 != EXPECTED_ACQUISITION_MANIFEST_SHA256:
        raise RuntimeError("source anchors do not reproduce frozen acquisition manifest")

    anchors = build_v12_source_anchor_manifest(
        source_times,
        acquisition_manifest_sha256=rebuilt.digest_sha256,
    )
    payload = {
        **anchors.logical_payload(),
        "source_anchor_sha256": anchors.digest_sha256,
        "selection_contract": "CAUSAL_SOURCE_ONLY_NO_MATURED_TARGET",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "source_count": payload["source_count"],
                "source_min": payload["source_min"],
                "source_max": payload["source_max"],
                "source_anchor_sha256": payload["source_anchor_sha256"],
                "acquisition_manifest_sha256": payload[
                    "acquisition_manifest_sha256"
                ],
            },
            sort_keys=True,
        )
    )


def _sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if __name__ == "__main__":
    main()
