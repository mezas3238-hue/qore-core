"""Blind source validation for the preregistered CIBO 2017H1 holdout.

This validator reads only immutable market-source metadata/timestamps. It never
runs Trader logic, inspects trade outcomes, or changes the preregistered window.
"""

from __future__ import annotations

import argparse
import json
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_holdout_registry import (
    PREREGISTERED_USD60_HOLDOUT,
    candidate_is_burn_clean_for_all_lineages,
)

_REQUIRED = {
    "AUDJPY": 10476530915,
    "EURUSD": 10475354631,
    "GBPJPY": 10475453293,
    "GBPUSD": 10475449182,
    "NAS100": 10476153072,
    "XAUUSD": 10476557530,
}
_HOLDOUT_START = datetime(2017, 1, 1, tzinfo=UTC)
_HOLDOUT_END = datetime(2017, 7, 1, tzinfo=UTC)


@dataclass(frozen=True, slots=True)
class BlindMarketSourceValidation:
    symbol: str
    artifact_id: int
    requested_start: datetime
    requested_end_exclusive: datetime
    first_observed_m5: datetime
    last_observed_m5: datetime
    retained_bars_year: int
    retained_bars_holdout: int
    first_holdout_bar: datetime
    last_holdout_bar: datetime
    months_present: tuple[int, ...]
    raw_integrity_status: str
    contradictory_bars: int
    out_of_window_bars: int
    timestamp_alignment_errors: int
    unresolved_gap_runs: int

    def __post_init__(self) -> None:
        if self.symbol not in _REQUIRED:
            raise CiboCapitalManagementError("unexpected holdout source symbol")
        if self.artifact_id != _REQUIRED[self.symbol]:
            raise CiboCapitalManagementError("holdout source artifact drift")
        if self.requested_start != datetime(2017, 1, 1, tzinfo=UTC):
            raise CiboCapitalManagementError("2017 source start drift")
        if self.requested_end_exclusive != datetime(2018, 1, 1, tzinfo=UTC):
            raise CiboCapitalManagementError("2017 source end drift")
        if self.raw_integrity_status != "CLEAN_PROVIDER_PAYLOAD":
            raise CiboCapitalManagementError("market source is not clean provider payload")
        if any(
            value != 0
            for value in (
                self.contradictory_bars,
                self.out_of_window_bars,
                self.timestamp_alignment_errors,
            )
        ):
            raise CiboCapitalManagementError("market source integrity violation")
        if self.retained_bars_year <= 0 or self.retained_bars_holdout <= 0:
            raise CiboCapitalManagementError("market source has no retained bars")
        if self.months_present != (1, 2, 3, 4, 5, 6):
            raise CiboCapitalManagementError("2017H1 monthly source coverage incomplete")
        if not (_HOLDOUT_START <= self.first_holdout_bar < _HOLDOUT_END):
            raise CiboCapitalManagementError("first holdout bar outside preregistered window")
        if not (_HOLDOUT_START < self.last_holdout_bar < _HOLDOUT_END):
            raise CiboCapitalManagementError("last holdout bar outside preregistered window")
        if self.first_holdout_bar > datetime(2017, 1, 3, 0, 0, tzinfo=UTC):
            raise CiboCapitalManagementError("January 2017 market opening coverage missing")
        if self.last_holdout_bar < datetime(2017, 6, 29, 0, 0, tzinfo=UTC):
            raise CiboCapitalManagementError("June 2017 market closing coverage missing")


def validate_artifact(path: Path, *, artifact_id: int) -> BlindMarketSourceValidation:
    if not isinstance(path, Path) or not path.is_file():
        raise CiboCapitalManagementError("market source ZIP is required")
    with zipfile.ZipFile(path) as archive:
        manifest_names = [
            name
            for name in archive.namelist()
            if name.endswith("PARTITION_MANIFEST/2017.json")
        ]
        raw_names = [
            name
            for name in archive.namelist()
            if name.endswith("RAW_M5_LEDGER/2017.jsonl")
        ]
        if len(manifest_names) != 1 or len(raw_names) != 1:
            raise CiboCapitalManagementError(
                "market source must contain one 2017 manifest and raw ledger"
            )
        manifest = json.loads(archive.read(manifest_names[0]))
        symbol = str(manifest["canonical_symbol"])
        timestamps: list[datetime] = []
        with archive.open(raw_names[0]) as stream:
            for raw_line in stream:
                row = json.loads(raw_line)
                opened_at = datetime.fromisoformat(str(row["opened_at"]))
                if _HOLDOUT_START <= opened_at < _HOLDOUT_END:
                    timestamps.append(opened_at)
        if not timestamps:
            raise CiboCapitalManagementError("2017H1 raw market source is empty")
        ordered = tuple(sorted(timestamps))
        if len(ordered) != len(set(ordered)):
            raise CiboCapitalManagementError("2017H1 raw market source duplicates timestamps")
        result = BlindMarketSourceValidation(
            symbol=symbol,
            artifact_id=artifact_id,
            requested_start=datetime.fromisoformat(str(manifest["requested_start"])),
            requested_end_exclusive=datetime.fromisoformat(
                str(manifest["requested_end_exclusive"])
            ),
            first_observed_m5=datetime.fromisoformat(str(manifest["first_observed_m5"])),
            last_observed_m5=datetime.fromisoformat(str(manifest["last_observed_m5"])),
            retained_bars_year=int(manifest["retained_bars"]),
            retained_bars_holdout=len(ordered),
            first_holdout_bar=ordered[0],
            last_holdout_bar=ordered[-1],
            months_present=tuple(sorted({item.month for item in ordered})),
            raw_integrity_status=str(manifest["raw_integrity_status"]),
            contradictory_bars=int(manifest["contradictory_bars"]),
            out_of_window_bars=int(manifest["out_of_window_bars"]),
            timestamp_alignment_errors=int(manifest["timestamp_alignment_errors"]),
            unresolved_gap_runs=int(manifest["unresolved_gap_runs"]),
        )
        return result


def report(validations: tuple[BlindMarketSourceValidation, ...]) -> dict[str, object]:
    by_symbol = {item.symbol: item for item in validations}
    if tuple(sorted(by_symbol)) != tuple(sorted(_REQUIRED)):
        raise CiboCapitalManagementError("six-symbol source set is incomplete")
    candidate = PREREGISTERED_USD60_HOLDOUT
    if candidate.start_at != _HOLDOUT_START or candidate.end_exclusive_at != _HOLDOUT_END:
        raise CiboCapitalManagementError("holdout preregistration drift")
    if not candidate_is_burn_clean_for_all_lineages(candidate):
        raise CiboCapitalManagementError("holdout candidate overlaps confirmed burn")
    return {
        "schema": "qore.cibo.usd60.holdout_source_validation.v1",
        "candidate_id": candidate.candidate_id,
        "holdout_start": _HOLDOUT_START.isoformat(),
        "holdout_end_exclusive": _HOLDOUT_END.isoformat(),
        "selection_outcomes_inspected": False,
        "trader_outcomes_executed": False,
        "burn_clean": True,
        "market_source_ready": True,
        "provider_economics_ready": False,
        "status": "MARKET_SOURCE_READY_PROVIDER_ECONOMICS_PENDING",
        "symbols": {
            symbol: {
                "artifact_id": item.artifact_id,
                "retained_bars_year": item.retained_bars_year,
                "retained_bars_holdout": item.retained_bars_holdout,
                "first_holdout_bar": item.first_holdout_bar.isoformat(),
                "last_holdout_bar": item.last_holdout_bar.isoformat(),
                "months_present": list(item.months_present),
                "raw_integrity_status": item.raw_integrity_status,
                "contradictory_bars": item.contradictory_bars,
                "out_of_window_bars": item.out_of_window_bars,
                "timestamp_alignment_errors": item.timestamp_alignment_errors,
                "unresolved_gap_runs": item.unresolved_gap_runs,
            }
            for symbol, item in sorted(by_symbol.items())
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    for symbol in sorted(_REQUIRED):
        parser.add_argument(f"--{symbol.lower()}", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    validations = tuple(
        validate_artifact(
            getattr(args, symbol.lower()),
            artifact_id=artifact_id,
        )
        for symbol, artifact_id in sorted(_REQUIRED.items())
    )
    payload = report(validations)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
