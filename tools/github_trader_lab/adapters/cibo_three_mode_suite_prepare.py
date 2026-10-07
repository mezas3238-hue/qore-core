#!/usr/bin/env python3
"""Prepare and persist CIBO lifecycle products for hot Trader Lab replay."""

from __future__ import annotations

import argparse
import functools
import hashlib
import json
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any


SYMBOLS = ("AUDJPY", "EURUSD", "GBPJPY", "GBPUSD", "NAS100", "XAUUSD")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def find_one(root: Path, name: str) -> Path:
    matches = sorted(root.rglob(name))
    if len(matches) != 1:
        raise FileNotFoundError(
            f"{root}: expected exactly one {name}, got {len(matches)}"
        )
    return matches[0]


def option_values(tokens: list[str], name: str) -> list[str]:
    values: list[str] = []
    index = 0
    prefix = name + "="
    while index < len(tokens):
        token = tokens[index]
        if token.startswith(prefix):
            values.append(token[len(prefix):])
        elif token == name:
            if index + 1 >= len(tokens):
                raise ValueError(f"{name}: missing value")
            values.append(tokens[index + 1])
            index += 1
        index += 1
    return values


def decimal_option(tokens: list[str], name: str, default: str) -> Decimal:
    values = option_values(tokens, name)
    return Decimal(values[-1] if values else default)


def serialize_lifecycle_map(
    lifecycle_map: dict[str, dict[str, object]],
) -> dict[str, dict[str, object]]:
    encoded: dict[str, dict[str, object]] = {}
    for signal, profile in lifecycle_map.items():
        row = dict(profile)
        row["actions"] = list(profile["actions"])
        row["enabled_features"] = list(profile["enabled_features"])
        row["events"] = [
            {
                "occurred_at": event.occurred_at.isoformat(),
                "action": event.action,
                "realized_r_delta": format(event.realized_r_delta, "f"),
                "remaining_volume_fraction": format(
                    event.remaining_volume_fraction, "f"
                ),
                "risk_fraction_remaining": format(
                    event.risk_fraction_remaining, "f"
                ),
                "margin_fraction_remaining": format(
                    event.margin_fraction_remaining, "f"
                ),
            }
            for event in profile["events"]
        ]
        encoded[signal] = row
    return encoded


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--evidence-dir", required=True, type=Path)
    parser.add_argument("--subject-root", required=True, type=Path)
    parser.add_argument("--suite", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    assets = args.evidence_dir / "assets"
    required = (
        "walk-forward",
        "historical-control",
        "atlas-AUDJPY",
        "atlas-EURUSD",
        "atlas-GBPJPY",
        "atlas-GBPUSD",
        "atlas-NAS100",
        "atlas-XAUUSD",
    )
    missing = [name for name in required if not (assets / name).is_dir()]
    if missing:
        raise SystemExit(f"missing shared CIBO suite assets: {missing}")

    sys.path.insert(0, str((args.subject_root / "src").resolve()))
    sys.path.insert(0, str((args.subject_root / "scripts").resolve()))
    import cibo_trader_lab_three_mode_ceiling as subject  # noqa: PLC0415

    # PREPARE owns all Atlas parsing. The cache means six raw Atlas artifacts
    # are decoded once even when several lifecycle thresholds are prepared.
    subject.load_raw_m5 = functools.lru_cache(maxsize=None)(subject.load_raw_m5)

    suite: dict[str, Any] = json.loads(args.suite.read_text(encoding="utf-8"))
    cases = suite.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("suite has no cases")

    walk_root = assets / "walk-forward"
    manifest_path = find_one(walk_root, "walk-forward-manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    roots = {
        symbol: assets / f"atlas-{symbol}"
        for symbol in SYMBOLS
    }

    sidecar_root = args.output.parent / f"{args.output.stem}.lifecycle"
    sidecar_root.mkdir(parents=True, exist_ok=True)
    lifecycle_sidecars: dict[str, str] = {}
    lifecycle_counts: dict[str, int] = {}

    for case in cases:
        if not isinstance(case, dict) or not bool(case.get("uses_atlas")):
            continue
        name = str(case["name"])
        tokens_raw = case.get("args", [])
        if not isinstance(tokens_raw, list) or any(
            not isinstance(item, str) for item in tokens_raw
        ):
            raise ValueError(f"{name}: args must be string list")
        tokens = list(tokens_raw)

        feature_values = option_values(tokens, "--lifecycle-feature")
        features = (
            frozenset(
                subject.CiboLifecycleFeature(value)
                for value in feature_values
            )
            if feature_values
            else subject.FULL_CIBO_LIFECYCLE_FEATURES
        )
        lifecycle = subject._build_lifecycle_map(
            manifest,
            roots,
            features=features,
            adverse_loss_cut_r=decimal_option(
                tokens,
                "--lifecycle-adverse-loss-cut-r",
                "-0.50",
            ),
            adverse_partial_fraction=decimal_option(
                tokens,
                "--lifecycle-adverse-partial-fraction",
                "0.25",
            ),
            bootstrap_partial_fraction=decimal_option(
                tokens,
                "--lifecycle-bootstrap-partial-fraction",
                "0.50",
            ),
            adverse_tightened_stop_r=decimal_option(
                tokens,
                "--lifecycle-adverse-tightened-stop-r",
                "-0.50",
            ),
            defensive_initial_stop_r=decimal_option(
                tokens,
                "--lifecycle-defensive-initial-stop-r",
                "-0.50",
            ),
        )
        sidecar = sidecar_root / f"{name}.json"
        sidecar.write_text(
            json.dumps(
                serialize_lifecycle_map(lifecycle),
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n",
            encoding="utf-8",
        )
        lifecycle_sidecars[name] = sidecar.relative_to(
            args.output.parent
        ).as_posix()
        lifecycle_counts[name] = len(lifecycle)

    payload = {
        "schema": "qore.github-trader-lab.cibo-three-mode-prepared.v2",
        "primary_evidence_sha256": sha256(args.evidence),
        "primary_evidence": str(args.evidence.resolve()),
        "assets_root": str(assets.resolve()),
        "required_assets": list(required),
        "suite_sha256": sha256(args.suite),
        "lifecycle_sidecars": lifecycle_sidecars,
        "lifecycle_signal_counts": lifecycle_counts,
        "prepared_from_raw_m1": False,
        "prepared_from_cached_causal_artifacts": True,
        "atlas_consumed_only_during_prepare": True,
        "hot_path_requires_atlas_scan": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
