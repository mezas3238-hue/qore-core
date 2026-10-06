from __future__ import annotations

import argparse
import json
from pathlib import Path

from qore.infrastructure.cibo_phase22_turtle_auxiliary_manifest import (
    PHASE22_TURTLE_AUXILIARY_ARTIFACTS,
    phase22_turtle_auxiliary_manifest_payload,
    phase22_turtle_auxiliary_manifest_sha256,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", type=Path)
    parser.add_argument("--tsv", type=Path)
    args = parser.parse_args()
    if args.json is None and args.tsv is None:
        raise SystemExit("at least one of --json/--tsv is required")
    if args.json is not None:
        payload = {
            **phase22_turtle_auxiliary_manifest_payload(),
            "manifest_sha256": phase22_turtle_auxiliary_manifest_sha256(),
        }
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    if args.tsv is not None:
        args.tsv.parent.mkdir(parents=True, exist_ok=True)
        args.tsv.write_text(
            "".join(
                "\t".join(
                    (
                        item.symbol,
                        item.role,
                        str(item.run_id),
                        str(item.artifact_id),
                        item.artifact_name,
                        item.artifact_digest,
                    )
                )
                + "\n"
                for item in PHASE22_TURTLE_AUXILIARY_ARTIFACTS
            ),
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
