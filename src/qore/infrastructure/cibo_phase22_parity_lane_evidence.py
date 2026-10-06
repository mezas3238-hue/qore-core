"""Typed evidence contract for one CIBO Phase22 Trader parity lane."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from hashlib import sha256

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_phase22_trader_parity_manifest import (
    CANONICAL_PHASE22_TRADER_IDS,
)

_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True, slots=True)
class CiboPhase22ParityLaneEvidence:
    trader_id: str
    frozen_source_git_sha: str
    methodology_sha256: str
    replay_engine_sha256: str
    parameter_sha256: str
    authorized_markets: tuple[str, ...]
    processed_markets: tuple[str, ...]
    historical_artifact_refs: tuple[str, ...]
    expected_population: int
    observed_population: int
    exact_historical_match: bool
    methodology_changed: bool = False
    fresh_outcomes_executed: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.trader_id not in CANONICAL_PHASE22_TRADER_IDS:
            raise CiboCapitalManagementError("Phase22 parity lane Trader drift")
        if _GIT_SHA_RE.fullmatch(self.frozen_source_git_sha) is None:
            raise CiboCapitalManagementError(
                "Phase22 parity lane source Git SHA invalid"
            )
        for name in (
            "methodology_sha256",
            "replay_engine_sha256",
            "parameter_sha256",
        ):
            if _SHA256_RE.fullmatch(getattr(self, name)) is None:
                raise CiboCapitalManagementError(
                    f"Phase22 parity lane {name} invalid"
                )
        if not self.authorized_markets:
            raise CiboCapitalManagementError(
                "Phase22 parity lane requires market authority"
            )
        if (
            len(self.authorized_markets) != len(set(self.authorized_markets))
            or self.processed_markets != self.authorized_markets
        ):
            raise CiboCapitalManagementError(
                "Phase22 parity lane must process exact authorized markets"
            )
        if (
            not self.historical_artifact_refs
            or len(self.historical_artifact_refs)
            != len(set(self.historical_artifact_refs))
        ):
            raise CiboCapitalManagementError(
                "Phase22 parity lane historical evidence refs invalid"
            )
        if (
            type(self.expected_population) is not int
            or type(self.observed_population) is not int
            or self.expected_population <= 0
            or self.observed_population <= 0
            or self.expected_population != self.observed_population
            or not self.exact_historical_match
        ):
            raise CiboCapitalManagementError(
                "Phase22 parity lane requires exact positive population match"
            )
        if (
            self.methodology_changed
            or self.fresh_outcomes_executed
            or self.productive_authority
        ):
            raise CiboCapitalManagementError(
                "Phase22 parity lane governance drift"
            )

    def payload(self) -> dict[str, object]:
        return {
            "schema": "qore.cibo.phase22.trader-parity-lane.v2",
            **asdict(self),
            "lane_sha256": self.fingerprint(),
        }

    def fingerprint(self) -> str:
        raw = json.dumps(
            {
                "trader_id": self.trader_id,
                "frozen_source_git_sha": self.frozen_source_git_sha,
                "methodology_sha256": self.methodology_sha256,
                "replay_engine_sha256": self.replay_engine_sha256,
                "parameter_sha256": self.parameter_sha256,
                "authorized_markets": list(self.authorized_markets),
                "processed_markets": list(self.processed_markets),
                "historical_artifact_refs": list(self.historical_artifact_refs),
                "expected_population": self.expected_population,
                "observed_population": self.observed_population,
                "exact_historical_match": self.exact_historical_match,
                "methodology_changed": False,
                "fresh_outcomes_executed": False,
                "productive_authority": False,
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return f"sha256:{sha256(raw).hexdigest()}"
