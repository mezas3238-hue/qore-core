"""Canonical source-receipt contract for the Phase22 V4 successor.

This contract binds immutable read-only source artifacts after collection.
It cannot collect market data, execute Traders, inspect outcomes, mutate broker
state, authorize fresh execution, or grant productive authority.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_next_policy_advanced_scientific_eligibility import (
    NEXT_POLICY_ADVANCED_SCIENTIFIC_ELIGIBILITY,
)
from qore.infrastructure.cibo_next_policy_code_bundle_lineage import (
    NEXT_POLICY_CODE_BUNDLE_LINEAGE,
)
from qore.infrastructure.cibo_phase22_v4_governance import (
    PHASE22_V4_CANDIDATE,
    V4_CANDIDATE_ID,
)

_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
EXPECTED_V4_SOURCE_KEYS = (
    ("AUDJPY", "M5"),
    ("AUDUSD", "M5"),
    ("EURUSD", "M5"),
    ("GBPJPY", "M5"),
    ("GBPUSD", "M5"),
    ("NAS100", "M1"),
    ("NAS100", "M5"),
    ("USDCAD", "M5"),
    ("USDJPY", "M5"),
    ("XAUUSD", "M5"),
)


@dataclass(frozen=True, slots=True)
class Phase22V4SourceBinding:
    symbol: str
    timeframe: str
    artifact_id: int
    artifact_digest: str
    collector_git_sha: str
    manifest_sha256: str
    retained_bars: int
    first_observed_at: str
    last_observed_at: str

    def __post_init__(self) -> None:
        if (self.symbol, self.timeframe) not in EXPECTED_V4_SOURCE_KEYS:
            raise CiboCapitalManagementError(
                "V4 source binding outside exact source surface"
            )
        if self.timeframe == "M1" and self.symbol != "NAS100":
            raise CiboCapitalManagementError(
                "V4 source only permits NAS100 M1"
            )
        for name in ("artifact_id", "retained_bars"):
            value = getattr(self, name)
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value <= 0
            ):
                raise CiboCapitalManagementError(
                    f"V4 source {name} must be positive int"
                )
        for name in ("artifact_digest", "manifest_sha256"):
            if _SHA256_RE.fullmatch(getattr(self, name)) is None:
                raise CiboCapitalManagementError(
                    f"V4 source {name} invalid"
                )
        if _GIT_SHA_RE.fullmatch(self.collector_git_sha) is None:
            raise CiboCapitalManagementError(
                "V4 source collector Git SHA invalid"
            )
        first = datetime.fromisoformat(self.first_observed_at)
        last = datetime.fromisoformat(self.last_observed_at)
        for value, name in ((first, "first"), (last, "last")):
            if value.tzinfo is None or value.utcoffset() is None:
                raise CiboCapitalManagementError(
                    f"V4 source {name} timestamp must be timezone-aware"
                )
        candidate = PHASE22_V4_CANDIDATE
        if not candidate.start_at <= first < candidate.end_exclusive_at:
            raise CiboCapitalManagementError(
                "V4 source first observation outside candidate"
            )
        if not candidate.start_at <= last < candidate.end_exclusive_at:
            raise CiboCapitalManagementError(
                "V4 source last observation outside candidate"
            )
        if last < first:
            raise CiboCapitalManagementError(
                "V4 source observation chronology invalid"
            )


@dataclass(frozen=True, slots=True)
class Phase22V4SourceReceipt:
    candidate_id: str
    source_availability_run_id: int
    source_availability_artifact_id: int
    source_availability_artifact_digest: str
    corpus_run_id: int
    corpus_seal_artifact_id: int
    corpus_seal_artifact_digest: str
    bindings: tuple[Phase22V4SourceBinding, ...]
    policy_bundle_sha256: str
    advanced_scientific_eligibility_sha256: str
    source_validation_complete: bool
    source_outcomes_inspected: bool = False
    v3_lane_artifact_contents_used: bool = False
    trader_logic_executed: bool = False
    broker_mutation: bool = False
    fresh_trader_execution_authorized: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.candidate_id != V4_CANDIDATE_ID:
            raise CiboCapitalManagementError(
                "V4 source receipt candidate identity drift"
            )
        for name in (
            "source_availability_run_id",
            "source_availability_artifact_id",
            "corpus_run_id",
            "corpus_seal_artifact_id",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value <= 0
            ):
                raise CiboCapitalManagementError(
                    f"V4 source receipt {name} invalid"
                )
        for name in (
            "source_availability_artifact_digest",
            "corpus_seal_artifact_digest",
            "policy_bundle_sha256",
            "advanced_scientific_eligibility_sha256",
        ):
            if _SHA256_RE.fullmatch(getattr(self, name)) is None:
                raise CiboCapitalManagementError(
                    f"V4 source receipt {name} invalid"
                )
        if self.policy_bundle_sha256 != (
            NEXT_POLICY_CODE_BUNDLE_LINEAGE.fingerprint()
        ):
            raise CiboCapitalManagementError(
                "V4 source receipt policy bundle drift"
            )
        if self.advanced_scientific_eligibility_sha256 != (
            NEXT_POLICY_ADVANCED_SCIENTIFIC_ELIGIBILITY.fingerprint()
        ):
            raise CiboCapitalManagementError(
                "V4 source receipt advanced eligibility drift"
            )
        keys = tuple(
            sorted((item.symbol, item.timeframe) for item in self.bindings)
        )
        if keys != EXPECTED_V4_SOURCE_KEYS:
            raise CiboCapitalManagementError(
                "V4 source receipt requires exact 10-source surface"
            )
        if len(self.bindings) != len(keys):
            raise CiboCapitalManagementError(
                "V4 source receipt duplicate source binding"
            )
        if not self.source_validation_complete:
            raise CiboCapitalManagementError(
                "V4 source receipt cannot represent incomplete validation"
            )
        if any(
            (
                self.source_outcomes_inspected,
                self.v3_lane_artifact_contents_used,
                self.trader_logic_executed,
                self.broker_mutation,
                self.fresh_trader_execution_authorized,
                self.productive_authority,
            )
        ):
            raise CiboCapitalManagementError(
                "V4 source receipt governance contamination"
            )

    def payload(self) -> dict[str, object]:
        candidate = PHASE22_V4_CANDIDATE
        return {
            "schema": "qore.cibo.phase22.v4-source-receipt.v1",
            "candidate_id": self.candidate_id,
            "window": {
                "start": candidate.start_at.isoformat(),
                "end_exclusive": candidate.end_exclusive_at.isoformat(),
            },
            "source_availability_run_id": self.source_availability_run_id,
            "source_availability_artifact_id": (
                self.source_availability_artifact_id
            ),
            "source_availability_artifact_digest": (
                self.source_availability_artifact_digest
            ),
            "corpus_run_id": self.corpus_run_id,
            "corpus_seal_artifact_id": self.corpus_seal_artifact_id,
            "corpus_seal_artifact_digest": self.corpus_seal_artifact_digest,
            "bindings": [asdict(item) for item in self.bindings],
            "policy_bundle_sha256": self.policy_bundle_sha256,
            "advanced_scientific_eligibility_sha256": (
                self.advanced_scientific_eligibility_sha256
            ),
            "source_validation_complete": True,
            "source_outcomes_inspected": False,
            "v3_lane_artifact_contents_used": False,
            "trader_logic_executed": False,
            "broker_mutation": False,
            "fresh_trader_execution_authorized": False,
            "productive_authority": False,
        }

    def fingerprint(self) -> str:
        raw = json.dumps(
            self.payload(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(raw).hexdigest()
