#!/usr/bin/env python3
"""Seal Architect-B CNH component identity closure."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from qore.infrastructure.core_stack_v2.shared_b_fx_cnh_identity import (
    write_resolution,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iso-evidence", type=Path, required=True)
    parser.add_argument("--authority-evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    payload = write_resolution(
        iso_evidence_path=args.iso_evidence,
        authority_evidence_path=args.authority_evidence,
        output_path=args.output,
    )
    print(
        json.dumps(
            {
                "identity": payload["identity"],
                "status": payload["status"],
                "currency_component_identity_verified_count": payload[
                    "currency_component_identity_verified_count"
                ],
                "fx_pairs_with_all_currency_components_verified": payload[
                    "fx_pairs_with_all_currency_components_verified"
                ],
                "canonical_tradable_identity_verified_count": payload[
                    "canonical_tradable_identity_verified_count"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
