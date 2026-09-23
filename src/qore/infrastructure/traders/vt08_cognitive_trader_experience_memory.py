"""VT08 Forex Trader Experience Memory for Cognitive V1.

This is distinct from CIBO Market Memory. It records how the frozen B01 VT08
methodology interacted with each Forex market/anchor in the consumed R3.15
window. Outcome statistics are retained for research context only and may never
be converted directly into runtime allow/deny rules or market/anchor rankings.
"""
# ruff: noqa: E501
from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from functools import lru_cache
from typing import Final, cast

from qore.infrastructure.traders.vt08_forex import AUTHORIZED_MARKETS
from qore.infrastructure.traders.vt08_source_kernel_r3_2 import OWNER_FOREX_ANCHORS

SCHEMA: Final = "qore.vt08.forex.cognitive.trader_experience_memory.v1"
SOURCE_RUN_ID: Final = 34759027136
SOURCE_HEAD_SHA: Final = "64bc2ab4809c39e4a2b2c72aa8c0e8ec1c709222"
HOLDOUT_ID: Final = "VT08_R3_15_FINAL_INDEPENDENT_2020_2022"

R315_CERTIFIED_PORTFOLIO_SIDES: Final[dict[str, tuple[str, ...]]] = {
    "AUDJPY": ("short",),
    "GBPJPY": ("long", "short"),
    "GBPUSD": ("short",),
}

_EXPERIENCE: Final[dict[str, dict[str, dict[str, object]]]] = cast(
    dict[str, dict[str, dict[str, object]]],
    json.loads(r'''{"AUDJPY":{"1":{"exit_reason_counts":{"h4_containment_exit":4,"stop":11,"target":5},"losses":11,"mean_return":"0.000477571912","profit_factor":"1.864902","sample":20,"side_counts":{"long":11,"short":9},"wins":9},"5":{"exit_reason_counts":{"h4_containment_exit":13,"stop":7,"target":5},"losses":11,"mean_return":"0.000549367018","profit_factor":"2.213174","sample":25,"side_counts":{"long":8,"short":17},"wins":14},"9":{"exit_reason_counts":{"h4_containment_exit":9,"stop":6},"losses":8,"mean_return":"-0.000273178773","profit_factor":"0.585461","sample":15,"side_counts":{"long":9,"short":6},"wins":7}},"AUDUSD":{"1":{"exit_reason_counts":{"h4_containment_exit":3,"stop":10,"target":8},"losses":11,"mean_return":"0.000525899159","profit_factor":"1.846917","sample":21,"side_counts":{"long":10,"short":11},"wins":10},"5":{"exit_reason_counts":{"h4_containment_exit":10,"stop":12,"target":5},"losses":17,"mean_return":"0.000190896568","profit_factor":"1.349671","sample":27,"side_counts":{"long":15,"short":12},"wins":10},"9":{"exit_reason_counts":{"h4_containment_exit":12,"stop":9,"target":3},"losses":12,"mean_return":"-0.000038668588","profit_factor":"0.953617","sample":24,"side_counts":{"long":14,"short":10},"wins":12}},"EURUSD":{"1":{"exit_reason_counts":{"stop":15,"target":7},"losses":15,"mean_return":"-0.000036871842","profit_factor":"0.922251","sample":22,"side_counts":{"long":10,"short":12},"wins":7},"5":{"exit_reason_counts":{"stop":9,"target":2},"losses":9,"mean_return":"-0.000499019129","profit_factor":"0.199549","sample":11,"side_counts":{"long":5,"short":6},"wins":2},"9":{"exit_reason_counts":{"h4_containment_exit":7,"stop":9,"target":4},"losses":10,"mean_return":"0.000430738307","profit_factor":"2.175173","sample":20,"side_counts":{"long":13,"short":7},"wins":10}},"GBPJPY":{"1":{"exit_reason_counts":{"h4_containment_exit":4,"stop":9,"target":6},"losses":9,"mean_return":"0.000226821050","profit_factor":"1.527816","sample":19,"side_counts":{"long":10,"short":9},"wins":10},"5":{"exit_reason_counts":{"h4_containment_exit":5,"stop":10,"target":4},"losses":11,"mean_return":"0.000247060548","profit_factor":"1.381889","sample":19,"side_counts":{"long":12,"short":7},"wins":8},"9":{"exit_reason_counts":{"h4_containment_exit":8,"stop":9,"target":3},"losses":10,"mean_return":"0.000126040089","profit_factor":"1.201364","sample":20,"side_counts":{"long":12,"short":8},"wins":10}},"GBPUSD":{"1":{"exit_reason_counts":{"h4_containment_exit":3,"stop":15,"target":8},"losses":17,"mean_return":"-0.000193001552","profit_factor":"0.642351","sample":26,"side_counts":{"long":13,"short":13},"wins":9},"5":{"exit_reason_counts":{"h4_containment_exit":6,"stop":6,"target":5},"losses":9,"mean_return":"-0.000278155948","profit_factor":"0.628311","sample":17,"side_counts":{"long":9,"short":8},"wins":8},"9":{"exit_reason_counts":{"h4_containment_exit":8,"stop":7,"target":3},"losses":10,"mean_return":"0.000518114659","profit_factor":"1.608312","sample":18,"side_counts":{"long":5,"short":13},"wins":8}},"USDCAD":{"1":{"exit_reason_counts":{"h4_containment_exit":3,"stop":10,"target":8},"losses":11,"mean_return":"0.000212949894","profit_factor":"1.520150","sample":21,"side_counts":{"long":10,"short":11},"wins":10},"5":{"exit_reason_counts":{"h4_containment_exit":4,"stop":7,"target":2},"losses":8,"mean_return":"0.000130023102","profit_factor":"1.303785","sample":13,"side_counts":{"long":7,"short":6},"wins":5},"9":{"exit_reason_counts":{"h4_containment_exit":3,"stop":10,"target":7},"losses":11,"mean_return":"0.000078646030","profit_factor":"1.136561","sample":20,"side_counts":{"long":12,"short":8},"wins":9}},"USDJPY":{"1":{"exit_reason_counts":{"h4_containment_exit":8,"stop":14,"target":4},"losses":15,"mean_return":"-0.000069782515","profit_factor":"0.825579","sample":26,"side_counts":{"long":14,"short":12},"wins":11},"5":{"exit_reason_counts":{"h4_containment_exit":6,"stop":6,"target":7},"losses":6,"mean_return":"0.000735560356","profit_factor":"4.432048","sample":19,"side_counts":{"long":9,"short":10},"wins":13},"9":{"exit_reason_counts":{"h4_containment_exit":10,"stop":13,"target":1},"losses":15,"mean_return":"-0.000326689418","profit_factor":"0.548739","sample":24,"side_counts":{"long":11,"short":13},"wins":9}}}'''),
)


def experience_cell(market: str, anchor_hour_ny: int) -> dict[str, object]:
    if market not in AUTHORIZED_MARKETS:
        raise ValueError("VT08 experience requested outside Forex authority")
    if anchor_hour_ny not in OWNER_FOREX_ANCHORS:
        raise ValueError("VT08 experience anchor outside 01/05/09 NY")
    return deepcopy(_EXPERIENCE[market][str(anchor_hour_ny)])


@lru_cache(maxsize=1)
def _payload_cached() -> dict[str, object]:
    return {
        "schema": SCHEMA,
        "memory_class": "TRADER_EXPERIENCE_LAB",
        "trader": "VT08_FOREX",
        "markets": tuple(AUTHORIZED_MARKETS),
        "anchors_ny": tuple(OWNER_FOREX_ANCHORS),
        "source": {
            "run_id": SOURCE_RUN_ID,
            "head_sha": SOURCE_HEAD_SHA,
            "holdout_id": HOLDOUT_ID,
            "window_start": "2020-07-01T00:00:00+00:00",
            "window_end_exclusive": "2022-07-01T00:00:00+00:00",
            "status": "CONSUMED_INDEPENDENT_VALIDATION",
            "b01_methodology_only": True,
        },
        "certification_context": {
            "r315_certified_portfolio_sides": R315_CERTIFIED_PORTFOLIO_SIDES,
            "nonlisted_market_or_side_grants_authority": False,
            "experience_statistics_grant_authority": False,
        },
        "market_anchor_experience": _EXPERIENCE,
        "supported_lessons": {
            "market_anchor_separation": (
                "VT08 experience is retained per market and 01/05/09 anchor; "
                "cells are not assumed interchangeable"
            ),
            "outcomes_are_not_identity": (
                "historical outcome dispersion is experience evidence, not "
                "methodology identity"
            ),
            "h4_containment_is_material": (
                "stop/target/H4-containment terminal paths all occur and must "
                "remain explicit in replay diagnostics"
            ),
        },
        "rejected_hypotheses": {
            "profit_factor_gate": (
                "historical PF by market/anchor cannot directly authorize or "
                "block a runtime trade"
            ),
            "best_anchor_selection": (
                "selecting anchors retrospectively by PnL is prohibited"
            ),
            "best_market_selection": (
                "selecting markets retrospectively by PnL is prohibited"
            ),
            "cross_trader_threshold_copy": (
                "VT31/Capitalizer/Turtle Soup thresholds are not VT08 knowledge"
            ),
        },
        "unresolved": {
            "causal_state_explanation": (
                "outcome differences still require decision-time causal feature "
                "attribution before any context policy can be proposed"
            ),
            "contextual_position_management": (
                "market/anchor-specific HOLD/PROTECT/REDUCE/EXIT behavior is "
                "not yet frozen"
            ),
        },
        "governance": {
            "consumed_evidence_only": True,
            "runtime_self_training_allowed": False,
            "pnl_direct_rule_promotion_allowed": False,
            "strategy_identity_rewrite_allowed": False,
            "market_or_anchor_ranking_allowed": False,
            "date_level_outcome_lookup_allowed": False,
            "execution_authority": False,
            "capital_authority": False,
        },
    }


def trader_experience_payload() -> dict[str, object]:
    return deepcopy(_payload_cached())


def trader_experience_runtime_view() -> dict[str, object]:
    return _payload_cached()


@lru_cache(maxsize=1)
def trader_experience_fingerprint() -> str:
    encoded = json.dumps(
        _payload_cached(),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_trader_experience() -> None:
    assert set(_EXPERIENCE) == set(AUTHORIZED_MARKETS)
    for market in AUTHORIZED_MARKETS:
        assert set(_EXPERIENCE[market]) == {"1", "5", "9"}
        for anchor in OWNER_FOREX_ANCHORS:
            cell = _EXPERIENCE[market][str(anchor)]
            sample = int(cell["sample"])
            assert int(cell["wins"]) + int(cell["losses"]) == sample
    payload = _payload_cached()
    governance = cast(dict[str, object], payload["governance"])
    assert governance["runtime_self_training_allowed"] is False
    assert governance["pnl_direct_rule_promotion_allowed"] is False
    assert governance["strategy_identity_rewrite_allowed"] is False
    assert governance["market_or_anchor_ranking_allowed"] is False
    assert governance["date_level_outcome_lookup_allowed"] is False
    assert len(trader_experience_fingerprint()) == 64
