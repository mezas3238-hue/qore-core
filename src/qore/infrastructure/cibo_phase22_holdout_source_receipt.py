"""Immutable receipt for the fresh CIBO 2017H1 Phase22 market source set.

The receipt binds the blind source-validation artifact and all nine immutable
Market Atlas archives required by the six single-symbol Traders plus the full
VT08 Forex authority. It contains no Trader outcomes and grants no productive
authority.
"""

from __future__ import annotations

from dataclasses import dataclass

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)

PHASE22_SOURCE_VALIDATION_RUN_ID = 36879071685
PHASE22_SOURCE_VALIDATION_ARTIFACT_ID = 11170192880
PHASE22_SOURCE_VALIDATION_ARTIFACT_DIGEST = (
    "sha256:fc7d26e1398487e1b984162206fd21e5fb4360c779d30916c02445ed8fbd6001"
)
PHASE22_SOURCE_VALIDATION_HEAD_SHA = (
    "5decb8177589018555465ab67ce2628dda422fb0"
)

SOURCE_ARCHIVES = (
    ("AUDJPY", 10476530915, "a416085cfcef04003ae89debaad360304a0c4c8bac65b3bf2b439a8a4b7098bf"),
    ("AUDUSD", 10475697610, "ac72aaf438c164cd79691a7cf1f3f0a68f4c65aa6a91a921a721c7a04ebdc2f0"),
    ("EURUSD", 10475354631, "e0fa9e316b79ba61c338161a57508359d4c6afe2fbf97d3f50f1e27c2d359a86"),
    ("GBPJPY", 10475453293, "b68e74b2afa54295f891c11cde19e12e92db4192930496036c7ebb372474e415"),
    ("GBPUSD", 10475449182, "77d5b65ce3c6763e3ac5f620e4167d4ef071bfe1c13746cd5ca7ad9788268dcf"),
    ("NAS100", 10476153072, "87ae8095feadce23c5026cda4dada49765d44d0baa2237b5bd7704ccc8deb863"),
    ("USDCAD", 10475972108, "35d57d024121dcfbbbfd201bd6bfd5f5250895cdfe7c47a817e58de32392ee50"),
    ("USDJPY", 10475389415, "e3ac9a45f3000c3e3bd93e50c730c952ddd08f77f1c857b5c4b3a67679fcaa51"),
    ("XAUUSD", 10476557530, "dcb905b11380e3d4e1a4dc621e269bb75d2886806dd662e260d21d1d15362e08"),
)

VT08_REQUIRED_MARKETS = (
    "AUDJPY",
    "AUDUSD",
    "EURUSD",
    "GBPJPY",
    "GBPUSD",
    "USDCAD",
    "USDJPY",
)


@dataclass(frozen=True, slots=True)
class CiboPhase22HoldoutSourceReceipt:
    candidate_id: str
    source_ready: bool
    burn_clean: bool
    source_validation_run_id: int
    source_validation_artifact_id: int
    source_validation_artifact_digest: str
    source_validation_head_sha: str
    source_archives: tuple[tuple[str, int, str], ...]
    trader_outcomes_executed: bool = False
    selection_outcomes_inspected: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.candidate_id != "CIBO_USD60_6M_HOLDOUT_2017H1_V1":
            raise CiboCapitalManagementError(
                "Phase22 source receipt candidate identity drift"
            )
        if not self.source_ready or not self.burn_clean:
            raise CiboCapitalManagementError(
                "Phase22 source receipt requires ready burn-clean source"
            )
        if self.source_validation_run_id != PHASE22_SOURCE_VALIDATION_RUN_ID:
            raise CiboCapitalManagementError(
                "Phase22 source receipt workflow lineage drift"
            )
        if (
            self.source_validation_artifact_id
            != PHASE22_SOURCE_VALIDATION_ARTIFACT_ID
        ):
            raise CiboCapitalManagementError(
                "Phase22 source receipt artifact lineage drift"
            )
        if (
            self.source_validation_artifact_digest
            != PHASE22_SOURCE_VALIDATION_ARTIFACT_DIGEST
        ):
            raise CiboCapitalManagementError(
                "Phase22 source receipt artifact digest drift"
            )
        if self.source_validation_head_sha != PHASE22_SOURCE_VALIDATION_HEAD_SHA:
            raise CiboCapitalManagementError(
                "Phase22 source receipt head lineage drift"
            )
        if self.source_archives != SOURCE_ARCHIVES:
            raise CiboCapitalManagementError(
                "Phase22 source receipt archive set drift"
            )
        symbols = tuple(item[0] for item in self.source_archives)
        if len(symbols) != len(set(symbols)):
            raise CiboCapitalManagementError(
                "Phase22 source receipt duplicate symbol"
            )
        if not set(VT08_REQUIRED_MARKETS).issubset(set(symbols)):
            raise CiboCapitalManagementError(
                "Phase22 source receipt does not cover VT08 Forex authority"
            )
        for symbol, artifact_id, digest in self.source_archives:
            if not symbol:
                raise CiboCapitalManagementError(
                    "Phase22 source receipt symbol required"
                )
            if (
                not isinstance(artifact_id, int)
                or isinstance(artifact_id, bool)
                or artifact_id <= 0
            ):
                raise CiboCapitalManagementError(
                    "Phase22 source receipt artifact id invalid"
                )
            if (
                len(digest) != 64
                or any(char not in "0123456789abcdef" for char in digest)
            ):
                raise CiboCapitalManagementError(
                    "Phase22 source receipt source digest invalid"
                )
        if (
            self.trader_outcomes_executed
            or self.selection_outcomes_inspected
            or self.productive_authority
        ):
            raise CiboCapitalManagementError(
                "Phase22 source receipt cannot contain outcomes/authority"
            )


PHASE22_HOLDOUT_SOURCE_RECEIPT = CiboPhase22HoldoutSourceReceipt(
    candidate_id="CIBO_USD60_6M_HOLDOUT_2017H1_V1",
    source_ready=True,
    burn_clean=True,
    source_validation_run_id=PHASE22_SOURCE_VALIDATION_RUN_ID,
    source_validation_artifact_id=PHASE22_SOURCE_VALIDATION_ARTIFACT_ID,
    source_validation_artifact_digest=PHASE22_SOURCE_VALIDATION_ARTIFACT_DIGEST,
    source_validation_head_sha=PHASE22_SOURCE_VALIDATION_HEAD_SHA,
    source_archives=SOURCE_ARCHIVES,
)


def phase22_holdout_source_receipt_payload() -> dict[str, object]:
    receipt = PHASE22_HOLDOUT_SOURCE_RECEIPT
    return {
        "schema": "qore.cibo.phase22.holdout-source-receipt.v1",
        "candidate_id": receipt.candidate_id,
        "source_ready": receipt.source_ready,
        "burn_clean": receipt.burn_clean,
        "source_validation": {
            "run_id": receipt.source_validation_run_id,
            "artifact_id": receipt.source_validation_artifact_id,
            "artifact_digest": receipt.source_validation_artifact_digest,
            "head_sha": receipt.source_validation_head_sha,
        },
        "source_archives": [
            {
                "symbol": symbol,
                "artifact_id": artifact_id,
                "zip_sha256": digest,
            }
            for symbol, artifact_id, digest in receipt.source_archives
        ],
        "vt08_required_markets": list(VT08_REQUIRED_MARKETS),
        "trader_outcomes_executed": False,
        "selection_outcomes_inspected": False,
        "productive_authority": False,
    }
