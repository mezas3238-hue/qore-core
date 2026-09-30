"""V47-S2C1 decision-time causal failure screen for consumed FRACTAL rows."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.trader_lab import (
    capitalizer_source_strategy_gross_economics_v47_s2b as s2b,
)
from qore.infrastructure.trader_lab import (
    capitalizer_source_strategy_isolation_v47_s1 as s1,
)
from qore.infrastructure.trader_lab import (
    capitalizer_source_strategy_isolation_v47_s2 as s2,
)

IDENTITY = "QORE_CAPITALIZER_V47_S2C1_FRACTAL_CAUSAL_FAILURE_SCREEN"
PREDECLARATION_COMMENT_ID = 5901906100
SOURCE_S2A_RUN_ID = 36642644284
SOURCE_S2A_SHA = "ff6c9745690dde76520aecf608e44401622a1074"
SOURCE_S2B_RUN_ID = 36651366703
SOURCE_S2B_SHA = "59d826f3b24031e52e6c0f32e8cca1ecfb4d0524"


def _target_r_band(value: Decimal) -> str:
    if value < Decimal("2"):
        return "<2R"
    if value < Decimal("4"):
        return "[2,4)R"
    if value < Decimal("8"):
        return "[4,8)R"
    if value < Decimal("16"):
        return "[8,16)R"
    return ">=16R"


def _load_s2a(root: Path) -> tuple[s2.S2AdmittedFillRow, ...]:
    rows: list[s2.S2AdmittedFillRow] = []
    for path in sorted(root.rglob("capitalizer-s2a-*-max3.jsonl")):
        for line in path.read_text().splitlines():
            if line.strip():
                rows.append(s2.S2AdmittedFillRow(**json.loads(line)))
    if len(rows) != 91:
        raise ValueError(f"S2C1 requires 91 frozen S2A rows, got {len(rows)}")
    return tuple(rows)


def _load_s2b(root: Path) -> tuple[s2b.S2BGrossTrade, ...]:
    rows: list[s2b.S2BGrossTrade] = []
    for path in sorted(root.rglob("capitalizer-s2b-chronology.jsonl")):
        for line in path.read_text().splitlines():
            if line.strip():
                rows.append(s2b.S2BGrossTrade(**json.loads(line)))
    if len(rows) != 91:
        raise ValueError(f"S2C1 requires 91 frozen S2B rows, got {len(rows)}")
    return tuple(rows)


def _key(period: str, symbol: str, entry_at: str) -> tuple[str, str, str]:
    return period, symbol, entry_at


def _feature_values(
    trade: s2b.S2BGrossTrade,
    source: s2.S2AdmittedFillRow,
) -> dict[str, str]:
    at = datetime.fromisoformat(trade.entry_at).astimezone(s1.NEW_YORK)
    return {
        "symbol": trade.symbol,
        "session": trade.session,
        "side": trade.side,
        "entry_mode": source.entry_mode,
        "target_kind": source.target_kind,
        "target_provenance": source.target_provenance,
        "ny_entry_hour": f"{at.hour:02d}",
        "weekday": at.strftime("%A").upper(),
        "target_r_band": _target_r_band(Decimal(trade.target_r)),
    }


def _metrics(rows: tuple[s2b.S2BGrossTrade, ...]) -> dict[str, object]:
    return asdict(s2b.metrics(rows))


def build_screen(
    s2a_root: Path,
    s2b_root: Path,
    output: Path,
) -> dict[str, object]:
    source_rows = _load_s2a(s2a_root)
    trade_rows = _load_s2b(s2b_root)
    source_map = {
        _key(row.period, row.symbol, row.entry_at): row
        for row in source_rows
    }
    if len(source_map) != len(source_rows):
        raise ValueError("S2C1 S2A key collision")
    joined: list[tuple[s2b.S2BGrossTrade, s2.S2AdmittedFillRow]] = []
    for trade in trade_rows:
        source = source_map.get(_key(trade.period, trade.symbol, trade.entry_at))
        if source is None:
            raise ValueError("S2C1 frozen S2A/S2B join mismatch")
        joined.append((trade, source))

    feature_names = tuple(
        _feature_values(joined[0][0], joined[0][1]).keys()
    )
    features: dict[str, object] = {}
    for feature in feature_names:
        by_value: dict[str, list[tuple[s2b.S2BGrossTrade, s2.S2AdmittedFillRow]]] = (
            defaultdict(list)
        )
        for pair in joined:
            by_value[_feature_values(pair[0], pair[1])[feature]].append(pair)

        values: dict[str, object] = {}
        for value, pairs in sorted(by_value.items()):
            all_rows = tuple(pair[0] for pair in pairs)
            period_payload: dict[str, object] = {}
            for period in ("reserved", "validation", "development"):
                subset = tuple(
                    pair[0] for pair in pairs if pair[0].period == period
                )
                period_payload[period] = _metrics(subset)
            values[value] = {
                "periods": period_payload,
                "combined_descriptive_only": _metrics(all_rows),
            }
        features[feature] = values

    payload: dict[str, object] = {
        "identity": IDENTITY,
        "predeclaration_comment_id": PREDECLARATION_COMMENT_ID,
        "source_s2a_run_id": SOURCE_S2A_RUN_ID,
        "source_s2a_sha": SOURCE_S2A_SHA,
        "source_s2b_run_id": SOURCE_S2B_RUN_ID,
        "source_s2b_sha": SOURCE_S2B_SHA,
        "frozen_population_rows": len(joined),
        "features": features,
        "target_r_bins": ["<2R", "[2,4)R", "[4,8)R", "[8,16)R", ">=16R"],
        "feature_promotion_allowed": False,
        "combined_metrics_have_certification_authority": False,
        "fresh_holdout_opened": False,
        "trader_certified": False,
    }
    output.mkdir(parents=True, exist_ok=True)
    path = output / "capitalizer-v47-s2c1-fractal-causal-failure-screen.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, sort_keys=True))
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("s2a_root", type=Path)
    parser.add_argument("s2b_root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build_screen(args.s2a_root, args.s2b_root, args.output)


if __name__ == "__main__":
    main()
