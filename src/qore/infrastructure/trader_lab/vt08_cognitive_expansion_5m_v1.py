"""VT08 Cognitive Expansion 5M V1 research contract.

This is a research-only license-extension program. It preserves the frozen VT08
B01 methodology while testing that methodology on four new FX markets plus one
existing control market. It grants no DEMO/LIVE/Production/real-capital authority.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Final

from qore.infrastructure.traders.vt08_b01_r3_8 import (
    OWNER_FOREX_ENTRY_ANCHORS,
    methodology_fingerprint as vt08_b01_methodology_fingerprint,
)

PROGRAM_ID: Final = "VT08_COGNITIVE_EXPANSION_5M_V1"
PROGRAM_VERSION: Final = "v1-research-001"

EXPANSION_MARKETS: Final = (
    "EURJPY",
    "USDCHF",
    "NZDUSD",
    "CADJPY",
    "USDCAD",
)
NEW_RESEARCH_MARKETS: Final = (
    "EURJPY",
    "USDCHF",
    "NZDUSD",
    "CADJPY",
)
CONTROL_MARKET: Final = "USDCAD"
ANCHORS_NY: Final = tuple(OWNER_FOREX_ENTRY_ANCHORS)

USDCAD_CONTROL_EVIDENCE: Final = {
    "source_run_id": 34759027136,
    "artifact_id": 10318398127,
    "artifact_digest": (
        "sha256:ca9c81bff7e7559c6ace39499a4edd8a019937cf1c20fcb71aec5f05c5dae69e"
    ),
    "holdout_id": "VT08_R3_15_FINAL_INDEPENDENT_2020_2022",
    "status": "CONSUMED_CONTROL_EVIDENCE",
}

NEW_MARKET_EVIDENCE_STATUS: Final = {
    "EURJPY": "NEW_M15_EVIDENCE_REQUIRED",
    "USDCHF": "NEW_M15_EVIDENCE_REQUIRED",
    "NZDUSD": "NEW_M15_EVIDENCE_REQUIRED",
    "CADJPY": "NEW_M15_EVIDENCE_REQUIRED",
}

RESEARCH_GATES: Final = {
    "minimum_trades_per_market_2y": 50,
    "minimum_profit_factor": "1.80",
    "maximum_observed_drawdown_r": "6.00",
    "minimum_mean_r": "0.00",
    "maximum_mc_p95_drawdown_r": "15.00",
    "minimum_mc_positive_terminal": "0.90",
    "required_anchor_stability": True,
    "required_temporal_validation": True,
    "required_stress": True,
    "required_monte_carlo": True,
}

REUSED_LABS: Final = (
    "VT08_B01_SOURCE_MECHANICS",
    "VT08_B01_BACKTEST_EXECUTION_MODEL",
    "VT08_B01_FAILURE_FORENSICS",
    "VT08_INDEX_CIBO_STOP_PROTECTION_PATTERN",
    "CIBO_MARKET_ATLAS_JOURNEY_LEDGER_PATTERN",
    "TRADER_LAB_WALK_FORWARD_PATTERN",
    "TRADER_LAB_ROBUSTNESS_MONTE_CARLO",
)


@dataclass(frozen=True, slots=True)
class Vt08Expansion5MFreeze:
    program_id: str = PROGRAM_ID
    program_version: str = PROGRAM_VERSION
    markets: tuple[str, ...] = EXPANSION_MARKETS
    new_research_markets: tuple[str, ...] = NEW_RESEARCH_MARKETS
    control_market: str = CONTROL_MARKET
    anchors_ny: tuple[int, ...] = ANCHORS_NY
    vt08_methodology_fingerprint: str = vt08_b01_methodology_fingerprint()
    research_only: bool = True
    methodology_mutation_authorized: bool = False
    new_market_execution_authority: bool = False
    live_authorized: bool = False
    production_authorized: bool = False
    real_capital_authorized: bool = False

    def __post_init__(self) -> None:
        if self.markets != EXPANSION_MARKETS:
            raise ValueError("VT08 5M market set drifted")
        if set(self.new_research_markets) & {self.control_market}:
            raise ValueError("control market must remain outside new-market set")
        if self.anchors_ny != (1, 5, 9):
            raise ValueError("VT08 5M anchors must remain 01/05/09 NY")
        if not self.research_only:
            raise ValueError("VT08 5M expansion must remain research-only")
        if (
            self.methodology_mutation_authorized
            or self.new_market_execution_authority
            or self.live_authorized
            or self.production_authorized
            or self.real_capital_authorized
        ):
            raise ValueError("VT08 5M expansion cannot grant operational authority")


def program_payload() -> dict[str, object]:
    freeze = Vt08Expansion5MFreeze()
    return {
        "schema": "qore.vt08.cognitive_expansion_5m.freeze.v1",
        **asdict(freeze),
        "research_gates": RESEARCH_GATES,
        "reused_labs": REUSED_LABS,
        "usdcad_control_evidence": USDCAD_CONTROL_EVIDENCE,
        "new_market_evidence_status": NEW_MARKET_EVIDENCE_STATUS,
        "selection_policy": (
            "no market or anchor may be promoted from best historical PF alone"
        ),
        "holdout_policy": (
            "development evidence is consumed; promotion requires fresh temporal evidence"
        ),
    }


def program_fingerprint() -> str:
    encoded = json.dumps(
        program_payload(),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
