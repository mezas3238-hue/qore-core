"""Causal ephemeral Situation Model for VT08 Forex Cognitive V1.

Unknown values remain explicit. This object may contain only information
observable no later than as_of and never terminal PnL or post-outcome labels.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from typing import Final

from qore.infrastructure.traders.vt08_forex import AUTHORIZED_MARKETS
from qore.infrastructure.traders.vt08_source_kernel_r3_2 import OWNER_FOREX_ANCHORS

SCHEMA: Final = "qore.vt08.forex.cognitive.situation_model.v1"


@dataclass(frozen=True, slots=True)
class Vt08ForexSituationModel:
    as_of: datetime
    market: str
    anchor_hour_ny: int
    side: str
    ltf_profile: str
    methodology_valid: bool
    source_identity_complete: bool
    h4_lifecycle_valid: bool
    bias_state: str
    scenario_state: str
    poi_state: str
    protected_swing_state: str
    cisd_state: str
    displacement_state: str
    entry_state: str
    entry_freshness_state: str
    liquidity_state: str
    range_state: str
    volatility_state: str
    journey_stage: str
    structural_destination_state: str
    exhaustion_state: str
    risk_geometry_state: str
    position_state: str
    supporting_evidence: tuple[str, ...] = ()
    material_contradictions: tuple[str, ...] = ()
    material_uncertainties: tuple[str, ...] = ()
    nonmaterial_observations: tuple[str, ...] = ()
    current_path_efficiency: Decimal | None = None
    current_overlap_rate: Decimal | None = None
    displacement_strength: Decimal | None = None
    destination_distance_r: Decimal | None = None
    terminal_pnl: None = None
    post_outcome_label: None = None

    def __post_init__(self) -> None:
        if self.as_of.tzinfo is None or self.as_of.utcoffset() is None:
            raise ValueError("VT08 situation as_of must be timezone-aware")
        if self.market not in AUTHORIZED_MARKETS:
            raise ValueError("VT08 situation market outside Forex authority")
        if self.anchor_hour_ny not in OWNER_FOREX_ANCHORS:
            raise ValueError("VT08 situation anchor outside Owner 01/05/09 scope")
        if self.side not in {"long", "short"}:
            raise ValueError("VT08 situation side must be long or short")
        for name in (
            "ltf_profile",
            "bias_state",
            "scenario_state",
            "poi_state",
            "protected_swing_state",
            "cisd_state",
            "displacement_state",
            "entry_state",
            "entry_freshness_state",
            "liquidity_state",
            "range_state",
            "volatility_state",
            "journey_stage",
            "structural_destination_state",
            "exhaustion_state",
            "risk_geometry_state",
            "position_state",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"VT08 situation {name} must be non-empty")
        for collection_name in (
            "supporting_evidence",
            "material_contradictions",
            "material_uncertainties",
            "nonmaterial_observations",
        ):
            values = getattr(self, collection_name)
            if type(values) is not tuple:
                raise ValueError(f"{collection_name} must be an immutable tuple")
            if any(not isinstance(item, str) or not item.strip() for item in values):
                raise ValueError(f"{collection_name} must contain non-empty strings")
            if len(set(values)) != len(values):
                raise ValueError(f"{collection_name} must not contain duplicates")
        for value in (
            self.current_path_efficiency,
            self.current_overlap_rate,
            self.displacement_strength,
            self.destination_distance_r,
        ):
            if value is not None and not value.is_finite():
                raise ValueError("VT08 situation Decimal values must be finite")
        if self.terminal_pnl is not None or self.post_outcome_label is not None:
            raise ValueError("VT08 situation cannot contain post-outcome information")

    def payload(self) -> dict[str, object]:
        raw = asdict(self)
        return {
            "schema": SCHEMA,
            "memory_class": "EPHEMERAL_CAUSAL_SITUATION",
            "persistent_memory": False,
            "causal_as_of_only": True,
            "terminal_pnl_present": False,
            "post_outcome_label_present": False,
            **{
                key: (
                    value.isoformat()
                    if isinstance(value, datetime)
                    else format(value, "f")
                    if isinstance(value, Decimal)
                    else value
                )
                for key, value in raw.items()
            },
        }

    def fingerprint(self) -> str:
        encoded = json.dumps(
            self.payload(),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()
