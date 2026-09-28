"""Collect frozen V40 pre-entry path state for exact V38-selected entrants."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.trader_lab import (
    capitalizer_preentry_causal_m1_path_state_v40 as path_state,
)
from qore.infrastructure.trader_lab import (
    capitalizer_preentry_native_m1_geometry_separability_v38 as v38,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
    iter_cibo_m1,
)

IDENTITY = "QORE_CAPITALIZER_PREENTRY_CAUSAL_M1_PATH_COLLECTOR_V40"
SLUGS = ("development", "validation", "reserved")


@dataclass(frozen=True, slots=True)
class SelectedPathState:
    symbol: str
    session: str
    operating_date: str
    side: str
    entry_at: str
    provenance: str
    path: path_state.PreentryCausalM1PathState
    authoritative_identity_joined: bool = True
    outcome_used_for_path: bool = False
    exit_used_for_path: bool = False

    def __post_init__(self) -> None:
        if not self.authoritative_identity_joined:
            raise ValueError("V40 path must join authoritative entrant identity")
        if self.outcome_used_for_path or self.exit_used_for_path:
            raise ValueError("V40 path cannot use outcome/exit")
        if self.path.symbol != self.symbol:
            raise ValueError("V40 joined symbol mismatch")
        if self.path.side != self.side:
            raise ValueError("V40 joined side mismatch")
        if self.path.entry_at != self.entry_at:
            raise ValueError("V40 joined entry timestamp mismatch")


def _aware(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("V40 requires timezone-aware entry timestamp")
    return parsed


def _path_bars(
    by_open: dict[datetime, CapitalizerM1Bar],
    *,
    entry_at: datetime,
) -> tuple[CapitalizerM1Bar, ...]:
    start = entry_at - timedelta(minutes=path_state.LOOKBACK_MINUTES)
    result: list[CapitalizerM1Bar] = []
    for minute in range(path_state.LOOKBACK_MINUTES):
        opened_at = start + timedelta(minutes=minute)
        bar = by_open.get(opened_at)
        if bar is None:
            raise ValueError(
                "V40 exact 30m causal path missing M1 bar at "
                f"{opened_at.isoformat()}"
            )
        result.append(bar)
    return tuple(result)


def collect_symbol(
    *,
    symbol: str,
    m1_root: Path,
    selected_geometry_root: Path,
    output: Path,
) -> dict[str, object]:
    bars = tuple(iter_cibo_m1(m1_root))
    if not bars:
        raise ValueError("V40 M1 root is empty")
    if {bar.symbol for bar in bars} != {symbol}:
        raise ValueError("V40 M1 root symbol mismatch")
    by_open = {bar.opened_at: bar for bar in bars}
    if len(by_open) != len(bars):
        raise ValueError("V40 duplicate M1 open timestamp")

    output.mkdir(parents=True, exist_ok=True)
    period_reports: list[dict[str, object]] = []

    for slug in SLUGS:
        geometry_by_key = v38._load_period_geometry(
            selected_geometry_root,
            slug=slug,
        )
        selected = tuple(
            sorted(
                (
                    row
                    for row in geometry_by_key.values()
                    if row.symbol == symbol
                ),
                key=lambda row: row.entry_at,
            )
        )
        if not selected:
            raise ValueError(f"V40 {slug} has no {symbol} entrants")

        rows: list[SelectedPathState] = []
        for row in selected:
            entry_at = _aware(row.entry_at)
            frozen_path = _path_bars(by_open, entry_at=entry_at)
            state = path_state.build_path_state(
                symbol=row.symbol,
                side=row.side,
                entry_at=entry_at,
                risk_price=Decimal(row.geometry.risk_price),
                bars=frozen_path,
            )
            rows.append(
                SelectedPathState(
                    symbol=row.symbol,
                    session=row.session,
                    operating_date=row.operating_date,
                    side=row.side,
                    entry_at=row.entry_at,
                    provenance=row.provenance,
                    path=state,
                )
            )

        stem = f"capitalizer-v40-{slug}-{symbol.lower()}-path"
        with (output / f"{stem}.jsonl").open(
            "w",
            encoding="utf-8",
        ) as handle:
            for selected_path in rows:
                handle.write(
                    json.dumps(asdict(selected_path), sort_keys=True) + "\n"
                )

        report: dict[str, object] = {
            "identity": IDENTITY,
            "slug": slug,
            "symbol": symbol,
            "selected_entrants": len(selected),
            "path_rows": len(rows),
            "coverage": "1",
            "lookback_minutes": path_state.LOOKBACK_MINUTES,
            "feature_dimension": len(path_state.FEATURE_NAMES),
            "path_only_representation": True,
            "entry_bar_used": False,
            "future_bar_used": False,
            "outcome_used_for_path": False,
            "exit_used_for_path": False,
            "mae_mfe_used": False,
            "feature_timestamp_le_entry": True,
            "fresh_holdout_opened": False,
            "runtime_policy_candidate": False,
            "trader_certified": False,
        }
        (output / f"{stem}-coverage.json").write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        period_reports.append(report)

    summary: dict[str, object] = {
        "identity": IDENTITY,
        "symbol": symbol,
        "periods": period_reports,
        "all_periods_full_coverage": all(
            row["coverage"] == "1"
            and row["selected_entrants"] == row["path_rows"]
            for row in period_reports
        ),
        "fresh_holdout_opened": False,
        "runtime_policy_candidate": False,
        "trader_certified": False,
    }
    (output / f"capitalizer-v40-{symbol.lower()}-path-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary


def load_path_rows(
    root: Path,
    *,
    slug: str,
) -> dict[tuple[str, str], SelectedPathState]:
    paths = sorted(root.rglob(f"capitalizer-v40-{slug}-*-path.jsonl"))
    if not paths:
        raise ValueError(f"V40 requires path ledgers for {slug}")
    rows: list[SelectedPathState] = []
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                raw = json.loads(line)
                if not isinstance(raw, dict):
                    raise ValueError("V40 path row must be JSON object")
                nested = raw.get("path")
                if not isinstance(nested, dict):
                    raise ValueError("V40 selected path missing nested state")
                raw["path"] = path_state.from_json_dict(nested)
                rows.append(SelectedPathState(**raw))
    by_key = {(row.symbol, row.entry_at): row for row in rows}
    if len(by_key) != len(rows):
        raise ValueError("V40 duplicate selected path identity")
    return by_key


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("m1_root", type=Path)
    parser.add_argument("selected_geometry_root", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--symbol", required=True)
    args = parser.parse_args()

    report = collect_symbol(
        symbol=args.symbol,
        m1_root=args.m1_root,
        selected_geometry_root=args.selected_geometry_root,
        output=args.output,
    )
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
