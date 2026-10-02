"""Immutable pre-evidence schedule for the Architect-2 T11 market-impact exam.

The schedule fixes every symbol, phase, matched pair, side, level order and
validation fold before any provider outcome is admissible.  It is planning
evidence only and cannot execute a broker request.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass

from qore.infrastructure.cibo_arch2_t11_nonlinear_input_freeze import (
    MARKET_IMPACT_CALIBRATION_EPISODES_PER_LEVEL_PER_SYMBOL,
    MARKET_IMPACT_VALIDATION_EPISODES_PER_LEVEL_PER_SYMBOL,
    REQUIRED_SYMBOLS,
    T11_NONLINEAR_INPUT_FREEZE,
)


@dataclass(frozen=True, slots=True)
class T11PlannedMarketImpactEpisode:
    ordinal: int
    qore_symbol: str
    phase: str
    pair_index: int
    fold_index: int
    side: str
    child_count: int
    level_order_position: int
    both_children_open_before_close_required: bool
    minimum_volume_child_only: bool
    realized_settlement_cost_usd_required: bool
    deposit_asset: str
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.ordinal <= 0:
            raise ValueError("T11 plan ordinal must be positive")
        if self.qore_symbol not in REQUIRED_SYMBOLS:
            raise ValueError("T11 plan symbol outside frozen universe")
        if self.phase not in {"CALIBRATION", "VALIDATION"}:
            raise ValueError("T11 plan phase invalid")
        if self.pair_index <= 0:
            raise ValueError("T11 plan pair index must be positive")
        if self.phase == "CALIBRATION" and self.fold_index != 0:
            raise ValueError("T11 calibration fold must be zero")
        if self.phase == "VALIDATION" and self.fold_index != self.pair_index:
            raise ValueError("T11 validation fold/pair identity drift")
        if self.side not in {"long", "short"}:
            raise ValueError("T11 plan side invalid")
        if self.child_count not in {1, 2}:
            raise ValueError("T11 plan child level invalid")
        if self.level_order_position not in {1, 2}:
            raise ValueError("T11 plan order position invalid")
        if (
            not self.both_children_open_before_close_required
            or not self.minimum_volume_child_only
            or not self.realized_settlement_cost_usd_required
            or self.deposit_asset != "USD"
            or self.productive_authority
        ):
            raise ValueError("T11 plan scientific/governance invariant drift")


@dataclass(frozen=True, slots=True)
class T11MarketImpactExperimentPlan:
    protocol_sha256: str
    episodes: tuple[T11PlannedMarketImpactEpisode, ...]
    episode_count: int
    child_entry_count: int
    broker_mutation_authorized: bool = False
    phase22_v2_consumption_authorized: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if not self.protocol_sha256.startswith("sha256:"):
            raise ValueError("T11 plan protocol digest invalid")
        if self.episode_count != len(self.episodes) or self.episode_count != 144:
            raise ValueError("T11 plan must contain exactly 144 episodes")
        expected_children = sum(item.child_count for item in self.episodes)
        if self.child_entry_count != expected_children or expected_children != 216:
            raise ValueError("T11 plan must contain exactly 216 child entries")
        if tuple(item.ordinal for item in self.episodes) != tuple(
            range(1, self.episode_count + 1)
        ):
            raise ValueError("T11 plan ordinals must be contiguous")
        if (
            self.broker_mutation_authorized
            or self.phase22_v2_consumption_authorized
            or self.productive_authority
        ):
            raise ValueError("T11 experiment plan cannot grant authority")

    def fingerprint(self) -> str:
        payload = {
            "protocol_sha256": self.protocol_sha256,
            "episodes": [asdict(item) for item in self.episodes],
            "episode_count": self.episode_count,
            "child_entry_count": self.child_entry_count,
            "broker_mutation_authorized": self.broker_mutation_authorized,
            "phase22_v2_consumption_authorized": (
                self.phase22_v2_consumption_authorized
            ),
            "productive_authority": self.productive_authority,
        }
        raw = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode()
        return "sha256:" + hashlib.sha256(raw).hexdigest()


def _pair_plan(pair_index: int) -> tuple[str, tuple[int, int]]:
    side = "long" if pair_index % 2 else "short"
    levels = (1, 2) if pair_index % 2 else (2, 1)
    return side, levels


def build_t11_market_impact_experiment_plan() -> T11MarketImpactExperimentPlan:
    episodes: list[T11PlannedMarketImpactEpisode] = []
    ordinal = 0
    for symbol in REQUIRED_SYMBOLS:
        for phase, pair_count in (
            (
                "CALIBRATION",
                MARKET_IMPACT_CALIBRATION_EPISODES_PER_LEVEL_PER_SYMBOL,
            ),
            (
                "VALIDATION",
                MARKET_IMPACT_VALIDATION_EPISODES_PER_LEVEL_PER_SYMBOL,
            ),
        ):
            for pair_index in range(1, pair_count + 1):
                side, levels = _pair_plan(pair_index)
                for order_position, child_count in enumerate(levels, start=1):
                    ordinal += 1
                    episodes.append(
                        T11PlannedMarketImpactEpisode(
                            ordinal=ordinal,
                            qore_symbol=symbol,
                            phase=phase,
                            pair_index=pair_index,
                            fold_index=(
                                0 if phase == "CALIBRATION" else pair_index
                            ),
                            side=side,
                            child_count=child_count,
                            level_order_position=order_position,
                            both_children_open_before_close_required=True,
                            minimum_volume_child_only=True,
                            realized_settlement_cost_usd_required=True,
                            deposit_asset="USD",
                            productive_authority=False,
                        )
                    )
    return T11MarketImpactExperimentPlan(
        protocol_sha256=T11_NONLINEAR_INPUT_FREEZE.fingerprint(),
        episodes=tuple(episodes),
        episode_count=len(episodes),
        child_entry_count=sum(item.child_count for item in episodes),
    )


T11_MARKET_IMPACT_EXPERIMENT_PLAN = build_t11_market_impact_experiment_plan()
