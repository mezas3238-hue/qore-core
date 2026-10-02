"""Typed freeze contract for CIBO Phase22 seven-Trader replay parity.

All seven receipts below bind completed immutable replay evidence. This module
grants no fresh execution, productive, LIVE or real-capital authority.
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

    def payload(self) -> dict[str, object]:
        return {
            "schema": "qore.cibo.phase22.trader-parity-manifest.v2",
            "receipts": [asdict(item) for item in self.receipts],
            "productive_authority": False,
            "manifest_sha256": self.fingerprint(),
        }

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


ACTIVE_PHASE22_TRADER_PARITY_MANIFEST = CiboPhase22TraderParityManifest(
    receipts=(
        Phase22TraderParityReceipt(
            trader_id="VT08_FOREX",
            methodology_git_sha=(
                "64bc2ab4809c39e4a2b2c72aa8c0e8ec1c709222"
            ),
            replay_engine_sha256=(
                "sha256:fedc34479059d058400961f02a6b1477ee8d538311f3a1fe"
                "9a628ebba41978a7"
            ),
            parameter_sha256=(
                "sha256:0c3fe8e1353386f7384a8532c7fe71bbbe9fcfdf1da7530b"
                "e4b53e01bc59de0d"
            ),
            historical_artifact_ref="github-actions-artifact://10318827002",
            parity_artifact_ref="github-actions-artifact://11182702511",
            parity_artifact_digest=(
                "sha256:3f76be54849ee9b08c49f1ac1c63196a722358d554165792"
                "fb1c6683f494dcea"
            ),
            expected_population=124,
            observed_population=124,
            exact_match=True,
        ),
        Phase22TraderParityReceipt(
            trader_id="R34_XAUUSD",
            methodology_git_sha=(
                "56ef138ee5ea1cde6d0bcf4c9e25e8b661c04e84"
            ),
            replay_engine_sha256=(
                "sha256:e1cf7c5cf10cc4820bd363dd460700699ae024574680b2feb"
                "b1656021f5b15db"
            ),
            parameter_sha256=(
                "sha256:1439d47e69c7c23a7354b8c70cc1519807ae711ab9da002d"
                "3eb220dbed4279a6"
            ),
            historical_artifact_ref="github-actions-artifact://10532254052",
            parity_artifact_ref="github-actions-artifact://11181833135",
            parity_artifact_digest=(
                "sha256:555e9461964afcf5e55408469d938f28d5be5ab3b6dcd103"
                "c5e6073addec84c2"
            ),
            expected_population=921,
            observed_population=921,
            exact_match=True,
        ),
        Phase22TraderParityReceipt(
            trader_id="R38_EURUSD",
            methodology_git_sha=(
                "324fb91d44a6fa328e66de2e22ace7386630c7aa"
            ),
            replay_engine_sha256=(
                "sha256:baafaaf385a91b17d9427ba56dc563ab30e453f065fe84d8"
                "8436a7ba6c402b27"
            ),
            parameter_sha256=(
                "sha256:68b007942b1e8583bfaed2568661cbd01142902d169fb534"
                "4a423bb960aa2aa8"
            ),
            historical_artifact_ref="github-actions-artifact://10539313228",
            parity_artifact_ref="github-actions-artifact://11182303601",
            parity_artifact_digest=(
                "sha256:5b9857edaf33060349b8d087adc3ca92b442509169f1342c"
                "3b7abb12e2d71ba8"
            ),
            expected_population=863,
            observed_population=863,
            exact_match=True,
        ),
        Phase22TraderParityReceipt(
            trader_id="R43_GBPUSD",
            methodology_git_sha=(
                "e02d9384fbe6521040fc2779a085c43b8d5f0f92"
            ),
            replay_engine_sha256=(
                "sha256:1dc90f9fe97e153817502c988d03768c4d15e8e4eb01a842"
                "4efa764d3a984404"
            ),
            parameter_sha256=(
                "sha256:c86c10d7bdfc6e226c1005791a05d9257472915bbf117a7e"
                "e7344572af85614b"
            ),
            historical_artifact_ref="github-actions-artifact://10552052483",
            parity_artifact_ref="github-actions-artifact://11182151896",
            parity_artifact_digest=(
                "sha256:6df15ca07027b91915372046979f5d70dd62d63580ee6414"
                "1494ee16a9edefba"
            ),
            expected_population=907,
            observed_population=907,
            exact_match=True,
        ),
        Phase22TraderParityReceipt(
            trader_id="R38_GBPJPY",
            methodology_git_sha=(
                "eb62226e05f63cf94c1940634de676c55285e6dd"
            ),
            replay_engine_sha256=(
                "sha256:a503ee2edae98910c2c46d4734c5dc07a17acce33115fab7"
                "166d63ba343fe6f0"
            ),
            parameter_sha256=(
                "sha256:5c3a9d899827773fa84db8166f63ac669284b161c3fd572b"
                "953a73d2dfd7f3f4"
            ),
            historical_artifact_ref="github-actions-artifact://10559826734",
            parity_artifact_ref="github-actions-artifact://11181798303",
            parity_artifact_digest=(
                "sha256:e0911a2e75ca6837a013f927e8cbaeeb275f1890ea058982"
                "8fc28b408b78fc27"
            ),
            expected_population=897,
            observed_population=897,
            exact_match=True,
        ),
        Phase22TraderParityReceipt(
            trader_id="R42_AUDJPY",
            methodology_git_sha=(
                "a332b077598e070a42b2497b3766d55e731f7dca"
            ),
            replay_engine_sha256=(
                "sha256:2ea67b9007d94c1eef52c7575b0bf72c9e30ee2ca1a1f988"
                "1b2e3deed5ef2204"
            ),
            parameter_sha256=(
                "sha256:94b7f28c0bf3ed8793019a1fc27e5db9a52d861948975833"
                "76719b040fcc6037"
            ),
            historical_artifact_ref="github-actions-artifact://10569333275",
            parity_artifact_ref="github-actions-artifact://11182541377",
            parity_artifact_digest=(
                "sha256:77ab74f059c27b2f792c23758707133a544d3ac5f0604e35"
                "3a26f711746672a6"
            ),
            expected_population=1039,
            observed_population=1039,
            exact_match=True,
        ),
        Phase22TraderParityReceipt(
            trader_id="VT31_NAS100",
            methodology_git_sha=(
                "cac38ed14f20e066536910145027426fd23f5939"
            ),
            replay_engine_sha256=(
                "sha256:9b5ae633d9392dc3f74dfaa5688124f97017872f24a105f6"
                "f6cf5ad4a959ab9c"
            ),
            parameter_sha256=(
                "sha256:089c41f98a72295278063cfc29caf8419538f68315d9f5e5"
                "7be144fbdae15e08"
            ),
            historical_artifact_ref="github-actions-artifact://10610673464",
            parity_artifact_ref="github-actions-artifact://11182901805",
            parity_artifact_digest=(
                "sha256:dc27de2c99c42c1fa5be2e35efb141cc155dba795d21cdd"
                "80479c2100480df08"
            ),
            expected_population=806,
            observed_population=806,
            exact_match=True,
        ),
    )
)
