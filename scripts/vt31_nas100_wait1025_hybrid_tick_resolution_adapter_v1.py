"""Adapter from WAIT_1025_B060 hybrid ambiguity manifests to the existing
high-density BID/ASK tick resolver.

This module adds no execution hypothesis. It only normalizes the two hybrid
classification names emitted by the governed WAIT1025 manifest into the
semantically identical OCO classification names already supported by
vt31_nas100_high_density_tick_resolution_v1.

All source metadata, activation timestamps, prices and window identities are
preserved. Missing or same-millisecond evidence remains fail-closed.
"""
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

import vt31_nas100_high_density_tick_resolution_v1 as resolver

SCHEMA = "qore.vt31.nas100.wait1025_hybrid_tick_resolution.v1"

CLASS_MAP = {
    "HYBRID_ALT_MULTI_PRICE_FIRST_FILL": "OCO_MULTI_PRICE_FIRST_FILL",
    "HYBRID_ALT_FILL_BAR_PATH": "OCO_FILL_BAR_PATH",
}


def resolve(
    manifest_path: Path,
    acquisition_dirs: list[Path],
    output_path: Path,
) -> dict[str, object]:
    source = json.loads(manifest_path.read_text())
    if source.get("research_only") is not True:
        raise ValueError("WAIT1025 manifest must be research-only")
    if source.get("opens_new_holdout") is not False:
        raise ValueError("WAIT1025 manifest cannot open fresh evidence")
    if source.get("variant") != "WAIT_1025_B060":
        raise ValueError("unexpected source variant")

    windows = source.get("windows")
    if not isinstance(windows, list):
        raise ValueError("manifest windows are malformed")

    normalized_windows: list[dict[str, object]] = []
    for raw in windows:
        if not isinstance(raw, dict):
            raise ValueError("window is malformed")
        classification = str(raw.get("classification"))
        mapped = CLASS_MAP.get(classification)
        if mapped is None:
            raise ValueError(
                f"unsupported WAIT1025 classification={classification}"
            )
        row = dict(raw)
        row["hybrid_source_classification"] = classification
        row["classification"] = mapped
        normalized_windows.append(row)

    normalized = dict(source)
    normalized["windows"] = normalized_windows
    normalized["adapter_schema"] = SCHEMA
    normalized["source_manifest_name"] = manifest_path.name

    with tempfile.TemporaryDirectory() as temp_dir:
        normalized_path = Path(temp_dir) / "normalized.json"
        normalized_path.write_text(
            json.dumps(normalized, sort_keys=True, indent=2) + "\n"
        )
        payload = resolver.resolve(
            normalized_path,
            acquisition_dirs,
            output_path,
        )

    payload["schema"] = SCHEMA
    payload["variant"] = "WAIT_1025_B060"
    payload["partition"] = source.get("partition")
    payload["source_manifest_sha256"] = source.get("sha256")
    payload["classification_adapter_only"] = True
    payload["governance"] = {
        **dict(payload["governance"]),
        "hybrid_classification_only_normalized": True,
        "activation_timestamp_preserved": True,
        "entry_stop_target_preserved": True,
        "source_window_identity_preserved": True,
        "future_labels_used": False,
        "terminal_pnl_used_to_select_window": False,
    }
    output_path.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n"
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument(
        "--acquisition-dir",
        action="append",
        required=True,
        type=Path,
    )
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = resolve(
        args.manifest,
        args.acquisition_dir,
        args.output,
    )
    print(
        json.dumps(
            {
                "partition": payload["partition"],
                "source_window_count": payload["source_window_count"],
                "tick_evidence_available_count": payload[
                    "tick_evidence_available_count"
                ],
                "counts": payload["counts"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
