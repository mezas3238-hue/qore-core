#!/usr/bin/env python3
"""Prepare and persist CIBO lifecycle products for hot Trader Lab replay."""

from __future__ import annotations

import argparse
import functools
import hashlib
import json
import sys
from bisect import bisect_left, bisect_right
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
    from qore.infrastructure.cibo_position_lifecycle import (  # noqa: PLC0415
        FULL_CIBO_LIFECYCLE_FEATURES,
        CiboLifecycleFeature,
        CiboPositionLifecycleInput,
        run_cibo_position_lifecycle,
    )
    from qore.infrastructure.cibo_single_account_manifest_economics import (  # noqa: PLC0415
        manifest_row_provider_cost_per_volume_usd,
    )
    from qore.infrastructure.cibo_single_account_manifest_settlement import (  # noqa: PLC0415
        manifest_row_to_shadow_outcome_observation,
    )
    from qore.infrastructure.trader_lab.cibo_market_atlas_journey_extractor_v1 import (  # noqa: PLC0415
        load_raw_m5,
    )

    # PREPARE owns all Atlas parsing. The cache means six raw Atlas artifacts
    # are decoded once even when several lifecycle thresholds are prepared.
    load_raw_m5_cached = functools.lru_cache(maxsize=None)(load_raw_m5)

    def build_lifecycle_map(
        manifest: dict[str, object],
        roots: dict[str, Path],
        *,
        features: frozenset[CiboLifecycleFeature],
        adverse_loss_cut_r: Decimal,
        adverse_partial_fraction: Decimal,
        bootstrap_partial_fraction: Decimal,
        adverse_tightened_stop_r: Decimal,
        defensive_initial_stop_r: Decimal,
    ) -> dict[str, dict[str, object]]:
        rows = manifest.get("opportunities")
        if not isinstance(rows, list):
            raise ValueError("lifecycle custody requires manifest opportunities")

        bars_by_symbol: dict[str, object] = {}
        bounds_by_symbol: dict[str, tuple[tuple[object, ...], tuple[object, ...]]] = {}
        for symbol in SYMBOLS:
            evidence, _provenance = load_raw_m5_cached(roots[symbol])
            if evidence.symbol != symbol:
                raise ValueError(
                    f"lifecycle Market Atlas identity drift: {symbol}"
                )
            bars_by_symbol[symbol] = evidence.bars
            bounds_by_symbol[symbol] = (
                tuple(item.opened_at for item in evidence.bars),
                tuple(item.closed_at for item in evidence.bars),
            )

        result: dict[str, dict[str, object]] = {}
        for raw in rows:
            if not isinstance(raw, dict):
                raise ValueError("lifecycle manifest row must be mapping")
            signal = str(raw["signal_fingerprint"])
            symbol = str(raw["qore_symbol"])
            opportunity = raw.get("trader_opportunity")
            if not isinstance(opportunity, dict):
                raise ValueError("lifecycle trader opportunity missing")
            outcome = manifest_row_to_shadow_outcome_observation(raw)
            opened, closed = bounds_by_symbol[symbol]
            series = bars_by_symbol[symbol]
            start = bisect_left(opened, outcome.entry_at)
            end = bisect_right(closed, outcome.exit_at)
            managed = run_cibo_position_lifecycle(
                CiboPositionLifecycleInput(
                    signal_fingerprint=signal,
                    side=str(opportunity["side"]),
                    entry_at=outcome.entry_at,
                    horizon_at=outcome.exit_at,
                    entry_price=Decimal(str(opportunity["intended_entry"])),
                    structural_stop=Decimal(str(opportunity["stop_loss"])),
                    technical_target=Decimal(str(opportunity["take_profit"])),
                    provider_cost_per_volume_usd=(
                        manifest_row_provider_cost_per_volume_usd(raw)
                    ),
                    stop_risk_per_volume_usd=Decimal(
                        str(opportunity["stop_loss_per_volume"])
                    ),
                    original_settlement_gross_r=(
                        outcome.gross_structural_outcome_r
                    ),
                ),
                series[start:end] if start < end else (),
                features=features,
                adverse_loss_cut_r=adverse_loss_cut_r,
                adverse_partial_fraction=adverse_partial_fraction,
                bootstrap_partial_fraction=bootstrap_partial_fraction,
                adverse_tightened_stop_r=adverse_tightened_stop_r,
                defensive_initial_stop_r=defensive_initial_stop_r,
            )
            result[signal] = {
                "original_gross_r": format(
                    outcome.gross_structural_outcome_r,
                    "f",
                ),
                "managed_gross_r": format(managed.gross_r, "f"),
                "managed_exit_at": managed.exit_at.isoformat(),
                "data_available": managed.data_available,
                "actions": list(managed.actions),
                "events": managed.events,
                "enabled_features": sorted(
                    item.value for item in features
                ),
                "adverse_loss_cut_r": format(adverse_loss_cut_r, "f"),
                "adverse_partial_fraction": format(
                    adverse_partial_fraction,
                    "f",
                ),
                "bootstrap_partial_fraction": format(
                    bootstrap_partial_fraction,
                    "f",
                ),
                "adverse_tightened_stop_r": format(
                    adverse_tightened_stop_r,
                    "f",
                ),
                "defensive_initial_stop_r": format(
                    defensive_initial_stop_r,
                    "f",
                ),
                "risk_released_before_exit_fraction": format(
                    managed.risk_released_before_exit_fraction,
                    "f",
                ),
                "margin_released_before_exit_fraction": format(
                    managed.margin_released_before_exit_fraction,
                    "f",
                ),
            }
        return result

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
    policy_cache: dict[str, tuple[str, int]] = {}

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
                CiboLifecycleFeature(value)
                for value in feature_values
            )
            if feature_values
            else FULL_CIBO_LIFECYCLE_FEATURES
        )
        adverse_loss_cut_r = decimal_option(
            tokens,
            "--lifecycle-adverse-loss-cut-r",
            "-0.50",
        )
        adverse_partial_fraction = decimal_option(
            tokens,
            "--lifecycle-adverse-partial-fraction",
            "0.25",
        )
        bootstrap_partial_fraction = decimal_option(
            tokens,
            "--lifecycle-bootstrap-partial-fraction",
            "0.50",
        )
        adverse_tightened_stop_r = decimal_option(
            tokens,
            "--lifecycle-adverse-tightened-stop-r",
            "-0.50",
        )
        defensive_initial_stop_r = decimal_option(
            tokens,
            "--lifecycle-defensive-initial-stop-r",
            "-0.50",
        )
        policy_payload = {
            "features": sorted(item.value for item in features),
            "adverse_loss_cut_r": format(adverse_loss_cut_r, "f"),
            "adverse_partial_fraction": format(
                adverse_partial_fraction, "f"
            ),
            "bootstrap_partial_fraction": format(
                bootstrap_partial_fraction, "f"
            ),
            "adverse_tightened_stop_r": format(
                adverse_tightened_stop_r, "f"
            ),
            "defensive_initial_stop_r": format(
                defensive_initial_stop_r, "f"
            ),
        }
        policy_key = json.dumps(
            policy_payload,
            sort_keys=True,
            separators=(",", ":"),
        )
        cached = policy_cache.get(policy_key)
        if cached is not None:
            lifecycle_sidecars[name] = cached[0]
            lifecycle_counts[name] = cached[1]
            continue

        lifecycle = build_lifecycle_map(
            manifest,
            roots,
            features=features,
            adverse_loss_cut_r=adverse_loss_cut_r,
            adverse_partial_fraction=adverse_partial_fraction,
            bootstrap_partial_fraction=bootstrap_partial_fraction,
            adverse_tightened_stop_r=adverse_tightened_stop_r,
            defensive_initial_stop_r=defensive_initial_stop_r,
        )
        policy_id = hashlib.sha256(policy_key.encode()).hexdigest()[:16]
        sidecar = sidecar_root / f"policy-{policy_id}.json"
        sidecar.write_text(
            json.dumps(
                serialize_lifecycle_map(lifecycle),
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n",
            encoding="utf-8",
        )
        relative = sidecar.relative_to(args.output.parent).as_posix()
        count = len(lifecycle)
        policy_cache[policy_key] = (relative, count)
        lifecycle_sidecars[name] = relative
        lifecycle_counts[name] = count

    payload = {
        "schema": "qore.github-trader-lab.cibo-three-mode-prepared.v2",
        "primary_evidence_sha256": sha256(args.evidence),
        "primary_evidence": str(args.evidence.resolve()),
        "assets_root": str(assets.resolve()),
        "required_assets": list(required),
        "suite_sha256": sha256(args.suite),
        "lifecycle_sidecars": lifecycle_sidecars,
        "lifecycle_signal_counts": lifecycle_counts,
        "unique_lifecycle_policy_count": len(policy_cache),
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
