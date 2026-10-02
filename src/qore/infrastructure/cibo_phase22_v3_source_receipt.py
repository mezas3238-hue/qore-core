"""Canonical receipt contract for the next Phase22 V3 market source.

The receipt binds sanitized GitHub Actions source artifacts only. It cannot
collect market data, execute Traders, inspect outcomes, mutate broker state or
authorize the one-shot exam.
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
from qore.infrastructure.cibo_phase22_next_exam_governance import (
    NEXT_PHASE22_CANDIDATE,
)

_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_EXPECTED_SOURCE_KEYS = (
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
class Phase22V3SourceBinding:
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
        if (self.symbol, self.timeframe) not in _EXPECTED_SOURCE_KEYS:
            raise CiboCapitalManagementError(
                "V3 source binding identity outside exact surface"
            )
        if self.timeframe == "M1" and self.symbol != "NAS100":
            raise CiboCapitalManagementError(
                "V3 source only permits NAS100 M1"
            )
        for name in ("artifact_id", "retained_bars"):
            value = getattr(self, name)
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value <= 0
            ):
                raise CiboCapitalManagementError(
                    f"V3 source {name} must be positive int"
                )
        for name in ("artifact_digest", "manifest_sha256"):
            if _SHA256_RE.fullmatch(getattr(self, name)) is None:
                raise CiboCapitalManagementError(
                    f"V3 source {name} invalid"
                )
        if _GIT_SHA_RE.fullmatch(self.collector_git_sha) is None:
            raise CiboCapitalManagementError(
                "V3 source collector Git SHA invalid"
            )
        first = datetime.fromisoformat(self.first_observed_at)
        last = datetime.fromisoformat(self.last_observed_at)
        for value, name in ((first, "first"), (last, "last")):
            if value.tzinfo is None or value.utcoffset() is None:
                raise CiboCapitalManagementError(
                    f"V3 source {name} timestamp must be aware"
                )
        candidate = NEXT_PHASE22_CANDIDATE
        if not (
            candidate.start_at
            <= first
            < candidate.end_exclusive_at
        ):
            raise CiboCapitalManagementError(
                "V3 source first observation outside candidate"
            )
        if not (
            candidate.start_at
            <= last
            < candidate.end_exclusive_at
        ):
            raise CiboCapitalManagementError(
                "V3 source last observation outside candidate"
            )
        if last < first:
            raise CiboCapitalManagementError(
                "V3 source observation chronology invalid"
            )


@dataclass(frozen=True, slots=True)
class Phase22V3SourceReceipt:
    candidate_id: str
    source_availability_run_id: int
    source_availability_artifact_id: int
    source_availability_artifact_digest: str
    corpus_run_id: int
    corpus_seal_artifact_id: int
    corpus_seal_artifact_digest: str
    bindings: tuple[Phase22V3SourceBinding, ...]
    policy_bundle_sha256: str
    advanced_scientific_eligibility_sha256: str
    source_validation_complete: bool
    source_outcomes_inspected: bool = False
    trader_logic_executed: bool = False
    broker_mutation: bool = False
    fresh_trader_execution_authorized: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        candidate = NEXT_PHASE22_CANDIDATE
        if self.candidate_id != candidate.candidate_id:
            raise CiboCapitalManagementError(
                "V3 source receipt candidate identity drift"
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
                    f"V3 source receipt {name} invalid"
                )
        for name in (
            "source_availability_artifact_digest",
            "corpus_seal_artifact_digest",
            "policy_bundle_sha256",
            "advanced_scientific_eligibility_sha256",
        ):
            if _SHA256_RE.fullmatch(getattr(self, name)) is None:
                raise CiboCapitalManagementError(
                    f"V3 source receipt {name} invalid"
                )
        if self.policy_bundle_sha256 != (
            NEXT_POLICY_CODE_BUNDLE_LINEAGE.fingerprint()
        ):
            raise CiboCapitalManagementError(
                "V3 source receipt policy bundle drift"
            )
        if self.advanced_scientific_eligibility_sha256 != (
            NEXT_POLICY_ADVANCED_SCIENTIFIC_ELIGIBILITY.fingerprint()
        ):
            raise CiboCapitalManagementError(
                "V3 source receipt advanced eligibility drift"
            )
        keys = tuple(
            sorted(
                (item.symbol, item.timeframe)
                for item in self.bindings
            )
        )
        if keys != _EXPECTED_SOURCE_KEYS:
            raise CiboCapitalManagementError(
                "V3 source receipt exact 10-source surface required"
            )
        if len(self.bindings) != len(keys):
            raise CiboCapitalManagementError(
                "V3 source receipt duplicate binding"
            )
        if not self.source_validation_complete:
            raise CiboCapitalManagementError(
                "V3 source receipt cannot materialize incomplete validation"
            )
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
                "V3 source receipt governance contamination"
            )

    def payload(self) -> dict[str, object]:
        candidate = NEXT_PHASE22_CANDIDATE
        return {
            "schema": "qore.cibo.phase22.v3-source-receipt.v1",
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
            "corpus_seal_artifact_digest": (
                self.corpus_seal_artifact_digest
            ),
            "bindings": [asdict(item) for item in self.bindings],
            "policy_bundle_sha256": self.policy_bundle_sha256,
            "advanced_scientific_eligibility_sha256": (
                self.advanced_scientific_eligibility_sha256
            ),
            "source_validation_complete": True,
            "source_outcomes_inspected": False,
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


PHASE22_V3_SOURCE_RECEIPT = Phase22V3SourceReceipt(
    candidate_id="CIBO_USD60_6M_HOLDOUT_2015-04-19_2015-10-19_V3",
    source_availability_run_id=37027014266,
    source_availability_artifact_id=11235766192,
    source_availability_artifact_digest=(
        "sha256:225c0ab8020be63fae37d44f5f3435550f61e53002e7277dc6a48fcd79c30961"
    ),
    corpus_run_id=37027578451,
    corpus_seal_artifact_id=11235822790,
    corpus_seal_artifact_digest=(
        "sha256:76efe25e3dbab67be02d00a38d8f93edba54c136d6c6ef4e1d629535d3c95c36"
    ),
    bindings=(
        Phase22V3SourceBinding(
            symbol="AUDJPY",
            timeframe="M5",
            artifact_id=11236400346,
            artifact_digest=(
                "sha256:2886b2f0107b38affcd1b13d5fb043ac30be4a963217768c0c20099a0a529bd2"
            ),
            collector_git_sha="448a52d66072fcaf3205ac6ffaeefdabdb026946",
            manifest_sha256=(
                "sha256:3fc09c663ed46d460df88fd4e047198e2748b5050ecc6e6ea2404d54f7df5734"
            ),
            retained_bars=37423,
            first_observed_at="2015-04-19T21:00:00+00:00",
            last_observed_at="2015-10-18T23:55:00+00:00",
        ),
        Phase22V3SourceBinding(
            symbol="AUDUSD",
            timeframe="M5",
            artifact_id=11236136916,
            artifact_digest=(
                "sha256:b9350303d991bec0d088adfc9b150ba309c8b1328f644efa671aa0900c33ec52"
            ),
            collector_git_sha="448a52d66072fcaf3205ac6ffaeefdabdb026946",
            manifest_sha256=(
                "sha256:b8757859b4dc69a19b770fd0ef8467083219b0a8052f3997883864ff86b78602"
            ),
            retained_bars=37422,
            first_observed_at="2015-04-19T21:00:00+00:00",
            last_observed_at="2015-10-18T23:55:00+00:00",
        ),
        Phase22V3SourceBinding(
            symbol="EURUSD",
            timeframe="M5",
            artifact_id=11235697327,
            artifact_digest=(
                "sha256:d5aec4402de5be4597398c91758b9db6b54857970080285b4393537704f6698f"
            ),
            collector_git_sha="448a52d66072fcaf3205ac6ffaeefdabdb026946",
            manifest_sha256=(
                "sha256:1c161f83a8432fcd2c1df2b38aabdfd4a16a38b685e44bbc4ec6457c48918531"
            ),
            retained_bars=37420,
            first_observed_at="2015-04-19T21:00:00+00:00",
            last_observed_at="2015-10-18T23:55:00+00:00",
        ),
        Phase22V3SourceBinding(
            symbol="GBPJPY",
            timeframe="M5",
            artifact_id=11236645380,
            artifact_digest=(
                "sha256:a34fe0fd72ba86fd5ef463d177b88f39613fa72122e2368a629bcf33a2c6e355"
            ),
            collector_git_sha="448a52d66072fcaf3205ac6ffaeefdabdb026946",
            manifest_sha256=(
                "sha256:7850b47f0682d2199558eb0d64a3630a066bee515fa62368b575bc05c771c72b"
            ),
            retained_bars=37422,
            first_observed_at="2015-04-19T21:00:00+00:00",
            last_observed_at="2015-10-18T23:55:00+00:00",
        ),
        Phase22V3SourceBinding(
            symbol="GBPUSD",
            timeframe="M5",
            artifact_id=11235652665,
            artifact_digest=(
                "sha256:c45ccb5618e7d6261e0ed7af5f5a20965a623dbc1cbbbd9480e234bd78b6be9c"
            ),
            collector_git_sha="448a52d66072fcaf3205ac6ffaeefdabdb026946",
            manifest_sha256=(
                "sha256:83ae3a871de52f4f883fadc22b21c152c488e4bdbc3b5a2a3eec4285eebb4c2b"
            ),
            retained_bars=37421,
            first_observed_at="2015-04-19T21:00:00+00:00",
            last_observed_at="2015-10-18T23:55:00+00:00",
        ),
        Phase22V3SourceBinding(
            symbol="NAS100",
            timeframe="M1",
            artifact_id=11235612657,
            artifact_digest=(
                "sha256:9560ff79bfe318d34d6f889cd723a83b1d82a293e1ecdeaaa9e281f50e76347d"
            ),
            collector_git_sha="448a52d66072fcaf3205ac6ffaeefdabdb026946",
            manifest_sha256=(
                "sha256:aef26b52d0d1caa2c68a32515d44a0997b22ef50a0b62552813dea65f2a8aaeb"
            ),
            retained_bars=168204,
            first_observed_at="2015-04-19T21:03:00+00:00",
            last_observed_at="2015-10-18T23:59:00+00:00",
        ),
        Phase22V3SourceBinding(
            symbol="NAS100",
            timeframe="M5",
            artifact_id=11235637559,
            artifact_digest=(
                "sha256:2a94f32997d69e01101ee99a64d6129c5c663d318b37658ed4ddd2e08ef8d97d"
            ),
            collector_git_sha="448a52d66072fcaf3205ac6ffaeefdabdb026946",
            manifest_sha256=(
                "sha256:d3bd22af0060e902384e75b58681becfe3e64dd96e60276becdbb3c9e998338a"
            ),
            retained_bars=35420,
            first_observed_at="2015-04-19T21:00:00+00:00",
            last_observed_at="2015-10-18T23:55:00+00:00",
        ),
        Phase22V3SourceBinding(
            symbol="USDCAD",
            timeframe="M5",
            artifact_id=11236185950,
            artifact_digest=(
                "sha256:84e70c28d2bf79120f4f1dc6521c815942411fe9b90b09f638416fb11fc719fe"
            ),
            collector_git_sha="448a52d66072fcaf3205ac6ffaeefdabdb026946",
            manifest_sha256=(
                "sha256:b19ae6d4dfb912953f9332edb3fa7e9c6f5252df5c394f866f6eb8cd74f9d6fc"
            ),
            retained_bars=37417,
            first_observed_at="2015-04-19T21:00:00+00:00",
            last_observed_at="2015-10-18T23:55:00+00:00",
        ),
        Phase22V3SourceBinding(
            symbol="USDJPY",
            timeframe="M5",
            artifact_id=11235902653,
            artifact_digest=(
                "sha256:4f5502075ee30cd45f1a76d49b1ad606b7fc9299637be1c84a74176e8f0b6571"
            ),
            collector_git_sha="448a52d66072fcaf3205ac6ffaeefdabdb026946",
            manifest_sha256=(
                "sha256:75c7d142b5f6bee8f9607eaaa4e07ed15e848b7c44971329936c9ba94bf92cee"
            ),
            retained_bars=37421,
            first_observed_at="2015-04-19T21:00:00+00:00",
            last_observed_at="2015-10-18T23:55:00+00:00",
        ),
        Phase22V3SourceBinding(
            symbol="XAUUSD",
            timeframe="M5",
            artifact_id=11236022445,
            artifact_digest=(
                "sha256:12b8fde58b7cb15575b3ab3b6d2e6c8e378a78f72cb8d86007ce0b14f7be0b4f"
            ),
            collector_git_sha="448a52d66072fcaf3205ac6ffaeefdabdb026946",
            manifest_sha256=(
                "sha256:5955d24d3d8901489aa4acc8f9e417fcf7a274ef2d36cc16f02eda91d618e5ef"
            ),
            retained_bars=35698,
            first_observed_at="2015-04-19T22:00:00+00:00",
            last_observed_at="2015-10-18T23:55:00+00:00",
        ),
    ),
    policy_bundle_sha256=(
        "sha256:4c2fbee5d9e6488c2c378eceda6da0a49a415f6af3b3aa29f673bfaa93ee54a4"
    ),
    advanced_scientific_eligibility_sha256=(
        "sha256:8101c287ba024032c81f97d1768c0380cb061e57de0cb87838e6b032074d610f"
    ),
    source_validation_complete=True,
)


def phase22_v3_source_receipt_payload() -> dict[str, object]:
    return PHASE22_V3_SOURCE_RECEIPT.payload()


def phase22_v3_source_receipt_sha256() -> str:
    return PHASE22_V3_SOURCE_RECEIPT.fingerprint()
