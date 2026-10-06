"""Immutable source-receipt contract for the Phase22 V5 successor.

The policy and scientific-eligibility fingerprints are frozen to the exact
pre-fresh frozen values. V5 source evidence may prove market-data availability/integrity
only; it cannot authorize Trader execution or broker mutation.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_phase22_v5_governance import V5_CANDIDATE_ID

_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
EXPECTED_SOURCE_KEYS = (
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
FROZEN_V5_POLICY_BUNDLE_SHA256 = (
    "sha256:4c2fbee5d9e6488c2c378eceda6da0a49a415f6af3b3aa29f673bfaa93ee54a4"
)
FROZEN_V5_ADVANCED_ELIGIBILITY_SHA256 = (
    "sha256:8101c287ba024032c81f97d1768c0380cb061e57de0cb87838e6b032074d610f"
)


def _sha(value: str, name: str) -> None:
    if _SHA256_RE.fullmatch(value) is None:
        raise CiboCapitalManagementError(f"V5 source receipt {name} invalid")


@dataclass(frozen=True, slots=True)
class Phase22V5SourceBinding:
    symbol: str
    timeframe: str
    artifact_id: int
    artifact_digest: str
    manifest_sha256: str
    retained_bars: int

    def __post_init__(self) -> None:
        if (self.symbol, self.timeframe) not in EXPECTED_SOURCE_KEYS:
            raise CiboCapitalManagementError("V5 source binding outside exact surface")
        if (
            type(self.artifact_id) is not int
            or self.artifact_id <= 0
            or type(self.retained_bars) is not int
            or self.retained_bars <= 0
        ):
            raise CiboCapitalManagementError("V5 source numeric identity invalid")
        _sha(self.artifact_digest, "artifact digest")
        _sha(self.manifest_sha256, "manifest digest")


@dataclass(frozen=True, slots=True)
class Phase22V5SourceReceipt:
    candidate_id: str
    source_availability_run_id: int
    source_availability_artifact_id: int
    source_availability_artifact_digest: str
    corpus_run_id: int
    corpus_git_sha: str
    corpus_seal_artifact_id: int
    corpus_seal_artifact_digest: str
    bindings: tuple[Phase22V5SourceBinding, ...]
    policy_bundle_sha256: str
    advanced_scientific_eligibility_sha256: str
    source_validation_complete: bool
    source_outcomes_inspected: bool = False
    trader_logic_executed: bool = False
    broker_mutation: bool = False
    fresh_trader_execution_authorized: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.candidate_id != V5_CANDIDATE_ID:
            raise CiboCapitalManagementError("V5 source receipt candidate drift")
        for name in (
            "source_availability_run_id",
            "source_availability_artifact_id",
            "corpus_run_id",
            "corpus_seal_artifact_id",
        ):
            value = getattr(self, name)
            if type(value) is not int or value <= 0:
                raise CiboCapitalManagementError(
                    f"V5 source receipt {name} invalid"
                )
        _sha(
            self.source_availability_artifact_digest,
            "availability artifact digest",
        )
        if _SHA1_RE.fullmatch(self.corpus_git_sha) is None:
            raise CiboCapitalManagementError("V5 source receipt corpus Git SHA invalid")
        _sha(self.corpus_seal_artifact_digest, "corpus seal digest")
        if self.policy_bundle_sha256 != FROZEN_V5_POLICY_BUNDLE_SHA256:
            raise CiboCapitalManagementError(
                "V5 policy changed after prior fresh evidence"
            )
        if (
            self.advanced_scientific_eligibility_sha256
            != FROZEN_V5_ADVANCED_ELIGIBILITY_SHA256
        ):
            raise CiboCapitalManagementError(
                "V5 scientific eligibility changed after prior fresh cycle"
            )
        keys = tuple(sorted((item.symbol, item.timeframe) for item in self.bindings))
        if keys != EXPECTED_SOURCE_KEYS or len(self.bindings) != len(keys):
            raise CiboCapitalManagementError(
                "V5 source receipt requires exact ten-source surface"
            )
        if not self.source_validation_complete:
            raise CiboCapitalManagementError("V5 source validation incomplete")
        if any(
            (
                self.source_outcomes_inspected,
                self.trader_logic_executed,
                self.broker_mutation,
                self.fresh_trader_execution_authorized,
                self.productive_authority,
            )
        ):
            raise CiboCapitalManagementError(
                "V5 source receipt contains forbidden authority/outcome state"
            )

    def payload(self) -> dict[str, Any]:
        return {
            "schema": "qore.cibo.phase22.v5-source-receipt.v1",
            "candidate_id": self.candidate_id,
            "source_availability_run_id": self.source_availability_run_id,
            "source_availability_artifact_id": self.source_availability_artifact_id,
            "source_availability_artifact_digest": (
                self.source_availability_artifact_digest
            ),
            "corpus_run_id": self.corpus_run_id,
            "corpus_git_sha": self.corpus_git_sha,
            "corpus_seal_artifact_id": self.corpus_seal_artifact_id,
            "corpus_seal_artifact_digest": self.corpus_seal_artifact_digest,
            "bindings": [asdict(item) for item in self.bindings],
            "policy_bundle_sha256": self.policy_bundle_sha256,
            "advanced_scientific_eligibility_sha256": (
                self.advanced_scientific_eligibility_sha256
            ),
            "source_validation_complete": self.source_validation_complete,
            "source_outcomes_inspected": self.source_outcomes_inspected,
            "trader_logic_executed": self.trader_logic_executed,
            "broker_mutation": self.broker_mutation,
            "fresh_trader_execution_authorized": (
                self.fresh_trader_execution_authorized
            ),
            "productive_authority": self.productive_authority,
        }

    def fingerprint(self) -> str:
        raw = json.dumps(
            self.payload(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(raw).hexdigest()


def load_phase22_v5_source_receipt(path: Path) -> Phase22V5SourceReceipt:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise CiboCapitalManagementError("V5 source receipt JSON object required")
    bindings_raw = raw.get("bindings")
    if not isinstance(bindings_raw, list):
        raise CiboCapitalManagementError("V5 source receipt bindings missing")
    bindings = tuple(Phase22V5SourceBinding(**item) for item in bindings_raw)
    fields = dict(raw)
    fields.pop("schema", None)
    fields["bindings"] = bindings
    try:
        return Phase22V5SourceReceipt(**fields)
    except TypeError as error:
        raise CiboCapitalManagementError(
            "V5 source receipt shape invalid"
        ) from error
