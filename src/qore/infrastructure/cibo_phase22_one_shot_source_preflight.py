"""Pre-outcome source/code validation for the single Phase22 V2 execution.

This surface is intentionally non-executing: it validates immutable source
archives and frozen replay-code identities only. It must not run fresh Trader
logic or inspect fresh outcomes.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_phase22_holdout_v2_source_receipt import (
    V2_SOURCE_BINDINGS,
)
from qore.infrastructure.cibo_phase22_trader_parity_manifest import (
    ACTIVE_PHASE22_TRADER_PARITY_MANIFEST,
)
from qore.infrastructure.cibo_phase22_vt31_v4_fresh_source import (
    load_phase22_vt31_m1,
)
from qore.infrastructure.trader_lab.cibo_market_atlas_journey_extractor_v1 import (
    load_raw_m5,
)
from qore.infrastructure.traders.vt08_b01_r3_8 import methodology_fingerprint


@dataclass(frozen=True, slots=True)
class FrozenFreshReplaySource:
    trader_id: str
    methodology_git_sha: str
    module_relative_path: str


FROZEN_TURTLE_REPLAY_SOURCES = (
    FrozenFreshReplaySource(
        "R34_XAUUSD",
        "56ef138ee5ea1cde6d0bcf4c9e25e8b661c04e84",
        "src/qore/infrastructure/trader_lab/"
        "cibo_phase18_xauusd_r34_geometry_replay.py",
    ),
    FrozenFreshReplaySource(
        "R38_EURUSD",
        "324fb91d44a6fa328e66de2e22ace7386630c7aa",
        "src/qore/infrastructure/trader_lab/"
        "cibo_phase18_eurusd_r38_geometry_replay.py",
    ),
    FrozenFreshReplaySource(
        "R43_GBPUSD",
        "e02d9384fbe6521040fc2779a085c43b8d5f0f92",
        "src/qore/infrastructure/trader_lab/"
        "cibo_phase18_gbpusd_r39_geometry_replay.py",
    ),
    FrozenFreshReplaySource(
        "R38_GBPJPY",
        "eb62226e05f63cf94c1940634de676c55285e6dd",
        "src/qore/infrastructure/trader_lab/"
        "cibo_phase18_gbpjpy_r37_geometry_replay.py",
    ),
    FrozenFreshReplaySource(
        "R42_AUDJPY",
        "a332b077598e070a42b2497b3766d55e731f7dca",
        "src/qore/infrastructure/trader_lab/"
        "cibo_phase18_audjpy_r40_geometry_replay.py",
    ),
)
FROZEN_VT31_SOURCE_SHA = "cac38ed14f20e066536910145027426fd23f5939"


def _parity_by_id() -> dict[str, object]:
    parity = ACTIVE_PHASE22_TRADER_PARITY_MANIFEST
    if parity is None:
        raise CiboCapitalManagementError(
            "Phase22 source preflight parity manifest missing"
        )
    return {item.trader_id: item for item in parity.receipts}


def validate_frozen_replay_source_manifest() -> None:
    parity = _parity_by_id()
    for item in FROZEN_TURTLE_REPLAY_SOURCES:
        receipt = parity[item.trader_id]
        if getattr(receipt, "methodology_git_sha") != item.methodology_git_sha:
            raise CiboCapitalManagementError(
                f"Phase22 frozen source SHA drift: {item.trader_id}"
            )
        if not item.module_relative_path.endswith(".py"):
            raise CiboCapitalManagementError(
                f"Phase22 frozen module path invalid: {item.trader_id}"
            )
    if (
        getattr(parity["VT31_NAS100"], "methodology_git_sha")
        != FROZEN_VT31_SOURCE_SHA
    ):
        raise CiboCapitalManagementError("Phase22 VT31 frozen source SHA drift")
    vt08_expected = getattr(parity["VT08_FOREX"], "parameter_sha256")
    if vt08_expected != "sha256:" + methodology_fingerprint():
        raise CiboCapitalManagementError(
            "Phase22 VT08 frozen methodology fingerprint drift"
        )


def expected_source_archive_rows() -> tuple[
    tuple[str, str, int, str, int, str, str], ...
]:
    return tuple(
        (
            item.symbol,
            item.timeframe,
            item.artifact_id,
            item.artifact_digest,
            item.retained_bars,
            item.first_observed_at,
            item.last_observed_at,
        )
        for item in V2_SOURCE_BINDINGS
    )


def _binding(symbol: str, timeframe: str):
    matches = tuple(
        item
        for item in V2_SOURCE_BINDINGS
        if item.symbol == symbol and item.timeframe == timeframe
    )
    if len(matches) != 1:
        raise CiboCapitalManagementError(
            f"Phase22 source preflight binding drift: {symbol}/{timeframe}"
        )
    return matches[0]


def validate_m5_source_root(*, root: Path, symbol: str) -> dict[str, object]:
    binding = _binding(symbol, "M5")
    evidence, provenance = load_raw_m5(root)
    if evidence.symbol != symbol:
        raise CiboCapitalManagementError(
            f"Phase22 source preflight symbol drift: {symbol}"
        )
    if int(provenance["retained_bars"]) != binding.retained_bars:
        raise CiboCapitalManagementError(
            f"Phase22 source preflight retained-bar drift: {symbol}"
        )
    if str(provenance["earliest_observed_m5"]) != binding.first_observed_at:
        raise CiboCapitalManagementError(
            f"Phase22 source preflight first-bar drift: {symbol}"
        )
    if str(provenance["latest_observed_m5"]) != binding.last_observed_at:
        raise CiboCapitalManagementError(
            f"Phase22 source preflight last-bar drift: {symbol}"
        )
    return {
        "symbol": symbol,
        "timeframe": "M5",
        "artifact_id": binding.artifact_id,
        "artifact_digest": binding.artifact_digest,
        "retained_bars": binding.retained_bars,
        "first_observed_at": binding.first_observed_at,
        "last_observed_at": binding.last_observed_at,
        "trader_logic_executed": False,
        "outcomes_inspected": False,
        "productive_authority": False,
    }


def validate_vt31_m1_source_root(*, root: Path) -> dict[str, object]:
    binding = _binding("NAS100", "M1")
    source = load_phase22_vt31_m1(root)
    if len(source.series) != binding.retained_bars:
        raise CiboCapitalManagementError(
            "Phase22 VT31 source retained-bar drift"
        )
    if source.first_observed_at.isoformat() != binding.first_observed_at:
        raise CiboCapitalManagementError("Phase22 VT31 source first-bar drift")
    expected_last_closed = "2016-04-19T00:00:00+00:00"
    if source.last_closed_at.isoformat() != expected_last_closed:
        raise CiboCapitalManagementError("Phase22 VT31 source close drift")
    return {
        "symbol": "NAS100",
        "timeframe": "M1",
        "artifact_id": binding.artifact_id,
        "artifact_digest": binding.artifact_digest,
        "retained_bars": binding.retained_bars,
        "first_observed_at": binding.first_observed_at,
        "last_observed_at": binding.last_observed_at,
        "trader_logic_executed": False,
        "outcomes_inspected": False,
        "productive_authority": False,
    }


validate_frozen_replay_source_manifest()
