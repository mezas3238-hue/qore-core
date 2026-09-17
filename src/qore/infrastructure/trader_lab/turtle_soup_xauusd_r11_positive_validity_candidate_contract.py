"""Frozen research contract for the first positive structural-validity candidate.

This contract freezes exactly what R11 learned from consumed evidence. It does
not authorize entry, execution, demo, live, or capital. It exists so the next
independent validation can test one immutable hypothesis without changing its
family definition or its multichannel anchors after seeing new outcomes.

The hypothesis is deliberately about *journey capacity*:
within exact BREAK A anatomy, stronger C1 directional rejection together with
limited post-reclaim re-violation identifies a structural situation with a
higher observed propensity to reach at least one active Draw-On-Liquidity.

It is not a probability of profit and not a guarantee that the selected DOL,
target, or trade will succeed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.turtle_soup_xauusd_r11_situation_recognition_engine import (
    A_REVIOLATION_MAX,
    A_WICK_MIN,
    BREAK_A_SIGNATURE,
)

IDENTITY = "TURTLE_SOUP_XAUUSD_R11_BREAK_A_MULTICHANNEL_VALIDITY_CANDIDATE_001"
STATUS = "FROZEN_RESEARCH_CANDIDATE_AWAITING_INDEPENDENT_VALIDATION"

SOURCE_RUN_ID = 35282212625
SOURCE_ARTIFACT_ID = 10522679602
SOURCE_DIGEST = (
    "sha256:d78081b2aab8a2d3d85e34e49a5f2134dfc90221cd5a5abf0df2fa7fd8f3e134"
)
SOURCE_HEAD = "4f6292ecb4081c353a66b1769a9f5bf7d4d1fbbb"

PRE_ENTRY_RECOGNIZED = 31
BINARY_AUDITABLE = 30
DOL_CAPABLE = 21
INVALIDATED_BEFORE_ANY_ACTIVE_DOL = 9
OTHER_DIAGNOSTIC = 1


def candidate_manifest() -> dict[str, Any]:
    return {
        "schema": "qore.turtle_soup_xauusd_r11.positive_validity_candidate.v1",
        "identity": IDENTITY,
        "status": STATUS,
        "hypothesis": {
            "scope": "EXACT_BREAK_A_ONLY",
            "family_signature": dict(BREAK_A_SIGNATURE),
            "required_multichannel_conditions": {
                "c1_directional_wick_fraction": {
                    "operator": ">=",
                    "threshold": str(A_WICK_MIN),
                    "channel": "LIQUIDITY_SIGNIFICANCE",
                },
                "post_reclaim_max_reviolation_source_fraction": {
                    "operator": "<=",
                    "threshold": str(A_REVIOLATION_MAX),
                    "channel": "CISD_RECLAIM_DEFENSE",
                },
            },
            "predicted_structural_property": (
                "ELEVATED_PLAUSIBILITY_OF_TOUCHING_AT_LEAST_ONE_ACTIVE_DOL"
            ),
            "predicts_profit": False,
            "predicts_selected_target_hit": False,
            "guarantees_direction": False,
        },
        "consumed_evidence": {
            "source_run_id": SOURCE_RUN_ID,
            "source_artifact_id": SOURCE_ARTIFACT_ID,
            "source_digest": SOURCE_DIGEST,
            "source_head": SOURCE_HEAD,
            "pre_entry_recognized": PRE_ENTRY_RECOGNIZED,
            "binary_auditable": BINARY_AUDITABLE,
            "dol_capable": DOL_CAPABLE,
            "invalidated_before_any_active_dol": INVALIDATED_BEFORE_ANY_ACTIVE_DOL,
            "other_diagnostic": OTHER_DIAGNOSTIC,
            "binary_dol_capable_rate": "0.7",
            "temporal_transfer": {
                "early_2016_2020": {
                    "pre_entry_candidates": 16,
                    "binary_auditable": 16,
                    "dol_capable": 10,
                    "rate": "0.625",
                },
                "transition_2021_2023": {
                    "pre_entry_candidates": 9,
                    "binary_auditable": 8,
                    "dol_capable": 6,
                    "rate": "0.75",
                },
                "recent_2024_2026": {
                    "pre_entry_candidates": 6,
                    "binary_auditable": 6,
                    "dol_capable": 5,
                    "rate": "0.8333333333333333333333333333",
                },
            },
        },
        "validation_contract": {
            "family_signature_mutable_after_freeze": False,
            "anchor_thresholds_mutable_after_freeze": False,
            "calendar_year_allowed_as_rule": False,
            "post_entry_information_allowed_as_recognition_input": False,
            "pnl_allowed_as_recognition_input": False,
            "automatic_threshold_search": False,
            "automatic_candidate_expansion": False,
            "independent_validation_required_before_positive_operating_contract": True,
            "fresh_holdout_opened_by_this_contract": False,
        },
        "limitations": (
            "Only 31 pre-entry candidate situations exist in consumed evidence.",
            "Only 30 have the binary capacity label used in the transfer audit.",
            "All supporting temporal partitions are consumed research evidence.",
            "The candidate establishes a testable journey-capacity hypothesis, not profitability.",
        ),
        "governance": {
            "candidate_promoted_to_operating_rule": False,
            "fresh_holdout_consumed": False,
            "demo_eligible": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }


def write_manifest(path: Path) -> dict[str, Any]:
    payload = candidate_manifest()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return payload
