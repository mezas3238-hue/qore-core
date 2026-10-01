"""Architect-2 terminal recommendation for CE2I T03.

The frozen current-provider contract has no surviving economically equivalent
lower-margin expression.  Direct duplicates were exhausted earlier.  The
exhaustive read-only two-leg FX/XAU screen found no lower-margin candidate, and
the pre-registered related US index instruments are hedge proxies with basis,
not exact normalized exposure equivalents.

This is a recommendation only; the Integrator owns canonical ledger mutation.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

RECOMMENDATION = "FALSIFIED_AND_CLOSED"
SCOPE = "CURRENT_GOVERNED_CTRADER_DEMO_T03_CONTRACT"

MULTILEG_RUN_ID = 36936279830
MULTILEG_RUN_HEAD_SHA = "9925d0f0a0e1fb88ba4da8eb15b602652e4423f8"
MULTILEG_ARTIFACT_ID = 11197727438
MULTILEG_ARTIFACT_DIGEST = (
    "sha256:bbb52ebf064d3e90459a4fadc79b020dd04a158e2fbb6ec815c420e28b19d78f"
)
MULTILEG_PAYLOAD_SHA256 = (
    "sha256:6630821cf0867f358ca5de28a7443e9870ef1b018168be2fdb3f8293106d407d"
)


@dataclass(frozen=True, slots=True)
class T03CurrentContractFalsification:
    workstream_id: str
    recommendation: str
    scope: str
    provider_key: str
    catalog_symbol_count: int
    enabled_pair_count: int
    governed_multileg_targets: tuple[str, ...]
    multileg_candidate_count: int
    continuous_lower_margin_candidate_count: int
    best_observed_margin_ratio: Decimal
    direct_single_instrument_candidate_exhausted: bool
    nas100_related_indices_are_exact_equivalents: bool
    alternate_provider_admissible_under_frozen_comparison_contract: bool
    fresh_oos_needed_without_candidate: bool
    holdout_outcomes_used: bool
    broker_mutation_performed: bool
    terminal_disposition_assigned: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.workstream_id != "T03":
            raise ValueError("T03 falsification identity drift")
        if self.recommendation != RECOMMENDATION or self.scope != SCOPE:
            raise ValueError("T03 falsification recommendation/scope drift")
        if self.provider_key != "ctrader-demo":
            raise ValueError("T03 falsification provider drift")
        if self.catalog_symbol_count != 352 or self.enabled_pair_count != 34:
            raise ValueError("T03 provider catalog coverage drift")
        if self.multileg_candidate_count != 33:
            raise ValueError("T03 multileg candidate count drift")
        if self.continuous_lower_margin_candidate_count != 0:
            raise ValueError("T03 cannot falsify a surviving lower-margin candidate")
        if self.best_observed_margin_ratio <= Decimal("1"):
            raise ValueError("T03 falsification margin bound drift")
        if not self.direct_single_instrument_candidate_exhausted:
            raise ValueError("T03 direct candidate screen must be exhausted")
        prohibited = (
            self.nas100_related_indices_are_exact_equivalents,
            self.alternate_provider_admissible_under_frozen_comparison_contract,
            self.fresh_oos_needed_without_candidate,
            self.holdout_outcomes_used,
            self.broker_mutation_performed,
            self.terminal_disposition_assigned,
            self.productive_authority,
        )
        if any(prohibited):
            raise ValueError("T03 falsification governance drift")


T03_CURRENT_CONTRACT_FALSIFICATION = T03CurrentContractFalsification(
    workstream_id="T03",
    recommendation=RECOMMENDATION,
    scope=SCOPE,
    provider_key="ctrader-demo",
    catalog_symbol_count=352,
    enabled_pair_count=34,
    governed_multileg_targets=(
        "AUDJPY",
        "EURUSD",
        "GBPJPY",
        "GBPUSD",
        "XAUUSD",
    ),
    multileg_candidate_count=33,
    continuous_lower_margin_candidate_count=0,
    best_observed_margin_ratio=Decimal(
        "1.9997205017171114"
    ),
    direct_single_instrument_candidate_exhausted=True,
    nas100_related_indices_are_exact_equivalents=False,
    alternate_provider_admissible_under_frozen_comparison_contract=False,
    fresh_oos_needed_without_candidate=False,
    holdout_outcomes_used=False,
    broker_mutation_performed=False,
)
