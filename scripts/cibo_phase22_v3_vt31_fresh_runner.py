"""Frozen VT31 V4 runner over the sealed Phase22 V3 M1 source."""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from collections import defaultdict
from datetime import date
from hashlib import sha256
from pathlib import Path
from typing import Any, cast

from qore.infrastructure.cibo_phase22_next_exam_governance import NEXT_CANDIDATE_ID
from qore.infrastructure.cibo_phase22_v3_vt31_source import (
    load_phase22_v3_vt31_m1,
)
from qore.infrastructure.market_data import OhlcSnapshot

FROZEN_SOURCE_GIT_SHA = "cac38ed14f20e066536910145027426fd23f5939"
WINDOW_START = date(2015, 4, 19)
WINDOW_END_EXCLUSIVE = date(2015, 10, 19)


def _load_frozen(root: Path) -> dict[str, Any]:
    if not root.is_dir():
        raise ValueError("frozen VT31 checkout missing")
    scripts = str((root / "scripts").resolve())
    source = str((root / "src").resolve())
    for value in (scripts, source):
        if value not in sys.path:
            sys.path.insert(0, value)
    return {
        "alt": importlib.import_module(
            "vt31_nas100_alt_tier_bifurcation_forensics_v1"
        ),
        "engine": importlib.import_module(
            "vt31_nas100_causal_hybrid_rearm_v1"
        ),
        "physical": importlib.import_module(
            "vt31_nas100_execution_binding_v4"
        ),
        "residual": importlib.import_module(
            "vt31_nas100_residual_regime_forensics_v2"
        ),
        "frozen": importlib.import_module(
            "vt31_nas100_structural_target_execution_binding_v4"
        ),
        "r25": importlib.import_module(
            "qore.infrastructure.trader_lab."
            "vt31_silver_bullet_r2_5_multi_index_research"
        ),
    }


def self_check(frozen_root: Path) -> dict[str, object]:
    modules = _load_frozen(frozen_root)
    frozen = modules["frozen"]
    identity = str(frozen.STRATEGY_IDENTITY)
    certified = str(frozen.CERTIFIED_STRATEGY_FINGERPRINT)
    binding = str(frozen.binding_fingerprint())
    if not identity or len(certified) != 64 or len(binding) != 64:
        raise ValueError("frozen VT31 V4 identity surface invalid")
    return {
        "frozen_source_git_sha": FROZEN_SOURCE_GIT_SHA,
        "strategy_identity": identity,
        "certified_strategy_fingerprint": certified,
        "execution_binding_fingerprint": binding,
        "fresh_outcomes_executed": False,
        "productive_authority": False,
    }


def _partition_executable_geometry(
    rows: list[dict[str, object]],
) -> tuple[list[dict[str, object]], int]:
    executable: list[dict[str, object]] = []
    censored = 0
    for row in rows:
        geometry = (
            row.get("entry"),
            row.get("initial_stop"),
            row.get("structural_target"),
        )
        if all(value is None for value in geometry):
            censored += 1
            continue
        if any(value is None for value in geometry):
            raise ValueError("VT31 V3 partial geometry must fail closed")
        executable.append(row)
    return executable, censored


def run_fresh(
    *,
    frozen_root: Path,
    source_root: Path,
) -> dict[str, object]:
    modules = _load_frozen(frozen_root)
    alt = modules["alt"]
    engine = modules["engine"]
    physical = modules["physical"]
    residual = modules["residual"]
    frozen = modules["frozen"]
    r25 = modules["r25"]

    source = load_phase22_v3_vt31_m1(source_root)

    def loader(_path: Path) -> tuple[OhlcSnapshot, ...]:
        return source.series

    original_residual = residual.load_market_evidence
    original_physical = physical.load_market_evidence
    residual.load_market_evidence = loader
    physical.load_market_evidence = loader
    try:
        rows, _evidence, diagnostics, stats = alt._current_rows(
            Path("PHASE22_V3_NAS100_M1")
        )
    finally:
        residual.load_market_evidence = original_residual
        physical.load_market_evidence = original_physical

    raw: dict[date, list[OhlcSnapshot]] = defaultdict(list)
    for bar in source.series:
        raw[r25._day(bar.opened_at)].append(bar)
    by_day = {
        local_day: tuple(sorted(items, key=lambda item: item.opened_at))
        for local_day, items in raw.items()
    }
    adjusted, binding_diag = physical._physicalize(rows, by_day=by_day)
    window_rows = [
        dict(row)
        for row in adjusted
        if WINDOW_START
        <= date.fromisoformat(cast(str, row["local_date"]))
        < WINDOW_END_EXCLUSIVE
    ]
    window_rows.sort(key=lambda row: cast(str, row["signal_at"]))
    executable, censored = _partition_executable_geometry(window_rows)

    opportunities: list[dict[str, object]] = []
    for row in executable:
        material = {
            "trader_id": "VT31_NAS100",
            "symbol": "NAS100",
            "signal_at": row["signal_at"],
            "side": row["side"],
            "entry": row["entry"],
            "stop": row["initial_stop"],
            "target": row["structural_target"],
            "strategy_identity": frozen.STRATEGY_IDENTITY,
            "execution_binding_fingerprint": frozen.binding_fingerprint(),
        }
        digest = sha256(
            json.dumps(
                material,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            ).encode("utf-8")
        ).hexdigest()
        opportunities.append(
            {
                **material,
                "signal_fingerprint": f"sha256:{digest}",
                "entry_at": row.get("filled_at"),
                "exit_at": row.get("exit_at"),
                "exit_reason": row.get("exit_reason"),
                "realized_r": row.get("r_multiple"),
                "methodology_sha256": (
                    "sha256:" + str(frozen.CERTIFIED_STRATEGY_FINGERPRINT)
                ),
                "causal_provenance": [
                    f"git:{FROZEN_SOURCE_GIT_SHA}",
                    f"sha256:{source.raw_sha256}",
                    "sha256:" + str(frozen.binding_fingerprint()),
                ],
                "volume": None,
            }
        )

    metrics = residual._metrics(executable)
    mc = engine._monte_carlo(
        executable,
        variant="VT31_NAS100_STRUCTURAL_TARGET_V1:PHASE22_V3_ONE_SHOT",
    )
    return {
        "schema": "qore.cibo.phase22.v3-vt31-v4-fresh.v1",
        "candidate_id": NEXT_CANDIDATE_ID,
        "trader_id": "VT31_NAS100",
        "symbol": "NAS100",
        "frozen_source_git_sha": FROZEN_SOURCE_GIT_SHA,
        "strategy_identity": frozen.STRATEGY_IDENTITY,
        "certified_strategy_fingerprint": (
            frozen.CERTIFIED_STRATEGY_FINGERPRINT
        ),
        "execution_binding_fingerprint": frozen.binding_fingerprint(),
        "window": {
            "start": WINDOW_START.isoformat(),
            "end_exclusive": WINDOW_END_EXCLUSIVE.isoformat(),
        },
        "source": {
            "raw_sha256": source.raw_sha256,
            "source_fingerprint": source.fingerprint,
            "collector_git_sha": source.collector_git_sha,
            "provider_symbol": source.provider_symbol,
            "retained_m1_bars": len(source.series),
        },
        "pre_geometry_population_count": len(window_rows),
        "censored_geometry_count": censored,
        "opportunity_count": len(opportunities),
        "opportunities": opportunities,
        "metrics": metrics,
        "monte_carlo": mc,
        "diagnostics": diagnostics,
        "source_stats": stats,
        "binding_diagnostics": binding_diag,
        "methodology_changed": False,
        "geometry_reconstructed": False,
        "selection_uses_realized_r": False,
        "legacy_trader_sizing_used_for_cibo": False,
        "fresh_outcomes_executed": True,
        "productive_authority": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frozen-root", type=Path, required=True)
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()

    if args.self_check:
        print(json.dumps(self_check(args.frozen_root), sort_keys=True))
        return
    if args.source_root is None or args.output is None:
        raise SystemExit("--source-root and --output required for fresh run")
    payload = run_fresh(
        frozen_root=args.frozen_root,
        source_root=args.source_root,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "candidate_id": payload["candidate_id"],
                "trader_id": payload["trader_id"],
                "opportunity_count": payload["opportunity_count"],
                "censored_geometry_count": payload["censored_geometry_count"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
