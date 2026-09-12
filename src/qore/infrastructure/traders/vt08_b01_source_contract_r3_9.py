"""VT-08 B01 final source-to-code contract after second-pass adjudication.

This module freezes source authority separately from QORE research containments.
It does not change the economic behavior of the existing R3.8 narrow C2 subset,
does not reuse the consumed baseline as independent validation, and grants no
DEMO/LIVE/real-capital authority.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256

from qore.infrastructure.traders.vt08_b01_r3_8 import (
    DAILY_SELECTION_POLICY,
    OPERATIONAL_CONTAINMENTS,
    OWNER_FOREX_ENTRY_ANCHORS,
    TARGET_POLICY,
)
from qore.kernel.errors import InfrastructureError

TRADER_CODE = "vt-08"
CONTRACT_VERSION = "r3.9-source-contract-v1"
PARENT_IMPLEMENTATION = "r3.8-b01-author-clarified-v1"
PRIMARY_SOURCE = "youtube:FAKWJ-1NlLE"
PRIMARY_SOURCE_SHA256 = (
    "bfe76fa4346ec4d7442886c21834aa26f0d82172bdb55666e8c77226cdf83271"
)
SOURCE_ENTRY_ANCHORS_NY = (1, 5, 9)
REPLAY_H4_GRID_HOURS_NY = (1, 5, 9, 13, 17, 21)
CONSUMED_BASELINE_RUN_ID = 34693803930
CONSUMED_FAILURE_FORENSICS_RUN_ID = 34696371933
FORBIDDEN_REUSE = "run-34693803930"


class Vt08B01SourceContractError(InfrastructureError):
    __slots__ = ()


class Authority(StrEnum):
    SOURCE_EXPLICIT = "source-explicit"
    SOURCE_SUPPORTED_FORMALIZATION = "source-supported-formalization"
    CONTEXT_DEPENDENT_SOURCE_FAMILY = "context-dependent-source-family"
    OPTIONAL_CONTEXTUAL_REFINEMENT = "optional-contextual-refinement"
    QORE_OPERATIONAL_CONTAINMENT = "qore-operational-containment"
    FUNDAMENTALLY_UNRESOLVED = "fundamentally-unresolved"


@dataclass(frozen=True, slots=True)
class SourceRule:
    rule_id: str
    authority: Authority
    source_behavior: str
    qore_behavior: str
    note: str

    def payload(self) -> dict[str, str]:
        return {
            "rule_id": self.rule_id,
            "authority": self.authority.value,
            "source_behavior": self.source_behavior,
            "qore_behavior": self.qore_behavior,
            "note": self.note,
        }


RULES = (
    SourceRule(
        "daily-bias",
        Authority.SOURCE_EXPLICIT,
        "four-case PDH/PDL continuation-or-reversal bias",
        "keep-r3.8-four-case-bias",
        "Bias logic remains source-authorized; day-boundary construction is separate.",
    ),
    SourceRule(
        "source-day",
        Authority.FUNDAMENTALLY_UNRESOLVED,
        "daily-candle-boundary-not-source-specified",
        "17NY-to-17NY-research-containment",
        "17:00 New York to 17:00 New York is QORE replay policy, not TTrades authority.",
    ),
    SourceRule(
        "c2-c3-fractal",
        Authority.SOURCE_EXPLICIT,
        "completed-C2-reversal-or-C3-continuation-fractal",
        "current-r3.8-executable-profile-remains-narrow-completed-C2-subset",
        "C3 is source-authorized but is not silently added to the frozen R3.8 subset.",
    ),
    SourceRule(
        "shallow-large",
        Authority.SOURCE_SUPPORTED_FORMALIZATION,
        "qualitative-time-and-range-consumption-distinction-only",
        "no-numeric-wick-classifier-in-current-B01-path",
        "No ATR, ratio, pips, ticks, or candle-count threshold is source-authorized.",
    ),
    SourceRule(
        "cisd-level",
        Authority.SOURCE_EXPLICIT,
        "open-of-first-opposing-candle-in-series",
        "keep-r3.8-first-series-open",
        "The level is source-explicit for a multi-candle sequence.",
    ),
    SourceRule(
        "cisd-confirmation",
        Authority.SOURCE_EXPLICIT,
        "close-through-CISD-level-wick-is-insufficient",
        "keep-r3.8-close-confirmation",
        "No additional displacement threshold is introduced.",
    ),
    SourceRule(
        "cisd-series-minimum",
        Authority.SOURCE_SUPPORTED_FORMALIZATION,
        "one-or-more-opposing-candles",
        "keep-r3.8-single-candle-capable-series",
        "Single-candle eligibility is implied by the source wording, not separately explicit.",
    ),
    SourceRule(
        "protected-swing",
        Authority.SOURCE_EXPLICIT,
        "important-level-interaction-plus-CISD-confirms-structural-extreme",
        "keep-r3.8-series-extreme-protected-swing",
        "The PS is the structural invalidation reference.",
    ),
    SourceRule(
        "protected-swing-selection",
        Authority.FUNDAMENTALLY_UNRESOLVED,
        "no-universal-rule-for-multiple-valid-protected-swings",
        "exactly-one-valid-PS-else-abstain",
        "Nearest, deepest, first, latest, or best-in-hindsight selection is prohibited.",
    ),
    SourceRule(
        "positional-entry-reference",
        Authority.SOURCE_EXPLICIT,
        "new-HTF-open-reference-after-completed-fractal-and-protected-swing",
        "keep-new-H4-open-reference",
        "Reference price is source authority; broker execution mechanics are not.",
    ),
    SourceRule(
        "positional-fill",
        Authority.QORE_OPERATIONAL_CONTAINMENT,
        "broker-fill-mechanics-not-source-specified",
        "historical-fill-at-new-H4-open",
        "Exact OHLC-open fill with zero execution friction is a replay containment.",
    ),
    SourceRule(
        "structural-stop",
        Authority.SOURCE_EXPLICIT,
        "protected-swing-extreme-is-structural-invalidation-reference",
        "keep-protected-swing-extreme",
        "The structural level is source-resolved.",
    ),
    SourceRule(
        "stop-offset",
        Authority.FUNDAMENTALLY_UNRESOLVED,
        "beneath-or-beyond-offset-not-quantified",
        "no-offset-research-containment",
        "No ticks, pips, spread multiplier, or volatility offset may be invented.",
    ),
    SourceRule(
        "target-family",
        Authority.CONTEXT_DEPENDENT_SOURCE_FAMILY,
        "structural-liquidity-objectives-with-2R-as-viability-or-generic-initial-reference",
        "fixed-2r-research-replay-containment",
        "No deterministic next-liquidity selector is source-resolved, so R3.9 does not synthesize one.",
    ),
    SourceRule(
        "h4-filled-lifecycle",
        Authority.FUNDAMENTALLY_UNRESOLVED,
        "no-source-forced-H4-exit-and-no-explicit-survival-rule",
        "close-at-next-H4-boundary-research-containment",
        "Pending and filled-position lifecycle must not be conflated.",
    ),
    SourceRule(
        "both-sides-swept",
        Authority.FUNDAMENTALLY_UNRESOLVED,
        "neutral-without-clear-directional-acceptance-but-no-deterministic-machine-rule",
        "abstain-when-direction-is-not-uniquely-resolved",
        "Both-side sweep is not promoted to a universal source invalidation.",
    ),
    SourceRule(
        "reentry-cardinality",
        Authority.FUNDAMENTALLY_UNRESOLVED,
        "no-source-daily-trade-count-or-reentry-rule",
        "exactly-one-B01-candidate-per-market-NY-date-else-abstain",
        "Daily cardinality is QORE governance, not TTrades authority.",
    ),
    SourceRule(
        "order-type",
        Authority.FUNDAMENTALLY_UNRESOLVED,
        "market-limit-stop-not-source-specified-for-positional-entry",
        "unspecified-in-source-contract",
        "Replay fill policy must not be relabeled as broker order-type authority.",
    ),
    SourceRule(
        "body-stop",
        Authority.OPTIONAL_CONTEXTUAL_REFINEMENT,
        "post-entry-contextual-body-refinement-is-optional",
        "excluded-from-core-B01-subset",
        "Body stop is not a core B01 requirement and is not introduced here.",
    ),
    SourceRule(
        "forex-entry-anchors",
        Authority.SOURCE_EXPLICIT,
        "01/05/09 America/New_York",
        "01/05/09 America/New_York",
        "13:00 is not a source-authorized Forex entry anchor.",
    ),
    SourceRule(
        "h4-reconstruction-grid",
        Authority.QORE_OPERATIONAL_CONTAINMENT,
        "full-six-candle-Forex-H4-grid-not-claimed-as-entry-authority",
        "01/05/09/13/17/21 reconstruction-grid-hours",
        "Grid hours reconstruct contiguous H4 bars and must not be exposed as source entry anchors.",
    ),
    SourceRule(
        "futures-14",
        Authority.FUNDAMENTALLY_UNRESOLVED,
        "14:00-futures-construction-not-source-resolved",
        "excluded-from-narrow-Forex-B01-replay",
        "No synthetic 14:00 Futures construction is authorized.",
    ),
    SourceRule(
        "c3-path",
        Authority.SOURCE_EXPLICIT,
        "positional-entry-may-follow-valid-completed-C2-or-C3-fractal",
        "outside-current-r3.8-narrow-c2-subset",
        "C3 requires a separately reviewed implementation rather than silent broadening of R3.8.",
    ),
)


def _r38_alignment_errors() -> tuple[str, ...]:
    errors: list[str] = []
    if tuple(OWNER_FOREX_ENTRY_ANCHORS) != SOURCE_ENTRY_ANCHORS_NY:
        errors.append("R3.8 entry anchors drifted from source-authorized 01/05/09")
    required_containments = {
        "historical-fill-at-new-h4-open-broker-order-type-unspecified",
        "protected-swing-structural-level-no-stop-offset",
        "conservative-initial-2r-replay-target",
        "close-modeled-position-at-next-h4-boundary",
    }
    if not required_containments.issubset(set(OPERATIONAL_CONTAINMENTS)):
        errors.append("R3.8 lost one or more explicit replay containments")
    if TARGET_POLICY != "conservative-initial-2r":
        errors.append("R3.8 replay target containment drifted")
    if DAILY_SELECTION_POLICY != (
        "exactly-one-b01-candidate-per-market-ny-date-else-abstain"
    ):
        errors.append("R3.8 daily cardinality containment drifted")
    return tuple(errors)


def source_contract_fingerprint() -> str:
    material = {
        "trader_code": TRADER_CODE,
        "contract_version": CONTRACT_VERSION,
        "parent_implementation": PARENT_IMPLEMENTATION,
        "primary_source": PRIMARY_SOURCE,
        "primary_source_sha256": PRIMARY_SOURCE_SHA256,
        "source_entry_anchors_ny": SOURCE_ENTRY_ANCHORS_NY,
        "replay_h4_grid_hours_ny": REPLAY_H4_GRID_HOURS_NY,
        "rules": [item.payload() for item in RULES],
        "consumed_baseline_run_id": CONSUMED_BASELINE_RUN_ID,
        "forbidden_reuse": FORBIDDEN_REUSE,
    }
    return sha256(
        json.dumps(
            material,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def source_contract_payload() -> dict[str, object]:
    errors = _r38_alignment_errors()
    return {
        "schema": "qore.traders.vt08_b01_source_contract.r3.9.v1",
        "trader_code": TRADER_CODE,
        "contract_version": CONTRACT_VERSION,
        "parent_implementation": PARENT_IMPLEMENTATION,
        "primary_source": PRIMARY_SOURCE,
        "primary_source_sha256": PRIMARY_SOURCE_SHA256,
        "source_entry_anchors_ny": list(SOURCE_ENTRY_ANCHORS_NY),
        "replay_h4_grid_hours_ny": list(REPLAY_H4_GRID_HOURS_NY),
        "source_contract_fingerprint": source_contract_fingerprint(),
        "rules": [item.payload() for item in RULES],
        "r38_alignment": {
            "aligned": not errors,
            "errors": list(errors),
            "economic_behavior_changed_by_contract_freeze": False,
        },
        "fresh_holdout_governance": {
            "required": True,
            "consumed_baseline_run_id": CONSUMED_BASELINE_RUN_ID,
            "consumed_failure_forensics_run_id": CONSUMED_FAILURE_FORENSICS_RUN_ID,
            "forbidden_reuse": FORBIDDEN_REUSE,
            "must_not_treat_overlapping_reacquisition_as_independent": True,
            "independent_validation_authorized": False,
            "status": "UNSEEN_INTERVAL_NOT_YET_RESERVED",
        },
        "execution_authority": {
            "research_only": True,
            "demo_eligible": False,
            "live": False,
            "real_capital": False,
        },
        "final_executability_verdict": "SOURCE_EXECUTABLE_WITH_EXPLICIT_CONTAINMENTS",
    }


def main() -> None:
    payload = source_contract_payload()
    alignment = payload["r38_alignment"]
    if not isinstance(alignment, dict) or alignment.get("aligned") is not True:
        raise Vt08B01SourceContractError("R3.8 replay no longer matches the frozen source contract")
    print(
        json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    )


if __name__ == "__main__":
    main()
