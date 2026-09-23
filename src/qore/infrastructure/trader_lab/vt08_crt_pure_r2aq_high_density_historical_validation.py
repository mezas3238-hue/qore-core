"""R2-AQ historical validation of the high-density FX core.

Frozen after R2-AO, before older-window outcomes.

Candidate core:
- ROLLING_H4 timing lattice;
- FIXED_1_5R target;
- no EFF or context filter;
- one selected hypothesis max per parent;
- R2-G NEWEST_SUPERSEDES_CONFIRMATION_FIRST;
- source-candle structural stop;
- C3-close expiry;
- STOP_FIRST.

Validation windows are older than the 2020-2026 R2-AO development evidence:
- AUDUSD: 2016-09-21 -> 2020-09-21
- USDJPY: 2014-09-21 -> 2020-09-21

This is historical validation, not untouched final certification evidence.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import (
    Model1LabTrade,
    _summary,
    aggregate_complete_m15,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2af_audusd_target_family import (
    TARGET_MULTIPLE,
    TargetArm,
    _resolve_fixed_target,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2aj_timing_lattice_density import (
    TimingLattice,
    _parents,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2c_close_unmitigated_replay import (
    build_close_unmitigated_breach_groups,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2e_source_multiplicity_census import (
    _aligned_sources,
    _c3_m15,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2g_competition_lab import (
    CompetitionPolicy,
    select_competing_hypothesis,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_window_evidence import load_m5_window
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket

IDENTITY = "VT08_CRT_PURE_R2AQ_HIGH_DENSITY_HISTORICAL_VALIDATION_001"
SCHEMA = "qore.vt08.crt_pure.r2aq_high_density_historical_validation.v1"
BASE_POLICY = CompetitionPolicy.NEWEST_SUPERSEDES_CONFIRMATION_FIRST
LATTICE = TimingLattice.ROLLING_H4
ARM = TargetArm.FIXED_1_5R
MULTIPLE = TARGET_MULTIPLE[ARM]


@dataclass(frozen=True, slots=True)
class ValidationWindow:
    market: CrtPureMarket
    start: datetime
    end: datetime


WINDOWS: dict[CrtPureMarket, ValidationWindow] = {
    CrtPureMarket.AUDUSD: ValidationWindow(
        market=CrtPureMarket.AUDUSD,
        start=datetime(2016, 9, 21, 0, 0, tzinfo=UTC),
        end=datetime(2020, 9, 21, 0, 0, tzinfo=UTC),
    ),
    CrtPureMarket.USDJPY: ValidationWindow(
        market=CrtPureMarket.USDJPY,
        start=datetime(2014, 9, 21, 0, 0, tzinfo=UTC),
        end=datetime(2020, 9, 21, 0, 0, tzinfo=UTC),
    ),
}


def _annual_boundaries(window: ValidationWindow) -> tuple[datetime, ...]:
    return tuple(
        datetime(year, 9, 21, 0, 0, tzinfo=UTC)
        for year in range(window.start.year, window.end.year + 1)
    )


def _window(
    rows: tuple[Model1LabTrade, ...],
    start: datetime,
    end: datetime,
) -> tuple[Model1LabTrade, ...]:
    return tuple(
        row
        for row in rows
        if start <= datetime.fromisoformat(row.entry_opened_at) < end
    )


def _annual(
    rows: tuple[Model1LabTrade, ...],
    window: ValidationWindow,
) -> dict[str, dict[str, Any]]:
    boundaries = _annual_boundaries(window)
    return {
        f"{left.year}_{right.year}": _summary(_window(rows, left, right))
        for left, right in zip(
            boundaries[:-1],
            boundaries[1:],
            strict=True,
        )
    }


def run_validation(
    market: CrtPureMarket,
) -> tuple[tuple[Model1LabTrade, ...], dict[str, Any]]:
    window = WINDOWS[market]
    bars = load_m5_window(
        market,
        start=window.start - timedelta(days=2),
        end_exclusive=window.end + timedelta(days=2),
    )
    # _parents uses module-level 2020-2026 limits, so this validation cannot use it.
    # Build rolling parents with a local imported helper in the next revision.
    raise RuntimeError("R2-AQ rolling parent window helper not bound")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("market", choices=[item.value for item in WINDOWS])
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    market = CrtPureMarket(args.market)
    trades, report = run_validation(market)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    with (args.output / "trades.jsonl").open("w", encoding="utf-8") as handle:
        for trade in trades:
            handle.write(json.dumps(asdict(trade), sort_keys=True) + "\n")
    print("CRT_R2AQ_HISTORICAL_JSON=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
