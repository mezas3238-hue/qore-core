"""Emit sealed T04/T10 causal calibration from burned Phase19 evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from qore.infrastructure.cibo_ce2i_burned_calibration import (
    burned_t04_t10_calibration_payload,
    burned_t04_t10_calibration_sha256,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = burned_t04_t10_calibration_payload()
    report["calibration_sha256"] = burned_t04_t10_calibration_sha256()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
