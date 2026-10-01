"""Phase22 V2 Journey/Target dependency lineage for frozen Turtle Traders.

This module does not read V2 on import. The build function is intended only
inside the one-shot execution after the consumption guard is READY. It reuses
the frozen Journey and Target Destination algorithms while replacing historical
10Y provenance constants with the exact Phase22 source/run lineage.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from qore.infrastructure.cibo_phase22_holdout_v2_source_receipt import (
    M5_COLLECTOR_GIT_SHA,
    M5_SOURCE_RUN_ID,
    V2_SOURCE_BINDINGS,
)
from qore.infrastructure.trader_lab import (
    cibo_market_atlas_journey_extractor_v1 as journey,
)
from qore.infrastructure.trader_lab import (
    cibo_market_atlas_target_destination_v2 as target,
)

V2_M5_SOURCE_IDENTITY = "CIBO_PHASE22_HOLDOUT_V2_M5_SOURCE_V1"


@dataclass(frozen=True, slots=True)
class Phase22TurtleDependencyLineage:
    symbol: str
    source_run_id: int
    source_artifact_id: int
    source_artifact_digest: str
    source_collector_git_sha: str
    journey_build_run_id: int
    journey_build_git_sha: str

    def __post_init__(self) -> None:
        binding = next(
            (
                item
                for item in V2_SOURCE_BINDINGS
                if item.symbol == self.symbol and item.timeframe == "M5"
            ),
            None,
        )
        if binding is None:
            raise ValueError("Phase22 Turtle symbol has no V2 M5 binding")
        if self.source_run_id != binding.run_id:
            raise ValueError("Phase22 Turtle source run drift")
        if self.source_artifact_id != binding.artifact_id:
            raise ValueError("Phase22 Turtle source artifact drift")
        if self.source_artifact_digest != binding.artifact_digest:
            raise ValueError("Phase22 Turtle source artifact digest drift")
        if self.source_collector_git_sha != binding.collector_git_sha:
            raise ValueError("Phase22 Turtle source collector drift")
        if self.source_run_id != M5_SOURCE_RUN_ID:
            raise ValueError("Phase22 Turtle M5 run identity drift")
        if self.source_collector_git_sha != M5_COLLECTOR_GIT_SHA:
            raise ValueError("Phase22 Turtle M5 collector identity drift")
        if self.journey_build_run_id <= 0:
            raise ValueError("Phase22 Journey build run id must be positive")
        if (
            len(self.journey_build_git_sha) != 40
            or any(
                ch not in "0123456789abcdef"
                for ch in self.journey_build_git_sha
            )
        ):
            raise ValueError("Phase22 Journey build Git SHA invalid")


def lineage_for_symbol(
    *,
    symbol: str,
    journey_build_run_id: int,
    journey_build_git_sha: str,
) -> Phase22TurtleDependencyLineage:
    matches = tuple(
        item
        for item in V2_SOURCE_BINDINGS
        if item.symbol == symbol and item.timeframe == "M5"
    )
    if len(matches) != 1:
        raise ValueError("Phase22 Turtle source binding must be unique")
    binding = matches[0]
    return Phase22TurtleDependencyLineage(
        symbol=symbol,
        source_run_id=binding.run_id,
        source_artifact_id=binding.artifact_id,
        source_artifact_digest=binding.artifact_digest,
        source_collector_git_sha=binding.collector_git_sha,
        journey_build_run_id=journey_build_run_id,
        journey_build_git_sha=journey_build_git_sha,
    )


@contextmanager
def phase22_dependency_lineage(
    lineage: Phase22TurtleDependencyLineage,
) -> Iterator[None]:
    """Temporarily rebind provenance only; algorithms are left untouched."""

    journey_original = (
        journey.SOURCE_IDENTITY,
        journey.SOURCE_RUN_ID,
        journey.SOURCE_GIT_SHA,
    )
    target_original = (
        target.SOURCE_JOURNEY_IDENTITY,
        target.SOURCE_JOURNEY_RUN_ID,
        target.SOURCE_JOURNEY_GIT_SHA,
        target.SOURCE_M5_RUN_ID,
        target.SOURCE_M5_GIT_SHA,
    )
    try:
        journey.SOURCE_IDENTITY = V2_M5_SOURCE_IDENTITY
        journey.SOURCE_RUN_ID = lineage.source_run_id
        journey.SOURCE_GIT_SHA = lineage.source_collector_git_sha

        target.SOURCE_JOURNEY_IDENTITY = journey.IDENTITY
        target.SOURCE_JOURNEY_RUN_ID = lineage.journey_build_run_id
        target.SOURCE_JOURNEY_GIT_SHA = lineage.journey_build_git_sha
        target.SOURCE_M5_RUN_ID = lineage.source_run_id
        target.SOURCE_M5_GIT_SHA = lineage.source_collector_git_sha
        yield
    finally:
        (
            journey.SOURCE_IDENTITY,
            journey.SOURCE_RUN_ID,
            journey.SOURCE_GIT_SHA,
        ) = journey_original
        (
            target.SOURCE_JOURNEY_IDENTITY,
            target.SOURCE_JOURNEY_RUN_ID,
            target.SOURCE_JOURNEY_GIT_SHA,
            target.SOURCE_M5_RUN_ID,
            target.SOURCE_M5_GIT_SHA,
        ) = target_original


def _file_sha256(path: Path) -> str:
    return "sha256:" + sha256(path.read_bytes()).hexdigest()


def build_phase22_turtle_dependencies(
    *,
    raw_source: Path,
    journey_output: Path,
    target_output: Path,
    lineage: Phase22TurtleDependencyLineage,
) -> dict[str, object]:
    """Build causal V2 dependencies after the one-shot guard has authorized use."""

    with phase22_dependency_lineage(lineage):
        journey_manifest = journey.build_symbol_journey(
            raw_source,
            journey_output,
        )
        if journey_manifest["symbol"] != lineage.symbol:
            raise ValueError("Phase22 Journey symbol drift")
        target_manifest = target.build_target_destination_v2(
            raw_source,
            journey_output,
            target_output,
        )
        if target_manifest["symbol"] != lineage.symbol:
            raise ValueError("Phase22 Target symbol drift")

    files = (
        journey_output / "MARKET_JOURNEY_LEDGER.jsonl",
        journey_output / "STRUCTURE_TOUCH_LEDGER.jsonl",
        journey_output / "PRE_DEPARTURE_SEQUENCE_LEDGER.jsonl",
        journey_output / "DEPARTURE_TIMING_LEDGER.jsonl",
        target_output / "TARGET_DESTINATION_LEDGER_V2.jsonl",
        target_output / "TARGET_DESTINATION_EPISODE_V2.jsonl",
    )
    if any(not item.is_file() for item in files):
        raise ValueError("Phase22 Turtle dependency output incomplete")
    payload = {
        "schema": "qore.cibo.phase22.turtle-v2-dependencies.v1",
        "symbol": lineage.symbol,
        "source": {
            "run_id": lineage.source_run_id,
            "artifact_id": lineage.source_artifact_id,
            "artifact_digest": lineage.source_artifact_digest,
            "collector_git_sha": lineage.source_collector_git_sha,
            "identity": V2_M5_SOURCE_IDENTITY,
        },
        "journey_build": {
            "run_id": lineage.journey_build_run_id,
            "git_sha": lineage.journey_build_git_sha,
            "algorithm_identity": journey.IDENTITY,
        },
        "target_build": {
            "algorithm_identity": target.IDENTITY,
            "causal_candidate_selection": True,
            "post_departure_outcomes_used_for_decision": False,
        },
        "file_sha256": {
            str(item): _file_sha256(item)
            for item in files
        },
        "trader_logic_executed": False,
        "productive_authority": False,
    }
    (target_output / "phase22-v2-dependency-receipt.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload
