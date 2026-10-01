"""Typed freeze contract for CIBO Phase22 seven-Trader replay parity.

This module does not manufacture parity. The active manifest remains absent
until all seven frozen Trader lanes have exact historical replay receipts.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from hashlib import sha256

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)

CANONICAL_PHASE22_TRADER_IDS = (
    "VT08_FOREX",
    "R34_XAUUSD",
    "R38_EURUSD",
    "R43_GBPUSD",
    "R38_GBPJPY",
    "R42_AUDJPY",
    "VT31_NAS100",
)

_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True, slots=True)
class Phase22TraderParityReceipt:
    trader_id: str
    methodology_git_sha: str
    replay_engine_sha256: str
    parameter_sha256: str
    historical_artifact_ref: str
    parity_artifact_ref: str
    parity_artifact_digest: str
    expected_population: int
    observed_population: int
    exact_match: bool
    methodology_changed: bool = False
    fresh_outcomes_executed: bool = False

    def __post_init__(self) -> None:
        if self.trader_id not in CANONICAL_PHASE22_TRADER_IDS:
            raise CiboCapitalManagementError("Phase22 parity Trader identity drift")
        if _GIT_SHA_RE.fullmatch(self.methodology_git_sha) is None:
            raise CiboCapitalManagementError(
                "Phase22 parity methodology Git SHA invalid"
            )
        for name in (
            "replay_engine_sha256",
            "parameter_sha256",
            "parity_artifact_digest",
        ):
            if _SHA256_RE.fullmatch(getattr(self, name)) is None:
                raise CiboCapitalManagementError(
                    f"Phase22 parity {name} invalid"
                )
        if not self.historical_artifact_ref or not self.parity_artifact_ref:
            raise CiboCapitalManagementError(
                "Phase22 parity artifact references are required"
            )
        if (
            type(self.expected_population) is not int
            or type(self.observed_population) is not int
            or self.expected_population <= 0
            or self.observed_population <= 0
        ):
            raise CiboCapitalManagementError(
                "Phase22 parity populations must be positive int"
            )
        if (
            self.observed_population != self.expected_population
            or not self.exact_match
        ):
            raise CiboCapitalManagementError(
                "Phase22 parity receipt requires exact population match"
            )
        if self.methodology_changed or self.fresh_outcomes_executed:
            raise CiboCapitalManagementError(
                "Phase22 parity cannot change methodology or execute fresh outcomes"
            )


@dataclass(frozen=True, slots=True)
class CiboPhase22TraderParityManifest:
    receipts: tuple[Phase22TraderParityReceipt, ...]
    productive_authority: bool = False

    def __post_init__(self) -> None:
        ids = tuple(item.trader_id for item in self.receipts)
        if ids != CANONICAL_PHASE22_TRADER_IDS:
            raise CiboCapitalManagementError(
                "Phase22 parity manifest requires exact ordered 7/7 surface"
            )
        if len(ids) != len(set(ids)):
            raise CiboCapitalManagementError(
                "Phase22 parity manifest contains duplicate Trader"
            )
        if self.productive_authority:
            raise CiboCapitalManagementError(
                "Phase22 parity manifest cannot grant productive authority"
            )

    def fingerprint(self) -> str:
        raw = json.dumps(
            {
                "schema": "qore.cibo.phase22.trader-parity-manifest.v2",
                "receipts": [asdict(item) for item in self.receipts],
                "productive_authority": False,
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return f"sha256:{sha256(raw).hexdigest()}"


ACTIVE_PHASE22_TRADER_PARITY_MANIFEST: CiboPhase22TraderParityManifest | None = None
