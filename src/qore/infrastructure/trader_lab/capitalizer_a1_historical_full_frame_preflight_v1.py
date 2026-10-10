"""Nine-market historical Master Frame INPUT audit over immutable native-M1 sensors.

This is the mandatory *readiness* gate before calling a FULL real-data
Master Frame replay. Source/method/HTF states are NOT manufactured from
the mere presence of sensor JSON strings. A successful census can return
BLOCKED_MISSING_NINE_MARKET_CAUSAL_WORLD; that is not a successful replay.

GitHub-only research. No trade selection, no future outcomes, no MT5.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    V49Opportunity,
)
from qore.infrastructure.trader_lab.capitalizer_master_cognitive_contract import (
    NINE_MARKET_UNIVERSE,
)
from qore.infrastructure.trader_lab.capitalizer_v50_g_causal_decision_trace import (
    source_opportunity_id,
)

IDENTITY = "QORE_SCALPER_A1_FULL_FRAME_HISTORICAL_INPUT_PREFLIGHT_V1"
NEEDED_PROVENANCE = (
    "NATIVE_NINE_MARKET_CAUSAL_WORLD_AT_EACH_M1_BARRIER",
    "NINE_MARKET_ASOF_PERCEPTION_EVIDENCE",
    "NINE_MARKET_ASOF_REGIME_EVIDENCE",
    "CROSS_MARKET_CAUSAL_GRAPH_ASOF",
    "ASOF_PORTFOLIO_POSITION_AND_SESSION_LEDGERS",
    "AUTHOR_RULE_AND_H1_M15_INDEPENDENT_ATTESTATION",
)
CRITICAL_SENSORS = (
    "ACTUAL_M15_STRUCTURE_REVALIDATION",
    "M1_PROTECTED_SWING_ATTESTATION",
    "H1_TARGET_ROOM_R",
    "FULL_COGNITIVE_MASTER_FRAME",
)


def _read_jsonl(path: Path) -> tuple[dict[str, Any], ...]:
    return tuple(
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    )


def _aware(value: str) -> datetime:
    at = datetime.fromisoformat(value)
    if at.tzinfo is None or at.utcoffset() is None:
        raise ValueError("historical evidence timestamps must be timezone-aware")
    return at


@dataclass(frozen=True, slots=True)
class A1HistoricalPreflightReport:
    identity: str
    historical_markets: int
    source_opportunities: int
    source_sensors_reconciled: int
    sensor_source_disagreements: int
    observed_source_m1_closes: int
    critical_sensor_statuses: dict[str, dict[str, int]]
    nine_market_world_barriers_attested: int
    barrier_evidence_gaps: tuple[str, ...]
    current_status: str
    master_frame_historical_trades: int | None = None
    full_historical_master_frame_replayed: bool = False
    measured_cognitive_pf: str | None = None
    measured_cognitive_drawdown_r: str | None = None
    trader_certified: bool = False
    live_authorized: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY or self.historical_markets != 9:
            raise ValueError("preflight requires nine historical native-M1 markets")
        if not (
            self.source_opportunities == self.source_sensors_reconciled
            == self.observed_source_m1_closes
        ):
            raise ValueError("historical source census dropped a causal M1 observation")
        if (
            self.nine_market_world_barriers_attested != 0
            or self.current_status != "BLOCKED_MISSING_NINE_MARKET_CAUSAL_WORLD"
            or self.master_frame_historical_trades is not None
            or self.full_historical_master_frame_replayed
            or self.measured_cognitive_pf is not None
            or self.measured_cognitive_drawdown_r is not None
            or self.trader_certified
            or self.live_authorized
        ):
            raise ValueError("preflight cannot pretend nine-market cognition was run")


def audit_pinned_historical_inputs(
    *, original_root: Path, sensor_root: Path,
) -> A1HistoricalPreflightReport:
    """Reconcile every source and predecision M1 sensor on exact source ID.

    No outcome ledger, H1 forward expiration, fabricated regime or stale
    nine-market observation enters cognition. This does NOT call the frame.
    """
    original_paths = sorted(original_root.rglob(
        "capitalizer-*-v49-hf-capacity-opportunities.jsonl"
    ))
    sensor_paths = sorted(sensor_root.rglob("scalper-entry-sensors-rows.jsonl"))
    if len(original_paths) != 9 or len(sensor_paths) != 9:
        raise ValueError("nine source books and nine native-M1 sensor books required")
    originals: dict[str, V49Opportunity] = {}
    market_symbols: set[str] = set()
    for path in original_paths:
        rows = tuple(V49Opportunity(**row) for row in _read_jsonl(path))
        if not rows or len({r.symbol for r in rows}) != 1:
            raise ValueError("source market book empty/mixed")
        market_symbols.add(rows[0].symbol)
        for original in rows:
            sid = source_opportunity_id(original)
            if sid in originals:
                raise ValueError("duplicate original source identity")
            at = _aware(original.m1_trigger_confirmed_at)
            if (
                not _aware(original.h1_state_from)
                <= _aware(original.m15_setup_confirmed_at) <= at
            ):
                raise ValueError("source H1/M15/M1 ancestry is future or reversed")
            originals[sid] = original
    if market_symbols != set(NINE_MARKET_UNIVERSE):
        raise ValueError("nine frozen markets incomplete")
    sensors: dict[str, dict[str, Any]] = {}
    statuses: dict[str, Counter[str]] = {
        key: Counter() for key in CRITICAL_SENSORS
    }
    disagreements = 0
    for path in sensor_paths:
        for row in _read_jsonl(path):
            sid = row["source_opportunity_id"]
            if sid in sensors or sid not in originals:
                raise ValueError("sensor identity repeated or has no original parent")
            original = originals[sid]
            if (
                row["symbol"] != original.symbol
                or row["original_entry_at"] != original.m1_trigger_confirmed_at
                or row["original_trigger_family"] != original.m1_trigger_family
                or row["original_source_signal_preserved"] is not True
                or row["execution_authorized"] is not False
                or row["hard_entry_gate_added"] is not False
                or row["full_master_frame_attested"] is not False
            ):
                raise ValueError("sensor shadow altered or claimed source execution")
            by_name = {entry["sensor"]: entry for entry in row["sensors"]}
            if len(by_name) != len(row["sensors"]):
                raise ValueError("duplicated native M1 sensor keys")
            if "H1_BIAS_DECLARED" not in by_name:
                raise ValueError("H1 declared source input is absent")
            for name in CRITICAL_SENSORS:
                if name not in by_name:
                    raise ValueError("missing critical sensor " + name)
                sensor = by_name[name]
                if _aware(sensor["observed_at"]) > _aware(
                    original.m1_trigger_confirmed_at
                ):
                    raise ValueError("future sensor entered source cognitive history")
                statuses[name][str(sensor["status"])] += 1
            if not row["sensor_source_identity_match"]:
                disagreements += 1
            sensors[sid] = row
    if set(sensors) != set(originals):
        raise ValueError("missing historical M1 source IDs in sensor inputs")
    return A1HistoricalPreflightReport(
        identity=IDENTITY,
        historical_markets=9,
        source_opportunities=len(originals),
        source_sensors_reconciled=len(sensors),
        sensor_source_disagreements=disagreements,
        observed_source_m1_closes=len(sensors),
        critical_sensor_statuses={
            key: dict(sorted(value.items())) for key, value in sorted(statuses.items())
        },
        nine_market_world_barriers_attested=0,
        barrier_evidence_gaps=NEEDED_PROVENANCE,
        current_status="BLOCKED_MISSING_NINE_MARKET_CAUSAL_WORLD",
    )


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("original_root", type=Path)
    p.add_argument("sensor_root", type=Path)
    p.add_argument("output", type=Path)
    args = p.parse_args()
    report = audit_pinned_historical_inputs(
        original_root=args.original_root, sensor_root=args.sensor_root
    )
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "scalper-a1-full-frame-historical-preflight.json").write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(asdict(report), sort_keys=True))


if __name__ == "__main__":
    main()
