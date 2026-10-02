"""Immutable Architect-2 terminal falsification receipt for CE2I T16.

The preregistered hedge candidates US30 and US500 were evaluated on a strictly
post-freeze, read-only cTrader DEMO M1 population. Both candidates failed every
temporal fold after the already sealed conservative round-trip execution cost.

This receipt recommends FALSIFIED_AND_CLOSED only. It does not mutate the
canonical ledger or grant productive authority.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from decimal import Decimal

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)

RUN_ID = 36941142280
RUN_HEAD_SHA = "f8c6409af5893ca8189a7aa13a3d406c4d19b649"
ARTIFACT_ID = 11199498760
ARTIFACT_DIGEST = (
    "sha256:2aa2024db38efa100c4cf97eb8fc59038ea8b78a0428719ee106ea4bee3a0a16"
)
PAYLOAD_SHA256 = (
    "sha256:81c5f14aa94e0e7065354256a6bcaf8a69154353180024e3f3089132223b5f54"
)
TERMINAL_RECOMMENDATION = "FALSIFIED_AND_CLOSED"


@dataclass(frozen=True, slots=True)
class T16CandidateFalsification:
    hedge_symbol: str
    observation_count: int
    fold_passes: tuple[bool, ...]
    net_protection_fraction_by_fold: tuple[Decimal, ...]
    conservative_round_trip_cost_fraction: Decimal

    def __post_init__(self) -> None:
        if self.hedge_symbol not in {"US30", "US500"}:
            raise CiboCapitalManagementError("T16 terminal hedge universe drift")
        if self.observation_count != 67:
            raise CiboCapitalManagementError("T16 terminal observation count drift")
        if self.fold_passes != (False, False, False, False):
            raise CiboCapitalManagementError("T16 terminal fold result drift")
        if len(self.net_protection_fraction_by_fold) != 4:
            raise CiboCapitalManagementError("T16 terminal fold metric surface drift")
        if any(
            not isinstance(value, Decimal)
            or not value.is_finite()
            or value >= 0
            for value in self.net_protection_fraction_by_fold
        ):
            raise CiboCapitalManagementError(
                "T16 terminal falsification requires negative net protection in 4/4 folds"
            )
        if (
            not isinstance(self.conservative_round_trip_cost_fraction, Decimal)
            or not self.conservative_round_trip_cost_fraction.is_finite()
            or self.conservative_round_trip_cost_fraction <= 0
        ):
            raise CiboCapitalManagementError("T16 terminal cost fraction invalid")


@dataclass(frozen=True, slots=True)
class T16TerminalFalsificationReceipt:
    workstream_id: str
    recommendation: str
    provider_key: str
    environment: str
    target_symbol: str
    provider_target_symbol: str
    bar_count_per_symbol: int
    candidates: tuple[T16CandidateFalsification, ...]
    all_preregistered_candidates_exhausted: bool
    candidate_passes: tuple[str, ...]
    broker_mutation_performed: bool
    holdout_outcomes_used: bool
    phase22_v2_consumed: bool
    fundednext_touched: bool
    vps_touched: bool
    canonical_ledger_modified: bool
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.workstream_id != "T16":
            raise CiboCapitalManagementError("T16 terminal workstream identity drift")
        if self.recommendation != TERMINAL_RECOMMENDATION:
            raise CiboCapitalManagementError("T16 terminal recommendation drift")
        if self.provider_key != "ctrader-demo" or self.environment != "demo":
            raise CiboCapitalManagementError("T16 terminal provider drift")
        if self.target_symbol != "NAS100" or self.provider_target_symbol != "USTEC":
            raise CiboCapitalManagementError("T16 terminal target binding drift")
        if self.bar_count_per_symbol != 68:
            raise CiboCapitalManagementError("T16 terminal bar population drift")
        if tuple(item.hedge_symbol for item in self.candidates) != ("US30", "US500"):
            raise CiboCapitalManagementError("T16 terminal candidate order drift")
        if not self.all_preregistered_candidates_exhausted or self.candidate_passes:
            raise CiboCapitalManagementError("T16 terminal candidate exhaustion drift")
        prohibited = (
            self.broker_mutation_performed,
            self.holdout_outcomes_used,
            self.phase22_v2_consumed,
            self.fundednext_touched,
            self.vps_touched,
            self.canonical_ledger_modified,
            self.productive_authority,
        )
        if any(prohibited):
            raise CiboCapitalManagementError("T16 terminal governance contamination")

    def fingerprint(self) -> str:
        payload = asdict(self)
        for candidate in payload["candidates"]:
            candidate["net_protection_fraction_by_fold"] = [
                format(value, "f")
                for value in candidate["net_protection_fraction_by_fold"]
            ]
            candidate["conservative_round_trip_cost_fraction"] = format(
                candidate["conservative_round_trip_cost_fraction"], "f"
            )
        raw = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(raw).hexdigest()


T16_TERMINAL_FALSIFICATION_RECEIPT = T16TerminalFalsificationReceipt(
    workstream_id="T16",
    recommendation=TERMINAL_RECOMMENDATION,
    provider_key="ctrader-demo",
    environment="demo",
    target_symbol="NAS100",
    provider_target_symbol="USTEC",
    bar_count_per_symbol=68,
    candidates=(
        T16CandidateFalsification(
            hedge_symbol="US30",
            observation_count=67,
            fold_passes=(False, False, False, False),
            net_protection_fraction_by_fold=(
                Decimal("-0.00003032105778006402779598444381"),
                Decimal("-0.00003746498486383862003857404060"),
                Decimal("-0.00003300062173808696913289662710"),
                Decimal("-0.00001964016907750274163458524086"),
            ),
            conservative_round_trip_cost_fraction=Decimal(
                "0.00005302387754902352402683240905"
            ),
        ),
        T16CandidateFalsification(
            hedge_symbol="US500",
            observation_count=67,
            fold_passes=(False, False, False, False),
            net_protection_fraction_by_fold=(
                Decimal("-0.0001011112334513366820590880707"),
                Decimal("-0.0001115161817158943681648621752"),
                Decimal("-0.00009935314728680398653784963347"),
                Decimal("-0.00008440855871870527243319084257"),
            ),
            conservative_round_trip_cost_fraction=Decimal(
                "0.000104309022058976660199933279"
            ),
        ),
    ),
    all_preregistered_candidates_exhausted=True,
    candidate_passes=(),
    broker_mutation_performed=False,
    holdout_outcomes_used=False,
    phase22_v2_consumed=False,
    fundednext_touched=False,
    vps_touched=False,
    canonical_ledger_modified=False,
)
